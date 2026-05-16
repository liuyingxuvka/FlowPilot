## 1. Model Gate

- [x] 1.1 Verify real FlowGuard is importable.
- [x] 1.2 Update focused FlowGuard/liveness checks or hazards so missing Controller postconditions are expected to stay on direct mechanical reissue until retry exhaustion.
- [x] 1.3 Run the focused FlowGuard checks and record Meta/Capability skips by user direction.

## 2. Runtime Fix

- [x] 2.1 Patch blocker classification for `controller_action_receipt_missing_router_postcondition`.
- [x] 2.2 Patch responsible-role fallback so this source does not default to PM before retry exhaustion.
- [x] 2.3 Normalize direct retry exhaustion metadata for zero-budget blockers.

## 3. Tests And Sync

- [x] 3.1 Add focused runtime tests for first issue, within-budget retry, retry exhaustion, and unrelated PM/fatal blockers.
- [x] 3.2 Run focused router tests, OpenSpec validation, py-compile, and install checks.
- [x] 3.3 Sync the installed FlowPilot skill from the repository and verify installed freshness.
- [x] 3.4 Update FlowGuard adoption notes and KB postflight.
