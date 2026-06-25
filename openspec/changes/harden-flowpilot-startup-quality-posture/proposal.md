## Why

FlowPilot already has strong packet, route, reviewer, and child-skill quality
rules, but the startup-to-PM bridge can still look like a narrow mechanical
handoff. A sparse startup request must not let the first PM route establish a
lower quality floor that later packets merely inherit.

## What Changes

- Strengthen existing startup/PM prompt cards so a normal fresh FlowPilot
  startup carries a high-quality current-run posture into product architecture,
  route drafting, node acceptance planning, and work packets.
- Keep the change prompt/template-only at the operational surface: no new
  runtime fields, schemas, packet kinds, ledgers, launch modes, compatibility
  aliases, or fallback paths.
- Keep non-operational workflow vocabulary out of role-facing startup, PM, and
  backend packet prompts; dedicated tests and models may still name bad-case
  variants.
- Extend existing planning-quality and reviewer-quality checks so missing
  startup quality projection is caught before install synchronization.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `startup-intake-control-plane-prompt`: startup prompt guidance now requires
  the PM release to preserve the normal high-quality current-run work posture.
- `flowpilot-prompt-boundary-policy`: formal prompts must not present
  alternate non-operational startup paths or mode choices to role agents.
- `formal-gate-review-standards`: route and reviewer gates must reject a
  shallow route that lost the startup/product quality floor.

## Impact

- Affected prompt/card files under
  `skills/flowpilot/assets/runtime_kit/cards/`.
- Affected reusable templates under `templates/flowpilot/`.
- Affected focused validation under `simulations/`, `tests/`, and
  `scripts/check_runtime_card_capability_reminders.py`.
- No dependency, package schema, runtime state, or public CLI change.
