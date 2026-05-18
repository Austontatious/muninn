# ADR-0010: Muninn v2 Personal Local Live Trial

## Problem

Muninn v2 has passed shadow migration, bridge, replay, and operations drills,
but isolated offline validation does not prove the context payload survives
normal Codex workflow pressure. A controlled personal/local live trial is needed
before any broader production cutover.

## Options Considered

1. Replace the live v1 MCP server with a v2 MCP implementation.
2. Change the global Codex MCP config to point at a new v2 service.
3. Use a local read-only v2 bridge helper while preserving v1 MCP as rollback
   and preserving the existing v1 write path.

## Decision

Use option 3.

Phase J activates a personal/local read-path trial through
`scripts/muninn_v2_live_context.py`. The helper consumes explicit v2 shadow DBs
through the existing read-only v2 bridge, writes audit artifacts under
`logs/live_trial/`, and renders deterministic context for the current task.

The trial does not replace the v1 MCP server, does not modify v1 schemas or
DB paths, does not enable adaptive retrieval by default, and does not introduce
v2 writes.

## Rationale

This path exercises the real context payload while keeping rollback mechanical.
It also preserves current v1 completion-card behavior, which is already part of
the local workflow, without silently porting writes into v2.

## Consequences

- Agents in this repo should use the v2 helper first for context reads during
  the personal/local trial.
- v1 MCP remains available for fallback after a logged v2 failure.
- Existing completion-card writes remain v1-only.
- Trial logs and bridge artifacts become the evidence for a 24-48 hour review.
- General production cutover remains blocked.

## Explicit Deferrals

- No network v2 bridge service.
- No v2 MCP replacement.
- No global Codex config rewrite.
- No adaptive default retrieval.
- No autonomous or implicit v2 memory writes.
- No Muninn-self production migration authority change.
