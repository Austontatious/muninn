# Muninn v2 Adjacent Core Report

Date: 2026-05-13

## What Was Implemented

Implemented the first adjacent Muninn v2 foundation under `src/muninn/v2`.

The slice adds:

- typed v2 primitives:
  - `MemoryEvent`
  - `MemoryCard`
  - `MemoryEntity`
  - `MemoryAssociation`
  - `EvidenceRef`
  - `RecallEvent`
  - `OntologyProfile`
- small protocol contracts:
  - `MemoryStore`
  - `EventLog`
  - `CardStore`
  - `EntityResolver`
  - `AssociationStore`
  - `RecallLog`
  - `ExportProvider`
  - `ImportProvider`
- separate v2 SQLite store with v2-prefixed tables
- JSON bundle and JSONL export
- v2 bundle import
- read-only v1 human-memory adapter
- partial v1-to-v2 import adapter
- tests for coexistence and import safety

## Files Changed

New implementation files:

- `src/muninn/v2/__init__.py`
- `src/muninn/v2/core/models.py`
- `src/muninn/v2/core/contracts.py`
- `src/muninn/v2/core/store.py`
- `src/muninn/v2/core/events.py`
- `src/muninn/v2/core/associations.py`
- `src/muninn/v2/core/recall.py`
- `src/muninn/v2/core/ontology.py`
- `src/muninn/v2/storage/sqlite_store.py`
- `src/muninn/v2/storage/export_bundle.py`
- `src/muninn/v2/storage/__init__.py`
- `src/muninn/v2/adapters/v1_read_adapter.py`
- `src/muninn/v2/adapters/v1_import_adapter.py`
- `src/muninn/v2/adapters/__init__.py`

New tests:

- `tests/test_v2_models.py`
- `tests/test_v2_sqlite_store.py`
- `tests/test_v2_v1_adapter.py`
- `tests/test_v2_v1_compatibility.py`

New docs:

- `docs/decisions/ADR-0008-muninn-v2-adjacent-core.md`
- `docs/muninn_v2_adjacent_core_plan.md`
- `docs/muninn_v2_contracts.md`
- `docs/muninn_v1_compatibility_strategy.md`
- `docs/muninn_v2_cutover_strategy.md`
- `docs/tasks/MUNINN_V2_ADJACENT_CORE_2026-05-13.md`
- `reports/muninn_v2_adjacent_core_report.md`

## Tests Run

Completed so far:

```text
python3 -m pytest -q tests/test_v2_models.py tests/test_v2_sqlite_store.py tests/test_v2_v1_adapter.py tests/test_v2_v1_compatibility.py
8 passed
```

```text
python3 -m py_compile src/muninn/v2/__init__.py src/muninn/v2/core/models.py src/muninn/v2/core/contracts.py src/muninn/v2/storage/sqlite_store.py src/muninn/v2/adapters/v1_read_adapter.py src/muninn/v2/adapters/v1_import_adapter.py
passed
```

Final validation:

```text
python3 -m pytest -q tests/test_v2_models.py tests/test_v2_sqlite_store.py tests/test_v2_v1_adapter.py tests/test_v2_v1_compatibility.py tests/test_human_memory_cards.py tests/test_mcp_human_memory_contracts.py tests/test_sdk_core_contract.py tests/test_health.py tests/test_backcompat_contract.py
27 passed
```

```text
python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)
passed
```

```text
python3 -m pytest -q
239 passed, 2 skipped
```

## v1 Compatibility Status

v1 compatibility is preserved by construction:

- no v1 runtime modules were changed
- no v1 schema files were changed
- no v1 APIs were changed
- no MCP tool names were changed
- no automatic migration was added
- v2 imports do not create v1 or v2 DB files
- the v1 adapter opens SQLite with `mode=ro` and `PRAGMA query_only=ON`

## Current Limitations

The v1 adapter currently maps only:

- v1 human-memory cards
- v1 evidence attached to cards
- v1 card relations
- v1 spaces as ontology profiles

Deferred:

- v1 interaction events
- v1 policy/adaptation card-specific projections
- v1 vectors
- v0 fact/episode/preference records
- Cardex multimodal source/chunk/artifact records
- Cardex signals/coaccess edges
- migration ledger/checksums
- side-by-side recall comparison

## Migration Risks

Main risks remaining:

- preserving relation semantics across richer association models
- avoiding accidental use of v2 DB paths that overlap v1 DB paths
- mapping JSON metadata into typed v2 payloads without silent loss
- later vector/salience work creeping into canonical substrate truth
- downstream consumers mistaking v2 pilot imports for production memory

## Recommended Next Slice

Build a dry-run pilot command or script that:

1. takes an explicit v1 human-memory DB path
2. takes one explicit v1 `space_key`
3. takes an explicit v2 output DB path
4. imports cards/evidence/relations/profile
5. exports JSONL
6. reports migrated and unsupported counts
7. verifies v1 row counts are unchanged

Do not expose that command through live MCP or route Codex startup through v2 yet.
