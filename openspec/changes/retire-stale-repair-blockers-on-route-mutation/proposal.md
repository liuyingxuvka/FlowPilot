## Why

Route mutation already quarantines old packets and supersedes old route nodes, but stale `repair_packet_open` blocker rows from older route versions can remain visibly open in the raw ledger. ProjectRadar exposed that this is confusing for audits and can become a future control-plane hazard even when current status/final-preflight already ignore those rows.

## What Changes

- Retire `repair_packet_open` blocker rows from older route versions when a route mutation advances the active route version.
- Preserve those rows as append-only history by using the existing `superseded_by_route_mutation` disposition and existing supersession metadata.
- Keep current-version repair-open blockers and blockers without a provably stale numeric route version unchanged.
- Add focused runtime tests and FlowGuard/model-test alignment coverage for stale-route-version blocker retirement.
- Keep the repair minimal: no new blocker fields, no new packet kind, no new reviewer/PM workflow, and no status-read mutation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `blocker-repair-policy`: route mutation must disposition older-route repair-open blockers as historical instead of leaving them runtime-open.
- `controller-user-status`: current status must not present route-mutation-superseded repair blockers as an active wait.

## Impact

- Runtime route-mutation helper in `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Focused runtime tests in `tests/test_flowpilot_core_runtime.py`.
- FlowGuard information-flow models and model-test alignment plan/results for route mutation and repair-blocker currentness.
- Local install sync and install audit after repository-owned skill files change.
