## Why

Foreground Controller standby has become hard to inspect because the same
standby states are repeatedly translated into required modes, return
permissions, patrol flags, and stop-preflight fields. This pass should shorten
that logic without changing the Controller-visible behavior or standby safety
contract.

## What Changes

- Refactor standby state classification into a small internal policy boundary.
- Keep the existing public `foreground_controller_standby` and
  `controller_patrol_timer` outputs compatible.
- Preserve each business state as a distinct state: terminal, user input,
  daemon liveness check, Controller action ready, wait-target check, blocker,
  reissue, waiting-for-role, and daemon-live-no-action.
- Reuse the existing Controller patrol FlowGuard model and focused runtime
  tests as behavior evidence.
- Do not split files, change daemon ownership, or let standby drive Router
  progress.

## Capabilities

### New Capabilities

- `controller-standby-state-policy`: Internal branch-pruning contract for
  deriving standby state, foreground mode, return permission, and final-answer
  preflight from one stable policy.

### Modified Capabilities

- `controller-foreground-standby`: Clarify that internal state/mode policy may
  be simplified only if all existing standby states and outputs remain
  compatible.
- `controller-patrol-timer`: Clarify that patrol result mapping must continue
  to use the standby state and stop-preflight policy without creating a second
  progress authority.

## Impact

- Affected implementation:
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby.py`
- Affected tests and models:
  - `simulations/flowpilot_controller_patrol_model.py`
  - `simulations/run_flowpilot_controller_patrol_checks.py`
  - `tests/test_flowpilot_router_runtime_foreground.py`
  - targeted foreground Controller runtime tests
- No public import, CLI, JSON schema, release, push, or publication is part of
  this change.
