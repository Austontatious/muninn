# ADR-0001: Durable Memory Boundary Ownership

## Problem
Cross-project runtime work risked letting orchestration or topology systems absorb durable memory responsibilities, causing unclear ownership for schema, versioning, and compatibility.

## Options considered
1. Keep implicit shared ownership across Muninn, Friday, and Mimir.
2. Assign durable memory ownership explicitly to Muninn and require interface consumption by other repos.

## Decision
Adopt explicit ownership contract `bnd-friday-muninn-memory-lifecycle-v1` and `bnd-mimir-muninn-topology-memory-v1`.

- Producer ownership for durable memory schema/lifecycle: Muninn.
- Version ownership for memory-side envelopes produced by Muninn: Muninn.
- Friday and Mimir consume supported interfaces/contracts only.
- Bifrost atlas records are consumable metadata, not memory-lifecycle authority transfer.

## Rationale
Durable memory lifecycle is a single control surface with persistence and policy implications; split ownership causes drift and undermines auditability.

## Consequences
- Friday must not mutate durable memory schema or lifecycle semantics.
- Mimir topology compatibility remains shape-aligned but runtime-independent.
- Cross-project changes touching memory boundaries require synchronized compatibility docs and contract validation.

## Explicit deferrals
- Transport-level error envelope harmonization across Muninn and Mimir remains deferred to a later contract version.
