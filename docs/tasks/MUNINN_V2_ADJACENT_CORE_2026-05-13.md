# Muninn v2 Adjacent Core Plan

## Objective
Create a safe adjacent Muninn v2 foundation that coexists with live Muninn v1 without changing current MCP, HTTP, CLI, or storage behavior.

## Scope
- In scope: new adjacent v2 models, contracts, SQLite store, export/import primitives, v1 read/import adapter, docs, report, tests.
- Out of scope: v1 rewrite, destructive schema migration, automatic production data migration, MCP/API contract changes, Mimir/Hrafnar feature work, salience/cognition/runtime UI.

## Checklist
- [x] Load governance, memory context, and inspect current tests/API/storage surfaces.
- [x] Add adjacent v2 typed primitives and contracts.
- [x] Add minimal v2 SQLite store and export bundle support.
- [x] Add read-only v1 adapter and partial import mapping.
- [x] Add docs and final implementation report.
- [x] Add tests for serialization, storage round-trip, v1 adapter read-only behavior, and import side effects.
- [x] Run targeted v2/v1 compatibility tests and broader test suite where feasible.

## Rollback Plan
Delete only the new `src/muninn/v2/` package, new v2 tests, new docs, this task sheet, and the v2 report. Do not touch v1 databases or schemas.

## Test Plan
- Run targeted v2 tests.
- Run representative v1 compatibility tests for human-memory, MCP contracts, SDK, and v0 API behavior.
- Run full `pytest -q` if runtime permits.
