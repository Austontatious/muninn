from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import BRIDGE_AUDIT_SCHEMA_VERSION, file_hash, payload_hash, safe_request_id


def write_bridge_artifacts(
    *,
    request: dict[str, Any],
    policy: dict[str, Any],
    response: dict[str, Any],
    out_dir: str | Path,
    v2_db: str | Path,
    db_before: dict[str, Any] | None,
    db_after: dict[str, Any] | None,
    retrieval_config: dict[str, Any],
    adaptive_config: dict[str, Any],
) -> dict[str, str]:
    output_dir = Path(out_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    request_id = safe_request_id(response.get("request_id") or request.get("request_id"))
    response_path = output_dir / f"bridge_response_{request_id}.json"
    audit_path = output_dir / f"bridge_audit_{request_id}.json"

    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = {
        "schema_version": BRIDGE_AUDIT_SCHEMA_VERSION,
        "record_type": "muninn_v2_bridge_audit",
        "request_id": request_id,
        "trace_id": response["audit"]["trace_id"],
        "operation": response["operation"],
        "consumer_id": response["consumer_id"],
        "created_at": response["audit"]["created_at"],
        "replayable": True,
        "request_hash": response["audit"]["input_hash"],
        "policy_hash": response["audit"]["policy_hash"] or payload_hash(policy),
        "response_hash": response["audit"]["response_hash"],
        "policy_decision": response["policy_decision"],
        "degradation": response["degradation"],
        "db": {
            "path": str(v2_db),
            "hash": file_hash(v2_db),
            "before": db_before,
            "after": db_after,
            "changed": _snapshot_changed(db_before, db_after),
        },
        "retrieval_config": retrieval_config,
        "adaptive_config": adaptive_config,
        "artifacts": {
            "response": str(response_path),
            "audit": str(audit_path),
        },
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"response": str(response_path), "audit": str(audit_path)}


def _snapshot_changed(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, bool]:
    if before is None or after is None:
        return {}
    keys = ["size_bytes", "mtime_ns", "wal_size_bytes", "wal_mtime_ns", "shm_size_bytes", "shm_mtime_ns"]
    return {key: before.get(key) != after.get(key) for key in keys}
