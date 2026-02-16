from __future__ import annotations

import sqlite3
from pathlib import Path

from . import db

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "migrations"


def ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at REAL NOT NULL
        )
        """
    )
    conn.commit()


def _already_applied(conn: sqlite3.Connection) -> set[str]:
    ensure_schema_migrations(conn)
    rows = db.fetch_all(conn, "SELECT id FROM schema_migrations")
    out: set[str] = set()
    for row in rows:
        if isinstance(row, sqlite3.Row):
            out.add(str(row["id"]))
        else:
            out.add(str(row[0]))
    return out


def _record_applied(conn: sqlite3.Connection, migration_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (id, applied_at) VALUES (?,?)",
        (migration_id, db.now()),
    )
    conn.commit()


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.fetch_all(conn, f"PRAGMA table_info({table})")
    for row in rows:
        name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
        if name == column:
            return True
    return False


def _namespace_migration_already_reflected(conn: sqlite3.Connection) -> bool:
    tables = [
        "entities",
        "facts",
        "episodes",
        "preferences",
        "embeddings",
        "embeddings_vec_index",
        "audit_log",
    ]
    return all(_has_column(conn, table, "namespace") for table in tables)


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    path = migrations_dir or MIGRATIONS_DIR
    ensure_schema_migrations(conn)
    applied = _already_applied(conn)
    applied_now: list[str] = []

    if not path.exists():
        return applied_now

    for migration in sorted(path.glob("*.sql")):
        migration_id = migration.name
        if migration_id in applied:
            continue

        if migration_id == "0001_add_namespace.sql" and _namespace_migration_already_reflected(conn):
            _record_applied(conn, migration_id)
            applied_now.append(migration_id)
            continue

        sql = migration.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.commit()
        except sqlite3.OperationalError as exc:
            conn.rollback()
            msg = str(exc).lower()
            if "duplicate column name" in msg and migration_id == "0001_add_namespace.sql":
                if _namespace_migration_already_reflected(conn):
                    _record_applied(conn, migration_id)
                    applied_now.append(migration_id)
                    continue
            raise

        _record_applied(conn, migration_id)
        applied_now.append(migration_id)

    return applied_now
