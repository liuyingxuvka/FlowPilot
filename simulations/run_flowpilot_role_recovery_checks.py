"""Run checks for the unified FlowPilot role-recovery model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_role_recovery_model as model


RESULTS_PATH = Path(__file__).with_name("flowpilot_role_recovery_results.json")


REQUIRED_LABELS = (
    "heartbeat_entered_unified_recovery",
    "manual_resume_entered_unified_recovery",
    "mid_run_liveness_fault_entered_unified_recovery",
    "user_stop_preempts_recovery",
    "recovery_preempts_normal_work",
    "current_run_state_loaded",
    "all_six_sweep_selected",
    "targeted_role_scope_selected",
    "restore_attempted_before_replacement",
    "old_role_restored",
    "targeted_replacement_spawned",
    "targeted_replacement_capacity_full",
    "slot_reconciliation_attempted_after_capacity_full",
    "full_crew_recycle_attempted",
    "full_crew_recycle_succeeded",
    "full_crew_recycle_failure_blocks_environment",
    "memory_context_injected",
    "packet_ownership_reconciled",
    "stale_generation_output_quarantined",
    "recovery_report_written",
    "recovered_role_obligations_scanned_existing_evidence",
    "recovered_role_obligations_scanned_missing_evidence",
    "recovered_role_obligations_scanned_semantic_ambiguity",
    "existing_ack_and_output_settled_without_replay",
    "replacement_row_created_for_original_order_1",
    "original_wait_superseded_after_replacement_1",
    "replacement_row_created_for_original_order_2",
    "original_wait_superseded_after_replacement_2",
    "replacement_creation_failure_blocks_later_replay",
    "mechanical_replay_completed_without_pm_notification",
    "pm_decision_requested_after_recovery",
    "pm_recovery_decision_returned",
    "recovery_loop_complete",
)


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|trigger={state.trigger_source}|"
        f"scope={state.recovery_scope}|failed={state.target_failed_roles}|"
        f"pending={state.recovery_pending}|priority={state.priority_confirmed}|"
        f"suspended={state.normal_work_suspended}|"
        f"tx={state.transaction_opened}|loaded={state.state_loaded}|"
        f"scope_confirmed={state.scope_confirmed}|"
        f"restore={state.restore_attempted},{state.restore_result}|"
        f"replace={state.targeted_replace_attempted},"
        f"{state.targeted_replace_result}|"
        f"slot={state.slot_reconciliation_attempted},"
        f"{state.slot_reconciliation_result}|"
        f"full={state.full_recycle_attempted},{state.full_recycle_result}|"
        f"crew={state.crew_ready},gen={state.crew_generation},"
        f"epoch={state.role_binding_epoch_advanced}|"
        f"memory={state.memory_context_injected}|"
        f"packet={state.packet_holder_lost},"
        f"{state.packet_ownership_reconciled}|"
        f"stale={state.stale_generation_output_seen},"
        f"{state.stale_generation_output_quarantined},"
        f"{state.stale_generation_output_accepted}|"
        f"report={state.recovery_report_written}|"
        f"scan={state.obligations_scanned}|"
        f"evidence={state.valid_existing_evidence_seen},"
        f"{state.existing_evidence_settled}|"
        f"replacement={state.replacement_required_count},"
        f"{state.replacement_rows_created},"
        f"{state.original_rows_superseded},"
        f"{state.replacement_order_preserved},"
        f"{state.replacement_creation_failed},"
        f"{state.later_replay_skipped_after_failure}|"
        f"replay={state.replay_plan_complete}|"
        f"ambiguity={state.semantic_ambiguity_seen},"
        f"{state.pm_escalation_required}|"
        f"pm={state.pm_decision_requested},{state.pm_decision_returned}"
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

    complete_states = [state for state in seen if state.status == "complete"]
    blocked_states = [state for state in seen if state.status == "blocked"]
    targeted_success = [
        state
        for state in complete_states
        if state.trigger_source == "mid_run_fault"
        and state.targeted_replace_result == "success"
    ]
    heartbeat_success = [
        state
        for state in complete_states
        if state.trigger_source in {"heartbeat", "manual_resume"}
        and state.recovery_scope == "all_six"
    ]
    full_recycle_success = [
        state
        for state in complete_states
        if state.full_recycle_result == "success"
    ]
    environment_blocked = [
        state
        for state in blocked_states
        if state.full_recycle_result == "failed"
    ]
    mechanical_success = [
        state
        for state in complete_states
        if state.replay_plan_complete and not state.pm_decision_requested
    ]
    existing_evidence_success = [
        state
        for state in mechanical_success
        if state.existing_evidence_settled
    ]
    ordered_replay_success = [
        state
        for state in mechanical_success
        if state.replacement_required_count
        and state.replacement_rows_created == state.replacement_required_count
        and state.original_rows_superseded == state.replacement_required_count
        and state.replacement_order_preserved
    ]
    pm_escalation_success = [
        state
        for state in complete_states
        if state.pm_escalation_required and state.pm_decision_returned
    ]

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not invariant_failures
        and not missing_labels
        and bool(targeted_success)
        and bool(heartbeat_success)
        and bool(full_recycle_success)
        and bool(environment_blocked)
        and bool(mechanical_success)
        and bool(existing_evidence_success)
        and bool(ordered_replay_success)
        and bool(pm_escalation_success),
        "state_count": len(seen),
        "edge_count": edges,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": len(complete_states),
        "blocked_state_count": len(blocked_states),
        "targeted_success_count": len(targeted_success),
        "heartbeat_success_count": len(heartbeat_success),
        "full_recycle_success_count": len(full_recycle_success),
        "environment_blocked_count": len(environment_blocked),
        "mechanical_success_count": len(mechanical_success),
        "existing_evidence_success_count": len(existing_evidence_success),
        "ordered_replay_success_count": len(ordered_replay_success),
        "pm_escalation_success_count": len(pm_escalation_success),
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
            "production_conformance_replay": (
                "skipped_with_reason: this is a pre-implementation abstract "
                "recovery model; production replay is added after the router "
                "adapter changes exist"
            )
        },
    }
    RESULTS_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
