BEGIN MUNINN V2 AGENT CONTEXT
schema_version: muninn.v2.rehydrate_response.v1
contract_version: 1.0.0
response_kind: shadow_rehydrate_preview
task: resume ReadyPlayer1 current campaign state and next steps
source_v2_db: /mnt/data/Muninn/reports/pilots/phase_d2_recall_reinforcement_2026-05-17/readyplayer1_phase_d2_shadow_v2.db
space_key: repo:5059f410815720ea
project_path: /mnt/data/ReadyPlayer1
retrieval_mode: hybrid
retrieval_backend: hybrid
degraded: true
degradation_reasons: sqlite_vec_unavailable_using_json_vector_fallback
budget: 9 selected (3 primary, 6 supplements), 0 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [eed995dd-60bf-4bd6-b678-9541501d5b5d] Phase 2 canonical current-state pointers and onboarding source consolidation
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 97.835261 rank: 1
  summary: Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
  body: Implemented canonical pointer surfaces runs/current/lane_current_state_index.json and runs/current/<lane_id>/lane_current_state.json and synced them from lane registry updates. Canonicalized lane registry onboarding semantics to keep onboarding_config_json/onboarding_template_json as current bootstrap source and preserve historical onboarding run snapshots in latest_onboarding_run_config_json/latest_onboarding_run_summary_json. Updated README, RUNBOOK, and ARCHITECTURE_CHECKPOINT to align operator default flow with the new current-state pointer strategy; added docs/tasks/repo_drift_phase2_e...
  evidence: /mnt/data/ReadyPlayer1/ARCHITECTURE_CHECKPOINT.md; /mnt/data/ReadyPlayer1/readyplayer1/cli.py; /mnt/data/ReadyPlayer1/RUNBOOK.md; /mnt/data/ReadyPlayer1/README.md; /mnt/data/ReadyPlayer1/docs/tasks/repo_drift_phase2_execution_summary.json
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'reinforcement_state', 'summary', 'title', 'vector'] tokens=['current', 'readyplayer1', 'state']
- [bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44] Campaign 005A promoted fire-control state normalization
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 95.571653 rank: 2
  summary: Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
  body: SubSim now emits structured fire_control observation fields and sonar-console frames carry them. ReadyPlayer1 normalizes producer fire-control state and infer-compatible replay state, adds coverage metrics, and preserved Campaign 004A fire-control behavior plus sonar/acoustic gates. Final status CAMPAIGN_005A_PROMOTED.
  evidence: /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py; /mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json; /mnt/data/ReadyPlayer1/readyplayer1/harness/subsim/sonar_adapter.py; /mnt/data/ReadyPlayer1/reports/campaign_005a_promotion_decision.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'reinforcement_state', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state']
- [1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0] Campaign 004A promoted with ReadyPlayer1 fire-control loop patch
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 86.692444 rank: 3
  summary: Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
  body: Evidence: clean_single_contact_tracking under seed 7 moved torpedo_count 2 -> 1, torpedo_duplicate_same_track_count 1 -> 0, and torpedo_wasted_shot_rate 0.5 -> 0.0. clutter_false_positive preservation metrics stayed unchanged, scenario suite remained 7 pass / 0 fail, golden regression passed, SubSim full tests passed, and ReadyPlayer1 focused SubSim tests passed. Next recommended campaign is Campaign 005A: normalize SubSim fire-control readiness/solution state into ReadyPlayer1 observations and replay traces.
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json; /mnt/data/ReadyPlayer1/PROJECT_MEMORY.md; /mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'reinforcement_state', 'summary', 'title', 'vector'] tokens=['campaign', 'next', 'readyplayer1', 'state']

CONTINUITY SUPPLEMENTS
- [0afb7524-b5b6-4e78-9a56-a08915eb895e] Campaign 007A promoted post-reacquisition stabilization
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: Campaign 007A promoted a bounded ReadyPlayer1 policy and metrics change for post-reacquisition belief stabilization. The belief_baseline now tracks recovery probe outcomes and briefly stabilizes a compatible recovered previous primary while preserving torpedo, sonar clutter, acoustic clutter, scenario, and golden gates.
  body: Campaign 007A made no SubSim gameplay or torpedo physics changes. ReadyPlayer1 belief_baseline now records guarded recovery probe state, stabilizes compatible recovered previous-primary evidence for a short window, and delays no-evidence stale cleanup to avoid clearing one frame before delayed recovery evidence appears. high_self_noise_degradation post_reacquisition_policy_stabilized_rate moved from 0.0 to 1.0 with sonar_action_thrash preserved at 5, previous_primary_recovered_rate preserved at 1.0, and post_reacquisition_clutter_rebind_rate preserved at 0.0. reacquisition_challenge_no_reco...
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_007a_promotion_decision.md; /mnt/data/ReadyPlayer1/reports/campaign_007a_comparison.json; /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py; /mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['acoustic', 'after', 'baseline', 'belief', 'bounded', 'campaign', 'change', 'clutter', 'compatible', 'contact', 'count', 'decision', 'drift', 'duplicate', 'emits', 'evidence', 'fail', 'gates', 'golden', 'json', 'metrics', 'moved', 'pass', 'passed', 'policy', 'preserved', 'preserving', 'primary', 'promoted', 'rate', 'readyplayer1', 'regression', 'replay', 'same', 'scenario', 'shot', 'sonar', 'stale', 'stayed', 'subsim', 'suite', 'torpedo', 'track', 'wasted', 'while']
- [fbcac688-f952-477f-87ca-ea7860c4f396] Campaign 006A promoted post-loss recovery probe
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: Campaign 006A promoted a bounded ReadyPlayer1 policy and metrics change for post-shot/post-loss reacquisition. The belief_baseline now performs an evidence-gated early active ping for credible lost tracks, improving post-loss probe behavior while preserving duplicate-shot, wasted-shot, sonar clutter, and acoustic clutter gates.
  body: Campaign 006A made no SubSim torpedo physics changes. ReadyPlayer1 belief_baseline uses normalized Campaign 005A fire-control/contact state to allow earlier reacquire pings only for credible lost/recoverable tracks, while rejecting clutter-like/high-risk contacts. Metrics now report post-loss reacquisition attempt/ping/success, clutter rebind, belief drift after loss, and valid-fire ready-but-hold rate. Scenario suite stayed 7 pass / 0 fail, golden regression passed, acoustic heldout clutter wrong binding stayed 0.0, sonar_clutter_wrong_binding_rate stayed 0.0, torpedo_duplicate_same_track_...
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_006a_comparison.json; /mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py; /mnt/data/ReadyPlayer1/reports/campaign_006a_promotion_decision.md; /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['005a', 'acoustic', 'after', 'baseline', 'behavior', 'belief', 'bounded', 'campaign', 'change', 'clutter', 'contact', 'control', 'count', 'decision', 'drift', 'duplicate', 'evidence', 'fail', 'fire', 'gates', 'golden', 'json', 'metrics', 'pass', 'passed', 'policy', 'preserving', 'promoted', 'rate', 'readyplayer1', 'regression', 'remained', 'replay', 'same', 'scenario', 'shot', 'sonar', 'stayed', 'subsim', 'suite', 'torpedo', 'track', 'wasted', 'while']
- [719fafb5-b25b-4460-a549-987799432a6c] Campaign 004A fire-control loop promoted
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: Campaign 004A is promoted. ReadyPlayer1 belief_baseline now exposes fire-control decision rationale and suppresses duplicate same-primary torpedo commits, moving clean_single_contact_tracking torpedo_count from 2 to 1 and torpedo_wasted_shot_rate from 0.5 to 0.0 while preserving sonar and acoustic clutter gates.
  body: The refreshed Campaign 004A evidence uses suite run 20260507T163754Z-subsim_suite-bd3e2a and heldout acoustic regression scoring. Scenario suite remains 7 pass / 0 fail with regression pass; acoustic_clutter_wrong_binding_rate remains 0.0; SubSim full tests passed 65; ReadyPlayer1 full tests passed with one skipped marker. Remaining risks are not hidden: timidity_indecision, belief_drift, and reacquisition_failure remain, and SubSim fire-control state is not yet normalized into replay observations.
  evidence: /mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py; /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py; /mnt/data/ReadyPlayer1/reports/campaign_004a_after_runs/acoustic_regression/campaign_004a_acoustic_regression_summary.json; /mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json; /mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['004a', 'acoustic', 'after', 'baseline', 'belief', 'campaign', 'clean', 'clutter', 'commits', 'contact', 'control', 'count', 'decision', 'drift', 'duplicate', 'evidence', 'fail', 'fire', 'full', 'gates', 'json', 'loop', 'metrics', 'observations', 'pass', 'passed', 'preserving', 'primary', 'promoted', 'rate', 'rationale', 'readyplayer1', 'regression', 'replay', 'runs', 'same', 'scenario', 'shot', 'single', 'sonar', 'subsim', 'suite', 'summary', 'suppresses', 'tests', 'torpedo', 'tracking', 'wasted', 'while']
- [8db59c21-0224-4ef0-b628-f336867bf591] Campaign 003 acoustic clutter binding integrated
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: ReadyPlayer1 now loads SubSim hydrophone acoustic eval cases, scores heldout-source acoustic clutter binding by default, and blocks rejected/high-risk clutter tracks from the reacquire-primary fallback. Heldout acoustic clutter wrong binding moved from 1.0 to 0.0 while surface-contact missed-track stayed 0.0.
  body: Durable evidence lives under reports/campaign_003_acoustic_clutter. The implementation adds acoustic case loading, acoustic clutter metrics, a subsim acoustic-clutter CLI/suite entry point, focused tests, and a bounded BeliefBaseline primary reacquire guard that does not use fixture labels at runtime.
  evidence: /mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_cases.py; /mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_promotion_decision.md; /mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_comparison.json; /mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py; /mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_clutter_metrics.py
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['acoustic', 'adds', 'baseline', 'belief', 'bounded', 'campaign', 'clutter', 'contact', 'decision', 'default', 'evidence', 'focused', 'json', 'metrics', 'moved', 'primary', 'readyplayer1', 'source', 'stayed', 'subsim', 'suite', 'tests', 'track', 'under', 'while']
- [2656c35f-79af-403d-9128-e98fc72663d6] Campaign 003 promoted for SubSim clutter binding
  kind: decision status: active stage: recent_in_scope_supplement reason: recent_query_token_overlap
  score: 19.0 rank: None
  summary: Campaign 003 promoted after ReadyPlayer1 primary-track candidate semantics reduced clutter primary binding without hiding raw false positives.
  body: ReadyPlayer1 now emits/uses primary_candidate and binding_candidate_score for SubSim sonar tracks. The belief_baseline lane defers primary selection when multiple weak possible contacts compete, while raw clutter confidence remains visible through sonar_clutter_raw_confidence_wrong_binding_rate. Target clutter_false_positive metrics moved sonar_clutter_wrong_binding_rate 0.2 -> 0.0 and sonar_action_thrash 4 -> 2 with scenario suite 7 pass / 0 fail and golden regression pass.
  evidence: /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py; /mnt/data/ReadyPlayer1/reports/campaign_003_comparison.json; /mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md; /mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['after', 'baseline', 'belief', 'campaign', 'clutter', 'decision', 'emits', 'fail', 'false', 'golden', 'json', 'lane', 'metrics', 'moved', 'pass', 'positive', 'primary', 'promoted', 'rate', 'readyplayer1', 'regression', 'scenario', 'semantics', 'sonar', 'subsim', 'suite', 'track', 'while']
- [fb80c2a4-3025-4a64-bd60-3cbf7484b2d2] SubSim ReadyPlayer1 evaluation contract v1 documented
  kind: interface status: active stage: recent_in_scope_supplement reason: recent_project_boundary_or_contract
  score: 27.0 rank: None
  summary: ReadyPlayer1 now carries the SubSim closed-loop evaluation contract and preflight status reports for Campaign 001. The contract records scenario id, seed, SubSim and ReadyPlayer1 commits, evaluator lane, metrics, replay/run artifacts, failure taxonomy, and promotion decision.
  body: Baseline, belief baseline, belief-state variant, and shadow lanes are documented. Learned or shadow lanes are advisory only and cannot be the sole promotion signal. Full seed 7 belief_baseline suite passed golden regression with one scenario expectation failure on clutter_false_positive.
  evidence: /mnt/data/ReadyPlayer1/READYPLAYER1_PROJECT_STATE.md; /mnt/data/ReadyPlayer1/docs/EVALUATION_CONTRACT.md; /mnt/data/ReadyPlayer1/reports/campaign_001_runs/20260507T143115Z-subsim_suite-677aa9/suite_summary.json; /mnt/data/ReadyPlayer1/reports/campaign_001_preflight.md
  explanation: path=recent_in_scope_shadow_supplement sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['artifacts', 'baseline', 'belief', 'campaign', 'clutter', 'commits', 'decision', 'docs', 'false', 'full', 'golden', 'json', 'lane', 'loop', 'metrics', 'passed', 'positive', 'readyplayer1', 'regression', 'replay', 'runs', 'scenario', 'seed', 'status', 'subsim', 'suite', 'summary']

EVIDENCE
- [05f3edf1-a1c7-4dde-9541-ae3a37e58cc6] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_007a_promotion_decision.md
- [324ae219-9e11-4a8f-b12e-a9d37798ab4d] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_007a_comparison.json
- [84a71d72-829d-4bf1-8214-c145269df127] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
- [e23a9e93-988f-4f92-9b83-a8b4b8849eab] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [194d9ef0-d37a-48ad-be7b-e35318f9f759] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json
- [7a30fa16-62a4-4b8a-a839-567f9d4435ae] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/PROJECT_MEMORY.md
- [7a35b654-0edc-4f34-989b-207490e27765] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
- [0d4a9ac0-7d8e-4ea6-a391-0207b11bd03e] card=2656c35f-79af-403d-9128-e98fc72663d6 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
- [96b63a0c-27e3-495e-a575-f8eff5054419] card=2656c35f-79af-403d-9128-e98fc72663d6 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_003_comparison.json
- [b9e368c7-7d7b-4b40-b167-98e828055ecd] card=2656c35f-79af-403d-9128-e98fc72663d6 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md
- [bc8adbca-fba1-4303-b129-ced1e85481aa] card=2656c35f-79af-403d-9128-e98fc72663d6 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [2b020d6e-b554-456d-bb7f-6e5763dc027b] card=719fafb5-b25b-4460-a549-987799432a6c type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [3654a416-d532-47f0-b355-a260bcbbf15d] card=719fafb5-b25b-4460-a549-987799432a6c type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
- [84e5853a-d1cd-43b4-92b3-b734276eefef] card=719fafb5-b25b-4460-a549-987799432a6c type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_after_runs/acoustic_regression/campaign_004a_acoustic_regression_summary.json
- [9054e34c-fe1f-4433-ab4d-156982bc6ef8] card=719fafb5-b25b-4460-a549-987799432a6c type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json
- [c93fb229-53d3-479d-8e21-a6a457a66872] card=719fafb5-b25b-4460-a549-987799432a6c type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
- [3938b649-3454-45e1-a2a2-066e4ba574fb] card=8db59c21-0224-4ef0-b628-f336867bf591 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_cases.py
- [823c5a29-9f0d-4d30-8b05-3044d18ed349] card=8db59c21-0224-4ef0-b628-f336867bf591 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_promotion_decision.md
- [853f3e0d-2f75-4704-9bb4-b06f1ca84af2] card=8db59c21-0224-4ef0-b628-f336867bf591 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_comparison.json
- [929e312a-c6c1-4f21-8cab-e3b524261da6] card=8db59c21-0224-4ef0-b628-f336867bf591 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [b2dc5f64-851a-417a-845f-10b66e63d92c] card=8db59c21-0224-4ef0-b628-f336867bf591 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_clutter_metrics.py
- [49016b7e-4d7c-4658-a76f-bee5e6c6d451] card=bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
- [5064aa40-d2bd-4526-bda9-44c002294d5d] card=bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json
- [b3dae469-81a5-42c8-a708-76a2bda3eee8] card=bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/harness/subsim/sonar_adapter.py
- [bc04fe78-5f79-43b2-9d01-e63ef7a4b4af] card=bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_005a_promotion_decision.md
- [1c36999b-a698-4e10-b478-6f336cfbe911] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/ARCHITECTURE_CHECKPOINT.md
- [2a974af6-f904-4cf6-a9dc-fa91c159a5f4] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/cli.py
- [3fa9a3a7-f042-4222-8b12-6215610a05ab] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/RUNBOOK.md
- [41256fa3-78ce-4dd4-8ca8-5e6e0572f10b] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/README.md
- [4da2f574-d688-4340-8071-b56975dc224c] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/docs/tasks/repo_drift_phase2_execution_summary.json
- [bf4173ec-f4b8-4f13-af0b-991245f7a20b] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/tests/test_subsim_lane_ops.py
- [d838aa3d-4717-4310-ab64-fda463dfdcb5] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/rl/lane_ops.py
- [e7198c14-20ab-4a26-a266-addfc6f71905] card=eed995dd-60bf-4bd6-b678-9541501d5b5d type=file ref=/mnt/data/ReadyPlayer1/docs/tasks/repo_drift_phase2_execution_summary.md
- [1f0a7b70-8673-4899-bf7e-c86e83ebc95d] card=fb80c2a4-3025-4a64-bd60-3cbf7484b2d2 type=file ref=/mnt/data/ReadyPlayer1/READYPLAYER1_PROJECT_STATE.md
- [242df097-0eae-435f-a378-d27ae2111ea0] card=fb80c2a4-3025-4a64-bd60-3cbf7484b2d2 type=file ref=/mnt/data/ReadyPlayer1/docs/EVALUATION_CONTRACT.md
- [a1af383c-21fa-48ac-8713-ed122d68869a] card=fb80c2a4-3025-4a64-bd60-3cbf7484b2d2 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_001_runs/20260507T143115Z-subsim_suite-677aa9/suite_summary.json
- [b6b51043-c0b7-4721-b28a-7d0de67157a8] card=fb80c2a4-3025-4a64-bd60-3cbf7484b2d2 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_001_preflight.md
- [074bd4f9-d2d4-4ae3-a7ee-075585bbf3eb] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_006a_comparison.json
- [21f79e08-e73f-449d-b074-ecc10c1e69af] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [b632f863-7ee8-4bd5-94b4-c4ef75b2c9fa] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_006a_promotion_decision.md
- [f5a27605-9617-4229-b771-ac1b93b6e0ab] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

AGENT BRIEFING
- Primary match: Phase 2 canonical current-state pointers and onboarding source consolidation - Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
- Primary match: Campaign 005A promoted fire-control state normalization - Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
- Primary match: Campaign 004A promoted with ReadyPlayer1 fire-control loop patch - Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
- Continuity: Campaign 007A promoted post-reacquisition stabilization - Campaign 007A promoted a bounded ReadyPlayer1 policy and metrics change for post-reacquisition belief stabilization. The belief_baseline now tracks recovery probe outcomes and briefly stabilizes a compatible recovered previous primary while preserving torpedo, sonar clutter, acoustic clutter, scenario, and golden gates.
- Continuity: Campaign 006A promoted post-loss recovery probe - Campaign 006A promoted a bounded ReadyPlayer1 policy and metrics change for post-shot/post-loss reacquisition. The belief_baseline now performs an evidence-gated early active ping for credible lost tracks, improving post-loss probe behavior while preserving duplicate-shot, wasted-shot, sonar clutter, and acoustic clutter gates.
- Continuity: Campaign 004A fire-control loop promoted - Campaign 004A is promoted. ReadyPlayer1 belief_baseline now exposes fire-control decision rationale and suppresses duplicate same-primary torpedo commits, moving clean_single_contact_tracking torpedo_count from 2 to 1 and torpedo_wasted_shot_rate from 0.5 to 0.0 while preserving sonar and acoustic clutter gates.
- Continuity: Campaign 003 acoustic clutter binding integrated - ReadyPlayer1 now loads SubSim hydrophone acoustic eval cases, scores heldout-source acoustic clutter binding by default, and blocks rejected/high-risk clutter tracks from the reacquire-primary fallback. Heldout acoustic clutter wrong binding moved from 1.0 to 0.0 while surface-contact missed-track stayed 0.0.
- Continuity: Campaign 003 promoted for SubSim clutter binding - Campaign 003 promoted after ReadyPlayer1 primary-track candidate semantics reduced clutter primary binding without hiding raw false positives.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
