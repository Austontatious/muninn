from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from typing import Any

from .spaces import canonicalize_space_key


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _ensure_client(conn: sqlite3.Connection, client_name: str | None) -> str | None:
    if not client_name:
        return None
    row = conn.execute("SELECT id FROM clients WHERE name = ?;", (client_name,)).fetchone()
    if row is not None:
        return str(row["id"])
    client_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-client:{client_name}"))
    conn.execute("INSERT INTO clients (id, name) VALUES (?, ?);", (client_id, client_name))
    return client_id


def _resolve_space_id(conn: sqlite3.Connection, *, user_id: str, space_key: str) -> tuple[str, str]:
    canonical_key = canonicalize_space_key(conn, user_id=user_id, space_key=space_key)
    row = conn.execute(
        "SELECT id FROM spaces WHERE user_id = ? AND key = ? LIMIT 1;",
        (user_id, canonical_key),
    ).fetchone()
    if row is None:
        raise ValueError(f"space_not_found:{canonical_key}")
    return str(row["id"]), canonical_key


def derive_signal_key(*parts: Any) -> str:
    normalized = [_normalize_text(part) for part in parts if _normalize_text(part)]
    if not normalized:
        return ""
    raw = "|".join(normalized)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def record_interaction_event(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    event_type: str,
    actor: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    signal_type: str | None = None,
    outcome_type: str | None = None,
    scope_type: str = "project",
    scope_key: str | None = None,
    signal_key: str | None = None,
    session_id: str | None = None,
    created_by_client_name: str | None = None,
    promoted_card_id: str | None = None,
    event_id: str | None = None,
    commit: bool = True,
) -> str:
    normalized_event_type = _normalize_text(event_type)
    normalized_actor = _normalize_text(actor)
    normalized_summary = " ".join(str(summary or "").strip().split())
    if not normalized_event_type:
        raise ValueError("invalid_event_type")
    if not normalized_actor:
        raise ValueError("invalid_actor")
    if not normalized_summary:
        raise ValueError("invalid_event_summary")

    space_id, canonical_key = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    client_id = _ensure_client(conn, created_by_client_name)
    payload_json = None
    if payload is not None:
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)

    interaction_id = event_id or str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO interaction_events (
            id, user_id, space_id, session_id, event_type, actor, signal_type,
            outcome_type, scope_type, scope_key, signal_key, summary, payload_json,
            promoted_card_id, created_by_client_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            interaction_id,
            user_id,
            space_id,
            session_id,
            normalized_event_type,
            normalized_actor,
            _normalize_text(signal_type) or None,
            _normalize_text(outcome_type) or None,
            _normalize_text(scope_type) or "project",
            scope_key,
            signal_key or derive_signal_key(canonical_key, normalized_event_type, normalized_summary),
            normalized_summary,
            payload_json,
            promoted_card_id,
            client_id,
        ),
    )
    if commit:
        conn.commit()
    return interaction_id


def list_interaction_events(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    limit: int = 20,
    session_id: str | None = None,
    event_types: list[str] | None = None,
    promotion_state: str = "all",
) -> list[dict[str, Any]]:
    space_id, canonical_key = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    params: list[Any] = [user_id, space_id]
    sql = """
        SELECT ie.*, s.key AS space_key, cl.name AS created_by_client_name
        FROM interaction_events ie
        JOIN spaces s ON s.id = ie.space_id
        LEFT JOIN clients cl ON cl.id = ie.created_by_client_id
        WHERE ie.user_id = ? AND ie.space_id = ?
    """
    if session_id:
        sql = f"{sql} AND ie.session_id = ?"
        params.append(session_id)
    normalized_types = [_normalize_text(item) for item in (event_types or []) if _normalize_text(item)]
    if normalized_types:
        placeholders = ", ".join(["?"] * len(normalized_types))
        sql = f"{sql} AND ie.event_type IN ({placeholders})"
        params.extend(normalized_types)
    normalized_promotion_state = _normalize_text(promotion_state or "all") or "all"
    if normalized_promotion_state == "promoted":
        sql = f"{sql} AND ie.promoted_card_id IS NOT NULL"
    elif normalized_promotion_state == "unpromoted":
        sql = f"{sql} AND ie.promoted_card_id IS NULL"
    sql = f"{sql} ORDER BY ie.created_at DESC LIMIT ?"
    params.append(max(1, int(limit)))
    rows = conn.execute(sql, tuple(params)).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        payload_json = row["payload_json"]
        payload: dict[str, Any] | None = None
        if isinstance(payload_json, str) and payload_json.strip():
            try:
                loaded = json.loads(payload_json)
                if isinstance(loaded, dict):
                    payload = loaded
            except json.JSONDecodeError:
                payload = None
        items.append(
            {
                "id": str(row["id"]),
                "space_key": canonical_key,
                "session_id": row["session_id"],
                "event_type": str(row["event_type"]),
                "actor": str(row["actor"]),
                "signal_type": row["signal_type"],
                "outcome_type": row["outcome_type"],
                "scope_type": row["scope_type"],
                "scope_key": row["scope_key"],
                "signal_key": row["signal_key"],
                "summary": str(row["summary"]),
                "payload": payload,
                "promoted_card_id": row["promoted_card_id"],
                "created_at": row["created_at"],
                "created_by_client_name": row["created_by_client_name"],
            }
        )
    return items


def count_similar_interaction_events(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    signal_key: str,
    scope_type: str | None = None,
    scope_key: str | None = None,
    lookback_days: int = 30,
) -> int:
    if not signal_key:
        return 0
    space_id, _ = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    params: list[Any] = [user_id, space_id, signal_key, f"-{max(1, int(lookback_days))} days"]
    sql = """
        SELECT COUNT(*) AS n
        FROM interaction_events
        WHERE user_id = ?
          AND space_id = ?
          AND signal_key = ?
          AND created_at >= datetime('now', ?)
    """
    normalized_scope_type = _normalize_text(scope_type)
    if normalized_scope_type:
        sql = f"{sql} AND scope_type = ?"
        params.append(normalized_scope_type)
    if scope_key:
        sql = f"{sql} AND scope_key = ?"
        params.append(scope_key)
    row = conn.execute(sql, tuple(params)).fetchone()
    if row is None:
        return 0
    return int(row["n"] or 0)


def link_promoted_card(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
    promoted_card_id: str,
    commit: bool = True,
) -> None:
    conn.execute(
        "UPDATE interaction_events SET promoted_card_id = ? WHERE id = ?",
        (promoted_card_id, interaction_id),
    )
    if commit:
        conn.commit()
