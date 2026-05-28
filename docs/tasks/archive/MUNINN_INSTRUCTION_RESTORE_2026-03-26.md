# Task: Restore Muninn Memory Instructions Across Repos

Status: completed
Date: 2026-03-26

## Objective
Restore and standardize Muninn memory read/write instructions across active repos, then add a durable upstream bootstrap path so new repos inherit the same contract.

## Scope
In:
- /mnt/data/Muninn
- /mnt/data/LAILA
- /mnt/data/Lex
- /mnt/data/Mimir
- /mnt/data/friday
- /mnt/data/.codex_ssot/v1
- /mnt/data/AGENTS_CORE.md

Out:
- runtime code changes in non-instruction subsystems
- unrelated docs cleanup

## Checklist
- [x] Recover canonical contract from Muninn (`AGENTS.md`, `README.md`, `docs/query_contracts.md`, `docs/INTEGRATION.md`, `ARCHITECTURE_CHECKPOINT.md`)
- [x] Inventory AGENTS/AGENT state across target repos
- [x] Add standardized Muninn integration block to target `AGENTS.md` files
- [x] Align `AGENT.md` compatibility stubs to avoid drift
- [x] Add upstream repo-initialization template + apply script in SSOT tools
- [x] Wire global references to upstream template/apply workflow
- [x] Add future infrastructure note for ambient Muninn usage
- [x] Run agents lint and resolve failures
- [x] Produce explicit repo-by-repo change report

## Rollback Plan
- Revert changed files per repo if contract wording causes conflicts.
- Keep repo-specific invariants untouched while removing only the inserted Muninn block.
- Remove SSOT bootstrap files if they prove incompatible.

## Test Plan
- Run: `bash /mnt/data/.codex_ssot/v1/tools/agents_lint.sh`
- Manually inspect each updated `AGENTS.md` for:
  - presence of Muninn block
  - no contradictory guidance
  - preserved repo-specific constraints
- Confirm `AGENT.md` is stub/symlink-compatible and not divergent policy text.
