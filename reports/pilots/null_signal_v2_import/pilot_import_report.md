# Muninn v2 Pilot Import Report

- Mode: `dry_run`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- Requested v2 DB: `/mnt/data/Muninn/reports/pilots/null_signal_v2_import/null_signal_v2.db`
- Written v2 DB: `/mnt/data/Muninn/reports/pilots/null_signal_v2_import/scratch_v2.db`
- Space key: `repo:8086caa7ff98deef`
- Project path: `/mnt/data/Null_Signal`
- v1 row counts changed: `no`

## Counts

- Scanned cards: 0
- Migrated cards: 0
- Evidence refs: 0
- Associations: 0
- Entities: 1
- Ontology profiles: 1
- Unsupported records: 0

## Safety

The v1 database was opened using SQLite read-only mode and `PRAGMA query_only=ON`.
The requested v2 DB is written only when `--write-v2` is passed.

## Unsupported Records

- `interaction_events`: 0 (present=true)
- `card_vectors`: 0 (present=true)
- `vector_index_state`: 0 (present=true)
