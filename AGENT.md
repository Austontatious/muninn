# Agent Guide (Codex / Contributors)

## What this repo is
Muninn is a pluggable memory harness (service + SDK) for LLM agents.

## How to work in this repo

- Keep changes small and composable
- Update `PROJECT_MEMORY.md` when you change architecture, interfaces, or assumptions
- Add/adjust tests for behavior changes
- Do not add heavyweight dependencies without clear justification

## Safety rules

- Do not add any feature that stores raw user transcripts as “memory” by default
- Do not store “instructions” or “policy overrides” in memory
- All writes must be attributable (provenance)

## Definition of Done

- Code formatted (`ruff`/`black`) and tests pass
- Docs updated if interfaces changed
