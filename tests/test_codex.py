import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_tasks as ct


class CodexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        def db():
            c = sqlite3.connect(self.root/'test.sqlite')
            c.row_factory = sqlite3.Row
            return c
        self.db = db
        self.m = ct.Manager(db, self.root, lambda: False)
        self.fake = self.root/'fake.py'
        self.fake.write_text('''import sys,json,time
from pathlib import Path
prompt=sys.stdin.read()
print(json.dumps({'type':'turn.started'}),flush=True)
if 'SLEEP' in prompt: time.sleep(20)
if 'FAIL' in prompt:
 print('usage limit reached',file=sys.stderr);sys.exit(2)
if 'EVENTFAIL' in prompt:
 print(json.dumps({'type':'turn.failed','error':{'message':'auth failed'}}),flush=True);sys.exit(0)
if 'CREATE' in prompt: Path('calculator.py').write_text('print(2+2)')
if 'EDIT' in prompt: Path('calculator.py').write_text('print(3+4)')
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Finished'}}),flush=True)
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10}}),flush=True)
''')
        self.health = patch.object(ct, 'health', return_value={'authenticated': True})
        self.cli = patch.object(ct, 'cli_command', return_value=[sys.executable, str(self.fake)])
        self.health.start(); self.cli.start()

    def tearDown(self):
        self.m.close();self.health.stop();self.cli.stop();self.tmp.cleanup()

    def submit(self, prompt='CREATE', **kwargs):
        return self.m.submit(dict(prompt=prompt,project='demo',mode='workspace-write',confirmed=True,**kwargs))

    def run_job(self, jid):
        job=next(j for j in self.m.jobs() if j['id']==jid)
        self.m.active[jid]=threading.Event()
        self.m.execute(job)
        return next(j for j in self.m.jobs() if j['id']==jid)

    def test_completion_real_subprocess_and_verified_file(self):
        job=self.run_job(self.submit(expected=['calculator.py']))
        self.assertEqual(job['status'],'completed');self.assertEqual(job['exit_code'],0)
        self.assertIn('calculator.py',json.loads(job['artifacts']));self.assertIn('Finished',job['output'])

    def test_failure_and_zero_exit_error_event(self):
        for prompt in ('FAIL','EVENTFAIL'):
            self.assertEqual(self.run_job(self.submit(prompt))['status'],'failed')

    def test_missing_artifact(self):
        self.assertEqual(self.run_job(self.submit('NONE',expected=['missing.py']))['status'],'artifact_missing')

    def test_timeout(self):
        real=ct.time.monotonic
        with patch.object(ct.time,'monotonic',side_effect=[real(),real()+100]):
            self.assertEqual(self.run_job(self.submit('SLEEP',timeout=10))['status'],'timed_out')

    def test_running_cancel(self):
        jid=self.submit('SLEEP');self.m.start()
        end=time.monotonic()+5
        while jid not in self.m.active and time.monotonic()<end: time.sleep(.02)
        self.assertIn(jid,self.m.active)
        self.m.cancel(jid)
        # stop_process allows up to ten seconds to reap a process on a busy runner.
        end=time.monotonic()+15
        while self.m.jobs()[0]['status']!='cancelled' and time.monotonic()<end: time.sleep(.02)
        self.assertEqual(self.m.jobs()[0]['status'],'cancelled')

    def test_queue_cancel_and_recovery(self):
        jid=self.submit();self.m.cancel(jid);self.assertEqual(self.m.jobs()[0]['status'],'cancelled')
        self.submit();ct.Manager(self.db,self.root,lambda:False)
        self.assertEqual(self.m.jobs()[0]['status'],'interrupted')

    def test_invalid_directories_files_and_confirmation(self):
        for name in ('../bad','C:\\Windows','a/b','.'):
            with self.assertRaises(ValueError):self.m.submit({'prompt':'x','project':name})
        for file in ('../bad','/etc/passwd','.env','dir/../../bad','C:/file'):
            with self.assertRaises(ValueError):self.submit(expected=[file])
        with self.assertRaises(ValueError):self.m.submit({'prompt':'x','project':'demo','mode':'workspace-write'})

    def test_symlink_and_redaction(self):
        self.m.project('demo',True)
        if os.name!='nt':
            (self.root/'projects'/'demo'/'escape').symlink_to(self.root,target_is_directory=True)
            with self.assertRaises(ValueError):self.m.file('demo','escape/fake.py')
        self.assertNotIn('sk-abcdefghijk',ct.redact('Bearer secret-token sk-abcdefghijk access_token=abc'))
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private','CODEX_API_KEY':'private'}):
            self.assertNotIn('OPENAI_API_KEY',ct.child_env())

    def test_auth_failure_no_process(self):
        with patch.object(ct,'health',return_value={'authenticated':False}),patch.object(ct.subprocess,'Popen') as popen:
            self.assertEqual(self.run_job(self.submit())['status'],'failed');popen.assert_not_called()

    def test_health_missing_timeout_and_wrong_auth(self):
        self.cli.stop();self.health.stop()
        with patch.object(ct.shutil,'which',return_value=None): self.assertFalse(ct.health()['detected'])
        with patch.object(ct,'cli_command',return_value=['codex']),patch.object(ct.subprocess,'run') as run:
            run.return_value=type('Result',(),dict(returncode=0,stdout='Logged in using ChatGPT',stderr=''))()
            self.assertTrue(ct.health()['authenticated'])
            run.return_value.stdout='Logged in using an API key';self.assertFalse(ct.health()['authenticated'])
            run.side_effect=ct.subprocess.TimeoutExpired('codex',15);self.assertFalse(ct.health()['authenticated'])
        self.health.start();self.cli.start()

    def test_windows_npm_detection_uses_node_not_shell(self):
        self.cli.stop()
        base=self.root/'npm';script=base/'node_modules/@openai/codex/bin/codex.js';script.parent.mkdir(parents=True);script.touch()
        def which(name): return str(base/'codex.cmd') if name=='codex' else ('node.exe' if name=='node.exe' else None)
        with patch.object(ct.shutil,'which',side_effect=which):self.assertEqual(ct.cli_command(),['node.exe',str(script)])
        self.cli.start()

    def test_gaming_holds_queue(self):
        self.m.gaming=lambda:True;self.submit();self.m.start();time.sleep(.6)
        self.assertEqual(self.m.jobs()[0]['status'],'queued')

    def test_followup_edit_and_execution(self):
        import subprocess
        self.assertEqual(self.run_job(self.submit('CREATE',expected=['calculator.py']))['status'],'completed')
        second=self.run_job(self.submit('EDIT',expected=['calculator.py']))
        self.assertEqual(second['status'],'completed')
        file=self.m.file('demo','calculator.py')
        self.assertEqual(subprocess.check_output([sys.executable,str(file)],text=True).strip(),'7')
        self.assertIn('calculator.py',json.loads(second['artifacts']))

    def test_restart_marks_active_states_interrupted(self):
        for status in ('queued','running','cancelling'):
            jid=self.submit('NONE');self.m.update(jid,status=status)
        ct.Manager(self.db,self.root,lambda:False)
        self.assertTrue(all(j['status']=='interrupted' for j in self.m.jobs()))
