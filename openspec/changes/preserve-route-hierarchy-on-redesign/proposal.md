## Why

Recent live FlowPilot evidence showed a route redesign that improved task
granularity but flattened a complex route into dozens of top-level leaf nodes.
That preserves serial progress but loses the intended parent/module lifecycle:
enter parent, check child decomposition, execute children, replay children
backward into the parent goal, and close the parent before moving on.

## What Changes

- Tighten PM route redesign guidance so initial planning, whole-route redesign,
  and node-entry redesign all produce one canonical executable route tree.
- Require a too-broad current leaf to be promoted into a parent/module when it
  is decomposed; new child nodes must belong under that current node rather
  than being appended as unrelated peers.
- Harden Reviewer and FlowGuard route/process review cards so complex flat
  all-leaf plans are blocked unless PM records a concrete reason that no
  parent/module composition boundary is needed.
- Add focused runtime validation and tests for existing route fields
  (`node_kind`, `parent_node_id`, `child_node_ids`) without adding a parallel
  route-plan schema or compatibility surface.
- Preserve the current staged route-redesign gate: PM still owns the route,
  FlowGuard models it, Reviewer challenges it, and Runtime owns mechanical
  shape rejection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `recursive-route-parent-entry`: route redesign and node-entry decomposition
  must preserve parent/module hierarchy and must not flatten complex child work
  into unrelated top-level leaves.

## Impact

- Runtime route-plan validation and route materialization helpers under
  `skills/flowpilot/assets/flowpilot_core_runtime/`.
- FlowPilot PM, Reviewer, and FlowGuard prompt cards under
  `skills/flowpilot/assets/runtime_kit/cards/`.
- Focused runtime, prompt-card, and FlowGuard simulation tests.
- OpenSpec and FlowGuard evidence records, local install sync, and local git
  commit state after validation.
