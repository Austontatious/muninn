from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ProvenanceType = Literal["user", "assistant", "tool", "document", "system"]


class Provenance(BaseModel):
    source_type: ProvenanceType
    source_id: str | None = None
    note: str | None = None
    ts: float | None = None


class MemoryCandidate(BaseModel):
    kind: Literal["fact", "episode", "preference"]
    entity: dict[str, Any] = Field(..., description="Entity reference or minimal entity payload")
    payload: dict[str, Any] = Field(..., description="Fields specific to kind")
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    provenance: Provenance


class WriteCandidatesRequest(BaseModel):
    namespace: str = "default"
    candidates: list[MemoryCandidate]


class WriteCandidatesResponse(BaseModel):
    accepted: int
    rejected: int
    ids: list[str]
    reasons: list[str] = []


class PendingCandidate(BaseModel):
    id: str
    namespace: str
    entity_id: str
    candidate: MemoryCandidate
    reason: str
    status: str
    created_at: float
    expires_at: float | None = None


class StageCandidatesRequest(BaseModel):
    namespace: str = "default"
    candidates: list[MemoryCandidate]
    ttl_seconds: int | None = None


class StageCandidatesResponse(BaseModel):
    accepted: int
    pending: int
    rejected: int
    accepted_ids: list[str]
    pending_ids: list[str]
    reject_reasons: list[str] = []
    pending_reasons: list[str] = []


class ListPendingRequest(BaseModel):
    namespace: str = "default"
    entity_id: str | None = None
    status: str = "pending"
    limit: int = 50


class ListPendingResponse(BaseModel):
    items: list[PendingCandidate]


class ConfirmCandidatesRequest(BaseModel):
    namespace: str = "default"
    pending_ids: list[str]
    decision: Literal["accept", "reject"]
    decided_by: str
    note: str | None = None


class ConfirmCandidatesResponse(BaseModel):
    namespace: str
    decision: str
    processed: int
    accepted_writes: int
    rejected: int
    missing: int
    expired: int
    accepted_ids: list[str] = []
    reasons: list[str] = []


class RetrieveRequest(BaseModel):
    namespace: str = "default"
    query: str
    entity_id: str | None = None
    k: int = 8
    query_embedding: list[float] | None = None
    embedding_model: str | None = None


class RetrievedItem(BaseModel):
    kind: Literal["fact", "episode", "preference"]
    id: str
    entity_id: str
    text: str
    confidence: float
    provenance: Provenance


class RetrieveResponse(BaseModel):
    items: list[RetrievedItem]


class UpsertEmbeddingsItem(BaseModel):
    item_id: str
    kind: Literal["fact", "episode", "preference"]
    entity_id: str
    model: str
    vector: list[float]


class UpsertEmbeddingsRequest(BaseModel):
    namespace: str = "default"
    items: list[UpsertEmbeddingsItem]


class UpsertEmbeddingsResponse(BaseModel):
    upserted: int
    rejected: int
    reasons: list[str] = []


class QueryVectorRequest(BaseModel):
    namespace: str = "default"
    model: str
    query_vector: list[float]
    entity_id: str | None = None
    kinds: list[Literal["fact", "episode", "preference"]] | None = None
    k: int = 8


class VectorHit(BaseModel):
    item_id: str
    kind: Literal["fact", "episode", "preference"]
    entity_id: str
    score: float


class QueryVectorResponse(BaseModel):
    hits: list[VectorHit]


class ReindexVectorsRequest(BaseModel):
    namespace: str = "default"
    model: str | None = None
    dim: int | None = None
    batch_size: int = 500
    dry_run: bool = False
    force_backend: Literal["auto", "sqlite_vec", "bruteforce"] = "auto"


class ReindexVectorsResponse(BaseModel):
    namespace: str
    backend_used: str
    scanned: int
    reindexed: int
    skipped: int
    reasons: list[str] = []


class CleanupRequest(BaseModel):
    namespace: str | None = None
    targets: list[Literal["pending", "decisions", "audit"]] = Field(
        default_factory=lambda: ["pending"]
    )
    statuses: list[Literal["pending", "accepted", "rejected", "expired"]] | None = None
    older_than_seconds: int | None = None
    limit: int = 2000
    dry_run: bool = False


class CleanupResponse(BaseModel):
    targets: list[str]
    namespace: str | None
    deleted_pending: int = 0
    deleted_decisions: int = 0
    deleted_audit: int = 0
    scanned: int = 0
    reasons: list[str] = []


class MemoryCard(BaseModel):
    card_type: str
    title: str
    bullets: list[str]
    constraints: list[str] = []
    open_questions: list[str] = []
    do_not_use: list[str] = []


class RenderCardsRequest(BaseModel):
    namespace: str = "default"
    items: list[RetrievedItem]
    profile: Literal["generic", "lexi", "friday"] = "generic"


class RenderCardsResponse(BaseModel):
    cards: list[MemoryCard]


class RehydrateRequest(BaseModel):
    namespace: str = "default"
    query: str
    entity_id: str | None = None
    k: int = 8
    profile: Literal["generic", "lexi", "friday"] = "generic"
    query_embedding: list[float] | None = None
    embedding_model: str | None = None


class RehydrateResponse(BaseModel):
    cards: list[MemoryCard]
    items: list[RetrievedItem]
