## Why

FlowPilot can now stop a semantic blocker with `stop_for_user` when PM cannot
legally repair a control-plane or evidence-runner failure. After the user or
Controller fixes the underlying issue, the current runtime only exposes PM
repair-decision reissue, stop, or cancel. That re-enters the same PM loop
instead of returning the stopped blocker to the original FlowGuard/Reviewer
recheck chain.

## What Changes

- Add an explicit stopped-blocker recovery resolution that reattaches a stopped
  blocker to its required recheck gate after explicit user request.
- Reissue the smallest required recheck packet instead of clearing the blocker
  or sending the decision back to PM.
- Preserve the PM stop boundary: no recovery without `--user-requested`.
- Restore a `pm_stopped` target packet to its pre-stop routing status when
  possible so the recheck chain can continue from the correct point.

## Capabilities

### New Capabilities

- `stopped-blocker-recheck-reattachment`: User-authorized recovery from a
  stopped blocker into the existing FlowGuard/Reviewer recheck path.

### Modified Capabilities

- `blocker-repair-policy`: Stopped blockers can be reattached to their
  required recheck gate after break-glass or user repair.
- `controller-break-glass-repair`: Break-glass exit returns through the
  formal stopped-blocker recheck command rather than direct clearance.
- `flowpilot-packet-review-flow`: Reviewer pass remains the clearing authority
  for review blockers after reattachment.

## Impact

- Runtime stopped-blocker recovery in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- CLI option surface in `skills/flowpilot/assets/flowpilot_new.py`.
- FlowPilot skill and Controller break-glass guidance.
- Focused runtime tests and FlowGuard regression coverage.
