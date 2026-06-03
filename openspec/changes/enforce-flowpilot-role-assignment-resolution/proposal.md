## Why

FlowPilot role continuity now records same-responsibility reuse in the current
run ledger, but the public control surface can still tell Controller to supply a
fresh `<new-agent-id>` before the runtime decides whether that fresh role is
needed. That leaves a pre-created candidate role surface even when the ledger
later rejects the candidate and reuses the existing role.

This change removes that compatibility-shaped edge so role assignment is
resolved before any new role surface is opened.

## What Changes

- **BREAKING**: `lease-agent` no longer accepts an arbitrary fresh agent id as
  the public first step for Controller.
- Add a role-assignment resolution step that returns one explicit disposition:
  reuse an existing role, create a new role, or block for role-continuity
  recovery.
- Make Controller-facing next actions and recovery commands name the
  role-assignment resolution step instead of `lease-agent --agent-id
  <new-agent-id>`.
- Keep `lease-agent` as the commit step only after a resolution has authorized
  the effective agent id.
- Block same-responsibility work when the current run already has usable public
  lease history for that responsibility but no role-continuity slot has been
  hydrated.

## Capabilities

### New Capabilities

- `role-assignment-resolution`: Decides whether a packet should reuse an
  existing same-responsibility role, create a new role, or block before any new
  role surface is opened.

### Modified Capabilities

None.

## Impact

- Affected code:
  - `skills/flowpilot/assets/flowpilot_new.py`
  - `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
  - `skills/flowpilot/assets/flowpilot_core_runtime/host.py`
  - role handoff and runtime tests
- Affected behavior:
  - Controller sees a resolve-first command.
  - New role surfaces are opened only when the current runtime resolution says
    `create_new_role`.
  - Reuse decisions no longer require or expose a fresh candidate id.
- No old-router or historical-artifact fallback is introduced.
