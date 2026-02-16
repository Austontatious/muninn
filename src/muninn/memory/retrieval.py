from __future__ import annotations

import json
import sqlite3

from .. import db
from ..models import Provenance, RetrievedItem


def _row_to_item(kind: str, row) -> RetrievedItem:
    prov = Provenance(**json.loads(row["provenance_json"]))
    if kind == "episode":
        text = row["summary"]
        entity_id = row["entity_id"]
    elif kind == "fact":
        text = f"{row['predicate']}: {row['object']}"
        entity_id = row["subject_id"]
    else:
        text = f"{row['key']}={row['value']}"
        entity_id = row["entity_id"]
    return RetrievedItem(
        kind=kind,
        id=row["id"],
        entity_id=entity_id,
        text=text,
        confidence=float(row["confidence"]),
        provenance=prov,
    )


def _safe_query(query: str) -> str:
    # Fall back to a broad token query if the caller sends unsupported MATCH syntax.
    tokens = [t for t in query.strip().split() if t]
    if not tokens:
        return query
    return " OR ".join(tokens)


def retrieve(namespace: str, query: str, entity_id: str | None, k: int) -> list[RetrievedItem]:
    _ = namespace
    conn = db.connect()
    hits: dict[str, RetrievedItem] = {}
    fts_query = _safe_query(query)

    # 1) FTS hits (lexical)
    try:
        # Episodes FTS
        if entity_id:
            rows = db.fetch_all(
                conn,
                """
                SELECT e.id, e.entity_id, e.summary, e.confidence, e.provenance_json
                FROM episodes_fts f
                JOIN episodes e ON e.id = f.id
                WHERE f.summary MATCH ? AND e.entity_id = ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, entity_id, k),
            )
        else:
            rows = db.fetch_all(
                conn,
                """
                SELECT e.id, e.entity_id, e.summary, e.confidence, e.provenance_json
                FROM episodes_fts f
                JOIN episodes e ON e.id = f.id
                WHERE f.summary MATCH ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, k),
            )
        for row in rows:
            item = _row_to_item("episode", row)
            hits[item.id] = item

        # Facts FTS
        if entity_id:
            rows = db.fetch_all(
                conn,
                """
                SELECT fa.id, fa.subject_id, fa.predicate, fa.object, fa.confidence, fa.provenance_json
                FROM facts_fts f
                JOIN facts fa ON fa.id = f.id
                WHERE f.text MATCH ? AND fa.subject_id = ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, entity_id, k),
            )
        else:
            rows = db.fetch_all(
                conn,
                """
                SELECT fa.id, fa.subject_id, fa.predicate, fa.object, fa.confidence, fa.provenance_json
                FROM facts_fts f
                JOIN facts fa ON fa.id = f.id
                WHERE f.text MATCH ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, k),
            )
        for row in rows:
            item = _row_to_item("fact", row)
            hits[item.id] = item

        # Preferences FTS
        if entity_id:
            rows = db.fetch_all(
                conn,
                """
                SELECT p.id, p.entity_id, p.key, p.value, p.confidence, p.provenance_json
                FROM preferences_fts f
                JOIN preferences p ON p.id = f.id
                WHERE f.text MATCH ? AND p.entity_id = ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, entity_id, k),
            )
        else:
            rows = db.fetch_all(
                conn,
                """
                SELECT p.id, p.entity_id, p.key, p.value, p.confidence, p.provenance_json
                FROM preferences_fts f
                JOIN preferences p ON p.id = f.id
                WHERE f.text MATCH ?
                ORDER BY bm25(f) ASC
                LIMIT ?
                """,
                (fts_query, k),
            )
        for row in rows:
            item = _row_to_item("preference", row)
            hits[item.id] = item
    except sqlite3.OperationalError:
        # If MATCH parsing fails, continue with recency-only fallback.
        pass

    # 2) Recency fallback (fill remaining)
    need = max(0, k - len(hits))
    if need > 0:
        params: list[str] = []
        ent_filter = ""
        if entity_id:
            ent_filter = "WHERE entity_id = ?"
            params.append(entity_id)

        # Episodes recent
        rows = db.fetch_all(
            conn,
            (
                "SELECT id, entity_id, summary, confidence, provenance_json "
                f"FROM episodes {ent_filter} ORDER BY created_at DESC LIMIT ?"
            ),
            tuple(params + [need]),
        )
        for row in rows:
            item = _row_to_item("episode", row)
            hits.setdefault(item.id, item)

        # Facts recent
        rows = db.fetch_all(
            conn,
            (
                "SELECT id, subject_id, predicate, object, confidence, provenance_json FROM facts "
                f"{'WHERE subject_id = ?' if entity_id else ''} ORDER BY created_at DESC LIMIT ?"
            ),
            tuple(([entity_id] if entity_id else []) + [need]),
        )
        for row in rows:
            item = _row_to_item("fact", row)
            hits.setdefault(item.id, item)

        # Preferences recent
        rows = db.fetch_all(
            conn,
            (
                "SELECT id, entity_id, key, value, confidence, provenance_json "
                f"FROM preferences {ent_filter} ORDER BY created_at DESC LIMIT ?"
            ),
            tuple(params + [need]),
        )
        for row in rows:
            item = _row_to_item("preference", row)
            hits.setdefault(item.id, item)

    # Return stable list (FTS first-ish by insertion order)
    return list(hits.values())[:k]
