# Muninn v2 Recall Reinforcement Replay

- Mode: `offline_replay`
- v2 DB: `reports/pilots/phase_d_recall_reinforcement_2026-05-17/lexi_phase_d_shadow_v2.db`
- Dry run: `false`
- Write state: `true`
- As of: `2026-05-17T23:00:00Z`
- Scope key: `repo:0c321b2a6f183a95`
- Eligible cards: 77
- Recall events: 1
- Boosted: 3
- Suppressed: 1
- Preserved: 73
- Decayed: 0
- Neutral: 0

## Top States

- `539f6130-6a78-4646-b7fe-da1d2a7d0b98` Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline status=`boosted` score=`3.746697`
- `8099af8a-88e6-4e88-b1c9-684c4ea5aa4e` Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling status=`boosted` score=`3.746697`
- `d61eacef-96d5-40fb-9dc4-5de8c11399c1` Lexi production audit verdict 2026-05-17 status=`boosted` score=`3.746697`
- `a4acf04b-a974-4320-8656-0546edc000f3` Lex vLLM service constrained to GPUs 0 and 1 with reduced context for stable startup status=`preserved` score=`1.15`
- `0734933b-cd2c-48ee-b6d4-d10114131382` Adaptive Dreamer Curriculum v1 is the canonical DreamerV2 sidecar path status=`preserved` score=`1.1`
- `6b4c21ae-25bc-4b56-81c4-4eaa0750afdb` Lex live avatar generation is queue-saturated and not using durable per-user avatar ownership status=`preserved` score=`1.1`
- `6e97a92a-84e7-423f-844c-927bd48a7d21` DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau status=`preserved` score=`1.1`
- `58fff1bd-db2d-497e-a028-510fd79d2d0c` DreamerV2 GPU-3 sidecar is running but appears replay-stalled and missing ffmpeg for summaries status=`preserved` score=`1.05`
- `796edb34-b4e0-4b79-b161-f715bd837228` Lex added a shadow-only bounded world-model harness around /lexi/process status=`preserved` score=`1.05`
- `cff2e813-64c0-485a-b7e5-f41941f13b94` Althing/Friday router evaluation chose custom minimal harness now, with Harbor as later outer-runner path status=`preserved` score=`1.05`
- `e5d3b5b9-405f-4627-a379-b883c0405a9a` Qwen3.6-27B swap test blocked on current Lex vLLM stack; reverted to known-good Lexi model status=`preserved` score=`1.05`
- `ee6b8b6a-ad7d-4db0-8a42-5498afc22719` TP=1 DP=8 expert-parallel experiment for Qwen3.5 failed and Lexi was reverted to original Qwen-Lex 3 runtime status=`preserved` score=`1.05`

## Safety

- Derived reinforcement state only.
- Canonical card truth is unchanged.
- v1 and live MCP defaults are untouched.
