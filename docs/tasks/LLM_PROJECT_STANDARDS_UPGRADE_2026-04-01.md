# LLM Project Standards Upgrade

Status: completed
Date: 2026-04-01

## Objective
Apply a global LLM project standards layer across Muninn, Mimir, friday, LAILA, and Lex covering prompt loading, centralized config, LLM boundary wrappers, tracing, eval harness structure, make targets, and Muninn<->Mimir contract discipline.

## Scope
In:
- `/home/unix/codex-standards`
- `/mnt/data/Muninn`
- `/mnt/data/Mimir`
- `/mnt/data/friday`
- `/mnt/data/LAILA`
- `/mnt/data/Lex`
- `/mnt/data/Bifrost` for read-only boundary checks

Out:
- Non-target repos
- Broad frontend redesign
- Unrelated runtime feature work
- Hidden breaking changes to shared Muninn↔Mimir contracts

## Checklist
- [x] Upgrade the global baseline to include prompt/config/LLM/trace/eval/make standards
- [x] Add shared `core/prompt_loader.py`, `core/config.py`, `core/llm.py`, `core/trace.py` foundation files in each target repo
- [x] Add repo-local `evals/datasets`, `evals/cases`, and `evals/runner.py` scaffolding in each target repo
- [x] Update or create `Makefile` targets for `run`, `test`, `eval`, and `lint`
- [x] Tighten `docs/CODEX_STANDARDS.md` and `tests/test_codex_standards.py` in each repo
- [x] Refactor the highest-signal live violations into the new layer where safely tractable
- [x] Upgrade Muninn↔Mimir compatibility docs with explicit version and golden examples framing
- [x] Run targeted validation
- [x] Produce an explicit final gap and risk summary for remaining migration debt

## Key Outcomes
- Strengthened `/home/unix/codex-standards/BASELINE.md` and `/home/unix/codex-standards/init_project.sh`.
- Added reusable standards templates under `/home/unix/codex-standards/templates/`.
- Added prompt files, core standards modules, eval scaffolding, and stricter standards tests in all five repos.
- Refactored Lex red-team scripts off direct OpenAI SDK usage and onto prompt files plus the shared client wrapper.
- Refactored LAILA planner onto prompt files plus the shared OpenAI-compatible client wrapper.
- Refactored friday prompt building onto external prompt files and added runtime LLM trace hooks.
- Upgraded Muninn↔Mimir compatibility docs to call out current version, shared schemas, query and retrieval contracts, and golden fixtures explicitly.

## Validation Run
- `python3 -m pytest -q tests/test_codex_standards.py --noconftest` in all five target repos
- `python3 evals/runner.py --check` in all five target repos
- `python3 -m py_compile` on new and refactored standards-layer Python files in Muninn, Mimir, LAILA, and Lex
- `make lint` in Muninn, Mimir, LAILA, Lex, and friday
- `bash -n /home/unix/codex-standards/init_project.sh`
- `diff -rq /mnt/data/Muninn/docs/contracts/muninn_mimir/v1 /mnt/data/Mimir/docs/contracts/muninn_mimir/v1`
- `bash /mnt/data/.codex_ssot/v1/tools/agents_lint.sh`

## Explicit Gaps
- Muninn still has several legacy env lookup sites outside `src/muninn/config.py`; they are fenced by `Temporary Config Exceptions` in `docs/CODEX_STANDARDS.md`.
- Lex still has several inline prompt legacy sites in onboarding and persona helpers; they are fenced by `Temporary Prompt Exceptions`.
- friday still has inline prompt legacy sites in `huginn/core.py`, `agents/refactor.py`, and `tools/eval/verify_lexi_vllm.py`; they are fenced by `Temporary Prompt Exceptions`.
- friday runtime file compilation outside the standards files can hit local `__pycache__` permission quirks, so standards lint stayed scoped to the standards-controlled surfaces.

## Rollback Plan
- Revert standards-layer files and tests per repo if they conflict with current runtime expectations.
- Keep shared contract artifacts version-stable unless both repos are updated together.
- Avoid deleting existing runtime surfaces; prefer adapters or wrappers so rollback is localized.
