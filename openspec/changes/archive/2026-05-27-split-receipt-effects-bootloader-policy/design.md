## Context

`flowpilot_router_controller_scheduler_receipts_effects.py` is currently a
facade-like owner for stateful Controller receipt effects. The startup
bootloader receipt branch is a distinct policy: it maps bootloader action
types to startup bootstrap/run-state effects before generic receipt handling
continues.

This is a StructureMesh split, not a behavior change.

## Target Structure

- `flowpilot_router_controller_scheduler_receipts_effects.py`
  - public compatibility helper names used by the router facade;
  - generic stateful receipt dispatch;
  - wait-target reminder receipt handling;
  - done-receipt orchestration.

- `flowpilot_router_controller_scheduler_receipts_bootloader.py`
  - bootloader action metadata lookup;
  - bootstrap pending-action matching;
  - startup bootloader receipt application and postcondition projection.

Dependency direction is one-way: the receipt-effects facade imports the child
bootloader module. The child module receives the router facade explicitly and
must not import the receipt-effects facade.

## Compatibility Boundary

The following names remain available from
`flowpilot_router_controller_scheduler_receipts_effects.py`:

- `_boot_action_meta`
- `_matching_bootstrap_pending_action`
- `_apply_startup_bootloader_receipt_effects`
- `_apply_stateful_receipt_postcondition`
- `_apply_done_controller_receipt_effects`

## Validation Boundary

The split is green only if:

- focused startup bootloader receipt runtime tests still pass;
- a source-boundary test directly exercises the child bootloader module;
- model-test alignment remains green and source-audit evidence covers the
  child module without duplicate evidence ownership;
- full coverage diagnostics no longer report
  `flowpilot_router_controller_scheduler_receipts_effects` as a StructureMesh
  split finding;
- local installed FlowPilot is synced and fresh.
