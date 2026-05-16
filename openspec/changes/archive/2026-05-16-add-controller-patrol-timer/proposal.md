## Why

FlowPilot's foreground Controller can still misread a quiet controller action
ledger as permission to end the chat even while the Router daemon is alive.
The existing monitor should remain the live source of truth, but Controller
needs an executable foreground keepalive duty that prevents accidental exit.

## What Changes

- Add a Controller patrol timer command that waits for a bounded interval,
  reads the existing Router daemon monitor and Controller action ledger, then
  returns a concrete next instruction.
- Keep the existing Router daemon monitor automatic; the patrol timer wraps
  that monitor for foreground Controller attention rather than replacing it.
- Harden the four existing Controller prompt surfaces so they name the exact
  patrol command and the anti-exit purpose.
- Require `continuous_controller_standby` to remain `in_progress` until the
  patrol command returns new Controller work, a terminal stop allowance, or
  another non-standby duty.
- Require `continue_patrol` outputs to say that Controller must rerun the same
  command and wait for that command's next output. Starting or restarting the
  command is not task completion.

## Capabilities

### New Capabilities

- `controller-patrol-timer`: Controller foreground keepalive patrol over the
  existing Router daemon monitor.

### Modified Capabilities

None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- focused FlowGuard model and runtime tests for Controller patrol behavior
- local FlowPilot install synchronization and install audit
