import tempfile, unittest
from pathlib import Path
import server

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  server.DB_PATH=Path(self.tmp.name)/"test.sqlite3"
 def tearDown(self): self.tmp.cleanup()
 def test_capability(self):
  server.call_tool("horus_capability_upsert",{"capability_id":"github.read","name":"GitHub read","status":"available"})
  self.assertEqual(server.call_tool("horus_capability_list",{})[0]["capability_id"],"github.read")
 def test_task_and_evidence(self):
  task=server.call_tool("horus_task_upsert",{"title":"Build tools","status":"in_progress"})
  server.call_tool("horus_evidence_append",{"subject":"Unit test","evidence_class":"test_result","source":"unittest","task_id":task["task_id"]})
  self.assertEqual(len(server.call_tool("horus_evidence_list",{"task_id":task["task_id"]})),1)
 def test_rpc(self):
  self.assertEqual(server.rpc({"id":1,"method":"initialize"})["result"]["serverInfo"]["name"],server.NAME)
  self.assertEqual(len(server.rpc({"id":2,"method":"tools/list"})["result"]["tools"]),6)
  self.assertEqual(server.rpc({"id":3,"method":"bad"})["error"]["code"],-32601)

if __name__=="__main__": unittest.main()
