import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

function env(token="test-secret") {
  const calls=[];
  const DB={prepare(sql){return {bind(...args){return {
    async run(){calls.push({sql,args});return {success:true};},
    async all(){calls.push({sql,args});return {results:[]};},
    async first(){calls.push({sql,args});return null;}
  };}};}};
  return {HORUS_API_TOKEN:token,DB,calls};
}
function req(method,body,headers={}) {
  return new Request("https://horus.example/mcp",{method,headers:{"content-type":"application/json","accept":"application/json, text/event-stream","authorization":"Bearer test-secret",...headers},body:body===undefined?undefined:JSON.stringify(body)});
}
test("health endpoint is public and reports service version",async()=>{
 const r=await worker.fetch(new Request("https://horus.example/health"),env());
 assert.equal(r.status,200);assert.equal((await r.json()).ok,true);
});
test("MCP GET is explicitly unsupported",async()=>{
 const r=await worker.fetch(new Request("https://horus.example/mcp"),env());
 assert.equal(r.status,405);
});
test("MCP rejects missing bearer token",async()=>{
 const r=await worker.fetch(req("POST",{jsonrpc:"2.0",id:1,method:"ping"},{authorization:""}),env());
 assert.equal(r.status,401);
});
test("MCP rejects untrusted browser origins",async()=>{
 const r=await worker.fetch(req("POST",{jsonrpc:"2.0",id:1,method:"ping"},{origin:"https://evil.example"}),env());
 assert.equal(r.status,403);
});
test("initialize negotiates supported protocol",async()=>{
 const e=env();const r=await worker.fetch(req("POST",{jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2025-03-26",capabilities:{},clientInfo:{name:"test",version:"1"}}}),e);
 const j=await r.json();assert.equal(r.status,200);assert.equal(j.result.protocolVersion,"2025-03-26");
});
test("tools/list exposes exactly six tools",async()=>{
 const e=env();const r=await worker.fetch(req("POST",{jsonrpc:"2.0",id:2,method:"tools/list"}),e);
 const j=await r.json();assert.equal(j.result.tools.length,6);
});
test("tools/call writes a capability through the D1 binding",async()=>{
 const e=env();const r=await worker.fetch(req("POST",{jsonrpc:"2.0",id:3,method:"tools/call",params:{name:"horus_capability_upsert",arguments:{capability_id:"test.cap",name:"Test capability",status:"unverified"}}}),e);
 const j=await r.json();assert.equal(j.result.isError,false);assert.equal(j.result.structuredContent.result.saved,true);assert.equal(e.calls.length,1);
});
test("notifications return 202 without a JSON body",async()=>{
 const r=await worker.fetch(req("POST",{jsonrpc:"2.0",method:"notifications/initialized"}),env());
 assert.equal(r.status,202);assert.equal(await r.text(),"");
});
