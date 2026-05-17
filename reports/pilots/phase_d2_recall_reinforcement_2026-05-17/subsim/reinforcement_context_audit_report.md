# Phase D2 Reinforcement Context Audit: SubSim

Decision: `pass_with_residual_context_risk`

- Query: resume SubSim current ReadyPlayer1 campaign integration state and next steps
- Event: `phase_d2_subsim_resume`
- Accepted fixture IDs: 7
- Suppressed fixture IDs: 2
- Replay counts: boosted=7, suppressed=2, preserved=6, decayed=0, neutral=3
- False suppressions: 0
- Suppression misses: 0
- Boosted-but-not-accepted: 0

## Diagnostic Retrieval Comparison

- Accepted top-12 baseline -> reinforced: 6 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Unclassified reinforced top-12 cards: 1

## Reinforced Top Results

- #1 `accepted` `8d0704f3-2903-44df-937c-c80902b20f64` SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003 (score 96.294069)
- #2 `accepted` `f94af521-4f75-4f42-b9d6-8a10b66d4a0d` SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy (score 88.027687)
- #3 `accepted` `66312a31-2eca-4931-8f28-ae75a2dc7411` Campaign 004A leaves SubSim fire-control physics unchanged (score 87.699669)
- #4 `accepted` `2fbc9cf8-118c-4a0d-84bc-a5ee90716adb` SubSim fire_control observation contract v1 (score 67.437106)
- #5 `accepted` `4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9` Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring (score 60.804168)
- #6 `accepted` `fb91d94b-b9e2-4bd8-a970-ff315747cd2d` SubSim sonar tracks expose explicit lifecycle state (score 55.721887)
- #7 `unclassified` `12583c95-c343-4350-bae7-0b882ed70d96` Campaign 001 sonar clutter readability producer behavior (score 44.402448)
- #8 `accepted` `5e260af6-8b17-427f-832d-028fae69d295` Hydrophone fixed eval and acoustic fixtures (score 40.567853)

## Interpretation

Explicit Phase D2 suppressions are honored by derived state and by the optional adaptive scoring hook. Remaining unclassified results are not treated as failures unless they were part of the audited negative fixture; they are follow-up evidence for Phase D3 calibration.
