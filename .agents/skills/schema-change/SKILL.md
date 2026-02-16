---
name: schema-change
description: When changing DB schema, API models, or tool payloads, follow the migration+docs+tests checklist.
---

# Schema Change Protocol

Use this skill when you modify any of:
- `src/muninn/schema.sql`
- `src/muninn/models.py`
- any `/v0/` API request/response shape
- `schemas/tooling/muninn_tool_spec.json`

## Checklist
1) Update schema/models
2) Update `scripts/init_db.py` to backfill/migrate (even if just backfill)
3) Update/extend tests proving the new behavior (must fail before / pass after)
4) Update `docs/INTEGRATION.md` examples
5) Update `schemas/tooling/muninn_tool_spec.json`
6) Run `pytest -q`

## Migration rules
- Prefer additive schema changes
- If any breaking change is unavoidable, bump tool spec version and document compatibility notes.
