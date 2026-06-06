## Why

FlowPilot now requires background or parallel AI role execution as a product
contract. Earlier startup wording treated background collaboration as a user
choice that could fall back to single-agent continuity. That fallback weakens
the new FlowPilot runtime because tests may pass through an old single-agent
path instead of proving the current structured route.

This change makes the current path explicit: FlowPilot must attempt to use a
host-supported isolated addressable background role surface. If the host cannot
provide that surface, or the user-facing startup acknowledgement is disabled,
FlowPilot must stop with a structured reason instead of continuing through a
single-agent fallback or legacy role/heartbeat path.

## What Changes

- Treat background or parallel role execution as mandatory for FlowPilot runs.
- Change the startup background UI from an optional mode choice into a required
  capability acknowledgement.
- Stop startup, resume rehydration, and role recovery when background role
  capability is unavailable or not acknowledged.
- Remove current positive paths for single-agent role continuity fallback.
- Keep on-demand role assignment as the current path through
  `resolve-role-assignment` and `lease-agent`.
- Add negative tests and fake-AI package coverage for disabled acknowledgement,
  missing capability evidence, old startup fields, single-agent fallback claims,
  legacy heartbeat, and fixed startup role actions.

## Impact

- Startup intake UI, startup answer validation, bootstrap state, role
  rehydration, and role recovery payload checks.
- FlowPilot runtime prompts/cards that describe background role capability,
  old fallback behavior, or unsupported legacy startup choices.
- FlowGuard startup and PM-review models, capability/meta parents, synthetic
  fake-AI tests, router runtime tests, and install readiness checks.
- Local install synchronization after the repository implementation is verified.
