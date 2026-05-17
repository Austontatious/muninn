from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..indexes import SQLiteDerivedIndexProvider, load_v2_cards
from ..retrieval import ShadowPreviewOptions, build_shadow_rehydrate_preview, write_shadow_rehydrate_preview_reports


BRIDGE_REQUEST_SCHEMA_VERSION = "muninn.v2.bridge_request.v1"
BRIDGE_REQUEST_CONTRACT_VERSION = "1.0.0"
BRIDGE_AUDIT_SCHEMA_VERSION = "muninn.v2.bridge_audit.v1"
BRIDGE_CAPABILITY_POLICY_VERSION = "muninn.v2.bridge_capability_policy.v1"


class BridgePolicyError(RuntimeError):
    """Raised when a v2 bridge request violates read-only bridge policy."""


def load_bridge_request(path: str | Path) -> dict[str, Any]:
    request_path = Path(path).expanduser()
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BridgePolicyError("bridge_request_must_be_object")
    return payload


def validate_bridge_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BridgePolicyError("bridge_request_must_be_object")
    if payload.get("schema_version") != BRIDGE_REQUEST_SCHEMA_VERSION:
        raise BridgePolicyError("unsupported_bridge_request_schema_version")
    if payload.get("contract_version") != BRIDGE_REQUEST_CONTRACT_VERSION:
        raise BridgePolicyError("unsupported_bridge_request_contract_version")

    capability = _required_dict(payload, "capability")
    if capability.get("name") != "read_only_context":
        raise BridgePolicyError("unsupported_bridge_capability")
    if capability.get("version") != BRIDGE_REQUEST_CONTRACT_VERSION:
        raise BridgePolicyError("unsupported_bridge_capability_version")

    safety = _required_dict(payload, "safety")
    if safety.get("dry_run") is not True:
        raise BridgePolicyError("bridge_dry_run_required")
    forbidden_true = {
        "allow_writes": "bridge_writes_forbidden",
        "allow_v1_access": "bridge_v1_access_forbidden",
        "allow_reinforcement_events": "bridge_reinforcement_event_writes_forbidden",
        "adaptive_retrieval": "bridge_adaptive_retrieval_default_forbidden",
        "allow_llm": "bridge_llm_dependency_forbidden",
    }
    for key, reason in forbidden_true.items():
        if bool(safety.get(key)):
            raise BridgePolicyError(reason)

    source = _required_dict(payload, "source")
    v2_db = str(source.get("v2_db") or "").strip()
    if not v2_db:
        raise BridgePolicyError("bridge_v2_db_required")
    if not Path(v2_db).expanduser().exists():
        raise BridgePolicyError(f"bridge_v2_db_not_found:{v2_db}")

    query = _required_dict(payload, "query")
    if not str(query.get("text") or "").strip():
        raise BridgePolicyError("bridge_query_text_required")

    options = _required_dict(payload, "options")
    mode = str(options.get("retrieval_mode") or "hybrid")
    if mode not in {"hybrid", "lexical", "vector"}:
        raise BridgePolicyError("unsupported_bridge_retrieval_mode")
    for key in ["limit", "primary_limit", "recent_limit"]:
        if int(options.get(key, 0)) < 1:
            raise BridgePolicyError(f"bridge_{key}_must_be_positive")
    max_chars = options.get("max_chars")
    if max_chars is not None and int(max_chars) < 1:
        raise BridgePolicyError("bridge_max_chars_must_be_positive")
    return payload


def build_read_only_bridge_context(
    request: dict[str, Any],
    *,
    out_dir: str | Path,
) -> dict[str, Any]:
    payload = validate_bridge_request(request)
    output_dir = Path(out_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    source = payload["source"]
    query = payload["query"]
    options = payload["options"]
    v2_db = Path(str(source["v2_db"])).expanduser()
    _reject_nonempty_wal(v2_db)
    before = _path_snapshot(v2_db)
    records = load_v2_cards(v2_db, immutable=True)
    provider = SQLiteDerivedIndexProvider(v2_db, records=records, read_only=True)
    response = build_shadow_rehydrate_preview(
        records,
        provider=provider,
        options=ShadowPreviewOptions(
            v2_db=str(v2_db),
            query=str(query["text"]),
            limit=int(options["limit"]),
            primary_limit=int(options["primary_limit"]),
            recent_limit=int(options["recent_limit"]),
            retrieval_mode=str(options.get("retrieval_mode") or "hybrid"),
            space_key=source.get("space_key"),
            project_path=source.get("project_path"),
            include_evidence=bool(options.get("include_evidence")),
            include_explanations=bool(options.get("include_explanations")),
            max_chars=options.get("max_chars"),
            recent_supplement=bool(options.get("recent_supplement", True)),
            strict=bool(options.get("strict")),
        ),
    )
    response["request"]["output"] = {
        "out_dir": str(output_dir),
        "json_report": str(output_dir / "bridge_rehydrate_response.json"),
        "md_report": str(output_dir / "bridge_context.md"),
    }
    artifacts = write_shadow_rehydrate_preview_reports(
        response,
        output_dir,
        json_report=output_dir / "bridge_rehydrate_response.json",
        md_report=output_dir / "bridge_context.md",
    )
    after = _path_snapshot(v2_db)
    audit = _bridge_audit(
        request=payload,
        response=response,
        out_dir=output_dir,
        artifacts=artifacts,
        before=before,
        after=after,
    )
    audit_path = output_dir / "bridge_audit_log.json"
    audit["artifacts"]["audit"] = str(audit_path)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def _bridge_audit(
    *,
    request: dict[str, Any],
    response: dict[str, Any],
    out_dir: Path,
    artifacts: dict[str, str],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    changed = {
        "v2_db_size_bytes": before["size_bytes"] != after["size_bytes"],
        "v2_db_mtime_ns": before["mtime_ns"] != after["mtime_ns"],
        "v2_wal_size_bytes": before["wal_size_bytes"] != after["wal_size_bytes"],
        "v2_wal_mtime_ns": before["wal_mtime_ns"] != after["wal_mtime_ns"],
        "v2_shm_size_bytes": before["shm_size_bytes"] != after["shm_size_bytes"],
        "v2_shm_mtime_ns": before["shm_mtime_ns"] != after["shm_mtime_ns"],
    }
    canonical_changed = changed["v2_db_size_bytes"] or changed["v2_db_mtime_ns"]
    sidecar_changed = any(
        changed[key]
        for key in [
            "v2_wal_size_bytes",
            "v2_wal_mtime_ns",
            "v2_shm_size_bytes",
            "v2_shm_mtime_ns",
        ]
    )
    selected = response["budget"]["selected_total"]
    return {
        "schema_version": BRIDGE_AUDIT_SCHEMA_VERSION,
        "record_type": "muninn_v2_bridge_context_audit",
        "contract_version": BRIDGE_REQUEST_CONTRACT_VERSION,
        "request_id": request.get("request_id"),
        "mode": "read_only_bridge_context",
        "capability_policy": {
            "schema_version": BRIDGE_CAPABILITY_POLICY_VERSION,
            "capability": "read_only_context",
            "allowed_operations": ["read_v2_cards", "read_v2_derived_index", "emit_rehydrate_response"],
            "forbidden_operations": [
                "write_v1",
                "write_v2_canonical_memory",
                "record_recall_event",
                "default_adaptive_retrieval",
                "live_mcp_or_codex_cutover",
                "llm_required_context_generation",
            ],
        },
        "source": {
            "v2_db": str(request["source"]["v2_db"]),
            "space_key": request["source"].get("space_key"),
            "project_path": request["source"].get("project_path"),
        },
        "response": {
            "schema_version": response["schema_version"],
            "contract_version": response["contract_version"],
            "response_id": response["response_id"],
            "response_kind": response["response_kind"],
            "selected_total": selected,
            "retrieval_mode": response["retrieval_provenance"]["mode"],
            "degraded": response["retrieval_provenance"]["degraded"],
            "fallbacks": response["fallbacks"],
            "artifacts": artifacts,
        },
        "db_snapshot": {
            "before": before,
            "after": after,
            "changed": changed,
        },
        "safety": {
            "v1_accessed": False,
            "v1_mutated": False,
            "v2_canonical_memory_mutated": canonical_changed,
            "v2_storage_sidecar_changed": sidecar_changed,
            "recall_events_recorded": False,
            "adaptive_retrieval_enabled_by_default": False,
            "live_mcp_or_codex_defaults_changed": False,
            "llm_used": False,
            "read_only_ok": not any(changed.values()),
        },
        "decision": "go_read_only_bridge" if selected and not any(changed.values()) else "no_go_review_required",
        "out_dir": str(out_dir),
        "artifacts": dict(artifacts),
    }


def _path_snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    wal = Path(str(path) + "-wal")
    shm = Path(str(path) + "-shm")
    wal_stat = wal.stat() if wal.exists() else None
    shm_stat = shm.stat() if shm.exists() else None
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "wal_size_bytes": wal_stat.st_size if wal_stat else 0,
        "wal_mtime_ns": wal_stat.st_mtime_ns if wal_stat else None,
        "shm_size_bytes": shm_stat.st_size if shm_stat else 0,
        "shm_mtime_ns": shm_stat.st_mtime_ns if shm_stat else None,
    }


def _reject_nonempty_wal(path: Path) -> None:
    wal = Path(str(path) + "-wal")
    if wal.exists() and wal.stat().st_size > 0:
        raise BridgePolicyError(f"bridge_v2_db_has_uncheckpointed_wal:{wal}")


def _required_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise BridgePolicyError(f"bridge_{key}_required")
    return value
