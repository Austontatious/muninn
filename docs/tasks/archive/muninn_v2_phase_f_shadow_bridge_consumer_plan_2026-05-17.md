# Muninn v2 Phase F Shadow Bridge Consumer Plan

Status: completed for 2026-05-17 Phase F.

## Objective

Validate whether the Phase E read-only bridge can feed controlled Codex-style
tasks as a shadow context provider without live integration, v1 mutation, or
adaptive defaults.

## Scope In

- v2-only bridge consumer evaluation harness.
- Fixture-based Friday, ReadyPlayer1, and Lexi pilot evaluation.
- Bridge request/policy examples and rendered context blocks.
- Audit replay/hash verification for bridge responses.
- Phase F report with GO/NO-GO status.

## Scope Out

- Live Codex/MCP context replacement.
- v1 runtime/schema/default changes.
- v1 writes or production DB mutation.
- Adaptive retrieval defaults.
- Mimir cognition or autonomous memory creation.

## Checklist

- [x] Inspect existing Phase E bridge artifacts and Phase B/C audit fixtures.
- [x] Add a v2-only bridge consumer evaluation module and CLI command.
- [x] Add tests for schema validation, audit replay, context rendering, coverage, and v1 isolation.
- [x] Generate Phase F fixtures, bridge request/policy copies, context blocks, and reports.
- [x] Run validation commands and v1 row-count safety checks.
- [ ] Commit only source/tests/docs/approved Phase F artifacts.

## Rollback

Remove the Phase F eval module/CLI/docs/tests/reports. No v1 state or project
repos should be modified by this task.

## Test Plan

- `PYTHONPATH=src python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
- `PYTHONPATH=src python3 -m pytest -q`
- read-only v1 row-count before/after comparison
