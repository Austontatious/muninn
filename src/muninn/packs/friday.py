from __future__ import annotations

from pydantic import BaseModel

from ..core.specs import AppPack, AppSpec, BundleSpec, BundleStageSpec, MemorySpec


class TaskOutcomePayload(BaseModel):
    outcome: str
    success: bool = True
    summary: str | None = None


class ProcedureLessonPayload(BaseModel):
    lesson: str
    trigger: str | None = None


class ToolPreferencePayload(BaseModel):
    tool: str
    preference: str


class ConstraintPayload(BaseModel):
    constraint: str
    rationale: str | None = None


class FridayPack(AppPack):
    def spec(self) -> AppSpec:
        memory_types = {
            "task_outcome": MemorySpec(
                name="task_outcome",
                description="Outcome from a completed task",
                payload_schema=TaskOutcomePayload,
                required_fields=["outcome"],
                retrieval_roles=["outcome"],
                evidence_required=True,
            ),
            "procedure_lesson": MemorySpec(
                name="procedure_lesson",
                description="Reusable lesson from a procedure",
                payload_schema=ProcedureLessonPayload,
                required_fields=["lesson"],
                retrieval_roles=["procedure"],
                evidence_required=True,
            ),
            "tool_preference": MemorySpec(
                name="tool_preference",
                description="Preferred tooling or approach",
                payload_schema=ToolPreferencePayload,
                required_fields=["tool", "preference"],
                retrieval_roles=["preference"],
            ),
            "constraint": MemorySpec(
                name="constraint",
                description="Operational constraint",
                payload_schema=ConstraintPayload,
                required_fields=["constraint"],
                retrieval_roles=["constraint"],
                evidence_required=True,
            ),
        }

        bundle = BundleSpec(
            name="friday_default",
            description="Staged bundle for Friday memory",
            stages=[
                BundleStageSpec(
                    name="orientation",
                    description="Recent outcomes and constraints",
                    kinds=["task_outcome", "constraint"],
                    limit=4,
                    mode="recent",
                ),
                BundleStageSpec(
                    name="working_context",
                    description="Relevant procedures and preferences",
                    kinds=None,
                    limit=6,
                    mode="search",
                ),
                BundleStageSpec(
                    name="deep_evidence",
                    description="Evidence-backed guidance",
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
            app_id="friday",
            name="Friday",
            description="Friday memory pack",
            memory_types=memory_types,
            bundles={bundle.name: bundle},
            default_bundle=bundle.name,
        )
