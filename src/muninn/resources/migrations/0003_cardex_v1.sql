BEGIN;

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

COMMIT;
