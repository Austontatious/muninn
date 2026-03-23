from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from ..client import MuninnClient
from ..models import (
    CardCreateRequest,
    CardEmbeddingUpsertRequest,
    CardexRetrieveRequest,
    ConfirmCandidatesRequest,
    DecideProposalRequest,
    IngestRequest,
    LinkCardRefsRequest,
    ListPendingRequest,
    PromoteRequest,
    ProposeRequest,
    QueryVectorRequest,
    RehydrateRequest,
    SourceArtifactsRequest,
    SourceCreateRequest,
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
    "muninn_cardex_create_card",
    "muninn_cardex_get_card",
    "muninn_cardex_create_source",
    "muninn_cardex_ingest",
    "muninn_cardex_add_source_artifacts",
    "muninn_cardex_link_refs",
    "muninn_cardex_retrieve",
    "muninn_cardex_promote",
    "muninn_cardex_propose",
    "muninn_cardex_confirm",
    "muninn_cardex_reject",
    "muninn_cardex_upsert_embedding",
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

    if tool_name == "muninn_cardex_create_card":
        return client.create_card(CardCreateRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_get_card":
        card_id = str(arguments.get("card_id") or "").strip()
        if not card_id:
            raise ValueError("muninn_cardex_get_card requires card_id")
        namespace = arguments.get("namespace", "default")
        return client.get_card(card_id=card_id, namespace=namespace).model_dump()

    if tool_name == "muninn_cardex_create_source":
        return client.create_source(SourceCreateRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_ingest":
        return client.ingest(IngestRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_add_source_artifacts":
        source_id = str(arguments.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("muninn_cardex_add_source_artifacts requires source_id")
        payload = dict(arguments)
        payload.pop("source_id", None)
        return client.add_source_artifacts(source_id, SourceArtifactsRequest(**payload)).model_dump()

    if tool_name == "muninn_cardex_link_refs":
        card_id = str(arguments.get("card_id") or "").strip()
        if not card_id:
            raise ValueError("muninn_cardex_link_refs requires card_id")
        payload = dict(arguments)
        payload.pop("card_id", None)
        return client.link_card_refs(card_id, LinkCardRefsRequest(**payload)).model_dump()

    if tool_name == "muninn_cardex_retrieve":
        return client.cardex_retrieve(CardexRetrieveRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_promote":
        return client.promote(PromoteRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_propose":
        return client.propose(ProposeRequest(**arguments)).model_dump()

    if tool_name == "muninn_cardex_confirm":
        proposal_id = str(arguments.get("proposal_id") or "").strip()
        if not proposal_id:
            raise ValueError("muninn_cardex_confirm requires proposal_id")
        payload = dict(arguments)
        payload.pop("proposal_id", None)
        return client.confirm_proposal(proposal_id, DecideProposalRequest(**payload)).model_dump()

    if tool_name == "muninn_cardex_reject":
        proposal_id = str(arguments.get("proposal_id") or "").strip()
        if not proposal_id:
            raise ValueError("muninn_cardex_reject requires proposal_id")
        payload = dict(arguments)
        payload.pop("proposal_id", None)
        return client.reject_proposal(proposal_id, DecideProposalRequest(**payload)).model_dump()

    if tool_name == "muninn_cardex_upsert_embedding":
        return client.upsert_card_embedding(CardEmbeddingUpsertRequest(**arguments)).model_dump()

    raise ValueError(f"Unknown Muninn tool: {tool_name}")
