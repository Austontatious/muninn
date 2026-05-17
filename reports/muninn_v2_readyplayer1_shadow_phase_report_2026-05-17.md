# Muninn v2 ReadyPlayer1 Shadow Phase Report

Date: 2026-05-17
Scope: ReadyPlayer1 shadow migration/retrieval-eval pilot only

## Executive Summary

ReadyPlayer1 imported cleanly into a fresh explicit Muninn v2 shadow DB at `reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db`.

The migration and derived-index layers are healthy for shadow evaluation: 48 cards and 197 evidence refs migrated, fidelity failures were 0, v1 row counts stayed unchanged, dry-run rebuild wrote nothing, and explicit index write populated 48 derived index rows in the shadow DB only.

The retrieval layer is not ready for single-repo v2 shadow rehydration. Retrieval eval found 0 absent expected records, but 10 expected records missed the top-10 windows. Recall parity remained low, with average overlap ratio 0.1148, 4 v1 records missing from the v2 top-10 windows, and 88 extra v2 records.

Decision: **NO-GO for ReadyPlayer1 v2 shadow rehydration as an agent context source.** It is a GO for continued offline retrieval diagnostics on the shadow DB.

## Commands Run

```bash
PYTHONPATH=src python3 -m muninn.v2.cli pilot-import \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db /mnt/data/Muninn/reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db \
  --space-key repo:5059f410815720ea \
  --project-path /mnt/data/ReadyPlayer1 \
  --out-dir /mnt/data/Muninn/reports/pilots/readyplayer1_v2_shadow_2026-05-17 \
  --strict \
  --write-v2
```

```bash
PYTHONPATH=src python3 -m muninn.v2.cli index-health --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_health
PYTHONPATH=src python3 -m muninn.v2.cli index-rebuild --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_rebuild_dry_run --dry-run
PYTHONPATH=src python3 -m muninn.v2.cli index-rebuild --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_rebuild_write --write-index
PYTHONPATH=src python3 -m muninn.v2.cli index-health --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_health_after_write
```

```bash
PYTHONPATH=src python3 -m muninn.v2.cli retrieval-eval \
  --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db \
  --fixture reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_retrieval_eval_queries.json \
  --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/retrieval_eval
```

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-parity \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db \
  --space-key repo:5059f410815720ea \
  --project-path /mnt/data/ReadyPlayer1 \
  --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/recall_parity \
  --query-file reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_retrieval_eval_queries.json \
  --limit 10 \
  --strict \
  --include-evidence \
  --include-ranking \
  --include-explanations
```

## Import And Fidelity Results

- Mode: `write_v2`
- Space: `repo:5059f410815720ea`
- Migrated cards: 48
- Migrated evidence refs: 197
- Migrated associations: 0
- Created entities: 1
- Created ontology profiles: 1
- Scanned records: 245
- Ledger entries: 247
- Fidelity records checked: 247
- Fidelity failures: 0
- Unsupported records: 0
- Ambiguous records: 0
- Errors: 0

## v1 Immutability Results

The importer and parity command opened v1 through read-only/query-only paths. v1 row counts stayed unchanged.

Representative v1 row counts before/after:

| Table | Before | After | Changed |
| --- | ---: | ---: | --- |
| cards | 510 | 510 | false |
| evidence | 1385 | 1385 | false |
| card_evidence | 1385 | 1385 | false |
| card_relations | 5 | 5 | false |
| interaction_events | 2 | 2 | false |
| card_vectors | 0 | 0 | false |
| vector_index_state | 0 | 0 | false |

The v1 DB size and mtime were unchanged across the pilot: `2236416` bytes, `2026-05-17 10:55:10.320301487 -0700`.

## Index Health And Rebuild Results

Initial index health:

- backend: `json_vector_fallback`
- backend available: true
- eligible records: 48
- indexed records: 0
- missing records: 48
- stale records: 0
- degraded: true
- reason: `sqlite_vec_unavailable_using_json_vector_fallback`, `index_table_missing`, `rebuild_required`

Dry-run rebuild:

- dry run: true
- planned upserts: 48
- planned deletes: 0
- written upserts: 0
- deleted records: 0
- persistent index tables after dry-run: none

Explicit shadow write:

- dry run: false
- planned upserts: 48
- written upserts: 48
- planned deletes: 0
- deleted records: 0
- writes were limited to the explicit shadow v2 DB

Post-write index health:

- eligible records: 48
- indexed records: 48
- missing records: 0
- stale records: 0
- degraded: true only because `sqlite_vec` is unavailable and JSON-vector fallback is active

The absence of `sqlite_vec` does not block core operation or shadow evaluation. It means this pilot measured the explicit fallback path.

## Retrieval Eval Results

- cases: 10
- expected records: 22
- hit records: 12
- mean recall at limit: 0.666667
- record absent count: 0
- retrieval mismatch count: 10
- extra result count: 88

Passing cases:

- Campaign 007A post-reacquisition belief stabilization: 1/1
- Campaign 006A early active ping reacquisition: 1/1
- Campaign 005A fire-control state normalization: 1/1
- Campaign 004A duplicate same-primary torpedo suppression: 2/2
- fire control ready but hold count: 2/2

Failing cases were all retrieval-window mismatches, not missing canonical records:

- torpedo wasted shot rate: 2/4
- sonar clutter wrong binding rate: 0/3
- acoustic clutter wrong binding rate: 1/3
- reacquisition failure taxonomy: 1/3
- ReadyPlayer1 next campaign recommendation: 1/2

## Recall Parity Results

- total queries: 10
- average overlap ratio: 0.1148
- full-overlap queries: 0
- partial-overlap queries: 7
- zero-overlap queries: 3
- total missing from v2: 4
- total extra from v2: 88
- evidence mismatches: 92
- v1 row counts changed: false
- v2 row counts changed: false

Likely mismatch causes reported by the parity tool:

- v2 provisional lexical scoring differs from v1 FTS bm25 ranking/windowing
- v2 provisional matcher searches evidence/body text with different weights than v1 FTS
- some overlapping or one-sided records have evidence availability differences

## Missing, Extra, And Mismatch Categories

- Record-existence failures: 0
- Migration/fidelity failures: 0
- Retrieval-eval mismatches: 10 expected records existed in v2 but missed the top-10 window
- Recall-parity missing-from-v2: 4 v1-returned records did not appear in the v2 top-10 windows
- Recall-parity extra-from-v2: 88 records appeared in v2 top-10 windows but not v1 top-10 windows

This points to retrieval scoring/windowing mismatch, not data loss.

## Output Artifacts

- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/pilot_import_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/pilot_import_report.json`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/record_fidelity_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/migration_ledger.jsonl`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/migration_checksums.json`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_health/index_health_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_rebuild_dry_run/index_rebuild_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_rebuild_write/index_rebuild_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/index_health_after_write/index_health_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/retrieval_eval/retrieval_eval_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/recall_parity/recall_parity_report.md`
- `reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_retrieval_eval_queries.json`

Generated DB artifacts under `reports/pilots/readyplayer1_v2_shadow_2026-05-17/` are local shadow-run artifacts and must not be committed.

## Go / No-Go

**NO-GO** for ReadyPlayer1 v2 shadow rehydration as an agent context source.

Reason: the v2 shadow data is complete, but retrieval quality is not yet reliable enough. Important ReadyPlayer1 metric and taxonomy queries still miss expected cards in top-10 windows, and v1/v2 recall parity overlap remains low.

**GO** for continued offline v2 retrieval diagnostics using the generated shadow DB and fixture.

## Next Recommended Task

Analyze the five failing retrieval-eval cases and compare derived-vector scoring, lexical fallback scoring, and v1 FTS/BM25 results side by side. The next task should produce a retrieval-design recommendation, not tune live v1 or change production defaults.

## Retrieval Design Addendum

Follow-up retrieval design work is recorded in `reports/muninn_v2_readyplayer1_retrieval_design_report_2026-05-17.md`.

That work implemented v2-only explainable hybrid retrieval for diagnostic/eval paths. ReadyPlayer1 retrieval-eval improved from 12/22 hits and mean recall@10 `0.666667` to 22/22 hits and mean recall@10 `1.0`, with retrieval mismatches reduced from 10 to 0 and extra results reduced from 88 to 35.

Updated decision: **GO with constraints** for ReadyPlayer1 v2 shadow rehydration preview/evaluation only. This remains non-production, requires explicit v2 shadow DB paths, and does not change live v1 retrieval or MCP/Codex defaults.
