"""Real elevated worker execution on an already-elevated disposable Windows runner.

This verifies authenticated execution, install/dependencies and revocation. It does
not substitute for the user's one-time interactive UAC setup acceptance.
"""
import ctypes,json,os,secrets,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from admin_broker import Broker,ps_literal
from providers import protected_bytes
import codex_tasks as ct

@unittest.skipUnless(os.name=='nt' and os.getenv('VEYRA_ADMIN_ACCEPTANCE')=='1','Windows admin acceptance is opt-in')
class AdminAcceptance(unittest.TestCase):
 def test_install_small_program_dependencies_and_disable(self):
  self.assertTrue(ctypes.windll.shell32.IsUserAnAdmin(),'Acceptance runner must already be elevated')
  with tempfile.TemporaryDirectory() as directory:
   data=Path(directory);broker=Broker(data);broker.directory.mkdir()
   (broker.directory/'key.dpapi').write_bytes(protected_bytes(secrets.token_bytes(32)))
   (broker.directory/'enabled').touch()
   worker=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'admin_broker.py'),'--worker',directory],**ct.process_options())
   try:
    deadline=time.time()+15
    while not broker.status()['enabled'] and time.time()<deadline:time.sleep(.1)
    self.assertTrue(broker.status()['enabled'])
    node=os.getenv('TREN_NODE') or shutil.which('node');npm=os.getenv('VEYRA_NPM_CLI')
    self.assertTrue(node and npm,'Bundled Node/npm paths must be supplied')
    install=data/'program';target=data/'disposable';target.mkdir();(target/'test.txt').write_text('owned fixture')
    script=("$ErrorActionPreference='Stop'; & "+ps_literal(node)+' '+ps_literal(npm)+' install --prefix '+ps_literal(install)+" rimraf@6.0.1 --ignore-scripts --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'Program installation failed' }; & "+ps_literal(node)+' '+ps_literal(install/'node_modules/rimraf/dist/esm/bin.mjs')+' '+ps_literal(target)+"; if ($LASTEXITCODE -ne 0) { throw 'Installed program failed' }; Write-Output 'INSTALL_AND_EXECUTION_VERIFIED'")
    args={'script':script,'cwd':directory,'timeout_seconds':180,'purpose':'Install pinned rimraf CLI and dependencies inside an isolated acceptance workspace and run it against an owned fixture.','elevated':True}
    result=broker.run(args);self.assertEqual(result.get('exit_code'),0,result)
    self.assertTrue((install/'node_modules/rimraf/package.json').is_file());self.assertTrue((install/'node_modules/glob/package.json').is_file());self.assertFalse(target.exists())
    (broker.directory/'enabled').unlink();(broker.directory/'disabled').touch();worker.wait(timeout=15)
    self.assertFalse(broker.status()['enabled'])
    with self.assertRaises(PermissionError):broker.run(args)
    print('Verified elevated worker program/dependency installation, execution and revocation. Interactive UAC setup remains separate.')
   finally:
    (broker.directory/'enabled').unlink(missing_ok=True);(broker.directory/'disabled').touch()
    if worker.poll() is None:worker.terminate();worker.wait(timeout=10)
