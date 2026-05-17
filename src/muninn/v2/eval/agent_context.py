from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from jsonschema import Draft202012Validator

from ..core.models import utc_now

AGENT_CONTEXT_AUDIT_SCHEMA_VERSION = "muninn.v2.agent_context_audit.v1"
AGENT_CONTEXT_FIXTURE_SCHEMA_VERSION = "muninn.v2.agent_context_audit_fixture.v1"
REHYDRATE_RESPONSE_SCHEMA_VERSION = "muninn.v2.rehydrate_response.v1"
REHYDRATE_RESPONSE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json"
)


class AgentContextAuditError(RuntimeError):
    """Raised when the offline agent-context audit cannot run safely."""


@dataclass(frozen=True)
class CoverageNeed:
    need_id: str
    description: str
    required: bool
    all_terms: tuple[str, ...]
    any_terms: tuple[str, ...]
    evidence_terms: tuple[str, ...]
    card_ids: tuple[str, ...]


@dataclass(frozen=True)
class WatchTerm:
    term: str
    reason: str
    blocking: bool = False


@dataclass(frozen=True)
class AgentContextAuditCase:
    case_id: str
    project: str
    task: str
    response_path: str
    expected_needs: tuple[CoverageNeed, ...]
    v1_context: str | None = None
    min_coverage: float = 0.85
    require_all_required: bool = True
    stale_terms: tuple[WatchTerm, ...] = ()
    confusing_terms: tuple[WatchTerm, ...] = ()
    ignored_overinclude_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentContextAuditFixture:
    name: str
    version: int
    cases: tuple[AgentContextAuditCase, ...]
    source_path: str


def load_agent_context_fixture(path: str | Path) -> AgentContextAuditFixture:
    fixture_path = Path(path).expanduser().resolve()
    payload = _read_json(fixture_path)
    if not isinstance(payload, dict):
        raise AgentContextAuditError("agent context fixture must be a JSON object")
    if payload.get("schema_version") != AGENT_CONTEXT_FIXTURE_SCHEMA_VERSION:
        raise AgentContextAuditError("unsupported agent context fixture schema_version")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise AgentContextAuditError("agent context fixture cases must be a non-empty list")
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    cases: list[AgentContextAuditCase] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise AgentContextAuditError(f"cases[{index}] must be an object")
        case_id = _required_text(raw, "id", f"cases[{index}]")
        if case_id in seen:
            raise AgentContextAuditError(f"duplicate case id: {case_id}")
        seen.add(case_id)
        response_path = _resolve_path(fixture_path.parent, _required_text(raw, "response_path", case_id))
        needs = _coverage_needs(raw.get("expected_needs"), case_id)
        cases.append(
            AgentContextAuditCase(
                case_id=case_id,
                project=str(raw.get("project") or ""),
                task=_required_text(raw, "task", case_id),
                response_path=str(response_path),
                expected_needs=tuple(needs),
                v1_context=_load_context_text(raw, base_dir=fixture_path.parent),
                min_coverage=float(raw.get("min_coverage", defaults.get("min_coverage", 0.85))),
                require_all_required=bool(
                    raw.get("require_all_required", defaults.get("require_all_required", True))
                ),
                stale_terms=tuple(_watch_terms(raw.get("stale_terms"), default_blocking=True)),
                confusing_terms=tuple(_watch_terms(raw.get("confusing_terms"), default_blocking=False)),
                ignored_overinclude_terms=tuple(
                    _text_list(raw.get("ignored_overinclude_terms") or defaults.get("ignored_overinclude_terms") or [])
                ),
            )
        )
    return AgentContextAuditFixture(
        name=str(payload.get("name") or fixture_path.stem),
        version=int(payload.get("version") or 1),
        cases=tuple(cases),
        source_path=str(fixture_path),
    )


def load_rehydrate_response(
    path: str | Path,
    *,
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    response_path = Path(path).expanduser().resolve()
    payload = _read_json(response_path)
    validate_rehydrate_response(payload, schema_path=schema_path)
    return payload


def validate_rehydrate_response(
    payload: dict[str, Any],
    *,
    schema_path: str | Path | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise AgentContextAuditError("RehydrateResponseV1 payload must be an object")
    if payload.get("schema_version") != REHYDRATE_RESPONSE_SCHEMA_VERSION:
        raise AgentContextAuditError("unsupported RehydrateResponseV1 schema_version")
    schema_file = Path(schema_path).expanduser().resolve() if schema_path else REHYDRATE_RESPONSE_SCHEMA_PATH
    schema = _read_json(schema_file)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def render_agent_context(response: dict[str, Any]) -> str:
    request = response["request"]
    source = request["source"]
    retrieval = response["retrieval_provenance"]
    budget = response["budget"]
    uncertainty = response["uncertainty"]
    primary = _cards_by_stage(response, "primary_retrieval")
    supplements = _cards_by_stage(response, "recent_in_scope_supplement")
    lines = [
        "BEGIN MUNINN V2 AGENT CONTEXT",
        f"schema_version: {response['schema_version']}",
        f"contract_version: {response['contract_version']}",
        f"response_kind: {response['response_kind']}",
        f"task: {request['query']['text']}",
        f"source_v2_db: {source['v2_db']}",
        f"space_key: {source.get('space_key')}",
        f"project_path: {source.get('project_path')}",
        f"retrieval_mode: {retrieval.get('mode')}",
        f"retrieval_backend: {retrieval.get('backend')}",
        f"degraded: {str(bool(retrieval.get('degraded'))).lower()}",
        f"degradation_reasons: {', '.join(retrieval.get('degradation_reasons') or []) or 'none'}",
        (
            "budget: "
            f"{budget['selected_total']} selected "
            f"({budget['primary_selected']} primary, {budget['supplement_selected']} supplements), "
            f"{budget['omitted_for_budget']} omitted_for_budget, "
            f"{budget['omitted_for_limit']} omitted_for_limit"
        ),
        "",
        "PRIMARY MEMORY",
    ]
    lines.extend(_render_cards(primary))
    lines.extend(["", "CONTINUITY SUPPLEMENTS"])
    lines.extend(_render_cards(supplements))
    lines.extend(["", "EVIDENCE"])
    evidence = response["selected_memory"].get("evidence", [])
    if evidence:
        for item in evidence:
            lines.append(
                "- "
                f"[{item.get('id')}] card={item.get('card_id')} "
                f"type={item.get('type')} ref={item.get('ref')}"
            )
    else:
        lines.append("- none included")
    lines.extend(["", "UNCERTAINTY AND GAPS"])
    gaps = uncertainty.get("context_gaps") or []
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- none reported")
    lines.extend(["", "AGENT BRIEFING"])
    bullets = response["agent_briefing"].get("bullets") or []
    if bullets:
        lines.extend(f"- {bullet}" for bullet in bullets)
    else:
        lines.append("- no briefing generated")
    lines.append("END MUNINN V2 AGENT CONTEXT")
    return "\n".join(lines) + "\n"


def run_agent_context_audit(
    fixture: AgentContextAuditFixture,
    *,
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    case_reports: list[dict[str, Any]] = []
    context_blocks: dict[str, str] = {}
    for case in fixture.cases:
        response = load_rehydrate_response(case.response_path, schema_path=schema_path)
        context_block = render_agent_context(response)
        v2_score = _score_context(
            context_block,
            case.expected_needs,
            selected_card_ids=_selected_card_ids(response),
            min_coverage=case.min_coverage,
            require_all_required=case.require_all_required,
        )
        v1_score = (
            _score_context(
                case.v1_context,
                case.expected_needs,
                selected_card_ids=set(),
                min_coverage=case.min_coverage,
                require_all_required=case.require_all_required,
            )
            if case.v1_context is not None
            else None
        )
        stale = _term_hits(context_block, case.stale_terms)
        confusing = _term_hits(context_block, case.confusing_terms)
        overincluded = _overincluded_cards(response, case.expected_needs, case.ignored_overinclude_terms)
        blocking_flags = [
            *[_flag_payload(item) for item in stale if item["blocking"]],
            *[_flag_payload(item) for item in confusing if item["blocking"]],
        ]
        v2_pass = bool(v2_score["pass"] and not blocking_flags)
        comparison = _comparison(v1_score=v1_score, v2_score=v2_score, v2_pass=v2_pass)
        case_reports.append(
            {
                "id": case.case_id,
                "project": case.project,
                "task": case.task,
                "response_path": case.response_path,
                "v2_context": {
                    "coverage_score": v2_score["coverage_score"],
                    "covered_required": v2_score["covered_required"],
                    "required_needs": v2_score["required_needs"],
                    "missing_required": v2_score["missing_required"],
                    "pass": v2_pass,
                },
                "v1_style_context": (
                    {
                        "provided": True,
                        "coverage_score": v1_score["coverage_score"],
                        "covered_required": v1_score["covered_required"],
                        "required_needs": v1_score["required_needs"],
                        "missing_required": v1_score["missing_required"],
                        "pass": v1_score["pass"],
                    }
                    if v1_score is not None
                    else {"provided": False}
                ),
                "comparison": comparison,
                "need_results": v2_score["need_results"],
                "stale": [_flag_payload(item) for item in stale],
                "confusing": [_flag_payload(item) for item in confusing],
                "over_included_cards": overincluded,
                "context_block_chars": len(context_block),
                "selected_cards": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "stage": item.get("selection", {}).get("stage"),
                    }
                    for item in response["selected_memory"].get("cards", [])
                ],
                "decision": "go" if comparison["same_good_decision_supported"] else "no_go",
            }
        )
        context_blocks[case.case_id] = context_block
    summary = _summary(case_reports)
    return {
        "schema_version": AGENT_CONTEXT_AUDIT_SCHEMA_VERSION,
        "record_type": "muninn_v2_agent_context_audit_report",
        "generated_at": utc_now(),
        "fixture": {
            "name": fixture.name,
            "version": fixture.version,
            "source_path": fixture.source_path,
        },
        "summary": summary,
        "cases": case_reports,
        "context_blocks": context_blocks,
        "safety": {
            "mode": "offline_read_only",
            "live_mcp_integration": False,
            "v1_writes": False,
            "default_context_source_changed": False,
        },
    }


def write_agent_context_audit_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "agent_context_audit_report.json"
    md_path = directory / "agent_context_audit_report.md"
    json_path.write_text(
        json.dumps(_report_without_context_blocks(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_audit_markdown(report), encoding="utf-8")
    context_dir = directory / "agent_context_blocks"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_paths: dict[str, str] = {}
    for case_id, context_block in sorted(report.get("context_blocks", {}).items()):
        path = context_dir / f"{_safe_file_name(case_id)}.md"
        path.write_text(context_block, encoding="utf-8")
        context_paths[case_id] = str(path)
    return {"json": str(json_path), "markdown": str(md_path), "context_blocks": context_paths}


def _score_context(
    context: str | None,
    needs: Sequence[CoverageNeed],
    *,
    selected_card_ids: set[str],
    min_coverage: float,
    require_all_required: bool,
) -> dict[str, Any]:
    text = _normalize_text(context or "")
    results: list[dict[str, Any]] = []
    required_needs = [need for need in needs if need.required]
    covered_required = 0
    for need in needs:
        result = _score_need(text, selected_card_ids=selected_card_ids, need=need)
        if need.required and result["covered"]:
            covered_required += 1
        results.append(result)
    coverage = round(covered_required / max(1, len(required_needs)), 6)
    missing_required = [
        item["id"] for item in results if item["required"] and not item["covered"]
    ]
    passes_required = not missing_required if require_all_required else coverage >= float(min_coverage)
    return {
        "coverage_score": coverage,
        "covered_required": covered_required,
        "required_needs": len(required_needs),
        "missing_required": missing_required,
        "need_results": results,
        "pass": bool(coverage >= float(min_coverage) and passes_required),
    }


def _score_need(text: str, *, selected_card_ids: set[str], need: CoverageNeed) -> dict[str, Any]:
    missing_all = [term for term in need.all_terms if _normalize_text(term) not in text]
    any_hit = True
    if need.any_terms:
        any_hit = any(_normalize_text(term) in text for term in need.any_terms)
    missing_evidence = [term for term in need.evidence_terms if _normalize_text(term) not in text]
    card_hit = True
    if need.card_ids:
        card_hit = any(card_id in selected_card_ids or _normalize_text(card_id) in text for card_id in need.card_ids)
    covered = not missing_all and any_hit and not missing_evidence and card_hit
    return {
        "id": need.need_id,
        "description": need.description,
        "required": need.required,
        "covered": bool(covered),
        "missing_all_terms": missing_all,
        "any_terms": list(need.any_terms),
        "any_term_hit": bool(any_hit),
        "missing_evidence_terms": missing_evidence,
        "card_id_hit": bool(card_hit),
    }


def _comparison(
    *,
    v1_score: dict[str, Any] | None,
    v2_score: dict[str, Any],
    v2_pass: bool,
) -> dict[str, Any]:
    if v1_score is None:
        return {
            "v1_context_provided": False,
            "same_good_decision_supported": bool(v2_pass),
            "coverage_delta_v2_minus_v1": None,
            "regressions": [],
        }
    v1_missing = set(v1_score["missing_required"])
    v2_missing = set(v2_score["missing_required"])
    regressions = sorted(v2_missing - v1_missing)
    return {
        "v1_context_provided": True,
        "same_good_decision_supported": bool(v2_pass and not regressions),
        "coverage_delta_v2_minus_v1": round(
            float(v2_score["coverage_score"]) - float(v1_score["coverage_score"]),
            6,
        ),
        "regressions": regressions,
    }


def _overincluded_cards(
    response: dict[str, Any],
    needs: Sequence[CoverageNeed],
    ignored_terms: Sequence[str],
) -> list[dict[str, Any]]:
    terms = _relevance_terms(needs, ignored_terms)
    if not terms:
        return []
    out: list[dict[str, Any]] = []
    for card in response["selected_memory"].get("cards", []):
        text = _normalize_text(
            " ".join(
                [
                    str(card.get("title") or ""),
                    str(card.get("summary") or ""),
                    str(card.get("body_excerpt") or ""),
                ]
            )
        )
        if not any(term in text for term in terms):
            out.append(
                {
                    "id": card.get("id"),
                    "title": card.get("title"),
                    "stage": card.get("selection", {}).get("stage"),
                    "reason": "no_expected_need_terms_matched_title_summary_or_body_excerpt",
                }
            )
    return out


def _relevance_terms(needs: Sequence[CoverageNeed], ignored_terms: Sequence[str]) -> list[str]:
    ignored = {_normalize_text(item) for item in ignored_terms}
    terms: list[str] = []
    for need in needs:
        for term in [*need.all_terms, *need.any_terms, *need.evidence_terms]:
            normalized = _normalize_text(term)
            if len(normalized) < 4 or normalized in ignored:
                continue
            terms.append(normalized)
    return sorted(set(terms))


def _term_hits(context: str, terms: Sequence[WatchTerm]) -> list[dict[str, Any]]:
    text = _normalize_text(context)
    out: list[dict[str, Any]] = []
    for item in terms:
        if _normalize_text(item.term) in text:
            out.append({"term": item.term, "reason": item.reason, "blocking": bool(item.blocking)})
    return out


def _summary(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    go = sum(1 for case in cases if case["decision"] == "go")
    avg = (
        round(sum(float(case["v2_context"]["coverage_score"]) for case in cases) / total, 6)
        if total
        else None
    )
    return {
        "cases": total,
        "go_cases": go,
        "no_go_cases": total - go,
        "average_v2_coverage_score": avg,
        "same_good_decision_supported_count": sum(
            1 for case in cases if case["comparison"]["same_good_decision_supported"]
        ),
        "cases_with_v1_comparison": sum(
            1 for case in cases if case["comparison"]["v1_context_provided"]
        ),
        "missing_required_total": sum(len(case["v2_context"]["missing_required"]) for case in cases),
        "stale_flag_total": sum(len(case["stale"]) for case in cases),
        "confusing_flag_total": sum(len(case["confusing"]) for case in cases),
        "over_included_card_total": sum(len(case["over_included_cards"]) for case in cases),
    }


def _render_audit_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Muninn v2 Agent Context Audit",
        "",
        f"- Fixture: `{report['fixture']['name']}`",
        f"- Cases: {summary['cases']}",
        f"- GO cases: {summary['go_cases']}",
        f"- NO-GO cases: {summary['no_go_cases']}",
        f"- Average v2 coverage: `{summary['average_v2_coverage_score']}`",
        f"- Same-good-decision supported: {summary['same_good_decision_supported_count']}",
        f"- Missing required needs: {summary['missing_required_total']}",
        f"- Confusing flags: {summary['confusing_flag_total']}",
        f"- Over-included cards: {summary['over_included_card_total']}",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"### {case['id']}",
                "",
                f"- Project: `{case['project']}`",
                f"- Decision: `{case['decision']}`",
                f"- V2 coverage: `{case['v2_context']['coverage_score']}`",
                f"- Missing required: `{case['v2_context']['missing_required']}`",
                f"- V1 comparison: `{case['comparison']}`",
                f"- Stale flags: `{case['stale']}`",
                f"- Confusing flags: `{case['confusing']}`",
                f"- Over-included cards: {len(case['over_included_cards'])}",
                "",
            ]
        )
        if case["over_included_cards"]:
            lines.append("Over-included candidates:")
            for item in case["over_included_cards"][:12]:
                lines.append(
                    f"- `{item.get('id')}` {item.get('title')} ({item.get('stage')})"
                )
            lines.append("")
    lines.extend(
        [
            "## Safety",
            "",
            "- Offline read-only harness only.",
            "- Does not call live MCP or change Codex defaults.",
            "- Does not write to v1 or project repositories.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_cards(cards: Sequence[dict[str, Any]]) -> list[str]:
    if not cards:
        return ["- none"]
    lines: list[str] = []
    for card in cards:
        selection = card.get("selection", {})
        lines.extend(
            [
                f"- [{card.get('id')}] {card.get('title')}",
                f"  kind: {card.get('kind')} status: {card.get('status')} stage: {selection.get('stage')}",
                f"  score: {selection.get('score')} rank: {selection.get('retrieval_rank')}",
                f"  summary: {card.get('summary')}",
            ]
        )
        if card.get("body_excerpt"):
            lines.append(f"  body: {card.get('body_excerpt')}")
        if card.get("evidence"):
            refs = [str(item.get("ref") or item.get("id")) for item in card.get("evidence", [])[:5]]
            lines.append("  evidence: " + "; ".join(refs))
        explanation = card.get("explanation")
        if isinstance(explanation, dict):
            lines.append(
                "  explanation: "
                f"path={explanation.get('retrieval_path')} "
                f"sources={explanation.get('candidate_sources')} "
                f"tokens={explanation.get('matched_tokens')}"
            )
    return lines


def _cards_by_stage(response: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    return [
        item
        for item in response["selected_memory"].get("cards", [])
        if item.get("selection", {}).get("stage") == stage
    ]


def _selected_card_ids(response: dict[str, Any]) -> set[str]:
    return {str(item.get("id") or "") for item in response["selected_memory"].get("cards", [])}


def _coverage_needs(raw: Any, case_id: str) -> list[CoverageNeed]:
    if not isinstance(raw, list) or not raw:
        raise AgentContextAuditError(f"{case_id}.expected_needs must be a non-empty list")
    needs: list[CoverageNeed] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise AgentContextAuditError(f"{case_id}.expected_needs[{index}] must be an object")
        need_id = _required_text(item, "id", f"{case_id}.expected_needs[{index}]")
        if need_id in seen:
            raise AgentContextAuditError(f"duplicate expected need id in {case_id}: {need_id}")
        seen.add(need_id)
        need = CoverageNeed(
            need_id=need_id,
            description=str(item.get("description") or need_id),
            required=bool(item.get("required", True)),
            all_terms=tuple(_text_list(item.get("all_terms") or [])),
            any_terms=tuple(_text_list(item.get("any_terms") or [])),
            evidence_terms=tuple(_text_list(item.get("evidence_terms") or [])),
            card_ids=tuple(_text_list(item.get("card_ids") or [])),
        )
        if not any([need.all_terms, need.any_terms, need.evidence_terms, need.card_ids]):
            raise AgentContextAuditError(f"{case_id}.expected_needs[{index}] has no match criteria")
        needs.append(need)
    return needs


def _watch_terms(raw: Any, *, default_blocking: bool) -> list[WatchTerm]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentContextAuditError("watch terms must be a list")
    out: list[WatchTerm] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            out.append(WatchTerm(term=item, reason=item, blocking=default_blocking))
            continue
        if not isinstance(item, dict):
            raise AgentContextAuditError(f"watch_terms[{index}] must be a string or object")
        out.append(
            WatchTerm(
                term=_required_text(item, "term", f"watch_terms[{index}]"),
                reason=str(item.get("reason") or item.get("term") or ""),
                blocking=bool(item.get("blocking", default_blocking)),
            )
        )
    return out


def _load_context_text(raw: dict[str, Any], *, base_dir: Path) -> str | None:
    if "v1_context" in raw:
        return _coerce_context(raw.get("v1_context"))
    if raw.get("v1_context_path"):
        return _resolve_path(base_dir, str(raw["v1_context_path"])).read_text(encoding="utf-8")
    return None


def _coerce_context(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{key}: {val}" for key, val in sorted(value.items()))
    return str(value or "")


def _required_text(raw: dict[str, Any], key: str, scope: str) -> str:
    text = " ".join(str(raw.get(key) or "").split())
    if not text:
        raise AgentContextAuditError(f"{scope}.{key} is required")
    return text


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise AgentContextAuditError("expected list of strings")
    return [" ".join(str(item).split()) for item in value if str(item).strip()]


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise AgentContextAuditError(f"file_not_found:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _safe_file_name(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")
    return out or "case"


def _flag_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {"term": item["term"], "reason": item["reason"], "blocking": bool(item["blocking"])}


def _report_without_context_blocks(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    out.pop("context_blocks", None)
    return out
