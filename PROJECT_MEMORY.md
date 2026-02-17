# Project Memory — Muninn (stateful)

## Mission
Build a standalone, pluggable memory harness for LLM agents that supports:

- durable canonical memory (facts/episodes/preferences) with provenance
- safe write-gating and auditability
- conceptual recall via compact memory cards
- clean integration interfaces (HTTP + provider adapters)

## Human Overview

### What it is
Muninn is an HTTP memory service for LLM applications. It sits beside your agent/orchestrator and provides durable memory operations without coupling to any specific model provider.

### What it does
- Stores canonical memory objects (facts, episodes, preferences) with provenance.
- Retrieves relevant memories for the current turn (lexical, vector, or hybrid).
- Renders compact memory cards for prompt context.
- Applies safety gates for writes, including a confirm-required queue for sensitive candidates.
- Exposes operational controls: migrations, debug stats, cleanup, readonly mode, optional API key protection.

### How it is done
- FastAPI service layer (`api.py`) exposes stable endpoints.
- SQLite canonical store with additive migrations (`schema.sql` + `scripts/migrations`).
- Retrieval pipeline combines FTS5, vector similarity, and RRF fusion.
- Policy + writeback pipeline enforces guardrails and dedupe/merge behavior.
- Pending workflow tables (`pending_candidates`, `candidate_decisions`) close the write lifecycle loop.
- Ops modules provide cleanup and observability endpoints.

## Architecture Map

- Ingress/API:
  - `src/muninn/api.py`
- Domain models:
  - `src/muninn/models.py`
- Memory pipeline:
  - `src/muninn/memory/policy.py`
  - `src/muninn/memory/writeback.py`
  - `src/muninn/memory/pending.py`
  - `src/muninn/memory/retrieval.py`
  - `src/muninn/memory/cards.py`
- Vector subsystem:
  - `src/muninn/vector/store.py`
  - `src/muninn/vector/sqlite_vec_backend.py`
  - `src/muninn/vector/reindex.py`
- Ops/security:
  - `src/muninn/ops/stats.py`
  - `src/muninn/ops/cleanup.py`
  - `src/muninn/middleware/auth.py`
- Persistence:
  - `src/muninn/schema.sql`
  - `scripts/migrations/*.sql`
  - `scripts/init_db.py`

## Turn Lifecycle (high-level)

1) Rehydrate: retrieve relevant memory and render cards for prompt injection.
2) Respond: agent answers user.
3) Stage: agent submits memory candidates.
4) Decide:
   - benign -> written to canonical tables
   - sensitive -> queued pending confirmation
   - unsafe/instruction-like -> rejected
5) Confirm/reject pending candidates.
6) Observe and maintain with debug stats and cleanup.

## Current Snapshot

- Repo scaffold created (FastAPI + SQLite)
- Schemas defined for core objects + memory cards
- Endpoints implemented:
  - health
  - write_candidates
  - retrieve
  - render_cards
  - rehydrate
  - upsert_embeddings
  - query_vector
  - memory/version
- Retrieval supports mode toggle:
  - `fts` (default)
  - `vector` (caller-provided query embedding)
  - `hybrid` (FTS + vector fused with RRF)
- Embeddings are caller-provided and stored in SQLite as normalized float32 blobs
- Optional sqlite-vec acceleration added with automatic fallback to brute-force
- Namespace isolation enforced in storage/query paths (v0.5)
- Admin reindex path added to rebuild sqlite-vec mappings from canonical embeddings
- Typed `MuninnClient` + OpenAI/Anthropic/local adapters added with contract tests (v0.6)
- Confirm-required lifecycle added: stage/list/confirm with durable pending queues (v0.7)
- Ops hardening added: cleanup endpoint, debug stats, readonly mode, optional API key middleware (v0.8)
- CLI baseline added for installability (`muninn up`, `muninn doctor`, `muninn status`)
- Universal local run hardened: `muninn up` now auto-creates config/data dirs, initializes DB+migrations, prints startup banner, and reports actionable port conflicts
- Local MCP wrapper added (`muninn mcp up`) with HTTP forwarding for core memory tools
- ChatGPT connector prep added: `muninn enable-chatgpt` provisions API key config, ensures API+MCP background services, and prints local MCP endpoint/header/key
- ChatGPT connector tunnel automation added: `enable-chatgpt` can download/use `cloudflared`, start quick tunnel, and print HTTPS `/mcp` URL

## Key Constraints

- Avoid storing raw transcripts as “memory”
- Memory is facts/episodes/preferences with confidence + provenance
- “Instruction injection” never stored (firewall)
- Muninn stays model-agnostic (no built-in embedding model coupling)

## Next Steps (nearest)

- Add ANN backend behind existing vector store interface (sqlite-vec / pgvector)
- Add admin authz layer for `/v0/admin/*` endpoints
- Add background reindex flow for sqlite-vec mappings after long brute-force-only periods
- Add contradiction ledger + merge/dedupe policies
- Add sensitivity tiers + redaction filters
