from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..core.models import MemoryCard, utc_now
from ..indexes import SQLiteDerivedIndexProvider
from ..retrieval import recall_with_fallback


@dataclass(frozen=True)
class RetrievalEvalCase:
    case_id: str
    query: str
    expected_card_ids: tuple[str, ...]
    space_key: str | None = None
    limit: int = 10


@dataclass(frozen=True)
class RetrievalEvalFixture:
    name: str
    version: int
    cases: tuple[RetrievalEvalCase, ...]
    source_path: str


def load_retrieval_fixture(path: str | Path) -> RetrievalEvalFixture:
    fixture_path = Path(path).expanduser().resolve()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("retrieval fixture must be a JSON object")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("retrieval fixture cases must be a non-empty list")
    cases: list[RetrievalEvalCase] = []
    seen: set[str] = set()
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    default_limit = int(defaults.get("limit") or 10)
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise ValueError(f"cases[{index}] must be an object")
        case_id = str(raw.get("id") or raw.get("case_id") or "").strip()
        query = " ".join(str(raw.get("query") or "").split())
        if not case_id:
            raise ValueError(f"cases[{index}].id is required")
        if case_id in seen:
            raise ValueError(f"duplicate case id: {case_id}")
        if not query:
            raise ValueError(f"cases[{index}].query is required")
        seen.add(case_id)
        expected = _dedupe(raw.get("expected_card_ids") or [])
        cases.append(
            RetrievalEvalCase(
                case_id=case_id,
                query=query,
                expected_card_ids=tuple(expected),
                space_key=(str(raw.get("space_key")).strip() if raw.get("space_key") else None),
                limit=int(raw.get("limit") or default_limit),
            )
        )
    return RetrievalEvalFixture(
        name=str(payload.get("name") or fixture_path.stem),
        version=int(payload.get("version") or 1),
        cases=tuple(cases),
        source_path=str(fixture_path),
    )


def run_retrieval_eval(
    *,
    records: Sequence[MemoryCard],
    fixture: RetrievalEvalFixture,
    provider: SQLiteDerivedIndexProvider | None = None,
) -> dict[str, Any]:
    cards_by_id = {card.id: card for card in records}
    case_reports: list[dict[str, Any]] = []
    total_expected = 0
    total_hits = 0
    record_absent = 0
    retrieval_mismatch = 0
    extra_results = 0
    for case in fixture.cases:
        recall = recall_with_fallback(
            records,
            case.query,
            provider=provider,
            limit=case.limit,
            scope_key=case.space_key,
        )
        results = list(recall["results"])
        result_ids = [str(item.get("record_id") or "") for item in results]
        expected_ids = list(case.expected_card_ids)
        hits = [card_id for card_id in expected_ids if card_id in result_ids]
        missing_expected: list[dict[str, Any]] = []
        for card_id in expected_ids:
            if card_id in result_ids:
                continue
            if card_id not in cards_by_id:
                status = "record_absent"
                record_absent += 1
            else:
                status = "retrieval_mismatch"
                retrieval_mismatch += 1
            missing_expected.append({"record_id": card_id, "classification": status})
        expected_set = set(expected_ids)
        extras = [card_id for card_id in result_ids if expected_set and card_id not in expected_set]
        extra_results += len(extras)
        total_expected += len(expected_ids)
        total_hits += len(hits)
        ranking_deltas = [
            {
                "record_id": card_id,
                "expected_rank": index,
                "actual_rank": result_ids.index(card_id) + 1 if card_id in result_ids else None,
                "rank_delta_actual_minus_expected": (
                    result_ids.index(card_id) + 1 - index if card_id in result_ids else None
                ),
            }
            for index, card_id in enumerate(expected_ids, start=1)
        ]
        case_reports.append(
            {
                "id": case.case_id,
                "query": case.query,
                "space_key": case.space_key,
                "backend": recall["backend"],
                "fallback_used": bool(recall["fallback_used"]),
                "expected_card_ids": expected_ids,
                "top_ids": result_ids,
                "hits": hits,
                "missing_expected": missing_expected,
                "extra_result_ids": extras,
                "ranking_deltas": ranking_deltas,
                "recall_at_limit": (
                    round(len(hits) / len(expected_ids), 6) if expected_ids else None
                ),
                "status": "pass" if not missing_expected else "fail",
            }
        )
    scored = [case for case in case_reports if case["recall_at_limit"] is not None]
    mean_recall = (
        round(sum(float(case["recall_at_limit"]) for case in scored) / len(scored), 6)
        if scored
        else None
    )
    return {
        "schema_version": "muninn.v2.retrieval_eval.v1",
        "record_type": "muninn_v2_retrieval_eval_report",
        "generated_at": utc_now(),
        "fixture": {
            "name": fixture.name,
            "version": fixture.version,
            "source_path": fixture.source_path,
        },
        "summary": {
            "cases": len(case_reports),
            "scored_cases": len(scored),
            "expected_records": total_expected,
            "hit_records": total_hits,
            "mean_recall_at_limit": mean_recall,
            "record_absent_count": record_absent,
            "retrieval_mismatch_count": retrieval_mismatch,
            "extra_result_count": extra_results,
        },
        "cases": case_reports,
    }


def write_retrieval_eval_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "retrieval_eval_report.json"
    md_path = directory / "retrieval_eval_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Muninn v2 Retrieval Eval",
        "",
        f"- Fixture: `{report['fixture']['name']}`",
        f"- Cases: {summary['cases']}",
        f"- Mean recall at limit: `{summary['mean_recall_at_limit']}`",
        f"- Record absent count: {summary['record_absent_count']}",
        f"- Retrieval mismatch count: {summary['retrieval_mismatch_count']}",
        f"- Extra result count: {summary['extra_result_count']}",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['id']}`: status=`{case['status']}` backend=`{case['backend']}` "
            f"hits={len(case['hits'])}/{len(case['expected_card_ids'])}"
        )
    lines.extend(
        [
            "",
            "Retrieval eval is diagnostic only. It measures behavior and does not tune or route production recall.",
        ]
    )
    return "\n".join(lines) + "\n"


def _dedupe(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(values, list):
        raise ValueError("expected_card_ids must be a list")
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
