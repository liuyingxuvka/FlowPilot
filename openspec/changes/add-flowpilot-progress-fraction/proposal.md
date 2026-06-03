## Why

Long FlowPilot runs can last for many hours without a simple user-visible sense
of how much currently expanded work has already ended. A runtime-owned progress
fraction gives the Controller a lightweight status signal without turning
progress into a completion gate or asking the Controller to inspect sealed work.

## What Changes

- Add a runtime-owned `progress_fraction` object to public FlowPilot status and
  action outputs.
- Count every currently expanded work node equally, including repair work
  nodes, while excluding control-plane mechanics such as ACKs, leases, patrols,
  liveness checks, and role-assignment resolution.
- Represent progress as a simple `ended_nodes/expanded_nodes` display string
  plus numeric fields, not as a percent.
- Teach Controller-facing instructions to relay the runtime-provided fraction
  when useful, without calculating it, converting it to a percent, or treating
  it as completion authority.

## Capabilities

### New Capabilities

- `flowpilot-progress-fraction`: Runtime-owned current expanded node progress
  reporting and Controller relay guidance.

### Modified Capabilities

None.

## Impact

- FlowPilot runtime public output schema and status payloads.
- Controller/system prompt guidance that describes user status reporting.
- Focused runtime and prompt tests.
- Local FlowPilot install-sync evidence after repository changes.
