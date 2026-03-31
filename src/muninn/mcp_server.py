from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import re
import socket
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, TextIO

import httpx
import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from . import __version__
from .human_memory.bootstrap import (
    DEFAULT_CLIENT_NAME,
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from .human_memory.adaptation import (
    ADAPTATION_MEMORY_TYPES,
    ADAPTATION_PERSISTENCE_VALUES,
    ADAPTATION_VIEWS,
    build_prompt_state_summary,
    query_adaptation_cards,
)
from .human_memory.cards import (
    card_supersede,
    card_upsert,
    cards_merge,
    cards_recent,
    cards_search,
    cards_search_count,
)
from .human_memory.interactions import list_interaction_events
from .human_memory.policy import (
    OUTCOME_TYPES,
    POLICY_KINDS,
    SIGNAL_TYPES,
    learn_policy_signal,
    query_policy_cards,
)
from .human_memory.rehydration import rehydrate_bundle
from .human_memory.spaces import (
    ResolvedSpace,
    canonicalize_space_key,
    get_or_create_space,
    get_space_summary,
    resolve_space_from_cwd,
    resolve_space_lookup_keys,
)
from .models import (
    ConfirmCandidatesRequest,
    ListPendingRequest,
    RehydrateRequest,
    StageCandidatesRequest,
)
from .telemetry import (
    close_telemetry_handle as _close_shared_telemetry_handle,
    emit_event as _emit_telemetry_event,
    resolve_telemetry_backup_count,
    resolve_telemetry_flush,
    resolve_telemetry_max_bytes,
    resolve_telemetry_path,
    telemetry_context,
)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_base_url() -> str:
    return os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _resolve_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.getenv("MUNINN_API_KEY")
    if api_key:
        header_name = os.getenv("MUNINN_API_KEY_HEADER", "X-API-Key")
        headers[header_name] = api_key
    return headers


def _resolve_mcp_requires_api_key() -> bool:
    value = os.getenv("MUNINN_MCP_REQUIRE_API_KEY")
    if value is None:
        return bool(os.getenv("MUNINN_API_KEY")) or bool(os.getenv("MUNINN_MCP_BEARER_TOKEN"))
    return value.strip() == "1"


def _resolve_mcp_api_key() -> str | None:
    value = os.getenv("MUNINN_API_KEY")
    if value is None:
        return None
    value = value.strip()
    return value or None


def _resolve_mcp_api_key_header() -> str:
    value = os.getenv("MUNINN_API_KEY_HEADER", "X-API-Key").strip()
    return value or "X-API-Key"


def _resolve_mcp_bearer_token() -> str | None:
    value = os.getenv("MUNINN_MCP_BEARER_TOKEN")
    if value is None:
        return None
    value = value.strip()
    return value or None


def _resolve_mcp_enable_slash_aliases() -> bool:
    return _env_flag("MUNINN_MCP_ENABLE_SLASH_ALIASES", True)


def _resolve_mcp_suppress_alias_warnings() -> bool:
    return _env_flag("MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS", True)


def _resolve_mcp_card_write_limit_per_hour() -> int:
    raw = os.getenv("MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR", "20").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 20
    return max(0, value)


def _resolve_mcp_card_write_window_seconds() -> int:
    raw = os.getenv("MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS", "3600").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 3600
    return max(1, value)


def _resolve_mcp_telemetry_path() -> Path | None:
    return resolve_telemetry_path()


def _resolve_mcp_telemetry_flush() -> bool:
    return resolve_telemetry_flush()


def _resolve_mcp_telemetry_max_bytes() -> int | None:
    return resolve_telemetry_max_bytes()


def _resolve_mcp_telemetry_backup_count() -> int:
    return resolve_telemetry_backup_count()


if _resolve_mcp_enable_slash_aliases() and _resolve_mcp_suppress_alias_warnings():
    # Keep deprecated slash aliases available without spamming runtime warnings.
    logging.getLogger("mcp.shared.tool_name_validation").setLevel(logging.ERROR)


def _close_telemetry_handle() -> None:
    _close_shared_telemetry_handle()


def _append_tool_event_jsonl(event: dict[str, Any]) -> None:
    _emit_telemetry_event(event)


def _normalize_host(host: str) -> str:
    normalized = host.strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    return normalized


def _format_http_url(host: str, port: int, path: str) -> str:
    normalized = _normalize_host(host)
    if ":" in normalized and not normalized.startswith("["):
        normalized = f"[{normalized}]"
    if not path.startswith("/"):
        path = "/" + path
    return f"http://{normalized}:{port}{path}"


def _is_loopback_host(host: str) -> bool:
    normalized = _normalize_host(host).lower()
    if normalized == "localhost":
        return True
    try:
        parsed = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return bool(parsed.is_loopback)


def _is_wildcard_host(host: str) -> bool:
    normalized = _normalize_host(host).lower()
    return normalized in {"0.0.0.0", "::"}


def _get_primary_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 1))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _list_interface_ipv4s() -> list[str]:
    ips: set[str] = set()
    primary = _get_primary_lan_ip()
    if primary and not primary.startswith("127."):
        ips.add(primary)
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET)
    except OSError:
        infos = []
    for info in infos:
        candidate = str(info[4][0])
        if not candidate or candidate.startswith("127."):
            continue
        ips.add(candidate)
    return sorted(ips)


def _has_mcp_auth_secret() -> bool:
    return bool(_resolve_mcp_api_key()) or bool(_resolve_mcp_bearer_token())


def _mcp_auth_mode() -> str:
    has_header_key = bool(_resolve_mcp_api_key())
    has_bearer = bool(_resolve_mcp_bearer_token())
    if has_header_key and has_bearer:
        return "api_key_or_bearer"
    if has_header_key:
        return "api_key"
    if has_bearer:
        return "bearer"
    return "off"


def _mcp_auth_state() -> str:
    if _resolve_mcp_requires_api_key():
        return "on"
    return "off"


def _coerce_primary_space(payload: dict[str, Any]) -> str | None:
    space_key = payload.get("space_key")
    if isinstance(space_key, str) and space_key.strip():
        return space_key.strip()
    canonical = payload.get("canonical_space_key")
    if isinstance(canonical, str) and canonical.strip():
        return canonical.strip()
    space_keys = payload.get("space_keys")
    if isinstance(space_keys, list):
        for item in space_keys:
            text = str(item or "").strip()
            if text:
                return text
    return None


def _coerce_result_count(payload: dict[str, Any]) -> int | None:
    for field in ("result_count", "results", "cards", "project_cards"):
        value = payload.get(field)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _log_tool_invocation(tool: str, **payload: Any) -> None:
    event_payload = dict(payload)
    invoked_as = str(event_payload.pop("invoked_as", tool))
    deprecated_alias = bool(event_payload.pop("deprecated_alias", False))
    status = str(event_payload.get("status", "")).strip().lower()
    error_code = event_payload.get("error_code")
    event_payload.setdefault("operation", tool)
    event_payload.setdefault("success", status == "ok" and not bool(error_code))
    primary_space = _coerce_primary_space(event_payload)
    if primary_space and "space" not in event_payload:
        event_payload["space"] = primary_space
    if "result_count" not in event_payload:
        result_count = _coerce_result_count(event_payload)
        if result_count is not None:
            event_payload["result_count"] = result_count
    event_name = "tool_error" if status == "error" or error_code else "tool_call"
    event = {
        "ts": round(time.time(), 3),
        "event": event_name,
        "module": "muninn.mcp_server",
        "tool": tool,
        "invoked_as": invoked_as,
        "deprecated_alias": deprecated_alias,
        **telemetry_context(),
        **event_payload,
    }
    _emit_telemetry_event(event, stream_prefix="MCP_TOOL", stream="stderr")


def _emit_runtime_event(event_name: str, **payload: Any) -> None:
    event = {
        "ts": round(time.time(), 3),
        "event": event_name,
        "module": "muninn.mcp_server",
        **telemetry_context(),
        **payload,
    }
    _emit_telemetry_event(event, stream_prefix="MUNINN_EVENT", stream="stderr")


def _new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def _elapsed_ms(start_ts: float) -> int:
    return int((time.perf_counter() - start_ts) * 1000)


_LEGACY_KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\:(?P<value>[^\s]+)")
_EVIDENCE_PREFERRED_KINDS = frozenset(
    {
        "decision",
        "constraint",
        "interface",
        "runbook",
        "policy.directive",
        "policy.preference",
        "policy.anti_pattern",
        "workflow.heuristic",
        "tooling.preference",
        "rehydration.priority",
    }
)
_TOOL_DERIVED_EVIDENCE_TYPES = frozenset({"file", "diff", "commit", "test", "log"})
ATLAS_KIND_PREFIX = "atlas."
ATLAS_ENTITY_TYPES = ("project", "capability", "relationship", "risk", "active_direction")
ATLAS_KINDS = tuple(f"{ATLAS_KIND_PREFIX}{entity_type}" for entity_type in ATLAS_ENTITY_TYPES)


def _summarize_text(value: str | None, *, max_chars: int = 120) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


def _parse_legacy_kv_text(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        raise ValueError("invalid_legacy_payload:empty")
    if text.startswith("{"):
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ValueError("invalid_legacy_payload:json_object_required")
        return loaded
    parsed: dict[str, Any] = {}
    for match in _LEGACY_KV_RE.finditer(text):
        key = str(match.group("key")).strip().lower()
        raw_value = str(match.group("value")).strip()
        parsed[key] = raw_value
    if not parsed:
        raise ValueError("invalid_legacy_payload:expected key:value pairs or json object")
    return parsed


def _coerce_string_list(value: Any, *, field_name: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        items = [item.strip() for item in re.split(r"[,\s]+", value) if item.strip()]
        return items or None
    if isinstance(value, (tuple, set)):
        value = list(value)
    if not isinstance(value, list):
        raise ValueError(f"invalid_{field_name}:expected list[str] or comma-separated string")
    return [str(item) for item in value]


def _resolve_query_text(value: Any) -> str:
    if isinstance(value, SearchQueryInput):
        return value.resolved_text()
    if isinstance(value, (dict, list)):
        return SearchQueryInput.model_validate(value).resolved_text()
    text = str(value or "").strip()
    if not text:
        raise ValueError("invalid_query:empty")
    return text


def _summarize_query_input(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, SearchQueryInput):
        try:
            return _summarize_query_for_log(value.resolved_text())
        except ValueError:
            return {"shape": "search_query_input"}
    if isinstance(value, dict):
        for key in ("text", "q", "query"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return _summarize_query_for_log(candidate)
        terms = value.get("terms")
        if isinstance(terms, list):
            joined = " ".join(str(item).strip() for item in terms if str(item).strip())
            if joined:
                return _summarize_query_for_log(joined)
        return {"shape": "query_object"}
    if isinstance(value, list):
        joined = " ".join(str(item).strip() for item in value if str(item).strip())
        if joined:
            return _summarize_query_for_log(joined)
        return {"shape": "query_list", "terms": len(value)}
    text = str(value).strip()
    if not text:
        return {"shape": type(value).__name__}
    return _summarize_query_for_log(text)


def _query_input_type(value: Any) -> str:
    if isinstance(value, SearchQueryInput):
        return "search_query_input"
    if isinstance(value, dict):
        return "query_object"
    if isinstance(value, list):
        return "query_terms_list"
    return "query_text"


def _summarize_query_for_log(query: str) -> dict[str, Any]:
    return {
        "text": _summarize_text(query, max_chars=96),
        "chars": len(query),
        "terms": len([token for token in re.split(r"\s+", query.strip()) if token]),
    }


def _summarize_lens_for_log(lens: LensInput) -> dict[str, Any]:
    return {
        "space": lens.space,
        "space_key": lens.space_key,
        "cwd": lens.cwd,
        "scope": lens.scope,
        "kinds": list(lens.kinds or []),
        "status": lens.status,
        "tags": list(lens.tags or []),
        "limit": lens.limit,
    }


def _normalize_token(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _dedupe_string_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = str(raw).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out or None


def _atlas_kind_from_entity_type(entity_type: str) -> str:
    normalized = _normalize_token(entity_type).replace(" ", "_")
    return f"{ATLAS_KIND_PREFIX}{normalized}"


def _atlas_entity_type_from_kind(kind: str) -> str | None:
    normalized = _normalize_token(kind)
    if not normalized.startswith(ATLAS_KIND_PREFIX):
        return None
    entity_type = normalized.removeprefix(ATLAS_KIND_PREFIX).strip()
    if entity_type in set(ATLAS_ENTITY_TYPES):
        return entity_type
    return None


def _build_evidence_refs(
    evidence: list["EvidenceInput"] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    evidence_refs: list[dict[str, Any]] = []
    evidence_ids: list[str] = []
    evidence_types: list[str] = []
    for item in evidence or []:
        evidence_id = str(uuid.uuid4())
        evidence_type = _normalize_token(item.type)
        if not evidence_type:
            continue
        evidence_ids.append(evidence_id)
        if evidence_type not in evidence_types:
            evidence_types.append(evidence_type)
        evidence_refs.append(
            {
                "id": evidence_id,
                "type": item.type,
                "ref": item.ref,
                "excerpt": item.excerpt,
                "meta_json": item.meta,
                "created_by_client_name": DEFAULT_CLIENT_NAME,
            }
        )
    return evidence_refs, evidence_ids, evidence_types


def _infer_provenance_class(
    *,
    card_kind: str,
    evidence_types: list[str],
    context: dict[str, Any] | None,
) -> str:
    existing = None
    if isinstance(context, dict):
        raw_provenance = context.get("provenance")
        if isinstance(raw_provenance, dict):
            existing = _normalize_token(raw_provenance.get("source_class"))
    if existing:
        return existing
    normalized_kind = _normalize_token(card_kind)
    evidence_type_set = {_normalize_token(item) for item in evidence_types if _normalize_token(item)}
    if normalized_kind in POLICY_KINDS or "preference" in normalized_kind:
        return "preference_or_instruction"
    if evidence_type_set & _TOOL_DERIVED_EVIDENCE_TYPES:
        return "tool_derived"
    if "chat" in evidence_type_set:
        return "user_provided"
    return "model_inference"


def _build_card_write_warnings(
    *,
    card_kind: str,
    evidence_types: list[str],
) -> list[dict[str, Any]]:
    normalized_kind = _normalize_token(card_kind)
    warnings: list[dict[str, Any]] = []
    if normalized_kind in _EVIDENCE_PREFERRED_KINDS and not evidence_types:
        warnings.append(
            {
                "code": "missing_evidence",
                "severity": "warning",
                "message": f"{normalized_kind} cards should include evidence for auditability.",
            }
        )
    return warnings


def _merge_card_context(
    *,
    context: dict[str, Any] | None,
    card_kind: str,
    evidence_types: list[str],
    warnings: list[dict[str, Any]],
    operation: str,
) -> dict[str, Any]:
    merged = dict(context or {})
    provenance = dict(merged.get("provenance") or {}) if isinstance(merged.get("provenance"), dict) else {}
    provenance.setdefault(
        "source_class",
        _infer_provenance_class(card_kind=card_kind, evidence_types=evidence_types, context=context),
    )
    provenance["evidence_count"] = len(evidence_types)
    provenance["evidence_types"] = sorted(dict.fromkeys(evidence_types))
    if warnings:
        provenance["warning_codes"] = [str(item["code"]) for item in warnings]
    merged["provenance"] = provenance
    muninn_meta = dict(merged.get("muninn") or {}) if isinstance(merged.get("muninn"), dict) else {}
    muninn_meta["write_operation"] = operation
    merged["muninn"] = muninn_meta
    return merged


def _atlas_context_from_card(card: CardInput) -> dict[str, Any] | None:
    if card.atlas is None:
        entity_type = _atlas_entity_type_from_kind(card.kind)
        if entity_type is None:
            return None
        return {"entity_type": entity_type}
    return {
        "entity_type": card.atlas.entity_type,
        "entity_id": card.atlas.entity_id,
        "owner_project": card.atlas.owner_project,
        "project": card.atlas.project,
        "capability": card.atlas.capability,
        "source": card.atlas.source,
        "target": card.atlas.target,
        "projects": list(card.atlas.projects or []),
        "capabilities": list(card.atlas.capabilities or []),
    }


def _merge_card_context_with_atlas(
    *,
    card: CardInput,
    context_json: dict[str, Any],
) -> dict[str, Any]:
    atlas_context = _atlas_context_from_card(card)
    if atlas_context is None:
        return context_json
    merged = dict(context_json)
    merged["atlas"] = atlas_context
    return merged


def _merge_tags_with_atlas(card: CardInput) -> list[str] | None:
    merged = _dedupe_string_list(card.tags)
    entity_type = _atlas_entity_type_from_kind(card.kind)
    if entity_type is None:
        return merged
    base = list(merged or [])
    base.extend(["atlas", f"atlas:{entity_type}"])
    if card.atlas is not None:
        base.append(f"atlas:id:{card.atlas.entity_id}")
    return _dedupe_string_list(base)


def _normalize_context_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(loaded, dict):
            return loaded
    return {}


def _atlas_value_matches(actual: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    return str(actual or "").strip() == expected


def _atlas_card_matches(card: dict[str, Any], query: AtlasQueryInput) -> bool:
    atlas_meta = card.get("atlas")
    if not isinstance(atlas_meta, dict):
        return False
    if not _atlas_value_matches(atlas_meta.get("entity_id"), query.entity_id):
        return False
    if not _atlas_value_matches(atlas_meta.get("owner_project"), query.owner_project):
        return False
    if not _atlas_value_matches(atlas_meta.get("project"), query.project):
        return False
    if not _atlas_value_matches(atlas_meta.get("capability"), query.capability):
        return False
    if not _atlas_value_matches(atlas_meta.get("source"), query.source):
        return False
    if not _atlas_value_matches(atlas_meta.get("target"), query.target):
        return False
    return True


def _normalize_atlas_result_row(row: dict[str, Any], *, include_body: bool) -> dict[str, Any]:
    context = _normalize_context_json(row.get("context_json"))
    atlas_meta = context.get("atlas") if isinstance(context.get("atlas"), dict) else {}
    normalized = {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "entity_type": str(atlas_meta.get("entity_type") or ""),
        "entity_id": atlas_meta.get("entity_id"),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "updated_at": _iso8601_utc(row.get("updated_at")),
        "tags": [str(v) for v in (row.get("tags") or [])],
        "atlas": atlas_meta,
        "score": _normalize_score(row.get("score")) if row.get("score") is not None else None,
    }
    if include_body:
        normalized["body"] = row.get("body")
    return normalized


def _space_log_context(
    conn: sqlite3.Connection | None,
    *,
    space_key: str | None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "client_name": DEFAULT_CLIENT_NAME,
        "db_target": str(_resolve_human_memory_db_path()),
        "db_name": _resolve_human_memory_db_path().name,
    }
    if conn is None or not space_key:
        return context
    summary = get_space_summary(conn, user_id=DEFAULT_USER_ID, space_key=space_key)
    meta = summary["meta"]
    context.update(
        {
            "space_key": summary["key"],
            "lookup_keys": summary["lookup_keys"],
            "project_label": summary["label"],
            "project_root": meta.get("root_path") or meta.get("cwd"),
            "project_identity": meta.get("identity"),
            "git_remote_norm": meta.get("git_remote_norm"),
        }
    )
    return context


def _build_space_resolution_details(
    lens: "LensInput",
    *,
    requested_cwd: str | None,
    requested_space_key: str | None,
    resolution_kind: str,
    canonical_space_key: str,
    alias_keys: list[str] | None = None,
    lookup_keys: list[str] | None = None,
) -> dict[str, Any]:
    normalized_aliases = [str(item) for item in (alias_keys or []) if str(item)]
    normalized_lookup = [str(item) for item in (lookup_keys or []) if str(item)]
    return {
        "requested_space": lens.space,
        "requested_space_key": requested_space_key,
        "requested_cwd": requested_cwd,
        "scope": lens.scope,
        "resolution_kind": resolution_kind,
        "canonical_space_key": canonical_space_key,
        "alias_keys": normalized_aliases,
        "lookup_keys": normalized_lookup,
        "alias_resolution_used": bool(
            requested_space_key
            and canonical_space_key
            and requested_space_key != canonical_space_key
        ),
        "alias_lookup_used": any(key not in {canonical_space_key, "global"} for key in normalized_lookup),
        "global_lookup_triggered": "global" in normalized_lookup and canonical_space_key != "global",
    }


def _summarize_zero_result_reason(
    *,
    results_count: int,
    lookup_details: dict[str, Any],
    operation: str,
) -> str | None:
    if results_count > 0:
        return None
    if operation == "cards.recent":
        if lookup_details.get("alias_lookup_used"):
            return "no_recent_cards_in_canonical_or_alias_scope"
        if lookup_details.get("global_lookup_triggered"):
            return "no_recent_cards_in_effective_scope"
        return "no_recent_cards_in_canonical_scope"
    if lookup_details.get("alias_lookup_used"):
        return "no_search_matches_in_canonical_or_alias_scope"
    if lookup_details.get("global_lookup_triggered"):
        return "no_search_matches_in_effective_scope"
    if lookup_details.get("alias_keys"):
        return "strict_scope_excluded_alias_lookup"
    return "no_search_matches_in_canonical_scope"


def _log_request_ingress(
    tool_name: str,
    *,
    request_id: str,
    invoked_as: str,
    lens: "LensInput | None" = None,
    cwd: str | None = None,
    query: str | None = None,
    signal_summary: str | None = None,
    session_id: str | None = None,
    input_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "operation": tool_name,
        "request_id": request_id,
        "invoked_as": invoked_as,
        "client_name": DEFAULT_CLIENT_NAME,
        "success": None,
    }
    if lens is not None:
        payload["lens"] = _summarize_lens_for_log(lens)
        payload["requested_space"] = lens.space
        payload["requested_space_key"] = lens.space_key
        payload["requested_scope"] = lens.scope
    if cwd:
        payload["requested_cwd"] = cwd
    if query:
        payload["query_summary"] = _summarize_query_for_log(query)
    if signal_summary:
        payload["signal_summary"] = _summarize_text(signal_summary, max_chars=96)
    if session_id:
        payload["session_id"] = session_id
    if input_type:
        payload["input_type"] = input_type
    if extra:
        payload.update(extra)
    _emit_runtime_event("request_ingress", **payload)


def _log_space_resolution(
    *,
    request_id: str,
    operation: str,
    conn: sqlite3.Connection | None,
    details: dict[str, Any],
) -> None:
    canonical_space_key = str(details.get("canonical_space_key") or "")
    merged_details = _space_log_context(conn, space_key=canonical_space_key or None)
    merged_details.update(details)
    _emit_runtime_event(
        "space_resolution",
        operation=operation,
        request_id=request_id,
        **merged_details,
    )


def _error_log_details(exc: Exception, err_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    details: dict[str, Any] = {
        "failure_class": type(exc).__name__,
        "error_text": _summarize_text(str(exc), max_chars=160),
    }
    err_details = ((err_payload.get("error") or {}).get("details")) if isinstance(err_payload, dict) else None
    if isinstance(err_details, dict):
        error_message = err_details.get("error")
        if error_message is not None:
            details["error_detail"] = _summarize_text(str(error_message), max_chars=160)
        if "db_reason" in err_details:
            details["db_reason"] = err_details.get("db_reason")
        if "field" in err_details:
            details["field"] = err_details.get("field")
    return details


def _validate_exposure_guard(host: str) -> None:
    if _is_loopback_host(host):
        return
    if not _resolve_mcp_requires_api_key() or not _has_mcp_auth_secret():
        raise RuntimeError(
            "Refusing non-loopback MCP bind without auth. "
            "Set MUNINN_MCP_BEARER_TOKEN or MUNINN_API_KEY and enable MUNINN_MCP_REQUIRE_API_KEY=1."
        )


def _print_connect_urls(host: str, port: int) -> None:
    if _is_loopback_host(host):
        print(f"  MCP URL: {_format_http_url('127.0.0.1', port, '/mcp')}")
        normalized = _normalize_host(host)
        if normalized in {"::1"}:
            print(f"  MCP URL (IPv6): {_format_http_url('::1', port, '/mcp')}")
        return

    if _is_wildcard_host(host):
        print(f"  MCP URL (loopback): {_format_http_url('127.0.0.1', port, '/mcp')}")
        for lan_ip in _list_interface_ipv4s():
            print(f"  MCP URL (LAN): {_format_http_url(lan_ip, port, '/mcp')}")
        return

    print(f"  MCP URL: {_format_http_url(host, port, '/mcp')}")


def _resolve_human_memory_db_path() -> Path:
    configured = os.getenv("MUNINN_HUMAN_MEMORY_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path("~/.local/share/muninn/human_memory.db").expanduser().resolve()


class LensInput(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    space: Literal["auto", "global"] = Field(
        default="auto",
        description="Use 'auto' or 'global'. For explicit keys, pass space_key.",
    )
    space_key: str | None = Field(
        default=None,
        description="Explicit space key, e.g. repo:..., path:..., cwd:..., global.",
    )
    cwd: str | None = Field(
        default=None,
        description="Current working directory. Required when space='auto'.",
    )
    scope: Literal["strict", "soft"] = Field(
        default="strict",
        description="strict=resolved space only, soft=resolved space then global fallback.",
    )
    kinds: list[str] | None = None
    status: Literal["active", "superseded", "archived"] = "active"
    tags: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_shapes(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = _parse_legacy_kv_text(value)
        if not isinstance(value, dict):
            return value
        if "lens" in value and isinstance(value.get("lens"), dict):
            value = dict(value["lens"])
        else:
            value = dict(value)
        if "kind" in value and "kinds" not in value:
            value["kinds"] = value.pop("kind")
        return value

    @field_validator("limit", mode="before")
    @classmethod
    def _coerce_limit(cls, value: Any) -> Any:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("invalid_limit:empty")
            return int(text)
        return value

    @field_validator("space_key", "cwd", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("cwd")
    @classmethod
    def _validate_auto_space_cwd(
        cls,
        value: str | None,
        info: Any,
    ) -> str | None:
        space = str(info.data.get("space") or "auto")
        space_key = str(info.data.get("space_key") or "").strip()
        if space == "auto" and not space_key and not value:
            raise PydanticCustomError(
                "missing_auto_space_cwd",
                "lens.cwd is required when lens.space='auto'.",
            )
        return value

    @field_validator("kinds", "tags")
    @classmethod
    def _normalize_string_filters(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = str(raw).strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized or None

    @field_validator("kinds", "tags", mode="before")
    @classmethod
    def _coerce_string_filters_before(cls, value: Any, info: Any) -> Any:
        return _coerce_string_list(value, field_name=str(info.field_name))


class SearchQueryInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str | None = None
    q: str | None = None
    query: str | None = None
    terms: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_shape(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"text": value}
        if isinstance(value, list):
            return {"terms": value}
        if not isinstance(value, dict):
            return value
        return dict(value)

    @field_validator("terms", mode="before")
    @classmethod
    def _coerce_terms(cls, value: Any) -> Any:
        return _coerce_string_list(value, field_name="query_terms")

    def resolved_text(self) -> str:
        for candidate in (self.text, self.q, self.query):
            text = str(candidate or "").strip()
            if text:
                return text
        if self.terms:
            joined = " ".join(str(term).strip() for term in self.terms if str(term).strip())
            if joined:
                return joined
        raise ValueError("invalid_query:expected text, q, query, or terms")


class PolicySignalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        min_length=1,
        description="Observed correction, failure, or directive to learn from.",
    )
    signal_type: str = Field(
        default="directive",
        description=f"Signal class. Allowed: {', '.join(SIGNAL_TYPES)}.",
    )
    outcome: str = Field(
        default="corrected",
        description=f"Observed outcome. Allowed: {', '.join(OUTCOME_TYPES)}.",
    )
    scope_type: str = Field(
        default="project",
        description="Scope type, e.g. global | user | project | repo | task-type | tool.",
    )
    scope_key: str | None = None
    lesson: str | None = None
    preferred_behavior: str | None = None
    anti_pattern: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tool_name: str | None = None
    task_type: str | None = None
    session_id: str | None = None
    tags: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_shape(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"summary": value}
        return value

    @field_validator("signal_type")
    @classmethod
    def _validate_signal_type(cls, value: str) -> str:
        normalized = _normalize_token(value or "directive")
        if normalized not in set(SIGNAL_TYPES):
            allowed = ", ".join(SIGNAL_TYPES)
            raise ValueError(f"invalid_signal_type:{normalized}:allowed={allowed}")
        return normalized

    @field_validator("outcome")
    @classmethod
    def _validate_outcome(cls, value: str) -> str:
        normalized = _normalize_token(value or "corrected")
        if normalized not in set(OUTCOME_TYPES):
            allowed = ", ".join(OUTCOME_TYPES)
            raise ValueError(f"invalid_outcome:{normalized}:allowed={allowed}")
        return normalized

    @field_validator(
        "scope_type",
        "scope_key",
        "lesson",
        "preferred_behavior",
        "anti_pattern",
        "tool_name",
        "task_type",
        "session_id",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = " ".join(str(value).strip().split())
        return text or None

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> Any:
        return _coerce_string_list(value, field_name="policy_tags")

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = _normalize_token(raw)
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized or None


class PolicyInspectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    scope_types: list[str] | None = None
    scope_key: str | None = None
    tool_name: str | None = None
    task_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)
    include_body: bool = False
    include_events: bool = True
    event_limit: int = Field(default=10, ge=0, le=50)
    session_id: str | None = None

    @field_validator("scope_types", mode="before")
    @classmethod
    def _coerce_scope_types(cls, value: Any) -> Any:
        return _coerce_string_list(value, field_name="policy_scope_types")

    @field_validator(
        "query",
        "scope_key",
        "tool_name",
        "task_type",
        "session_id",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = " ".join(str(value).strip().split())
        return text or None

    @field_validator("scope_types")
    @classmethod
    def _normalize_scope_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = _normalize_token(raw)
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized or None


class AdaptationQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str = Field(
        min_length=1,
        description="Subject/client id to scope adaptation retrieval.",
    )
    view: str = Field(
        default="all",
        description=(
            "Preset retrieval view: all | durable_preferences | recent_overrides | "
            "corrections | outcomes | prompt_state."
        ),
    )
    categories: list[str] | None = None
    memory_types: list[str] | None = Field(
        default=None,
        description=f"Optional override. Allowed: {', '.join(ADAPTATION_MEMORY_TYPES)}.",
    )
    persistence: list[str] | None = Field(
        default=None,
        description=f"Optional override. Allowed: {', '.join(ADAPTATION_PERSISTENCE_VALUES)}.",
    )
    scope_types: list[str] | None = None
    scope_id: str | None = None
    source_types: list[str] | None = None
    session_id: str | None = None
    tags: list[str] | None = None
    max_age_days: int | None = Field(default=None, ge=1, le=3650)
    status: Literal["active", "superseded", "archived"] = "active"
    limit: int = Field(default=20, ge=1, le=100)
    include_body: bool = False

    @field_validator("view")
    @classmethod
    def _validate_view(cls, value: str) -> str:
        normalized = str(value or "").strip().lower() or "all"
        if normalized not in set(ADAPTATION_VIEWS):
            allowed = ", ".join(ADAPTATION_VIEWS)
            raise ValueError(f"invalid_adaptation_view:{normalized}:allowed={allowed}")
        return normalized

    @field_validator(
        "subject_id",
        "scope_id",
        "session_id",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator(
        "categories",
        "memory_types",
        "persistence",
        "scope_types",
        "source_types",
        "tags",
    )
    @classmethod
    def _normalize_list_fields(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = str(raw).strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized or None


class AtlasCardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: Literal["project", "capability", "relationship", "risk", "active_direction"]
    entity_id: str = Field(min_length=1)
    owner_project: str | None = None
    project: str | None = None
    capability: str | None = None
    source: str | None = None
    target: str | None = None
    projects: list[str] | None = None
    capabilities: list[str] | None = None

    @field_validator(
        "entity_id",
        "owner_project",
        "project",
        "capability",
        "source",
        "target",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("projects", "capabilities", mode="before")
    @classmethod
    def _coerce_list_fields(cls, value: Any) -> Any:
        return _coerce_string_list(value, field_name="atlas_refs")

    @field_validator("projects", "capabilities")
    @classmethod
    def _normalize_list_fields(cls, value: list[str] | None) -> list[str] | None:
        return _dedupe_string_list(value)


class CardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        default=None,
        description="If provided, update this card id; otherwise create a new card.",
    )
    kind: str
    status: Literal["active", "superseded", "archived"] = "active"
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    title: str = Field(min_length=1)
    summary: str = Field(
        min_length=1,
        description="Prompt-friendly summary. Keep this to 1-3 sentences.",
    )
    body: str = Field(
        min_length=1,
        description="Full durable memory body. Include details needed for later reuse.",
    )
    tags: list[str] | None = None
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional provenance context (files, commits, tests).",
    )
    atlas: AtlasCardInput | None = Field(
        default=None,
        description="Optional first-class atlas metadata for atlas.* cards.",
    )

    @model_validator(mode="after")
    def _validate_atlas_alignment(self) -> "CardInput":
        kind_entity_type = _atlas_entity_type_from_kind(self.kind)
        if kind_entity_type is None:
            if self.atlas is not None:
                raise ValueError("atlas metadata requires kind=atlas.<entity_type>")
            return self
        if self.atlas is None:
            return self
        if self.atlas.entity_type != kind_entity_type:
            raise ValueError(
                f"atlas entity_type '{self.atlas.entity_type}' does not match kind '{self.kind}'"
            )
        return self


class AtlasQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    entity_types: list[Literal["project", "capability", "relationship", "risk", "active_direction"]] | None = None
    entity_id: str | None = None
    owner_project: str | None = None
    project: str | None = None
    capability: str | None = None
    source: str | None = None
    target: str | None = None
    include_body: bool = False
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator(
        "query",
        "entity_id",
        "owner_project",
        "project",
        "capability",
        "source",
        "target",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        text = " ".join(str(value).strip().split())
        return text or None

    @field_validator("entity_types", mode="before")
    @classmethod
    def _coerce_entity_types(cls, value: Any) -> Any:
        return _coerce_string_list(value, field_name="atlas_entity_types")

    @field_validator("entity_types")
    @classmethod
    def _normalize_entity_types(
        cls, value: list[str] | None
    ) -> list[Literal["project", "capability", "relationship", "risk", "active_direction"]] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = _normalize_token(raw).replace(" ", "_")
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized or None


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["chat", "log", "diff", "file", "url", "commit", "test"]
    ref: str | None = None
    excerpt: str | None = None
    meta: dict[str, Any] | None = None


class ToolCallError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@contextmanager
def _human_memory_conn(*, correlation_id: str | None = None) -> sqlite3.Connection:
    db_path = _resolve_human_memory_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = open_db(str(db_path))
    try:
        apply_init_schema(conn, correlation_id=correlation_id)
        bootstrap_defaults(conn, correlation_id=correlation_id)
        yield conn
    finally:
        conn.close()


def _tool_error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def _handle_tool_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, ToolCallError):
        return _tool_error(exc.code, exc.message, exc.details)
    if isinstance(exc, ValidationError):
        details: dict[str, Any] = {"error": "validation_failed"}
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = [str(part) for part in (first.get("loc") or []) if str(part) != "__root__"]
            field = ".".join(loc)
            if field:
                details["field"] = field
            message = str(first.get("msg") or "invalid value")
            details["error"] = f"{field}: {message}" if field else message
            details["validation_errors"] = [
                {
                    "field": ".".join(
                        str(part) for part in (item.get("loc") or []) if str(part) != "__root__"
                    ),
                    "message": str(item.get("msg") or "invalid value"),
                }
                for item in errors[:3]
            ]
        return _tool_error(
            "InvalidArguments",
            "Tool arguments are invalid.",
            details,
        )
    if isinstance(exc, ValueError):
        message = str(exc)
        details: dict[str, Any] = {"error": message}
        if message.startswith("invalid_"):
            field = message.split(":", 1)[0].removeprefix("invalid_")
            if field:
                details["field"] = field
        return _tool_error(
            "InvalidArguments",
            "Tool arguments are invalid.",
            details,
        )
    if isinstance(exc, sqlite3.IntegrityError):
        return _tool_error(
            "ConstraintViolation",
            "A database constraint failed.",
            {"error": str(exc)},
        )
    if isinstance(exc, sqlite3.Error):
        raw_error = str(exc)
        lowered = raw_error.lower()
        db_reason = "sqlite_error"
        if "locked" in lowered or "busy" in lowered:
            db_reason = "locked"
        elif "no such column" in lowered or "no such table" in lowered:
            db_reason = "schema_mismatch"
        return _tool_error(
            "DatabaseUnavailable",
            "The database could not be reached or queried.",
            {"error": raw_error, "db_reason": db_reason},
        )
    return _tool_error(
        "InternalError",
        "An unexpected error occurred while executing the tool.",
        {"error": str(exc)},
    )


def _iso8601_utc(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        if text.endswith("Z") or "+" in text:
            return text
        return f"{text}Z"
    if " " in text:
        return f"{text.replace(' ', 'T')}Z"
    return text


def _resolve_primary_space_with_details(
    conn: sqlite3.Connection,
    lens: LensInput,
) -> tuple[str, dict[str, Any]]:
    explicit_key = (lens.space_key or "").strip()
    if explicit_key:
        get_or_create_space(
            conn,
            user_id=DEFAULT_USER_ID,
            resolved=ResolvedSpace(
                key=explicit_key,
                label=explicit_key,
                meta_json='{"source":"explicit_space_key"}',
                ),
        )
        canonical_key = canonicalize_space_key(conn, user_id=DEFAULT_USER_ID, space_key=explicit_key)
        details = _build_space_resolution_details(
            lens,
            requested_cwd=lens.cwd,
            requested_space_key=explicit_key,
            resolution_kind="explicit_space_key",
            canonical_space_key=canonical_key,
            alias_keys=[],
            lookup_keys=[canonical_key],
        )
        return canonical_key, details

    if lens.space == "global":
        details = _build_space_resolution_details(
            lens,
            requested_cwd=lens.cwd,
            requested_space_key="global",
            resolution_kind="global_space",
            canonical_space_key="global",
            alias_keys=[],
            lookup_keys=["global"],
        )
        return "global", details

    if not lens.cwd:
        raise ToolCallError(
            "InvalidArguments",
            "lens.cwd is required when lens.space='auto'.",
            {"field": "lens.cwd"},
        )

    try:
        resolved = resolve_space_from_cwd(lens.cwd)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise ToolCallError(
            "SpaceResolutionFailed",
            "Failed to resolve space from cwd.",
            {"cwd": lens.cwd, "error": str(exc)},
        ) from exc

    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    canonical_key = canonicalize_space_key(conn, user_id=DEFAULT_USER_ID, space_key=resolved.key)
    details = _build_space_resolution_details(
        lens,
        requested_cwd=lens.cwd,
        requested_space_key=resolved.key,
        resolution_kind="cwd_auto",
        canonical_space_key=canonical_key,
        alias_keys=list(resolved.alias_keys),
        lookup_keys=[canonical_key],
    )
    return canonical_key, details


def _resolve_primary_space(conn: sqlite3.Connection, lens: LensInput) -> str:
    primary, _ = _resolve_primary_space_with_details(conn, lens)
    return primary


def _scope_space_keys_with_details(
    conn: sqlite3.Connection,
    lens: LensInput,
) -> tuple[list[str], dict[str, Any]]:
    primary, details = _resolve_primary_space_with_details(conn, lens)
    if primary == "global":
        details["lookup_keys"] = ["global"]
        return ["global"], details
    if lens.scope == "soft":
        lookup_keys = resolve_space_lookup_keys(conn, user_id=DEFAULT_USER_ID, space_key=primary)
        if "global" not in lookup_keys:
            lookup_keys.append("global")
        details.update(
            _build_space_resolution_details(
                lens,
                requested_cwd=lens.cwd,
                requested_space_key=details.get("requested_space_key"),
                resolution_kind=str(details.get("resolution_kind") or "cwd_auto"),
                canonical_space_key=primary,
                alias_keys=[key for key in lookup_keys if key not in {primary, "global"}],
                lookup_keys=lookup_keys,
            )
        )
        return lookup_keys, details
    strict_lookup = [primary]
    details.update(
        _build_space_resolution_details(
            lens,
            requested_cwd=lens.cwd,
            requested_space_key=details.get("requested_space_key"),
            resolution_kind=str(details.get("resolution_kind") or "cwd_auto"),
            canonical_space_key=primary,
            alias_keys=resolve_space_lookup_keys(conn, user_id=DEFAULT_USER_ID, space_key=primary)[1:],
            lookup_keys=strict_lookup,
        )
    )
    return strict_lookup, details


def _scope_space_keys(conn: sqlite3.Connection, lens: LensInput) -> list[str]:
    lookup_keys, _ = _scope_space_keys_with_details(conn, lens)
    return lookup_keys


def _normalize_card_recent_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "status": str(row.get("status", "")),
        "salience": float(row.get("salience", 0.0) or 0.0),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "updated_at": _iso8601_utc(row.get("updated_at")),
        "tags": [str(v) for v in (row.get("tags") or [])],
        "evidence_count": int(row.get("evidence_count") or 0),
        "has_evidence": bool(row.get("has_evidence")),
    }


def _normalize_adaptation_card_row(row: dict[str, Any]) -> dict[str, Any]:
    adaptation = row.get("adaptation") or {}
    scope = adaptation.get("scope") if isinstance(adaptation, dict) else {}
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "status": str(row.get("status", "")),
        "salience": float(row.get("salience", 0.0) or 0.0),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "updated_at": _iso8601_utc(row.get("updated_at")),
        "created_at": _iso8601_utc(row.get("created_at")),
        "tags": [str(v) for v in (row.get("tags") or [])],
        "body": row.get("body"),
        "created_by_client_name": row.get("created_by_client_name"),
        "adaptation": {
            "memory_type": adaptation.get("memory_type"),
            "subject_id": adaptation.get("subject_id"),
            "category": adaptation.get("category"),
            "scope": {
                "type": scope.get("type") if isinstance(scope, dict) else None,
                "id": scope.get("id") if isinstance(scope, dict) else None,
            },
            "persistence": adaptation.get("persistence"),
            "source_type": adaptation.get("source_type"),
            "confidence": adaptation.get("confidence"),
            "session_id": adaptation.get("session_id"),
            "workflow_tags": adaptation.get("workflow_tags") or [],
            "provenance": adaptation.get("provenance"),
        },
    }


def _normalize_policy_card_row(row: dict[str, Any]) -> dict[str, Any]:
    policy = row.get("policy") or {}
    scope = policy.get("scope") if isinstance(policy, dict) else {}
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "body": row.get("body"),
        "updated_at": _iso8601_utc(row.get("updated_at")),
        "created_at": _iso8601_utc(row.get("created_at")),
        "tags": [str(v) for v in (row.get("tags") or [])],
        "evidence_count": int(row.get("evidence_count") or 0),
        "has_evidence": bool(row.get("has_evidence")),
        "score": float(row.get("score") or 0.0),
        "policy": {
            "signal_type": policy.get("signal_type"),
            "outcome": policy.get("outcome"),
            "scope": {
                "type": scope.get("type") if isinstance(scope, dict) else None,
                "key": scope.get("key") if isinstance(scope, dict) else None,
            },
            "lesson": policy.get("lesson"),
            "preferred_behavior": policy.get("preferred_behavior"),
            "anti_pattern": policy.get("anti_pattern"),
            "confidence": policy.get("confidence"),
            "repetition_count": policy.get("repetition_count"),
            "tool_name": policy.get("tool_name"),
            "task_type": policy.get("task_type"),
            "signal_key": policy.get("signal_key"),
            "source_interaction_id": policy.get("source_interaction_id"),
            "supersedes_card_id": policy.get("supersedes_card_id"),
        },
    }


def _normalize_interaction_event_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "session_id": row.get("session_id"),
        "event_type": str(row.get("event_type", "")),
        "actor": str(row.get("actor", "")),
        "signal_type": row.get("signal_type"),
        "outcome_type": row.get("outcome_type"),
        "scope_type": row.get("scope_type"),
        "scope_key": row.get("scope_key"),
        "signal_key": row.get("signal_key"),
        "summary": str(row.get("summary", "")),
        "payload": row.get("payload"),
        "promoted_card_id": row.get("promoted_card_id"),
        "created_at": _iso8601_utc(row.get("created_at")),
        "created_by_client_name": row.get("created_by_client_name"),
    }


def _normalize_score(raw_score: Any) -> float:
    try:
        value = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    return round(1.0 / (1.0 + abs(value)), 6)


def _collect_recent_cards(
    conn: sqlite3.Connection,
    lens: LensInput,
    scoped_space_keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    remaining = lens.limit
    space_keys = scoped_space_keys or _scope_space_keys(conn, lens)
    for space_key in space_keys:
        if remaining <= 0:
            break
        rows = cards_recent(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            kinds=lens.kinds,
            status=lens.status,
            tags=lens.tags,
            limit=remaining,
        )
        for row in rows:
            card_id = str(row.get("id", ""))
            if not card_id or card_id in seen:
                continue
            cards.append(_normalize_card_recent_row(row))
            seen.add(card_id)
            remaining -= 1
            if remaining <= 0:
                break
    return cards


def _collect_search_results(
    conn: sqlite3.Connection,
    query: str,
    lens: LensInput,
    scoped_space_keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    remaining = lens.limit
    space_keys = scoped_space_keys or _scope_space_keys(conn, lens)
    for space_key in space_keys:
        if remaining <= 0:
            break
        rows = cards_search(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            query=query,
            kinds=lens.kinds,
            status=lens.status,
            tags=lens.tags,
            limit=remaining,
        )
        for row in rows:
            card_id = str(row.get("id", ""))
            if not card_id or card_id in seen:
                continue
            results.append(
                {
                    "card": {
                        "id": card_id,
                        "space_key": str(row.get("space_key", "")),
                        "kind": str(row.get("kind", "")),
                        "title": str(row.get("title", "")),
                        "summary": str(row.get("summary", "")),
                        "updated_at": _iso8601_utc(row.get("updated_at")),
                        "tags": [str(v) for v in (row.get("tags") or [])],
                        "evidence_count": int(row.get("evidence_count") or 0),
                        "has_evidence": bool(row.get("has_evidence")),
                    },
                    "score": _normalize_score(row.get("score")),
                }
            )
            seen.add(card_id)
            remaining -= 1
            if remaining <= 0:
                break
    return results


def _collect_adaptation_cards(
    conn: sqlite3.Connection,
    lens: LensInput,
    query: AdaptationQueryInput,
    scoped_space_keys: list[str] | None = None,
) -> dict[str, Any]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    remaining = query.limit
    space_keys = scoped_space_keys or _scope_space_keys(conn, lens)
    last_filters: dict[str, Any] | None = None

    for space_key in space_keys:
        if remaining <= 0:
            break
        payload = query_adaptation_cards(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            subject_id=query.subject_id,
            view=query.view,
            categories=query.categories,
            memory_types=query.memory_types,
            persistence=query.persistence,
            scope_types=query.scope_types,
            scope_id=query.scope_id,
            source_types=query.source_types,
            session_id=query.session_id,
            tags=query.tags,
            max_age_days=query.max_age_days,
            status=query.status,
            limit=remaining,
            include_body=query.include_body,
        )
        if last_filters is None and isinstance(payload.get("filters"), dict):
            last_filters = dict(payload["filters"])

        for row in payload.get("cards", []):
            card_id = str(row.get("id", ""))
            if not card_id or card_id in seen:
                continue
            normalized = _normalize_adaptation_card_row(row)
            if not query.include_body:
                normalized.pop("body", None)
            cards.append(normalized)
            seen.add(card_id)
            remaining -= 1
            if remaining <= 0:
                break

    by_memory_type = {memory_type: 0 for memory_type in ADAPTATION_MEMORY_TYPES}
    by_persistence = {key: 0 for key in ADAPTATION_PERSISTENCE_VALUES}
    for card in cards:
        adaptation = card.get("adaptation") or {}
        memory_type = str(adaptation.get("memory_type") or "")
        persistence = str(adaptation.get("persistence") or "")
        if memory_type in by_memory_type:
            by_memory_type[memory_type] += 1
        if persistence in by_persistence:
            by_persistence[persistence] += 1

    prompt_source_cards = [
        {
            "id": card.get("id"),
            "summary": card.get("summary"),
            "updated_at": card.get("updated_at"),
            "tags": card.get("tags", []),
            "adaptation": card.get("adaptation"),
        }
        for card in cards
    ]

    return {
        "cards": cards,
        "counts": {
            "total": len(cards),
            "by_memory_type": by_memory_type,
            "by_persistence": by_persistence,
        },
        "filters": last_filters or {},
        "prompt_state": build_prompt_state_summary(prompt_source_cards),
    }


def _normalize_rehydration_card_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "status": str(row.get("status", "")),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "body": row.get("body"),
        "updated_at": _iso8601_utc(row.get("updated_at")),
        "tags": [str(v) for v in (row.get("tags") or [])],
        "evidence_count": int(row.get("evidence_count") or 0),
        "has_evidence": bool(row.get("has_evidence")),
        "score": float(row.get("score") or 0.0),
        "stage": str(row.get("stage", "")),
    }


def _normalize_rehydration_payload(payload: dict[str, Any]) -> dict[str, Any]:
    project_cards = [_normalize_rehydration_card_row(row) for row in payload.get("project_cards", [])]
    policy_cards = [_normalize_policy_card_row(row) for row in payload.get("policy_cards", [])]
    bundle = payload.get("bundle") or {}
    bundle_keys = ("facts", "constraints", "evidence", "lessons", "preferences")
    normalized_bundle = {
        key: [
            _normalize_policy_card_row(row) if key in {"lessons", "preferences"} else _normalize_rehydration_card_row(row)
            for row in bundle.get(key, [])
        ]
        for key in bundle_keys
    }
    stage_reports = []
    for row in payload.get("stages", []):
        stage_reports.append(
            {
                "stage": str(row.get("stage", "")),
                "space_key": str(row.get("space_key", "")),
                "space_keys": [str(item) for item in (row.get("space_keys") or [])],
                "results": int(row.get("results") or 0),
                "attempted": bool(row.get("attempted")),
                "skipped": bool(row.get("skipped")),
                "skip_reason": row.get("skip_reason"),
                "zero_reason": row.get("zero_reason"),
                "per_space_results": list(row.get("per_space_results") or []),
            }
        )
    space = payload.get("space") or {}
    summary = payload.get("summary") or {}
    policy_diagnostics = payload.get("policy_diagnostics") or {}
    return {
        "space": {
            "canonical_key": str(space.get("canonical_key", "")),
            "lookup_keys": [str(item) for item in (space.get("lookup_keys") or [])],
            "scope": str(space.get("scope", "")),
        },
        "query": str(payload.get("query", "")),
        "stages": stage_reports,
        "project_cards": project_cards,
        "policy_cards": policy_cards,
        "policy_diagnostics": {
            "scanned_rows": int(policy_diagnostics.get("scanned_rows") or 0),
            "invalid_policy_rows": int(policy_diagnostics.get("invalid_policy_rows") or 0),
            "invalid_reasons": dict(policy_diagnostics.get("invalid_reasons") or {}),
        },
        "summary": {
            "project_cards": int(summary.get("project_cards") or 0),
            "policy_cards": int(summary.get("policy_cards") or 0),
            "rehydration_empty": bool(summary.get("rehydration_empty")),
        },
        "bundle": normalized_bundle,
    }


def _count_recent_card_creates(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    client_name: str,
    window_seconds: int,
) -> int:
    interval = f"-{max(1, int(window_seconds))} seconds"
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        LEFT JOIN clients cl ON cl.id = c.created_by_client_id
        WHERE c.user_id = ?
          AND s.key = ?
          AND cl.name = ?
          AND c.created_at >= datetime('now', ?)
        """,
        (user_id, space_key, client_name, interval),
    ).fetchone()
    if row is None:
        return 0
    return int(row["n"] or 0)


class McpApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if _resolve_mcp_requires_api_key() and request.url.path.startswith("/mcp"):
            configured_api_key = _resolve_mcp_api_key()
            configured_bearer = _resolve_mcp_bearer_token()
            header_name = _resolve_mcp_api_key_header()
            provided_api_key = request.headers.get(header_name)
            authorization = request.headers.get("authorization") or ""
            provided_bearer = None
            if authorization.lower().startswith("bearer "):
                provided_bearer = authorization[7:].strip()

            if provided_bearer is not None:
                # Bearer token takes precedence if both headers are present.
                bearer_ok = bool(
                    configured_bearer
                    and hmac.compare_digest(provided_bearer, configured_bearer)
                )
                if not bearer_ok:
                    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
                return await call_next(request)

            api_key_ok = bool(
                configured_api_key
                and provided_api_key
                and hmac.compare_digest(provided_api_key, configured_api_key)
            )
            if not api_key_ok:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)


async def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_resolve_base_url()}{path}"
    async with httpx.AsyncClient(headers=_resolve_headers(), timeout=30.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code >= 400:
        raise ValueError(f"Muninn API error [{response.status_code}] {path}: {response.text}")

    if not response.content:
        return {}
    return response.json()


def create_mcp_server(host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    mcp = FastMCP(
        name="muninn-mcp",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )

    @mcp.tool(name="muninn_rehydrate", description="Forward to /v0/memory/rehydrate")
    async def muninn_rehydrate(
        namespace: str,
        query: str,
        entity_id: str | None = None,
        k: int = 8,
        profile: str = "generic",
        embedding_model: str | None = None,
        query_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        req = RehydrateRequest(
            namespace=namespace,
            query=query,
            entity_id=entity_id,
            k=k,
            profile=profile,
            embedding_model=embedding_model,
            query_embedding=query_embedding,
        )
        return await _post_json("/v0/memory/rehydrate", req.model_dump())

    @mcp.tool(
        name="muninn_stage_candidates",
        description="Forward to /v0/memory/stage_candidates",
    )
    async def muninn_stage_candidates(
        namespace: str,
        candidates: list[dict[str, Any]],
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        req = StageCandidatesRequest(
            namespace=namespace,
            candidates=candidates,
            ttl_seconds=ttl_seconds,
        )
        return await _post_json("/v0/memory/stage_candidates", req.model_dump())

    @mcp.tool(name="muninn_list_pending", description="Forward to /v0/memory/list_pending")
    async def muninn_list_pending(
        namespace: str,
        entity_id: str | None = None,
        status: str = "pending",
        limit: int = 50,
    ) -> dict[str, Any]:
        req = ListPendingRequest(
            namespace=namespace,
            entity_id=entity_id,
            status=status,
            limit=limit,
        )
        return await _post_json("/v0/memory/list_pending", req.model_dump())

    @mcp.tool(
        name="muninn_confirm_candidates",
        description="Forward to /v0/memory/confirm_candidates",
    )
    async def muninn_confirm_candidates(
        namespace: str,
        pending_ids: list[str],
        decision: str,
        decided_by: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        req = ConfirmCandidatesRequest(
            namespace=namespace,
            pending_ids=pending_ids,
            decision=decision,
            decided_by=decided_by,
            note=note,
        )
        return await _post_json("/v0/memory/confirm_candidates", req.model_dump())

    async def _handle_system_ping(invoked_as: str) -> dict[str, Any]:
        canonical = "muninn.system.ping"
        started = time.perf_counter()
        request_id = _new_request_id()
        db_path = _resolve_human_memory_db_path()
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            input_type="ping",
        )
        payload = {
            "ok": True,
            "version": __version__,
            "db_path": str(db_path),
            "auth": _mcp_auth_state(),
            "auth_mode": _mcp_auth_mode(),
        }
        log_payload: dict[str, Any] = {
            "status": "ok",
            "request_id": request_id,
            "auth": payload["auth"],
            "auth_mode": payload["auth_mode"],
            "client_name": DEFAULT_CLIENT_NAME,
            "db_target": str(db_path),
            "db_name": db_path.name,
            "duration_ms": _elapsed_ms(started),
        }
        if invoked_as != canonical:
            log_payload["invoked_as"] = invoked_as
            log_payload["deprecated_alias"] = True
        _log_tool_invocation(canonical, **log_payload)
        return payload

    async def _handle_spaces_resolve(cwd: str, invoked_as: str) -> dict[str, Any]:
        canonical = "muninn.spaces.resolve"
        started = time.perf_counter()
        request_id = _new_request_id()
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            cwd=cwd,
            input_type="cwd_text",
        )
        try:
            resolved_cwd = cwd.strip()
            if not resolved_cwd:
                raise ToolCallError(
                    "InvalidArguments",
                    "cwd is required.",
                    {"field": "cwd"},
                )
            resolved = resolve_space_from_cwd(resolved_cwd)
            with _human_memory_conn(correlation_id=request_id) as conn:
                get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
                summary = get_space_summary(conn, user_id=DEFAULT_USER_ID, space_key=resolved.key)
                space_details = {
                    "requested_space": "auto",
                    "requested_space_key": None,
                    "requested_cwd": resolved_cwd,
                    "scope": "strict",
                    "resolution_kind": "cwd_auto",
                    "canonical_space_key": summary["key"],
                    "alias_keys": [key for key in summary["lookup_keys"] if key != summary["key"]],
                    "lookup_keys": summary["lookup_keys"],
                    "alias_resolution_used": bool(
                        [key for key in summary["lookup_keys"] if key != summary["key"]]
                    ),
                    "alias_lookup_used": False,
                    "global_lookup_triggered": False,
                }
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=space_details,
                )
                space_context = _space_log_context(conn, space_key=summary["key"])
            payload = {
                "space": {
                    "key": summary["key"],
                    "label": summary["label"],
                    "meta": summary["meta"],
                    "lookup_keys": summary["lookup_keys"],
                }
            }
            log_payload: dict[str, Any] = {
                "status": "ok",
                "request_id": request_id,
                "space_key": summary["key"],
                "lookup_keys": summary["lookup_keys"],
                "cwd": resolved_cwd,
                **space_details,
                **space_context,
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "error_code": error_code,
                "cwd": cwd,
                "client_name": DEFAULT_CLIENT_NAME,
                "db_target": str(_resolve_human_memory_db_path()),
                "db_name": _resolve_human_memory_db_path().name,
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_recent(lens: LensInput, invoked_as: str) -> dict[str, Any]:
        canonical = "muninn.cards.recent"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            input_type="lens_only",
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                cards = _collect_recent_cards(conn, lens, scoped_space_keys=scoped)
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_keys": scoped,
                    "cards": len(cards),
                    "result_count": len(cards),
                    "zero_result_reason": _summarize_zero_result_reason(
                        results_count=len(cards),
                        lookup_details=scope_details,
                        operation="cards.recent",
                    ),
                    "lens": _summarize_lens_for_log(lens),
                    **scope_details,
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return {"cards": cards}
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_search(query: Any, lens: LensInput, invoked_as: str) -> dict[str, Any]:
        canonical = "muninn.cards.search"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        q: str | None = None
        scope_details: dict[str, Any] | None = None
        try:
            _log_request_ingress(
                canonical,
                request_id=request_id,
                invoked_as=invoked_as,
                lens=lens,
                input_type=_query_input_type(query),
                extra={"query_summary": _summarize_query_input(query)},
            )
            q = _resolve_query_text(query).strip()
            if not q:
                raise ToolCallError(
                    "InvalidArguments",
                    "query must be non-empty.",
                    {"field": "query"},
                )
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                total_matches = 0
                for key in scoped:
                    total_matches += cards_search_count(
                        conn,
                        user_id=DEFAULT_USER_ID,
                        space_key=key,
                        query=q,
                        kinds=lens.kinds,
                        status=lens.status,
                        tags=lens.tags,
                    )
                results = _collect_search_results(conn, q, lens, scoped_space_keys=scoped)
                top_score = float(results[0]["score"]) if results else None
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_keys": scoped,
                    "query": _summarize_text(q, max_chars=96),
                    "query_summary": _summarize_query_for_log(q),
                    "results": len(results),
                    "result_count": len(results),
                    "total_matches": total_matches,
                    "top_score": top_score,
                    "zero_result_reason": _summarize_zero_result_reason(
                        results_count=len(results),
                        lookup_details=scope_details,
                        operation="cards.search",
                    ),
                    "lens": _summarize_lens_for_log(lens),
                    **scope_details,
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return {"results": results}
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "query_summary": _summarize_query_for_log(q) if q else None,
                "lens": _summarize_lens_for_log(lens),
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_atlas_query(
        lens: LensInput,
        query: AtlasQueryInput,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.cards.atlas.query"
        started = time.perf_counter()
        request_id = _new_request_id()
        scope_details: dict[str, Any] | None = None
        primary_space_key: str | None = None
        query_text = str(query.query or "").strip()
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            query=query_text or None,
            input_type="atlas_query",
            extra={
                "entity_types": list(query.entity_types or []),
                "entity_id": query.entity_id,
                "owner_project": query.owner_project,
                "project": query.project,
                "capability": query.capability,
            },
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                effective_entity_types = list(query.entity_types or ATLAS_ENTITY_TYPES)
                effective_kinds = [_atlas_kind_from_entity_type(entity_type) for entity_type in effective_entity_types]
                if lens.kinds:
                    allowed = set(lens.kinds)
                    effective_kinds = [kind for kind in effective_kinds if kind in allowed]

                rows: list[dict[str, Any]] = []
                seen: set[str] = set()
                for space_key in scoped:
                    if len(rows) >= query.limit:
                        break
                    if query_text:
                        candidate_rows = cards_search(
                            conn,
                            user_id=DEFAULT_USER_ID,
                            space_key=space_key,
                            query=query_text,
                            kinds=effective_kinds or None,
                            status=lens.status,
                            tags=lens.tags,
                            limit=query.limit,
                            include_body=query.include_body,
                            include_context=True,
                        )
                    else:
                        candidate_rows = cards_recent(
                            conn,
                            user_id=DEFAULT_USER_ID,
                            space_key=space_key,
                            kinds=effective_kinds or None,
                            status=lens.status,
                            tags=lens.tags,
                            limit=query.limit,
                            include_body=query.include_body,
                            include_context=True,
                        )
                    for raw_row in candidate_rows:
                        card_id = str(raw_row.get("id", ""))
                        if not card_id or card_id in seen:
                            continue
                        normalized = _normalize_atlas_result_row(raw_row, include_body=query.include_body)
                        if not _atlas_card_matches(normalized, query):
                            continue
                        rows.append(normalized)
                        seen.add(card_id)
                        if len(rows) >= query.limit:
                            break

                payload = {
                    "space": {
                        "key": primary_space_key,
                        "lookup_keys": scoped,
                    },
                    "filters": {
                        "entity_types": effective_entity_types,
                        "entity_id": query.entity_id,
                        "owner_project": query.owner_project,
                        "project": query.project,
                        "capability": query.capability,
                        "source": query.source,
                        "target": query.target,
                        "query": query_text or None,
                    },
                    "cards": rows,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "space_keys": scoped,
                    "query_summary": _summarize_query_for_log(query_text) if query_text else None,
                    "result_count": len(rows),
                    "entity_types": effective_entity_types,
                    "filters_applied": bool(
                        query.entity_id
                        or query.owner_project
                        or query.project
                        or query.capability
                        or query.source
                        or query.target
                    ),
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                "query_summary": _summarize_query_for_log(query_text) if query_text else None,
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_adaptation_query(
        lens: LensInput,
        query: AdaptationQueryInput,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.cards.adaptation.query"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            session_id=query.session_id,
            input_type="adaptation_query",
            extra={
                "subject_id": query.subject_id,
                "view": query.view,
            },
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                payload = _collect_adaptation_cards(conn, lens, query, scoped_space_keys=scoped)
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_keys": scoped,
                    "view": query.view,
                    "subject_id": query.subject_id,
                    "cards": int(((payload.get("counts") or {}).get("total")) or 0),
                    "result_count": int(((payload.get("counts") or {}).get("total")) or 0),
                    "lens": _summarize_lens_for_log(lens),
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_rehydrate_bundle(
        lens: LensInput,
        query: Any,
        *,
        include_body: bool,
        include_policy: bool,
        tool_name: str | None,
        task_type: str | None,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.rehydrate.bundle"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        q: str | None = None
        scope_details: dict[str, Any] | None = None
        try:
            _log_request_ingress(
                canonical,
                request_id=request_id,
                invoked_as=invoked_as,
                lens=lens,
                input_type=_query_input_type(query),
                extra={"query_summary": _summarize_query_input(query)},
            )
            q = _resolve_query_text(query).strip()
            if not q:
                raise ToolCallError(
                    "InvalidArguments",
                    "query must be non-empty.",
                    {"field": "query"},
                )
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                payload = rehydrate_bundle(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    query=q,
                    kinds=lens.kinds,
                    status=lens.status,
                    tags=lens.tags,
                    limit=lens.limit,
                    include_body=include_body,
                    include_policy=include_policy,
                    scope=lens.scope,
                    tool_name=tool_name,
                    task_type=task_type,
                )
                normalized = _normalize_rehydration_payload(payload)
                stage_reports = normalized.get("stages") or []
                for idx, stage in enumerate(stage_reports, start=1):
                    _emit_runtime_event(
                        "rehydration_stage",
                        operation=canonical,
                        request_id=request_id,
                        stage_index=idx,
                        stage=stage.get("stage"),
                        attempted=stage.get("attempted"),
                        skipped=stage.get("skipped"),
                        skip_reason=stage.get("skip_reason"),
                        zero_reason=stage.get("zero_reason"),
                        results=stage.get("results"),
                        space_keys=stage.get("space_keys"),
                        per_space_results=stage.get("per_space_results"),
                        canonical_space_key=primary_space_key,
                    )
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "query_summary": _summarize_query_for_log(q),
                    "lens": _summarize_lens_for_log(lens),
                    "tool_name": tool_name,
                    "task_type": task_type,
                    "stage_sequence": [row["stage"] for row in stage_reports],
                    "stage_results": {row["stage"]: row["results"] for row in stage_reports},
                    "skipped_stages": {
                        row["stage"]: row["skip_reason"]
                        for row in stage_reports
                        if row.get("skipped")
                    },
                    "zero_result_stages": {
                        row["stage"]: row["zero_reason"]
                        for row in stage_reports
                        if row.get("attempted") and int(row.get("results") or 0) == 0
                    },
                    "project_cards": len(normalized.get("project_cards") or []),
                    "policy_cards": len(normalized.get("policy_cards") or []),
                    "invalid_policy_rows": int(
                        ((normalized.get("policy_diagnostics") or {}).get("invalid_policy_rows")) or 0
                    ),
                    "final_selected_cards": int(
                        ((normalized.get("summary") or {}).get("project_cards")) or 0
                    ),
                    "rehydration_empty": bool(
                        ((normalized.get("summary") or {}).get("rehydration_empty"))
                    ),
                    "result_count": len(normalized.get("project_cards") or [])
                    + len(normalized.get("policy_cards") or []),
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return normalized
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "query_summary": _summarize_query_for_log(q) if q else None,
                "lens": _summarize_lens_for_log(lens),
                "tool_name": tool_name,
                "task_type": task_type,
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_policy_learn(
        lens: LensInput,
        signal: PolicySignalInput,
        evidence: list[EvidenceInput] | None,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.policy.learn"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            signal_summary=signal.summary,
            session_id=signal.session_id,
            input_type="policy_signal",
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                evidence_refs, evidence_ids, evidence_types = _build_evidence_refs(evidence)
                result = learn_policy_signal(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    summary=signal.summary,
                    signal_type=signal.signal_type,
                    outcome=signal.outcome,
                    scope_type=signal.scope_type,
                    scope_key=signal.scope_key,
                    lesson=signal.lesson,
                    preferred_behavior=signal.preferred_behavior,
                    anti_pattern=signal.anti_pattern,
                    confidence=signal.confidence,
                    tool_name=signal.tool_name,
                    task_type=signal.task_type,
                    session_id=signal.session_id,
                    created_by_client_name=DEFAULT_CLIENT_NAME,
                    tags=signal.tags,
                    evidence_refs=evidence_refs or None,
                    raw_payload=signal.model_dump(mode="json"),
                )
                payload = {
                    "signal": {
                        **result,
                        "signal_type": signal.signal_type,
                        "outcome": signal.outcome,
                        "scope_type": signal.scope_type,
                        "scope_key": signal.scope_key,
                    },
                    "evidence_ids": evidence_ids,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "signal_type": signal.signal_type,
                    "outcome": signal.outcome,
                    "scope_type": signal.scope_type,
                    "scope_key": signal.scope_key,
                    "tool_name": signal.tool_name,
                    "task_type": signal.task_type,
                    "promoted": bool(result.get("promoted")),
                    "policy_card_id": result.get("policy_card_id"),
                    "interaction_id": result.get("interaction_id"),
                    "interaction_event_captured": bool(result.get("interaction_event_captured")),
                    "confidence": result.get("confidence"),
                    "repetition_count": result.get("repetition_count"),
                    "promotion_attempted": bool(((result.get("promotion") or {}).get("attempted"))),
                    "promotion_reason": ((result.get("promotion") or {}).get("reason")),
                    "promotion_threshold_confidence": (
                        (result.get("promotion") or {}).get("threshold_confidence")
                    ),
                    "promotion_threshold_repetition": (
                        (result.get("promotion") or {}).get("threshold_repetition")
                    ),
                    "updated_existing_policy_card": bool(
                        ((result.get("promotion") or {}).get("updated_existing"))
                    ),
                    "signal_summary": _summarize_text(signal.summary, max_chars=96),
                    "evidence_count": len(evidence_types),
                    "evidence_types": evidence_types,
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "signal_type": signal.signal_type,
                "outcome": signal.outcome,
                "scope_type": signal.scope_type,
                "scope_key": signal.scope_key,
                "tool_name": signal.tool_name,
                "task_type": signal.task_type,
                "signal_summary": _summarize_text(signal.summary, max_chars=96),
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_policy_inspect(
        lens: LensInput,
        query: PolicyInspectInput,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.policy.inspect"
        started = time.perf_counter()
        request_id = _new_request_id()
        primary_space_key: str | None = None
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            query=query.query,
            session_id=query.session_id,
            input_type="policy_inspect_query",
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                policy_payload = query_policy_cards(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    query=query.query,
                    scope_types=query.scope_types,
                    scope_key=query.scope_key,
                    tool_name=query.tool_name,
                    task_type=query.task_type,
                    include_global=(lens.scope == "soft"),
                    limit=query.limit,
                    include_body=query.include_body,
                )
                policy_cards = [
                    _normalize_policy_card_row(row) for row in policy_payload.get("cards", [])
                ]
                interaction_events: list[dict[str, Any]] = []
                if query.include_events and query.event_limit > 0:
                    interaction_events = [
                        _normalize_interaction_event_row(row)
                        for row in list_interaction_events(
                            conn,
                            user_id=DEFAULT_USER_ID,
                            space_key=primary_space_key,
                            limit=query.event_limit,
                            session_id=query.session_id,
                            event_types=["policy_signal"],
                        )
                    ]
                payload = {
                    "space": {
                        "key": primary_space_key,
                        "lookup_keys": list((policy_payload.get("filters") or {}).get("lookup_keys") or []),
                    },
                    "cards": policy_cards,
                    "filters": policy_payload.get("filters") or {},
                    "interaction_events": interaction_events,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "query_summary": _summarize_query_for_log(query.query)
                    if query.query
                    else None,
                    "tool_name": query.tool_name,
                    "task_type": query.task_type,
                    "result_count": len(policy_cards),
                    "interaction_events": len(interaction_events),
                    "invalid_policy_rows": int(
                        ((policy_payload.get("diagnostics") or {}).get("invalid_policy_rows")) or 0
                    ),
                    "policy_rows_scanned": int(
                        ((policy_payload.get("diagnostics") or {}).get("scanned_rows")) or 0
                    ),
                    "scope_types": list(query.scope_types or []),
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "query_summary": _summarize_query_for_log(query.query) if query.query else None,
                "tool_name": query.tool_name,
                "task_type": query.task_type,
                **(scope_details or {}),
                **_space_log_context(None, space_key=primary_space_key),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_upsert(
        lens: LensInput,
        card: CardInput,
        evidence: list[EvidenceInput] | None,
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.cards.upsert"
        started = time.perf_counter()
        request_id = _new_request_id()
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            input_type="card_upsert_request",
            extra={
                "card_kind": card.kind,
                "card_id": card.id,
            },
        )
        try:
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                existing_card = None
                if card.id:
                    existing_card = conn.execute(
                        "SELECT id FROM cards WHERE id = ?;",
                        (card.id,),
                    ).fetchone()
                is_create = existing_card is None
                if is_create:
                    write_limit = _resolve_mcp_card_write_limit_per_hour()
                    if write_limit > 0:
                        window_seconds = _resolve_mcp_card_write_window_seconds()
                        recent_writes = _count_recent_card_creates(
                            conn,
                            user_id=DEFAULT_USER_ID,
                            space_key=primary_space_key,
                            client_name=DEFAULT_CLIENT_NAME,
                            window_seconds=window_seconds,
                        )
                        if recent_writes >= write_limit:
                            raise ToolCallError(
                                "WriteRateLimited",
                                "Card write rate limit exceeded for this client and space.",
                                {
                                    "limit": write_limit,
                                    "window_seconds": window_seconds,
                                    "space_key": primary_space_key,
                                    "client_name": DEFAULT_CLIENT_NAME,
                                    "recent_writes": recent_writes,
                                    "advice": (
                                        "Wait for the current window to pass or update existing cards "
                                        "instead of creating additional new cards."
                                    ),
                                },
                            )
                evidence_refs, evidence_ids, evidence_types = _build_evidence_refs(evidence)
                warnings = _build_card_write_warnings(
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                )
                context_json = _merge_card_context(
                    context=card.context,
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                    warnings=warnings,
                    operation=canonical,
                )
                context_json = _merge_card_context_with_atlas(card=card, context_json=context_json)
                merged_tags = _merge_tags_with_atlas(card)

                card_id = card_upsert(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    kind=card.kind,
                    title=card.title,
                    summary=card.summary,
                    body=card.body,
                    status=card.status,
                    salience=card.salience,
                    tags=merged_tags,
                    created_by_client_name=DEFAULT_CLIENT_NAME,
                    context_json=context_json,
                    card_id=card.id,
                    evidence_refs=evidence_refs or None,
                )
                row = conn.execute(
                    """
                    SELECT c.id AS id, c.updated_at AS updated_at, s.key AS space_key
                    FROM cards c
                    JOIN spaces s ON s.id = c.space_id
                    WHERE c.id = ?
                    """,
                    (card_id,),
                ).fetchone()
                if row is None:
                    raise ToolCallError(
                        "InternalError",
                        "Card upsert completed but card row could not be loaded.",
                        {"card_id": card_id},
                    )
                payload = {
                    "card": {
                        "id": str(row["id"]),
                        "space_key": str(row["space_key"]),
                        "updated_at": _iso8601_utc(row["updated_at"]),
                    },
                    "evidence_ids": evidence_ids,
                    "warnings": warnings,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "card_id": str(row["id"]),
                    "evidence_ids": evidence_ids,
                    "is_create": is_create,
                    "card_kind": card.kind,
                    "evidence_count": len(evidence_types),
                    "evidence_types": evidence_types,
                    "warning_codes": [str(item["code"]) for item in warnings],
                    "title_chars": len(card.title.strip()),
                    "summary_chars": len(card.summary.strip()),
                    "body_chars": len(card.body),
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                "card_kind": card.kind,
                **(scope_details or {}),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_supersede(
        lens: LensInput,
        old_card_id: str,
        card: CardInput,
        evidence: list[EvidenceInput] | None,
        relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"],
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.cards.supersede"
        started = time.perf_counter()
        request_id = _new_request_id()
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            input_type="card_supersede_request",
            extra={
                "old_card_id": old_card_id,
                "card_kind": card.kind,
            },
        )
        try:
            old_id = old_card_id.strip()
            if not old_id:
                raise ToolCallError(
                    "InvalidArguments",
                    "old_card_id is required.",
                    {"field": "old_card_id"},
                )
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                evidence_refs, evidence_ids, evidence_types = _build_evidence_refs(evidence)
                warnings = _build_card_write_warnings(
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                )
                context_json = _merge_card_context(
                    context=card.context,
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                    warnings=warnings,
                    operation=canonical,
                )
                context_json = _merge_card_context_with_atlas(card=card, context_json=context_json)
                merged_tags = _merge_tags_with_atlas(card)
                result = card_supersede(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    old_card_id=old_id,
                    kind=card.kind,
                    title=card.title,
                    summary=card.summary,
                    body=card.body,
                    status=card.status,
                    salience=card.salience,
                    tags=merged_tags,
                    created_by_client_name=DEFAULT_CLIENT_NAME,
                    context_json=context_json,
                    source_confidence=None,
                    evidence_refs=evidence_refs or None,
                    relation_type=relation_type,
                )
                payload = {
                    "old_card_id": result["old_card_id"],
                    "new_card_id": result["new_card_id"],
                    "relation_type": result["relation_type"],
                    "evidence_ids": evidence_ids,
                    "warnings": warnings,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "old_card_id": result["old_card_id"],
                    "card_id": result["new_card_id"],
                    "relation_type": result["relation_type"],
                    "evidence_ids": evidence_ids,
                    "evidence_count": len(evidence_types),
                    "evidence_types": evidence_types,
                    "warning_codes": [str(item["code"]) for item in warnings],
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                "old_card_id": old_card_id,
                "card_kind": card.kind,
                **(scope_details or {}),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    async def _handle_cards_merge(
        lens: LensInput,
        card_ids: list[str],
        card: CardInput,
        evidence: list[EvidenceInput] | None,
        relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"],
        invoked_as: str,
    ) -> dict[str, Any]:
        canonical = "muninn.cards.merge"
        started = time.perf_counter()
        request_id = _new_request_id()
        scope_details: dict[str, Any] | None = None
        _log_request_ingress(
            canonical,
            request_id=request_id,
            invoked_as=invoked_as,
            lens=lens,
            input_type="card_merge_request",
            extra={
                "source_count": len(card_ids),
                "card_kind": card.kind,
            },
        )
        try:
            if len(card_ids) < 2:
                raise ToolCallError(
                    "InvalidArguments",
                    "card_ids must include at least 2 values.",
                    {"field": "card_ids"},
                )
            with _human_memory_conn(correlation_id=request_id) as conn:
                scoped, scope_details = _scope_space_keys_with_details(conn, lens)
                primary_space_key = scoped[0] if scoped else None
                _log_space_resolution(
                    request_id=request_id,
                    operation=canonical,
                    conn=conn,
                    details=scope_details,
                )
                evidence_refs, evidence_ids, evidence_types = _build_evidence_refs(evidence)
                warnings = _build_card_write_warnings(
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                )
                context_json = _merge_card_context(
                    context=card.context,
                    card_kind=card.kind,
                    evidence_types=evidence_types,
                    warnings=warnings,
                    operation=canonical,
                )
                context_json = _merge_card_context_with_atlas(card=card, context_json=context_json)
                merged_tags = _merge_tags_with_atlas(card)
                result = cards_merge(
                    conn,
                    user_id=DEFAULT_USER_ID,
                    space_key=primary_space_key,
                    card_ids=card_ids,
                    kind=card.kind,
                    title=card.title,
                    summary=card.summary,
                    body=card.body,
                    status=card.status,
                    salience=card.salience,
                    tags=merged_tags,
                    created_by_client_name=DEFAULT_CLIENT_NAME,
                    context_json=context_json,
                    source_confidence=None,
                    evidence_refs=evidence_refs or None,
                    relation_type=relation_type,
                )
                payload = {
                    "merged_card_id": result["merged_card_id"],
                    "superseded_card_ids": result["superseded_card_ids"],
                    "relation_type": result["relation_type"],
                    "evidence_ids": evidence_ids,
                    "warnings": warnings,
                }
                log_payload: dict[str, Any] = {
                    "status": "ok",
                    "request_id": request_id,
                    "scope": lens.scope,
                    "space_key": primary_space_key,
                    "card_id": result["merged_card_id"],
                    "source_card_ids": result["superseded_card_ids"],
                    "source_count": len(result["superseded_card_ids"]),
                    "relation_type": result["relation_type"],
                    "evidence_ids": evidence_ids,
                    "evidence_count": len(evidence_types),
                    "evidence_types": evidence_types,
                    "warning_codes": [str(item["code"]) for item in warnings],
                    **(scope_details or {}),
                    **_space_log_context(conn, space_key=primary_space_key),
                    "duration_ms": _elapsed_ms(started),
                }
                if invoked_as != canonical:
                    log_payload["invoked_as"] = invoked_as
                    log_payload["deprecated_alias"] = True
                _log_tool_invocation(canonical, **log_payload)
                return payload
        except Exception as exc:
            err = _handle_tool_exception(exc)
            error_code = ((err.get("error") or {}).get("code")) if isinstance(err, dict) else None
            log_payload = {
                "status": "error",
                "request_id": request_id,
                "scope": lens.scope,
                "error_code": error_code,
                "lens": _summarize_lens_for_log(lens),
                "source_count": len(card_ids),
                "card_kind": card.kind,
                **(scope_details or {}),
                **_error_log_details(exc, err),
                "duration_ms": _elapsed_ms(started),
            }
            if invoked_as != canonical:
                log_payload["invoked_as"] = invoked_as
                log_payload["deprecated_alias"] = True
            _log_tool_invocation(canonical, **log_payload)
            return err

    @mcp.tool(
        name="muninn.system.ping",
        description="Lightweight MCP diagnostic ping for connectivity, version, DB path, and auth state.",
    )
    async def muninn_system_ping() -> dict[str, Any]:
        return await _handle_system_ping("muninn.system.ping")

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/system.ping",
            description="DEPRECATED alias for muninn.system.ping. Will be removed in v0.12.",
        )
        async def muninn_system_ping_alias() -> dict[str, Any]:
            return await _handle_system_ping("muninn/system.ping")

    @mcp.tool(
        name="muninn.spaces.resolve",
        description="Resolve space metadata from cwd. Use this first for lens-based card operations.",
    )
    async def muninn_spaces_resolve(cwd: str) -> dict[str, Any]:
        return await _handle_spaces_resolve(cwd, "muninn.spaces.resolve")

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/spaces.resolve",
            description="DEPRECATED alias for muninn.spaces.resolve. Will be removed in v0.12.",
        )
        async def muninn_spaces_resolve_alias(cwd: str) -> dict[str, Any]:
            return await _handle_spaces_resolve(cwd, "muninn/spaces.resolve")

    @mcp.tool(
        name="muninn.cards.recent",
        description=(
            "Fetch recent durable cards for a lens (space + scope). "
            "Returns prompt-friendly summaries first."
        ),
    )
    async def muninn_cards_recent(lens: LensInput) -> dict[str, Any]:
        return await _handle_cards_recent(lens, "muninn.cards.recent")

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.recent",
            description="DEPRECATED alias for muninn.cards.recent. Will be removed in v0.12.",
        )
        async def muninn_cards_recent_alias(lens: LensInput) -> dict[str, Any]:
            return await _handle_cards_recent(lens, "muninn/cards.recent")

    @mcp.tool(
        name="muninn.cards.search",
        description="FTS search over card title/summary/body within a lens.",
    )
    async def muninn_cards_search(query: str | SearchQueryInput | list[str], lens: LensInput) -> dict[str, Any]:
        return await _handle_cards_search(query, lens, "muninn.cards.search")

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.search",
            description="DEPRECATED alias for muninn.cards.search. Will be removed in v0.12.",
        )
        async def muninn_cards_search_alias(
            query: str | SearchQueryInput | list[str],
            lens: LensInput,
        ) -> dict[str, Any]:
            return await _handle_cards_search(query, lens, "muninn/cards.search")

    @mcp.tool(
        name="muninn.cards.atlas.query",
        description=(
            "Query atlas.* cards with stable ownership and boundary refs "
            "(project/capability/source/target/entity_id)."
        ),
    )
    async def muninn_cards_atlas_query(
        lens: LensInput,
        query: AtlasQueryInput,
    ) -> dict[str, Any]:
        return await _handle_cards_atlas_query(lens, query, "muninn.cards.atlas.query")

    @mcp.tool(
        name="muninn.rehydrate.bundle",
        description=(
            "Run deterministic session rehydration: strict search, recent, soft fallback, "
            "alias/global widening, and policy-state retrieval."
        ),
    )
    async def muninn_rehydrate_bundle(
        lens: LensInput,
        query: str | SearchQueryInput | list[str],
        include_body: bool = False,
        include_policy: bool = True,
        tool_name: str | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        return await _handle_rehydrate_bundle(
            lens,
            query,
            include_body=include_body,
            include_policy=include_policy,
            tool_name=tool_name,
            task_type=task_type,
            invoked_as="muninn.rehydrate.bundle",
        )

    @mcp.tool(
        name="muninn.policy.learn",
        description=(
            "Capture evaluative/directive feedback as scoped policy-state without weight updates."
        ),
    )
    async def muninn_policy_learn(
        lens: LensInput,
        signal: PolicySignalInput,
        evidence: list[EvidenceInput] | None = None,
    ) -> dict[str, Any]:
        return await _handle_policy_learn(lens, signal, evidence, "muninn.policy.learn")

    @mcp.tool(
        name="muninn.policy.inspect",
        description=(
            "Inspect active scoped policy-state and recent interaction signals for the current project."
        ),
    )
    async def muninn_policy_inspect(
        lens: LensInput,
        query: PolicyInspectInput | None = None,
    ) -> dict[str, Any]:
        return await _handle_policy_inspect(
            lens,
            query or PolicyInspectInput(),
            "muninn.policy.inspect",
        )

    @mcp.tool(
        name="muninn.cards.adaptation.query",
        description=(
            "Query adaptation-memory cards (preferences, overrides, corrections, outcomes) "
            "with deterministic subject/scope/persistence filters."
        ),
    )
    async def muninn_cards_adaptation_query(
        lens: LensInput,
        query: AdaptationQueryInput,
    ) -> dict[str, Any]:
        return await _handle_cards_adaptation_query(
            lens,
            query,
            "muninn.cards.adaptation.query",
        )

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.adaptation.query",
            description="DEPRECATED alias for muninn.cards.adaptation.query. Will be removed in v0.12.",
        )
        async def muninn_cards_adaptation_query_alias(
            lens: LensInput,
            query: AdaptationQueryInput,
        ) -> dict[str, Any]:
            return await _handle_cards_adaptation_query(
                lens,
                query,
                "muninn/cards.adaptation.query",
            )

    @mcp.tool(
        name="muninn.cards.upsert",
        description=(
            "Create or update a durable memory card. "
            "Only write when something durable changed. "
            "Write 1-3 cards max per task. summary should be 1-3 sentences."
        ),
    )
    async def muninn_cards_upsert(
        lens: LensInput,
        card: CardInput,
        evidence: list[EvidenceInput] | None = None,
    ) -> dict[str, Any]:
        return await _handle_cards_upsert(lens, card, evidence, "muninn.cards.upsert")

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.upsert",
            description="DEPRECATED alias for muninn.cards.upsert. Will be removed in v0.12.",
        )
        async def muninn_cards_upsert_alias(
            lens: LensInput,
            card: CardInput,
            evidence: list[EvidenceInput] | None = None,
        ) -> dict[str, Any]:
            return await _handle_cards_upsert(lens, card, evidence, "muninn/cards.upsert")

    @mcp.tool(
        name="muninn.cards.supersede",
        description="Supersede one card with a canonical replacement and record lineage relation.",
    )
    async def muninn_cards_supersede(
        lens: LensInput,
        old_card_id: str,
        card: CardInput,
        relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"] = "supersedes",
        evidence: list[EvidenceInput] | None = None,
    ) -> dict[str, Any]:
        return await _handle_cards_supersede(
            lens,
            old_card_id,
            card,
            evidence,
            relation_type,
            "muninn.cards.supersede",
        )

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.supersede",
            description="DEPRECATED alias for muninn.cards.supersede. Will be removed in v0.12.",
        )
        async def muninn_cards_supersede_alias(
            lens: LensInput,
            old_card_id: str,
            card: CardInput,
            relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"] = "supersedes",
            evidence: list[EvidenceInput] | None = None,
        ) -> dict[str, Any]:
            return await _handle_cards_supersede(
                lens,
                old_card_id,
                card,
                evidence,
                relation_type,
                "muninn/cards.supersede",
            )

    @mcp.tool(
        name="muninn.cards.merge",
        description="Merge multiple cards into one canonical card and link merged lineage.",
    )
    async def muninn_cards_merge(
        lens: LensInput,
        card_ids: list[str],
        card: CardInput,
        relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"] = "duplicates",
        evidence: list[EvidenceInput] | None = None,
    ) -> dict[str, Any]:
        return await _handle_cards_merge(
            lens,
            card_ids,
            card,
            evidence,
            relation_type,
            "muninn.cards.merge",
        )

    if _resolve_mcp_enable_slash_aliases():
        @mcp.tool(
            name="muninn/cards.merge",
            description="DEPRECATED alias for muninn.cards.merge. Will be removed in v0.12.",
        )
        async def muninn_cards_merge_alias(
            lens: LensInput,
            card_ids: list[str],
            card: CardInput,
            relation_type: Literal["supersedes", "duplicates", "contradicts", "refines"] = "duplicates",
            evidence: list[EvidenceInput] | None = None,
        ) -> dict[str, Any]:
            return await _handle_cards_merge(
                lens,
                card_ids,
                card,
                evidence,
                relation_type,
                "muninn/cards.merge",
            )

    return mcp


def run_mcp_server(host: str = "127.0.0.1", port: int = 8765, base_url: str | None = None) -> None:
    if base_url:
        os.environ["MUNINN_BASE_URL"] = base_url

    _validate_exposure_guard(host)
    server = create_mcp_server(host=host, port=port)
    app = server.streamable_http_app()
    if _resolve_mcp_requires_api_key():
        app.add_middleware(McpApiKeyMiddleware)

    print("Muninn MCP up")
    _print_connect_urls(host, port)
    print(f"  Muninn Base URL: {_resolve_base_url()}")
    print(f"  Human-memory DB: {_resolve_human_memory_db_path()}")
    print(f"  API key header forwarding: {'enabled' if os.getenv('MUNINN_API_KEY') else 'disabled'}")
    print(f"  Bearer auth enabled: {'yes' if _resolve_mcp_bearer_token() else 'no'}")
    print(f"  MCP auth required: {'yes' if _resolve_mcp_requires_api_key() else 'no'}")
    print(f"  Slash aliases enabled: {'yes' if _resolve_mcp_enable_slash_aliases() else 'no'}")
    if _resolve_mcp_enable_slash_aliases():
        print(f"  Alias warning suppression: {'yes' if _resolve_mcp_suppress_alias_warnings() else 'no'}")
    telemetry_path = _resolve_mcp_telemetry_path()
    print(f"  MCP telemetry JSONL: {telemetry_path if telemetry_path else 'disabled'}")
    if telemetry_path:
        print(f"  Telemetry flush: {'yes' if _resolve_mcp_telemetry_flush() else 'no'}")
        print(
            "  Telemetry rotation: "
            f"{_resolve_mcp_telemetry_max_bytes()} bytes x {_resolve_mcp_telemetry_backup_count()} backups"
        )
        print("  Telemetry fallback: console/journal events remain active if file logging fails")
    limit = _resolve_mcp_card_write_limit_per_hour()
    if limit <= 0:
        print("  Card upsert rate limit: disabled")
    else:
        print(
            "  Card upsert rate limit: "
            f"{limit}/{_resolve_mcp_card_write_window_seconds()}s per client per space"
        )
    _emit_runtime_event(
        "startup",
        operation="muninn.mcp_server",
        stage="ready",
        config_source="cli_args_and_env",
        host=host,
        port=port,
        base_url=_resolve_base_url(),
        auth_required=_resolve_mcp_requires_api_key(),
        auth_mode=_mcp_auth_mode(),
        slash_aliases=_resolve_mcp_enable_slash_aliases(),
        telemetry_path=str(telemetry_path) if telemetry_path else None,
        telemetry_rotation_policy=(
            "size"
            if telemetry_path and _resolve_mcp_telemetry_max_bytes() is not None
            else "disabled"
        ),
        telemetry_retention_backups=(
            _resolve_mcp_telemetry_backup_count() if telemetry_path else 0
        ),
        telemetry_fallback="console_or_journal",
    )
    if not _is_loopback_host(host):
        print("  WARNING: non-loopback bind enabled; ensure firewall and explicit auth tokens are configured.")
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("Muninn MCP stopped")


def run_mcp_stdio(base_url: str | None = None) -> None:
    if base_url:
        os.environ["MUNINN_BASE_URL"] = base_url

    server = create_mcp_server()
    print("Muninn MCP stdio up")
    print(f"  Muninn Base URL: {_resolve_base_url()}")
    print(f"  Human-memory DB: {_resolve_human_memory_db_path()}")
    telemetry_path = _resolve_mcp_telemetry_path()
    print(f"  MCP telemetry JSONL: {telemetry_path if telemetry_path else 'disabled'}")
    if telemetry_path:
        print(
            "  Telemetry rotation: "
            f"{_resolve_mcp_telemetry_max_bytes()} bytes x {_resolve_mcp_telemetry_backup_count()} backups"
        )
        print("  Telemetry fallback: console/journal events remain active if file logging fails")
    _emit_runtime_event(
        "startup",
        operation="muninn.mcp_stdio",
        stage="ready",
        config_source="cli_args_and_env",
        base_url=_resolve_base_url(),
        auth_mode=_mcp_auth_mode(),
        telemetry_path=str(telemetry_path) if telemetry_path else None,
        telemetry_rotation_policy=(
            "size"
            if telemetry_path and _resolve_mcp_telemetry_max_bytes() is not None
            else "disabled"
        ),
        telemetry_retention_backups=(
            _resolve_mcp_telemetry_backup_count() if telemetry_path else 0
        ),
        telemetry_fallback="console_or_journal",
    )
    try:
        server.run(transport="stdio")
    except KeyboardInterrupt:
        print("Muninn MCP stdio stopped")
