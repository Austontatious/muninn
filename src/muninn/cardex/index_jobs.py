from __future__ import annotations

import hashlib
import json
from typing import Any

from .. import db
from ..models import CardEmbeddingUpsertRequest
from . import embeddings, store

_SUPPORTED_MODALITIES: set[str] = {"text"}
_ARTIFACT_PRIORITY_SQL = """CASE artifact_type
    WHEN 'summary' THEN 0
    WHEN 'transcript' THEN 1
    WHEN 'caption' THEN 2
    WHEN 'ocr' THEN 3
    WHEN 'extracted_text' THEN 4
    ELSE 9 END"""


def _json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def _json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _compact_json(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compose_card_text(conn, namespace: str, card_id: str) -> tuple[str, str, str] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT card_id, title, summary, tags_json, details_json
        FROM cards
        WHERE namespace = ? AND card_id = ?
        """,
        (namespace, card_id),
    )
    if not row:
        return None

    tags = " ".join(_json_list(row["tags_json"]))
    details = _compact_json(_json_dict(row["details_json"]))
    pieces = [str(row["title"] or ""), str(row["summary"] or ""), tags, details]
    text = "\n".join(piece.strip() for piece in pieces if piece and piece.strip()).strip()
    if not text:
        text = str(row["title"] or card_id)
    return "card", str(row["card_id"]), text


def _compose_chunk_text(conn, namespace: str, chunk_id: str) -> tuple[str, str, str] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT c.chunk_id, c.text, s.title AS source_title
        FROM chunks c
        JOIN documents d ON d.doc_id = c.doc_id AND d.namespace = ?
        JOIN sources s ON s.source_id = d.source_id AND s.namespace = ?
        WHERE c.namespace = ? AND c.chunk_id = ?
        """,
        (namespace, namespace, namespace, chunk_id),
    )
    if not row:
        return None
    source_title = str(row["source_title"] or "")
    chunk_text = str(row["text"] or "")
    text = "\n".join(part for part in [source_title, chunk_text] if part.strip()).strip()
    return "chunk", str(row["chunk_id"]), text or str(row["chunk_id"])


def _compose_source_text(conn, namespace: str, source_id: str) -> tuple[str, str, str] | None:
    source = db.fetch_one(
        conn,
        """
        SELECT source_id, title, uri
        FROM sources
        WHERE namespace = ? AND source_id = ?
        """,
        (namespace, source_id),
    )
    if not source:
        return None

    doc = db.fetch_one(
        conn,
        """
        SELECT content_text
        FROM documents
        WHERE namespace = ? AND source_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (namespace, source_id),
    )
    artifacts = db.fetch_all(
        conn,
        f"""
        SELECT content_text
        FROM artifacts
        WHERE namespace = ?
          AND source_id = ?
          AND content_text IS NOT NULL
          AND trim(content_text) != ''
        ORDER BY {_ARTIFACT_PRIORITY_SQL}, created_at DESC
        LIMIT 3
        """,
        (namespace, source_id),
    )

    parts: list[str] = [str(source["title"] or ""), str(source["uri"] or "")]
    if doc and doc["content_text"] is not None:
        parts.append(str(doc["content_text"]))
    for artifact in artifacts:
        parts.append(str(artifact["content_text"]))

    text = "\n".join(piece.strip() for piece in parts if piece and piece.strip()).strip()
    if not text:
        text = str(source["source_id"])
    return "source", str(source["source_id"]), text


def _compose_artifact_text(conn, namespace: str, artifact_id: str) -> tuple[str, str, str] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT a.source_id, a.content_text, a.artifact_type, s.title
        FROM artifacts a
        JOIN sources s ON s.source_id = a.source_id AND s.namespace = ?
        WHERE a.namespace = ? AND a.artifact_id = ?
        """,
        (namespace, namespace, artifact_id),
    )
    if not row:
        return None

    parts = [
        str(row["title"] or ""),
        str(row["artifact_type"] or ""),
        str(row["content_text"] or ""),
    ]
    text = "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    if not text:
        text = str(row["source_id"])
    # Artifact embeddings are folded into source-level owners for now.
    return "source", str(row["source_id"]), text


def _resolve_job_text(
    conn,
    namespace: str,
    owner_type: str,
    owner_id: str,
) -> tuple[str, str, str] | None:
    if owner_type == "card":
        return _compose_card_text(conn, namespace, owner_id)
    if owner_type == "chunk":
        return _compose_chunk_text(conn, namespace, owner_id)
    if owner_type == "source":
        return _compose_source_text(conn, namespace, owner_id)
    if owner_type == "artifact":
        return _compose_artifact_text(conn, namespace, owner_id)
    return None


def _claim_pending_jobs(conn, namespace: str | None, limit: int) -> list[dict[str, Any]]:
    where = ["status = 'pending'"]
    params: list[object] = []
    if namespace:
        where.append("namespace = ?")
        params.append(namespace)
    rows = db.fetch_all(
        conn,
        (
            "SELECT job_id, namespace, owner_type, owner_id, modality "
            "FROM index_jobs "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY priority DESC, created_at ASC "
            "LIMIT ?"
        ),
        tuple(params + [max(1, int(limit))]),
    )

    claimed: list[dict[str, Any]] = []
    now_ts = db.now()
    for row in rows:
        updated = conn.execute(
            """
            UPDATE index_jobs
            SET status = 'running', updated_at = ?
            WHERE job_id = ?
              AND namespace = ?
              AND status = 'pending'
            """,
            (now_ts, str(row["job_id"]), str(row["namespace"])),
        ).rowcount
        if updated:
            claimed.append(
                {
                    "job_id": str(row["job_id"]),
                    "namespace": str(row["namespace"]),
                    "owner_type": str(row["owner_type"]),
                    "owner_id": str(row["owner_id"]),
                    "modality": str(row["modality"]),
                }
            )
    conn.commit()
    return claimed


def _set_job_status(conn, namespace: str, job_id: str, status: str) -> None:
    conn.execute(
        """
        UPDATE index_jobs
        SET status = ?, updated_at = ?
        WHERE namespace = ? AND job_id = ?
        """,
        (status, db.now(), namespace, job_id),
    )
    conn.commit()


def process_pending_index_jobs(
    limit: int = 50,
    namespace: str | None = None,
    model: str | None = None,
    dim: int | None = None,
) -> dict[str, Any]:
    conn = db.connect()
    claimed = _claim_pending_jobs(conn, namespace=namespace, limit=limit)
    model_name = model or embeddings.default_card_embedding_model()
    dims = int(dim if dim is not None else embeddings.default_card_embedding_dim())

    done = 0
    failed = 0
    skipped = 0

    for job in claimed:
        job_id = str(job["job_id"])
        ns = str(job["namespace"])
        owner_type = str(job["owner_type"])
        owner_id = str(job["owner_id"])
        modality = str(job["modality"])

        if modality not in _SUPPORTED_MODALITIES:
            skipped += 1
            _set_job_status(conn, namespace=ns, job_id=job_id, status="done")
            continue

        owner = _resolve_job_text(conn, namespace=ns, owner_type=owner_type, owner_id=owner_id)
        if not owner:
            failed += 1
            _set_job_status(conn, namespace=ns, job_id=job_id, status="failed")
            continue

        embed_owner_type, embed_owner_id, text = owner
        try:
            vector = embeddings.embed_text(text, dim=dims)
            content_hash = _sha256_text(text)
            store.upsert_card_embedding(
                CardEmbeddingUpsertRequest(
                    namespace=ns,
                    owner_type=embed_owner_type,
                    owner_id=embed_owner_id,
                    modality="text",
                    model=model_name,
                    dims=len(vector),
                    vector=vector,
                    content_hash=content_hash,
                    embed_status="ready",
                    embed_error=None,
                    requested_by="system:index_worker",
                )
            )
            _set_job_status(conn, namespace=ns, job_id=job_id, status="done")
            done += 1
        except Exception:
            failed += 1
            _set_job_status(conn, namespace=ns, job_id=job_id, status="failed")

    conn.close()
    return {
        "claimed": len(claimed),
        "done": done,
        "failed": failed,
        "skipped": skipped,
        "model": model_name,
        "dim": dims,
    }


__all__ = ["process_pending_index_jobs"]
