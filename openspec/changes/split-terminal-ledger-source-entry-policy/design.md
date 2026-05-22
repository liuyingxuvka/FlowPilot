## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_terminal_ledger_traceability.py`

Selected branch:

- Source-of-truth entry construction for the final route-wide ledger.

Not selected:

- Dirty scheduler receipt/standby candidates, because they are peer-work risk.
- `flowpilot_router_protocol_external_event_data.py`, because it is a data
  table with no current decision/effect branch to prune.
- `flowpilot_router_runtime_state.py`, because state ownership is broader and
  higher risk than this terminal source-entry split.
- `flowpilot_router_startup_intake_materialization.py`, because startup intake
  writes require a separate startup-focused proof pass.

## Compatibility Boundary

The parent module remains the public compatibility surface. Existing helper
names continue to resolve through `flowpilot_router_terminal_ledger_traceability.py`.
The child module is an implementation owner for source-entry projection only.

## Leaf Model Boundary

The previous source-audited terminal obligation remains the Router-level final
ledger and backward replay invariant. The source-entry child is modeled below
that level as two leaf obligations:

- `terminal.final_ledger_source_entries` owns final source-of-truth entry
  construction and gate-family output shapes.
- `terminal.requirement_trace_projection` owns route-node requirement defaults
  and root-replay closure rows.

Each leaf obligation keeps its own primary boundary evidence. If another child
test appears as a second primary owner for one of these obligations, split the
model again before relabeling evidence.

## Validation

- Compile parent, child, tests, and model-test evidence files.
- Run focused terminal source-entry child tests.
- Run terminal runtime tests covering final ledger source paths.
- Run model-test alignment and full model coverage inventory checks.
- Sync the repo-owned FlowPilot skill into the local installed version and
  verify freshness serially after sync.
