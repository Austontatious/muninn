from __future__ import annotations

import os
from typing import Any

from ..client import MuninnClient
from ..models import MemoryCandidate, RehydrateRequest, WriteCandidatesRequest


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
