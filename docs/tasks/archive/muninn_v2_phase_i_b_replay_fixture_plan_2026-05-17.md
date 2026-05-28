# Muninn v2 Phase I-B Replay Fixture Plan

Date: 2026-05-17

## Objective

Upgrade Phase I `REPLAY-GATE: LIMITED` repos to real replay-gate status where possible, and classify repos that lack an identifiable v1 memory source.

## Scope

In scope:

- Generate minimal project-specific bridge operations drill fixtures for Phase I LIMITED repos.
- Run `bridge-ops-drill` and `bridge-replay-gate` against copied Phase I shadow DBs.
- Verify identity/current-state context, contamination denial, audit hash replay, and adaptive-default-off behavior.
- Update the Phase I migration manifest with Phase I-B replay and no-source classifications.
- Produce Phase I-B closeout reports.

Out of scope:

- v1 runtime/schema/MCP/default changes.
- live Codex/MCP integration.
- production cutover.
- live memory writes.
- generated shadow/copy DB commits.

## Safety Plan

- Use existing Phase I shadow DBs as read sources.
- Copy each LIMITED repo DB into the Phase I-B artifact directory before adding derived reinforcement state needed by adaptive-on replay checks.
- Do not mutate `/home/unix/.local/share/muninn/human_memory.db`.
- Keep bridge writes disabled and adaptive scoring disabled by default.
- Commit only reports, fixtures, and manifest updates; leave copied DBs and raw bridge artifacts unstaged.

## Validation Plan

1. Generate fixtures under `reports/pilots/phase_i_b_replay_fixtures_2026-05-17/fixtures/`.
2. Run bridge operations drill per LIMITED repo.
3. Run replay gate per repo with existing v1 safety report.
4. Update Phase I manifest and create Phase I-B closeout reports.
5. Run:
   - `PYTHONPATH=src python3 -m pytest -q tests/test_v2_*.py`
   - `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`
   - `PYTHONPATH=src python3 -m pytest -q`

## Rollback

If any fixture generation or gate result is invalid, leave generated artifacts uncommitted, record NO-GO status in the report, and do not alter production-readiness recommendations.
