"""Trusted updater: release validation, code-only transaction and restart supervisor."""
import argparse
import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

MAX_ZIP = 16 * 1024 * 1024
MAX_UNPACKED = 64 * 1024 * 1024
CORE = {'app.py','index.html','webtools.py','providers.py','codex_tasks.py','start.bat','upgrade.bat',
        'upgrade.py','update_runtime.py','version.json','verify-codex.bat','build_release.py','setup.bat','setup.ps1'}
CORE.update({'agent_runtime.py','admin_broker.py','tool_bridge.py','ui_extensions.js',
             'runtime/worker.mjs','runtime/snapshot.mjs','runtime/package.json','runtime/package-lock.json',
             'vendor/golemancy/LICENSE','vendor/golemancy/NOTICE.md'})
HOSTS = {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
REQUIRED = {'app.py','index.html','codex_tasks.py','providers.py','webtools.py','update_runtime.py','version.json'}


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):
        raise ValueError('Use a stable three-part release version, e.g. 0.5.0.')
    return tuple(int(n) for n in value.split('.'))


def current_version(root):
    try: return json.loads((Path(root)/'version.json').read_text())['version']
    except FileNotFoundError: return '0.4.0'


def allowed(name):
    return name in CORE or bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.md',name)) or bool(re.fullmatch(r'tests/test_[A-Za-z0-9_]+\.py|tests/ui_logic\.cjs',name))


def repo_name(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}',value) or value.split('/')[1] in ('.','..'):
        raise ValueError('Enter a GitHub repository as owner/repository.')
    return value


def checked_url(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Only official GitHub HTTPS update endpoints are accepted.')
    return url


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return super().redirect_request(req,fp,code,msg,headers,checked_url(newurl))


def fetch(url,limit):
    req=urllib.request.Request(checked_url(url),headers={'User-Agent':'TREN-Updater','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    try:
        with urllib.request.build_opener(Redirects()).open(req,timeout=30) as r:
            checked_url(r.url);data=r.read(limit+1)
            if len(data)>limit:raise ValueError('Update response exceeds size limit.')
            return data
    except urllib.error.HTTPError as e:
        if e.code==404:raise ValueError('No public release found. Check the repository and publish a stable release.') from e
        if e.code in (403,429):raise ValueError('GitHub rate limit or access restriction. Try later or use a downloaded ZIP.') from e
        raise ValueError('GitHub update request failed: HTTP '+str(e.code)) from e
    except (urllib.error.URLError,TimeoutError) as e:raise ValueError('Cannot reach GitHub. Check connection or use a downloaded ZIP.') from e


def release(repo):
    repo=repo_name(repo);r=json.loads(fetch('https://api.github.com/repos/'+repo+'/releases/latest',1024*1024))
    if r.get('draft') or r.get('prerelease'):raise ValueError('Only stable published releases are accepted.')
    v=str(r.get('tag_name','')).removeprefix('v');version(v)
    candidates=[a for a in r.get('assets',[]) if a.get('name')=='TREN-v'+v+'.zip']
    if len(candidates)!=1:raise ValueError('Release must contain one asset named TREN-v'+v+'.zip.')
    a=candidates[0];digest=a.get('digest','')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest):raise ValueError('GitHub did not provide a SHA-256 asset digest; use ZIP import or republish the release.')
    url=a.get('browser_download_url','');checked_url(url)
    expected='https://github.com/'+repo+'/releases/download/'+r['tag_name']+'/'+a['name']
    if url!=expected:raise ValueError('Release download does not belong to the selected repository.')
    if type(a.get('size')) is not int or not 0<a['size']<=MAX_ZIP:raise ValueError('Update asset exceeds size limit.')
    return {'version':v,'url':url,'sha256':digest[7:],'size':a['size'],'notes':str(r.get('body',''))[:8000]}


def validate_archive(path,expected_version=None):
    path=Path(path)
    if not 0<path.stat().st_size<=MAX_ZIP:raise ValueError('ZIP must be between 1 byte and 16 MiB.')
    with zipfile.ZipFile(path) as z:
        entries=z.infolist()
        if len(entries)>300 or sum(i.file_size for i in entries)>MAX_UNPACKED:raise ValueError('Update archive exceeds file/expanded-size limits.')
        names=[i.filename for i in entries]
        if len(set(names))!=len(names):raise ValueError('Duplicate archive paths.')
        for i in entries:
            n=i.filename
            if '\\' in n or ':' in n or n.startswith('/') or '..' in PurePosixPath(n).parts or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe archive path or link.')
            if i.is_dir():continue
            if not n.startswith('Tren-Local/') or not (allowed(n[len('Tren-Local/'):]) or n=='Tren-Local/update-manifest.json'):raise ValueError('Unexpected file in update: '+n)
        try:m=json.loads(z.read('Tren-Local/update-manifest.json'))
        except (KeyError,ValueError):raise ValueError('Missing/invalid update-manifest.json.')
        if not isinstance(m,dict):raise ValueError('Manifest must be an object.')
        v=m.get('version');version(v)
        if m.get('format')!=1 or expected_version and v!=expected_version:raise ValueError('Manifest format/version mismatch.')
        files=m.get('files')
        if not isinstance(files,dict) or not REQUIRED.issubset(files) or len(files)>250:raise ValueError('Incomplete update manifest.')
        actual={n[len('Tren-Local/'):] for n in names if not n.endswith('/') and n!='Tren-Local/update-manifest.json'}
        if set(files)!=actual:raise ValueError('Archive contents do not match manifest.')
        for name,digest in files.items():
            if not allowed(name) or not re.fullmatch(r'[a-f0-9]{64}',str(digest)):raise ValueError('Invalid manifest file.')
            if hashlib.sha256(z.read('Tren-Local/'+name)).hexdigest()!=digest:raise ValueError('File checksum mismatch: '+name)
        if json.loads(z.read('Tren-Local/version.json')).get('version')!=v:raise ValueError('version.json mismatch.')
        return m


def extract(path,destination,manifest):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for name in manifest['files']:
            out=destination/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read('Tren-Local/'+name))


def safe_target(root,name):
    root=Path(root).resolve();p=root/name
    if not allowed(name) or not p.resolve().is_relative_to(root) or any(x.is_symlink() for x in [p,*p.parents] if x!=root.parent):raise ValueError('Unsafe installation path: '+name)
    return p


def rollback(root,backup):
    root=Path(root).resolve();backup=Path(backup).resolve()
    if backup.parent!=root/'backups' or backup.is_symlink():raise ValueError('Invalid backup location.')
    m=json.loads((backup/'restore.json').read_text())
    for name in m['files']:
        p=safe_target(root,name)
        if name in m['existing']:
            old=backup/'code'/name
            if old.is_symlink() or not old.is_file():raise ValueError('Backup incomplete.')
            p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,p)
        elif p.is_file():p.unlink()


def install(root,source,manifest,data):
    root=Path(root).resolve();source=Path(source).resolve();data=Path(data).resolve()
    if not (root/'app.py').is_file() or not data.is_dir():raise ValueError('Existing TREN installation/data not found.')
    for name,digest in manifest['files'].items():
        p=source/name
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Staged file changed: '+name)
        safe_target(root,name)
    if (root/'backups').is_symlink():raise ValueError('Backup directory cannot be a link.')
    backup=root/'backups'/('pre-'+manifest['version']+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True)
    existing=[]
    for name in manifest['files']:
        p=safe_target(root,name)
        if p.exists():
            if not p.is_file():raise ValueError('Installation file is not regular: '+name)
            out=backup/'code'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out);existing.append(name)
    if (data/'assistant.sqlite').exists():
        with sqlite3.connect(data/'assistant.sqlite') as src,sqlite3.connect(backup/'assistant-snapshot.sqlite') as dst:src.backup(dst)
    (backup/'restore.json').write_text(json.dumps({'files':list(manifest['files']),'existing':existing}))
    try:
        for name in manifest['files']:
            p=safe_target(root,name);p.parent.mkdir(parents=True,exist_ok=True)
            temp=p.with_name(p.name+'.tren-new')
            if temp.is_symlink():raise ValueError('Temporary install path cannot be a link.')
            shutil.copyfile(source/name,temp);os.replace(temp,p)
    except Exception:
        rollback(root,backup);raise
    return backup


def detached_options():
    if os.name=='nt':return {'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS}
    return {'start_new_session':True}


def wait_parent(pid,timeout=90):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
        k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=k.OpenProcess(0x00100000,False,pid)
        if not handle:return
        try:
            if k.WaitForSingleObject(handle,int(timeout*1000))!=0:raise ValueError('TREN did not stop in time. Update not installed.')
        finally:k.CloseHandle(handle)
    else:
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:
                os.kill(pid,0)
                procstat=Path('/proc')/str(pid)/'stat'
                if procstat.exists() and procstat.read_text().split(') ',1)[1].startswith('Z'):
                    return
            except ProcessLookupError:return
            time.sleep(.2)
        raise ValueError('TREN did not stop in time. Update not installed.')


def status_write(data,**body):
    p=Path(data)/'updates'/'status.json';p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix('.tmp');t.write_text(json.dumps(body));os.replace(t,p)


def launch(root,data,port):
    env=os.environ.copy();env['TREN_DATA']=str(data);env['TREN_PORT']=str(port)
    log=open(Path(data)/'updates'/'restart.log','ab')
    try:return subprocess.Popen([sys.executable,str(Path(root)/'app.py'),'--no-browser'],cwd=root,env=env,stdout=log,stderr=log,stdin=subprocess.DEVNULL,**detached_options())
    finally:log.close()


def healthy(port,expected,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/')
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=2) as r:
                if r.status==200 and r.headers.get('Server','').split(' ',1)[0]=='TrenLocal/'+expected:return True
        except (OSError,urllib.error.URLError):pass
        time.sleep(.4)
    return False


def supervise(root,data,stage,port,pid,backup=None):
    restore=None;new=None;stopped=False
    try:
        wait_parent(pid)
        stopped=True
        if backup:
            rollback(root,backup);target=current_version(root)
        else:
            manifest=json.loads((Path(stage)/'manifest.json').read_text());target=manifest['version']
            restore=install(root,Path(stage)/'source',manifest,data)
        new=launch(root,data,port)
        if not healthy(port,target):raise ValueError('Updated TREN did not pass its startup check.')
        status_write(data,phase='complete',message=('Rollback complete.' if backup else 'Update complete.'),version=target,backup=str(restore or backup), pid=new.pid)
    except Exception as exc:
        if new and new.poll() is None:
            new.terminate()
            try:new.wait(timeout=10)
            except subprocess.TimeoutExpired:new.kill();new.wait()
        if restore:
            rollback(root,restore)
        if stopped:
            try:launch(root,data,port)
            except Exception:pass
        status_write(data,phase='failed',message=str(exc)+' Previous code restored when a backup was available; reopen TREN.',backup=str(restore or backup or ''))


class Manager:
    def __init__(self,root,data,get_setting,set_setting):
        self.root=Path(root);self.data=Path(data);self.get_setting=get_setting;self.set_setting=set_setting;self.lock=threading.RLock();self.latest=None;self.staged=None;self.busy=False
    def state(self):
        result={'version':current_version(self.root),'repository':self.get_setting('update_repository','alecjhalpin/Veyra'),'busy':self.busy,'latest':self.latest,'staged':None}
        if self.staged:result['staged']={'version':self.staged['version'],'source':self.staged['origin']}
        p=self.data/'updates/status.json'
        try:result['last_result']=json.loads(p.read_text())
        except (FileNotFoundError,ValueError):result['last_result']=None
        return result
    def check(self,repo):
        with self.lock:
            self.latest=release(repo);self.set_setting('update_repository',repo_name(repo));self.latest['available']=version(self.latest['version'])>version(current_version(self.root));return self.latest
    def stage(self,raw,origin,expected=None):
        with self.lock:
            if self.busy:raise ValueError('Update installation already started.')
            self.staged=None
            if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_ZIP:raise ValueError('Invalid update ZIP size.')
            folder=self.data/'updates'/('stage-'+str(time.time_ns()));folder.mkdir(parents=True)
            zip_path=folder/'update.zip';zip_path.write_bytes(raw)
            try:m=validate_archive(zip_path,expected)
            except zipfile.BadZipFile as exc:raise ValueError('The selected file is not a valid TREN ZIP.') from exc
            if version(m['version'])<=version(current_version(self.root)):raise ValueError('Update must be newer than the installed version. Use rollback for older versions.')
            extract(zip_path,folder/'source',m);(folder/'manifest.json').write_text(json.dumps(m))
            self.staged={'version':m['version'],'origin':origin,'folder':str(folder)};return self.state()
    def download(self):
        with self.lock:
            if not self.latest or not self.latest['available']:raise ValueError('Check for a newer release first.')
            a=self.latest;raw=fetch(a['url'],MAX_ZIP)
            if len(raw)!=a['size'] or hashlib.sha256(raw).hexdigest()!=a['sha256']:raise ValueError('Downloaded update does not match GitHub size/checksum.')
            return self.stage(raw,'GitHub release',a['version'])
    def begin(self,port,pid,backup=None):
        with self.lock:
            if self.busy:raise ValueError('Update already started.')
            if not backup and not self.staged:raise ValueError('Choose/download an update first.')
            if backup:
                b=Path(backup).resolve()
                if b.parent!=self.root.resolve()/'backups' or not (b/'restore.json').is_file():raise ValueError('Invalid backup.')
            else:b=None
            stage=Path(self.staged['folder']) if self.staged else self.data/'updates'
            stage.mkdir(parents=True,exist_ok=True)
            helper=stage/'trusted-updater.py';shutil.copyfile(Path(__file__),helper)
            args=[sys.executable,str(helper),'--supervise','--root',str(self.root),'--data',str(self.data),'--stage',str(stage),'--port',str(port),'--pid',str(pid)]
            if b:args+=['--backup',str(b)]
            subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**detached_options())
            self.busy=True;status_write(self.data,phase='restarting',message='Stopping TREN, backing up, installing and restarting.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--supervise',action='store_true');p.add_argument('--root');p.add_argument('--data');p.add_argument('--stage');p.add_argument('--port',type=int);p.add_argument('--pid',type=int);p.add_argument('--backup');a=p.parse_args()
    if a.supervise:supervise(a.root,a.data,a.stage,a.port,a.pid,a.backup)
