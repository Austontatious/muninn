from __future__ import annotations

import json
from typing import Any

from .contracts import (
    BundleExplanation,
    BundleResult,
    BundleStageDecision,
    BundleStageResult,
    MemoryItem,
)
from .specs import BundleSpec
from .storage import HumanMemoryStore


def _card_to_item(card: dict[str, Any], *, app_id: str) -> MemoryItem | None:
    context_json = card.get("context_json")
    if isinstance(context_json, str) and context_json.strip():
        try:
            context_json = json.loads(context_json)
        except json.JSONDecodeError:
            context_json = None
    payload = None
    if isinstance(context_json, dict):
        stored_app_id = context_json.get("app_id")
        if stored_app_id and stored_app_id != app_id:
            return None
        payload = context_json.get("app_payload")
    return MemoryItem(
        id=str(card.get("id")),
        app_id=app_id,
        kind=str(card.get("kind")),
        title=str(card.get("title") or ""),
        summary=str(card.get("summary") or ""),
        body=str(card.get("body") or "") if card.get("body") else "",
        payload=payload,
        tags=list(card.get("tags") or []),
        evidence=[],
        space_key=str(card.get("space_key") or ""),
        metadata={
            "score": card.get("score"),
            "evidence_count": card.get("evidence_count"),
            "has_evidence": card.get("has_evidence"),
            "updated_at": card.get("updated_at"),
        },
    )


def _sort_rows(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "recent":
        return sorted(rows, key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    # Default: cards_search returns bm25 score (lower is better)
    return sorted(
        rows,
        key=lambda item: (
            float(item.get("score") or 0.0),
            str(item.get("updated_at") or ""),
        ),
    )


def build_bundle(
    store: HumanMemoryStore,
    conn,
    *,
    app_id: str,
    space_key: str,
    scope: str,
    query: str,
    bundle_spec: BundleSpec,
    available_kinds: list[str],
    include_body: bool = False,
) -> BundleResult:
    decisions: list[BundleStageDecision] = []
    stage_results: list[BundleStageResult] = []
    seen: set[str] = set()
    suppressed_total = 0

    for stage in bundle_spec.stages:
        stage_scope = stage.scope or scope
        stage_kinds = stage.kinds or available_kinds
        stage_limit = max(1, int(stage.limit))

        if stage.mode in {"search", "evidence"} and not str(query or "").strip():
            decision = BundleStageDecision(
                stage=stage.name,
                attempted=False,
                results=0,
                suppressed=0,
                reason="empty_query",
            )
            decisions.append(decision)
            stage_results.append(BundleStageResult(stage=stage.name, items=[], decision=decision))
            continue

        space_keys = store.resolve_space_keys(conn, space_key=space_key, scope=stage_scope)
        rows: list[dict[str, Any]] = []
        for key in space_keys:
            if stage.mode == "recent":
                rows.extend(
                    store.recent_cards(
                        conn,
                        space_key=key,
                        kinds=stage_kinds,
                        limit=stage_limit,
                        include_body=include_body,
                    )
                )
            else:
                rows.extend(
                    store.search_cards(
                        conn,
                        space_key=key,
                        query=query,
                        kinds=stage_kinds,
                        limit=stage_limit,
                        include_body=include_body,
                    )
                )

        if stage.require_evidence or stage.mode == "evidence":
            rows = [row for row in rows if bool(row.get("has_evidence"))]

        sorted_rows = _sort_rows(rows, "recent" if stage.mode == "recent" else "search")
        items: list[MemoryItem] = []
        suppressed = 0
        for row in sorted_rows:
            card_id = str(row.get("id"))
            if not card_id or card_id in seen:
                suppressed += 1
                continue
            seen.add(card_id)
            item = _card_to_item(row, app_id=app_id)
            if item is None:
                suppressed += 1
                continue
            items.append(item)
            if len(items) >= stage_limit:
                break

        suppressed_total += suppressed
        decision = BundleStageDecision(
            stage=stage.name,
            attempted=True,
            results=len(items),
            suppressed=suppressed,
            reason=None,
        )
        decisions.append(decision)
        stage_results.append(BundleStageResult(stage=stage.name, items=items, decision=decision))

    explanation = BundleExplanation(
        bundle_name=bundle_spec.name,
        space_key=space_key,
        scope=scope,
        decisions=decisions,
        suppressed_total=suppressed_total,
    )
    return BundleResult(bundle_name=bundle_spec.name, stages=stage_results, explanation=explanation)
