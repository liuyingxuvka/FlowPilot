# FlowPilot Low-Quality Success Hardening Plan

Date: 2026-05-13

## Purpose

Fuse low-quality-success prevention into existing FlowPilot PM and reviewer
gates without adding a new major phase, default route node, or parallel review
workflow.

The target failure is not only catastrophic failure. The more common failure is
that a difficult part is handled thinly: the artifact exists, the checklist
looks complete, and the route can technically advance, but the work avoided the
hard part and does not meet the user's real quality bar.

## Design Rule

Do not add a new default workflow line. Embed the new lens inside existing
artifacts and gates:

- PM product architecture;
- root contract and scenario pack;
- PM route skeleton;
- PM node acceptance plan;
- current-node worker packet guidance;
- reviewer independent challenge;
- PM final ledger and closure.

Add a new route node only when an identified hard part cannot be owned by an
existing node and needs its own research, modeling, validation, or repair
artifact.

## Optimization Checklist

| Step | Existing place to strengthen | Concrete change | No-bloat rule | Completion evidence |
| --- | --- | --- | --- | --- |
| 1 | `pm_product_architecture` card and product architecture template | Add concise low-quality-success review language and fields for hard parts, tempting thin shortcuts, warning signs, required proof of depth, and reviewer probes. | This is part of product architecture, not a new phase. | Product architecture card and template mention low-quality success, hard parts, thin shortcuts, and proof of depth. |
| 2 | `pm_root_contract` card, root contract template, standard scenario pack template | Require PM to promote only hard low-quality risks into root requirements or scenario coverage. | Do not turn every improvement into a root blocker. | Contract/scenario wording distinguishes hard low-quality risks from nonblocking improvements. |
| 3 | `pm_route_skeleton` card | Require existing route nodes to name which hard part or low-quality shortcut they prevent. | Do not add a node just because a risk exists; first bind it to an existing node. | Route card says uncovered hard low-quality risks block route approval, while covered risks stay inside existing nodes. |
| 4 | `pm_node_acceptance_plan` card and node acceptance template | Strengthen the current high-standard recheck so each node names its likely thin-success pattern and proof that the node did the hard work. | Use existing node acceptance, not a new node-level gate. | Node plan card/template include local hard part, thin shortcut, warning signs, and required depth evidence. |
| 5 | `pm_current_node_loop` card and worker packet template | Put the node's low-quality shortcut warning into worker packets and require worker evidence that the hard part was addressed. | Keep this as a short packet section, not a new worker report type. | Worker packet/result templates include low-quality shortcut warning and proof-of-depth handoff. |
| 6 | Reviewer core plus product, route, node, worker, evidence, parent, and final reviewer cards | Extend existing `independent_challenge` to ask whether the plan/result avoided low-quality success and whether evidence proves depth rather than existence. | Reviewer advises or blocks; reviewer does not become PM or create a separate review stage. | Reviewer cards mention low-quality success, thin shortcuts, existence-only evidence, and task-specific proof of depth. |
| 7 | `pm_final_ledger` and `pm_closure` cards | Require PM to close or disposition low-quality-success risks already named in product architecture and node acceptance. | Reuse the final ledger residual-risk path; no new terminal ledger type. | Final ledger/closure cards require unresolved hard low-quality risks to be fixed, waived, not applicable, or blocking. |
| 8 | `check_install.py` and focused tests | Add lightweight propagation checks for the markers above. | Markers verify only key surfaces, not every card line. | Install check and planning/reviewer tests fail if the lens is missing from key cards/templates. |

## Bug And Regression Checklist

| Risk id | Possible bug | Why it matters | FlowGuard or test must catch |
| --- | --- | --- | --- |
| LQ1 | PM product architecture omits the low-quality-success review. | Route planning stays optimistic and hard parts are not visible early. | Planning-quality hazard: missing PM low-quality-success review. |
| LQ2 | PM writes generic risks such as "do good work" with no hard part, shortcut, or evidence. | The new text becomes ritual prose and does not change execution. | Planning-quality hazard: generic low-quality review lacks task-specific hard part and proof. |
| LQ3 | Route nodes do not bind hard low-quality risks to existing owners. | Risks are recognized but no node is responsible for preventing them. | Planning-quality hazard: hard low-quality risk has no route owner. |
| LQ4 | PM adds extra nodes for every risk, bloating the route. | The fix makes FlowPilot slower and more complex. | Planning-quality hazard: low-quality risk causes unjustified route bloat. |
| LQ5 | Node acceptance plan lacks local thin-success warning or proof of depth. | Workers can still complete the node superficially. | Planning-quality hazard: node plan missing local low-quality-risk mapping. |
| LQ6 | Worker packets omit the node's low-quality shortcut warning. | PM insight does not reach execution. | Planning-quality hazard or targeted card/template check for worker packet projection. |
| LQ7 | Worker returns existence-only evidence for a user-facing or hard-part claim. | A file, screenshot, or report can substitute for real quality. | Reviewer active-challenge hazard: low-quality success accepted from existence-only evidence. |
| LQ8 | Reviewer checks the PM checklist but does not challenge thin success. | The review still passes plausible but low-depth work. | Reviewer active-challenge hazard: low-quality-success challenge missing. |
| LQ9 | Reviewer treats every quality improvement as a hard blocker. | The route becomes scope creep. | Existing planning/reviewer hazards for nonblocking improvement scope creep. |
| LQ10 | Final ledger closes while hard low-quality risks remain unresolved. | Completion can pass without proving difficult parts were handled. | Planning-quality hazard: closure skips low-quality-risk disposition. |
| LQ11 | The model passes but production cards/templates do not carry the behavior. | Model-only confidence does not affect FlowPilot runs. | `check_install.py` and focused tests for card/template markers. |
| LQ12 | Local installed FlowPilot stays stale after repo edits. | User invokes old behavior. | Local install sync and install check. |

## Required FlowGuard Gate Before Prompt Edits

1. Upgrade `simulations/flowpilot_planning_quality_model.py` so LQ1-LQ6 and
   LQ10 are explicit hazards.
2. Upgrade `simulations/flowpilot_reviewer_active_challenge_model.py` so LQ7
   and LQ8 are explicit hazards, while preserving existing safeguards for
   LQ9.
3. Run both model check runners and confirm every listed hazard is detected.
4. Confirm the safe plan accepts the intended low-intrusion approach: risks are
   embedded in existing PM/reviewer gates, and new nodes are required only when
   an existing node cannot own the hard part.
5. Only after the model passes, edit runtime cards, templates, and marker
   checks.

## Edit Order

1. Model and runner updates.
2. Planning/reviewer tests for model hazards.
3. PM cards and templates.
4. Reviewer cards and templates.
5. Install/card propagation checks.
6. Focused tests after each edit group.
7. Full practical verification.
8. Local installed skill sync and local install audit.
9. Local git review only. No remote GitHub push.
