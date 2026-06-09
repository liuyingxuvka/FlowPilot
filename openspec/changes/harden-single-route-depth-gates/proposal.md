## Why

Recent FlowPilot route work shows that the simplified runtime can still drift
toward a small set of broad route nodes when the PM, FlowGuard operator, and
Reviewer treat route depth mostly as prompt guidance. This weakens high-quality
completion because a parent-sized objective can look executable even when the
worker would need to replan or decompose it.

The fix should preserve the simplified new FlowPilot direction: one real route
tree, current-contract authority, and minimal new persistent state. Depth and
coverage should be enforced through existing route fields, operator simulation,
Reviewer challenge, and tests before adding any new schema surface.

## What Changes

- Update PM route guidance so the PM writes one canonical executable route tree,
  not a separate PM-authored display plan.
- Treat display/status artifacts as Router-derived projections of the canonical
  route and frontier, not an additional PM plan.
- Strengthen FlowGuard operator route-process checks so process viability
  explicitly simulates effective parent/module/leaf traversal, leaf
  worker-readiness, child-skill projection, parent replay, and final evidence
  closure.
- Strengthen Reviewer route and node-plan challenges so broad leaves,
  direct-dispatchable parents, and worker-replanning leaves block the current
  gate.
- Add conservative runtime checks that reuse existing route fields to prevent
  parent/module or child-bearing nodes from receiving worker task packets.
- Add focused tests and model evidence for broad-route bad cases without adding
  a large set of new route-node fields.

## Capabilities

### New Capabilities

- `single-route-depth-gates`: Defines the minimal route-depth and process-gate
  behavior for a single canonical FlowPilot route tree.

### Modified Capabilities

- `recursive-route-parent-entry`: Parent/module route scopes must remain
  composition/review scopes and must not become worker task packets.
- `route-display-refresh`: Display artifacts remain derived projections of the
  canonical route and frontier instead of PM-authored alternate plans.
- `flowpilot-packet-review-flow`: Current-node packet dispatch must respect the
  accepted node plan and existing route-node structure before worker relay.

## Impact

- Runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- Core runtime route materialization and task-packet dispatch under
  `skills/flowpilot/assets/flowpilot_core_runtime/`.
- Focused runtime tests under `tests/`.
- FlowGuard simulation/model evidence under `simulations/` when needed.
- Local install sync via `scripts/install_flowpilot.py --sync-repo-owned --json`
  after source validation.
