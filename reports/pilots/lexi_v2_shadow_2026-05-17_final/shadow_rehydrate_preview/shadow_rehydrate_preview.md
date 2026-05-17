# Muninn v2 Shadow Rehydration Preview

## Executive Summary

- Usable: `true`
- Total cards: 8 (3 primary, 5 supplements)
- Retrieval backend: `hybrid`
- Fallback used: `false`
- Degraded: `true`

## Query / Task

`resume Lexi current production audit and runtime modernization state and next steps`

## Source

- v2 DB: `reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db`
- Space key: `repo:0c321b2a6f183a95`
- Project path: `None`

## Composition Strategy

- Strategy: `hybrid_primary_plus_recent_supplement`
- Retrieval mode: `hybrid`
- Limit: 12
- Primary limit: 3
- Recent limit: 9
- Max chars: `None`

## Primary Retrieval Matches

- `d61eacef-96d5-40fb-9dc4-5de8c11399c1` Lexi production audit verdict 2026-05-17
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-17 21:24:31` score=`112.700624`
  - summary: Production audit completed for Lexi.
  - body excerpt: Lexi should be presented as a deployed production-facing alpha/prototype, not production-ready, until the audit blockers are fixed: public /lexi/readyz 503, disabled avatar_edit/img2img, divergent backend source trees plus active production overrides, repo-root pytest import failure, telemetry/logging claim mismatch, streaming sanitizer NameError, and alpha session memory not recording /process under X-Lexi-Session.
  - evidence: `/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/status_matrix.md`; `/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/README.md`; `/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/risk_register.md`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['audit', 'lexi', 'production']
- `6e97a92a-84e7-423f-844c-927bd48a7d21` DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau
  - stage: `primary_retrieval` reason: `query_match` kind: `constraint` updated: `2026-04-19 18:54:41` score=`57.646469`
  - summary: The Lex DreamerV2 GPU-3 sidecar is still generating fresh MiniGrid episodes, including files written on 2026-04-19, so the experiment is not dead or fully stalled. But current learning is weak because replay requires `minlen: 10` while almost all recent episodes are only 5-9 steps and are being skipped before they can enter replay.
  - body excerpt: Read-only runtime checks on 2026-04-19 showed `lex-dreamerv2-gpu3-shadow` up and the latest train episode file landing at 2026-04-19T18:47:41-07:00. Historical progression is real: the first 1000 logged returns averaged about 0.4488 reward and 34.15 steps, while the last 1000 averaged about 0.949 reward and 5.44 steps, indicating the policy learned the toy MiniGrid task. The current bottleneck is replay-gated saturation, not total inactivity: the persistent config keeps `replay.capacity: 50000` and `replay.minlen: 10`, the live tail is dominated by `Skipping short episode` lines, and 9992 o...
  - evidence: `/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152260`; `/mnt/data/Lex/tmp/dreamerv2_probe/run_minigrid_persistent.py:26`; `/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3/config.yaml:69`; `/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152063`; `/mnt/data/Lex/docs/world_model_shadow_harness_report.md:15`
  - explanation: sources=['body', 'summary', 'title', 'vector'] tokens=['current', 'runtime', 'steps']
- `6f25a3c0-676d-4e64-8351-213b18040f93` Lex modernization phases 1-5 checkpointed with validated auth/prompt/eval hardening
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-01 17:29:31` score=`54.659741`
  - summary: Created a known-good checkpoint commit for Lex modernization phases 1-5 and added a concise durable checkpoint document. Validation status records pytest, route uniqueness, eval runner, clean-shell make eval, frontend build, backend startup smoke, auth/session, Google CSRF behavior, and prompt trust-boundary probes as passing.
  - body excerpt: Checkpoint commit fdb9d9733ee67464cdda57c5c9debcecbe681ab3 captures phase 1-5 modernization changes and docs/lexi_modernization_checkpoint.md records completed phases, security assumptions, deferred risks, and next-phase options. Recommended next lane is Phase 6 deployment/runtime resilience focused on writable-path preflight/creation, clearer unwritable-path errors, summarizer fallback handling, FastAPI lifespan migration, and Pydantic v2 warning cleanup.
  - evidence: `/mnt/data/Lex/evals/runner.py:1`; `/mnt/data/Lex/docs/lexi_modernization_checkpoint.md:1`; `/mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md:1`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['lexi', 'modernization', 'next', 'runtime']

## Recent In-Scope Supplements

- `539f6130-6a78-4646-b7fe-da1d2a7d0b98` Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-01 17:53:15`
  - summary: Created a clean Phase 6 checkpoint commit containing only deployment/runtime resilience source, tests, and report updates. Runtime artifacts and generated eval/avatar files were intentionally left uncommitted.
  - body excerpt: Checkpoint commit 072ed15db5e745b50e7c4a715b7e475913666ffb records runtime preflight enforcement, summarizer degraded fallback handling, lifespan startup migration, and low-risk Pydantic v2 config cleanup. Commit scope excludes backend/memory user manifest drift, evals/last_results outputs, and local avatar image artifacts to keep the checkpoint clean and reproducible.
  - evidence: `/mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1`; `/mnt/data/Lex/tests/test_runtime_preflight.py:1`; `/mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['avatar', 'backend', 'checkpoint', 'clean', 'cleanup', 'commit', 'config', 'created', 'deployment', 'docs', 'eval', 'fallback', 'files', 'handling', 'last', 'lexi', 'lifespan', 'memory', 'migration', 'modernization', 'only', 'phase', 'preflight', 'pydantic', 'records', 'resilience', 'runtime', 'source', 'startup', 'summarizer']
- `8099af8a-88e6-4e88-b1c9-684c4ea5aa4e` Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-01 17:47:21`
  - summary: Lex Phase 6 adds startup runtime-path preflight with writable-path enforcement, bounded summarizer fallback behavior, and FastAPI lifespan migration to replace deprecated startup events. Session runtime directories now resolve from env at runtime to avoid stale import-time path binding.
  - body excerpt: Implemented backend/lexi/core/runtime_preflight.py and wired run_runtime_preflight() into backend lifespan startup before other startup hooks. Added per-request timeout override support in model loader and degraded summarizer fallback in utils/summarize.py so summarizer unavailability does not break chat/session continuity updates. Migrated class-based Pydantic config usage in now.py and love_loop.py to v2 model_config, and added focused tests for preflight create/fail behavior, startup guarded cache flush behavior, and summarizer degraded-mode fallback.
  - evidence: `/mnt/data/Lex/backend/lexi/core/backend_core.py:80`; `/mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1`; `/mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['added', 'backend', 'before', 'behavior', 'config', 'docs', 'fallback', 'fastapi', 'focused', 'handling', 'import', 'lexi', 'lifespan', 'migration', 'modernization', 'path', 'phase', 'preflight', 'pydantic', 'resilience', 'runtime', 'session', 'startup', 'summarizer', 'writable']
- `c40c8b59-4e43-4e9d-976a-0c27e289596c` Phase 5 runtime smoke proof completed for Lex modernization
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-04-30 21:53:11`
  - summary: Phase 5 smoke validation passed for tests, route uniqueness, eval runner, and frontend build. Runtime auth/session, Google secure CSRF, Google dev/test bypass, chat path, and route inventory parity were verified. Backend startup requires writable runtime paths in this environment.
  - body excerpt: Ran PYTHONPATH=. pytest -rA (171 passed, 1 skipped), route uniqueness inspection (total=100 unique=100 duplicates=0), eval runner checks (9/9), and make eval from a clean shell. Frontend build compiled successfully. Backend startup smoke succeeded when runtime paths were explicitly set to writable temp locations; default local paths can fail with permission errors. Prompt trust boundaries remain enforced for tool/external context and for memory retrieval paths when retrieval is present.
  - evidence: `/mnt/data/Lex/tests/test_phase1_stabilization.py`; `/mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md`; `/mnt/data/Lex/evals/last_results.json`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['auth', 'backend', 'build', 'checks', 'clean', 'completed', 'csrf', 'docs', 'errors', 'eval', 'frontend', 'google', 'last', 'lexi', 'make', 'memory', 'modernization', 'path', 'phase', 'prompt', 'pytest', 'requires', 'route', 'runner', 'runtime', 'session', 'shell', 'skipped', 'smoke', 'startup', 'total', 'trust', 'uniqueness', 'validation', 'writable']
- `650e57d3-d07d-42c5-888d-28a0160fb224` Lex modernization phases 2A-4 hardened auth boundaries, prompt trust blocks, and eval gates
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `decision` updated: `2026-04-30 21:01:33`
  - summary: Implemented Google CSRF double-submit checks, trusted-proxy IP resolution, route inventory/deprecation mapping, untrusted-context prompt framing, and machine-graded eval cases without introducing import-time network writes.
  - body excerpt: Phase 2A: Google login now validates g_csrf_token body/cookie with explicit LEXI_GOOGLE_CSRF_BYPASS dev gate, and request IP resolution now trusts forwarded headers only from configured proxy CIDRs. Phase 2B: runtime inventory documents 100 routes, 10 compatibility aliases, and no removals. Phase 3: added shared untrusted context formatter and system trust-boundary rule; retrieved memory/tool/external blocks are framed as data-only. Phase 4: replaced pending eval scaffolds with 9 machine-graded deterministic cases plus runner reporting.
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['added', 'auth', 'boundary', 'checks', 'csrf', 'eval', 'google', 'import', 'lexi', 'memory', 'modernization', 'only', 'phase', 'phases', 'plus', 'prompt', 'route', 'runner', 'runtime', 'security', 'trust']
- `df2b467b-c10b-4a2f-8c2c-e1f5e34d603f` Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating
  - stage: `recent_in_scope_supplement` reason: `recent_query_primary_domain_overlap` kind: `decision` updated: `2026-04-30 20:05:44`
  - summary: Review found high-priority risks in import-time side effects, Google login CSRF handling, and broken test collection; medium-priority gaps in route duplication, proxy-trust handling, and untrusted memory/tool text boundaries. Recommended sequence is stabilize core reliability first, then apply instruction-hierarchy and eval upgrades aligned with current published techniques.
  - body excerpt: Implementation order: (1) remove import-time network/file side effects and eliminate duplicate route mounts, (2) fix test collection drift and restore deterministic gates, (3) add Google login CSRF double-submit verification and trusted-proxy IP handling, (4) label tool/memory text as untrusted and enforce instruction-priority handling, (5) upgrade eval harness from scaffold-only checks to behavior/criterion scoring over representative datasets.
  - evidence: `/mnt/data/Lex/backend/lexi/__init__.py:36`; `/mnt/data/Lex/backend/lexi/routes/auth.py:182`; `/mnt/data/Lex/evals/runner.py:45`; `/mnt/data/Lex/backend/lexi/routes/lexi.py:197`; `/mnt/data/Lex/backend/lexi/core/backend_core.py:203`
  - explanation: sources=['query_tokens', 'primary_result_domain_tokens'] tokens=['auth', 'backend', 'behavior', 'checks', 'csrf', 'eval', 'file', 'first', 'google', 'handling', 'hardening', 'import', 'lexi', 'memory', 'only', 'real', 'recommended', 'risks', 'route', 'runner', 'trust']

## Evidence / Provenance

- Evidence refs available on preview cards: 25
- Evidence refs included in report: 25
- Retrieval mode: `hybrid`
- Degradation reasons: `['sqlite_vec_unavailable_using_json_vector_fallback']`

## Explanation Notes

- Explanations included: `true`
- Duplicates removed: 0
- Omitted for budget: 0
- Omitted for limit: 0

## Context Gaps / Uncertainty

- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

## Suggested Agent Briefing

- Primary match: Lexi production audit verdict 2026-05-17 - Production audit completed for Lexi.
- Primary match: DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau - The Lex DreamerV2 GPU-3 sidecar is still generating fresh MiniGrid episodes, including files written on 2026-04-19, so the experiment is not dead or fully stalled. But current learning is weak because replay requires `minlen: 10` while almost all recent episodes are only 5-9 steps and are being skipped before they can enter replay.
- Primary match: Lex modernization phases 1-5 checkpointed with validated auth/prompt/eval hardening - Created a known-good checkpoint commit for Lex modernization phases 1-5 and added a concise durable checkpoint document. Validation status records pytest, route uniqueness, eval runner, clean-shell make eval, frontend build, backend startup smoke, auth/session, Google CSRF behavior, and prompt trust-boundary probes as passing.
- Continuity: Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline - Created a clean Phase 6 checkpoint commit containing only deployment/runtime resilience source, tests, and report updates. Runtime artifacts and generated eval/avatar files were intentionally left uncommitted.
- Continuity: Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling - Lex Phase 6 adds startup runtime-path preflight with writable-path enforcement, bounded summarizer fallback behavior, and FastAPI lifespan migration to replace deprecated startup events. Session runtime directories now resolve from env at runtime to avoid stale import-time path binding.
- Continuity: Phase 5 runtime smoke proof completed for Lex modernization - Phase 5 smoke validation passed for tests, route uniqueness, eval runner, and frontend build. Runtime auth/session, Google secure CSRF, Google dev/test bypass, chat path, and route inventory parity were verified. Backend startup requires writable runtime paths in this environment.
- Continuity: Lex modernization phases 2A-4 hardened auth boundaries, prompt trust blocks, and eval gates - Implemented Google CSRF double-submit checks, trusted-proxy IP resolution, route inventory/deprecation mapping, untrusted-context prompt framing, and machine-graded eval cases without introducing import-time network writes.
- Continuity: Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating - Review found high-priority risks in import-time side effects, Google login CSRF handling, and broken test collection; medium-priority gaps in route duplication, proxy-trust handling, and untrusted memory/tool text boundaries. Recommended sequence is stabilize core reliability first, then apply instruction-hierarchy and eval upgrades aligned with current published techniques.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
