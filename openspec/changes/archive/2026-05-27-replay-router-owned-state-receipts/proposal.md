## Why

`load_resume_state` is a Router-owned state action, but the Controller ledger
can project it into a `done` receipt before the Router-owned postcondition flag
has been applied. A receipt alone cannot prove `resume_state_loaded`, so this
gap can create false stateful-controller blockers or leave resume recovery
dependent on unsupported receipt handling.

## What Changes

- Require Router-owned state loader receipts to replay the registered Router
  action handler instead of treating Controller `done` as standalone proof.
- Add a shared registry for state loader actions that are legal to replay from
  Controller receipt reconciliation.
- Extend the focused Controller receipt FlowGuard model with the bad case where
  a Router-owned state action is projected without registered replay.
- Add source audit coverage for `load_*_state` actions that write Router-owned
  flags but are missing from the replay registry.
- Add runtime regression evidence that `load_resume_state` receipt
  reconciliation sets `resume_state_loaded` through the Router handler path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `stateful-controller-postconditions`: Stateful postcondition receipt
  reconciliation must distinguish evidence-backed Controller work from
  Router-owned state loader replay.
- `router-controller-ledger-reconciliation`: Router reconciliation must apply a
  registered Router-owned replay path before unsupported-postcondition blocker
  routing.
- `resume-rehydration-obligation-replay`: Heartbeat/manual resume state loading
  must remain Router-owned even when the wake path is represented by a
  Controller receipt.
- `runtime-ledger-persistence`: Fresh runtime JSON write locks must defer
  daemon reads when the target ledger is temporarily incomplete, even when host
  liveness evidence is briefly ambiguous.

## Impact

- Affected runtime code: Controller receipt effects and shared control-plane
  contract helpers.
- Affected verification: focused FlowGuard receipt-fold model, source-contract
  audit, resume runtime tests, meta/capability background checks, and local
  install synchronization checks.
- No sealed-body boundary, target-project behavior, release, publication, or
  dependency changes are included.
