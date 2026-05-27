## Context

`flowpilot_router_controller_scheduler_current_work.py` is currently a
facade-like owner for current-work projection. The pending-action resolution
branch is a distinct policy: it decides whether a pending wait still blocks
progress, whether a scheduler row proves durable resolution, and whether a
worker-role wait should be projected through active packet batches.

This is a StructureMesh split, not a behavior change.

## Target Structure

- `flowpilot_router_controller_scheduler_current_work.py`
  - public compatibility helper names used by the router facade;
  - owner labels and current-work payload construction;
  - packet ledger, active batch, passive wait, and fallback projection;
  - delegation to the pending-resolution child module.

- `flowpilot_router_controller_scheduler_current_work_pending.py`
  - pending-action controller-authority checks;
  - scheduler-row lookup for pending actions;
  - durable wait resolution classification;
  - pending-action clearing after durable resolution;
  - worker-role batch-projection selection.

Dependency direction is one-way: the current-work facade imports the child
pending-resolution module. The child module receives the router facade
explicitly and must not import the current-work facade.

## Compatibility Boundary

The following names remain available from
`flowpilot_router_controller_scheduler_current_work.py`:

- `_pending_action_has_controller_authority`
- `_scheduler_row_for_pending_action`
- `_pending_action_durable_resolution`
- `_clear_pending_action_if_durable_wait_resolved`
- `_pending_role_wait_should_use_batch_projection`
- `_derive_current_work`

## Validation Boundary

The split is green only if:

- focused current-work runtime tests still pass;
- a source-boundary test directly exercises the child pending-resolution module;
- model-test alignment remains green and source-audit evidence covers the
  child module without duplicate evidence ownership;
- full coverage diagnostics no longer report
  `flowpilot_router_controller_scheduler_current_work` as a StructureMesh
  split finding;
- local installed FlowPilot is synced and fresh.
