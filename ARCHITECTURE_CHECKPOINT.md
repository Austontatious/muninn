# Architecture Checkpoint

Last updated: 2026-03-22

This document is the stable runtime map for Muninn as it exists in the local repo now. It is descriptive, not aspirational. It should match the code that is actually on the critical path today.

## System purpose

Muninn is a local, model-agnostic memory substrate.

The current priority runtime is the human-memory system used directly by Codex-facing MCP tools. That runtime is designed to provide:

- durable project memory as cards
- auditable provenance via evidence
- deterministic lexical retrieval and rehydration
- scoped behavior adaptation through policy-state and interaction traces
- operator visibility through CLI inspection and structured telemetry

Muninn still also exposes the legacy `/v0/memory/*` plane. That plane remains live, but it is intentionally not unified with the human-memory runtime in this stabilization pass.

## Current runtime architecture

The live critical path for Codex-facing memory work is:

```text
MCP client
  -> src/muninn/mcp_server.py
     -> request ingress / correlation ids
     -> input coercion + validation
     -> canonical space resolution
     -> human-memory DB bootstrap/init
     -> card / policy / rehydration operations
     -> structured telemetry
     -> SQLite human_memory.db

CLI operator path
  -> src/muninn/cli.py
     -> human-memory DB bootstrap/init
     -> policy inspection / audit / heal
     -> structured telemetry
```

Core runtime responsibilities are split as follows:

- `mcp_server.py`
  - owns the live MCP human-memory tool surface
  - owns request validation, request ids, ingress logging, and tool-level orchestration
- `telemetry.py`
  - owns shared structured telemetry emission and JSONL rotation
- `api.py`
  - owns core API startup/migration lifecycle and emits structured startup events
- `human_memory/bootstrap.py`
  - owns schema/init/bootstrap for the human-memory DB
- `human_memory/spaces.py`
  - owns canonical project identity and alias handling
- `human_memory/cards.py`
  - owns durable card/evidence/FTS storage behavior
- `human_memory/rehydration.py`
  - owns deterministic staged retrieval for session resume
- `human_memory/policy.py`
  - owns policy-state query/write behavior and promotion rules
- `human_memory/interactions.py`
  - owns raw interaction event capture and promoted/unpromoted linkage
- `cli.py`
  - owns operator workflows for audit, heal, and policy inspection

Old vs new, in practical terms:

- Old center of gravity:
  - convention-based retrieval flow
  - drifting space identity
  - append-only MCP telemetry without rotation
  - no operator policy inspection path
- Current center of gravity:
  - canonical project identity with alias migration
  - deterministic rehydration bundle
  - policy-state learning through memory updates, not weight updates
  - structured telemetry across MCP, bootstrap, rehydration, policy learning, and CLI
  - policy inspection from CLI

## Canonical data model

The human-memory runtime is backed by `human_memory.db`.

### Core relational objects

- `users`
  - local namespace owner
- `clients`
  - caller identity such as `codex-vscode`
- `spaces`
  - canonical project/global scopes
- `space_aliases`
  - alias-to-canonical namespace mapping
- `cards`
  - durable memory units
- `cards_fts`
  - FTS5 lexical retrieval over card text
- `evidence`
  - provenance refs such as file, diff, commit, test, log, URL, or chat
- `card_evidence`
  - card-to-evidence join table
- `card_relations`
  - lineage edges such as `supersedes`, `duplicates`, `contradicts`, `refines`
- `tags`
- `card_tags`
- `interaction_events`
  - raw evaluative/directive traces used for later promotion into policy-state

### Logical memory classes carried in `cards`

- project/factual memory
  - `decision`
  - `constraint`
  - `interface`
  - `runbook`
- policy-state memory
  - `policy.directive`
  - `policy.preference`
  - `policy.anti_pattern`
  - `workflow.heuristic`
  - `tooling.preference`
  - `rehydration.priority`

### JSON metadata conventions

- `context_json.provenance`
  - provenance class, evidence counts, evidence types, warning codes
- `context_json.policy_state`
  - structured behavior guidance used at retrieval time

### Space resolution rules (canonical)

The current canonical rule is:

- git repo with remote:
  - `repo:<sha(remote_norm)>`
- git repo without remote:
  - `path:<sha(repo_root)>`
- non-git path:
  - `path:<sha(abs_cwd)>`

Compatibility aliases remain valid through `space_aliases`, including legacy `cwd:*` forms.

## Ingestion path

The stabilized ingestion path for human-memory writes is:

1. MCP or CLI receives an operation.
2. Request shape is validated and normalized.
3. Space identity is resolved into a canonical `space_key`.
4. Human-memory DB init/bootstrap is run if needed.
5. Evidence refs are normalized.
6. Card/policy context is enriched with provenance metadata.
7. Storage is committed into:
   - `cards`
   - `evidence`
   - `card_evidence`
   - `card_relations` when lineage operations apply
   - `interaction_events` for policy-signal capture
8. Structured telemetry records the operation, target space, counts, warnings, and failure class when needed.

Lineage-preserving write operations remain first-class:

- `muninn.cards.upsert`
- `muninn.cards.supersede`
- `muninn.cards.merge`

This pass does not redesign ingestion. It hardens observability around the existing flow.

## Retrieval / rehydration path

Basic lexical retrieval remains card-centric:

- `muninn.cards.recent`
- `muninn.cards.search`

Scope semantics are:

- `strict`
  - canonical project space only
- `soft`
  - canonical project space
  - alias spaces
  - `global`

Deterministic session rehydration is owned by `muninn.rehydrate.bundle` and `src/muninn/human_memory/rehydration.py`.

Current stage order:

1. `strict_search`
2. `recent_strict`
3. `soft_search`
4. `alias_search`
5. `recent_evidence`
6. `global_search` when soft scope is enabled

Current scoring inputs are:

- stage priority
- kind bonus
- lexical overlap
- recency
- evidence presence/count
- canonical-space match bonus

Rehydration output is split into:

- `facts`
- `constraints`
- `evidence`
- `lessons`
- `preferences`

This pass keeps retrieval lexical and staged. It does not add broad semantic retrieval.

## Policy/adaptation pipeline

Policy/adaptation behavior is memory-native, not weight-native.

The policy learning path is:

1. a correction/failure/directive is captured
2. `interaction_events` records the raw trace first
3. policy logic derives a stable `signal_key`
4. repetition/confidence/pattern rules decide whether promotion should happen
5. durable policy-state is written back as typed cards when promotion criteria are met
6. future rehydration can retrieve these policy cards alongside project memory

Current policy-state kinds are:

- `policy.directive`
- `policy.preference`
- `policy.anti_pattern`
- `workflow.heuristic`
- `tooling.preference`
- `rehydration.priority`

Important boundary:

- factual/project memory stays in ordinary cards
- evidence stays separate
- raw feedback traces stay in `interaction_events`
- learned behavior guidance lives in policy cards

The adaptation retrieval/query path is:

1. MCP tool `muninn.cards.adaptation.query` routes through `src/muninn/mcp_server.py`.
2. `src/muninn/human_memory/adaptation.py` resolves filters and views.
3. Adaptation cards are read from canonical scoped card storage with strict/soft lens handling.
4. Results are normalized for prompt-state use (`build_prompt_state_summary`) and emitted with structured telemetry.

Both paths are live in current runtime:

- policy learning/writes: `interactions.py` + `policy.py`
- adaptation reads/projection: `adaptation.py`

## Compatibility and migration rules

The compatibility posture is additive.

### Schema/init

Human-memory init is still anchored on a single base schema file plus additive self-healing compatibility logic.

- root schema file:
  - `migrations/0001_init.sql`
- additive/init compatibility:
  - `src/muninn/human_memory/bootstrap.py`

Current init behavior:

- applies base schema idempotently
- sets `PRAGMA user_version = 1` for the human-memory DB
- backfills additive compatibility structures when missing
- bootstraps default local user/client/global space
- emits bootstrap/migration telemetry with correlation ids when available

### Namespace compatibility

Legacy and alternate space keys are reconciled through `space_aliases`.

During space creation/resolution, old alias space rows can be migrated into the canonical space for:

- `cards`
- `evidence`
- `interaction_events`

### MCP contract compatibility

The MCP human-memory layer continues to accept older payload variants for retrieval, while canonical behavior is object-shaped and field-validated.

### Explicit boundary on `/v0`

The legacy `/v0/memory/*` plane remains live and intentionally separate.

This pass does not merge it into the human-memory runtime unless correctness would require it. No such merge was introduced here.

## Known limitations

1. The repo still has two memory planes.
   - `/v0/memory/*` is still separate from the human-memory runtime.
2. Retrieval is still lexical.
   - “soft” means wider staged lexical recall, not embeddings-based semantic search.
3. Policy-state still lives inside `cards.context_json`.
   - there is not a dedicated relational policy table yet.
4. Policy promotion remains heuristic-first.
   - explicit behavior-hint extraction is intentionally narrow.
5. Global fallback can still introduce noise if overused.
6. CLI policy inspection is inspection-only in this pass.
   - no broad mutation/admin console was added.
7. Some legacy/auxiliary modules remain in the repo.
   - they are not treated as architecture-defining for this checkpoint unless they move back onto the live critical path.

## Files that define the architecture

The current architecture-defining file set is:

- `src/muninn/mcp_server.py`
  - live MCP human-memory contract, request orchestration, ingress/failure logging
- `src/muninn/human_memory/spaces.py`
  - canonical `space_key` rules, alias lookup, alias migration
- `src/muninn/human_memory/cards.py`
  - durable cards, evidence joins, lineage, FTS retrieval
- `src/muninn/human_memory/rehydration.py`
  - deterministic staged rehydration behavior
- `src/muninn/human_memory/policy.py`
  - policy-state retrieval, promotion logic, confidence/repetition handling
- `src/muninn/human_memory/interactions.py`
  - interaction event capture and promoted/unpromoted linkage
- `src/muninn/human_memory/adaptation.py`
  - adaptation-card filtering, view projections, and prompt-state summary shaping
- `migrations/0001_init.sql`
  - base human-memory schema
- `src/muninn/human_memory/bootstrap.py`
  - human-memory init/bootstrap/migration compatibility path
- `src/muninn/cli.py`
  - operator workflows for audit, heal, and policy inspection
- `src/muninn/telemetry.py`
  - shared structured telemetry sink and rotation behavior for MCP, bootstrap, CLI, and API startup events
- `src/muninn/api.py`
  - startup + migration telemetry for the core `/v0` API runtime

### Code-verified anchors (current runtime)

The following symbols are the concrete anchors verified in code for this checkpoint:

- `src/muninn/human_memory/bootstrap.py`
  - `open_db`, `apply_init_schema`, `bootstrap_defaults`
- `src/muninn/human_memory/spaces.py`
  - `resolve_space_from_cwd`, `canonicalize_space_key`, `resolve_space_lookup_keys`, `get_or_create_space`
- `src/muninn/human_memory/cards.py`
  - `cards_recent`, `cards_search`, `card_upsert`, `card_supersede`, `cards_merge`
- `src/muninn/human_memory/rehydration.py`
  - `rehydrate_bundle`
- `src/muninn/human_memory/policy.py`
  - `learn_policy_signal`, `query_policy_cards`
- `src/muninn/human_memory/interactions.py`
  - `record_interaction_event`, `list_interaction_events`, `link_promoted_card`
- `src/muninn/human_memory/adaptation.py`
  - `query_adaptation_cards`, `build_prompt_state_summary`
- `src/muninn/mcp_server.py`
  - registered tools: `muninn.spaces.resolve`, `muninn.cards.recent`, `muninn.cards.search`, `muninn.rehydrate.bundle`, `muninn.policy.learn`, `muninn.policy.inspect`, `muninn.cards.adaptation.query`, `muninn.cards.upsert`, `muninn.cards.supersede`, `muninn.cards.merge`
- `migrations/0001_init.sql`
  - canonical tables: `users`, `clients`, `spaces`, `space_aliases`, `cards`, `cards_fts`, `evidence`, `card_evidence`, `card_relations`, `tags`, `card_tags`, `interaction_events`

Notes on path accuracy:

- the repo does not currently have a live `src/muninn/migrations/0001_init.sql`; the active base schema file is `migrations/0001_init.sql`
- the repo does not currently have a live `src/muninn/bootstrap.py`; the active human-memory bootstrap file is `src/muninn/human_memory/bootstrap.py`

Files intentionally not treated as architecture-defining in this checkpoint include:

- tests
- fixtures
- one-off migration helpers or backfill scripts
- notebooks and experiments
- docs other than this checkpoint document
- deprecated slash-alias wrappers by themselves
- legacy `/v0` forwarding routes as architecture-defining for the human-memory runtime

## When to update this document

- Any change to:
  - rehydration logic
  - memory schema
  - policy/adaptation behavior
  - MCP interface
  - canonical space resolution
