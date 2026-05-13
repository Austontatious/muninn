from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LifecyclePolicy(BaseModel):
    default_state: Literal["active", "pending"] = "active"
    allow_supersede: bool = True
    allow_revoke: bool = True


class ConsolidationPolicy(BaseModel):
    merge_keys: list[str] = Field(default_factory=list)
    allow_merge: bool = True


class RetrievalPolicy(BaseModel):
    roles: list[str] = Field(default_factory=list)
    stage_boosts: dict[str, float] = Field(default_factory=dict)


class ProjectionPolicy(BaseModel):
    include_fields: list[str] | None = None
    summarize_body: bool = False


class MemorySpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    payload_schema: type[BaseModel] | dict[str, Any] | None = None
    required_fields: list[str] = Field(default_factory=list)
    identity_keys: list[str] = Field(default_factory=list)
    retrieval_roles: list[str] = Field(default_factory=list)
    evidence_required: bool = False
    lifecycle_policy: LifecyclePolicy = Field(default_factory=LifecyclePolicy)
    consolidation_policy: ConsolidationPolicy = Field(default_factory=ConsolidationPolicy)
    retrieval_policy: RetrievalPolicy = Field(default_factory=RetrievalPolicy)
    projection_policy: ProjectionPolicy = Field(default_factory=ProjectionPolicy)


class BundleStageSpec(BaseModel):
    name: str
    description: str | None = None
    kinds: list[str] | None = None
    limit: int = 6
    mode: Literal["search", "recent", "evidence"] = "search"
    scope: Literal["strict", "soft"] | None = None
    require_evidence: bool = False


class BundleSpec(BaseModel):
    name: str
    description: str | None = None
    stages: list[BundleStageSpec] = Field(default_factory=list)
    default_limit: int = 12
    rehydration_strategy: Literal["sdk", "legacy_human"] = "sdk"


class AppSpec(BaseModel):
    app_id: str
    name: str
    description: str | None = None
    memory_types: dict[str, MemorySpec] = Field(default_factory=dict)
    bundles: dict[str, BundleSpec] = Field(default_factory=dict)
    default_bundle: str | None = None


class AppPack:
    def spec(self) -> AppSpec:
        raise NotImplementedError
