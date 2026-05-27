## Why

FlowPilot can prove a packet/result relay from Router-visible evidence while the Controller receipt reconciler still leaves the Router-owned postcondition flag false. This creates false control blockers and can prevent Router from waiting on already-started worker work.

## What Changes

- Add a shared Controller receipt evidence-fold contract for packet/result relay actions.
- Require evidence-backed relay actions to declare how their Controller `done` receipt folds into Router-owned flags.
- Reconcile packet relay receipts from packet ledger, parallel batch, relay history, active-holder leases, packet-open evidence, and result envelopes without reading sealed bodies.
- Treat workers that have opened or ACKed packets as in-progress work to wait for, not as a reason to reissue the same relay action.
- Keep retry/control-blocker behavior only for missing, invalid, or contradictory Router-visible evidence.
- Add FlowGuard and runtime regression evidence for the material scan miss and same-family relay actions.

## Capabilities

### New Capabilities

- `controller-receipt-evidence-folds`: Defines the shared evidence-fold contract for Controller receipts that must update Router-owned postcondition flags from Router-visible evidence.

### Modified Capabilities

- `stateful-controller-postconditions`: Stateful postcondition receipt reconciliation must include registered evidence folds for evidence-backed packet/result relay actions.
- `router-controller-ledger-reconciliation`: Router decision entry must apply evidence folds before retry/blocker decisions or next-action selection.
- `router-two-table-async-scheduler`: Duplicate dispatch guards must suppress equivalent relay actions when receipt evidence, relay evidence, or worker active-holder evidence already proves work is in flight or complete.
- `partial-batch-accounting`: Batch and worker wait decisions must use packet relay/open/result evidence even when the aggregate Router flag was stale before reconciliation.

## Impact

- Affected runtime code: Controller receipt effects, packet/result relay reconciliation helpers, duplicate dispatch suppression for relay actions, and next-action gating that depends on relay flags.
- Affected verification: new focused FlowGuard model/check, source-contract audit, targeted Router runtime tests for material scan receipt folding, and background meta/capability regressions.
- No sealed body boundary, publication, release, dependency, or target-project behavior changes are included.
