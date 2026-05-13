# Cross-Project Compatibility (Muninn <-> Mimir)

## Purpose

Muninn and Mimir stay independently deployable, but the shared query and retrieval boundary must not drift silently.
This document defines the cross-repo contract surface that must remain mechanically aligned in both repos.

## Current Version

- Contract set: `muninn-mimir-shared`
- Current version: `1.0.0`
- Schema family: `v1`
- Version source of truth: `docs/contracts/muninn_mimir/v1/versions.json`

## Shared Schemas

Locked by schemas under `docs/contracts/muninn_mimir/v1/schemas/`:
- `card-envelope.v1.schema.json`
- `lifecycle-state.v1.schema.json`
- `provenance-envelope.v1.schema.json`
- `confidence-trust.v1.schema.json`
- `rehydrate-request.v1.schema.json`
- `rehydrate-response.v1.schema.json`
- `topology-ref.v1.schema.json`
- `mimir-memory-proposal-batch.v1.schema.json`

## Query Formats And Retrieval Contracts

The following surfaces are shared contracts, even if runtime implementations differ:
- card envelope projection used for durable memory results
- lifecycle and confidence projection used in downstream ranking and trust handling
- provenance envelope used to explain where a retrieved item came from
- `rehydrate-request` envelope used to express scope, kinds, and lookup intent
- `rehydrate-response` envelope used to return cards, summaries, and retrieval metadata
- topology reference projection used when Mimir-originated repo structure is attached to Muninn-oriented flows
- Mimir memory proposal batch projection used for guarded, review-required Muninn import workflows

Internal models may differ. Shared external projections may not.

## Golden Examples

Golden fixtures live under `docs/contracts/muninn_mimir/v1/examples/`.

Valid examples:
- `examples/valid/card-envelope.basic.v1.json`
- `examples/valid/lifecycle-state.active.v1.json`
- `examples/valid/provenance-envelope.query.v1.json`
- `examples/valid/confidence-trust.medium.v1.json`
- `examples/valid/topology-ref.anchor.v1.json`
- `examples/valid/rehydrate-request.soft.v1.json`
- `examples/valid/rehydrate-response.basic.v1.json`
- `examples/valid/mimir-memory-proposal-batch.basic.v1.json`

Invalid examples:
- `examples/invalid/card-envelope.missing-provenance.v1.json`
- `examples/invalid/lifecycle-state.bad-value.v1.json`
- `examples/invalid/topology-ref.missing-relation.v1.json`
- `examples/invalid/rehydrate-request.bad-scope.v1.json`
- `examples/invalid/rehydrate-response.bad-item.v1.json`
- `examples/invalid/mimir-memory-proposal-batch.missing-evidence.v1.json`

## Current Deferred Surface

- Error and validation envelope harmonization is deferred in v1. Muninn and Mimir still expose different transport-level error formats, so that envelope is intentionally not treated as shared until explicitly versioned.

## Producer And Consumer View

- Muninn provides memory-card envelopes, rehydrate semantics, and provenance-bearing memory results consumed by cross-project integrations.
- Mimir provides topology-aware repo projections and consumes the shared envelope semantics when interfacing with Muninn-oriented workflows.
- Mimir provides review-required memory proposal artifacts; Muninn validates and previews them before any future explicit approval/write path.

## Authoritative Artifact Locations

Both locations are canonical and must stay byte-identical for the same version:
- `/mnt/data/Muninn/docs/contracts/muninn_mimir/v1`
- `/mnt/data/Mimir/docs/contracts/muninn_mimir/v1`

## Versioning And Compatibility Policy

Backward-compatible changes:
- add optional fields only
- add safely ignorable enum values only when both repos can ignore them
- add examples or tests without changing required semantics

Breaking changes:
- remove or rename required fields
- narrow enums or change existing value meaning
- change envelope meaning without a new contract version

## Required Change Workflow

When a shared contract changes:
1. Update schemas and fixtures in both repos.
2. Update this document and the sibling repo copy.
3. Update compatibility tests in both repos.
4. Run validation in both repos.
5. If sibling compatibility work is deferred, record the gap explicitly in the same change.

## Deferred Gaps Log Policy

If a known compatibility gap is not fixed immediately, record:
- affected surface
- impacted repo or repos
- temporary behavior
- follow-up owner and expected fix window

## Core Boundary Ownership Matrix (Phase B)

Canonical boundary contract records are maintained in:
- `/mnt/data/Bifrost/atlas/boundaries.json`

| Boundary ID | Producer | Consumer | Schema Owner | Version Owner | Compatibility Owner |
| --- | --- | --- | --- | --- | --- |
| `bnd-friday-muninn-memory-lifecycle-v1` | muninn | friday | muninn | muninn | friday |
| `bnd-mimir-muninn-topology-memory-v1` | mimir | muninn | mimir | mimir | muninn |
| `bnd-bifrost-atlas-authority-v1` | bifrost | muninn | bifrost | bifrost | muninn |

## Muninn Scope Lock

In scope for Muninn at cross-project boundaries:
- durable memory substrate schema/lifecycle ownership
- versioning of memory-side envelopes where Muninn is producer
- compatibility validation for consumers of Muninn memory interfaces

Out of scope for Muninn at cross-project boundaries:
- orchestration ownership (Friday)
- repo-topology internals ownership (Mimir)
- cross-project vocabulary authority ownership (Bifrost)
- product-surface ownership (Lex)
