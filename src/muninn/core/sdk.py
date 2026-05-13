from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from .bundle import build_bundle
from .config import MuninnConfig
from .contracts import (
    BundleExplanation,
    BundleResult,
    BundleStageDecision,
    BundleStageResult,
    MemoryEvent,
    MemoryItem,
)
from .procedures import (
    ProcedureBundleResult,
    ProcedureQueryResult,
    ProcedureReflection,
    ProcedureReflectionResult,
    ProcedureSpec,
    ProcedureStore,
)
from .registry import AppRegistry
from .specs import AppPack, BundleSpec, MemorySpec
from .storage import HumanMemoryStore


class Muninn:
    def __init__(
        self,
        *,
        app_pack: AppPack,
        config: MuninnConfig | None = None,
    ) -> None:
        self._config = config or MuninnConfig()
        self._registry = AppRegistry()
        self._app_spec = app_pack.spec()
        self._registry.register_app(self._app_spec)
        self._store = HumanMemoryStore(self._config)
        self._procedure_store = ProcedureStore(self._store, self._config)

    def register_app(self, app_spec) -> None:
        self._registry.register_app(app_spec)

    def register_memory_type(self, app_id: str, memory_spec: MemorySpec) -> None:
        app = self._registry.get_app(app_id)
        if memory_spec.name in app.memory_types:
            raise ValueError(f"memory_type_already_registered:{app_id}:{memory_spec.name}")
        app.memory_types[memory_spec.name] = memory_spec

    def register_bundle(self, app_id: str, bundle_spec: BundleSpec) -> None:
        app = self._registry.get_app(app_id)
        if bundle_spec.name in app.bundles:
            raise ValueError(f"bundle_already_registered:{app_id}:{bundle_spec.name}")
        app.bundles[bundle_spec.name] = bundle_spec

    def write(self, item: MemoryItem) -> str:
        if item.app_id != self._app_spec.app_id:
            raise ValueError("app_id_mismatch")
        memory_spec = self._registry.get_memory_spec(self._app_spec.app_id, item.kind)
        if memory_spec.evidence_required and not item.evidence:
            raise ValueError("evidence_required")
        payload_json = item.payload or {}
        if memory_spec.required_fields:
            missing = [field for field in memory_spec.required_fields if field not in payload_json]
            if missing:
                raise ValueError(f"payload_missing_fields:{','.join(missing)}")
        schema = memory_spec.payload_schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                schema.model_validate(payload_json)
            except ValidationError as exc:
                raise ValueError("payload_invalid") from exc
        context_json = {
            "app_id": self._app_spec.app_id,
            "memory_type": item.kind,
            "app_payload": payload_json,
        }
        evidence_refs = [ref.model_dump() for ref in item.evidence]
        with self._store.connect() as conn:
            space_key = self._store.ensure_space_key(
                conn, space_key=item.space_key or self._config.space_key, cwd=self._config.cwd
            )
            return self._store.upsert_card(
                conn,
                space_key=space_key,
                kind=item.kind,
                title=item.title,
                summary=item.summary,
                body=item.body,
                tags=item.tags,
                context_json=context_json,
                evidence_refs=evidence_refs or None,
            )

    def attach_evidence(self, *, card_id: str, evidence: list[dict[str, Any]]) -> str:
        with self._store.connect() as conn:
            existing = self._store.fetch_card(conn, card_id=card_id)
            if existing is None:
                raise ValueError(f"card_not_found:{card_id}")
            context = existing.get("context_json") or {}
            return self._store.upsert_card(
                conn,
                space_key=str(existing.get("space_key")),
                kind=str(existing.get("kind")),
                title=str(existing.get("title") or ""),
                summary=str(existing.get("summary") or ""),
                body=str(existing.get("body") or ""),
                tags=None,
                context_json=context if isinstance(context, dict) else None,
                evidence_refs=evidence,
            )

    def record_event(self, event: MemoryEvent) -> str:
        with self._store.connect() as conn:
            space_key = self._store.ensure_space_key(
                conn, space_key=self._config.space_key, cwd=self._config.cwd
            )
            return self._store.record_event(conn, space_key=space_key, event=event.model_dump())

    def query(self, *, query: str, kinds: list[str] | None = None, limit: int = 12) -> list[MemoryItem]:
        with self._store.connect() as conn:
            space_key = self._store.ensure_space_key(
                conn, space_key=self._config.space_key, cwd=self._config.cwd
            )
            rows = self._store.search_cards(
                conn,
                space_key=space_key,
                query=query,
                kinds=kinds,
                limit=limit,
                include_body=True,
            )
        items: list[MemoryItem] = []
        for row in rows:
            context_json = row.get("context_json")
            payload = None
            if isinstance(context_json, str) and context_json.strip():
                try:
                    context_json = json.loads(context_json)
                except json.JSONDecodeError:
                    context_json = None
            if isinstance(context_json, dict):
                stored_app_id = context_json.get("app_id")
                if stored_app_id and stored_app_id != self._app_spec.app_id:
                    continue
                payload = context_json.get("app_payload")
            items.append(
                MemoryItem(
                    id=str(row.get("id")),
                    app_id=self._app_spec.app_id,
                    kind=str(row.get("kind")),
                    title=str(row.get("title") or ""),
                    summary=str(row.get("summary") or ""),
                    body=str(row.get("body") or "") if row.get("body") else "",
                    payload=payload,
                    tags=list(row.get("tags") or []),
                    space_key=str(row.get("space_key") or ""),
                    metadata={"score": row.get("score")},
                )
            )
        return items

    def retrieve_candidates(self, *, query: str, kinds: list[str] | None = None, limit: int = 12) -> list[MemoryItem]:
        return self.query(query=query, kinds=kinds, limit=limit)

    def rehydrate_bundle(
        self,
        *,
        query: str,
        bundle_name: str | None = None,
        scope: str | None = None,
        include_body: bool = False,
    ) -> BundleResult:
        bundle_spec = self._registry.get_bundle_spec(self._app_spec.app_id, bundle_name)
        scope_value = scope or self._config.scope

        with self._store.connect() as conn:
            space_key = self._store.ensure_space_key(
                conn, space_key=self._config.space_key, cwd=self._config.cwd
            )
            available_kinds = list(self._app_spec.memory_types.keys())
            if bundle_spec.rehydration_strategy == "legacy_human":
                legacy = self._store.rehydrate_legacy_bundle(
                    conn,
                    space_key=space_key,
                    query=query,
                    kinds=available_kinds,
                    limit=bundle_spec.default_limit,
                    scope=scope_value,
                    include_body=include_body,
                    include_policy=True,
                    tool_name="sdk",
                    task_type=None,
                )
                return _legacy_to_bundle_result(bundle_spec, legacy)
            return build_bundle(
                self._store,
                conn,
                app_id=self._app_spec.app_id,
                space_key=space_key,
                scope=scope_value,
                query=query,
                bundle_spec=bundle_spec,
                available_kinds=available_kinds,
                include_body=include_body,
            )

    def explain_bundle(self, *, query: str, bundle_name: str | None = None) -> dict[str, Any]:
        bundle = self.rehydrate_bundle(query=query, bundle_name=bundle_name)
        return bundle.explanation.model_dump()

    def supersede(self, *, old_card_id: str, item: MemoryItem) -> dict[str, Any]:
        with self._store.connect() as conn:
            space_key = self._store.ensure_space_key(
                conn, space_key=item.space_key or self._config.space_key, cwd=self._config.cwd
            )
            return self._store.supersede_card(
                conn,
                space_key=space_key,
                old_card_id=old_card_id,
                kind=item.kind,
                title=item.title,
                summary=item.summary,
                body=item.body,
                tags=item.tags,
                context_json={
                    "app_id": self._app_spec.app_id,
                    "memory_type": item.kind,
                    "app_payload": item.payload or {},
                },
                evidence_refs=[ref.model_dump() for ref in item.evidence] or None,
            )

    def revoke(self, *, card_id: str) -> None:
        with self._store.connect() as conn:
            self._store.revoke_card(conn, card_id=card_id)

    def write_procedure(self, spec: ProcedureSpec) -> str:
        return self._procedure_store.write(spec)

    def supersede_procedure(self, *, supersedes_card_id: str, spec: ProcedureSpec) -> str:
        return self._procedure_store.supersede(supersedes_card_id=supersedes_card_id, spec=spec)

    def query_procedures(
        self,
        *,
        task_label: str,
        context_summary: str = "",
        task_type: str | None = None,
        tool_names: list[str] | None = None,
        limit: int = 3,
        include_evidence: bool = False,
    ) -> ProcedureQueryResult:
        return self._procedure_store.query(
            space_key=self._config.space_key,
            task_label=task_label,
            context_summary=context_summary,
            task_type=task_type,
            tool_names=tool_names,
            limit=limit,
            include_evidence=include_evidence,
            cwd=self._config.cwd,
        )

    def rehydrate_procedure_bundle(
        self,
        *,
        task_label: str,
        context_summary: str = "",
        task_type: str | None = None,
        tool_names: list[str] | None = None,
        limit: int = 3,
        stage_depth: str = "working_context",
    ) -> ProcedureBundleResult:
        return self._procedure_store.rehydrate_bundle(
            space_key=self._config.space_key,
            task_label=task_label,
            context_summary=context_summary,
            task_type=task_type,
            tool_names=tool_names,
            limit=limit,
            stage_depth=stage_depth,  # type: ignore[arg-type]
            cwd=self._config.cwd,
        )

    def explain_procedure_bundle(self, **kwargs: Any) -> dict[str, Any]:
        return self._procedure_store.explain_bundle(
            space_key=self._config.space_key,
            cwd=self._config.cwd,
            **kwargs,
        )

    def reflect_procedure(self, reflection: ProcedureReflection) -> ProcedureReflectionResult:
        return self._procedure_store.reflect(
            reflection=reflection,
            space_key=self._config.space_key,
            cwd=self._config.cwd,
        )


def _legacy_to_bundle_result(bundle_spec: BundleSpec, legacy: dict[str, Any]) -> BundleResult:
    stages: list[Any] = []
    decisions: list[Any] = []
    suppressed_total = 0
    for stage in legacy.get("stages", []):
        decision = stage.get("decision", {})
        decision_obj = BundleStageDecision(
            stage=str(stage.get("stage") or ""),
            attempted=bool(decision.get("attempted", True)),
            results=int(decision.get("results", 0)),
            suppressed=int(decision.get("suppressed", 0)),
            reason=decision.get("reason"),
        )
        suppressed_total += decision_obj.suppressed
        decisions.append(decision_obj)
        items = []
        for raw in stage.get("items", []):
            items.append(
                MemoryItem(
                    id=str(raw.get("id")),
                    app_id="legacy",
                    kind=str(raw.get("kind")),
                    title=str(raw.get("title") or ""),
                    summary=str(raw.get("summary") or ""),
                    body=str(raw.get("body") or "") if raw.get("body") else "",
                    payload=None,
                    tags=list(raw.get("tags") or []),
                    evidence=[],
                    space_key=str(raw.get("space_key") or ""),
                    metadata=raw,
                )
            )
        stages.append(
            BundleStageResult(
                stage=str(stage.get("stage") or ""),
                items=items,
                decision=decision_obj,
            )
        )
    explanation = BundleExplanation(
        bundle_name=legacy.get("bundle_name", bundle_spec.name),
        space_key=legacy.get("space_key", ""),
        scope=legacy.get("scope", "strict"),
        decisions=decisions,
        suppressed_total=suppressed_total,
        notes=["legacy_bundle"],
    )
    return BundleResult(
        bundle_name=legacy.get("bundle_name", bundle_spec.name),
        stages=stages,
        explanation=explanation,
    )
