## 1. Model Coverage

- [x] 1.1 Update the persistent Router daemon FlowGuard model so stateful Controller actions require postcondition evidence before receipt reconciliation.
- [x] 1.2 Add known-bad hazards for receipt-present/evidence-missing, Router-cleared/evidence-missing, and role-confirmed/artifact-missing states.
- [x] 1.3 Rerun focused persistent daemon checks and record the updated result artifact.
- [x] 1.4 Run the live control-plane audit against the current blocker and confirm it projects to the same stateful receipt invariant.

## 2. Production Reconciliation

- [ ] 2.1 Add stateful postcondition and required-deliverable metadata to Controller action records for startup boundary actions, beginning with `confirm_controller_core_boundary`.
- [ ] 2.2 Add a shared Router reconciliation validator table for stateful Controller action types.
- [ ] 2.3 Implement the `confirm_controller_core_boundary` validator so it reclaims existing `startup/controller_boundary_confirmation.json`, validates it, and syncs the related Router flags before clearing the action.
- [ ] 2.4 Update daemon and foreground receipt reconciliation to mark missing deliverables incomplete and enqueue bounded Controller repair rows before blocker escalation.
- [ ] 2.5 Escalate incomplete or invalid stateful receipts to control blockers only after the repair budget is exhausted.

## 3. Verification

- [ ] 3.1 Add focused runtime tests for minimal `done` receipts without postcondition evidence.
- [ ] 3.2 Add focused runtime tests for valid artifact reclaim before blocker creation.
- [ ] 3.3 Add focused runtime tests for successful Controller deliverable repair, repair-budget blocker escalation, normal startup boundary confirmation, and generic receipt-only actions.
- [ ] 3.4 Rerun focused FlowGuard checks and targeted runtime tests; skip heavyweight meta/capability model regressions unless explicitly requested.
