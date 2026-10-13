"""Explicitly provisioned per-user elevated worker. Never disables UAC or uses SYSTEM.

The user approves installation through normal UAC. Authenticated finite requests run in
that user's elevated interactive logon session; no arbitrary network listener is created.
"""
import base64,ctypes,hashlib,hmac,json,os,secrets,subprocess,sys,threading,time
from pathlib import Path
import codex_tasks as ct
from providers import protected_bytes

TASK_NAME='VEYRA Elevated Worker'

def ps_literal(value):return "'"+str(value).replace("'","''")+"'"
def sign(key,payload):return hmac.new(key,json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
def write_atomic(path,value):
    temp=path.with_suffix('.new');temp.write_text(json.dumps(value),encoding='utf-8');os.replace(temp,path)

class Broker:
    def __init__(self,data):self.data=Path(data).resolve();self.directory=self.data/'admin_broker';self.lock=threading.RLock()
    def key(self):return protected_bytes((self.directory/'key.dpapi').read_bytes(),True)
    def status(self):
        enabled=(self.directory/'enabled').exists();alive=False
        try:
            value=json.loads((self.directory/'heartbeat.json').read_text());alive=time.time()-value['time']<8
        except (OSError,ValueError,KeyError):pass
        return {'enabled':enabled and alive,'configured':(self.directory/'key.dpapi').exists(),'running':alive,'windows':os.name=='nt','task':TASK_NAME}
    def enable(self,confirmed=False):
        if not confirmed:raise ValueError('Confirm unattended administrator access. This permits enabled autonomous agents to modify system-wide files, install programs and change Windows configuration without another VEYRA approval for each action.')
        if os.name!='nt':raise ValueError('Elevated background access requires a Windows administrator account.')
        if self.status()['running']:self.disable()
        self.directory.mkdir(parents=True,exist_ok=True)
        if not (self.directory/'key.dpapi').exists():(self.directory/'key.dpapi').write_bytes(protected_bytes(secrets.token_bytes(32)))
        (self.directory/'disabled').unlink(missing_ok=True);(self.directory/'enabled').touch()
        user=subprocess.run(['whoami.exe'],capture_output=True,text=True,timeout=5,**ct.process_options()).stdout.strip()
        worker_executable=Path(sys.executable).with_name('pythonw.exe')
        if not worker_executable.is_file():raise RuntimeError('Windowless Python is unavailable. Use the bundled Windows desktop runtime.')
        action_args=subprocess.list2cmdline([str(Path(__file__).resolve()),'--worker',str(self.data)])
        script=("$ErrorActionPreference='Stop'; $a=New-ScheduledTaskAction -Execute "+ps_literal(str(worker_executable))+" -Argument "+ps_literal(action_args)+"; $p=New-ScheduledTaskPrincipal -UserId "+ps_literal(user)+" -LogonType Interactive -RunLevel Highest; $t=New-ScheduledTaskTrigger -AtLogOn -User "+ps_literal(user)+"; $s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable; Register-ScheduledTask -TaskName "+ps_literal(TASK_NAME)+" -Action $a -Principal $p -Trigger $t -Settings $s -Force | Out-Null; Start-ScheduledTask -TaskName "+ps_literal(TASK_NAME))
        try:
            result=ct.pc_elevated({'script':script,'cwd':'','timeout_seconds':60,'purpose':'Install the explicitly enabled VEYRA elevated worker for this Windows user.','elevated':True},self.data,lambda:False)
            if result.get('ok') is False or result.get('exit_code',0)!=0:raise RuntimeError('Elevated worker setup did not complete: '+str(result)[:1000])
            end=time.monotonic()+20
            while time.monotonic()<end:
                if self.status()['enabled']:return {'ok':True,**self.status()}
                time.sleep(.2)
            raise RuntimeError('The worker did not report readiness. It requires the same administrator Windows account that owns VEYRA; check Task Scheduler.')
        except Exception:
            self.disable();raise
    def disable(self):
        self.directory.mkdir(parents=True,exist_ok=True);(self.directory/'enabled').unlink(missing_ok=True);(self.directory/'disabled').touch();self.cancel_all()
        if os.name=='nt':
            end=time.monotonic()+12
            while (self.directory/'heartbeat.json').exists() and time.monotonic()<end:time.sleep(.1)
            subprocess.run(['schtasks.exe','/End','/TN',TASK_NAME],capture_output=True,timeout=10,**ct.process_options())
        return {'ok':True,'enabled':False}
    def cancel_all(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        (self.directory/'cancel_all').write_text(str(time.time()))
        for path in self.directory.glob('*.request.json'):(self.directory/(path.name.split('.')[0]+'.cancel')).touch()
    def run(self,args,cancelled=lambda:False):
        ct.pc_validate('pc_command',args)
        if not self.status()['enabled']:raise PermissionError('The elevated worker is not enabled and ready.')
        with self.lock:
            if cancelled():raise InterruptedError('Elevated action cancelled before dispatch.')
            if not self.status()['enabled']:raise PermissionError('Elevated access was revoked.')
            key=self.key();rid=secrets.token_hex(16);payload={'id':rid,'args':{**args,'elevated':False},'created':time.time(),'expires':time.time()+min(600,args['timeout_seconds'])+30,'parent_pid':os.getpid(),'parent_identity':ct.pc_process_identity(os.getpid())}
            request=self.directory/(rid+'.request.json');response=self.directory/(rid+'.response.json');write_atomic(request,{'payload':payload,'signature':sign(key,payload)})
            end=time.monotonic()+args['timeout_seconds']+35
            try:
                while time.monotonic()<end:
                    if cancelled() or not (self.directory/'enabled').exists():(self.directory/(rid+'.cancel')).touch();raise InterruptedError('Elevated action cancelled; inspect completed effects.')
                    if response.exists():
                        packet=json.loads(response.read_text());value=packet['payload']
                        if value.get('id')!=rid or not hmac.compare_digest(sign(key,value),packet.get('signature','')):raise RuntimeError('Elevated result authentication failed.')
                        return value['result']
                    time.sleep(.1)
                (self.directory/(rid+'.cancel')).touch();return {'ok':False,'may_still_be_running':True,'error':'Elevated result was not confirmed. Inspect state before retrying.'}
            finally:
                request.unlink(missing_ok=True);response.unlink(missing_ok=True)

def worker(data):
    if os.name!='nt' or not ctypes.windll.shell32.IsUserAnAdmin():raise RuntimeError('Worker must run elevated under the explicitly authorized user.')
    broker=Broker(data);directory=broker.directory;key=broker.key();seen=set()
    def heartbeat():
        while (directory/'enabled').exists() and not (directory/'disabled').exists():
            write_atomic(directory/'heartbeat.json',{'time':time.time(),'pid':os.getpid(),'protocol':1});time.sleep(1)
    threading.Thread(target=heartbeat,daemon=True).start()
    while (directory/'enabled').exists() and not (directory/'disabled').exists():
        for path in directory.glob('*.request.json'):
            rid=path.name.split('.')[0]
            if rid in seen:continue
            seen.add(rid)
            try:
                packet=json.loads(path.read_text());payload=packet['payload']
                if not hmac.compare_digest(sign(key,payload),packet.get('signature','')) or payload.get('id')!=rid:continue
                if not payload.get('created',0)<=time.time()<=payload.get('expires',0):continue
                ct.pc_validate('pc_command',payload['args']);cancel=directory/(rid+'.cancel')
                cancelled=lambda:cancel.exists() or not (directory/'enabled').exists() or (directory/'disabled').exists() or time.time()>payload['expires']
                if ct.pc_process_identity(payload.get('parent_pid',0))!=payload.get('parent_identity') or payload.get('parent_identity') is None:continue
                result={'ok':False,'cancelled':True} if cancelled() else ct.pc_run_command(payload['args'],lambda:cancelled() or ct.pc_process_identity(payload['parent_pid'])!=payload['parent_identity'])
                value={'id':rid,'result':result};write_atomic(directory/(rid+'.response.json'),{'payload':value,'signature':sign(key,value)})
            except Exception as error:
                value={'id':rid,'result':{'ok':False,'error':ct.redact(str(error))}};write_atomic(directory/(rid+'.response.json'),{'payload':value,'signature':sign(key,value)})
        if len(seen)>10000:seen={p.name.split('.')[0] for p in directory.glob('*.request.json')}
        time.sleep(.1)
    (directory/'heartbeat.json').unlink(missing_ok=True)

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--worker':worker(sys.argv[2])
    else:raise SystemExit('Use VEYRA Settings to explicitly enable the elevated worker.')
