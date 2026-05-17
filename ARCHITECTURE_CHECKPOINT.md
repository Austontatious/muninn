# Architecture Checkpoint

Last updated: 2026-05-17

This document records the current architectural truth for Muninn. It is not a running diary and should not absorb every experiment, task note, or future design sketch.

## Current Posture

Muninn has two relevant development lines:

- Muninn v1: active production memory for Codex-facing workflows.
- Muninn v2: adjacent opt-in substrate work on the checkpoint branch.

Muninn v1 remains the live branch of use unless a task explicitly says otherwise. New durable substrate design should bias toward v2, but that does not imply cutover, migration, or changed defaults.

## Production v1 Boundary

Muninn v1 owns the current live memory behavior:

- MCP/Codex-facing memory tools
- durable human-memory cards
- evidence/provenance refs
- canonical spaces and aliases
- deterministic rehydration
- policy/adaptation state
- interaction events
- current production SQLite schemas and DB paths

The critical v1 runtime remains centered on:

- `src/muninn/mcp_server.py`
- `src/muninn/cli.py`
- `src/muninn/api.py`
- `src/muninn/core`
- `src/muninn/human_memory/bootstrap.py`
- `src/muninn/human_memory/spaces.py`
- `src/muninn/human_memory/cards.py`
- `src/muninn/human_memory/rehydration.py`
- `src/muninn/human_memory/policy.py`
- `src/muninn/human_memory/interactions.py`
- `migrations/0001_init.sql`

The current v1 SDK/runtime wrapper posture is:

- `src/muninn/core` provides SDK-facing envelopes, app packs, procedure models, and storage adapters around the existing human-memory plane.
- `src/muninn/core/v0_runtime.py` is a compatibility wrapper for existing `/v0/*` API behavior.
- `src/muninn/runtime` contains thin import wrappers for HTTP, MCP, and CLI entrypoints.
- This SDK layer does not change default DB paths, MCP defaults, or production cutover posture.

Any v1 change needs explicit scope and extra scrutiny when it touches:

- MCP/Codex tool behavior
- default production DB paths
- schema or migration behavior
- retrieval/rehydration semantics
- policy/adaptation behavior
- card/evidence contracts
- space resolution

## Adjacent v2 Boundary

Muninn v2 exists under:

- `src/muninn/v2`

The v2 checkpoint currently provides:

- typed memory primitives
- small protocol contracts
- explicit-path SQLite storage with v2-prefixed tables
- JSON/JSONL export and bundle import helpers
- read-only v1 projection/import adapters
- dry-run pilot import tooling
- migration ledger/checksum/fidelity reporting
- opt-in recall parity measurement
- optional derived-index diagnostics and retrieval-eval helpers
- opt-in shadow rehydration preview reports
- `RehydrateResponseV1` as the stable v2 shadow rehydration response envelope
- offline agent-context consumer audits for `RehydrateResponseV1` artifacts
- offline recall/reinforcement event replay into derived reinforcement state
- read-only bridge request/audit contracts for controlled v2 context consumption

v2 is not the production recall path. It must remain opt-in until a future task explicitly approves a cutover plan.

## Non-Negotiable Safety Rules

- Do not run automatic migration on import/startup.
- Do not modify v1 schemas from v2 tooling.
- Do not change MCP/Codex defaults as part of v2 work.
- Do not write to production v1 DBs from pilot, parity, or adapter code.
- Do not make v2 the default recall path without explicit user instruction.
- Keep Mimir salience/cognition outside Muninn core.
- Keep Hrafnar interpreter/runtime/protocol behavior outside Muninn core.
- Treat scratch DBs and pilot output as non-production artifacts.

## Current Data Model Truth

The production v1 human-memory model is card-centric:

- `spaces`
- `space_aliases`
- `cards`
- `cards_fts`
- `evidence`
- `card_evidence`
- `card_relations`
- `tags`
- `card_tags`
- `interaction_events`

v1 cards carry durable project memory, policy-state memory, procedural memory, and atlas-like records through typed card kinds and structured JSON context.

The v2 model is substrate-oriented:

- memory events
- cards
- entities
- associations
- evidence refs
- recall events
- ontology profiles
- derived export/import bundles

Vector indexes, salience propagation, cognition loops, and interpreter/runtime behavior are not canonical truth in v2 core. They can be optional derived layers or future Mimir/Hrafnar work.

The optional v2 derived-index layer is diagnostic infrastructure only. It can create explicit `v2_vector_indexes` and `v2_index_state` tables in a caller-provided v2 SQLite DB during `muninn.v2.cli index-rebuild --write-index`; dry-run and health checks do not create those tables. The index is rebuildable from canonical v2 cards and may degrade to a labeled lexical/hash fallback when sqlite_vec is unavailable.

## Current Retrieval Truth

Production v1 retrieval remains the live behavior:

- card-centric lexical search
- deterministic staged rehydration
- strict/soft scope handling
- evidence-aware ranking inputs
- policy/adaptation cards retrieved through v1 paths

The v2 recall-parity command is measurement only. It can compare v1 FTS with a provisional v2 lexical matcher or the v2 hybrid matcher, but neither path is a live recall engine and neither should be tuned to fake parity.

The v2 retrieval-eval command is also measurement only. It scores fixed query fixtures, distinguishes record absence from retrieval mismatch, and writes JSON/Markdown reports without changing production routing. Its default diagnostic mode is now explainable hybrid retrieval: deterministic title/body/evidence/metric scoring with optional derived-vector rescue, explicit score components, and stable ranking. This remains shadow/evaluation infrastructure only.

The v2 shadow rehydration preview command is an explicit-DB report generator only. It composes primary diagnostic retrieval matches with clearly labeled recent in-scope supplements, can include evidence and explanations, and writes JSON/Markdown artifacts without changing v1 retrieval, MCP/Codex defaults, or any live context source.

Its JSON artifact is now the versioned `RehydrateResponseV1` envelope (`muninn.v2.rehydrate_response.v1`, contract version `1.0.0`). Future v2 APIs and opt-in agent-context experiments must consume that envelope instead of command-specific preview fields. The envelope carries request metadata, selected memory cards/events/evidence, explanations, uncertainty/context gaps, budget usage, retrieval provenance, and fallback/degradation markers.

The v2 agent-context audit command is the Phase B offline consumer harness. It validates real `RehydrateResponseV1` artifacts, renders deterministic context blocks, compares them against fixture-defined project-state needs and optional v1-style baseline text, and emits audit reports. It is read-only evaluation infrastructure, not live MCP/Codex integration.

The v2 recall/reinforcement layer is offline-only adaptive retrieval metadata. It records explicit recall events and replays them into `v2_reinforcement_state` in caller-provided v2 DBs without mutating canonical card text, bodies, evidence, or v1 data. Replay is deterministic and explainable: accepted records are boosted, scoped suppressions are penalized, durable boundary/contract records receive preservation against quiet-period decay, repeated signals use deterministic diminishing returns, recalled-only exposure is capped below accepted reinforcement, and effective scores remain bounded. The optional hybrid retrieval hook can consume this state only when explicitly supplied; adaptive scoring is not a default retrieval or live context path.

The v2 read-only bridge is a Phase E shadow integration harness. It accepts `BridgeRequestV1` (`muninn.v2.bridge_request.v1`, contract version `1.0.0`) for the single capability `read_only_context`, reads only an explicit v2 DB, emits `RehydrateResponseV1` plus Markdown context and a bridge audit log, and rejects requests that permit writes, v1 access, reinforcement event recording, adaptive retrieval defaults, or LLM-dependent context generation. It is not a network service, MCP route, Codex default, or cutover mechanism.

## Migration And Cutover Posture

There is no live migration and no automatic cutover.

Current safe migration work is limited to:

- explicit v1 DB path
- explicit v2 DB path
- explicit space/project selector
- read-only v1 access
- scratch or caller-provided v2 outputs
- row-count verification
- ledger/checksum/fidelity reports
- side-by-side parity reports

No production v1 data should be destructively migrated. Future migration must be reversible, auditable, and proven on narrow pilots before wider use.

## Current Next Milestone

The next architecture milestone is Phase E pre-cutover validation:

1. keep the bridge local/offline and read-only
2. validate bridge request/response contracts and audit logs
3. prove bridge context is safe before any live agent-context integration
4. write an explicit cutover and rollback plan before changing production defaults

## Documentation Boundaries

Use these surfaces for different kinds of knowledge:

- `AGENTS.md`: repository operating policy for agents.
- `ARCHITECTURE_CHECKPOINT.md`: concise current architecture truth.
- `RUNBOOK.md`: operational procedures.
- `docs/decisions/`: ADRs for durable architectural decisions.
- `docs/tasks/`: temporary task sheets and investigations.
- `reports/`: generated assessments, inventories, pilots, and parity outputs.

Root-level `PLANS.md` is deprecated for this repo. Superseded plans should live in ADRs, task docs, reports, or this checkpoint depending on their durability.

## Update Rules

Update this file when a task changes:

- live v1 runtime behavior
- v1 schema or migration behavior
- v1 MCP/Codex contract behavior
- v1 retrieval/rehydration semantics
- v2 substrate contracts or storage model
- v1/v2 compatibility, migration, or cutover posture

Do not update this file for routine report generation, scratch pilot output, transient implementation notes, or unrelated worktree drift.
