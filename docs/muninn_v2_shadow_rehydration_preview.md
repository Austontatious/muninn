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

The command writes JSON and Markdown. Markdown includes:

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

Unless disabled, the command selects recent active cards from the same filtered v2 record set. These cards are continuity supplements, not query hits. They are sorted deterministically by `updated_at` descending and card id ascending, exclude primary duplicates, and are limited by `recent_limit` and the overall `limit`.

### Stage C: Evidence Attachment

When `--include-evidence` is passed, evidence refs attached to each card are included. The command never fabricates evidence. Without the flag, reports still include evidence counts.

### Stage D: Budgeting

The command enforces the overall `limit`. When `--max-chars` is provided, it applies a deterministic approximate character budget to card title, summary, body excerpt, and evidence refs. Primary cards are considered before supplements; omitted counts and reasons are reported.

### Stage E: Suggested Agent Briefing

The briefing is generated deterministically from retrieved card titles and summaries. It does not use an LLM, infer hidden conclusions, or invent project state. If retrieved content is sparse, the briefing marks uncertainty.

## Boundary

This command is Muninn v2 shadow/evaluation infrastructure. It is not Mimir cognition and does not implement motif detection, spreading activation, hidden salience propagation, autonomous reasoning, or topology analysis. Mimir may later consume preview artifacts, but Muninn v2 remains the durable-memory substrate and this command remains opt-in.
