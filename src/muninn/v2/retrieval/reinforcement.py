from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..core.models import MemoryCard, RecallEvent, utc_now
from ..storage import SQLiteMemoryStore


REINFORCEMENT_SCHEMA_VERSION = "muninn.v2.recall_reinforcement.v1"
REINFORCEMENT_STATE_TABLE = "v2_reinforcement_state"
DURABLE_KINDS = {"constraint", "decision", "interface", "runbook"}
BACKGROUND_TAGS = {"background", "contrast-only", "background-only"}


@dataclass(frozen=True)
class ReinforcementWeights:
    recall: float = 0.35
    accepted: float = 2.0
    suppressed: float = 3.0
    durable_preserve: float = 0.75
    evidence_preserve_cap: float = 0.5
    recall_exposure_cap: float = 1.25
    decay: float = 0.75
    half_life_days: float = 30.0
    min_score: float = -8.0
    max_score: float = 12.0
    preserve_floor: float = 0.5

    def to_dict(self) -> dict[str, float]:
        return {
            "recall": self.recall,
            "accepted": self.accepted,
            "suppressed": self.suppressed,
            "durable_preserve": self.durable_preserve,
            "evidence_preserve_cap": self.evidence_preserve_cap,
            "recall_exposure_cap": self.recall_exposure_cap,
            "decay": self.decay,
            "half_life_days": self.half_life_days,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "preserve_floor": self.preserve_floor,
        }


def load_reinforcement_state_map(
    v2_db: str | Path,
    *,
    scope_key: str | None = None,
) -> dict[str, dict[str, Any]]:
    store = SQLiteMemoryStore(v2_db)
    return {
        str(item["record_id"]): dict(item)
        for item in store.list_reinforcement_state(scope_key=scope_key)
    }


def build_recall_event_record_report(
    *,
    event: RecallEvent,
    v2_db: str | Path,
    out_dir: str | Path,
    write_event: bool,
    existing_event_count_before: int,
    existing_event_count_after: int,
) -> dict[str, Any]:
    changed = existing_event_count_after != existing_event_count_before
    return {
        "schema_version": REINFORCEMENT_SCHEMA_VERSION,
        "record_type": "muninn_v2_recall_event_record_report",
        "mode": "offline_recall_event_record",
        "v2_db": str(v2_db),
        "out_dir": str(out_dir),
        "write_event": bool(write_event),
        "event": event.to_dict(),
        "counts": {
            "recall_events_before": existing_event_count_before,
            "recall_events_after": existing_event_count_after,
            "recall_events_changed": changed,
        },
        "safety": _safety_payload(),
    }


def replay_reinforcement(
    *,
    cards: Sequence[MemoryCard],
    recall_events: Sequence[RecallEvent],
    as_of: str | None = None,
    scope_key: str | None = None,
    weights: ReinforcementWeights | None = None,
) -> dict[str, Any]:
    config = weights or ReinforcementWeights()
    as_of_dt = _parse_time(as_of) if as_of else _max_observed_time(cards, recall_events)
    as_of_text = _format_time(as_of_dt)
    filtered_cards = [
        card
        for card in cards
        if str(card.status or "active") == "active" and (not scope_key or card.scope_key == scope_key)
    ]
    filtered_events = [
        event
        for event in recall_events
        if not scope_key or event.scope_key == scope_key
    ]
    filtered_events = sorted(filtered_events, key=lambda event: (str(event.created_at), str(event.id)))
    states = [
        _state_for_card(card, filtered_events, as_of_dt=as_of_dt, weights=config)
        for card in sorted(filtered_cards, key=lambda item: str(item.id))
    ]
    states.sort(key=lambda item: (-float(item["effective_score"]), str(item["record_id"])))
    return {
        "schema_version": REINFORCEMENT_SCHEMA_VERSION,
        "record_type": "muninn_v2_recall_reinforcement_replay",
        "mode": "offline_replay",
        "as_of": as_of_text,
        "scope_key": scope_key,
        "weights": config.to_dict(),
        "counts": {
            "eligible_cards": len(filtered_cards),
            "recall_events": len(filtered_events),
            "boosted": sum(1 for item in states if item["status"] == "boosted"),
            "suppressed": sum(1 for item in states if item["status"] == "suppressed"),
            "preserved": sum(1 for item in states if item["status"] == "preserved"),
            "decayed": sum(1 for item in states if item["status"] == "decayed"),
            "neutral": sum(1 for item in states if item["status"] == "neutral"),
        },
        "states": states,
        "safety": _safety_payload(),
    }


def apply_reinforcement_state_to_score(
    record_id: str,
    base_score: float,
    state_by_record_id: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[float, dict[str, float], dict[str, float], dict[str, Any] | None]:
    if not state_by_record_id:
        return base_score, {}, {}, None
    state = state_by_record_id.get(record_id)
    if not state:
        return base_score, {}, {}, None
    effective = float(state.get("effective_score") or 0.0)
    status = str(state.get("status") or "neutral")
    components: dict[str, float] = {}
    penalties: dict[str, float] = {}
    multiplier = 4.0
    if effective > 0:
        components["reinforcement_effective_boost"] = round(effective * multiplier, 6)
    elif effective < 0:
        penalties["reinforcement_effective_penalty"] = round(effective * multiplier, 6)
    if status == "suppressed":
        penalties["reinforcement_suppressed_memory"] = round(-max(40.0, abs(base_score) + 20.0), 6)
    elif status == "preserved":
        components["reinforcement_preservation_floor"] = 2.0
    adjusted = base_score + sum(components.values()) + sum(penalties.values())
    return adjusted, components, penalties, dict(state)


def write_recall_event_record_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "recall_event_record_report.json"
    md_path = directory / "recall_event_record_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_recall_event_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def write_reinforcement_replay_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "recall_reinforcement_replay_report.json"
    md_path = directory / "recall_reinforcement_replay_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_replay_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _state_for_card(
    card: MemoryCard,
    events: Sequence[RecallEvent],
    *,
    as_of_dt: datetime,
    weights: ReinforcementWeights,
) -> dict[str, Any]:
    recalled = 0
    accepted = 0
    suppressed = 0
    recall_boost = 0.0
    accepted_boost = 0.0
    suppression = 0.0
    event_ids: list[str] = []
    last_event_at: str | None = None
    recalled_signal_count = 0
    accepted_signal_count = 0
    suppressed_signal_count = 0
    for event in events:
        event_weight = _time_weight(event.created_at, as_of_dt=as_of_dt, half_life_days=weights.half_life_days)
        touched = False
        if card.id in event.recalled_ids:
            recalled += 1
            recalled_signal_count += 1
            recall_boost += weights.recall * event_weight * _diminishing_signal_weight(recalled_signal_count)
            touched = True
        if card.id in event.accepted_ids:
            accepted += 1
            accepted_signal_count += 1
            accepted_boost += weights.accepted * event_weight * _diminishing_signal_weight(accepted_signal_count)
            touched = True
        if card.id in event.suppressed_ids:
            suppressed += 1
            suppressed_signal_count += 1
            suppression += weights.suppressed * event_weight * _diminishing_signal_weight(suppressed_signal_count)
            touched = True
        if touched:
            event_ids.append(event.id)
            last_event_at = event.created_at

    durable = _is_durable(card)
    recall_boost = min(recall_boost, weights.recall_exposure_cap)
    quiet_anchor = _parse_time(last_event_at) if last_event_at else _parse_time(card.updated_at or card.created_at)
    quiet_days = max(0.0, (as_of_dt - quiet_anchor).total_seconds() / 86400.0)
    raw_decay = weights.decay * (quiet_days / max(1.0, weights.half_life_days))
    decay = min(raw_decay, 0.4 if durable else 4.0)
    preservation = _preservation_score(card, weights) if durable else 0.0
    base = _base_salience(card)
    effective = base + recall_boost + accepted_boost + preservation - suppression - decay
    floor_applied = False
    if durable and suppressed <= accepted and effective < weights.preserve_floor:
        effective = weights.preserve_floor
        floor_applied = True
    effective = min(weights.max_score, max(weights.min_score, effective))
    diminishing_returns_applied = max(recalled, accepted, suppressed) > 1
    status = _status(
        accepted=accepted,
        recalled=recalled,
        suppressed=suppressed,
        suppression=suppression,
        accepted_boost=accepted_boost,
        durable=durable,
        floor_applied=floor_applied,
        decay=decay,
    )
    return {
        "schema_version": REINFORCEMENT_SCHEMA_VERSION,
        "record_type": "muninn_v2_reinforcement_state",
        "record_id": card.id,
        "scope_key": card.scope_key,
        "card": {
            "title": card.title,
            "kind": card.kind,
            "status": card.status,
            "created_at": card.created_at,
            "updated_at": card.updated_at,
            "evidence_count": len(card.evidence),
        },
        "status": status,
        "effective_score": round(float(effective), 6),
        "base_salience": round(base, 6),
        "components": {
            "recall_boost": round(recall_boost, 6),
            "accepted_boost": round(accepted_boost, 6),
            "suppression": round(-suppression, 6),
            "quiet_decay": round(-decay, 6),
            "durable_preservation": round(preservation, 6),
            "preservation_floor_applied": floor_applied,
            "diminishing_returns_applied": diminishing_returns_applied,
        },
        "event_counts": {
            "recalled": recalled,
            "accepted": accepted,
            "suppressed": suppressed,
        },
        "event_ids": event_ids,
        "last_event_at": last_event_at,
        "quiet_days": round(quiet_days, 6),
        "computed_at": _format_time(as_of_dt),
        "explanation": _explanation(
            status=status,
            durable=durable,
            floor_applied=floor_applied,
            recalled=recalled,
            accepted=accepted,
            suppressed=suppressed,
            quiet_days=quiet_days,
            diminishing_returns_applied=diminishing_returns_applied,
        ),
    }


def _status(
    *,
    accepted: int,
    recalled: int,
    suppressed: int,
    suppression: float,
    accepted_boost: float,
    durable: bool,
    floor_applied: bool,
    decay: float,
) -> str:
    if suppressed and suppression > accepted_boost + (0.75 if durable else 0.0):
        return "suppressed"
    if accepted:
        return "boosted"
    if floor_applied or (durable and decay >= 0.35):
        return "preserved"
    if recalled:
        return "boosted"
    if decay >= 0.5:
        return "decayed"
    return "neutral"


def _explanation(
    *,
    status: str,
    durable: bool,
    floor_applied: bool,
    recalled: int,
    accepted: int,
    suppressed: int,
    quiet_days: float,
    diminishing_returns_applied: bool,
) -> list[str]:
    notes = [f"status={status}"]
    if accepted:
        notes.append(f"accepted {accepted} time(s), producing deterministic reinforcement")
    if recalled and not accepted:
        notes.append(f"recalled {recalled} time(s), producing a smaller exposure boost")
    if suppressed:
        notes.append(f"suppressed {suppressed} time(s), applying deterministic suppression")
    if diminishing_returns_applied:
        notes.append("repeated recall signals use deterministic diminishing returns")
    if durable:
        notes.append("durable card kind receives preservation against quiet-period decay")
    if floor_applied:
        notes.append("preservation floor kept durable project-state memory retrievable")
    if quiet_days:
        notes.append(f"quiet for {quiet_days:.2f} day(s), decay applied from replay clock")
    return notes


def _diminishing_signal_weight(signal_count: int) -> float:
    return 1.0 / math.sqrt(max(1, int(signal_count)))


def _base_salience(card: MemoryCard) -> float:
    raw = card.metadata.get("v1_salience") if isinstance(card.metadata, dict) else None
    try:
        return max(0.0, float(raw or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _is_durable(card: MemoryCard) -> bool:
    if str(card.kind or "").lower() in DURABLE_KINDS:
        return True
    tags = {str(item).lower() for item in card.tags}
    return bool(tags & {"durable", "project-state", "checkpoint"})


def _preservation_score(card: MemoryCard, weights: ReinforcementWeights) -> float:
    tags = {str(item).lower() for item in card.tags}
    if tags & BACKGROUND_TAGS:
        return 0.0
    evidence_bonus = min(weights.evidence_preserve_cap, 0.05 * len(card.evidence))
    return weights.durable_preserve + evidence_bonus


def _time_weight(created_at: str, *, as_of_dt: datetime, half_life_days: float) -> float:
    event_dt = _parse_time(created_at)
    age_days = max(0.0, (as_of_dt - event_dt).total_seconds() / 86400.0)
    return math.pow(0.5, age_days / max(1.0, float(half_life_days)))


def _parse_time(value: str | None) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.now(timezone.utc)
    normalized = text.replace("Z", "+00:00")
    if "T" not in normalized and " " in normalized:
        normalized = normalized.replace(" ", "T", 1)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _max_observed_time(cards: Sequence[MemoryCard], events: Sequence[RecallEvent]) -> datetime:
    values = [
        *[card.updated_at or card.created_at for card in cards],
        *[event.created_at for event in events],
        utc_now(),
    ]
    return max(_parse_time(value) for value in values)


def _safety_payload() -> dict[str, Any]:
    return {
        "mode": "offline_v2_only",
        "canonical_card_mutation": False,
        "v1_db_access": False,
        "live_mcp_integration": False,
        "default_context_source_changed": False,
    }


def _render_recall_event_markdown(report: dict[str, Any]) -> str:
    event = report["event"]
    counts = report["counts"]
    lines = [
        "# Muninn v2 Recall Event Record",
        "",
        f"- v2 DB: `{report['v2_db']}`",
        f"- Write event: `{str(report['write_event']).lower()}`",
        f"- Event ID: `{event['id']}`",
        f"- Query: `{event['query']}`",
        f"- Scope key: `{event.get('scope_key')}`",
        f"- Recalled: {len(event.get('recalled_ids') or [])}",
        f"- Accepted: {len(event.get('accepted_ids') or [])}",
        f"- Suppressed: {len(event.get('suppressed_ids') or [])}",
        f"- Recall events before: {counts['recall_events_before']}",
        f"- Recall events after: {counts['recall_events_after']}",
        "",
        "This is an offline v2 recall event. It does not mutate canonical cards or v1.",
    ]
    return "\n".join(lines) + "\n"


def _render_replay_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# Muninn v2 Recall Reinforcement Replay",
        "",
        f"- Mode: `{report['mode']}`",
        f"- v2 DB: `{report.get('v2_db')}`",
        f"- Dry run: `{str(report.get('dry_run', True)).lower()}`",
        f"- Write state: `{str(report.get('write_state', False)).lower()}`",
        f"- As of: `{report['as_of']}`",
        f"- Scope key: `{report.get('scope_key')}`",
        f"- Eligible cards: {counts['eligible_cards']}",
        f"- Recall events: {counts['recall_events']}",
        f"- Boosted: {counts['boosted']}",
        f"- Suppressed: {counts['suppressed']}",
        f"- Preserved: {counts['preserved']}",
        f"- Decayed: {counts['decayed']}",
        f"- Neutral: {counts['neutral']}",
        "",
        "## Top States",
        "",
    ]
    for item in report["states"][:12]:
        lines.append(
            f"- `{item['record_id']}` {item['card']['title']} "
            f"status=`{item['status']}` score=`{item['effective_score']}`"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Derived reinforcement state only.",
            "- Canonical card truth is unchanged.",
            "- v1 and live MCP defaults are untouched.",
        ]
    )
    return "\n".join(lines) + "\n"
