# Recursive Route Planning Loop FlowGuard Findings

Date: 2026-04-30

## Scope

This process-preflight model tests the recursive FlowPilot planning loop that
should sit above the existing hierarchical heartbeat and route mutation models.

The modeled rule is that a route tree is never just a static plan:

- the initial route tree is generated as a candidate and then checked by the
  root FlowGuard model before it becomes the first route version;
- every parent node reruns FlowGuard against its current child subtree before
  entering children;
- if the child subtree needs adjustment, the route enters a formal mutation
  boundary, creates a new route version, and reruns the same parent review;
- every leaf node still has its own local Grill-me, local FlowGuard model,
  model-derived checks, execution, validation, parent alignment, and evidence;
- if work stops while the current leaf is unfinished, the next heartbeat
  resumes the same leaf and cannot advance to the next node.

## Modeled Structure

The concrete state graph uses a compact but recursive route tree:

- 2 phases;
- 4 groups;
- 8 leaves;
- 7 parent subtree reviews: root, 2 phases, and 4 groups.

The model is intentionally smaller than a real showcase route so it can be
fully explored, but it preserves the same shape:

```text
route -> phase -> group -> leaf -> heartbeat micro-step
```

## Parent Subtree Loop

Each parent node follows the same sequence:

1. Load the existing child subtree.
2. Emit the visible child-subtree map.
3. Run focused parent-scope Grill-me.
4. Build the parent subtree FlowGuard model.
5. Run parent subtree FlowGuard checks.
6. Decide whether the child subtree needs adjustment.
7. Mark the child subtree ready only after the model and adjustment review pass.
8. Enter the next child scope.

This means a phase does not blindly execute the child nodes that were generated
at route startup. When FlowPilot enters a phase or group, the existing child
nodes become the current model input and may be refined before execution.

## Subtree Mutation Loop

If a parent subtree model finds a structural gap, the route enters a formal
mutation boundary:

1. Enter the subtree mutation boundary.
2. Emit the mutation roadmap.
3. Run full mutation-level Grill-me.
4. Analyze stale evidence, parent contracts, and resume scope.
5. Check the mutation FlowGuard model.
6. Write the route delta.
7. Apply the mutation as a new route version.
8. Recheck the mutated route.
9. Write the mutation transition record.
10. Resume the same parent review and rerun the child-subtree model.

The model verifies that a subtree mutation cannot directly enter children. It
must return to the same parent review and rerun that parent model.

## Leaf Recovery Loop

The model includes an interruption while a leaf node is unfinished. The next
heartbeat must:

1. read the interrupted node key;
2. confirm the current leaf is still the interrupted leaf;
3. resume that same unfinished leaf;
4. prevent transition to the next leaf until evidence is written.

This is the recovery rule:

```text
unfinished current node -> heartbeat recovery -> same node -> evidence -> next node
```

The route cannot advance away from an interrupted leaf until that exact leaf has
evidence.

## Leaf Repair Loop

The model also includes a leaf validation failure. When validation fails:

1. FlowPilot stays on the same leaf;
2. local model checks and derived tests are reset;
3. the leaf model is checked again;
4. work reruns;
5. validation must pass before evidence is written.

This prevents failed validation from being treated as a normal next-node
transition.

## Check Results

Commands:

```powershell
python -m py_compile .flowpilot/task-models/recursive-route-planning-loop/model.py .flowpilot/task-models/recursive-route-planning-loop/run_checks.py
python .flowpilot/task-models/recursive-route-planning-loop/run_checks.py
```

Result:

- states: 3942;
- edges: 4069;
- invariant failures: 0;
- missing required labels: 0;
- progress findings: 0;
- stuck states: 0;
- non-terminating components: 0;
- terminal complete states: 36.

Representative success traces:

- baseline route: 186 heartbeat steps;
- route with subtree mutation: 202 heartbeat steps;
- route with unfinished-node recovery: 188 heartbeat steps;
- route with leaf repair after validation failure: 191 heartbeat steps.

The baseline trace contains 7 parent subtree FlowGuard checks and 8 leaf
FlowGuard checks. The mutation trace contains 8 parent subtree FlowGuard checks,
because the affected parent is rerun after mutation.

## Design Implication

The next FlowPilot protocol repair should add an explicit recursive planning
loop:

- initial route generation is candidate-tree generation followed by root
  FlowGuard review;
- every parent node treats its existing child plan as model input and reruns
  FlowGuard before entering children;
- subtree adjustment is not an informal plan edit; it is a formal mutation node;
- unfinished-node recovery is a first-class heartbeat behavior;
- validation failure stays on the current leaf and reruns the local model.

Together with the hierarchical heartbeat model and route mutation model, this
gives FlowPilot a coherent execution rule:

```text
model the tree -> execute the smallest current node -> write evidence ->
transition by heartbeat -> rerun parent models when entering a new layer ->
mutate routes only through checked route-version transitions
```
