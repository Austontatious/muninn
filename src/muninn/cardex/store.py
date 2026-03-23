from __future__ import annotations

import hashlib
import json
from typing import Any

from .. import db
from ..models import (
    ArtifactInput,
    CardEmbeddingUpsertRequest,
    CardEmbeddingUpsertResponse,
    CardRecord,
    CardRefInput,
    CardStatus,
    CardType,
    EvidenceOwnerType,
    EvidenceStatus,
    SourceArtifactsResponse,
    SourceCreateRequest,
    SourceCreateResponse,
    SourceRecord,
)
from . import embeddings

_ALLOWED_CARD_FIELDS = {
    "type",
    "title",
    "summary",
    "details_json",
    "tags_json",
    "salience",
    "confidence",
    "sensitivity_tier",
    "status",
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _json_load_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_load_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _json_load_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _enqueue_index_job_conn(
    conn,
    namespace: str,
    owner_type: str,
    owner_id: str,
    modality: str = "text",
    priority: int = 50,
) -> str | None:
    existing = db.fetch_one(
        conn,
        """
        SELECT job_id
        FROM index_jobs
        WHERE namespace = ?
          AND owner_type = ?
          AND owner_id = ?
          AND modality = ?
          AND status IN ('pending','running')
        LIMIT 1
        """,
        (namespace, owner_type, owner_id, modality),
    )
    if existing:
        return None

    job_id = db.new_id("idxjob")
    conn.execute(
        """
        INSERT INTO index_jobs
            (job_id, namespace, owner_type, owner_id, modality, priority, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            job_id,
            namespace,
            owner_type,
            owner_id,
            modality,
            int(priority),
            "pending",
            db.now(),
            db.now(),
        ),
    )
    conn.commit()
    return job_id


def enqueue_index_job(
    namespace: str,
    owner_type: str,
    owner_id: str,
    modality: str = "text",
    priority: int = 50,
) -> str | None:
    conn = db.connect()
    job_id = _enqueue_index_job_conn(
        conn=conn,
        namespace=namespace,
        owner_type=owner_type,
        owner_id=owner_id,
        modality=modality,
        priority=priority,
    )
    conn.close()
    return job_id


def get_evidence_owner(
    namespace: str,
    owner_type: EvidenceOwnerType,
    owner_id: str,
) -> dict[str, Any] | None:
    conn = db.connect()
    row = None
    if owner_type == "artifact":
        row = db.fetch_one(
            conn,
            """
            SELECT
                a.artifact_id AS owner_id,
                a.artifact_type,
                a.content_text,
                a.content_json,
                a.source_id,
                s.title AS source_title,
                s.uri AS source_uri,
                s.sensitivity_tier
            FROM artifacts a
            JOIN sources s ON s.source_id = a.source_id AND s.namespace = ?
            WHERE a.namespace = ? AND a.artifact_id = ?
            """,
            (namespace, namespace, owner_id),
        )
    if owner_type == "chunk":
        row = db.fetch_one(
            conn,
            """
            SELECT
                c.chunk_id AS owner_id,
                c.text AS content_text,
                c.doc_id,
                d.source_id,
                s.title AS source_title,
                s.uri AS source_uri,
                s.sensitivity_tier
            FROM chunks c
            JOIN documents d ON d.doc_id = c.doc_id AND d.namespace = ?
            JOIN sources s ON s.source_id = d.source_id AND s.namespace = ?
            WHERE c.namespace = ? AND c.chunk_id = ?
            """,
            (namespace, namespace, namespace, owner_id),
        )
    conn.close()

    if not row:
        return None

    out = {
        "owner_type": owner_type,
        "owner_id": str(row["owner_id"]),
        "source_id": str(row["source_id"]),
        "source_title": str(row["source_title"] or ""),
        "source_uri": str(row["source_uri"] or ""),
        "sensitivity_tier": int(row["sensitivity_tier"]),
        "content_text": str(row["content_text"] or ""),
    }
    if owner_type == "artifact":
        out["artifact_type"] = str(row["artifact_type"] or "")
        out["content_json"] = _json_load_object(row["content_json"])
    if owner_type == "chunk":
        out["doc_id"] = str(row["doc_id"] or "")
    return out


def get_evidence_state(namespace: str, owner_type: EvidenceOwnerType, owner_id: str) -> dict[str, Any] | None:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        """
        SELECT namespace, owner_type, owner_id, status, score, reason_json, created_at, updated_at
        FROM evidence_state
        WHERE namespace = ? AND owner_type = ? AND owner_id = ?
        """,
        (namespace, owner_type, owner_id),
    )
    conn.close()
    if not row:
        return None
    return {
        "namespace": str(row["namespace"]),
        "owner_type": str(row["owner_type"]),
        "owner_id": str(row["owner_id"]),
        "status": str(row["status"]),
        "score": float(row["score"]),
        "reason_json": _json_load_object(row["reason_json"]),
        "created_at": float(row["created_at"]),
        "updated_at": float(row["updated_at"]),
    }


def upsert_evidence_state(
    namespace: str,
    owner_type: EvidenceOwnerType,
    owner_id: str,
    status: EvidenceStatus,
    score: float = 0.0,
    reason_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conn = db.connect()
    now_ts = db.now()
    conn.execute(
        """
        INSERT INTO evidence_state
            (namespace, owner_type, owner_id, status, score, reason_json, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(namespace, owner_type, owner_id) DO UPDATE SET
            status = excluded.status,
            score = excluded.score,
            reason_json = excluded.reason_json,
            updated_at = excluded.updated_at
        """,
        (
            namespace,
            owner_type,
            owner_id,
            status,
            float(score),
            _json_dumps(reason_json or {}),
            now_ts,
            now_ts,
        ),
    )
    conn.commit()
    row = db.fetch_one(
        conn,
        """
        SELECT namespace, owner_type, owner_id, status, score, reason_json, created_at, updated_at
        FROM evidence_state
        WHERE namespace = ? AND owner_type = ? AND owner_id = ?
        """,
        (namespace, owner_type, owner_id),
    )
    conn.close()
    if not row:  # pragma: no cover - defensive
        raise ValueError("evidence_state_upsert_failed")
    return {
        "namespace": str(row["namespace"]),
        "owner_type": str(row["owner_type"]),
        "owner_id": str(row["owner_id"]),
        "status": str(row["status"]),
        "score": float(row["score"]),
        "reason_json": _json_load_object(row["reason_json"]),
        "created_at": float(row["created_at"]),
        "updated_at": float(row["updated_at"]),
    }


def find_active_card_for_owner(
    namespace: str,
    owner_type: EvidenceOwnerType,
    owner_id: str,
) -> str | None:
    conn = db.connect()
    row = None
    if owner_type == "chunk":
        row = db.fetch_one(
            conn,
            """
            SELECT cr.card_id
            FROM card_refs cr
            JOIN cards c ON c.card_id = cr.card_id AND c.namespace = cr.namespace
            WHERE cr.namespace = ?
              AND cr.ref_type = 'chunk'
              AND cr.ref_id = ?
              AND c.status = 'active'
            ORDER BY c.updated_at DESC
            LIMIT 1
            """,
            (namespace, owner_id),
        )
    if owner_type == "artifact":
        owner = get_evidence_owner(namespace=namespace, owner_type=owner_type, owner_id=owner_id)
        if owner:
            row = db.fetch_one(
                conn,
                """
                SELECT cr.card_id
                FROM card_refs cr
                JOIN cards c ON c.card_id = cr.card_id AND c.namespace = cr.namespace
                WHERE cr.namespace = ?
                  AND cr.ref_type = 'source'
                  AND cr.ref_id = ?
                  AND c.status = 'active'
                ORDER BY c.updated_at DESC
                LIMIT 1
                """,
                (namespace, str(owner["source_id"])),
            )
    conn.close()
    if not row:
        return None
    return str(row["card_id"])


def _row_to_card(row) -> CardRecord:
    return CardRecord(
        card_id=row["card_id"],
        namespace=row["namespace"],
        type=row["type"],
        title=row["title"],
        summary=row["summary"],
        details_json=_json_load_dict(row["details_json"]),
        tags_json=_json_load_list(row["tags_json"]),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
        salience=float(row["salience"]),
        confidence=float(row["confidence"]),
        sensitivity_tier=int(row["sensitivity_tier"]),
        status=row["status"],
    )


def _row_to_source(row) -> SourceRecord:
    return SourceRecord(
        source_id=row["source_id"],
        namespace=row["namespace"],
        source_type=row["source_type"],
        uri=row["uri"],
        title=row["title"],
        metadata_json=_json_load_dict(row["metadata_json"]),
        content_hash=row["content_hash"],
        sensitivity_tier=int(row["sensitivity_tier"]),
        created_at=float(row["created_at"]),
    )


def create_card(
    namespace: str,
    card_type: CardType,
    title: str,
    summary: str,
    details_json: dict[str, Any],
    tags_json: list[str],
    salience: float = 0.5,
    confidence: float = 0.7,
    sensitivity_tier: int = 0,
    status: CardStatus = "active",
    card_id: str | None = None,
) -> CardRecord:
    conn = db.connect()
    cid = card_id or db.new_id("card")
    now_ts = db.now()

    db.execute_one(
        conn,
        """
        INSERT INTO cards
            (card_id, namespace, type, title, summary, details_json, tags_json, created_at, updated_at,
             salience, confidence, sensitivity_tier, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            cid,
            namespace,
            card_type,
            title,
            summary,
            _json_dumps(details_json),
            _json_dumps(tags_json),
            now_ts,
            now_ts,
            float(salience),
            float(confidence),
            int(sensitivity_tier),
            status,
        ),
    )

    row = db.fetch_one(
        conn,
        "SELECT * FROM cards WHERE namespace = ? AND card_id = ?",
        (namespace, cid),
    )
    conn.close()
    if not row:  # pragma: no cover - defensive
        raise ValueError("card_insert_failed")
    if status == "active":
        enqueue_index_job(
            namespace=namespace,
            owner_type="card",
            owner_id=cid,
            modality="text",
            priority=80,
        )
    return _row_to_card(row)


def get_card(namespace: str, card_id: str) -> CardRecord | None:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        "SELECT * FROM cards WHERE namespace = ? AND card_id = ?",
        (namespace, card_id),
    )
    conn.close()
    if not row:
        return None
    card = _row_to_card(row)
    if card.status == "active":
        enqueue_index_job(
            namespace=namespace,
            owner_type="card",
            owner_id=card.card_id,
            modality="text",
            priority=80,
        )
    return card


def update_card(namespace: str, card_id: str, updates: dict[str, Any]) -> CardRecord | None:
    set_fragments: list[str] = []
    values: list[Any] = []

    for key, value in updates.items():
        if key not in _ALLOWED_CARD_FIELDS:
            continue
        if key == "details_json":
            value = _json_dumps(value if isinstance(value, dict) else {})
        if key == "tags_json":
            value = _json_dumps(value if isinstance(value, list) else [])
        set_fragments.append(f"{key} = ?")
        values.append(value)

    if not set_fragments:
        return get_card(namespace, card_id)

    set_fragments.append("updated_at = ?")
    values.append(db.now())
    values.extend([namespace, card_id])

    conn = db.connect()
    conn.execute(
        f"UPDATE cards SET {', '.join(set_fragments)} WHERE namespace = ? AND card_id = ?",
        tuple(values),
    )
    conn.commit()

    row = db.fetch_one(
        conn,
        "SELECT * FROM cards WHERE namespace = ? AND card_id = ?",
        (namespace, card_id),
    )
    conn.close()
    if not row:
        return None
    card = _row_to_card(row)
    if card.status == "active":
        enqueue_index_job(
            namespace=namespace,
            owner_type="card",
            owner_id=card.card_id,
            modality="text",
            priority=80,
        )
    return card


def _chunk_document(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[int, int, str]]:
    if not text:
        return []

    size = max(1, int(chunk_size))
    overlap = max(0, min(int(chunk_overlap), size - 1))
    step = max(1, size - overlap)

    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((start, end, chunk_text))
        if end >= len(text):
            break
        start += step
    return chunks


def _insert_artifacts(
    conn,
    namespace: str,
    source_id: str,
    artifacts: list[ArtifactInput],
) -> list[str]:
    artifact_ids: list[str] = []
    for artifact in artifacts:
        artifact_id = db.new_id("art")
        content_json: str | None = None
        if artifact.content_json is not None:
            content_json = _json_dumps(artifact.content_json)
        db.execute_one(
            conn,
            """
            INSERT INTO artifacts
                (artifact_id, namespace, source_id, artifact_type, content_text, content_json, created_at, generator)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                artifact_id,
                namespace,
                source_id,
                artifact.artifact_type,
                artifact.content_text,
                content_json,
                db.now(),
                artifact.generator,
            ),
        )
        artifact_ids.append(artifact_id)
    return artifact_ids


def create_source(req: SourceCreateRequest) -> SourceCreateResponse:
    conn = db.connect()
    source_id = db.new_id("src")
    created_at = db.now()

    db.execute_one(
        conn,
        """
        INSERT INTO sources
            (source_id, namespace, source_type, uri, title, metadata_json, content_hash, sensitivity_tier, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            source_id,
            req.namespace,
            req.source_type,
            req.uri,
            req.title,
            _json_dumps(req.metadata_json),
            req.content_hash,
            int(req.sensitivity_tier),
            created_at,
        ),
    )

    doc_id: str | None = None
    chunk_ids: list[str] = []

    if req.document_text:
        doc_id = db.new_id("doc")
        db.execute_one(
            conn,
            """
            INSERT INTO documents (doc_id, namespace, source_id, content_text, created_at)
            VALUES (?,?,?,?,?)
            """,
            (doc_id, req.namespace, source_id, req.document_text, db.now()),
        )

        for idx, (char_start, char_end, text) in enumerate(
            _chunk_document(req.document_text, req.chunk_size, req.chunk_overlap)
        ):
            chunk_id = db.new_id("chunk")
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            db.execute_one(
                conn,
                """
                INSERT INTO chunks
                    (chunk_id, namespace, doc_id, idx, text, heading_path_json, char_start, char_end, text_hash, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    chunk_id,
                    req.namespace,
                    doc_id,
                    idx,
                    text,
                    None,
                    char_start,
                    char_end,
                    text_hash,
                    db.now(),
                ),
            )
            chunk_ids.append(chunk_id)

    artifact_ids = _insert_artifacts(conn, req.namespace, source_id, req.artifacts)

    row = db.fetch_one(
        conn,
        "SELECT * FROM sources WHERE namespace = ? AND source_id = ?",
        (req.namespace, source_id),
    )
    conn.close()
    if not row:  # pragma: no cover - defensive
        raise ValueError("source_insert_failed")

    return SourceCreateResponse(
        source=_row_to_source(row),
        doc_id=doc_id,
        chunk_ids=chunk_ids,
        artifact_ids=artifact_ids,
    )


def add_source_artifacts(
    namespace: str,
    source_id: str,
    artifacts: list[ArtifactInput],
) -> SourceArtifactsResponse:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        "SELECT source_id FROM sources WHERE namespace = ? AND source_id = ?",
        (namespace, source_id),
    )
    if not row:
        conn.close()
        raise ValueError("source_not_found")

    artifact_ids = _insert_artifacts(conn, namespace, source_id, artifacts)
    conn.close()
    return SourceArtifactsResponse(source_id=source_id, artifact_ids=artifact_ids)


def link_card_refs(namespace: str, card_id: str, refs: list[CardRefInput]) -> int:
    conn = db.connect()
    card_row = db.fetch_one(
        conn,
        "SELECT card_id FROM cards WHERE namespace = ? AND card_id = ?",
        (namespace, card_id),
    )
    if not card_row:
        conn.close()
        raise ValueError("card_not_found")

    inserted = 0
    now_ts = db.now()
    for ref in refs:
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO card_refs
                (namespace, card_id, ref_type, ref_id, role, note, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                namespace,
                card_id,
                ref.ref_type,
                ref.ref_id,
                ref.role,
                ref.note,
                now_ts,
            ),
        )
        if conn.total_changes > before:
            inserted += 1
    conn.commit()
    conn.close()
    return inserted


def list_card_refs(namespace: str, card_ids: list[str]) -> dict[str, list[dict[str, str]]]:
    if not card_ids:
        return {}

    conn = db.connect()
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = db.fetch_all(
        conn,
        (
            "SELECT card_id, ref_type, ref_id, role "
            "FROM card_refs "
            f"WHERE namespace = ? AND card_id IN ({placeholders}) "
            "ORDER BY created_at DESC"
        ),
        tuple([namespace] + card_ids),
    )
    conn.close()

    out: dict[str, list[dict[str, str]]] = {card_id: [] for card_id in card_ids}
    for row in rows:
        out.setdefault(row["card_id"], []).append(
            {
                "ref_type": str(row["ref_type"]),
                "ref_id": str(row["ref_id"]),
                "role": str(row["role"]),
            }
        )
    return out


def upsert_card_embedding(req: CardEmbeddingUpsertRequest) -> CardEmbeddingUpsertResponse:
    conn = db.connect()
    vector_blob: bytes | None = None
    if req.vector is not None:
        vector_blob = embeddings.pack_f32(req.vector)

    dims = int(req.dims)
    if req.vector is not None:
        dims = len(req.vector)

    now_ts = db.now()
    existing_rows = db.fetch_all(
        conn,
        """
        SELECT embedding_id
        FROM card_embeddings
        WHERE namespace = ?
          AND owner_type = ?
          AND owner_id = ?
          AND modality = ?
          AND model = ?
        ORDER BY created_at DESC, embedding_id DESC
        """,
        (
            req.namespace,
            req.owner_type,
            req.owner_id,
            req.modality,
            req.model,
        ),
    )

    if existing_rows:
        embedding_id = str(existing_rows[0]["embedding_id"])
        conn.execute(
            """
            UPDATE card_embeddings
            SET dims = ?,
                vector_blob = ?,
                content_hash = ?,
                embed_status = ?,
                embed_error = ?,
                created_at = ?
            WHERE embedding_id = ?
            """,
            (
                dims,
                vector_blob,
                req.content_hash,
                req.embed_status,
                req.embed_error,
                now_ts,
                embedding_id,
            ),
        )
        if len(existing_rows) > 1:
            stale_ids = [str(row["embedding_id"]) for row in existing_rows[1:]]
            placeholders = ", ".join(["?"] * len(stale_ids))
            conn.execute(
                f"DELETE FROM card_embeddings WHERE embedding_id IN ({placeholders})",
                tuple(stale_ids),
            )
    else:
        embedding_id = db.new_id("emb")
        conn.execute(
            """
            INSERT INTO card_embeddings
                (embedding_id, namespace, owner_type, owner_id, modality, model, dims, vector_blob,
                 content_hash, embed_status, embed_error, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                embedding_id,
                req.namespace,
                req.owner_type,
                req.owner_id,
                req.modality,
                req.model,
                dims,
                vector_blob,
                req.content_hash,
                req.embed_status,
                req.embed_error,
                now_ts,
            ),
        )
    conn.commit()
    conn.close()

    return CardEmbeddingUpsertResponse(
        embedding_id=embedding_id,
        embed_status=req.embed_status,
    )
