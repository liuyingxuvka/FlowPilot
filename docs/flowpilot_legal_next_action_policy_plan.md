# FlowPilot Legal Next Action Policy Plan

Date: 2026-05-12

## Purpose

FlowPilot already has strong registries for output contracts, event capability,
and control transactions. Those tables answer whether a role can submit a
contract, whether a Router event is registered and currently receivable, and
which state surfaces a transaction mutates.

The missing layer is the route-decision surface before a PM decision is
requested:

> Given the current route, execution frontier, ledger, flags, and live Router
> action, which route actions may the PM choose right now?

This plan adds a compact legal-next-action policy layer. The Router computes
`legal_next_actions` before asking the PM for route movement decisions, validates
PM submissions against the same set, and validates again before writing route,
frontier, ledger, or run-state mutations.

## Risk Intent Brief

- Protected harm: PM or another role chooses a route jump, parent closure, route
  mutation, or terminal closure before the current child chain is actually
  closed.
- State that must be visible: active route id/version, frontier version, active
  node id/kind, child topology, completed descendants, node-completion ledger,
  pending action allowed events, current flags, stale evidence markers, and live
  Router next action coverage.
- Side effects to protect: delivering PM decision cards, accepting PM decision
  events, writing parent backward replay/segment decisions, mutating routes,
  writing completed nodes, advancing frontier, and final closure.
- Hard invariant: the Router may show, accept, or commit only route actions that
  are legal for the current route/frontier/ledger state. A PM decision is an
  input to the Router, not permission to bypass this invariant.
- Residual blindspot: the first implementation covers route movement and parent
  lifecycle authority. It does not redesign the full PM planning system or all
  card text generation.

## Optimization Sequence

| Order | Optimization point | Concrete work | FlowGuard proof before runtime edit | Runtime done evidence |
| --- | --- | --- | --- | --- |
| 1 | Freeze legal-action policy surface | Record route actions, state predicates, and commit points in this plan. | `flowpilot_legal_next_action_model.py` contains one valid plan scenario and all risk scenarios below. | This document exists and is referenced by adoption notes. |
| 2 | Add legal-next-action FlowGuard model | Model Router action computation before PM decision, submission validation, and commit validation. | Valid scenarios pass; every risk id in the checklist rejects with its expected failure. | `simulations/flowpilot_legal_next_action_results.json` is green. |
| 3 | Add compact policy registry | Add `runtime_kit/route_action_policy_registry.json` or equivalent rows under the control registry. Rows name action id, event, transaction type, actor, required state, forbidden state, and commit targets. | Source/model checks reject missing rows, row/event mismatch, and policy rows that allow closure before child chain closure. | Registry is installed with the skill and referenced by source checks. |
| 4 | Compute legal actions before PM decisions | Add one Router helper that reads current route/frontier/ledger/flags and returns legal action ids plus blocking reasons. | Model rejects PM decision requested with an unfiltered or open-ended action set. | PM decision card/wait payload includes `legal_next_actions`; illegal closure actions are absent until prerequisites are true. |
| 5 | Validate submitted PM route decisions | Before accepting `pm_records_parent_segment_decision`, `pm_completes_parent_node_from_backward_replay`, route mutation decisions, or terminal closure, re-compute legal actions and reject decisions outside the set. | Model rejects PM-selected action accepted outside current legal set. | Router returns a control blocker instead of writing flags/state for illegal PM selections. |
| 6 | Validate immediately before commit | Before writing completed nodes, frontier advancement, stale-evidence mutation, or terminal closure, re-compute legal actions and verify current route/frontier versions still match. | Model rejects stale legal-action snapshots and commit-after-state-drift. | Route/frontier writes are blocked if route/frontier/ledger changed after the PM card was issued. |
| 7 | Connect to existing registries | Legal actions must reference existing output contracts, event capability rows, and control transaction rows instead of duplicating them. | Model rejects unregistered action rows and action rows whose event/transaction/contract references disagree. | Source checks validate route-action policy rows against existing registries. |
| 8 | Run staged verification and local sync | After each runtime slice, run the narrow model/test set, then broader checks. Long model suites may run in the background while focused checks run in the foreground. | New model, parent/child lifecycle model, model mesh, router loop, and control transaction checks pass. | Local installed skill sync/audit/check pass; local git records the work; GitHub is not pushed. |

## Initial Route Action Policy Rows

| Action id | Actor | Router event | Existing transaction | Required state | Forbidden state |
| --- | --- | --- | --- | --- | --- |
| `continue_current_child` | Router/PM | current child event set | packet/result/gate transactions | active child exists and child work is incomplete | active parent closure requested |
| `enter_next_child` | Router | none or route progression internal | route_progression | parent/module active, child remains unentered or incomplete | all effective children complete |
| `wait_for_child_result` | Router | `worker_current_node_result_returned` or review events | result_absorption/reviewer_gate_result | packet dispatched or review requested | no active packet/review wait |
| `request_child_repair` | PM | repair events | control_blocker_repair/route_mutation | child blocker or stale child evidence exists | no child-scoped blocker or repair target |
| `build_parent_backward_targets` | PM | `pm_builds_parent_backward_targets` | route_progression | all effective descendants complete with current ledger | missing child entry, child execution, descendant completion, or current ledger |
| `review_parent_backward_replay` | Reviewer | `reviewer_passes_parent_backward_replay` / `reviewer_blocks_parent_backward_replay` | reviewer_gate_result | parent targets built and child chain closed | targets missing or child chain not closed |
| `record_parent_segment_decision` | PM | `pm_records_parent_segment_decision` | route_progression/route_mutation | reviewer-passed parent replay and current prior-path context | replay not passed, stale evidence unresolved, child chain not closed |
| `complete_parent_node` | PM | `pm_completes_parent_node_from_backward_replay` | route_progression | parent segment decision is `continue`, current route/frontier/ledger match | non-continue decision, stale legal-action snapshot, incomplete descendants |
| `mutate_route` | PM | `pm_mutates_route_after_review_block` | route_mutation | reviewer/PM blocker requires structural route change | mutation would reuse stale evidence without marking |
| `terminal_closure` | PM | terminal closure event | route_progression/legacy closure transaction | all route nodes completed and final gates pass | any active route node, open child, active blocker, or stale evidence |

## Bug and Regression Checklist

| Risk id | Possible bug | Required FlowGuard catch |
| --- | --- | --- |
| L1 | Router asks PM for an open-ended next-step decision before computing legal actions. | Reject `pm_decision_requested_without_legal_actions`. |
| L2 | PM sees `complete_parent_node` while a child or descendant is incomplete. | Reject `parent_closure_offered_before_child_chain_closed`. |
| L3 | PM sees `record_parent_segment_decision` before parent backward replay is passed. | Reject `segment_decision_offered_before_parent_replay_pass`. |
| L4 | Direct child completion is counted as full subtree completion while descendant leaves are pending. | Reject `direct_child_done_used_as_subtree_done`. |
| L5 | Stale route status or old completion ledger is used as current child completion authority. | Reject `stale_child_completion_authority`. |
| L6 | PM selects an action that was not in the Router-computed legal action set, and Router accepts it. | Reject `pm_selected_action_outside_legal_set`. |
| L7 | Router accepts a registered event whose current legal action predicate is false. | Reject `event_registered_but_action_illegal`. |
| L8 | Legal-action snapshot is computed, route/frontier changes, and Router commits using the stale snapshot. | Reject `stale_legal_action_snapshot_committed`. |
| L9 | Policy row references an event, output contract, or transaction row that does not exist. | Reject `policy_registry_reference_missing`. |
| L10 | Policy row permits an action for the wrong active node kind. | Reject `action_node_kind_mismatch`. |
| L11 | Route mutation action fails to mark stale evidence or require rerun of affected parent replay. | Reject `route_mutation_without_stale_evidence_policy`. |
| L12 | Terminal closure is offered while route nodes, child work, active blockers, or stale evidence remain. | Reject `terminal_closure_offered_with_open_route_work`. |
| L13 | PM work-request escape hatch allows PM to bypass legal route-action options. | Reject `pm_work_request_bypasses_route_action_policy`. |
| L14 | Commit writes only part of the affected state surfaces. | Reject `legal_action_partial_commit`. |
| L15 | Existing event/transaction registries pass but legal-action policy is not checked in model mesh. | Reject `mesh_green_without_legal_action_projection`. |

## Verification Matrix

| Verification | Purpose | Expected before implementation |
| --- | --- | --- |
| `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` | Verify real FlowGuard is available. | `1.0` or current supported schema. |
| `python simulations/run_flowpilot_legal_next_action_checks.py --json-out simulations/flowpilot_legal_next_action_results.json` | Prove the new legal-action model catches L1-L15 and accepts valid plans. | Pass. |
| `python simulations/run_flowpilot_parent_child_lifecycle_checks.py --json-out simulations/flowpilot_parent_child_lifecycle_results.json` | Ensure child-chain closure hazards remain covered. | Pass. |
| `python simulations/run_flowpilot_model_mesh_checks.py --project-root . --run-id run-20260512-110741 --json-out simulations/flowpilot_model_mesh_results.json` | Ensure mesh blocks live state when legal action or parent/child conformance fails. | Pass with current run still blocked until production state is repaired. |
| Targeted Router runtime tests | Prove PM cannot see, submit, or commit illegal route actions. | Pass after implementation. |
| Install sync/audit/check | Make local installed FlowPilot match repository. | Pass after implementation. |

## Non-Goals

- Do not push to GitHub.
- Do not read sealed packet, result, report, or decision bodies.
- Do not rewrite all FlowPilot cards in this slice.
- Do not remove PM ownership of route decisions. PM still decides among legal
  options; Router owns the legal option boundary.
- Do not silently reset or overwrite concurrent AI changes in unrelated files.
