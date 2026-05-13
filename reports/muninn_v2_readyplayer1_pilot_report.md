# Muninn v2 ReadyPlayer1 Pilot Report

Date: 2026-05-13

## Executive Summary

The non-empty ReadyPlayer1 dry-run pilot completed safely.

This was a dry-run only. It did not create the requested v2 DB and did not mutate v1 during the pilot verification window. The command wrote reports, JSON/JSONL exports, a migration ledger, deterministic checksums, a side-by-side record fidelity report, and a scratch v2 DB under `reports/pilots/readyplayer1_v2_import/`.

Completion-memory writes were intentionally not performed during this run so they could not affect final row-count reporting.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli pilot-import \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/readyplayer1_v2.db \
  --space-key repo:5059f410815720ea \
  --project-path /mnt/data/ReadyPlayer1 \
  --out-dir /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import \
  --dry-run \
  --strict
```

## Space Identity

- project path: `/mnt/data/ReadyPlayer1`
- git remote: `https://github.com/Austontatious/ReadyPlayer1.git`
- normalized remote: `https://github.com/austontatious/readyplayer1`
- canonical v1 space key: `repo:5059f410815720ea`
- path alias: `path:95e200a57f7e9605`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`

The selector was unambiguous. `ambiguous_records.json` contains no records.

## Migration Counts

- scanned cards: 48
- migrated cards: 48
- migrated evidence refs: 197
- migrated associations: 0
- migrated events: 0
- created entities: 1
- created ontology profiles: 1
- unsupported records in selected space: 0
- migration ledger entries: 247
- fidelity records checked: 247
- fidelity failures: 0

ReadyPlayer1 currently has no v1 `card_relations` or `interaction_events` scoped to the selected space.

## v1 Immutability Verification

All v1 row counts were unchanged during the pilot.

Relevant counts:

- `spaces`: 33 before, 33 after
- `cards`: 507 before, 507 after
- `evidence`: 1372 before, 1372 after
- `card_evidence`: 1372 before, 1372 after
- `card_relations`: 5 before, 5 after
- `interaction_events`: 2 before, 2 after
- `card_vectors`: 0 before, 0 after
- `vector_index_state`: 0 before, 0 after

Selected-space counts after the run:

- ReadyPlayer1 cards: 48
- ReadyPlayer1 distinct evidence refs: 197
- ReadyPlayer1 relations: 0
- ReadyPlayer1 interaction events: 0

## Checksums

- source aggregate: `875dca8bf01992fd12d3c80660f004a71057ef043c6327568a37be6b8ce0e8d4`
- target aggregate: `495804303977237fa69724bd8eccc2df39d4a95dce700daf41bd07d35d3a385d`
- v2 export bundle: `65454134b27e9ec649077460fa51d2c330ddae583988491c575bc1a15b2b83b3`
- migration ledger: `f9ab3d2f03a6fc27741790e290851c7eccdce80275999eac6ff4ed95db602459`
- fidelity report: `95440ea1fc02c5d07023f3ea37ddce5f60848b7dbf76e5f4b5320e4c4ced1b0f`

## Fidelity Summary

- fidelity passed: true
- records checked: 247
- failures: 0
- cards checked/passed: 48 / 48
- evidence refs checked/passed: 197 / 197
- associations checked/passed: 0 / 0
- ontology profiles checked: 1
- entities checked: 1

## Output Artifacts

- `reports/pilots/readyplayer1_v2_import/pilot_import_report.md`
- `reports/pilots/readyplayer1_v2_import/pilot_import_report.json`
- `reports/pilots/readyplayer1_v2_import/v1_row_count_before_after.json`
- `reports/pilots/readyplayer1_v2_import/unsupported_records.json`
- `reports/pilots/readyplayer1_v2_import/ambiguous_records.json`
- `reports/pilots/readyplayer1_v2_import/migrated_cards.jsonl`
- `reports/pilots/readyplayer1_v2_import/migrated_events.jsonl`
- `reports/pilots/readyplayer1_v2_import/migrated_entities.jsonl`
- `reports/pilots/readyplayer1_v2_import/migrated_associations.jsonl`
- `reports/pilots/readyplayer1_v2_import/evidence_refs.jsonl`
- `reports/pilots/readyplayer1_v2_import/ontology_profile.json`
- `reports/pilots/readyplayer1_v2_import/v2_export_bundle.json`
- `reports/pilots/readyplayer1_v2_import/v2_export_bundle.jsonl`
- `reports/pilots/readyplayer1_v2_import/migration_ledger.jsonl`
- `reports/pilots/readyplayer1_v2_import/migration_checksums.json`
- `reports/pilots/readyplayer1_v2_import/record_fidelity_report.json`
- `reports/pilots/readyplayer1_v2_import/record_fidelity_report.md`
- `reports/pilots/readyplayer1_v2_import/scratch_v2.db`

The requested v2 DB path `reports/pilots/readyplayer1_v2_import/readyplayer1_v2.db` was not created because the run was dry-run mode.

## Known Gaps

- This pilot did not exercise association mapping because ReadyPlayer1 has no card relations.
- Interaction events remain unsupported in this slice.
- v1 vectors and vector index state remain unsupported derived state.
- There is still no recall parity comparison between v1 and v2.
- No production consumer reads from v2.

## Recommended Next Slice

Add a side-by-side recall parity command that compares v1 retrieval output with v2 record projections for ReadyPlayer1 without changing live MCP/Codex defaults.
