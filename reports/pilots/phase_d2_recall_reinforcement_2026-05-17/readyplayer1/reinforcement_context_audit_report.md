# Phase D2 Reinforcement Context Audit: ReadyPlayer1

Decision: `pass_with_residual_context_risk`

- Query: resume ReadyPlayer1 current campaign state and next steps
- Event: `phase_d2_readyplayer1_resume`
- Accepted fixture IDs: 7
- Suppressed fixture IDs: 3
- Replay counts: boosted=7, suppressed=3, preserved=36, decayed=0, neutral=2
- False suppressions: 0
- Suppression misses: 0
- Boosted-but-not-accepted: 0

## Diagnostic Retrieval Comparison

- Accepted top-12 baseline -> reinforced: 6 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Unclassified reinforced top-12 cards: 5

## Reinforced Top Results

- #1 `accepted` `eed995dd-60bf-4bd6-b678-9541501d5b5d` Phase 2 canonical current-state pointers and onboarding source consolidation (score 95.663091)
- #2 `accepted` `bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44` Campaign 005A promoted fire-control state normalization (score 93.168438)
- #3 `accepted` `1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0` Campaign 004A promoted with ReadyPlayer1 fire-control loop patch (score 84.728124)
- #4 `accepted` `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted (score 71.924636)
- #5 `accepted` `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (score 71.852296)
- #6 `accepted` `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (score 71.809743)
- #7 `unclassified` `b045f7d1-a009-4883-b194-935622d7cd12` RSSM v2 governed-resume workflow is now operational with consolidated operator view (score 60.534396)
- #8 `unclassified` `6c405f42-8fb5-4735-8bad-fcd2f5b71908` State-space continuity refinement v3 added as canonical RL ablation lane (score 60.377638)
- #9 `accepted` `fb80c2a4-3025-4a64-bd60-3cbf7484b2d2` SubSim ReadyPlayer1 evaluation contract v1 documented (score 58.722863)
- #10 `unclassified` `4be809aa-731f-420c-8dc1-99cb5813c0ea` Campaign 002A promoted for SubSim sonar lifecycle diagnostics (score 57.438632)
- #11 `unclassified` `8564b6a1-ddf1-4150-a709-d4b485db1893` RSSM v2 canonical lane baseline pinned to 6 validated / 1 monitored and registry-driven defaults (score 55.113068)
- #12 `unclassified` `f5021943-807e-4015-a4d6-a24e1f8b8db4` Campaign 001 promoted on belief_baseline clutter evidence (score 54.588933)

## Interpretation

Explicit Phase D2 suppressions are honored by derived state and by the optional adaptive scoring hook. Remaining unclassified results are not treated as failures unless they were part of the audited negative fixture; they are follow-up evidence for Phase D3 calibration.
