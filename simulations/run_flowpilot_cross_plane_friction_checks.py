"""Run checks for the FlowPilot cross-plane friction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_cross_plane_friction_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_cross_plane_friction_results.json"


REQUIRED_LABELS = (
    "controller_boundary_preserved_for_cross_plane_audit",
    "material_scan_envelopes_have_role_contracts_and_write_targets",
    "terminal_closure_writes_single_lifecycle_authority",
    "route_snapshot_projects_completed_frontier_nodes",
    "cockpit_projects_completed_nodes_and_hides_closed_runs",
    "reviewer_block_events_registered_in_router_taxonomy",
    "node_completion_idempotency_scoped_to_active_node",
    "install_policy_accepts_first_class_cockpit_source",
    "standard_six_roles_ready_or_blocked_before_route_work",
    "active_task_catalog_uses_current_pointer_not_history",
    "minimal_repair_strategy_satisfies_cross_plane_invariants",
)


HAZARD_EXPECTED_FAILURES = {
    "controller_reads_sealed_body_during_audit": "Controller opened sealed body files during cross-plane reconciliation",
    "material_dispatch_output_contract_role_drift": "material-scan dispatch lacks role-scoped output contract",
    "material_dispatch_write_target_missing": "material-scan dispatch lacks explicit result write target",
    "legacy_material_packets_left_unmigrated": "material-scan dispatch lacks legacy packet migration/quarantine",
    "terminal_closure_missing_run_lifecycle": "terminal closure is missing run_lifecycle.json",
    "terminal_authority_mismatch": "terminal closure is missing router/frontier/lifecycle terminal agreement",
    "terminal_control_blocker_not_cleared": "terminal closure is missing cleared active control blocker",
    "terminal_heartbeat_still_active": "terminal closure is missing inactive heartbeat",
    "route_state_snapshot_status_mismatch": "route_state_snapshot is missing completed-node status from execution_frontier",
    "route_state_snapshot_completed_checklists_pending": "route_state_snapshot is missing completed-node checklist projection",
    "selected_state_conflated_with_completed_state": "route_state_snapshot is missing selected/current state separated from completion",
    "cockpit_status_mismatch": "Cockpit projection is missing node status from execution_frontier",
    "cockpit_completed_checklists_pending": "Cockpit projection is missing completed-node checklist projection",
    "cockpit_closed_run_exposed_as_active_tab": "Cockpit projection is missing closed runs hidden from active tabs",
    "reviewer_block_event_taxonomy_gap": "reviewer blocker events are outside EXTERNAL_EVENTS taxonomy",
    "node_completion_idempotency_global_only": "node completion idempotency is not scoped to the active node",
    "install_audit_layout_policy_conflict": "install audit still rejects first-class flowpilot_cockpit source",
    "installed_skill_source_drift": "installed FlowPilot skill source differs from repository source",
    "six_role_liveness_unproven": "standard six roles have neither readiness proof nor an early blocker",
    "active_history_visible_by_default": "completed, abandoned, or stale history is visible by default",
    "active_task_authority_not_current_pointer": "active UI task authority is not the current pointer",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|step={state.step}|"
        f"boundary={state.controller_boundary_preserved},body={state.sealed_body_files_opened_by_controller}|"
        f"material={state.material_scan_packets_observed},"
        f"{state.material_output_contract_role_scoped},"
        f"{state.material_dispatch_write_target_explicit},"
        f"{state.material_legacy_packets_quarantined_or_migrated}|"
        f"terminal={state.terminal_closure_observed},"
        f"{state.run_lifecycle_record_written},"
        f"{state.router_frontier_lifecycle_terminal_consistent},"
        f"{state.terminal_control_blocker_cleared},"
        f"{state.heartbeat_inactive_after_terminal}|"
        f"route={state.completed_nodes_observed},{state.route_snapshot_visible},"
        f"{state.route_snapshot_status_derived_from_frontier},"
        f"{state.route_snapshot_checklists_complete_for_completed_nodes},"
        f"{state.selected_status_separate_from_completion}|"
        f"cockpit={state.cockpit_projection_visible},"
        f"{state.cockpit_status_derived_from_frontier},"
        f"{state.cockpit_checklists_complete_for_completed_nodes},"
        f"{state.cockpit_closed_runs_hidden_from_active_tabs}|"
        f"events={state.reviewer_block_events_observed},{state.reviewer_block_events_registered}|"
        f"completion={state.node_completion_observed},"
        f"{state.node_completion_idempotency_scoped_to_active_node}|"
        f"install={state.cockpit_source_present_in_tree},"
        f"{state.install_audit_policy_accepts_first_class_cockpit},"
        f"{state.installed_skill_matches_repository_source}|"
        f"roles={state.standard_six_roles_requested},{state.role_liveness_ready_or_blocked}|"
        f"active_tasks={state.active_task_policy_observed},"
        f"{state.history_default_hidden},{state.current_pointer_is_active_authority}|"
        f"strategy={state.minimal_repair_strategy_selected}"
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
            if idx not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
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


def _solution_simulation() -> dict[str, object]:
    solution_state = model.repair_solution_state()
    failures = model.invariant_failures(solution_state)
    return {
        "ok": not failures and model.is_success(solution_state),
        "state": solution_state.__dict__,
        "invariant_failures": failures,
        "proof": (
            "The minimal repair strategy is represented by the safe solution "
            "state, where every failing plane is closed without sealed-body reads "
            "or broad product-content rewrites."
        ),
    }


def run_checks(
    *,
    json_out_requested: bool = False,
    live_root: Path | None = Path("."),
    run_id: str | None = None,
) -> dict[str, object]:
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
    live_run_audit = (
        model.audit_live_run(live_root, run_id=run_id)
        if live_root is not None
        else {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "findings": [],
            "projected_invariant_failures": [],
            "body_files_opened": False,
        }
    )
    findings = live_run_audit.get("findings")
    finding_list = findings if isinstance(findings, list) else []
    repair_strategy = model.minimal_repair_strategy(finding_list)
    solution = _solution_simulation()
    skipped_checks = {
        "production_mutation": (
            "skipped_with_reason: user requested model upgrade, scan, and "
            "minimal repair strategy before production code edits"
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
        and bool(live_run_audit["ok"])
        and bool(solution["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "live_run_audit": live_run_audit,
        "minimal_repair_strategy": repair_strategy,
        "solution_simulation": solution,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, help="Optional JSON result output path.")
    parser.add_argument(
        "--live-root",
        type=Path,
        default=Path("."),
        help="Project root containing .flowpilot/current.json for read-only live audit.",
    )
    parser.add_argument("--run-id", help="Optional FlowPilot run id to audit instead of current.json.")
    parser.add_argument("--skip-live-audit", action="store_true", help="Run only the abstract model.")
    args = parser.parse_args()

    result = run_checks(
        json_out_requested=bool(args.json_out),
        live_root=None if args.skip_live_audit else args.live_root,
        run_id=args.run_id,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
