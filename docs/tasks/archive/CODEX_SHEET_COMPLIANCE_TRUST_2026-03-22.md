# CODEX Sheet: Muninn Compliance + Trust Pass

Status: completed  
Date: 2026-03-22  
Scope: `/mnt/data/Muninn` only

## Objective
Make Muninn compliant with `/mnt/data/GLOBAL_STANDARDS.md` and repo `AGENTS.md` without expanding scope or rewriting runtime logic.

## Constraints
- No behavior rewrites.
- No cross-repo edits.
- Structure and tracking fixes only.

## Checklist
- [x] Ensure canonical instruction/ops/architecture files exist:
  - `AGENTS.md`
  - `AGENT.md` (stub/symlink)
  - `RUNBOOK.md`
  - `ARCHITECTURE_CHECKPOINT.md`
- [x] Verify architecture linkage:
  - `AGENTS.md` points to `ARCHITECTURE_CHECKPOINT.md` as architecture truth
  - checkpoint lists architecture-defining files
- [x] Move root-level task sheet:
  - `PLANS.md` -> `docs/tasks/archive/PLANS.md`
- [x] Keep contract docs in canonical docs:
  - `docs/query_contracts.md`
  - `docs/laila_adaptation_memory.md`
- [x] Verify no duplicate runbook path (`RUNBOOK.md` vs `docs/RUNBOOK.md`)
- [x] Run agents lint after instruction/doc updates

## Out of Scope
- Runtime logic changes
- API behavior changes
- Rewriting README/RUNBOOK narrative content
