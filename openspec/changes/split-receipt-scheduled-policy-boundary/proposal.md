## Why

`flowpilot_router_controller_scheduler_receipts_scheduled.py` still mixed the
scheduled receipt scan loop with finite scheduler-row, backfill, pending-clear,
and apply-result classification rules. That kept the scheduled receipt owner
over the StructureMesh threshold and made the leaf policy boundary harder to
test directly.

## What Changes

- Add a scheduled receipt policy child module.
- Keep the existing scheduled receipt parent as the compatibility surface.
- Move finite scheduler-row lookup, backfill, pending-clear, reconciliation
  commit, and apply-result classification helpers into the child.
- Add source-audited model/test evidence for the new leaf boundary.

## Impact

- No public Controller action, receipt, scheduler-row, blocker, or Router flag
  behavior changes.
- The scheduled receipt parent falls below the StructureMesh threshold.
- The finite scheduled receipt policy rules now have direct child-boundary
  tests.
