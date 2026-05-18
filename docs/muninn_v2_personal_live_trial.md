# Muninn v2 Personal Local Live Trial

## Status

Phase J enables a personal/local live trial for Auston's Codex workflows.

- Personal local live trial: GO when smoke tests pass
- General production cutover: NO-GO
- Live MCP replacement: NO-GO
- Adaptive default retrieval: OFF
- v2 writes: DISABLED
- Existing completion-card writes: V1_ONLY, using the existing v1 workflow
- v1 rollback: AVAILABLE

This is not public production cutover and not a permanent migration decision.

## Cutover Path

The least invasive trial path is:

```text
Codex context reads -> Muninn v2 read-only bridge helper
Codex completion writes -> existing v1 workflow only
Adaptive scoring -> disabled by default
Fallback -> documented v1 MCP read path after the v2 failure is logged
```

The trial helper is:

```bash
python3 scripts/muninn_v2_live_context.py \
  --cwd "$PWD" \
  --query "short task summary"
```

The helper reads `configs/muninn_v2_live_trial.json`, resolves the configured
project by `cwd`, calls the v2 read-only bridge, writes bridge audit artifacts
under `logs/live_trial/artifacts/`, appends a structured event to
`logs/live_trial/muninn_v2_live_trial_events.jsonl`, and prints a deterministic
context block.

## Current Live Wiring Before Trial

The existing live wiring remains available:

- v1 API: `http://127.0.0.1:8000/health`
- v1 MCP: `http://127.0.0.1:8765/mcp`
- Codex MCP config: `/home/unix/.codex/config.toml`
- VS Code MCP config: `/home/unix/.config/Code/User/mcp.json`
- user services:
  - `/home/unix/.config/systemd/user/muninn-api.service`
  - `/home/unix/.config/systemd/user/muninn-mcp.service`
- v1 core DB: `/home/unix/.local/share/muninn/muninn.db`
- v1 human memory DB: `/home/unix/.local/share/muninn/human_memory.db`

Phase J does not change those service files or replace the MCP server.

## Trial Config

Committed trial config:

- `configs/muninn_v2_live_trial.json`

Local untracked trial DB copies:

- `reports/pilots/phase_j_personal_live_trial_2026-05-17/v2_trial_dbs/*_shadow_v2.db`

The config is deny-by-default per project:

- one explicit `space_key`
- one explicit `project_path`
- one explicit v2 DB path
- `allow_cross_project=false`
- `allow_adaptive_scoring=false`
- `allow_reinforcement_write=false`
- evidence and explanations required except for projects known to lack evidence

## Logging

Use `logs/live_trial/` for trial observations.

Record:

- read request failures
- write attempts and write failures
- v2 bridge errors
- v1 fallback usage
- denied policy requests
- missing context
- confusing or over-included context
- contamination suspicions
- adaptive/degradation surprises

Do not log secrets.

## Rollback

Rollback is mechanical:

1. Stop using `scripts/muninn_v2_live_context.py`.
2. Resume the existing v1 MCP task-start read flow:
   - `muninn.spaces.resolve`
   - `muninn.rehydrate.bundle`
   - fallback `muninn.cards.recent` / `muninn.cards.search`
3. Keep completion writes on the existing v1 workflow.
4. Leave v2 trial artifacts in place for review or archive them after review.
5. If instruction changes are undesirable, revert the Phase J commit.

Backups from the trial start are under:

```text
reports/pilots/phase_j_personal_live_trial_2026-05-17/backups/
```

DB backups are local runtime artifacts and must not be committed.

## Trial Review

After 24-48 hours of normal use, review:

- `logs/live_trial/muninn_v2_live_trial_events.jsonl`
- bridge audit artifacts under `logs/live_trial/artifacts/`
- v2 read failures
- v1 fallback usage
- missing or confusing context reports
- write attempts/failures
- operator notes

The review must decide whether v2 stays in personal local trial, rolls back to
v1-only reads, or advances to a broader cutover plan.
