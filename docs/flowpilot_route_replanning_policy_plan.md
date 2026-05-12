# FlowPilot Route Replanning Policy Plan

Date: 2026-05-12

## Intent

This plan repairs the class of failure observed in ProjectRadar
`run-20260511-200916`: FlowPilot was still at root planning, but a repair node
was inserted as the active node before normal child execution began. The fix is
not a workaround. It makes route changes model-first and separates planning
revisions from true repair work.

## Optimization Checklist

| ID | Optimization | Plain-language rule | Required gate |
| --- | --- | --- | --- |
| O1 | Planning-phase route rewrite | If the root route is not executable before any child work starts, rewrite the route draft instead of creating a repair node. | Process FlowGuard, plus Reviewer |
| O2 | Normal node expansion | If planning discovers missing work, PM may add ordinary sibling or child nodes, but each node must have owner, input, output, evidence, and acceptance fields. | Process FlowGuard, plus Reviewer |
| O3 | Capability expansion | If a route or node adds product capability, Product FlowGuard must run before Process FlowGuard checks the changed route. | Product FlowGuard, then Process FlowGuard, plus Reviewer |
| O4 | Node-entry replanning | Before entering a parent/module/leaf, if the node lacks capability or is too coarse, PM may split or add ordinary nodes. This is not repair. | Product FlowGuard if product capability changes; Process FlowGuard for structure; Reviewer |
| O5 | In-progress replanning | If a current node is underway but has not produced a reviewed failed result, PM may revise the node internals or add same-scope nodes. This is still replanning, not repair. | Product/Process FlowGuard according to changed surface, plus Reviewer |
| O6 | Review-failure repair | Repair nodes are allowed only after a concrete reviewed failure or route-invalidating review finding. | Complete repair metadata, stale-evidence handling, Process FlowGuard, Reviewer recheck |
| O7 | Executable active node gate | A node cannot become active unless FlowPilot can tell whether it is parent/module/leaf/repair and how it will be executed or decomposed. | Process FlowGuard |
| O8 | Controller boundary | Controller may not compensate for a stuck route by doing product work. It may only relay, record, or ask the proper role for a modeled decision. | Router/control-plane check |

## Risk And Bug Checklist

| ID | Failure mode to catch | Why it matters | Model hazard |
| --- | --- | --- | --- |
| B1 | Planning issue creates a repair node | This repeats the ProjectRadar failure before any child work starts. | `planning_repair_node_created` |
| B2 | Root planning adds `route_root_repair_*` when completed nodes are zero | Root planning is still design work, not a failed execution needing repair. | `root_repair_before_child_execution` |
| B3 | Added ordinary node lacks execution fields | Router cannot dispatch or review vague nodes. | `ordinary_node_missing_fields` |
| B4 | Product capability changes without Product FlowGuard | Process may be valid while product behavior is wrong. | `capability_change_without_product_check` |
| B5 | Process FlowGuard runs before Product FlowGuard after capability expansion | Process would simulate the wrong product target. | `process_before_product_for_capability_change` |
| B6 | Route structure changes without Process FlowGuard | The route can become unreachable or non-executable. | `structure_change_without_process_check` |
| B7 | PM uses a changed route before Reviewer approval | A mechanically valid route may still miss requirements. | `changed_route_without_reviewer` |
| B8 | Node-entry capability gap creates repair node | The node has not failed yet; it should be split or replanned. | `node_entry_repair_before_work` |
| B9 | In-progress capability gap creates repair node before reviewed failure | Lack of capability during work is replanning unless there is a failed review. | `in_progress_repair_before_review_failure` |
| B10 | Repair node lacks target/reason/input/output/evidence/return/rechecks | This creates another active node that cannot be executed. | `repair_node_missing_fields` |
| B11 | Repair does not mark stale evidence | Old evidence can be reused after route changes. | `repair_without_stale_reset` |
| B12 | Repair does not define return to mainline | The route can get stranded in repair. | `repair_without_mainline_return` |
| B13 | Active node is not executable before use | Router cannot know who acts next or what proof is required. | `active_node_not_executable` |
| B14 | Controller directly implements after a route gate problem | This violates FlowPilot authority boundaries. | `controller_direct_implementation` |
| B15 | Old approvals are reused after route/product change | Replanning must invalidate stale approvals. | `stale_approval_reused_after_change` |

## Model-First Gate

Before changing FlowPilot production behavior, `simulations/flowpilot_route_replanning_policy_model.py`
must prove:

1. Bad paths B1-B15 are rejected.
2. Valid planning replans, node-entry replans, in-progress replans, and
   review-failure repairs are accepted.
3. Every accepted change has the right Product FlowGuard, Process FlowGuard,
   and Reviewer gates for its risk surface.
4. No changed route is used for execution before the active node is executable.

## Implementation Order After Model Pass

1. Add route-state fields or helpers that distinguish `planning`, `node_entry`,
   `node_in_progress`, and `review_failure` change contexts.
2. Change PM/router policy so planning and node-entry gaps produce route draft
   rewrites or ordinary node additions, not repair nodes.
3. Add validation that a repair node can only be created after reviewed failure
   evidence and must include target, reason, input, output, evidence, stale
   reset, return, and rerun obligations.
4. Add Product-before-Process ordering when new product capability is added.
5. Add active-node executability validation before route activation or node
   entry.
6. Add or update tests/checks, then sync the repository-owned skill to the
   installed local Codex skill.
