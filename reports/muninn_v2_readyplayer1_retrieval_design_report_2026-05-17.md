# Muninn v2 ReadyPlayer1 Retrieval Design Report

Date: 2026-05-17
Scope: Muninn v2 retrieval diagnostics only

## Executive Summary

ReadyPlayer1 retrieval failure was a scoring/windowing issue, not migration loss. The baseline vector/fallback eval had 12/22 hits, mean recall@10 `0.666667`, 10 retrieval mismatches, and 88 extra results.

The v2 hybrid retrieval implementation fixes the ReadyPlayer1 fixture without ReadyPlayer1-specific expected-ID hardcoding. Final retrieval eval has 22/22 hits, mean recall@10 `1.0`, 0 record-absent, 0 retrieval mismatches, and 35 extra results.

Decision: **GO with constraints** for ReadyPlayer1 v2 shadow rehydration preview/evaluation. This is not production cutover and does not change live Codex/MCP defaults.

## Baseline Metrics

- cases: 10
- expected records: 22
- hit records: 12
- mean recall@10: `0.666667`
- record absent: 0
- retrieval mismatches: 10
- extra results: 88
- recall-parity average overlap: `0.1148`

## Failure Analysis Summary

- All expected records existed in v2, so failures were not migration loss.
- Retrieval eval used vector-only results whenever a derived index existed.
- The deterministic hash-vector fallback was too weak for short metric/taxonomy/campaign queries.
- Existing lexical tokenization did not split snake_case metric names such as `sonar_clutter_wrong_binding_rate` into natural-language query tokens.
- Broad domain tokens flooded top-10 windows without enough specificity penalty.

Detailed per-query analysis is in `reports/muninn_v2_readyplayer1_retrieval_failure_analysis_2026-05-17.md` and `.json`.

## Retrieval Contract Summary

- Inputs: query text, optional space/project, optional limit/filters/profile, optional evidence/explanation expansion, retrieval mode.
- Candidate sources: title, summary, body, tags, evidence, space, recency, salience, and optional vector rescue.
- Scoring: deterministic additive components with explicit penalties for broad/low-specificity and evidence-only weak matches.
- Explanations: each result reports candidate sources, matched tokens/fields, score components, penalties, and vector usage.
- Boundary: retrieval diagnostics only; no Mimir cognition, no live v1 behavior, no MCP/Codex default changes.

## Implemented Scoring Changes

- Added `src/muninn/v2/retrieval/scoring.py` for deterministic query normalization and IDF helpers.
- Added `src/muninn/v2/retrieval/hybrid_recall.py` for explainable hybrid retrieval.
- Updated retrieval eval to support `--retrieval-mode hybrid|lexical|vector`; default is `hybrid` for diagnostics.
- Updated recall parity to support optional `--retrieval-mode hybrid` while preserving lexical default.
- Added compact top-result explanations to retrieval-eval reports.

## Iteration History

| Iteration | Hits | Mean recall@10 | Mismatches | Extras | Parity overlap | Parity missing | Parity extra |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline vector/fallback | 12/22 | 0.666667 | 10 | 88 | 0.1148 | 4 | 88 |
| hybrid iter 1 | 22/22 | 1.0 | 0 | 65 | 0.2297 | 0 | 71 |
| hybrid iter 2 | 22/22 | 1.0 | 0 | 35 | 0.3212 | 0 | 41 |

Hybrid iter 2 has zero overlap failures for all queries where v1 returned at least one result: `0` of `8`.

## Final Per-Case Results

| Query | Hits | Expected ranks | Returned |
| --- | ---: | --- | ---: |
| Campaign 007A post-reacquisition belief stabilization | 1/1 | 0afb7524:1 | 6 |
| Campaign 006A early active ping reacquisition | 1/1 | fbcac688:1 | 3 |
| Campaign 005A fire-control state normalization | 1/1 | bef388b3:1 | 5 |
| Campaign 004A duplicate same-primary torpedo suppression | 2/2 | 719fafb5:2, 1eb0763c:1 | 7 |
| fire control ready but hold count | 2/2 | bef388b3:3, 719fafb5:1 | 4 |
| torpedo wasted shot rate | 4/4 | 0afb7524:3, fbcac688:2, 719fafb5:1, 1eb0763c:4 | 4 |
| sonar clutter wrong binding rate | 3/3 | 0afb7524:2, fbcac688:3, 2656c35f:1 | 8 |
| acoustic clutter wrong binding rate | 3/3 | 0afb7524:5, 8db59c21:1, 719fafb5:2 | 7 |
| reacquisition failure taxonomy | 3/3 | 0afb7524:2, fbcac688:3, e1959e49:1 | 3 |
| ReadyPlayer1 next campaign recommendation | 2/2 | 0afb7524:5, fbcac688:2 | 10 |

## Remaining Failure Cases

None in retrieval eval. Recall parity still has two zero-overlap rows only because v1 returned no records for those query strings, making overlap impossible by definition. v2 hybrid returned reasonable candidates for both.

## GO / NO-GO

**GO with constraints** for ReadyPlayer1 v2 shadow rehydration preview/evaluation.

Constraints:

- Use only explicit v2 shadow DB paths.
- Keep v1 as live source of truth.
- Do not change MCP/Codex defaults.
- Keep generated DBs and bulky pilot artifacts uncommitted.
- Treat this as single-repo evidence; repeat on another repo before any broader cutover discussion.

## Next Recommended Task

Run the same hybrid retrieval contract against at least one additional migrated repo and add a small shadow rehydration preview command that renders top-N hybrid results without changing Codex defaults.
