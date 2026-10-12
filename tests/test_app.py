import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

spec = importlib.util.spec_from_file_location('assistant', Path(__file__).resolve().parents[1] / 'app.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        a.DATA = Path(self.temp.name)
        a.SESSIONS.clear()
        a.ATTEMPTS.clear()
        self.code = a.init()
        self.server = a.ThreadingHTTPServer(('127.0.0.1', 0), a.Handler)
        self.server.daemon_threads = True
        self.host = '127.0.0.1:' + str(self.server.server_port)
        self.server.allowed_hosts = {self.host}
        self.server.pairing_code = self.code
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''

    def test_coding_api_auth_submit_preview_cancel(self):
        import codex_tasks
        manager = codex_tasks.Manager(a.db, a.DATA, lambda: False)
        with patch.object(a, 'CODING', manager):
            self.assertEqual(self.request('/api/codex/health')[0], 401)
            self.login()
            status, result, _ = self.request('/api/codex/submit', {'prompt': 'Review code', 'project': 'api-test'})
            self.assertEqual(status, 202)
            jid = result['id']
            self.assertEqual(self.request('/api/codex/cancel', {'id': jid})[0], 200)
            self.assertEqual(manager.jobs()[0]['status'], 'cancelled')
            (manager.project('api-test')/'hello.py').write_text('print(4)')
            status, result, _ = self.request('/api/codex/file?project=api-test&path=hello.py')
            self.assertEqual(status, 200)
            self.assertEqual(result['text'], 'print(4)')
            self.assertEqual(self.request('/api/codex/file?project=api-test&path=../pairing-code.txt')[0], 400)
            self.assertEqual(self.request('/api/providers', {'coding_backend': 'disabled'})[0], 200)
            self.assertEqual(self.request('/api/codex/submit', {'prompt': 'x', 'project': 'api-test'})[0], 400)
        manager.close()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, body=None, extra=None):
        headers = {'Cookie': self.cookie}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Origin': 'http://' + self.host})
        headers.update(extra or {})
        req = urllib.request.Request('http://' + self.host + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            r = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            r = e
        with r:
            return r.status, json.load(r), r.headers

    def login(self):
        status, data, headers = self.request('/api/login', {'code': self.code})
        self.assertEqual(status, 200)
        self.cookie = headers['Set-Cookie'].split(';')[0]

    def test_auth_and_origin_and_host(self):
        self.assertEqual(self.request('/api/state')[0], 401)
        self.assertEqual(self.request('/api/login', {'code': 'wrong'})[0], 401)
        self.login()
        self.assertEqual(self.request('/api/state')[0], 200)
        self.assertEqual(self.request('/api/memory', {'content': 'Bad'}, {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('/api/state', extra={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('/api/logout', {})[0], 200)
        self.assertEqual(self.request('/api/state')[0], 401)

    def test_pairing_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.request('/api/login', {'code': 'wrong'})[0], 401)
        self.assertEqual(self.request('/api/login', {'code': self.code})[0], 429)

    def remember(self, name='Test browser'):
        status, _, headers = self.request('/api/login', {'code': self.code, 'remember': True, 'name': name})
        self.assertEqual(status, 200)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.assertIn('Max-Age=7776000', headers['Set-Cookie'])
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])

    def test_remembered_device_survives_restart_and_stores_only_hash(self):
        self.remember()
        raw_token = self.cookie.split('=', 1)[1]
        with a.db() as c:
            row = dict(c.execute('SELECT * FROM devices').fetchone())
        self.assertEqual(row['token_hash'], a.token_hash(raw_token))
        self.assertNotIn(raw_token, json.dumps(row))
        a.SESSIONS.clear()
        a.init()
        status, state, _ = self.request('/api/state')
        self.assertEqual(status, 200)
        self.assertTrue(state['devices'][0]['current'])
        self.assertNotIn('token_hash', state['devices'][0])
        self.assertNotIn(raw_token, json.dumps(state))
        with a.db() as c:
            c.execute('UPDATE devices SET expires=?', (time.time()-1,))
        self.assertEqual(self.request('/api/state')[0], 401)

    def test_device_revocation_and_logout(self):
        self.remember('First')
        first_cookie = self.cookie
        first_id = self.request('/api/devices')[1]['devices'][0]['id']
        self.remember('Second')
        self.assertEqual(len(self.request('/api/devices')[1]['devices']), 2)
        status, result, _ = self.request('/api/devices/revoke', {'id': first_id})
        self.assertEqual(status, 200)
        self.assertFalse(result['current'])
        self.assertEqual(self.request('/api/state', extra={'Cookie': first_cookie})[0], 401)
        self.assertEqual(self.request('/api/state')[0], 200)
        self.assertEqual(self.request('/api/logout', {})[0], 200)
        self.assertEqual(self.request('/api/state')[0], 401)
        with a.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM devices').fetchone()[0], 0)

    def test_temporary_session_and_device_route_guards(self):
        self.assertEqual(self.request('/api/devices')[0], 401)
        self.assertEqual(self.request('/api/devices/revoke', {'id': 'a'*32})[0], 401)
        self.assertEqual(self.request('/api/login', {'code': self.code, 'remember': 'yes'})[0], 400)
        self.login()
        self.assertEqual(self.request('/api/devices/revoke', {'id': '../data'})[0], 400)
        self.assertEqual(self.request('/api/devices/revoke', {'id': 'a'*32}, {'Origin': 'https://evil.example'})[0], 403)
        a.SESSIONS.clear()
        self.assertEqual(self.request('/api/state')[0], 401)

    def test_current_device_revoke_clears_cookie(self):
        self.remember()
        did = self.request('/api/devices')[1]['devices'][0]['id']
        status, result, headers = self.request('/api/devices/revoke', {'id': did})
        self.assertEqual(status, 200)
        self.assertTrue(result['current'])
        self.assertIn('Max-Age=0', headers['Set-Cookie'])
        self.assertEqual(self.request('/api/state')[0], 401)

    def test_pc_agent_api_auth_consent_and_settings(self):
        from unittest.mock import Mock
        agent=Mock();agent.submit.return_value='job';agent.jobs.return_value=[];agent.active=None
        agent.lock=threading.RLock()
        gpt=Mock();gpt.state.return_value={'status':'connected','sharing':True}
        with patch.object(a,'PC',agent),patch.object(a,'GPT',gpt):
            self.assertEqual(self.request('/api/pc/submit',{'prompt':'storage'})[0],401)
            self.assertEqual(self.request('/api/pc/approve',{})[0],401)
            agent.submit.assert_not_called()
            self.login()
            self.assertEqual(self.request('/api/pc/submit',{'prompt':'storage'})[0],202)
            self.assertEqual(self.request('/api/pc/approve',{'id':'job','request_id':'request','digest':'digest','allow':True})[0],200)
            agent.decide.assert_called_once_with('job','request','digest',True)
            self.assertEqual(self.request('/api/pc/submit',{'prompt':'storage'},{'Origin':'https://evil.example'})[0],403)
            self.assertEqual(self.request('/api/pc/settings',{'mode':'off'})[0],200)
            self.assertEqual(self.request('/api/pc/submit',{'prompt':'storage'})[0],400)
            self.assertEqual(self.request('/api/pc/settings',{'mode':'everything-without-review'})[0],400)

    def test_auto_route_is_authenticated_validated_and_cannot_submit_work(self):
        from unittest.mock import Mock
        gpt=Mock();agent=Mock();coding=Mock()
        a.set_setting('chat_backend','chatgpt')
        with patch.object(a,'GPT',gpt),patch.object(a,'PC',agent),patch.object(a,'CODING',coding):
            self.assertEqual(self.request('/api/auto/route',{'message':'How are you?'})[0],401)
            gpt.respond.assert_not_called()
            self.login()
            for route in ('chat','agent','code','review'):
                gpt.respond.return_value=json.dumps({'route':route,'reason':'Synthetic decision'})
                status,body,_=self.request('/api/auto/route',{'message':'A synthetic request'})
                self.assertEqual(status,200)
                self.assertEqual(body['route'],route)
            for invalid in ('not JSON','{"route":"execute","reason":"bad"}','{"route":"agent"}'):
                gpt.respond.return_value=invalid
                self.assertEqual(self.request('/api/auto/route',{'message':'x'})[0],400)
            a.set_setting('pc_agent_mode','off')
            gpt.respond.return_value='{"route":"agent","reason":"Needs live PC state"}'
            self.assertEqual(self.request('/api/auto/route',{'message':'storage'})[0],400)
            self.assertEqual(self.request('/api/auto/route',{'message':'x'},{'Origin':'https://evil.example'})[0],403)
            agent.submit.assert_not_called();coding.submit.assert_not_called()

    def test_desktop_controller_is_private_and_requires_exact_token(self):
        import hashlib,os
        with patch.object(a,'DESKTOP_TOKEN','synthetic-desktop-controller'):
            status,result,_=self.request('/api/desktop/status')
            self.assertEqual(status,200)
            self.assertEqual(result['installation'],hashlib.sha256(os.path.normcase(str(a.ROOT)).encode()).hexdigest())
            self.assertNotIn('synthetic-desktop-controller',json.dumps(result))
            self.assertEqual(self.request('/api/desktop/stop',{'confirmed':True})[0],401)
            self.assertEqual(self.request('/api/desktop/stop',{'confirmed':True},{'X-TREN-Desktop':'wrong'})[0],401)
            self.assertEqual(self.request('/api/desktop/stop',{'confirmed':False},{'X-TREN-Desktop':'synthetic-desktop-controller'})[0],400)
            self.assertEqual(self.request('/api/desktop/stop',{'confirmed':True},{'X-TREN-Desktop':'synthetic-desktop-controller','Origin':'https://evil.example'})[0],403)
            stopped=threading.Event()
            with patch.object(self.server,'shutdown',side_effect=stopped.set),patch.object(a,'STOP') as stop:
                self.assertEqual(self.request('/api/desktop/stop',{'confirmed':True},{'X-TREN-Desktop':'synthetic-desktop-controller'})[0],200)
                self.assertTrue(stopped.wait(2))
                stop.set.assert_called_once()

    def test_rebrand_keeps_returning_identity_and_new_profiles_use_nova(self):
        self.assertEqual(a.state()['profile']['name'],'Nova')
        a.set_setting('onboarding_complete','1')
        a.init()
        self.assertEqual(a.state()['profile']['name'],'TREN')
        a.set_setting('assistant_name','Custom Name')
        a.init()
        self.assertEqual(a.state()['profile']['name'],'Custom Name')

    def test_repository_rename_migrates_only_the_legacy_default(self):
        a.set_setting('update_repository','alecjhalpin/TREN')
        a.init()
        self.assertEqual(a.setting('update_repository'),'alecjhalpin/Veyra')
        a.set_setting('update_repository','someone/custom')
        a.init()
        self.assertEqual(a.setting('update_repository'),'someone/custom')

    def test_assistant_profile_requires_pairing_and_persists(self):
        self.assertEqual(self.request('/api/profile',{'name':'Nova','completed':False})[0],401)
        self.login()
        for body in ({'name':'<script>','completed':True},{'name':'Nova','completed':'yes'},{'name':' ','completed':True}):
            self.assertEqual(self.request('/api/profile',body)[0],400)
        self.assertEqual(self.request('/api/profile',{'name':'Nova','completed':False})[0],200)
        self.assertEqual(a.state()['profile'],{'name':'Nova','named':True,'onboarding_complete':False})
        self.assertIn('You are Nova,',a.system_prompt())
        a.init()
        self.assertFalse(a.state()['profile']['onboarding_complete'])
        self.assertEqual(self.request('/api/profile',{'name':'Nova','completed':True})[0],200)
        a.init()
        self.assertTrue(a.state()['profile']['onboarding_complete'])

    def test_existing_user_data_does_not_force_first_run_setup(self):
        with a.db() as connection:
            connection.execute("DELETE FROM settings WHERE key='onboarding_complete'")
            connection.execute("INSERT INTO memories(content,created) VALUES('Preserved note',1)")
        a.init()
        self.assertTrue(a.state()['profile']['onboarding_complete'])
        self.assertEqual(a.state()['memories'][0]['content'],'Preserved note')

    def test_second_instance_does_not_touch_running_job_state(self):
        with patch.object(sys,'argv',['app.py','--no-browser']),patch.object(a,'TrenHTTPServer',side_effect=OSError('port in use')),patch.object(a,'init') as initialize:
            a.main()
            initialize.assert_not_called()

    def test_chat_and_explicit_memory_persistence(self):
        self.login()
        self.assertEqual(self.request('/api/memory', {'content': 'Name: Alec'})[0], 200)
        captured = []
        def fake(path, body=None, timeout=5):
            captured.append(body)
            return {'message': {'content': 'Hello Alec'}}
        with patch.object(a, 'ollama_request', side_effect=fake):
            status, data, _ = self.request('/api/chat', {'message': 'Hello'})
        self.assertEqual(status, 200)
        self.assertEqual(data['answer'], 'Hello Alec')
        self.assertIn('Name: Alec', captured[0]['messages'][0]['content'])
        self.assertEqual(a.init(), self.code)
        state = a.state()
        self.assertEqual(len(state['messages']), 2)
        self.assertEqual(state['memories'][0]['content'], 'Name: Alec')

    def test_validation_and_model_failure(self):
        self.login()
        self.assertEqual(self.request('/api/chat', {'message': ''})[0], 400)
        self.assertEqual(self.request('/api/tasks', {'title':'x','prompt':'x','next_run':float('nan')})[0], 400)
        with patch.object(a, 'ollama_request', side_effect=urllib.error.URLError('offline')):
            status, data, _ = self.request('/api/chat', {'message': 'hello'})
        self.assertEqual(status, 503)
        self.assertIn('Ollama', data['error'])
        self.assertEqual(a.state()['messages'], [])

    def test_gpt_context_and_provider_persistence(self):
        from unittest.mock import Mock
        self.login()
        a.set_setting('chat_backend', 'chatgpt')
        a.chat('/remember Prefer concise answers')
        backend = Mock()
        backend.respond.return_value = 'GPT reply'
        backend.state.return_value = {'status': 'connected', 'sharing': True}
        with patch.object(a, 'GPT', backend), patch.object(a, 'generate', side_effect=AssertionError('No Ollama')):
            status, result, _ = self.request('/api/chat', {'message': 'Hello'})
        self.assertEqual(status, 200)
        self.assertEqual(result['answer'], 'GPT reply')
        messages, instructions, model = backend.respond.call_args.args
        self.assertIn('Prefer concise answers', instructions)
        self.assertEqual(messages[-1]['content'], 'Hello')
        self.assertEqual(a.state()['messages'][-1]['provider'], 'chatgpt')
        self.assertEqual(a.state()['messages'][1]['provider'], 'local')

    def test_gpt_failure_fallback_is_opt_in_and_labelled(self):
        from unittest.mock import Mock
        import providers
        self.login()
        a.set_setting('chat_backend', 'chatgpt')
        backend = Mock()
        backend.respond.side_effect = providers.ChatGPTError('subscription_sharing_usage_limit_exceeded')
        backend.state.return_value = {'status': 'connected', 'sharing': True}
        with patch.object(a, 'GPT', backend), patch.object(a, 'generate', return_value='Local reply') as local:
            self.assertEqual(self.request('/api/chat', {'message': 'Hello'})[0], 503)
            local.assert_not_called()
            self.assertEqual(a.state()['messages'], [])
            a.set_setting('ollama_fallback', '1')
            status, result, _ = self.request('/api/chat', {'message': 'Hello'})
            self.assertEqual(status, 200)
            self.assertIn('Ollama fallback', result['answer'])
            self.assertEqual(a.state()['messages'][-1]['provider'], 'ollama')
            status, _, _ = self.request('/api/chat', {'message': 'Hi locally', 'provider': 'ollama'})
            self.assertEqual(status, 200)
            self.assertEqual(backend.respond.call_count, 2)

    def test_gpt_auth_settings_routes_are_paired_and_validated(self):
        from unittest.mock import Mock
        backend = Mock()
        backend.state.return_value = {'status': 'connected', 'sharing': True}
        backend.models_cache = [{'slug': 'available'}]
        backend.models.return_value = backend.models_cache
        backend.start_sign_in.return_value = {'status': 'connecting'}
        backend.disconnect.return_value = {'ok': True, 'remote_revoked': True}
        with patch.object(a, 'GPT', backend):
            for route in ('/api/chatgpt/connect', '/api/chatgpt/models', '/api/chatgpt/disconnect'):
                self.assertEqual(self.request(route, {})[0], 401)
            backend.start_sign_in.assert_not_called()
            self.login()
            self.assertEqual(self.request('/api/chatgpt/connect', {})[0], 202)
            self.assertEqual(self.request('/api/chatgpt/models', {})[0], 200)
            body = {'backend': 'chatgpt', 'model': 'available', 'fallback': False}
            self.assertEqual(self.request('/api/conversation/settings', body)[0], 200)
            self.assertEqual(a.setting('chat_backend'), 'chatgpt')
            self.assertEqual(self.request('/api/conversation/settings', {**body, 'model': 'unknown'})[0], 400)
            self.assertEqual(self.request('/api/chat', {'message': 'Hello', 'provider': 'unknown'})[0], 400)
            self.assertEqual(self.request('/api/chatgpt/disconnect', {})[0], 200)
            self.assertEqual(a.setting('chat_backend'), 'ollama')

    def test_due_claim_once_and_recurring_catchup(self):
        with a.db() as c:
            c.execute('INSERT INTO tasks(title,prompt,next_run,interval_seconds) VALUES(?,?,?,?)', ('once','hello',100,0))
            c.execute('INSERT INTO tasks(title,prompt,next_run,interval_seconds) VALUES(?,?,?,?)', ('repeat','hello',100,3600))
        first = a.claim_due(10000)
        second = a.claim_due(10000)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNone(a.claim_due(10000))
        with a.db() as c:
            tasks = list(c.execute('SELECT * FROM tasks ORDER BY id'))
        self.assertEqual(tasks[0]['enabled'], 0)
        self.assertEqual(tasks[1]['next_run'], 10900)
        with patch.object(a, 'generate', return_value='Scheduled answer'):
            a.execute_run(*first)
        self.assertEqual(a.state()['runs'][-1]['status'], 'done')
        a.init()
        self.assertEqual(a.state()['runs'][0]['status'], 'interrupted')

    def test_prompt_run_and_failure_record(self):
        self.login()
        now = time.time()
        self.assertEqual(self.request('/api/tasks', {'title':'Review','prompt':'Suggest next steps','next_run':now+10,'interval_seconds':0})[0], 200)
        item = a.claim_due(now+20)
        with patch.object(a, 'generate', side_effect=RuntimeError('offline')):
            a.execute_run(*item)
        self.assertEqual(a.state()['runs'][0]['status'], 'failed')
        self.assertEqual(a.state()['runs'][0]['result'], 'offline')
        self.assertEqual(self.request('/api/tasks/delete', {'id':item[0]['id']})[0], 200)
        self.assertEqual(a.state()['tasks'], [])


    def test_web_tool_loop_and_source_links(self):
        self.login()
        responses = [
            {'message': {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'web_search', 'arguments': {'query': 'test'}}}]}},
            {'message': {'role': 'assistant', 'content': 'A grounded answer'}}]
        with patch.object(a, 'ollama_request', side_effect=responses), patch.object(a.webtools, 'run', return_value={'results': [{'title':'Source','url':'https://example.com'}]}):
            status, data, _ = self.request('/api/chat', {'message': 'Search for test'})
        self.assertEqual(status, 200)
        self.assertIn('https://example.com', data['answer'])
        self.assertEqual(a.state()['events'][0]['status'], 'done')

    def test_gaming_pause_and_web_setting(self):
        self.login()
        with patch.object(a, 'ollama_request', return_value={}):
            self.assertEqual(self.request('/api/settings', {'key':'gaming','value':True})[0], 200)
        with a.db() as c:
            c.execute('INSERT INTO tasks(title,prompt,next_run,interval_seconds) VALUES(?,?,?,?)', ('once','hello',100,0))
        self.assertIsNone(a.claim_due(1000))
        self.assertTrue(a.state()['gaming'])
        self.assertEqual(self.request('/api/tasks/run', {'id':1})[0], 400)
        self.assertEqual(self.request('/api/settings', {'key':'web_enabled','value':False})[0], 200)
        with self.assertRaises(RuntimeError):
            a.use_web_tool('web_search', {'query':'test'})
        self.assertEqual(self.request('/api/settings', {'key':'gaming','value':False})[0], 200)
        self.assertIsNotNone(a.claim_due(1000))

    def test_direct_commands_do_not_call_model(self):
        self.login()
        with patch.object(a, 'generate', side_effect=AssertionError('Should not use model')):
            self.assertEqual(self.request('/api/chat', {'message':'/remember I prefer concise answers'})[0], 200)
            status, data, _ = self.request('/api/chat', {'message':'/remind 10m | Review | Suggest project next steps'})
            self.assertEqual(status, 200)
            self.assertIn('Created task', data['answer'])
            self.assertEqual(self.request('/api/chat', {'message':'/remind nonsense'})[0], 400)
        self.assertEqual(a.state()['memories'][0]['content'], 'I prefer concise answers')
        self.assertEqual(len(a.state()['tasks']), 1)

    def test_tool_budget_is_bounded(self):
        calls = [{'function': {'name': 'web_search', 'arguments': {'query': 'test'}}}] * 10
        with patch.object(a, 'ollama_request', return_value={'message': {'role':'assistant','tool_calls':calls}}), patch.object(a.webtools, 'run', return_value={'results': []}) as run:
            with self.assertRaises(RuntimeError):
                a.generate([{'role':'user','content':'search'}])
            self.assertEqual(run.call_count, 6)

    def test_update_endpoints_require_auth_and_confirm(self):
        class FakeUpdates:
            def state(self):return {'version':'0.5.0'}
            def check(self,repo):return {'version':'0.6.0','available':True}
            def stage(self,raw,origin):return {'staged':{'version':'0.6.0'}}
        with patch.object(a,'UPDATER',FakeUpdates()):
            self.assertEqual(self.request('/api/updates/state')[0],401)
            self.assertEqual(self.request('/api/updates/upload',{'zip':'bad'})[0],401)
            self.login()
            self.assertEqual(self.request('/api/updates/check',{'repository':'owner/repo'})[0],200)
            self.assertEqual(self.request('/api/updates/upload',{'zip':'!bad'})[0],400)
            self.assertEqual(self.request('/api/updates/install',{})[0],400)
            with patch.object(a,'begin_update') as begin:
                self.assertEqual(self.request('/api/updates/install',{'confirmed':True})[0],202)
                begin.assert_called_once()

    def test_update_rejects_queued_work_and_releases_maintenance(self):
        import codex_tasks
        manager=codex_tasks.Manager(a.db,a.DATA,lambda:False)
        manager.submit({'prompt':'test','project':'test'})
        with patch.object(a,'CODING',manager):
            with self.assertRaises(ValueError):a.begin_update(self.server)
            self.assertFalse(a.UPDATING.is_set())
            self.assertTrue(a.GENERATION_LOCK.acquire(blocking=False));a.GENERATION_LOCK.release()
        manager.close()


    def test_stop_cancels_active_local_inference_response(self):
        gate=threading.Event();opened=threading.Event();errors=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):opened.set();gate.wait(2);return b'{}'
            def close(self):gate.set()
        response=Response()
        class Opener:
            def open(self,*args,**kwargs):return response
        def infer():
            try:a.ollama_request('/api/chat',{},timeout=2)
            except Exception as error:errors.append(error)
        with patch.object(a.urllib.request,'build_opener',return_value=Opener()),patch.object(a,'GPT',None):
            thread=threading.Thread(target=infer,name='local-fixture');thread.start();self.assertTrue(opened.wait(1));a.cancel_provider_requests('local-fixture');thread.join(1)
        self.assertFalse(thread.is_alive());self.assertIsInstance(errors[0],InterruptedError);self.assertFalse(a.OLLAMA_REQUESTS)


if __name__ == '__main__':
    unittest.main()
