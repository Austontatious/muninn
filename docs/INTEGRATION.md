# Integration — Muninn

Muninn is a memory harness you call over HTTP.
All reads/writes are namespace-scoped at the DB layer. Always pass the correct `namespace`.

## Endpoints (v0)
- `POST /v0/memory/rehydrate`
- `POST /v0/memory/retrieve`
- `POST /v0/memory/write_candidates`
- `POST /v0/memory/stage_candidates`
- `POST /v0/memory/list_pending`
- `POST /v0/memory/confirm_candidates`
- `GET /v0/memory/pending`
- `POST /v0/memory/upsert_embeddings`
- `POST /v0/memory/query_vector`
- `GET /v0/memory/version`
- `GET /v0/debug/vector_backend`
- `GET /health`

## Tool calling (generic)
### 1) Rehydrate memory for the current user message
Request:
```json
{
  "namespace": "lexi",
  "query": "user message here",
  "entity_id": "ent_user",
  "k": 8,
  "profile": "lexi",
  "embedding_model": "text-embedding-3-small",
  "query_embedding": [0.12, -0.03, 0.44]
}
```

Response:
- `cards[]` (compact conceptual memory)
- `items[]` (raw retrieved snippets, for audit/debug)

### 2) Write memory candidates after you respond
Request:
```json
{
  "namespace": "lexi",
  "candidates": [
    {
      "kind": "preference",
      "entity": {"id":"ent_user","kind":"user","name":"Auston"},
      "payload": {"key":"style.response","value":"direct"},
      "confidence": 0.9,
      "provenance": {"source_type":"user","source_id":"chat_turn_123"}
    }
  ]
}
```

`/v0/memory/write_candidates` is a direct write path for trusted callers.
For user-facing flows, prefer the confirm-required workflow below.

## Confirm-required workflow
Use this for user-facing memory capture to avoid silently storing sensitive data.

1) Call `/v0/memory/stage_candidates` with candidate memories.
2) Muninn auto-writes benign candidates and queues sensitive ones as pending.
3) Call `/v0/memory/list_pending` (or `GET /v0/memory/pending`) to show pending items.
4) Ask the user/agent to confirm.
5) Call `/v0/memory/confirm_candidates` with `decision=accept|reject`.

### Stage candidates
Request:
```json
{
  "namespace": "lexi",
  "ttl_seconds": 3600,
  "candidates": [
    {
      "kind": "preference",
      "entity": {"id":"ent_user","kind":"user","name":"Auston"},
      "payload": {"key":"health.note","value":"sensitive"},
      "confidence": 0.9,
      "provenance": {"source_type":"user","source_id":"turn_123"}
    }
  ]
}
```

Response shape:
```json
{
  "accepted": 0,
  "pending": 1,
  "rejected": 0,
  "accepted_ids": [],
  "pending_ids": ["pend_..."],
  "reject_reasons": [],
  "pending_reasons": ["CONFIRM_REQUIRED: ..."]
}
```

### Confirm candidates
Request:
```json
{
  "namespace": "lexi",
  "pending_ids": ["pend_..."],
  "decision": "accept",
  "decided_by": "user:123",
  "note": "approved"
}
```

## Embeddings: caller-provided
Muninn is model-agnostic. Callers compute embeddings and upsert them.
Current vector search is brute-force over SQLite rows by default.

Flow:
1) Caller computes embeddings for each memory item text and upserts via `/v0/memory/upsert_embeddings`.
2) On each query, caller computes query embedding and calls `/v0/memory/rehydrate` with `embedding_model` + `query_embedding`.

### Upsert embeddings
Request:
```json
{
  "namespace": "lexi",
  "items": [
    {
      "item_id": "fact_abc123",
      "kind": "fact",
      "entity_id": "ent_user",
      "model": "text-embedding-3-small",
      "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    }
  ]
}
```

Response:
```json
{
  "upserted": 1,
  "rejected": 0,
  "reasons": []
}
```

### Query vector
Request:
```json
{
  "namespace": "lexi",
  "model": "text-embedding-3-small",
  "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
  "entity_id": "ent_user",
  "kinds": ["fact", "preference"],
  "k": 8
}
```

## Vector acceleration (optional sqlite-vec)
Muninn stays portable by default. `sqlite-vec` acceleration is best-effort and optional.

- Default backend: brute-force (`embeddings` table scan)
- Optional backend: sqlite-vec (`vec0` KNN) when available and enabled

Environment variables:
- `MUNINN_VEC_BACKEND=auto|bruteforce|sqlite_vec`
- `MUNINN_SQLITE_VEC_ENABLED=1|0`
- `MUNINN_SQLITE_VEC_PATH=/path/to/sqlite_vec.(so|dylib|dll)` (optional explicit extension path)
- `MUNINN_VEC_TABLE_PREFIX=muninn_vec` (prefix for generated vec0 tables)

Debug endpoint:
- `GET /v0/debug/vector_backend` returns configured backend, sqlite-vec load state, and effective backend.

macOS note:
- System Python/SQLite builds may block extension loading. If so, use a Python/SQLite build that supports loadable extensions.

Response:
```json
{
  "hits": [
    {
      "item_id": "fact_abc123",
      "kind": "fact",
      "entity_id": "ent_user",
      "score": 0.992
    }
  ]
}
```

## ChatGPT (OpenAI-style tools) — suggested tool shapes
Use tools:
- `muninn_rehydrate(query, namespace, entity_id, k, profile, embedding_model?, query_embedding?)`
- `muninn_write_candidates(namespace, candidates)`
- `muninn_stage_candidates(namespace, candidates, ttl_seconds?)`
- `muninn_list_pending(namespace, entity_id?, status?, limit?)`
- `muninn_confirm_candidates(namespace, pending_ids, decision, decided_by, note?)`
- `muninn_upsert_embeddings(namespace, items)`
- `muninn_query_vector(namespace, model, query_vector, entity_id?, kinds?, k?)`

Your agent should:
- call `muninn_rehydrate` at the start of a turn
- inject `<SYSTEM_MEMORY>` cards into the prompt
- after answering, prefer `muninn_stage_candidates` then `muninn_confirm_candidates` for sensitive items
- periodically upsert embeddings for new/updated memory records

## Claude tools (Anthropic-style)
Same flow; only tool JSON differs. Keep request/response payloads identical.

## Local agents
Call with `httpx`/`requests`. Example in `examples/cli_agent_demo.py`.

## Prompt injection block
Recommended:
```text
<SYSTEM_MEMORY>
{cards rendered as bullets}
</SYSTEM_MEMORY>
```

Keep cards short. Do not paste raw transcripts.

## Ops

Admin vector reindex endpoint:
- `POST /v0/admin/reindex_vectors`

This endpoint rebuilds sqlite-vec mappings from canonical `embeddings` rows for a namespace.
It is intended for operational use only; protect behind network/auth controls in production.

## Provider adapters (included)

Muninn ships lightweight provider helpers without SDK lock-in:

- OpenAI style:
  - `muninn.adapters.openai_tools.openai_tools_spec`
  - `muninn.adapters.openai_tools.dispatch_openai_tool_call`
- Anthropic style:
  - `muninn.adapters.anthropic_tools.anthropic_tools_spec`
  - `muninn.adapters.anthropic_tools.dispatch_anthropic_tool_call`
- Local typed client:
  - `muninn.client.MuninnClient`

Examples:
- `examples/openai_tools_demo.py`
- `examples/anthropic_tools_demo.py`
- `examples/local_client_demo.py`

## Minimal agent loop

1) Call rehydrate (`/v0/memory/rehydrate`) with current message + namespace/entity.
2) Inject returned cards into a `<SYSTEM_MEMORY>` block.
3) Generate the assistant response.
4) Propose `0..N` write candidates (facts/preferences/episodes with provenance).
5) Call stage/confirm (`/v0/memory/stage_candidates` + `/v0/memory/confirm_candidates`) or direct write for trusted flows.
