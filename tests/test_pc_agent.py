"""PC agent tests use temp files, fake GPT and harmless subprocess fixtures.
Windows PowerShell/UAC and live plan-sharing tools are not certified here.
"""
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import codex_tasks as pc


def file_args(path,action='read',**kwargs):
    return {'action':action,'path':str(path),'destination':'','content':'','pattern':'','limit':100,**kwargs}


def call(name,args,cid='call-1'):
    item={'type':'function_call','name':name,'namespace':'tren','call_id':cid,'arguments':json.dumps(args)}
    return {'text':'','calls':[item],'output':[{'type':'reasoning','id':'reasoning-id','encrypted_content':'synthetic'},item]}


FINAL={'text':'Verified task result','calls':[],'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Verified task result'}]}]}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data=self.root/'data';self.data.mkdir();self.files=self.root/'files';self.files.mkdir()
        self.managers=[]
    def db(self):
        c=sqlite3.connect(self.data/'test.sqlite',timeout=10);c.row_factory=sqlite3.Row;return c
    def tearDown(self):
        for m in self.managers:m.close()
        self.temp.cleanup()
    def manager(self,response,mode=lambda:'review'):
        m=pc.PCManager(self.db,self.data,response,lambda p:([{'role':'user','content':p}],'context'),lambda *_:{'results':[]},mode)
        self.managers.append(m);return m
    def wait(self,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            value=predicate()
            if value:return value
            time.sleep(.01)
        self.fail('Timed out waiting for fixture task.')
    def finished(self,m):
        return self.wait(lambda:m.jobs()[0] if not m.active else None)

    def test_real_storage_and_namespaced_read_loop(self):
        requests=[]
        def model(messages,instructions,tools):
            requests.append(json.loads(json.dumps(messages)))
            self.assertEqual(tools[0]['type'],'namespace')
            return call('pc_info',{'section':'storage'}) if len(requests)==1 else FINAL
        m=self.manager(model);m.submit('How much storage is left?');job=self.finished(m)
        self.assertEqual(job['status'],'completed');self.assertIsNone(job['approval'])
        evidence=json.loads(requests[1][-1]['output'])
        self.assertTrue(evidence['ok']);self.assertGreater(evidence['drives'][0]['total_bytes'],0)
        self.assertEqual(requests[1][-1]['call_id'],'call-1')
        self.assertEqual(requests[1][-3]['type'],'reasoning')

    def test_mutation_requires_current_exact_approval_and_backup(self):
        path=self.files/'note.txt';path.write_text('original')
        turns=[call('pc_files',file_args(path,'write',content='updated')),FINAL]
        m=self.manager(lambda *_:turns.pop(0));jid=m.submit('Update this file')
        pending=self.wait(lambda:m.pending)
        self.assertEqual(path.read_text(),'original')
        with self.assertRaises(ValueError):m.decide(jid,pending['request_id'],'wrong',True)
        self.assertEqual(path.read_text(),'original')
        m.decide(jid,pending['request_id'],pending['digest'],True)
        with self.assertRaises(ValueError):m.decide(jid,pending['request_id'],pending['digest'],True)
        job=self.finished(m);self.assertEqual(job['status'],'completed');self.assertEqual(path.read_text(),'updated')
        result=json.loads(job['steps'][0]['result'])
        self.assertEqual((Path(result['backup'])/'original').read_text(),'original')

    def test_denial_and_cancellation_never_execute(self):
        for cancel in (False,True):
            path=self.files/('cancel.txt' if cancel else 'deny.txt')
            m=self.manager(lambda *_:call('pc_files',file_args(path,'write',content='never')))
            jid=m.submit('Propose a write');pending=self.wait(lambda:m.pending)
            if cancel:m.cancel(jid)
            else:m.decide(jid,pending['request_id'],pending['digest'],False)
            job=self.finished(m)
            self.assertEqual(job['status'],'cancelled' if cancel else 'denied');self.assertFalse(path.exists())

    def test_read_only_mode_blocks_commands_without_permission_prompt(self):
        turns=[call('pc_command',{'script':'Write-Output test','cwd':'','purpose':'test','timeout_seconds':5,'elevated':False}),FINAL]
        m=self.manager(lambda *_:turns.pop(0),lambda:'inspect')
        with patch.object(m.tools,'run',side_effect=AssertionError('No execution')):
            m.submit('Read only');job=self.finished(m)
        self.assertIsNone(job['approval']);self.assertEqual(job['steps'][0]['status'],'failed')
        self.assertEqual(job['status'],'finished_with_errors')
        self.assertIn('permissions',job['steps'][0]['result'])

    def test_restart_interrupts_no_replay_and_rejects_stale_approval(self):
        m=self.manager(lambda *_:FINAL)
        with self.db() as c:c.execute('INSERT INTO pc_jobs VALUES(?,?,?,?,?,?,NULL)',('old','old task','awaiting_approval','','[]',time.time()))
        new=self.manager(lambda *_:self.fail('No replay'))
        self.assertEqual(new.jobs()[0]['status'],'interrupted')
        with self.assertRaises(ValueError):new.decide('old','old-request','old-digest',True)

    def test_duplicate_call_id_stops_replay(self):
        m=self.manager(lambda *_:call('pc_info',{'section':'storage'}))
        with patch.object(m.tools,'run',return_value={'ok':True}) as execute:
            m.submit('test');job=self.finished(m)
            self.assertEqual(execute.call_count,1)
        self.assertEqual(job['status'],'failed');self.assertIn('Repeated tool call',job['result'])

    def test_partial_failure_retains_action_record_and_no_fallback(self):
        count=0
        def response(*_):
            nonlocal count
            count+=1
            if count==1:return call('pc_files',file_args(self.files/'created.txt','write',content='created'))
            raise RuntimeError('Provider became unavailable')
        m=self.manager(response);jid=m.submit('write');pending=self.wait(lambda:m.pending)
        m.decide(jid,pending['request_id'],pending['digest'],True)
        job=self.finished(m)
        self.assertEqual(job['status'],'failed');self.assertEqual(job['steps'][0]['status'],'done')
        self.assertEqual((self.files/'created.txt').read_text(),'created')

    def test_files_read_search_write_copy_move_delete_and_protected_paths(self):
        tools=pc.PCTools(self.data,lambda *_:{})
        original=self.files/'a.txt';original.write_text('hello')
        self.assertEqual(tools.run('pc_files',file_args(original))['text'],'hello')
        listing=tools.run('pc_files',file_args(self.files,'search',pattern='*.txt'))
        self.assertEqual(len(listing['entries']),1)
        copy=self.files/'copy.txt';tools.run('pc_files',file_args(original,'copy',destination=str(copy)))
        moved=self.files/'moved.txt';tools.run('pc_files',file_args(copy,'move',destination=str(moved)))
        self.assertFalse(copy.exists());self.assertEqual(moved.read_text(),'hello')
        result=tools.run('pc_files',file_args(moved,'delete'))
        self.assertFalse(moved.exists());self.assertEqual((Path(result['backup'])/'original').read_text(),'hello')
        secret=self.data/'pairing-code.txt';secret.write_text('protected')
        with self.assertRaises(ValueError):tools.run('pc_files',file_args(secret))
        link=self.files/'linked.txt'
        try:link.symlink_to(secret)
        except OSError:pass
        else:
            with self.assertRaises(ValueError):tools.run('pc_files',file_args(link))
        with self.assertRaises(ValueError):tools.run('pc_files',file_args(self.files,'delete'))
        with self.assertRaises(ValueError):pc.pc_path('../relative')

    def test_command_runner_real_harmless_subprocess_exit_timeout_and_cancel(self):
        args={'script':'fixture','cwd':str(self.files),'purpose':'fixture','timeout_seconds':2,'elevated':False}
        argv=[sys.executable,'-c',"import sys;sys.stdin.read();print('fixture output');sys.exit(3)"]
        result=pc.pc_run_command(args,lambda:False,argv)
        self.assertFalse(result['ok']);self.assertEqual(result['exit_code'],3)
        self.assertIn('fixture output',result['stdout'])
        sleepy=[sys.executable,'-c','import sys,time;sys.stdin.read();time.sleep(10)']
        result=pc.pc_run_command({**args,'timeout_seconds':1},lambda:False,sleepy)
        self.assertEqual(result['status'],'timeout')
        event=threading.Event();timer=threading.Timer(.1,event.set);timer.start()
        result=pc.pc_run_command(args,event.is_set,sleepy);timer.join()
        self.assertTrue(result['cancelled'])

    def test_elevation_verified_result_and_payload_tampering(self):
        args={'script':'Write-Output fixture','cwd':str(self.files),'purpose':'fixture','timeout_seconds':5,'elevated':True}
        def launch(argv,cwd):
            pc.pc_admin_main(*argv[2:]);return 71
        with patch.object(pc,'pc_process_identity',return_value=123),patch.object(pc,'pc_shell_elevate',side_effect=launch),patch.object(pc,'pc_wait_handle',return_value=0),patch.object(pc,'pc_close_handle') as close,patch.object(pc,'pc_run_command',return_value={'ok':True,'stdout':'verified'}):
            result=pc.pc_elevated(args,self.data,lambda:False)
            self.assertTrue(result['ok']);close.assert_called_once_with(71)
        payload=base64.urlsafe_b64encode(json.dumps({'args':args,'parent_pid':1,'parent_identity':2}).encode()).decode()
        with self.assertRaises(ValueError):pc.pc_admin_main(payload,'wrong',str(self.files),'00'*32)
        def forged(argv,cwd):
            (Path(argv[4])/'result.json').write_text(json.dumps({'result':{'ok':True},'signature':'forged'}))
            return 72
        with patch.object(pc,'pc_process_identity',return_value=123),patch.object(pc,'pc_shell_elevate',side_effect=forged),patch.object(pc,'pc_wait_handle',return_value=0),patch.object(pc,'pc_close_handle'):
            with self.assertRaises(RuntimeError):pc.pc_elevated(args,self.data,lambda:False)


if __name__=='__main__':unittest.main()
