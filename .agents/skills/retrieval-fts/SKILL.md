---
name: retrieval-fts
description: Modify retrieval behavior (FTS/hybrid) safely with deterministic ranking, entity filters, and tests.
---

# Retrieval / FTS Changes

Use this skill when editing:
- `src/muninn/memory/retrieval.py`
- FTS tables/triggers in `src/muninn/schema.sql`

## Guardrails
- Preserve `entity_id` filtering semantics.
- Keep retrieval deterministic (stable ordering).
- Always return `items[]` for audit/debug.

## Checklist
1) Update schema + backfill if needed
2) Update retrieval logic
3) Add/adjust tests:
   - at least one test for query hit
   - at least one test for entity filter
4) Run `pytest -q`
