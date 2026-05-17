# Phase D2 Reinforcement Context Audit: Lexi

Decision: `pass_with_residual_context_risk`

- Query: resume Lexi current production audit and runtime modernization state and next steps
- Event: `phase_d2_lexi_resume`
- Accepted fixture IDs: 7
- Suppressed fixture IDs: 1
- Replay counts: boosted=7, suppressed=1, preserved=69, decayed=0, neutral=0
- False suppressions: 0
- Suppression misses: 0
- Boosted-but-not-accepted: 0

## Diagnostic Retrieval Comparison

- Accepted top-12 baseline -> reinforced: 4 -> 7
- Suppressed top-12 baseline -> reinforced: 0 -> 0
- Unclassified reinforced top-12 cards: 5

## Reinforced Top Results

- #1 `accepted` `d61eacef-96d5-40fb-9dc4-5de8c11399c1` Lexi production audit verdict 2026-05-17 (score 126.159816)
- #2 `accepted` `6e97a92a-84e7-423f-844c-927bd48a7d21` DreamerV2 persistent sidecar still collects fresh episodes but current learning is near replay-gated plateau (score 72.304416)
- #3 `accepted` `6f25a3c0-676d-4e64-8351-213b18040f93` Lex modernization phases 1-5 checkpointed with validated auth/prompt/eval hardening (score 68.654723)
- #4 `accepted` `c40c8b59-4e43-4e9d-976a-0c27e289596c` Phase 5 runtime smoke proof completed for Lex modernization (score 60.904845)
- #5 `unclassified` `b56a0d1b-7eef-439a-821e-12b048fee950` AWQ checkpoint fallback is blocked on V100/sm_70 in current vLLM runtime (score 57.47465)
- #6 `unclassified` `82f73be8-e791-410b-b873-05dd572d061e` Lex avatar management currently mixes per-IP rendering with per-user state, with legacy persona routes taking precedence (score 56.329072)
- #7 `unclassified` `e5d3b5b9-405f-4627-a379-b883c0405a9a` Qwen3.6-27B swap test blocked on current Lex vLLM stack; reverted to known-good Lexi model (score 54.64157)
- #8 `unclassified` `6b93f328-be1a-4420-a852-b2733cdd0a87` Run shadow specialized-lane live validation with completeness audit (score 48.181485)
- #9 `accepted` `650e57d3-d07d-42c5-888d-28a0160fb224` Lex modernization phases 2A-4 hardened auth boundaries, prompt trust blocks, and eval gates (score 44.938747)
- #10 `accepted` `8099af8a-88e6-4e88-b1c9-684c4ea5aa4e` Phase 6 hardened runtime preflight, summarizer fallback, and startup lifecycle handling (score 42.731736)
- #11 `unclassified` `ee6b8b6a-ad7d-4db0-8a42-5498afc22719` TP=1 DP=8 expert-parallel experiment for Qwen3.5 failed and Lexi was reverted to original Qwen-Lex 3 runtime (score 41.850501)
- #12 `accepted` `539f6130-6a78-4646-b7fe-da1d2a7d0b98` Phase 6 runtime resilience checkpoint committed on top of Phase 1-5 baseline (score 40.527009)

## Interpretation

Explicit Phase D2 suppressions are honored by derived state and by the optional adaptive scoring hook. Remaining unclassified results are not treated as failures unless they were part of the audited negative fixture; they are follow-up evidence for Phase D3 calibration.
