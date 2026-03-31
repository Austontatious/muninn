# Procedural Memory in Muninn

## Overview
Muninn now supports structured procedural memory as a first-class card subtype.

- Card kind: `procedure.card`
- Canonical structure: `cards.context_json.procedure`
- Lineage preserved through existing card relations (`supersedes`, etc.)

This extends existing card/evidence/relations primitives and does not introduce a parallel storage subsystem.

## Procedure schema (structured)

`context_json.procedure` stores:
- `schema_version`
- `trigger_conditions`
- `scope` (`type`, optional `id`)
- `steps` (ordered)
- `tool_requirements`
- `pitfalls`
- `verification_checks`
- `confidence`
- `validation_status` (`candidate|validated|needs_review|deprecated`)
- `task_types`
- `provenance`
- `supersedes_card_id`
- `superseded_by_card_id`

Card-level `created_at` / `updated_at` fields provide temporal metadata.

## Retrieval and ranking

`query_procedure_cards(...)` provides bounded procedure retrieval with ranking that combines:
- confidence
- validation status bonus/penalty
- lexical overlap against task/context
- task-type and tool overlap bonuses
- scope bonus/penalty
- staleness penalty
- instability/deprecated penalties

Returned payload includes both detailed and compact procedure forms for prompt-efficient injection.
Returned rows include `selection_reasons` for debugging why a procedure was selected.

## Reflection ingestion

`ingest_procedure_reflection(...)` consumes outcome summaries and applies rule-based decisions:
- create a new procedure candidate
- update an existing matching procedure
- attach evidence-only provenance when match is strong and no material guidance changed
- supersede an existing procedure when guidance materially changes
- lower confidence / mark `needs_review` after failure signals
- mark procedure `deprecated` after repeated failure evidence
- ignore non-reusable reflections

Deterministic quality gates:
- new procedure creation requires non-trivial signal (multi-step/tool/correction/generalizable context)
- low-signal reflections are ignored instead of creating clutter

### Structured Evidence Contract

Procedure reflection metadata may include `metadata.structured_evidence` as a list of evidence objects.
This contract is strict and mirrors Muninn card upsert evidence input:

- required object key: `type`
- optional keys: `ref`, `excerpt`, `meta`
- allowed `type`: `chat|log|diff|file|url|commit|test`
- `ref` and `excerpt` must be strings when provided
- `meta` must be an object when provided
- extra keys are rejected as malformed evidence entries

Malformed entries are not silently coerced. They are skipped and surfaced via warning codes/messages in reflection results.

## HTTP API surface

These endpoints are exposed in `src/muninn/api.py`:
- `POST /v0/memory/procedures/retrieve`
- `POST /v0/memory/procedures/reflect`

Both use the human-memory DB (`MUNINN_HUMAN_MEMORY_DB_PATH` or default path) and explicit `space_key` scoping.
