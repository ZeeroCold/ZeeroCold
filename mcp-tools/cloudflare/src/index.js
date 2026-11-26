const LEGACY_PROTOCOLS = ["2025-03-26", "2025-11-25"];
const MODERN_PROTOCOL = "2026-07-28";
const SUPPORTED_PROTOCOLS = [...LEGACY_PROTOCOLS, MODERN_PROTOCOL];
const SERVER = { name: "horus-capability-and-evidence", version: "0.2.1" };
const TOOLS = [
 {name:"horus_capability_upsert",description:"Record or update a capability assessment. Recording is not proof of live availability.",inputSchema:{type:"object",properties:{capability_id:{type:"string",minLength:1,maxLength:120},name:{type:"string",minLength:1,maxLength:200},status:{type:"string",enum:["available","available_with_setup","external_required","not_controllable","unverified"]},evidence:{type:"string",maxLength:4000},tested_at:{type:"string",maxLength:80}},required:["capability_id","name","status"],additionalProperties:false}},
 {name:"horus_capability_list",description:"List recorded capability assessments.",inputSchema:{type:"object",properties:{status:{type:"string",enum:["available","available_with_setup","external_required","not_controllable","unverified"]},limit:{type:"integer",minimum:1,maximum:200}},additionalProperties:false}},
 {name:"horus_task_upsert",description:"Track a task state. This is a record keeper, not a background executor.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},title:{type:"string",minLength:1,maxLength:240},status:{type:"string",enum:["planned","in_progress","blocked","verified","cancelled"]},details:{type:"string",maxLength:8000},blocker:{type:"string",maxLength:2000}},required:["title","status"],additionalProperties:false}},
 {name:"horus_task_get",description:"Get a task by ID, or list recent tasks.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},limit:{type:"integer",minimum:1,maximum:100}},additionalProperties:false}},
 {name:"horus_evidence_append",description:"Append a source-tagged evidence record.",inputSchema:{type:"object",properties:{subject:{type:"string",minLength:1,maxLength:240},evidence_class:{type:"string",enum:["tool_result","test_result","source_inspection","user_report","external_reference","inference"]},source:{type:"string",minLength:1,maxLength:1000},observed_at:{type:"string",maxLength:80},confidence:{type:"number",minimum:0,maximum:1},task_id:{type:"string",maxLength:120},capability_id:{type:"string",maxLength:120},notes:{type:"string",maxLength:6000}},required:["subject","evidence_class","source"],additionalProperties:false}},
 {name:"horus_evidence_list",description:"List evidence, optionally filtered by task or capability.",inputSchema:{type:"object",properties:{task_id:{type:"string",maxLength:120},capability_id:{type:"string",maxLength:120},limit:{type:"integer",minimum:1,maximum:200}},additionalProperties:false}}
];
const CORS = {
 "access-control-allow-origin":"*",
 "access-control-allow-methods":"POST, OPTIONS",
 "access-control-allow-headers":"authorization, content-type, accept, mcp-protocol-version, mcp-session-id",
 "access-control-max-age":"86400",
 "vary":"Origin"
};
const json=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store",...CORS,...headers}});
const now=()=>new Date().toISOString();
function safeEqual(a,b){
 if(typeof a!=="string"||typeof b!=="string")return false;
 let diff=a.length^b.length; const n=Math.max(a.length,b.length);
 for(let i=0;i<n;i++)diff|=(a.charCodeAt(i%Math.max(1,a.length))||0)^(b.charCodeAt(i%Math.max(1,b.length))||0);
 return diff===0;
}
function valid(schema,a){
 if(!a||typeof a!=="object"||Array.isArray(a))return "arguments must be an object";
 for(const k of Object.keys(a))if(schema.additionalProperties===false&&!schema.properties[k])return "unknown argument: "+k;
 for(const k of schema.required||[])if(a[k]===undefined)return "missing required argument: "+k;
 for(const [k,v] of Object.entries(a)){
  const p=schema.properties[k];if(!p)continue;
  if(p.type==="string"&&(typeof v!=="string"||v.length>(p.maxLength||1e9)||(p.minLength&&v.length<p.minLength)))return "invalid string: "+k;
  if(p.type==="integer"&&(!Number.isInteger(v)||v<(p.minimum??-Infinity)||v>(p.maximum??Infinity)))return "invalid integer: "+k;
  if(p.type==="number"&&(typeof v!=="number"||!Number.isFinite(v)||v<(p.minimum??-Infinity)||v>(p.maximum??Infinity)))return "invalid number: "+k;
  if(p.enum&&!p.enum.includes(v))return "invalid value for: "+k;
 }
 return null;
}
async function query(db,sql,...args){return db.prepare(sql).bind(...args).all();}
async function callTool(env,name,a){
 const db=env.DB,t=TOOLS.find(x=>x.name===name);if(!t)throw Error("Unknown tool");
 const err=valid(t.inputSchema,a);if(err)throw Error(err);
 if(name==="horus_capability_upsert"){
  const ts=now();await db.prepare("INSERT INTO capabilities(capability_id,name,status,evidence,tested_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(capability_id) DO UPDATE SET name=excluded.name,status=excluded.status,evidence=excluded.evidence,tested_at=excluded.tested_at,updated_at=excluded.updated_at").bind(a.capability_id,a.name,a.status,a.evidence||"",a.tested_at||"",ts).run();
  return {saved:true,capability_id:a.capability_id,status:a.status,note:"Assessment recorded; not independently verified."};
 }
 if(name==="horus_capability_list"){
  const lim=a.limit||100,r=a.status?await query(db,"SELECT * FROM capabilities WHERE status=? ORDER BY updated_at DESC LIMIT ?",a.status,lim):await query(db,"SELECT * FROM capabilities ORDER BY updated_at DESC LIMIT ?",lim);return r.results;
 }
 if(name==="horus_task_upsert"){
  const id=a.task_id||crypto.randomUUID(),ts=now();await db.prepare("INSERT INTO tasks(task_id,title,status,details,blocker,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET title=excluded.title,status=excluded.status,details=excluded.details,blocker=excluded.blocker,updated_at=excluded.updated_at").bind(id,a.title,a.status,a.details||"",a.blocker||"",ts).run();return {saved:true,task_id:id,status:a.status};
 }
 if(name==="horus_task_get"){
  if(a.task_id){const r=await db.prepare("SELECT * FROM tasks WHERE task_id=?").bind(a.task_id).first();return r||{found:false,task_id:a.task_id};}
  return (await query(db,"SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",a.limit||50)).results;
 }
 if(name==="horus_evidence_append"){
  const id=crypto.randomUUID(),ts=now();await db.prepare("INSERT INTO evidence(evidence_id,subject,evidence_class,source,observed_at,confidence,task_id,capability_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)").bind(id,a.subject,a.evidence_class,a.source,a.observed_at||ts,a.confidence??null,a.task_id||null,a.capability_id||null,a.notes||"",ts).run();return {saved:true,evidence_id:id};
 }
 if(name==="horus_evidence_list"){
  const clauses=[],values=[];if(a.task_id){clauses.push("task_id=?");values.push(a.task_id);}if(a.capability_id){clauses.push("capability_id=?");values.push(a.capability_id);}
  const where=clauses.length?" WHERE "+clauses.join(" AND "):"",r=await db.prepare("SELECT * FROM evidence"+where+" ORDER BY created_at DESC LIMIT ?").bind(...values,a.limit||100).all();return r.results;
 }
 throw Error("Unknown tool");
}
async function rpc(env,req){
 if(!req||typeof req!=="object"||Array.isArray(req)||req.jsonrpc!=="2.0"||typeof req.method!=="string")return {jsonrpc:"2.0",id:req?.id??null,error:{code:-32600,message:"Invalid Request"}};
 const id=req.id,method=req.method;
 if(method==="notifications/initialized"||method==="notifications/cancelled"||method==="notifications/progress")return null;
 if(method==="initialize"){
  const requested=req.params?.protocolVersion;
  if(!SUPPORTED_PROTOCOLS.includes(requested))return {jsonrpc:"2.0",id,error:{code:-32602,message:"Unsupported protocol version",data:{supported:SUPPORTED_PROTOCOLS}}};
  return {jsonrpc:"2.0",id,result:{protocolVersion:requested,capabilities:{tools:{listChanged:false}},serverInfo:SERVER,instructions:"HORUS tools record capability assessments, task states, and source-tagged evidence. They do not execute background work."}};
 }
 if(method==="ping")return {jsonrpc:"2.0",id,result:{}};
 if(method==="tools/list")return {jsonrpc:"2.0",id,result:{tools:TOOLS}};
 if(method==="tools/call"){
  try{const p=req.params||{},result=await callTool(env,p.name,p.arguments||{});return {jsonrpc:"2.0",id,result:{content:[{type:"text",text:JSON.stringify(result,null,2)}],structuredContent:{result},isError:false}};}
  catch(e){return {jsonrpc:"2.0",id,result:{content:[{type:"text",text:"Tool error: "+e.message}],isError:true}};}
 }
 return {jsonrpc:"2.0",id,error:{code:-32601,message:"Method not found"}};
}
export default {
 async fetch(request,env){
  const url=new URL(request.url);
  if(request.method==="GET"&&url.pathname==="/health")return json({ok:true,service:SERVER.name,version:SERVER.version,protocols:SUPPORTED_PROTOCOLS});
  if(url.pathname!=="/mcp")return json({error:"not_found"},404);
  if(request.method==="OPTIONS")return new Response(null,{status:204,headers:CORS});
  if(request.method==="GET"||request.method==="DELETE")return new Response(null,{status:405,headers:{...CORS,allow:"POST, OPTIONS"}});
  if(request.method!=="POST")return json({error:"method_not_allowed"},405,{allow:"POST, OPTIONS"});
  const origin=request.headers.get("origin");
  const allowed=(env.ALLOWED_ORIGINS||"https://chatgpt.com,https://chat.openai.com").split(",").map(x=>x.trim()).filter(Boolean);
  if(origin&&!allowed.includes(origin))return json({error:"origin_not_allowed"},403);
  if(!env.HORUS_API_TOKEN)return json({error:"server_not_configured"},503);
  const auth=request.headers.get("authorization")||"";
  if(!auth.startsWith("Bearer ")||!safeEqual(auth.slice(7),env.HORUS_API_TOKEN))return json({error:"unauthorized"},401);
  if(!env.DB)return json({error:"database_not_bound"},503);
  const ct=request.headers.get("content-type")||"",accept=request.headers.get("accept")||"";
  if(!ct.toLowerCase().includes("application/json"))return json({error:"content_type_must_be_application_json"},415);
  if(!accept.includes("application/json")&&!accept.includes("text/event-stream"))return json({error:"accept_must_include_application_json_or_text_event_stream"},406);
  let body;try{body=await request.json();}catch{return json({error:"invalid_json"},400);}
  if(Array.isArray(body))return json({error:"batch_requests_not_supported"},400);
  const versionHeader=request.headers.get("mcp-protocol-version");
  const methodHeader=request.headers.get("mcp-method");
  const nameHeader=request.headers.get("mcp-name");
  const bodyVersion=body?.params?._meta?.["io.modelcontextprotocol/protocolVersion"];
  const modern=versionHeader===MODERN_PROTOCOL||bodyVersion===MODERN_PROTOCOL;
  if(modern){
   const err=(message)=>json({jsonrpc:"2.0",id:body?.id??null,error:{code:-32020,message}},400);
   if(versionHeader!==MODERN_PROTOCOL||bodyVersion!==MODERN_PROTOCOL)return err("MCP-Protocol-Version header and request metadata must both be 2026-07-28");
   if(!methodHeader||methodHeader!==body?.method)return err("Mcp-Method header is missing or does not match request method");
   const needsName=body.method==="tools/call"||body.method==="resources/read"||body.method==="prompts/get";
   if(needsName&&(!nameHeader||nameHeader!==body?.params?.name&&nameHeader!==body?.params?.uri))return err("Mcp-Name header is missing or does not match request name");
  } else if(versionHeader&&versionHeader!== "2025-03-26" && versionHeader!=="2025-11-25"){
   return json({jsonrpc:"2.0",id:body?.id??null,error:{code:-32602,message:"Unsupported protocol version",data:{supported:SUPPORTED_PROTOCOLS}}},400);
  }
  if(modern&&body?.method==="initialize")return json({jsonrpc:"2.0",id:body?.id??null,error:{code:-32601,message:"initialize is not part of protocol 2026-07-28; send the request metadata headers"}},404);
  const out=await rpc(env,body);
  if(!out)return new Response(null,{status:202,headers:CORS});
  if(modern&&out.error?.code===-32601)return json(out,404);
  return json(out,200);
 }
};
