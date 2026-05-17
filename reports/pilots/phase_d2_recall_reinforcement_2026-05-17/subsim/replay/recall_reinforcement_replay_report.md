# Muninn v2 Recall Reinforcement Replay

- Mode: `offline_replay`
- v2 DB: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/subsim_phase_d2_shadow_v2.db`
- Dry run: `false`
- Write state: `true`
- As of: `2026-05-18T00:00:00Z`
- Scope key: `repo:363c13a65e92ef58`
- Eligible cards: 18
- Recall events: 1
- Boosted: 7
- Suppressed: 2
- Preserved: 6
- Decayed: 0
- Neutral: 3

## Top States

- `2fbc9cf8-118c-4a0d-84bc-a5ee90716adb` SubSim fire_control observation contract v1 status=`boosted` score=`3.797357`
- `5e260af6-8b17-427f-832d-028fae69d295` Hydrophone fixed eval and acoustic fixtures status=`boosted` score=`3.797357`
- `66312a31-2eca-4931-8f28-ae75a2dc7411` Campaign 004A leaves SubSim fire-control physics unchanged status=`boosted` score=`3.797357`
- `4d5faed6-e51e-4bc1-8ca1-8ebedcbc18d9` Hydrophone fixtures feed ReadyPlayer1 acoustic clutter scoring status=`boosted` score=`3.747357`
- `8d0704f3-2903-44df-937c-c80902b20f64` SubSim x ReadyPlayer1 campaign ledger checkpoint updated through Campaign 003 status=`boosted` score=`3.747357`
- `f94af521-4f75-4f42-b9d6-8a10b66d4a0d` SubSim Campaign 004A preserved gameplay while ReadyPlayer1 improved fire-control policy status=`boosted` score=`3.747357`
- `fb91d94b-b9e2-4bd8-a970-ff315747cd2d` SubSim sonar tracks expose explicit lifecycle state status=`boosted` score=`3.747357`
- `518a6ff0-75ef-4daa-86c2-a3dd7c6a8be6` Renderer Params v1 and first hybrid acoustic renderer implemented from hydrophone analysis status=`preserved` score=`1.25`
- `a4659ce9-bcf2-4615-9c37-4c09601943ab` Hydrophone corpus expansion v2 status=`neutral` score=`1.19166`
- `1fff427d-0f12-44cd-a002-56f1516745fb` Bounded hydrophone pipeline status=`neutral` score=`1.191227`
- `bf3358a7-1331-40f4-8943-778fb2a179c6` Add isolated machine-readable sonar console module for AI playtesting status=`preserved` score=`1.15`
- `ec85f42c-c39b-4c01-97f8-675ec09a8a73` Desktop runtime now uses HybridAcousticRendererV1 with preset-pack control status=`preserved` score=`1.15`

## Safety

- Derived reinforcement state only.
- Canonical card truth is unchanged.
- v1 and live MCP defaults are untouched.
