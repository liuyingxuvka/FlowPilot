## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_runtime_state.py`

Selected branch:

- Run-state persistence and stale-save reconciliation.

Not selected:

- Dirty scheduler receipt/standby candidates, because they remain peer-work
  risk.
- `flowpilot_router_protocol_external_event_data.py`, because it is currently
  a data table rather than a duplicated decision/effect path.
- Startup materialization, because startup seed writes need a startup-specific
  proof pass.
- Packet-ledger resume projection, role-memory, and continuation quarantine
  helpers inside runtime state, because those are separate business branches
  and should not be mixed into this persistence split.

## Compatibility Boundary

The parent module remains the compatibility surface. Existing helper names
continue to resolve through `flowpilot_router_runtime_state.py`, and the child
module receives the router facade explicitly so shared runtime constants and IO
helpers remain bound at call time.

## Leaf Model Boundary

The runtime-state persistence child is split into two leaf model obligations
because stale-save merge and load/save facade behavior have different primary
evidence:

- `runtime_state.stale_save_merge_boundary` owns stale-save metadata,
  append-only list merging, compatible pending-wait reminder preservation,
  foreground clears, and volatile metadata exclusion.
- `runtime_state.load_save_persistence_boundary` owns run-root binding, default
  normalization, facade return shapes, disk write behavior, and refreshed load
  metadata after save.

If either leaf accumulates multiple primary-looking evidence rows, split that
leaf again instead of changing test labels.

## Validation

- Compile parent, child, tests, and model-test evidence files.
- Run focused runtime-state persistence tests.
- Run a focused existing stale-save runtime test.
- Run model-test alignment and full model coverage inventory checks.
- Sync the repo-owned FlowPilot skill into the local installed version and
  verify freshness serially after sync.
