# AGENTS.md — Muninn

## 1) Purpose
Muninn is the canonical memory and learning substrate.

It is responsible for:
- durable memory storage (cards, evidence, spaces)
- deterministic rehydration of context
- interaction-event capture
- policy/adaptation state derived from behavior

Muninn is not an orchestrator or agent. It is a **state system**.

---

## 2) Precedence and Global Standards
This repo follows global standards defined at:

- `/mnt/data/GLOBAL_STANDARDS.md`
- `/mnt/data/AGENTS_CORE.md`

Precedence order:
1. Direct user instruction
2. This file (`AGENTS.md`)
3. Global standards
4. Core agent baseline

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
