## Why

Router startup can stall when Controller action ledgers and scheduler rows say a stateful action is done/reconciled, but the Router-owned flag that gates the next decision remains false. The concrete failure was `write_display_surface_status`: the display evidence existed, yet startup pre-review repeatedly requeued the same action and never released `user_intake` to PM.

## What Changes

- Add a Router decision-entry reconciliation gate that folds Controller receipts, scheduler rows, and Router-owned stateful postconditions before computing any next action.
- Make stateful postcondition application idempotent: an already-reconciled receipt may still replay or reclaim its Router-owned flag when that flag drifted false.
- Prevent duplicate dispatch for the same Controller action when an equivalent action is already in flight, already done, or already reconciled but needs state repair.
- Treat unresolved drift as a bounded Controller repair/control-blocker condition, not as permission to issue the same ordinary command forever.
- Preserve current two-table scheduler and foreground Controller behavior for independent nonblocking startup work that is genuinely still in flight.
- Add focused FlowGuard and runtime regression evidence for the known-bad startup display drift loop.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `router-controller-ledger-reconciliation`: Router reconciliation must replay/reclaim stateful postconditions before next-action selection and blocker creation.
- `stateful-controller-postconditions`: stateful receipt postconditions must be idempotent and repairable when ledgers claim reconciliation but Router-owned flags drift.
- `router-two-table-async-scheduler`: duplicate dispatch must respect in-flight and already-reconciled Controller rows before enqueueing equivalent ordinary actions.
- `current-scope-pre-review-reconciliation`: startup/current-scope review waits must treat recoverable stateful postcondition drift as reconciliation work, not as an endlessly requeued local obligation.
- `startup-display-surface`: startup route-sign display completion must be reclaimable from valid display evidence and must not repeatedly reissue after completion.

## Impact

- Affected runtime code: Controller receipt folding, scheduled action reconciliation, startup display next-action selection, duplicate-open action checks, and pre-review reconciliation.
- Affected verification: focused current-scope reconciliation FlowGuard model/checks, targeted router runtime tests for startup display postcondition drift, install checks, local install sync, and background meta/capability regressions.
- No release, publish, dependency, sealed-body, or target-project behavior changes are included.
