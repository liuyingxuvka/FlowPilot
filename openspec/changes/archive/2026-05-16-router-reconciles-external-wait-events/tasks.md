## 1. Model And Contract

- [x] 1.1 Add FlowGuard state for durable external-event wait rows and their Router-owned closure.
- [x] 1.2 Add hazards for recorded-event/stale-wait, next-wait-before-old-wait-closed, and Controller-owned wait closure.
- [x] 1.3 Validate the OpenSpec change and run the focused FlowGuard check.

## 2. Router Runtime

- [x] 2.1 Add a generic helper that closes open `await_role_decision` Controller action rows when a recorded event appears in `allowed_external_events`.
- [x] 2.2 Call the helper from normal event recording, already-recorded event handling, and Router durable-event reconciliation.
- [x] 2.3 Reconcile matching Router scheduler rows from the same external-event evidence.

## 3. Verification And Sync

- [x] 3.1 Add focused runtime tests for newly recorded and already-recorded events closing stale wait rows.
- [x] 3.2 Run targeted router/runtime tests and focused FlowGuard checks; skip heavyweight meta/capability checks by user request.
- [x] 3.3 Sync the installed local FlowPilot skill and audit install freshness.
- [x] 3.4 Record FlowGuard adoption and KB postflight notes.
