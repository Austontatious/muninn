# Muninn v2 ReadyPlayer1 Pilot Import Plan

## Objective
Run a second dry-run v1 to v2 pilot import against the non-empty ReadyPlayer1 space and add migration ledger/checksum plus side-by-side record fidelity artifacts.

## Scope
- In scope: adjacent v2 pilot importer report artifacts, deterministic checksums, per-record migration ledger, fidelity reports, tests, docs, ReadyPlayer1 dry-run outputs.
- Out of scope: live v1 writes, v1 schema/API changes, live MCP/Codex route changes, automatic migrations, v2 cutover, completion-memory writes before final row-count reporting.

## Checklist
- [x] Identify ReadyPlayer1 v1 DB and space key.
- [x] Add deterministic migration ledger and checksum artifacts.
- [x] Add side-by-side record fidelity report artifacts.
- [x] Add tests for ledger/checksum/fidelity behavior.
- [x] Update pilot docs and ReadyPlayer1 pilot report.
- [x] Run v2 tests, py_compile, and full test suite.
- [x] Run ReadyPlayer1 dry-run and verify final v1 row counts.

## Rollback Plan
The implementation is adjacent. Remove the new v2 CLI/report additions, tests, docs, and pilot output directory. No v1 data rollback should be required.

## Test Plan
- `python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
- `python3 -m pytest -q`
