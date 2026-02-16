from __future__ import annotations

import os
from typing import Any, Literal

from ..client import MuninnClient
from ..models import (
    ConfirmCandidatesRequest,
    ListPendingRequest,
    MemoryCandidate,
    RehydrateRequest,
    StageCandidatesRequest,
    WriteCandidatesRequest,
)


def make_client_from_env() -> MuninnClient:
    base_url = os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    return MuninnClient(base_url=base_url)


def rehydrate(
    namespace: str,
    profile: str,
    entity_id: str,
    query: str,
    k: int = 8,
    embedding_model: str | None = None,
    query_embedding: list[float] | None = None,
) -> dict[str, Any]:
    with make_client_from_env() as client:
        req = RehydrateRequest(
            namespace=namespace,
            profile=profile,
            entity_id=entity_id,
            query=query,
            k=k,
            embedding_model=embedding_model,
            query_embedding=query_embedding,
        )
        return client.rehydrate(req).model_dump()


def write_candidates(
    namespace: str,
    candidates: list[MemoryCandidate | dict[str, Any]],
) -> dict[str, Any]:
    parsed: list[MemoryCandidate] = [
        candidate if isinstance(candidate, MemoryCandidate) else MemoryCandidate(**candidate)
        for candidate in candidates
    ]
    with make_client_from_env() as client:
        req = WriteCandidatesRequest(namespace=namespace, candidates=parsed)
        return client.write_candidates(req).model_dump()


def stage_candidates(
    namespace: str,
    candidates: list[MemoryCandidate | dict[str, Any]],
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    parsed: list[MemoryCandidate] = [
        candidate if isinstance(candidate, MemoryCandidate) else MemoryCandidate(**candidate)
        for candidate in candidates
    ]
    with make_client_from_env() as client:
        req = StageCandidatesRequest(namespace=namespace, candidates=parsed, ttl_seconds=ttl_seconds)
        return client.stage_candidates(req).model_dump()


def list_pending(
    namespace: str,
    entity_id: str | None = None,
    status: str = "pending",
    limit: int = 50,
) -> dict[str, Any]:
    with make_client_from_env() as client:
        req = ListPendingRequest(namespace=namespace, entity_id=entity_id, status=status, limit=limit)
        return client.list_pending(req).model_dump()


def confirm_candidates(
    namespace: str,
    pending_ids: list[str],
    decision: Literal["accept", "reject"],
    decided_by: str,
    note: str | None = None,
) -> dict[str, Any]:
    with make_client_from_env() as client:
        req = ConfirmCandidatesRequest(
            namespace=namespace,
            pending_ids=pending_ids,
            decision=decision,
            decided_by=decided_by,
            note=note,
        )
        return client.confirm_candidates(req).model_dump()
