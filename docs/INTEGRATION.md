# Integration — Muninn

Muninn is a memory harness you call over HTTP.

## Endpoints (v0)
- `POST /v0/memory/rehydrate`
- `POST /v0/memory/write_candidates`
- `GET /v0/memory/version`
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
  "profile": "lexi"
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

## ChatGPT (OpenAI-style tools) — suggested tool shapes
Use two tools:
- `muninn_rehydrate(query, namespace, entity_id, k, profile)`
- `muninn_write_candidates(namespace, candidates)`

Your agent should:
- call `muninn_rehydrate` at the start of a turn
- inject `<SYSTEM_MEMORY>` cards into the prompt
- after answering, propose `0..N` memory candidates and call `muninn_write_candidates`

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
