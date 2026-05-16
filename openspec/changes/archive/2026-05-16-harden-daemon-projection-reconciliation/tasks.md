## 1. Paper Plan And Model Gate

- [x] 1.1 Create a narrow ordered optimization and risk matrix for daemon projection reconciliation.
- [x] 1.2 Verify real FlowGuard import before production changes.
- [x] 1.3 Extend the focused daemon reconciliation model with projection convergence and fast-loop sleep hazards.
- [x] 1.4 Run known-bad hazard checks and confirm each projection/fast-loop bad case is detected.
- [x] 1.5 Run the intended focused model path and record the result artifact.

## 2. Router Runtime

- [x] 2.1 Add an idempotent Controller-boundary projection sync helper that works without a live pending action.
- [x] 2.2 Call the projection sync inside the reconciliation barrier before pending-action return or next-action computation.
- [x] 2.3 Prevent `confirm_controller_core_boundary` from being reissued when valid durable projection evidence already exists.
- [x] 2.4 Skip daemon sleep only after `max_actions_per_tick`, preserving sleep for real barriers and no-action ticks.

## 3. Runtime Tests

- [x] 3.1 Add a focused test for stale boundary flags plus reconciled durable evidence with no pending action.
- [x] 3.2 Add a focused test proving the daemon immediately continues after queue budget exhaustion without sleeping.
- [x] 3.3 Run focused Router tests for Controller boundary and daemon queue behavior.

## 4. Final Verification And Sync

- [x] 4.1 Re-run the focused daemon reconciliation FlowGuard check.
- [x] 4.2 Run OpenSpec validation for this change.
- [x] 4.3 Sync repo-owned FlowPilot assets into the local installed skill and audit the install.
- [x] 4.4 Update FlowGuard adoption notes with commands, results, skipped Meta/Capability checks, and residual risk.
- [x] 4.5 Review local git status and keep peer-agent changes intact.
