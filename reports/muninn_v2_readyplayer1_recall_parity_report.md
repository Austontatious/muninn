# Muninn v2 ReadyPlayer1 Recall Parity Report

Date: 2026-05-13

## Executive Summary

The opt-in ReadyPlayer1 recall parity run completed safely. It opened both v1 and v2 SQLite databases read-only/query-only, wrote only parity artifacts, and reported no v1 or v2 row-count changes.

This run measures retrieval overlap only. It does not tune v2 retrieval, does not change live MCP/Codex behavior, and does not make v2 the default recall path.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-parity \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/scratch_v2.db \
  --space-key repo:5059f410815720ea \
  --project-path /mnt/data/ReadyPlayer1 \
  --out-dir /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/recall_parity \
  --query-file /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/readyplayer1_recall_queries.json \
  --limit 10 \
  --strict \
  --include-evidence \
  --include-ranking \
  --include-explanations
```

## Retrieval Paths

- v1 path: `muninn.human_memory.cards.cards_search` using FTS5/BM25.
- v2 path: provisional lexical matcher over v2 `MemoryCard` title, summary, body, tags, and evidence text.

The v2 path is intentionally provisional and explainable. It is not Mimir-style salience/cognition and is not a production recall path.

## Aggregate Metrics

- total queries: 10
- average overlap ratio: 0.1148
- full-overlap queries: 0
- partial-overlap queries: 7
- zero-overlap queries: 3
- total missing from v2: 4
- total extra from v2: 88
- ranking deltas: 12
- evidence checks: 104
- evidence OK: 12
- evidence mismatches: 92

The high extra-from-v2 count is expected for this crude v2 matcher because it returns a full top-10 window for broad token matches while v1 FTS often returns fewer exact matches.

## Query Summary

| Query | v1 | v2 | Overlap | Ratio | Missing | Extra |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Campaign 007A post-reacquisition belief stabilization | 1 | 10 | 1 | 0.1000 | 0 | 9 |
| Campaign 006A early active ping reacquisition | 1 | 10 | 1 | 0.1000 | 0 | 9 |
| Campaign 005A fire-control state normalization | 1 | 10 | 1 | 0.1000 | 0 | 9 |
| Campaign 004A duplicate same-primary torpedo suppression | 0 | 10 | 0 | 0.0000 | 0 | 10 |
| fire control ready but hold count | 1 | 10 | 0 | 0.0000 | 1 | 10 |
| torpedo wasted shot rate | 4 | 10 | 4 | 0.4000 | 0 | 6 |
| sonar clutter wrong binding rate | 4 | 10 | 2 | 0.1667 | 2 | 8 |
| acoustic clutter wrong binding rate | 3 | 10 | 2 | 0.1818 | 1 | 8 |
| reacquisition failure taxonomy | 1 | 10 | 1 | 0.1000 | 0 | 9 |
| ReadyPlayer1 next campaign recommendation | 0 | 10 | 0 | 0.0000 | 0 | 10 |

## Missing From v2

Missing here means v1 returned the record in its top-N window and the provisional v2 matcher did not.

- `fire control ready but hold count`
  - `fbcac688-f952-477f-87ca-ea7860c4f396`
- `sonar clutter wrong binding rate`
  - `0afb7524-b5b6-4e78-9a56-a08915eb895e`
  - `fbcac688-f952-477f-87ca-ea7860c4f396`
- `acoustic clutter wrong binding rate`
  - `0afb7524-b5b6-4e78-9a56-a08915eb895e`

These are retrieval-window mismatches, not migration loss: the ReadyPlayer1 pilot import fidelity report showed 48/48 cards migrated and 0 fidelity failures.

## Extra From v2

The v2 provisional matcher returned 88 records that v1 did not return for the same top-10 windows. This is mostly a scoring/windowing mismatch, not a record-existence issue.

Likely causes:

- v2 provisional lexical matching is broader than v1 FTS/BM25.
- v2 searches body and evidence text with different weights.
- v2 always returns top token matches up to the limit when broad terms match.

## Evidence Findings

Evidence parity on overlapping cards was clean where records overlapped: 12 checks passed. The mismatch count is high because missing/extra one-sided records are included as evidence parity mismatches.

No evidence loss was observed for overlapping returned cards in this run.

## Row-Count Safety

v1 row counts changed: false

- `cards`: 507 before, 507 after
- `evidence`: 1372 before, 1372 after
- `card_evidence`: 1372 before, 1372 after
- `card_relations`: 5 before, 5 after
- `interaction_events`: 2 before, 2 after

v2 row counts changed: false

- `v2_cards`: 48 before, 48 after
- `v2_entities`: 1 before, 1 after
- `v2_ontology_profiles`: 1 before, 1 after
- `v2_associations`: 0 before, 0 after
- `v2_recall_events`: 0 before, 0 after

## Output Artifacts

- `reports/pilots/readyplayer1_v2_import/recall_parity/recall_parity_report.md`
- `reports/pilots/readyplayer1_v2_import/recall_parity/recall_parity_report.json`
- `reports/pilots/readyplayer1_v2_import/recall_parity/recall_parity_results.jsonl`
- `reports/pilots/readyplayer1_v2_import/recall_parity/missing_from_v2.json`
- `reports/pilots/readyplayer1_v2_import/recall_parity/extra_from_v2.json`
- `reports/pilots/readyplayer1_v2_import/recall_parity/ranking_deltas.json`
- `reports/pilots/readyplayer1_v2_import/recall_parity/evidence_parity_report.json`
- `reports/pilots/readyplayer1_v2_import/recall_parity/readyplayer1_recall_queries.json`

## Recommendation

Do not tune v2 retrieval yet. First add a record-existence parity view next to retrieval parity so each query can distinguish:

1. v1 returned record and v2 record exists but was not retrieved
2. v1 returned record and v2 record is actually missing
3. v2 returned extra record that exists only because provisional lexical recall is broad

That distinction will make the next retrieval design decision more precise.
