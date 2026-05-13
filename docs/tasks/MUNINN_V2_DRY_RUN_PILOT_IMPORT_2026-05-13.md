# Muninn v2 Dry-Run Pilot Import Plan

## Objective
Add and run the first safe single-project Muninn v1 to v2 pilot import path for Null_Signal without touching v1 production memory or live Codex/MCP behavior.

## Scope
- In scope: adjacent v2 CLI, read-only v1 inspection, explicit v2 output path, dry-run reports, tests, docs, Null_Signal pilot artifacts if the v1 DB and space key are unambiguous.
- Out of scope: v1 schema/API changes, automatic migrations, production cutover, live MCP route changes, Mimir/Hrafnar features, destructive data movement.

## Checklist
- [x] Confirm v1 storage candidates and Null_Signal space identity.
- [x] Add scoped v1 adapter reads needed by the pilot importer.
- [x] Add `muninn.v2.cli pilot-import` with explicit path/selector safety gates.
- [x] Add tests for CLI safety, dry-run behavior, row-count verification, unsupported records, and fixture mappings.
- [x] Add pilot import documentation.
- [x] Add Null_Signal pilot report.
- [x] Run targeted and full validation.
- [x] Run the real Null_Signal dry-run only if v1 DB and space key are unambiguous.

## Rollback Plan
The change is adjacent. Remove the new v2 CLI/test/doc files and revert the small v1 adapter scoping additions. No v1 DB or production schema should be modified by the code path.

## Test Plan
- `python3 -m pytest -q tests/test_v2_*.py`
- `python3 -m pytest -q`
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
