# Muninn Project Migration Runbook

Last updated: 2026-04-05

## 1. Core migration principles

- Muninn owns the durable memory substrate, not every app’s product state.
- Procedural memory is the primary optimization target for Codex/Sindri/Friday-style systems.
- Lexi is the exception, not the default template for substrate evolution.
- Apps define memory semantics via app packs (`AppSpec`, `MemorySpec`, `BundleSpec`).
- SDK core is canonical; HTTP/MCP/CLI are adapters.
- Provenance, trust, lifecycle, and evidence remain substrate-owned.
- Old ad hoc memory surfaces should be wrapped or retired, not duplicated indefinitely.

## 2. Project classification template

Use this template for every project migration.

### A. What belongs in Muninn

List durable memory types the project should store in Muninn. Examples:

- durable user memory
- preferences and constraints
- project/task/procedure lessons
- corrections
- reusable decisions and stable facts

### B. What stays native to the project

List state that is first-class product data or operational state. Examples:

- auth/account/session truth
- app-native product state
- repo/world topology or domain-specific truth

### C. Required app-pack shape

Specify the pack contract:

- memory types and required fields
- retrieval lanes
- bundle stages
- evidence expectations
- supersession/consolidation rules
- projection views

### D. Integration mode

- embedded or service mode
- compatibility wrappers required
- migration order inside the project

### E. Proof criteria

Define what proves the migration is successful:

- cleaner prompt assembly and lower duplication
- better continuity without noise
- explainability and provenance intact
- measurable workflow improvements

## 3. Lexi migration plan (primary)

Lexi consumes procedure memory only where it directly improves user workflows; it is not the substrate driver.

### What belongs in Muninn

- `profile_fact`
- `interaction_preference`
- `project`
- `project_state`
- `constraint`
- `correction`

### What stays Lexi-native

- auth/account/session truth
- app-native product state
- request/session ephemeral state

### Required pack shape

- Memory types above with strict identity keys.
- Retrieval lanes: lexical, identity, continuity, constraint.
- Bundle stages: cover-sheet continuity, topical task bundle, evidence/history only on demand.
- Evidence expectations: required for `constraint` and `correction` when available.
- Supersession rules: `correction` supersedes previous conflicting facts.
- Projection views: “continuity” (short), “task” (working set), “deep” (evidence/history).

### Integration mode

- Prefer embedded SDK mode for local dev and tests.
- Service mode allowed where shared infra is required.
- Wrap existing Lexi memory read/write paths to call the pack-driven SDK.

### Migration sequence

1. Define and validate Lexi pack (`LexiPack`) in Muninn.
2. Wrap legacy write paths to emit SDK writes with evidence.
3. Replace read paths with bundle projections (continuity + task).
4. Validate explainability surfaces and evidence links.
5. Retire duplicated legacy paths after proof.

### Proof criteria

- Lower memory duplication in prompt assembly.
- Stable continuity bundle with explicit provenance.
- No regression in task completion quality.

## 4. Friday migration plan

### Likely Muninn scope

- `task_outcome`
- `procedure_lesson`
- `tool_preference`
- `constraint`

Procedure emphasis:
- prioritize reusable workflow steps and recovery paths over generic note capture.

### What stays Friday-native

- orchestration runtime state
- task scheduling and execution logs

### Integration mode

- Embedded SDK preferred for agent-local runs.
- Service mode acceptable for shared workers.

### Proof criteria

- Procedure lessons retrieved consistently without re-derivation.
- Tool preferences apply without manual hardcoding.

## 5. Huginn migration plan

### Likely Muninn scope

- `relationship_signal`
- `contact_preference`
- `social_event`
- `interaction_pattern`

### What stays Huginn-native

- contact graph truth and CRM integrations
- messaging/session state

### Integration mode

- Service mode likely; embedded mode for tests.

### Proof criteria

- Relationship continuity improves without polluting canonical contact truth.

## 6. Sindri migration plan

### Likely Muninn scope (narrow)

- `promotion_lesson`
- `decision_artifact`
- `risk_pattern`
- `review_lesson`

Procedure emphasis:
- focus on review/playbook sequences, validation order, and recovery steps.

### What stays Sindri-native

- trust/process contract logic
- review pipeline state

### Integration mode

- Embedded SDK for controlled scope.

### Proof criteria

- Durable review lessons are reused without expanding Muninn’s scope.

## 7. Mimir bridge section (explicit boundary)

- Mimir world-state remains Mimir-native and is not migrated into Muninn.
- Valid Muninn uses for Mimir:
  - procedural lessons
  - cross-session task memory adjacent to repo work
  - bridge bundles that combine durable task memory with repo-state retrieval
- Invalid uses:
  - topology truth
  - bindings/adjacencies/world-state source of truth

## 8. Recommended rollout order

1. Finish Muninn local-surface unification.
2. Lexi migration.
3. Friday or Huginn migration.
4. Sindri bounded integration.
5. Mimir bridge only.

## 9. Reusable migration checklist template

- Classify memory vs native state.
- Define pack specs and bundle stages.
- Choose runtime mode (embedded or service).
- Add write/read wrappers.
- Validate bundle projections and explainability.
- Smoke test real workflows.
- Retire duplicated legacy paths.
