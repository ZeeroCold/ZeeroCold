const PROTOCOL = "2025-03-26";
const SERVER = { name: "horus-capability-and-evidence", version: "0.2.0" };
const TOOLS = [
 {name:"horus_capability_upsert",description:"Record or update a capability assessment. Recording is not proof of live availability.",inputSchema:{type:"object",properties:{capability_id:{type:"string",minLength:1,maxLength:120},name:{type:"string",minLength:1,maxLength:200},status:{type:"string",enum:["available","available_with_setup","external_required","not_controllable","unverified"]},evidence:{type:"string",maxLength:4000},tested_at:{type:"string",maxLength:80}},required:["capability_id","name","status"],additionalProperties:false}},
 {name:"horus_capability_list",description:"List recorded capability assessments.",inputSchema:{type:"object",properties:{status:{type:"string",enum:["available","available_with_setup","external_required","not_controllable","unverified"]},limit:{type:"integer",minimum:1,maximum:200}},additionalProperties:false}},
 {name:"horus_task_upsert",description:"Track a task state. This is a record keeper, not a background executor.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},title:{type:"string",minLength:1,maxLength:240},status:{type:"string",enum:["planned","in_progress","blocked","verified","cancelled"]},details:{type:"string",maxLength:8000},blocker:{type:"string",maxLength:2000}},required:["title","status"],additionalProperties:false}},
 {name:"horus_task_get",description:"Get a task by ID, or list recent tasks.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},limit:{type:"integer",minimum:1,maximum:100}},additionalProperties:false}},
 {name:"horus_evidence_append",description:"Append a source-tagged evidence record.",inputSchema:{type:"object",properties:{subject:{type:"string",minLength:1,maxLength:240},evidence_class:{type:"string",enum:["tool_result","test_result","source_inspection","user_report","external_reference","inference"]},source:{type:"string",minLength:1,maxLength:1000},observed_at:{type:"string",maxLength:80},confidence:{type:"number",minimum:0,maximum:1},task_id:{type:"string",maxLength:120},capability_id:{type:"string",maxLength:120},notes:{type:"string",maxLength:6000}},required:["subject","evidence_class","source"],additionalProperties:false}},
 {name:"horus_evidence_list",description:"List evidence, optionally filtered by task or capability.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},capability_id:{type:"string",maxLength:120},limit:{type:"integer",minimum:1,maximum:200}},additionalProperties:false}}
];
const json = (body,status=200,headers={}) => new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store",...headers}});
const now=()=>new Date().toISOString();
function valid(schema,a){
 if(!a||typeof a!=="object"||Array.isArray(a))return "arguments must be an object";
 for(const k of Object.keys(a))if(schema.additionalProperties===false&&!schema.properties[k])return "unknown argument: "+k;
 for(const k of schema.required||[])if(a[k]===undefined)return "missing required argument: "+k;
 for(const [k,v] of Object.entries(a)){
  const p=schema.properties[k]; if(!p)continue;
  if(p.type==="string"&&(typeof v!=="string"||v.length>(p.maxLength||1e9)||(p.minLength&&v.length<p.minLength)))return "invalid string: "+k;
  if(p.type==="integer"&&(!Number.isInteger(v)||v<(p.minimum??-Infinity)||v>(p.maximum??Infinity)))return "invalid integer: "+k;
  if(p.type==="number"&&(typeof v!=="number"||v<(p.minimum??-Infinity)||v>(p.maximum??Infinity)))return "invalid number: "+k;
  if(p.enum&&!p.enum.includes(v))return "invalid value for: "+k;
 }
 return null;
}
async function query(db,sql,...args){return db.prepare(sql).bind(...args).all();}
async function callTool(env,name,a){
 const db=env.DB, t=TOOLS.find(x=>x.name===name); if(!t)throw Error("Unknown tool");
 const err=valid(t.inputSchema,a); if(err)throw Error(err);
 if(name==="horus_capability_upsert"){
  const ts=now(); await db.prepare("INSERT INTO capabilities(capability_id,name,status,evidence,tested_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(capability_id) DO UPDATE SET name=excluded.name,status=excluded.status,evidence=excluded.evidence,tested_at=excluded.tested_at,updated_at=excluded.updated_at").bind(a.capability_id,a.name,a.status,a.evidence||"",a.tested_at||"",ts).run();
  return {saved:true,capability_id:a.capability_id,status:a.status,note:"Assessment recorded; not independently verified."};
 }
 if(name==="horus_capability_list"){
  const lim=a.limit||100; const r=a.status?await query(db,"SELECT * FROM capabilities WHERE status=? ORDER BY updated_at DESC LIMIT ?",a.status,lim):await query(db,"SELECT * FROM capabilities ORDER BY updated_at DESC LIMIT ?",lim); return r.results;
 }
 if(name==="horus_task_upsert"){
  const id=a.task_id||crypto.randomUUID(),ts=now(); await db.prepare("INSERT INTO tasks(task_id,title,status,details,blocker,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET title=excluded.title,status=excluded.status,details=excluded.details,blocker=excluded.blocker,updated_at=excluded.updated_at").bind(id,a.title,a.status,a.details||"",a.blocker||"",ts).run(); return {saved:true,task_id:id,status:a.status};
 }
 if(name==="horus_task_get"){
  if(a.task_id){const r=await db.prepare("SELECT * FROM tasks WHERE task_id=?").bind(a.task_id).first();return r||{found:false,task_id:a.task_id};}
  const r=await query(db,"SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",a.limit||50);return r.results;
 }
 if(name==="horus_evidence_append"){
  const id=crypto.randomUUID(); await db.prepare("INSERT INTO evidence(evidence_id,subject,evidence_class,source,observed_at,confidence,task_id,capability_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)").bind(id,a.subject,a.evidence_class,a.source,a.observed_at||now(),a.confidence??null,a.task_id||null,a.capability_id||null,a.notes||"",now()).run();return {saved:true,evidence_id:id};
 }
 if(name==="horus_evidence_list"){
  const clauses=[],values=[];if(a.task_id){clauses.push("task_id=?");values.push(a.task_id);}if(a.capability_id){clauses.push("capability_id=?");values.push(a.capability_id);}
  const where=clauses.length?" WHERE "+clauses.join(" AND "):"";const r=await db.prepare("SELECT * FROM evidence"+where+" ORDER BY created_at DESC LIMIT ?").bind(...values,a.limit||100).all();return r.results;
 }
}
async function rpc(env,req){
 const id=req?.id,method=req?.method;
 if(method==="notifications/initialized")return null;
 if(method==="initialize")return {jsonrpc:"2.0",id,result:{protocolVersion:PROTOCOL,capabilities:{tools:{listChanged:false}},serverInfo:SERVER}};
 if(method==="ping")return {jsonrpc:"2.0",id,result:{}};
 if(method==="tools/list")return {jsonrpc:"2.0",id,result:{tools:TOOLS}};
 if(method==="tools/call"){
  try{const p=req.params||{};const result=await callTool(env,p.name,p.arguments||{});return {jsonrpc:"2.0",id,result:{content:[{type:"text",text:JSON.stringify(result,null,2)}],structuredContent:{result},isError:false}};}
  catch(e){return {jsonrpc:"2.0",id,result:{content:[{type:"text",text:"Tool error: "+e.message}],isError:true}};}
 }
 return {jsonrpc:"2.0",id,error:{code:-32601,message:"Method not found"}};
}
export default {
 async fetch(request,env){
  const url=new URL(request.url);
  if(request.method==="GET"&&url.pathname==="/health")return json({ok:true,service:SERVER.name,version:SERVER.version});
  if(url.pathname!=="/mcp")return json({error:"not_found"},404);
  if(request.method==="OPTIONS")return new Response(null,{status:204,headers:{"access-control-allow-origin":"*","access-control-allow-methods":"POST, GET, OPTIONS","access-control-allow-headers":"authorization, content-type, mcp-session-id, mcp-protocol-version","access-control-max-age":"86400"}});
  if(request.method==="GET")return new Response("SSE not supported; use Streamable HTTP POST.",{status:405,headers:{"allow":"POST, OPTIONS"}});
  if(request.method!=="POST")return json({error:"method_not_allowed"},405,{allow:"POST, OPTIONS"});
  if(!env.HORUS_API_TOKEN)return json({error:"server_not_configured"},503);
  const auth=request.headers.get("authorization")||"";
  if(!auth.startsWith("Bearer ")||auth.slice(7)!==env.HORUS_API_TOKEN)return json({error:"unauthorized"},401);
  if(!env.DB)return json({error:"database_not_bound"},503);
  const ct=request.headers.get("content-type")||"";if(!ct.includes("application/json"))return json({error:"content_type_must_be_application_json"},415);
  let body;try{body=await request.json();}catch{return json({error:"invalid_json"},400);}
  if(Array.isArray(body)){const out=[];for(const item of body){const r=await rpc(env,item);if(r)out.push(r);}return json(out);}
  const out=await rpc(env,body);if(!out)return new Response(null,{status:202});
  return json(out,200,{"access-control-allow-origin":"*"});
 }
};
