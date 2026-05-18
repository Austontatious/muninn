# Integration — Muninn

Muninn is a memory harness you call over HTTP.
All reads/writes are namespace-scoped at the DB layer.
When API-key auth is enforced, the server resolves namespace from auth and rejects cross-namespace overrides.
Client `namespace` fields are optional for compatibility.
When auth is not enforced, namespace overrides are ignored by default unless `MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE=1`.

For human-first lens testing outside the existing Cardex API surface, a standalone core schema is available at `migrations/0001_init.sql` with helpers under `src/muninn/human_memory/`.

## Muninn v2 Read-Only Bridge (Shadow Only)

Muninn v2 exposes a local CLI bridge for controlled read-only context
experiments:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-request \
  --v2-db /path/to/shadow_v2.db \
  --policy /path/to/bridge-policy.json \
  --request /path/to/bridge-request.json \
  --out-dir /path/to/output
```

Legacy narrow rehydrate-only compatibility:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-context \
  --request /path/to/bridge-request.json \
  --out-dir /path/to/output
```

The request must conform to `docs/contracts/muninn_v2_bridge/v1/schemas/bridge-request.v1.schema.json`.
The policy must conform to `docs/contracts/muninn_v2_bridge/v1/schemas/bridge-capability-policy.v1.schema.json`.
The bridge emits `BridgeResponseV1`; rehydrate responses embed the existing
`RehydrateResponseV1` JSON payload. This bridge is v2-only and
shadow/evaluation-only; it does not change live v1 HTTP endpoints, MCP tools, or
Codex defaults.

## Muninn v2 Personal Local Live Trial

Phase J adds a local operator helper for Auston's personal context-read trial:

```bash
python3 scripts/muninn_v2_live_context.py \
  --cwd "$PWD" \
  --query "short task summary"
```

The helper wraps the read-only v2 bridge and renders a deterministic context
block for the current project. It requires a configured explicit v2 DB in
`configs/muninn_v2_live_trial.json`, writes bridge audit artifacts under
`logs/live_trial/artifacts/`, and logs structured trial events under
`logs/live_trial/`.

This helper is local and reversible. It does not replace v1 MCP, does not expose
a network service, does not write v2 memory, and does not enable adaptive
retrieval by default.

Supported operations are `health`, `search`, `rehydrate`, and `explain`.
Requests that violate consumer, operation, space, project, budget, evidence,
explanation, adaptive-scoring, or reinforcement-write policy are denied before
retrieval.

Shadow consumer evaluation for bridge artifacts is available through:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-consumer-eval \
  --fixture /path/to/bridge-consumer-fixture.json \
  --out-dir /path/to/audit-output
```

This consumes existing `BridgeResponseV1` rehydrate artifacts, validates their
embedded `RehydrateResponseV1`, renders deterministic context blocks, verifies
audit replay hashes, and scores offline task coverage. It is an evaluation
harness only; it does not call live MCP, write v1, or change default context
selection.

Replayable shadow operations drills are available through:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-ops-drill \
  --fixture /path/to/bridge-ops-drill-fixture.json \
  --out-dir /path/to/drill-output
```

This runs multi-task shadow workflows through the v2 bridge in adaptive-off,
budget-pressure, and explicitly allowed adaptive-on modes. It verifies replay
audit hashes, cross-project contamination denials, continuity coverage, and
rendered context blocks for operator review. It remains offline, read-only, and
shadow-only.

Pre-live replay gate validation is available through:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-replay-gate \
  --drill-report /path/to/bridge_ops_drill_report.json \
  --v1-safety /path/to/v1_row_counts_before_after.json \
  --out-dir /path/to/gate-output \
  --run-failure-drills
```

The gate replays bridge audit hashes, verifies policy denial/contamination
checks, required-context retention, budget-pressure behavior, adaptive-off
defaults, adaptive-on state visibility, v1 untouched status, and expected
failure drills. It is a pre-live validation gate only; it does not authorize
cutover.

Common failure modes:

- `InvalidBridgeRequest`: request schema/required fields failed validation.
- `DeniedByPolicy`: consumer, operation, project, or safety setting is not
  allowed by policy.
- `V2DatabaseMissing`: explicit v2 DB path does not exist.
- `BridgeExecutionFailed`: read-only bridge execution failed after policy allow.

## Endpoints (v0)
- `POST /cards`
- `GET /cards/{card_id}`
- `POST /ingest`
- `POST /sources`
- `POST /sources/{source_id}/artifacts`
- `POST /cards/{card_id}/refs`
- `POST /embeddings`
- `POST /retrieve`
- `POST /promote`
- `POST /propose`
- `POST /confirm/{proposal_id}`
- `POST /reject/{proposal_id}`
- `POST /v0/memory/rehydrate`
- `POST /v0/memory/procedures/retrieve`
- `POST /v0/memory/procedures/reflect`
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

## MCP Human-Memory Tool Surface (v1)
The local MCP wrapper now exposes a lens-first human-memory tool set mapped to `src/muninn/human_memory/*`:

- `muninn.spaces.resolve`
- `muninn.cards.recent`
- `muninn.cards.search`
- `muninn.rehydrate.bundle`
- `muninn.policy.learn`
- `muninn.policy.inspect`
- `muninn.cards.adaptation.query`
- `muninn.cards.upsert`
- `muninn.cards.supersede`
- `muninn.cards.merge`
- `muninn.system.ping`

Deprecated aliases:
- Slash aliases (`muninn/spaces.resolve`, `muninn/cards.recent`, `muninn/cards.search`, `muninn/cards.upsert`, `muninn/cards.supersede`, `muninn/cards.merge`, `muninn/system.ping`) are still accepted for compatibility and are scheduled for removal in `v0.12`.
- Slash aliases also exist for adaptation query: `muninn/cards.adaptation.query` (deprecated; scheduled for removal in `v0.12`).

Transport modes:
- Primary: Streamable HTTP (`muninn mcp up`, default bind `127.0.0.1`).
- Compatibility: STDIO (`muninn mcp stdio`).
- Non-loopback HTTP binds are blocked unless auth is configured.

Input contract:
- Reads/writes accept a `lens` object.
- `lens.space` supports `auto|global`.
- `lens.space_key` can be used for explicit keys (`repo:*`, `path:*`, `cwd:*`, `global`).
- `lens.cwd` is required when `lens.space="auto"`.
- `lens.scope` supports `strict|soft`.
- `strict` means canonical project space only.
- `soft` means canonical project space first, then alias spaces, then `global`.
- Legacy compatibility is preserved for nested `{"lens": {...}}`, single `kind`, string `limit`, comma-separated filters, and legacy `key:value` string lenses.

Human-memory model:
- `cards`: durable project/task memories such as decisions, constraints, interfaces, runbooks
- `evidence`: files, diffs, commits, tests, logs, URLs, or user messages linked to cards
- `policy-state`: scoped behavioral lessons stored as typed cards (`policy.directive`, `policy.preference`, `policy.anti_pattern`, `workflow.heuristic`, `tooling.preference`, `rehydration.priority`)
- `interaction_events`: raw evaluative/directive traces used to promote policy-state without changing model weights

Canonical `space_key` strategy:
- prefer `repo:<sha(remote_norm)>` when a git remote is available
- fall back to `path:<sha(repo_root)>` for git repos without remotes
- fall back to `path:<sha(abs_cwd)>` for non-git paths
- legacy `path:*` and `cwd:*` keys are tracked as aliases and can be searched during transition

Rehydration flow:
- `muninn.rehydrate.bundle` makes the intended session-start sequence explicit in one call
- retrieval stages are:
  1) strict search
  2) recent strict
  3) soft search
  4) alias fallback
  5) recent evidence-backed cards
  6) global fallback when `scope=soft`
- policy-state is retrieved in parallel and returned separately from facts/evidence

Pseudo-RL / next-state adaptation:
- `muninn.policy.learn` captures evaluative and directive signals from normal use
- signals are stored first as interaction traces
- repeated or directive-rich traces promote into scoped policy-state cards
- future sessions retrieve those policy cards through `muninn.rehydrate.bundle` or `muninn.policy.inspect`
- this is memory/state adaptation only; Muninn does not update model weights live

Write behavior:
- `muninn.cards.upsert` is intended for durable changes only.
- Recommended cadence is 1-3 cards per meaningful task.
- `summary` should remain concise (1-3 sentences); `body` holds full durable context.
- Use `muninn.cards.supersede` and `muninn.cards.merge` to preserve card lineage instead of deleting/replacing in place.
- write handlers enrich `context.provenance` with:
  - `source_class`: `user_provided | tool_derived | model_inference | preference_or_instruction`
  - `evidence_count`
  - `evidence_types`
  - `warning_codes`
- `decision`, `constraint`, `interface`, `runbook`, and policy-state cards warn when evidence is missing
- Soft write-rate limiting is enabled by default for new card creation in MCP upsert:
  - `MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR` (default `20`, set `0` to disable)
  - `MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS` (default `3600`)

LAILA adaptation query behavior:
- `muninn.cards.adaptation.query` provides deterministic retrieval for typed adaptation memories:
  - direct preference (`preference.direct`)
  - inferred preference (`preference.inferred`)
  - scoped override (`override.scoped`)
  - correction (`correction`)
  - outcome (`outcome`)
- Query supports filters for `subject_id`, `category`, `scope`, `persistence`, `session_id`, `source_type`, tags, and recency (`max_age_days`).
- Query exposes preset views:
  - `durable_preferences`
  - `recent_overrides`
  - `corrections`
  - `outcomes`
  - `prompt_state`
- Response includes deterministic `counts` and `prompt_state` grouping by category.
- See:
  - `docs/laila_adaptation_memory.md`
  - `docs/query_contracts.md`

Error contract:
```json
{
  "error": {
    "code": "InvalidArguments|SpaceResolutionFailed|WriteRateLimited|DatabaseUnavailable|ConstraintViolation|InternalError",
    "message": "Short actionable error",
    "details": {}
  }
}
```

Validation/debug notes:
- malformed legacy payloads degrade to `InvalidArguments` instead of `InternalError`
- error details include best-effort `field` names when available
- `lens.space="auto"` with missing or blank `lens.cwd` is rejected during lens validation before space resolution runs
- database lock/busy conditions surface as `DatabaseUnavailable` with `db_reason=locked`

DB path:
- Core API/Cardex state uses `MUNINN_DB_PATH` (default `~/.local/share/muninn/muninn.db`).
- Human-memory MCP tools initialize and use `MUNINN_HUMAN_MEMORY_DB_PATH` when set.
- Default path is `~/.local/share/muninn/human_memory.db`.
- Debug MCP reads/writes (`muninn.spaces.resolve`, `muninn.cards.*`, `muninn.rehydrate.bundle`, `muninn.policy.*`) against `human_memory.db`, not `muninn.db`.
- The human-memory procedure routes (`/v0/memory/procedures/retrieve` and `/v0/memory/procedures/reflect`) also use `human_memory.db`.

HTTP auth:
- Namespace key map mode (recommended): `MUNINN_API_KEYS="keyA:nsA,keyB:nsB"` (or JSON object string)
- Legacy single key mode: `MUNINN_API_KEY` (+ optional `MUNINN_API_KEY_HEADER`)
- Bearer mode: `MUNINN_MCP_BEARER_TOKEN` (`Authorization: Bearer <token>`)
- Invalid non-empty `MUNINN_API_KEYS` fails closed for protected routes (requests are unauthorized).
- Slash alias controls:
  - `MUNINN_MCP_ENABLE_SLASH_ALIASES=1|0` (default `1`)
  - `MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS=1|0` (default `1`; only applies when slash aliases are enabled)
- Structured MCP telemetry (JSONL):
  - `MUNINN_MCP_TELEMETRY_PATH=~/.local/share/muninn/mcp_telemetry.jsonl`
  - `MUNINN_MCP_TELEMETRY_FLUSH=1` (optional immediate flush)
  - `MUNINN_MCP_TELEMETRY_MAX_BYTES` (optional rotation threshold in bytes)
  - `MUNINN_MCP_TELEMETRY_BACKUP_COUNT` (optional retained rotated files; default `5`)
  - when the active file crosses the threshold it rotates to `.1`, older backups shift upward, and `backup_count=0` truncates instead of keeping backups
  - telemetry captures operation name, caller, cwd/project context, canonicalized space key, summarized query/lens, result counts, warnings, DB target, and latency
  - query text is summarized/redacted rather than dumped verbatim at full length

CLI audit entrypoint:
- `muninn audit --last 2h` (or `--since "2026-02-19 15:00"`)
- Source priority:
  1) telemetry JSONL file (when present)
  2) `journalctl --user -u muninn-mcp.service` MCP_TOOL parsing fallback
- audit now reports missing-evidence warnings for successful MCP upserts

Inspection/debugging workflow:
1. `muninn.system.ping`
2. `muninn.spaces.resolve`
3. `muninn.rehydrate.bundle` for task-start rehydration
4. `muninn.policy.inspect` to see active directives, preferences, and recent policy signals
5. `muninn audit --last 2h` to evaluate discipline, retrieval misses, and evidence hygiene

Architecture sketch:

```text
User / Agent / Tool events
        |
        v
interaction_events ----> policy.learn interpreter
        |                        |
        |                        v
        |                  policy-state cards
        |                        |
        v                        v
evidence + durable cards --> rehydrate.bundle --> facts | evidence | lessons | preferences
```

Codex config example:
```toml
[mcp_servers.muninn]
url = "http://127.0.0.1:8765/mcp"
enabled = true
tool_timeout_sec = 60
```

Codex config file location:
- `~/.codex/config.toml`
- After edits, restart VS Code (or reload the Codex extension/session) so the MCP server config is reloaded.

## Cardex v1 (card-centric multimodal-ready)
Cardex introduces cards as the primary memory unit and keeps supporting artifacts/sources as references.

### Create card (write-gated by default)
`POST /cards` creates a proposal unless `trusted_mode=true`.

Request:
```json
{
  "namespace": "lexi",
  "type": "place",
  "title": "Belize restaurant mention",
  "summary": "Possible restaurant in Belize connected to Bowie references.",
  "tags_json": ["belize", "restaurant", "bowie"],
  "trusted_mode": false,
  "requested_by": "agent:lexi"
}
```

### Create source (+ optional document/chunks/artifacts)
`POST /sources` can ingest text now while keeping room for image/audio/video artifacts.

Request:
```json
{
  "namespace": "lexi",
  "source_type": "web",
  "uri": "https://example.com/bowie-belize",
  "title": "Bowie Belize Notes",
  "document_text": "Long text body ...",
  "artifacts": [
    {"artifact_type": "summary", "content_text": "Short source summary", "generator": "stub"}
  ]
}
```

### Deterministic ingestion (v1)
`POST /ingest` is the preferred path for source ingestion. It normalizes text, generates stable IDs, emits searchable artifacts, and deterministic chunks.

Request:
```json
{
  "namespace": "lexi",
  "source_type": "document",
  "uri": "https://example.com/bowie-belize",
  "title": "Bowie Belize notes",
  "text": "Raw pasted content ...",
  "user_tags": ["belize", "bowie"],
  "chunk_target_tokens": 450,
  "chunk_overlap_tokens": 80,
  "card_mode": "none"
}
```

Response includes:
- deterministic `source_id`, `doc_id`, `chunk_ids`, `artifact_ids`
- `artifact_type=extracted_text` for text inputs
- pending artifacts for media/url/file stubs
- heuristic tags and provenance metadata

### Link refs to cards
`POST /cards/{card_id}/refs`

Request:
```json
{
  "namespace": "lexi",
  "refs": [
    {"ref_type": "source", "ref_id": "src_123", "role": "evidence"},
    {"ref_type": "chunk", "ref_id": "chunk_456", "role": "evidence"}
  ]
}
```

### Add artifacts to an existing source
`POST /sources/{source_id}/artifacts`

Request:
```json
{
  "namespace": "lexi",
  "artifacts": [
    {"artifact_type": "caption", "content_text": "Street food stall in Belize", "generator": "stub"}
  ]
}
```

### Retrieve context pack
`POST /retrieve` returns card summaries + evidence snippets + `audit_id`.

Request:
```json
{
  "namespace": "lexi",
  "query": "restaurant in Belize that David Bowie mentioned",
  "purpose": "assistant_answer",
  "scope": ["cards", "evidence"],
  "modalities": ["text", "image", "audio", "video"],
  "sensitivity_ceiling": 1,
  "k_cards": 20,
  "k_evidence": 8
}
```

Response includes:
- `cards[]`
- `evidence[]`
- `audit_id`
- `redactions[]` (tier blocks + content redaction events)

Current retrieval behavior:
- Searches `cards` first (FTS/keyword).
- Uses `artifacts.content_text` as fallback signal.
- Expands evidence via `card_refs` into chunks/docs/sources.
- Applies sensitivity ceiling and basic redaction policy (`tiered_redaction_v1`).
- Vector multimodal search is stubbed (`vector_search=stub_pending`).
- Records access signals (`signals`, `coaccess_edges`) for returned cards/evidence.
- Evaluates deterministic implicit promotion triggers and emits write-gated proposals.

### Promote meaningful evidence
`POST /promote` promotes an `artifact` or `chunk` into meaningful memory.

Request:
```json
{
  "namespace": "lexi",
  "owner_type": "artifact",
  "owner_id": "art_123",
  "mode": "propose",
  "card_type": "fact",
  "card_title": "Belize Bowie lead",
  "card_summary": "Promoted evidence summary",
  "tags": ["belize", "bowie"],
  "requested_by": "agent:lexi"
}
```

Behavior:
- `mode=propose`: creates a write-gated proposal that confirms into card + refs + promoted evidence state.
- `mode=trusted`: auto-confirms only when allowed by tier policy; sensitive evidence falls back to proposal.
- Promotion enqueues `index_jobs` for promoted evidence and active cards.

### Propose / confirm / reject
`POST /propose`, `POST /confirm/{proposal_id}`, and `POST /reject/{proposal_id}` manage write-gated mutations for:
- `create_card`
- `update_card`
- `link_refs`
- `add_source`

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

Audit behavior:
- Every request path writes an audit row on success or failure.
- `audit_log` is append-only (update/delete blocked by DB triggers).

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
