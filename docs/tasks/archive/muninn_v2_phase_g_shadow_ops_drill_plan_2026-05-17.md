# Muninn v2 Phase G Replayable Shadow Operations Drill Plan

Status: completed for 2026-05-17 Phase G only.

## Objective

Run a replayable shadow operations drill that simulates multi-session,
multi-project agent workflows through the v2 bridge without cutover, defaults,
or writes.

## Scope In

- v2-only operational drill harness.
- Multi-turn/session bridge requests for Friday, ReadyPlayer1, and Lexi.
- Adaptive-off vs explicit adaptive-on bridge comparison using existing derived
  reinforcement state only.
- Budget-pressure, stale-context, contamination, and audit replay checks.
- Rendered context blocks plus operator-review notes.
- Phase G JSON/Markdown reports.

## Scope Out

- Live Codex/MCP integration.
- v1 schema/runtime/default changes.
- v1 DB writes or v2 canonical memory writes.
- Autonomous memory creation.
- Adaptive retrieval as a default.
- Mimir cognition.

## Checklist

- [x] Add opt-in read-only adaptive bridge path guarded by request and policy.
- [x] Add replayable bridge operations drill harness and CLI command.
- [x] Add docs and tests for longitudinal/audit/budget/contamination behavior.
- [x] Generate Phase G fixtures and run Friday/ReadyPlayer1/Lexi drills.
- [x] Run validation commands and v1 row-count safety checks.
- [x] Commit only source/tests/docs/approved Phase G artifacts.

## Rollback

Revert the Phase G eval module/CLI/docs/tests/reports and the opt-in adaptive
bridge read path. No v1 state, project repos, or canonical v2 cards should be
modified.

## Test Plan

- `PYTHONPATH=src python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
- `PYTHONPATH=src python3 -m pytest -q`
- read-only v1 row-count before/after comparison
