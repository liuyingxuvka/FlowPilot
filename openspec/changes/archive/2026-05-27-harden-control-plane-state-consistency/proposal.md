## Why

FlowPilot can deadlock when Controller/Router actions are recorded as done in one ledger while related durable lifecycle records still say the work is not relayed, not superseded, or not owned by the expected role. The 2026-05-19 run exposed this as a material-result relay flag that did not advance the batch lifecycle, followed by a superseded PM role-work request that still blocked dispatch.

## What Changes

- Add a control-plane state consistency gate before Router computes the next action from durable evidence.
- Make receipt folds update all authoritative lifecycle records they own, not only Router flags.
- Make PM role-work supersession terminalize the old request in indexes, lifecycle records, and packet metadata.
- Make dispatch target-busy checks depend on true recipient ownership or active leases, not stale unrelayed Controller-held requests.
- Add daemon save freshness protection so stale snapshots cannot overwrite newer foreground evidence.
- Stabilize wait reminder identity/cooldown persistence and result-body self-check metadata projection.
- Add FlowGuard model coverage, focused runtime tests, background meta/capability regression evidence, and local install sync.

## Capabilities

### New Capabilities

- `control-plane-state-consistency`: Router must reconcile durable control-plane facts before next-action decisions and must reject stale projection states.

### Modified Capabilities

- `router-controller-ledger-reconciliation`: next-action selection must consume a reconciled durable projection that includes packet batches and PM role-work indexes.
- `stateful-controller-postconditions`: receipt folds must apply complete lifecycle postconditions, not flag-only partial postconditions.
- `dispatch-recipient-gate`: recipient busy checks must distinguish true role-held work from Controller-held or superseded stale requests.
- `daemon-projection-reconciliation`: daemon saves must merge or retry when foreground state changed after the daemon snapshot.
- `wait-reconciliation`: wait reminder materialization must use stable durable wait identity and cooldown state.

## Impact

- Affected runtime code: Controller receipt evidence folds, packet batch projection helpers, PM role-work request registration/lifecycle, dispatch blockers, daemon state saving, wait-reminder receipt/materialization, and packet result self-check metadata parsing.
- Affected verification: new control-plane state consistency FlowGuard model, focused router runtime tests, existing receipt-fold and dispatch-gate models, background meta/capability checks, install sync, and install freshness checks.
- No remote publish, dependency upgrade, sealed-body boundary relaxation, or broad router facade refactor is included.
