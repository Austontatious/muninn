# Muninn v2 Shadow Rehydration Preview

## Executive Summary

- Usable: `true`
- Total cards: 9 (3 primary, 6 supplements)
- Retrieval backend: `hybrid`
- Fallback used: `false`
- Degraded: `true`

## Query / Task

`resume ReadyPlayer1 current campaign state and next steps`

## Source

- v2 DB: `reports/pilots/readyplayer1_v2_shadow_2026-05-17/readyplayer1_shadow_v2.db`
- Space key: `repo:5059f410815720ea`
- Project path: `None`

## Composition Strategy

- Strategy: `hybrid_primary_plus_recent_supplement`
- Retrieval mode: `hybrid`
- Limit: 12
- Primary limit: 3
- Recent limit: 9
- Max chars: `None`

## Primary Retrieval Matches

- `eed995dd-60bf-4bd6-b678-9541501d5b5d` Phase 2 canonical current-state pointers and onboarding source consolidation
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-04-23 17:39:49` score=`81.846053`
  - summary: Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
  - body excerpt: Implemented canonical pointer surfaces runs/current/lane_current_state_index.json and runs/current/<lane_id>/lane_current_state.json and synced them from lane registry updates. Canonicalized lane registry onboarding semantics to keep onboarding_config_json/onboarding_template_json as current bootstrap source and preserve historical onboarding run snapshots in latest_onboarding_run_config_json/latest_onboarding_run_summary_json. Updated README, RUNBOOK, and ARCHITECTURE_CHECKPOINT to align operator default flow with the new current-state pointer strategy; added docs/tasks/repo_drift_phase2_e...
  - evidence: `/mnt/data/ReadyPlayer1/ARCHITECTURE_CHECKPOINT.md`; `/mnt/data/ReadyPlayer1/readyplayer1/cli.py`; `/mnt/data/ReadyPlayer1/RUNBOOK.md`; `/mnt/data/ReadyPlayer1/README.md`; `/mnt/data/ReadyPlayer1/docs/tasks/repo_drift_phase2_execution_summary.json`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['current', 'readyplayer1', 'state']
- `bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44` Campaign 005A promoted fire-control state normalization
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-07 17:05:08` score=`80.382445`
  - summary: Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
  - body excerpt: SubSim now emits structured fire_control observation fields and sonar-console frames carry them. ReadyPlayer1 normalizes producer fire-control state and infer-compatible replay state, adds coverage metrics, and preserved Campaign 004A fire-control behavior plus sonar/acoustic gates. Final status CAMPAIGN_005A_PROMOTED.
  - evidence: `/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py`; `/mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json`; `/mnt/data/ReadyPlayer1/readyplayer1/harness/subsim/sonar_adapter.py`; `/mnt/data/ReadyPlayer1/reports/campaign_005a_promotion_decision.md`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state']
- `1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0` Campaign 004A promoted with ReadyPlayer1 fire-control loop patch
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-07 16:18:00` score=`71.703236`
  - summary: Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
  - body excerpt: Evidence: clean_single_contact_tracking under seed 7 moved torpedo_count 2 -> 1, torpedo_duplicate_same_track_count 1 -> 0, and torpedo_wasted_shot_rate 0.5 -> 0.0. clutter_false_positive preservation metrics stayed unchanged, scenario suite remained 7 pass / 0 fail, golden regression passed, SubSim full tests passed, and ReadyPlayer1 focused SubSim tests passed. Next recommended campaign is Campaign 005A: normalize SubSim fire-control readiness/solution state into ReadyPlayer1 observations and replay traces.
  - evidence: `/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json`; `/mnt/data/ReadyPlayer1/PROJECT_MEMORY.md`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'next', 'readyplayer1', 'state']

## Recent In-Scope Supplements

- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-07 17:52:40`
  - summary: Campaign 007A promoted a bounded ReadyPlayer1 policy and metrics change for post-reacquisition belief stabilization. The belief_baseline now tracks recovery probe outcomes and briefly stabilizes a compatible recovered previous primary while preserving torpedo, sonar clutter, acoustic clutter, scenario, and golden gates.
  - body excerpt: Campaign 007A made no SubSim gameplay or torpedo physics changes. ReadyPlayer1 belief_baseline now records guarded recovery probe state, stabilizes compatible recovered previous-primary evidence for a short window, and delays no-evidence stale cleanup to avoid clearing one frame before delayed recovery evidence appears. high_self_noise_degradation post_reacquisition_policy_stabilized_rate moved from 0.0 to 1.0 with sonar_action_thrash preserved at 5, previous_primary_recovered_rate preserved at 1.0, and post_reacquisition_clutter_rebind_rate preserved at 0.0. reacquisition_challenge_no_reco...
  - evidence: `/mnt/data/ReadyPlayer1/reports/campaign_007a_promotion_decision.md`; `/mnt/data/ReadyPlayer1/reports/campaign_007a_comparison.json`; `/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py`; `/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['acoustic', 'after', 'baseline', 'belief', 'bounded', 'campaign', 'change', 'clutter', 'compatible', 'contact', 'count', 'decision', 'drift', 'duplicate', 'emits', 'evidence', 'fail', 'gates', 'golden', 'json', 'metrics', 'moved', 'pass', 'passed', 'policy', 'preserved', 'preserving', 'primary', 'promoted', 'rate', 'readyplayer1', 'regression', 'replay', 'same', 'scenario', 'shot', 'sonar', 'stale', 'stayed', 'subsim', 'suite', 'torpedo', 'track', 'wasted', 'while']
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-07 17:32:36`
  - summary: Campaign 006A promoted a bounded ReadyPlayer1 policy and metrics change for post-shot/post-loss reacquisition. The belief_baseline now performs an evidence-gated early active ping for credible lost tracks, improving post-loss probe behavior while preserving duplicate-shot, wasted-shot, sonar clutter, and acoustic clutter gates.
  - body excerpt: Campaign 006A made no SubSim torpedo physics changes. ReadyPlayer1 belief_baseline uses normalized Campaign 005A fire-control/contact state to allow earlier reacquire pings only for credible lost/recoverable tracks, while rejecting clutter-like/high-risk contacts. Metrics now report post-loss reacquisition attempt/ping/success, clutter rebind, belief drift after loss, and valid-fire ready-but-hold rate. Scenario suite stayed 7 pass / 0 fail, golden regression passed, acoustic heldout clutter wrong binding stayed 0.0, sonar_clutter_wrong_binding_rate stayed 0.0, torpedo_duplicate_same_track_...
  - evidence: `/mnt/data/ReadyPlayer1/reports/campaign_006a_comparison.json`; `/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py`; `/mnt/data/ReadyPlayer1/reports/campaign_006a_promotion_decision.md`; `/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['005a', 'acoustic', 'after', 'baseline', 'behavior', 'belief', 'bounded', 'campaign', 'change', 'clutter', 'contact', 'control', 'count', 'decision', 'drift', 'duplicate', 'evidence', 'fail', 'fire', 'gates', 'golden', 'json', 'metrics', 'pass', 'passed', 'policy', 'preserving', 'promoted', 'rate', 'readyplayer1', 'regression', 'remained', 'replay', 'same', 'scenario', 'shot', 'sonar', 'stayed', 'subsim', 'suite', 'torpedo', 'track', 'wasted', 'while']
- `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-07 16:43:23`
  - summary: Campaign 004A is promoted. ReadyPlayer1 belief_baseline now exposes fire-control decision rationale and suppresses duplicate same-primary torpedo commits, moving clean_single_contact_tracking torpedo_count from 2 to 1 and torpedo_wasted_shot_rate from 0.5 to 0.0 while preserving sonar and acoustic clutter gates.
  - body excerpt: The refreshed Campaign 004A evidence uses suite run 20260507T163754Z-subsim_suite-bd3e2a and heldout acoustic regression scoring. Scenario suite remains 7 pass / 0 fail with regression pass; acoustic_clutter_wrong_binding_rate remains 0.0; SubSim full tests passed 65; ReadyPlayer1 full tests passed with one skipped marker. Remaining risks are not hidden: timidity_indecision, belief_drift, and reacquisition_failure remain, and SubSim fire-control state is not yet normalized into replay observations.
  - evidence: `/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py`; `/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_after_runs/acoustic_regression/campaign_004a_acoustic_regression_summary.json`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['004a', 'acoustic', 'after', 'baseline', 'belief', 'campaign', 'clean', 'clutter', 'commits', 'contact', 'control', 'count', 'decision', 'drift', 'duplicate', 'evidence', 'fail', 'fire', 'full', 'gates', 'json', 'loop', 'metrics', 'observations', 'pass', 'passed', 'preserving', 'primary', 'promoted', 'rate', 'rationale', 'readyplayer1', 'regression', 'replay', 'runs', 'same', 'scenario', 'shot', 'single', 'sonar', 'subsim', 'suite', 'summary', 'suppresses', 'tests', 'torpedo', 'tracking', 'wasted', 'while']
- `8db59c21-0224-4ef0-b628-f336867bf591` Campaign 003 acoustic clutter binding integrated
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-07 16:33:50`
  - summary: ReadyPlayer1 now loads SubSim hydrophone acoustic eval cases, scores heldout-source acoustic clutter binding by default, and blocks rejected/high-risk clutter tracks from the reacquire-primary fallback. Heldout acoustic clutter wrong binding moved from 1.0 to 0.0 while surface-contact missed-track stayed 0.0.
  - body excerpt: Durable evidence lives under reports/campaign_003_acoustic_clutter. The implementation adds acoustic case loading, acoustic clutter metrics, a subsim acoustic-clutter CLI/suite entry point, focused tests, and a bounded BeliefBaseline primary reacquire guard that does not use fixture labels at runtime.
  - evidence: `/mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_cases.py`; `/mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_promotion_decision.md`; `/mnt/data/ReadyPlayer1/reports/campaign_003_acoustic_clutter/campaign_003_acoustic_clutter_comparison.json`; `/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py`; `/mnt/data/ReadyPlayer1/readyplayer1/eval/acoustic_clutter_metrics.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['acoustic', 'adds', 'baseline', 'belief', 'bounded', 'campaign', 'clutter', 'contact', 'decision', 'default', 'evidence', 'focused', 'json', 'metrics', 'moved', 'primary', 'readyplayer1', 'source', 'stayed', 'subsim', 'suite', 'tests', 'track', 'under', 'while']
- `2656c35f-79af-403d-9128-e98fc72663d6` Campaign 003 promoted for SubSim clutter binding
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-05-07 16:01:15`
  - summary: Campaign 003 promoted after ReadyPlayer1 primary-track candidate semantics reduced clutter primary binding without hiding raw false positives.
  - body excerpt: ReadyPlayer1 now emits/uses primary_candidate and binding_candidate_score for SubSim sonar tracks. The belief_baseline lane defers primary selection when multiple weak possible contacts compete, while raw clutter confidence remains visible through sonar_clutter_raw_confidence_wrong_binding_rate. Target clutter_false_positive metrics moved sonar_clutter_wrong_binding_rate 0.2 -> 0.0 and sonar_action_thrash 4 -> 2 with scenario suite 7 pass / 0 fail and golden regression pass.
  - evidence: `/mnt/data/ReadyPlayer1/readyplayer1/eval/metrics.py`; `/mnt/data/ReadyPlayer1/reports/campaign_003_comparison.json`; `/mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md`; `/mnt/data/ReadyPlayer1/readyplayer1/agents/policies/belief_baseline.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['after', 'baseline', 'belief', 'campaign', 'clutter', 'decision', 'emits', 'fail', 'false', 'golden', 'json', 'lane', 'metrics', 'moved', 'pass', 'positive', 'primary', 'promoted', 'rate', 'readyplayer1', 'regression', 'scenario', 'semantics', 'sonar', 'subsim', 'suite', 'track', 'while']
- `fb80c2a4-3025-4a64-bd60-3cbf7484b2d2` SubSim ReadyPlayer1 evaluation contract v1 documented
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `interface` updated: `2026-05-07 14:39:41`
  - summary: ReadyPlayer1 now carries the SubSim closed-loop evaluation contract and preflight status reports for Campaign 001. The contract records scenario id, seed, SubSim and ReadyPlayer1 commits, evaluator lane, metrics, replay/run artifacts, failure taxonomy, and promotion decision.
  - body excerpt: Baseline, belief baseline, belief-state variant, and shadow lanes are documented. Learned or shadow lanes are advisory only and cannot be the sole promotion signal. Full seed 7 belief_baseline suite passed golden regression with one scenario expectation failure on clutter_false_positive.
  - evidence: `/mnt/data/ReadyPlayer1/READYPLAYER1_PROJECT_STATE.md`; `/mnt/data/ReadyPlayer1/docs/EVALUATION_CONTRACT.md`; `/mnt/data/ReadyPlayer1/reports/campaign_001_runs/20260507T143115Z-subsim_suite-677aa9/suite_summary.json`; `/mnt/data/ReadyPlayer1/reports/campaign_001_preflight.md`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['artifacts', 'baseline', 'belief', 'campaign', 'clutter', 'commits', 'decision', 'docs', 'false', 'full', 'golden', 'json', 'lane', 'loop', 'metrics', 'passed', 'positive', 'readyplayer1', 'regression', 'replay', 'runs', 'scenario', 'seed', 'status', 'subsim', 'suite', 'summary']

## Evidence / Provenance

- Evidence refs available on preview cards: 41
- Evidence refs included in report: 41
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

- Primary match: Phase 2 canonical current-state pointers and onboarding source consolidation - Phase 2 consolidated ReadyPlayer1 lane current-state consumption around runs/current pointer artifacts and removed stale onboarding-source ambiguity from registry defaults. Registry onboarding now points to the canonical template/source while historical onboarding run artifacts are retained as lineage fields.
- Primary match: Campaign 005A promoted fire-control state normalization - Campaign 005A promoted explicit fire-control readiness and solution-state visibility for SubSim observations consumed by ReadyPlayer1.
- Primary match: Campaign 004A promoted with ReadyPlayer1 fire-control loop patch - Campaign 004A promoted after a bounded ReadyPlayer1-side change to the belief_baseline fire-control loop. The policy now emits fire-control decision rationale, suppresses duplicate same-primary torpedo commits, and adds deterministic fire-control metrics while preserving SubSim sonar gains.
- Continuity: Campaign 007A promoted post-reacquisition stabilization - Campaign 007A promoted a bounded ReadyPlayer1 policy and metrics change for post-reacquisition belief stabilization. The belief_baseline now tracks recovery probe outcomes and briefly stabilizes a compatible recovered previous primary while preserving torpedo, sonar clutter, acoustic clutter, scenario, and golden gates.
- Continuity: Campaign 006A promoted post-loss recovery probe - Campaign 006A promoted a bounded ReadyPlayer1 policy and metrics change for post-shot/post-loss reacquisition. The belief_baseline now performs an evidence-gated early active ping for credible lost tracks, improving post-loss probe behavior while preserving duplicate-shot, wasted-shot, sonar clutter, and acoustic clutter gates.
- Continuity: Campaign 004A fire-control loop promoted - Campaign 004A is promoted. ReadyPlayer1 belief_baseline now exposes fire-control decision rationale and suppresses duplicate same-primary torpedo commits, moving clean_single_contact_tracking torpedo_count from 2 to 1 and torpedo_wasted_shot_rate from 0.5 to 0.0 while preserving sonar and acoustic clutter gates.
- Continuity: Campaign 003 acoustic clutter binding integrated - ReadyPlayer1 now loads SubSim hydrophone acoustic eval cases, scores heldout-source acoustic clutter binding by default, and blocks rejected/high-risk clutter tracks from the reacquire-primary fallback. Heldout acoustic clutter wrong binding moved from 1.0 to 0.0 while surface-contact missed-track stayed 0.0.
- Continuity: Campaign 003 promoted for SubSim clutter binding - Campaign 003 promoted after ReadyPlayer1 primary-track candidate semantics reduced clutter primary binding without hiding raw false positives.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
