"""Run checks for the FlowPilot repair transaction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_repair_transaction_model as model


REQUIRED_LABELS = (
    "reviewer_blocker_detected_node_acceptance_plan",
    "reviewer_blocker_detected_current_node_dispatch",
    "reviewer_blocker_detected_node_result",
    "reviewer_blocker_detected_material_dispatch",
    "router_registers_blocker_with_origin_and_failure_events",
    "pm_records_model_miss_triage_for_modelable_blocker",
    "pm_records_flowguard_out_of_scope_reason",
    "pm_issues_model_miss_officer_request",
    "officer_reports_same_class_findings_and_minimal_repair",
    "pm_selects_model_backed_repair_candidate",
    "pm_selects_out_of_scope_repair_candidate",
    "pm_records_repair_decision_without_resolving_blocker",
    "router_opens_repair_transaction",
    "router_opens_await_existing_event_repair_transaction",
    "router_queues_operation_replay_repair_transaction",
    "router_queues_controller_repair_work_packet",
    "router_records_terminal_repair_stop",
    "existing_event_producer_completes_repair_success",
    "existing_event_producer_returns_followup_blocker",
    "queued_repair_action_completes_success",
    "queued_repair_action_reports_followup_blocker",
    "pm_writes_reissue_spec_inside_transaction",
    "router_atomically_commits_reissue_generation_and_outcome_table",
    "post_repair_model_check_passed_after_committed_generation",
    "reviewer_recheck_requested_after_committed_generation",
    "reviewer_recheck_allows_dispatch",
    "reviewer_recheck_returns_followup_blocker",
    "reviewer_recheck_returns_protocol_blocker",
    "router_refreshes_visible_authorities_after_recheck",
)


HAZARD_EXPECTED_FAILURES = {
    "blocker_registered_without_nonterminal_events": "router blocker registration lacked origin or nonterminal repair events",
    "node_acceptance_plan_without_pm_lane": "reviewer block kind node_acceptance_plan has no matching PM repair lane",
    "current_node_dispatch_missing_model_miss_card_support": "reviewer block kind current_node_dispatch is not accepted end-to-end by PM model-miss repair",
    "material_dispatch_repair_event_not_accepted": "reviewer block kind material_dispatch is not accepted end-to-end by PM model-miss repair",
    "material_dispatch_repair_event_not_routed": "reviewer block kind material_dispatch is not accepted end-to-end by PM model-miss repair",
    "pm_decision_self_resolves_blocker": "PM repair decision resolved the blocker by itself",
    "repair_decision_before_model_miss_triage": "PM repair decision started before closing model-miss triage obligation",
    "repair_decision_before_model_miss_path_selected": "PM repair decision started before selecting a model-miss repair path",
    "model_backed_repair_without_officer_report": "PM selected a model-backed repair before officer same-class findings and minimal repair recommendation",
    "out_of_scope_repair_without_reason": "PM out-of-scope repair decision lacked FlowGuard incapability reason",
    "reissue_spec_outside_transaction": "PM repair wrote replacement artifacts outside a repair transaction",
    "await_existing_event_without_producer": "await_existing_event repair transaction lacked an existing producer",
    "legacy_event_replay_without_producer": "legacy event_replay transaction lacked an existing producer compatibility alias",
    "operation_replay_without_safe_recorded_operation": "operation_replay repair transaction did not queue a safe recorded operation replay",
    "controller_repair_packet_without_boundaries": "controller_repair_work_packet transaction lacked bounded work packet and queued action",
    "transaction_commits_packet_files_without_ledger": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "transaction_commits_ledger_without_dispatch_index": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "transaction_commits_without_router_outcome_table": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "partial_generation_published_before_commit": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "replacement_generation_keeps_old_generation_current": "replacement packet generation lacked supersession, canonical identity, replayable hashes, or explicit result targets",
    "replacement_generation_has_duplicate_identity": "replacement packet generation lacked supersession, canonical identity, replayable hashes, or explicit result targets",
    "success_only_outcome_table": "repair transaction router outcome table did not route success, blocker, and protocol outcomes",
    "parent_repair_rerun_targets_current_node_packet": "repair rerun target event incompatible with active node kind",
    "parent_repair_outcome_targets_current_node_packet": "repair outcome event incompatible with active node kind",
    "collapsed_repair_outcomes_on_business_event": "repair outcome table collapsed success blocker and protocol-blocker onto one business-validated event",
    "routable_outcome_missing_event_identity": "repair success outcome was routable without event identity",
    "reviewer_recheck_before_commit": "reviewer recheck was requested before a committed generation and complete outcome table",
    "reviewer_recheck_before_post_repair_model_check": "reviewer recheck was requested before the repaired FlowGuard model checked the candidate fix",
    "reviewer_blocker_unroutable": "reviewer recheck outcome was not accepted by router",
    "reviewer_protocol_blocker_unroutable": "reviewer recheck outcome was not accepted by router",
    "blocked_terminal_without_followup_blocker": "repair transaction blocked without registering a follow-up blocker",
    "complete_terminal_without_authority_refresh": "terminal repair transaction state did not refresh ledger, frontier, and display authorities",
    "complete_terminal_keeps_stale_repair_lane": "terminal repair transaction left stale active repair transaction or recheck pending action",
    "controller_no_legal_next_after_recheck": "repair transaction reached no legal next action",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|steps={state.steps}|"
        f"node={state.active_node_kind},origin={state.control_repair_origin},"
        f"rerun={state.rerun_target_event}|"
        f"blocker={state.blocker_detected},{state.blocker_registered_in_router},"
        f"{state.blocker_has_origin_event},{state.blocker_has_allowed_nonterminal_events},"
        f"kind={state.blocker_kind},lane={state.blocker_pm_repair_lane},"
        f"cards={state.pm_model_miss_cards_accept_blocker_kind},"
        f"triage={state.pm_model_miss_triage_accepts_blocker_kind},"
        f"repair_accepts={state.pm_review_repair_event_accepts_blocker_kind},"
        f"repair_routes={state.pm_review_repair_event_routes_blocker_kind}|"
        f"model_miss={state.model_miss_triage_recorded},modelable={state.flowguard_bug_class_modelable},"
        f"out_of_scope={state.flowguard_out_of_scope_reason_recorded},"
        f"request={state.model_miss_officer_request_issued},"
        f"report={state.model_miss_officer_report_returned},"
        f"same_class={state.same_class_findings_recorded},"
        f"candidates={state.repair_candidates_compared},"
        f"minimal={state.minimal_sufficient_repair_recommended},"
        f"pm_selected={state.pm_selected_repair_after_model_miss}|"
        f"pm={state.pm_repair_decision_recorded},self_resolve={state.pm_decision_resolves_blocker}|"
        f"tx={state.repair_transaction_opened},{state.transaction_id_recorded},{state.transaction_plan_kind}|"
        f"exec={state.repair_plan_validation_passed},{state.replay_operation_recorded},"
        f"{state.replay_operation_safe},{state.concrete_repair_action_queued},"
        f"{state.existing_event_producer_found},{state.controller_repair_packet_bounded},"
        f"{state.router_internal_handler_found},{state.terminal_stop_recorded},"
        f"legacy={state.legacy_event_replay_alias}|"
        f"stage={state.replacement_spec_written},{state.packet_files_staged},"
        f"{state.ledger_entries_staged},{state.dispatch_index_staged},"
        f"{state.router_resolution_table_staged},commit={state.transaction_committed_atomically},"
        f"partial={state.partial_generation_published}|"
        f"gen={state.replacement_generation_published},{state.old_generation_superseded},"
        f"{state.canonical_packet_identity_unique},{state.packet_hashes_replayable},"
        f"{state.result_write_targets_explicit},post_model={state.post_repair_model_check_passed}|"
        f"outcomes={state.success_outcome_routable},{state.blocker_outcome_routable},"
        f"{state.protocol_outcome_routable},events={state.success_outcome_event},"
        f"{state.blocker_outcome_event},{state.protocol_outcome_event}|"
        f"review={state.reviewer_recheck_requested},{state.reviewer_outcome},"
        f"accepted={state.router_accepted_reviewer_outcome}|"
        f"terminal={state.original_blocker_resolved},{state.followup_blocker_registered},"
        f"{state.packet_ledger_refreshed},{state.frontier_refreshed},"
        f"{state.display_refreshed},active_tx={state.active_repair_transaction},"
        f"repair_pending={state.repair_recheck_pending_action},"
        f"main={state.main_flow_resumed_after_success},dead={state.no_legal_next_action}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "terminal_state_count": len(terminal),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "repair_transaction_generation_commit",
        "principles": [
            "PM repair decisions first close the model-miss obligation: FlowGuard-modelable blockers get officer same-class findings and a minimal repair recommendation, while out-of-scope blockers need an explicit incapability reason.",
            "PM repair decisions open a transaction; they never resolve blockers directly.",
            "The repair transaction plan kind is the executable authority; PM explanation fields do not create Router work by themselves.",
            "Every committed repair transaction has a concrete queued action, existing event producer, Router handler, or explicit terminal stop.",
            "Replacement packets are committed as one generation across physical files, packet ledger, dispatch index, and router resolution table.",
            "Committed repair generations pass the repaired FlowGuard model check before reviewer recheck starts.",
            "The router publishes success, blocker, and protocol-blocker outcomes as distinct event identities before reviewer recheck starts.",
            "Every repair target event is checked against the active node kind; parent/backward-replay repairs only use parent-safe events.",
            "A reviewer failure is a legal terminal blocked state with a router-visible follow-up blocker, not controller no-legal-next-action.",
            "Terminal success or blocked states refresh packet ledger, frontier, and display authorities together.",
        ],
        "minimal_runtime_change_set": [
            "Add a PM model-miss triage gate before PM repair decision and transaction opening.",
            "Require officer model-miss reports to include same-class findings, candidate comparison, and a minimal sufficient repair recommendation for modelable blockers.",
            "Add a run-scoped repair_transaction record and transaction_id.",
            "Validate repair_transaction.plan_kind with plan-specific executable fields before commit.",
            "Move packet reissue materialization behind one commit function.",
            "Run the repaired FlowGuard model against the candidate fix before reviewer recheck.",
            "Replace allowed_resolution_events success-only lists with an outcome table containing distinct success and non-success event identities.",
            "Add one event-capability preflight used by both allowed_external_events and repair outcome-table construction.",
            "Require reviewer recheck to consume only committed generation ids.",
            "Refresh router_state, packet_ledger, execution_frontier, and display surfaces in the same commit/finalize path.",
        ],
    }


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    skipped_checks = {
        "production_mutation": (
            "covered_elsewhere: this runner validates the model contract; "
            "runtime conformance is exercised by router unit tests"
        ),
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "architecture_candidate": _architecture_candidate(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing JSON result payload.")
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
