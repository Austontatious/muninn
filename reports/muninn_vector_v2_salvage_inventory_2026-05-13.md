# Muninn Vector v2 Salvage Inventory

Basis: initial `git status` and diff snapshot captured before this task's implementation edits.

## Summary

- High-risk v1 live-path drift: v1 schema migration, v1 bootstrap auto-table creation, v1 CLI vector/session commands, v1 MCP session tool, and v1 rehydrate vector admission.
- Salvageable concepts: deterministic derived vectors, index health, dry-run rebuild, lexical fallback, query fixtures, overlap/mismatch reporting, and session-shaped report output.
- Commit eligibility: only v2 code/docs/tests/reports should be staged. v1 runtime/schema/MCP changes should not be bundled.

## Architecture Review Answers

1. Vector health issue:
   - `sqlite_vec` is unavailable, so the attempted v1 vector code reports fallback.
   - v1 vector tables and generation jobs were never safely committed as production behavior.
   - The live v1 service does not depend on vector health; current MCP/API health is OK.
   - The reported `478` missing vectors are expected because the experimental v1 index was not built and should not be auto-created in production.

2. v2-compatible pieces:
   - deterministic hash embedding as a local fallback
   - index status with eligible/indexed/missing/stale counts
   - explicit dry-run rebuild and explicit write flag
   - lexical fallback labeled as provisional
   - retrieval eval reports with missing/extra/ranking diagnostics
   - optional session-shaped report helper

3. v1-only pieces to avoid:
   - `migrations/0001_init.sql`
   - `src/muninn/human_memory/bootstrap.py`
   - `src/muninn/cli.py` commands using human-memory DB defaults
   - `src/muninn/mcp_server.py` MCP tool additions
   - live `rehydrate.bundle` vector admission changes

4. Safe v1 opt-in tooling:
   - None selected for this task. Even opt-in v1 vector commands would still introduce production DB defaults and schema expectations.

5. Mimir-adjacent pieces:
   - salience propagation
   - spreading activation
   - hidden-link discovery
   - motif/cognition-style retrieval
   - vector admission policy beyond measurement

## Per-File Classification

See `reports/muninn_vector_v2_salvage_inventory_2026-05-13.json` for the complete path-by-path classification.
