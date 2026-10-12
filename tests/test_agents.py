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
  while self.engine.job(jid)['status'] in ('queued','running','awaiting_approval','waiting_children','cancelling') and time.time()<end:time.sleep(.02)
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
  parent_cancel=self.engine.active[parent]['cancel'];child_cancel=self.engine.active[child]['cancel'];grandchild_cancel=self.engine.active[grandchild]['cancel']
  self.engine.cancel(child)
  self.assertFalse(parent_cancel.is_set());self.assertTrue(child_cancel.is_set());self.assertTrue(grandchild_cancel.is_set())
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

 def test_uncertain_workflow_pauses_before_another_scheduled_attempt(self):
  workflow=self.engine.save_workflow({'name':'Safe recurring task','prompt':'Mission','cron':'* * * * *','enabled':True})
  first=self.wait(self.engine.submit('default','Prior mission',workflow_id=workflow['id']))
  self.engine.update(first['id'],status='uncertain')
  with self.db() as c:c.execute('UPDATE workflows SET last_job=?,next_run=0 WHERE id=?',(first['id'],workflow['id']))
  before=len(self.engine.state()['jobs']);self.engine.tick()
  self.assertEqual(len(self.engine.state()['jobs']),before);self.assertFalse(self.engine.state()['workflows'][0]['enabled'])
  self.assertIn('Inspect the previous action log',self.engine.state()['notifications'][0]['text'])
 def test_nested_workflow_uses_configured_workspace_without_deadlock(self):
  workflow=self.engine.save_workflow({'name':'Nested workflow','prompt':'Child workflow mission','cron':'* * * * *'})
  turns={}
  def model(messages,*args):
   thread=threading.current_thread().name;turns[thread]=turns.get(thread,0)+1
   if messages[-1].get('content')=='Parent workflow mission' and turns[thread]==1:
    return {'text':'','output':[],'calls':[{'name':'workflow','call_id':'run','arguments':json.dumps({'request':json.dumps({'operation':'run','id':workflow['id']})})}]}
   return {'text':'Verified fixture result','calls':[],'output':[]}
  self.response=model;root=self.wait(self.engine.submit('default','Parent workflow mission'))
  self.assertEqual(root['status'],'completed',root)
  children=[j for j in self.engine.state()['jobs'] if j['parent_id']==root['id']]
  self.assertEqual(len(children),1);self.assertEqual(children[0]['status'],'completed');self.assertEqual(children[0]['agent_id'],'default')
 def test_resume_blocks_mutations_performed_by_a_subagent(self):
  file=self.data/'projects/default/child.txt';args={'action':'write','path':str(file),'destination':'','content':'child wrote once','pattern':'','limit':10}
  turns={};resuming=[False];executions=[]
  original=self.engine.dispatch
  def dispatch(*call):
   if call[3]=='pc_files':executions.append(1)
   return original(*call)
  self.engine.dispatch=dispatch
  def model(messages,*ignored):
   thread=threading.current_thread().name;turns[thread]=turns.get(thread,0)+1
   if resuming[0] or messages[0]['content']=='Write child' and turns[thread]==1:
    return {'text':'','output':[],'calls':[{'name':'pc_files','call_id':'write','arguments':json.dumps(args)}]}
   if messages[0]['content']=='Parent delegation' and turns[thread]==1:
    return {'text':'','output':[],'calls':[{'name':'delegate','call_id':'child','arguments':json.dumps({'request':json.dumps({'operation':'spawn','name':'Writer','mission':'Write child'})})}]}
   return {'text':'Verified fixture result','calls':[],'output':[]}
  self.response=model;first=self.wait(self.engine.submit('default','Parent delegation'))
  self.assertEqual(first['status'],'completed',first);self.assertEqual(file.read_text(),'child wrote once')
  resuming[0]=True;second=self.wait(self.engine.submit('default','Continue verification',resume=first['id']))
  self.assertEqual(second['status'],'denied',second);self.assertEqual(len(executions),1)
 def test_restore_rejects_workspace_collisions_transactionally(self):
  self.engine.save_agent({'id':'other','project':'other','name':'Other'})
  exported=self.engine.backup();payload=json.loads(base64.b64decode(exported['backup']))
  for agent in payload['tables']['agents']:agent['project']='default'
  encoded=base64.b64encode(json.dumps(payload).encode()).decode()
  with self.assertRaises(ValueError):self.engine.restore(encoded,True)
  self.assertEqual(self.engine.agent('other')['project'],'other')

 def test_chat_can_save_scoped_memory_with_pc_access_off(self):
  self.mode='off';turns=[0];seen=[]
  def chat(messages,instructions,provider,on_text,tools):
   seen.extend(tool['name'] for namespace in tools for tool in namespace['tools']);turns[0]+=1
   if turns[0]==1:return {'text':'','output':[],'calls':[{'name':'agent_memory','call_id':'save','arguments':json.dumps({'request':json.dumps({'operation':'save','content':'Prefers a blue orb','pinned':True,'priority':10})})}]}
   return {'text':'Saved your preference.','output':[],'calls':[]}
  self.engine.chat_response=chat;job=self.wait(self.engine.submit('default','Remember my blue orb preference',chat=True,provider='chatgpt'))
  self.assertEqual(job['status'],'completed',job);self.assertEqual(set(seen),{'agent_memory'});self.assertIn('blue orb',self.engine.context_memory('default'))
 def test_chat_cannot_execute_pc_tools(self):
  self.engine.chat_response=lambda *a:{'text':'','output':[],'calls':[{'name':'pc_files','call_id':'forbidden','arguments':json.dumps({'action':'write','path':str(self.data/'forbidden.txt'),'destination':'','content':'must not execute','pattern':'','limit':10})}]}
  job=self.wait(self.engine.submit('default','Ordinary conversation',chat=True,provider='chatgpt'))
  self.assertEqual(job['status'],'denied');self.assertFalse((self.data/'forbidden.txt').exists())
