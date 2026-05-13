# Muninn v2 Pilot Import Report

- Mode: `dry_run`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- Requested v2 DB: `/mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/readyplayer1_v2.db`
- Written v2 DB: `/mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/scratch_v2.db`
- Space key: `repo:5059f410815720ea`
- Project path: `/mnt/data/ReadyPlayer1`
- v1 row counts changed: `no`

## Counts

- Scanned cards: 48
- Migrated cards: 48
- Evidence refs: 197
- Associations: 0
- Entities: 1
- Ontology profiles: 1
- Unsupported records: 0
- Ledger entries: 247
- Fidelity records checked: 247
- Fidelity failures: 0

## Safety

The v1 database was opened using SQLite read-only mode and `PRAGMA query_only=ON`.
The requested v2 DB is written only when `--write-v2` is passed.

## Unsupported Records

- `interaction_events`: 0 (present=true)
- `card_vectors`: 0 (present=true)
- `vector_index_state`: 0 (present=true)
