# Security

## Principles

- Store only structured memory, not raw transcripts.
- Every write includes provenance (source type, timestamp, optional tool/doc reference).
- Never store executable instructions as memory.
- Support sensitivity tiers and redaction (v1).

## Data handling

- SQLite DB is local and unencrypted by default (dev).
- For production: use Postgres + disk encryption + access controls.
