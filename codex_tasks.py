"""Single-worker durable Codex queue. No shell, token access, or sandbox bypass."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import subprocess
import threading
import time


def redact(text):
    text = re.sub(r'(?i)(bearer\s+)[\w.\-]+', r'\1[redacted]', str(text))
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b', '[redacted]', text)
    return re.sub(r'(?i)((?:api[_-]?key|access_token|refresh_token|password|secret)\s*["\x27]?\s*[:=]\s*)[^\s,}]+', r'\1[redacted]', text)


def cli_command():
    executable = shutil.which('codex.exe') or shutil.which('codex') or shutil.which('codex.cmd')
    if not executable:
        raise RuntimeError('Codex CLI not found. Restart TREN after confirming codex login status in your normal terminal.')
    if Path(executable).suffix.lower() in ('.cmd', '.bat', '.ps1'):
        # npm's Windows shim cannot be safely invoked with arbitrary arguments.
        # Call its installed JS entry through node, with shell=False instead.
        script = Path(executable).parent / 'node_modules' / '@openai' / 'codex' / 'bin' / 'codex.js'
        node = shutil.which('node.exe') or shutil.which('node')
        if not script.is_file() or not node:
            raise RuntimeError('Cannot resolve the installed npm Codex entry point. No shell fallback is used.')
        return [node, str(script)]
    return [executable]


def process_options():
    if os.name == 'nt':
        return {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {'start_new_session': True}


def child_env():
    env = os.environ.copy()
    # Reuse CLI login, never accidentally switch to separately billed API auth.
    for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
        env.pop(key, None)
    return env


def health():
    try:
        cmd = cli_command()
        result = subprocess.run(cmd + ['login', 'status'], capture_output=True, text=True,
                                timeout=15, env=child_env(), **process_options())
        text = result.stdout + result.stderr
        chatgpt = result.returncode == 0 and 'chatgpt' in text.lower()
        return {'detected': True, 'authenticated': chatgpt, 'provider': 'codex',
                'message': 'ChatGPT login ready' if chatgpt else 'Run codex login and choose ChatGPT. API-key login is not used by TREN.'}
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return {'detected': False, 'authenticated': False, 'message': redact(exc)}


def stop_process(proc):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True,
                       timeout=10, **process_options())
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


class Manager:
    def __init__(self, db, data, gaming):
        self.db, self.data, self.gaming = db, Path(data), gaming
        self.root = (self.data / 'projects').resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.active = {}
        self.closed = threading.Event()
        with self.db() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS coding_jobs(
                id INTEGER PRIMARY KEY, prompt TEXT, project TEXT, mode TEXT, expected TEXT,
                timeout INTEGER, status TEXT, output TEXT DEFAULT '', artifacts TEXT DEFAULT '[]',
                exit_code INTEGER, created REAL, finished REAL)''')
            c.execute("UPDATE coding_jobs SET status='interrupted',finished=? WHERE status IN ('queued','running','cancelling')", (time.time(),))
        self.worker = None

    def start(self):
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def project(self, name, create=False):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', name):
            raise ValueError('Project name must contain only letters, numbers, hyphens and underscores (1–64 characters).')
        path = self.root / name
        if create:
            path.mkdir(exist_ok=True)
        if not path.is_dir() or path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError('Invalid project directory.')
        return path.resolve()

    def file(self, project, relative):
        root = self.project(project)
        if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
            raise ValueError('Use a relative file path with forward slashes.')
        path = root / relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('File must stay inside the project.')
        if any(part.startswith('.') or part.lower() in ('node_modules', '__pycache__') for part in Path(relative).parts):
            raise ValueError('Hidden and dependency files are excluded.')
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
            raise ValueError('Links outside the project are excluded.')
        return resolved

    def submit(self, body):
        prompt = body.get('prompt')
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 6000:
            raise ValueError('Provide a coding request (1–6000 characters).')
        project = body.get('project', 'default')
        self.project(project, create=True)
        mode = body.get('mode', 'read-only')
        if mode not in ('read-only', 'workspace-write'):
            raise ValueError('Unsupported permission mode.')
        # Every write is explicitly confirmed, rather than trying to guess destructive intent.
        if mode == 'workspace-write' and body.get('confirmed') is not True:
            raise ValueError('Confirm project edits before submitting a write task.')
        expected = body.get('expected', [])
        if not isinstance(expected, list) or len(expected) > 30:
            raise ValueError('Provide up to 30 expected file paths.')
        for file in expected:
            self.file(project, file)
        timeout = body.get('timeout', 900)
        if type(timeout) is not int or not 10 <= timeout <= 3600:
            raise ValueError('Timeout must be 10–3600 seconds.')
        with self.lock, self.db() as c:
            if c.execute("SELECT COUNT(*) FROM coding_jobs WHERE status IN ('queued','running','cancelling')").fetchone()[0] >= 10:
                raise ValueError('Queue full. Wait or cancel a task.')
            return c.execute('INSERT INTO coding_jobs(prompt,project,mode,expected,timeout,status,created) VALUES(?,?,?,?,?,?,?)',
                             (redact(prompt.strip()), project, mode, json.dumps(expected), timeout, 'queued', time.time())).lastrowid

    def jobs(self):
        with self.db() as c:
            return [dict(r) for r in c.execute('SELECT * FROM coding_jobs ORDER BY id DESC LIMIT 50')]

    def update(self, jid, **fields):
        with self.db() as c:
            c.execute('UPDATE coding_jobs SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', (*fields.values(), jid))

    def append(self, jid, text):
        text = redact(text)[:12000]
        with self.db() as c:
            c.execute('UPDATE coding_jobs SET output=substr(output || ?, -64000) WHERE id=?', (text+'\n', jid))

    def cancel(self, jid):
        with self.lock, self.db() as c:
            row = c.execute('SELECT status FROM coding_jobs WHERE id=?', (jid,)).fetchone()
            if not row:
                raise ValueError('Task not found.')
            if row[0] == 'queued':
                c.execute("UPDATE coding_jobs SET status='cancelled',finished=? WHERE id=?", (time.time(), jid))
            elif jid in self.active:
                self.active[jid].set()
                c.execute("UPDATE coding_jobs SET status='cancelling' WHERE id=?", (jid,))

    def snapshot(self, project):
        root = self.project(project)
        result = {}
        visited = 0
        for directory, folders, files in os.walk(root, followlinks=False):
            folders[:] = [f for f in folders if not f.startswith('.') and f not in ('node_modules', '__pycache__') and not (Path(directory)/f).is_symlink()]
            for name in files:
                visited += 1
                if visited > 2000:
                    return result
                path = Path(directory)/name
                relative = path.relative_to(root).as_posix()
                try:
                    safe = self.file(project, relative)
                    if safe.is_file() and safe.stat().st_size <= 5_000_000:
                        result[relative] = hashlib.sha256(safe.read_bytes()).hexdigest()
                except (ValueError, OSError):
                    continue
        return result

    def loop(self):
        while not self.closed.is_set():
            if not self.gaming():
                with self.lock, self.db() as c:
                    row = c.execute("SELECT * FROM coding_jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
                    if row:
                        job = dict(row)
                        self.active[job['id']] = threading.Event()
                        c.execute("UPDATE coding_jobs SET status='running' WHERE id=?", (job['id'],))
                if row:
                    self.execute(job)
            self.closed.wait(.5)

    def execute(self, job):
        jid = job['id']
        proc = None
        status, code = 'failed', None
        try:
            if not health()['authenticated']:
                raise RuntimeError('ChatGPT Codex login unavailable. Check Coding → Check Codex. No API fallback or automatic retry was attempted.')
            root = self.project(job['project'])
            before = self.snapshot(job['project'])
            args = cli_command() + ['-a', 'never', 'exec', '--json', '--sandbox', job['mode'],
                                    '--skip-git-repo-check', '-C', str(root), '-']
            # never denies escalation; it does not bypass the sandbox. Stdin keeps user text out of command construction.
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='utf-8', errors='replace', cwd=str(root), env=child_env(), **process_options())
            events = queue.Queue(maxsize=256)
            def reader(stream, kind):
                try:
                    for line in iter(lambda: stream.readline(65536), ''):
                        while not self.closed.is_set():
                            try:
                                events.put((kind, line), timeout=.2)
                                break
                            except queue.Full:
                                continue
                finally:
                    stream.close()
            readers = [threading.Thread(target=reader, args=(stream, kind), daemon=True)
                       for stream, kind in ((proc.stdout, 'event'), (proc.stderr, 'stderr'))]
            for thread in readers:
                thread.start()
            proc.stdin.write('Work only in this project. Do not deploy, publish, purchase, access credentials, or modify files outside it. '
                             'If a high-impact action is needed, describe it instead of doing it.\n'
                             'Expected output files: ' + ', '.join(json.loads(job['expected'])) +
                             '\nCreate or update requested files on disk and verify them before claiming success.\n\n' + job['prompt'])
            proc.stdin.close()
            deadline = time.monotonic() + job['timeout']
            failed = False
            while proc.poll() is None or any(t.is_alive() for t in readers) or not events.empty():
                if self.active[jid].is_set() or self.closed.is_set():
                    status = 'cancelled'
                    stop_process(proc)
                    break
                if time.monotonic() >= deadline:
                    status = 'timed_out'
                    stop_process(proc)
                    break
                try:
                    kind, line = events.get(timeout=.1)
                except queue.Empty:
                    continue
                if kind == 'stderr':
                    self.append(jid, line)
                    continue
                try:
                    event = json.loads(line)
                    typ = event.get('type', 'progress')
                    item = event.get('item', {})
                    if typ in ('turn.failed', 'error'):
                        failed = True
                        self.append(jid, json.dumps(event))
                    elif item.get('type') == 'agent_message':
                        self.append(jid, item.get('text', ''))
                    elif item.get('type') == 'command_execution':
                        self.append(jid, item.get('command', '') + '\n' + item.get('aggregated_output', '') + '\nStatus: ' + item.get('status', '') + ' · exit: ' + str(item.get('exit_code')))
                    elif typ == 'turn.completed':
                        self.append(jid, 'Turn complete. Usage: '+json.dumps(event.get('usage', {})))
                    else:
                        self.append(jid, typ + (' · '+item.get('type', '') if item else ''))
                except (ValueError, TypeError, AttributeError):
                    self.append(jid, line)
            code = proc.poll()
            if status not in ('cancelled', 'timed_out'):
                status = 'completed' if code == 0 and not failed else 'failed'
            after = self.snapshot(job['project'])
            changed = [p for p, digest in after.items() if before.get(p) != digest]
            expected = json.loads(job['expected'])
            missing = [p for p in expected if not self.file(job['project'], p).is_file()]
            if status == 'completed' and missing:
                status = 'artifact_missing'
                self.append(jid, 'Expected files missing: '+', '.join(missing))
            self.update(jid, artifacts=json.dumps(sorted(set(changed + [p for p in expected if p not in missing]))))
            if status == 'failed':
                self.append(jid, 'Task failed. Check authentication, plan usage limits, and sandbox errors above. No automatic retry or API billing fallback.')
        except Exception as exc:
            self.append(jid, str(exc))
        finally:
            if proc and proc.poll() is None:
                stop_process(proc)
            self.update(jid, status=status, exit_code=code, finished=time.time())
            with self.lock:
                self.active.pop(jid, None)

    def close(self):
        self.closed.set()
        with self.lock:
            for event in self.active.values():
                event.set()
        if self.worker:
            self.worker.join(timeout=15)
