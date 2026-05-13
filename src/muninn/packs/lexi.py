from __future__ import annotations

from pydantic import BaseModel

from ..core.specs import AppPack, AppSpec, BundleSpec, BundleStageSpec, MemorySpec


class ProfileFactPayload(BaseModel):
    subject: str
    fact: str
    source: str | None = None


class InteractionPreferencePayload(BaseModel):
    preference: str
    scope: str | None = None


class ProjectPayload(BaseModel):
    name: str
    description: str | None = None


class ProjectStatePayload(BaseModel):
    state: str
    details: str | None = None


class ConstraintPayload(BaseModel):
    constraint: str
    rationale: str | None = None


class CorrectionPayload(BaseModel):
    correction: str
    original: str | None = None


class LexiPack(AppPack):
    def spec(self) -> AppSpec:
        memory_types = {
            "profile_fact": MemorySpec(
                name="profile_fact",
                description="Stable profile fact",
                payload_schema=ProfileFactPayload,
                required_fields=["subject", "fact"],
                identity_keys=["subject", "fact"],
                retrieval_roles=["profile"],
            ),
            "interaction_preference": MemorySpec(
                name="interaction_preference",
                description="Preference for interaction style or constraints",
                payload_schema=InteractionPreferencePayload,
                required_fields=["preference"],
                retrieval_roles=["preference"],
            ),
            "project": MemorySpec(
                name="project",
                description="Project anchor",
                payload_schema=ProjectPayload,
                required_fields=["name"],
                retrieval_roles=["orientation"],
            ),
            "project_state": MemorySpec(
                name="project_state",
                description="Current project status",
                payload_schema=ProjectStatePayload,
                required_fields=["state"],
                retrieval_roles=["status"],
            ),
            "constraint": MemorySpec(
                name="constraint",
                description="Stable constraint",
                payload_schema=ConstraintPayload,
                required_fields=["constraint"],
                retrieval_roles=["constraint"],
                evidence_required=True,
            ),
            "correction": MemorySpec(
                name="correction",
                description="Correction or override",
                payload_schema=CorrectionPayload,
                required_fields=["correction"],
                retrieval_roles=["correction"],
                evidence_required=True,
            ),
        }

        bundle = BundleSpec(
            name="lexi_default",
            description="Staged bundle for Lexi memory",
            stages=[
                BundleStageSpec(
                    name="orientation",
                    description="High-level anchors",
                    kinds=["project", "project_state", "constraint"],
                    limit=4,
                    mode="recent",
                ),
                BundleStageSpec(
                    name="working_context",
                    description="Task-relevant memory",
                    kinds=None,
                    limit=6,
                    mode="search",
                ),
                BundleStageSpec(
                    name="deep_evidence",
                    description="Evidence-backed memory",
                    kinds=None,
                    limit=4,
                    mode="evidence",
                    require_evidence=True,
                ),
            ],
            default_limit=12,
            rehydration_strategy="sdk",
        )

        return AppSpec(
            app_id="lexi",
            name="Lexi",
            description="Lexi memory pack",
            memory_types=memory_types,
            bundles={bundle.name: bundle},
            default_bundle=bundle.name,
        )
