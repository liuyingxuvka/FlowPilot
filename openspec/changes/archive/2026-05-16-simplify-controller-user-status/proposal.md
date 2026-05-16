## Why

FlowPilot Controller status updates can surface internal router and packet
terms that are useful to the control plane but hard for users to understand.
The status surface should show what is happening without exposing diagnostic
metadata unless the user asks for it.

## What Changes

- Add a Controller prompt rule requiring user-facing reports to use plain
  language and avoid internal event names, packet ids, ledger names, hashes,
  action ids, contract names, and diagnostic paths by default.
- Add a Router action reminder so every Controller action carries the same
  user-facing plain-language boundary when the action is mentioned to the user.
- Change the current status summary from a broad technical status object into a
  source that also carries compact progress facts: route depth, per-level
  position and completion counts, overall completion count, elapsed runtime,
  and coarse state.
- Keep route signs, worker progress prompts, language detection, translation
  tables, and sealed-body boundaries out of scope.

## Capabilities

### New Capabilities

- `controller-user-status`: Defines plain-language Controller user reporting
  and compact progress-fact status summary behavior.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- Focused router/runtime tests for action contracts and status summary shape
- FlowGuard model coverage for user-facing status leakage and progress-fact
  summary requirements
- Local installed FlowPilot skill sync and install audit checks
