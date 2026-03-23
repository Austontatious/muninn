# Query Contracts (Stable)

## 1) Lens Contract

Canonical lens shape for `muninn.cards.recent`, `muninn.cards.search`, `muninn.rehydrate.bundle`, `muninn.policy.learn`, `muninn.policy.inspect`, and `muninn.cards.adaptation.query`:

```json
{
  "lens": {
    "space": "auto",
    "space_key": null,
    "cwd": "/abs/path",
    "scope": "strict",
    "kinds": ["decision", "constraint"],
    "status": "active",
    "tags": ["schema"],
    "limit": 20
  }
}
```

Rules:
- `space=auto` requires `cwd` unless `space_key` is provided.
- `space_key` is canonicalized through alias lookup before read/write.
- `scope=strict` means canonical project space only.
- `scope=soft` means canonical project space, then alias spaces, then `global`.
- `kinds` and `tags` are normalized: trim, lowercase, dedupe.

Backward-compatible shapes still accepted:
- nested object: `{"lens": {...}}`
- single `kind` field instead of `kinds`
- string `limit`
- comma-separated or whitespace-separated `kinds` / `tags`
- legacy key-value string:

```json
"space_key:repo:abc123 scope:soft kind:runbook limit:3"
```

## 2) Search Query Contract

Canonical search input for `muninn.cards.search` and `muninn.rehydrate.bundle`:

```json
{
  "query": {
    "text": "checkpoint c audit flush batching"
  }
}
```

Backward-compatible query shapes:
- plain string: `"checkpoint c audit flush batching"`
- alias fields: `q`, `query`
- term list: `{"terms": ["checkpoint", "audit", "batching"]}`
- bare string list: `["checkpoint", "audit", "batching"]`

Behavior:
- query text is normalized to safe FTS tokens
- punctuation-heavy inputs no longer reach SQLite unchanged
- malformed query payloads return `InvalidArguments` with field-level details when available

## 3) Canonical Space Identity

Space identity is normalized before both reads and writes.

Canonical strategy:
- git repo with `remote.origin.url`: `repo:<sha(remote_norm)>`
- git repo without remote: `path:<sha(repo_root)>`
- non-git path: `path:<sha(abs_cwd)>`

Compatibility aliases:
- repo-root path aliases are retained in `space_aliases`
- legacy `cwd:*` keys resolve to canonical `path:*`
- `resolve_space_lookup_keys(...)` returns `[canonical, aliases...]`

During transition:
- soft retrieval searches canonical space first, alias spaces second, `global` last
- writes reconcile alias-key rows into canonical space when possible

## 4) Rehydration Contract (`muninn.rehydrate.bundle`)

Purpose:
- make session-start/task-resume retrieval deterministic
- return project memory and policy-state in separate tracks

Request:

```json
{
  "lens": {
    "space": "auto",
    "cwd": "/abs/path",
    "scope": "soft",
    "kinds": ["decision", "constraint", "runbook", "interface"],
    "limit": 12
  },
  "query": "docker logs exact commands",
  "tool_name": "shell",
  "task_type": "troubleshooting",
  "include_body": false,
  "include_policy": true
}
```

Retrieval stages:
1. `strict_search`
2. `recent_strict`
3. `soft_search`
4. `alias_search`
5. `recent_evidence`
6. `global_search` when `scope=soft`

Response shape:

```json
{
  "space": {
    "canonical_key": "repo:...",
    "lookup_keys": ["repo:...", "path:...", "global"],
    "scope": "soft"
  },
  "query": "docker logs exact commands",
  "stages": [
    {"stage": "strict_search", "space_key": "repo:...", "results": 0}
  ],
  "project_cards": [],
  "policy_cards": [],
  "bundle": {
    "facts": [],
    "constraints": [],
    "evidence": [],
    "lessons": [],
    "preferences": []
  }
}
```

Scoring factors:
- canonical-space match
- recency
- evidence presence
- card kind bonus
- lexical overlap
- stage priority

## 5) Policy-State Contracts

### `muninn.policy.learn`

Purpose:
- capture evaluative and directive feedback as scoped policy-state
- update future behavior through memory/state, not weights

Request:

```json
{
  "lens": {
    "space": "auto",
    "cwd": "/abs/path",
    "scope": "strict"
  },
  "signal": {
    "summary": "No, check the repo first before answering implementation questions.",
    "signal_type": "mixed",
    "outcome": "corrected",
    "scope_type": "project",
    "scope_key": null,
    "tool_name": null,
    "task_type": "implementation"
  },
  "evidence": [
    {"type": "chat", "ref": "turn:123"}
  ]
}
```

Allowed `signal_type`:
- `evaluative`
- `directive`
- `mixed`

Allowed `outcome`:
- `success`
- `partial`
- `failure`
- `corrected`

Behavior:
- every call records an interaction event
- weak one-off evaluative signals stay as interaction-only records
- repeated or directive-rich signals promote into policy cards
- promoted policy cards are evidence-linked back to their source interaction

### `muninn.policy.inspect`

Purpose:
- inspect active project/global policy-state and recent policy interactions

Request:

```json
{
  "lens": {
    "space": "auto",
    "cwd": "/abs/path",
    "scope": "soft"
  },
  "query": {
    "query": "exact commands",
    "scope_types": ["project"],
    "tool_name": "shell",
    "task_type": "troubleshooting",
    "limit": 10,
    "include_events": true,
    "event_limit": 10
  }
}
```

## 6) Adaptation Query Contract (`muninn.cards.adaptation.query`)

Request shape:

```json
{
  "lens": {
    "space": "auto",
    "cwd": "/abs/path",
    "scope": "soft",
    "limit": 20
  },
  "query": {
    "subject_id": "client_acme",
    "view": "prompt_state",
    "categories": ["voice", "cta_tolerance"],
    "memory_types": ["preference.direct", "correction"],
    "persistence": ["durable", "session_only"],
    "scope_types": ["campaign", "session", "social"],
    "scope_id": "spring_2026",
    "source_types": ["direct_feedback", "operator_edit", "analytics"],
    "session_id": "sess-42",
    "tags": ["social", "campaign"],
    "max_age_days": 30,
    "status": "active",
    "limit": 20,
    "include_body": false
  }
}
```

Supported `view`:
- `all`
- `durable_preferences`
- `recent_overrides`
- `corrections`
- `outcomes`
- `prompt_state`

## 7) Evidence and Provenance Metadata

Write tools enrich card context with a normalized provenance summary:

```json
{
  "provenance": {
    "source_class": "tool_derived",
    "evidence_count": 2,
    "evidence_types": ["file", "test"],
    "warning_codes": []
  }
}
```

Current `source_class` values:
- `user_provided`
- `tool_derived`
- `model_inference`
- `preference_or_instruction`

Write warnings:
- `decision`, `constraint`, `interface`, `runbook`, and policy-state cards warn when evidence is missing
- warnings are returned in tool responses and logged into MCP telemetry

## 8) Failure Behavior

- malformed lens/query/policy payloads return `InvalidArguments`
- error payloads include a best-effort `field` when one can be identified
- SQLite lock/busy errors map to `DatabaseUnavailable` with `db_reason=locked`
- schema mismatch maps to `DatabaseUnavailable` with `db_reason=schema_mismatch`

Telemetry is privacy-conscious by default:
- query fields are summarized/redacted, not logged verbatim at full length
- card bodies are never dumped to telemetry by default
