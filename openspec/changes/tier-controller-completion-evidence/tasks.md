## 1. OpenSpec And Model

- [x] 1.1 Finalize the four-tier OpenSpec contract for Router-owned state, nonblocking display work, external continuation actions, and role-output decisions.
- [x] 1.2 Update the control-plane FlowGuard model and hazards for nonblocking display/status work and strict role-output decisions.

## 2. Router Implementation

- [x] 2.1 Remove hard `visible_plan_synced` postconditions from display sync actions while preserving soft `visible_plan_sync` and compatibility flags.
- [x] 2.2 Keep hard lightweight confirmation for continuation-critical external actions.
- [x] 2.3 Preserve file-backed role-output validation for PM repair decisions and other semantic role decisions.

## 3. Tests, Sync, And Git

- [x] 3.1 Add focused router runtime tests for nonblocking display sync and existing role-output rejection behavior.
- [x] 3.2 Run focused FlowGuard checks, router tests, and install checks; launch heavyweight model regressions in background when required.
- [x] 3.3 Sync the local installed FlowPilot skill and verify source freshness.
- [x] 3.4 Stage and commit this work together with the parallel AI changes the user wants preserved.
