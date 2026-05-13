# ADR-0003: ChatGPT Muninn MCP Bridge

## Problem

ChatGPT needs a private HTTPS MCP connector that can read Muninn durable memory, rehydrate project context, and propose memory updates without exposing raw mutation, admin, debug, shell, arbitrary file, or arbitrary network access.

The connector must preserve project boundaries: Muninn owns durable user/project memory and staged memory lifecycle, while Mimir owns repository topology/world-state. Shape compatibility or references to Mimir must not become runtime ownership transfer.

## Options Considered

1. Expose the existing full Muninn MCP server directly.
   - Rejected because the current local MCP surface contains broader human-memory tools than the ChatGPT connector should expose.
2. Add ChatGPT compatibility tools to `src/muninn/mcp_server.py`.
   - Rejected for first production behavior because it would mix private ChatGPT path-prefix deployment concerns into the local Codex-facing MCP surface.
3. Add a narrow standalone FastMCP bridge that calls allowed Muninn HTTP routes.
   - Selected because it keeps the public connector small, auditable, and independently deployable next to Dockerized Muninn.

## Decision

Add `apps/muninn_mcp/server.py` as a standalone FastMCP streamable HTTP bridge named `Muninn Memory`.

The bridge exposes only:

- `search`
- `fetch`
- `search_memory`
- `fetch_memory`
- `rehydrate_project`
- `stage_memory_candidates`
- `list_pending_memory`
- `confirm_memory_candidates`

It calls only the allowed Muninn HTTP routes:

- `GET /health`
- `GET /v0/memory/version`
- `POST /v0/memory/retrieve`
- `POST /v0/memory/rehydrate`
- `POST /v0/memory/render_cards`
- `POST /v0/memory/stage_candidates`
- `POST /v0/memory/list_pending`
- `POST /v0/memory/confirm_candidates`

The adapter rejects forbidden raw-write/admin/debug routes before transport.

## Rationale

A standalone bridge creates a narrow public contract for ChatGPT without changing the existing Codex-facing MCP server. It allows path-prefix deployment through Traefik or existing TLS termination and keeps bridge-to-Muninn communication on Docker networking through `MUNINN_BASE_URL=http://friday-muninn-1:8000`.

Staged writes are intentionally two-step. `stage_memory_candidates` may propose candidates, but `confirm_memory_candidates` requires the exact confirmation phrase `CONFIRM MUNINN WRITE` before it calls Muninn. The bridge never calls `/v0/memory/write_candidates`.

The live Muninn `Provenance` schema accepts `source_type`, `source_id`, `note`, and `ts`. ChatGPT/MCP/write-mode provenance is therefore encoded into those allowed fields rather than sent as ignored arbitrary keys.

## Consequences

- ChatGPT gets compatibility `search`/`fetch` tools and richer Muninn-specific tools.
- The connector remains read-first with staged-write review.
- The public surface has no raw write/admin/debug tools.
- The bridge remains coupled to the legacy `/v0/memory/*` compatibility plane until a future public memory API is introduced.
- Traefik labels can route `https://<host>/mcp-<secret>/mcp` by stripping the secret prefix before the request reaches FastMCP's `/mcp` endpoint.

## Explicit Deferrals

- OAuth and per-user authorization are deferred. A long secret path prefix is acceptable only for a private prototype.
- Cloudflare tunnel changes are documented but not applied in this repo because the current tunnel config lives under `/mnt/data/Lex`.
- Tightening the existing Muninn host port binding from `0.0.0.0:18000` to loopback or no host port is documented but not applied here to avoid breaking existing Friday/local workflows.
- A direct Muninn get-by-id route is not added. `fetch` uses retrieve plus exact-match filtering.
