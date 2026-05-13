# CODEX Standards

## Baseline Reference
- `/home/unix/codex-standards/BASELINE.md`

## Required Directories
- `prompts/`
- `prompts/system/`
- `prompts/tasks/`
- `prompts/evals/`
- `evals/`
- `evals/datasets/`
- `evals/cases/`
- `core/`
- `tests/`
- `docs/`

## Required Files
- `Makefile`
- `core/config.py`
- `core/prompt_loader.py`
- `core/llm.py`
- `core/trace.py`
- `evals/runner.py`
- `tests/test_codex_standards.py`

## Make Targets
- `run`
- `test`
- `eval`
- `lint`

## Prompt Scan Roots
- `src/`
- `scripts/`

## Config Scan Roots
- `src/muninn/`

## Model Interface Scan Roots
- `src/`
- `scripts/`

## Canonical Prompt Surfaces
- `prompts/`

## Canonical Config Surfaces
- `core/config.py`
- `src/muninn/config.py`

## Canonical Model Interface Surfaces
- `core/llm.py`

## Temporary Prompt Exceptions
- `None.`

## Temporary Config Exceptions
- `src/muninn/adapters/local_tools.py`
- `src/muninn/api.py`
- `src/muninn/cardex/embeddings.py`
- `src/muninn/cli.py`
- `src/muninn/db.py`
- `src/muninn/mcp_server.py`
- `src/muninn/middleware/auth.py`
- `src/muninn/telemetry.py`

## Temporary Model Interface Exceptions
- `None.`

## Core Rules
- No inline prompts in runtime code.
- No direct model SDK usage outside canonical interface surfaces.
- New env access belongs in typed config surfaces or in an explicit temporary exception.
- Eval scaffolding and trace hooks are mandatory for LLM-facing work.

## Contract Change Rules
- Request or response schema changes require a version bump.
- Retrieval format or memory layout changes require compatibility review.
- Shared Muninn or Mimir contract changes require test updates in both repos.

## Anti-Bloat Rule
- Do not add speculative frameworks, agent wrappers, or duplicate standards layers.
- If a layer does not improve correctness, observability, or control, remove it.

## Simplicity Rule
- Prefer explicit, inspectable functions over hidden orchestration.
- Keep prompt loading, config loading, transport, and trace emission separable.

## Senior Architecture Guardrails
This repo follows the Senior Architecture Guardrails defined in `/home/unix/codex-standards/BASELINE.md`.

Key enforced rules:
- ADR required for major subsystems, contracts, schemas, and workflow patterns (`docs/decisions/`).
- Every shared boundary must define ownership (producer, consumer, schema owner, version owner, compatibility owner).
- Shared interfaces are stable contracts; internal reach-through and implicit schema mutation are forbidden.
- Hidden side effects are forbidden; writes must be explicit and read paths must not mutate state.
- Setup/bootstrap/migration scripts must be idempotent and safe to re-run.
- Shared contracts must be versioned and include schema + golden examples + compatibility notes.
- Contract testing is required on producer and consumer sides where applicable.
- One canonical path per concern; alternate paths require explicit justification.
- Failure modes, trust boundaries, and out-of-scope deferrals must be explicit.

## Validation
- `python3 -m pytest -q tests/test_codex_standards.py --noconftest`
- `python3 evals/runner.py --check`
- `python3 -m py_compile core/config.py core/prompt_loader.py core/llm.py core/trace.py tests/test_codex_standards.py evals/runner.py`

## Enterprise Trust Gates
- Canonical gate: `make enterprise-check`
- Dependency inventory: `make enterprise-deps`
- Vulnerability scan path: `make enterprise-vuln`
- Known-good artifact: `make known-good` (writes `artifacts/known_good/<timestamp>.json`)
- Repo-specific checkpoint/rollback discipline: `docs/ENTERPRISE_TRUST_BASELINE.md`
