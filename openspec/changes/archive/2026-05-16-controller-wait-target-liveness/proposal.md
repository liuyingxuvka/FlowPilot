## Why

FlowPilot Controller standby already keeps the foreground turn attached to the
Router daemon, but the monitor does not clearly say who is being waited on,
what should appear, or what Controller must check during repeated waits. This
can leave Controller passively watching stale status when a background role is
lost, unresponsive, or blocked.

## What Changes

- Add a wait-target monitor contract to Router daemon status for Controller
  standby.
- Split wait handling into three simple classes: ACK waits, role
  report/result waits, and Controller-local actions.
- For ACK waits, require a reminder after three minutes and a PM-routed blocker
  after ten minutes without the ACK.
- For role report/result waits, require a reminder every ten minutes and an
  active liveness probe on each reminder cycle.
- Keep liveness as a check obligation plus last-check evidence, not a cached
  "role is alive" truth in the monitor.
- For Controller-local actions, require Controller to self-audit the action
  ledger and receipts instead of sending reminders.
- Route lost, cancelled, missing, unresponsive, or self-blocked roles through
  the existing Router control-blocker and PM recovery path.

## Capabilities

### New Capabilities

- `controller-wait-target-liveness`: Controller standby reads Router-authored
  wait target metadata, sends bounded reminders, performs required liveness
  checks, self-audits Controller-local waits, and escalates unhealthy waits to
  the existing PM blocker flow.

### Modified Capabilities

- `controller-foreground-standby`: Existing foreground standby now carries
  wait-target metadata and reminder/liveness obligations instead of only a
  generic live-daemon wait.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- Controller role/runtime guidance under `skills/flowpilot/assets/runtime_kit/`
- FlowGuard standby/daemon model and focused checks
- Router runtime tests for ACK reminder/blocker, report reminder liveness, and
  Controller-local self-audit
- Local install sync and audit checks
