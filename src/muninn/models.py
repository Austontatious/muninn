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


class RetrieveRequest(BaseModel):
    namespace: str = "default"
    query: str
    entity_id: str | None = None
    k: int = 8


class RetrievedItem(BaseModel):
    kind: Literal["fact", "episode", "preference"]
    id: str
    entity_id: str
    text: str
    confidence: float
    provenance: Provenance


class RetrieveResponse(BaseModel):
    items: list[RetrievedItem]


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


class RehydrateResponse(BaseModel):
    cards: list[MemoryCard]
    items: list[RetrievedItem]
