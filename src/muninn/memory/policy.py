from __future__ import annotations

from dataclasses import dataclass

from ..models import MemoryCandidate


@dataclass(frozen=True)
class Decision:
    accept: bool
    reason: str = ""


def decide_write(candidate: MemoryCandidate) -> Decision:
    # v0 policy: accept benign structured memory; reject obvious instruction injection markers.
    text = " ".join([str(candidate.entity), str(candidate.payload)]).lower()
    bad_markers = [
        "ignore previous",
        "system prompt",
        "override policy",
        "do not follow",
        "jailbreak",
    ]
    if any(marker in text for marker in bad_markers):
        return Decision(False, "Rejected: possible instruction injection")
    return Decision(True, "Accepted")
