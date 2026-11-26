"""HORUS Sentinel: observe worker health and audit integrity; no process control."""
from __future__ import annotations
import threading,time
from typing import Any,Callable
class Sentinel:
    def __init__(self,health_provider:Callable[[],dict[str,Any]],interval:float=5.0):
        self.health_provider=health_provider; self.interval=max(1.0,interval)
        self._stop=threading.Event(); self._thread=None; self._events=[]; self._lock=threading.Lock()
    def check_once(self):
        try:
            h=self.health_provider(); ok=bool(h.get("worker_running")) and bool(h.get("audit_integrity",True))
            event={"timestamp":time.time(),"healthy":ok,"health":h,"alert":None if ok else "worker_stopped_or_audit_integrity_failed"}
        except Exception as e: event={"timestamp":time.time(),"healthy":False,"health":{},"alert":"health_check_failed:"+type(e).__name__}
        with self._lock: self._events=(self._events+[event])[-200:]
        return event
    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread=threading.Thread(target=self._loop,daemon=True,name="horus-sentinel"); self._thread.start()
    def _loop(self):
        while not self._stop.is_set(): self.check_once(); self._stop.wait(self.interval)
    def stop(self,timeout=3):
        self._stop.set()
        if self._thread: self._thread.join(timeout)
    def status(self):
        with self._lock: return {"running":bool(self._thread and self._thread.is_alive()),"recent_events":self._events[-20:],"mode":"observe_and_alert_only"}
