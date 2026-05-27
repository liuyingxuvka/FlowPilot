## 1. Contract And Model

- [x] 1.1 Capture the recurring failure as an OpenSpec delta for role-output transaction boundaries, authority-state split brain, ingress coverage, and control-plane friction.
- [x] 1.2 Update FlowGuard/control-plane model evidence for package disposition ledger candidates that fail source self-checks, split canonical authority, or pass only scoped checks.

## 2. Runtime Fix

- [x] 2.1 Make reconciled PM package disposition events call the existing domain writer before flags, event history, idempotency, or wait closure are recorded.
- [x] 2.2 Preserve stale direct-event and role-output replay quarantine behavior without using it as the only guard.
- [x] 2.3 Apply the domain-first rule to material, research, and current-node package disposition events.

## 3. Regression Coverage

- [x] 3.1 Add a negative regression for a role-output ledger PM material disposition whose source result self-check fails.
- [x] 3.2 Add a positive regression proving a valid ledger PM disposition commits the canonical artifact before event finalization.
- [x] 3.3 Keep existing stale replay quarantine tests passing.
- [x] 3.4 Add a split-brain regression where event idempotency/history exists but canonical package disposition state is missing.
- [x] 3.5 Add an ingress matrix regression for direct event, role-output replay, and daemon replay/startup over the package disposition defect family.

## 4. Validation And Sync

- [x] 4.1 Run focused router/runtime tests for role-output reconciliation and PM package disposition contracts.
- [x] 4.2 Run relevant FlowGuard/model checks, live-run audit, historical bad-case replay, and inspect background artifacts for long checks.
- [x] 4.3 Sync the installed FlowPilot skill/runtime copy and run install/source-fresh checks.
- [x] 4.4 Validate the OpenSpec change and review git status without reverting peer work.
