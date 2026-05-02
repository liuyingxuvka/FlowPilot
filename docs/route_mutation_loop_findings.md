# Route Mutation Loop FlowGuard Findings

Date: 2026-04-30

## Scope

This process-preflight model tests how FlowPilot should handle route-tree
changes after a formal route has already started. It extends the hierarchical
heartbeat model with explicit route mutation behavior so a long-running route
can evolve without collapsing back into ad hoc execution.

The modeled mutation kinds are:

- add a child node;
- add a parallel node;
- delete an unstarted future node;
- replace a planned node;
- reroute to another branch;
- split an oversized leaf node into smaller leaves;
- reparent a node under a better parent contract;
- prune an obsolete branch while preserving history.

## Mutation Rule

Route mutation is modeled as a formal node, not as an informal edit to the
current plan.

Before any route tree delta is applied, the heartbeat must:

1. enter a mutation boundary;
2. quiesce active leaf work;
3. emit a mutation roadmap;
4. run layered mutation Grill-me;
5. complete impact analysis;
6. build the mutation FlowGuard model;
7. run mutation FlowGuard checks;
8. write a route delta, evidence plan, and resume target.

Only after these gates pass can the route tree be changed.

## Evidence Handling

The model requires mutation-specific evidence behavior:

- new child, parallel, replacement, reroute, and split mutations must generate
  new node gates;
- replacement, reroute, split, and reparent mutations must invalidate stale
  evidence;
- deletion and prune mutations must write tombstones;
- delete, replace, reroute, and prune mutations must preserve old branch
  history;
- reparent mutations must recompute parent links;
- all mutations must reset parent rollups and regenerate the validation plan.

## Post-Mutation Resume

After a mutation is applied, work still cannot resume immediately. The
heartbeat must:

1. create a new route version;
2. recheck the mutated route tree;
3. replay existing evidence against updated parent contracts;
4. emit the updated visible route map;
5. write the transition record from the old version to the new version;
6. classify the resume target;
7. resume only after all mutation evidence is complete.

This makes node addition, deletion, transfer, expansion, replacement, and
branch migration auditable as first-class route transitions.

## Check Results

Commands:

```powershell
python -m py_compile .flowpilot/task-models/route-mutation-loop/model.py .flowpilot/task-models/route-mutation-loop/run_checks.py
python .flowpilot/task-models/route-mutation-loop/run_checks.py
```

Result:

- states: 277;
- edges: 308;
- modeled mutation kinds: 8;
- invariant failures: 0;
- missing required labels: 0;
- missing completed mutation kinds: 0;
- progress findings: 0;
- stuck states: 0;
- non-terminating components: 0.

Every mutation kind has a representative success trace. Each trace includes
trigger detection, mutation boundary entry, mutation roadmap, full mutation
Grill-me, impact analysis, mutation model build/check, delta planning, mutation
application, route recheck, conformance replay, updated map emission,
transition record, resume target classification, resume, and completion.

## Design Implication

The repaired FlowPilot loop should treat route changes as normal, modeled
events:

- route mutation is its own heartbeat-controlled node;
- active work is quiesced before route mutation;
- mutation reviews require full formal Grill-me and FlowGuard discipline;
- evidence must be invalidated, preserved, regenerated, or replayed depending
  on the mutation kind;
- a new checked route version and visible map are required before resume.

This closes the gap where a long-running FlowPilot route could discover a new
need but continue by silently editing the plan outside the formal route model.
