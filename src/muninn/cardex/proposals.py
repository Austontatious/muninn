from __future__ import annotations

import json
from typing import Any

from .. import db
from ..models import (
    CardRefInput,
    ProposalRecord,
    ProposalType,
    ProposeRequest,
    SourceCreateRequest,
)
from . import store

_ALLOWED_STATUSES: set[str] = {"proposed", "confirmed", "rejected", "expired"}


def _row_to_proposal(row) -> ProposalRecord:
    payload: dict[str, Any]
    try:
        payload = json.loads(row["payload_json"])
    except json.JSONDecodeError:
        payload = {}
    status = str(row["status"])
    if status not in _ALLOWED_STATUSES:
        status = "rejected"

    proposal_type = str(row["proposal_type"])
    if proposal_type not in {"create_card", "update_card", "link_refs", "add_source"}:
        proposal_type = "create_card"

    return ProposalRecord(
        proposal_id=row["proposal_id"],
        namespace=row["namespace"],
        proposal_type=proposal_type,
        payload_json=payload,
        status=status,
        created_at=float(row["created_at"]),
        decided_at=float(row["decided_at"]) if row["decided_at"] is not None else None,
        requested_by=row["requested_by"],
        decided_by=row["decided_by"],
        reason=row["reason"],
    )


def create_proposal(req: ProposeRequest) -> ProposalRecord:
    conn = db.connect()
    proposal_id = db.new_id("prop")
    db.execute_one(
        conn,
        """
        INSERT INTO proposals
            (proposal_id, namespace, proposal_type, payload_json, status, created_at, requested_by, reason)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            proposal_id,
            req.namespace,
            req.proposal_type,
            json.dumps(req.payload_json, separators=(",", ":"), ensure_ascii=True),
            "proposed",
            db.now(),
            req.requested_by,
            req.reason,
        ),
    )
    row = db.fetch_one(
        conn,
        "SELECT * FROM proposals WHERE namespace = ? AND proposal_id = ?",
        (req.namespace, proposal_id),
    )
    conn.close()
    if not row:  # pragma: no cover - defensive
        raise ValueError("proposal_insert_failed")
    return _row_to_proposal(row)


def get_proposal(namespace: str, proposal_id: str) -> ProposalRecord | None:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        "SELECT * FROM proposals WHERE namespace = ? AND proposal_id = ?",
        (namespace, proposal_id),
    )
    conn.close()
    if not row:
        return None
    return _row_to_proposal(row)


def _apply_create_card(namespace: str, payload: dict[str, Any]) -> dict[str, Any]:
    card = store.create_card(
        namespace=namespace,
        card_type=payload["type"],
        title=str(payload["title"]),
        summary=str(payload["summary"]),
        details_json=payload.get("details_json", {}),
        tags_json=[str(tag) for tag in payload.get("tags_json", [])],
        salience=float(payload.get("salience", 0.5)),
        confidence=float(payload.get("confidence", 0.7)),
        sensitivity_tier=int(payload.get("sensitivity_tier", 0)),
        status=payload.get("status", "active"),
        card_id=payload.get("card_id"),
    )
    out: dict[str, Any] = {"card_id": card.card_id}

    raw_refs = payload.get("refs")
    if isinstance(raw_refs, list) and raw_refs:
        refs = [CardRefInput(**item) for item in raw_refs]
        out["linked"] = store.link_card_refs(namespace=namespace, card_id=card.card_id, refs=refs)

    promotion = payload.get("promotion")
    if isinstance(promotion, dict):
        owner_type = str(promotion.get("owner_type") or "").strip()
        owner_id = str(promotion.get("owner_id") or "").strip()
        if owner_type in {"artifact", "chunk"} and owner_id:
            state = store.upsert_evidence_state(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                status="promoted",
                score=1.0,
                reason_json={
                    "reason": str(promotion.get("reason") or "promotion_confirmed"),
                    "proposal_apply": "create_card",
                    "card_id": card.card_id,
                    "requested_by": promotion.get("requested_by"),
                    "requested_mode": promotion.get("requested_mode"),
                    "effective_mode": promotion.get("effective_mode"),
                },
            )
            out["evidence_status"] = state["status"]
            out["promotion_owner_type"] = owner_type
            out["promotion_owner_id"] = owner_id
            out["index_job_id"] = store.enqueue_index_job(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                modality="text",
                priority=70,
            )

    return out


def _apply_update_card(namespace: str, payload: dict[str, Any]) -> dict[str, Any]:
    card_id = str(payload.get("card_id") or "").strip()
    if not card_id:
        raise ValueError("missing_card_id")

    updates: dict[str, Any] = payload.get("updates", {})
    if not updates:
        updates = {k: v for k, v in payload.items() if k != "card_id"}

    card = store.update_card(namespace=namespace, card_id=card_id, updates=updates)
    if not card:
        raise ValueError("card_not_found")
    return {"card_id": card.card_id, "updated": True}


def _apply_add_source(namespace: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = SourceCreateRequest(
        namespace=namespace,
        source_type=payload["source_type"],
        uri=payload["uri"],
        title=payload["title"],
        metadata_json=payload.get("metadata_json", {}),
        content_hash=payload.get("content_hash"),
        sensitivity_tier=int(payload.get("sensitivity_tier", 0)),
        document_text=payload.get("document_text"),
        chunk_size=int(payload.get("chunk_size", 700)),
        chunk_overlap=int(payload.get("chunk_overlap", 80)),
        artifacts=payload.get("artifacts", []),
    )
    out = store.create_source(req)
    return {
        "source_id": out.source.source_id,
        "doc_id": out.doc_id,
        "chunk_ids": out.chunk_ids,
        "artifact_ids": out.artifact_ids,
    }


def _apply_link_refs(namespace: str, payload: dict[str, Any]) -> dict[str, Any]:
    card_id = str(payload.get("card_id") or "").strip()
    if not card_id:
        raise ValueError("missing_card_id")

    raw_refs = payload.get("refs")
    if not isinstance(raw_refs, list) or not raw_refs:
        raise ValueError("missing_refs")

    refs = [CardRefInput(**item) for item in raw_refs]
    linked = store.link_card_refs(namespace=namespace, card_id=card_id, refs=refs)
    return {"card_id": card_id, "linked": linked}


def apply_proposal(namespace: str, proposal_type: ProposalType, payload_json: dict[str, Any]) -> dict[str, Any]:
    if proposal_type == "create_card":
        return _apply_create_card(namespace=namespace, payload=payload_json)
    if proposal_type == "update_card":
        return _apply_update_card(namespace=namespace, payload=payload_json)
    if proposal_type == "add_source":
        return _apply_add_source(namespace=namespace, payload=payload_json)
    if proposal_type == "link_refs":
        return _apply_link_refs(namespace=namespace, payload=payload_json)
    raise ValueError(f"unsupported_proposal_type:{proposal_type}")


def confirm_proposal(
    namespace: str,
    proposal_id: str,
    decided_by: str,
    reason: str | None,
) -> tuple[ProposalRecord | None, dict[str, Any] | None]:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        """
        SELECT *
        FROM proposals
        WHERE namespace = ? AND proposal_id = ? AND status = 'proposed'
        """,
        (namespace, proposal_id),
    )
    if not row:
        conn.close()
        return None, None

    proposal = _row_to_proposal(row)
    applied = apply_proposal(namespace, proposal.proposal_type, proposal.payload_json)

    db.execute_one(
        conn,
        """
        UPDATE proposals
        SET status = 'confirmed', decided_at = ?, decided_by = ?, reason = ?
        WHERE namespace = ? AND proposal_id = ?
        """,
        (db.now(), decided_by, reason, namespace, proposal_id),
    )

    updated_row = db.fetch_one(
        conn,
        "SELECT * FROM proposals WHERE namespace = ? AND proposal_id = ?",
        (namespace, proposal_id),
    )
    conn.close()
    if not updated_row:
        return None, applied
    return _row_to_proposal(updated_row), applied


def reject_proposal(
    namespace: str,
    proposal_id: str,
    decided_by: str,
    reason: str | None,
) -> ProposalRecord | None:
    conn = db.connect()
    row = db.fetch_one(
        conn,
        """
        SELECT *
        FROM proposals
        WHERE namespace = ? AND proposal_id = ? AND status = 'proposed'
        """,
        (namespace, proposal_id),
    )
    if not row:
        conn.close()
        return None

    db.execute_one(
        conn,
        """
        UPDATE proposals
        SET status = 'rejected', decided_at = ?, decided_by = ?, reason = ?
        WHERE namespace = ? AND proposal_id = ?
        """,
        (db.now(), decided_by, reason, namespace, proposal_id),
    )

    updated_row = db.fetch_one(
        conn,
        "SELECT * FROM proposals WHERE namespace = ? AND proposal_id = ?",
        (namespace, proposal_id),
    )
    conn.close()
    if not updated_row:
        return None
    return _row_to_proposal(updated_row)
