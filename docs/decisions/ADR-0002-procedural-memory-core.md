# ADR-0002: Procedural Memory as a First-Class Core Concept

Date: 2026-04-05

## Problem

Muninn needs to reduce repeated reasoning and token burn in Codex/Sindri/Friday workflows. The highest ROI memory is operational procedure knowledge (startup, validation, recovery, troubleshooting). Procedural memory previously lived only in legacy `/v0` routes and was not a first-class SDK/core primitive.

## Options Considered

1. **Keep procedures as legacy-only**
   - Pros: minimal change.
   - Cons: split-brain architecture, no SDK support, poor reuse for embedded mode.

2. **Model procedures as generic memory items only**
   - Pros: uses existing MemorySpec/BundleSpec.
   - Cons: loses typed structure and projection semantics needed for token efficiency.

3. **Add first-class procedural primitives in core** (chosen)
   - Pros: typed structure, staged retrieval, compact projections, consistent lifecycle/supersession.
   - Cons: adds a new core surface to maintain.

## Decision

Add `core.procedures` with typed procedure models, staged retrieval, and projection helpers. Rewire `/v0/memory/procedures/*` to use the new core adapter while preserving compatibility. SDK (`Muninn`) gains `write_procedure`, `query_procedures`, `rehydrate_procedure_bundle`, and `reflect_procedure` surfaces.

## Rationale

Procedural memory is the primary optimization target for technical agents. A first-class core primitive allows compact, role-shaped bundles and maintains lifecycle/supersession without bloating prompts or duplicating logic across runtime adapters.

## Consequences

- New SDK/core surface for procedures is now canonical.
- `/v0/memory/procedures/*` becomes a compatibility wrapper.
- Apps can adopt procedure primitives without redefining generic memory types.

## Explicit Deferrals

- No automatic migration of all app packs to procedure-first semantics.
- No cross-project rollout beyond documentation in this pass.
- No broad UI/admin tooling for procedure management yet.
