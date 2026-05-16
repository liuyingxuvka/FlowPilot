## Why

Formal FlowPilot startup still can reach Controller-led waiting while the
persistent Router daemon was not actually started. That leaves ordinary
Router waits dependent on a later heartbeat or manual command, which violates
the intended one-second Router rhythm.

## What Changes

- Make the persistent Router daemon an unconditional part of formal FlowPilot
  startup, not an optional mode.
- Start the daemon from startup code before Controller core is loaded.
- Fail startup immediately if the daemon cannot be started.
- Keep manual `daemon`, `next`, and `apply` commands available only as
  diagnostics or repair tools, not as the formal startup path.
- Preserve terminal/user stop behavior, where FlowPilot explicitly stops the
  daemon during lifecycle reconciliation.

## Capabilities

### New Capabilities

- `formal-daemon-startup`: Formal FlowPilot startup starts the persistent
  Router daemon as an internal runtime requirement.

### Modified Capabilities

- None. There are no archived OpenSpec specs in this repository yet.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- Router runtime tests under `tests/`
- FlowGuard startup/daemon checks under `simulations/`
- Local installed `flowpilot` skill copy after implementation sync
