BEGIN MUNINN V2 AGENT CONTEXT
schema_version: muninn.v2.rehydrate_response.v1
contract_version: 1.0.0
response_kind: shadow_rehydrate_preview
task: resume Lexi current production audit and runtime modernization state and next steps
source_v2_db: reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db
space_key: repo:0c321b2a6f183a95
project_path: None
retrieval_mode: hybrid
retrieval_backend: hybrid
degraded: true
degradation_reasons: sqlite_vec_unavailable_using_json_vector_fallback
budget: 8 selected (3 primary, 5 supplements), 0 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [d61eacef-96d5-40fb-9dc4-5de8c11399c1] Lexi production audit verdict 2026-05-17
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 112.700624 rank: 1
  summary: Production audit completed for Lexi.
  body: Lexi should be presented as a deployed production-facing alpha/prototype, not production-ready, until the audit blockers are fixed: public /lexi/readyz 503, disabled avatar_edit/img2img, divergent backend source trees plus active production overrides, repo-root pytest import failure, telemetry/logging claim mismatch, streaming sanitizer NameError, and alpha session memory not recording /process under X-Lexi-Session.
  evidence: /mnt/data/Lex/reports/lexi_production_audit_2026-05-17/status_matrix.md; /mnt/data/Lex/reports/lexi_production_audit_2026-05-17/README.md; /mnt/data/Lex/reports/lexi_production_audit_2026-05-17/risk_register.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['audit', 'lexi', 'production']
- [6e97a92a-84e7-423f-844c-927bd48a7d21] DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau
  kind: constraint status: active stage: primary_retrieval reason: query_match
  score: 57.646469 rank: 2
  summary: The Lex DreamerV2 GPU-3 sidecar is still generating fresh MiniGrid episodes, including files written on 2026-04-19, so the experiment is not dead or fully stalled. But current learning is weak because replay requires `minlen: 10` while almost all recent episodes are only 5-9 steps and are being skipped before they can enter replay.
  body: Read-only runtime checks on 2026-04-19 showed `lex-dreamerv2-gpu3-shadow` up and the latest train episode file landing at 2026-04-19T18:47:41-07:00. Historical progression is real: the first 1000 logged returns averaged about 0.4488 reward and 34.15 steps, while the last 1000 averaged about 0.949 reward and 5.44 steps, indicating the policy learned the toy MiniGrid task. The current bottleneck is replay-gated saturation, not total inactivity: the persistent config keeps `replay.capacity: 50000` and `replay.minlen: 10`, the live tail is dominated by `Skipping short episode` lines, and 9992 o...
  evidence: /mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152260; /mnt/data/Lex/tmp/dreamerv2_probe/run_minigrid_persistent.py:26; /mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3/config.yaml:69; /mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152063; /mnt/data/Lex/docs/world_model_shadow_harness_report.md:15
  explanation: path=v2_hybrid_recall sources=['body', 'summary', 'title', 'vector'] tokens=['current', 'runtime', 'steps']
- [6f25a3c0-676d-4e64-8351-213b18040f93] Lex modernization phases 1-5 checkpointed with validated auth/prompt/eval hardening
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 54.659741 rank: 3
  summary: Created a known-good checkpoint commit for Lex modernization phases 1-5 and added a concise durable checkpoint document. Validation status records pytest, route uniqueness, eval runner, clean-shell make eval, frontend build, backend startup smoke, auth/session, Google CSRF behavior, and prompt trust-boundary probes as passing.
  body: Checkpoint commit fdb9d9733ee67464cdda57c5c9debcecbe681ab3 captures phase 1-5 modernization changes and docs/lexi_modernization_checkpoint.md records completed phases, security assumptions, deferred risks, and next-phase options. Recommended next lane is Phase 6 deployment/runtime resilience focused on writable-path preflight/creation, clearer unwritable-path errors, summarizer fallback handling, FastAPI lifespan migration, and Pydantic v2 warning cleanup.
  evidence: /mnt/data/Lex/evals/runner.py:1; /mnt/data/Lex/docs/lexi_modernization_checkpoint.md:1; /mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md:1
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['lexi', 'modernization', 'next', 'runtime']

CONTINUITY SUPPLEMENTS
- [539f6130-6a78-4646-b7fe-da1d2a7d0b98] Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 20.5 rank: None
  summary: Created a clean Phase 6 checkpoint commit containing only deployment/runtime resilience source, tests, and report updates. Runtime artifacts and generated eval/avatar files were intentionally left uncommitted.
  body: Checkpoint commit 072ed15db5e745b50e7c4a715b7e475913666ffb records runtime preflight enforcement, summarizer degraded fallback handling, lifespan startup migration, and low-risk Pydantic v2 config cleanup. Commit scope excludes backend/memory user manifest drift, evals/last_results outputs, and local avatar image artifacts to keep the checkpoint clean and reproducible.
  evidence: /mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1; /mnt/data/Lex/tests/test_runtime_preflight.py:1; /mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['avatar', 'backend', 'checkpoint', 'clean', 'cleanup', 'commit', 'config', 'created', 'deployment', 'docs', 'eval', 'fallback', 'files', 'handling', 'last', 'lexi', 'lifespan', 'memory', 'migration', 'modernization', 'only', 'phase', 'preflight', 'pydantic', 'records', 'resilience', 'runtime', 'source', 'startup', 'summarizer']
- [8099af8a-88e6-4e88-b1c9-684c4ea5aa4e] Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 20.5 rank: None
  summary: Lex Phase 6 adds startup runtime-path preflight with writable-path enforcement, bounded summarizer fallback behavior, and FastAPI lifespan migration to replace deprecated startup events. Session runtime directories now resolve from env at runtime to avoid stale import-time path binding.
  body: Implemented backend/lexi/core/runtime_preflight.py and wired run_runtime_preflight() into backend lifespan startup before other startup hooks. Added per-request timeout override support in model loader and degraded summarizer fallback in utils/summarize.py so summarizer unavailability does not break chat/session continuity updates. Migrated class-based Pydantic config usage in now.py and love_loop.py to v2 model_config, and added focused tests for preflight create/fail behavior, startup guarded cache flush behavior, and summarizer degraded-mode fallback.
  evidence: /mnt/data/Lex/backend/lexi/core/backend_core.py:80; /mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1; /mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['added', 'backend', 'before', 'behavior', 'config', 'docs', 'fallback', 'fastapi', 'focused', 'handling', 'import', 'lexi', 'lifespan', 'migration', 'modernization', 'path', 'phase', 'preflight', 'pydantic', 'resilience', 'runtime', 'session', 'startup', 'summarizer', 'writable']
- [c40c8b59-4e43-4e9d-976a-0c27e289596c] Phase 5 runtime smoke proof completed for Lex modernization
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 22.0 rank: None
  summary: Phase 5 smoke validation passed for tests, route uniqueness, eval runner, and frontend build. Runtime auth/session, Google secure CSRF, Google dev/test bypass, chat path, and route inventory parity were verified. Backend startup requires writable runtime paths in this environment.
  body: Ran PYTHONPATH=. pytest -rA (171 passed, 1 skipped), route uniqueness inspection (total=100 unique=100 duplicates=0), eval runner checks (9/9), and make eval from a clean shell. Frontend build compiled successfully. Backend startup smoke succeeded when runtime paths were explicitly set to writable temp locations; default local paths can fail with permission errors. Prompt trust boundaries remain enforced for tool/external context and for memory retrieval paths when retrieval is present.
  evidence: /mnt/data/Lex/tests/test_phase1_stabilization.py; /mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md; /mnt/data/Lex/evals/last_results.json
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['auth', 'backend', 'build', 'checks', 'clean', 'completed', 'csrf', 'docs', 'errors', 'eval', 'frontend', 'google', 'last', 'lexi', 'make', 'memory', 'modernization', 'path', 'phase', 'prompt', 'pytest', 'requires', 'route', 'runner', 'runtime', 'session', 'shell', 'skipped', 'smoke', 'startup', 'total', 'trust', 'uniqueness', 'validation', 'writable']
- [650e57d3-d07d-42c5-888d-28a0160fb224] Lex modernization phases 2A-4 hardened auth boundaries, prompt trust blocks, and eval gates
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 28.5 rank: None
  summary: Implemented Google CSRF double-submit checks, trusted-proxy IP resolution, route inventory/deprecation mapping, untrusted-context prompt framing, and machine-graded eval cases without introducing import-time network writes.
  body: Phase 2A: Google login now validates g_csrf_token body/cookie with explicit LEXI_GOOGLE_CSRF_BYPASS dev gate, and request IP resolution now trusts forwarded headers only from configured proxy CIDRs. Phase 2B: runtime inventory documents 100 routes, 10 compatibility aliases, and no removals. Phase 3: added shared untrusted context formatter and system trust-boundary rule; retrieved memory/tool/external blocks are framed as data-only. Phase 4: replaced pending eval scaffolds with 9 machine-graded deterministic cases plus runner reporting.
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['added', 'auth', 'boundary', 'checks', 'csrf', 'eval', 'google', 'import', 'lexi', 'memory', 'modernization', 'only', 'phase', 'phases', 'plus', 'prompt', 'route', 'runner', 'runtime', 'security', 'trust']
- [df2b467b-c10b-4a2f-8c2c-e1f5e34d603f] Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_primary_domain_overlap
  score: 13.0 rank: None
  summary: Review found high-priority risks in import-time side effects, Google login CSRF handling, and broken test collection; medium-priority gaps in route duplication, proxy-trust handling, and untrusted memory/tool text boundaries. Recommended sequence is stabilize core reliability first, then apply instruction-hierarchy and eval upgrades aligned with current published techniques.
  body: Implementation order: (1) remove import-time network/file side effects and eliminate duplicate route mounts, (2) fix test collection drift and restore deterministic gates, (3) add Google login CSRF double-submit verification and trusted-proxy IP handling, (4) label tool/memory text as untrusted and enforce instruction-priority handling, (5) upgrade eval harness from scaffold-only checks to behavior/criterion scoring over representative datasets.
  evidence: /mnt/data/Lex/backend/lexi/__init__.py:36; /mnt/data/Lex/backend/lexi/routes/auth.py:182; /mnt/data/Lex/evals/runner.py:45; /mnt/data/Lex/backend/lexi/routes/lexi.py:197; /mnt/data/Lex/backend/lexi/core/backend_core.py:203
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'primary_result_domain_tokens'] tokens=['auth', 'backend', 'behavior', 'checks', 'csrf', 'eval', 'file', 'first', 'google', 'handling', 'hardening', 'import', 'lexi', 'memory', 'only', 'real', 'recommended', 'risks', 'route', 'runner', 'trust']

EVIDENCE
- [c0d6a763-a39b-4cfa-926b-79910c179cd1] card=539f6130-6a78-4646-b7fe-da1d2a7d0b98 type=file ref=/mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1
- [cf39ea9a-6852-45d9-b75f-fdf53d3edefa] card=539f6130-6a78-4646-b7fe-da1d2a7d0b98 type=file ref=/mnt/data/Lex/tests/test_runtime_preflight.py:1
- [edbe6755-2aa1-4b7d-9db8-d6fd08d538e0] card=539f6130-6a78-4646-b7fe-da1d2a7d0b98 type=file ref=/mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1
- [139cbb41-3c2b-4e41-8cc4-4e61895f5991] card=6e97a92a-84e7-423f-844c-927bd48a7d21 type=file ref=/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152260
- [1523f1d2-a26b-4b17-84e1-78f82d892a85] card=6e97a92a-84e7-423f-844c-927bd48a7d21 type=file ref=/mnt/data/Lex/tmp/dreamerv2_probe/run_minigrid_persistent.py:26
- [3075d4fb-33af-435c-9082-59f8f30995ba] card=6e97a92a-84e7-423f-844c-927bd48a7d21 type=file ref=/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3/config.yaml:69
- [3351b60b-cd4f-4841-a63d-0700a675f0eb] card=6e97a92a-84e7-423f-844c-927bd48a7d21 type=file ref=/mnt/data/Lex/artifacts/local/dreamerv2_probe/minigrid_empty5_persistent_gpu3.log:15152063
- [d1061a73-0319-45f4-b0fc-592b25132cc4] card=6e97a92a-84e7-423f-844c-927bd48a7d21 type=file ref=/mnt/data/Lex/docs/world_model_shadow_harness_report.md:15
- [1e69b415-6812-439b-9453-dc081fbb52b6] card=6f25a3c0-676d-4e64-8351-213b18040f93 type=file ref=/mnt/data/Lex/evals/runner.py:1
- [4edd09e1-134a-41a4-af39-61b3ac241c5c] card=6f25a3c0-676d-4e64-8351-213b18040f93 type=file ref=/mnt/data/Lex/docs/lexi_modernization_checkpoint.md:1
- [b469369a-b122-4ab5-bf3e-cfa3ed3b652a] card=6f25a3c0-676d-4e64-8351-213b18040f93 type=file ref=/mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md:1
- [0e374130-c5e9-4c90-a9f4-49cc848887ec] card=8099af8a-88e6-4e88-b1c9-684c4ea5aa4e type=file ref=/mnt/data/Lex/backend/lexi/core/backend_core.py:80
- [35b43ad4-7b91-4b2c-b785-faffa22cf283] card=8099af8a-88e6-4e88-b1c9-684c4ea5aa4e type=file ref=/mnt/data/Lex/backend/lexi/core/runtime_preflight.py:1
- [b01416b4-2353-4f9e-ad73-a8caadb881a2] card=8099af8a-88e6-4e88-b1c9-684c4ea5aa4e type=file ref=/mnt/data/Lex/docs/lexi_modernization_phase6_runtime_resilience_report.md:1
- [1a60774d-e194-43d2-a5ca-8c0aefac50a7] card=c40c8b59-4e43-4e9d-976a-0c27e289596c type=file ref=/mnt/data/Lex/tests/test_phase1_stabilization.py
- [658aead5-2fd7-4dac-8513-a37cae81fc85] card=c40c8b59-4e43-4e9d-976a-0c27e289596c type=file ref=/mnt/data/Lex/docs/lexi_modernization_phase5_runtime_smoke_report.md
- [9f9c0cfa-f182-4694-818e-a7e5bbbf693c] card=c40c8b59-4e43-4e9d-976a-0c27e289596c type=file ref=/mnt/data/Lex/evals/last_results.json
- [5c3a3c10-d642-420b-98d6-d866dd0051f1] card=d61eacef-96d5-40fb-9dc4-5de8c11399c1 type=file ref=/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/status_matrix.md
- [9dd61aa5-08eb-4840-870f-db80d40eff61] card=d61eacef-96d5-40fb-9dc4-5de8c11399c1 type=file ref=/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/README.md
- [d6e928e7-4188-49a6-88ca-6e5f8fb67521] card=d61eacef-96d5-40fb-9dc4-5de8c11399c1 type=file ref=/mnt/data/Lex/reports/lexi_production_audit_2026-05-17/risk_register.md
- [49dd7c2b-acb8-4b91-94c9-82876d94e420] card=df2b467b-c10b-4a2f-8c2c-e1f5e34d603f type=file ref=/mnt/data/Lex/backend/lexi/__init__.py:36
- [5fe24c9e-bdc6-4a95-8e4b-bdaf9d6ae9b8] card=df2b467b-c10b-4a2f-8c2c-e1f5e34d603f type=file ref=/mnt/data/Lex/backend/lexi/routes/auth.py:182
- [af166b2f-47b9-475a-97c2-34222f9d0e4c] card=df2b467b-c10b-4a2f-8c2c-e1f5e34d603f type=file ref=/mnt/data/Lex/evals/runner.py:45
- [d7dea95a-3dd3-4b1e-bd0f-c1927240a852] card=df2b467b-c10b-4a2f-8c2c-e1f5e34d603f type=file ref=/mnt/data/Lex/backend/lexi/routes/lexi.py:197
- [df90a0f6-0d7c-44ac-ad2e-acd6f1de6570] card=df2b467b-c10b-4a2f-8c2c-e1f5e34d603f type=file ref=/mnt/data/Lex/backend/lexi/core/backend_core.py:203

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

AGENT BRIEFING
- Primary match: Lexi production audit verdict 2026-05-17 - Production audit completed for Lexi.
- Primary match: DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau - The Lex DreamerV2 GPU-3 sidecar is still generating fresh MiniGrid episodes, including files written on 2026-04-19, so the experiment is not dead or fully stalled. But current learning is weak because replay requires `minlen: 10` while almost all recent episodes are only 5-9 steps and are being skipped before they can enter replay.
- Primary match: Lex modernization phases 1-5 checkpointed with validated auth/prompt/eval hardening - Created a known-good checkpoint commit for Lex modernization phases 1-5 and added a concise durable checkpoint document. Validation status records pytest, route uniqueness, eval runner, clean-shell make eval, frontend build, backend startup smoke, auth/session, Google CSRF behavior, and prompt trust-boundary probes as passing.
- Continuity: Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline - Created a clean Phase 6 checkpoint commit containing only deployment/runtime resilience source, tests, and report updates. Runtime artifacts and generated eval/avatar files were intentionally left uncommitted.
- Continuity: Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling - Lex Phase 6 adds startup runtime-path preflight with writable-path enforcement, bounded summarizer fallback behavior, and FastAPI lifespan migration to replace deprecated startup events. Session runtime directories now resolve from env at runtime to avoid stale import-time path binding.
- Continuity: Phase 5 runtime smoke proof completed for Lex modernization - Phase 5 smoke validation passed for tests, route uniqueness, eval runner, and frontend build. Runtime auth/session, Google secure CSRF, Google dev/test bypass, chat path, and route inventory parity were verified. Backend startup requires writable runtime paths in this environment.
- Continuity: Lex modernization phases 2A-4 hardened auth boundaries, prompt trust blocks, and eval gates - Implemented Google CSRF double-submit checks, trusted-proxy IP resolution, route inventory/deprecation mapping, untrusted-context prompt framing, and machine-graded eval cases without introducing import-time network writes.
- Continuity: Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating - Review found high-priority risks in import-time side effects, Google login CSRF handling, and broken test collection; medium-priority gaps in route duplication, proxy-trust handling, and untrusted memory/tool text boundaries. Recommended sequence is stabilize core reliability first, then apply instruction-hierarchy and eval upgrades aligned with current published techniques.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
