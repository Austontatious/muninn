# AGENTS.md — Muninn

## 1) Purpose
Muninn is the canonical memory and learning substrate.

It is responsible for:
- durable memory storage (cards, evidence, spaces)
- deterministic rehydration of context
- interaction-event capture
- policy/adaptation state derived from behavior

Muninn is not an orchestrator or agent. It is a **state system**.

## 1.1) Current v1/v2 Operating Posture
This root-level `AGENTS.md` is the canonical repo instruction sheet for Codex, VS Code, and other integrating agents.

Muninn v1 remains the active production memory system for Codex-facing workflows:
- v1 owns live MCP/Codex behavior, durable human-memory cards, evidence, spaces, policy/adaptation state, and deterministic rehydration.
- v1 changes require extra scrutiny, explicit task scope, focused tests, and an `ARCHITECTURE_CHECKPOINT.md` update when behavior, schema, retrieval, or MCP contracts change.
- Do not change live MCP/Codex defaults, production DB paths, or v1 schema behavior without explicit user instruction.

Muninn v2 is adjacent, opt-in substrate work:
- v2 development belongs under `src/muninn/v2` unless a task explicitly says otherwise.
- v2 must not run automatic migration, cutover, MCP route replacement, or production DB writes on import/startup.
- v2 should provide explicit adapters, dry-run pilots, export/import paths, and parity reports before any live adoption discussion.
- New substrate work should bias toward v2, while v1 remains the active/live branch of use unless the task explicitly says to modify v1.

Current v2 milestone order:
1. record-existence parity
2. retrieval parity measurement
3. retrieval design
4. explicit cutover planning only after evidence supports it

## 1.2) Canonical Muninn Memory Protocol (for integrating agents)
Repositories that integrate Muninn should use this workflow as operational policy:

On task start (before substantial edits):
- Call `muninn.spaces.resolve` with current absolute `cwd`.
- Use the returned `space.key` as `<resolved-space-key>` for retrieval calls.
- Preferred: call `muninn.rehydrate.bundle` with:
  - `lens`: `{space_key:"<resolved-space-key>", scope:"soft", kinds:["decision","constraint","runbook","interface"], limit:12}`
  - `query`: short task summary.
- Compatibility sequence (when bundle is unavailable):
  - `muninn.cards.recent` with `lens`: `{space_key:"<resolved-space-key>", scope:"strict", kinds:["decision","constraint","runbook","interface"], limit:12}`
  - `muninn.cards.search` with `lens`: `{space_key:"<resolved-space-key>", scope:"soft", kinds:["decision","constraint","runbook","interface"], limit:12}` and short task query.
- If `space_key` is unavailable, pass a full lens with `space:"auto"` and absolute `cwd`.
- Use retrieved memory before implementation decisions.

On meaningful completion:
- Persist durable outcomes with `muninn.cards.upsert` (`1-3` cards per meaningful task).
- Send object-shaped upsert arguments only (never prose strings for `card`).
- Canonical upsert payload:

```json
{
  "lens": {
    "space_key": "<resolved-space-key>",
    "scope": "strict"
  },
  "card": {
    "kind": "decision",
    "title": "Summarize the durable decision",
    "summary": "One to three sentences with the durable outcome.",
    "body": "Durable details that should survive future sessions."
  },
  "evidence": [
    {"type": "file", "ref": "/abs/path/file.py:42"}
  ]
}
```

- For `decision`, `constraint`, `interface`, and `runbook`, include at least one evidence ref whenever applicable.
- If evidence is unavailable, do not fabricate it; delay the durable write or mark explicit follow-up and treat it as non-compliant until evidence is added.
- Prefer `muninn.cards.supersede` / `muninn.cards.merge` when refining existing threads.

Memory hygiene:
- Do not persist transient reasoning, scratch notes, or speculative output.
- Prefer `strict` scope by default; use `soft` only when cross-project recall is intentional.
- Regression gate command:
  - `cd /mnt/data/Muninn && PYTHONPATH=src python3 -m muninn.cli audit --last 24h --json --gate`

## 2) Precedence and Global Standards
This repo follows the canonical global baseline:

- `/home/unix/codex-standards/BASELINE.md`

Precedence order:
1. Direct user instruction
2. This file (`AGENTS.md`)
3. `/home/unix/codex-standards/BASELINE.md`
4. `/home/unix/.codex/AGENTS.md` bootstrap pointer

Any deviation from global standards MUST be explicitly documented below.

---

## 3) Core Invariants (Do Not Break)

### 3.1 Memory correctness over feature breadth
- Memory retrieval and rehydration MUST be reliable and explainable.
- Do not introduce features that weaken determinism or traceability.

### 3.2 Deterministic rehydration
- Rehydration MUST follow a defined staged process.
- All stages MUST be observable via logs.
- Silent fallback or implicit behavior is non-compliant.

### 3.3 Separation of concerns
- Cards store facts/state
- Interaction events store raw behavioral signals
- Policy cards store derived behavioral constraints

These MUST NOT be conflated.

### 3.4 Canonical space resolution
- All memory operations MUST resolve to a canonical space.
- Alias or fallback behavior MUST be explicit and logged.

### 3.5 Backward compatibility
- Existing query paths and contracts MUST NOT be broken without explicit migration handling.

### 3.6 Cross-project contract discipline (Muninn <-> Mimir)
- Shared contract surfaces are interface surfaces; contract changes are interface changes.
- Treat tool inputs/outputs, query envelopes, retrieval semantics, and startup patterns as contract surfaces.
- Any shared-contract change MUST update:
  - shared artifacts/docs in both repos (`docs/CROSS_PROJECT_COMPATIBILITY.md`, `docs/contracts/muninn_mimir/v1`)
  - compatibility tests in both repos
- Any shared-contract change MUST include explicit sibling-project compatibility review.
- If downstream compatibility work is deferred, record it explicitly in the same change with scope and follow-up note.

---

## 4) Architecture Discipline

- The file `ARCHITECTURE_CHECKPOINT.md` is the source of truth for:
  - runtime structure
  - data model
  - ingestion and retrieval flows
  - adaptation/policy pipeline

- Any change to:
  - memory schema
  - rehydration logic
  - policy/adaptation logic
  - MCP interface behavior

  MUST update `ARCHITECTURE_CHECKPOINT.md` in the same change.

- Do not implement cross-cutting architectural changes without explicit task scope.

---

## 5) Observability Requirements

Muninn is a decision system and MUST be observable.

At minimum, logs MUST make it possible to determine:
- what request occurred
- which space was resolved
- which rehydration stages executed
- what each stage returned
- why a result was empty
- what policy/adaptation actions were taken

Silent failure or empty-result behavior without explanation is non-compliant.

---

## 6) Allowed Changes

Permitted without escalation:
- bug fixes that improve correctness
- improvements to logging and observability
- internal refactors that do not change behavior
- schema extensions that are backward-compatible

Requires explicit task-level approval:
- changes to rehydration semantics
- changes to memory data model
- changes to policy/adaptation behavior
- changes that affect MCP contract or external interfaces
- merging or removing `/v0` compatibility paths

---

## 7) Non-Goals (Unless Explicitly Requested)

- Do not unify `/v0` and human-memory systems prematurely
- Do not introduce large-scale semantic retrieval systems
- Do not add new subsystems without clear architectural placement
- Do not expand scope beyond the defined task

---

## 8) Repo Structure Expectations

This repo MUST maintain:

- `AGENTS.md` — this file (repo contract)
- `RUNBOOK.md` — operational procedures
- `ARCHITECTURE_CHECKPOINT.md` — current system map
- `docs/tasks/` — temporary task sheets and investigations

The following MUST NOT occur:
- task sheets in root
- stale root `PLANS.md` files treated as live direction
- architecture defined in multiple conflicting docs
- untracked canonical guidance files

---

## 9) Exceptions

No exceptions currently defined.

Any future exception to global standards MUST:
- be documented here
- include rationale
- be narrowly scoped

---

## 10) Reporting Requirements

All changes MUST include a summary stating:
- what was changed
- what was intentionally not changed
- any risks introduced
- whether `ARCHITECTURE_CHECKPOINT.md` was updated or reviewed

## Cross-Project Atlas Check
For cross-project architecture, ownership, capability placement, duplication risk, or boundary questions, consult Bifrost (`/mnt/data/Bifrost`) before making substantial changes.
