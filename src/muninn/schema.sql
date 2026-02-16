PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(subject_id) REFERENCES entities(id)
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    start_ts REAL,
    end_ts REAL,
    confidence REAL NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);

CREATE TABLE IF NOT EXISTS preferences (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL NOT NULL,
    decay_ts REAL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
