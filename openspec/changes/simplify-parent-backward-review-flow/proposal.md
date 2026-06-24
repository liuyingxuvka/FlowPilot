## Why

The previous parent backward replay repair fixed the late glassbreak by adding a
second independent review over the replay result, but that made the route
longer than the intended V-shaped closure path. FlowPilot needs one clean
current-contract path: a parent/module backward check is itself a Reviewer
closure review, PM consumes that review evidence, and downstream work cannot
open until the current parent/module closure is absorbed.

## What Changes

- **BREAKING**: Parent/module backward replay is no longer a current task
  family followed by a second `review.any_current_subject` packet. It becomes a
  single parent backward Reviewer packet/result that carries the reviewer
  signature, pass/block decision, child evidence references, findings,
  blockers, and self-check.
- **BREAKING**: `task.parent_backward_replay` is retired from current positive
  runtime authority. Old or task-shaped parent replay evidence is rejected as an
  unsupported current-contract shape, not translated or promoted.
- Parent/module nodes with children may not advance, open sibling/downstream
  work, bubble upward, or reach terminal replay until their own parent backward
  review has passed and PM has absorbed it through the parent segment decision.
- A normal current route may have at most one active parent backward review
  closure obligation on the frontier. Multiple unclosed parent/module review
  gaps are treated as control-plane corruption or injected bad state, not a
  dependency-ordered repair queue.
- Controller break-glass and final preflight must route a missing current
  parent/module closure to the single parent backward review packet for the
  current frontier node, or hard-block if the route has already advanced past an
  unclosed parent.
- Prompt cards, policy rows, runtime contracts, fake-AI responders, FlowGuard
  models, unit tests, router-tier tests, and acceptance TestMesh coverage must
  all use the same single-path semantics.
- Full fake-AI Cartesian coverage must cover valid current payloads, missing
  field profiles, wrong shape profiles, stale/old evidence profiles, timing
  profiles, route-shape profiles, and injected corrupted multi-gap profiles.

## Capabilities

### New Capabilities

- `single-parent-backward-review`: Current-contract parent/module V-shaped
  closure review semantics, including no-second-review, no-downstream-before-
  absorption, no-fallback old shape rejection, and control-plane hard-blocking
  for impossible multi-gap states.

### Modified Capabilities

- `recursive-route-parent-entry`: Parent/module nodes must close through one
  current parent backward review and PM absorption before downstream frontier
  progression.
- `flowpilot-packet-review-flow`: Parent backward review becomes a first-class
  Reviewer result family rather than a task result plus separate review.
- `flowpilot-closure-kernel`: Final preflight must never repair a skipped
  parent/module closure by promoting old evidence or queueing multiple review
  repairs.
- `router-runtime-testmesh`: Router and fake-AI test tiers must include
  Cartesian current-contract coverage for the single parent backward review
  path and injected corruption blockers.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`,
  `packet_result_contracts.py`, `packet_stage_evidence_matrix.py`,
  `fake_e2e.py`, and run-shell/status projection surfaces.
- Prompt/runtime cards: `reviewer/parent_backward_replay.md`,
  `pm_parent_backward_targets.md`, `pm_parent_segment_decision.md`,
  `reviewer/final_backward_replay.md`, `pm_closure.md`, and
  `controller_break_glass_repair.md`.
- Policy and docs: runtime route-action policy registry, FlowPilot protocol and
  failure-mode references, README, changelog, version, and local install sync.
- Validation: new FlowGuard model/check runner, fake-AI Cartesian matrix,
  core runtime tests, new-entrypoint fake E2E tests, router route/packet/
  terminal tiers, acceptance TestMesh, model-test alignment, topology, install
  checks, and release-tier background evidence.
