# Muninn v2 Phase C Multi-Repo Shadow Validation

Date: 2026-05-17

## Executive Summary

Phase C passed as an offline, v2-only shadow validation step. SubSim and Sindri both imported into fresh explicit v2 shadow DBs with zero fidelity failures, complete fallback-derived indexes, and GO agent-context audits.

C1 proved the Phase B harness generalizes beyond Friday and ReadyPlayer1. C2 was needed: initial SubSim/Sindri audits had full coverage but 9 over-included cards and 2 confusing/background flags. Tightened supplement selection reduced that to 1 over-included card and 0 confusing flags while preserving 1.0 coverage.

Friday and ReadyPlayer1 regression audits were rerun after tightening. Both remain GO with 1.0 coverage and zero missing required needs. Friday still has non-blocking noise from a primary Android contrast card and some extra selected cards; that is not a supplement-selection regression.

## C1 Pilots

SubSim:

- Path: `/mnt/data/subsim`
- Space key: `repo:363c13a65e92ef58`
- Shadow DB: `reports/pilots/subsim_v2_shadow_2026-05-17/subsim_shadow_v2.db`
- Import: 18 cards, 74 evidence refs, 1 entity, 1 ontology profile
- Fidelity: 94 checked, 0 failures, 0 unsupported, 0 ambiguous
- Index: 18 eligible, 18 indexed, 0 missing, 0 stale
- Backend: `json_vector_fallback`, degraded only because `sqlite_vec` is unavailable

Sindri:

- Path: `/mnt/data/Sindri`
- Space key: `path:316f4f67d061cbdd`
- Shadow DB: `reports/pilots/sindri_v2_shadow_2026-05-17/sindri_shadow_v2.db`
- Import: 26 cards, 76 evidence refs, 1 entity, 1 ontology profile
- Fidelity: 104 checked, 0 failures, 0 unsupported, 0 ambiguous
- Index: 26 eligible, 26 indexed, 0 missing, 0 stale
- Backend: `json_vector_fallback`, degraded only because `sqlite_vec` is unavailable

## Audit Results

Initial SubSim/Sindri audit:

- Cases: 2
- GO: 2
- Average coverage: 1.0
- Missing required needs: 0
- Confusing flags: 2
- Over-included cards: 9

Tightened SubSim/Sindri audit:

- Cases: 2
- GO: 2
- Average coverage: 1.0
- Missing required needs: 0
- Confusing flags: 0
- Over-included cards: 1

Friday/ReadyPlayer1 tightened regression audit:

- Cases: 2
- GO: 2
- Average coverage: 1.0
- Missing required needs: 0
- Confusing flags: 1
- Over-included cards: 5

## C2 Supplement Tightening

Implemented in v2-only `shadow-rehydrate-preview` composition:

- Added explicit supplement reason codes in `selected_memory.cards[].selection.reason`.
- Added reason visibility to Markdown preview and deterministic agent-context blocks.
- Strict previews no longer fill the remaining budget with weak recency alone.
- Added background/contrast penalties for diagnostic or non-current cards such as hard-gate trials, manual-review trials, optimizer runs, and process-only background notes.
- Added a boundary/contract preservation path so older durable project contracts, canonical entrypoints, and runtime-memory boundary cards are not lost solely because they are older.
- Preserved non-strict continuity fallback with a small cap.

Reason codes:

- `recent_campaign_or_numeric_token_overlap`
- `recent_query_token_overlap`
- `recent_query_primary_domain_overlap`
- `recent_primary_domain_overlap`
- `recent_project_boundary_or_contract`
- `recent_same_scope_continuity_fallback`

## Safety

No live v1 schema, runtime retrieval, MCP defaults, or project repositories were changed. All shadow DB writes went only to explicit paths under `reports/pilots`.

Post-run v1 count check:

- `cards`: 515
- `evidence`: 1405
- `card_evidence`: 1405
- `interaction_events`: 2

The live v1 DB mtime was already at `2026-05-17 13:52:53 -0700` during this task and counts remained stable after the Phase C commands.

## Output Artifacts

- `reports/pilots/subsim_v2_shadow_2026-05-17/`
- `reports/pilots/sindri_v2_shadow_2026-05-17/`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_phase_c_initial_fixture.json`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_phase_c_tightened_fixture.json`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_phase_c_friday_rp1_regression_fixture.json`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_audit_initial/`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_audit_tightened/`
- `reports/pilots/phase_c_multi_repo_2026-05-17/agent_context_audit_friday_rp1_regression/`

## Decision

GO for continued offline v2 shadow validation and multi-repo harness use.

GO for the tightened supplement-selection policy as v2 shadow-preview behavior.

NO-GO for live agent context. The remaining blocker is not migration or schema fidelity; it is broader preview review, multi-repo sample size, rollback/cutover planning, and residual primary-result noise.

## Recommended Next Task

Run Phase C on at least one more independent repo, then start Phase D as offline recall/reinforcement mechanics only. Do not wire v2 context into live MCP or Codex defaults yet.
