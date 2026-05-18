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
budget: 5 selected (3 primary, 2 supplements), 4 omitted_for_budget, 0 omitted_for_limit

PRIMARY MEMORY
- [eed995dd-60bf-4bd6-b678-9541501d5b5d] Phase 2 canonical current-state pointers and onboarding source consolidation
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 81.846053 rank: 1
  summary: Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
  body: Implemented canonical pointer surfaces runs/current/lane_current_state_index.json and runs/current/<lane_id>/lane_current_state.json and synced them from lane registry updates. Canonicalized lane registry onboarding semantics to keep onboarding_config_json/onboarding_template_json as current bootstrap source and preserve historical onboarding run snapshots in latest_onboarding_run_config_json/latest_onboarding_run_summary_json. Updated README, RUNBOOK, and ARCHITECTURE_CHECKPOINT to align operator default flow with the new current-state pointer strategy; added docs/tasks/repo_drift_phase2_e...
  evidence: /mnt/data/ReadyPlayer1/ARCHITECTURE_CHECKPOINT.md; /mnt/data/ReadyPlayer1/readyplayer1/cli.py; /mnt/data/ReadyPlayer1/RUNBOOK.md; /mnt/data/ReadyPlayer1/README.md; /mnt/data/ReadyPlayer1/docs/tasks/repo_drift_phase2_execution_summary.json
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['current', 'readyplayer1', 'state']
- [bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44] Campaign 005A promoted fire-control state normalization
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 80.382445 rank: 2
  summary: Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
  body: SubSim now emits structured fire_control observation fields and sonar-console frames carry them. ReadyPlayer1 normalizes producer fire-control state and infer-compatible replay state, adds coverage metrics, and preserved Campaign 004A fire-control behavior plus sonar/acoustic gates. Final status CAMPAIGN_005A_PROMOTED.
  evidence: /mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py; /mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json; /mnt/data/ReadyPlayer1/readyplayer1/harness/subsim/sonar_adapter.py; /mnt/data/ReadyPlayer1/reports/campaign_005a_promotion_decision.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state']
- [1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0] Campaign 004A promoted with ReadyPlayer1 fire-control loop patch
  kind: decision status: active stage: primary_retrieval reason: query_match
  score: 71.703236 rank: 3
  summary: Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
  body: Evidence: clean_single_contact_tracking under seed 7 moved torpedo_count 2 -> 1, torpedo_duplicate_same_track_count 1 -> 0, and torpedo_wasted_shot_rate 0.5 -> 0.0. clutter_false_positive preservation metrics stayed unchanged, scenario suite remained 7 pass / 0 fail, golden regression passed, SubSim full tests passed, and ReadyPlayer1 focused SubSim tests passed. Next recommended campaign is Campaign 005A: normalize SubSim fire-control readiness/solution state into ReadyPlayer1 observations and replay traces.
  evidence: /mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json; /mnt/data/ReadyPlayer1/PROJECT_MEMORY.md; /mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
  explanation: path=v2_hybrid_recall sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'next', 'readyplayer1', 'state']

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

EVIDENCE
- [05f3edf1-a1c7-4dde-9541-ae3a37e58cc6] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_007a_promotion_decision.md
- [324ae219-9e11-4a8f-b12e-a9d37798ab4d] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_007a_comparison.json
- [84a71d72-829d-4bf1-8214-c145269df127] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py
- [e23a9e93-988f-4f92-9b83-a8b4b8849eab] card=0afb7524-b5b6-4e78-9a56-a08915eb895e type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [194d9ef0-d37a-48ad-be7b-e35318f9f759] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json
- [7a30fa16-62a4-4b8a-a839-567f9d4435ae] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/PROJECT_MEMORY.md
- [7a35b654-0edc-4f34-989b-207490e27765] card=1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md
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
- [074bd4f9-d2d4-4ae3-a7ee-075585bbf3eb] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_006a_comparison.json
- [21f79e08-e73f-449d-b074-ecc10c1e69af] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py
- [b632f863-7ee8-4bd5-94b4-c4ef75b2c9fa] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/reports/campaign_006a_promotion_decision.md
- [f5a27605-9617-4229-b771-ac1b93b6e0ab] card=fbcac688-f952-477f-87ca-ea7860c4f396 type=file ref=/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py

UNCERTAINTY AND GAPS
- Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
- 4 candidate cards were omitted by max_chars budget.

AGENT BRIEFING
- Primary match: Phase 2 canonical current-state pointers and onboarding source consolidation - Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
- Primary match: Campaign 005A promoted fire-control state normalization - Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
- Primary match: Campaign 004A promoted with ReadyPlayer1 fire-control loop patch - Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
- Continuity: Campaign 007A promoted post-reacquisition stabilization - Campaign 007A promoted a bounded ReadyPlayer1 policy and metrics change for post-reacquisition belief stabilization. The belief_baseline now tracks recovery probe outcomes and briefly stabilizes a compatible recovered previous primary while preserving torpedo, sonar clutter, acoustic clutter, scenario, and golden gates.
- Continuity: Campaign 006A promoted post-loss recovery probe - Campaign 006A promoted a bounded ReadyPlayer1 policy and metrics change for post-shot/post-loss reacquisition. The belief_baseline now performs an evidence-gated early active ping for credible lost tracks, improving post-loss probe behavior while preserving duplicate-shot, wasted-shot, sonar clutter, and acoustic clutter gates.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
END MUNINN V2 AGENT CONTEXT
