# ADR-0008: Muninn v2 Adjacent Core Foundation

Date: 2026-05-13

## Problem

Muninn v1 is live production infrastructure for Codex-facing durable memory. Muninn needs a v2 substrate foundation, but an in-place rewrite or automatic migration would risk breaking active MCP, CLI, HTTP, and storage workflows.

## Options Considered

1. Rewrite v1 in place.
   - Rejected because v1 is live infrastructure and current contracts must remain stable.
2. Add v2 concepts into existing v1 modules and schemas.
   - Rejected for this slice because it would increase split-brain coupling and make rollback harder.
3. Create an adjacent v2 core with explicit contracts, separate storage, and read-only v1 adapters.
   - Accepted because it creates a safe foothold while preserving v1 behavior.

## Decision

Create `src/muninn/v2` as an adjacent package. It defines minimal typed primitives, protocol contracts, a separate SQLite store, JSON/JSONL export support, and read-only v1 import adapters.

The v2 store writes only to paths explicitly passed by the caller. It does not use v1 environment variables, open v1 production databases, or run migrations on import.

## Rationale

This preserves live v1 behavior while allowing v2 contracts to be proven on a narrow pilot. It also keeps durable-memory substrate responsibilities separate from Mimir salience/cognition and Hrafnar runtime/protocol concerns.

## Consequences

- v1 MCP, HTTP, CLI, and storage contracts remain untouched.
- v2 has its own schema tables prefixed with `v2_`.
- v1-to-v2 mapping is partial and read-only by default.
- Consumers must opt into v2 by importing `muninn.v2` and choosing a v2 DB path.
- No production data migration runs automatically.

## Explicit Deferrals

- No global cutover.
- No v1 schema migration.
- No automatic production import.
- No vector canonical truth model.
- No salience propagation engine.
- No Hrafnar runtime/UI layer.
- No Mimir cognition or topology processing inside Muninn v2.
