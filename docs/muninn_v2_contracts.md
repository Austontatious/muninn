# Muninn v2 Contracts

Date: 2026-05-13

## Contract Version

Foundation schema version:

```text
muninn.v2.foundation.v1
```

This is an adjacent pilot contract, not a replacement for v1 MCP or HTTP contracts.

## Canonical Primitives

### EvidenceRef

Evidence/provenance reference.

Fields:

- `id`
- `evidence_type`
- `ref`
- `excerpt`
- `source_id`
- `metadata`
- `created_at`

### MemoryEvent

Raw event in the durable memory substrate.

Fields:

- `id`
- `event_type`
- `actor`
- `summary`
- `scope_key`
- `payload`
- `evidence`
- `provenance`
- `created_at`

### MemoryCard

Durable memory card.

Fields:

- `id`
- `kind`
- `title`
- `summary`
- `body`
- `status`
- `confidence`
- `scope_key`
- `entity_ids`
- `tags`
- `evidence`
- `provenance`
- `metadata`
- `created_at`
- `updated_at`

### MemoryEntity

Generalized entity record.

Fields:

- `id`
- `entity_type`
- `name`
- `aliases`
- `properties`
- `evidence`
- `provenance`
- `created_at`
- `updated_at`

### MemoryAssociation

Typed association edge.

Fields:

- `id`
- `source_id`
- `source_type`
- `target_id`
- `target_type`
- `association_type`
- `weight`
- `evidence`
- `metadata`
- `created_at`
- `updated_at`

### RecallEvent

Durable record of recall behavior.

Fields:

- `id`
- `query`
- `actor`
- `scope_key`
- `recalled_ids`
- `accepted_ids`
- `suppressed_ids`
- `metadata`
- `created_at`

### OntologyProfile

Profile describing valid domain vocabulary for a pilot/import.

Fields:

- `id`
- `name`
- `version`
- `description`
- `entity_types`
- `card_kinds`
- `association_types`
- `metadata`
- `created_at`
- `updated_at`

## Stable Interfaces

Defined as Python protocols in `src/muninn/v2/core/contracts.py`:

- `MemoryStore`
- `EventLog`
- `CardStore`
- `EntityResolver`
- `AssociationStore`
- `RecallLog`
- `ExportProvider`
- `ImportProvider`

These are intentionally small and storage-neutral.

## SQLite Store

The minimal v2 SQLite implementation stores canonical JSON records in v2-prefixed tables:

- `v2_events`
- `v2_cards`
- `v2_entities`
- `v2_associations`
- `v2_recall_events`
- `v2_ontology_profiles`
- `v2_schema_info`

The JSON record is the canonical pilot payload. Indexed columns exist only for basic lookup/list operations.

## Export Format

`SQLiteMemoryStore.export_bundle()` returns a JSON-compatible object with:

- `schema_version`
- `record_type`
- `counts`
- `ontology_profiles`
- `entities`
- `cards`
- `associations`
- `events`
- `recall_events`

`SQLiteMemoryStore.export_jsonl()` returns one header line followed by one line per canonical record.

## Compatibility Notes

- v2 contracts do not alter v1 contracts.
- v2 IDs may preserve v1 IDs during import to retain relation targets.
- v1 metadata is explicitly marked with `source_system="muninn_v1"`.
- v2 import/export is opt-in and file/path explicit.
- Vector indexes are deferred and should remain derived, not canonical truth.
