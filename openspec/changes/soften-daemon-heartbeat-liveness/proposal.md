## Why

FlowPilot currently treats a short Router daemon heartbeat delay as a daemon repair/restart condition too early. In practice a one-second tick can be delayed briefly by host scheduling or file I/O, so Controller should not be told that the daemon is stale until a real liveness check proves it is gone.

## What Changes

- Add a five-second heartbeat grace window for foreground daemon monitoring.
- Change monitor output from early `daemon_repair_or_restart` decisions to a two-state heartbeat status: `ok` or `check_liveness`.
- Make `check_liveness` instruct Controller to inspect the current daemon process/lock/status and choose either attach/continue or safe recovery.
- Preserve the single-writer daemon lock rule: recovery must attach if an active daemon is found and restart only when the daemon is actually dead.
- Update user-facing wording so transient heartbeat delay is not reported as "stale" before Controller verifies it.
- Extend FlowGuard and runtime tests for delayed heartbeat, alive-after-delay, dead-after-delay, and active-writer attach cases.

## Capabilities

### New Capabilities
- `daemon-heartbeat-liveness`: Foreground daemon monitor status distinguishes normal heartbeat age from liveness-check-needed age, leaving recovery judgement to Controller.

### Modified Capabilities
- `persistent-router-daemon`: Daemon lock replacement remains allowed only after liveness verification proves the prior daemon is not active.
- `controller-patrol-timer`: Patrol output should surface `check_liveness` rather than a premature repair/restart outcome when heartbeat age exceeds the grace window.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- Focused daemon reconciliation and/or patrol FlowGuard simulations under `simulations/`
- Runtime tests in `tests/test_flowpilot_router_runtime.py`
- Install/self-check coverage in `scripts/check_install.py` if new model runners or result artifacts are added
- FlowPilot skill instructions and local installed skill synchronization after repository changes
