# Muninn v2 Pilot Import Report

- Mode: `write_v2`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- Requested v2 DB: `reports/pilots/sindri_v2_shadow_2026-05-17/sindri_shadow_v2.db`
- Written v2 DB: `reports/pilots/sindri_v2_shadow_2026-05-17/sindri_shadow_v2.db`
- Space key: `path:316f4f67d061cbdd`
- Project path: `/mnt/data/Sindri`
- v1 row counts changed: `no`

## Counts

- Scanned cards: 26
- Migrated cards: 26
- Evidence refs: 76
- Associations: 0
- Entities: 1
- Ontology profiles: 1
- Unsupported records: 0
- Ledger entries: 104
- Fidelity records checked: 104
- Fidelity failures: 0

## Safety

The v1 database was opened using SQLite read-only mode and `PRAGMA query_only=ON`.
The requested v2 DB is written only when `--write-v2` is passed.

## Unsupported Records

- `interaction_events`: 0 (present=true)
- `card_vectors`: 0 (present=true)
- `vector_index_state`: 0 (present=true)
