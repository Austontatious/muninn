from __future__ import annotations

import json
from typing import Any


def bundle_to_json(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, sort_keys=True, indent=2)


def bundle_to_jsonl(bundle: dict[str, Any]) -> str:
    lines: list[str] = []
    header = {
        "schema_version": bundle.get("schema_version"),
        "record_type": "export_header",
        "counts": bundle.get("counts", {}),
    }
    lines.append(json.dumps(header, sort_keys=True, separators=(",", ":")))
    for section in (
        "ontology_profiles",
        "entities",
        "cards",
        "associations",
        "events",
        "recall_events",
    ):
        for record in bundle.get(section, []) or []:
            lines.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")
