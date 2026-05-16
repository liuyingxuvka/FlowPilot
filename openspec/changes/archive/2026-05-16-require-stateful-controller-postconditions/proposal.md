## Why

The current startup blocker showed that a Controller receipt can be marked `done`
while the Router-visible stateful postcondition is still missing. Existing
models covered this class abstractly, but the persistent startup/daemon model
did not bind the rule to concrete Controller boundary actions, so the bad run
looked like a valid generic receipt.

## What Changes

- Require every stateful Controller action to declare its postcondition contract
  before the Router can reconcile a `done` receipt.
- Require Router-visible durable evidence for that postcondition before the
  Router clears the action, advances flags, or computes the next startup step.
- Treat incomplete stateful receipts as recoverable Controller deliverable work:
  reclaim valid existing artifacts when present, otherwise mark the original
  action incomplete and issue a bounded Controller repair row before escalating
  to a control blocker.
- Add FlowGuard coverage for receipt-present/evidence-missing, Router-cleared
  without evidence, and Controller role confirmed without the boundary artifact.

## Capabilities

### New Capabilities
- `stateful-controller-postconditions`: Defines the receipt and reconciliation
  contract for Controller actions that mutate Router-visible startup or runtime
  state.

### Modified Capabilities
- None.

## Impact

- Affects FlowPilot Router/Controller startup reconciliation and daemon receipt
  processing.
- Affects focused FlowGuard models and result artifacts under `simulations/`.
- Does not change release, publish, deployment, or heavyweight meta/capability
  model checks.
