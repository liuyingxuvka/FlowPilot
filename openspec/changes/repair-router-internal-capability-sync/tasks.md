## 1. OpenSpec And Model Boundary

- [x] 1.1 Capture Router-owned capability sync ownership in OpenSpec proposal, design, and spec deltas.
- [x] 1.2 Keep the existing FlowGuard control-plane friction model checks for false Controller waits and stale projections.

## 2. Runtime Repair

- [x] 2.1 Add explicit metadata for Router-owned internal postcondition events.
- [x] 2.2 Materialize ready internal postconditions before passive role-wait selection.
- [x] 2.3 Reconcile or clear stale wait/projection rows once capability sync evidence exists.
- [x] 2.4 Preserve idempotent manual `capability_evidence_synced` event compatibility.

## 3. Runtime Tests And Validation

- [x] 3.1 Add or update runtime tests so capability sync is produced by Router/daemon reconciliation without a manual event call.
- [x] 3.2 Run focused tests for expected waits, capability sync, and projection cleanup.
- [x] 3.3 Run the focused FlowGuard control-plane friction check and inspect results.
- [x] 3.4 Run meta/capability model checks in background artifacts and inspect final exit evidence.

## 4. Sync And Repository Hygiene

- [x] 4.1 Sync the installed local FlowPilot skill after code and evidence settle.
- [x] 4.2 Run install audit/check commands after sync.
- [x] 4.3 Review local git status and avoid committing unrelated peer-agent changes.
