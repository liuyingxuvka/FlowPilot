## Why

Router receipt reconciliation can currently turn a missing Controller
postcondition into a PM repair blocker even when the failure is a mechanical
Controller/Router synchronization issue. That is too coarse: the existing
blocker policy already has a direct retry path, and this case should use that
path before PM is involved.

## What Changes

- Classify `controller_action_receipt_missing_router_postcondition` as a
  mechanical control-plane reissue while its direct retry budget remains.
- Preserve the existing two-attempt direct retry budget and escalate to PM only
  after the retry budget is exhausted or evidence is invalid.
- Keep semantic, route-changing, fatal, and self-interrogation blockers on
  their existing PM/fatal lanes.
- Normalize retry-budget metadata so zero-budget PM blockers are not reported
  as having a still-available direct retry path.

## Capabilities

### New Capabilities

- `controller-postcondition-blocker-routing`: Covers how Router classifies and
  routes missing Controller postcondition blockers through direct retry before
  PM escalation.

### Modified Capabilities

- None.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected validation: focused Router runtime tests, daemon reconciliation
  projection, and router process liveness checks.
- No dependency or public API changes.
