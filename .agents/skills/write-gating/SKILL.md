---
name: write-gating
description: Adjust memory write policies, sensitive gating, and dedupe/merge rules without creating memory rot.
---

# Write Gating + Dedupe / Merge

Use this skill when editing:
- `src/muninn/memory/policy.py`
- `src/muninn/memory/writeback.py`

## Safety firewall
- Reject instruction-like memory (policy overrides, jailbreak content).
- Sensitive memory should return `CONFIRM_REQUIRED` (do not silently store).

## Data hygiene
- Preferences should merge by (entity_id, key).
- Facts should dedupe by (subject_id, predicate, object) and bump confidence.

## Checklist
- Add/adjust tests for:
  - merge behavior
  - dedupe behavior
  - confirm-required behavior
- Run `pytest -q`.
