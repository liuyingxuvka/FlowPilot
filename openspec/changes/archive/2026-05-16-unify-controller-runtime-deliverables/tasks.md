## 1. Runtime Contract

- [x] 1.1 Add Controller-scoped runtime output metadata for boundary confirmation.
- [x] 1.2 Add a runtime/helper path that writes canonical Controller boundary confirmation artifacts and receipts without Controller hand-writing JSON.

## 2. Router Reconciliation

- [x] 2.1 Make Controller boundary confirmation actions advertise the runtime contract metadata.
- [x] 2.2 Reconcile Controller boundary confirmation only from valid runtime evidence.
- [x] 2.3 Fix repair accounting so issued repair rows do not count as failed before their returned evidence is invalid.

## 3. FlowGuard And Validation

- [x] 3.1 Update focused FlowGuard coverage for Controller runtime deliverables and repair-attempt accounting.
- [x] 3.2 Run focused checks and install/local sync verification while skipping heavyweight meta/capability regressions.
