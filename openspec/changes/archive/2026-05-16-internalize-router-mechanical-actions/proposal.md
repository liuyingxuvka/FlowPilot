## Why

FlowPilot currently has many local mechanical actions implemented as Python
branches, but some of those actions are still exposed as Controller work rows.
That keeps the Controller busy with Router bookkeeping and creates extra
receipt/reconciliation surfaces where false blockers or duplicate work can
appear.

## What Changes

- Add a Router-internal action boundary for local mechanical work that the
  Router can prove and complete without Controller authority.
- Make startup `user_intake` Router-owned startup material until PM system-card
  bundle ACK is mechanically settled; Controller no longer acts as the
  temporary holder or delivery source for that startup packet.
- Add a deterministic Router settlement pass for mechanical returns. The pass
  normalizes completed ACKs, reconciles matching wait/check rows, and releases
  any Router-owned startup packet whose release condition is satisfied.
- Keep Controller work packages for host-boundary and role-interaction work:
  heartbeat binding, role recovery/rehydration, system-card relay, and normal
  PM/Worker/Reviewer packet handoff remain Controller-visible work.
- Add a focused FlowGuard model before production edits. The model must reject
  known-bad cases where Router-internal work leaks into Controller rows,
  Controller work packages are swallowed by Router, duplicate ticks repeat
  local side effects, sealed bodies are read, or failures are marked as
  success.
- Implement the runtime change in small slices, with focused tests after each
  slice and no heavyweight Meta/Capability simulations unless explicitly
  requested later.
- Sync the installed local FlowPilot skill after verification and leave local
  git with all intended changes visible.

## Capabilities

### New Capabilities

- `router-internal-mechanical-actions`: Defines which FlowPilot actions the
  Router SHALL consume internally, which actions SHALL remain Controller work
  packages, and how FlowGuard/test coverage protects the boundary.

### Modified Capabilities

None.

## Impact

- Affected code:
  - `skills/flowpilot/assets/flowpilot_router.py`
  - `tests/test_flowpilot_router_runtime.py`
  - focused FlowGuard model and runner under `simulations/`
  - install sync/audit scripts as verification commands only
- Affected runtime behavior:
  - local Router bookkeeping should avoid unnecessary Controller action rows;
  - startup `user_intake` should be held and released by Router rather than
    relayed from Controller after ACK;
  - Controller work-package authority should remain intact for role and host
    interactions;
  - Router failures should become explicit blockers or wait states, not silent
    success.
- Non-impact:
  - no public release/publish action;
  - no Meta/Capability heavyweight model run in this task by user direction;
  - no bypass of PM, Reviewer, Worker, or Controller semantic authority.
