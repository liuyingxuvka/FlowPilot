"""Run checks for the FlowPilot heartbeat/manual-resume re-entry model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_resume_model as model


RESULTS_PATH = Path(__file__).with_name("flowpilot_resume_results.json")


REQUIRED_LABELS = (
    "stable_heartbeat_launcher_entered",
    "stable_manual_resume_launcher_entered",
    "resume_wake_recorded_to_router",
    "one_minute_heartbeat_resume_trigger_confirmed",
    "current_pointer_loaded",
    "current_run_root_loaded",
    "old_run_control_state_rejected",
    "router_state_loaded",
    "packet_ledger_loaded",
    "prompt_ledger_loaded",
    "execution_frontier_loaded",
    "visible_plan_restored_from_current_run",
    "crew_memory_loaded",
    "controller_relay_boundary_confirmed",
    "six_role_liveness_concurrent_probe_batch_started",
    "six_role_liveness_checked_all_active",
    "six_role_liveness_checked_recovery_needed",
    "six_role_liveness_timeout_unknown_recorded",
    "host_reuse_or_replace_resume_roles_requested",
    "active_live_resume_roles_reused_after_memory_refresh",
    "only_failed_resume_roles_replaced_from_current_run_memory",
    "all_uncertain_resume_roles_replaced_from_current_run_memory",
    "current_run_memory_injected_into_resume_roles",
    "crew_rehydration_report_written_before_pm_resume",
    "crew_capability_officer_lifecycle_flags_reconciled",
    "resume_state_clear_for_pm_decision",
    "ambiguous_resume_state_blocked_for_pm_recovery",
    "controller_instructed_to_check_prompt_manifest",
    "pm_decision_card_delivered_with_controller_reminder",
    "pm_resume_decision_returned",
    "reviewer_dispatch_card_delivered",
    "reviewer_dispatch_allowed",
    "existing_worker_result_envelope_found",
    "pm_requests_fresh_worker_packet",
    "controller_instructed_to_check_packet_ledger",
    "existing_worker_result_routed_to_reviewer_after_ledger",
    "fresh_worker_packet_sent_after_ledger",
    "fresh_worker_result_routed_to_reviewer_after_ledger",
    "reviewer_passes_reviewed_worker_result",
    "pm_node_decision_card_delivered",
    "pm_records_progress_from_reviewed_packet",
    "reentry_loop_complete",
)


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|entry={state.entry_mode}|holder={state.holder}|"
        f"work={state.work_branch}|ambiguous={state.ambiguous_state}|"
        f"heartbeat={state.heartbeat_trigger_evidence_loaded},"
        f"{state.heartbeat_interval_minutes},"
        f"{state.heartbeat_trigger_bound_to_current_run}|"
        f"ptr={state.current_pointer_loaded},{state.current_pointer_valid}|"
        f"run={state.run_root_loaded},{state.run_root_matches_pointer}|"
        f"router={state.router_state_loaded}|packet={state.packet_ledger_loaded}|"
        f"prompt={state.prompt_ledger_loaded}|frontier={state.frontier_loaded}|"
        f"visible_plan={state.visible_plan_restored_from_run}|"
        f"crew={state.crew_memory_loaded},{state.host_role_rehydrate_requested},"
        f"{state.crew_roles_ready},restored={state.crew_restored},"
        f"replaced={state.crew_replaced},memory_injected={state.run_memory_injected_into_roles},"
        f"report={state.crew_rehydration_report_written}|"
        f"liveness={state.resume_wake_recorded_to_router},batch={state.liveness_probe_batch_started},"
        f"{state.liveness_probe_batch_concurrent},"
        f"{state.all_six_liveness_probes_started_before_wait},"
        f"{state.liveness_probe_batch_id_consistent},serial={state.serial_liveness_wait_used},"
        f"{state.all_six_role_liveness_checked},{state.role_liveness_outcome}|"
        f"reuse={state.live_agent_reuse_preferred},{state.active_live_agents_reused},"
        f"failed={state.failed_role_count},replaced={state.replacement_role_count},"
        f"unneeded={state.unnecessary_replacement_attempted}|"
        f"lifecycle={state.crew_lifecycle_flags_current},"
        f"{state.capability_lifecycle_flags_current},"
        f"{state.officer_lifecycle_flags_current}|"
        f"pm={state.pm_decision_prompt_delivered},{state.pm_decision_returned}|"
        f"review={state.reviewer_dispatch_allowed},{state.reviewer_result_passed}|"
        f"progress={state.route_progress_recorded},{state.route_progress_source}|"
        f"prompt_counts={state.prompt_deliveries}/"
        f"{state.manifest_check_requests}/{state.manifest_checks}|"
        f"mail_counts={state.mail_deliveries}/"
        f"{state.ledger_check_requests}/{state.ledger_checks}"
    )


def explore_safe_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial}
    labels: set[str] = set()
    edges = 0
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            edges += 1
            if transition.state not in seen:
                seen.add(transition.state)
                queue.append(transition.state)

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    complete_states = sum(1 for state in seen if state.status == "complete")
    blocked_states = sum(1 for state in seen if state.status == "blocked")
    return {
        "ok": not invariant_failures
        and not missing_labels
        and complete_states > 0
        and blocked_states > 0,
        "state_count": len(seen),
        "edge_count": edges,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": complete_states,
        "blocked_state_count": blocked_states,
        "invariant_failures": invariant_failures,
        "states": list(seen),
    }


def check_progress(graph: dict[str, object]) -> dict[str, object]:
    states = list(graph["states"])
    index = {state: idx for idx, state in enumerate(states)}
    edges: list[list[int]] = [[] for _ in states]
    for state in states:
        source = index[state]
        for transition in model.next_safe_states(state):
            edges[source].append(index[transition.state])

    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, targets in enumerate(edges):
            if source in can_reach_terminal:
                continue
            if any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(source)
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
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def run_flowguard_explorer() -> dict[str, object]:
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


def check_hazards() -> dict[str, object]:
    results: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        detected = bool(failures)
        results[name] = {
            "detected": detected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": results}


def main() -> int:
    safe = explore_safe_graph()
    progress = check_progress(safe)
    explorer = run_flowguard_explorer()
    hazards = check_hazards()
    result = {
        "ok": bool(safe["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"]),
        "safe_graph": {key: value for key, value in safe.items() if key != "states"},
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "skipped_checks": {
            "conformance_replay": (
                "skipped_with_reason: this abstract resume model has no production "
                "adapter in the allowed write set"
            )
        },
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
