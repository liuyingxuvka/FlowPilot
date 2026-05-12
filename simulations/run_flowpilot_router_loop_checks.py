"""Run checks for the FlowPilot current-node router packet-loop model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_router_loop_model as model


REQUIRED_LABELS = (
    "controller_boundary_confirmed_envelope_only",
    "controller_fail_closes_no_next_action_to_pm_blocker",
    "pm_activates_route",
    "officer_lifecycle_flags_reconciled_before_model_packet",
    "officer_packet_card_delivered_before_controller_relay",
    "officer_packet_relayed_after_officer_card",
    "officer_result_returned_to_packet_ledger",
    "officer_result_ledger_checked_before_pm_relay",
    "officer_result_routed_to_pm_after_ledger_check",
    "pm_absorbs_officer_result_before_node_packet",
    "controller_refreshes_route_history_context_for_node_plan",
    "pm_reads_prior_path_context_for_node_plan",
    "pm_opens_current_node_high_standard_gate",
    "pm_writes_node_acceptance_plan_before_packet",
    "reviewer_reviews_node_acceptance_plan_before_packet",
    "current_node_packet_registered_after_route_activation_and_acceptance_plan",
    "write_grant_issued_from_current_node_packet",
    "router_direct_dispatch_allowed_for_current_node",
    "worker_dispatched_after_router_direct_dispatch",
    "active_holder_lease_issued_for_current_worker",
    "active_holder_ack_recorded_by_current_worker",
    "active_holder_packet_opened_through_runtime",
    "active_holder_progress_recorded_as_controller_safe_metadata",
    "active_holder_initial_result_submitted_to_router",
    "router_mechanically_rejects_result_to_same_holder",
    "active_holder_resubmits_mechanically_repaired_result",
    "router_accepts_fast_lane_result_mechanics",
    "worker_result_ledger_checked_before_reviewer_relay",
    "router_writes_controller_notice_after_fast_lane_close",
    "worker_result_routed_to_reviewer",
    "reviewer_worker_result_review_card_delivered_after_result_relay",
    "reviewer_passes_current_node_result",
    "reviewer_blocks_current_node_result",
    "controller_refreshes_route_history_context_for_repair_or_mutation",
    "pm_reads_prior_path_context_for_repair_or_mutation",
    "pm_registers_repair_packet_after_reviewer_block",
    "router_direct_repair_dispatch_after_block",
    "repair_worker_dispatched_after_router_direct_dispatch",
    "repair_result_returned_to_packet_ledger",
    "repair_result_ledger_checked_before_reviewer_relay",
    "repair_result_routed_to_reviewer_after_ledger_check",
    "reviewer_rechecks_repair_result",
    "reviewer_passes_current_node_after_repair_recheck",
    "route_mutation_after_reviewer_block_marks_stale_evidence_and_frontier",
    "frontier_rewritten_for_mutated_route",
    "pm_activates_mutated_route",
    "reviewer_blocks_mutated_route_result_terminal",
    "pm_node_completion_card_delivered_after_reviewer_pass",
    "pm_completes_current_node_after_reviewer_pass",
    "node_completion_ledger_updated_after_pm_completion",
    "pm_enumerates_parent_backward_targets_after_node_completion",
    "reviewer_parent_backward_replay_after_targets",
    "controller_refreshes_route_history_context_for_parent_segment",
    "pm_reads_prior_path_context_for_parent_segment",
    "pm_records_parent_segment_decision_after_backward_replay",
    "pm_completes_parent_node_after_replay_and_segment_decision",
    "reviewer_reruns_same_scope_replay_after_route_mutation",
    "current_route_scanned_for_final_ledger",
    "pm_evidence_quality_package_card_delivered_before_final_ledger",
    "pm_writes_evidence_quality_package_before_final_ledger",
    "evidence_quality_review_card_delivered_after_package",
    "reviewer_passes_evidence_quality_before_final_ledger",
    "controller_refreshes_route_history_context_for_final_ledger",
    "pm_reads_prior_path_context_for_final_ledger",
    "final_ledger_zero_unresolved_confirmed",
    "final_ledger_scan_finds_unresolved_items",
    "pm_final_ledger_card_delivered_after_evidence_quality_pass",
    "pm_generates_final_ledger_source_of_truth",
    "pm_builds_clean_final_ledger",
    "terminal_replay_map_generated_from_final_ledger",
    "reviewer_terminal_root_segment_replayed",
    "reviewer_terminal_parent_segment_replayed",
    "reviewer_terminal_leaf_segment_replayed",
    "pm_records_terminal_segment_decisions",
    "final_backward_replay_card_delivered_after_terminal_segments",
    "reviewer_final_backward_replay_after_all_segments",
    "task_completion_projection_published_from_completion_ledger",
    "pm_terminal_closure_card_delivered_after_completion_projection",
    "completion_recorded_after_final_replay",
)


HAZARD_EXPECTED_FAILURES = {
    "packet_registered_before_route_activation": "current-node packet registered before route activation",
    "officer_packet_card_before_route_activation": "officer packet card delivered before route activation",
    "officer_packet_card_before_lifecycle_flags": "officer packet card delivered before officer lifecycle flags were reconciled",
    "officer_packet_relayed_without_officer_card": "officer packet relayed before officer card",
    "officer_result_routed_without_ledger_check": "officer result routed to PM before packet-ledger check",
    "reviewer_acceptance_plan_review_without_plan": "reviewer reviewed node acceptance plan before PM wrote it",
    "node_acceptance_plan_without_pm_high_standard_gate": "node acceptance plan written before PM high-standard gate",
    "node_acceptance_plan_without_prior_path_context": "node acceptance plan written before PM read fresh prior path context",
    "packet_registered_before_acceptance_plan_review": "current-node packet registered before PM high-standard gate and reviewed node acceptance plan",
    "parent_node_current_packet_registered": "current-node packet registered for parent or module node",
    "control_repair_wait_event_incompatible_with_parent": "router allowed event incompatible with active node kind",
    "parent_backward_repair_targets_leaf_dispatch": "parent backward replay repair waited on non-parent-safe event",
    "collapsed_repair_outcomes_on_business_validated_event": "repair outcome table collapsed success blocker and protocol-blocker onto one business-validated event",
    "worker_dispatched_before_reviewer_dispatch": "worker dispatched before router direct dispatch",
    "reviewer_pass_without_routed_worker_result": "reviewer decided before worker result was routed to reviewer",
    "reviewer_result_card_before_result_relay": "reviewer result-review card delivered before worker result relay",
    "reviewer_decision_without_result_review_card": "reviewer decided before result-review card delivery",
    "worker_result_routed_without_ledger_check": "worker result routed before result was returned and packet-ledger checked",
    "pm_completion_without_reviewer_pass": "PM completed current node before reviewer pass",
    "repair_packet_without_reviewer_block": "repair packet registered before reviewer block",
    "repair_worker_dispatched_before_reviewer_dispatch": "repair worker dispatched before router direct repair dispatch",
    "repair_result_routed_without_ledger_check": "repair result routed before result was returned and packet-ledger checked",
    "repair_recheck_without_reviewer_result": "repair recheck passed before repair result reached reviewer",
    "pm_completion_after_block_without_recheck": "reviewer pass after block recorded without repair recheck",
    "route_mutation_without_reviewer_block": "route mutation recorded without reviewer block",
    "route_mutation_without_stale_evidence": "route mutation did not mark affected evidence stale",
    "route_mutation_without_stale_frontier": "route mutation did not mark the execution frontier stale",
    "route_mutation_without_prior_path_context": "route mutation recorded before PM used prior path context",
    "packet_registered_against_stale_mutation_frontier": "current-node packet registered against stale mutation frontier",
    "final_scan_before_same_scope_replay_after_mutation": "current route scanned for final ledger before same-scope replay rerun after mutation",
    "parent_completed_without_backward_replay": "parent node completed before parent backward replay and PM segment decision",
    "parent_completed_without_pm_segment_decision": "parent node completed before parent backward replay and PM segment decision",
    "parent_segment_decision_without_prior_path_context": "PM parent segment decision recorded before PM read fresh prior path context",
    "final_ledger_card_before_evidence_quality_package_card": "PM final ledger card delivered before PM evidence/quality package card",
    "final_ledger_card_before_reviewer_evidence_quality_pass": "PM final ledger card delivered before reviewer evidence quality pass",
    "final_ledger_built_before_evidence_quality_reviewer_pass": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_without_parent_completion": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_without_node_completion": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_without_current_route_scan": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_with_unresolved_items": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_without_source_of_truth_generation": "final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation",
    "final_ledger_card_without_prior_path_context": "PM final ledger card delivered before PM read fresh prior path context",
    "final_ledger_without_prior_path_context": "final ledger built before PM read fresh prior path context",
    "final_ledger_with_stale_or_unresolved_evidence": "final ledger built while stale or unresolved evidence remained",
    "final_ledger_with_pending_generated_resources": "final ledger built while generated resources were still pending",
    "final_ledger_missing_ui_visual_screenshots": "final ledger built before required UI/visual screenshots existed",
    "final_ledger_reuses_old_assets_as_current_evidence": "final ledger built while old assets were reused as current evidence",
    "terminal_replay_map_without_source_ledger": "terminal replay map generated before clean source-of-truth final ledger",
    "terminal_parent_segment_before_root": "terminal parent segment replayed before root segment",
    "terminal_leaf_segment_before_parent": "terminal leaf segment replayed before parent segment",
    "terminal_pm_decisions_before_segments": "PM terminal segment decisions recorded before all terminal replay segments",
    "final_backward_replay_without_segments": "final backward replay passed before clean ledger, replay map, and PM segment decisions",
    "final_backward_replay_without_clean_ledger": "final backward replay passed before clean ledger, replay map, and PM segment decisions",
    "controller_reads_sealed_body": "Controller read a sealed packet/result body",
    "controller_originates_project_evidence": "Controller originated project evidence",
    "controller_relays_body_content": "Controller relayed packet/result body content instead of envelope-only metadata",
    "completion_before_final_backward_replay": "completion recorded before final backward replay",
    "completion_without_task_completion_projection": "completion recorded before task completion projection was derived from completion ledger",
    "controller_does_project_work_after_no_next_action": "Controller started project work after no-next-action instead of fail-closing to PM",
    "expected_evidence_quality_package_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "expected_evidence_quality_review_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "expected_final_backward_replay_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "expected_final_ledger_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "expected_pm_completion_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "expected_pm_terminal_closure_wait_materializes_blocker": "expected role-event wait incorrectly wrote PM decision-required blocker",
    "node_completion_ledger_without_pm_completion": "node completion ledger updated before PM node completion",
    "no_next_action_without_pm_blocker": "Controller detected no legal next action without writing a PM decision-required blocker",
    "parent_targets_before_node_completion_ledger": "parent backward targets enumerated before node completion ledger update",
    "task_completion_projection_without_completion_ledger": "task completion projection published before node completion ledger and final backward replay",
    "worker_dispatched_before_write_grant": "worker dispatched before current-node write grant",
    "worker_project_write_without_grant": "worker project write occurred before current-node write grant",
    "write_grant_before_packet_registration": "write grant issued before current-node packet registration",
    "active_holder_lease_before_worker_dispatch": "active-holder lease issued before current worker dispatch and write grant",
    "active_holder_contact_without_lease": "active-holder contact attempted without an issued lease",
    "active_holder_contact_by_wrong_role": "active-holder fast lane accepted contact from a non-holder role",
    "active_holder_contact_by_stale_agent": "active-holder fast lane accepted contact from a stale or wrong agent",
    "active_holder_contact_by_stale_packet": "active-holder fast lane accepted a stale or wrong packet",
    "active_holder_contact_after_stale_frontier": "active-holder fast lane accepted contact after route or frontier staleness",
    "active_holder_contact_action_not_allowed": "active-holder fast lane accepted an action outside the lease",
    "fast_lane_progress_leaks_controller_visible_content": "active-holder progress exposed sealed body, findings, evidence, or recommendations",
    "fast_lane_result_before_packet_ack": "active-holder result submitted before packet ack",
    "fast_lane_result_before_packet_open": "active-holder result submitted before packet body was opened through packet runtime",
    "fast_lane_mechanical_pass_marks_node_complete": "PM completed current node before reviewer pass",
    "fast_lane_closes_without_controller_notice": "worker result routed to reviewer before router wrote Controller next-action notice",
    "fast_lane_controller_notice_before_ledger_check": "router wrote Controller next-action notice before fast-lane mechanics and ledger check passed",
    "true_no_next_action_without_blocker": "Controller detected no legal next action without writing a PM decision-required blocker",
}


EXPECTED_ROLE_EVENT_WAIT_FAILURE = "expected role-event wait incorrectly wrote PM decision-required blocker"


def _expected_failure_for_hazard(name: str) -> str:
    if name in HAZARD_EXPECTED_FAILURES:
        return HAZARD_EXPECTED_FAILURES[name]
    if (
        name.startswith("expected_role_event_wait_")
        and name.endswith("_materializes_blocker")
    ):
        return EXPECTED_ROLE_EVENT_WAIT_FAILURE
    raise KeyError(name)


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|route={state.route_version},"
        f"node_kind={state.active_node_kind}|"
        f"active={state.route_activated}|ctrl={state.controller_boundary_confirmed}|"
        f"ctrl_mode={state.controller_only_mode_active},"
        f"{state.no_next_action_detected},"
        f"{state.pm_decision_required_blocker_written}|"
        f"control_repair={state.control_repair_origin},"
        f"{state.control_repair_wait_event},"
        f"outcomes={state.repair_outcome_success_event},"
        f"{state.repair_outcome_blocker_event},"
        f"{state.repair_outcome_protocol_blocker_event}|"
        f"officer={state.officer_packet_card_delivered},"
        f"{state.officer_packet_relayed},"
        f"{state.officer_packet_identity_boundary_present},"
        f"{state.officer_result_returned},"
        f"{state.officer_result_identity_boundary_present},"
        f"{state.officer_result_ledger_checked},"
        f"{state.officer_result_routed_to_pm},"
        f"life={state.officer_lifecycle_flags_current}|"
        f"history={state.route_history_context_refreshed},"
        f"{state.pm_prior_path_context_reviewed},"
        f"{state.route_history_context_stale},"
        f"{state.pm_prior_path_context_used_for_route_mutation}|"
        f"high_standard={state.pm_node_high_standard_gate_opened},"
        f"{state.pm_node_high_standard_risks_reviewed}|"
        f"plan={state.node_acceptance_plan_written},"
        f"{state.reviewer_node_acceptance_plan_reviewed}|"
        f"packet={state.current_node_packet_registered},grant={state.write_grant_issued}|"
        f"dispatch={state.reviewer_dispatch_allowed},{state.worker_dispatched},"
        f"write={state.worker_project_write_performed},"
        f"{state.worker_packet_identity_boundary_present}|"
        f"result={state.worker_result_returned},"
        f"{state.worker_result_identity_boundary_present},"
        f"{state.worker_result_ledger_checked},"
        f"{state.worker_result_routed_to_reviewer}|"
        f"review_card={state.reviewer_worker_result_card_delivered}|"
        f"review={state.reviewer_decision},block_seen={state.reviewer_block_seen}|"
        f"repair={state.repair_packet_registered},"
        f"{state.repair_dispatch_allowed},"
        f"{state.repair_worker_dispatched},"
        f"{state.repair_packet_identity_boundary_present},"
        f"{state.repair_result_returned},"
        f"{state.repair_result_identity_boundary_present},"
        f"{state.repair_result_ledger_checked},"
        f"{state.repair_result_routed_to_reviewer},"
        f"{state.repair_recheck_passed}|"
        f"node_done={state.pm_node_completion_card_delivered},"
        f"{state.pm_node_completed},{state.node_completion_ledger_updated}|parent="
        f"{state.parent_backward_targets_enumerated},"
        f"{state.parent_backward_replay_passed},"
        f"{state.parent_pm_segment_decision_recorded},"
        f"{state.parent_node_completed}|mutation={state.route_mutation_count},"
        f"stale={state.stale_evidence_marked},{state.frontier_marked_stale},"
        f"frontier_rewritten={state.frontier_rewritten_after_mutation},"
        f"same_scope_replay={state.same_scope_replay_rerun_after_mutation}|"
        f"evidence_quality={state.pm_evidence_quality_package_card_delivered},"
        f"{state.evidence_quality_package_written},"
        f"{state.evidence_quality_review_card_delivered},"
        f"{state.evidence_quality_reviewer_passed}|hazards="
        f"{state.stale_or_unresolved_evidence_present},"
        f"{state.pending_generated_resources},"
        f"{state.ui_visual_required},"
        f"{state.ui_visual_screenshots_present},"
        f"{state.old_assets_reused_as_current_evidence}|"
        f"ledger={state.current_route_scan_done},{state.unresolved_count_zero},"
        f"{state.pm_final_ledger_card_delivered},"
        f"source={state.final_ledger_source_of_truth_generated},"
        f"{state.final_ledger_built},{state.final_ledger_clean}|"
        f"segments={state.terminal_replay_map_generated_from_final_ledger},"
        f"{state.terminal_replay_root_segment_passed},"
        f"{state.terminal_replay_parent_segment_passed},"
        f"{state.terminal_replay_leaf_segment_passed},"
        f"{state.terminal_replay_pm_segment_decisions_recorded}|"
        f"replay={state.final_backward_replay_card_delivered},"
        f"{state.final_backward_replay_passed},"
        f"projection={state.task_completion_projection_published},"
        f"closure={state.pm_terminal_closure_card_delivered}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(seen)
                seen.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    invariant_failures = graph["invariant_failures"]
    return {
        "ok": not invariant_failures
        and not missing_labels
        and any(model.is_success(state) for state in states)
        and any(state.status == "blocked" for state in states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": sum(1 for state in states if state.status == "complete"),
        "blocked_state_count": sum(1 for state in states if state.status == "blocked"),
        "invariant_failures": invariant_failures,
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
            ):
                can_reach_terminal.add(source)
                changed = True
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _tarjan_scc(edges: list[list[tuple[str, int]]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlinks: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for _label, target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def _check_loops(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    closed_nonterminal_components: list[list[str]] = []

    for component in _tarjan_scc(edges):
        members = set(component)
        if any(model.is_terminal(states[index]) for index in members):
            continue
        has_outgoing_to_other_component = any(
            target not in members
            for index in members
            for _label, target in edges[index]
        )
        if not has_outgoing_to_other_component:
            closed_nonterminal_components.append(
                [_state_id(states[index]) for index in component[:5]]
            )

    return {
        "ok": not closed_nonterminal_components,
        "nonterminating_component_count": len(closed_nonterminal_components),
        "nonterminating_component_samples": closed_nonterminal_components[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _check_hazards() -> dict[str, object]:
    results: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = _expected_failure_for_hazard(name)
        detected = any(expected in failure for failure in failures)
        results[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": results}


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    loops = _check_loops(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    skipped_checks = {
        "conformance_replay": (
            "skipped_with_reason: this abstract router-loop model has no "
            "production replay adapter in the allowed write set"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = (
            "skipped_with_reason: no --json-out path was provided"
        )
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(loops["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "loop": loops,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for writing the JSON result payload.",
    )
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
