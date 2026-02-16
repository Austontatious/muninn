from __future__ import annotations

import json
import sqlite3

from .. import db
from ..config import max_vec_scan, retrieval_mode, rrf_k0
from ..models import Provenance, RetrievedItem
from ..vector import store as vector_store
from .fusion import rrf_fuse


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
    tokens = [token for token in query.strip().split() if token]
    if not tokens:
        return query
    return " OR ".join(tokens)


def _retrieve_fts(
    conn,
    query: str,
    entity_id: str | None,
    k: int,
) -> list[RetrievedItem]:
    hits: dict[str, RetrievedItem] = {}
    fts_query = _safe_query(query)

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
        return []

    return list(hits.values())[:k]


def _retrieve_recent(conn, entity_id: str | None, k: int) -> list[RetrievedItem]:
    if k <= 0:
        return []

    hits: dict[str, RetrievedItem] = {}
    params: list[str] = []
    ent_filter = ""
    if entity_id:
        ent_filter = "WHERE entity_id = ?"
        params.append(entity_id)

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, entity_id, summary, confidence, provenance_json "
            f"FROM episodes {ent_filter} ORDER BY created_at DESC LIMIT ?"
        ),
        tuple(params + [k]),
    )
    for row in rows:
        item = _row_to_item("episode", row)
        hits.setdefault(item.id, item)

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, subject_id, predicate, object, confidence, provenance_json FROM facts "
            f"{'WHERE subject_id = ?' if entity_id else ''} ORDER BY created_at DESC LIMIT ?"
        ),
        tuple(([entity_id] if entity_id else []) + [k]),
    )
    for row in rows:
        item = _row_to_item("fact", row)
        hits.setdefault(item.id, item)

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, entity_id, key, value, confidence, provenance_json "
            f"FROM preferences {ent_filter} ORDER BY created_at DESC LIMIT ?"
        ),
        tuple(params + [k]),
    )
    for row in rows:
        item = _row_to_item("preference", row)
        hits.setdefault(item.id, item)

    return list(hits.values())[:k]


def _retrieve_by_ids(conn, ids: list[str]) -> list[RetrievedItem]:
    if not ids:
        return []

    placeholders = ", ".join(["?"] * len(ids))
    by_id: dict[str, RetrievedItem] = {}

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, entity_id, summary, confidence, provenance_json FROM episodes "
            f"WHERE id IN ({placeholders})"
        ),
        tuple(ids),
    )
    for row in rows:
        by_id[row["id"]] = _row_to_item("episode", row)

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, subject_id, predicate, object, confidence, provenance_json FROM facts "
            f"WHERE id IN ({placeholders})"
        ),
        tuple(ids),
    )
    for row in rows:
        by_id[row["id"]] = _row_to_item("fact", row)

    rows = db.fetch_all(
        conn,
        (
            "SELECT id, entity_id, key, value, confidence, provenance_json FROM preferences "
            f"WHERE id IN ({placeholders})"
        ),
        tuple(ids),
    )
    for row in rows:
        by_id[row["id"]] = _row_to_item("preference", row)

    ordered: list[RetrievedItem] = []
    seen: set[str] = set()
    for item_id in ids:
        item = by_id.get(item_id)
        if item and item.id not in seen:
            ordered.append(item)
            seen.add(item.id)
    return ordered


def retrieve(
    namespace: str,
    query: str,
    entity_id: str | None,
    k: int,
    query_embedding: list[float] | None = None,
    embedding_model: str | None = None,
) -> list[RetrievedItem]:
    conn = db.connect()
    k = max(1, int(k))

    fts_items = _retrieve_fts(conn, query=query, entity_id=entity_id, k=k)
    fts_ids = [item.id for item in fts_items]

    vec_ids: list[str] = []
    if query_embedding is not None and embedding_model:
        vec_hits = vector_store.query_vector(
            namespace=namespace,
            model=embedding_model,
            query_vec=query_embedding,
            entity_id=entity_id,
            kinds=None,
            k=k,
            max_scan=max_vec_scan(),
        )
        vec_ids = [hit.item_id for hit in vec_hits]

    mode = retrieval_mode()
    if mode == "vector":
        selected_ids = vec_ids if vec_ids else fts_ids
    elif mode == "hybrid":
        selected_ids = rrf_fuse(fts_ids, vec_ids, rrf_k0()) if vec_ids else fts_ids
    else:
        selected_ids = fts_ids

    items = _retrieve_by_ids(conn, selected_ids[:k])

    if len(items) < k:
        seen = {item.id for item in items}
        for item in _retrieve_recent(conn, entity_id=entity_id, k=k):
            if item.id in seen:
                continue
            items.append(item)
            seen.add(item.id)
            if len(items) >= k:
                break

    return items[:k]
