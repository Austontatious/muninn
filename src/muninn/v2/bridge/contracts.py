from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..core.models import utc_now

BRIDGE_CONTRACT_VERSION = "1.0.0"
BRIDGE_REQUEST_SCHEMA_VERSION = "BridgeRequestV1"
BRIDGE_RESPONSE_SCHEMA_VERSION = "BridgeResponseV1"
BRIDGE_POLICY_SCHEMA_VERSION = "BridgeCapabilityPolicyV1"
BRIDGE_AUDIT_SCHEMA_VERSION = "BridgeAuditV1"
BRIDGE_VERSION = "muninn-v2-bridge/1.0.0"
SUPPORTED_OPERATIONS = {"health", "search", "rehydrate", "explain"}


def load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json_payload_must_be_object")
    return payload


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def file_hash(path: str | Path) -> str | None:
    target = Path(path).expanduser()
    if not target.exists() or not target.is_file():
        return None
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def safe_request_id(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raw = "request_" + short_hash(utc_now())
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._-")
    return cleaned[:96] or "request_" + short_hash(raw)


def validate_operation_request(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not isinstance(payload, dict):
        return ["invalid_request_object"]
    if payload.get("schema_version") != BRIDGE_REQUEST_SCHEMA_VERSION:
        reasons.append("invalid_schema_version")
    operation = payload.get("operation")
    if not operation:
        reasons.append("missing_operation")
    if not str(payload.get("consumer_id") or "").strip():
        reasons.append("missing_consumer_id")
    if operation in {"search", "rehydrate"} and not str(payload.get("query") or "").strip():
        reasons.append("missing_query")
    if operation == "explain" and not str(payload.get("card_id") or "").strip():
        reasons.append("missing_card_id")
    if operation in {"search", "rehydrate", "explain"}:
        if not str(payload.get("space_key") or "").strip() or not str(payload.get("project_path") or "").strip():
            reasons.append("missing_project_scope")
    if payload.get("allow_reinforcement_write") is True:
        reasons.append("reinforcement_write_forbidden")
    return reasons


def bridge_response(
    *,
    request: dict[str, Any],
    status: str,
    policy_decision: dict[str, Any],
    degradation: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    trace_id: str | None = None,
    input_hash: str | None = None,
    policy_hash: str | None = None,
) -> dict[str, Any]:
    request_id = safe_request_id(request.get("request_id"))
    response = {
        "schema_version": BRIDGE_RESPONSE_SCHEMA_VERSION,
        "contract_version": BRIDGE_CONTRACT_VERSION,
        "record_type": "muninn_v2_bridge_response",
        "request_id": request_id,
        "operation": str(request.get("operation") or "unknown"),
        "consumer_id": str(request.get("consumer_id") or ""),
        "status": status,
        "policy_decision": policy_decision,
        "degradation": degradation or {"degraded": False, "reason_codes": []},
        "result": result or {},
        "error": error,
        "audit": {
            "trace_id": trace_id or "bridge_" + short_hash(request_id + ":" + utc_now()),
            "created_at": utc_now(),
            "replayable": True,
            "input_hash": input_hash or payload_hash(request),
            "policy_hash": policy_hash,
            "response_hash": None,
        },
    }
    response["audit"]["response_hash"] = payload_hash({**response, "audit": {**response["audit"], "response_hash": None}})
    return response
