# Muninn v2 Shadow Rehydration Preview

## Purpose

`shadow-rehydrate-preview` is an opt-in Muninn v2 diagnostic command that turns an explicit v2 shadow database into an agent-context preview. It is for migration validation and shadow evaluation only.

It does not change v1 retrieval, v1 schema, MCP behavior, Codex defaults, or any production project state.

## Inputs

Required inputs:

- `--v2-db PATH`: explicit Muninn v2 SQLite database path.
- `--query TEXT`: task summary or resume query.
- `--out-dir PATH`: output directory for JSON and Markdown reports.

Optional inputs:

- `--limit N`: total preview card limit. Default: `12`.
- `--primary-limit N`: maximum primary retrieval cards. Default: `3`.
- `--recent-limit N`: maximum recent supplement cards. Default: `9`.
- `--retrieval-mode hybrid|lexical|vector`: diagnostic retrieval mode. Default: `hybrid`.
- `--space-key KEY`: optional v2 card scope filter. In strict mode, multi-space DBs require this.
- `--project-path PATH`: optional metadata filter using v2 card project path metadata when present.
- `--include-evidence`: include evidence refs and excerpts.
- `--include-explanations`: include retrieval score explanations.
- `--max-chars N`: approximate context budget; primary cards are preferred over supplements.
- `--json-report PATH` and `--md-report PATH`: optional report paths.
- `--no-recent-supplement`: disable continuity supplements.
- `--strict`: fail on ambiguous or empty filtered inputs.

## Output Sections

The command writes JSON and Markdown.

The JSON output is the stable `RehydrateResponseV1` envelope documented in `docs/muninn_v2_rehydrate_response_v1.md` and validated by `docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json`. Future v2 APIs and agent-context experiments must consume that envelope rather than command-specific ad hoc fields.

Markdown includes:

- Executive summary
- Query/task
- Source DB
- Retrieval mode
- Composition strategy
- Primary retrieval matches
- Recent in-scope supplements
- Evidence/provenance
- Explanation notes
- Context gaps / uncertainty
- Suggested agent briefing

## Composition Stages

### Stage A: Primary Retrieval

The command runs the selected v2 diagnostic retrieval mode against active v2 cards:

- `hybrid`: explainable hybrid lexical/evidence/vector-rescue retrieval.
- `lexical`: provisional lexical fallback.
- `vector`: optional derived vector index, with fallback behavior if unavailable.

The top `primary_limit` non-duplicate cards are primary matches. Explanations are included only when requested.

### Stage B: Recent In-Scope Supplement

Unless disabled, the command selects recent active cards from the same filtered v2 record set. These cards are continuity supplements, not primary query hits. They are sorted deterministically by `updated_at` descending, relevance score, and card id ascending, exclude primary duplicates, and are limited by `recent_limit` and the overall `limit`.

Supplements must carry an explicit reason code in `selected_memory.cards[].selection.reason`:

- `recent_campaign_or_numeric_token_overlap`: the card matched meaningful numeric, campaign, version, or phase-like query tokens.
- `recent_query_token_overlap`: the card matched at least two non-generic query tokens.
- `recent_query_primary_domain_overlap`: the card matched both the query and terms from primary results.
- `recent_primary_domain_overlap`: the card matched enough primary-result domain terms to support continuity.
- `recent_project_boundary_or_contract`: the card preserves a project boundary, contract, canonical entrypoint, or runtime-memory separation that matched the project/query or primary domain.
- `recent_same_scope_continuity_fallback`: non-strict mode only; a small cap for recent same-scope cards when stronger supplements are sparse.

Strict previews do not fill remaining budget with weak recency alone. Background-only or contrast-only cards, such as process notes that merely mention the topic while documenting deferred or non-current work, are penalized and omitted from strict supplements unless they have a stronger numeric/campaign match.

### Stage C: Evidence Attachment

When `--include-evidence` is passed, evidence refs attached to each card are included. The command never fabricates evidence. Without the flag, reports still include evidence counts.

### Stage D: Budgeting

The command enforces the overall `limit`. When `--max-chars` is provided, it applies a deterministic approximate character budget to card title, summary, body excerpt, and evidence refs. Primary cards are considered before supplements; omitted counts and reasons are reported.

### Stage E: Suggested Agent Briefing

The briefing is generated deterministically from retrieved card titles and summaries. It does not use an LLM, infer hidden conclusions, or invent project state. If retrieved content is sparse, the briefing marks uncertainty.

## RehydrateResponseV1 Envelope

The emitted JSON includes:

- `schema` and `contract_version`
- `request` query/source/options metadata
- `selected_memory.cards`, `selected_memory.events`, and `selected_memory.evidence`
- `explanations` with stable card selection reasons and optional score details
- `uncertainty.context_gaps` and warnings
- `budget` limits, selected counts, duplicate removal, and omitted counts
- `retrieval_provenance` for backend, mode, provider status, query profile, and retrieval paths
- `fallbacks` for degraded vector/index or lexical fallback behavior
- `agent_briefing` generated without an LLM

## Boundary

This command is Muninn v2 shadow/evaluation infrastructure. It is not Mimir cognition and does not implement motif detection, spreading activation, hidden salience propagation, autonomous reasoning, or topology analysis. Mimir may later consume preview artifacts, but Muninn v2 remains the durable-memory substrate and this command remains opt-in.
