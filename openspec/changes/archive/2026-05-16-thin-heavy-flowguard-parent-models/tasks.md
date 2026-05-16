## 1. OpenSpec and FlowGuard Preflight

- [x] 1.1 Validate the OpenSpec artifacts and confirm this change is apply-ready.
- [x] 1.2 Verify the real FlowGuard package is importable and record the trigger boundary.
- [x] 1.3 Recheck coordination/git status before production edits and preserve peer-agent work.

## 2. Parent Responsibility Ledger

- [x] 2.1 Add a machine-readable Meta/Capability parent responsibility ledger with partition, invariant-family, owner, evidence, and release-obligation fields.
- [x] 2.2 Add ledger validation that rejects uncovered partitions, duplicate unsafe ownership, missing child evidence, hidden skipped checks, and stale evidence.

## 3. Thin Parent Evidence Path

- [x] 3.1 Add a thin parent helper/model that reads child evidence contracts without expanding child or legacy parent state graphs.
- [x] 3.2 Add thin Meta and Capability result/proof output with explicit result type and release-confidence boundary.
- [x] 3.3 Preserve legacy full Meta and Capability graph exploration behind explicit forced/full execution modes.

## 4. Hierarchy and Validation Integration

- [x] 4.1 Update hierarchy inventory to distinguish thin parent, full legacy, proof reuse, and incomplete background evidence.
- [x] 4.2 Update smoke, install, and coverage-sweep validation to run thin parent checks in foreground while keeping full regressions as background/forced obligations.
- [x] 4.3 Add focused tests for default thin behavior, forced full behavior, stale evidence rejection, and release-confidence boundaries.

## 5. Background Regression and Sync

- [x] 5.1 Launch full Meta and Capability regressions in the background using the standard log artifact contract.
- [x] 5.2 Run focused foreground checks and inspect background artifacts before making release-level claims.
- [x] 5.3 Sync the installed FlowPilot skill from the repository and verify source freshness.

## 6. Final Integration

- [x] 6.1 Recheck git status, include compatible peer-agent changes, and avoid reverting unrelated work.
- [x] 6.2 Record FlowGuard adoption notes and predictive KB postflight observations.
- [x] 6.3 Commit the integrated local git version after validation and sync are complete.
