# Muninn v2 Shadow Rehydration Preview

## Executive Summary

- Usable: `true`
- Total cards: 8 (3 primary, 5 supplements)
- Retrieval backend: `hybrid`
- Fallback used: `false`
- Degraded: `true`

## Query / Task

`resume Friday project current state and next steps`

## Source

- v2 DB: `reports/pilots/friday_v2_shadow_2026-05-17/friday_shadow_v2.db`
- Space key: `repo:f8cc7f64d3636a4e`
- Project path: `None`

## Composition Strategy

- Strategy: `hybrid_primary_plus_recent_supplement`
- Retrieval mode: `hybrid`
- Limit: 12
- Primary limit: 3
- Recent limit: 9
- Max chars: `None`

## Primary Retrieval Matches

- `17beee42-c7ec-4769-9b2b-d90b395c90d7` Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks
  - stage: `primary_retrieval` reason: `query_match` kind: `runbook` updated: `2026-04-14 16:34:57` score=`45.868704`
  - summary: Validated analysis phase against existing gold_full_v1 runner artifacts using dry-run, heuristic-only full pass, OpenAI smoke limit=3, and resume dedupe check.
  - body excerpt: Commands exercised: analyze_run --run-id gold_full_v1 --dry-run; heuristic-only full run to write 50-result artifact set; OpenAI smoke run with --limit 3 producing analysis_results and priority_slices; resume rerun with same analysis_run_id showing to_analyze=0 and no growth in analysis_results line count.
  - evidence: `/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_heuristic_v2/analysis_summary.json`; `/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_summary.json`; `/mnt/data/friday/evals/analysis/README.md`; `/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_results.jsonl`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'resume']
- `d0510e00-574e-4960-87b1-ad33a99e6546` Run Friday corpus runner in dry-run, smoke, and resume modes
  - stage: `primary_retrieval` reason: `query_match` kind: `runbook` updated: `2026-04-14 15:03:49` score=`44.999295`
  - summary: Use evals/runner/config.example.yaml to execute corpus tasks and emit run artifacts under evals/runs/<run_id>. Resume mode skips already-recorded stable IDs (task_id for gold, variant_id for generated).
  - body excerpt: Validation commands exercised: dry-run for gold_only/generated_only/combined; live smoke run for combined limit=3 with run_id smoke_runner_v1; resume rerun with same run_id produced to_run=0 and did not append duplicates. Additional live mode checks were run for gold_only limit=1 and generated_only limit=1.
  - evidence: `/mnt/data/friday/evals/runs/smoke_runner_v1/run_summary.json`; `/mnt/data/friday/evals/runner/config.example.yaml`; `/mnt/data/friday/evals/runner/README.md`; `/mnt/data/friday/evals/runs/smoke_runner_v1/run_results.jsonl`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'resume']
- `c1907668-82e4-4e07-908d-69250a58e825` Friday mobile client uses native Android Compose project under android/
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-04-12 08:43:25` score=`42.217736`
  - summary: Friday now has a conventional native Android app at android/ as the canonical mobile frontend foundation, rather than a web-wrapper approach. The MVP ships with chat UX, mode switching, connection states, and configurable endpoint routing to existing Friday APIs.
  - body excerpt: Implemented Kotlin + Jetpack Compose app module (com.friday.mobile) with layered state/network/settings boundaries. Default endpoint is seeded to http://100.125.116.103:18080/ and routes map by mode to /api/althing/chat and /api/chat. Connection health probes /healthz and the UI exposes retry/error handling with Tailscale hinting.
  - evidence: `/mnt/data/friday/android/app/src/main/java/com/friday/mobile/ChatViewModel.kt`; `/mnt/data/friday/android/README.md`; `/mnt/data/friday/android/app/src/main/java/com/friday/mobile/ui/screens/ChatScreen.kt`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'project', 'state']

## Recent In-Scope Supplements

- `ea8d2c51-9a13-4736-8b12-45c068c6a783` Friday bridge and tools now expose read-only /mnt/data workspace access
  - stage: `recent_in_scope_supplement` reason: `recent_query_primary_domain_overlap` kind: `decision` updated: `2026-04-19 17:54:48`
  - summary: Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
  - body excerpt: FRIDAY_FILE_SEARCH_EXTRA_ROOTS is set to /mnt/data, friday-backend mounts /mnt/data read-only, inspect_repo_path can inspect files or directories across configured read-only roots, and case-insensitive path resolution allows host-style prompts like /mnt/data/Friday or /mnt/data/Althing to resolve safely without enabling writes.
  - evidence: `/mnt/data/friday/backend/tools/builtins.py`; `/mnt/data/friday/backend/api/althing_chat.py`; `/mnt/data/friday/backend/core/chat_engine.py`; `/mnt/data/friday/.env.example`; `/mnt/data/friday/docker-compose.app.yml`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'chat', 'compose', 'example', 'friday', 'mode', 'only', 'under']
- `7fcab1ba-2af2-498d-b712-d6c79520fd6e` Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end
  - stage: `recent_in_scope_supplement` reason: `recent_query_primary_domain_overlap` kind: `decision` updated: `2026-04-19 17:30:26`
  - summary: Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
  - body excerpt: Implemented direct-chat coder auto-routing in `backend/core/chat_engine.py` for inferred `code_execution` routes behind `FRIDAY_CODER_AUTO_ROUTE` (default on). Added bounded repo-local `read_repo_file` in `backend/tools/builtins.py`, allowed it under the existing read-only file-tool gate in `backend/tools/engine.py`, and added runtime prompt-path extraction plus automatic repo-context injection so prompts like `README.md` or `backend/core/chat_engine.py` can succeed even when the model does not request tools correctly. Updated `Dockerfile` to copy the repo working tree into `/app` so repo-l...
  - evidence: `/mnt/data/friday/backend/tools/engine.py:83`; `/mnt/data/friday/backend/tools/builtins.py:204`; `/mnt/data/friday/Dockerfile:18`; `/mnt/data/friday/backend/core/chat_engine.py:1311`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['chat', 'default', 'existing', 'friday', 'implemented', 'live', 'only', 'results', 'routes', 'routing', 'under']
- `849362c5-ed42-43a2-9084-897ecf2c7de1` Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `decision` updated: `2026-04-15 01:59:50`
  - summary: Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
  - body excerpt: Mimir remains a repo cognition substrate, not runtime working memory. Added scripts/mimir_context.sh and Makefile targets (mimir-status, mimir-index, mimir-query, mimir-bundle). Documented boundary between WorkingScratchpad runtime cognition, durable conversational memory, and Mimir repo cognition.
  - evidence: `/mnt/data/friday/docs/ALTHING_WORKING_MEMORY_VS_MIMIR_BOUNDARY.md:1`; `/mnt/data/friday/Makefile:1`; `/mnt/data/friday/scripts/mimir_context.sh:1`; `/mnt/data/friday/docs/ALTHING_MIMIR_ROOT_DECISION.md:1`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'friday']
- `6c7f8245-1952-4464-8998-79725736746e` Althing memory audit identifies bridge/direct split and missing private whiteboard
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `decision` updated: `2026-04-15 01:27:02`
  - summary: Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
  - body excerpt: Created ALTHING memory state audit, gap analysis, and next-step recommendation docs plus machine-readable summary. Key durable finding: Muninn and transcript memory are wired in direct /api/chat path, not in /api/althing/chat default UI flow; closest substrate for whiteboard is transient ExecutionState/intermediate and tool/refinement buffers.
  - evidence: `/mnt/data/friday/artifacts/althing_memory_state_summary.json:1`; `/mnt/data/friday/docs/ALTHING_MEMORY_NEXT_STEP_RECOMMENDATION.md:1`; `/mnt/data/friday/docs/ALTHING_MEMORY_GAP_ANALYSIS.md:1`; `/mnt/data/friday/docs/ALTHING_MEMORY_STATE_AUDIT.md:1`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'analysis', 'artifacts', 'chat', 'default', 'friday', 'next']
- `ecc7842e-8058-4603-b3a0-633970ad4db5` V3 routing+prompt pass completed with targeted and full reruns
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `decision` updated: `2026-04-14 21:57:29`
  - summary: The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
  - body excerpt: Control-layer fixes in prompt_builder/interaction_policy/response_shaper/chat_engine plus runtime context prompt layers reduced routing and prompt-following failures on both targeted and full reruns. The canonical report and delta artifacts were finalized under evals/remediation for future comparison and planning.
  - evidence: `/mnt/data/friday/evals/remediation/remediation_pass_v3_routing_prompt_report.md`; `/mnt/data/friday/evals/remediation/routing_prompt_rerun_v3_delta.json`; `/mnt/data/friday/evals/remediation/combined_v2_to_v3_delta.json`
  - explanation: sources=['query_tokens', 'primary_result_domain_tokens'] tokens=['artifacts', 'canonical', 'chat', 'combined', 'evals', 'friday', 'full', 'implemented', 'pass', 'produced', 'rerun', 'routing', 'under', 'were']

## Evidence / Provenance

- Evidence refs available on preview cards: 31
- Evidence refs included in report: 31
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

- Primary match: Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks - Validated analysis phase against existing gold_full_v1 runner artifacts using dry-run, heuristic-only full pass, OpenAI smoke limit=3, and resume dedupe check.
- Primary match: Run Friday corpus runner in dry-run, smoke, and resume modes - Use evals/runner/config.example.yaml to execute corpus tasks and emit run artifacts under evals/runs/<run_id>. Resume mode skips already-recorded stable IDs (task_id for gold, variant_id for generated).
- Primary match: Friday mobile client uses native Android Compose project under android/ - Friday now has a conventional native Android app at android/ as the canonical mobile frontend foundation, rather than a web-wrapper approach. The MVP ships with chat UX, mode switching, connection states, and configurable endpoint routing to existing Friday APIs.
- Continuity: Friday bridge and tools now expose read-only /mnt/data workspace access - Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
- Continuity: Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end - Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
- Continuity: Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory - Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
- Continuity: Althing memory audit identifies bridge/direct split and missing private whiteboard - Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
- Continuity: V3 routing+prompt pass completed with targeted and full reruns - The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
