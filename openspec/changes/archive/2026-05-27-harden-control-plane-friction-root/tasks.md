## 1. Model And Scope

- [x] 1.1 Reuse the existing control-plane friction FlowGuard model and confirm it covers the same-class bad cases.
- [x] 1.2 Keep the repair scoped to identity, delivery, liveness, ledger, and material evidence authority.

## 2. Runtime And Router Fixes

- [x] 2.1 Scope Controller and scheduler identity to batch/request/packet/recipient work units.
- [x] 2.2 Reject failed-delivery payloads recorded as `done` Controller receipts.
- [x] 2.3 Harden packet ledger atomic writes and corrupt-read recovery.
- [x] 2.4 Require live crew-ledger evidence for active-holder leases and receipt folds.
- [x] 2.5 Tighten material artifact map and formal gate package authority claims.

## 3. Validation And Sync

- [x] 3.1 Add focused unit/runtime tests for the repaired boundaries.
- [x] 3.2 Run focused tests and FlowGuard checks, using background artifacts for long regressions.
- [x] 3.3 Sync the repo-owned installed FlowPilot skill and run serialized install/audit checks.
- [x] 3.4 Review git status and report remaining risks.
