# Muninn v2 Adjacent Core Plan

Date: 2026-05-13

## Summary

Muninn v2 starts as an adjacent durable-memory substrate package under `src/muninn/v2`. Muninn v1 remains live production memory. No v1 schema, MCP tool, HTTP route, CLI command, or production database is modified by this foundation slice.

## Design Posture

Muninn v2 is:

- durable memory substrate
- explicit typed primitives
- separate storage
- export/import capable
- compatible with read-only v1 projections

Muninn v2 is not:

- a v1 rewrite
- an automatic migration runner
- a vector database as source of truth
- a salience/cognition engine
- an interpreter/runtime/UI layer
- a transcript archive

## New Adjacent Package

The v2 foundation lives under:

```text
src/muninn/v2/
  core/
    models.py
    contracts.py
    store.py
    events.py
    associations.py
    recall.py
    ontology.py
  storage/
    sqlite_store.py
    export_bundle.py
  adapters/
    v1_read_adapter.py
    v1_import_adapter.py
```

This package is intentionally not imported by v1 runtime modules. Existing users must opt into it explicitly with imports such as:

```python
from muninn.v2 import SQLiteMemoryStore, MemoryCard
```

## Phase 1 Capabilities

Implemented in this slice:

- dataclass primitives for events, cards, entities, associations, evidence, recall events, and ontology profiles
- protocol contracts for store surfaces
- minimal SQLite store with v2-prefixed tables
- JSON bundle and JSONL export
- import from exported v2 bundles
- read-only v1 human-memory adapter
- partial v1-to-v2 import adapter
- tests proving no import-time migrations and v1 MCP tool coexistence

## Storage Isolation

The v2 SQLite store only touches the DB path passed to `SQLiteMemoryStore`. It does not read:

- `MUNINN_DB_PATH`
- `MUNINN_HUMAN_MEMORY_DB_PATH`
- v1 default `muninn.db`
- v1 default `human_memory.db`

No v2 production location is defined in this slice. Pilot callers must pass an explicit test or pilot path.

## Pilot Shape

A single-project pilot should:

1. Create a new v2 DB path outside production v1 files.
2. Use `V1ReadAdapter` to inspect a single v1 human-memory space.
3. Use `V1ImportAdapter` to import only that space into the v2 DB.
4. Compare v1 and v2 counts and exported bundles.
5. Do not route Codex live startup through v2.

## Rollback

Rollback is deletion of:

- `src/muninn/v2/`
- v2 tests
- v2 docs/report
- pilot v2 DB files

No v1 data rollback is required because v1 is read-only from the v2 adapters and untouched by the v2 store.
