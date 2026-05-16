## Why

FlowPilot startup currently shows a separate `FlowPilot Startup Status` card
whose only user-facing content is that the controller is waiting for a PM route.
The startup banner already confirms FlowPilot activation, and the startup Route
Sign already owns the route-shaped display, so the extra waiting card adds
visual noise without helping the user understand progress.

## What Changes

- Stop requiring the controller to paste the `FlowPilot Startup Status` waiting
  card into the user dialog when no PM route exists.
- Keep the internal `display_plan.json` waiting projection and route authority
  guard so Controller still cannot invent route items before PM route approval.
- Keep startup Route Sign display as the only user-visible route placeholder
  before a canonical route exists.
- Keep canonical route display unchanged after PM activates a reviewed route.

## Capabilities

### New Capabilities

- `startup-display-surface`: Defines which startup display artifacts are
  user-visible before PM route activation, and which waiting-state records stay
  internal.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- FlowGuard display/startup models and result files that cover startup waiting
  display behavior
- FlowGuard adoption evidence and local installed FlowPilot skill sync
