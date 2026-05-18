# Muninn v2 Phase J Personal Local Live Trial Report

## Executive Summary

Phase J starts a reversible personal/local live trial for Auston: context reads use the v2 read-only bridge helper, while v1 MCP/API remain unchanged and available for rollback. v2 writes are disabled; existing completion-card writes remain v1-only.

## Cutover Path

- reads: `v2_bridge_helper_scripts/muninn_v2_live_context.py`
- writes: `V1_ONLY existing completion-card workflow; no v2 writes`
- adaptive_default: `OFF`
- fallback: `logged v2 failure then v1 MCP fallback`
- live_mcp_replaced: `False`
- global_codex_config_changed: `False`

## Endpoints

- Before: v1 API `http://127.0.0.1:8000/health`; v1 MCP `http://127.0.0.1:8765/mcp`; v2 bridge CLI only.
- After: v1 API and v1 MCP unchanged; v2 reads use `scripts/muninn_v2_live_context.py`.

## Backups

- backup_dir: `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups`
- v1_core_backup: `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/muninn_v1_core_2026-05-17.db`
- v1_human_backup: `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/human_memory_v1_2026-05-17.db`
- config_backup_dir: `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/config`
- v2_backup_examples:
  - `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/muninn_shadow_v2_phase_i_2026-05-17.db`
  - `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/friday_shadow_v2_phase_i_2026-05-17.db`
  - `/mnt/data/Muninn/reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/readyplayer1_shadow_v2_phase_i_2026-05-17.db`

## Smoke Tests

- helper muninn: status `ok`, selected cards `8`, degraded `True` ['sqlite_vec_unavailable_using_json_vector_fallback']
- helper friday: status `ok`, selected cards `8`, degraded `True` ['sqlite_vec_unavailable_using_json_vector_fallback']
- helper readyplayer1: status `ok`, selected cards `9`, degraded `True` ['sqlite_vec_unavailable_using_json_vector_fallback']
- bridge adaptive_denial: status `denied`, returncode `0`, reasons `['adaptive_scoring_not_allowed']`
- bridge health: status `ok`, returncode `0`, reasons `[]`
- bridge rehydrate: status `ok`, returncode `0`, reasons `[]`
- bridge search: status `ok`, returncode `0`, reasons `[]`
- bridge wrong_project_denial: status `denied`, returncode `0`, reasons `['space_not_allowed', 'project_path_not_allowed']`
- MCP system ping: `ok`, version `0.11.0`, DB `/home/unix/.local/share/muninn/human_memory.db`, auth off
- API health: `ok`

Known smoke caveat: sqlite_vec is unavailable, so v2 bridge responses are degraded with `sqlite_vec_unavailable_using_json_vector_fallback`. Muninn smoke context also surfaced an older ReadyPlayer1 no-go supplement alongside newer go-with-constraints memory; monitor stale/conflicting supplements during the trial.

## Validation

- tests_test_v2: `84 passed`
- py_compile_v2_and_helper: `passed`
- full_pytest: `271 passed, 2 skipped, 2 warnings`
- agents_lint: `PASS=0 WARN=30 FAIL=0; Muninn warning pre-existing policy-section lint, no failures`

## V1 Safety

- `human_memory.db` row counts, size, mtime, and hash stayed unchanged after smoke/validation.
- `muninn.db` changed only by two `GET /health` audit_log rows from service smoke checks: `434 -> 436`.
- v1 backups are available under the Phase J backup directory.

## Rollback

1. Stop calling `scripts/muninn_v2_live_context.py`.
2. Resume the existing v1 MCP task-start context flow.
3. Keep existing v1 completion-card writes unchanged.
4. Revert the Phase J commit if repo-local instructions should no longer prefer v2 reads.

## Status

- personal_local_live_trial: `GO_WITH_V1_CORE_AUDIT_LOG_CAVEAT`
- general_production_cutover: `NO-GO`
- v1_rollback: `AVAILABLE`
- adaptive_default: `OFF`
- writes: `V1_ONLY`

## Trial Review

Review logs/live_trial after 24-48 hours for failed reads/writes, missing/confusing context, fallback usage, stale supplements, and operator notes.
