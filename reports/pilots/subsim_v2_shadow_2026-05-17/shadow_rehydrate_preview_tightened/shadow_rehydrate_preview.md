# Muninn v2 Shadow Rehydration Preview

## Executive Summary

- Usable: `true`
- Total cards: 8 (3 primary, 5 supplements)
- Retrieval backend: `hybrid`
- Fallback used: `false`
- Degraded: `true`

## Query / Task

`resume SubSim current ReadyPlayer1 campaign integration state and next steps`

## Source

- v2 DB: `reports/pilots/subsim_v2_shadow_2026-05-17/subsim_shadow_v2.db`
- Space key: `repo:363c13a65e92ef58`
- Project path: `None`

## Composition Strategy

- Strategy: `hybrid_primary_plus_recent_supplement`
- Retrieval mode: `hybrid`
- Limit: 12
- Primary limit: 3
- Recent limit: 9
- Max chars: `None`

## Primary Retrieval Matches

- `8d0704f3-2903-44df-937c-c80902b20f64` SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-07 16:01:24` score=`83.980211`
  - summary: Both repos now carry PROJECT_MEMORY campaign ledgers through Campaign 003 with Campaign 004A recommended next.
  - body excerpt: The checkpoint records Preflight, Campaign 001, Campaign 002A, and Campaign 003 as promoted. Current trusted metrics include SubSim full suite 58 passed, ReadyPlayer1 focused SubSim and golden tests 28 passed, scenario suite 7 pass / 0 fail, golden regression pass, and Campaign 003 clutter binding improvement sonar_clutter_wrong_binding_rate 0.2 -> 0.0. Recommended next campaign is 004A torpedo / fire-control feedback loop.
  - evidence: `/mnt/data/ReadyPlayer1/reports/campaign_003_promotion_decision.md`; `/mnt/data/subsim/PROJECT_MEMORY.md`; `/mnt/data/ReadyPlayer1/PROJECT_MEMORY.md`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'current', 'next', 'readyplayer1', 'subsim']
- `f94af521-4f75-4f42-b9d6-8a10b66d4a0d` SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy
  - stage: `primary_retrieval` reason: `query_match` kind: `interface` updated: `2026-05-07 16:18:10` score=`75.131649`
  - summary: Campaign 004A did not change SubSim gameplay, torpedo physics, sonar producer code, or scenario expectations. It records that ReadyPlayer1 now suppresses duplicate same-primary torpedo commits and exposes fire-control metrics against existing SubSim replay evidence.
  - body excerpt: Trusted post-campaign state: SubSim full tests passed with 65 tests, scenario suite stayed 7 pass / 0 fail, and clutter_false_positive sonar metrics were preserved. Remaining SubSim-side interface risk is that live FireControl state exists but is not yet normalized into ReadyPlayer1 sonar replay/live observations; Campaign 005A should expose solution lifecycle and post-shot feedback without changing torpedo physics.
  - evidence: `/mnt/data/subsim/PROJECT_MEMORY.md`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_comparison.json`; `/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state', 'subsim']
- `b97c8e3f-2a41-4031-946f-2f57b87f2bc2` SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-05-07 14:39:41` score=`75.114139`
  - summary: SubSim now has local project state, evaluation contract, ship targets, campaign plan, and reports for the bounded ReadyPlayer1 evaluation loop. Campaign 001 is sonar contact readability under clutter, anchored by ReadyPlayer1 before metrics for clutter_false_positive.
  - body excerpt: No gameplay changes were made during preflight. SubSim full tests passed and deterministic seed 7 trace export succeeded after creating reports/. Promotion remains hold until after metrics exist; status is READY_FOR_CAMPAIGN_001_IMPLEMENTATION.
  - evidence: `/mnt/data/subsim/SUBSIM_PROJECT_STATE.md`; `/mnt/data/subsim/docs/CAMPAIGN_001_PLAN.md`; `/mnt/data/subsim/reports/preflight_subsim_skirmish_seed7_trace.json`; `/mnt/data/subsim/reports/evaluation_contract_status.json`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['campaign', 'readyplayer1', 'state', 'subsim']

## Recent In-Scope Supplements

- `2fbc9cf8-118c-4a0d-84bc-a5ee90716adb` SubSim fire_control observation contract v1
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `interface` updated: `2026-05-07 17:05:15`
  - summary: SubSim exposes fire-control readiness and solution-state data through build_observation and sonar-console frames for ReadyPlayer1 Campaign 005A.
  - body excerpt: The fire_control block includes fire_control_ready, fire_control_solution_state, fire_control_solution_quality, weapon_ready, valid_fire_opportunity, hold reason, target id, solution timing, and active_torpedo_count. This is producer/adapter visibility only; torpedo physics and firing timing were not changed.
  - evidence: `/mnt/data/subsim/subsim/game.py`; `/mnt/data/subsim/subsim/testing/sonar_console/contracts.py`; `/mnt/data/subsim/subsim/testing/sonar_console/console.py`; `/mnt/data/ReadyPlayer1/reports/campaign_005a_comparison.json`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['005a', 'campaign', 'contract', 'control', 'exposes', 'fire', 'hold', 'physics', 'producer', 'ready', 'readyplayer1', 'reports', 'solution', 'sonar', 'subsim', 'through', 'torpedo', 'were']
- `66312a31-2eca-4931-8f28-ae75a2dc7411` Campaign 004A leaves SubSim fire-control physics unchanged
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `interface` updated: `2026-05-07 16:43:30`
  - summary: Campaign 004A was a ReadyPlayer1 policy/evaluator improvement and did not change SubSim torpedo physics, damage, range, sonar producer behavior, or scenario expectations. SubSim remains the protected producer surface for future fire-control state normalization.
  - body excerpt: The next recommended slice is to normalize SubSim live FireControl solution state into sonar replay/live observations so ReadyPlayer1 can distinguish solution_start, ready, fired, miss, and reacquisition feedback without approximating entirely from policy memory.
  - evidence: `/mnt/data/ReadyPlayer1/reports/campaign_004a_promotion_decision.md`; `/mnt/data/subsim/subsim/game.py`; `/mnt/data/subsim/subsim/engine/weapons.py`; `/mnt/data/subsim/PROJECT_MEMORY.md`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['004a', 'campaign', 'change', 'control', 'expectations', 'feedback', 'fire', 'firecontrol', 'improvement', 'live', 'memory', 'next', 'observations', 'physics', 'policy', 'producer', 'promotion', 'ready', 'readyplayer1', 'recommended', 'remains', 'replay', 'reports', 'scenario', 'solution', 'sonar', 'subsim', 'torpedo', 'without']
- `4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9` Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `interface` updated: `2026-05-07 16:33:57`
  - summary: SubSim hydrophone artifacts under data/hydrophone/fixtures and data/hydrophone/manifests/splits are the fixed inputs for ReadyPlayer1 Campaign 003 acoustic clutter-binding evaluation. Promotion scoring defaults to heldout_source_eval and excludes synthetic cases unless explicitly requested.
  - body excerpt: The fixture export commands were rerun successfully for 78 cases/fixtures after fixed splits were rebuilt with seed 1337. Runtime policy decisions should still use contact evidence, confidence, lifecycle, ambiguity, and binding quality rather than fixture labels as direct truth.
  - evidence: `/mnt/data/subsim/data/hydrophone/manifests/splits/`; `/mnt/data/subsim/data/hydrophone/fixtures/subsim_acoustic_contacts.jsonl`; `/mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['after', 'binding', 'campaign', 'clutter', 'contact', 'evaluation', 'evidence', 'export', 'lifecycle', 'policy', 'promotion', 'readyplayer1', 'seed', 'should', 'subsim', 'under', 'were']
- `5e260af6-8b17-427f-832d-028fae69d295` Hydrophone fixed eval and acoustic fixtures
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `interface` updated: `2026-05-07 16:14:11`
  - summary: SubSim hydrophone now has deterministic group-safe fixed splits and real-only gameplay/eval fixture exports.
  - body excerpt: The fixed eval slice writes data/hydrophone/manifests/splits/{train,validation,heldout_source_eval}.jsonl plus split_summary.json, updates classifier training to use those manifests with separate validation and heldout-source metrics, and exports SubSim/ReadyPlayer1 acoustic fixture JSONL under data/hydrophone/fixtures. Synthetic fixtures remain excluded by default and require explicit include flags.
  - evidence: `/mnt/data/subsim/data/hydrophone/manifests/splits/split_summary.json`; `/mnt/data/subsim/scripts/hydrophone/train_hydrophone_classifier.py`; `/mnt/data/subsim/scripts/hydrophone/build_fixed_eval_splits.py`; `/mnt/data/subsim/data/hydrophone/fixtures/readyplayer1_acoustic_eval_cases.jsonl`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['deterministic', 'gameplay', 'include', 'metrics', 'readyplayer1', 'subsim', 'under']
- `fb91d94b-b9e2-4bd8-a970-ff315747cd2d` SubSim sonar tracks expose explicit lifecycle state
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `interface` updated: `2026-05-07 15:34:51`
  - summary: Campaign 002A extended the SubSim sonar-console PerceivedTrack contract with lifecycle_state and emits possible/suspect/tracking/confirmed/rejected/lost from perception. This is a producer-side readability signal, not a confidence threshold change.
  - body excerpt: SubSim PerceptionEngine now computes lifecycle_state after ambiguity flags and contact_quality. Weak passive-only clutter reaches rejected, active ping or strong evidence reaches confirmed, and older confidence/clutter rejection behavior from Campaign 001 is preserved.
  - evidence: `/mnt/data/subsim/subsim/testing/sonar_console/perception.py`; `/mnt/data/subsim/subsim/testing/sonar_console/tests/test_perception.py`; `/mnt/data/subsim/subsim/testing/sonar_console/contracts.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['002a', 'after', 'campaign', 'change', 'clutter', 'contact', 'contract', 'evidence', 'expose', 'lifecycle', 'preserved', 'producer', 'readability', 'side', 'sonar', 'subsim', 'tests']

## Evidence / Provenance

- Evidence refs available on preview cards: 28
- Evidence refs included in report: 28
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

- Primary match: SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003 - Both repos now carry PROJECT_MEMORY campaign ledgers through Campaign 003 with Campaign 004A recommended next.
- Primary match: SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy - Campaign 004A did not change SubSim gameplay, torpedo physics, sonar producer code, or scenario expectations. It records that ReadyPlayer1 now suppresses duplicate same-primary torpedo commits and exposes fire-control metrics against existing SubSim replay evidence.
- Primary match: SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected - SubSim now has local project state, evaluation contract, ship targets, campaign plan, and reports for the bounded ReadyPlayer1 evaluation loop. Campaign 001 is sonar contact readability under clutter, anchored by ReadyPlayer1 before metrics for clutter_false_positive.
- Continuity: SubSim fire_control observation contract v1 - SubSim exposes fire-control readiness and solution-state data through build_observation and sonar-console frames for ReadyPlayer1 Campaign 005A.
- Continuity: Campaign 004A leaves SubSim fire-control physics unchanged - Campaign 004A was a ReadyPlayer1 policy/evaluator improvement and did not change SubSim torpedo physics, damage, range, sonar producer behavior, or scenario expectations. SubSim remains the protected producer surface for future fire-control state normalization.
- Continuity: Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring - SubSim hydrophone artifacts under data/hydrophone/fixtures and data/hydrophone/manifests/splits are the fixed inputs for ReadyPlayer1 Campaign 003 acoustic clutter-binding evaluation. Promotion scoring defaults to heldout_source_eval and excludes synthetic cases unless explicitly requested.
- Continuity: Hydrophone fixed eval and acoustic fixtures - SubSim hydrophone now has deterministic group-safe fixed splits and real-only gameplay/eval fixture exports.
- Continuity: SubSim sonar tracks expose explicit lifecycle state - Campaign 002A extended the SubSim sonar-console PerceivedTrack contract with lifecycle_state and emits possible/suspect/tracking/confirmed/rejected/lost from perception. This is a producer-side readability signal, not a confidence threshold change.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
