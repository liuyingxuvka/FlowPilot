## Overview

This change replaces the old "every worker node gets pre-work FlowGuard" trunk with a structural-change trunk. FlowPilot keeps node plans deep by making PM self-check at every node entry and by letting Reviewer block shallow or over-detailed node plans. FlowGuard is mandatory only when PM changes the route or node topology.

## Runtime Contract

### Ordinary node path

1. PM receives a `task.node_acceptance_plan` packet for the active node.
2. PM returns `decision=pass` with a top-level `node_context_package`.
3. Runtime stages `commit_node_acceptance_plan`.
4. FlowGuard is not issued for this ordinary node-entry path.
5. Reviewer reviews the node acceptance plan.
6. System validation commits the node acceptance plan.
7. Runtime enters child nodes for parent/module nodes, or issues the worker node packet for leaf nodes.

### Structural-change path

1. PM decides the active node/route is structurally wrong and returns `decision=redesign_route` with strict `route_plan`, or a PM repair/disposition result chooses `redesign_route`.
2. Runtime stages `commit_route_redesign` and opens a PM decision gate with status `awaiting_flowguard`.
3. FlowGuard Operator receives the current staged decision and strict route plan as the modeled subject.
4. If FlowGuard blocks, the original PM result is blocked and no route mutation commits.
5. If FlowGuard passes, the PM decision gate moves to `awaiting_pm_flowguard_acceptance`.
6. PM receives `pm_flowguard_acceptance` with authorized reads for the original PM decision and FlowGuard report.
7. PM chooses:
   - `accept`: absorb the report and send the same staged decision to Reviewer.
   - `redesign_route`: write a replacement strict `route_plan`, which creates a new staged route decision and reruns FlowGuard.
   - `block` or `stop_for_user`: stop the structural decision without committing route mutation.
8. Reviewer reviews only the PM-absorbed structural decision.
9. System validation commits the staged route mutation.

## Ownership

- Runtime/router owns mechanical validity: packet kinds, strict fields, route scope, current run, current packet/result ids, staged effects, and rejection of old packet kinds or fallback shapes.
- FlowGuard Operator owns process/model simulation of structural route decisions and reports risks or pass/block findings to PM.
- PM owns route structure, PM FlowGuard absorption, route-plan rewrites, and final decision to send the absorbed structural plan to Reviewer.
- Reviewer owns independent quality/decomposition review of the final PM-absorbed plan. Reviewer may block coarse leaves, over-fragmented leaves, missing child topology, missing PM absorption, or missing current evidence.

## Data Shape

The only new current-contract packet family is `pm_flowguard_acceptance.pm_flowguard_acceptance`.

Required accepted shape:

```json
{
  "decision": "accept",
  "reason": "PM absorbed the FlowGuard report and keeps the staged route plan.",
  "flowguard_absorption": "Concrete PM summary of what was accepted, changed, or rejected from the FlowGuard report.",
  "accepted_flowguard_result_id": "result-..."
}
```

If PM chooses `decision=redesign_route`, the result must include `route_plan` with the strict current `flowpilot.route_plan.v1` shape. There is no optional FlowGuard field and no uncertain branch.

## Negative Contract

- Do not issue `node_prework_flowguard` for ordinary `decision=pass` node acceptance plans.
- Do not let FlowGuard report pass directly release Reviewer; PM absorption is mandatory for structural decisions.
- Do not let Reviewer review an unabsorbed structural FlowGuard report.
- Do not let PM choose optional or uncertain FlowGuard states.
- Do not accept nested legacy node acceptance packages, old field aliases, missing route-plan defaults, or historical route artifacts as current route mutation evidence.

## Verification Strategy

- Focused runtime tests cover ordinary node plan to worker without pre-work FlowGuard.
- Focused runtime tests cover structural node acceptance redesign, PM repair redesign, and PM disposition redesign through FlowGuard, PM absorption, Reviewer, system validation, and route commit.
- Fake-AI packet shape tests cover `pm_flowguard_acceptance` success and invalid optional/legacy fields.
- FlowGuard model checks replace the old pre-work-node gate model with route-redesign gate semantics and known-bad hazards.
- Model-test-alignment metadata maps the new obligations to the updated tests.
- Prompt coverage tests assert PM/Reviewer/FlowGuard cards describe the binary path and PM absorption.
- Affected meta/capability checks, install sync, and topology check run before done.
