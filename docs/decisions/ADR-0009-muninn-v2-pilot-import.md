# ADR-0009: Muninn v2 Dry-Run Pilot Import

Date: 2026-05-13

## Problem

Muninn v2 needs real migration evidence, but Muninn v1 remains live production memory for Codex. A pilot importer must prove v1-to-v2 projection without creating an accidental cutover path or mutating v1.

## Options Considered

1. Add migration behavior to live v1 startup.
2. Add a new production `muninn` CLI subcommand.
3. Add an adjacent v2-only pilot command requiring explicit paths and selectors.

## Decision

Use an adjacent v2-only command:

```bash
python3 -m muninn.v2.cli pilot-import ...
```

The command requires explicit `--v1-db`, `--v2-db`, `--space-key`, `--project-path`, and `--out-dir`. It defaults to dry-run behavior and writes the requested v2 DB only with `--write-v2`.

## Rationale

This keeps the migration path inspectable and testable without changing live MCP, HTTP, or v1 CLI behavior. Explicit paths prevent accidental production target selection. Row-count verification makes v1 immutability visible in every pilot report.

## Consequences

- v1 remains source of truth.
- pilot outputs are audit artifacts, not production data.
- the command can be run repeatedly against one project without touching v1.
- dry-run mode may create a scratch v2 DB under the output directory.

## Explicit Deferrals

- no automatic migration
- no live consumer reads from v2
- no interaction-event mapping to `MemoryEvent` yet
- no vector/salience import beyond unsupported-record reporting
- no migration ledger or source checksum manifest yet
- no side-by-side recall parity command yet
