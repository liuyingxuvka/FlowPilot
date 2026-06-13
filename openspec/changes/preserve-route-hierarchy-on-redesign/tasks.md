## 1. Preflight And Existing Model Grounding

- [x] 1.1 Verify real FlowGuard package/adoption state and read current route/topology model ownership notes.
- [x] 1.2 Inspect current route-plan normalization, materialization, staged redesign, parent traversal, Reviewer, PM, and FlowGuard card surfaces.
- [x] 1.3 Record the focused FlowGuard development-process model boundary and minimum revalidation plan.

## 2. Route Hierarchy Runtime Contracts

- [x] 2.1 Add focused route-plan topology validation using existing `node_kind`, `parent_node_id`, and `child_node_ids` fields.
- [x] 2.2 Ensure invalid parent/module, leaf-with-children, missing child reference, and conflicting parent reference shapes are mechanically blocked.
- [x] 2.3 Ensure node-entry `redesign_route` for an active node requires the active node or replacement scope to own the decomposed child subtree.

## 3. PM, Reviewer, And FlowGuard Cards

- [x] 3.1 Update PM route skeleton and project-manager cards so route redesign outputs one canonical executable tree, not a flat task list.
- [x] 3.2 Update PM node acceptance guidance so over-broad active leaves are promoted to parent/module and children remain under that node.
- [x] 3.3 Update Reviewer route and node-plan review cards to block complex flat all-leaf redesigns and peer-appended node splits.
- [x] 3.4 Update FlowGuard route/process cards to model parent-to-child and child-to-parent closure coverage for redesigns.

## 4. Focused Tests And FlowGuard Evidence

- [x] 4.1 Add or update FlowGuard simulation coverage for flat complex route rejection and recursive node promotion.
- [x] 4.2 Add focused unit tests for route-plan topology validation and node-entry subtree redesign.
- [x] 4.3 Add prompt/card instruction coverage tests for PM, Reviewer, and FlowGuard hierarchy obligations.

## 5. Validation, Install Sync, And Local Git

- [x] 5.1 Run OpenSpec strict validation for the change.
- [x] 5.2 Run focused FlowGuard simulation checks and focused pytest for touched runtime/cards.
- [x] 5.3 Rebuild/check FlowGuard topology if model, card, or validation surfaces require it.
- [x] 5.4 Sync the repo-owned FlowPilot skill to the local installed skill and then run install audit/check serially.
- [x] 5.5 Review git diff/status, preserve peer-agent changes, commit the completed local result, and record KB postflight.
