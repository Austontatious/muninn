BEGIN;

CREATE TABLE IF NOT EXISTS pending_candidates (
  id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  candidate_json TEXT NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL
);

CREATE INDEX IF NOT EXISTS idx_pending_ns_entity_status ON pending_candidates(namespace, entity_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_ns_status ON pending_candidates(namespace, status);

CREATE TABLE IF NOT EXISTS candidate_decisions (
  id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  pending_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  decided_by TEXT NOT NULL,
  note TEXT,
  decided_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_ns_pending ON candidate_decisions(namespace, pending_id);

COMMIT;
