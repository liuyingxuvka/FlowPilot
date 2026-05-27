## Why

`flowpilot_router_terminal_ledger_traceability.py` still owns two different
responsibilities: validating/finalizing the terminal ledger and constructing
the source-of-truth entry list consumed by that ledger. Keeping both in one
module makes the terminal completion path harder to audit.

## What Changes

- Add a source-entry child module for root requirement ids, route-node
  traceability projection, root-replay closure rows, and final source-of-truth
  entry construction.
- Keep the existing terminal ledger traceability facade helper names and
  return shapes.
- Add source-audited model/test evidence for the new child module.

## Impact

- No public FlowPilot facade behavior changes.
- Terminal ledger source-of-truth entry logic becomes a smaller, directly
  tested child boundary.
- Remaining StructureMesh candidates stay visible for future heartbeats.
