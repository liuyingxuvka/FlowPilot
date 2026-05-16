## Why

FlowPilot's autonomous Router now needs to distinguish nonblocking display
work from workflow-critical evidence. The current failure shows that a small
display/status action can be treated like a hard postcondition gate, causing a
recoverable Controller-side update to escalate into PM repair flow.

## What Changes

- Add four Router evidence classes:
  - Router-owned state writes run inside Router and do not need Controller
    receipts.
  - Controller display/communication work is soft-recorded and cannot block the
    main route.
  - external actions needed to keep the run alive still require lightweight
    hard confirmation.
  - role decisions, reviewer reports, worker results, and PM repair decisions
    continue to require file-backed role-output evidence with hashes and
    runtime receipts.
- Stop treating `visible_plan_synced` as a hard postcondition for display-only
  sync work; write the display state and continue.
- Keep a best-effort `visible_plan_sync`/flag marker for status visibility
  without using it as a PM-repair trigger.
- Preserve strict role-output handling for control-blocker repair decisions.

## Capabilities

### New Capabilities

- `controller-completion-evidence`: Defines four-tier completion handling for
  Router-owned state, Controller display work, external keepalive actions, and
  role-output decisions.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/run_flowpilot_control_plane_friction_checks.py`
- focused router runtime tests
- control-plane FlowGuard result artifacts
- local installed FlowPilot skill sync and install checks
