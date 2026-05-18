BEGIN MUNINN V2 AGENT CONTEXT
schema_version: muninn.v2.rehydrate_response.v1
contract_version: 1.0.0
response_kind: shadow_rehydrate_preview
task: continue Friday direct code route with Mimir repo-cognition boundary and read-only workspace context
source_v2_db: /mnt/data/Muninn/reports/pilots/phase_d2_recall_reinforcement_2026-05-17/friday_phase_d2_shadow_v2.db
space_key: repo:f8cc7f64d3636a4e
project_path: /mnt/data/friday
retrieval_mode: hybrid
retrieval_backend: hybrid
degraded: true
degradation_reasons: sqlite_vec_unavailable_using_json_vector_fallback
budget: 7 selected (3 primary, 4 supplements), 1 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [7fcab1ba-2af2-498d-b712-d6c79520fd6e] Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 174.979313 rank: 1
  summary: Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
  body: Implemented direct-chat coder auto-routing in `backend/core/chat_engine.py` for inferred `code_execution` routes behind `FRIDAY_CODER_AUTO_ROUTE` (default on). Added bounded repo-local `read_repo_file` in `backend/tools/builtins.py`, allowed it under the existing read-only file-tool gate in `backend/tools/engine.py`, and added runtime prompt-path extraction plus automatic repo-context injection so prompts like `README.md` or `backend/core/chat_engine.py` can succeed even when the model does not request tools correctly. Updated `Dockerfile` to copy the repo working tree into `/app` so repo-l...
  evidence: /mnt/data/friday/backend/tools/engine.py:83; /mnt/data/friday/backend/tools/builtins.py:204; /mnt/data/friday/Dockerfile:18; /mnt/data/friday/backend/core/chat_engine.py:1311
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['code', 'context', 'direct', 'friday', 'only', 'read', 'repo', 'route']
- [ea8d2c51-9a13-4736-8b12-45c068c6a783] Friday bridge and tools now expose read-only /mnt/data workspace access
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 133.818545 rank: 2
  summary: Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
  body: FRIDAY_FILE_SEARCH_EXTRA_ROOTS is set to /mnt/data, friday-backend mounts /mnt/data read-only, inspect_repo_path can inspect files or directories across configured read-only roots, and case-insensitive path resolution allows host-style prompts like /mnt/data/Friday or /mnt/data/Althing to resolve safely without enabling writes.
  evidence: /mnt/data/friday/backend/tools/builtins.py; /mnt/data/friday/backend/api/althing_chat.py; /mnt/data/friday/backend/core/chat_engine.py; /mnt/data/friday/.env.example; /mnt/data/friday/docker-compose.app.yml
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['direct', 'friday', 'only', 'read', 'repo', 'workspace']
- [849362c5-ed42-43a2-9084-897ecf2c7de1] Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 110.56814 rank: 3
  summary: Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
  body: Mimir remains a repo cognition substrate, not runtime working memory. Added scripts/mimir_context.sh and Makefile targets (mimir-status, mimir-index, mimir-query, mimir-bundle). Documented boundary between WorkingScratchpad runtime cognition, durable conversational memory, and Mimir repo cognition.
  evidence: /mnt/data/friday/docs/ALTHING_WORKING_MEMORY_VS_MIMIR_BOUNDARY.md:1; /mnt/data/friday/Makefile:1; /mnt/data/friday/scripts/mimir_context.sh:1; /mnt/data/friday/docs/ALTHING_MIMIR_ROOT_DECISION.md:1
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['boundary', 'cognition', 'context', 'friday', 'mimir', 'repo']

CONTINUITY SUPPLEMENTS
- [6c7f8245-1952-4464-8998-79725736746e] Althing memory audit identifies bridge/direct split and missing private whiteboard
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 27.0 rank: None
  summary: Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
  body: Created ALTHING memory state audit, gap analysis, and next-step recommendation docs plus machine-readable summary. Key durable finding: Muninn and transcript memory are wired in direct /api/chat path, not in /api/althing/chat default UI flow; closest substrate for whiteboard is transient ExecutionState/intermediate and tool/refinement buffers.
  evidence: /mnt/data/friday/artifacts/althing_memory_state_summary.json:1; /mnt/data/friday/docs/ALTHING_MEMORY_NEXT_STEP_RECOMMENDATION.md:1; /mnt/data/friday/docs/ALTHING_MEMORY_GAP_ANALYSIS.md:1; /mnt/data/friday/docs/ALTHING_MEMORY_STATE_AUDIT.md:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['across', 'althing', 'bridge', 'chat', 'data', 'default', 'direct', 'durable', 'friday', 'memory', 'path', 'plus', 'runtime', 'substrate', 'tool', 'working']
- [ecc7842e-8058-4603-b3a0-633970ad4db5] V3 routing+prompt pass completed with targeted and full reruns
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 21.0 rank: None
  summary: The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
  body: Control-layer fixes in prompt_builder/interaction_policy/response_shaper/chat_engine plus runtime context prompt layers reduced routing and prompt-following failures on both targeted and full reruns. The canonical report and delta artifacts were finalized under evals/remediation for future comparison and planning.
  evidence: /mnt/data/friday/evals/remediation/remediation_pass_v3_routing_prompt_report.md; /mnt/data/friday/evals/remediation/routing_prompt_rerun_v3_delta.json; /mnt/data/friday/evals/remediation/combined_v2_to_v3_delta.json
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'primary_result_domain_tokens'] tokens=['chat', 'data', 'engine', 'friday', 'implemented', 'plus', 'prompt', 'routing', 'runtime', 'under']
- [f51f3e42-5ede-42fa-840c-c546c9562bb1] Friday chat runtime now uses adaptive lane-aware budgeting before LLM dispatch
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: The chat path now selects per-route lane budget profiles, trims context deterministically, applies task-aware output caps, and records budget intervention telemetry before sending model requests.
  body: Implemented in backend/core/chat_engine.py with lane keys (general/reasoning/retrieval/coding), 30B/7B scaling, trim order (history -> procedural overlay -> system memory -> excerpt shrink -> output reduction -> narrow fallback), and richer token_budget_applied events carrying lane/profile, token breakdown, trim actions, overflow_prevented, and fallback_mode_used.
  evidence: /mnt/data/friday/evals/remediation/remediation_pass_v2_adaptive_budgeting_report.md:1; /mnt/data/friday/tests/test_chat_budgeting.py:1; /mnt/data/friday/backend/core/chat_engine.py:1
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['backend', 'chat', 'core', 'data', 'engine', 'friday', 'implemented', 'memory', 'mode', 'model', 'path', 'route', 'runtime', 'selects', 'tests', 'used']
- [5ba9d678-421f-4264-bfed-249375da8adb] Friday remediation v1 validation artifacts and rerun IDs
  kind: runbook status: active stage: recent_in_scope_supplement reason: recent_query_primary_domain_overlap
  score: 14.5 rank: None
  summary: Remediation validation should include focused pytest coverage plus targeted gold and generated reruns recorded under dedicated run IDs and remediation reports.
  body: Use remediation report at evals/remediation/remediation_pass_v1_report.md and metrics snapshot at evals/remediation/remediation_pass_v1_metrics.json. Key reruns: remediation_targeted_v1e (12 gold tasks for routing/tool/prompt/repair slices) and remediation_runtime_smoke_v1 (18 generated variants on previously runtime-failing families).
  evidence: /mnt/data/friday/evals/remediation/remediation_pass_v1_metrics.json; /mnt/data/friday/evals/runs/remediation_targeted_v1e/run_results.jsonl; /mnt/data/friday/evals/runs/remediation_runtime_smoke_v1/run_results.jsonl; /mnt/data/friday/evals/remediation/remediation_pass_v1_report.md
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['data', 'friday', 'plus', 'prompt', 'routing', 'runtime', 'should', 'tool', 'under']

EVIDENCE
- [16e8f5e9-79f3-403b-b0e9-9f8895bce505] card=5ba9d678-421f-4264-bfed-249375da8adb type=file ref=/mnt/data/friday/evals/remediation/remediation_pass_v1_metrics.json
- [7589703e-6b26-41de-883b-2508bbf885ee] card=5ba9d678-421f-4264-bfed-249375da8adb type=file ref=/mnt/data/friday/evals/runs/remediation_targeted_v1e/run_results.jsonl
- [f0bcc443-9bb9-4541-9189-fd267518f0f6] card=5ba9d678-421f-4264-bfed-249375da8adb type=file ref=/mnt/data/friday/evals/runs/remediation_runtime_smoke_v1/run_results.jsonl
- [f97a9d55-9c5a-4aa0-a856-2bb2e885244d] card=5ba9d678-421f-4264-bfed-249375da8adb type=file ref=/mnt/data/friday/evals/remediation/remediation_pass_v1_report.md
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
- [5dc31385-9398-45e1-8b3f-3e8ed9b1f653] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/tools/builtins.py
- [726a558e-ab3c-4d2f-81bb-3c32cd8ea623] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/api/althing_chat.py
- [73535e7c-ca67-498b-8ff1-3488059b01b2] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/backend/core/chat_engine.py
- [b0909751-52ec-478f-8d48-3d396c051d4e] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/.env.example
- [c21d7a97-e41a-43fc-8273-b1462ee9f3a5] card=ea8d2c51-9a13-4736-8b12-45c068c6a783 type=file ref=/mnt/data/friday/docker-compose.app.yml
- [0e68e175-0e1c-4ecf-81a8-d28c7d4ca159] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/remediation_pass_v3_routing_prompt_report.md
- [4ee058af-5f23-494a-ac72-d91a135d7224] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/routing_prompt_rerun_v3_delta.json
- [cfbcc4b7-8ad4-40c7-9c8c-78938ec8369e] card=ecc7842e-8058-4603-b3a0-633970ad4db5 type=file ref=/mnt/data/friday/evals/remediation/combined_v2_to_v3_delta.json
- [60f0da01-86f7-4a36-8ffa-1fa12df4c855] card=f51f3e42-5ede-42fa-840c-c546c9562bb1 type=file ref=/mnt/data/friday/evals/remediation/remediation_pass_v2_adaptive_budgeting_report.md:1
- [c4e2e6a7-0c38-4a6f-991f-00c18241648d] card=f51f3e42-5ede-42fa-840c-c546c9562bb1 type=file ref=/mnt/data/friday/tests/test_chat_budgeting.py:1
- [dc32e9f2-c136-4232-87f5-8633cf8849d6] card=f51f3e42-5ede-42fa-840c-c546c9562bb1 type=file ref=/mnt/data/friday/backend/core/chat_engine.py:1

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
- 1 candidate cards were omitted by max_chars budget.

AGENT BRIEFING
- Primary match: Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end - Friday direct chat now auto-selects the coder transport for inferred code-execution prompts and can recover repo-local context from explicit file-path prompts without enabling the broader tool plane. The backend image now carries the repo working tree into `/app`, so read-only repo file access works in the live container as well as in tests.
- Primary match: Friday bridge and tools now expose read-only /mnt/data workspace access - Friday direct chat can now inspect read-only workspace paths under /mnt/data, and Althing-mode UI prompts that reference local paths fall back to that direct Friday path instead of staying on Althing-only lanes.
- Primary match: Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory - Confirmed Mimir should be used at Friday root for developer/agent navigation and added script/Makefile entrypoints for status/index/query/bundle without creating runtime coupling.
- Continuity: Althing memory audit identifies bridge/direct split and missing private whiteboard - Audited Friday and adjacent Althing runtime memory behavior. Direct Friday has transcript plus provider-backed memory, while default Althing bridge flow is effectively stateless across turns unless clients send messages. No first-class private working scratchpad exists.
- Continuity: V3 routing+prompt pass completed with targeted and full reruns - The v3 pass implemented narrow routing and prompt-contract refinements, produced a targeted rerun manifest from v2 fail/borderline routing+prompt records, and completed both targeted and full reruns with delta artifacts.
- Continuity: Friday chat runtime now uses adaptive lane-aware budgeting before LLM dispatch - The chat path now selects per-route lane budget profiles, trims context deterministically, applies task-aware output caps, and records budget intervention telemetry before sending model requests.
- Continuity: Friday remediation v1 validation artifacts and rerun IDs - Remediation validation should include focused pytest coverage plus targeted gold and generated reruns recorded under dedicated run IDs and remediation reports.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
