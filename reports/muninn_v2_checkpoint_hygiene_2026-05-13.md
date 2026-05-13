# Muninn v2 Checkpoint Hygiene Report

Date: 2026-05-13

## Inspection

- Current branch before checkpoint branch creation: `release/v0.1`
- Tracked modified files: 25
- Tracked deleted files: 1
- Untracked status entries: 71
- Expanded untracked files: 168

Commands run:

```bash
git status --short
git branch --show-current
git diff --stat
git diff --name-status
```

## Include In v2 Checkpoint

Implementation:

- `src/muninn/v2/`

Tests:

- `tests/test_v2_models.py`
- `tests/test_v2_sqlite_store.py`
- `tests/test_v2_v1_adapter.py`
- `tests/test_v2_v1_compatibility.py`
- `tests/test_v2_pilot_import_cli.py`

v2 docs and ADRs:

- `docs/decisions/ADR-0008-muninn-v2-adjacent-core.md`
- `docs/decisions/ADR-0009-muninn-v2-pilot-import.md`
- `docs/muninn_architecture_assessment.md`
- `docs/muninn_component_inventory.md`
- `docs/muninn_contract_candidates.md`
- `docs/muninn_migration_options.md`
- `docs/muninn_rewrite_vs_upgrade.md`
- `docs/muninn_v1_compatibility_strategy.md`
- `docs/muninn_v2_adjacent_core_plan.md`
- `docs/muninn_v2_contracts.md`
- `docs/muninn_v2_cutover_strategy.md`
- `docs/muninn_v2_gap_analysis.md`
- `docs/muninn_v2_pilot_import.md`
- `docs/muninn_v2_recall_parity.md`
- `docs/tasks/MUNINN_ARCHITECTURE_ASSESSMENT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_ADJACENT_CORE_2026-05-13.md`
- `docs/tasks/MUNINN_V2_DRY_RUN_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_READYPLAYER1_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_RECALL_PARITY_2026-05-13.md`

Reports and generated text/JSON/JSONL artifacts:

- `reports/muninn_api_inventory.json`
- `reports/muninn_dependency_inventory.json`
- `reports/muninn_schema_inventory.json`
- `reports/muninn_storage_inventory.json`
- `reports/muninn_v2_adjacent_core_report.md`
- `reports/muninn_v2_null_signal_pilot_report.md`
- `reports/muninn_v2_readyplayer1_pilot_report.md`
- `reports/muninn_v2_readyplayer1_recall_parity_report.md`
- `reports/muninn_v2_worktree_hygiene_2026-05-13.md`
- `reports/muninn_v2_worktree_hygiene_2026-05-13.json`
- `reports/muninn_v2_checkpoint_hygiene_2026-05-13.md`
- non-SQLite files under `reports/pilots/null_signal_v2_import/`
- non-SQLite files under `reports/pilots/readyplayer1_v2_import/`

## Exclude / Unrelated Drift

Tracked unrelated or mixed drift excluded from the v2 checkpoint:

- `.gitignore`
- `Makefile`
- `README.md`
- `RUNBOOK.md`
- `docs/CROSS_PROJECT_COMPATIBILITY.md`
- `docs/INTEGRATION.md`
- `docs/contracts/muninn_mimir/v1/README.md`
- `docs/contracts/muninn_mimir/v1/versions.json`
- `docs/query_contracts.md`
- `migrations/0001_init.sql`
- `pyproject.toml`
- `src/muninn/__init__.py`
- `src/muninn/api.py`
- `src/muninn/cli.py`
- `src/muninn/human_memory/__init__.py`
- `src/muninn/human_memory/bootstrap.py`
- `src/muninn/human_memory/cards.py`
- `src/muninn/human_memory/procedures.py`
- `src/muninn/human_memory/rehydration.py`
- `src/muninn/mcp_server.py`
- `tests/test_cli_audit.py`
- `tests/test_cross_project_contracts.py`
- `tests/test_mcp_human_memory_contracts.py`

Untracked unrelated drift excluded:

- `.github/`
- `apps/muninn_mcp/`
- `core/`
- `docker-compose.mcp.yml`
- `docs/CODEX_STANDARDS.md`
- `docs/ENTERPRISE_TRUST_BASELINE.md`
- `docs/MUNINN_PROJECT_MIGRATION_RUNBOOK.md`
- `docs/MUNINN_SURFACE_STATUS.md`
- `docs/SDK_COMPATIBILITY_AND_MIGRATION.md`
- `docs/SDK_CORE_CONTRACT.md`
- `docs/contracts/muninn_mimir/v1/examples/`
- `docs/contracts/muninn_mimir/v1/mimir-memory-proposal-import.md`
- `docs/contracts/muninn_mimir/v1/schemas/mimir-memory-proposal-batch.v1.schema.json`
- `docs/muninn_sdk_refactor_boundary_audit.md`
- `docs/muninn_v0_surface_audit.md`
- `docs/tasks/LLM_PROJECT_STANDARDS_UPGRADE_2026-04-01.md`
- `docs/tasks/PLANS.md`
- `docs/tasks/archive/STRUCTURED_EVIDENCE_HARDENING_PLAN.md`
- `evals/`
- `examples/embedded_sdk_demo.py`
- `prompts/`
- `src/muninn/core/`
- `src/muninn/human_memory/retrieval_eval.py`
- `src/muninn/human_memory/session_start.py`
- `src/muninn/human_memory/vector_store.py`
- `src/muninn/mimir_proposals.py`
- `src/muninn/packs/`
- `src/muninn/runtime/`
- non-v2 retrieval/vector/SDK/bridge tests

Generated SQLite DB artifacts excluded:

- `reports/pilots/null_signal_v2_import/scratch_v2.db`
- `reports/pilots/readyplayer1_v2_import/scratch_v2.db`

## Needs Human Review

- `AGENTS.md` is modified but is not v2 checkpoint work.
- Root `PLANS.md` is deleted; this is not verified as intentional v2 work.
- `ARCHITECTURE_CHECKPOINT.md` contains v2 additions mixed with broader SDK/runtime/bridge/vector drift. It should not be fully staged for the v2 checkpoint unless a human accepts the non-v2 architecture updates or a clean partial-stage is prepared.
- `docs/decisions/ADR-0001-*` through `ADR-0007-*` and `docs/decisions/README.md` are untracked and appear to belong to broader architecture history, not this v2 checkpoint.

## Recommendation

Create branch `muninn-v2-adjacent-core-pilot-recall-parity` from the current worktree, stage only the scoped v2 implementation/tests/docs/reports listed above, exclude unrelated drift, and commit the v2 checkpoint. Do not stage `AGENTS.md`, root `PLANS.md` deletion, live v1 runtime files, migrations, or scratch SQLite DB artifacts.
