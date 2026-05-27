## Why

The live FlowPilot run exposed a control-plane miss where a new role liveness
fault opened a fresh role recovery transaction, but an older successful
recovery report was reclaimed as current proof. This let Router/Controller keep
waiting on a Project Manager agent that the host could no longer address.

## What Changes

- Require role recovery readiness to bind to the latest recovery transaction,
  affected role set, crew slot transaction markers, and fresh host
  addressability evidence.
- Split "replacement was requested or spawned" from "replacement is currently
  addressable" for role slots and active-holder leases.
- Prevent blocked or empty recovery receipts from reclaiming stale recovery
  reports that do not match the current transaction.
- Add daemon diagnostics for fatal runtime errors, especially memory pressure,
  and reduce default state output size for routine Controller/daemon loops.
- Add targeted regression and FlowGuard model evidence for stale report reuse,
  unknown liveness, replacement-not-yet-active, and daemon diagnostic coverage.

## Capabilities

### New Capabilities
- `role-recovery-liveness-proofs`: Defines current role recovery proof
  freshness, host addressability, replacement-proof semantics, and report
  reclaim rules.

### Modified Capabilities
- `daemon-lifecycle-recovery`: Require recovered or replaced role cohorts to be
  current-transaction scoped and host-addressable before dependent work resumes.
- `resume-rehydration-obligation-replay`: Block resume replay and PM resume
  delivery when role recovery evidence is stale, partial, or not
  host-addressable.
- `role-recovery-obligation-replay`: Require role obligation replay to start
  only after current transaction recovery evidence is proven, not merely after a
  role id exists.
- `persistent-router-daemon`: Require actionable fatal-error diagnostics and
  compact default status output for daemon/Controller monitoring paths.

## Impact

- Runtime recovery code under `skills/flowpilot/assets/`.
- Router daemon and CLI state/status output.
- Router runtime tests under `tests/router_runtime/` and singleton/model
  alignment tests.
- FlowGuard singleton identity and persistent daemon model/check artifacts.
- Local installed FlowPilot skill sync and install-readiness checks.
