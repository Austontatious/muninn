from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..core.models import MemoryCard
from ..indexes import SQLiteDerivedIndexProvider, load_v2_cards
from ..retrieval import ShadowPreviewOptions, build_shadow_rehydrate_preview, hybrid_recall, lexical_recall
from ..retrieval.reinforcement import REINFORCEMENT_SCHEMA_VERSION
from .audit import write_bridge_artifacts
from .contracts import (
    BRIDGE_VERSION,
    bridge_response,
    payload_hash,
    safe_request_id,
    validate_operation_request,
)
from .policy import effective_limit, effective_max_context_chars, evaluate_policy
from .read_only import _path_snapshot, _reject_nonempty_wal


def run_bridge_request(
    *,
    v2_db: str | Path,
    policy: dict[str, Any],
    request: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Any]:
    request = dict(request)
    request.setdefault("request_id", safe_request_id(request.get("request_id")))
    input_hash = payload_hash(request)
    policy_hash = payload_hash(policy)
    validation_reasons = validate_operation_request(request)
    if validation_reasons:
        response = bridge_response(
            request=request,
            status="error",
            policy_decision={"allowed": False, "reason_codes": validation_reasons, "clamps": {}},
            degradation={"degraded": True, "reason_codes": ["request_validation_failed"]},
            error={"code": "InvalidBridgeRequest", "message": "Bridge request failed validation.", "details": {"reason_codes": validation_reasons}},
            input_hash=input_hash,
            policy_hash=policy_hash,
        )
        _write_artifacts(v2_db=v2_db, policy=policy, request=request, response=response, out_dir=out_dir)
        return response

    decision = evaluate_policy(request, policy)
    if not decision.allowed:
        response = bridge_response(
            request=request,
            status="denied",
            policy_decision=decision.to_dict(),
            degradation={"degraded": False, "reason_codes": []},
            error={"code": "DeniedByPolicy", "message": "Bridge request denied by capability policy.", "details": {"reason_codes": decision.reason_codes}},
            input_hash=input_hash,
            policy_hash=policy_hash,
        )
        _write_artifacts(v2_db=v2_db, policy=policy, request=request, response=response, out_dir=out_dir)
        return response

    db_path = Path(v2_db).expanduser()
    if not db_path.exists():
        response = bridge_response(
            request=request,
            status="error",
            policy_decision=decision.to_dict(),
            degradation={"degraded": True, "reason_codes": ["v2_db_missing"]},
            error={"code": "V2DatabaseMissing", "message": "Explicit v2 DB path does not exist.", "details": {"v2_db": str(db_path)}},
            input_hash=input_hash,
            policy_hash=policy_hash,
        )
        _write_artifacts(v2_db=v2_db, policy=policy, request=request, response=response, out_dir=out_dir)
        return response

    try:
        _reject_nonempty_wal(db_path)
        before = _path_snapshot(db_path)
        records = load_v2_cards(db_path, immutable=True)
        provider = SQLiteDerivedIndexProvider(db_path, records=records, read_only=True)
        response = _dispatch_allowed_request(
            request=request,
            policy=policy,
            decision=decision,
            v2_db=db_path,
            records=records,
            provider=provider,
            input_hash=input_hash,
            policy_hash=policy_hash,
        )
        after = _path_snapshot(db_path)
    except Exception as exc:
        response = bridge_response(
            request=request,
            status="error",
            policy_decision=decision.to_dict(),
            degradation={"degraded": True, "reason_codes": ["bridge_execution_failed"]},
            error={"code": "BridgeExecutionFailed", "message": str(exc), "details": {}},
            input_hash=input_hash,
            policy_hash=policy_hash,
        )
        before = _safe_snapshot(db_path)
        after = _safe_snapshot(db_path)

    _write_artifacts(v2_db=v2_db, policy=policy, request=request, response=response, out_dir=out_dir, before=before, after=after)
    return response


def _dispatch_allowed_request(
    *,
    request: dict[str, Any],
    policy: dict[str, Any],
    decision: Any,
    v2_db: Path,
    records: Sequence[MemoryCard],
    provider: SQLiteDerivedIndexProvider,
    input_hash: str,
    policy_hash: str,
) -> dict[str, Any]:
    operation = str(request["operation"])
    if operation == "health":
        result, degradation = _health_result(v2_db, records, provider, policy)
    elif operation == "search":
        result, degradation = _search_result(request, policy, decision, records, provider, v2_db)
    elif operation == "rehydrate":
        result, degradation = _rehydrate_result(request, policy, decision, records, provider, v2_db)
    elif operation == "explain":
        result, degradation = _explain_result(request, policy, decision, records, provider, v2_db)
    else:
        result = {}
        degradation = {"degraded": True, "reason_codes": ["unsupported_operation"]}
    return bridge_response(
        request=request,
        status="ok",
        policy_decision=decision.to_dict(),
        degradation=degradation,
        result=result,
        input_hash=input_hash,
        policy_hash=policy_hash,
    )


def _health_result(
    v2_db: Path,
    records: Sequence[MemoryCard],
    provider: SQLiteDerivedIndexProvider,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema_available = _table_exists(v2_db, "v2_cards")
    index_status = provider.status().to_dict()
    degradation_reasons = list(index_status.get("reason") or []) if index_status.get("degraded") else []
    return (
        {
            "bridge_version": BRIDGE_VERSION,
            "db_readable": True,
            "schema_available": schema_available,
            "cards_available": len(records),
            "index_status": index_status,
            "adaptive_scoring_default": False,
            "policy_loaded": True,
            "policy_consumer_id": policy.get("consumer_id"),
        },
        {"degraded": bool(degradation_reasons), "reason_codes": degradation_reasons},
    )


def _search_result(
    request: dict[str, Any],
    policy: dict[str, Any],
    decision: Any,
    records: Sequence[MemoryCard],
    provider: SQLiteDerivedIndexProvider,
    v2_db: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    limit = effective_limit(request, policy, decision)
    mode = str(request.get("retrieval_mode") or "hybrid")
    scope_key = str(request.get("space_key") or "")
    reinforcement_state, adaptive = _adaptive_context(request, policy, v2_db=v2_db, scope_key=scope_key)
    results, status = _run_retrieval(
        records,
        str(request.get("query") or ""),
        mode=mode,
        limit=limit,
        scope_key=scope_key,
        provider=provider,
        reinforcement_state=reinforcement_state,
    )
    include_evidence = bool(request.get("include_evidence"))
    include_explanations = bool(request.get("include_explanations"))
    cards = [_result_card_payload(item, include_evidence=include_evidence, include_explanations=include_explanations) for item in results]
    degradation = _degradation_from_status(status)
    if bool(policy.get("require_evidence")) and any(not item.get("evidence") for item in cards):
        degradation["degraded"] = True
        degradation["reason_codes"].append("evidence_required_but_unavailable")
    return (
        {
            "operation": "search",
            "query": request.get("query"),
            "retrieval_mode": mode,
            "limit": limit,
            "clamps": dict(decision.clamps),
            "results": cards,
            "result_count": len(cards),
            "adaptive_scoring": adaptive,
        },
        degradation,
    )


def _rehydrate_result(
    request: dict[str, Any],
    policy: dict[str, Any],
    decision: Any,
    records: Sequence[MemoryCard],
    provider: SQLiteDerivedIndexProvider,
    v2_db: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    limit = effective_limit(request, policy, decision)
    primary_limit = min(int(request.get("primary_limit") or 3), limit)
    recent_limit = max(0, limit - primary_limit)
    scope_key = str(request.get("space_key") or "")
    reinforcement_state, adaptive = _adaptive_context(request, policy, v2_db=v2_db, scope_key=scope_key)
    response = build_shadow_rehydrate_preview(
        records,
        provider=provider,
        options=ShadowPreviewOptions(
            v2_db=str(v2_db),
            query=str(request.get("query") or ""),
            limit=limit,
            primary_limit=primary_limit,
            recent_limit=recent_limit or 1,
            retrieval_mode=str(request.get("retrieval_mode") or "hybrid"),
            space_key=request.get("space_key"),
            project_path=_effective_project_path_filter(records, request.get("project_path")),
            include_evidence=bool(request.get("include_evidence")),
            include_explanations=bool(request.get("include_explanations")),
            max_chars=effective_max_context_chars(request, policy, decision),
            recent_supplement=bool(request.get("recent_supplement", True)),
            strict=bool(request.get("strict", True)),
            reinforcement_state=reinforcement_state,
        ),
    )
    degradation = {
        "degraded": bool(response["retrieval_provenance"]["degraded"]),
        "reason_codes": _fallback_reason_codes(response),
    }
    if bool(policy.get("require_evidence")) and not response["selected_memory"].get("evidence"):
        degradation["degraded"] = True
        degradation["reason_codes"].append("evidence_required_but_unavailable")
    return (
        {
            "operation": "rehydrate",
            "rehydrate_response": response,
            "adaptive_scoring": adaptive,
            "clamps": dict(decision.clamps),
        },
        degradation,
    )


def _explain_result(
    request: dict[str, Any],
    policy: dict[str, Any],
    decision: Any,
    records: Sequence[MemoryCard],
    provider: SQLiteDerivedIndexProvider,
    v2_db: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    card_id = str(request.get("card_id") or "")
    card = {card.id: card for card in records}.get(card_id)
    query = str(request.get("query") or "")
    explanation = provider.explain(card_id)
    retrieval_match: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    scope_key = str(request.get("space_key") or "")
    reinforcement_state, adaptive = _adaptive_context(request, policy, v2_db=v2_db, scope_key=scope_key)
    if query:
        results, status = _run_retrieval(
            records,
            query,
            mode=str(request.get("retrieval_mode") or "hybrid"),
            limit=effective_limit(request, policy, decision),
            scope_key=scope_key,
            provider=provider,
            reinforcement_state=reinforcement_state,
        )
        retrieval_match = next((item for item in results if item.get("record_id") == card_id), None)
    degradation = _degradation_from_status(status)
    if card is None:
        degradation["degraded"] = True
        degradation["reason_codes"].append("card_not_found")
    return (
        {
            "operation": "explain",
            "card_id": card_id,
            "card_found": card is not None,
            "card": _card_summary(card, include_evidence=True) if card else None,
            "derived_index": explanation,
            "retrieval_match": retrieval_match,
            "adaptive_scoring": adaptive,
        },
        degradation,
    )


def _run_retrieval(
    records: Sequence[MemoryCard],
    query: str,
    *,
    mode: str,
    limit: int,
    scope_key: str,
    provider: SQLiteDerivedIndexProvider,
    reinforcement_state: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if mode == "lexical":
        return lexical_recall(records, query, limit=limit, scope_key=scope_key), None
    if mode == "vector":
        return provider.query(query, limit=limit), provider.status().to_dict()
    payload = hybrid_recall(
        records,
        query,
        provider=provider,
        reinforcement_state=reinforcement_state,
        limit=limit,
        scope_key=scope_key,
    )
    return list(payload["results"]), payload.get("status")


def _adaptive_context(
    request: dict[str, Any],
    policy: dict[str, Any],
    *,
    v2_db: Path,
    scope_key: str,
) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any]]:
    requested = bool(request.get("allow_adaptive_scoring"))
    if not requested:
        return None, {
            "requested": False,
            "enabled": False,
            "default": False,
            "state_version": None,
            "state_count": 0,
            "boosted_cards": [],
            "suppressed_cards": [],
            "reason_codes": [],
        }
    if not bool(policy.get("allow_adaptive_scoring")):
        return None, {
            "requested": True,
            "enabled": False,
            "default": False,
            "state_version": None,
            "state_count": 0,
            "boosted_cards": [],
            "suppressed_cards": [],
            "reason_codes": ["adaptive_scoring_not_allowed"],
        }
    state_map = _load_reinforcement_state_readonly(v2_db, scope_key=scope_key)
    boosted = [
        record_id
        for record_id, item in sorted(state_map.items())
        if str(item.get("status") or "") in {"boosted", "preserved"}
    ]
    suppressed = [
        record_id
        for record_id, item in sorted(state_map.items())
        if str(item.get("status") or "") == "suppressed"
    ]
    enabled = bool(state_map)
    return (
        state_map if enabled else None,
        {
            "requested": True,
            "enabled": enabled,
            "default": False,
            "state_version": REINFORCEMENT_SCHEMA_VERSION if enabled else None,
            "state_count": len(state_map),
            "boosted_cards": boosted[:25],
            "suppressed_cards": suppressed[:25],
            "reason_codes": [] if enabled else ["reinforcement_state_unavailable"],
        },
    )


def _load_reinforcement_state_readonly(db_path: Path, *, scope_key: str | None) -> dict[str, dict[str, Any]]:
    if not _table_exists(db_path, "v2_reinforcement_state"):
        return {}
    uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
    sql = "SELECT record_id, record_json FROM v2_reinforcement_state"
    params: list[Any] = []
    if scope_key:
        sql += " WHERE scope_key = ?"
        params.append(scope_key)
    sql += " ORDER BY record_id ASC"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for record_id, record_json in rows:
        try:
            payload = _json_loads_object(record_json)
        except Exception:
            continue
        out[str(record_id)] = payload
    return out


def _json_loads_object(value: Any) -> dict[str, Any]:
    payload = json.loads(str(value))
    return payload if isinstance(payload, dict) else {}


def _result_card_payload(item: dict[str, Any], *, include_evidence: bool, include_explanations: bool) -> dict[str, Any]:
    card = MemoryCard.from_dict(item["record"]) if isinstance(item.get("record"), dict) else None
    payload = _card_summary(card, include_evidence=include_evidence) if card else {"id": item.get("record_id")}
    payload.update(
        {
            "score": item.get("score"),
            "rank": item.get("rank"),
            "backend": item.get("backend"),
            "scope_key": item.get("scope_key"),
        }
    )
    if include_explanations:
        payload["explanation"] = item.get("explanation")
    return payload


def _card_summary(card: MemoryCard | None, *, include_evidence: bool) -> dict[str, Any]:
    if card is None:
        return {}
    payload = {
        "id": card.id,
        "kind": card.kind,
        "title": card.title,
        "summary": card.summary,
        "body": card.body,
        "scope_key": card.scope_key,
        "updated_at": card.updated_at,
    }
    if include_evidence:
        payload["evidence"] = [item.to_dict() for item in card.evidence]
    return payload


def _degradation_from_status(status: dict[str, Any] | None) -> dict[str, Any]:
    reasons = list((status or {}).get("reason") or [])
    return {"degraded": bool((status or {}).get("degraded") or reasons), "reason_codes": reasons}


def _fallback_reason_codes(response: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for fallback in response.get("fallbacks") or []:
        reason = fallback.get("reason")
        if reason:
            reasons.append(str(reason))
    return reasons


def _effective_project_path_filter(records: Sequence[MemoryCard], project_path: Any) -> str | None:
    value = str(project_path or "").strip()
    if not value:
        return None
    for card in records:
        metadata = card.metadata if isinstance(card.metadata, dict) else {}
        if str(metadata.get("project_path") or metadata.get("root_path") or "") == value:
            return value
    return None


def _write_artifacts(
    *,
    v2_db: str | Path,
    policy: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    out_dir: str | Path,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    write_bridge_artifacts(
        request=request,
        policy=policy,
        response=response,
        out_dir=out_dir,
        v2_db=v2_db,
        db_before=before,
        db_after=after,
        retrieval_config={
            "operation": request.get("operation"),
            "retrieval_mode": request.get("retrieval_mode", "hybrid"),
            "limit": request.get("limit"),
            "max_context_chars": request.get("max_context_chars"),
        },
        adaptive_config={
            "requested": bool(request.get("allow_adaptive_scoring")),
            "enabled": bool(response.get("result", {}).get("adaptive_scoring", {}).get("enabled")),
            "default": False,
            "state_version": response.get("result", {}).get("adaptive_scoring", {}).get("state_version"),
            "state_count": response.get("result", {}).get("adaptive_scoring", {}).get("state_count", 0),
        },
    )


def _table_exists(db_path: Path, table_name: str) -> bool:
    uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
    return row is not None


def _safe_snapshot(db_path: Path) -> dict[str, Any] | None:
    try:
        return _path_snapshot(db_path) if db_path.exists() else None
    except Exception:
        return None
