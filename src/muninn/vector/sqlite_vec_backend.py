from __future__ import annotations

import re
import sqlite3
from typing import Literal

from .. import db
from ..config import vec_table_prefix


def _safe_part(value: str, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_")
    if not cleaned:
        cleaned = "x"
    return cleaned[:max_len]


def table_name_for(model: str, dim: int) -> str:
    prefix = _safe_part(vec_table_prefix(), max_len=24)
    safe_model = _safe_part(model, max_len=40)
    return f"{prefix}__{safe_model}__d{int(dim)}"


def ensure_vec_table(conn: sqlite3.Connection, model: str, dim: int) -> str:
    if dim <= 0:
        raise ValueError("invalid vector dimension")
    table = table_name_for(model, dim)
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {table} USING vec0(embedding float[{int(dim)}]);"
    )
    return table


def _delete_vec_row(conn: sqlite3.Connection, table_name: str, rowid: int) -> None:
    try:
        conn.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (int(rowid),))
    except Exception:
        # Ignore if old table no longer exists or row cannot be deleted.
        pass


def upsert_vec(
    conn: sqlite3.Connection,
    item_id: str,
    model: str,
    dim: int,
    kind: str,
    entity_id: str,
    embedding_f32_blob: bytes,
    updated_at: float,
) -> tuple[str, int]:
    table_name = ensure_vec_table(conn, model, dim)

    existing = db.fetch_one(
        conn,
        "SELECT table_name, rowid FROM embeddings_vec_index WHERE item_id = ?",
        (item_id,),
    )
    if existing:
        _delete_vec_row(conn, existing["table_name"], int(existing["rowid"]))

    cur = conn.execute(f"INSERT INTO {table_name}(embedding) VALUES (?)", (embedding_f32_blob,))
    new_rowid = int(cur.lastrowid)

    conn.execute(
        """
        INSERT INTO embeddings_vec_index(item_id, table_name, rowid, model, dim, kind, entity_id, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            table_name = excluded.table_name,
            rowid = excluded.rowid,
            model = excluded.model,
            dim = excluded.dim,
            kind = excluded.kind,
            entity_id = excluded.entity_id,
            updated_at = excluded.updated_at
        """,
        (item_id, table_name, new_rowid, model, dim, kind, entity_id, updated_at),
    )

    return table_name, new_rowid


def _build_index_filters(
    model: str,
    dim: int,
    table_name: str,
    entity_id: str | None,
    kinds: list[Literal["fact", "episode", "preference"]] | None,
) -> tuple[str, list[object]]:
    where = ["model = ?", "dim = ?", "table_name = ?"]
    params: list[object] = [model, int(dim), table_name]

    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)

    if kinds:
        placeholders = ", ".join(["?"] * len(kinds))
        where.append(f"kind IN ({placeholders})")
        params.extend(kinds)

    return " AND ".join(where), params


def knn_query(
    conn: sqlite3.Connection,
    model: str,
    dim: int,
    query_blob: bytes,
    entity_id: str | None,
    kinds: list[Literal["fact", "episode", "preference"]] | None,
    k: int,
) -> list[tuple[str, float]]:
    if dim <= 0:
        return []

    table_name = ensure_vec_table(conn, model, dim)
    where_sql, filter_params = _build_index_filters(model, dim, table_name, entity_id, kinds)
    subquery = f"SELECT rowid FROM embeddings_vec_index WHERE {where_sql}"
    k_val = max(1, int(k))

    join_sql = f"""
        SELECT i.item_id, v.distance
        FROM {table_name} v
        JOIN embeddings_vec_index i ON i.table_name = ? AND i.rowid = v.rowid
        WHERE v.rowid IN ({subquery})
          AND v.embedding MATCH ?
          AND v.k = ?
        ORDER BY v.distance
    """

    try:
        rows = db.fetch_all(
            conn,
            join_sql,
            tuple([table_name] + filter_params + [query_blob, k_val]),
        )
        results: list[tuple[str, float]] = []
        for row in rows:
            distance = float(row["distance"])
            score = 1.0 / (1.0 + distance)
            results.append((row["item_id"], score))
        return results
    except Exception:
        pass

    # Fallback: query rowids first, then map rowid -> item_id.
    vec_sql = f"""
        SELECT rowid, distance
        FROM {table_name}
        WHERE rowid IN ({subquery})
          AND embedding MATCH ?
          AND k = ?
        ORDER BY distance
    """
    try:
        vec_rows = db.fetch_all(conn, vec_sql, tuple(filter_params + [query_blob, k_val]))
    except Exception:
        return []

    if not vec_rows:
        return []

    rowids = [int(row["rowid"]) for row in vec_rows]
    placeholders = ", ".join(["?"] * len(rowids))
    map_rows = db.fetch_all(
        conn,
        (
            "SELECT rowid, item_id FROM embeddings_vec_index "
            f"WHERE table_name = ? AND rowid IN ({placeholders})"
        ),
        tuple([table_name] + rowids),
    )
    item_by_rowid = {int(row["rowid"]): row["item_id"] for row in map_rows}

    results: list[tuple[str, float]] = []
    for row in vec_rows:
        rowid = int(row["rowid"])
        item_id = item_by_rowid.get(rowid)
        if not item_id:
            continue
        distance = float(row["distance"])
        score = 1.0 / (1.0 + distance)
        results.append((item_id, score))
    return results
