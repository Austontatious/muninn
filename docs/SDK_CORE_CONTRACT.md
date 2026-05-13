# Muninn SDK Core Contract

Date: 2026-04-05

## Purpose
Define the SDK-first core contract for Muninn. Transport layers (HTTP/MCP/CLI) must wrap these surfaces without altering semantics.

## Core Objects

### Memory Item
A durable unit of memory with app-defined payload.

Required envelope fields:
- `app_id`
- `kind`
- `title`
- `summary`

Optional envelope fields:
- `body`
- `payload` (app-defined typed payload)
- `tags`
- `evidence` (list of structured evidence refs)
- `provenance`
- `trust`
- `lifecycle`
- `space_key`
- `metadata`

### Evidence
Evidence is structured and attached to memory items. Supported fields:
- `type` (`file`, `diff`, `commit`, `test`, `log`, `url`, `chat`, `artifact`, `other`)
- `ref` (e.g., file path, URL, commit hash)
- `excerpt` (optional textual snippet)
- `meta` (optional JSON map)

### Event
Memory events capture behavioral signals and are stored in `interaction_events`.
Fields:
- `event_type`, `actor`, `summary`
- optional: `payload`, `signal_type`, `outcome_type`, `scope_type`, `scope_key`, `session_id`

### Bundle
Bundles are staged retrieval plans with explicit decisions.
- `BundleStageSpec` defines stage name, mode, kinds, and evidence requirements.
- `BundleResult` returns staged items and decision explanations.

### Procedural Memory (First-Class)
Procedures are durable operational patterns with typed structure and lifecycle semantics.
Core concepts:
- `ProcedureSpec` (procedure_name, intent_tags, scope, preconditions, steps, expected_outcomes, failure_modes, fallbacks, when_not_to_use, confidence, evidence_refs, supersedes, status, validation_status)
- `ProcedureBundleResult` (orientation → working_context → deep_evidence, with explicit stage decisions)
- Projections (`compact`, `steps`, `troubleshooting`, `recovery`, `validation`, `deep`) for token-efficient injection.
Lifecycle semantics:
- `validation_status` (`candidate`, `validated`, `needs_review`, `deprecated`) controls ranking and eligibility.
- supersession uses `supersede_procedure` to mark predecessors as superseded.

## App Contracts
Apps define their memory semantics via `AppSpec` / `MemorySpec` / `BundleSpec`.

### MemorySpec
- `name` (type name)
- `payload_schema` (Pydantic model or schema object)
- `required_fields`
- `identity_keys`
- `retrieval_roles`
- `evidence_required`
- lifecycle/consolidation/projection policies

### BundleSpec
- `name`, `description`
- `stages`: list of `BundleStageSpec`
- `rehydration_strategy`: `sdk` or `legacy_human`

## Public SDK Surface
`muninn.core.sdk.Muninn`

- `register_app(app_spec)`
- `register_memory_type(app_id, memory_spec)`
- `register_bundle(app_id, bundle_spec)`
- `write(item)`
- `attach_evidence(card_id, evidence)`
- `record_event(event)`
- `query(query, kinds, limit)`
- `retrieve_candidates(query, kinds, limit)`
- `rehydrate_bundle(query, bundle_name, scope)`
- `explain_bundle(query, bundle_name)`
- `supersede(old_card_id, item)`
- `revoke(card_id)`

Procedural additions:
- `write_procedure(spec)`
- `supersede_procedure(supersedes_card_id, spec)`
- `query_procedures(task_label, context_summary, task_type, tool_names, limit)`
- `rehydrate_procedure_bundle(task_label, context_summary, task_type, tool_names, limit, stage_depth)`
- `explain_procedure_bundle(...)`
- `reflect_procedure(reflection)`

## Storage Abstraction
Initial storage backend is the human-memory SQLite DB. The SDK interacts through `HumanMemoryStore` which isolates DB calls from SDK logic. Future backends should implement the same store surface.

## Validation Rules
- App payloads are validated when `MemorySpec.schema` is provided.
- `required_fields` must be present in `payload`.
- `evidence_required` enforces evidence on write.

## Compatibility Notes
This core contract does not remove or change existing HTTP/MCP/CLI interfaces. Runtime adapters should map transport payloads into this contract.
