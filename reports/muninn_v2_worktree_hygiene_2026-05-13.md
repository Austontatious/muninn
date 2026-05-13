# Muninn v2 Worktree Hygiene Checkpoint

Date: 2026-05-13

## Summary

Current branch: `release/v0.1`

Git status summary:

- tracked modified files: 25
- tracked deleted files: 1
- untracked status entries: 71
- expanded untracked files: 168
- total status entries: 97

Recent commits:

- `fe095d6 chore: sync local source of truth`
- `9089a43 chore: batch sync local working tree`
- `dff9781 feat(chatgpt): add cloudflared quick tunnel for MCP HTTPS`
- `a1f776f feat(chatgpt): add enable-chatgpt setup and API key provisioning`
- `950c466 feat(cli): bootstrap universal local run for muninn up`

## Modified Files

### Muninn v2 Intended Changes

None currently tracked as modified. The v2 implementation files are still untracked.

### Docs / Reports / Checkpoints Related To v2

- `ARCHITECTURE_CHECKPOINT.md`

### Tests Related To v2

None currently tracked as modified. The v2 tests are still untracked.

### Unrelated / Pre-Existing Drift

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

### Unknown / Needs Human Review

- `AGENTS.md`
- `PLANS.md` deleted from repo root

## Untracked Files

### Muninn v2 Intended Changes

- `src/muninn/v2/`

### Docs / Reports / Checkpoints Related To v2

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
- `docs/tasks/MUNINN_ARCHITECTURE_ASSESSMENT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_ADJACENT_CORE_2026-05-13.md`
- `docs/tasks/MUNINN_V2_DRY_RUN_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_READYPLAYER1_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_RECALL_PARITY_2026-05-13.md`
- `reports/muninn_*_inventory.json`
- `reports/muninn_v2_*_report.md`
- `reports/pilots/null_signal_v2_import/`
- `reports/pilots/readyplayer1_v2_import/`

### Tests Related To v2

- `tests/test_v2_models.py`
- `tests/test_v2_pilot_import_cli.py`
- `tests/test_v2_sqlite_store.py`
- `tests/test_v2_v1_adapter.py`
- `tests/test_v2_v1_compatibility.py`

### Unrelated / Pre-Existing Drift

- `.github/workflows/enterprise-baseline.yml`
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
- non-v2 retrieval, vector, SDK, bridge, and standards tests

### Unknown / Needs Human Review

- `docs/decisions/ADR-0001-*` through `ADR-0007-*`
- `docs/decisions/README.md`

## Recommendation

Recommendation: continue only with tightly scoped adjacent-v2 work in the current branch, but do not commit the whole worktree.

The worktree is too broad for a single safe checkpoint commit. The v2 recall parity work can proceed because it is isolated to `src/muninn/v2`, `tests/test_v2_*`, v2 docs, and v2 pilot reports. A commit or branch checkpoint should separate v2 work from unrelated runtime, SDK, bridge, scaffolding, and standards drift.

Suggested checkpoint branch:

```text
muninn-v2-adjacent-core-pilot-recall-parity
```

Suggested commit grouping:

1. v2 adjacent core + pilot importer + recall parity CLI
2. v2 tests only
3. v2 docs / ADRs / architecture checkpoint
4. pilot output reports and generated artifacts
5. separate human-reviewed commit for unrelated SDK/runtime/bridge/scaffolding drift

Do not include these in a v2 checkpoint without review:

- `AGENTS.md`
- root `PLANS.md` deletion
- `migrations/0001_init.sql`
- `src/muninn/api.py`
- `src/muninn/mcp_server.py`
- `src/muninn/cli.py`
- `src/muninn/human_memory/*`
- `apps/muninn_mcp/`
- `src/muninn/core/`
- `src/muninn/runtime/`

## Safety Notes

- No reset, stash, clean, commit, branch creation, or file deletion was performed.
- `AGENTS.md` is modified but was not touched for this checkpoint; run `agents_lint` before committing if it remains included.
- Root `PLANS.md` deletion plus untracked `docs/tasks/PLANS.md` needs human review.
- Generated SQLite DB artifacts under `reports/pilots` are audit artifacts; decide separately whether binary scratch DBs should be committed.
