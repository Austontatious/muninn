# Muninn v2 Phase H Shadow Ops Gate Plan

Status: completed for 2026-05-17 Phase H only.

## Objective

Turn Phase G shadow operations evidence into an operator-facing runbook and an
executable pre-live replay gate.

## Scope In

- Operator runbook for shadow bridge drills and artifact inspection.
- Executable replay gate over Phase G drill reports and audit artifacts.
- Human review workflow and rollback/shutdown criteria.
- Failure drill simulations for expected operational hazards.
- Tests and Phase H reports.

## Scope Out

- Live Codex/MCP integration.
- v1 schema/runtime/default changes.
- v1 DB writes.
- Bridge daemon deployment or service enablement.
- Adaptive retrieval as a default.
- Autonomous memory writes.

## Checklist

- [x] Add replay gate evaluator and CLI command.
- [x] Add failure drill simulations.
- [x] Add operator runbook.
- [x] Add tests for gate success, no-v1 access, and failure drill detection.
- [x] Run gate against Phase G artifacts.
- [x] Run validation commands.
- [x] Commit only Phase H source/docs/tests/reports.

## Rollback

Remove the `bridge-replay-gate` command, replay gate evaluator, Phase H docs,
tests, and reports. No v1 or live bridge state should be modified.

## Test Plan

- `PYTHONPATH=src python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
- `PYTHONPATH=src python3 -m pytest -q`
- Verify final v1 row-count/size/mtime unchanged using read-only checks.
