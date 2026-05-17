# Muninn v2 Vector Salvage Report

Date: 2026-05-13
Scope: `/mnt/data/Muninn`

## Executive Summary

The remaining vector/session/retrieval drift was not safe as v1 work. It mixed v1 schema, bootstrap, CLI, MCP, retrieval semantics, evals, and docs.

Useful parts were salvaged into v2 as opt-in derived-index and retrieval-evaluation infrastructure. v1 live schema/runtime/MCP defaults were reverted to the committed baseline.

## Architecture Decision

Vectors are derived indexes, not canonical memory.

Canonical v2 truth remains:
- cards
- events
- entities
- associations
- evidence/provenance
- recall events
- ontology profiles
- export/import records

The v2 derived-index layer is optional, rebuildable, explicit-path only, and diagnostic. sqlite_vec absence is allowed and reported as degraded fallback status.

## Implemented

- `VectorIndexStatus`
- `DerivedIndexProvider`
- `SQLiteDerivedIndexProvider`
- deterministic hash embedding fallback
- lexical fallback recall
- v2 index health and rebuild reports
- v2 retrieval eval with record-absent vs retrieval-mismatch classification
- optional v2 session retrieval report helper
- v2 CLI commands:
  - `index-health`
  - `index-rebuild`
  - `retrieval-eval`

## v1 Safety

Reverted/discarded:
- v1 migration vector tables
- v1 bootstrap auto-table creation
- v1 human-memory vector store exports
- v1 rehydration vector modes
- v1 CLI vectors/session/eval commands
- v1 MCP session-start tool registration
- v1 tests for those surfaces

No production DB migrations were run. No live v1 DB writes were performed by the salvage implementation.

## Files Salvaged To v2

- `src/muninn/v2/indexes/`
- `src/muninn/v2/retrieval/`
- `src/muninn/v2/eval/`
- `src/muninn/v2/diagnostics/`
- `src/muninn/v2/session/`
- `tests/test_v2_derived_indexes.py`
- `tests/test_v2_cli_indexes.py`
- `tests/test_v2_retrieval_eval.py`
- `docs/muninn_v2_derived_indexes.md`
- `docs/muninn_v2_retrieval_eval.md`

## Verification Status

Focused v2 test command passed:

```bash
python3 -m pytest -q tests/test_v2_derived_indexes.py tests/test_v2_cli_indexes.py tests/test_v2_retrieval_eval.py
```

Result: `9 passed`.

Required v2 wildcard test command passed:

```bash
python3 -m pytest -q tests/test_v2_*.py
```

Result: `30 passed`.

v2 compile check passed:

```bash
python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)
```

Full test command passed:

```bash
python3 -m pytest -q
```

Result: `217 passed, 2 skipped, 2 warnings`.
