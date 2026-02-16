PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    applied_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_namespace ON entities(namespace);
CREATE INDEX IF NOT EXISTS idx_entities_ns_id ON entities(namespace, id);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(subject_id) REFERENCES entities(id)
);
CREATE INDEX IF NOT EXISTS idx_facts_namespace ON facts(namespace);
CREATE INDEX IF NOT EXISTS idx_facts_ns_subject ON facts(namespace, subject_id);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    entity_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    start_ts REAL,
    end_ts REAL,
    confidence REAL NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);
CREATE INDEX IF NOT EXISTS idx_episodes_namespace ON episodes(namespace);
CREATE INDEX IF NOT EXISTS idx_episodes_ns_entity ON episodes(namespace, entity_id);

CREATE TABLE IF NOT EXISTS preferences (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    entity_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL NOT NULL,
    decay_ts REAL,
    provenance_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);
CREATE INDEX IF NOT EXISTS idx_preferences_namespace ON preferences(namespace);
CREATE INDEX IF NOT EXISTS idx_preferences_ns_entity_key ON preferences(namespace, entity_id, key);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    event_type TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_namespace ON audit_log(namespace);

-- Full-text search (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    id UNINDEXED,
    subject_id UNINDEXED,
    text
);

CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    id UNINDEXED,
    entity_id UNINDEXED,
    summary
);

CREATE VIRTUAL TABLE IF NOT EXISTS preferences_fts USING fts5(
    id UNINDEXED,
    entity_id UNINDEXED,
    text
);

-- Triggers: facts -> facts_fts
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(id, subject_id, text)
    VALUES (new.id, new.subject_id, new.predicate || ': ' || new.object);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    DELETE FROM facts_fts WHERE id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    DELETE FROM facts_fts WHERE id = old.id;
    INSERT INTO facts_fts(id, subject_id, text)
    VALUES (new.id, new.subject_id, new.predicate || ': ' || new.object);
END;

-- Triggers: episodes -> episodes_fts
CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(id, entity_id, summary) VALUES (new.id, new.entity_id, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
    DELETE FROM episodes_fts WHERE id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
    DELETE FROM episodes_fts WHERE id = old.id;
    INSERT INTO episodes_fts(id, entity_id, summary) VALUES (new.id, new.entity_id, new.summary);
END;

-- Triggers: preferences -> preferences_fts
CREATE TRIGGER IF NOT EXISTS preferences_ai AFTER INSERT ON preferences BEGIN
    INSERT INTO preferences_fts(id, entity_id, text) VALUES (new.id, new.entity_id, new.key || '=' || new.value);
END;
CREATE TRIGGER IF NOT EXISTS preferences_ad AFTER DELETE ON preferences BEGIN
    DELETE FROM preferences_fts WHERE id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS preferences_au AFTER UPDATE ON preferences BEGIN
    DELETE FROM preferences_fts WHERE id = old.id;
    INSERT INTO preferences_fts(id, entity_id, text) VALUES (new.id, new.entity_id, new.key || '=' || new.value);
END;

-- Embeddings (caller-provided). Store normalized float32 vectors as BLOB.
CREATE TABLE IF NOT EXISTS embeddings (
    item_id TEXT PRIMARY KEY,         -- references facts.id / episodes.id / preferences.id
    namespace TEXT NOT NULL DEFAULT 'default',
    kind TEXT NOT NULL,               -- "fact" | "episode" | "preference"
    entity_id TEXT NOT NULL,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector_blob BLOB NOT NULL,        -- float32 array, normalized
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_embeddings_kind ON embeddings(kind);
CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
CREATE INDEX IF NOT EXISTS idx_embeddings_namespace ON embeddings(namespace);
CREATE INDEX IF NOT EXISTS idx_embeddings_ns_model ON embeddings(namespace, model);
CREATE INDEX IF NOT EXISTS idx_embeddings_ns_entity ON embeddings(namespace, entity_id);

-- Mapping from item_id to vec0 rowid per (model, dim, table_name).
CREATE TABLE IF NOT EXISTS embeddings_vec_index (
    item_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    table_name TEXT NOT NULL,
    rowid INTEGER NOT NULL,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    kind TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vec_index_table_rowid ON embeddings_vec_index(table_name, rowid);
CREATE INDEX IF NOT EXISTS idx_vec_index_model_dim ON embeddings_vec_index(model, dim);
CREATE INDEX IF NOT EXISTS idx_vec_index_entity ON embeddings_vec_index(entity_id);
CREATE INDEX IF NOT EXISTS idx_vec_index_namespace ON embeddings_vec_index(namespace);
CREATE INDEX IF NOT EXISTS idx_vec_index_ns_model_dim ON embeddings_vec_index(namespace, model, dim);

CREATE TABLE IF NOT EXISTS pending_candidates (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,          -- "pending" | "accepted" | "rejected" | "expired"
    created_at REAL NOT NULL,
    expires_at REAL
);

CREATE INDEX IF NOT EXISTS idx_pending_ns_entity_status ON pending_candidates(namespace, entity_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_ns_status ON pending_candidates(namespace, status);

CREATE TABLE IF NOT EXISTS candidate_decisions (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    pending_id TEXT NOT NULL,
    decision TEXT NOT NULL,        -- "accept" | "reject"
    decided_by TEXT NOT NULL,      -- freeform: "user:123" or "agent:lexi"
    note TEXT,
    decided_at REAL NOT NULL,
    FOREIGN KEY(pending_id) REFERENCES pending_candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_decisions_ns_pending ON candidate_decisions(namespace, pending_id);
