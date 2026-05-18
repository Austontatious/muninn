# Muninn v2 Phase I Batch Shadow Migration Report

Generated: 2026-05-18T01:31:13Z

## Executive Summary

- Repos inventoried: 32
- Duplicate inventory aliases collapsed: 3
- Shadow candidates with v1 memory: 18
- Shadow migrations succeeded: 18
- Shadow migrations failed: 0
- Blocked/no v1 memory or missing path: 14
- Cards imported: 489
- Evidence refs imported: 1395
- Bridge read-only GO repos: 18
- Replay gate GO repos: 3
- Replay gate LIMITED repos: 15

## Final Status

- batch_shadow_migration: `PARTIAL-GO`
- bridge_readonly: `GO_FOR_PASSING_REPOS`
- production_migration_excluding_muninn: `NOT_READY`
- muninn_production_migration: `EXCLUDED_PENDING_SEPARATE_PLAN`
- live_cutover: `NO-GO`
- writes: `NO-GO`
- adaptive_default: `NO-GO`

## v1 Safety

- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- Row counts changed: `False`
- Main DB size changed: `False`
- Main DB mtime changed: `False`
- WAL mtime changed: `True`
- SHM mtime changed: `True`
- Safety report: `/mnt/data/Muninn/reports/pilots/phase_i_batch_shadow_migration_2026-05-17/v1_safety_before_after.json`

Read-only pilot import touched SQLite WAL/SHM metadata, but the main v1 DB file size, mtime, and all table row counts remained unchanged.

## Per-Repo Readiness

| Repo | Path | Space | Cards | Evidence | Shadow | Bridge | Replay | Production | Notes |
|---|---|---:|---:|---:|---|---|---|---|---|
| Accounting | `/mnt/data/Accounting` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| AgentPack | `/mnt/data/AgentPack` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Althing | `/mnt/data/althing` | `path:f2bb13bd786fd92c` | 44 | 151 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Aquagenesys | `/mnt/data/Aquagenesys` | `path:84e2f8323ea83b57` | 4 | 16 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| austontatious-dev | `/mnt/data/austontatious-dev` | `repo:9b87d03cb11a90c4` | 17 | 59 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Bifrost | `/mnt/data/Bifrost` | `path:4b38992d2d9b0912` | 5 | 8 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Brilliant | `/mnt/data/Brilliant` | `path:50aa2332ed9719c7` | 2 | 6 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| ChefAI | `/mnt/data/ChefAI` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| comfy | `/mnt/data/comfy` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Echo | `/mnt/data/Echo` | `path:0101d9215af48be6` | 10 | 38 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Fenrir | `/mnt/data/Fenrir` | `path:7ebc0f0b97e0bdc3` | 17 | 69 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Friday | `/mnt/data/friday` | `repo:f8cc7f64d3636a4e` | 48 | 152 | GO | GO | GO | CANDIDATE |  |
| Gauntlet | `/mnt/data/Gauntlet` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Gauntlet-005 | `/mnt/data/Gauntlet-005` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Gauntlet-010 | `/mnt/data/Gauntlet-010` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Guantlet001 | `/mnt/data/Guantlet001` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Heimdall | `/mnt/data/Heimdall` | `path:808c403947b88ec1` | 4 | 12 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Hrafnar | `/mnt/data/Hrafnar` | `path:08438f64e19a2dc3` | 2 | 10 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| LAILA | `/mnt/data/LAILA` | `repo:63325bc94a03e407` | 39 | 68 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Lex | `/mnt/data/Lex` | `repo:0c321b2a6f183a95` | 85 | 176 | GO | GO | GO | CANDIDATE |  |
| Lexi | `/mnt/data/Lexi` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| MemeTrader | `/mnt/data/MemeTrader` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| Mimir | `/mnt/data/Mimir` | `repo:06bbe8682f884cf1` | 74 | 175 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| Muninn | `/mnt/data/Muninn` | `repo:0a6d43de03a835a0` | 44 | 108 | GO | GO | LIMITED | EXCLUDED_PENDING_SEPARATE_PLAN | high-risk self-hosting; needs project-specific replay fixture |
| Null_Signal | `/mnt/data/Null_Signal` | `repo:8086caa7ff98deef` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| OnHand | `/mnt/data/OnHand` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| portfolio | `/mnt/data/portfolio` | `path:6b69ffc5f8046453` | 2 | 0 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| PulseTrade | `/mnt/data/PulseTrade` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| ReadyPlayer1 | `/mnt/data/ReadyPlayer1` | `repo:5059f410815720ea` | 48 | 197 | GO | GO | GO | CANDIDATE |  |
| Sindri | `/mnt/data/Sindri` | `path:316f4f67d061cbdd` | 26 | 76 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |
| SNN | `/mnt/data/SNN` | `` | 0 | 0 | NO-GO | NO-GO | NO-GO | BLOCKED | no_identifiable_v1_space_with_cards |
| SubSim | `/mnt/data/subsim` | `repo:363c13a65e92ef58` | 18 | 74 | GO | GO | LIMITED | CANDIDATE | needs project-specific replay fixture |

## Duplicate Inventory Aliases

- `althing` at `/mnt/data/althing` duplicated an already migrated path; raw duplicate import return code `2` is excluded from migration-failure counts.
- `friday` at `/mnt/data/friday` duplicated an already migrated path; raw duplicate import return code `2` is excluded from migration-failure counts.
- `subsim` at `/mnt/data/subsim` duplicated an already migrated path; raw duplicate import return code `2` is excluded from migration-failure counts.

## Degraded Index Modes

All successful Phase I shadow indexes used the optional `json_vector_fallback` backend where `sqlite_vec` was unavailable. This is acceptable for shadow diagnostics and remains explicitly degraded; it is not a production cutover signal.

## Bridge Validation

Each successful shadow candidate received a project-scoped `BridgeCapabilityPolicyV1` and was tested with `health`, `search`, `rehydrate`, `explain`, wrong-project denial, and adaptive-scoring denial. Denials returned structured `denied` responses.

## Replay Gate / Readiness

Friday, ReadyPlayer1, and Lex reuse existing Phase G/H replay gate evidence and passed the Phase I aggregate replay gate. Other successfully migrated repos are marked `LIMITED` because they have bridge artifacts but do not yet have project-specific Phase G/H replay fixtures.

## Migration Recommendation

Passing repos are ready for continued shadow evaluation and per-project replay fixture creation. Production migration excluding Muninn is `NOT_READY` until blocked/no-source repos are resolved or explicitly scoped out, and until LIMITED replay-gate repos receive fixtures.

## Muninn Separate Plan

Muninn was included in shadow validation but remains `EXCLUDED_PENDING_SEPARATE_PLAN` for production migration because it is the self-hosting memory system. A final Muninn migration must be planned separately after all other repos have an approved production path.

## Artifacts

- Manifest: `/mnt/data/Muninn/reports/pilots/phase_i_batch_shadow_migration_2026-05-17/migration_manifest.json`
- JSON report: `/mnt/data/Muninn/reports/muninn_v2_phase_i_batch_shadow_migration_2026-05-17.json`
- Command logs: `/mnt/data/Muninn/reports/pilots/phase_i_batch_shadow_migration_2026-05-17/command_logs`
