# Route Mutation Activation and Display Repair Plan

Date: 2026-05-10

## Goal

Repair FlowPilot route mutation behavior so PM-added repair or replacement
nodes are modeled, checked, activated, and displayed in the right order.

The current problem is a cross-layer mismatch:

- mutation records can describe a repair relationship;
- route storage may append the new node to the flat node list;
- user-facing Mermaid can infer a linear mainline from list order;
- display sync can expose a route change before the reviewed route is activated
  and before execution enters the new node.

This is model-first work. Production router or display edits start only after
the FlowGuard model proves the intended sequence and catches the listed risks.

## Optimization Sequence

| Step | Optimization point | Concrete implementation target | Verification |
| --- | --- | --- | --- |
| 1 | Separate mutation proposal from active execution | PM route mutation records a candidate topology and writes a draft/proposed route; it does not overwrite active `flow.json` or move the active frontier to the new node before recheck and activation | Route mutation unit test: active frontier remains on the old node while the draft waits for route checks |
| 2 | Make route topology explicit | Every inserted repair/replacement node records a topology strategy: `return_to_original`, `supersede_original`, or `branch_then_continue` | FlowGuard hazard: missing topology strategy fails |
| 3 | Allow replacement without forced return | `supersede_original` may mark old nodes superseded and continue from the replacement without `repair_return_to_node_id` | Unit test: supersede mutation is accepted without return target when superseded nodes are explicit |
| 4 | Require route recheck before activation | Process FlowGuard, product FlowGuard, and reviewer route gates must pass against the candidate route before PM activation | Existing route-check gates plus new model invariant: activation before process recheck fails |
| 5 | Display only after activation and node entry | Chat/Cockpit route display must not publish the proposed repair route as current; when PM activation makes the new node current, the route sign may display the new route and current position | FlowGuard hazard: draft/proposed repair route displayed as current fails |
| 6 | Render repair topology instead of list order | Mermaid must not draw an appended repair node as the final mainline stage. Return repairs render as a branch/return edge; replacements render superseded nodes distinctly or omit them from the effective mainline | Route-sign unit tests for return and supersede topology |
| 7 | Preserve stale evidence and completion gates | Route mutation still records stale evidence, resets route approvals, requires fresh route activation, and forces final ledger rebuild | Existing router-loop checks plus focused mutation tests |
| 8 | Sync locally only | After validation, sync the repository-owned FlowPilot skill to the local installed copy and create local git history only; do not push to GitHub | `install_flowpilot.py --sync-repo-owned`, install check, local git status |

## Possible Bugs and Required Model Coverage

| Risk id | Possible bug | FlowGuard model must catch it |
| --- | --- | --- |
| R1 | PM mutation immediately overwrites active `flow.json` before route recheck | Invariant: proposed mutation cannot change active route before checked activation |
| R2 | PM mutation immediately moves active frontier to repair node before activation | Invariant: execution cannot enter candidate node before route activation |
| R3 | Candidate repair route is shown in chat/Cockpit as current before activation | Invariant: proposed route display as current is forbidden |
| R4 | PM activation happens before process FlowGuard route simulation/recheck | Invariant: activation requires process recheck pass |
| R5 | PM activation happens before product/reviewer route checks | Invariant: activation requires all route gates |
| R6 | New node has no topology strategy | Hazard: missing `return_to_original`, `supersede_original`, or `branch_then_continue` fails |
| R7 | Replacement/supersede node is incorrectly forced to return to the old node | Hazard: `supersede_original` with forced return fails |
| R8 | Return repair has no return target | Hazard: `return_to_original` without `repair_return_to_node_id` fails |
| R9 | Mermaid draws a repair node as a final sequential stage after terminal/final node | Hazard: appended repair rendered as mainline final node fails |
| R10 | Superseded old node remains displayed as an active unfinished node | Hazard: superseded node treated as pending/active fails |
| R11 | Repair route reuses stale worker or reviewer evidence | Invariant: mutation invalidates affected evidence before activation |
| R12 | Generated display files are treated as user-visible display before chat/Cockpit receipt | Existing display invariant remains required |
| R13 | Existing packet sealed-body boundary is weakened by display repair | Existing display invariant remains required |

## Accepted Topology Strategies

| Strategy | Meaning | Required fields | Display shape |
| --- | --- | --- | --- |
| `return_to_original` | The inserted node repairs the current/original node, then the original node is rechecked or rerun | `repair_node_id`, `repair_of_node_id`, `repair_return_to_node_id` | Original node branches to repair node; repair node returns to original |
| `supersede_original` | The inserted node replaces the old node; the old node is historical/superseded and not an unfinished active obligation | `repair_node_id`, `superseded_nodes` | Replacement is effective; superseded node is marked superseded or hidden from active mainline |
| `branch_then_continue` | The inserted node handles a bounded detour and then continues to a declared downstream node | `repair_node_id`, `continue_after_node_id` | Current node branches to inserted node; inserted node continues to downstream node |

## Non-Goals

- Do not push to GitHub.
- Do not change unrelated UI/product behavior.
- Do not treat FlowGuard as a visual renderer. The model proves route/display
  state ordering; unit tests prove concrete Mermaid projection.
- Do not overwrite parallel AI changes in unrelated files.
