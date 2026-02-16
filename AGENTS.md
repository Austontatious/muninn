# AGENTS — Muninn Repo Guardrails

Codex reads `AGENTS.md` before doing work. Use this file as the source of truth for how to operate in this repo. :contentReference[oaicite:3]{index=3}

## Quick commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`
- Install: `pip install -e .[dev]`
- Init DB: `python scripts/init_db.py`
- Run API: `./scripts/dev_run.sh`
- Tests: `pytest -q`

## Muninn-specific guardrails
- Do not store raw chat transcripts as “memory” by default.
- All memory writes must have provenance.
- Never store instruction-like content (policy overrides, jailbreak text) in memory.
- Keep API payloads backward compatible; avoid breaking changes.
- If you change schemas/models/endpoints, also update:
  - docs/INTEGRATION.md
  - schemas/tooling/muninn_tool_spec.json
  - tests

## When the task is complex
If a change touches schema + API + retrieval/policy, write an execution plan in PLANS.md first (small, explicit checklist), then implement. :contentReference[oaicite:4]{index=4}

## Existing guidance
- Also see AGENT.md if present. AGENTS.md is canonical; do not delete AGENT.md.
