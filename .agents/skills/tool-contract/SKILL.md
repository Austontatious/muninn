---
name: tool-contract
description: Maintain stable agent-facing contracts (endpoints, schemas, integration docs) with explicit versioning.
---

# Tool Contract Discipline

Use this skill when editing:
- `docs/INTEGRATION.md`
- `schemas/tooling/muninn_tool_spec.json`
- `src/muninn/api.py`
- Pydantic request/response models

## Rules
- Prefer adding optional fields over changing types.
- Keep example payloads copy-pastable and valid JSON.
- Any new endpoint must be documented in INTEGRATION.md with:
  - request example
  - response example (shape)
  - common failure modes
- Any breaking change must increment the `schemas/tooling/muninn_tool_spec.json` version.

## Validation
- Add a test (or update an existing one) that exercises the endpoint.
- Run `pytest -q`.
