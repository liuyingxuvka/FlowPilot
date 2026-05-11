# FlowPilot Recursive Decomposition Upgrade Plan

Date: 2026-05-11

## Goal

Upgrade FlowPilot from a shallow route list into a recursive route tree:

- PM may plan to arbitrary depth.
- Only worker-ready leaf nodes may receive worker packets.
- Parent and module nodes are composition and acceptance boundaries.
- Reviewer checks whether decomposition is too shallow or too deep.
- Router automatically triggers parent backward review when all children of a
  parent are complete.
- User-facing display remains compact by default: top two levels plus the
  active path and leaf-progress summary.

## Implementation Checklist

| Order | Area | Concrete change | Primary files | Validation |
| --- | --- | --- | --- | --- |
| 1 | Risk plan | Record optimization points and bug list before implementation. | `docs/flowpilot_recursive_decomposition_upgrade_plan.md` | Plan maps each risk to a FlowGuard scenario. |
| 2 | FlowGuard model | Add a dedicated recursive decomposition model before production changes. | `simulations/flowpilot_recursive_decomposition_model.py`, `simulations/run_flowpilot_recursive_decomposition_checks.py` | Model detects all named hazards and accepts the intended plan. |
| 3 | Prompt cards | Require PM recursive decomposition, leaf readiness, reviewer depth review, and parent backward replay. | `pm_route_skeleton.md`, `pm_node_acceptance_plan.md`, `pm_current_node_loop.md`, reviewer/officer route cards | Planning-quality tests assert required language is present. |
| 4 | Route templates | Add first-class tree fields and leaf readiness examples. | `templates/flowpilot/routes/route-001/flow.template.json`, `node_acceptance_plan.template.json`, `execution_frontier.template.json` | Template tests and JSON parsing. |
| 5 | Router tree helpers | Flatten recursive nodes, find active nodes at any depth, classify leaf/parent, and select next leaf in depth-first order. | `skills/flowpilot/assets/flowpilot_router.py` | Router runtime tests for nested routes. |
| 6 | Router dispatch gates | Block worker packets for parent/module nodes and for leaves without `leaf_readiness_gate.status=pass`. | `flowpilot_router.py` | Runtime tests reject parent dispatch and unready leaves. |
| 7 | Parent review trigger | When a node's children are complete, require parent backward replay before marking the parent complete or advancing above it. | `flowpilot_router.py`, parent review cards/templates | Runtime tests require parent replay. |
| 8 | User display projection | Show only display depth two by default, plus active-path breadcrumb and hidden-leaf progress. | `flowpilot_user_flow_diagram.py`, display-plan code | Display tests confirm deep children are hidden but active path is visible. |
| 9 | PMK route memory | Store decomposition rationale and leaf-readiness history for resume and mutation. | `.flowpilot` templates, route-memory helpers/cards | Tests or artifact-contract checks confirm paths/fields exist. |
| 10 | Broad verification | Run targeted tests first, then meta/capability checks, install sync/check, and smoke test. | tests, simulations, install scripts | All practical checks pass before local commit. |

## Risk And Bug Checklist

| ID | Possible bug | Why it matters | FlowGuard coverage requirement |
| --- | --- | --- | --- |
| R1 | Complex route is accepted with only two shallow layers. | Worker still has to do project management inside a packet. | Model must reject `fixed_two_layer_complex_route`. |
| R2 | PM declares a leaf even though the worker would need to re-plan or split it. | Leaf packet is too coarse and execution quality drops. | Model must reject `coarse_leaf_marked_ready`. |
| R3 | PM over-splits operational steps into separate nodes. | Route becomes noisy and slow without stronger proof. | Model must reject `over_split_leaf_steps`. |
| R4 | Reviewer route challenge passes without checking depth adequacy and over-splitting. | PM self-check becomes the only quality gate. | Model must reject `reviewer_skips_depth_review`. |
| R5 | Router dispatches a parent/module node to a worker. | Parent composition target is treated as executable work. | Model must reject `parent_dispatched_to_worker`. |
| R6 | Router dispatches a leaf without a passed leaf-readiness gate. | Formal gate exists in prose but is not enforced. | Model must reject `unready_leaf_dispatched`. |
| R7 | Children pass locally, but parent composition review is skipped. | Small tasks pass while the parent user goal is still broken. | Model must reject `parent_review_skipped`. |
| R8 | Parent review failure advances normally instead of causing route mutation or child rework. | Bad composition evidence becomes accepted history. | Model must reject `parent_failure_advances`. |
| R9 | Route mutation splits a node but stale frontier continues on the old node. | Router executes stale work after the route changed. | Model must reject `mutation_frontier_not_reset`. |
| R10 | User display exposes the full deep tree by default. | User-facing UI becomes unreadable. | Model must reject `display_leaks_deep_tree`. |
| R11 | User display hides deep work without showing active path. | User cannot understand what FlowPilot is doing now. | Model must reject `display_hides_active_path`. |
| R12 | Final route-wide ledger omits deep leaf nodes. | Completion can pass with hidden unfinished work. | Model must reject `final_ledger_omits_deep_leaf`. |
| R13 | PMK does not record decomposition rationale. | Resume and route mutation lose why nodes were split or stopped. | Model must reject `missing_decomposition_memory`. |

## Intended Safe Plan

The intended plan must pass FlowGuard only when all of the following are true:

1. PM writes a full route tree, not only a shallow display plan.
2. Each non-leaf node has children or an explicit reviewed leaf-readiness
   waiver.
3. Each leaf has a passing readiness gate with single outcome, proof, owner,
   dependency, and failure-isolation fields.
4. Reviewer checks both under-decomposition and over-decomposition.
5. Router dispatches only leaf nodes with passing readiness gates.
6. Router triggers parent backward review after all children complete.
7. Parent review failure causes route mutation or targeted child rework.
8. Display projection is shallow by default but carries active path and leaf
   progress.
9. Route memory records split/stop/merge rationale.
10. Final route-wide ledger covers every effective deep leaf and parent review.

## Verification Order

Run checks in this order:

1. Compile and run the dedicated recursive decomposition model.
2. Run targeted unit tests for planning cards, router runtime, and route display.
3. Run `python simulations/run_flowpilot_planning_quality_checks.py`.
4. Run `python simulations/run_flowpilot_route_display_checks.py`.
5. Run broad project-control checks:
   - `python simulations/run_meta_checks.py`
   - `python simulations/run_capability_checks.py`
6. Sync local install:
   - `python scripts/install_flowpilot.py --sync-repo-owned --json`
   - `python scripts/audit_local_install_sync.py --json`
   - `python scripts/install_flowpilot.py --check --json`
7. Run `python scripts/smoke_autopilot.py`.

Long-running FlowGuard checks should be launched as background jobs where
practical, with logs written under `tmp/`.
