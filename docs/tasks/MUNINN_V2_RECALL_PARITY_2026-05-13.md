# Muninn v2 Recall Parity Plan

## Objective
Add an opt-in v1/v2 recall parity command and run it against ReadyPlayer1 using the existing v2 scratch DB without changing live MCP/Codex behavior.

## Scope
- In scope: worktree hygiene report, v2-only recall parity CLI command, fixed ReadyPlayer1 query set, parity artifacts, tests, docs, architecture checkpoint note.
- Out of scope: v1 writes, v1 schema changes, live route/default changes, retrieval tuning, v2 cutover, automatic migration, cleanup of unrelated drift.

## Checklist
- [x] Write worktree hygiene report/checkpoint recommendation.
- [x] Add opt-in `recall-parity` command under `muninn.v2.cli`.
- [x] Add ReadyPlayer1 fixed query set.
- [x] Add parity tests for argument gates, read-only behavior, reports, missing/extra records, empty query sets, and missing DB handling.
- [x] Update docs and architecture checkpoint.
- [x] Run requested validation commands.
- [x] Run ReadyPlayer1 parity command if safe.

## Rollback Plan
Remove the v2 recall parity additions, v2 tests, docs, and generated parity artifacts. Do not reset, stash, delete, or otherwise alter unrelated drift.

## Test Plan
- `python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
- `python3 -m pytest -q`
