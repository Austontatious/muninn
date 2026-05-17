# Muninn v2 Derived Indexes

Muninn v2 treats vector indexes as optional derived infrastructure.

Canonical truth remains:
- memory events
- cards
- entities
- associations
- evidence and provenance
- recall events
- ontology profiles
- append/export records

Vectors are not canonical memory. They are rebuildable diagnostic or retrieval-assist indexes derived from canonical v2 records.

## Safety Contract

- v2 index commands require an explicit `--v2-db` path.
- v2 index commands never open or mutate production v1 DBs.
- importing `muninn.v2` does not create index tables or require `sqlite_vec`.
- derived index tables are created only by explicit `index-rebuild --write-index`.
- `index-rebuild` is dry-run by default.
- sqlite_vec absence is allowed and reported as degraded fallback status.
- lexical fallback is provisional and labeled as fallback.

## Commands

```bash
PYTHONPATH=src python3 -m muninn.v2.cli index-health \
  --v2-db /path/to/v2.db \
  --out-dir /path/to/reports

PYTHONPATH=src python3 -m muninn.v2.cli index-rebuild \
  --v2-db /path/to/v2.db \
  --out-dir /path/to/reports

PYTHONPATH=src python3 -m muninn.v2.cli index-rebuild \
  --v2-db /path/to/v2.db \
  --out-dir /path/to/reports \
  --write-index
```

`index-health` writes:
- `index_health_report.json`
- `index_health_report.md`

`index-rebuild` writes:
- `index_rebuild_report.json`
- `index_rebuild_report.md`

## Status Fields

`VectorIndexStatus` reports:
- `backend`
- `backend_available`
- `eligible_records`
- `indexed_records`
- `missing_records`
- `stale_records`
- `degraded`
- `reason`

`eligible_records` are active v2 cards. `missing_records` means canonical cards do not yet have matching derived index rows. `stale_records` means the derived row no longer matches the canonical card content hash, update timestamp, model, or dimension.

## Boundary

Mimir may later consume v2 index-health and retrieval-eval reports for topology or cognition work. Muninn v2 should not grow salience propagation, spreading activation, motif detection, or hidden-link discovery inside the derived-index layer.
