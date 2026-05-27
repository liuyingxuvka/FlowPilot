## Why

Controller receipt evidence folds now have the right public contract, but the
packet/result lifecycle writeback code still repeats the same decision tree in
more than one place. This pass reduces bug risk by making the lifecycle target
state explicit before writing records.

## What Changes

- Add one internal lifecycle policy helper for receipt evidence folds.
- Refactor packet batch and PM role-work lifecycle writeback to consume that
  policy instead of branching separately on packet dispatch vs result relay.
- Preserve the existing receipt registry, public imports, Router flags,
  packet/result evidence checks, sealed-body boundary, and lifecycle outputs.
- No file split and no behavior change.

## Capabilities

### New Capabilities

- `receipt-fold-lifecycle-policy`: Internal branch-pruning contract for
  Controller receipt evidence fold lifecycle writeback.

### Modified Capabilities

None.

## Impact

- Affected code:
  `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py`.
- Affected tests and checks: focused receipt-fold runtime tests, FlowGuard
  receipt evidence-fold checks, Router branch-pruning checks, structure/model
  alignment checks, install sync/audit checks.
