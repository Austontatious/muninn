# Conservative Repository Cleanup Report - 2026-05-28

## Scope

- Repository: `/mnt/data/Muninn`
- Branch: `muninn-v2-adjacent-core-pilot-recall-parity`
- Task scope: documentation/navigation cleanup only.
- Runtime/API/schema behavior changed: no.
- Meaningful files deleted: none.

## Summary

This cleanup made the current repository guidance easier to navigate without
erasing project history or generated evidence. It archived completed task
sheets, added front-door indexes for docs and reports, labeled stale or
historical docs, updated README pointers, and classified preexisting untracked
pilot artifacts as generated evidence requiring review before any deletion.

## Current Canonical Docs

- `AGENTS.md`: repository policy, memory protocol, and current v1/v2 posture.
- `ARCHITECTURE_CHECKPOINT.md`: current architecture truth.
- `RUNBOOK.md`: operations and Phase J trial workflow.
- `docs/CODEX_STANDARDS.md`: repo standards contract and validation commands.
- `docs/decisions/`: durable architectural decisions.
- `docs/contracts/`: versioned contract schemas and examples.
- `docs/README.md`: new documentation map.
- `reports/README.md`: new generated-report index.

## Pass 1 Classification

| Classification | Files / groups | Notes |
| --- | --- | --- |
| `CURRENT_CANONICAL` | `AGENTS.md`, `ARCHITECTURE_CHECKPOINT.md`, `RUNBOOK.md`, `docs/CODEX_STANDARDS.md`, `docs/decisions/`, `docs/contracts/` | Current guidance and contracts. |
| `HISTORICAL_EVIDENCE` | `reports/*.md`, `reports/*.json`, assessment docs, archived task sheets | Retained for provenance and design history. |
| `SUPERSEDED_PLAN` | completed task sheets formerly under `docs/tasks/*.md` | Moved to `docs/tasks/archive/`. |
| `GENERATED_ARTIFACT` | `reports/pilots/**`, live-trial logs, JSON/JSONL report pairs | Evidence from specific runs; not current instructions. |
| `DUPLICATE_OR_NOISE` | `.playwright-mcp/` | Local Playwright MCP cache; now ignored, not deleted. |
| `REVIEW_NEEDED` | untracked pilot evidence groups, `PROJECT_MEMORY.md` | Do not delete or stage wholesale without human review. |

## Files Moved

Completed or superseded task sheets were archived with `git mv`:

- `docs/tasks/LLM_PROJECT_STANDARDS_UPGRADE_2026-04-01.md` -> `docs/tasks/archive/LLM_PROJECT_STANDARDS_UPGRADE_2026-04-01.md`
- `docs/tasks/MUNINN_ARCHITECTURE_ASSESSMENT_2026-05-13.md` -> `docs/tasks/archive/MUNINN_ARCHITECTURE_ASSESSMENT_2026-05-13.md`
- `docs/tasks/MUNINN_INSTRUCTION_RESTORE_2026-03-26.md` -> `docs/tasks/archive/MUNINN_INSTRUCTION_RESTORE_2026-03-26.md`
- `docs/tasks/MUNINN_V2_ADJACENT_CORE_2026-05-13.md` -> `docs/tasks/archive/MUNINN_V2_ADJACENT_CORE_2026-05-13.md`
- `docs/tasks/MUNINN_V2_DRY_RUN_PILOT_IMPORT_2026-05-13.md` -> `docs/tasks/archive/MUNINN_V2_DRY_RUN_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_READYPLAYER1_PILOT_IMPORT_2026-05-13.md` -> `docs/tasks/archive/MUNINN_V2_READYPLAYER1_PILOT_IMPORT_2026-05-13.md`
- `docs/tasks/MUNINN_V2_RECALL_PARITY_2026-05-13.md` -> `docs/tasks/archive/MUNINN_V2_RECALL_PARITY_2026-05-13.md`
- `docs/tasks/muninn_v2_phase_f_shadow_bridge_consumer_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_f_shadow_bridge_consumer_plan_2026-05-17.md`
- `docs/tasks/muninn_v2_phase_g_shadow_ops_drill_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_g_shadow_ops_drill_plan_2026-05-17.md`
- `docs/tasks/muninn_v2_phase_h_shadow_ops_gate_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_h_shadow_ops_gate_plan_2026-05-17.md`
- `docs/tasks/muninn_v2_phase_i_b_replay_fixture_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_i_b_replay_fixture_plan_2026-05-17.md`
- `docs/tasks/muninn_v2_phase_i_batch_shadow_migration_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_i_batch_shadow_migration_plan_2026-05-17.md`
- `docs/tasks/muninn_v2_phase_j_personal_live_trial_plan_2026-05-17.md` -> `docs/tasks/archive/muninn_v2_phase_j_personal_live_trial_plan_2026-05-17.md`

Historical reports may still contain pre-cleanup task-sheet paths. Those
reports are retained as generated evidence and were not hand-edited.

## Status Headers Added

- `README.md`: current v1/v2 posture and canonical references.
- `PROJECT_MEMORY.md`: `REVIEW_NEEDED / HISTORICAL`.
- `ROADMAP.md`: `HISTORICAL`.
- `docs/muninn_architecture_assessment.md`: `HISTORICAL ASSESSMENT`.
- `docs/muninn_v2_cutover_strategy.md`: `SUPERSEDED`.
- `docs/README.md`: `CURRENT INDEX`.
- `docs/tasks/README.md`: `CURRENT INDEX`.
- `docs/tasks/archive/README.md`: `HISTORICAL`.
- `reports/README.md`: `GENERATED EVIDENCE INDEX`.
- `reports/pilots/README.md`: `GENERATED EVIDENCE`.

## README / Pointer Changes

- README now points readers to `AGENTS.md`, `ARCHITECTURE_CHECKPOINT.md`,
  `RUNBOOK.md`, `docs/CODEX_STANDARDS.md`, `docs/README.md`, and
  `reports/README.md`.
- Added `docs/README.md` as the docs map.
- Added `reports/README.md` and `reports/pilots/README.md` as generated
  evidence indexes.
- Added `docs/tasks/README.md` and `docs/tasks/archive/README.md` to separate
  active task sheets from historical plans.
- Did not edit `AGENTS.md` or `AGENT.md`; agents lint is therefore not required
  for this cleanup.

## Generated Artifacts Organized

- Existing pilot artifacts remain under `reports/pilots/`.
- Added `reports/pilots/README.md` to document handling policy for generated
  JSON, JSONL, Markdown, DB, WAL, and SHM artifacts.
- Added `.playwright-mcp/` to `.gitignore` as local tool state. The existing
  local cache was not deleted.

## Review Needed

- Preexisting untracked pilot evidence remains visible in git status. It
  includes generated artifacts for Friday, ReadyPlayer1, Lexi, Sindri, SubSim,
  Phase I-B replay fixtures, Phase I batch shadow migration, and Phase J live
  trial evidence. These should be reviewed before deciding whether to commit,
  archive elsewhere, or delete any subset.
- `PROJECT_MEMORY.md` contains useful older state but also overlaps with
  canonical docs. It is now labeled `REVIEW_NEEDED / HISTORICAL`; a future
  cleanup can split durable records from stale summary text.

## Deletion Candidates Requiring Approval

- Meaningful deletion candidates proposed by this cleanup: none.
- Optional non-meaningful local cleanup: `.playwright-mcp/` can be removed from
  the working tree if explicitly approved, but it is now ignored and was not
  deleted.
- Any deletion of pilot evidence under `reports/pilots/**` requires explicit
  human review because those files are generated validation evidence.

## Validation

- `python3.11 --version && PYTHON=python3.11 make test`: passed,
  `Python 3.11.14`, `13 passed`.
- `PYTHON=python3.11 make eval`: passed,
  `[ok] eval scaffolding present (1 case files)`.
- `PYTHON=python3.11 make lint`: passed.
- `git diff --check && git diff --cached --check`: passed.
- Task-sheet root sanity: passed; only `docs/tasks/README.md` remains directly
  under `docs/tasks/`.
- Current-doc path sanity: passed; moved `docs/tasks/*.md` paths appear only in
  this cleanup report as an explicit move ledger.
- Agents linter: not run because `AGENTS.md` and `AGENT.md` were not changed.

## Remaining Risk

- This cleanup moved task-sheet paths. Historical generated reports were not
  edited, so some old reports preserve original pre-cleanup paths as evidence.
- The worktree still contains substantial preexisting untracked generated pilot
  evidence that is not part of the cleanup commit unless separately approved.
