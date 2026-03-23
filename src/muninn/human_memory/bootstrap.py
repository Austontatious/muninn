from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from ..telemetry import emit_event, telemetry_context

DEFAULT_USER_ID = "ent_local_user"
DEFAULT_CLIENT_NAME = "codex-vscode"
GLOBAL_SPACE_KEY = "global"


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "migrations" / "0001_init.sql"


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        if str(row["name"]) == column:
            return True
    return False


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1;",
        (table,),
    ).fetchone()
    return row is not None


def _db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list;").fetchone()
    if row is None:
        return "<unknown>"
    path = str(row["file"] or "").strip()
    return path or ":memory:"


def _schema_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version;").fetchone()
    if row is None:
        return 0
    return int(row[0] or 0)


def _emit_bootstrap_event(
    event: str,
    *,
    correlation_id: str | None,
    stage: str,
    db_target: str,
    **payload: object,
) -> None:
    emit_event(
        {
            "event": event,
            "module": "muninn.human_memory.bootstrap",
            "stage": stage,
            "correlation_id": correlation_id,
            "db_target": db_target,
            **telemetry_context(),
            **payload,
        },
        stream_prefix="MUNINN_EVENT",
        stream="stderr",
    )


def _apply_self_healing_compat(conn: sqlite3.Connection) -> list[str]:
    # Backfill additive schema changes for existing local DBs.
    applied: list[str] = []
    if not _has_column(conn, "cards", "fingerprint"):
        conn.execute("ALTER TABLE cards ADD COLUMN fingerprint TEXT;")
        applied.append("cards.fingerprint")
    if not _has_column(conn, "cards", "is_unstable"):
        conn.execute("ALTER TABLE cards ADD COLUMN is_unstable INTEGER NOT NULL DEFAULT 0;")
        applied.append("cards.is_unstable")
    if not _has_column(conn, "cards", "quarantine_reason"):
        conn.execute("ALTER TABLE cards ADD COLUMN quarantine_reason TEXT;")
        applied.append("cards.quarantine_reason")

    compat_tables = {
        "card_relations": _table_exists(conn, "card_relations"),
        "space_aliases": _table_exists(conn, "space_aliases"),
        "interaction_events": _table_exists(conn, "interaction_events"),
    }

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_cards_fingerprint_active
        ON cards(user_id, space_id, kind, fingerprint)
        WHERE status = 'active' AND fingerprint IS NOT NULL;

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
          UPDATE space_aliases
          SET updated_at = datetime('now')
          WHERE user_id = OLD.user_id AND alias_key = OLD.alias_key;
        END;

        CREATE INDEX IF NOT EXISTS idx_space_aliases_canonical
        ON space_aliases(user_id, canonical_key);

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
        """
    )
    for table_name, existed in compat_tables.items():
        if not existed and _table_exists(conn, table_name):
            applied.append(f"table:{table_name}")
    conn.commit()
    return applied


def open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def apply_init_schema(
    conn: sqlite3.Connection,
    schema_path: str | Path | None = None,
    *,
    correlation_id: str | None = None,
) -> dict[str, object]:
    path = Path(schema_path) if schema_path is not None else _default_schema_path()
    db_target = _db_path(conn)
    before_version = _schema_user_version(conn)
    _emit_bootstrap_event(
        "human_memory_schema",
        correlation_id=correlation_id,
        stage="start",
        db_target=db_target,
        schema_path=str(path),
        schema_user_version=before_version,
        bootstrap_path="apply_init_schema",
    )
    try:
        sql = path.read_text(encoding="utf-8")
        conn.executescript(sql)
        if _schema_user_version(conn) < 1:
            conn.execute("PRAGMA user_version = 1;")
        conn.commit()
        compat_changes = _apply_self_healing_compat(conn)
        after_version = _schema_user_version(conn)
        report = {
            "db_target": db_target,
            "schema_path": str(path),
            "schema_user_version_before": before_version,
            "schema_user_version_after": after_version,
            "compat_changes": compat_changes,
            "init_result": "ok",
        }
        _emit_bootstrap_event(
            "human_memory_schema",
            correlation_id=correlation_id,
            stage="finish",
            **report,
        )
        return report
    except Exception as exc:
        _emit_bootstrap_event(
            "human_memory_schema",
            correlation_id=correlation_id,
            stage="failure",
            db_target=db_target,
            schema_path=str(path),
            schema_user_version=before_version,
            bootstrap_path="apply_init_schema",
            init_result="error",
            error_class=type(exc).__name__,
            error_text=str(exc),
        )
        raise


def bootstrap_defaults(
    conn: sqlite3.Connection,
    *,
    correlation_id: str | None = None,
) -> dict[str, object]:
    db_target = _db_path(conn)
    _emit_bootstrap_event(
        "human_memory_bootstrap",
        correlation_id=correlation_id,
        stage="start",
        db_target=db_target,
        bootstrap_path="bootstrap_defaults",
    )
    try:
        user_insert = conn.execute(
            "INSERT OR IGNORE INTO users (id, display_name) VALUES (?, ?);",
            (DEFAULT_USER_ID, "Local User"),
        )
        created_user = int(user_insert.rowcount or 0) > 0

        client_row = conn.execute(
            "SELECT id FROM clients WHERE name = ?;",
            (DEFAULT_CLIENT_NAME,),
        ).fetchone()
        created_client = False
        if client_row is None:
            client_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-client:{DEFAULT_CLIENT_NAME}"))
            conn.execute(
                "INSERT INTO clients (id, name) VALUES (?, ?);",
                (client_id, DEFAULT_CLIENT_NAME),
            )
            created_client = True

        global_space_id = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-space:{DEFAULT_USER_ID}:{GLOBAL_SPACE_KEY}")
        )
        global_before = conn.execute(
            "SELECT 1 FROM spaces WHERE user_id = ? AND key = ? LIMIT 1;",
            (DEFAULT_USER_ID, GLOBAL_SPACE_KEY),
        ).fetchone()
        conn.execute(
            """
            INSERT OR IGNORE INTO spaces (id, user_id, key, label, meta_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (global_space_id, DEFAULT_USER_ID, GLOBAL_SPACE_KEY, "Global", '{"system":"muninn"}'),
        )

        conn.commit()
        report = {
            "db_target": db_target,
            "bootstrap_path": "bootstrap_defaults",
            "created_user": created_user,
            "created_client": created_client,
            "created_global_space": global_before is None,
            "init_result": "ok",
        }
        _emit_bootstrap_event(
            "human_memory_bootstrap",
            correlation_id=correlation_id,
            stage="finish",
            **report,
        )
        return report
    except Exception as exc:
        _emit_bootstrap_event(
            "human_memory_bootstrap",
            correlation_id=correlation_id,
            stage="failure",
            db_target=db_target,
            bootstrap_path="bootstrap_defaults",
            init_result="error",
            error_class=type(exc).__name__,
            error_text=str(exc),
        )
        raise
