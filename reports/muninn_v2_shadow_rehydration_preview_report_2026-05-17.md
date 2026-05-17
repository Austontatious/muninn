# Muninn v2 Shadow Rehydration Preview Report - 2026-05-17

## Executive Summary

- Implemented a v2-only `shadow-rehydrate-preview` command.
- The command requires explicit `--v2-db`, `--query`, and `--out-dir`.
- It writes JSON and Markdown reports and does not read or write v1 databases.
- Friday and ReadyPlayer1 both produced usable 12-card previews with 3 primary retrieval matches and 9 recent in-scope supplements.
- Decision: GO for v2 shadow rehydration preview/evaluation; NO-GO for live agent context.

## Implementation Summary

Added `src/muninn/v2/retrieval/shadow_rehydrate.py` and wired it into `src/muninn/v2/cli.py` as `shadow-rehydrate-preview`.

The implementation:

- loads active cards from the explicit v2 DB only
- supports `hybrid`, `lexical`, and `vector` diagnostic retrieval modes
- composes primary query matches plus recent continuity supplements
- deduplicates by card id
- supports evidence and explanation inclusion flags
- enforces total limits and optional approximate `--max-chars` budgeting
- emits deterministic JSON/Markdown reports
- includes context gaps and a deterministic agent briefing

## Composition Contract

The command follows the contract documented in `docs/muninn_v2_shadow_rehydration_preview.md`:

1. Primary retrieval over active v2 cards.
2. Recent in-scope supplement, unless disabled.
3. Optional evidence attachment.
4. Limit and optional character-budget enforcement, preferring primary cards.
5. Deterministic non-LLM agent briefing from retrieved titles and summaries.

Boundary: this is Muninn v2 shadow/evaluation infrastructure, not Mimir cognition, salience propagation, live Codex context, or production migration.

## Friday Preview Assessment

Command:

`PYTHONPATH=src python3 -m muninn.v2.cli shadow-rehydrate-preview --v2-db reports/pilots/friday_v2_shadow_2026-05-17/friday_shadow_v2.db --query "resume Friday project current state and next steps" --out-dir reports/pilots/friday_v2_shadow_2026-05-17/shadow_rehydrate_preview_command --limit 12 --primary-limit 3 --recent-limit 9 --retrieval-mode hybrid --include-evidence --include-explanations --strict`

Result:

- candidate cards: 47
- primary results: 3
- recent supplements: 9
- total preview cards: 12
- omitted for budget: 0
- omitted for limit: 0
- usable: true

Assessment:

- The command reproduces the previously useful staged preview shape.
- The most current Friday implementation/ops cards appear in the recent supplement section.
- Primary matches for the broad resume query skew toward analysis/corpus/mobile cards, so the supplement stage is necessary for a good Friday resume preview.
- Context gap correctly reports degraded derived index backend: `sqlite_vec_unavailable_using_json_vector_fallback`.

## ReadyPlayer1 Preview Assessment

Command:

`PYTHONPATH=src python3 -m muninn.v2.cli shadow-rehydrate-preview --v2-db reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db --query "resume ReadyPlayer1 current campaign state and next steps" --out-dir reports/pilots/readyplayer1_v2_shadow_2026-05-17/shadow_rehydrate_preview_command --limit 12 --primary-limit 3 --recent-limit 9 --retrieval-mode hybrid --include-evidence --include-explanations --strict`

Result:

- candidate cards: 48
- primary results: 3
- recent supplements: 9
- total preview cards: 12
- omitted for budget: 0
- omitted for limit: 0
- usable: true

Assessment:

- Primary matches surfaced current-state and campaign cards.
- Recent supplements surfaced Campaign 007A, 006A, and 004A continuity cards.
- The deterministic briefing distinguishes retrieved facts from uncertainty and reports the degraded vector backend.

## Safety Checks

- No v1 runtime/schema/MCP/default files were modified.
- Command code reads only the explicit v2 DB path.
- Tests include a monkeypatch guard proving the command does not call the v1 read connector.
- `sqlite_vec` is not required; degraded fallback status is reported.
- Generated shadow DBs and pilot artifacts remain uncommitted.
- Bifrost boundary check reinforces that this command is durable-memory preview infrastructure, not Mimir topology/cognition.

## Adequacy Decision

GO for v2 shadow rehydration preview/evaluation.

NO-GO for live agent context until:

- another review validates preview report quality
- staged preview semantics are accepted as the v2 shadow rehydration contract
- cutover plan exists
- rollback plan exists
- live MCP/Codex defaults are explicitly approved for any change

## Remaining Gaps

- Friday broad-query primary retrieval can be less useful than the recent supplement.
- The preview command is report-oriented; it does not yet produce a versioned shared rehydrate-response envelope.
- Recall parity against v1 FTS remains a measurement gap, not a migration-loss gap.
- `sqlite_vec` remains unavailable, so derived vector status is degraded.

## Recommended Next Task

Run an operator review of the Friday and ReadyPlayer1 preview Markdown outputs, then define the exact v2 shadow rehydrate-response envelope that would be consumed by a future non-live agent-context experiment.
