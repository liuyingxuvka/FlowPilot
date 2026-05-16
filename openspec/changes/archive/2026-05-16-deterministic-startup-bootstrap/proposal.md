## Why

The current startup path schedules deterministic file-initialization work as
Controller rows, then also reconciles those rows through startup-specific and
generic receipt paths. A live run showed that this split can create a false PM
repair blocker after a startup row was already reconciled.

This change makes startup simpler: a deterministic bootstrap seed creates the
run foundation directly, and the unified Router scheduler starts only after
that foundation exists.

## What Changes

- Move deterministic local file setup out of Controller rows and into a
  bootstrap seed that runs before the Router scheduler table is active.
- Keep the bootstrap seed narrow: it may create directories, empty ledgers,
  run pointers, startup-answer records, user-request references, and the
  initial user-intake scaffold; it may not spawn roles, create heartbeat
  automation, load Controller core, generate PM repair blockers, or make AI
  judgments.
- Start the unified Router scheduler after the seed has written and verified
  the foundation.
- Schedule only real startup obligations after the seed, such as role-slot
  startup, heartbeat binding when requested, and Controller core handoff.
- Reconcile all scheduled rows through one generic receipt/postcondition path.
  A row that is already reconciled must be idempotently skipped and must never
  become a PM repair blocker.
- Treat bootstrap seed failure as a startup failure before the FlowPilot route
  starts, not as a PM semantic repair blocker.

## Capabilities

### New Capabilities
- `deterministic-startup-bootstrap`: deterministic startup file foundation is
  completed by code before the unified Router scheduler begins.

### Modified Capabilities
- `startup-daemon-first-driver`: the daemon remains the scheduler driver after
  the deterministic seed, but no longer owns deterministic file-initialization
  rows as Controller work.
- `router-two-table-async-scheduler`: startup rows in the scheduler table are
  limited to work that needs scheduling, waiting, or postcondition
  reconciliation.
- `controller-action-ledger`: deterministic seed work is recorded as bootstrap
  evidence, not Controller actions requiring Controller receipts.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- Focused startup/runtime tests in `tests/test_flowpilot_router_runtime.py`
- FlowGuard startup/bootstrap and daemon reconciliation models under
  `simulations/`
- OpenSpec artifacts for this change
- Local installed FlowPilot skill copy after implementation sync

Heavyweight Meta and Capability simulations are explicitly skipped for this
change by user direction; focused FlowGuard models and targeted runtime tests
remain required.
