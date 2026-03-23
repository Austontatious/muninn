import sqlite3

import pytest


def _create_legacy_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE facts (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            confidence REAL NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE episodes (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            start_ts REAL,
            end_ts REAL,
            confidence REAL NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE preferences (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL NOT NULL,
            decay_ts REAL,
            provenance_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE embeddings (
            item_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector_blob BLOB NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE embeddings_vec_index (
            item_id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            rowid INTEGER NOT NULL,
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE audit_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO facts (id, subject_id, predicate, object, confidence, provenance_json, created_at) VALUES (?,?,?,?,?,?,?)",
        ("fact_1", "ent_user", "topic", "alpha", 0.9, "{}", 1.0),
    )
    conn.commit()


def test_migrate_adds_namespace_and_defaults_existing_rows(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    _create_legacy_schema(conn)

    monkeypatch.setenv("MUNINN_DB_PATH", str(db_path))

    from muninn.migrations import apply_migrations

    applied = apply_migrations(conn)
    assert "0001_add_namespace.sql" in applied
    assert "0003_cardex_v1.sql" in applied
    assert "0004_meaningful_memory.sql" in applied

    row = conn.execute("SELECT namespace FROM facts WHERE id = 'fact_1'").fetchone()
    assert row is not None
    assert row[0] == "default"

    cols = [r[1] for r in conn.execute("PRAGMA table_info(embeddings_vec_index)").fetchall()]
    assert "namespace" in cols

    cards_cols = [r[1] for r in conn.execute("PRAGMA table_info(cards)").fetchall()]
    assert "card_id" in cards_cols
    assert "summary" in cards_cols

    # Proposal status invariant enforced
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute(
            """
            INSERT INTO proposals (proposal_id, namespace, proposal_type, payload_json, status, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            ("prop_bad", "default", "create_card", "{}", "invalid_status", 1.0),
        )
        conn.commit()
    conn.rollback()

    # Sensitivity tier invariant enforced
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute(
            """
            INSERT INTO cards
                (card_id, namespace, type, title, summary, details_json, tags_json, created_at, updated_at, salience,
                 confidence, sensitivity_tier, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "card_bad",
                "default",
                "fact",
                "bad",
                "bad",
                "{}",
                "[]",
                1.0,
                1.0,
                0.5,
                0.7,
                99,
                "active",
            ),
        )
        conn.commit()
    conn.rollback()

    # Evidence status invariant enforced
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute(
            """
            INSERT INTO evidence_state
                (namespace, owner_type, owner_id, status, score, reason_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            ("default", "artifact", "art_bad", "invalid_status", 0.0, "{}", 1.0, 1.0),
        )
        conn.commit()
    conn.rollback()

    # Index job status invariant enforced
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute(
            """
            INSERT INTO index_jobs
                (job_id, namespace, owner_type, owner_id, modality, priority, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            ("idx_bad", "default", "artifact", "art_bad", "text", 10, "invalid_status", 1.0, 1.0),
        )
        conn.commit()
    conn.rollback()
