'''Bounded read-only Codex App Server bridge for HORUS.'''
from __future__ import annotations
import json, os, shutil, subprocess, threading, time
from pathlib import Path
from typing import Any

class CodexBridgeError(RuntimeError): pass

class CodexAppServerBridge:
    def __init__(self, allowed_roots=None, executable=None, timeout=90.0):
        roots = allowed_roots if allowed_roots is not None else [x for x in os.environ.get('HORUS_ALLOWED_WORKSPACES','').split(os.pathsep) if x]
        self.allowed_roots = [Path(x).expanduser().resolve() for x in roots]
        self.executable = executable or os.environ.get('HORUS_CODEX_BIN') or shutil.which('codex')
        self.timeout = timeout

    def status(self):
        if not self.executable: return {'available':False,'authenticated':False,'reason':'Codex CLI not found on PATH'}
        try:
            version = subprocess.run([self.executable,'--version'],capture_output=True,text=True,timeout=8)
            login = subprocess.run([self.executable,'login','status'],capture_output=True,text=True,timeout=8)
            detail = (login.stdout+' '+login.stderr).strip()
            authenticated = login.returncode == 0 and any(x in detail.lower() for x in ('logged in','signed in','authenticated','chatgpt'))
            return {'available':version.returncode == 0,'authenticated':authenticated,'version':(version.stdout or version.stderr).strip().splitlines()[:1],'detail':detail[:300]}
        except (OSError,subprocess.TimeoutExpired) as exc:
            return {'available':False,'authenticated':False,'reason':str(exc)}

    def resolve_workspace(self, workspace):
        if not self.allowed_roots: raise PermissionError('No HORUS_ALLOWED_WORKSPACES roots configured')
        target = Path(workspace).expanduser().resolve()
        if not any(target == root or root in target.parents for root in self.allowed_roots): raise PermissionError('Workspace outside allow-list')
        if not target.is_dir(): raise FileNotFoundError(str(target))
        return target

    @staticmethod
    def extract_text(value: Any) -> str:
        if isinstance(value,str): return value
        if isinstance(value,list): return ''.join(CodexAppServerBridge.extract_text(x) for x in value)
        if not isinstance(value,dict): return ''
        kind = str(value.get('type') or value.get('kind') or '').replace('-','').replace('_','').lower()
        role = str(value.get('role') or value.get('speaker') or '').lower()
        if kind in {'agentmessage','assistantmessage','outputtext','text'} or role in {'assistant','agent'}:
            for key in ('text','content','parts','items','output'):
                if key in value:
                    found = CodexAppServerBridge.extract_text(value[key])
                    if found: return found
        for key in ('item','turn','items','output','content','parts','itemsView'):
            if key in value:
                found = CodexAppServerBridge.extract_text(value[key])
                if found: return found
        return ''

    def ask_read_only(self, workspace, prompt):
        if not self.executable: raise CodexBridgeError('Codex CLI not found')
        if not prompt or len(prompt) > 32000: raise ValueError('Prompt must contain 1..32000 characters')
        cwd = self.resolve_workspace(workspace)
        proc = subprocess.Popen([self.executable,'app-server'],cwd=str(cwd),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',bufsize=1)
        next_id = 1
        def send(payload):
            proc.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n'); proc.stdin.flush()
        def receive(predicate, deadline):
            while time.monotonic() < deadline:
                line = proc.stdout.readline()
                if not line: raise CodexBridgeError('Codex App Server closed stdout')
                try: msg = json.loads(line)
                except json.JSONDecodeError: continue
                if 'id' in msg and msg.get('method'):
                    send({'id':msg['id'],'result':{'decision':'decline'}})
                    continue
                if predicate(msg): return msg
            raise TimeoutError('Timed out waiting for Codex App Server')
        try:
            rid=next_id; next_id+=1
            send({'id':rid,'method':'initialize','params':{'clientInfo':{'name':'horus_autonomous_agent','title':'HORUS','version':'1.3.0'}}})
            response=receive(lambda m:m.get('id')==rid,time.monotonic()+self.timeout)
            if response.get('error'): raise CodexBridgeError(str(response['error']))
            send({'method':'initialized','params':{}})
            rid=next_id; next_id+=1
            send({'id':rid,'method':'thread/start','params':{'approvalPolicy':'on-request','sandbox':'read-only','cwd':str(cwd)}})
            response=receive(lambda m:m.get('id')==rid,time.monotonic()+self.timeout)
            if response.get('error'): raise CodexBridgeError(str(response['error']))
            thread_id=((response.get('result') or {}).get('thread') or {}).get('id')
            if not thread_id: raise CodexBridgeError('No thread id returned')
            rid=next_id; next_id+=1
            send({'id':rid,'method':'turn/start','params':{'threadId':thread_id,'input':[{'type':'text','text':prompt}]}})
            response=receive(lambda m:m.get('id')==rid,time.monotonic()+self.timeout)
            if response.get('error'): raise CodexBridgeError(str(response['error']))
            deadline=time.monotonic()+self.timeout; answer=''; status='unknown'
            while time.monotonic()<deadline:
                line=proc.stdout.readline()
                if not line: raise CodexBridgeError('Codex exited before turn/completed')
                try: msg=json.loads(line)
                except json.JSONDecodeError: continue
                if 'id' in msg and msg.get('method'):
                    send({'id':msg['id'],'result':{'decision':'decline'}}); continue
                method=msg.get('method'); params=msg.get('params') or {}
                if method=='item/agentMessage/delta' and isinstance(params.get('delta'),str): answer+=params['delta']
                elif method in ('item/completed','item/updated') and not answer: answer+=self.extract_text(params.get('item') or params)
                elif method=='turn/completed':
                    turn=params.get('turn') or {}; answer=answer or self.extract_text(turn.get('items') or turn.get('output') or turn.get('itemsView') or [])
                    status=str(turn.get('status') or 'completed')
                    if turn.get('error'): raise CodexBridgeError(str(turn['error']))
                    break
            else: raise TimeoutError('Codex turn did not complete')
            return {'thread_id':thread_id,'status':status,'response':answer,'workspace':str(cwd),'sandbox':'read-only','approval_policy':'on-request','approval_requests':'declined'}
        finally:
            try: proc.terminate(); proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass
