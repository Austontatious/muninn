BEGIN MUNINN V2 AGENT CONTEXT
schema_version: muninn.v2.rehydrate_response.v1
contract_version: 1.0.0
response_kind: shadow_rehydrate_preview
task: resume SubSim current ReadyPlayer1 campaign integration state and next steps
source_v2_db: reports/pilots/subsim_v2_shadow_2026-05-17/subsim_shadow_v2.db
space_key: repo:363c13a65e92ef58
project_path: None
retrieval_mode: hybrid
retrieval_backend: hybrid
degraded: true
degradation_reasons: sqlite_vec_unavailable_using_json_vector_fallback
budget: 8 selected (3 primary, 5 supplements), 0 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [8d0704f3-2903-44df-937c-c80902b20f64] SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 83.980211 rank: 1
  summary: Both repos now carry PROJECT_MEMORY campaign ledgers through Campaign 003 with Campaign 004A recommended next.
  body: The checkpoint records Preflight, Campaign 001, Campaign 002A, and Campaign 003 as promoted. Current trusted metrics include SubSim full suite 58 passed, ReadyPlayer1 focused SubSim and golden tests 28 passed, scenario suite 7 pass / 0 fail, golden regression pass, and Campaign 003 clutter binding improvement sonar_clutter_wrong_binding_rate 0.2 -> 0.0. Recommended next campaign is 004A torpedo / fire-control feedback loop.
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md; /mnt/data/subsim/PROJECT_MEMORY.md; /mnt/data/ReadyPlayer1/PROJECT_MEMORY.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'current', 'next', 'readyplayer1', 'subsim']
- [f94af521-4f75-4f42-b9d6-8a10b66d4a0d] SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy
  kind: interface status: active stage: primary_retrieval reason: query_match
  score: 75.131649 rank: 2
  summary: Campaign 004A did not change SubSim gameplay, torpedo physics, sonar producer code, or scenario expectations. It records that ReadyPlayer1 now suppresses duplicate same-primary torpedo commits and exposes fire-control metrics against existing SubSim replay evidence.
  body: Trusted post-campaign state: SubSim full tests passed with 65 tests, scenario suite stayed 7 pass / 0 fail, and clutter_false_positive sonar metrics were preserved. Remaining SubSim-side interface risk is that live FireControl state exists but is not yet normalized into ReadyPlayer1 sonar replay/live observations; Campaign 005A should expose solution lifecycle and post-shot feedback without changing torpedo physics.
  evidence: /mnt/data/subsim/PROJECT_MEMORY.md; /mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json; /mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state', 'subsim']
- [b97c8e3f-2a41-4031-946f-2f57b87f2bc2] SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 75.114139 rank: 3
  summary: SubSim now has local project state, evaluation contract, ship targets, campaign plan, and reports for the bounded ReadyPlayer1 evaluation loop. Campaign 001 is sonar contact readability under clutter, anchored by ReadyPlayer1 before metrics for clutter_false_positive.
  body: No gameplay changes were made during preflight. SubSim full tests passed and deterministic seed 7 trace export succeeded after creating reports/. Promotion remains hold until after metrics exist; status is READY_FOR_CAMPAIGN_001_IMPLEMENTATION.
  evidence: /mnt/data/subsim/SUBSIM_PROJECT_STATE.md; /mnt/data/subsim/docs/CAMPAIGN_001_PLAN.md; /mnt/data/subsim/reports/preflight_subsim_skirmish_seed7_trace.json; /mnt/data/subsim/reports/evaluation_contract_status.json
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state', 'subsim']

CONTINUITY SUPPLEMENTS
- [2fbc9cf8-118c-4a0d-84bc-a5ee90716adb] SubSim fire_control observation contract v1
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 31.5 rank: None
  summary: SubSim exposes fire-control readiness and solution-state data through build_observation and sonar-console frames for ReadyPlayer1 Campaign 005A.
  body: The fire_control block includes fire_control_ready, fire_control_solution_state, fire_control_solution_quality, weapon_ready, valid_fire_opportunity, hold reason, target id, solution timing, and active_torpedo_count. This is producer/adapter visibility only; torpedo physics and firing timing were not changed.
  evidence: /mnt/data/subsim/subsim/game.py; /mnt/data/subsim/subsim/testing/sonar_console/contracts.py; /mnt/data/subsim/subsim/testing/sonar_console/console.py; /mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['005a', 'campaign', 'contract', 'control', 'exposes', 'fire', 'hold', 'physics', 'producer', 'ready', 'readyplayer1', 'reports', 'solution', 'sonar', 'subsim', 'through', 'torpedo', 'were']
- [66312a31-2eca-4931-8f28-ae75a2dc7411] Campaign 004A leaves SubSim fire-control physics unchanged
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 26.5 rank: None
  summary: Campaign 004A was a ReadyPlayer1 policy/evaluator improvement and did not change SubSim torpedo physics, damage, range, sonar producer behavior, or scenario expectations. SubSim remains the protected producer surface for future fire-control state normalization.
  body: The next recommended slice is to normalize SubSim live FireControl solution state into sonar replay/live observations so ReadyPlayer1 can distinguish solution_start, ready, fired, miss, and reacquisition feedback without approximating entirely from policy memory.
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md; /mnt/data/subsim/subsim/game.py; /mnt/data/subsim/subsim/engine/weapons.py; /mnt/data/subsim/PROJECT_MEMORY.md
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['004a', 'campaign', 'change', 'control', 'expectations', 'feedback', 'fire', 'firecontrol', 'improvement', 'live', 'memory', 'next', 'observations', 'physics', 'policy', 'producer', 'promotion', 'ready', 'readyplayer1', 'recommended', 'remains', 'replay', 'reports', 'scenario', 'solution', 'sonar', 'subsim', 'torpedo', 'without']
- [4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9] Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 23.5 rank: None
  summary: SubSim hydrophone artifacts under data/hydrophone/fixtures and data/hydrophone/manifests/splits are the fixed inputs for ReadyPlayer1 Campaign 003 acoustic clutter-binding evaluation. Promotion scoring defaults to heldout_source_eval and excludes synthetic cases unless explicitly requested.
  body: The fixture export commands were rerun successfully for 78 cases/fixtures after fixed splits were rebuilt with seed 1337. Runtime policy decisions should still use contact evidence, confidence, lifecycle, ambiguity, and binding quality rather than fixture labels as direct truth.
  evidence: /mnt/data/subsim/data/hydrophone/manifests/splits/; /mnt/data/subsim/data/hydrophone/fixtures/subsim_acoustic_contacts.jsonl; /mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['after', 'binding', 'campaign', 'clutter', 'contact', 'evaluation', 'evidence', 'export', 'lifecycle', 'policy', 'promotion', 'readyplayer1', 'seed', 'should', 'subsim', 'under', 'were']
- [5e260af6-8b17-427f-832d-028fae69d295] Hydrophone fixed eval and acoustic fixtures
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 16.25 rank: None
  summary: SubSim hydrophone now has deterministic group-safe fixed splits and real-only gameplay/eval fixture exports.
  body: The fixed eval slice writes data/hydrophone/manifests/splits/{train,validation,heldout_source_eval}.jsonl plus split_summary.json, updates classifier training to use those manifests with separate validation and heldout-source metrics, and exports SubSim/ReadyPlayer1 acoustic fixture JSONL under data/hydrophone/fixtures. Synthetic fixtures remain excluded by default and require explicit include flags.
  evidence: /mnt/data/subsim/data/hydrophone/manifests/splits/split_summary.json; /mnt/data/subsim/scripts/hydrophone/train_hydrophone_classifier.py; /mnt/data/subsim/scripts/hydrophone/build_fixed_eval_splits.py; /mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['deterministic', 'gameplay', 'include', 'metrics', 'readyplayer1', 'subsim', 'under']
- [fb91d94b-b9e2-4bd8-a970-ff315747cd2d] SubSim sonar tracks expose explicit lifecycle state
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 27.0 rank: None
  summary: Campaign 002A extended the SubSim sonar-console PerceivedTrack contract with lifecycle_state and emits possible/suspect/tracking/confirmed/rejected/lost from perception. This is a producer-side readability signal, not a confidence threshold change.
  body: SubSim PerceptionEngine now computes lifecycle_state after ambiguity flags and contact_quality. Weak passive-only clutter reaches rejected, active ping or strong evidence reaches confirmed, and older confidence/clutter rejection behavior from Campaign 001 is preserved.
  evidence: /mnt/data/subsim/subsim/testing/sonar_console/perception.py; /mnt/data/subsim/subsim/testing/sonar_console/tests/test_perception.py; /mnt/data/subsim/subsim/testing/sonar_console/contracts.py
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['002a', 'after', 'campaign', 'change', 'clutter', 'contact', 'contract', 'evidence', 'expose', 'lifecycle', 'preserved', 'producer', 'readability', 'side', 'sonar', 'subsim', 'tests']

EVIDENCE
- [08aee04d-43f5-4dc4-8751-41f5551df312] card=2fbc9cf8-118c-4a0d-84bc-a5ee90716adb type=file ref=/mnt/data/subsim/subsim/game.py
- [4b01c177-fbbc-4629-b8c1-fd15b903c41c] card=2fbc9cf8-118c-4a0d-84bc-a5ee90716adb type=file ref=/mnt/data/subsim/subsim/testing/sonar_console/contracts.py
- [6671a4fe-7674-45d8-8bb0-5866f25385fb] card=2fbc9cf8-118c-4a0d-84bc-a5ee90716adb type=file ref=/mnt/data/subsim/subsim/testing/sonar_console/console.py
- [f15f3f04-2031-465c-b2f6-d728d83e2be4] card=2fbc9cf8-118c-4a0d-84bc-a5ee90716adb type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json
- [1e341037-f8e8-4c77-be3d-95379bdc4357] card=4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9 type=file ref=/mnt/data/subsim/data/hydrophone/manifests/splits/
- [62e8bde9-1366-4551-b69a-12d4ba542b7f] card=4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9 type=file ref=/mnt/data/subsim/data/hydrophone/fixtures/subsim_acoustic_contacts.jsonl
- [7f3e9069-051c-4c6c-8b9a-1bcefbdacc75] card=4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9 type=file ref=/mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl
- [2f2855d2-91bb-4c09-bef6-f3b6e4120a79] card=5e260af6-8b17-427f-832d-028fae69d295 type=file ref=/mnt/data/subsim/data/hydrophone/manifests/splits/split_summary.json
- [4c712e01-2c9a-4caa-87b6-12e85abd0f54] card=5e260af6-8b17-427f-832d-028fae69d295 type=file ref=/mnt/data/subsim/scripts/hydrophone/train_hydrophone_classifier.py
- [7d21534f-a66c-47d5-8b59-019861e42d36] card=5e260af6-8b17-427f-832d-028fae69d295 type=file ref=/mnt/data/subsim/scripts/hydrophone/build_fixed_eval_splits.py
- [cc83acdd-735c-48f6-b364-8ef48ee6374d] card=5e260af6-8b17-427f-832d-028fae69d295 type=file ref=/mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl
- [59b312c3-4af9-45a6-a340-6c96804b290a] card=66312a31-2eca-4931-8f28-ae75a2dc7411 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
- [94ff25ce-e03b-48da-8f8a-048c47704986] card=66312a31-2eca-4931-8f28-ae75a2dc7411 type=file ref=/mnt/data/subsim/subsim/game.py
- [b41f7a4f-48f8-48d4-8c01-9805f30d2f4b] card=66312a31-2eca-4931-8f28-ae75a2dc7411 type=file ref=/mnt/data/subsim/subsim/engine/weapons.py
- [db8ab317-46c8-4a4a-ba3a-4478266a6df8] card=66312a31-2eca-4931-8f28-ae75a2dc7411 type=file ref=/mnt/data/subsim/PROJECT_MEMORY.md
- [6ecbc012-2e3e-4e79-b01c-2ba883b9a180] card=8d0704f3-2903-44df-937c-c80902b20f64 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md
- [9c83e055-b1f6-442c-9b33-64db023b8a77] card=8d0704f3-2903-44df-937c-c80902b20f64 type=file ref=/mnt/data/subsim/PROJECT_MEMORY.md
- [d4dc70e3-e4be-4195-9db4-c22c0d92b1b1] card=8d0704f3-2903-44df-937c-c80902b20f64 type=file ref=/mnt/data/ReadyPlayer1/PROJECT_MEMORY.md
- [34240428-d020-473a-9cbe-4e26824077ec] card=b97c8e3f-2a41-4031-946f-2f57b87f2bc2 type=file ref=/mnt/data/subsim/SUBSIM_PROJECT_STATE.md
- [3b881561-172b-4407-9267-e2b1ef940e43] card=b97c8e3f-2a41-4031-946f-2f57b87f2bc2 type=file ref=/mnt/data/subsim/docs/CAMPAIGN_001_PLAN.md
- [cf586115-64a2-48bc-a8be-ab6a1ceb35fb] card=b97c8e3f-2a41-4031-946f-2f57b87f2bc2 type=file ref=/mnt/data/subsim/reports/preflight_subsim_skirmish_seed7_trace.json
- [e1853d73-092a-4b6d-9772-1e47fcfd9c7e] card=b97c8e3f-2a41-4031-946f-2f57b87f2bc2 type=file ref=/mnt/data/subsim/reports/evaluation_contract_status.json
- [7a89aa8e-bc98-4a5d-8c06-5faba52d706f] card=f94af521-4f75-4f42-b9d6-8a10b66d4a0d type=file ref=/mnt/data/subsim/PROJECT_MEMORY.md
- [a6e1b720-f91d-4c16-bba1-283ef73889f1] card=f94af521-4f75-4f42-b9d6-8a10b66d4a0d type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json
- [d551cf7c-47fb-4f7c-a7ec-ad627466cecb] card=f94af521-4f75-4f42-b9d6-8a10b66d4a0d type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
- [238ab039-897a-450c-b40e-aa87a5d19efe] card=fb91d94b-b9e2-4bd8-a970-ff315747cd2d type=file ref=/mnt/data/subsim/subsim/testing/sonar_console/perception.py
- [a3dcf534-a197-42c5-bd0c-f8b69e3524d6] card=fb91d94b-b9e2-4bd8-a970-ff315747cd2d type=file ref=/mnt/data/subsim/subsim/testing/sonar_console/tests/test_perception.py
- [c33a569f-5d05-4971-9bc3-32cbc3c0f308] card=fb91d94b-b9e2-4bd8-a970-ff315747cd2d type=file ref=/mnt/data/subsim/subsim/testing/sonar_console/contracts.py

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

AGENT BRIEFING
- Primary match: SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003 - Both repos now carry PROJECT_MEMORY campaign ledgers through Campaign 003 with Campaign 004A recommended next.
- Primary match: SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy - Campaign 004A did not change SubSim gameplay, torpedo physics, sonar producer code, or scenario expectations. It records that ReadyPlayer1 now suppresses duplicate same-primary torpedo commits and exposes fire-control metrics against existing SubSim replay evidence.
- Primary match: SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected - SubSim now has local project state, evaluation contract, ship targets, campaign plan, and reports for the bounded ReadyPlayer1 evaluation loop. Campaign 001 is sonar contact readability under clutter, anchored by ReadyPlayer1 before metrics for clutter_false_positive.
- Continuity: SubSim fire_control observation contract v1 - SubSim exposes fire-control readiness and solution-state data through build_observation and sonar-console frames for ReadyPlayer1 Campaign 005A.
- Continuity: Campaign 004A leaves SubSim fire-control physics unchanged - Campaign 004A was a ReadyPlayer1 policy/evaluator improvement and did not change SubSim torpedo physics, damage, range, sonar producer behavior, or scenario expectations. SubSim remains the protected producer surface for future fire-control state normalization.
- Continuity: Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring - SubSim hydrophone artifacts under data/hydrophone/fixtures and data/hydrophone/manifests/splits are the fixed inputs for ReadyPlayer1 Campaign 003 acoustic clutter-binding evaluation. Promotion scoring defaults to heldout_source_eval and excludes synthetic cases unless explicitly requested.
- Continuity: Hydrophone fixed eval and acoustic fixtures - SubSim hydrophone now has deterministic group-safe fixed splits and real-only gameplay/eval fixture exports.
- Continuity: SubSim sonar tracks expose explicit lifecycle state - Campaign 002A extended the SubSim sonar-console PerceivedTrack contract with lifecycle_state and emits possible/suspect/tracking/confirmed/rejected/lost from perception. This is a producer-side readability signal, not a confidence threshold change.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
