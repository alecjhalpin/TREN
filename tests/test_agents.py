import base64,datetime,json,sqlite3,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from agent_runtime import Engine,Budget,cron_matches,next_cron,DEFAULT_LIMITS
class Bridge:
 def stop_all(self):pass
 def close(self):pass
 def call(self,*args,**kwargs):return {'ok':True}
class AgentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.data=Path(self.tmp.name);self.mode='auto';self.calls=[]
  def db():
   c=sqlite3.connect(self.data/'test.sqlite',timeout=15);c.row_factory=sqlite3.Row;return c
  self.db=db
  self.response=lambda *args:{'text':'Verified fixture result','calls':[],'output':[],'usage':{'input_tokens':2,'output_tokens':3}}
  self.engine=Engine(db,self.data,lambda *a:self.response(*a),lambda:self.mode,bridge=Bridge())
 def tearDown(self):self.engine.close();self.tmp.cleanup()
 def wait(self,jid):
  end=time.time()+5
  while self.engine.job(jid)['status'] in ('queued','running','awaiting_approval','cancelling') and time.time()<end:time.sleep(.02)
  return self.engine.job(jid)
 def test_real_job_checkpoints_and_usage(self):
  jid=self.engine.submit('default','Inspect a fixture')
  job=self.wait(jid);self.assertEqual(job['status'],'completed');self.assertEqual(job['usage']['input_tokens'],2)
  self.assertNotIn('checkpoint',self.engine.state()['jobs'][0])
 def test_memory_isolation_pin_ranking_and_crud(self):
  self.engine.save_agent({'id':'other','project':'other','name':'Other'})
  first=self.engine.memory('default','save',{'content':'Pinned fact','pinned':True,'priority':1})
  self.engine.memory('default','save',{'content':'High priority','priority':10})
  self.engine.memory('other','save',{'content':'Other private fact','priority':10})
  result=self.engine.context_memory('default');self.assertTrue(result.startswith('- Pinned fact'));self.assertNotIn('Other private',result)
  with self.assertRaises(ValueError):self.engine.memory('other','update',{'id':first['id'],'content':'Overwrite'})
  self.engine.memory('default','delete',first);self.assertNotIn('Pinned fact',self.engine.context_memory('default'))
 def test_stop_all_pauses_and_cancels(self):
  gate=threading.Event();self.response=lambda *a:(gate.wait(2) or {'text':'Never execute','calls':[],'output':[]})
  jid=self.engine.submit('default','Wait');self.engine.stop_all();gate.set();self.assertEqual(self.wait(jid)['status'],'cancelled')
  with self.assertRaises(ValueError):self.engine.submit('default','Cannot start')
 def test_review_bound_approval_and_revocation(self):
  self.mode='review';count=[0]
  def respond(*args):
   count[0]+=1
   if count[0]==1:return {'text':'','output':[],'calls':[{'name':'pc_files','call_id':'one','arguments':json.dumps({'action':'write','path':str(self.data/'projects'/'default'/'hello.txt'),'destination':'','content':'actual file','pattern':'','limit':20})}]}
   return {'text':'done','output':[],'calls':[]}
  self.response=respond;jid=self.engine.submit('default','Create actual file')
  end=time.time()+3
  while jid not in self.engine.pending and time.time()<end:time.sleep(.02)
  item=self.engine.pending[jid];self.assertFalse((self.data/'projects'/'default'/'hello.txt').exists())
  with self.assertRaises(ValueError):self.engine.decide(jid,item['request_id'],'wrong',True)
  self.engine.decide(jid,item['request_id'],item['digest'],True)
  self.assertEqual(self.wait(jid)['status'],'completed');self.assertEqual((self.data/'projects'/'default'/'hello.txt').read_text(),'actual file')
 def test_inspect_never_mutates_and_auto_does(self):
  file=self.data/'projects'/'default'/'file.txt';count=[0]
  def respond(*args):
   count[0]+=1
   return {'text':'done','output':[],'calls':[] if count[0]>1 else [{'name':'pc_files','call_id':'one','arguments':json.dumps({'action':'write','path':str(file),'destination':'','content':'written','pattern':'','limit':10})}]}
  self.response=respond;self.mode='inspect';self.assertEqual(self.wait(self.engine.submit('default','write'))['status'],'denied');self.assertFalse(file.exists())
  self.mode='auto';count[0]=0;self.assertEqual(self.wait(self.engine.submit('default','write'))['status'],'completed');self.assertTrue(file.exists())
 def test_shared_budgets_and_depth(self):
  b=Budget({**DEFAULT_LIMITS,'calls':1,'agents':1});b.consume()
  with self.assertRaises(RuntimeError):b.consume()
  with self.assertRaises(RuntimeError):b.consume('agent')
 def test_cron_and_coalescing(self):
  when=datetime.datetime(2026,10,12,9,0);self.assertTrue(cron_matches('0 9 * * 1-5',when));self.assertFalse(cron_matches('0 9 * * 0',when))
  stamp=datetime.datetime(2026,10,12,9,1,tzinfo=datetime.timezone.utc).timestamp()
  self.assertEqual(next_cron('0 9 * * *',stamp,'UTC'),datetime.datetime(2026,10,13,9,tzinfo=datetime.timezone.utc).timestamp())
  w=self.engine.save_workflow({'name':'Once per minute','prompt':'report','cron':'* * * * *','enabled':True,'timezone':'UTC'})
  self.engine.tick(stamp+100000);self.engine.tick(stamp+100000)
  with self.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM agent_jobs').fetchone()[0],1)
 def test_restore_disables_schedules_and_keeps_profiles(self):
  self.engine.memory('default','save',{'content':'Keep me','pinned':True})
  self.engine.save_workflow({'name':'Scheduled','prompt':'report','cron':'* * * * *','enabled':True})
  exported=self.engine.backup();self.engine.restore(exported['backup'],True)
  self.assertIn('Keep me',self.engine.context_memory('default'));self.assertTrue(self.engine.state()['paused']);self.assertFalse(self.engine.state()['workflows'][0]['enabled'])
 def test_workspace_traversal_and_links(self):
  with self.assertRaises(ValueError):self.engine.preview('default','../../outside')
 def test_nested_cancel_stops_descendants_but_not_parent(self):
  gate=threading.Event()
  def response(*args):
   gate.wait(3)
   return {'text':'finished','calls':[],'output':[]}
  self.response=response
  self.engine.save_agent({'id':'child','project':'child','name':'Child'})
  self.engine.save_agent({'id':'grandchild','project':'grandchild','name':'Grandchild'})
  parent=self.engine.submit('default','Parent mission')
  child=self.engine.submit('child','Child mission',parent=parent)
  grandchild=self.engine.submit('grandchild','Grandchild mission',parent=child)
  self.engine.cancel(child)
  self.assertFalse(self.engine.active[parent]['cancel'].is_set())
  self.assertTrue(self.engine.active[child]['cancel'].is_set())
  self.assertTrue(self.engine.active[grandchild]['cancel'].is_set())
  gate.set()
  self.assertEqual(self.wait(child)['status'],'cancelled')
  self.assertEqual(self.wait(grandchild)['status'],'cancelled')
 def test_backup_restores_portable_settings_and_limits_without_secrets(self):
  with self.db() as c:
   c.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
   c.executemany('INSERT INTO settings VALUES(?,?)',[('assistant_name','Nova'),('chat_backend','chatgpt'),('pc_agent_mode','auto'),('private_token','must stay private')])
  limits={**DEFAULT_LIMITS,'concurrency':2};self.engine.set('limits',limits)
  exported=self.engine.backup();payload=json.loads(base64.b64decode(exported['backup']))
  self.assertNotIn('private_token',payload['preferences']);self.assertNotIn('pc_agent_mode',payload['preferences'])
  with self.db() as c:c.execute("UPDATE settings SET value='Changed' WHERE key='assistant_name'")
  self.engine.set('limits',{**DEFAULT_LIMITS,'concurrency':3})
  self.engine.restore(exported['backup'],True)
  self.assertEqual(self.engine.limits()['concurrency'],2)
  with self.db() as c:
   self.assertEqual(c.execute("SELECT value FROM settings WHERE key='assistant_name'").fetchone()[0],'Nova')
   self.assertEqual(c.execute("SELECT value FROM settings WHERE key='pc_agent_mode'").fetchone()[0],'review')
   self.assertEqual(c.execute("SELECT value FROM settings WHERE key='private_token'").fetchone()[0],'must stay private')
 def test_uncertain_mutation_is_not_replayed_from_checkpoint(self):
  path=self.data/'projects/default/once.txt';args={'action':'write','path':str(path),'destination':'','content':'once','pattern':'','limit':10}
  self.response=lambda *a:{'text':'','output':[],'calls':[{'name':'pc_files','call_id':'fixture','arguments':json.dumps(args)}]}
  original=self.engine.dispatch;executions=[]
  def interrupted_dispatch(*args):
   executions.append(1);original(*args);raise RuntimeError('Transport interrupted after write')
  self.engine.dispatch=interrupted_dispatch
  first=self.wait(self.engine.submit('default','Write once'))
  self.assertEqual(first['status'],'uncertain');self.assertEqual(path.read_text(),'once')
  second=self.wait(self.engine.submit('default','Write once',resume=first['id']))
  self.assertEqual(second['status'],'denied');self.assertEqual(len(executions),1);self.assertEqual(path.read_text(),'once')
