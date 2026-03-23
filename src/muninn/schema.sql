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
CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

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

-- Cardex v1 (multimodal-ready, card-centric memory store)
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    type TEXT NOT NULL CHECK(type IN ('contact','recipe','paper','fact','place','media','thread','collection','custom')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    salience REAL NOT NULL DEFAULT 0.5 CHECK(salience >= 0.0 AND salience <= 1.0),
    confidence REAL NOT NULL DEFAULT 0.7 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    sensitivity_tier INTEGER NOT NULL DEFAULT 0 CHECK(sensitivity_tier >= 0 AND sensitivity_tier <= 3),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived'))
);
CREATE INDEX IF NOT EXISTS idx_cards_namespace ON cards(namespace);
CREATE INDEX IF NOT EXISTS idx_cards_ns_status ON cards(namespace, status);
CREATE INDEX IF NOT EXISTS idx_cards_ns_tier ON cards(namespace, sensitivity_tier);
CREATE INDEX IF NOT EXISTS idx_cards_ns_updated ON cards(namespace, updated_at DESC);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    source_type TEXT NOT NULL CHECK(source_type IN ('document','web','note','image','audio','video','file','email','chat','other')),
    uri TEXT NOT NULL,
    title TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT,
    sensitivity_tier INTEGER NOT NULL DEFAULT 0 CHECK(sensitivity_tier >= 0 AND sensitivity_tier <= 3),
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sources_namespace ON sources(namespace);
CREATE INDEX IF NOT EXISTS idx_sources_ns_tier ON sources(namespace, sensitivity_tier);
CREATE INDEX IF NOT EXISTS idx_sources_ns_type ON sources(namespace, source_type);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    source_id TEXT NOT NULL,
    content_text TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE INDEX IF NOT EXISTS idx_documents_namespace ON documents(namespace);
CREATE INDEX IF NOT EXISTS idx_documents_ns_source ON documents(namespace, source_id);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    doc_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    heading_path_json TEXT,
    char_start INTEGER,
    char_end INTEGER,
    text_hash TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);
CREATE INDEX IF NOT EXISTS idx_chunks_namespace ON chunks(namespace);
CREATE INDEX IF NOT EXISTS idx_chunks_ns_doc ON chunks(namespace, doc_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_doc_idx ON chunks(doc_id, idx);

CREATE TABLE IF NOT EXISTS card_refs (
    namespace TEXT NOT NULL DEFAULT 'default',
    card_id TEXT NOT NULL,
    ref_type TEXT NOT NULL CHECK(ref_type IN ('source','doc','chunk','entity','external')),
    ref_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('evidence','primary','related','thumbnail','transcript','caption')),
    note TEXT,
    created_at REAL NOT NULL,
    PRIMARY KEY (namespace, card_id, ref_type, ref_id, role),
    FOREIGN KEY(card_id) REFERENCES cards(card_id)
);
CREATE INDEX IF NOT EXISTS idx_card_refs_ns_card ON card_refs(namespace, card_id);
CREATE INDEX IF NOT EXISTS idx_card_refs_ns_ref ON card_refs(namespace, ref_type, ref_id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    source_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL CHECK(artifact_type IN ('extracted_text','transcript','caption','ocr','objects','summary','thumbnail','keyframes','embedding_text')),
    content_text TEXT,
    content_json TEXT,
    created_at REAL NOT NULL,
    generator TEXT NOT NULL DEFAULT 'stub',
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_namespace ON artifacts(namespace);
CREATE INDEX IF NOT EXISTS idx_artifacts_ns_source ON artifacts(namespace, source_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_ns_type ON artifacts(namespace, artifact_type);

CREATE TABLE IF NOT EXISTS card_embeddings (
    embedding_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    owner_type TEXT NOT NULL CHECK(owner_type IN ('card','source','chunk')),
    owner_id TEXT NOT NULL,
    modality TEXT NOT NULL CHECK(modality IN ('text','image','audio','video')),
    model TEXT NOT NULL,
    dims INTEGER NOT NULL,
    vector_blob BLOB,
    content_hash TEXT,
    embed_status TEXT NOT NULL DEFAULT 'pending' CHECK(embed_status IN ('pending','ready','failed')),
    embed_error TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_card_embeddings_namespace ON card_embeddings(namespace);
CREATE INDEX IF NOT EXISTS idx_card_embeddings_owner ON card_embeddings(namespace, owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_card_embeddings_status ON card_embeddings(namespace, embed_status);
CREATE INDEX IF NOT EXISTS idx_card_embeddings_model ON card_embeddings(namespace, model, modality);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    proposal_type TEXT NOT NULL CHECK(proposal_type IN ('create_card','update_card','link_refs','add_source')),
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('proposed','confirmed','rejected','expired')),
    created_at REAL NOT NULL,
    decided_at REAL,
    requested_by TEXT,
    decided_by TEXT,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_proposals_namespace ON proposals(namespace);
CREATE INDEX IF NOT EXISTS idx_proposals_ns_status ON proposals(namespace, status);
CREATE INDEX IF NOT EXISTS idx_proposals_ns_created ON proposals(namespace, created_at DESC);

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
CREATE INDEX IF NOT EXISTS idx_index_jobs_ns_status
    ON index_jobs(namespace, status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_index_jobs_ns_owner
    ON index_jobs(namespace, owner_type, owner_id, modality);
CREATE UNIQUE INDEX IF NOT EXISTS idx_index_jobs_pending_unique
    ON index_jobs(namespace, owner_type, owner_id, modality, status)
    WHERE status IN ('pending','running');

CREATE TRIGGER IF NOT EXISTS cards_tier_check_insert
BEFORE INSERT ON cards
WHEN NEW.sensitivity_tier < 0 OR NEW.sensitivity_tier > 3
BEGIN
    SELECT RAISE(ABORT, 'invalid sensitivity_tier');
END;
CREATE TRIGGER IF NOT EXISTS cards_tier_check_update
BEFORE UPDATE ON cards
WHEN NEW.sensitivity_tier < 0 OR NEW.sensitivity_tier > 3
BEGIN
    SELECT RAISE(ABORT, 'invalid sensitivity_tier');
END;

CREATE TRIGGER IF NOT EXISTS sources_tier_check_insert
BEFORE INSERT ON sources
WHEN NEW.sensitivity_tier < 0 OR NEW.sensitivity_tier > 3
BEGIN
    SELECT RAISE(ABORT, 'invalid sensitivity_tier');
END;
CREATE TRIGGER IF NOT EXISTS sources_tier_check_update
BEFORE UPDATE ON sources
WHEN NEW.sensitivity_tier < 0 OR NEW.sensitivity_tier > 3
BEGIN
    SELECT RAISE(ABORT, 'invalid sensitivity_tier');
END;

CREATE TRIGGER IF NOT EXISTS proposals_status_check_insert
BEFORE INSERT ON proposals
WHEN NEW.status NOT IN ('proposed','confirmed','rejected','expired')
BEGIN
    SELECT RAISE(ABORT, 'invalid proposal status');
END;
CREATE TRIGGER IF NOT EXISTS proposals_status_check_update
BEFORE UPDATE ON proposals
WHEN NEW.status NOT IN ('proposed','confirmed','rejected','expired')
BEGIN
    SELECT RAISE(ABORT, 'invalid proposal status');
END;

-- Cardex FTS
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
    card_id UNINDEXED,
    namespace UNINDEXED,
    title,
    summary,
    tags
);

CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
    artifact_id UNINDEXED,
    namespace UNINDEXED,
    source_id UNINDEXED,
    content_text
);

CREATE TRIGGER IF NOT EXISTS cards_ai AFTER INSERT ON cards BEGIN
    INSERT INTO cards_fts(card_id, namespace, title, summary, tags)
    VALUES (new.card_id, new.namespace, new.title, new.summary, new.tags_json);
END;
CREATE TRIGGER IF NOT EXISTS cards_ad AFTER DELETE ON cards BEGIN
    DELETE FROM cards_fts WHERE card_id = old.card_id;
END;
CREATE TRIGGER IF NOT EXISTS cards_au AFTER UPDATE ON cards BEGIN
    DELETE FROM cards_fts WHERE card_id = old.card_id;
    INSERT INTO cards_fts(card_id, namespace, title, summary, tags)
    VALUES (new.card_id, new.namespace, new.title, new.summary, new.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS artifacts_ai AFTER INSERT ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifact_id, namespace, source_id, content_text)
    VALUES (new.artifact_id, new.namespace, new.source_id, COALESCE(new.content_text, ''));
END;
CREATE TRIGGER IF NOT EXISTS artifacts_ad AFTER DELETE ON artifacts BEGIN
    DELETE FROM artifacts_fts WHERE artifact_id = old.artifact_id;
END;
CREATE TRIGGER IF NOT EXISTS artifacts_au AFTER UPDATE ON artifacts BEGIN
    DELETE FROM artifacts_fts WHERE artifact_id = old.artifact_id;
    INSERT INTO artifacts_fts(artifact_id, namespace, source_id, content_text)
    VALUES (new.artifact_id, new.namespace, new.source_id, COALESCE(new.content_text, ''));
END;
