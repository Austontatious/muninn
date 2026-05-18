# Muninn v2 Phase J Personal Live Trial Plan

## Objective

Start a reversible personal/local live trial where Codex-style context reads use
Muninn v2 bridge responses, while v1 remains the rollback and existing write
path.

## Scope

In scope:
- freeze current repo, DB, service, and config state
- create local backups
- add a v2 bridge context helper
- add live-trial logging location and instructions
- update repo-local guidance and rollback docs
- run smoke tests and validation

Out of scope:
- v1 schema/runtime/MCP changes
- public production cutover
- global Codex MCP config replacement
- adaptive retrieval by default
- v2 writes or autonomous memory creation

## Checklist

- [x] Freeze git/service/DB/config state.
- [x] Create v1, v2, and config backups.
- [x] Inspect existing live wiring.
- [x] Choose least invasive cutover path.
- [x] Add v2 live-trial context helper.
- [x] Add log directory and logging guidance.
- [x] Update AGENTS/RUNBOOK/docs/checkpoint.
- [x] Run smoke tests.
- [x] Run validation suite.
- [x] Commit scoped Phase J artifacts.

## Rollback Plan

1. Stop calling `scripts/muninn_v2_live_context.py`.
2. Resume the v1 MCP task-start context flow.
3. Keep existing v1 completion-card writes unchanged.
4. Revert the Phase J commit if repo-local instructions should no longer
   prefer v2 reads.
5. Use DB backups under
   `reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/` only on
   explicit manual restore request.

## Test Plan

- v2 bridge health/search/rehydrate for Muninn
- v2 bridge rehydrate for Friday
- v2 bridge rehydrate for ReadyPlayer1 or another migrated repo
- wrong-project denial
- adaptive denial
- helper-rendered Codex-style context
- v1 DB backup presence and v1 safety comparison
- `tests/test_v2_*.py`
- `py_compile` for `src/muninn/v2`
- full pytest suite
- `agents_lint` because `AGENTS.md` changed
