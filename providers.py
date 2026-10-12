"""Provider capabilities are independent of TREN memory and scheduling."""
PROVIDERS = {
    'chatgpt': {'name': 'ChatGPT plan sharing', 'capabilities': ['conversation']},
    'ollama': {'name': 'Ollama', 'capabilities': ['conversation', 'web_research']},
    'codex': {'name': 'Codex / ChatGPT login', 'capabilities': ['coding', 'code_review']},
}


def coding_intent(text):
    import re
    return text.startswith('/code ') or bool(re.search(
        r'\b(create|build|write|fix|implement|debug|refactor)\b.*\b(python|application|app|code|script|website|program|bug)\b',
        text, re.I))


# Documented local-app OAuth flow. No API keys or Codex credentials are read.
import base64
import ctypes
import hashlib
import http.server
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser

ISSUER = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
SHARING = 'chatgpt.tokens.use.direct'
SCOPES = 'openid profile email offline_access resource.invoke ' + SHARING
ERRORS = {
    'sign_in_required': 'Connect ChatGPT in Settings first.',
    'sharing_not_enabled': 'ChatGPT sign-in succeeded, but plan sharing was not granted. Enable sharing and reconnect.',
    'invalid_grant': 'The ChatGPT connection expired. Reconnect in Settings.',
    'subscription_sharing_usage_limit_exceeded': 'Your ChatGPT sharing limit was reached. Check app limits in ChatGPT Settings.',
    'subscription_sharing_usage_unavailable': 'ChatGPT plan usage could not be checked. Try again shortly.',
    'subscription_sharing_user_not_eligible': 'This account or workspace is not eligible for ChatGPT plan sharing.',
    'subscription_sharing_v2_client_not_enabled': 'VEYRA is not enabled for plan sharing on this account.',
    'cancelled': 'ChatGPT sign-in was cancelled.',
    'access_denied': 'ChatGPT permission was declined.',
    'stream_ended': 'ChatGPT stream ended before a completion event. No tool actions from this response were executed.',
    'tool_response_empty': 'ChatGPT completed the PC-agent response without text or function calls.',
    'tool_response_invalid': 'ChatGPT returned a function call with missing or invalid fields. No tool actions from this response were executed.',
    'response_format_error': 'VEYRA could not parse the ChatGPT response format. No tool actions from this response were executed.',
    'incomplete_response': 'ChatGPT did not complete its response. No partial answer was saved.',
    'storage_unavailable': 'ChatGPT credentials could not be protected or read. Existing credentials were preserved.',
    'identity_unavailable': 'ChatGPT identity verification is unavailable. Your saved connection was preserved; try again.',
    'invalid_identity': 'ChatGPT identity verification failed. Reconnect in Settings.',
    'network_error': 'ChatGPT could not be reached. Check your connection and try again.',
    'connection_busy': 'Finish or cancel ChatGPT sign-in before changing this connection.',
}


class ChatGPTError(RuntimeError):
    def __init__(self, code):
        # Never pass provider error messages, tokens, request URLs or traces to UI.
        self.code = code if isinstance(code, str) and code in ERRORS else 'provider_error'
        super().__init__(ERRORS.get(self.code, 'ChatGPT could not complete this request. Check the connection and try again.'))


def provider_error(data):
    error = data.get('error', {}) if isinstance(data, dict) else {}
    code = error.get('code') or error.get('type') if isinstance(error, dict) else error
    if isinstance(code, str):
        code = code.replace('subscription_sharing_v2_usage_', 'subscription_sharing_usage_')
    return ChatGPTError(code)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ChatGPTError('network_error')


def protected_bytes(value, decrypt=False):
    """Windows DPAPI, CurrentUser. No secret in command arguments or plaintext files."""
    if os.name != 'nt':
        raise ChatGPTError('storage_unavailable')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(value)
    incoming = Blob(len(value), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not fn(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ChatGPTError('storage_unavailable')
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


JWT_VERIFY = """
const fs=require('node:fs'),crypto=require('node:crypto');
try{const {token,key}=JSON.parse(fs.readFileSync(0,'utf8'));
const p=token.split('.');const pub=crypto.createPublicKey({key,format:'jwk'});
process.stdout.write(crypto.verify('RSA-SHA256',Buffer.from(p[0]+'.'+p[1]),pub,Buffer.from(p[2],'base64url'))?'1':'0');}
catch{process.stdout.write('0');}
"""


def verify_signature(token, key):
    node = os.getenv('TREN_NODE') or shutil.which('node')
    if not node:
        raise ChatGPTError('identity_unavailable')
    try:
        result = subprocess.run([node, '-e', JWT_VERIFY], input=json.dumps({'token': token, 'key': key}),
                                text=True, capture_output=True, timeout=15, shell=False,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.SubprocessError):
        raise ChatGPTError('identity_unavailable') from None
    return result.returncode == 0 and result.stdout == '1'


def read_stream(response, structured=False, on_text=None):
    """SSE is successful only after response.completed, including late failures."""
    chunks, event_lines, total = [], [], 0
    completed_items = {}
    deadline = time.monotonic() + 180
    while True:
        if time.monotonic() > deadline:
            raise ChatGPTError('incomplete_response')
        line = response.readline(1024 * 1024 + 1)
        if not line:
            break
        total += len(line)
        if len(line) > 1024 * 1024 or total > 16 * 1024 * 1024:
            raise ChatGPTError('incomplete_response')
        if line.rstrip(b'\r\n') == b'':
            if not event_lines:
                continue
            try:
                event = json.loads('\n'.join(event_lines))
            except (ValueError, UnicodeError):
                raise ChatGPTError('incomplete_response') from None
            event_lines = []
            if not isinstance(event, dict):
                raise ChatGPTError('incomplete_response')
            kind = event.get('type')
            if kind == 'response.output_text.delta':
                delta = event.get('delta')
                if not isinstance(delta, str):
                    raise ChatGPTError('incomplete_response')
                chunks.append(delta)
                if on_text:on_text(delta)
            elif kind == 'response.output_item.done':
                index, item = event.get('output_index'), event.get('item')
                if type(index) is not int or not 0 <= index < 1000 or not isinstance(item, dict):
                    raise ChatGPTError('response_format_error')
                if index in completed_items and completed_items[index] != item:
                    raise ChatGPTError('response_format_error')
                completed_items[index] = item
            elif kind in ('response.failed', 'response.incomplete', 'error'):
                raise provider_error(event.get('response', event))
            elif kind == 'response.completed':
                complete = event.get('response', {})
                if complete.get('status') != 'completed':
                    raise ChatGPTError('incomplete_response')
                # Final output is authoritative when present. Some streams put
                # completed items in output_item.done rather than repeating them.
                items = complete.get('output', [])
                if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
                    raise ChatGPTError('response_format_error')
                if not items:
                    items = [completed_items[i] for i in sorted(completed_items)]
                output = []
                for item in items:
                    if item.get('type') == 'message':
                        for part in item.get('content', []):
                            if part.get('type') == 'output_text':
                                output.append(part.get('text', ''))
                            elif part.get('type') == 'refusal':
                                output.append(part.get('refusal', ''))
                text = ''.join(output or chunks).strip()
                if structured:
                    calls = [item for item in items if item.get('type') == 'function_call']
                    for call in calls:
                        if not all(isinstance(call.get(k), str) and call[k] for k in ('call_id', 'name', 'arguments')) or len(call['arguments']) > 40000:
                            raise ChatGPTError('tool_response_invalid')
                    if not text and not calls:
                        raise ChatGPTError('tool_response_empty')
                    return {'text': text, 'output': items, 'calls': calls, 'usage':complete.get('usage') if isinstance(complete.get('usage'),dict) else {}}
                if not text:
                    raise ChatGPTError('incomplete_response')
                return text
        elif line.startswith(b'data:'):
            try:
                event_lines.append(line[5:].strip().decode('utf-8'))
            except UnicodeError:
                raise ChatGPTError('incomplete_response') from None
    raise ChatGPTError('stream_ended' if structured else 'incomplete_response')


class ChatGPT:
    """One Windows account connection. All credential operations share one lock."""
    def __init__(self, data, on_connected=lambda: None):
        self.directory = Path(data) / 'chatgpt'
        self.path = self.directory / 'connection.dpapi'
        self.lock = threading.RLock()
        self.requests_lock=threading.Lock();self.requests={}
        self.cancelled = threading.Event()
        self.connecting = False
        self.on_connected = on_connected
        self.models_cache = []
        self.catalog_at = 0
        self.discovery_cache = None
        self.record = {}
        self.error = None
        self.supported = os.name == 'nt' and bool(os.getenv('TREN_NODE') or shutil.which('node'))
        if self.path.exists():
            try:
                if self.path.is_symlink() or self.directory.is_symlink() or self.path.stat().st_size > 1024 * 1024:
                    raise ChatGPTError('storage_unavailable')
                self.record = json.loads(protected_bytes(self.path.read_bytes(), True).decode('utf-8'))
                if not isinstance(self.record, dict) or self.record.get('format') != 1:
                    raise ChatGPTError('storage_unavailable')
            except Exception:
                self.error = ChatGPTError('storage_unavailable')

    def state(self):
        # Cached DTO; never hand credentials, ID tokens or browser URLs to callers.
        return {'supported': self.supported,
                'status': 'connecting' if self.connecting else self.record.get('status', 'disconnected'),
                'sharing': SHARING in self.record.get('scopes', []),
                'identity': self.record.get('identity', {}), 'models': self.models_cache,
                'error': str(self.error) if self.error else None}

    def _save(self):
        if self.error and self.error.code == 'storage_unavailable':
            raise self.error
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.directory.is_symlink() or self.path.is_symlink():
            raise ChatGPTError('storage_unavailable')
        raw = protected_bytes(json.dumps(self.record).encode('utf-8'))
        tmp = self.directory / ('connection-' + secrets.token_hex(12) + '.tmp')
        try:
            with tmp.open('xb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except OSError:
            raise ChatGPTError('storage_unavailable') from None
        finally:
            tmp.unlink(missing_ok=True)

    def _open(self, url, data=None, token=None, form=False, timeout=30):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.fragment or
                (parsed.netloc != 'auth.openai.com' and not url.startswith(RESOURCE + '/'))):
            raise ChatGPTError('network_error')
        headers = {'Accept': 'application/json'}
        if token:
            if parsed.netloc != 'api.openai.com':
                raise ChatGPTError('network_error')
            headers['Authorization'] = 'Bearer ' + token
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
            data = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        request = urllib.request.Request(url, data=data, headers=headers)
        # No proxy credentials/environment API keys and no credential-carrying redirects.
        try:
            return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)
        except urllib.error.HTTPError as e:
            try:
                error = provider_error(json.loads(e.read(65536)))
            except Exception:
                error = ChatGPTError('provider_error')
            raise error from None
        except (OSError, urllib.error.URLError):
            raise ChatGPTError('network_error') from None

    def _json(self, url, data=None, token=None, form=False):
        with self._open(url, data, token, form) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ChatGPTError('provider_error')
        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except ValueError:
            raise ChatGPTError('provider_error') from None

    def _discovery(self):
        if not self.discovery_cache:
            config = self._json(ISSUER + '/.well-known/openid-configuration')
            if config.get('issuer') != ISSUER:
                raise ChatGPTError('identity_unavailable')
            for key in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
                value = config.get(key, '')
                if not isinstance(value, str) or urllib.parse.urlsplit(value).netloc != 'auth.openai.com' or not value.startswith(ISSUER + '/'):
                    raise ChatGPTError('identity_unavailable')
            self.discovery_cache = config
        return self.discovery_cache

    def _identity(self, token, client_id, nonce=None, at=None):
        try:
            parts = token.split('.')
            if len(parts) != 3 or len(token) > 65536:
                raise ValueError()
            header, claims = [json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4))) for p in parts[:2]]
            now = time.time() if at is None else at
            aud = claims['aud']
            if (header.get('alg') != 'RS256' or header.get('crit') or header.get('b64') is False or
                not isinstance(header.get('kid'), str) or claims['iss'] != ISSUER or
                not isinstance(claims['sub'], str) or not claims['sub'] or
                not isinstance(claims['exp'], (float, int)) or not math.isfinite(claims['exp']) or claims['exp'] < now - 5 or
                not isinstance(claims['iat'], (float, int)) or not math.isfinite(claims['iat']) or claims['iat'] > now + 5 or
                (claims.get('nbf', 0) > now + 5) or
                not (aud == client_id or isinstance(aud, list) and client_id in aud) or
                (claims.get('azp', client_id) != client_id) or
                (isinstance(aud, list) and len(aud) > 1 and claims.get('azp') != client_id) or
                (nonce is not None and claims.get('nonce') != nonce)):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ChatGPTError('invalid_identity') from None
        try:
            keys = self._json(self._discovery()['jwks_uri']).get('keys', [])
            choices = [key for key in keys if isinstance(key, dict) and key.get('kid') == header['kid'] and
                       key.get('kty') == 'RSA' and key.get('use', 'sig') == 'sig' and key.get('alg', 'RS256') == 'RS256']
            if len(choices) != 1:
                raise ChatGPTError('identity_unavailable')
        except ChatGPTError:
            raise ChatGPTError('identity_unavailable') from None
        if not verify_signature(token, choices[0]):
            raise ChatGPTError('invalid_identity')
        return claims['sub'], {key: claims[key][:200] for key in ('name', 'email') if isinstance(claims.get(key), str)}

    def _finish_pending(self):
        pending = self.record['pending']
        data, received = pending['data'], pending['received']
        refresh = pending.get('refresh', False)
        scope = data.get('scope', ' '.join(self.record.get('scopes', [])) if refresh else None)
        if not isinstance(scope, str):
            raise ChatGPTError('provider_error')
        scopes = scope.split()
        needs_credentials = refresh or SHARING in scopes or 'offline_access' in scopes or 'access_token' in data
        if needs_credentials and (not isinstance(data.get('access_token'), str) or not data['access_token'] or
                str(data.get('token_type', '')).lower() != 'bearer' or
                not isinstance(data.get('expires_in'), (int, float)) or not math.isfinite(data['expires_in']) or data['expires_in'] <= 0 or
                ('offline_access' in scopes and (not isinstance(data.get('refresh_token'), str) or not data['refresh_token']))):
            raise ChatGPTError('provider_error')
        if 'id_token' in data or not refresh:
            sub, identity = self._identity(data.get('id_token'), self.record['client_id'], pending.get('nonce'), received)
            if self.record.get('subject') and sub != self.record['subject']:
                raise ChatGPTError('invalid_identity')
            self.record.update(subject=sub, identity=identity)
        self.record.update(status='connected', scopes=scopes, access_token=data.get('access_token'),
                           expires=received + data.get('expires_in', 0),
                           refresh_token=data.get('refresh_token', self.record.get('refresh_token')),
                           earliest_refresh=data.get('earliest_refresh_at'))
        self.record.pop('pending')
        self._save()

    def _credentials(self):
        if self.connecting:
            raise ChatGPTError('connection_busy')
        if self.error and self.error.code == 'storage_unavailable':
            raise self.error
        if 'pending' in self.record:
            self._finish_pending()
        if self.record.get('status') != 'connected':
            raise ChatGPTError('sign_in_required')
        if SHARING not in self.record.get('scopes', []):
            raise ChatGPTError('sharing_not_enabled')
        if self.record.get('expires', 0) < time.time() + 60:
            earliest = self.record.get('earliest_refresh')
            if isinstance(earliest, str):
                try:
                    from datetime import datetime
                    earliest = datetime.fromisoformat(earliest.replace('Z', '+00:00')).timestamp()
                except ValueError:
                    earliest = 0
            if not isinstance(earliest, (float, int)) or earliest <= time.time():
                if not self.record.get('refresh_token'):
                    raise ChatGPTError('invalid_grant')
                try:
                    data = self._json(self._discovery()['token_endpoint'], {'grant_type': 'refresh_token',
                        'client_id': self.record['client_id'], 'refresh_token': self.record['refresh_token'],
                        'resource': RESOURCE}, form=True)
                except ChatGPTError as e:
                    if e.code == 'invalid_grant':
                        self.record['status'] = 'reauth_required'
                        self._save()
                    raise
                # Commit the rotating credential before remote key retrieval.
                self.record['pending'] = {'data': data, 'received': time.time(), 'refresh': True}
                self._save()
                self._finish_pending()
        if SHARING not in self.record.get('scopes', []):
            raise ChatGPTError('sharing_not_enabled')
        return self.record['access_token']

    def models(self):
        with self.lock:
            try:
                body = self._json(RESOURCE + '/models', token=self._credentials())
                if not isinstance(body.get('models'), list):
                    raise ChatGPTError('provider_error')
                result = []
                for item in body['models']:
                    if not isinstance(item, dict) or item.get('visibility') != 'list':
                        continue
                    if not all(isinstance(item.get(k), str) and 0 < len(item[k].strip()) <= 200 for k in ('slug', 'display_name')):
                        raise ChatGPTError('provider_error')
                    result.append({'slug': item['slug'], 'display_name': item['display_name']})
                self.models_cache = result
                self.catalog_at = time.time()
                self.error = None
                return result
            except ChatGPTError as e:
                self.error = e
                raise

    def respond(self, messages, instructions, model=''):
        return self.respond_turn(messages, instructions, model)

    def respond_turn(self, messages, instructions, model='', tools=None, on_text=None):
        response=None
        try:
            # Refresh/catalog writes are serialized. Independent agent response streams are not.
            with self.lock:
                if not self.models_cache or time.time()-self.catalog_at>300:self.models()
                choices=[m['slug'] for m in self.models_cache];selected=model or (choices[0] if choices else '')
                if selected not in choices:raise ChatGPTError('provider_error')
                token=self._credentials()
            body={'model':selected,'input':messages,'instructions':instructions,'store':False,'stream':True}
            if tools is not None:body.update(tools=tools,parallel_tool_calls=False,include=['reasoning.encrypted_content'])
            with self._open(RESOURCE+'/responses',body,token=token,timeout=60) as response:
                with self.requests_lock:self.requests[response]=threading.current_thread().name
                try:result=read_stream(response,structured=tools is not None,on_text=on_text)
                finally:
                    with self.requests_lock:self.requests.pop(response,None)
            with self.lock:self.error=None
            return result
        except ChatGPTError as error:
            if getattr(response,'veyra_cancelled',False):raise InterruptedError('Response cancelled.') from None
            with self.lock:self.error=error
            raise
        except OSError:
            if getattr(response,'veyra_cancelled',False):raise InterruptedError('Response cancelled.') from None
            with self.lock:self.error=ChatGPTError('network_error')
            raise self.error from None
        except (ValueError,TypeError,AttributeError):
            if getattr(response,'veyra_cancelled',False):raise InterruptedError('Response cancelled.') from None
            with self.lock:self.error=ChatGPTError('response_format_error')
            raise self.error from None

    def cancel_requests(self,tag=None):
        with self.requests_lock:responses=[r for r,name in self.requests.items() if tag is None or name==tag]
        for response in responses:
            response.veyra_cancelled=True
            try:
                sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
                if sock:sock.shutdown(__import__('socket').SHUT_RDWR)
                response.close()
            except OSError:pass

    def start_sign_in(self):
        with self.lock:
            if self.connecting:
                raise ChatGPTError('connection_busy')
            if not self.supported:
                raise RuntimeError('ChatGPT sign-in currently needs Windows and the existing Node.js installation.')
            if self.error and self.error.code == 'storage_unavailable':
                raise self.error
            self.cancelled.clear()
            self.connecting = True
            self.error = None
            threading.Thread(target=self._sign_in, daemon=True).start()
        return self.state()

    def cancel_sign_in(self):
        self.cancelled.set()
        return self.state()

    def _sign_in(self):
        server = None
        try:
            config = self._discovery()
            state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
            callback = {}
            saved_client = self.record.get('client_id')
            manager = self
            class Callback(http.server.BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass  # URL contains one-time secrets. Never log it.
                def setup(self):
                    super().setup()
                    self.connection.settimeout(5)
                def do_GET(self):
                    parsed = urllib.parse.urlsplit(self.path)
                    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
                    code = 400
                    body = b'Invalid sign-in callback. Return to the original sign-in tab.'
                    if (len(self.headers.get_all('Host', [])) == 1 and self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}' and
                            not parsed.scheme and not parsed.netloc and parsed.path == '/auth/callback' and
                            not callback and not manager.cancelled.is_set() and
                            len(query.get('state', [])) == 1 and
                            secrets.compare_digest(query['state'][0].encode('utf-8'), state.encode('ascii'))):
                        client = query.get('client_id', [saved_client])[0]
                        if 'error' in query:
                            callback['error'] = 'access_denied'
                        elif (len(query.get('code', [])) == 1 and query['code'][0] and
                              len(query.get('client_id', [])) <= 1 and isinstance(client, str) and
                              re.fullmatch(r'[A-Za-z0-9_-]{1,200}', client) and client != 'dynamic_agent_client' and
                              (not saved_client or saved_client == client)):
                            callback.update(code=query['code'][0], client_id=client)
                        else:
                            callback['error'] = 'provider_error'
                        code = 200
                        script = 'history.replaceState(null,"","/auth/complete");'
                        script_hash = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                        self.send_response(code)
                        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'sha256-" + script_hash + "'; frame-ancestors 'none'; base-uri 'none'")
                        body = ('<!doctype html><meta charset="utf-8"><title>VEYRA sign-in</title><h1>Return to VEYRA</h1><p>VEYRA is verifying your connection. You can close this tab.</p><script>' + script + '</script>').encode()
                    else:
                        self.send_response(code)
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
            server = http.server.HTTPServer(('127.0.0.1', 0), Callback)
            server.timeout = .25
            redirect = f'http://127.0.0.1:{server.server_port}/auth/callback'
            with self.lock:
                self.record.setdefault('format', 1)
                self.record.setdefault('host_id', 'urn:uuid:' + str(uuid.uuid4()))
                self._save()
            params = {'client_id': saved_client or 'dynamic_agent_client', 'response_type': 'code',
                      'redirect_uri': redirect, 'scope': SCOPES, 'resource': RESOURCE,
                      'state': state, 'nonce': nonce, 'code_challenge_method': 'S256',
                      'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(),
                      'ext_agent_host_id': self.record['host_id'], 'prompt': 'consent'}
            if not saved_client:
                params['agent_name_hint'] = 'VEYRA'
            if not webbrowser.open(config['authorization_endpoint'] + '?' + urllib.parse.urlencode(params)):
                raise ChatGPTError('provider_error')
            deadline = time.monotonic() + 600
            while not callback and not self.cancelled.is_set() and time.monotonic() < deadline:
                server.handle_request()
            if self.cancelled.is_set() or not callback:
                raise ChatGPTError('cancelled')
            if 'error' in callback:
                raise ChatGPTError(callback['error'])
            with self.lock:
                self.record['client_id'] = callback['client_id']
                self._save()  # Registration survives a failed one-time exchange.
                if self.cancelled.is_set():
                    raise ChatGPTError('cancelled')
                data = self._json(config['token_endpoint'], {'grant_type': 'authorization_code',
                    'client_id': callback['client_id'], 'code': callback['code'], 'code_verifier': verifier,
                    'redirect_uri': redirect, 'resource': RESOURCE}, form=True)
                self.record['pending'] = {'data': data, 'received': time.time(), 'nonce': nonce}
                self._save()
                self._finish_pending()
                self.models_cache = []
                if SHARING in self.record.get('scopes', []):
                    self.on_connected()
                else:
                    raise ChatGPTError('sharing_not_enabled')
        except ChatGPTError as e:
            self.error = e
        except Exception:
            self.error = ChatGPTError('provider_error')
        finally:
            if server:
                server.server_close()
            self.connecting = False

    def disconnect(self):
        with self.lock:
            if self.connecting:
                raise ChatGPTError('connection_busy')
            if self.error and self.error.code == 'storage_unavailable':
                raise self.error
            remote_error = False
            token = self.record.get('pending', {}).get('data', {}).get('refresh_token') or self.record.get('refresh_token')
            try:
                endpoint = self._discovery().get('revocation_endpoint') if token else None
                if token and endpoint:
                    with self._open(endpoint, {'client_id': self.record['client_id'],
                                    'token': token, 'token_type_hint': 'refresh_token'}, form=True):
                        pass
                elif token:
                    remote_error = True
            except Exception:
                remote_error = True
            self.record = {k: v for k, v in self.record.items() if k in ('format', 'client_id', 'host_id', 'subject', 'identity')}
            self.record['status'] = 'disconnected'
            self._save()
            self.models_cache = []
            self.error = None
            return {'ok': True, 'remote_revoked': not remote_error,
                    'notice': 'Local credentials removed. Remote revocation failed; disconnect VEYRA in ChatGPT Settings.' if remote_error else None}
