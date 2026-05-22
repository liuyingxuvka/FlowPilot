## Why

`flowpilot_router_controller_scheduler_receipts_packet_folds.py` still owns the
receipt-fold registry, packet/result evidence validation, lifecycle writeback,
PM role-work writeback, control-blocker delivery, and the public fold entrypoint
in one file. The lifecycle and registry parts are small, finite boundaries that
can be tested directly, so keeping them in the broad owner keeps the packet-fold
model too coarse.

## What Changes

- Add a receipt packet-fold registry child module.
- Add a receipt packet-fold lifecycle child module.
- Keep the existing packet-fold parent as the compatibility surface.
- Add source-audited model/test evidence for the new leaf boundaries.

## Impact

- No public action types, Router flags, receipt summaries, or sealed-body
  boundaries change.
- The parent packet-fold module falls below the StructureMesh threshold.
- Registry and lifecycle writeback now have direct child-boundary tests.
