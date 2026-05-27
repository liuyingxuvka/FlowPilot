## Why

`flowpilot_router_runtime_state.py` still mixes bootstrap/run-state helpers
with stale-save reconciliation and run-state persistence. The stale-save path
has several decision branches for append-only lists, pending waits, reminder
fields, and concurrently changed flags, so keeping it inside the broad runtime
state owner makes the write boundary harder to audit.

## What Changes

- Add a runtime-state persistence child module for run-state load metadata,
  stale-save merge policy, `load_run_state`, `load_run_state_from_run_root`,
  and `save_run_state`.
- Keep existing runtime-state facade helper names and return shapes available
  through `flowpilot_router_runtime_state.py`.
- Add focused tests and source-audited model/test evidence for the new child
  boundary.

## Impact

- No public FlowPilot facade behavior changes.
- Run-state stale-save and persistence behavior becomes a smaller directly
  tested boundary.
- Remaining StructureMesh candidates stay visible for future heartbeats.
