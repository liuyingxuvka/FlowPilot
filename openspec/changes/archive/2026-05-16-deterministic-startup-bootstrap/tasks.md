## 1. Model Hardening Gate

- [x] 1.1 Add or update a FlowGuard model for deterministic startup bootstrap ordering.
- [x] 1.2 Add hazards for scheduler-before-seed, seed-success-with-missing-artifacts, deterministic setup left as Controller rows, seed failure as PM blocker, and scheduler bypass for role/heartbeat/core work.
- [x] 1.3 Extend daemon reconciliation checks so already reconciled rows are idempotently skipped and cannot emit PM blockers.
- [x] 1.4 Run focused FlowGuard checks and record that Meta/Capability heavyweight simulations are skipped by user direction.

## 2. Deterministic Bootstrap Seed

- [x] 2.1 Refactor bootstrap seed code to create run shell, current pointer, run index, runtime directories, and empty ledgers directly.
- [x] 2.2 Move placeholder filling, mailbox initialization, user-request reference recording, and user-intake scaffold creation into the seed.
- [x] 2.3 Write bootstrap evidence for every deterministic artifact and fail startup before route activation if any required artifact is missing.
- [x] 2.4 Add focused tests for successful seed creation and startup failure before PM blocker on seed failure.

## 3. Unified Scheduler Boundary

- [x] 3.1 Remove deterministic setup actions from daemon-scheduled startup Controller rows.
- [x] 3.2 Keep role-slot startup, heartbeat binding when requested, and Controller core loading as unified scheduler rows.
- [x] 3.3 Update scheduler/startup tests to assert deterministic setup is seed evidence, not Controller ledger work.

## 4. Unified Reconciliation

- [x] 4.1 Simplify startup scheduled row completion so it uses the generic receipt/postcondition reconciler.
- [x] 4.2 Add an idempotent guard: already reconciled action or scheduler row is skipped before blocker creation.
- [x] 4.3 Add regression tests for the `initialize_mailbox` false PM blocker class and for a real unsatisfied postcondition blocker.

## 5. Sync And Final Verification

- [x] 5.1 Run focused runtime tests after each implementation slice.
- [x] 5.2 Run install sync and freshness checks for the local FlowPilot skill.
- [x] 5.3 Update FlowGuard adoption logs and KB postflight.
- [x] 5.4 Prepare local git state with all intended changes while preserving peer-agent work.
