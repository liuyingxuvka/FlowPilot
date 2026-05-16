## 1. OpenSpec and FlowGuard

- [x] 1.1 Create proposal, design, and dispatch-recipient-gate spec.
- [x] 1.2 Add a focused FlowGuard dispatch-recipient-gate model.
- [x] 1.3 Run the focused model and preserve result evidence.

## 2. Router Implementation

- [x] 2.1 Add a Router helper that classifies role-facing dispatch actions.
- [x] 2.2 Add busy-recipient detection across pending ACKs, passive waits,
  packet ledger active holders, and PM role-work records.
- [x] 2.3 Route blocked dispatches to an existing or generated wait instead of
  exposing the new Controller row.
- [x] 2.4 Keep system-card bundles and different-role parallel dispatch valid.

## 3. Verification and Sync

- [x] 3.1 Add focused router runtime tests for busy same-role block, returned
  worker result freeing the worker, PM still busy for disposition, and grouped
  system-card bundle allowance.
- [x] 3.2 Run focused unit tests and focused FlowGuard checks.
- [x] 3.3 Run practical install/sync checks and update the local installed
  FlowPilot skill version.
- [x] 3.4 Record FlowGuard adoption notes and any skipped heavy checks.
- [x] 3.5 Leave Meta and Capability heavy simulations skipped with an explicit
  reason unless focused failures show their boundary is touched.
