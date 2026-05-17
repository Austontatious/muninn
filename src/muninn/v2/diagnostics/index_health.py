from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from ..core.models import MemoryCard, utc_now
from ..indexes import SQLiteDerivedIndexProvider


def build_index_health_report(
    *,
    v2_db: str | Path,
    records: Sequence[MemoryCard],
) -> dict[str, Any]:
    provider = SQLiteDerivedIndexProvider(v2_db, records=records)
    status = provider.status()
    return {
        "schema_version": "muninn.v2.derived_indexes.v1",
        "record_type": "muninn_v2_index_health_report",
        "generated_at": utc_now(),
        "v2_db": str(Path(v2_db).expanduser()),
        "status": status.to_dict(),
        "canonical_records": {
            "cards_loaded": len(records),
            "active_cards": sum(1 for card in records if str(card.status or "active") == "active"),
        },
        "derived_index_contract": {
            "canonical_truth": "v2 cards/events/entities/associations/evidence remain canonical",
            "index_role": "optional derived diagnostic retrieval assist",
            "rebuild": "explicit",
        },
    }


def write_index_health_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "index_health_report.json"
    md_path = directory / "index_health_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _render_markdown(report: dict[str, Any]) -> str:
    status = report["status"]
    lines = [
        "# Muninn v2 Derived Index Health",
        "",
        f"- v2 DB: `{report['v2_db']}`",
        f"- Backend: `{status['backend']}`",
        f"- Backend available: `{str(status['backend_available']).lower()}`",
        f"- Eligible records: {status['eligible_records']}",
        f"- Indexed records: {status['indexed_records']}",
        f"- Missing records: {status['missing_records']}",
        f"- Stale records: {status['stale_records']}",
        f"- Degraded: `{str(status['degraded']).lower()}`",
        "",
        "## Reasons",
        "",
    ]
    reasons = list(status.get("reason") or [])
    if reasons:
        lines.extend(f"- `{reason}`" for reason in reasons)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Contract",
            "",
            "- Vectors are optional derived indexes, not canonical truth.",
            "- Rebuilds are explicit and scoped to the provided v2 DB path.",
            "- sqlite_vec absence is allowed; fallback status must be reported.",
        ]
    )
    return "\n".join(lines) + "\n"
