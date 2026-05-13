from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_PROPOSAL_TYPES = {
    "project_boundary",
    "durable_decision",
    "current_state_checkpoint",
    "known_risk",
    "confirmed_alignment",
    "next_step",
    "guardrail",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


class MimirProposalValidationError(ValueError):
    """Raised when a Mimir proposal batch is not safe to preview or approve."""


def load_proposal_batch(path: str | Path) -> dict[str, Any]:
    batch_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(batch_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MimirProposalValidationError(f"proposal_batch_missing:{batch_path}") from exc
    except json.JSONDecodeError as exc:
        raise MimirProposalValidationError(f"proposal_batch_malformed_json:{exc}") from exc
    if not isinstance(payload, dict):
        raise MimirProposalValidationError("proposal_batch_must_be_object")
    payload["_loaded_from"] = str(batch_path)
    return payload


def _stable_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _source_system(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("source_system") or "").strip()
    if explicit:
        return explicit
    schema_version = str(payload.get("schema_version") or "")
    if schema_version.startswith("mimir."):
        return "mimir"
    return ""


def _generated_by_command(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("generated_by_command") or "").strip()
    if explicit:
        return explicit
    if str(payload.get("schema_version") or "") == "mimir.muninn_memory_proposal_batch.v1":
        return "mimir world propose-memory"
    return ""


def normalize_proposal_batch(payload: dict[str, Any]) -> dict[str, Any]:
    proposals = payload.get("proposals")
    if not isinstance(proposals, list):
        proposals = []
    write_behavior = payload.get("write_behavior", {}) if isinstance(payload.get("write_behavior"), dict) else {}
    review_required = bool(payload.get("review_required", write_behavior.get("review_required_for_all_proposals", False)))
    normalized = dict(payload)
    normalized["batch_id"] = str(payload.get("batch_id") or f"mimir-proposals-{_stable_hash({'world_id': payload.get('world_id'), 'task': payload.get('task'), 'proposals': proposals})}")
    normalized["source_system"] = _source_system(payload)
    normalized["generated_by_command"] = _generated_by_command(payload)
    normalized["review_required"] = review_required
    normalized["writes_to_muninn"] = bool(payload.get("writes_to_muninn", write_behavior.get("writes_to_muninn", False)))
    normalized["writes_durable_memory"] = bool(payload.get("writes_durable_memory", write_behavior.get("writes_durable_memory", False)))
    normalized["proposals"] = proposals
    return normalized


def _proposal_errors(proposal: dict[str, Any], index: int) -> list[str]:
    prefix = f"proposals[{index}]"
    errors: list[str] = []
    if str(proposal.get("memory_type") or "") not in ALLOWED_PROPOSAL_TYPES:
        errors.append(f"{prefix}.unknown_memory_type:{proposal.get('memory_type')}")
    if str(proposal.get("confidence") or "") not in ALLOWED_CONFIDENCE:
        errors.append(f"{prefix}.invalid_confidence:{proposal.get('confidence')}")
    if proposal.get("review_required") is not True:
        errors.append(f"{prefix}.review_required_not_true")
    evidence = proposal.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{prefix}.missing_evidence")
    else:
        for evidence_index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"{prefix}.evidence[{evidence_index}].must_be_object")
                continue
            if not str(item.get("source_path") or "").strip() and not str(item.get("ref") or "").strip():
                errors.append(f"{prefix}.evidence[{evidence_index}].missing_source_path")
    source_paths = proposal.get("source_paths")
    if not isinstance(source_paths, list) or not [str(path).strip() for path in source_paths]:
        errors.append(f"{prefix}.missing_source_paths")
    if str(proposal.get("memory_type") or "") == "ambiguous_signal":
        review_metadata = proposal.get("review_metadata", {})
        if not isinstance(review_metadata, dict) or review_metadata.get("explicitly_reviewed") is not True:
            errors.append(f"{prefix}.ambiguous_signal_without_explicit_review")
    if str(proposal.get("title") or "").strip() == "":
        errors.append(f"{prefix}.missing_title")
    if str(proposal.get("summary") or "").strip() == "":
        errors.append(f"{prefix}.missing_summary")
    if str(proposal.get("why_durable") or "").strip() == "":
        errors.append(f"{prefix}.missing_why_durable")
    return errors


def validate_proposal_batch(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_proposal_batch(payload)
    errors: list[str] = []
    warnings: list[str] = []

    if normalized["source_system"] != "mimir":
        errors.append(f"source_system_not_mimir:{normalized['source_system'] or '<missing>'}")
    if not normalized.get("world_id"):
        errors.append("missing_world_id")
    if not normalized.get("task"):
        errors.append("missing_task")
    if not normalized.get("generated_by_command"):
        errors.append("missing_generated_by_command")
    if normalized.get("review_required") is not True:
        errors.append("batch_review_required_not_true")
    if normalized.get("writes_to_muninn") is True:
        errors.append("batch_claims_writes_to_muninn")
    if normalized.get("writes_durable_memory") is True:
        errors.append("batch_claims_writes_durable_memory")
    if not isinstance(normalized.get("proposals"), list) or not normalized["proposals"]:
        errors.append("missing_proposals")

    for index, proposal in enumerate(normalized.get("proposals", [])):
        if not isinstance(proposal, dict):
            errors.append(f"proposals[{index}].must_be_object")
            continue
        errors.extend(_proposal_errors(proposal, index))

    if payload.get("source_system") is None:
        warnings.append("source_system_inferred_from_mimir_schema_version")
    if payload.get("batch_id") is None:
        warnings.append("batch_id_deterministically_derived")
    if payload.get("generated_by_command") is None and normalized.get("generated_by_command"):
        warnings.append("generated_by_command_inferred_from_schema_version")

    proposal_types = sorted({
        str(proposal.get("memory_type"))
        for proposal in normalized.get("proposals", [])
        if isinstance(proposal, dict) and proposal.get("memory_type")
    })
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "batch_id": normalized.get("batch_id"),
        "source_system": normalized.get("source_system"),
        "world_id": normalized.get("world_id"),
        "task": normalized.get("task"),
        "proposal_count": len(normalized.get("proposals", [])),
        "proposal_types": proposal_types,
        "normalized_batch": normalized,
    }


def _confidence_score(confidence: str) -> float:
    return {"high": 0.85, "medium": 0.65, "low": 0.35}.get(confidence, 0.5)


def _card_kind(memory_type: str) -> str:
    if memory_type in {"project_boundary", "guardrail", "confirmed_alignment"}:
        return "interface"
    if memory_type in {"known_risk"}:
        return "constraint"
    if memory_type in {"next_step"}:
        return "runbook"
    return "decision"


def map_proposal_to_card_envelope(
    proposal: dict[str, Any],
    *,
    batch: dict[str, Any],
    namespace: str,
) -> dict[str, Any]:
    confidence = str(proposal.get("confidence") or "medium")
    evidence = proposal.get("evidence") if isinstance(proposal.get("evidence"), list) else []
    proposal_id = str(proposal.get("proposal_id") or _stable_hash(proposal))
    memory_type = str(proposal.get("memory_type") or "durable_decision")
    return {
        "contract_version": "1.0.0",
        "stable_id": f"mimir:{batch.get('batch_id')}:{proposal_id}",
        "kind": _card_kind(memory_type),
        "title": str(proposal.get("title") or ""),
        "summary": str(proposal.get("summary") or ""),
        "lifecycle": {
            "lifecycle_state": "observed",
            "status": "candidate",
            "reason": "Mimir proposal requires Muninn review/approval before durable write.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "confidence": {
            "score": _confidence_score(confidence),
            "trust_level": confidence if confidence in ALLOWED_CONFIDENCE else "medium",
            "rationale": str(proposal.get("why_durable") or ""),
        },
        "provenance": {
            "source_type": "derived",
            "source_id": f"mimir:{batch.get('world_id')}:{proposal_id}",
            "note": "Mapped from a Mimir declared-world memory proposal. Preview/dry-run mapping does not write memory.",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(evidence),
            "evidence": [
                {
                    "type": "file",
                    "ref": str(item.get("source_path") or item.get("ref") or ""),
                    "excerpt": str(item.get("excerpt") or "")[:240],
                }
                for item in evidence
                if isinstance(item, dict) and (item.get("source_path") or item.get("ref"))
            ],
            "metadata": {
                "namespace": namespace,
                "batch_id": batch.get("batch_id"),
                "world_id": batch.get("world_id"),
                "task": batch.get("task"),
                "proposal_id": proposal_id,
                "project_id": proposal.get("project_id"),
                "memory_type": memory_type,
                "suggested_namespace": proposal.get("suggested_namespace"),
                "suggested_tags": proposal.get("suggested_tags", []),
                "review_required": proposal.get("review_required"),
            },
        },
        "topology_refs": [
            {
                "ref_kind": "space",
                "ref_id": namespace,
                "relation": "proposed_for_namespace",
            }
        ],
        "payload": {
            "source_system": "mimir",
            "batch_id": batch.get("batch_id"),
            "proposal_id": proposal_id,
            "world_id": batch.get("world_id"),
            "task": batch.get("task"),
            "project_id": proposal.get("project_id"),
            "scope": proposal.get("scope"),
            "memory_type": memory_type,
            "source_paths": proposal.get("source_paths", []),
            "suggested_tags": proposal.get("suggested_tags", []),
            "why_durable": proposal.get("why_durable"),
            "review_metadata": {
                "review_required": True,
                "approved_by": None,
                "approved_at": None,
            },
        },
    }


def preview_proposal_batch(
    payload: dict[str, Any],
    *,
    namespace: str,
    proposal_ids: list[str] | None = None,
) -> dict[str, Any]:
    validation = validate_proposal_batch(payload)
    if not validation["ok"]:
        return {
            "ok": False,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "cards": [],
            "would_write": False,
        }
    batch = validation["normalized_batch"]
    selected_ids = {item for item in proposal_ids or [] if item}
    proposals = [
        proposal
        for proposal in batch["proposals"]
        if isinstance(proposal, dict) and (not selected_ids or str(proposal.get("proposal_id")) in selected_ids)
    ]
    missing = sorted(selected_ids - {str(proposal.get("proposal_id")) for proposal in proposals})
    cards = [
        map_proposal_to_card_envelope(proposal, batch=batch, namespace=namespace)
        for proposal in proposals
    ]
    return {
        "ok": not missing,
        "errors": [f"proposal_id_not_found:{proposal_id}" for proposal_id in missing],
        "warnings": validation["warnings"],
        "batch_id": batch["batch_id"],
        "world_id": batch.get("world_id"),
        "namespace": namespace,
        "selected_count": len(cards),
        "cards": cards,
        "would_write": False,
    }


def approve_proposal_batch(
    payload: dict[str, Any],
    *,
    namespace: str,
    proposal_ids: list[str] | None = None,
    approve_all: bool = False,
    write: bool = False,
) -> dict[str, Any]:
    if write:
        return {
            "ok": False,
            "errors": ["write_mode_not_implemented_in_this_contract_slice"],
            "warnings": [],
            "cards": [],
            "would_write": True,
            "wrote": False,
        }
    if not approve_all and not proposal_ids:
        return {
            "ok": False,
            "errors": ["approval_requires_proposal_id_or_approve_all"],
            "warnings": [],
            "cards": [],
            "would_write": False,
            "wrote": False,
        }
    preview = preview_proposal_batch(
        payload,
        namespace=namespace,
        proposal_ids=None if approve_all else proposal_ids,
    )
    preview["approval_mode"] = "all" if approve_all else "selected"
    preview["dry_run"] = True
    preview["wrote"] = False
    return preview
