# Muninn v2 Phase I-B Replay Fixture Closeout

Generated: 2026-05-18T01:52:16Z

## Executive Summary

- LIMITED repos targeted: 15
- Replay gates GO: 15
- Replay gates NO-GO: 0
- No-source repos classified: 14
- Need memory-space creation: 8
- Scoped out: 1
- Duplicate/alias: 1
- Inactive/archive: 4

## Required Statuses

- phase_i_b_replay_fixtures: `GO`
- production_migration_excluding_muninn: `NOT_READY`
- muninn_production_migration: `EXCLUDED_PENDING_SEPARATE_PLAN`
- live_cutover: `NO-GO`
- writes: `NO-GO`
- adaptive_default: `NO-GO`

## Replay Fixture Results

| Repo | Gate | Tasks | Mode runs | Audit failures | Contamination | Adaptive default | Evidence required |
|---|---|---:|---:|---:|---:|---:|---|
| Althing | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Aquagenesys | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| austontatious-dev | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Bifrost | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Brilliant | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Echo | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Fenrir | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Heimdall | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Hrafnar | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| LAILA | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Mimir | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| Muninn | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| portfolio | GO | 1 | 3 | 0 | 1/1 | 0 | False |
| Sindri | GO | 1 | 3 | 0 | 1/1 | 0 | True |
| SubSim | GO | 1 | 3 | 0 | 1/1 | 0 | True |

All replay fixtures are minimal project-specific checks for identity scope plus one selected current-state memory. They verify bridge audit hashes, contamination denial, visible degradation markers, and adaptive-default-off behavior through the existing replay gate. Portfolio has no migrated evidence refs, so its replay policy does not require evidence; the failure-drill harness now explicitly mutates the sample policy when simulating missing required evidence.

## No-Source Scope Decisions

| Repo | Classification | Production | Reason |
|---|---|---|---|
| Accounting | `needs_memory_space_creation` | `BLOCKED` | Active dirty repo with remote; no v1 space with cards was identifiable. |
| AgentPack | `needs_memory_space_creation` | `BLOCKED` | Local tool/skill pack repo with untracked content; no v1 space with cards was identifiable. |
| ChefAI | `needs_memory_space_creation` | `BLOCKED` | Active dirty repo; no v1 space with cards was identifiable. |
| comfy | `scoped_out` | `SCOPED_OUT` | Third-party ComfyUI checkout/runtime dependency, not a managed project memory target for this migration wave. |
| Gauntlet | `needs_memory_space_creation` | `BLOCKED` | Dirty active-looking repo; no v1 space with cards was identifiable. |
| Gauntlet-005 | `inactive_archive` | `INACTIVE_ARCHIVE` | Clean Gauntlet variant with no v1 memory source; classify as archived unless reactivated. |
| Gauntlet-010 | `inactive_archive` | `INACTIVE_ARCHIVE` | Clean Gauntlet variant with no v1 memory source; classify as archived unless reactivated. |
| Guantlet001 | `inactive_archive` | `INACTIVE_ARCHIVE` | Clean legacy typo-named Gauntlet variant with no v1 memory source; classify as archived unless reactivated. |
| Lexi | `duplicate_alias` | `DUPLICATE_ALIAS` | Non-git Lexi directory; active Lex memory is represented by /mnt/data/Lex. |
| MemeTrader | `needs_memory_space_creation` | `BLOCKED` | Active dirty repo with remote; no v1 space with cards was identifiable. |
| Null_Signal | `needs_memory_space_creation` | `BLOCKED` | Active dirty repo with remote; no v1 space with cards was identifiable. |
| OnHand | `needs_memory_space_creation` | `BLOCKED` | Explicitly requested repo and active dirty workspace; no v1 space with cards was identifiable. |
| PulseTrade | `needs_memory_space_creation` | `BLOCKED` | Active dirty repo with remote; no v1 space with cards was identifiable. |
| SNN | `inactive_archive` | `INACTIVE_ARCHIVE` | Clean repo with no remote and no v1 memory source; classify as archived unless reactivated. |

## Production Migration Decision

Production migration excluding Muninn remains `NOT_READY` because active no-source repos still need explicit memory-space creation before they can be migrated. Candidate repos with Phase I shadows now have real replay-gate coverage; Muninn remains excluded pending a separate self-hosting migration plan.

## v1 Safety

Phase I-B bridge/replay commands did not intentionally access or write the live v1 DB. A post-run comparison against the Phase I after-snapshot detected an external live v1 change during the Phase I-B window: `cards` increased 522 -> 523, `evidence` increased 1429 -> 1432, and `card_evidence` increased 1429 -> 1432. The newest card is Lexi-scoped (`repo:0c321b2a6f183a95`) and unrelated to Phase I-B bridge fixtures. This keeps live cutover and production migration blocked until a quiet-window rerun confirms no concurrent v1 writes.

Safety report: `reports/pilots/phase_i_b_replay_fixtures_2026-05-17/v1_safety_after_phase_i_b.json`

## Artifacts

- Updated manifest: `/mnt/data/Muninn/reports/pilots/phase_i_batch_shadow_migration_2026-05-17/migration_manifest.json`
- JSON closeout: `/mnt/data/Muninn/reports/muninn_v2_phase_i_b_replay_fixture_closeout_2026-05-17.json`
- Phase I-B artifact directory: `/mnt/data/Muninn/reports/pilots/phase_i_b_replay_fixtures_2026-05-17`
