## 1. Model And Contract

- [x] 1.1 Extend the focused daemon reconciliation FlowGuard model/checks for same-origin blocker resolution and stale PM repair queue supersession.
- [x] 1.2 Run the focused daemon reconciliation model before production edits and confirm known-bad hazards fail.

## 2. Router Settlement Implementation

- [ ] 2.1 Add auditable same-origin control-blocker resolution for reconciled Controller actions and startup bootloader postconditions.
- [ ] 2.2 Supersede pending `handle_control_blocker` Controller rows and scheduler rows when their source blocker resolves before delivery.
- [ ] 2.3 Reconcile `load_controller_core` done receipts as startup bootloader postconditions when the Router daemon is ready.
- [ ] 2.4 Reorder the next-action settlement barrier so active blocker actions are considered only after durable reconciliation and stale-blocker cleanup.

## 3. Runtime Regression Tests

- [ ] 3.1 Add a regression proving a reconciled startup action clears an older same-origin blocker and does not return PM repair work.
- [ ] 3.2 Add a regression proving a queued PM `handle_control_blocker` row is superseded when the source blocker resolves before delivery.
- [ ] 3.3 Preserve existing Controller receipt projection and direct pending-action behavior from parallel changes.

## 4. Verification And Sync

- [ ] 4.1 Run focused FlowGuard checks and targeted runtime tests for the touched boundary.
- [ ] 4.2 Run install check, sync the local installed FlowPilot skill, and verify installed-skill freshness.
- [ ] 4.3 Run local smoke/check commands that are practical without Meta/Capability heavyweight regressions.
- [ ] 4.4 Review the final working tree, including compatible peer-agent changes, before git submission.
