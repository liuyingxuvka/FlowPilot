"""Run checks for the FlowPilot two-table async scheduler model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_two_table_async_scheduler_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_two_table_async_scheduler_results.json"

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.CONTROLLER_OWNS_ROUTER_DEPENDENCIES: "Controller table owns Router dependency metadata",
    model.DAEMON_DUPLICATES_CONTROLLER_ROW_ON_RETRY: "daemon retry duplicated Controller row without deterministic idempotency",
    model.REVIEWER_STARTS_BEFORE_STARTUP_SCOPE_CLEAN: "Reviewer startup fact review started before startup current-scope reconciliation was clean",
    model.DAEMON_ENQUEUES_PAST_BARRIER: "Router daemon enqueued work after a barrier",
    model.PM_ACTIVATION_REQUIRES_SECOND_GLOBAL_JOIN: "PM startup activation required redundant all-startup ACK join",
    model.STATEFUL_RECEIPT_CLEARED_WITHOUT_POSTCONDITION: "Router reconciled stateful receipt without Router-visible postcondition evidence",
    model.LIVE_WAIT_WITH_EMPTY_CONTROLLER_PLAN: "live daemon wait exposed an empty Controller plan instead of a continuous standby row",
    model.PASSIVE_WAIT_WRITTEN_AS_CONTROLLER_WORK: "passive wait status was written as ordinary Controller work",
    model.PASSIVE_WAIT_HIDES_ROUTER_LOCAL_OBLIGATION: "passive wait hid a Router-local obligation that should have preempted waiting",
    model.STANDBY_WITHOUT_WAIT_TARGET_STATUS: "passive wait status was not projected into Router monitor status",
    model.CONTROLLER_LEDGER_PROMPT_MISSING_TOP_DOWN: "Controller action ledger lacks table-local top-to-bottom prompt coverage",
    model.FLOWPILOT_RUNNING_FOREGROUND_CLOSURE_ALLOWED: "foreground Controller closure was allowed while FlowPilot was still running",
    model.STANDBY_COMPLETES_AFTER_ONE_CHECK: "continuous standby row was completed after one monitor check",
    model.STANDBY_TIMEOUT_TREATED_AS_COMPLETION: "timeout_still_waiting was treated as standby completion",
    model.STANDBY_NEW_WORK_IGNORED: "continuous standby ignored new Controller work instead of returning to top-to-bottom row processing",
    model.NO_OUTPUT_WAIT_TRIGGERS_ROLE_RECOVERY: "no-output wait requested role recovery before bounded same-work reissue",
    model.NO_OUTPUT_REISSUE_WITHOUT_SUPERSEDE: "no-output replacement was not durable before continuation",
    model.UNAVAILABLE_WAIT_REISSUED_INSTEAD_OF_RECOVERY: "unavailable role did not enter role recovery",
    model.STARTUP_UI_BEFORE_DAEMON: "startup external actions ran before Router daemon became the startup driver",
    model.STARTUP_ROLES_OR_HEARTBEAT_BEFORE_DAEMON: "startup external actions ran before Router daemon became the startup driver",
    model.DAEMON_WAITS_FOR_CONTROLLER_CORE_DURING_STARTUP: "Router daemon waited for Controller core instead of driving startup work",
    model.ROUTER_SCHEDULER_LEDGER_PARTIAL_WRITE: "Router scheduler ledger was not valid JSON after daemon table write",
    model.CONTROLLER_ACTION_LEDGER_PARTIAL_WRITE: "Controller action ledger was not valid JSON after Controller table write",
    model.ROUTER_SCHEDULER_LEDGER_MULTI_WRITER: "Router scheduler ledger had more than one writer",
    model.FRESH_SCHEDULER_WRITE_LOCK_REPORTED_CORRUPT: "fresh Router scheduler ledger write lock was not deferred to the next tick",
    model.STARTUP_BOOTLOADER_RECEIPT_LEAVES_STALE_PENDING_ACTION: (
        "daemon consumed startup Controller receipt without syncing bootstrap flag, pending action, and Router row"
    ),
    model.STARTUP_BANNER_DISPLAY_GLOBAL_BARRIER: "startup parallel obligation blocked unrelated startup queueing",
    model.STARTUP_HEARTBEAT_GLOBAL_BARRIER: "startup parallel obligation blocked unrelated startup queueing",
    model.STARTUP_ROLE_SPAWN_GLOBAL_BARRIER: "startup role-slot dependency blocked unrelated startup queueing",
    model.STARTUP_OBLIGATION_BEFORE_CONTROLLER_CORE: (
        "Controller-ledger startup obligation was exposed before Controller core loaded"
    ),
    model.ROLE_DEPENDENT_WORK_BEFORE_ROLE_SLOTS_READY: (
        "role-dependent startup work was queued before role slots were ready"
    ),
    model.REVIEWER_STARTS_BEFORE_PARALLEL_STARTUP_OBLIGATIONS_CLEAN: (
        "Reviewer startup fact review started before startup parallel obligations were reconciled"
    ),
    model.TRUE_BARRIER_DEMOTED_TO_PARALLEL: "Router daemon continued queueing after a true barrier",
    model.DUPLICATE_STARTUP_PARALLEL_OBLIGATION_ROW: (
        "daemon retry duplicated a startup parallel obligation row without open-row skip"
    ),
    model.STARTUP_OBLIGATION_RECONCILED_WITHOUT_ROUTER_PROOF: (
        "startup obligation was reconciled without Router-visible proof"
    ),
    model.SCHEDULER_RECONCILED_ROW_DOWNGRADED: (
        "Router scheduler row reconciliation status was downgraded after receipt sync"
    ),
    model.SINGLE_CARD_ACK_WAIT_STALE_AFTER_RETURN_RESOLUTION: (
        "Controller passive wait stayed waiting after single-card ACK return resolved"
    ),
    model.SINGLE_CARD_ACK_SCHEDULER_STALE_AFTER_RETURN_RESOLUTION: (
        "Router scheduler row stayed waiting after single-card ACK return resolved"
    ),
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|daemon={state.daemon_started},"
        f"{state.daemon_tick_seconds}|tables={state.router_scheduler_table_exists},"
        f"{state.controller_action_table_exists},valid_json={state.router_scheduler_ledger_valid_json},"
        f"{state.controller_action_ledger_valid_json},write_lock_fresh={state.router_scheduler_write_lock_fresh},"
        f"deferred={state.daemon_deferred_for_fresh_write_lock},atomic={state.ledger_writes_atomic},"
        f"scheduler_single_writer={state.router_scheduler_single_writer},"
        f"router_meta={state.router_table_has_dependency_metadata},"
        f"controller_graph={state.controller_table_has_router_dependency_graph}|"
        f"prompt={state.controller_table_prompt_present},{state.controller_table_prompt_before_actions},"
        f"{state.controller_table_prompt_top_down_order},{state.controller_table_prompt_receipt_duty},"
        f"{state.controller_table_prompt_foreground_while_running},{state.controller_table_prompt_authority_limits}|"
        f"startup_driver={state.minimal_run_shell_created},{state.daemon_first_driver_before_external_startup_actions},"
        f"ui_before_daemon={state.startup_ui_opened_before_daemon},roles_before_daemon={state.startup_roles_started_before_daemon},"
        f"heartbeat_before_daemon={state.startup_heartbeat_bound_before_daemon},"
        f"daemon_drives_pre_core={state.daemon_drives_startup_before_controller_core},"
        f"daemon_waits_pre_core={state.daemon_waits_for_controller_core_without_startup_drive},"
        f"controller_core={state.controller_core_loaded},"
        f"bootstrap_pending={state.startup_bootstrap_pending_action_open},"
        f"bootstrap_flag={state.startup_bootstrap_flag_current},"
        f"startup_receipt={state.startup_controller_receipt_done},"
        f"startup_receipt_processed={state.startup_daemon_processed_done_receipt},"
        f"startup_router_row_reconciled={state.startup_router_row_reconciled},"
        f"startup_next_after_receipt={state.startup_next_row_scheduled_after_receipt},"
        f"startup_barrier_after_receipt={state.startup_real_barrier_reached_after_receipt},"
        f"startup_reissued_done={state.startup_same_action_reissued_after_done_receipt}|"
        f"startup_obligation=open:{state.startup_parallel_obligation_open},"
        f"proof:{state.startup_parallel_obligation_proof_written},"
        f"reconciled:{state.startup_parallel_obligation_reconciled},"
        f"clean:{state.startup_parallel_obligations_clean},"
        f"blocked_unrelated:{state.startup_parallel_obligation_blocked_unrelated_queue},"
        f"heartbeat_open:{state.startup_heartbeat_obligation_open}|"
        f"role_slots=open:{state.startup_role_slots_open},ready:{state.startup_role_slots_ready},"
        f"blocked_unrelated:{state.startup_role_slots_blocked_unrelated_queue},"
        f"role_independent:{state.role_independent_work_enqueued},"
        f"role_dependent:{state.role_dependent_work_enqueued}|"
        f"unrelated_startup=available:{state.unrelated_startup_work_available},"
        f"enqueued:{state.unrelated_startup_work_enqueued}|"
        f"true_barrier={state.current_action_true_barrier},"
        f"continued_after_true_barrier={state.queue_continued_after_true_barrier},"
        f"dup_parallel_rows={state.duplicate_startup_parallel_obligation_rows},"
        f"scheduler_row_reconciled={state.scheduler_row_status_reconciled},"
        f"scheduler_row_downgraded={state.scheduler_row_status_downgraded_to_receipt_done}|"
        f"queue={state.independent_controller_row_pending},{state.independent_row_enqueued},"
        f"{state.next_independent_row_enqueued},barrier={state.barrier_active},"
        f"after_barrier={state.enqueued_after_barrier}|idempotency={state.idempotency_key_used},"
        f"duplicate={state.duplicate_controller_row_created}|receipt={state.receipt_done},"
        f"stateful={state.stateful_postcondition_required},post={state.router_visible_postcondition_written},"
        f"reconciled={state.router_marked_row_reconciled}|startup={state.startup_local_rows_clean},"
        f"{state.startup_prep_cards_sent},{state.startup_prep_acks_clean},"
        f"{state.startup_scope_reconciliation_checked},{state.startup_scope_reconciliation_clean},"
        f"review={state.reviewer_startup_fact_review_started}|pm={state.reviewer_fact_report_recorded},"
        f"{state.pm_startup_activation_card_sent},{state.pm_startup_activation_ack_clean},"
        f"single_ack={state.single_card_ack_return_resolved},"
        f"{state.single_card_controller_wait_row_reconciled},{state.single_card_scheduler_row_reconciled},"
        f"{state.single_card_wait_still_waiting_after_return_resolution},"
        f"{state.single_card_scheduler_still_waiting_after_return_resolution},"
        f"decision={state.pm_activation_decision_accepted},second_join={state.pm_activation_second_global_join_required},"
        f"route={state.route_work_started}|running={state.flowpilot_still_running},{state.running_wait_state_kind}|"
        f"passive_wait={state.passive_wait_status_present},"
        f"ordinary_row={state.passive_wait_written_as_ordinary_controller_row},"
        f"monitor={state.passive_wait_metadata_in_monitor},"
        f"local_obligation={state.router_local_obligation_available},"
        f"hidden_by_wait={state.router_local_obligation_hidden_by_passive_wait}|"
        f"standby={state.live_wait_without_ordinary_controller_row},"
        f"row={state.continuous_standby_row_present},stable={state.standby_row_stable_idempotency},"
        f"names_wait={state.standby_row_names_wait_target},plan_sync={state.standby_codex_plan_sync_required},"
        f"plan_progress={state.standby_codex_plan_item_in_progress},strict_wait={state.standby_strict_monitor_wait_policy},"
        f"one_check_done={state.standby_completed_after_one_check},timeout_done={state.standby_timeout_still_waiting_treated_as_completion},"
        f"closure_allowed={state.foreground_closure_allowed_while_running},"
        f"foreground_stopped={state.foreground_controller_stopped_during_standby},"
        f"new_work={state.new_controller_work_exposed_during_standby},"
        f"ledger_update={state.standby_updates_ledger_on_new_work},"
        f"top_down_return={state.standby_returns_to_top_down_row_processing}|"
        f"wait_status={state.wait_target_status},no_output_reissue={state.no_output_reissue_created},"
        f"budget_exhausted={state.no_output_retry_budget_exhausted},"
        f"pm_escalation={state.no_output_pm_escalation_recorded},"
        f"replacement_durable={state.no_output_replacement_wait_durable},"
        f"original_superseded={state.no_output_original_wait_superseded},"
        f"role_recovery={state.role_recovery_requested}|reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
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

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.scheduler_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(flowguard["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
        "model_boundary": (
            "focused Router scheduler/Controller table/startup gate model; "
            "runtime tests remain required; heavyweight meta/capability checks intentionally skipped"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
