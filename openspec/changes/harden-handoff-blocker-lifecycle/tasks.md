## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate this OpenSpec change before implementation.
- [x] 1.2 Classify the live ProjectRadar stale blocker/handoff issue as a FlowGuard lifecycle model miss.
- [x] 1.3 Preserve the no-compatibility and no-new-field-mesh constraints.

## 2. FlowGuard Model Coverage

- [x] 2.1 Extend blocker-repair information-flow coverage for accepted noncurrent repair packets still blocking final preflight.
- [x] 2.2 Extend project-control information-flow coverage for producer handoff result, downstream authorized read, and final-preflight cleanup.
- [x] 2.3 Update model-test alignment coverage for the runtime and prompt obligations touched by this repair.

## 3. Runtime And Prompt Repair

- [x] 3.1 Make final return preflight ignore or report superseded/noncurrent repair blockers through the current-effective blocker filter.
- [x] 3.2 Extend route-mutation cleanup to supersede same-family noncurrent repair blockers without accepting historical evidence.
- [x] 3.3 Update PM, Reviewer, and FlowGuard Operator guidance for repeated missing-authorized-material failures and downstream handoff consumption.

## 4. Tests And Evidence

- [x] 4.1 Add focused runtime tests for old accepted repair packets not blocking final preflight.
- [x] 4.2 Add focused runtime tests for route mutation superseding same-family old repair blockers.
- [x] 4.3 Run targeted FlowGuard model checks and focused runtime/card tests.
- [x] 4.4 Rebuild/check topology after model/test/card/runtime changes.

## 5. Sync And Local Version

- [x] 5.1 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 5.2 Verify local install sync and install checks.
- [x] 5.3 Review git status, preserve peer-agent changes, and record the local repository version state.
