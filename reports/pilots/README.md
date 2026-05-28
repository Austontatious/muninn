# Pilot Artifacts

> Status: GENERATED EVIDENCE. This directory contains v2 shadow migration,
> bridge, replay, recall, and live-trial artifacts. Do not treat files here as
> current source-of-truth instructions.

## Handling Policy

- Preserve Markdown, JSON, JSONL, manifests, and checksums unless a cleanup task
  explicitly approves deletion.
- Keep generated SQLite DBs, WAL files, and other bulky runtime artifacts out of
  git unless a task explicitly approves committing them.
- Prefer adding an index or report over editing generated artifacts in place.
- When a pilot has both a top-level report under `../` and raw artifacts here,
  read the top-level report first.

## Current Notable Artifact Groups

- `phase_j_personal_live_trial_2026-05-17/`: Phase J trial setup, backups,
  smoke evidence, policies, requests, and copied v2 trial DBs.
- `phase_i_batch_shadow_migration_2026-05-17/`: multi-repo shadow migration
  artifacts and manifest.
- `phase_i_b_replay_fixtures_2026-05-17/`: replay fixtures and closeout inputs.
- `phase_h_shadow_ops_gate_2026-05-17/`: replay gate and safety evidence.
- `phase_g_shadow_ops_drill_2026-05-17/`: replayable shadow operations drill.
- `phase_e_readonly_bridge_2026-05-17/`: read-only bridge request/response
  artifacts.
- `<project>_v2_shadow_2026-05-17/`: single-project shadow migration and
  retrieval evidence.
