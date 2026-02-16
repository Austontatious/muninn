from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .. import db


def _select_ids(conn: sqlite3.Connection, sql: str, params: tuple, limit: int) -> list[str]:
    rows = db.fetch_all(conn, f"{sql} LIMIT ?", params + (limit,))
    return [str(row["id"]) for row in rows]


def _delete_by_ids(conn: sqlite3.Connection, table: str, ids: Iterable[str], dry_run: bool) -> int:
    ids_list = list(ids)
    if dry_run or not ids_list:
        return 0

    placeholders = ",".join("?" for _ in ids_list)
    db.execute_one(conn, f"DELETE FROM {table} WHERE id IN ({placeholders})", tuple(ids_list))
    return len(ids_list)


def cleanup_pending(
    conn: sqlite3.Connection,
    namespace: str | None,
    statuses: list[str],
    cutoff_ts: float,
    limit: int,
    dry_run: bool,
) -> tuple[int, int]:
    if not statuses:
        return 0, 0

    status_placeholders = ",".join("?" for _ in statuses)
    sql = (
        "SELECT id FROM pending_candidates "
        f"WHERE status IN ({status_placeholders}) AND created_at < ?"
    )
    params: list[object] = [*statuses, cutoff_ts]
    if namespace is not None:
        sql += " AND namespace = ?"
        params.append(namespace)
    sql += " ORDER BY created_at ASC"

    ids = _select_ids(conn, sql, tuple(params), limit)
    deleted = _delete_by_ids(conn, "pending_candidates", ids, dry_run)
    return deleted, len(ids)


def cleanup_decisions(
    conn: sqlite3.Connection,
    namespace: str | None,
    cutoff_ts: float | None,
    limit: int,
    dry_run: bool,
) -> tuple[int, int]:
    where_parts: list[str] = []
    params: list[object] = []

    if namespace is not None:
        where_parts.append("d.namespace = ?")
        params.append(namespace)

    conditions = [
        "NOT EXISTS (SELECT 1 FROM pending_candidates p WHERE p.id = d.pending_id AND p.namespace = d.namespace)"
    ]
    if cutoff_ts is not None:
        conditions.append("d.decided_at < ?")
        params.append(cutoff_ts)

    where_parts.append("(" + " OR ".join(conditions) + ")")

    sql = "SELECT d.id FROM candidate_decisions d WHERE " + " AND ".join(where_parts)
    sql += " ORDER BY d.decided_at ASC"

    ids = _select_ids(conn, sql, tuple(params), limit)
    deleted = _delete_by_ids(conn, "candidate_decisions", ids, dry_run)
    return deleted, len(ids)


def cleanup_audit(
    conn: sqlite3.Connection,
    namespace: str | None,
    cutoff_ts: float,
    limit: int,
    dry_run: bool,
) -> tuple[int, int]:
    sql = "SELECT id FROM audit_log WHERE created_at < ?"
    params: list[object] = [cutoff_ts]
    if namespace is not None:
        sql += " AND namespace = ?"
        params.append(namespace)
    sql += " ORDER BY created_at ASC"

    ids = _select_ids(conn, sql, tuple(params), limit)
    deleted = _delete_by_ids(conn, "audit_log", ids, dry_run)
    return deleted, len(ids)
