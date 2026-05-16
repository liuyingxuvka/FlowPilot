## Why

FlowPilot currently exposes the startup heartbeat host action after
`load_controller_core`, which makes a host continuation authority look like
ordinary Controller work. The startup gate should establish real continuation
before the Controller core boundary so later Controller actions can focus on
relay, status, and role-boundary duties.

## What Changes

- Move the scheduled-continuation heartbeat creation boundary before
  `load_controller_core` when the startup intake selected heartbeat
  continuation.
- Preserve manual-resume behavior: no heartbeat action is emitted when the
  startup answer selected manual continuation.
- Keep resume/recovery behavior available after Controller entry only for
  repairing or consuming existing continuation state, not for first-time
  startup heartbeat creation.
- Add FlowGuard coverage and runtime tests that fail if `load_controller_core`
  can happen before the requested startup heartbeat host receipt is recorded.

## Capabilities

### New Capabilities

- `startup-continuation-bootstrap`: Startup establishes requested continuation
  authority before Controller core handoff.

### Modified Capabilities

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- `simulations/meta_model.py` and generated FlowGuard result files
- Local FlowPilot skill installation after validation
