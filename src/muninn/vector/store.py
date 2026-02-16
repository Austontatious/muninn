from __future__ import annotations

import logging
import sqlite3
from typing import Literal

from .. import db
from ..config import sqlite_vec_enabled, vec_backend
from ..models import UpsertEmbeddingsItem, VectorHit
from . import sqlite_vec_backend
from .sqlite_vec_loader import is_sqlite_vec_loaded, maybe_load_sqlite_vec, serialize_f32
from .vectors import dot, from_f32_blob, l2_normalize, to_f32_blob

logger = logging.getLogger(__name__)
VALID_KINDS: set[str] = {"fact", "episode", "preference"}
_WARNED_SQLITE_VEC_UNAVAILABLE = False


def _valid_kinds(
    kinds: list[Literal["fact", "episode", "preference"]] | None,
) -> list[Literal["fact", "episode", "preference"]] | None:
    if not kinds:
        return None
    filtered = [kind for kind in kinds if kind in VALID_KINDS]
    if not filtered:
        return None
    return filtered


def _should_use_sqlite_vec(conn: sqlite3.Connection) -> bool:
    global _WARNED_SQLITE_VEC_UNAVAILABLE

    mode = vec_backend()
    if mode == "bruteforce":
        return False
    if not sqlite_vec_enabled():
        return False

    loaded = maybe_load_sqlite_vec(conn) or is_sqlite_vec_loaded(conn)
    if loaded:
        return True

    if mode == "sqlite_vec" and not _WARNED_SQLITE_VEC_UNAVAILABLE:
        logger.warning("sqlite-vec backend requested but unavailable; falling back to brute-force")
        _WARNED_SQLITE_VEC_UNAVAILABLE = True
    return False


def effective_backend(conn: sqlite3.Connection | None = None) -> tuple[str, bool, str]:
    should_close = False
    if conn is None:
        conn = db.connect()
        should_close = True

    try:
        config_mode = vec_backend()
        enabled = sqlite_vec_enabled()
        loaded = (maybe_load_sqlite_vec(conn) if enabled else False) or is_sqlite_vec_loaded(conn)

        if config_mode == "bruteforce" or not enabled:
            eff = "bruteforce"
        elif loaded:
            eff = "sqlite_vec"
        else:
            eff = "bruteforce"
        return config_mode, loaded, eff
    finally:
        if should_close:
            conn.close()


def upsert_embeddings(
    namespace: str,
    items: list[UpsertEmbeddingsItem],
    now_ts: float | None = None,
) -> tuple[int, int, list[str]]:
    conn = db.connect()
    ts = float(now_ts) if now_ts is not None else db.now()
    use_sqlite_vec = _should_use_sqlite_vec(conn)

    upserted = 0
    rejected = 0
    reasons: list[str] = []

    for item in items:
        vec = [float(v) for v in item.vector]
        dim = len(vec)
        if dim == 0:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: empty vector")
            continue
        if dim < 8 or dim > 4096:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: dim out of range [{dim}]")
            continue

        try:
            normalized = l2_normalize(vec)
            canonical_blob = to_f32_blob(normalized)
            existing = db.fetch_one(
                conn,
                "SELECT namespace FROM embeddings WHERE item_id = ?",
                (item.item_id,),
            )
            if existing and existing["namespace"] != namespace:
                rejected += 1
                reasons.append(
                    f"Rejected {item.item_id}: item_id already belongs to namespace '{existing['namespace']}'"
                )
                continue

            conn.execute(
                """
                INSERT INTO embeddings (item_id, namespace, kind, entity_id, model, dim, vector_blob, updated_at)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(item_id) DO UPDATE SET
                    namespace = excluded.namespace,
                    kind = excluded.kind,
                    entity_id = excluded.entity_id,
                    model = excluded.model,
                    dim = excluded.dim,
                    vector_blob = excluded.vector_blob,
                    updated_at = excluded.updated_at
                """,
                (
                    item.item_id,
                    namespace,
                    item.kind,
                    item.entity_id,
                    item.model,
                    dim,
                    canonical_blob,
                    ts,
                ),
            )

            if use_sqlite_vec:
                try:
                    vec_blob = serialize_f32(normalized)
                    sqlite_vec_backend.upsert_vec(
                        conn=conn,
                        namespace=namespace,
                        item_id=item.item_id,
                        model=item.model,
                        dim=dim,
                        kind=item.kind,
                        entity_id=item.entity_id,
                        embedding_f32_blob=vec_blob,
                        updated_at=ts,
                    )
                except Exception:
                    logger.warning(
                        "sqlite-vec upsert failed for %s; canonical embeddings retained",
                        item.item_id,
                    )
            else:
                # Prevent stale sqlite-vec mappings from surfacing if backend was previously enabled.
                conn.execute(
                    "DELETE FROM embeddings_vec_index WHERE namespace = ? AND item_id = ?",
                    (namespace, item.item_id),
                )

            upserted += 1
        except ValueError as exc:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: {exc}")

    conn.commit()
    conn.close()
    return upserted, rejected, reasons


def _metadata_for_ids(
    conn: sqlite3.Connection, namespace: str, ordered_ids: list[str]
) -> dict[str, tuple[str, str]]:
    if not ordered_ids:
        return {}

    placeholders = ", ".join(["?"] * len(ordered_ids))
    rows = db.fetch_all(
        conn,
        (
            "SELECT item_id, kind, entity_id FROM embeddings "
            f"WHERE namespace = ? AND item_id IN ({placeholders})"
        ),
        tuple([namespace] + ordered_ids),
    )
    out = {row["item_id"]: (row["kind"], row["entity_id"]) for row in rows}

    missing = [item_id for item_id in ordered_ids if item_id not in out]
    if missing:
        miss_ph = ", ".join(["?"] * len(missing))
        rows = db.fetch_all(
            conn,
            (
                "SELECT item_id, kind, entity_id FROM embeddings_vec_index "
                f"WHERE namespace = ? AND item_id IN ({miss_ph})"
            ),
            tuple([namespace] + missing),
        )
        for row in rows:
            out[row["item_id"]] = (row["kind"], row["entity_id"])

    return out


def _query_vector_bruteforce(
    conn: sqlite3.Connection,
    namespace: str,
    model: str,
    query_norm: list[float],
    entity_id: str | None,
    kinds: list[Literal["fact", "episode", "preference"]] | None,
    k: int,
    max_scan: int,
) -> list[VectorHit]:
    query_dim = len(query_norm)

    where = ["namespace = ?", "model = ?"]
    params: list[object] = [namespace, model]

    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)

    if kinds:
        placeholders = ", ".join(["?"] * len(kinds))
        where.append(f"kind IN ({placeholders})")
        params.extend(kinds)

    scan_cap = max(1, int(max_scan))
    sql = (
        "SELECT item_id, kind, entity_id, dim, vector_blob FROM embeddings "
        f"WHERE {' AND '.join(where)} LIMIT ?"
    )
    rows = db.fetch_all(conn, sql, tuple(params + [scan_cap]))

    hits: list[VectorHit] = []
    for row in rows:
        dim = int(row["dim"])
        if dim != query_dim:
            continue

        try:
            stored = from_f32_blob(row["vector_blob"])
            if len(stored) != query_dim:
                continue
            score = dot(query_norm, stored)
        except ValueError:
            continue

        hits.append(
            VectorHit(
                item_id=row["item_id"],
                kind=row["kind"],
                entity_id=row["entity_id"],
                score=float(score),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.item_id))
    return hits[: max(1, int(k))]


def query_vector(
    namespace: str,
    model: str,
    query_vec: list[float],
    entity_id: str | None,
    kinds: list[Literal["fact", "episode", "preference"]] | None,
    k: int,
    max_scan: int,
) -> list[VectorHit]:
    if not query_vec:
        return []

    valid_kinds = _valid_kinds(kinds)

    try:
        query_norm = l2_normalize([float(v) for v in query_vec])
    except ValueError:
        return []

    conn = db.connect()
    query_dim = len(query_norm)

    if _should_use_sqlite_vec(conn):
        try:
            query_blob = serialize_f32(query_norm)
            ranked = sqlite_vec_backend.knn_query(
                conn=conn,
                namespace=namespace,
                model=model,
                dim=query_dim,
                query_blob=query_blob,
                entity_id=entity_id,
                kinds=valid_kinds,
                k=k,
            )
            if ranked:
                ordered_ids = [item_id for item_id, _ in ranked]
                score_by_id = {item_id: score for item_id, score in ranked}
                metadata = _metadata_for_ids(conn, namespace=namespace, ordered_ids=ordered_ids)

                hits: list[VectorHit] = []
                for item_id in ordered_ids:
                    meta = metadata.get(item_id)
                    if not meta:
                        continue
                    kind, ent_id = meta
                    hits.append(
                        VectorHit(
                            item_id=item_id,
                            kind=kind,
                            entity_id=ent_id,
                            score=float(score_by_id[item_id]),
                        )
                    )
                if hits:
                    conn.close()
                    return hits[: max(1, int(k))]
        except Exception:
            logger.warning("sqlite-vec query failed; falling back to brute-force")

    hits = _query_vector_bruteforce(
        conn=conn,
        namespace=namespace,
        model=model,
        query_norm=query_norm,
        entity_id=entity_id,
        kinds=valid_kinds,
        k=k,
        max_scan=max_scan,
    )
    conn.close()
    return hits
