## 1. Model And Contract

- [x] 1.1 Extend the focused control-plane consistency FlowGuard model with role-output event fold and stale pending-authority hazards.
- [x] 1.2 Update the focused model runner expected hazards and repair-candidate gate.
- [x] 1.3 Validate the OpenSpec change and focused model before production edits.

## 2. Runtime Repair

- [x] 2.1 Add generic durable reconciliation for authorized direct role-output events.
- [x] 2.2 Ensure material-sufficiency role-output events update Router material review projections and PM repair/research branch state.
- [x] 2.3 Add pending-action validation against Controller action and Router scheduler wait row closure state.
- [x] 2.4 Apply pending-action validation before daemon status/current-work derivation, reminder creation, and next-action selection.

## 3. Runtime Tests

- [x] 3.1 Add a captured-style regression where material-sufficiency role output exists, wait rows are resolved, Router state lacks the event, and pending action is stale.
- [x] 3.2 Add a regression proving done/reconciled wait rows cannot authorize current-work from pending action or create reminders.

## 4. Validation And Sync

- [x] 4.1 Run focused FlowGuard checks for control-plane consistency, daemon reconciliation, and two-table scheduler.
- [x] 4.2 Run focused runtime tests for control-plane contracts and affected daemon/status behavior.
- [x] 4.3 Run install sync and install freshness checks.
- [x] 4.4 Review git status and stage only scoped files after preserving peer-agent changes.
