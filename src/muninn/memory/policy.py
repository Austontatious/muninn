from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..models import MemoryCandidate


@dataclass(frozen=True)
class Decision:
    accept: bool
    action: Literal["accept", "reject", "confirm_required"]
    reason: str = ""


BAD_MARKERS = ["ignore previous", "system prompt", "override policy", "do not follow", "jailbreak"]
SENSITIVE_KEYS = [
    "health.",
    "medical.",
    "sex.",
    "religion.",
    "politics.",
    "finance.",
    "address.",
    "ssn.",
]


def decide_write(candidate: MemoryCandidate) -> Decision:
    blob = (" ".join([str(candidate.entity), str(candidate.payload)])).lower()

    if any(marker in blob for marker in BAD_MARKERS):
        return Decision(
            accept=False,
            action="reject",
            reason="Rejected: possible instruction injection",
        )

    # Confirm-required: sensitivity heuristics
    if candidate.kind == "preference":
        key = str(candidate.payload.get("key", "")).lower()
        if any(key.startswith(sk) for sk in SENSITIVE_KEYS):
            return Decision(
                accept=False,
                action="confirm_required",
                reason="CONFIRM_REQUIRED: sensitive preference key",
            )

    if candidate.kind == "fact":
        pred = str(candidate.payload.get("predicate", "")).lower()
        obj = str(candidate.payload.get("object", "")).lower()
        if any(
            sensitive in (pred + " " + obj)
            for sensitive in ["diagnosis", "medication", "political party", "religion"]
        ):
            return Decision(
                accept=False,
                action="confirm_required",
                reason="CONFIRM_REQUIRED: sensitive fact",
            )

    # v0.2+: accept benign writes
    return Decision(accept=True, action="accept", reason="Accepted")
