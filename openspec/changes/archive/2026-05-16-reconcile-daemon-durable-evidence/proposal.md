## Why

A live FlowPilot run showed a second-layer daemon failure: the expected reviewer
startup fact output existed in durable files, and a Controller receipt existed
for resume role rehydration, but Router state still said the startup fact report
and resume role restore were missing. The daemon therefore kept returning stale
work instead of reconciling the files that already existed.

The first-layer foreground fix keeps Controller visibly attached while Router
waits. This change fixes the Router side: every daemon or manual next-action
tick must reconcile durable Controller receipts and direct role-output evidence
before it decides what work to return.

## What Changes

- Add a durable reconciliation barrier before Router computes or repeats a
  pending action.
- Reconcile Controller receipts back into the active pending action, including
  clearing completed non-stateful actions and blocking incomplete receipts for
  stateful actions that require Router-owned postconditions.
- Reconcile direct role-output runtime ledger entries for startup fact reports
  into Router flags/events and canonical startup artifacts.
- Preserve strict authority: Controller receipts prove host execution metadata;
  role-output runtime envelopes and canonical artifacts prove role outputs.
  Controller does not read sealed role-output bodies.
- Add a FlowGuard model and focused runtime tests for stale pending action,
  receipt-only completion, role-output ledger submission, and canonical artifact
  flag drift.

## Capabilities

### Modified Capabilities

- `persistent-router-daemon`: Router daemon reconciliation now includes
  durable Controller receipts and direct role-output runtime ledger evidence
  before next-action computation.
- `controller-action-ledger`: Controller receipts are no longer only ledger
  status updates; they must either update Router state safely, clear completed
  pending actions, or surface a repair blocker.

## Impact

- Router runtime:
  - `skills/flowpilot/assets/flowpilot_router.py`
- FlowGuard models:
  - `simulations/flowpilot_daemon_reconciliation_model.py`
  - `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Runtime tests:
  - `tests/test_flowpilot_router_runtime.py`
- Local install sync and audit:
  - `scripts/check_install.py`
  - `scripts/install_flowpilot.py --sync-repo-owned --json`
  - `scripts/audit_local_install_sync.py --json`
  - `scripts/install_flowpilot.py --check --json`
