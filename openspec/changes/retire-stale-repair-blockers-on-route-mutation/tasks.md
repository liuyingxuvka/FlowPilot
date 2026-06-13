## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate the OpenSpec change and keep its scope to route-mutation cleanup.
- [x] 1.2 Verify the real FlowGuard package/project adoption and identify the owning route/repair models.

## 2. Runtime Lifecycle Fix

- [x] 2.1 Extend the existing route-mutation repair-open cleanup helper to retire older-route `repair_packet_open` blockers.
- [x] 2.2 Preserve current-version, nonnumeric-version, and already-dispositioned blockers unchanged.
- [x] 2.3 Reuse existing `superseded_by_route_mutation` metadata and event behavior.

## 3. Models And Tests

- [x] 3.1 Add runtime tests for older-route repair blocker retirement, current-version preservation, nonnumeric-version preservation, and idempotence.
- [x] 3.2 Update focused FlowGuard information-flow models/checks for stale-route-version repair blocker retirement.
- [x] 3.3 Update model-test alignment evidence for the new runtime test.

## 4. Validation, Sync, And Git

- [x] 4.1 Run OpenSpec validation, focused pytest/unittest coverage, FlowGuard checks, model-test alignment, and topology build/check.
- [x] 4.2 Sync repository-owned FlowPilot files to the installed local skill and run install audits/checks.
- [x] 4.3 Commit the completed local changes without reverting peer-agent work.
