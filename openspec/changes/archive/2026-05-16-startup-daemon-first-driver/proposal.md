## Why

Formal FlowPilot startup currently starts the Router daemon only after startup
intake, role creation, and heartbeat binding have already happened. A live
run showed the daemon was started before Controller core, but not as the first
startup driver. That lets early startup work bypass the same Router table /
Controller table protocol used later in the run.

## What Changes

- Create the minimal run shell first, then start or attach the one-second
  Router daemon before startup UI, role startup, heartbeat binding, or
  Controller core work.
- Make the daemon schedule startup bootloader rows into the same Controller
  action ledger and Router scheduler ledger used after startup.
- Keep the Controller table simple: Controller sees one row at a time, does
  the work, and checks the row off. Router keeps ordering, dependency, barrier,
  and reconciliation state in its own scheduler ledger.
- Let Router continue scheduling nonblocking startup rows until it reaches a
  real barrier. Barriers include user answers, host automation/spawn work,
  payload requirements, current-scope reconciliation, and Controller core
  handoff.
- At the startup review gate, require current startup-scope reconciliation:
  pending ACKs, receipts, startup daemon rows, and required postconditions must
  be clean before reviewer real-time/fact review starts.
- Fail startup or surface a repair action if the daemon cannot schedule startup
  work; do not silently fall back to foreground-only bootloader ordering.

## Capabilities

### New Capabilities

- `startup-daemon-first-driver`: The Router daemon is the startup driver after
  minimal run-shell creation and before external startup work.

### Modified Capabilities

- `formal-daemon-startup`: Strengthens "daemon before Controller core" into
  "daemon first, then daemon-scheduled startup work."
- `router-two-table-async-scheduler`: Extends the existing two-table async
  scheduling rule to bootloader startup rows.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- FlowPilot skill/runtime prompt cards and protocol references
- Focused startup/router runtime tests under `tests/`
- Focused FlowGuard startup scheduler model/checks under `simulations/`
- Local installed `flowpilot` skill copy after implementation sync

This focused change does not require the heavyweight `run_meta_checks.py` or
`run_capability_checks.py` regressions.
