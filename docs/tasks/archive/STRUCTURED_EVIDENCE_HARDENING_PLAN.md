Status: completed

## Objective
Eliminate recurring structured-evidence warnings by hardening caller-side evidence construction and validation for Friday lifecycle/procedure writeback, while keeping Muninn evidence schema strict.

## Scope
In:
- `/mnt/data/Muninn` evidence contract visibility, warning specificity (if needed), tests, docs.
- `/mnt/data/friday` canonical evidence DTO/builder + local validation + write path integration + tests.
- Cross-repo contract alignment for `muninn.cards.upsert` evidence payloads.

Out:
- Broad schema redesign of Muninn cards.
- Any loosening/coercive acceptance of malformed evidence in Muninn.
- Non-related feature work.

## Checklist
- [x] Confirm actual Muninn evidence schema, enforcement mechanism, and warning emission path.
- [x] Capture one real Friday lifecycle/procedure payload currently sent to Muninn.
- [x] Identify exact mismatch between Friday payload and Muninn schema.
- [x] Implement canonical typed evidence builder/validator in Friday integration layer.
- [x] Narrow Friday Muninn transport path to validated canonical evidence only.
- [x] Add/extend Muninn tests for valid/invalid structured evidence behavior and warning specificity.
- [x] Add/extend Friday tests for builder correctness, invalid input rejection, and no-warning writeback path.
- [x] Update contract docs in Muninn and Friday.
- [x] Run targeted tests in both repos and record results.

## Rollback Plan
- Revert Friday evidence builder/path changes and related tests if integration regressions appear.
- Revert Muninn warning-message/test adjustments if they break backward-compatible expectations.
- Keep Muninn schema strictness unchanged throughout.

## Test Plan
- Muninn:
  - evidence payload accepted with canonical shape
  - malformed evidence rejected with precise validation details
  - warning behavior remains limited to missing evidence for preferred kinds
- Friday:
  - lifecycle/procedure evidence builder emits Muninn-valid `evidence[]`
  - malformed evidence input fails local validation before transport
  - writeback path sends canonical evidence and does not trigger structured-evidence warning
