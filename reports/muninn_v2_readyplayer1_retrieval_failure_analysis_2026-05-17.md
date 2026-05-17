# Muninn v2 ReadyPlayer1 Retrieval Failure Analysis

Date: 2026-05-17

## Summary

- Retrieval eval cases: 10
- Expected records: 22
- Hit records: 12
- Mean recall at limit: `0.666667`
- Record absent count: 0
- Retrieval mismatch count: 10
- Extra result count: 88
- Recall parity average overlap: `0.1148`

This is retrieval/scoring/windowing failure, not migration loss. All expected records exist in v2.

## Root Causes

- v2 eval used vector-only results whenever a derived index existed, so precise lexical/title hits could be displaced by hash-vector similarity.
- The fallback vector index is deterministic but too weak for short metric/taxonomy queries and campaign-specific variants.
- Broad domain tokens such as sonar, clutter, reacquisition, rate, and ReadyPlayer1 flood top-10 windows without enough specificity penalty.
- Campaign/numeric/version tokens and title phrase matches need stronger explicit boosts.

## Weakest Cases

- `sonar-clutter-wrong-binding-rate` (sonar clutter wrong binding rate): recall=0.0 classification=broad token flood, body underweighted, title underweighted, vector fallback too weak, missing numeric/token handling
- `acoustic-clutter-wrong-binding-rate` (acoustic clutter wrong binding rate): recall=0.333333 classification=broad token flood, body underweighted, vector fallback too weak, missing numeric/token handling
- `reacquisition-failure-taxonomy` (reacquisition failure taxonomy): recall=0.333333 classification=broad token flood, vector fallback too weak, title underweighted, body underweighted
- `torpedo-wasted-shot-rate` (torpedo wasted shot rate): recall=0.5 classification=broad token flood, vector fallback too weak, missing numeric/token handling
- `readyplayer1-next-campaign-recommendation` (ReadyPlayer1 next campaign recommendation): recall=0.5 classification=broad token flood, body underweighted, vector fallback too weak

## Per-Query Findings

### Campaign 007A post-reacquisition belief stabilization

- case: `campaign-007a-post-reacquisition-stabilization`
- status: `pass`
- recall@limit: `1.0`
- expected exists in v2: `true`
- hits: 1
- misses: 0
- extras: 9
- classification: pass

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=1, vector_rank=2)

Top result IDs:
- v1: 0afb7524
- v2 lexical: 0afb7524, fbcac688, f5021943, 719fafb5, 1eb0763c, 4be809aa, 2656c35f, bef388b3, 8db59c21, a44681f9
- v2 vector/fallback: fbcac688, 0afb7524, ab7fcfef, 8db59c21, b045f7d1, 4c81a807, 4be809aa, 5dc2dbe5, 34bc2a67, 6a914585

### Campaign 006A early active ping reacquisition

- case: `campaign-006a-early-active-ping-reacquisition`
- status: `pass`
- recall@limit: `1.0`
- expected exists in v2: `true`
- hits: 1
- misses: 0
- extras: 9
- classification: pass

Expected records:
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (evidence=4, lexical_rank=1, vector_rank=1)

Top result IDs:
- v1: fbcac688
- v2 lexical: fbcac688, 0afb7524, 719fafb5, f5021943, 4be809aa, 1eb0763c, bef388b3, 2656c35f, a96ab62a, 8db59c21
- v2 vector/fallback: fbcac688, 1eb0763c, 2656c35f, 719fafb5, 4be809aa, c988cfd8, 703b5352, 4c81a807, 34bc2a67, 0afb7524

### Campaign 005A fire-control state normalization

- case: `campaign-005a-fire-control-state-normalization`
- status: `pass`
- recall@limit: `1.0`
- expected exists in v2: `true`
- hits: 1
- misses: 0
- extras: 9
- classification: pass

Expected records:
- `bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44` Campaign 005A promoted fire-control state normalization (evidence=4, lexical_rank=1, vector_rank=2)

Top result IDs:
- v1: bef388b3
- v2 lexical: bef388b3, 1eb0763c, 719fafb5, fbcac688, 4be809aa, 0afb7524, fcdf1422, 6c405f42, f5021943, 934bc660
- v2 vector/fallback: 1eb0763c, bef388b3, 719fafb5, fbcac688, 6a914585, 2656c35f, 703b5352, 934bc660, 6c405f42, 8db59c21

### Campaign 004A duplicate same-primary torpedo suppression

- case: `campaign-004a-duplicate-same-primary-torpedo-suppression`
- status: `pass`
- recall@limit: `1.0`
- expected exists in v2: `true`
- hits: 2
- misses: 0
- extras: 8
- classification: pass

Expected records:
- `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted (evidence=5, lexical_rank=2, vector_rank=3)
- `1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0` Campaign 004A promoted with ReadyPlayer1 fire-control loop patch (evidence=3, lexical_rank=1, vector_rank=1)

Top result IDs:
- v1: none
- v2 lexical: 1eb0763c, 719fafb5, 0afb7524, fbcac688, 2656c35f, 8db59c21, bef388b3, f5021943, 4be809aa, 6a914585
- v2 vector/fallback: 1eb0763c, bef388b3, 719fafb5, fbcac688, 81ffce0a, a44681f9, 5af5de69, 6a914585, 2b2f8c21, 2656c35f

### fire control ready but hold count

- case: `fire-control-ready-but-hold-count`
- status: `pass`
- recall@limit: `1.0`
- expected exists in v2: `true`
- hits: 2
- misses: 0
- extras: 8
- classification: pass

Expected records:
- `bef388b3-b3d2-4d14-ae7c-bda5b0fb4d44` Campaign 005A promoted fire-control state normalization (evidence=4, lexical_rank=3, vector_rank=3)
- `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted (evidence=5, lexical_rank=2, vector_rank=2)

Top result IDs:
- v1: fbcac688
- v2 lexical: 1eb0763c, 719fafb5, bef388b3, fcdf1422, c7a9d5cf, 1b486cc7, 934bc660, c988cfd8, 57514758, a914d42e
- v2 vector/fallback: 1eb0763c, 719fafb5, bef388b3, 2cc8e63b, fbcac688, c7a9d5cf, e1959e49, 2b2f8c21, ec3b5350, 6c405f42

### torpedo wasted shot rate

- case: `torpedo-wasted-shot-rate`
- status: `fail`
- recall@limit: `0.5`
- expected exists in v2: `true`
- hits: 2
- misses: 2
- extras: 8
- classification: broad token flood, vector fallback too weak, missing numeric/token handling

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=6, vector_rank=None)
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (evidence=4, lexical_rank=2, vector_rank=1)
- `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted (evidence=5, lexical_rank=1, vector_rank=9)
- `1eb0763c-9d10-446c-9ca0-e4ef2ac02cb0` Campaign 004A promoted with ReadyPlayer1 fire-control loop patch (evidence=3, lexical_rank=5, vector_rank=None)

Top result IDs:
- v1: fbcac688, 719fafb5, 1eb0763c, 0afb7524
- v2 lexical: 719fafb5, fbcac688, 4c81a807, 85fa6620, 1eb0763c, 0afb7524, 405c83a3, 96dc449d, 8db59c21, 5dc2dbe5
- v2 vector/fallback: fbcac688, 34bc2a67, 39a11e88, 96dc449d, 6c405f42, b6db9c8b, f5021943, fb80c2a4, 719fafb5, 5dc2dbe5

### sonar clutter wrong binding rate

- case: `sonar-clutter-wrong-binding-rate`
- status: `fail`
- recall@limit: `0.0`
- expected exists in v2: `true`
- hits: 0
- misses: 3
- extras: 10
- classification: broad token flood, body underweighted, title underweighted, vector fallback too weak, missing numeric/token handling

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=None, vector_rank=None)
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (evidence=4, lexical_rank=None, vector_rank=None)
- `2656c35f-79af-403d-9128-e98fc72663d6` Campaign 003 promoted for SubSim clutter binding (evidence=4, lexical_rank=2, vector_rank=None)

Top result IDs:
- v1: 2656c35f, 0afb7524, fbcac688, 719fafb5
- v2 lexical: 8db59c21, 2656c35f, 4be809aa, 4c81a807, 405c83a3, 9379dfbe, a44681f9, 5dc2dbe5, f5021943, 719fafb5
- v2 vector/fallback: 5dc2dbe5, e1959e49, a44681f9, caff839c, 8db59c21, 703b5352, b045f7d1, 85fa6620, f5021943, 96dc449d

### acoustic clutter wrong binding rate

- case: `acoustic-clutter-wrong-binding-rate`
- status: `fail`
- recall@limit: `0.333333`
- expected exists in v2: `true`
- hits: 1
- misses: 2
- extras: 9
- classification: broad token flood, body underweighted, vector fallback too weak, missing numeric/token handling

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=None, vector_rank=None)
- `8db59c21-0224-4ef0-b628-f336867bf591` Campaign 003 acoustic clutter binding integrated (evidence=5, lexical_rank=1, vector_rank=1)
- `719fafb5-b25b-4460-a549-987799432a6c` Campaign 004A fire-control loop promoted (evidence=5, lexical_rank=6, vector_rank=None)

Top result IDs:
- v1: fbcac688, 0afb7524, 719fafb5
- v2 lexical: 8db59c21, 2656c35f, 4c81a807, 405c83a3, 9379dfbe, 719fafb5, 5dc2dbe5, 703b5352, ab7fcfef, fbcac688
- v2 vector/fallback: 8db59c21, 5dc2dbe5, 703b5352, ec3b5350, 85927e0f, b045f7d1, ab7fcfef, 4c81a807, c7a9d5cf, e1959e49

### reacquisition failure taxonomy

- case: `reacquisition-failure-taxonomy`
- status: `fail`
- recall@limit: `0.333333`
- expected exists in v2: `true`
- hits: 1
- misses: 2
- extras: 9
- classification: broad token flood, vector fallback too weak, title underweighted, body underweighted

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=3, vector_rank=None)
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (evidence=4, lexical_rank=8, vector_rank=5)
- `e1959e49-bc15-43ce-ac02-163ce98ea423` Failure taxonomy is now a first-class report surface for sonar runs (evidence=4, lexical_rank=1, vector_rank=None)

Top result IDs:
- v1: fbcac688
- v2 lexical: e1959e49, 6a914585, 0afb7524, a96ab62a, 2b2f8c21, fb80c2a4, 5dc2dbe5, fbcac688, 9379dfbe, 6c405f42
- v2 vector/fallback: 2b2f8c21, 703b5352, ec3b5350, 9379dfbe, fbcac688, 6a914585, 8db59c21, 34bc2a67, 4c81a807, 5dc2dbe5

### ReadyPlayer1 next campaign recommendation

- case: `readyplayer1-next-campaign-recommendation`
- status: `fail`
- recall@limit: `0.5`
- expected exists in v2: `true`
- hits: 1
- misses: 1
- extras: 9
- classification: broad token flood, body underweighted, vector fallback too weak

Expected records:
- `0afb7524-b5b6-4e78-9a56-a08915eb895e` Campaign 007A promoted post-reacquisition stabilization (evidence=4, lexical_rank=5, vector_rank=None)
- `fbcac688-f952-477f-87ca-ea7860c4f396` Campaign 006A promoted post-loss recovery probe (evidence=4, lexical_rank=4, vector_rank=6)

Top result IDs:
- v1: none
- v2 lexical: 1eb0763c, 719fafb5, bef388b3, fbcac688, 0afb7524, f5021943, 4be809aa, 2656c35f, fb80c2a4, 8db59c21
- v2 vector/fallback: 34bc2a67, 6c405f42, fcdf1422, 405c83a3, bef388b3, fbcac688, 2656c35f, 79b74025, 719fafb5, 4be809aa
