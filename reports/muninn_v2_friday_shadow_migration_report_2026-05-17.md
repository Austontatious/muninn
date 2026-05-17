# Muninn v2 Friday Shadow Migration Report - 2026-05-17

## Executive Summary

- Friday v1 -> v2 shadow migration succeeded with 48 cards, 152 evidence refs, 1 association, 1 entity, and 1 ontology profile.
- Fidelity failures: `0`; unsupported: `0`; ambiguous: `0`; v1 row counts, size, and mtime stayed unchanged through import/eval.
- Derived index rebuild wrote 47 active eligible records into the explicit shadow DB only.
- Hybrid retrieval eval passed: 12 cases, 18 expected records, 18 hits, mean recall@10 `1.0`, record absent `0`, mismatches `0`, extras `71`.
- Decision: GO for offline diagnostics, GO with constraints for v2 shadow rehydration preview, NO-GO for live agent context.

## Friday Identity Confirmation

- Space key: `repo:f8cc7f64d3636a4e` exists with label `friday`.
- Space root path: `/mnt/data/friday`.
- Friday git root: `/mnt/data/friday`; remote: `https://github.com/Austontatious/friday.git`.
- v1 Friday card count: 48 total, 47 active; evidence rows: 152; card-evidence links: 152.
- Selector ambiguity: none for requested repo key. A legacy `friday` space exists with 0 cards and was not selected.

## Import And Fidelity

- Migrated cards: 48
- Migrated evidence refs: 152
- Migrated associations: 1
- Created entities: 1
- Ontology profiles: 1
- Fidelity records checked: 203
- Fidelity failures: 0

## v1 Immutability

- Baseline and final size: `2236416` bytes.
- Baseline and final mtime: `2026-05-17 11:31:40.044628767 -0700`.
- Table row counts unchanged: `true`.
- Pilot report `v1_row_counts_changed`: `false`.

## Index Health And Rebuild

- Initial: eligible=47 indexed=0 missing=47 stale=0 backend=`json_vector_fallback` degraded=`true`.
- Dry-run: planned_upserts=47 written_upserts=0 planned_deletes=0.
- Write: planned_upserts=47 written_upserts=47 deleted=0.
- Post-write: eligible=47 indexed=47 missing=0 stale=0 backend=`json_vector_fallback` degraded=`true`.
- sqlite_vec is unavailable; fallback JSON vector index is complete and degraded by design.

## Retrieval Fixture

- Fixture: `/mnt/data/Muninn/reports/pilots/friday_v2_shadow_2026-05-17/friday_retrieval_eval_queries.json`
- Cases: 12
- Expected records: 18
- Fixture was built from migrated Friday cards and includes implementation, runbook, architecture/interface, constraint, Docker/network, eval, and runtime-budget themes.
- Two expected IDs were corrected after an initial eval exposed fixture typos; corrected IDs were verified in `migrated_cards.jsonl`.

## Retrieval Eval Metrics

| Mode | Hits | Expected | Mean recall@10 | Absent | Mismatch | Extras |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 18 | 18 | 1.0 | 0 | 0 | 71 |
| lexical | 18 | 18 | 1.0 | 0 | 0 | 102 |
| vector | 17 | 18 | 0.958333 | 0 | 1 | 103 |

## Recall Parity

- Lexical parity: average_overlap=0.049999999999999996 partial=6 zero=6 missing_from_v2=0 extra_from_v2=114.
- Hybrid parity: average_overlap=0.07777777777777778 partial=6 zero=6 missing_from_v2=0 extra_from_v2=81.
- Initial parity attempt with the retrieval fixture failed safely because recall-parity expects a top-level `queries` list; rerun used `friday_recall_queries.json`.

## Shadow Rehydration Preview

- Preview JSON: `/mnt/data/Muninn/reports/pilots/friday_v2_shadow_2026-05-17/shadow_rehydrate_preview/shadow_rehydrate_preview.json`
- Preview Markdown: `/mnt/data/Muninn/reports/pilots/friday_v2_shadow_2026-05-17/shadow_rehydrate_preview/shadow_rehydrate_preview.md`
- Hybrid primary cards: 3
- Recent supplement cards: 9
- Total preview cards: 12
- Adequate for Friday shadow preview: `true`.
- Adequate for live agent context: `false`.
- Caveat: pure broad hybrid retrieval returned only 3 high-specificity cards, so the preview uses a report-only recent supplement. This should become a formal v2 command before live use.

## GO/NO-GO Decision

- Offline diagnostics: GO.
- v2 shadow rehydration preview: GO with constraints.
- Live agent context: NO-GO.

## Risks And Blockers

- sqlite_vec unavailable; JSON vector fallback is complete but degraded.
- Recall parity overlap remains low because v1 FTS and v2 hybrid rank different fields/windows.
- Shadow preview staging is generated report-only, not a durable CLI contract.
- v2 must remain opt-in; no live Friday/Codex/MCP defaults changed.

## Recommended Next Task

Implement a v2-only `shadow-rehydrate-preview` command with explicit staged hybrid plus recent fallback semantics, tests, and docs; then rerun Friday and ReadyPlayer1 previews through the same command.

## Formal Preview Command Addendum

Follow-up work added the v2-only `shadow-rehydrate-preview` command and reran Friday through it:

- Output: `reports/pilots/friday_v2_shadow_2026-05-17/shadow_rehydrate_preview_command/`
- Result: 3 primary hybrid matches, 9 recent in-scope supplements, 12 total cards, usable=true.
- Assessment: GO for Friday v2 shadow rehydration preview/evaluation. The broad resume query still depends on the recent supplement stage for the most current operational cards.
- Live agent context remains NO-GO without review, cutover planning, and rollback planning.
