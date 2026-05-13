from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceType = Literal[
    "file",
    "diff",
    "commit",
    "test",
    "log",
    "url",
    "chat",
    "artifact",
    "other",
]


class EvidenceRef(BaseModel):
    type: EvidenceType
    ref: str | None = None
    excerpt: str | None = None
    meta: dict[str, Any] | None = None


class ProvenanceEnvelope(BaseModel):
    source_type: Literal[
        "user",
        "assistant",
        "tool",
        "document",
        "system",
        "imported",
        "unknown",
    ] = "unknown"
    source_id: str | None = None
    note: str | None = None
    captured_at: float | None = None


class TrustEnvelope(BaseModel):
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    validated: bool = False
    signal: str | None = None


class LifecycleState(BaseModel):
    state: Literal["active", "superseded", "revoked", "pending"] = "active"
    created_at: float | None = None
    updated_at: float | None = None
    supersedes: str | None = None
    revoked_reason: str | None = None


class MemoryEvent(BaseModel):
    event_type: str
    actor: str
    summary: str
    payload: dict[str, Any] | None = None
    signal_type: str | None = None
    outcome_type: str | None = None
    scope_type: str = "project"
    scope_key: str | None = None
    session_id: str | None = None


class MemoryItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str | None = None
    app_id: str
    kind: str
    title: str
    summary: str
    body: str = ""
    payload: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    provenance: ProvenanceEnvelope | None = None
    trust: TrustEnvelope | None = None
    lifecycle: LifecycleState | None = None
    space_key: str | None = None
    metadata: dict[str, Any] | None = None


class BundleStageDecision(BaseModel):
    stage: str
    attempted: bool
    results: int
    suppressed: int = 0
    reason: str | None = None


class BundleStageResult(BaseModel):
    stage: str
    items: list[MemoryItem]
    decision: BundleStageDecision


class BundleExplanation(BaseModel):
    bundle_name: str
    space_key: str
    scope: str
    decisions: list[BundleStageDecision]
    suppressed_total: int = 0
    notes: list[str] = Field(default_factory=list)


class BundleResult(BaseModel):
    bundle_name: str
    stages: list[BundleStageResult]
    explanation: BundleExplanation
