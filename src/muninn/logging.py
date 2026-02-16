import json
import time
from typing import Any


def audit_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": time.time(),
        "type": event_type,
        "payload": payload,
    }


def audit_event_json(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False, separators=(",", ":"))
