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
    namespace: str | None = None
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
    namespace: str | None = None
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
    namespace: str | None = None
    entity_id: str | None = None
    status: str = "pending"
    limit: int = 50


class ListPendingResponse(BaseModel):
    items: list[PendingCandidate]


class ConfirmCandidatesRequest(BaseModel):
    namespace: str | None = None
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
    namespace: str | None = None
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
    namespace: str | None = None
    items: list[UpsertEmbeddingsItem]


class UpsertEmbeddingsResponse(BaseModel):
    upserted: int
    rejected: int
    reasons: list[str] = []


class QueryVectorRequest(BaseModel):
    namespace: str | None = None
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
    namespace: str | None = None
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
    namespace: str | None = None
    items: list[RetrievedItem]
    profile: Literal["generic", "lexi", "friday"] = "generic"


class RenderCardsResponse(BaseModel):
    cards: list[MemoryCard]


class RehydrateRequest(BaseModel):
    namespace: str | None = None
    query: str
    entity_id: str | None = None
    k: int = 8
    profile: Literal["generic", "lexi", "friday"] = "generic"
    query_embedding: list[float] | None = None
    embedding_model: str | None = None


class RehydrateResponse(BaseModel):
    cards: list[MemoryCard]
    items: list[RetrievedItem]


class ProcedureRetrieveRequest(BaseModel):
    namespace: str | None = None
    space_key: str = "global"
    task_label: str
    context_summary: str = ""
    task_type: str | None = None
    tool_names: list[str] = Field(default_factory=list)
    limit: int = Field(default=3, ge=1, le=20)


class ProcedureRetrieveResponse(BaseModel):
    procedures: list[dict[str, Any]] = Field(default_factory=list)
    compact: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ProcedureReflectionRequest(BaseModel):
    namespace: str | None = None
    space_key: str = "global"
    task_label: str
    context_summary: str = ""
    actions_taken: list[str] = Field(default_factory=list)
    outcome_status: Literal["success", "partial_success", "failure"] = "partial_success"
    what_worked: str = ""
    what_failed: str = ""
    changed_outcome: str = ""
    reusable: bool = False
    candidate_procedure_id: str | None = None
    task_type: str | None = None
    workflow_type: str | None = None
    tool_requirements: list[str] = Field(default_factory=list)
    verification_checks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = "laila"


class ProcedureReflectionResponse(BaseModel):
    action: str
    procedure_card_id: str | None = None
    outcome_status: str
    confidence: float | None = None
    validation_status: str | None = None
    reason: str | None = None
    evidence_count: int = 0
    warning_codes: list[str] = Field(default_factory=list)
    warnings: list[dict[str, str]] = Field(default_factory=list)


CardType = Literal[
    "contact",
    "recipe",
    "paper",
    "fact",
    "place",
    "media",
    "thread",
    "collection",
    "custom",
]
CardStatus = Literal["active", "archived"]
SourceType = Literal[
    "document",
    "web",
    "note",
    "image",
    "audio",
    "video",
    "file",
    "email",
    "chat",
    "other",
]
RefType = Literal["source", "doc", "chunk", "entity", "external"]
RefRole = Literal["evidence", "primary", "related", "thumbnail", "transcript", "caption"]
ArtifactType = Literal[
    "extracted_text",
    "transcript",
    "caption",
    "ocr",
    "objects",
    "summary",
    "thumbnail",
    "keyframes",
    "embedding_text",
]
ProposalType = Literal["create_card", "update_card", "link_refs", "add_source"]
ProposalStatus = Literal["proposed", "confirmed", "rejected", "expired"]
EmbeddingOwnerType = Literal["card", "source", "chunk"]
EmbeddingModality = Literal["text", "image", "audio", "video"]
EmbeddingStatus = Literal["pending", "ready", "failed"]
EvidenceOwnerType = Literal["artifact", "chunk"]
EvidenceStatus = Literal["captured", "candidate", "promoted"]
PromoteMode = Literal["propose", "trusted"]


class ArtifactInput(BaseModel):
    artifact_type: ArtifactType
    content_text: str | None = None
    content_json: dict[str, Any] | list[Any] | None = None
    generator: str = "stub"


class SourceCreateRequest(BaseModel):
    namespace: str | None = None
    source_type: SourceType
    uri: str
    title: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None
    sensitivity_tier: int = Field(default=0, ge=0, le=3)
    document_text: str | None = None
    chunk_size: int = Field(default=700, ge=200, le=5000)
    chunk_overlap: int = Field(default=80, ge=0, le=1000)
    artifacts: list[ArtifactInput] = Field(default_factory=list)
    requested_by: str | None = None


class SourceRecord(BaseModel):
    source_id: str
    namespace: str
    source_type: str
    uri: str
    title: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None
    sensitivity_tier: int
    created_at: float


class SourceCreateResponse(BaseModel):
    source: SourceRecord
    doc_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)


class SourceArtifactsRequest(BaseModel):
    namespace: str | None = None
    artifacts: list[ArtifactInput]
    requested_by: str | None = None


class SourceArtifactsResponse(BaseModel):
    source_id: str
    artifact_ids: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    namespace: str | None = None
    source_type: SourceType
    title: str | None = None
    uri: str | None = None
    text: str | None = None
    mime_type: str | None = None
    file_path: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    user_tags: list[str] = Field(default_factory=list)
    sensitivity_tier: int = Field(default=0, ge=0, le=3)
    requested_by: str | None = None
    chunk_target_tokens: int = Field(default=450, ge=64, le=4096)
    chunk_overlap_tokens: int = Field(default=80, ge=0, le=1024)
    card_mode: Literal["none", "propose", "trusted"] = "none"
    card_type: CardType | None = None
    card_title: str | None = None
    card_summary: str | None = None


class IngestChunk(BaseModel):
    chunk_id: str
    idx: int
    char_start: int
    char_end: int
    text_hash: str


class IngestResponse(BaseModel):
    source: SourceRecord
    content_hash: str | None = None
    tags: list[str] = Field(default_factory=list)
    doc_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    chunks: list[IngestChunk] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    artifact_types: list[str] = Field(default_factory=list)
    card_id: str | None = None
    proposal_id: str | None = None
    suggested_refs: list[dict[str, Any]] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)


class CardRefInput(BaseModel):
    ref_type: RefType
    ref_id: str
    role: RefRole = "related"
    note: str | None = None


class CardRecord(BaseModel):
    card_id: str
    namespace: str
    type: CardType
    title: str
    summary: str
    details_json: dict[str, Any] = Field(default_factory=dict)
    tags_json: list[str] = Field(default_factory=list)
    created_at: float
    updated_at: float
    salience: float
    confidence: float
    sensitivity_tier: int
    status: CardStatus


class CardCreateRequest(BaseModel):
    namespace: str | None = None
    type: CardType
    title: str
    summary: str
    details_json: dict[str, Any] = Field(default_factory=dict)
    tags_json: list[str] = Field(default_factory=list)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    sensitivity_tier: int = Field(default=0, ge=0, le=3)
    status: CardStatus = "active"
    trusted_mode: bool = False
    requested_by: str | None = None


class CardCreateResponse(BaseModel):
    status: Literal["created", "proposed"]
    card_id: str | None = None
    proposal_id: str | None = None


class LinkCardRefsRequest(BaseModel):
    namespace: str | None = None
    refs: list[CardRefInput]
    requested_by: str | None = None


class LinkCardRefsResponse(BaseModel):
    card_id: str
    linked: int


class RetrieveCardRef(BaseModel):
    ref_type: str
    ref_id: str
    role: str


class RetrievedCard(BaseModel):
    card_id: str
    title: str
    summary: str
    tags: list[str]
    confidence: float
    refs: list[RetrieveCardRef]


class EvidenceRef(BaseModel):
    type: str
    id: str


class EvidenceProvenance(BaseModel):
    doc_title: str | None = None
    uri: str | None = None


class RetrievedEvidence(BaseModel):
    source_id: str | None = None
    ref: EvidenceRef
    snippet: str
    provenance: EvidenceProvenance
    redactions: list[str] = Field(default_factory=list)
    blocked: bool = False
    blocked_reason: str | None = None


class RedactionEvent(BaseModel):
    type: Literal["content_redaction", "tier_block"]
    target_type: Literal["card", "evidence", "artifact", "source", "chunk", "doc"]
    target_id: str
    reason: str
    tier: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CardexRetrieveRequest(BaseModel):
    namespace: str | None = None
    query: str
    purpose: str = "assistant_answer"
    scope: list[Literal["cards", "evidence"]] = Field(
        default_factory=lambda: ["cards"]
    )
    modalities: list[EmbeddingModality] = Field(
        default_factory=lambda: ["text", "image", "audio", "video"]
    )
    sensitivity_ceiling: int = Field(default=3, ge=0, le=3)
    k_cards: int = Field(default=20, ge=1, le=100)
    k_evidence: int = Field(default=8, ge=1, le=100)


class CardexRetrieveResponse(BaseModel):
    cards: list[RetrievedCard]
    evidence: list[RetrievedEvidence]
    audit_id: str
    redactions: list[RedactionEvent] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)


class PromoteRequest(BaseModel):
    namespace: str | None = None
    owner_type: EvidenceOwnerType
    owner_id: str
    mode: PromoteMode = "propose"
    card_type: CardType = "fact"
    card_title: str | None = None
    card_summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    refs: list[CardRefInput] | None = None
    requested_by: str | None = None


class PromoteResponse(BaseModel):
    status: Literal["proposed", "promoted", "noop"]
    proposal_id: str | None = None
    card_id: str | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class ProposalRecord(BaseModel):
    proposal_id: str
    namespace: str
    proposal_type: ProposalType
    payload_json: dict[str, Any]
    status: ProposalStatus
    created_at: float
    decided_at: float | None = None
    requested_by: str | None = None
    decided_by: str | None = None
    reason: str | None = None


class ProposeRequest(BaseModel):
    namespace: str | None = None
    proposal_type: ProposalType
    payload_json: dict[str, Any]
    requested_by: str | None = None
    reason: str | None = None
    trusted_mode: bool = False


class ProposeResponse(BaseModel):
    proposal: ProposalRecord
    applied: dict[str, Any] | None = None


class DecideProposalRequest(BaseModel):
    namespace: str | None = None
    decided_by: str
    reason: str | None = None


class DecideProposalResponse(BaseModel):
    proposal: ProposalRecord
    applied: dict[str, Any] | None = None


class CardEmbeddingUpsertRequest(BaseModel):
    namespace: str | None = None
    owner_type: EmbeddingOwnerType
    owner_id: str
    modality: EmbeddingModality
    model: str
    dims: int = Field(ge=1)
    vector: list[float] | None = None
    content_hash: str | None = None
    embed_status: EmbeddingStatus = "pending"
    embed_error: str | None = None
    requested_by: str | None = None


class CardEmbeddingUpsertResponse(BaseModel):
    embedding_id: str
    embed_status: EmbeddingStatus
