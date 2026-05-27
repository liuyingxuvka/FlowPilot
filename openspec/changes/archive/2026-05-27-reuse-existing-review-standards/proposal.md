## Why

The simplified PM-to-Reviewer packet flow now sends Reviewer a PM-built formal
gate package, but the package can still make the current acceptance source too
implicit. That creates a risk that Reviewer either judges from a broad pile of
background standards or blocks because the current gate's existing standard is
not easy to find.

## What Changes

- Preserve the simplified flow: Worker or Officer results return to PM, PM
  records disposition, PM releases a formal gate package, and Reviewer reviews
  that package.
- Reuse existing acceptance sources instead of introducing a new acceptance
  criteria schema.
- Ensure PM formal gate packages expose existing packet/result references that
  let Reviewer find the source packet acceptance slice, output contract, and
  node acceptance plan when applicable.
- Clarify Reviewer instructions: pass or block the current gate from the
  current packet acceptance slice, source output contract, formal package, and
  node acceptance plan when applicable; keep higher-standard ideas as PM
  suggestion items unless they expose a hard current-gate failure.
- Keep the existing blocker path for missing standards or missing evidence:
  Reviewer blocks with `blockers` and `recommended_resolution`; PM decides the
  repair or reissue path.

## Capabilities

### New Capabilities
- `formal-gate-review-standards`: PM formal gate packages and Reviewer reviews
  reuse existing packet acceptance, output-contract, node-plan, blocker, and
  suggestion-ledger structures.

### Modified Capabilities

## Impact

- Affected runtime package writer:
  `skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions.py`
- Affected Reviewer prompt cards:
  `skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md`
  and focused Reviewer gate cards.
- Affected FlowGuard models and checks for PM formal package release and
  Reviewer gate start.
- Affected focused tests for PM formal gate package content and control gates.
- No dependency changes, publishing, remote push, or broad refactor.
