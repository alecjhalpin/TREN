"""Bounded, persistent Node tool-worker transport. No network listener or renderer secrets."""
import json,os,queue,secrets,subprocess,threading,time
from pathlib import Path
import codex_tasks as ct

class ToolBridge:
    def __init__(self,data,worker=None):
        self.data=Path(data);self.worker=Path(worker or Path(__file__).parent/'runtime'/'worker.mjs')
        self.lock=threading.RLock();self.proc=None;self.pending={};self.methods={};self.closed=False
    def start(self):
        with self.lock:
            if self.closed:raise RuntimeError('Tool worker is stopped.')
            if self.proc and self.proc.poll() is None:return
            node=os.getenv('TREN_NODE') or __import__('shutil').which('node')
            if not node:raise RuntimeError('Install the VEYRA desktop runtime before using browser, MCP or voice.')
            env=ct.child_env();env['VEYRA_DATA']=str(self.data)
            self.proc=subprocess.Popen([node,str(self.worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',env=env,**ct.process_options())
            proc=self.proc
            def read():
                try:
                    for line in iter(lambda:proc.stdout.readline(16*1024*1024+1),''):
                        if len(line)>16*1024*1024:break
                        try:
                            reply=json.loads(line)
                            with self.lock:target=self.pending.get(reply.get('id'))
                            if target:target.put_nowait(reply)
                        except (ValueError,queue.Full):pass
                finally:
                    proc.stdout.close()
                    with self.lock:
                        targets=list(self.pending.values()) if self.proc is proc else []
                        for target in targets:
                            try:target.put_nowait({'error':'Tool worker ended; inspect actions before retrying.'})
                            except queue.Full:pass
            threading.Thread(target=read,daemon=True).start()
    def send(self,packet):
        with self.lock:
            if not self.proc or self.proc.poll() is not None:raise RuntimeError('Tool worker ended.')
            self.proc.stdin.write(json.dumps(packet,separators=(',',':'))+'\n');self.proc.stdin.flush()
    def call(self,method,payload=None,cancelled=lambda:False,timeout=120):
        self.start();rid=secrets.token_hex(16);target=queue.Queue(1)
        with self.lock:self.pending[rid]=target;self.methods[rid]=method
        try:
            self.send({'id':rid,'method':method,'params':payload or {}})
            end=time.monotonic()+timeout
            while True:
                if cancelled() or time.monotonic()>end:
                    self.send({'id':secrets.token_hex(16),'method':'cancel','params':{'request_id':rid}})
                    raise InterruptedError('Tool cancelled; inspect its recorded effects before retrying.')
                try:reply=target.get(timeout=.1)
                except queue.Empty:continue
                if reply.get('error'):raise RuntimeError(str(reply['error'])[:3000])
                return reply.get('result')
        finally:
            with self.lock:self.pending.pop(rid,None);self.methods.pop(rid,None)
    def cancel_method(self,method):
        with self.lock:
            for rid,kind in list(self.methods.items()):
                if kind==method:self.send({'id':secrets.token_hex(16),'method':'cancel','params':{'request_id':rid}})
    def stop_all(self):
        # Terminate the whole local process tree, including browser/MCP children and local inference.
        with self.lock:
            proc=self.proc
            if proc and proc.poll() is None:
                try:self.send({'id':secrets.token_hex(16),'method':'stop_all','params':{}})
                except (OSError,RuntimeError):pass
                try:ct.stop_process(proc)
                except (OSError,subprocess.SubprocessError):pass
            if proc and proc.stdin:
                try:proc.stdin.close()
                except OSError:pass
            self.proc=None
            for target in self.pending.values():
                try:target.put_nowait({'error':'Tool worker stopped; inspect actions before retrying.'})
                except queue.Full:pass
    def close(self):
        with self.lock:
            self.closed=True
            self.stop_all()
            if self.proc:
                try:ct.stop_process(self.proc)
                except (OSError,subprocess.SubprocessError):pass
                self.proc=None
