# Hierarchical Heartbeat Loop FlowGuard Findings

Date: 2026-04-30

## Scope

This process-preflight model tests a stricter FlowPilot execution loop for
formal showcase software routes. The model responds to the route-008 process
failure where the artifact was usable but the execution proof was too flat.

The modeled structure is:

```text
route -> phase -> group -> leaf node -> heartbeat micro-step
```

The central rule is that a heartbeat advances only the smallest active leaf
node. Parent group, phase, and route nodes advance only after child evidence is
written and checked.

## Modeled Granularity

The model uses a concrete route tree with:

- 6 phases;
- 14 group nodes;
- 28 leaf nodes before completion review;
- 29 leaf nodes if completion review raises the standard;
- 3 FlowGuard model layers per leaf minimum;
- tiered grill-me depth: full 100-per-active-layer rounds only at formal
  boundaries, focused 20-50 question rounds at phase/group/module/leaf and
  child-skill boundaries, and lightweight 5-10 question checks at heartbeat
  micro-steps.

The concrete leaf list covers contract, architecture, UI concept and
interaction, implementation/runtime, validation, and delivery/completion.

## Per-Leaf Loop

Every leaf must pass this heartbeat sequence:

1. Enter the leaf by heartbeat.
2. Emit a micro-roadmap.
3. Run focused leaf-node grill-me.
4. Build a local FlowGuard stack.
5. Check that local FlowGuard stack.
6. Derive tests from the model.
7. Execute only that leaf scope.
8. Run validation.
9. Check parent alignment.
10. Write evidence and transition record.

The local FlowGuard stack is modeled as at least:

- parent-contract model;
- local function model;
- validation/transition model.

## Parent Reviews

Group and phase nodes are not just labels. They each require:

- parent roadmap;
- focused parent-scope grill-me;
- FlowGuard refinement against child outputs;
- model-derived acceptance checks;
- rollup evidence.

This prevents a formal FlowPilot route from hiding most work inside one large
implementation node.

## Completion Review

Completion requires:

- full route tree map;
- full completion Grill-me;
- conformance replay from child evidence to parent contracts;
- high-value-work review;
- final report;
- heartbeat shutdown.

If completion review finds a high-value gap, the model adds a new child leaf
and sends the route back through the same leaf, parent, and completion gates.

## Check Results

Command:

```powershell
python .flowpilot/task-models/hierarchical-heartbeat-loop/run_checks.py
```

Result:

- states: 933;
- edges: 960;
- invariant failures: 0;
- missing required labels: 0;
- progress findings: 0;
- stuck states: 0;
- non-terminating components: 0.

The representative success trace contains 441 heartbeat steps, 28 leaf entries,
28 leaf Grill-me rounds, 28 leaf FlowGuard stack checks, 14 group reviews, and
6 phase reviews before route completion.

Existing compatibility checks also passed:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

## Design Implication

The next protocol repair should not merely raise the question count. It should
make the route tree itself the execution primitive:

- a formal route is a hierarchy, not a flat list;
- every leaf has local Grill-me, local FlowGuard, derived checks, and evidence;
- every parent node has a real review gate;
- heartbeat is the transition mechanism between micro-stages;
- completion can expand the route tree when the standard rises.

Route-008 should therefore remain useful as a Cockpit artifact but insufficient
as a proof of the final FlowPilot process standard.
