from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from ..client import MuninnClient
from ..models import (
    ConfirmCandidatesRequest,
    ListPendingRequest,
    QueryVectorRequest,
    RehydrateRequest,
    StageCandidatesRequest,
    UpsertEmbeddingsRequest,
    WriteCandidatesRequest,
)

PUBLIC_TOOL_NAMES = {
    "muninn_rehydrate",
    "muninn_write_candidates",
    "muninn_stage_candidates",
    "muninn_list_pending",
    "muninn_confirm_candidates",
    "muninn_upsert_embeddings",
    "muninn_query_vector",
    "muninn_version",
    "muninn_debug_vector_backend",
}


def load_tool_spec() -> dict[str, Any]:
    try:
        spec_path = resources.files("muninn.resources").joinpath("muninn_tool_spec.json")
        return json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception:
        # Fallback for local dev paths.
        path = Path(__file__).resolve().parents[3] / "schemas" / "tooling" / "muninn_tool_spec.json"
        return json.loads(path.read_text(encoding="utf-8"))


def public_tools_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    tools = spec.get("tools", [])
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = tool.get("tool_name")
        path = str(tool.get("path", ""))
        if name not in PUBLIC_TOOL_NAMES:
            continue
        if path.startswith("/v0/admin/"):
            continue
        out.append(tool)
    return out


def dispatch_tool_call(client: MuninnClient, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "muninn_rehydrate":
        return client.rehydrate(RehydrateRequest(**arguments)).model_dump()

    if tool_name == "muninn_write_candidates":
        return client.write_candidates(WriteCandidatesRequest(**arguments)).model_dump()

    if tool_name == "muninn_stage_candidates":
        return client.stage_candidates(StageCandidatesRequest(**arguments)).model_dump()

    if tool_name == "muninn_list_pending":
        return client.list_pending(ListPendingRequest(**arguments)).model_dump()

    if tool_name == "muninn_confirm_candidates":
        return client.confirm_candidates(ConfirmCandidatesRequest(**arguments)).model_dump()

    if tool_name == "muninn_upsert_embeddings":
        return client.upsert_embeddings(UpsertEmbeddingsRequest(**arguments)).model_dump()

    if tool_name == "muninn_query_vector":
        return client.query_vector(QueryVectorRequest(**arguments)).model_dump()

    if tool_name == "muninn_version":
        return client.version(
            namespace=arguments.get("namespace", "default"),
            profile=arguments.get("profile", "generic"),
            embedding_model=arguments.get("embedding_model"),
        )

    if tool_name == "muninn_debug_vector_backend":
        return client.debug_vector_backend()

    raise ValueError(f"Unknown Muninn tool: {tool_name}")
