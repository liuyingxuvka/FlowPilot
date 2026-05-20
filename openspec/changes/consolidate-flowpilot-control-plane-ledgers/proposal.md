## Why

FlowPilot control-plane friction is recurring because several runtime records still
act like competing sources of truth: Controller receipts, scheduler rows,
controller action records, daemon status, and legacy `pending_action` can drift or
write the same scheduler ledger from different paths. This change consolidates
the control plane so foreground actors append receipts/events while the Router
daemon owns scheduler folding and live projections.

## What Changes

- Make Router scheduler ledger mutation daemon-owned during daemon mode; foreground
  receipt paths may append receipts and action-local facts but must not directly
  mutate scheduler rows except through an explicit daemon/fallback folding lane.
- Normalize transient Windows runtime ledger access failures into deferrable
  write-in-progress outcomes instead of daemon-fatal errors.
- Demote legacy `pending_action` to a compatibility projection when a matching
  Controller action ledger row exists, avoiding contradictory `apply_required`
  decisions.
- Make batch waits expose all missing roles from refreshed packet/member state
  instead of collapsing generic worker events to `worker_a`.
- Reconcile stale passive/current-scope wait rows once their blocker or stage
  condition has already been superseded.
- Preserve hard constraints: Controller remains the foreground patrol actor,
  role information boundaries remain envelope/body separated, and signed packet
  artifacts remain immutable.

## Capabilities

### New Capabilities
- `control-plane-ledger-consolidation`: Defines the daemon-owned folding and
  projection rules that prevent runtime ledgers from acting as competing
  authorities.

### Modified Capabilities
- `persistent-router-daemon`: Daemon runtime must treat scheduler ledger access
  contention as deferrable and continue after transient write collisions.
- `runtime-ledger-persistence`: Runtime ledger atomicity must cover read-back and
  verification access failures, not only replace-time failures.
- `router-two-table-async-scheduler`: Scheduler rows must be folded through one
  owner while Controller-facing rows remain executable projections.
- `controller-action-ledger`: Controller receipt reconciliation must append
  receipts and let Router-owned folding update action/scheduler state.
- `partial-batch-accounting`: Batch wait summaries must derive current missing
  roles from packet/batch members, not a single inferred worker event role.

## Impact

- Affected runtime modules under `skills/flowpilot/assets/`, especially Router
  daemon runtime, controller scheduler receipt reconciliation, scheduler ledger
  writes, expected wait role projection, packet/batch status summaries, and JSON
  atomic write helpers.
- Affected FlowGuard simulations for persistent daemon, two-table scheduler,
  control-plane friction, and model-test alignment.
- Affected router runtime tests for foreground Controller receipts, daemon
  write-lock behavior, batch wait summaries, and stale passive wait cleanup.
- Local installed FlowPilot skill sync and install audit must be rerun after the
  repair.
