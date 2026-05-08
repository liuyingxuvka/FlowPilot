"""Run checks for the FlowPilot control-plane friction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_control_plane_friction_model as model


REQUIRED_LABELS = (
    "controller_boundary_confirmed_envelope_only",
    "select_expanded_safe_flow",
    "select_optimized_transaction_flow",
    "pm_writes_research_package_with_scope_fields",
    "pm_records_research_capability_decision_preserving_package_scope",
    "worker_packet_materialized_with_research_scope",
    "packet_delivered_by_controller",
    "target_records_packet_body_open_receipt",
    "worker_result_returned_to_ledger",
    "controller_routes_result_to_reviewer_after_ledger_check",
    "reviewer_records_result_body_open_receipt",
    "optimized_relay_transaction_records_delivery_open_and_hash",
    "reviewer_writes_report_after_receipts",
    "router_accepts_reviewer_report",
    "pm_material_understanding_written_to_canonical_files",
    "product_architecture_card_delivered_with_material_context_and_fresh_views",
    "pm_writes_route_draft_with_nonempty_nodes",
    "route_process_check_card_delivered_with_route_draft_context",
    "process_officer_passes_route_check_after_nonempty_route",
    "user_stop_requested",
    "run_lifecycle_reconciled_all_authorities",
    "route_state_snapshot_refreshed_after_lifecycle_change",
    "control_plane_flow_complete",
)


HAZARD_EXPECTED_FAILURES = {
    "research_package_scope_dropped": "worker research packet was materialized after PM package scope fields were dropped",
    "reviewer_report_without_result_open_receipt": "reviewer report was accepted before delivery, packet-open, result-return, relay, and result-open receipts existed",
    "missing_receipt_blocker_escalated_to_pm": "missing receipt blocker was not routed as same-role reviewer control-plane reissue",
    "stopped_run_with_active_heartbeat": "stopped run left heartbeat, crew, packet loop, or frontier authority active",
    "stopped_run_with_active_packet_loop": "stopped run left heartbeat, crew, packet loop, or frontier authority active",
    "stopped_run_without_terminal_frontier": "stopped run left heartbeat, crew, packet loop, or frontier authority active",
    "stale_snapshot_published_as_active": "active route_state_snapshot is stale against frontier or packet ledger",
    "product_architecture_delivery_missing_material_context": "product architecture card was delivered without PM material-understanding source paths",
    "protocol_blocker_file_unregistered": "protocol blocker file existed without router-visible blocker registration",
    "control_blocker_index_stale_after_artifact_update": "router control blocker index disagreed with control blocker artifact status",
    "pm_repair_followup_event_unmatchable": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "pm_repair_followup_event_not_normalized": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "phase_card_missing_required_upstream_source": "delivered phase card was missing required upstream source paths",
    "delivered_card_phase_context_stale": "delivered card current_phase did not match its actual workflow phase",
    "terminal_snapshot_flag_mismatch": "terminal route_state_snapshot flags disagreed with terminal run status",
    "child_skill_gate_manifest_review_unsynced": "child-skill gate manifest did not sync reviewer pass status",
    "terminal_heartbeat_cleanup_unproven": "terminal continuation cleanup lacked host automation proof",
    "role_output_hash_replay_mismatch": "persisted role-output envelope hashes were not replayable against body paths",
    "frontier_stale_after_product_architecture_delivery": "execution frontier remained at material_scan after product architecture delivery",
    "display_view_stale_after_product_architecture_delivery": "route snapshot or display plan remained stale after product architecture delivery",
    "route_process_check_on_empty_route_draft": "route process check was delivered for an empty route draft",
    "route_process_check_on_shadow_route_draft": "route process check used a shadow route draft instead of the canonical route source",
    "route_draft_repair_kept_stale_route_checks": "route draft repair left stale route-check flags active",
    "multiple_active_tasks_under_current_json_only": "multiple active UI tasks were exposed under current_json_only authority",
    "optimized_transaction_without_hash_check": "optimized relay transaction skipped delivery, receipt, result-return, role, or hash evidence",
    "controller_reads_sealed_body": "Controller read sealed packet/result body",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|mode={state.mode}|holder={state.holder}|"
        f"steps={state.handoff_steps}|ctrl={state.controller_boundary_confirmed},"
        f"read={state.controller_read_sealed_body}|pkg={state.pm_research_package_written},"
        f"{state.research_package_has_decision_question},"
        f"{state.research_package_has_allowed_sources},"
        f"{state.research_package_has_stop_conditions}|cap={state.research_capability_decision_recorded}|"
        f"packet={state.worker_packet_written},{state.worker_packet_preserves_research_fields},"
        f"{state.packet_delivered},{state.packet_body_open_receipt}|result={state.result_returned},"
        f"{state.result_routed_to_reviewer},{state.result_body_open_receipt}|"
        f"review={state.reviewer_report_written},{state.reviewer_report_accepted}|"
        f"material={state.pm_material_understanding_written},{state.pm_material_understanding_source_available}|"
        f"product={state.product_architecture_card_delivered},"
        f"{state.product_architecture_delivery_has_material_context}|"
        f"protocol_blocker={state.protocol_blocker_file_written},"
        f"{state.protocol_blocker_registered_in_router_state}|"
        f"control_blocker_sync={state.control_blocker_artifact_status_written},"
        f"{state.control_blocker_router_index_matches_artifact}|"
        f"phase_sources={state.phase_dependency_cards_delivered},"
        f"{state.phase_required_sources_complete},{state.delivered_card_phase_context_fresh}|"
        f"terminal_snapshot={state.terminal_snapshot_published},"
        f"{state.terminal_snapshot_flags_consistent}|"
        f"child_skill_gate={state.child_skill_gate_review_recorded},"
        f"{state.child_skill_gate_manifest_synced_with_review}|"
        f"terminal_cleanup={state.terminal_continuation_cleanup_recorded},"
        f"{state.terminal_host_automation_cleanup_proven}|"
        f"role_hash={state.role_output_envelopes_recorded},"
        f"{state.role_output_hashes_replayable}|"
        f"stage_views={state.stage_advanced_after_material_scan},"
        f"{state.frontier_fresh_after_stage_advance},{state.product_stage_view_published},"
        f"{state.product_stage_view_fresh}|"
        f"route_draft={state.route_draft_written},{state.route_draft_has_nodes},"
        f"{state.route_draft_single_canonical_source},{state.route_draft_shadow_source_used},"
        f"{state.route_process_check_card_delivered},{state.route_process_check_passed},"
        f"{state.route_draft_repaired_after_check},{state.route_review_flags_reset_after_draft_repair}|"
        f"opt={state.optimized_relay_transaction},{state.optimized_transaction_records_delivery},"
        f"{state.optimized_transaction_records_open_receipts},"
        f"{state.optimized_transaction_records_result_return}|"
        f"role_hash={state.role_identity_checked},{state.hash_verified}|"
        f"blocker={state.receipt_missing_blocker},{state.control_blocker_lane},"
        f"{state.control_blocker_target_role},{state.pm_repair_decision_recorded},"
        f"{state.control_blocker_followup_event_matchable},"
        f"{state.control_resolution_predicate_normalized}|stop={state.stop_requested},"
        f"{state.current_status_stopped},hb={state.continuation_heartbeat_active},"
        f"crew={state.crew_live_agents_active},packet_loop={state.packet_loop_active},"
        f"frontier={state.frontier_terminal}|snapshot={state.snapshot_published_as_active},"
        f"{state.snapshot_fresh_against_frontier_and_ledger}|active={state.multiple_running_index_entries_visible},"
        f"{state.active_task_authority}"
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


def _scenario_metrics(graph: dict[str, object]) -> dict[str, object]:
    complete_states = [state for state in graph["states"] if model.is_success(state)]
    expanded_steps = [state.handoff_steps for state in complete_states if state.mode == "expanded"]
    optimized_steps = [state.handoff_steps for state in complete_states if state.mode == "optimized"]
    expanded = min(expanded_steps) if expanded_steps else None
    optimized = min(optimized_steps) if optimized_steps else None
    saved = None if expanded is None or optimized is None else expanded - optimized
    percent = None if not expanded or saved is None else round((saved / expanded) * 100, 2)
    return {
        "expanded_safe_flow_min_steps": expanded,
        "optimized_safe_flow_min_steps": optimized,
        "handoff_steps_saved": saved,
        "handoff_step_reduction_percent": percent,
        "optimization_passes_same_invariants": bool(expanded_steps and optimized_steps),
    }


def run_checks(*, json_out_requested: bool = False, live_root: Path | None = Path(".")) -> dict[str, object]:
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
    metrics = _scenario_metrics(graph)
    live_run_audit = (
        model.audit_live_run(live_root)
        if live_root is not None
        else {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "findings": [],
            "projected_invariant_failures": [],
        }
    )
    skipped_checks = {
        "production_mutation": (
            "skipped_with_reason: this model check is read-only and does not "
            "repair FlowPilot runtime artifacts"
        )
    }
    if live_run_audit.get("skipped"):
        skipped_checks["live_run_audit"] = live_run_audit.get("skip_reason")
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(metrics["optimization_passes_same_invariants"])
        and bool(live_run_audit["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "scenario_metrics": metrics,
        "live_run_audit": live_run_audit,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing the JSON result payload.")
    parser.add_argument(
        "--live-root",
        type=Path,
        default=Path("."),
        help="Project root containing .flowpilot/current.json for read-only live-run audit.",
    )
    parser.add_argument("--skip-live-audit", action="store_true", help="Run only the abstract FlowGuard model.")
    args = parser.parse_args()

    result = run_checks(
        json_out_requested=bool(args.json_out),
        live_root=None if args.skip_live_audit else args.live_root,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
