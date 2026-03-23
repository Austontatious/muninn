from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from typing import Any

from .spaces import canonicalize_space_key

ALLOWED_RELATION_TYPES = {"supersedes", "duplicates", "contradicts", "refines"}
_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _normalize_tag_names(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        name = str(raw).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _normalize_fts_query(query: str) -> str:
    text = str(query or "").strip()
    if not text:
        raise ValueError("invalid_search_query:empty")

    # FTS5 query syntax is strict; tokenize to avoid parser failures on punctuation-heavy input.
    tokens = [token.lower() for token in _FTS_TOKEN_RE.findall(text)]
    if not tokens:
        raise ValueError("invalid_search_query:no_terms")

    return " ".join(tokens[:32])


def _card_fingerprint(kind: str, title: str, summary: str) -> str:
    normalized_kind = _normalize_text(kind)
    normalized_title = _normalize_text(title)
    normalized_summary = _normalize_text(summary)
    base = normalized_title or normalized_summary or "untitled"
    summary_hash = hashlib.sha256(normalized_summary.encode("utf-8")).hexdigest()[:16]
    raw = f"{normalized_kind}|{base}|{summary_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _load_tags_by_card_ids(conn: sqlite3.Connection, card_ids: list[str]) -> dict[str, list[str]]:
    if not card_ids:
        return {}
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = conn.execute(
        f"""
        SELECT ct.card_id AS card_id, t.name AS tag_name
        FROM card_tags ct
        JOIN tags t ON t.id = ct.tag_id
        WHERE ct.card_id IN ({placeholders})
        ORDER BY t.name ASC
        """,
        tuple(card_ids),
    ).fetchall()
    out: dict[str, list[str]] = {cid: [] for cid in card_ids}
    for row in rows:
        cid = str(row["card_id"])
        out.setdefault(cid, []).append(str(row["tag_name"]))
    return out


def _load_evidence_counts_by_card_ids(conn: sqlite3.Connection, card_ids: list[str]) -> dict[str, int]:
    if not card_ids:
        return {}
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = conn.execute(
        f"""
        SELECT card_id, COUNT(*) AS n
        FROM card_evidence
        WHERE card_id IN ({placeholders})
        GROUP BY card_id
        """,
        tuple(card_ids),
    ).fetchall()
    out: dict[str, int] = {cid: 0 for cid in card_ids}
    for row in rows:
        out[str(row["card_id"])] = int(row["n"] or 0)
    return out


def _sync_card_tags(conn: sqlite3.Connection, card_id: str, tags: list[str] | None) -> None:
    if tags is None:
        return

    normalized = _normalize_tag_names(tags)
    conn.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
    for name in normalized:
        tag_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-tag:{name}"))
        conn.execute(
            "INSERT OR IGNORE INTO tags (id, name) VALUES (?, ?);",
            (tag_id, name),
        )
        row = conn.execute("SELECT id FROM tags WHERE name = ?;", (name,)).fetchone()
        if row is None:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?);",
            (card_id, str(row["id"])),
        )


def _ensure_client(conn: sqlite3.Connection, client_name: str | None) -> str | None:
    if not client_name:
        return None
    row = conn.execute("SELECT id FROM clients WHERE name = ?;", (client_name,)).fetchone()
    if row:
        return str(row["id"])
    client_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-client:{client_name}"))
    conn.execute(
        "INSERT INTO clients (id, name) VALUES (?, ?);",
        (client_id, client_name),
    )
    return client_id


def _resolve_space_id(conn: sqlite3.Connection, user_id: str, space_key: str) -> str:
    canonical_key = canonicalize_space_key(conn, user_id=user_id, space_key=space_key)
    row = conn.execute(
        "SELECT id FROM spaces WHERE user_id = ? AND key = ?;",
        (user_id, canonical_key),
    ).fetchone()
    if row is None:
        raise ValueError(f"space_not_found:{canonical_key}")
    return str(row["id"])


def _validate_relation_type(relation_type: str) -> str:
    normalized = _normalize_text(relation_type)
    if normalized not in ALLOWED_RELATION_TYPES:
        allowed = ",".join(sorted(ALLOWED_RELATION_TYPES))
        raise ValueError(f"invalid_relation_type:{normalized}:allowed={allowed}")
    return normalized


def _find_active_card_by_fingerprint(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_id: str,
    kind: str,
    fingerprint: str,
) -> str | None:
    row = conn.execute(
        """
        SELECT id
        FROM cards
        WHERE user_id = ?
          AND space_id = ?
          AND kind = ?
          AND status = 'active'
          AND fingerprint = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (user_id, space_id, kind, fingerprint),
    ).fetchone()
    if row is None:
        return None
    return str(row["id"])


def _record_relation(
    conn: sqlite3.Connection,
    *,
    from_card_id: str,
    to_card_id: str,
    relation_type: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO card_relations (from_card_id, to_card_id, relation_type)
        VALUES (?, ?, ?)
        """,
        (from_card_id, to_card_id, relation_type),
    )


def _refresh_unstable_flag(
    conn: sqlite3.Connection,
    *,
    card_id: str,
    lookback_days: int = 14,
    churn_threshold: int = 3,
) -> None:
    interval = f"-{max(1, int(lookback_days))} days"
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM card_relations
        WHERE from_card_id = ?
          AND relation_type IN ('supersedes', 'duplicates')
          AND created_at >= datetime('now', ?)
        """,
        (card_id, interval),
    ).fetchone()
    churn = int(row["n"] or 0) if row is not None else 0
    unstable = 1 if churn >= max(1, int(churn_threshold)) else 0
    reason = f"relation_churn:{churn}/{lookback_days}d" if unstable else None
    conn.execute(
        "UPDATE cards SET is_unstable = ?, quarantine_reason = ? WHERE id = ?",
        (unstable, reason, card_id),
    )


def _collect_card_rows(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_id: str,
    card_ids: list[str],
) -> list[sqlite3.Row]:
    if not card_ids:
        return []
    placeholders = ", ".join(["?"] * len(card_ids))
    params = [user_id, space_id, *card_ids]
    rows = conn.execute(
        f"""
        SELECT *
        FROM cards
        WHERE user_id = ?
          AND space_id = ?
          AND id IN ({placeholders})
        """,
        tuple(params),
    ).fetchall()
    return list(rows)


def cards_recent(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    kinds: list[str] | None = None,
    status: str = "active",
    tags: list[str] | None = None,
    limit: int = 20,
    include_body: bool = False,
    include_context: bool = False,
) -> list[dict[str, Any]]:
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    select_columns = (
        "c.id, s.key AS space_key, c.kind, c.status, c.salience, c.title, c.summary, "
        "c.created_at, c.updated_at, c.is_unstable, c.quarantine_reason"
    )
    if include_body:
        select_columns = f"{select_columns}, c.body"
    if include_context:
        select_columns = (
            f"{select_columns}, c.source_confidence, c.context_json, cl.name AS created_by_client_name"
        )

    params: list[Any] = [user_id, space_id, status]
    sql = f"""
        SELECT {select_columns}
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        LEFT JOIN clients cl ON cl.id = c.created_by_client_id
        WHERE c.user_id = ?
          AND c.space_id = ?
          AND c.status = ?
    """
    if kinds:
        placeholders = ", ".join(["?"] * len(kinds))
        sql = f"{sql} AND c.kind IN ({placeholders})"
        params.extend(kinds)
    normalized_tags = _normalize_tag_names(tags)
    if normalized_tags:
        placeholders = ", ".join(["?"] * len(normalized_tags))
        sql = (
            f"{sql} AND EXISTS ("
            "SELECT 1 FROM card_tags ct "
            "JOIN tags t ON t.id = ct.tag_id "
            "WHERE ct.card_id = c.id "
            f"AND t.name IN ({placeholders})"
            ")"
        )
        params.extend(normalized_tags)
    sql = f"{sql} ORDER BY c.is_unstable ASC, c.updated_at DESC LIMIT ?"
    params.append(max(1, int(limit)))
    rows = conn.execute(sql, tuple(params)).fetchall()
    items = [dict(row) for row in rows]
    card_ids = [str(item["id"]) for item in items]
    tags_by_card = _load_tags_by_card_ids(conn, card_ids)
    evidence_counts = _load_evidence_counts_by_card_ids(conn, card_ids)
    for item in items:
        card_id = str(item["id"])
        evidence_count = int(evidence_counts.get(card_id, 0))
        item["tags"] = tags_by_card.get(card_id, [])
        item["evidence_count"] = evidence_count
        item["has_evidence"] = evidence_count > 0
    return items


def cards_search(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    query: str,
    kinds: list[str] | None = None,
    status: str = "active",
    tags: list[str] | None = None,
    limit: int = 20,
    include_body: bool = False,
    include_context: bool = False,
) -> list[dict[str, Any]]:
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    normalized_query = _normalize_fts_query(query)
    select_columns = (
        "c.id, s.key AS space_key, c.kind, c.status, c.salience, c.title, c.summary, "
        "c.created_at, c.updated_at, c.is_unstable, c.quarantine_reason"
    )
    if include_body:
        select_columns = f"{select_columns}, c.body"
    if include_context:
        select_columns = (
            f"{select_columns}, c.source_confidence, c.context_json, cl.name AS created_by_client_name"
        )

    params: list[Any] = [user_id, space_id, status, normalized_query]
    sql = f"""
        SELECT {select_columns}, bm25(cards_fts) AS score
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        LEFT JOIN clients cl ON cl.id = c.created_by_client_id
        JOIN cards_fts ON cards_fts.rowid = c.rowid
        WHERE c.user_id = ?
          AND c.space_id = ?
          AND c.status = ?
          AND cards_fts MATCH ?
    """
    if kinds:
        placeholders = ", ".join(["?"] * len(kinds))
        sql = f"{sql} AND c.kind IN ({placeholders})"
        params.extend(kinds)
    normalized_tags = _normalize_tag_names(tags)
    if normalized_tags:
        placeholders = ", ".join(["?"] * len(normalized_tags))
        sql = (
            f"{sql} AND EXISTS ("
            "SELECT 1 FROM card_tags ct "
            "JOIN tags t ON t.id = ct.tag_id "
            "WHERE ct.card_id = c.id "
            f"AND t.name IN ({placeholders})"
            ")"
        )
        params.extend(normalized_tags)
    sql = f"{sql} ORDER BY c.is_unstable ASC, score ASC, c.updated_at DESC LIMIT ?"
    params.append(max(1, int(limit)))
    rows = conn.execute(sql, tuple(params)).fetchall()
    items = [dict(row) for row in rows]
    card_ids = [str(item["id"]) for item in items]
    tags_by_card = _load_tags_by_card_ids(conn, card_ids)
    evidence_counts = _load_evidence_counts_by_card_ids(conn, card_ids)
    for item in items:
        card_id = str(item["id"])
        evidence_count = int(evidence_counts.get(card_id, 0))
        item["tags"] = tags_by_card.get(card_id, [])
        item["evidence_count"] = evidence_count
        item["has_evidence"] = evidence_count > 0
    return items


def cards_search_count(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    query: str,
    kinds: list[str] | None = None,
    status: str = "active",
    tags: list[str] | None = None,
) -> int:
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    normalized_query = _normalize_fts_query(query)
    params: list[Any] = [user_id, space_id, status, normalized_query]
    sql = """
        SELECT COUNT(*) AS n
        FROM cards c
        JOIN cards_fts ON cards_fts.rowid = c.rowid
        WHERE c.user_id = ?
          AND c.space_id = ?
          AND c.status = ?
          AND cards_fts MATCH ?
    """
    if kinds:
        placeholders = ", ".join(["?"] * len(kinds))
        sql = f"{sql} AND c.kind IN ({placeholders})"
        params.extend(kinds)
    normalized_tags = _normalize_tag_names(tags)
    if normalized_tags:
        placeholders = ", ".join(["?"] * len(normalized_tags))
        sql = (
            f"{sql} AND EXISTS ("
            "SELECT 1 FROM card_tags ct "
            "JOIN tags t ON t.id = ct.tag_id "
            "WHERE ct.card_id = c.id "
            f"AND t.name IN ({placeholders})"
            ")"
        )
        params.extend(normalized_tags)
    row = conn.execute(sql, tuple(params)).fetchone()
    if row is None:
        return 0
    return int(row["n"] or 0)


def card_upsert(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    kind: str,
    title: str,
    summary: str,
    body: str,
    status: str = "active",
    salience: float = 0.5,
    tags: list[str] | None = None,
    created_by_client_name: str | None = None,
    source_confidence: float | None = None,
    context_json: dict[str, Any] | None = None,
    card_id: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    dedupe_by_fingerprint: bool = True,
    commit: bool = True,
) -> str:
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    client_id = _ensure_client(conn, created_by_client_name)
    fingerprint = _card_fingerprint(kind, title, summary)
    cid = card_id
    if cid is None and dedupe_by_fingerprint:
        cid = _find_active_card_by_fingerprint(
            conn,
            user_id=user_id,
            space_id=space_id,
            kind=kind,
            fingerprint=fingerprint,
        )
    if cid is None:
        cid = str(uuid.uuid4())

    ctx_json = None
    if context_json is not None:
        ctx_json = json.dumps(context_json, separators=(",", ":"), ensure_ascii=True)

    existing = conn.execute(
        "SELECT id FROM cards WHERE id = ?;",
        (cid,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO cards
                (id, user_id, space_id, kind, status, salience, title, summary, body, fingerprint,
                 created_by_client_id, source_confidence, context_json, is_unstable, quarantine_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                cid,
                user_id,
                space_id,
                kind,
                status,
                float(salience),
                title,
                summary,
                body,
                fingerprint,
                client_id,
                source_confidence,
                ctx_json,
                0,
                None,
            ),
        )
    else:
        conn.execute(
            """
            UPDATE cards
            SET user_id = ?,
                space_id = ?,
                kind = ?,
                status = ?,
                salience = ?,
                title = ?,
                summary = ?,
                body = ?,
                fingerprint = ?,
                created_by_client_id = ?,
                source_confidence = ?,
                context_json = ?
            WHERE id = ?
            """,
            (
                user_id,
                space_id,
                kind,
                status,
                float(salience),
                title,
                summary,
                body,
                fingerprint,
                client_id,
                source_confidence,
                ctx_json,
                cid,
            ),
        )

    _sync_card_tags(conn, cid, tags)

    if evidence_refs:
        for ref in evidence_refs:
            evidence_type = str(ref.get("type") or "").strip()
            if not evidence_type:
                continue
            evidence_id = str(ref.get("id") or "") or str(uuid.uuid4())
            evidence_client_name = ref.get("created_by_client_name") or created_by_client_name
            evidence_client_id = _ensure_client(
                conn, str(evidence_client_name) if evidence_client_name else None
            )
            meta = ref.get("meta_json")
            meta_json = None
            if isinstance(meta, dict):
                meta_json = json.dumps(meta, separators=(",", ":"), ensure_ascii=True)
            elif isinstance(meta, str):
                meta_json = meta

            conn.execute(
                """
                INSERT OR REPLACE INTO evidence
                    (id, user_id, space_id, type, ref, excerpt, blob_path, created_by_client_id, meta_json)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    evidence_id,
                    user_id,
                    space_id,
                    evidence_type,
                    ref.get("ref"),
                    ref.get("excerpt"),
                    ref.get("blob_path"),
                    evidence_client_id,
                    meta_json,
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO card_evidence (card_id, evidence_id) VALUES (?, ?)",
                (cid, evidence_id),
            )

    if commit:
        conn.commit()
    return cid


def card_supersede(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    old_card_id: str,
    kind: str,
    title: str,
    summary: str,
    body: str,
    status: str = "active",
    salience: float = 0.5,
    tags: list[str] | None = None,
    created_by_client_name: str | None = None,
    source_confidence: float | None = None,
    context_json: dict[str, Any] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    relation_type: str = "supersedes",
) -> dict[str, Any]:
    normalized_relation = _validate_relation_type(relation_type)
    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    old_row = conn.execute(
        """
        SELECT id
        FROM cards
        WHERE id = ? AND user_id = ? AND space_id = ?
        LIMIT 1
        """,
        (old_card_id, user_id, space_id),
    ).fetchone()
    if old_row is None:
        raise ValueError(f"card_not_found:{old_card_id}")

    conn.execute("SAVEPOINT card_supersede")
    try:
        conn.execute("UPDATE cards SET status = 'superseded' WHERE id = ?", (old_card_id,))
        new_card_id = card_upsert(
            conn,
            user_id=user_id,
            space_key=space_key,
            kind=kind,
            title=title,
            summary=summary,
            body=body,
            status=status,
            salience=salience,
            tags=tags,
            created_by_client_name=created_by_client_name,
            source_confidence=source_confidence,
            context_json=context_json,
            evidence_refs=evidence_refs,
            dedupe_by_fingerprint=False,
            commit=False,
        )
        _record_relation(
            conn,
            from_card_id=old_card_id,
            to_card_id=new_card_id,
            relation_type=normalized_relation,
        )
        _refresh_unstable_flag(conn, card_id=old_card_id)
        conn.execute("RELEASE SAVEPOINT card_supersede")
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT card_supersede")
        conn.execute("RELEASE SAVEPOINT card_supersede")
        conn.rollback()
        raise

    return {
        "old_card_id": old_card_id,
        "new_card_id": new_card_id,
        "relation_type": normalized_relation,
    }


def cards_merge(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    card_ids: list[str],
    kind: str,
    title: str,
    summary: str,
    body: str,
    status: str = "active",
    salience: float = 0.5,
    tags: list[str] | None = None,
    created_by_client_name: str | None = None,
    source_confidence: float | None = None,
    context_json: dict[str, Any] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    relation_type: str = "duplicates",
) -> dict[str, Any]:
    normalized_relation = _validate_relation_type(relation_type)
    deduped_ids: list[str] = []
    seen: set[str] = set()
    for raw in card_ids:
        card_id = str(raw).strip()
        if not card_id or card_id in seen:
            continue
        seen.add(card_id)
        deduped_ids.append(card_id)
    if len(deduped_ids) < 2:
        raise ValueError("merge_requires_two_or_more_cards")

    space_id = _resolve_space_id(conn, user_id=user_id, space_key=space_key)
    rows = _collect_card_rows(
        conn,
        user_id=user_id,
        space_id=space_id,
        card_ids=deduped_ids,
    )
    found_ids = {str(row["id"]) for row in rows}
    missing = [cid for cid in deduped_ids if cid not in found_ids]
    if missing:
        raise ValueError(f"cards_not_found:{','.join(missing)}")

    merged_tags = tags
    if merged_tags is None:
        tags_by_card = _load_tags_by_card_ids(conn, deduped_ids)
        merged_tags = []
        for cid in deduped_ids:
            merged_tags.extend(tags_by_card.get(cid, []))
        merged_tags = _normalize_tag_names(merged_tags)

    conn.execute("SAVEPOINT cards_merge")
    try:
        merged_card_id = card_upsert(
            conn,
            user_id=user_id,
            space_key=space_key,
            kind=kind,
            title=title,
            summary=summary,
            body=body,
            status=status,
            salience=salience,
            tags=merged_tags,
            created_by_client_name=created_by_client_name,
            source_confidence=source_confidence,
            context_json=context_json,
            evidence_refs=evidence_refs,
            dedupe_by_fingerprint=False,
            commit=False,
        )

        superseded_ids: list[str] = []
        for source_card_id in deduped_ids:
            if source_card_id == merged_card_id:
                continue
            conn.execute(
                "UPDATE cards SET status = 'superseded' WHERE id = ?",
                (source_card_id,),
            )
            _record_relation(
                conn,
                from_card_id=source_card_id,
                to_card_id=merged_card_id,
                relation_type=normalized_relation,
            )
            _refresh_unstable_flag(conn, card_id=source_card_id)
            superseded_ids.append(source_card_id)

        conn.execute("RELEASE SAVEPOINT cards_merge")
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT cards_merge")
        conn.execute("RELEASE SAVEPOINT cards_merge")
        conn.rollback()
        raise

    return {
        "merged_card_id": merged_card_id,
        "superseded_card_ids": superseded_ids,
        "relation_type": normalized_relation,
    }
