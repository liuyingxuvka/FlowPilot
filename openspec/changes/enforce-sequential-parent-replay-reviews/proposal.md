## Why

FlowPilot currently accepts parent/module backward replay task results after
matching FlowGuard evidence, but the independent Reviewer review required for
that replay result can be discovered only at final closure. In nested routes,
final closure may then report both a child/module replay and the top-level
replay as missing independent review, flattening a dependency-ordered problem
into parallel blockers and forcing Controller break-glass to create routable
review packets.

This must be repaired in the current contract path only: future FlowPilot runs
must follow one clean child-to-parent closure sequence, with no old-run
migration, legacy fallback, field alias, or compatibility translation.

## What Changes

- **BREAKING**: Parent/module backward replay task acceptance no longer closes
  the parent replay obligation by itself. It must be followed by an accepted
  independent review of the parent replay result.
- **BREAKING**: Parent/top-level replay may not be issued or consumed while an
  effective child/module replay is missing its independent review.
- **BREAKING**: Terminal backward replay may not be issued until every
  effective parent/module/top-level replay result has an accepted independent
  review.
- Final closure may still report all discovered missing review evidence for
  diagnostics, but the runtime must expose only the deepest/earliest missing
  parent replay review as the next actionable repair.
- Runtime review-packet generation must create normal current Reviewer packets
  for accepted parent replay task results, reusing the existing
  `review.any_current_subject` / `parent_backward_replay_review` contract.
- Prompt cards and policy rows must state that PM segment decisions and
  terminal closure depend on reviewed parent replay evidence, not only replay
  task acceptance.
- Fake-AI, unit, FlowGuard, and route-tier regressions must cover child +
  parent simultaneous missing-review cases, terminal replay gating, no duplicate
  review packets, and the fact that a reviewer-owned parent replay task is not
  itself the independent review.
- No migration or compatibility path is added for old or currently running
  runs. Historical runs are regression evidence only and must not become
  current completion evidence.

## Capabilities

### New Capabilities

- `sequential-parent-replay-review`: Current-contract ordering for parent,
  module, and top-level backward replay review gates, including no-fallback
  final-closure repair action selection.

### Modified Capabilities

- `recursive-route-parent-entry`: Parent/module nodes must remain in the route
  frontier until their replay result has an accepted independent review.
- `flowpilot-packet-review-flow`: Parent backward replay task results must
  generate and consume independent Reviewer packets through the current review
  contract.
- `flowpilot-closure-kernel`: Final closure must distinguish diagnostic
  blocker aggregation from the single dependency-ordered actionable repair.
- `router-runtime-testmesh`: Route and runtime test tiers must include focused
  parent-replay-review ordering and missing-review regression coverage.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Review contracts and evidence matrices:
  `review_window_contracts.py`, `packet_stage_evidence_matrix.py`, and related
  contract test surfaces.
- Prompt/runtime cards:
  `pm_parent_backward_targets.md`, `reviewer/parent_backward_replay.md`,
  `pm_parent_segment_decision.md`, `reviewer/final_backward_replay.md`,
  `pm_closure.md`, and `controller_break_glass_repair.md`.
- Policy and validation:
  `runtime_kit/route_action_policy_registry.json`, fake-E2E responder,
  FlowGuard simulations, unit tests, route-tier tests, install sync, topology,
  version, and changelog.
