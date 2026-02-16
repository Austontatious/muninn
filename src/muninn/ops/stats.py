from __future__ import annotations

import sqlite3
from typing import Any

from .. import __version__, db
from ..config import readonly, retrieval_mode, vec_backend
from ..vector import store as vector_store

TABLE_COUNT_KEYS = [
    ("entities", "entities"),
    ("facts", "facts"),
    ("episodes", "episodes"),
    ("preferences", "preferences"),
    ("embeddings", "embeddings"),
    ("audit_log", "audit_log"),
]


def _safe_count(
    conn: sqlite3.Connection,
    table: str,
    namespace: str | None,
    errors: list[str],
) -> int | None:
    try:
        if namespace is None:
            row = db.fetch_one(conn, f"SELECT count(*) AS n FROM {table}")
        else:
            row = db.fetch_one(conn, f"SELECT count(*) AS n FROM {table} WHERE namespace = ?", (namespace,))
    except sqlite3.OperationalError as exc:
        errors.append(f"{table}:{exc}")
        return None

    if not row:
        return 0
    return int(row["n"])


def _safe_pending_status_counts(
    conn: sqlite3.Connection,
    namespace: str | None,
    errors: list[str],
) -> dict[str, int]:
    sql = "SELECT status, count(*) AS n FROM pending_candidates"
    params: tuple[object, ...] = ()
    if namespace is not None:
        sql += " WHERE namespace = ?"
        params = (namespace,)
    sql += " GROUP BY status"

    try:
        rows = db.fetch_all(conn, sql, params)
    except sqlite3.OperationalError as exc:
        errors.append(f"pending_candidates:{exc}")
        return {}

    out = {"pending": 0, "accepted": 0, "rejected": 0, "expired": 0}
    for row in rows:
        out[str(row["status"])] = int(row["n"])
    return out


def _safe_migrations(conn: sqlite3.Connection, errors: list[str]) -> dict[str, Any]:
    try:
        count_row = db.fetch_one(conn, "SELECT count(*) AS n FROM schema_migrations")
        last_row = db.fetch_one(
            conn,
            "SELECT id FROM schema_migrations ORDER BY applied_at DESC LIMIT 1",
        )
    except sqlite3.OperationalError as exc:
        errors.append(f"schema_migrations:{exc}")
        return {"applied_count": 0, "last_applied": None}

    return {
        "applied_count": int(count_row["n"]) if count_row else 0,
        "last_applied": str(last_row["id"]) if last_row else None,
    }


def collect_stats(namespace: str | None, api_version: str) -> dict[str, Any]:
    conn = db.connect()
    errors: list[str] = []

    backend_config, sqlite_loaded, effective_backend = vector_store.effective_backend()

    counts: dict[str, Any] = {"namespace": namespace}
    for table, key in TABLE_COUNT_KEYS:
        counts[key] = _safe_count(conn, table, namespace, errors)
    counts["pending_candidates_by_status"] = _safe_pending_status_counts(conn, namespace, errors)

    migrations = _safe_migrations(conn, errors)

    conn.close()

    out = {
        "versions": {
            "app_version": __version__,
            "api_version": api_version,
        },
        "config": {
            "readonly": readonly(),
            "retrieval_mode": retrieval_mode(),
            "vec_backend_config": vec_backend(),
            "sqlite_vec_loaded": sqlite_loaded,
            "effective_backend": effective_backend,
            "debug_backend_config": backend_config,
        },
        "migrations": migrations,
        "counts": counts,
    }
    if errors:
        out["errors"] = errors
    return out
