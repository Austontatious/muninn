# Muninn v2 Shadow Rehydration Preview

## Executive Summary

- Usable: `true`
- Total cards: 8 (3 primary, 5 supplements)
- Retrieval backend: `hybrid`
- Fallback used: `false`
- Degraded: `true`

## Query / Task

`resume Sindri current wrapper-lane trust calibration state and next steps`

## Source

- v2 DB: `reports/pilots/sindri_v2_shadow_2026-05-17/sindri_shadow_v2.db`
- Space key: `path:316f4f67d061cbdd`
- Project path: `None`

## Composition Strategy

- Strategy: `hybrid_primary_plus_recent_supplement`
- Retrieval mode: `hybrid`
- Limit: 12
- Primary limit: 3
- Recent limit: 9
- Max chars: `None`

## Primary Retrieval Matches

- `e4dccb72-35fa-461b-9208-b08a9c28507d` Phase 5 adds machine-gated trust outputs for flagship wrapper lane
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-04-04 23:25:04` score=`60.914301`
  - summary: Sindri now emits structured promotion-gate results and safe operator summaries for wrapper-lane jobs, and uses calibrated posture mapping to distinguish caveat, patch-before, abstain, and blocking outcomes.
  - body excerpt: Implemented bounded machine-gated trust in Phase 5 by extending promotion decisions with gate outputs (artifact completeness, risk flags, unresolved gaps, patchability, blockers, readiness, posture, safe summary, next action, operator attention). Orchestrator, job records, promotion_decision artifact, decision trace, and review bundle now carry this structured state. Calibration was adjusted to avoid false host-mutation abstentions when non-mutation intent is explicit and to reduce brittle evidence-quality rejection for flagship local-reference cases.
  - evidence: `/mnt/data/Sindri/sindri/review.py`; `/mnt/data/Sindri/sindri/orchestrator.py`; `/mnt/data/Sindri/sindri/review_bundle.py`
  - explanation: sources=['body', 'evidence', 'summary', 'title', 'vector'] tokens=['calibration', 'lane', 'next', 'sindri', 'state', 'trust', 'wrapper']
- `092f7e10-b6ab-43d2-9cbf-49ce08ff0b32` Trust regression surface helper command for wrapper-lane calibration
  - stage: `primary_retrieval` reason: `query_match` kind: `runbook` updated: `2026-04-05 00:54:22` score=`56.864028`
  - summary: Phase 8.5 adds a single helper command to run lint/tests and trust check runners required for non-regressive calibration passes.
  - body excerpt: Use `make trust_regression_check` or `bash scripts/run_trust_regression_check.sh` to execute the baseline trust regression surface checks (lint, tests, eval scaffold checks for phase35/phase4/pilot/phase7/phase8).
  - evidence: `/mnt/data/Sindri/Makefile`; `/mnt/data/Sindri/scripts/run_trust_regression_check.sh`; `/mnt/data/Sindri/docs/TRUST_REGRESSION_SURFACE.md`
  - explanation: sources=['body', 'evidence', 'summary', 'tags', 'title', 'vector'] tokens=['calibration', 'lane', 'sindri', 'trust', 'wrapper']
- `a2f4cb59-71d2-4131-8b7b-b030b8eaa342` Phase 10 graduates wrapper lane with explicit criteria gate
  - stage: `primary_retrieval` reason: `query_match` kind: `decision` updated: `2026-04-05 01:53:33` score=`47.425472`
  - summary: Sindri Phase 10 adds explicit graduation criteria and a dedicated assessment slice for capability_wrapper_scaffold, yielding a graduate_lane verdict while preserving trust guardrails.
  - body excerpt: Phase10 introduces deterministic graduation scoring over safety, abstention quality, reviewer burden, disagreement quality, handoff sufficiency, patch boundedness, scope containment, and blocker/ambiguity preservation. The graduation slice passed all criteria with unsafe_promotion_rate=0.0, incorrect_abstention_rate=0.0, and full_manual_inspection_rate=0.0. Wrapper lane is now framed as the first reference-quality narrow pilot lane; adjacent-lane transfer remains deferred to a separate proving phase.
  - evidence: `/mnt/data/Sindri/evals/phase10_pilot_graduation/last_results.json`; `/mnt/data/Sindri/docs/phase10_pilot_graduation_report.md`; `61214ba`
  - explanation: sources=['body', 'evidence', 'summary', 'tags', 'title', 'vector'] tokens=['lane', 'sindri', 'trust', 'wrapper']

## Recent In-Scope Supplements

- `5dbf7a31-341b-4940-96d9-9e7c965d2c64` Phase 11 transfer validation sequence
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `runbook` updated: `2026-04-05 02:30:26`
  - summary: Phase 11 transfer proving requires full trust regression checks plus the dedicated phase11 runner check/run.
  - body excerpt: For adjacent-lane transfer work, run make lint/test, trust regression checks, baseline eval check surfaces, and phase11 runner check+run. Keep wrapper lane as control by preserving phase10 graduation stability and running make trust_regression_check before accepting any transfer verdict.
  - evidence: `/mnt/data/Sindri/scripts/run_trust_regression_check.sh`; `/mnt/data/Sindri/docs/phase11_transfer_plan.md`; `/mnt/data/Sindri/evals/phase11_adjacent_lane_transfer/runner.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['adjacent', 'baseline', 'before', 'check', 'checks', 'dedicated', 'eval', 'full', 'graduation', 'lane', 'lint', 'make', 'phase', 'phase10', 'preserving', 'proving', 'regression', 'scripts', 'sindri', 'transfer', 'trust', 'verdict', 'wrapper']
- `6383fd96-30ca-4cfc-ab54-5c8fa7dd447a` Phase 11 adjacent-lane transfer verdict is partial
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-04-05 02:30:20`
  - summary: Adjacent parser/transform lane transfer passes safety and containment but remains burden-heavy. Verdict is transfer_partial with wrapper lane retained as stable control.
  - body excerpt: Phase 11 introduced an adjacent lane transfer slice (8 cases) using wrapper-lane trust surfaces with bounded specialization. Core safety remained intact (unsafe promotion 0.0, incorrect abstention 0.0, scope containment 1.0), but reviewer burden criteria and manifest-first targeted density missed thresholds, so transfer is partial rather than full success.
  - evidence: `/mnt/data/Sindri/evals/phase11_adjacent_lane_transfer/last_results.json`; `/mnt/data/Sindri/docs/phase11_adjacent_lane_transfer_report.md`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['abstention', 'adjacent', 'bounded', 'burden', 'cases', 'containment', 'criteria', 'first', 'full', 'incorrect', 'lane', 'passes', 'phase', 'promotion', 'remains', 'results', 'reviewer', 'safety', 'scope', 'sindri', 'slice', 'transfer', 'trust', 'unsafe', 'verdict', 'wrapper']
- `3fa9a04c-b3b0-4385-b5aa-3fc4a2469a01` Phase 10 graduation validation sequence for wrapper lane
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `runbook` updated: `2026-04-05 01:53:40`
  - summary: Phase10 validation extends the trust suite with phase10 check/run commands and script while keeping prior phase checks intact.
  - body excerpt: Canonical sequence now includes: make lint; make test; eval checks for runner/phase35/phase4/pilot/phase7/phase8/phase9/phase10; full runs for pilot/phase7/phase8/phase9/phase10; make trust_regression_check; make eval; wrapper scripts for pilot through phase10 in --check and run modes. The phase10 outputs are evals/phase10_pilot_graduation/last_results.json and docs/phase10_pilot_graduation_report.md.
  - evidence: `/mnt/data/Sindri/scripts/run_trust_regression_check.sh`; `/mnt/data/Sindri/scripts/run_phase10_pilot_graduation.sh`; `/mnt/data/Sindri/evals/phase10_pilot_graduation/runner.py`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['check', 'checks', 'eval', 'full', 'graduation', 'lane', 'lint', 'make', 'outputs', 'phase', 'phase10', 'phase35', 'phase4', 'phase7', 'phase8', 'pilot', 'regression', 'results', 'runbook', 'scripts', 'sindri', 'trust', 'while', 'wrapper']
- `ed1e4d35-42c5-4824-86c4-42d06a29a95a` Phase 9 manifest-first calibration validation and execution path
  - stage: `recent_in_scope_supplement` reason: `recent_project_boundary_or_contract` kind: `runbook` updated: `2026-04-05 01:24:18`
  - summary: Phase 9 requires running baseline lint/tests/checks, pilot/phase7/phase8/phase9 runners, trust regression helper, and lane scripts to regenerate deterministic manifest-first analysis artifacts.
  - body excerpt: Core run sequence: make lint; make test; phase check runners for evals/runner.py, phase35, phase4, pilot wrapper, phase7, phase8, phase9; run make trust_regression_check; run make eval; run scripts/run_pilot_wrapper_lane.sh, scripts/run_phase7_reviewer_burden.sh, scripts/run_phase8_targeted_review_calibration.sh, scripts/run_phase9_manifest_first_calibration.sh in --check and full modes. Canonical outputs include evals/phase9_manifest_first_calibration/last_results.json and docs/phase9_manifest_first_calibration_report.md.
  - evidence: `/mnt/data/Sindri/evals/phase9_manifest_first_calibration/runner.py`; `/mnt/data/Sindri/scripts/run_trust_regression_check.sh`; `/mnt/data/Sindri/scripts/run_phase9_manifest_first_calibration.sh`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['baseline', 'burden', 'calibration', 'check', 'checks', 'deterministic', 'eval', 'first', 'full', 'helper', 'lane', 'lint', 'make', 'outputs', 'phase', 'phase35', 'phase4', 'phase7', 'phase8', 'pilot', 'regression', 'results', 'review', 'reviewer', 'runbook', 'runners', 'scripts', 'sindri', 'tests', 'trust', 'wrapper']
- `f87a7fb3-fdb2-4baf-bed2-4d03d6aaf543` Phase 9 narrows manifest-first override friction with handoff-first calibration
  - stage: `recent_in_scope_supplement` reason: `recent_query_token_overlap` kind: `decision` updated: `2026-04-05 01:24:11`
  - summary: Phase 9 adds manifest-first cluster analysis, manifest-specific override reasons, and first-inspection handoff refinement to reduce targeted-review overrides without widening scope. Safety posture stays intact with unsafe promotion and incorrect abstention at 0.0 on the phase9 slice.
  - body excerpt: Implemented a narrow calibration against the dominant manifest-first targeted-review disagreement residue. Added dedicated phase9 eval corpus and runner, manifest-first cluster artifact generation, and review/verifier refinements focused on manifest.json first-check clarity. Validation suite including trust regression helper passed end-to-end. Phase9 slice reports disagreement and override-heavy rates reduced versus phase8 reference while preserving blocker/ambiguity guardrails.
  - evidence: `/mnt/data/Sindri/evals/phase9_manifest_first_calibration/last_results.json`; `/mnt/data/Sindri/docs/phase9_manifest_first_calibration_report.md`; `1810311`
  - explanation: sources=['query_tokens', 'title_summary_tokens', 'primary_result_domain_tokens'] tokens=['abstention', 'adds', 'ambiguity', 'artifact', 'blocker', 'calibration', 'check', 'dedicated', 'disagreement', 'eval', 'first', 'guardrails', 'handoff', 'helper', 'implemented', 'incorrect', 'inspection', 'lane', 'narrow', 'passed', 'phase', 'phase8', 'posture', 'preserving', 'promotion', 'reduce', 'reference', 'regression', 'results', 'review', 'safety', 'scope', 'sindri', 'slice', 'trust', 'unsafe', 'while', 'wrapper']

## Evidence / Provenance

- Evidence refs available on preview cards: 23
- Evidence refs included in report: 23
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

- Primary match: Phase 5 adds machine-gated trust outputs for flagship wrapper lane - Sindri now emits structured promotion-gate results and safe operator summaries for wrapper-lane jobs, and uses calibrated posture mapping to distinguish caveat, patch-before, abstain, and blocking outcomes.
- Primary match: Trust regression surface helper command for wrapper-lane calibration - Phase 8.5 adds a single helper command to run lint/tests and trust check runners required for non-regressive calibration passes.
- Primary match: Phase 10 graduates wrapper lane with explicit criteria gate - Sindri Phase 10 adds explicit graduation criteria and a dedicated assessment slice for capability_wrapper_scaffold, yielding a graduate_lane verdict while preserving trust guardrails.
- Continuity: Phase 11 transfer validation sequence - Phase 11 transfer proving requires full trust regression checks plus the dedicated phase11 runner check/run.
- Continuity: Phase 11 adjacent-lane transfer verdict is partial - Adjacent parser/transform lane transfer passes safety and containment but remains burden-heavy. Verdict is transfer_partial with wrapper lane retained as stable control.
- Continuity: Phase 10 graduation validation sequence for wrapper lane - Phase10 validation extends the trust suite with phase10 check/run commands and script while keeping prior phase checks intact.
- Continuity: Phase 9 manifest-first calibration validation and execution path - Phase 9 requires running baseline lint/tests/checks, pilot/phase7/phase8/phase9 runners, trust regression helper, and lane scripts to regenerate deterministic manifest-first analysis artifacts.
- Continuity: Phase 9 narrows manifest-first override friction with handoff-first calibration - Phase 9 adds manifest-first cluster analysis, manifest-specific override reasons, and first-inspection handoff refinement to reduce targeted-review overrides without widening scope. Safety posture stays intact with unsafe promotion and incorrect abstention at 0.0 on the phase9 slice.
- Uncertainty: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback
