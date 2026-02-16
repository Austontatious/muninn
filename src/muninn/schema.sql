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
