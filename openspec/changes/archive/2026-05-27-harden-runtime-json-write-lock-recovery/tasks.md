## 1. Model And Tests

- [x] 1.1 Extend the persistent daemon FlowGuard model/checks for nested write-lock wait recovery and mechanical blocker classification.
- [x] 1.2 Add focused router runtime tests for replace-time `PermissionError`, nested `router_state.json` write-lock waits, and Controller action write-lock classification.

## 2. Runtime Implementation

- [x] 2.1 Normalize persistent `PermissionError` from atomic JSON replacement into `RouterLedgerWriteInProgress` with target path and lock metadata.
- [x] 2.2 Make daemon `RouterLedgerWriteInProgress` handling tolerate nested status/state write-lock waits without releasing the daemon lock as `daemon_error`.
- [x] 2.3 Keep runtime write-lock failures out of PM semantic repair routing until bounded runtime settlement/takeover has been attempted.

## 3. Validation And Sync

- [x] 3.1 Run focused FlowGuard checks and targeted router runtime tests.
- [x] 3.2 Sync the repo-owned FlowPilot skill into the local installed skill and run install/audit checks.
- [x] 3.3 Start heavyweight meta/capability regressions in the background and inspect final artifacts before reporting completion.
- [x] 3.4 Repair validation background-runner coverage issues found while launching Router regressions.
