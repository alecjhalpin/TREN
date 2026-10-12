import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import update_runtime as u
import build_release

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=self.base/'installed';self.root.mkdir();self.data=self.root/'data';self.data.mkdir()
        (self.root/'app.py').write_text('previous code');(self.root/'version.json').write_text('{"version":"0.4.0"}')
        (self.root/'allowed-hosts.txt').write_text('private.example');(self.data/'pairing-code.txt').write_text('private-test')
        with sqlite3.connect(self.data/'assistant.sqlite') as c:c.execute('CREATE TABLE memories(content)');c.execute("INSERT INTO memories VALUES('keep me')")
        self.before=(self.data/'assistant.sqlite').read_bytes();self.source=self.base/'source';self.source.mkdir()
        for n in u.REQUIRED:(self.source/n).write_text('{"version":"0.5.0"}' if n=='version.json' else 'new '+n)
        self.zip=self.base/'update.zip';self.manifest=build_release.build(self.source,self.zip)
        settings={};self.manager=u.Manager(self.root,self.data,lambda k,d='':settings.get(k,d),lambda k,v:settings.update({k:v}))
    def tearDown(self):self.temp.cleanup()
    def test_manifest_and_staging(self):
        self.assertEqual(u.validate_archive(self.zip)['version'],'0.5.0');self.manager.stage(self.zip.read_bytes(),'ZIP')
        self.assertEqual(self.manager.state()['staged']['version'],'0.5.0')
        self.assertEqual((self.data/'assistant.sqlite').read_bytes(),self.before)
    def test_traversal_links_unlisted_and_duplicates_rejected(self):
        for name in ('Tren-Local/../evil.py','Tren-Local/data/pairing-code.txt','Tren-Local/.env','C:/evil.py','Tren-Local/evil.py'):
            bad=self.base/'bad.zip'
            with zipfile.ZipFile(bad,'w') as z:z.writestr(name,'bad')
            with self.assertRaises(ValueError):u.validate_archive(bad)
        with zipfile.ZipFile(self.zip,'a') as z:z.writestr('Tren-Local/app.py','duplicate')
        with self.assertRaises(ValueError):u.validate_archive(self.zip)
    def test_checksum_and_version_mismatch(self):
        with self.assertRaises(ValueError):u.validate_archive(self.zip,'0.6.0')
        m=dict(self.manifest);m['files']=dict(m['files']);m['files']['app.py']='0'*64
        bad=self.base/'bad.zip'
        with zipfile.ZipFile(self.zip) as src,zipfile.ZipFile(bad,'w') as z:
            for n in src.namelist():z.writestr(n,json.dumps(m) if n.endswith('update-manifest.json') else src.read(n))
        with self.assertRaises(ValueError):u.validate_archive(bad)
    def test_install_rollback_preserves_database_pairing_hosts(self):
        b=u.install(self.root,self.source,self.manifest,self.data)
        self.assertEqual((self.root/'app.py').read_text(),'new app.py')
        self.assertEqual((self.data/'assistant.sqlite').read_bytes(),self.before)
        self.assertEqual((self.data/'pairing-code.txt').read_text(),'private-test')
        self.assertEqual((self.root/'allowed-hosts.txt').read_text(),'private.example')
        u.rollback(self.root,b);self.assertEqual((self.root/'app.py').read_text(),'previous code')
        self.assertFalse((self.root/'update_runtime.py').exists());self.assertEqual((self.data/'assistant.sqlite').read_bytes(),self.before)
    def test_transaction_failure_restores_old_code(self):
        original=u.os.replace;count=[0]
        def fail(a,b):
            count[0]+=1
            if count[0]==2:raise OSError('simulated disk failure')
            return original(a,b)
        with patch.object(u.os,'replace',side_effect=fail):
            with self.assertRaises(OSError):u.install(self.root,self.source,self.manifest,self.data)
        self.assertEqual((self.root/'app.py').read_text(),'previous code');self.assertEqual((self.data/'assistant.sqlite').read_bytes(),self.before)
    def test_repo_urls_and_release_digest(self):
        for repo in ('../bad','owner/repo/extra','https://github.com/o/r','o/..'):
            with self.assertRaises(ValueError):u.repo_name(repo)
        for url in ('http://github.com/o/r','https://evil.test/u','https://github.com@evil.test/u','https://github.com:8080/u'):
            with self.assertRaises(ValueError):u.checked_url(url)
        raw=self.zip.read_bytes();asset={'name':'TREN-v0.5.0.zip','size':len(raw),'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'browser_download_url':'https://github.com/owner/repo/releases/download/v0.5.0/TREN-v0.5.0.zip'}
        r={'tag_name':'v0.5.0','assets':[asset],'draft':False,'prerelease':False}
        with patch.object(u,'fetch',return_value=json.dumps(r).encode()):self.manager.check('owner/repo')
        with patch.object(u,'fetch',return_value=raw):self.manager.download()
        with patch.object(u,'fetch',return_value=b'wrong'):
            with self.assertRaises(ValueError):self.manager.download()
        del asset['digest']
        with patch.object(u,'fetch',return_value=json.dumps(r).encode()):
            with self.assertRaises(ValueError):u.release('owner/repo')
    def test_same_or_older_version_rejected(self):
        (self.root/'version.json').write_text('{"version":"0.5.0"}')
        with self.assertRaises(ValueError):self.manager.stage(self.zip.read_bytes(),'ZIP')
    def test_staged_tamper_and_target_symlink(self):
        (self.source/'app.py').write_text('tampered')
        with self.assertRaises(ValueError):u.install(self.root,self.source,self.manifest,self.data)
        import os
        if os.name=='nt':return
        (self.root/'app.py').unlink();(self.root/'app.py').symlink_to(self.base/'elsewhere')
        with self.assertRaises(ValueError):u.safe_target(self.root,'app.py')
    def test_supervisor_failed_health_rolls_back_and_relaunches(self):
        stage=self.base/'stage';stage.mkdir();(stage/'manifest.json').write_text(json.dumps(self.manifest))
        import shutil;shutil.copytree(self.source,stage/'source')
        fake=type('Proc',(),{'poll':lambda self:0,'pid':9999})()
        with patch.object(u,'wait_parent'),patch.object(u,'launch',return_value=fake) as launch,patch.object(u,'healthy',return_value=False):
            u.supervise(self.root,self.data,stage,8765,123)
        self.assertEqual((self.root/'app.py').read_text(),'previous code');self.assertEqual(launch.call_count,2)
        self.assertEqual(json.loads((self.data/'updates/status.json').read_text())['phase'],'failed')
    def test_restart_helper_is_current_trusted_copy(self):
        self.manager.stage(self.zip.read_bytes(),'ZIP')
        with patch.object(u.subprocess,'Popen') as process:self.manager.begin(8765,123)
        args=process.call_args.args[0];self.assertEqual(Path(args[1]).read_bytes(),Path(u.__file__).read_bytes());self.assertTrue(self.manager.busy)
