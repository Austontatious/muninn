# Muninn v2 Phase I Batch Shadow Migration Plan

Date: 2026-05-17

## Scope

Batch shadow-migrate known local project repositories into explicit Muninn v2 pilot databases under:

`reports/pilots/phase_i_batch_shadow_migration_2026-05-17/`

Write scope is limited to Muninn Phase I reports, manifests, policies, requests, and generated shadow artifacts. Other project repositories are inventory-only.

## Safety Boundaries

- Do not mutate v1 runtime, schema, MCP routes, defaults, or production DBs.
- Do not cut over v2 for any project.
- Do not enable adaptive retrieval by default.
- Do not write live memory or completion cards during this phase.
- Do not commit generated shadow DBs, WAL/SHM files, or bulky raw exports.
- Treat Muninn as a high-risk self-hosting project and exclude it from production migration recommendations.

## Execution Checklist

1. Discover local git repositories under `/mnt/data` and match them to v1 spaces where possible.
2. Record repo state: path, branch, HEAD, dirty status, obvious artifact drift, and high-risk flags.
3. Capture v1 safety snapshot using read-only SQLite access and file metadata.
4. For each repo with an identifiable v1 space, run v2 `pilot-import` into an explicit Phase I shadow DB.
5. Run v2 index health, rebuild dry-run, explicit shadow index write when safe, and post-write health.
6. Run read-only bridge checks with a strict project-scoped policy: health, search, rehydrate, explain, wrong-project denial, adaptive-denied.
7. Run full replay gate where Phase G/H fixtures exist; otherwise record limited replay readiness from bridge artifacts.
8. Generate machine-readable migration manifest and human-readable Phase I report.
9. Re-check v1 safety metadata and row counts.
10. Run v2 tests, py_compile, and full test suite.
11. Commit only approved reports/manifests/small fixtures; leave generated DBs unstaged.

## Expected Final Statuses

- Batch shadow migration: GO or PARTIAL-GO.
- Bridge read-only: GO for passing repos.
- Production migration excluding Muninn: READY or NOT READY.
- Muninn production migration: EXCLUDED_PENDING_SEPARATE_PLAN.
- Live cutover: NO-GO.
- Writes: NO-GO.
- Adaptive default: NO-GO.
