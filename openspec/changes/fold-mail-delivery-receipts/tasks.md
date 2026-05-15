## 1. Model Gate

- [x] 1.1 Verify real FlowGuard is importable.
- [x] 1.2 Upgrade the daemon reconciliation model so mail-delivery receipts must fold into packet/mail ledger and Router flags, or remain explicit blockers.
- [x] 1.3 Add live-run projection checks for `deliver_mail` receipt/ledger divergence and PM repair-decision consumption.
- [x] 1.4 Run the focused model-only check and confirm the current live projection catches the existing blocker.
- [x] 1.5 Record that Meta and Capability heavyweight simulations are skipped by user direction.

## 2. Runtime Fix

- [x] 2.1 Extract a shared Router-owned mail-delivery fold helper.
- [x] 2.2 Use the helper from direct `deliver_mail` apply.
- [x] 2.3 Use the helper from Controller receipt reconciliation for `deliver_mail`.
- [x] 2.4 Keep the fold idempotent across repeated daemon ticks or repeated receipts.

## 3. Tests And Validation

- [x] 3.1 Add focused runtime tests for Controller receipt `deliver_mail` folding.
- [x] 3.2 Add focused runtime tests for repeated receipt reconciliation not duplicating mail ledger entries.
- [x] 3.3 Run focused Router tests, FlowGuard model/projection checks, and OpenSpec validation.
- [x] 3.4 Sync the installed FlowPilot skill from repository source and verify installed freshness.
- [x] 3.5 Update FlowGuard adoption notes and KB postflight.
