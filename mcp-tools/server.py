#!/usr/bin/env python3
"""HORUS MCP tools: bearer-authenticated, stdlib-only Streamable HTTP service."""
import hmac, json, os, sqlite3, threading, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

NAME, VERSION, PROTOCOL = "horus-capability-and-evidence", "0.1.0", "2025-03-26"
DB_PATH = Path(os.getenv("HORUS_DB_PATH", "./data/horus.sqlite3"))
TOKEN = os.getenv("HORUS_API_TOKEN", "")
LOCK = threading.RLock()

TOOLS = [
 {"name":"horus_capability_upsert","description":"Record or update a capability assessment. A record is not proof of live availability.","inputSchema":{"type":"object","properties":{"capability_id":{"type":"string","minLength":1,"maxLength":120},"name":{"type":"string","minLength":1,"maxLength":200},"status":{"type":"string","enum":["available","available_with_setup","external_required","not_controllable","unverified"]},"evidence":{"type":"string","maxLength":4000},"tested_at":{"type":"string","maxLength":80}},"required":["capability_id","name","status"],"additionalProperties":False}},
 {"name":"horus_capability_list","description":"List recorded capability assessments.","inputSchema":{"type":"object","properties":{"status":{"type":"string","enum":["available","available_with_setup","external_required","not_controllable","unverified"]},"limit":{"type":"integer","minimum":1,"maximum":200}},"additionalProperties":False}},
 {"name":"horus_task_upsert","description":"Track a task state. This is a record keeper, not a background executor.","inputSchema":{"type":"object","properties":{"task_id":{"type":"string","maxLength":120},"title":{"type":"string","minLength":1,"maxLength":240},"status":{"type":"string","enum":["planned","in_progress","blocked","verified","cancelled"]},"details":{"type":"string","maxLength":8000},"blocker":{"type":"string","maxLength":2000}},"required":["title","status"],"additionalProperties":False}},
 {"name":"horus_task_get","description":"Get a task by ID, or list recent tasks.","inputSchema":{"type":"object","properties":{"task_id":{"type":"string","maxLength":120},"limit":{"type":"integer","minimum":1,"maximum":100}},"additionalProperties":False}},
 {"name":"horus_evidence_append","description":"Append an evidence record with source and evidence class.","inputSchema":{"type":"object","properties":{"subject":{"type":"string","minLength":1,"maxLength":240},"evidence_class":{"type":"string","enum":["tool_result","test_result","source_inspection","user_report","external_reference","inference"]},"source":{"type":"string","minLength":1,"maxLength":1000},"observed_at":{"type":"string","maxLength":80},"confidence":{"type":"number","minimum":0,"maximum":1},"task_id":{"type":"string","maxLength":120},"capability_id":{"type":"string","maxLength":120},"notes":{"type":"string","maxLength":6000}},"required":["subject","evidence_class","source"],"additionalProperties":False}},
 {"name":"horus_evidence_list","description":"List evidence, optionally filtered by task or capability.","inputSchema":{"type":"object","properties":{"task_id":{"type":"string","maxLength":120},"capability_id":{"type":"string","maxLength":120},"limit":{"type":"integer","minimum":1,"maximum":200}},"additionalProperties":False}}
]

def now():
 return datetime.now(timezone.utc).isoformat(timespec="seconds")

def db_open():
 DB_PATH.parent.mkdir(parents=True, exist_ok=True)
 c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
 c.executescript("""
 CREATE TABLE IF NOT EXISTS capabilities(capability_id TEXT PRIMARY KEY,name TEXT NOT NULL,status TEXT NOT NULL,evidence TEXT NOT NULL DEFAULT '',tested_at TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY,title TEXT NOT NULL,status TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',blocker TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,subject TEXT NOT NULL,evidence_class TEXT NOT NULL,source TEXT NOT NULL,observed_at TEXT NOT NULL,confidence REAL,task_id TEXT,capability_id TEXT,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
 CREATE INDEX IF NOT EXISTS evidence_task ON evidence(task_id);
 CREATE INDEX IF NOT EXISTS evidence_capability ON evidence(capability_id);
 """)
 return c

def call_tool(name,a):
 with LOCK, db_open() as c:
  if name=="horus_capability_upsert":
   c.execute("""INSERT INTO capabilities VALUES(?,?,?,?,?,?) ON CONFLICT(capability_id) DO UPDATE SET name=excluded.name,status=excluded.status,evidence=excluded.evidence,tested_at=excluded.tested_at,updated_at=excluded.updated_at""",(a["capability_id"],a["name"],a["status"],a.get("evidence",""),a.get("tested_at",""),now()))
   return {"saved":True,"capability_id":a["capability_id"],"status":a["status"],"note":"Assessment recorded; not independently verified."}
  if name=="horus_capability_list":
   q="SELECT * FROM capabilities"; p=[]
   if a.get("status"): q+=" WHERE status=?"; p.append(a["status"])
   q+=" ORDER BY updated_at DESC LIMIT ?"; p.append(a.get("limit",100))
   return [dict(x) for x in c.execute(q,p)]
  if name=="horus_task_upsert":
   tid=a.get("task_id") or str(uuid.uuid4())
   c.execute("""INSERT INTO tasks VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET title=excluded.title,status=excluded.status,details=excluded.details,blocker=excluded.blocker,updated_at=excluded.updated_at""",(tid,a["title"],a["status"],a.get("details",""),a.get("blocker",""),now()))
   return {"saved":True,"task_id":tid,"status":a["status"]}
  if name=="horus_task_get":
   if a.get("task_id"):
    x=c.execute("SELECT * FROM tasks WHERE task_id=?",(a["task_id"],)).fetchone()
    return dict(x) if x else {"found":False,"task_id":a["task_id"]}
   return [dict(x) for x in c.execute("SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",(a.get("limit",50),))]
  if name=="horus_evidence_append":
   eid=str(uuid.uuid4()); ts=a.get("observed_at") or now()
   c.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,a["subject"],a["evidence_class"],a["source"],ts,a.get("confidence"),a.get("task_id"),a.get("capability_id"),a.get("notes",""),now()))
   return {"saved":True,"evidence_id":eid}
  if name=="horus_evidence_list":
   q="SELECT * FROM evidence WHERE 1=1"; p=[]
   for k in ("task_id","capability_id"):
    if a.get(k): q+=f" AND {k}=?"; p.append(a[k])
   q+=" ORDER BY created_at DESC LIMIT ?"; p.append(a.get("limit",100))
   return [dict(x) for x in c.execute(q,p)]
 raise ValueError("Unknown tool")

def rpc(req):
 rid=req.get("id"); method=req.get("method")
 if method=="notifications/initialized": return None
 if method=="initialize": return {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":PROTOCOL,"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":NAME,"version":VERSION}}}
 if method=="ping": return {"jsonrpc":"2.0","id":rid,"result":{}}
 if method=="tools/list": return {"jsonrpc":"2.0","id":rid,"result":{"tools":TOOLS}}
 if method=="tools/call":
  p=req.get("params") or {}; name=p.get("name"); args=p.get("arguments") or {}
  try:
   if name not in {t["name"] for t in TOOLS}: raise ValueError("Unknown tool")
   result=call_tool(name,args)
   return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":json.dumps(result,ensure_ascii=False,indent=2)}],"structuredContent":{"result":result},"isError":False}}
  except Exception as e:
   return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":f"Tool error: {type(e).__name__}: {e}"}],"isError":True}}
 return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"Method not found"}}

class Handler(BaseHTTPRequestHandler):
 def send_json(self,code,obj):
  b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
 def do_GET(self):
  if self.path=="/health": return self.send_json(200,{"ok":True,"service":NAME,"version":VERSION})
  return self.send_json(404,{"error":"not_found"})
 def do_POST(self):
  if self.path!="/mcp": return self.send_json(404,{"error":"not_found"})
  if not TOKEN: return self.send_json(503,{"error":"HORUS_API_TOKEN is not configured"})
  auth=self.headers.get("Authorization",""); supplied=auth[7:] if auth.startswith("Bearer ") else ""
  if not hmac.compare_digest(supplied,TOKEN): return self.send_json(401,{"error":"unauthorized"})
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n<1 or n>1000000: return self.send_json(413,{"error":"invalid_body_size"})
   req=json.loads(self.rfile.read(n))
   if isinstance(req,list): return self.send_json(200,[x for x in (rpc(y) for y in req) if x is not None])
   out=rpc(req)
   return self.send_json(202,{}) if out is None else self.send_json(200,out)
  except Exception as e: return self.send_json(400,{"error":"invalid_request","detail":str(e)})
 def log_message(self,fmt,*args): print(fmt%args)

def main():
 if not TOKEN: raise SystemExit("Set HORUS_API_TOKEN to a long random secret.")
 host=os.getenv("HORUS_HOST","0.0.0.0"); port=int(os.getenv("PORT",os.getenv("HORUS_PORT","8000")))
 with db_open(): pass
 print(f"Starting {NAME} on {host}:{port}")
 ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=="__main__": main()
