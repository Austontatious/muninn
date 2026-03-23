PRAGMA foreign_keys = ON;

-- =========
-- users
-- =========
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  display_name TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========
-- clients
-- =========
CREATE TABLE IF NOT EXISTS clients (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========
-- spaces
-- =========
CREATE TABLE IF NOT EXISTS spaces (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  label TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, key)
);

CREATE TRIGGER IF NOT EXISTS spaces_set_updated_at
AFTER UPDATE ON spaces
FOR EACH ROW
BEGIN
  UPDATE spaces SET updated_at = datetime('now') WHERE id = OLD.id;
END;

CREATE TABLE IF NOT EXISTS space_aliases (
  user_id TEXT NOT NULL,
  alias_key TEXT NOT NULL,
  canonical_key TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(user_id, alias_key),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS space_aliases_set_updated_at
AFTER UPDATE ON space_aliases
FOR EACH ROW
BEGIN
  UPDATE space_aliases SET updated_at = datetime('now') WHERE user_id = OLD.user_id AND alias_key = OLD.alias_key;
END;

CREATE INDEX IF NOT EXISTS idx_space_aliases_canonical
ON space_aliases(user_id, canonical_key);

-- =========
-- cards
-- =========
CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  space_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','superseded','archived')),
  salience REAL NOT NULL DEFAULT 0.5
    CHECK (salience >= 0.0 AND salience <= 1.0),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  body TEXT NOT NULL,
  fingerprint TEXT,
  is_unstable INTEGER NOT NULL DEFAULT 0
    CHECK (is_unstable IN (0, 1)),
  quarantine_reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  created_by_client_id TEXT,
  source_confidence REAL
    CHECK (source_confidence IS NULL OR (source_confidence >= 0.0 AND source_confidence <= 1.0)),
  context_json TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(space_id) REFERENCES spaces(id) ON DELETE CASCADE,
  FOREIGN KEY(created_by_client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE TRIGGER IF NOT EXISTS cards_set_updated_at
AFTER UPDATE ON cards
FOR EACH ROW
BEGIN
  UPDATE cards SET updated_at = datetime('now') WHERE id = OLD.id;
END;

CREATE INDEX IF NOT EXISTS idx_cards_lens
ON cards(user_id, space_id, status, kind, updated_at DESC);

-- =========
-- cards FTS (title/summary/body)
-- =========
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
  title, summary, body,
  content='cards',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS cards_ai AFTER INSERT ON cards BEGIN
  INSERT INTO cards_fts(rowid, title, summary, body)
  VALUES (new.rowid, new.title, new.summary, new.body);
END;

CREATE TRIGGER IF NOT EXISTS cards_au AFTER UPDATE ON cards BEGIN
  INSERT INTO cards_fts(cards_fts, rowid, title, summary, body)
  VALUES ('delete', old.rowid, old.title, old.summary, old.body);
  INSERT INTO cards_fts(rowid, title, summary, body)
  VALUES (new.rowid, new.title, new.summary, new.body);
END;

CREATE TRIGGER IF NOT EXISTS cards_ad AFTER DELETE ON cards BEGIN
  INSERT INTO cards_fts(cards_fts, rowid, title, summary, body)
  VALUES ('delete', old.rowid, old.title, old.summary, old.body);
END;

-- =========
-- evidence
-- =========
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  space_id TEXT NOT NULL,
  type TEXT NOT NULL
    CHECK (type IN ('chat','log','diff','file','url','commit','test')),
  ref TEXT,
  excerpt TEXT,
  blob_path TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  created_by_client_id TEXT,
  meta_json TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(space_id) REFERENCES spaces(id) ON DELETE CASCADE,
  FOREIGN KEY(created_by_client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_lens
ON evidence(user_id, space_id, type, created_at DESC);

-- =========
-- joins
-- =========
CREATE TABLE IF NOT EXISTS card_evidence (
  card_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  PRIMARY KEY(card_id, evidence_id),
  FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
  FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS card_relations (
  from_card_id TEXT NOT NULL,
  to_card_id TEXT NOT NULL,
  relation_type TEXT NOT NULL
    CHECK (relation_type IN ('supersedes','duplicates','contradicts','refines')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(from_card_id, to_card_id, relation_type),
  FOREIGN KEY(from_card_id) REFERENCES cards(id) ON DELETE CASCADE,
  FOREIGN KEY(to_card_id) REFERENCES cards(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_card_relations_from
ON card_relations(from_card_id, relation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_card_relations_to
ON card_relations(to_card_id, relation_type, created_at DESC);

-- =========
-- tags
-- =========
CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS card_tags (
  card_id TEXT NOT NULL,
  tag_id TEXT NOT NULL,
  PRIMARY KEY(card_id, tag_id),
  FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- =========
-- interaction events
-- =========
CREATE TABLE IF NOT EXISTS interaction_events (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  space_id TEXT NOT NULL,
  session_id TEXT,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  signal_type TEXT,
  outcome_type TEXT,
  scope_type TEXT NOT NULL DEFAULT 'project',
  scope_key TEXT,
  signal_key TEXT,
  summary TEXT NOT NULL,
  payload_json TEXT,
  promoted_card_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  created_by_client_id TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(space_id) REFERENCES spaces(id) ON DELETE CASCADE,
  FOREIGN KEY(created_by_client_id) REFERENCES clients(id) ON DELETE SET NULL,
  FOREIGN KEY(promoted_card_id) REFERENCES cards(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_events_lens
ON interaction_events(user_id, space_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_interaction_events_signal
ON interaction_events(user_id, space_id, signal_key, created_at DESC);
