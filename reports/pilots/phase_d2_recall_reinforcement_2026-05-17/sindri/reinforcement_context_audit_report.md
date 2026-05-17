# Phase D2 Reinforcement Context Audit: Sindri

Decision: `pass_with_residual_context_risk`

- Query: resume Sindri current wrapper-lane trust calibration state and next steps
- Event: `phase_d2_sindri_resume`
- Accepted fixture IDs: 8
- Suppressed fixture IDs: 1
- Replay counts: boosted=8, suppressed=1, preserved=17, decayed=0, neutral=0
- False suppressions: 0
- Suppression misses: 0
- Boosted-but-not-accepted: 0

## Diagnostic Retrieval Comparison

- Accepted top-12 baseline -> reinforced: 3 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Unclassified reinforced top-12 cards: 3

## Reinforced Top Results

- #1 `accepted` `e4dccb72-35fa-461b-9208-b08a9c28507d` Phase 5 adds machine-gated trust outputs for flagship wrapper lane (score 73.949023)
- #2 `accepted` `092f7e10-b6ab-43d2-9cbf-49ce08ff0b32` Trust regression surface helper command for wrapper-lane calibration (score 70.29422)
- #3 `accepted` `a2f4cb59-71d2-4131-8b7b-b030b8eaa342` Phase 10 graduates wrapper lane with explicit criteria gate (score 60.475599)
- #4 `accepted` `ed1e4d35-42c5-4824-86c4-42d06a29a95a` Phase 9 manifest-first calibration validation and execution path (score 49.24099)
- #5 `unclassified` `d5bf9668-d420-41c7-a7e4-0943e10d74cb` Phase 6 operationalizes wrapper-lane pilot telemetry and calibration signals (score 47.570377)
- #6 `unclassified` `40912dad-173e-4d7c-84db-0061e56dce95` Pilot wrapper-lane eval runbook for machine-gated trust (score 44.524289)
- #7 `accepted` `3fa9a04c-b3b0-4385-b5aa-3fc4a2469a01` Phase 10 graduation validation sequence for wrapper lane (score 43.50374)
- #8 `accepted` `f87a7fb3-fdb2-4baf-bed2-4d03d6aaf543` Phase 9 narrows manifest-first override friction with handoff-first calibration (score 39.212436)
- #9 `accepted` `6383fd96-30ca-4cfc-ab54-5c8fa7dd447a` Phase 11 adjacent-lane transfer verdict is partial (score 36.939777)
- #10 `unclassified` `b3ac4697-88c2-499e-9cbb-8b883cc91888` Phase 4 confirms calibration generalizes and flagship lane is pilot-ready (score 35.364446)

## Interpretation

Explicit Phase D2 suppressions are honored by derived state and by the optional adaptive scoring hook. Remaining unclassified results are not treated as failures unless they were part of the audited negative fixture; they are follow-up evidence for Phase D3 calibration.
