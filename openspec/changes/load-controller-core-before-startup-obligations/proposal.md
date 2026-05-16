## Why

FlowPilot startup currently projects `emit_startup_banner` into the Controller
action ledger before `load_controller_core` is complete. That makes a
Controller-owned row appear before Controller is officially on duty, which
blurs the authority boundary and confuses the daemon-owned startup flow.

## What Changes

- Treat `load_controller_core` as the first Controller-ledger startup handoff
  after native startup intake and deterministic user-intake materialization.
- Queue startup obligations such as `emit_startup_banner`,
  `create_heartbeat_automation`, and `start_role_slots` only after Controller
  core has been loaded.
- Preserve the existing daemon-owned Router scheduler, Controller receipt
  reconciliation, startup intake sealed-body boundary, and heartbeat host proof
  contract.
- Update FlowGuard models and focused runtime tests so the old order is a
  known-bad case.

## Capabilities

### New Capabilities

- `startup-controller-core-ordering`: Startup control-plane ordering for
  Controller core handoff before Controller-ledger startup obligations.

### Modified Capabilities

- None.

## Impact

- Affected files: `skills/flowpilot/assets/flowpilot_router.py`, FlowGuard
  startup/order models under `simulations/`, focused router runtime tests,
  OpenSpec artifacts, local installed FlowPilot skill synchronization, and
  installation audit results.
- No public API changes, no dependency changes, and no change to native startup
  intake schemas or sealed user request body access.
