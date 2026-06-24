# Add PM Break-Glass Exit

## Why

PM can currently stop a semantic blocker for user input, and FlowPilot already
has Controller break-glass repair for control-plane failures. The gap is that
some PM decision packets expose `stop_for_user` as the only legal non-repair
exit even when the evidence points to a FlowPilot control-plane defect.

That means a missing-material, packet-contract, event-authority, or legal-next
action failure can be pushed to the user even though it should first enter the
existing break-glass repair lane.

## What Changes

- Add `break_glass` as a PM sibling decision wherever the current PM contract
  already lets PM stop for user or environment because normal continuation is
  not possible.
- Keep `stop_for_user` for substantive user decisions such as scope, goal,
  acceptance, authority, or cancellation.
- Route `break_glass` to the existing Controller control-plane blocker duty
  and break-glass playbook. It must not pass gates, waive blockers, mutate
  routes, close work, or read sealed bodies.
- Update PM cards, contract enums, runtime validators, fake AI package
  coverage, and Cartesian/model checks together.
- Preserve the new-only FlowPilot contract. Do not add compatibility fallback
  for older packet shapes.

## Non-Goals

- No new recovery subsystem.
- No extra user-confirmation loop before break-glass.
- No broad new field mesh.
- No authority for Controller break-glass to approve project work, route
  mutation, PM decisions, Reviewer decisions, FlowGuard Operator decisions, or
  terminal closure.
