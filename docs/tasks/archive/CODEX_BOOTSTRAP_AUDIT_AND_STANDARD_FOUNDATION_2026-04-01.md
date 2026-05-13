# Codex Bootstrap Audit And Standard Foundation

Status: archived/superseded
Date: 2026-04-01

Archive note: superseded by the committed repo baseline surfaces:
`AGENTS.md`, `docs/CODEX_STANDARDS.md`, `docs/ENTERPRISE_TRUST_BASELINE.md`,
root `core/`, root `prompts/`, root `evals/`, and `tests/test_codex_standards.py`.
This file is historical context only and must not be treated as live task direction.

## Objective
Audit existing Codex/bootstrap standards across the machine, consolidate them into one canonical baseline, align Muninn/Mimir/LAILA/Lex/friday to that baseline, and stop before any template-extraction work.

## Scope
In:
- `/home/unix/.codex`
- `/home/unix/codex-standards`
- `/mnt/data/GLOBAL_STANDARDS.md`
- `/mnt/data/AGENTS_CORE.md`
- `/mnt/data/.codex_ssot/v1/templates`
- `/mnt/data/.codex_ssot/v1/tools`
- `/mnt/data/Muninn`
- `/mnt/data/Mimir`
- `/mnt/data/LAILA`
- `/mnt/data/Lex`
- `/mnt/data/friday`
- `/mnt/data/Bifrost` for read-only atlas consultation

Out:
- Template extraction or prompt rewrites beyond bootstrap enforcement foundations
- Runtime feature work unrelated to standards/bootstrap alignment
- Repos outside the five named targets, except read-only audit references

## Checklist
- [x] Audit existing bootstrap/standards artifacts and identify overlap/conflict
- [ ] Create one canonical global baseline and init script
- [ ] Update legacy global bootstrap/template files to point at the canonical baseline
- [ ] Add per-repo standards docs, required directory scaffolding, and enforcement tests
- [ ] Archive or neutralize duplicate/conflicting standards artifacts inside target repos
- [ ] Run repo validations and `agents_lint`
- [ ] Write `/mnt/data/codex_audit_report.md`
- [ ] Write `/mnt/data/codex_standardization_report.md`

## Rollback Plan
- Revert edited standards/bootstrap files in the affected repos if the new baseline introduces conflicts.
- Remove newly created placeholder directories/files if they prove incompatible with a repo's structure.
- Restore archived one-off docs to their original paths only if a canonical doc was incorrectly displaced.

## Test Plan
- Run targeted repo enforcement tests: `pytest -q tests/test_codex_standards.py`
- Run targeted lint for new Python tests where available
- Run `bash /mnt/data/.codex_ssot/v1/tools/agents_lint.sh` after AGENTS/AGENT updates
