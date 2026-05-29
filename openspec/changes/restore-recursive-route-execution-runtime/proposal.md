## Why

The new black-box FlowPilot runtime now proves a symmetric role-packet chain,
but it can still close after the PM planning packet without executing the PM
route. That is a scoped completion miss: old FlowPilot could keep moving
through route nodes, reviews, repairs, route mutations, parent replay, and final
route-wide closure.

## What Changes

- Add recursive route execution to the new current-run ledger: PM route drafts
  become structured route nodes, node acceptance plans, and an execution
  frontier.
- Make the existing symmetric packet lifecycle run inside each effective route
  node instead of treating the first PM packet as the whole project.
- Add PM disposition after reviewed node work so PM can accept, repair, split,
  mutate, block, or continue the route.
- Add route mutation/frontier behavior for stale node evidence, late packets,
  sibling replacement, and repair nodes.
- Replace one-packet final closure with a route-wide gate ledger over all
  effective nodes, FlowGuard targets, reviews, validation rows, stale evidence,
  unresolved resources, and parent/final backward replay.
- Expand fake-agent rehearsal from a five-packet happy chain into multi-node
  normal, repair, mutation, stale-evidence, wrong-target, dead-agent, and
  missing-node closure scenarios.
- Synchronize install/version/git evidence only after the recursive runtime
  checks and relevant model regressions are current.

## Capabilities

### New Capabilities

- `recursive-route-execution-runtime`: Materializes PM route drafts into route
  nodes and executes them recursively through frontier-owned packet loops,
  FlowGuard target checks, PM disposition, route mutation, and final
  route-wide closure.

### Modified Capabilities

- None. The new capability tightens the black-box runtime contract without
  changing archived old-protocol specs directly.

## Impact

- Runtime code under `skills/flowpilot/assets/ai_project_runtime/` and the
  formal entrypoint `skills/flowpilot/assets/flowpilot_new.py`.
- Fake project rehearsal models and runners under `simulations/`.
- Focused tests under `tests/`.
- Version, changelog, install inventory/sync, FlowGuard adoption records, and
  local git evidence after implementation.
