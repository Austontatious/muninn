BEGIN MUNINN V2 AGENT CONTEXT
schema_version: muninn.v2.rehydrate_response.v1
contract_version: 1.0.0
response_kind: shadow_rehydrate_preview
task: resume Friday project current state and next steps
source_v2_db: /mnt/data/Muninn/reports/pilots/phase_d2_recall_reinforcement_2026-05-17/friday_phase_d2_shadow_v2.db
space_key: repo:f8cc7f64d3636a4e
project_path: /mnt/data/friday
retrieval_mode: hybrid
retrieval_backend: hybrid
degraded: true
degradation_reasons: sqlite_vec_unavailable_using_json_vector_fallback
budget: 8 selected (3 primary, 5 supplements), 0 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [17beee42-c7ec-4769-9b2b-d90b395c90d7] Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks
  kind: runbook status: active stage: primary_retrieval reason: query_match
  score: 45.868704 rank: 1
  summary: Validated analysis phase against existing gold_full_v1 runner artifacts using dry-run, heuristic-only full pass, OpenAI smoke limit=3, and resume dedupe check.
  body: Commands exercised: analyze_run --run-id gold_full_v1 --dry-run; heuristic-only full run to write 50-result artifact set; OpenAI smoke run with --limit 3 producing analysis_results and priority_slices; resume rerun with same analysis_run_id showing to_analyze=0 and no growth in analysis_results line count.
  evidence: /mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_heuristic_v2/analysis_summary.json; /mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_summary.json; /mnt/data/friday/evals/analysis/README.md; /mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_results.jsonl
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'resume']
- [d0510e00-574e-4960-87b1-ad33a99e6546] Run Friday corpus runner in dry-run, smoke, and resume modes
  kind: runbook status: active stage: primary_retrieval reason: query_match
  score: 44.999295 rank: 2
  summary: Use evals/runner/config.example.yaml to execute corpus tasks and emit run artifacts under evals/runs/<run_id>. Resume mode skips already-recorded stable IDs (task_id for gold, variant_id for generated).
  body: Validation commands exercised: dry-run for gold_only/generated_only/combined; live smoke run for combined limit=3 with run_id smoke_runner_v1; resume rerun with same run_id produced to_run=0 and did not append duplicates. Additional live mode checks were run for gold_only limit=1 and generated_only limit=1.
  evidence: /mnt/data/friday/evals/runs/smoke_runner_v1/run_summary.json; /mnt/data/friday/evals/runner/config.example.yaml; /mnt/data/friday/evals/runner/README.md; /mnt/data/friday/evals/runs/smoke_runner_v1/run_results.jsonl
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'resume']
- [c1907668-82e4-4e07-908d-69250a58e825] Friday mobile client uses native Android Compose project under android/
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 42.217736 rank: 3
  summary: Friday now has a conventional native Android app at android/ as the canonical mobile frontend foundation, rather than a web-wrapper approach. The MVP ships with chat UX, mode switching, connection states, and configurable endpoint routing to existing Friday APIs.
  body: Implemented Kotlin + Jetpack Compose app module (com.friday.mobile) with layered state/network/settings boundaries. Default endpoint is seeded to http://100.125.116.103:18080/ and routes map by mode to /api/althing/chat and /api/chat. Connection health probes /healthz and the UI exposes retry/error handling with Tailscale hinting.
  evidence: /mnt/data/friday/android/app/src/main/java/com/friday/mobile/ChatViewModel.kt; /mnt/data/friday/android/README.md; /mnt/data/friday/android/app/src/main/java/com/friday/mobile/ui/screens/ChatScreen.kt
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['friday', 'project', 'state']

CONTINUITY SUPPLEMENTS
- [ea8d2c51-9a13-4736-8b12-45c068c6a783] Friday bridge and tools now expose read-only /mnt/data workspace access
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_primary_domain_overlap
  score: 14.5 rank: None
  summary: Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
  body: FRIDAY_FILE_SEARCH_EXTRA_ROOTS is set to /mnt/data, friday-backend mounts /mnt/data read-only, inspect_repo_path can inspect files or directories across configured read-only roots, and case-insensitive path resolution allows host-style prompts like /mnt/data/Friday or /mnt/data/Althing to resolve safely without enabling writes.
  evidence: /mnt/data/friday/backend/tools/builtins.py; /mnt/data/friday/backend/api/althing_chat.py; /mnt/data/friday/backend/core/chat_engine.py; /mnt/data/friday/.env.example; /mnt/data/friday/docker-compose.app.yml
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'chat', 'compose', 'example', 'friday', 'mode', 'only', 'under']
- [7fcab1ba-2af2-498d-b712-d6c79520fd6e] Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_primary_domain_overlap
  score: 14.5 rank: None
  summary: Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
  body: Implemented direct-chat coder auto-routing in `backend/core/chat_engine.py` for inferred `code_execution` routes behind `FRIDAY_CODER_AUTO_ROUTE` (default on). Added bounded repo-local `read_repo_file` in `backend/tools/builtins.py`, allowed it under the existing read-only file-tool gate in `backend/tools/engine.py`, and added runtime prompt-path extraction plus automatic repo-context injection so prompts like `README.md` or `backend/core/chat_engine.py` can succeed even when the model does not request tools correctly. Updated `Dockerfile` to copy the repo working tree into `/app` so repo-l...
  evidence: /mnt/data/friday/backend/tools/engine.py:83; /mnt/data/friday/backend/tools/builtins.py:204; /mnt/data/friday/Dockerfile:18; /mnt/data/friday/backend/core/chat_engine.py:1311
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['chat', 'default', 'existing', 'friday', 'implemented', 'live', 'only', 'results', 'routes', 'routing', 'under']
- [849362c5-ed42-43a2-9084-897ecf2c7de1] Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 15.0 rank: None
  summary: Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
  body: Mimir remains a repo cognition substrate, not runtime working memory. Added scripts/mimir_context.sh and Makefile targets (mimir-status, mimir-index, mimir-query, mimir-bundle). Documented boundary between WorkingScratchpad runtime cognition, durable conversational memory, and Mimir repo cognition.
  evidence: /mnt/data/friday/docs/ALTHING_WORKING_MEMORY_VS_MIMIR_BOUNDARY.md:1; /mnt/data/friday/Makefile:1; /mnt/data/friday/scripts/mimir_context.sh:1; /mnt/data/friday/docs/ALTHING_MIMIR_ROOT_DECISION.md:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'friday']
- [6c7f8245-1952-4464-8998-79725736746e] Althing memory audit identifies bridge/direct split and missing private whiteboard
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 23.0 rank: None
  summary: Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
  body: Created ALTHING memory state audit, gap analysis, and next-step recommendation docs plus machine-readable summary. Key durable finding: Muninn and transcript memory are wired in direct /api/chat path, not in /api/althing/chat default UI flow; closest substrate for whiteboard is transient ExecutionState/intermediate and tool/refinement buffers.
  evidence: /mnt/data/friday/artifacts/althing_memory_state_summary.json:1; /mnt/data/friday/docs/ALTHING_MEMORY_NEXT_STEP_RECOMMENDATION.md:1; /mnt/data/friday/docs/ALTHING_MEMORY_GAP_ANALYSIS.md:1; /mnt/data/friday/docs/ALTHING_MEMORY_STATE_AUDIT.md:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['althing', 'analysis', 'artifacts', 'chat', 'default', 'friday', 'next']
- [ecc7842e-8058-4603-b3a0-633970ad4db5] V3 routing+prompt pass completed with targeted and full reruns
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 21.0 rank: None
  summary: The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
  body: Control-layer fixes in prompt_builder/interaction_policy/response_shaper/chat_engine plus runtime context prompt layers reduced routing and prompt-following failures on both targeted and full reruns. The canonical report and delta artifacts were finalized under evals/remediation for future comparison and planning.
  evidence: /mnt/data/friday/evals/remediation/remediation_pass_v3_routing_prompt_report.md; /mnt/data/friday/evals/remediation/routing_prompt_rerun_v3_delta.json; /mnt/data/friday/evals/remediation/combined_v2_to_v3_delta.json
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'primary_result_domain_tokens'] tokens=['artifacts', 'canonical', 'chat', 'combined', 'evals', 'friday', 'full', 'implemented', 'pass', 'produced', 'rerun', 'routing', 'under', 'were']

EVIDENCE
- [17144789-09c0-4dd1-93db-23e795a1e58f] card=17beee42-c7ec-4769-9b2b-d90b395c90d7 type=file ref=/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_heuristic_v2/analysis_summary.json
- [1e6b94d0-aed0-477f-94e4-f4dc8b149183] card=17beee42-c7ec-4769-9b2b-d90b395c90d7 type=file ref=/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_summary.json
- [2727e421-390a-4ced-988c-bcb5980cdd15] card=17beee42-c7ec-4769-9b2b-d90b395c90d7 type=file ref=/mnt/data/friday/evals/analysis/README.md
- [61df0a11-0173-4b17-8571-b844735fe56d] card=17beee42-c7ec-4769-9b2b-d90b395c90d7 type=file ref=/mnt/data/friday/evals/analysis_runs/gold_full_v1_analysis_smoke_v1/analysis_results.jsonl
- [0b6774a3-7336-4559-b064-ec2f295ec473] card=6c7f8245-1952-4464-8998-79725736746e type=file ref=/mnt/data/friday/artifacts/althing_memory_state_summary.json:1
- [0d2eae8d-53c9-45f8-a787-45afd52188ad] card=6c7f8245-1952-4464-8998-79725736746e type=file ref=/mnt/data/friday/docs/ALTHING_MEMORY_NEXT_STEP_RECOMMENDATION.md:1
- [5ceea109-4b84-451f-a9cc-e3e7cb433e4d] card=6c7f8245-1952-4464-8998-79725736746e type=file ref=/mnt/data/friday/docs/ALTHING_MEMORY_GAP_ANALYSIS.md:1
- [f631e78c-21f4-44c1-822b-79fb5062e2d9] card=6c7f8245-1952-4464-8998-79725736746e type=file ref=/mnt/data/friday/docs/ALTHING_MEMORY_STATE_AUDIT.md:1
- [13f786f8-5b0b-4a83-9146-fa5a4de4f618] card=7fcab1ba-2af2-498d-b712-d6c79520fd6e type=file ref=/mnt/data/friday/backend/tools/engine.py:83
- [72aa7b50-7c2e-499a-b882-0bcbcb11005d] card=7fcab1ba-2af2-498d-b712-d6c79520fd6e type=file ref=/mnt/data/friday/backend/tools/builtins.py:204
- [852cca34-f82d-48fb-8721-df5d1628c5aa] card=7fcab1ba-2af2-498d-b712-d6c79520fd6e type=file ref=/mnt/data/friday/Dockerfile:18
- [a5d6a4f4-d702-4e97-a99a-5f1f7b1c3725] card=7fcab1ba-2af2-498d-b712-d6c79520fd6e type=file ref=/mnt/data/friday/backend/core/chat_engine.py:1311
- [11e12b86-bebd-4b35-a3f8-271dcdd41434] card=849362c5-ed42-43a2-9084-897ecf2c7de1 type=file ref=/mnt/data/friday/docs/ALTHING_WORKING_MEMORY_VS_MIMIR_BOUNDARY.md:1
- [6221b384-d711-4311-80c4-7faad6d5d91c] card=849362c5-ed42-43a2-9084-897ecf2c7de1 type=file ref=/mnt/data/friday/Makefile:1
- [69b97e6f-0e36-46e1-86fb-24b1d1c11eed] card=849362c5-ed42-43a2-9084-897ecf2c7de1 type=file ref=/mnt/data/friday/scripts/mimir_context.sh:1
- [8bdbd300-8761-43f8-b42b-3cfb31244162] card=849362c5-ed42-43a2-9084-897ecf2c7de1 type=file ref=/mnt/data/friday/docs/ALTHING_MIMIR_ROOT_DECISION.md:1
- [12b145e3-692f-4918-b59d-9c89562be555] card=c1907668-82e4-4e07-908d-69250a58e825 type=file ref=/mnt/data/friday/android/app/src/main/java/com/friday/mobile/ChatViewModel.kt
- [69067d0e-b6d2-4c1d-a417-52721e89c0b6] card=c1907668-82e4-4e07-908d-69250a58e825 type=file ref=/mnt/data/friday/android/README.md
- [9e980adf-c4bb-420a-8b53-b8ff22a633fe] card=c1907668-82e4-4e07-908d-69250a58e825 type=file ref=/mnt/data/friday/android/app/src/main/java/com/friday/mobile/ui/screens/ChatScreen.kt
- [4d81bbad-dfd1-4bbe-a8fb-9d4faffd11cb] card=d0510e00-574e-4960-87b1-ad33a99e6546 type=file ref=/mnt/data/friday/evals/runs/smoke_runner_v1/run_summary.json
- [a74fa9c0-8a02-42e7-af2a-6ccb8f650ba0] card=d0510e00-574e-4960-87b1-ad33a99e6546 type=file ref=/mnt/data/friday/evals/runner/config.example.yaml
- [aaaa4e39-c7cf-4615-940e-4ba29083aba2] card=d0510e00-574e-4960-87b1-ad33a99e6546 type=file ref=/mnt/data/friday/evals/runner/README.md
- [e719e25a-5bdd-40f4-863f-93ca60d2b4e2] card=d0510e00-574e-4960-87b1-ad33a99e6546 type=file ref=/mnt/data/friday/evals/runs/smoke_runner_v1/run_results.jsonl
- [5dc31385-9398-45e1-8b3f-3e8ed9b1f653] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/tools/builtins.py
- [726a558e-ab3c-4d2f-81bb-3c32cd8ea623] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/api/althing_chat.py
- [73535e7c-ca67-498b-8ff1-3488059b01b2] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/core/chat_engine.py
- [b0909751-52ec-478f-8d48-3d396c051d4e] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/.env.example
- [c21d7a97-e41a-43fc-8273-b1462ee9f3a5] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/docker-compose.app.yml
- [0e68e175-0e1c-4ecf-81a8-d28c7d4ca159] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/remediation_pass_v3_routing_prompt_report.md
- [4ee058af-5f23-494a-ac72-d91a135d7224] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/routing_prompt_rerun_v3_delta.json
- [cfbcc4b7-8ad4-40c7-9c8c-78938ec8369e] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/combined_v2_to_v3_delta.json

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

AGENT BRIEFING
- Primary match: Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks - Validated analysis phase against existing gold_full_v1 runner artifacts using dry-run, heuristic-only full pass, OpenAI smoke limit=3, and resume dedupe check.
- Primary match: Run Friday corpus runner in dry-run, smoke, and resume modes - Use evals/runner/config.example.yaml to execute corpus tasks and emit run artifacts under evals/runs/<run_id>. Resume mode skips already-recorded stable IDs (task_id for gold, variant_id for generated).
- Primary match: Friday mobile client uses native Android Compose project under android/ - Friday now has a conventional native Android app at android/ as the canonical mobile frontend foundation, rather than a web-wrapper approach. The MVP ships with chat UX, mode switching, connection states, and configurable endpoint routing to existing Friday APIs.
- Continuity: Friday bridge and tools now expose read-only /mnt/data workspace access - Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
- Continuity: Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end - Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
- Continuity: Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory - Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
- Continuity: Althing memory audit identifies bridge/direct split and missing private whiteboard - Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
- Continuity: V3 routing+prompt pass completed with targeted and full reruns - The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
