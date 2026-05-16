## Why

A live FlowPilot startup run showed that Router could queue PM repair work for a
Controller action even after the same action later reconciled successfully. The
control plane needs one accounting rule: settle all durable evidence and stale
blockers before exposing exactly one next action.

## What Changes

- Add a pre-next-action settlement requirement for Router daemon/manual ticks.
- Reconcile Controller receipts, scheduler rows, postconditions, active
  control blockers, and queued blocker-delivery actions as one ordered unit.
- Resolve same-origin control blockers when their originating Controller action
  or postcondition has been reconciled.
- Supersede queued `handle_control_blocker` rows when the source blocker is
  resolved before delivery.
- Keep PM repair as a valid next action only after the standard settlement
  phase proves the blocker is still unresolved and direct mechanical repair
  paths are exhausted.
- Preserve the one-action-per-tick contract: settlement may update ledgers, but
  the tick returns at most one Controller-visible action.

## Capabilities

### New Capabilities

- `settled-router-next-action`: Router settles durable control-plane evidence,
  blockers, and stale queued repair rows before returning a single next action.

### Modified Capabilities

- None.

## Impact

- Router runtime:
  - `skills/flowpilot/assets/flowpilot_router.py`
- FlowGuard model/checks:
  - `simulations/flowpilot_daemon_reconciliation_model.py`
  - `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Runtime tests:
  - `tests/test_flowpilot_router_runtime.py`
- Verification and sync:
  - focused FlowGuard checks and runtime tests;
  - local installed FlowPilot skill sync/check;
  - no heavyweight Meta or Capability model run in this task by user direction.
