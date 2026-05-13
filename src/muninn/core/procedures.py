from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..human_memory import procedures as human_procedures
from .config import MuninnConfig
from .contracts import BundleStageDecision, EvidenceRef
from .storage import HumanMemoryStore

ProcedureStatus = Literal["active", "deprecated", "superseded", "pending"]
ProcedureValidationStatus = Literal["candidate", "validated", "needs_review", "deprecated"]
ProcedureStageDepth = Literal["orientation", "working_context", "deep_evidence"]
ProcedureProjectionKind = Literal[
    "compact",
    "steps",
    "troubleshooting",
    "recovery",
    "validation",
    "deep",
]


class ProcedureScope(BaseModel):
    type: str = "global"
    id: str | None = None


class ProcedureSpec(BaseModel):
    procedure_name: str
    intent_tags: list[str] = Field(default_factory=list)
    scope: ProcedureScope | dict[str, Any] | str | None = None
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    supersedes: str | None = None
    status: ProcedureStatus = "active"
    validation_status: ProcedureValidationStatus = "candidate"
    task_types: list[str] = Field(default_factory=list)
    retrieval_roles: list[str] = Field(default_factory=list)
    tool_requirements: list[str] = Field(default_factory=list)
    verification_checks: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    body: str | None = None


class ProcedureRecord(BaseModel):
    id: str
    title: str
    summary: str
    when_to_apply: list[str] = Field(default_factory=list)
    intent_tags: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    tool_requirements: list[str] = Field(default_factory=list)
    pitfalls: list[str] = Field(default_factory=list)
    verification_checks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    validation_status: str = "candidate"
    status: str | None = None
    task_types: list[str] = Field(default_factory=list)
    retrieval_roles: list[str] = Field(default_factory=list)
    updated_at: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    failure_count: int = 0
    evidence_count: int = 0
    has_evidence: bool = False
    selection_reasons: list[str] = Field(default_factory=list)
    score: float = 0.0
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ProcedureBundleStage(BaseModel):
    stage: str
    procedures: list[dict[str, Any]]
    decision: BundleStageDecision


class ProcedureBundleExplanation(BaseModel):
    stage_depth: ProcedureStageDepth
    decisions: list[BundleStageDecision]
    suppressed_total: int = 0
    notes: list[str] = Field(default_factory=list)


class ProcedureBundleResult(BaseModel):
    stages: list[ProcedureBundleStage]
    explanation: ProcedureBundleExplanation


class ProcedureQueryResult(BaseModel):
    procedures: list[ProcedureRecord]
    compact: list[dict[str, Any]]
    diagnostics: dict[str, Any]


class ProcedureReflection(BaseModel):
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


class ProcedureReflectionResult(BaseModel):
    action: str
    procedure_card_id: str | None = None
    outcome_status: str
    confidence: float | None = None
    validation_status: str | None = None
    reason: str | None = None
    evidence_count: int = 0
    warning_codes: list[str] = Field(default_factory=list)
    warnings: list[dict[str, str]] = Field(default_factory=list)


def _summary_from_spec(spec: ProcedureSpec) -> str:
    if spec.summary and spec.summary.strip():
        return spec.summary.strip()
    if spec.expected_outcomes:
        return "; ".join([item.strip() for item in spec.expected_outcomes if item.strip()])[:280]
    if spec.steps:
        return "; ".join([item.strip() for item in spec.steps[:2] if item.strip()])
    return spec.procedure_name.strip()


def _body_from_spec(spec: ProcedureSpec) -> str:
    if spec.body and spec.body.strip():
        return spec.body.strip()
    if spec.steps:
        return "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(spec.steps))
    return ""


def _ensure_scope_dict(scope: ProcedureScope | dict[str, Any] | str | None) -> dict[str, Any] | str | None:
    if isinstance(scope, ProcedureScope):
        return scope.model_dump()
    return scope


def _normalize_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _coerce_status(spec: ProcedureSpec) -> str:
    if spec.status == "pending":
        return "active"
    if spec.status in {"deprecated", "superseded"}:
        return "active"
    return "active"


def _coerce_validation(spec: ProcedureSpec) -> str:
    if spec.validation_status:
        return spec.validation_status
    if spec.status in {"deprecated", "superseded"}:
        return "deprecated"
    return "candidate"


def _spec_to_upsert_kwargs(spec: ProcedureSpec) -> dict[str, Any]:
    summary = _summary_from_spec(spec)
    return {
        "title": spec.procedure_name.strip(),
        "summary": summary,
        "trigger_conditions": _normalize_list(spec.intent_tags + spec.preconditions),
        "intent_tags": _normalize_list(spec.intent_tags),
        "preconditions": _normalize_list(spec.preconditions),
        "scope": _ensure_scope_dict(spec.scope),
        "steps": _normalize_list(spec.steps),
        "expected_outcomes": _normalize_list(spec.expected_outcomes),
        "failure_modes": _normalize_list(spec.failure_modes),
        "fallbacks": _normalize_list(spec.fallbacks),
        "when_not_to_use": _normalize_list(spec.when_not_to_use),
        "tool_requirements": _normalize_list(spec.tool_requirements),
        "pitfalls": _normalize_list(spec.failure_modes + spec.when_not_to_use),
        "verification_checks": _normalize_list(spec.verification_checks),
        "confidence": spec.confidence,
        "validation_status": _coerce_validation(spec),
        "task_types": _normalize_list(spec.task_types),
        "retrieval_roles": _normalize_list(spec.retrieval_roles),
        "provenance": dict(spec.provenance),
        "supersedes_card_id": spec.supersedes,
        "status": _coerce_status(spec),
        "body": _body_from_spec(spec),
        "evidence_refs": [ref.model_dump() for ref in spec.evidence_refs] or None,
    }


def _fetch_evidence_refs(conn, card_ids: list[str]) -> dict[str, list[EvidenceRef]]:
    if not card_ids:
        return {}
    placeholders = ",".join("?" for _ in card_ids)
    rows = conn.execute(
        f"""
        SELECT ce.card_id, e.type, e.ref, e.excerpt, e.meta_json
        FROM card_evidence ce
        JOIN evidence e ON e.id = ce.evidence_id
        WHERE ce.card_id IN ({placeholders})
        """,
        card_ids,
    ).fetchall()
    grouped: dict[str, list[EvidenceRef]] = {}
    for row in rows:
        card_id = str(row[0])
        meta_json = row[4]
        meta = None
        if isinstance(meta_json, str) and meta_json.strip():
            try:
                meta = json.loads(meta_json)
            except json.JSONDecodeError:
                meta = None
        grouped.setdefault(card_id, []).append(
            EvidenceRef(
                type=str(row[1]),
                ref=str(row[2]) if row[2] is not None else None,
                excerpt=str(row[3]) if row[3] is not None else None,
                meta=meta,
            )
        )
    return grouped


def _to_record(raw: dict[str, Any], evidence_refs: list[EvidenceRef] | None = None) -> ProcedureRecord:
    return ProcedureRecord(
        id=str(raw.get("id")),
        title=str(raw.get("title") or ""),
        summary=str(raw.get("summary") or ""),
        when_to_apply=list(raw.get("when_to_apply") or []),
        intent_tags=list(raw.get("intent_tags") or []),
        preconditions=list(raw.get("preconditions") or []),
        scope=dict(raw.get("scope") or {}),
        steps=list(raw.get("steps") or []),
        expected_outcomes=list(raw.get("expected_outcomes") or []),
        failure_modes=list(raw.get("failure_modes") or []),
        fallbacks=list(raw.get("fallbacks") or []),
        when_not_to_use=list(raw.get("when_not_to_use") or []),
        tool_requirements=list(raw.get("tool_requirements") or []),
        pitfalls=list(raw.get("pitfalls") or []),
        verification_checks=list(raw.get("verification_checks") or []),
        confidence=float(raw.get("confidence") or 0.0),
        validation_status=str(raw.get("validation_status") or "candidate"),
        status=str(raw.get("status")) if raw.get("status") is not None else None,
        task_types=list(raw.get("task_types") or []),
        retrieval_roles=list(raw.get("retrieval_roles") or []),
        updated_at=str(raw.get("updated_at")) if raw.get("updated_at") is not None else None,
        provenance=dict(raw.get("provenance") or {}),
        failure_count=int(raw.get("failure_count") or 0),
        evidence_count=int(raw.get("evidence_count") or 0),
        has_evidence=bool(raw.get("has_evidence")),
        selection_reasons=list(raw.get("selection_reasons") or []),
        score=float(raw.get("score") or 0.0),
        evidence_refs=evidence_refs or [],
    )


def render_procedure(procedure: ProcedureRecord, projection: ProcedureProjectionKind) -> dict[str, Any]:
    base = {
        "id": procedure.id,
        "title": procedure.title,
        "summary": procedure.summary,
        "confidence": procedure.confidence,
        "validation_status": procedure.validation_status,
    }
    if projection == "compact":
        base.update(
            {
                "when_to_apply": procedure.when_to_apply[:3],
                "steps": procedure.steps[:5],
                "pitfalls": procedure.pitfalls[:3],
                "selection_reasons": procedure.selection_reasons,
                "score": procedure.score,
                "evidence_count": procedure.evidence_count,
            }
        )
        return base
    if projection == "steps":
        base.update(
            {
                "preconditions": procedure.preconditions,
                "steps": procedure.steps,
                "expected_outcomes": procedure.expected_outcomes,
                "verification_checks": procedure.verification_checks,
                "tool_requirements": procedure.tool_requirements,
            }
        )
        return base
    if projection == "troubleshooting":
        base.update(
            {
                "failure_modes": procedure.failure_modes,
                "pitfalls": procedure.pitfalls,
                "fallbacks": procedure.fallbacks,
                "when_not_to_use": procedure.when_not_to_use,
                "verification_checks": procedure.verification_checks,
            }
        )
        return base
    if projection == "recovery":
        base.update(
            {
                "fallbacks": procedure.fallbacks,
                "steps": procedure.steps,
                "failure_modes": procedure.failure_modes,
                "when_not_to_use": procedure.when_not_to_use,
            }
        )
        return base
    if projection == "validation":
        base.update(
            {
                "verification_checks": procedure.verification_checks,
                "expected_outcomes": procedure.expected_outcomes,
                "steps": procedure.steps,
            }
        )
        return base
    base.update(
        {
            "steps": procedure.steps,
            "expected_outcomes": procedure.expected_outcomes,
            "failure_modes": procedure.failure_modes,
            "fallbacks": procedure.fallbacks,
            "when_not_to_use": procedure.when_not_to_use,
            "provenance": procedure.provenance,
            "evidence": [ref.model_dump() for ref in procedure.evidence_refs],
        }
    )
    return base


class ProcedureStore:
    def __init__(self, store: HumanMemoryStore, config: MuninnConfig | None = None) -> None:
        self._store = store
        self._config = config or MuninnConfig()

    def _resolve_space(self, conn, *, space_key: str | None, cwd: str | None) -> str:
        return self._store.ensure_space_key(
            conn,
            space_key=space_key or self._config.space_key,
            cwd=cwd or self._config.cwd,
        )

    def write(self, spec: ProcedureSpec, *, space_key: str | None = None, cwd: str | None = None) -> str:
        with self._store.connect() as conn:
            resolved_space = self._resolve_space(conn, space_key=space_key, cwd=cwd)
            return human_procedures.procedure_card_upsert(
                conn,
                user_id=self._store.user_id,
                space_key=resolved_space,
                **_spec_to_upsert_kwargs(spec),
            )

    def supersede(self, *, supersedes_card_id: str, spec: ProcedureSpec, space_key: str | None = None, cwd: str | None = None) -> str:
        with self._store.connect() as conn:
            resolved_space = self._resolve_space(conn, space_key=space_key, cwd=cwd)
            payload = _spec_to_upsert_kwargs(spec)
            payload["supersedes_card_id"] = supersedes_card_id
            return human_procedures.procedure_card_upsert(
                conn,
                user_id=self._store.user_id,
                space_key=resolved_space,
                **payload,
            )

    def query(
        self,
        *,
        space_key: str | None,
        task_label: str,
        context_summary: str = "",
        task_type: str | None = None,
        tool_names: list[str] | None = None,
        limit: int = 3,
        include_evidence: bool = False,
        cwd: str | None = None,
        conn=None,
    ) -> ProcedureQueryResult:
        if conn is None:
            with self._store.connect() as conn:
                return self.query(
                    space_key=space_key,
                    task_label=task_label,
                    context_summary=context_summary,
                    task_type=task_type,
                    tool_names=tool_names,
                    limit=limit,
                    include_evidence=include_evidence,
                    cwd=cwd,
                    conn=conn,
                )
        resolved_space = self._resolve_space(conn, space_key=space_key, cwd=cwd)
        payload = human_procedures.query_procedure_cards(
            conn,
            user_id=self._store.user_id,
            space_key=resolved_space,
            task_label=task_label,
            context_summary=context_summary,
            task_type=task_type,
            tool_names=tool_names or [],
            limit=limit,
        )
        procedures = list(payload.get("procedures") or [])
        evidence_by_id: dict[str, list[EvidenceRef]] = {}
        if include_evidence:
            evidence_by_id = _fetch_evidence_refs(conn, [str(item.get("id")) for item in procedures])
        records = [
            _to_record(item, evidence_by_id.get(str(item.get("id"))))
            for item in procedures
        ]
        return ProcedureQueryResult(
            procedures=records,
            compact=list(payload.get("compact") or []),
            diagnostics=dict(payload.get("diagnostics") or {}),
        )

    def rehydrate_bundle(
        self,
        *,
        space_key: str | None,
        task_label: str,
        context_summary: str = "",
        task_type: str | None = None,
        tool_names: list[str] | None = None,
        limit: int = 3,
        stage_depth: ProcedureStageDepth = "working_context",
        cwd: str | None = None,
        conn=None,
    ) -> ProcedureBundleResult:
        query_result = self.query(
            space_key=space_key,
            task_label=task_label,
            context_summary=context_summary,
            task_type=task_type,
            tool_names=tool_names,
            limit=limit,
            include_evidence=stage_depth == "deep_evidence",
            cwd=cwd,
            conn=conn,
        )
        diagnostics = query_result.diagnostics
        procedures = query_result.procedures

        stages: list[ProcedureBundleStage] = []
        decisions: list[BundleStageDecision] = []
        suppressed = int(diagnostics.get("skipped") or 0) + int(diagnostics.get("filtered_low_confidence") or 0)

        orientation_items = [render_procedure(proc, "compact") for proc in procedures]
        decisions.append(
            BundleStageDecision(
                stage="orientation",
                attempted=True,
                results=len(orientation_items),
                suppressed=suppressed,
                reason=None if orientation_items else "no_matching_procedures",
            )
        )
        stages.append(
            ProcedureBundleStage(
                stage="orientation",
                procedures=orientation_items,
                decision=decisions[-1],
            )
        )

        if stage_depth in {"working_context", "deep_evidence"}:
            working_items = [render_procedure(proc, "steps") for proc in procedures]
            decisions.append(
                BundleStageDecision(
                    stage="working_context",
                    attempted=True,
                    results=len(working_items),
                    suppressed=suppressed,
                    reason=None if working_items else "no_matching_procedures",
                )
            )
            stages.append(
                ProcedureBundleStage(
                    stage="working_context",
                    procedures=working_items,
                    decision=decisions[-1],
                )
            )
        else:
            decisions.append(
                BundleStageDecision(
                    stage="working_context",
                    attempted=False,
                    results=0,
                    suppressed=0,
                    reason="stage_depth_orientation",
                )
            )

        if stage_depth == "deep_evidence":
            deep_items = [render_procedure(proc, "deep") for proc in procedures]
            decisions.append(
                BundleStageDecision(
                    stage="deep_evidence",
                    attempted=True,
                    results=len(deep_items),
                    suppressed=0,
                    reason=None if deep_items else "no_matching_procedures",
                )
            )
            stages.append(
                ProcedureBundleStage(
                    stage="deep_evidence",
                    procedures=deep_items,
                    decision=decisions[-1],
                )
            )
        else:
            decisions.append(
                BundleStageDecision(
                    stage="deep_evidence",
                    attempted=False,
                    results=0,
                    suppressed=0,
                    reason="stage_depth_limit",
                )
            )

        explanation = ProcedureBundleExplanation(
            stage_depth=stage_depth,
            decisions=decisions,
            suppressed_total=suppressed,
            notes=["deep_evidence_not_requested"] if stage_depth != "deep_evidence" else [],
        )
        return ProcedureBundleResult(stages=stages, explanation=explanation)

    def explain_bundle(self, **kwargs: Any) -> dict[str, Any]:
        bundle = self.rehydrate_bundle(**kwargs)
        return bundle.explanation.model_dump()

    def reflect(
        self,
        *,
        reflection: ProcedureReflection,
        space_key: str | None = None,
        cwd: str | None = None,
        conn=None,
    ) -> ProcedureReflectionResult:
        if conn is None:
            with self._store.connect() as conn:
                return self.reflect(reflection=reflection, space_key=space_key, cwd=cwd, conn=conn)
        resolved_space = self._resolve_space(conn, space_key=space_key, cwd=cwd)
        payload = human_procedures.ingest_procedure_reflection(
            conn,
            user_id=self._store.user_id,
            space_key=resolved_space,
            reflection=reflection.model_dump(exclude={"actor"}),
            actor=reflection.actor,
        )
        return ProcedureReflectionResult(**payload)
