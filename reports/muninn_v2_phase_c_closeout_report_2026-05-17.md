# Muninn v2 Phase C Closeout Report - 2026-05-17

## Executive Summary

Phase C is GO for moving to Phase D offline recall/reinforcement mechanics, with strict constraints. It remains NO-GO for live agent context, MCP integration, bridge work, or cutover.

The final independent pilot used Lexi (`/mnt/data/Lex`, `repo:0c321b2a6f183a95`) because it had richer v1 memory coverage than LAILA and a clear repo-remote identity. Lexi passed fresh v1-to-v2 shadow import, fidelity, derived-index rebuild, RehydrateResponseV1 preview generation, and offline agent-context audit without retrieval or supplement-selection tuning.

## Lexi Pilot Result

- Shadow directory: `reports/pilots/lexi_v2_shadow_2026-05-17_final/`
- Shadow DB: `reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db`
- Import: 79 cards, 155 evidence refs, 2 associations, 1 entity, 1 ontology profile
- Fidelity: 238 records checked, 0 failures, 0 unsupported, 0 ambiguous
- Initial index health: 77 eligible, 0 indexed, rebuild required
- Dry-run rebuild: 77 planned upserts, 0 writes
- Write rebuild: 77 written upserts to the shadow DB only
- Post-write index health: 77 eligible, 77 indexed, 0 missing, 0 stale
- Backend: `json_vector_fallback`, degraded only because `sqlite_vec` is unavailable

## Preview And Audit

Final preview query:

`resume Lexi current production audit and runtime modernization state and next steps`

The preview emitted a valid `RehydrateResponseV1` JSON artifact plus Markdown. It selected 3 primary cards and 5 continuity supplements. The top primary result was the current `Lexi production audit verdict 2026-05-17`; Phase 6 runtime resilience and Phase 1-5 modernization context were included as supplements.

Agent-context audit:

- Cases: 1
- GO cases: 1
- Mean v2 coverage: 1.0
- Missing required needs: 0
- Stale flags: 0
- Confusing flags: 0
- Over-included cards: 1
- Same-good-decision supported: yes

The single over-included supplement was the older Lex end-to-end review card. It is adjacent and not blocking; no tuning was justified.

## V1 Immutability Note

During the first Lexi run, the live v1 DB changed externally: a new card, `Lexi production audit verdict 2026-05-17`, appeared at `2026-05-17 21:24:31` UTC with three evidence refs. I did not issue a Muninn completion-card write for this task.

To avoid evaluating a stale shadow snapshot, I re-baselined and reran Lexi into a fresh final shadow directory. During the final import/index/preview/audit window, v1 remained unchanged:

- DB size: 2265088 bytes
- DB mtime: `2026-05-17 14:24:31.655443750 -0700`
- Cards: 516
- Evidence: 1408
- Card/evidence links: 1408
- Interaction events: 2

All controlled writes went only to the explicit Lexi v2 shadow DB and report directories.

## Cross-Pilot Comparison

| Pilot Set | Cases | GO | Mean Coverage | Missing Required | Confusing Flags | Over-Included |
|---|---:|---:|---:|---:|---:|---:|
| Friday + ReadyPlayer1 regression | 2 | 2 | 1.0 | 0 | 1 | 5 |
| SubSim + Sindri tightened | 2 | 2 | 1.0 | 0 | 0 | 1 |
| Lexi final independent | 1 | 1 | 1.0 | 0 | 0 | 1 |
| Phase C total after tightening | 5 | 5 | 1.0 | 0 | 1 | 7 |

Phase C now covers five project-context cases across Friday, ReadyPlayer1, SubSim, Sindri, and Lexi. The harness generalized beyond the original pilots and the final independent pilot did not require code or scoring changes.

## Phase D GO Criteria

Phase D may start only as offline recall/reinforcement mechanics if:

- It uses explicit v2 DB paths and report artifacts only.
- It preserves `RehydrateResponseV1` and agent-context-audit contracts.
- It does not change v1 schema, live MCP, Codex defaults, or production DBs.
- It measures recall/reinforcement behavior against fixed expected-needs fixtures before affecting context selection.
- It treats vectors as optional derived indexes and accepts `sqlite_vec` absence as degraded fallback state.

## Phase D NO-GO / Stop Criteria

Stop Phase D work if:

- Any pilot drops below 0.85 v2 coverage or misses required needs.
- Any blocking stale/confusing term appears in rendered context.
- Any recall/reinforcement path requires v1 writes or live default changes.
- Supplement noise increases materially without an explainable general reason.
- Generated DBs or other shadow artifacts are accidentally staged for commit.

## Decision

- Phase C closeout: GO
- Phase D offline recall/reinforcement mechanics: GO with constraints
- Live agent context: NO-GO
- Bridge/cutover: NO-GO

Recommended next task: start Phase D with a read-only recall/reinforcement design that consumes `RehydrateResponseV1` and audit outputs, then runs offline against the existing five-pilot fixture set before any new retrieval or context-selection behavior is considered.
