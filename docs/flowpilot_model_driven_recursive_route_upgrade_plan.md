# FlowPilot Model-Driven Recursive Route Upgrade Plan

## Scope

Upgrade FlowPilot route governance from "PM drafts a route and officers review
it" to a model-driven loop:

- PM owns product and route decisions.
- Product FlowGuard Officer turns PM intent into product behavior models.
- Reviewer challenges product models before route drafting.
- Process FlowGuard Officer turns route drafts into serial execution models.
- Reviewer challenges route/process models before activation.
- Every non-leaf node repeats the same local product/process/reviewer loop.
- PM may promote a too-large leaf into a parent node and split it deeper.
- Parent completion and final project completion run backward coverage checks.
- Chat display keeps Mermaid visuals: placeholder before route, real route after
  route activation.

This plan does not include remote GitHub publication.

## Optimization Sequence

| Step | Optimization point | Concrete change | Primary files |
| --- | --- | --- | --- |
| 1 | Product model as first-class artifact | Product Officer must write a real product behavior model, not only a pass report. PM must explicitly accept or request rebuild. | `cards/officers/product_architecture_modelability.md`, `cards/phases/pm_product_architecture.md`, `contract_index.json` |
| 2 | Product reviewer gate before route | Reviewer challenges the product model before PM can draft the route. | `cards/reviewer/product_architecture_challenge.md`, `flowpilot_router.py` |
| 3 | Route draft depends on accepted product model | PM route skeleton must cite the accepted and reviewer-challenged product model. | `cards/phases/pm_route_skeleton.md`, route templates |
| 4 | Process model as first-class artifact | Process Officer must write a serial execution model and leaf decomposition audit. | `cards/officers/route_process_check.md`, `contract_index.json`, route templates |
| 5 | PM accepts process model | PM must approve or request rebuild of the serial execution model before route product check/reviewer challenge. | `flowpilot_router.py`, new PM decision contract/card text |
| 6 | Reviewer route challenge after process model | Reviewer challenges serial coverage, leaf size, repair returns, and closure safety. | `cards/reviewer/route_challenge.md` |
| 7 | Recursive non-leaf entry loop | Every non-leaf node runs local product modeling, PM acceptance, reviewer product challenge, process modeling, PM acceptance, and reviewer route challenge before child execution. | `pm_node_acceptance_plan.md`, `route_process_check.md`, `route_challenge.md`, `flowpilot_router.py` |
| 8 | Leaf promotion | At node entry, PM may decide a leaf is too large, promote it to a parent/module, add children, invalidate affected approvals, and rerun local loops. | `pm_node_acceptance_plan.md`, `flowpilot_router.py`, route templates |
| 9 | Parent completion backward check | A parent/module cannot close until all children are covered, omissions are checked, and model-miss repair/supplement nodes have run when needed. | `parent_backward_replay.md`, `pm_parent_segment_decision.md`, `flowpilot_router.py` |
| 10 | Final whole-project backward check | Project completion requires a root-level review over every major node/subtree and model-miss expansion for omissions. | `pm_closure.md`, `final_backward_replay.md`, `flowpilot_router.py`, terminal models |
| 11 | Chat and Cockpit route display | Startup shows a labeled placeholder Mermaid diagram; real route shows canonical serial Mermaid plus status text. Cockpit shows full tree and serial line. | `flowpilot_user_flow_diagram.py`, route-display model/tests |
| 12 | Local install sync only | Sync repo-owned FlowPilot skill into local installed copy and verify source freshness. Do not push GitHub. | `install_flowpilot.py`, `audit_local_install_sync.py` |

## New Canonical Artifacts

| Artifact | Purpose |
| --- | --- |
| `.flowpilot/runs/<run>/flowguard/product_behavior_model.json` | Product states, user actions, transitions, failure/recovery paths, forbidden downgrades, evidence requirements, counterexamples. |
| `.flowpilot/runs/<run>/decisions/pm_product_model_decision.json` | PM accepts the product model or requests rebuild. |
| `.flowpilot/runs/<run>/reviews/product_model_challenge.json` | Reviewer challenge of product model before route drafting. |
| `.flowpilot/runs/<run>/flowguard/process_route_execution_model.json` | Canonical serial execution order, hierarchy metadata, repair returns, closure gate. |
| `.flowpilot/runs/<run>/flowguard/leaf_decomposition_audit.json` | Audit that every terminal leaf is worker-ready and has no hidden parallel or oversized work. |
| `.flowpilot/runs/<run>/decisions/pm_process_model_decision.json` | PM accepts the serial process model or requests rebuild. |
| `.flowpilot/runs/<run>/routes/<route>/nodes/<node>/node_product_model.json` | Local product model for a non-leaf node before entering children. |
| `.flowpilot/runs/<run>/routes/<route>/nodes/<node>/node_process_execution_model.json` | Local serial child execution model for a non-leaf node. |
| `.flowpilot/runs/<run>/routes/<route>/nodes/<node>/pm_node_model_decision.json` | PM acceptance/rebuild decision for a local node model. |
| `.flowpilot/runs/<run>/reviews/node_model_challenge/<node>.json` | Reviewer challenge for the node-local product/process plan. |
| `.flowpilot/runs/<run>/reviews/parent_backward_replay/<node>.json` | Parent completion backward review with omission/model-miss checks. |
| `.flowpilot/runs/<run>/reviews/final_whole_project_backward_replay.json` | Final root-level review that all major nodes/subtrees were covered. |

## Bug And Hazard Checklist

| Risk id | Possible bug from this upgrade | FlowGuard expectation | Runtime/test expectation |
| --- | --- | --- | --- |
| R1 | PM drafts route before Product Officer wrote product model. | Model rejects route drafting before product model. | Router blocks `pm.route_skeleton`. |
| R2 | Product model exists but PM did not accept it. | Model rejects route drafting before PM product model decision. | Router requires `pm_product_model_decision.json`. |
| R3 | Reviewer product challenge is skipped. | Model rejects route drafting before product reviewer pass. | Router order includes reviewer gate before route skeleton. |
| R4 | Process Officer only reviews route instead of producing serial model. | Model rejects route activation without process execution model. | Router requires `process_route_execution_model.json`. |
| R5 | Process model contains parallel branches as execution truth. | Model rejects non-serial execution model. | Process artifact has one canonical `serial_execution_order`. |
| R6 | A terminal leaf hides multiple independent tasks. | Model rejects leaf readiness. | Leaf audit blocks hidden parallel/multi-worker leaves. |
| R7 | PM cannot split an oversized leaf discovered at node entry. | Model requires leaf promotion path. | Router supports leaf-to-parent promotion and invalidates stale approvals. |
| R8 | Leaf promotion keeps old process/reviewer passes. | Model rejects stale approvals after promotion. | Router clears affected approvals and reruns local gates. |
| R9 | Non-leaf node enters children without local product loop. | Model rejects non-leaf child execution before local product model, PM acceptance, reviewer challenge. | Node-entry router gate enforces local product loop. |
| R10 | Non-leaf node enters children without local process loop. | Model rejects non-leaf child execution before local serial model, PM acceptance, reviewer challenge. | Node-entry router gate enforces local process loop. |
| R11 | Parent closes though children were omitted. | Model rejects parent completion without child coverage audit. | Parent backward replay checks all children and omissions. |
| R12 | Parent omission is patched without model-miss review. | Model rejects omission repair unless process model is reviewed/upgraded first. | Parent replay sends omission to model-miss flow. |
| R13 | Same-class omissions are not searched after a model miss. | Model rejects completion until same-class search is recorded. | Repair flow records same-class omission scan. |
| R14 | Final project closure checks only the last node. | Model rejects completion without all-major-node root review. | Terminal replay scans every major node/subtree. |
| R15 | Final omission does not upgrade FlowGuard/Process model. | Model rejects closure until model upgrade/recheck and supplemental nodes run. | Final closure flow routes to model-miss repair. |
| R16 | Startup placeholder is mistaken for real route. | Model requires explicit placeholder identity and replacement rule. | Display packet uses `startup_placeholder` and `is_placeholder: true`. |
| R17 | Real route appears but chat keeps placeholder. | Model rejects canonical route display with placeholder semantics. | Display generator replaces placeholder with real route. |
| R18 | Chat shows only text status after real route. | Model rejects real-route display without Mermaid. | Chat markdown includes Mermaid plus status summary. |
| R19 | Real-route Mermaid uses fixed protocol stages. | Model rejects canonical route sourced from protocol lifecycle. | Mermaid uses serial execution model/route nodes. |
| R20 | Cockpit hides deep tree or active path. | Model rejects UI projection without full tree and active path. | Cockpit data includes full tree, serial line, and current path. |

## Implementation Order

1. Add or update FlowGuard models and hazard checks first.
2. Run the new model's intended scenario and known-bad hazards.
3. Only after the model catches the hazards and accepts the intended plan, edit
   prompt cards, contracts, templates, Router state, and display generator.
4. After each implementation slice, run the smallest relevant tests.
5. Run broader meta/capability checks after the behavior-bearing changes settle.
6. Sync the local installed FlowPilot skill and verify install freshness.
7. Leave GitHub remote untouched.

## Background-Run Policy

Long broad simulations may run in the background while local prompt/router work
continues, but the final result must wait for and report their outcomes. Local
source edits and install sync remain on the main thread to avoid overwriting
parallel AI work.

