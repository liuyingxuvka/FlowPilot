## 1. FlowGuard Model Updates

- [x] 1.1 Add the observed model-miss obligation for FlowGuard pass with blocked child evidence.
- [x] 1.2 Extend the field contract model with child hard evidence status projection into FlowGuard result outcome and Reviewer handoff.
- [x] 1.3 Extend information-flow alignment so FlowGuard reports cannot become Reviewer input unless evidence consistency passes.
- [x] 1.4 Extend model-test alignment obligations with owner code contracts and ordinary tests for the consistency gate.

## 2. Runtime Contract Implementation

- [x] 2.1 Add a focused FlowGuard result evidence-consistency checker in the current packet result path.
- [x] 2.2 Reject `flowguard_check` results whose top-level `passed` conflicts with contract self-check booleans.
- [x] 2.3 Reject `flowguard_check` results whose top-level `passed` conflicts with machine-readable blocked child evidence status.
- [x] 2.4 Ensure rejected inconsistent FlowGuard results do not record a passed work order or issue a Reviewer packet.
- [x] 2.5 Ensure route mutation that quarantines an open repair packet records a terminal disposition on the prior repair-open blocker.

## 3. Regression Coverage

- [x] 3.1 Add unit tests for failed self-check, blocked child evidence, and no Reviewer dispatch after rejection.
- [x] 3.2 Add fake AI chaos coverage for current-shaped contradictory FlowGuard results.
- [x] 3.3 Add synthetic or historical replay coverage for the observed blocked-child-report failure family.
- [x] 3.4 Preserve old-shape rejection tests and no-fallback negative coverage.
- [x] 3.5 Add runtime and model-test-alignment coverage for superseded repair-open blockers after route mutation.

## 4. Validation And Active-Run Recovery

- [x] 4.1 Run targeted runtime, fake AI, and synthetic replay tests.
- [x] 4.2 Run affected FlowGuard model checks and model-test alignment checks.
- [x] 4.3 Rebuild and check FlowGuard project topology after model/test/code changes.
- [x] 4.4 Run install/sync audits required by the repository.
- [x] 4.5 Inspect the two active FlowPilot runs after the fix and, if needed, use current-protocol action to push blocked runs back to the corrected path.
