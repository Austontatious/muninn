# LAILA Adaptation Memory Contract (Muninn)

## Purpose
Muninn stores adaptation-relevant memory signals for LAILA.

Muninn does:
- persist typed adaptation signals
- expose deterministic retrieval/filtering primitives
- preserve provenance and evidence links

Muninn does **not**:
- decide behavior policy
- choose prompt strategy
- apply adaptation weighting logic

LAILA owns adaptation policy and prompt assembly decisions.

## Card Typing Convention
Adaptation cards use `kind`:

- `adaptation.preference.direct`
- `adaptation.preference.inferred`
- `adaptation.override.scoped`
- `adaptation.correction`
- `adaptation.outcome`

These map to tags:

- `preference.direct`
- `preference.inferred`
- `override.scoped`
- `correction`
- `outcome`

## Required Adaptation Metadata
Stored in `cards.context_json.adaptation`:

```json
{
  "schema_version": 1,
  "memory_type": "preference.direct",
  "subject_id": "client_acme",
  "category": "voice",
  "scope": {"type": "campaign", "id": "spring_2026"},
  "persistence": "durable",
  "source_type": "direct_feedback",
  "confidence": 0.91,
  "session_id": "sess-42",
  "workflow_tags": ["business_goal", "social"],
  "provenance": {"source_ref": "feedback_ticket_123"}
}
```

Also supported at card level:
- `source_confidence` mirrors adaptation confidence when available
- `created_by_client_name` identifies writer client
- `evidence_refs` links provenance artifacts

## Persistence Model
- `persistence=durable` + tag `durable_candidate`
- `persistence=one_off` + tag `one_off`
- `persistence=session_only` + tag `session_only`

Durable vs one-off/session separation is explicit and queryable.

## Tagging Conventions
Adaptation cards are multi-tag by design. Common tags:

- base: `adaptation`, one memory-type tag
- optional category tags: `voice`, `tone`, `topic`, `business_goal`, `cta_tolerance`, `humor`, `polish`, `cadence`, `budget_preference`
- optional scope/channel tags: `campaign`, `social`, `video`
- persistence tags: `durable_candidate`, `one_off`, `session_only`

## Retrieval Guarantees
`query_adaptation_cards` and MCP `muninn.cards.adaptation.query` support deterministic filtering by:

- `subject_id`
- `memory_type`
- `category`
- `scope.type` and `scope.id`
- `persistence`
- `source_type`
- `session_id`
- `tags`
- recency (`max_age_days`, based on signal capture `created_at`)

Response always includes:
- filtered cards
- counts by memory type and persistence
- `prompt_state` summary grouped by category

## Backward Compatibility
- Existing non-adaptation cards remain unchanged.
- Existing `muninn.cards.recent`/`muninn.cards.search` contracts remain valid.
- Adaptation support is additive.
