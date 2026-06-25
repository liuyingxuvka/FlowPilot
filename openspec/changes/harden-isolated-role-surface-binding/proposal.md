## Why

FlowPilot already resolves role reuse, replacement, and blocking through the
runtime, but active AI-facing instructions can still be read too loosely by a
Controller: a `reuse_existing_role` decision may be executed as a fresh chat or
main-thread role attempt when the existing host surface is inconvenient or not
visible after resume/compaction. This change hardens the current prompt and
protocol boundary so role work remains host-neutral, isolated, addressable, and
runtime-directed.

## What Changes

- Clarify Controller-facing dispatch instructions for `reuse_existing_role`,
  `create_new_role`, and `blocked` role-assignment dispositions.
- Clarify that PM, reviewer, worker, FlowGuard operator, and other formal role
  packet work must run inside a host-supported isolated addressable AI execution
  surface, not in the Controller foreground.
- Preserve host neutrality: the execution surface may be a background agent,
  separate thread, new conversation, worker, independent AI session, or another
  equivalent host-supported surface.
- Clarify that missing or unreachable existing role surfaces are recovery or
  blocker conditions unless the runtime explicitly authorizes replacement.
- Add validation coverage that rejects prompt drift toward Controller-owned role
  work, Codex-only wording, or fresh-surface creation during reuse.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: harden prompt and protocol requirements
  for runtime-directed role-surface binding and isolated AI execution surfaces.

## Impact

- Affects FlowPilot skill prompts and protocol/reference text.
- Affects prompt-boundary validation and focused regression coverage.
- Does not change the runtime owner of role assignment decisions.
- Does not add compatibility aliases, fallback single-agent routes, or
  host-product-specific requirements.
