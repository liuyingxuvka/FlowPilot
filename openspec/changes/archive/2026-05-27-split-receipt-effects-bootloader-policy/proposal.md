## Why

The full FlowGuard coverage diagnostics still flag
`flowpilot_router_controller_scheduler_receipts_effects.py` as a deferred
StructureMesh split candidate. The file is a compatibility facade but still
contains the startup bootloader receipt branch inline with the generic
Controller receipt effect path.

Keeping that branch inline lengthens the receipt-effect decision chain and
makes it easier for future edits to mix startup bootloader state writes with
generic receipt reconciliation.

## What Changes

- Extract startup bootloader receipt helpers into a focused child module.
- Keep `flowpilot_router_controller_scheduler_receipts_effects.py` as the
  compatibility facade for existing router-owned helper names.
- Preserve the existing receipt result shapes, postcondition checks, scheduler
  reconciliation sources, bootstrap/run-state writes, and terminal lifecycle
  skip behavior.
- Refresh model-test alignment and full coverage diagnostics after the split.

## Impact

- Affected source:
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_effects.py`
  - new internal child module under `skills/flowpilot/assets/`
- Affected validation:
  - focused startup bootloader receipt tests;
  - focused source-boundary test for the child module;
  - model-test alignment and full coverage sweep/inventory;
  - local FlowPilot install sync/freshness audit.
