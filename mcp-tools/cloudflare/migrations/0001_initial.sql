CREATE TABLE IF NOT EXISTS capabilities (
 capability_id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('available','available_with_setup','external_required','not_controllable','unverified')),
 evidence TEXT NOT NULL DEFAULT '',
 tested_at TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_capabilities_status_updated ON capabilities(status, updated_at);
CREATE TABLE IF NOT EXISTS tasks (
 task_id TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('planned','in_progress','blocked','verified','cancelled')),
 details TEXT NOT NULL DEFAULT '',
 blocker TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at);
CREATE TABLE IF NOT EXISTS evidence (
 evidence_id TEXT PRIMARY KEY,
 subject TEXT NOT NULL,
 evidence_class TEXT NOT NULL CHECK(evidence_class IN ('tool_result','test_result','source_inspection','user_report','external_reference','inference')),
 source TEXT NOT NULL,
 observed_at TEXT NOT NULL,
 confidence REAL CHECK(confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
 task_id TEXT,
 capability_id TEXT,
 notes TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_task_created ON evidence(task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_capability_created ON evidence(capability_id, created_at);
