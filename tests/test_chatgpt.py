"""Protocol/loopback tests with synthetic tokens. No real account or DPAPI claim."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import providers as p


def encoded(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b'=').decode()


def token(nonce='nonce', client='issued-client', **claims):
    return encoded({'alg': 'RS256', 'kid': 'test-key'}) + '.' + encoded({
        'iss': p.ISSUER, 'aud': client, 'exp': time.time() + 300, 'iat': time.time(),
        'sub': 'synthetic-user', 'nonce': nonce, 'name': 'Test User', **claims}) + '.signature'


def grant(nonce='nonce'):
    return {'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh',
            'token_type': 'Bearer', 'expires_in': 3600, 'scope': p.SCOPES, 'id_token': token(nonce)}


DISCOVERY = {'issuer': p.ISSUER, 'authorization_endpoint': p.ISSUER + '/api/accounts/authorize',
             'token_endpoint': p.ISSUER + '/api/accounts/oauth/token', 'jwks_uri': p.ISSUER + '/.well-known/jwks.json',
             'revocation_endpoint': p.ISSUER + '/oauth/revoke'}


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.crypto = patch.object(p, 'protected_bytes', side_effect=lambda value, decrypt=False: value[4:] if decrypt else b'TEST' + value)
        self.crypto.start()
        self.signature = patch.object(p, 'verify_signature', return_value=True)
        self.signature.start()
        self.client = p.ChatGPT(self.tmp.name)
        self.client.supported = True
        self.client.discovery_cache = dict(DISCOVERY)

    def tearDown(self):
        self.client.cancel_sign_in()
        self.signature.stop()
        self.crypto.stop()
        self.tmp.cleanup()

    def json_remote(self, url, data=None, token=None, form=False):
        if 'jwks' in url:
            return {'keys': [{'kid': 'test-key', 'kty': 'RSA'}]}
        if url == p.RESOURCE + '/models':
            return {'models': [{'slug': 'preferred-slug', 'display_name': 'Preferred model', 'visibility': 'list'},
                               {'slug': 'hidden', 'display_name': 'Hidden', 'visibility': 'hidden'}]}
        return dict(DISCOVERY)

    def connected(self):
        self.client.record = {'format': 1, 'client_id': 'issued-client', 'pending': {'data': grant(),
                              'received': time.time(), 'nonce': 'nonce'}}
        with patch.object(self.client, '_json', side_effect=self.json_remote):
            self.client._finish_pending()

    def test_identity_claims_nonce_and_signature_required(self):
        with patch.object(self.client, '_json', side_effect=self.json_remote):
            self.assertEqual(self.client._identity(token(), 'issued-client', 'nonce')[0], 'synthetic-user')
            for bad in [token(nonce='wrong'), token(client='other'), token(iss='https://evil.example'),
                        token(exp=time.time()-30), token(iat=time.time()+30), token(azp='other')]:
                with self.assertRaises(p.ChatGPTError) as error:
                    self.client._identity(bad, 'issued-client', 'nonce')
                self.assertEqual(error.exception.code, 'invalid_identity')
            with patch.object(p, 'verify_signature', return_value=False):
                with self.assertRaises(p.ChatGPTError):
                    self.client._identity(token(), 'issued-client', 'nonce')

    def test_callback_pkce_registration_and_no_credentials_in_state(self):
        done = threading.Event()
        browser_query = {}
        calls = []
        self.client.on_connected = done.set
        def browser(url):
            browser_query.update({k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).items()})
            def callback():
                redirect = browser_query['redirect_uri']
                for query in [{'state': 'wrong'}, {'state': 'é'}, {'state': browser_query['state'], 'client_id': 'issued-client', 'code': 'one-time-code'}]:
                    try:
                        with urllib.request.urlopen(redirect + '?' + urllib.parse.urlencode(query)) as response:
                            self.assertEqual(response.status, 200)
                    except urllib.error.HTTPError as e:
                        self.assertEqual(e.code, 400)
            threading.Thread(target=callback, daemon=True).start()
            return True
        def remote(url, data=None, token=None, form=False):
            if url == DISCOVERY['token_endpoint']:
                calls.append(data)
                self.assertEqual(self.client.record['client_id'], 'issued-client')
                return grant(browser_query['nonce'])
            return self.json_remote(url, data, token, form)
        with patch.object(p.webbrowser, 'open', side_effect=browser), patch.object(self.client, '_json', side_effect=remote):
            self.client.start_sign_in()
            self.assertTrue(done.wait(5))
            for _ in range(50):
                if not self.client.connecting:
                    break
                time.sleep(.01)
        self.assertEqual(browser_query['client_id'], 'dynamic_agent_client')
        self.assertEqual(browser_query['agent_name_hint'], 'TREN')
        self.assertTrue(browser_query['ext_agent_host_id'].startswith('urn:uuid:'))
        self.assertEqual(calls[0]['client_id'], 'issued-client')
        challenge = base64.urlsafe_b64encode(hashlib.sha256(calls[0]['code_verifier'].encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(challenge, browser_query['code_challenge'])
        self.assertEqual(calls[0]['redirect_uri'], browser_query['redirect_uri'])
        safe = json.dumps(self.client.state())
        for secret in ('synthetic-access', 'synthetic-refresh', 'one-time-code', browser_query['nonce']):
            self.assertNotIn(secret, safe)
        self.assertTrue(self.client.path.read_bytes().startswith(b'TEST'))

    def test_rotating_refresh_checkpoint_survives_key_outage_and_restart(self):
        self.connected()
        self.client.record['expires'] = 0
        refresh_calls = []
        def unavailable(url, data=None, token=None, form=False):
            if url == DISCOVERY['token_endpoint']:
                refresh_calls.append(data)
                return {**grant(), 'refresh_token': 'rotated-refresh'}
            raise p.ChatGPTError('network_error')
        with patch.object(self.client, '_json', side_effect=unavailable):
            with self.assertRaises(p.ChatGPTError):
                self.client._credentials()
        restarted = p.ChatGPT(self.tmp.name)
        restarted.discovery_cache = dict(DISCOVERY)
        self.assertEqual(restarted.record['pending']['data']['refresh_token'], 'rotated-refresh')
        with patch.object(restarted, '_json', side_effect=self.json_remote):
            self.assertEqual(restarted._credentials(), 'synthetic-access')
        self.assertEqual(len(refresh_calls), 1)
        self.assertEqual(restarted.record['refresh_token'], 'rotated-refresh')
        self.assertNotIn('pending', restarted.record)

    def test_sharing_permission_and_dynamic_catalog(self):
        self.connected()
        with patch.object(self.client, '_json', side_effect=self.json_remote):
            self.assertEqual(self.client.models(), [{'slug': 'preferred-slug', 'display_name': 'Preferred model'}])
            self.client.record['scopes'] = ['openid']
            with self.assertRaises(p.ChatGPTError) as error:
                self.client.models()
            self.assertEqual(error.exception.code, 'sharing_not_enabled')

    def test_identity_only_consent_is_not_plan_sharing(self):
        self.client.record = {'format': 1, 'client_id': 'issued-client', 'pending': {
            'data': {'id_token': token(), 'scope': 'openid profile email'}, 'received': time.time(), 'nonce': 'nonce'}}
        with patch.object(self.client, '_json', side_effect=self.json_remote):
            self.client._finish_pending()
        self.assertEqual(self.client.state()['status'], 'connected')
        self.assertFalse(self.client.state()['sharing'])
        with self.assertRaises(p.ChatGPTError) as error:
            self.client._credentials()
        self.assertEqual(error.exception.code, 'sharing_not_enabled')

    def test_response_request_uses_only_oauth_and_terminal_completion(self):
        self.connected()
        terminal = {'type': 'response.completed', 'response': {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'Complete reply'}]}]}}
        stream = io.BytesIO(('data: ' + json.dumps(terminal) + '\n\n').encode())
        with patch.object(self.client, '_json', side_effect=self.json_remote), patch.object(self.client, '_open', return_value=stream) as opened:
            self.assertEqual(self.client.respond([{'role': 'user', 'content': 'Hello'}], 'Saved TREN notes'), 'Complete reply')
        args, kwargs = opened.call_args
        self.assertEqual(args[0], p.RESOURCE + '/responses')
        self.assertEqual(args[1]['model'], 'preferred-slug')
        self.assertIs(args[1]['store'], False)
        self.assertIs(args[1]['stream'], True)
        self.assertEqual(kwargs['token'], 'synthetic-access')

    def test_namespaced_tools_request_returns_completed_calls(self):
        import codex_tasks
        self.connected()
        event={'type':'response.completed','response':{'status':'completed','output':[
            {'type':'function_call','namespace':'tren','name':'pc_info','call_id':'call','arguments':'{"section":"storage"}'}]}}
        stream=io.BytesIO(('data: '+json.dumps(event)+'\n\n').encode())
        with patch.object(self.client,'_json',side_effect=self.json_remote),patch.object(self.client,'_open',return_value=stream) as opened:
            reply=self.client.respond_turn([{'role':'user','content':'storage'}],'context',tools=codex_tasks.pc_schemas())
        body=opened.call_args.args[1]
        self.assertEqual(body['tools'][0]['type'],'namespace')
        self.assertEqual(reply['calls'][0]['call_id'],'call')
        self.assertNotIn('previous_response_id',body)
        self.assertFalse(body['store']);self.assertTrue(body['stream'])

    def test_late_failure_or_disconnected_stream_never_accepts_partial_text(self):
        delta = {'type': 'response.output_text.delta', 'delta': 'partial reply'}
        failed = {'type': 'response.failed', 'response': {'error': {'code': 'subscription_sharing_usage_limit_exceeded', 'message': 'SECRET'}}}
        for events in ([delta], [delta, failed], [{'type': 'response.incomplete'}]):
            stream = io.BytesIO(''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode())
            with self.assertRaises(p.ChatGPTError) as error:
                p.read_stream(stream)
            self.assertNotIn('SECRET', str(error.exception))
        self.assertEqual(p.provider_error({'error': {'message': 'Bearer SECRET'}}).code, 'provider_error')

    def test_disallowed_network_origins_and_redirects(self):
        for url in ['http://auth.openai.com/token', 'https://evil.example/token', 'https://api.openai.com.evil/v1/models',
                    'https://user:password@auth.openai.com/token', 'https://auth.openai.com/#secret']:
            with self.assertRaises(p.ChatGPTError):
                self.client._open(url, token='never-sent')
        with self.assertRaises(p.ChatGPTError):
            p.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example')

    def test_corrupt_store_is_preserved_and_disconnect_does_not_erase_it(self):
        self.client.directory.mkdir()
        self.client.path.write_bytes(b'corrupt-credential-file')
        loaded = p.ChatGPT(self.tmp.name)
        with self.assertRaises(p.ChatGPTError):
            loaded.disconnect()
        self.assertEqual(self.client.path.read_bytes(), b'corrupt-credential-file')


class SignatureTests(unittest.TestCase):
    def test_structured_tool_only_completion_preserves_namespace_and_reasoning(self):
        import io
        output=[{'type':'reasoning','id':'r','encrypted_content':'synthetic'},
                {'type':'function_call','namespace':'tren','name':'pc_info','call_id':'call-id','arguments':'{"section":"storage"}'}]
        event={'type':'response.completed','response':{'status':'completed','output':output}}
        parsed=p.read_stream(io.BytesIO(('data: '+json.dumps(event)+'\n\n').encode()),structured=True)
        self.assertEqual(parsed['output'],output)
        self.assertEqual(parsed['calls'][0]['call_id'],'call-id')
        self.assertEqual(parsed['text'],'')

    def test_tool_failures_are_distinguished_without_executing_partial_calls(self):
        import io
        cases = [
            (b'', 'stream_ended'),
            ({'status': 'completed', 'output': []}, 'tool_response_empty'),
            ({'status': 'completed', 'output': [{'type':'function_call','name':'pc_info'}]}, 'tool_response_invalid'),
        ]
        for response, code in cases:
            raw = response if isinstance(response, bytes) else ('data: '+json.dumps({'type':'response.completed','response':response})+'\n\n').encode()
            with self.subTest(code=code), self.assertRaises(p.ChatGPTError) as failure:
                p.read_stream(io.BytesIO(raw), structured=True)
            self.assertEqual(failure.exception.code, code)

    def test_real_node_rsa_signature_and_tampering(self):
        script = """const c=require('node:crypto');const {privateKey,publicKey}=c.generateKeyPairSync('rsa',{modulusLength:2048});const h=Buffer.from(JSON.stringify({alg:'RS256'})).toString('base64url');const b=Buffer.from(JSON.stringify({sub:'synthetic'})).toString('base64url');const text=h+'.'+b;console.log(JSON.stringify({token:text+'.'+c.sign('RSA-SHA256',Buffer.from(text),privateKey).toString('base64url'),key:publicKey.export({format:'jwk'})}));"""
        fixture = json.loads(subprocess.check_output(['node', '-e', script], text=True))
        self.assertTrue(p.verify_signature(fixture['token'], fixture['key']))
        pieces = fixture['token'].split('.')
        pieces[1] = encoded({'sub': 'tampered'})
        self.assertFalse(p.verify_signature('.'.join(pieces), fixture['key']))


if __name__ == '__main__':
    unittest.main()
