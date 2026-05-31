## Why

The current FlowPilot runtime can assign packets and accept results, but the role handoff is still easy for Controller to improvise incorrectly. A live PM run stopped after ACK because the role was told to wait for runtime-delivered body text instead of using current lease authority to open its assigned packet.

## What Changes

- Add a Controller-safe, runtime-generated role handoff template for every requested packet responsibility, not just PM.
- Add a formal current-run `open-packet` command that lets the assigned active role open only its own packet body after ACK.
- Return the generated handoff from `lease-agent` and expose a re-render command so Controller does not hand-write packet authority instructions.
- Keep sealed body content out of Controller-visible status, handoff text, progress, and public reports.
- Update role cards, specs, FlowGuard evidence, and tests so PM, worker, reviewer, FlowGuard operator, research worker, and UI QA packet flows share the same rule.
- Sync the repository-owned FlowPilot skill to the local installed skill after validation.

## Capabilities

### New Capabilities
- `flowpilot-role-packet-access`: runtime-generated role handoff text and role-scoped packet opening for current-run leased packets.

### Modified Capabilities
- `new-flowpilot-formal-entrypoint`: `lease-agent` exposes the safe role handoff and `open-packet` becomes part of the current packet lifecycle.
- `flowpilot-prompt-boundary-policy`: prompt/card surfaces must point all roles to the runtime-generated handoff and formal open command instead of ad hoc Controller wording.
- `packet-open-authority-exits`: packet open authority is current assignment plus active lease plus ACK plus role/hash checks, not Controller relay signatures or chat-only permission.
- `known-friction-regression-gates`: the missing role handoff/body exposure failure is registered as a hard regression row.

## Impact

- Affected runtime code: `flowpilot_new.py`, `flowpilot_core_runtime/packets.py`, and a new runtime handoff helper.
- Affected prompt surfaces: role cards, packet identity prompt, Controller card, and FlowPilot skill launcher guidance.
- Affected tests/models: core runtime tests, card instruction coverage, packet access FlowGuard checks, known-friction evidence, OpenSpec validation, topology check, and install sync checks.
- No dependency or public stack change.
