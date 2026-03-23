from __future__ import annotations

import sqlite3
from typing import Any

from .cards import cards_merge


def _resolve_space_id(conn: sqlite3.Connection, *, user_id: str, space_key: str) -> str:
    row = conn.execute(
        "SELECT id FROM spaces WHERE user_id = ? AND key = ?",
        (user_id, space_key),
    ).fetchone()
    if row is None:
        raise ValueError(f"space_not_found:{space_key}")
    return str(row["id"])


def _build_space_filter(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str | None,
) -> tuple[str, tuple[Any, ...], str]:
    if not space_key:
        return "", tuple(), "all"
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    return " AND c.space_id = ?", (space_id,), space_key


def run_heal(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str | None = None,
    window_days: int = 30,
    apply: bool = False,
    max_actions: int = 20,
) -> dict[str, Any]:
    window_days = max(1, int(window_days))
    max_actions = max(0, int(max_actions))
    lookback = f"-{window_days} days"
    space_filter_sql, space_filter_params, scope_value = _build_space_filter(
        conn,
        user_id=user_id,
        space_key=space_key,
    )

    fingerprint_rows = conn.execute(
        f"""
        SELECT s.key AS space_key, c.kind AS kind, c.fingerprint AS fingerprint, COUNT(*) AS n
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND c.status = 'active'
          AND c.fingerprint IS NOT NULL
          AND c.fingerprint <> ''
          AND c.updated_at >= datetime('now', ?)
          {space_filter_sql}
        GROUP BY c.space_id, c.kind, c.fingerprint
        HAVING COUNT(*) > 1
        ORDER BY n DESC, c.kind ASC
        """,
        (user_id, lookback, *space_filter_params),
    ).fetchall()

    title_rows = conn.execute(
        f"""
        SELECT s.key AS space_key, c.kind AS kind, lower(trim(c.title)) AS title_norm, COUNT(*) AS n
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND c.status = 'active'
          AND c.updated_at >= datetime('now', ?)
          {space_filter_sql}
        GROUP BY c.space_id, c.kind, lower(trim(c.title))
        HAVING COUNT(*) > 1
        ORDER BY n DESC, c.kind ASC
        """,
        (user_id, lookback, *space_filter_params),
    ).fetchall()

    contradiction_rows = conn.execute(
        f"""
        SELECT s.key AS space_key, c.kind AS kind, lower(trim(c.title)) AS title_norm, COUNT(*) AS n
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND c.status = 'active'
          AND c.updated_at >= datetime('now', ?)
          {space_filter_sql}
        GROUP BY c.space_id, c.kind, lower(trim(c.title))
        HAVING COUNT(DISTINCT c.fingerprint) > 1
        ORDER BY n DESC, c.kind ASC
        """,
        (user_id, lookback, *space_filter_params),
    ).fetchall()

    stale_rows = conn.execute(
        f"""
        SELECT c.id AS card_id, s.key AS space_key, c.kind AS kind, c.title AS title, c.updated_at AS updated_at
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND c.status = 'active'
          AND c.salience < 0.35
          AND c.updated_at < datetime('now', ?)
          AND NOT EXISTS (SELECT 1 FROM card_evidence ce WHERE ce.card_id = c.id)
          {space_filter_sql}
        ORDER BY c.updated_at ASC
        LIMIT 100
        """,
        (user_id, lookback, *space_filter_params),
    ).fetchall()

    applied_actions: list[dict[str, Any]] = []
    merged_source_ids: set[str] = set()
    merge_candidates: list[tuple[str, str, str, list[str]]] = []

    for row in fingerprint_rows:
        space = str(row["space_key"])
        kind = str(row["kind"])
        fp = str(row["fingerprint"])
        card_rows = conn.execute(
            """
            SELECT c.id AS id
            FROM cards c
            JOIN spaces s ON s.id = c.space_id
            WHERE c.user_id = ?
              AND c.status = 'active'
              AND s.key = ?
              AND c.kind = ?
              AND c.fingerprint = ?
            ORDER BY c.updated_at DESC
            """,
            (user_id, space, kind, fp),
        ).fetchall()
        ids = [str(item["id"]) for item in card_rows]
        if len(ids) > 1:
            merge_candidates.append((space, kind, "fingerprint", ids))

    for row in title_rows:
        space = str(row["space_key"])
        kind = str(row["kind"])
        title_norm = str(row["title_norm"])
        card_rows = conn.execute(
            """
            SELECT c.id AS id
            FROM cards c
            JOIN spaces s ON s.id = c.space_id
            WHERE c.user_id = ?
              AND c.status = 'active'
              AND s.key = ?
              AND c.kind = ?
              AND lower(trim(c.title)) = ?
            ORDER BY c.updated_at DESC
            """,
            (user_id, space, kind, title_norm),
        ).fetchall()
        ids = [str(item["id"]) for item in card_rows]
        if len(ids) > 1:
            merge_candidates.append((space, kind, "title", ids))

    if apply and max_actions > 0:
        for space, kind, merge_reason, ids in merge_candidates:
            remaining = [cid for cid in ids if cid not in merged_source_ids]
            if len(remaining) < 2:
                continue
            primary = conn.execute(
                "SELECT title, summary, body FROM cards WHERE id = ?",
                (remaining[0],),
            ).fetchone()
            if primary is None:
                continue
            merge_result = cards_merge(
                conn,
                user_id=user_id,
                space_key=space,
                card_ids=remaining,
                kind=kind,
                title=str(primary["title"]),
                summary=str(primary["summary"]),
                body=str(primary["body"]),
                relation_type="duplicates",
                context_json={
                    "healed_from": remaining,
                    "heal_reason": merge_reason,
                    "window_days": window_days,
                },
            )
            for cid in merge_result["superseded_card_ids"]:
                merged_source_ids.add(str(cid))
            applied_actions.append(
                {
                    "action": "merge_duplicates",
                    "space_key": space,
                    "reason": merge_reason,
                    "merged_card_id": merge_result["merged_card_id"],
                    "superseded_card_ids": merge_result["superseded_card_ids"],
                }
            )
            if len(applied_actions) >= max_actions:
                break

    return {
        "window_days": window_days,
        "scope": scope_value,
        "duplicates_by_fingerprint": [dict(row) for row in fingerprint_rows],
        "duplicates_by_title": [dict(row) for row in title_rows],
        "contradictions": [dict(row) for row in contradiction_rows],
        "stale_candidates": [dict(row) for row in stale_rows],
        "actions_applied": len(applied_actions),
        "applied": applied_actions,
        "apply_mode": bool(apply),
    }
