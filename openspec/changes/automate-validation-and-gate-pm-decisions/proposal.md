## Why

The fresh FlowPilot runtime currently sends ordinary packet results through a
fixed `FlowGuard -> Reviewer -> Validator -> Closure` chain even though Router
already enforces the ordering and stale-evidence rules mechanically. At the
same time, some PM decisions that can mutate route state or waive blockers
apply directly after PM submission.

This change keeps the reliable fixed-flow benefit while removing the redundant
AI validator hop from ordinary successful work and strengthening high-risk PM
decisions before they can change control state.

## What Changes

- Replace ordinary Validator work packets with a system-owned validation
  evidence check after reviewer pass.
- Keep validation evidence as a ledger artifact used by closure; do not remove
  validation evidence or closure blockers.
- Preserve legacy validation packet handling for old or repair runs that
  already contain validator packets.
- Classify PM repair and PM disposition decisions by risk.
- Let low-risk PM repair decisions reissue or collect work directly because
  they still require downstream recheck.
- Require high-risk PM decisions such as route mutation and waiver to pass a
  FlowGuard packet and reviewer packet before applying the decision.
- Keep PM accept after a fully closed node direct, unless the PM decision tries
  to change scope, waive evidence, or mutate the route.

## Capabilities

### New Capabilities
- `new-flowpilot-validation-automation-and-pm-risk-gates`: System-owned
  validation evidence and high-risk PM decision gating in the fresh runtime.

### Modified Capabilities
None. This change adds the fresh-runtime automation/risk-gate contract while
remaining compatible with active, not-yet-archived new FlowPilot change
artifacts.

## Impact

- Runtime packet progression in
  `skills/flowpilot/assets/ai_project_runtime/runtime.py`.
- Focused high-standard runtime tests.
- FlowGuard model and runner for validation automation and PM decision gates.
- Related active change artifacts for semantic gate outcomes and formal
  entrypoint behavior remain source context but are not archived base specs.
- OpenSpec validation and install-sync confidence for the local `flowpilot`
  skill.
