## Why

The fresh FlowPilot runtime currently sends ordinary packet results through a
fixed `FlowGuard -> Reviewer -> Validator -> Closure` chain even though Router
already enforces the ordering and stale-evidence rules mechanically. At the
same time, some PM decisions that can mutate route state or waive blockers
apply directly after PM submission.

This change keeps the reliable fixed-flow benefit while removing the redundant
AI validator hop from ordinary successful work and requiring PM
continue-repair decisions to pass the same current gate before they can change
control state or release repair work.

## What Changes

- Replace ordinary Validator work packets with a system-owned validation
  evidence check after reviewer pass.
- Keep validation evidence as a ledger artifact used by closure; do not remove
  validation evidence or closure blockers.
- Preserve legacy validation packet handling for old or repair runs that
  already contain validator packets.
- Stage PM continue-repair decisions before applying their side effects or
  opening resulting repair work.
- Require FlowGuard, PM absorption, reviewer, system validation, and system
  closure before the staged PM continue-repair decision applies.
- Keep PM accept after a fully closed node direct, unless the PM decision tries
  to change scope, waive evidence, or mutate the route.

## Capabilities

### New Capabilities
- `new-flowpilot-validation-automation-and-pm-risk-gates`: System-owned
  validation evidence and unified PM continue-repair decision gating in the
  fresh runtime.

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
