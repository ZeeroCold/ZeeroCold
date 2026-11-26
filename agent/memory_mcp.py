"""Narrow HORUS Memory MCP client: typed task/evidence records only."""
from __future__ import annotations
import json,os,urllib.request,urllib.error,uuid
class MemoryMCPError(RuntimeError): pass
class MemoryMCPClient:
    def __init__(self,endpoint=None,token=None,timeout=12):
        self.endpoint=(endpoint or os.getenv("HORUS_MCP_ENDPOINT","")).rstrip("/")
        self.token=token or os.getenv("HORUS_API_TOKEN",""); self.timeout=timeout
    def _rpc(self,method,params=None):
        if not self.endpoint or not self.token: raise MemoryMCPError("HORUS_MCP_ENDPOINT and HORUS_API_TOKEN are required")
        body=json.dumps({"jsonrpc":"2.0","id":str(uuid.uuid4()),"method":method,"params":params or {}}).encode()
        req=urllib.request.Request(self.endpoint,data=body,method="POST",headers={"Authorization":"Bearer "+self.token,"Content-Type":"application/json","Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: payload=json.loads(r.read().decode())
        except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as e: raise MemoryMCPError(str(e)) from e
        if "error" in payload: raise MemoryMCPError(str(payload["error"]))
        return payload.get("result",{})
    def status(self):
        init=self._rpc("initialize",{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"horus-agent","version":"1.4.0"}})
        self._rpc("notifications/initialized"); names={x.get("name") for x in self._rpc("tools/list").get("tools",[])}
        required={"horus_task_upsert","horus_task_get","horus_evidence_append","horus_evidence_list"}
        return {"connected":required.issubset(names),"server":init.get("serverInfo",{}),"available_tools":sorted(names),"missing_required":sorted(required-names)}
    def call(self,name,arguments):
        result=self._rpc("tools/call",{"name":name,"arguments":arguments})
        if result.get("isError"): raise MemoryMCPError(str(result.get("content")))
        return result.get("structuredContent",result)
