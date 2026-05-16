## Why

FlowPilot currently protects dispatch with several local checks, but the rules
are split across system-card ACK clearance, packet relay validation, parallel
batch registration, active-holder leases, and PM role-work routing. A Router
path can still expose a new role-facing dispatch row without one unified check
that the same target role is idle from previous unfinished work.

## What Changes

- Add one Router-owned pre-dispatch recipient gate for role-facing deliveries
  before they are exposed as Controller work.
- Preserve the existing local gates for packet legality, system-card ACK
  clearance, same-batch duplicate-role rejection, and active-holder authority.
- Add the missing cross-path rule: a target role must not receive a new
  independent work packet, mail, system-card bundle, or PM role-work request
  while that same role still owns unfinished prior work.
- When the gate blocks dispatch, Router should expose or preserve the wait for
  the prior unfinished obligation instead of adding the new delivery row.
- Keep same-role system-card bundles valid as one grouped delivery, and keep
  different idle roles able to work in parallel.

## Capabilities

### New Capabilities

- `dispatch-recipient-gate`: Router checks role-facing dispatches through a
  single pre-dispatch gate that combines existing dispatch legality checks with
  a recipient-idle rule.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- Focused router runtime tests for blocked same-role dispatch and allowed idle
  or grouped dispatch.
- A focused FlowGuard model/check for dispatch gate safety. Heavy Meta and
  Capability simulations are deferred per user instruction unless the touched
  boundary later proves to depend on them.
