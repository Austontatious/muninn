from __future__ import annotations

import json
from typing import Any

from .. import db
from ..models import CardRefInput, ProposeRequest, RetrievedEvidence
from . import proposals, store

ACCESS_WINDOW_SECONDS = 7 * 24 * 60 * 60
QUERY_RECURRENCE_WINDOW_SECONDS = 24 * 60 * 60
REJECTION_COOLDOWN_SECONDS = 14 * 24 * 60 * 60


def _proposal_state(
    namespace: str,
    owner_type: str,
    owner_id: str,
) -> dict[str, Any]:
    conn = db.connect()
    rows = db.fetch_all(
        conn,
        """
        SELECT proposal_id, status, created_at, decided_at, payload_json
        FROM proposals
        WHERE namespace = ?
          AND proposal_type = 'create_card'
          AND status IN ('proposed','rejected')
        ORDER BY created_at DESC
        """,
        (namespace,),
    )
    conn.close()

    open_proposal_id: str | None = None
    latest_rejected_at: float | None = None
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            continue
        promotion = payload.get("promotion")
        if not isinstance(promotion, dict):
            continue
        if str(promotion.get("owner_type")) != owner_type:
            continue
        if str(promotion.get("owner_id")) != owner_id:
            continue

        status = str(row["status"])
        if status == "proposed" and open_proposal_id is None:
            open_proposal_id = str(row["proposal_id"])
        if status == "rejected":
            decided_at = row["decided_at"]
            if decided_at is None:
                continue
            rejected_at = float(decided_at)
            if latest_rejected_at is None or rejected_at > latest_rejected_at:
                latest_rejected_at = rejected_at

    return {
        "open_proposal_id": open_proposal_id,
        "latest_rejected_at": latest_rejected_at,
    }


def _default_card_title(owner_type: str, owner: dict[str, Any]) -> str:
    source_title = str(owner.get("source_title") or "").strip() or "Untitled source"
    if owner_type == "artifact":
        artifact_type = str(owner.get("artifact_type") or "artifact").strip()
        return f"{source_title} ({artifact_type})"
    return f"{source_title} excerpt"


def _default_card_summary(owner_type: str, owner: dict[str, Any]) -> str:
    text = str(owner.get("content_text") or "").strip()
    if text:
        compact = " ".join(text.split())
        if len(compact) > 240:
            compact = compact[:237].rstrip() + "..."
        return compact
    if owner_type == "artifact":
        artifact_type = str(owner.get("artifact_type") or "artifact").strip()
        return f"Promoted {artifact_type} evidence from source material."
    return "Promoted chunk evidence from source material."


def _default_tags(owner_type: str, owner: dict[str, Any]) -> list[str]:
    tags = {"meaningful", "promoted", owner_type}
    source_title = str(owner.get("source_title") or "").strip().lower()
    for token in source_title.split():
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if len(cleaned) >= 3:
            tags.add(cleaned)
        if len(tags) >= 8:
            break
    return sorted(tags)


def _default_refs(owner_type: str, owner_id: str, owner: dict[str, Any]) -> list[CardRefInput]:
    refs: list[CardRefInput] = []
    source_id = str(owner.get("source_id") or "").strip()
    if owner_type == "chunk":
        refs.append(CardRefInput(ref_type="chunk", ref_id=owner_id, role="evidence"))
        if source_id:
            refs.append(CardRefInput(ref_type="source", ref_id=source_id, role="primary"))
        return refs

    if source_id:
        refs.append(CardRefInput(ref_type="source", ref_id=source_id, role="evidence"))
    return refs


def _normalize_refs(
    owner_type: str,
    owner_id: str,
    owner: dict[str, Any],
    refs: list[CardRefInput] | None,
) -> list[CardRefInput]:
    if refs:
        return refs
    return _default_refs(owner_type=owner_type, owner_id=owner_id, owner=owner)


def promote_owner(
    namespace: str,
    owner_type: str,
    owner_id: str,
    mode: str = "propose",
    card_type: str = "fact",
    card_title: str | None = None,
    card_summary: str | None = None,
    tags: list[str] | None = None,
    refs: list[CardRefInput] | None = None,
    requested_by: str | None = None,
    reason: str = "manual_promote",
    enforce_cooldown: bool = False,
) -> dict[str, Any]:
    owner = store.get_evidence_owner(namespace=namespace, owner_type=owner_type, owner_id=owner_id)
    if not owner:
        raise ValueError("owner_not_found")

    existing_card_id = store.find_active_card_for_owner(
        namespace=namespace,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    if existing_card_id:
        state = store.upsert_evidence_state(
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
            status="promoted",
            score=1.0,
            reason_json={
                "reason": "already_linked_card",
                "card_id": existing_card_id,
            },
        )
        job_id = store.enqueue_index_job(
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
            modality="text",
            priority=70,
        )
        return {
            "status": "noop",
            "proposal_id": None,
            "card_id": existing_card_id,
            "notes": {
                "reason": "already_linked_card",
                "evidence_state": state["status"],
                "index_job_id": job_id,
            },
        }

    state = _proposal_state(namespace=namespace, owner_type=owner_type, owner_id=owner_id)
    open_proposal_id = state["open_proposal_id"]
    if open_proposal_id:
        return {
            "status": "noop",
            "proposal_id": open_proposal_id,
            "card_id": None,
            "notes": {"reason": "existing_open_proposal"},
        }

    now_ts = db.now()
    if enforce_cooldown and state["latest_rejected_at"] is not None:
        if now_ts - float(state["latest_rejected_at"]) < REJECTION_COOLDOWN_SECONDS:
            return {
                "status": "noop",
                "proposal_id": None,
                "card_id": None,
                "notes": {"reason": "cooldown_active"},
            }

    requested_mode = mode if mode in {"propose", "trusted"} else "propose"
    effective_mode = requested_mode
    sensitivity_tier = int(owner["sensitivity_tier"])
    if requested_mode == "trusted" and sensitivity_tier > 0:
        effective_mode = "propose"

    resolved_title = (card_title or "").strip() or _default_card_title(owner_type, owner)
    resolved_summary = (card_summary or "").strip() or _default_card_summary(owner_type, owner)
    resolved_tags = [str(tag) for tag in (tags or _default_tags(owner_type, owner))]
    resolved_refs = _normalize_refs(owner_type, owner_id, owner, refs)

    payload = {
        "type": card_type,
        "title": resolved_title,
        "summary": resolved_summary,
        "tags_json": resolved_tags,
        "refs": [ref.model_dump() for ref in resolved_refs],
        "promotion": {
            "owner_type": owner_type,
            "owner_id": owner_id,
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "reason": reason,
            "requested_by": requested_by,
            "sensitivity_tier": sensitivity_tier,
        },
    }

    proposal = proposals.create_proposal(
        ProposeRequest(
            namespace=namespace,
            proposal_type="create_card",
            payload_json=payload,
            requested_by=requested_by,
            reason=reason,
        )
    )

    candidate_reason = {
        "reason": reason,
        "proposal_id": proposal.proposal_id,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
    }
    store.upsert_evidence_state(
        namespace=namespace,
        owner_type=owner_type,
        owner_id=owner_id,
        status="candidate",
        score=1.0,
        reason_json=candidate_reason,
    )

    if effective_mode == "trusted":
        confirmed, applied = proposals.confirm_proposal(
            namespace=namespace,
            proposal_id=proposal.proposal_id,
            decided_by=requested_by or "trusted_mode",
            reason="trusted_mode_auto_confirm",
        )
        card_id = None
        index_job_id = None
        if applied:
            card_id = str(applied.get("card_id") or "") or None
            index_job_id = applied.get("index_job_id")
        return {
            "status": "promoted",
            "proposal_id": proposal.proposal_id,
            "card_id": card_id,
            "notes": {
                "reason": reason,
                "requested_mode": requested_mode,
                "effective_mode": effective_mode,
                "confirmed": confirmed is not None,
                "computed_refs": payload["refs"],
                "sensitivity_tier": sensitivity_tier,
                "index_job_id": index_job_id,
            },
        }

    return {
        "status": "proposed",
        "proposal_id": proposal.proposal_id,
        "card_id": None,
        "notes": {
            "reason": reason,
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "computed_refs": payload["refs"],
            "sensitivity_tier": sensitivity_tier,
        },
    }


def evaluate_implicit_triggers(
    namespace: str,
    evidence: list[RetrievedEvidence],
    query_hash: str | None,
    requested_by: str = "system:implicit_trigger",
) -> list[dict[str, Any]]:
    now_ts = db.now()
    actions: list[dict[str, Any]] = []
    seen_owners: set[tuple[str, str]] = set()

    conn = db.connect()
    for rank, item in enumerate(evidence, start=1):
        owner_type = str(item.ref.type or "").strip()
        owner_id = str(item.ref.id or "").strip()
        if owner_type not in {"artifact", "chunk"} or not owner_id:
            continue
        owner_key = (owner_type, owner_id)
        if owner_key in seen_owners:
            continue
        seen_owners.add(owner_key)

        owner = store.get_evidence_owner(namespace=namespace, owner_type=owner_type, owner_id=owner_id)
        if not owner:
            continue

        signal_row = db.fetch_one(
            conn,
            """
            SELECT access_count, last_accessed_at
            FROM signals
            WHERE namespace = ? AND owner_type = ? AND owner_id = ?
            """,
            (namespace, owner_type, owner_id),
        )
        access_count = int(signal_row["access_count"]) if signal_row else 0
        last_accessed_at = float(signal_row["last_accessed_at"]) if signal_row and signal_row["last_accessed_at"] is not None else 0.0

        current_state = store.get_evidence_state(
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        prior_reason = dict(current_state["reason_json"]) if current_state else {}
        prior_status = str(current_state["status"]) if current_state else "captured"

        top3_hits = int(prior_reason.get("top3_hits") or 0)
        if rank <= 3 and not item.blocked:
            top3_hits += 1

        previous_query_hash = str(prior_reason.get("last_query_hash") or "")
        previous_query_at = float(prior_reason.get("last_query_at") or 0.0)
        if query_hash and previous_query_hash == query_hash and now_ts - previous_query_at <= QUERY_RECURRENCE_WINDOW_SECONDS:
            query_recurrence = int(prior_reason.get("query_recurrence") or 1) + 1
        else:
            query_recurrence = 1

        trigger_access = (
            access_count >= 3
            and last_accessed_at > 0
            and (now_ts - last_accessed_at) <= ACCESS_WINDOW_SECONDS
        )
        trigger_query = query_recurrence >= 2
        trigger_top3 = top3_hits >= 3
        trigger_reasons = [
            reason
            for reason, active in (
                ("access_count_3_within_7d", trigger_access),
                ("query_recurrence_2_within_24h", trigger_query),
                ("top3_hits_3", trigger_top3),
            )
            if active
        ]

        reason_json = dict(prior_reason)
        reason_json.update(
            {
                "top3_hits": top3_hits,
                "last_query_hash": query_hash,
                "last_query_at": now_ts,
                "query_recurrence": query_recurrence,
                "last_rank": rank,
                "last_blocked": bool(item.blocked),
                "last_access_count": access_count,
                "last_accessed_at": last_accessed_at,
                "last_trigger_reasons": trigger_reasons,
            }
        )

        if prior_status == "promoted":
            store.upsert_evidence_state(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                status="promoted",
                score=1.0,
                reason_json=reason_json,
            )
            continue

        existing_card_id = store.find_active_card_for_owner(namespace, owner_type, owner_id)
        if existing_card_id:
            reason_json["reason"] = "already_linked_card"
            reason_json["card_id"] = existing_card_id
            state = store.upsert_evidence_state(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                status="promoted",
                score=1.0,
                reason_json=reason_json,
            )
            job_id = store.enqueue_index_job(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                modality="text",
                priority=70,
            )
            actions.append(
                {
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                    "status": state["status"],
                    "reason": "already_linked_card",
                    "proposal_id": None,
                    "index_job_id": job_id,
                }
            )
            continue

        if trigger_reasons and not item.blocked:
            score = min(
                1.0,
                (access_count / 5.0)
                + (top3_hits / 5.0)
                + (0.2 if query_recurrence >= 2 else 0.0),
            )
            reason_json["reason"] = "implicit_trigger"
            reason_json["trigger_reasons"] = trigger_reasons
            store.upsert_evidence_state(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                status="candidate",
                score=score,
                reason_json=reason_json,
            )

            promoted = promote_owner(
                namespace=namespace,
                owner_type=owner_type,
                owner_id=owner_id,
                mode="propose",
                requested_by=requested_by,
                reason="implicit_trigger",
                enforce_cooldown=True,
            )
            promoted["owner_type"] = owner_type
            promoted["owner_id"] = owner_id
            promoted["trigger_reasons"] = trigger_reasons
            actions.append(promoted)
            continue

        store.upsert_evidence_state(
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
            status="captured",
            score=float(current_state["score"]) if current_state else 0.0,
            reason_json=reason_json,
        )

    conn.close()
    return actions
