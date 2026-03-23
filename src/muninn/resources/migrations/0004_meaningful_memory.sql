BEGIN;

CREATE TABLE IF NOT EXISTS evidence_state (
  namespace TEXT NOT NULL DEFAULT 'default',
  owner_type TEXT NOT NULL CHECK(owner_type IN ('artifact','chunk')),
  owner_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'captured' CHECK(status IN ('captured','candidate','promoted')),
  score REAL NOT NULL DEFAULT 0.0 CHECK(score >= 0.0),
  reason_json TEXT NOT NULL DEFAULT '{}',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  PRIMARY KEY (namespace, owner_type, owner_id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_state_ns_status ON evidence_state(namespace, status);
CREATE INDEX IF NOT EXISTS idx_evidence_state_ns_updated ON evidence_state(namespace, updated_at DESC);

CREATE TABLE IF NOT EXISTS signals (
  namespace TEXT NOT NULL DEFAULT 'default',
  owner_type TEXT NOT NULL CHECK(owner_type IN ('card','artifact','chunk','source')),
  owner_id TEXT NOT NULL,
  access_count INTEGER NOT NULL DEFAULT 0 CHECK(access_count >= 0),
  last_accessed_at REAL,
  last_query_hash TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  PRIMARY KEY (namespace, owner_type, owner_id)
);
CREATE INDEX IF NOT EXISTS idx_signals_ns_owner ON signals(namespace, owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_signals_ns_updated ON signals(namespace, updated_at DESC);

CREATE TABLE IF NOT EXISTS coaccess_edges (
  namespace TEXT NOT NULL DEFAULT 'default',
  a_type TEXT NOT NULL CHECK(a_type IN ('card','artifact','chunk','source')),
  a_id TEXT NOT NULL,
  b_type TEXT NOT NULL CHECK(b_type IN ('card','artifact','chunk','source')),
  b_id TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 0.0 CHECK(weight >= 0.0),
  updated_at REAL NOT NULL,
  PRIMARY KEY (namespace, a_type, a_id, b_type, b_id)
);
CREATE INDEX IF NOT EXISTS idx_coaccess_edges_ns_a ON coaccess_edges(namespace, a_type, a_id);
CREATE INDEX IF NOT EXISTS idx_coaccess_edges_ns_b ON coaccess_edges(namespace, b_type, b_id);

CREATE TABLE IF NOT EXISTS index_jobs (
  job_id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL DEFAULT 'default',
  owner_type TEXT NOT NULL CHECK(owner_type IN ('card','artifact','chunk','source')),
  owner_id TEXT NOT NULL,
  modality TEXT NOT NULL CHECK(modality IN ('text','image','audio','video')),
  priority INTEGER NOT NULL DEFAULT 50,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','done','failed')),
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_index_jobs_ns_status ON index_jobs(namespace, status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_index_jobs_ns_owner ON index_jobs(namespace, owner_type, owner_id, modality);
CREATE UNIQUE INDEX IF NOT EXISTS idx_index_jobs_pending_unique
  ON index_jobs(namespace, owner_type, owner_id, modality, status)
  WHERE status IN ('pending','running');

COMMIT;
