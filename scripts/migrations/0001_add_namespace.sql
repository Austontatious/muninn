-- migration id: 0001_add_namespace.sql
BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
  id TEXT PRIMARY KEY,
  applied_at REAL NOT NULL
);

-- Entities
ALTER TABLE entities ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_entities_namespace ON entities(namespace);
CREATE INDEX IF NOT EXISTS idx_entities_ns_id ON entities(namespace, id);

-- Facts
ALTER TABLE facts ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_facts_namespace ON facts(namespace);
CREATE INDEX IF NOT EXISTS idx_facts_ns_subject ON facts(namespace, subject_id);

-- Episodes
ALTER TABLE episodes ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_episodes_namespace ON episodes(namespace);
CREATE INDEX IF NOT EXISTS idx_episodes_ns_entity ON episodes(namespace, entity_id);

-- Preferences
ALTER TABLE preferences ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_preferences_namespace ON preferences(namespace);
CREATE INDEX IF NOT EXISTS idx_preferences_ns_entity_key ON preferences(namespace, entity_id, key);

-- Embeddings
ALTER TABLE embeddings ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_embeddings_namespace ON embeddings(namespace);
CREATE INDEX IF NOT EXISTS idx_embeddings_ns_model ON embeddings(namespace, model);
CREATE INDEX IF NOT EXISTS idx_embeddings_ns_entity ON embeddings(namespace, entity_id);

-- embeddings_vec_index
ALTER TABLE embeddings_vec_index ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_vec_index_namespace ON embeddings_vec_index(namespace);
CREATE INDEX IF NOT EXISTS idx_vec_index_ns_model_dim ON embeddings_vec_index(namespace, model, dim);

-- Audit log
ALTER TABLE audit_log ADD COLUMN namespace TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_audit_namespace ON audit_log(namespace);

COMMIT;
