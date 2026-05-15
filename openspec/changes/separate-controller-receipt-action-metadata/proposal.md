## Why

Daemon-owned Controller action rows currently carry Router pending-action metadata that still says `apply_required: true` and uses "apply" wording. This conflicts with the Controller ledger contract, where Controller completes rows by performing the row work and writing a `controller-receipt`.

## What Changes

- Add a Controller-ledger-specific action view for `runtime/controller_actions/*.json` so Controller rows expose `controller-receipt` as their completion path.
- Preserve original Router pending-action intent separately when needed, instead of letting `apply_required` imply that a Controller row should use the normal `apply` command.
- Rewrite daemon-scheduled startup/display/role/heartbeat/terminal wording in Controller-visible metadata and cards so receipt rows say "write a Controller receipt" rather than "apply the action".
- Keep true Router pending actions, such as the native startup intake UI pending action, on the existing apply path when they are not being projected into a Controller ledger row.
- Add regression coverage that verifies daemon-scheduled Controller rows do not expose misleading apply semantics while direct pending actions keep the correct apply contract.

## Capabilities

### New Capabilities
- `controller-receipt-action-metadata`: Controller action ledger rows expose a receipt-based completion contract while preserving original Router pending-action metadata separately.

### Modified Capabilities

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/SKILL.md`
- Router runtime regression tests and focused FlowGuard prompt/daemon boundary checks.
