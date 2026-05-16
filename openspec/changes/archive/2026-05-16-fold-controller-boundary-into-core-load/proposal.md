## Why

FlowPilot startup currently exposes a standalone
`confirm_controller_core_boundary` Controller action after
`load_controller_core`. That separate row asks Controller to restate the
boundary it has just received, adding a redundant foreground step and another
receipt surface during startup.

The safety property is still needed: Router must have a durable Controller
boundary confirmation before later startup review and work dispatch. The
separate visible startup action is the part to remove.

## What Changes

- Fold fresh-run Controller boundary confirmation into the
  `load_controller_core` postcondition.
- Keep the existing boundary artifact, runtime receipt shape, hashes, and
  Router flag checks.
- Do not schedule `confirm_controller_core_boundary` as a fresh startup
  Controller row once `load_controller_core` has reconciled successfully.
- Preserve compatibility for existing runs that already contain a pending or
  completed `confirm_controller_core_boundary` row.
- Update FlowGuard startup/control-plane models and focused runtime tests so
  the old two-step startup path is a known-bad regression.

## Capabilities

### New Capabilities

- `controller-boundary-core-load`: Controller boundary confirmation ownership
  during startup core loading.

### Modified Capabilities

- None.

## Impact

- Affected files: `skills/flowpilot/assets/flowpilot_router.py`,
  FlowGuard startup/control-plane simulations, focused router runtime tests,
  OpenSpec artifacts, local installed FlowPilot skill synchronization, and
  install/audit verification output.
- No public API changes, no new dependency, no change to sealed startup intake
  body handling, and no weakening of Controller/PM/Worker/Reviewer authority.
