## 1. Model Gate

- [x] 1.1 Verify real FlowGuard is importable and record this change's Risk Intent.
- [x] 1.2 Update startup ordering models so pre-Core Controller-ledger startup obligations are rejected.
- [x] 1.3 Run focused model checks before production code edits.

## 2. Runtime Ordering

- [x] 2.1 Update Router startup action selection so `load_controller_core` is exposed before banner, heartbeat, or role-slot Controller rows.
- [x] 2.2 Preserve scheduled heartbeat and role-slot requirements after Controller core reconciliation.
- [x] 2.3 Preserve the startup-intake ledger-return prompt boundary from the parallel change.

## 3. Tests And Sync

- [x] 3.1 Update focused runtime tests for the new startup ordering and old-order rejection.
- [x] 3.2 Run focused tests and FlowGuard checks; Meta/Capability heavyweight regressions skipped by user as too heavy for this pass.
- [x] 3.3 Sync the installed local FlowPilot skill from the repository and audit the installed copy.

## 4. Integration

- [x] 4.1 Review peer-agent changes and keep compatible work in the final staged set.
- [x] 4.2 Run final install/smoke checks practical for the touched boundary.
- [x] 4.3 Commit the combined compatible workspace changes.
