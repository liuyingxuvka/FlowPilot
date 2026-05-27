## 1. Model And Boundary

- [x] 1.1 Classify the observed failure as a FlowGuard model miss and map it to the existing daemon reconciliation startup hazards.
- [x] 1.2 Confirm the OpenSpec delta is valid and tied to startup answer reconciliation, startup settlement ownership, and deterministic startup bootstrap.

## 2. Implementation

- [x] 2.1 Update startup receipt reconciliation so normal `record_startup_answers` receipts validate and reconcile the answer postcondition idempotently.
- [x] 2.2 Update startup daemon/intake projection so completed native intake seed side effects prevent reissuing answer and deterministic setup rows.
- [x] 2.3 Preserve existing blocker behavior for malformed, conflicting, or unsupported startup receipts.

## 3. Regression Coverage

- [x] 3.1 Add a focused runtime regression for the live-daemon startup intake/apply interleaving that previously produced a `record_startup_answers` blocker.
- [x] 3.2 Add a replay regression proving matching `record_startup_answers` receipts reconcile without a PM/control blocker and conflicting receipts still fail safely.

## 4. Validation And Sync

- [x] 4.1 Run focused startup/controller runtime tests and OpenSpec validation.
- [x] 4.2 Run relevant FlowGuard model checks, using background logs for long regressions.
- [x] 4.3 Sync the local installed FlowPilot skill from the repository and run install check/audit.
- [x] 4.4 Re-check git state and report task-owned changes separately from peer-agent edits.
