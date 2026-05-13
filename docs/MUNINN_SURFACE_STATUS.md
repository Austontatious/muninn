# Muninn Surface Status

Last updated: 2026-04-05

## Canonical surfaces

The canonical architecture is SDK-first with runtime adapters:

- **SDK core**: `muninn.core` (canonical envelopes, app packs, `Muninn` orchestration).
- **App packs**: `src/muninn/packs/*` (app-defined memory contracts and bundle specs).
- **Core storage adapter**: `core.storage.HumanMemoryStore` (canonical human-memory DB adapter).
- **Runtime adapters** (thin wrappers):
  - MCP server (`src/muninn/mcp_server.py`)
  - HTTP API (`src/muninn/api.py`, non-`/v0` routes)
  - CLI (`src/muninn/cli.py`)

New integrations should target the SDK core or MCP tools, not the `/v0/*` plane.

## Transitional / compatibility surfaces

The following surfaces remain for compatibility and local workflows:

- **`/v0/*` HTTP routes**
  - Routed through `core.v0_runtime.V0Runtime` for a single v0 logic path.
  - Backed by the legacy `muninn.db` schema and vector store.
  - Intended for compatibility only, not new integrations.

- **`/v0/memory/procedures/*`**
  - Routed through `core.procedures.ProcedureStore` for a single procedural logic path.
  - Still exposed under `/v0` for compatibility.

- **`/v0/debug/*` and `/v0/admin/*`**
  - Operational/debug-only endpoints.
  - Preserved for local operators; not part of the SDK surface.

## Notes

- The v0 routes are intentionally documented and kept stable for local workflows.
- The canonical direction is SDK core + runtime adapters; v0 should remain a thin compatibility layer until it can be retired safely.
