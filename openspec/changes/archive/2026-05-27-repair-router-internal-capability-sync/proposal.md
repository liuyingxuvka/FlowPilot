## Why

`capability_evidence_synced` is a Router-owned deterministic postcondition, but
the current control plane can expose it as a passive Controller wait after the
reviewer ACK, review pass, PM approval, and source artifacts already exist.
That leaves the run stuck even though no human or role decision is actually
missing.

## What Changes

- Classify `capability_evidence_synced` as a Router-internal postcondition
  materialized from existing child-skill manifest, PM approval, and capability
  artifacts.
- Reconcile Router-internal postconditions before creating role-decision waits.
- Keep the existing external-event recording path for compatibility, but make
  the normal daemon/next-action path Router-owned and idempotent.
- Clear stale wait/projection rows once authoritative Router-owned evidence
  exists.
- Extend FlowGuard and runtime tests so this class of false Controller wait is
  caught before release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `router-internal-mechanical-actions`: Router-internal postconditions must be
  materialized by Router when prerequisites and source evidence are ready.
- `router-external-wait-reconciliation`: Router-internal postconditions must
  not be exposed as external role-event waits.
- `daemon-projection-reconciliation`: Daemon reconciliation must clear stale
  projections after Router-owned postcondition evidence appears.

## Impact

- Affected runtime code: expected-wait selection, capability evidence
  synchronization, and Controller projection reconciliation.
- Affected verification: focused runtime tests, control-plane friction
  FlowGuard checks, meta/capability background checks, install sync/audit.
- No release, publication, dependency, frozen acceptance, or target-project
  behavior changes are included.
