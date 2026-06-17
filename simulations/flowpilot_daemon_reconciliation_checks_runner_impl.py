"""Run checks for the FlowPilot daemon durable reconciliation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_daemon_reconciliation_model as model
from flowpilot_daemon_reconciliation_checks_projection import _live_run_projection


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_daemon_reconciliation_results.json"
STARTUP_RECONCILIATION_SOURCE = "startup_daemon_bootloader_postcondition"
STARTUP_BOOTLOADER_RECEIPT_SOURCE = "startup_bootloader_controller_receipt"
STARTUP_RECONCILIATION_SOURCES = (STARTUP_RECONCILIATION_SOURCE, STARTUP_BOOTLOADER_RECEIPT_SOURCE)
MISSING_POSTCONDITION_BLOCKER_SOURCE = "controller_action_receipt_missing_router_postcondition"
CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE = "router_owned_controller_boundary_confirmation_reclaim"
STARTUP_BLOCKER_RECONCILIATION_RESOLUTIONS = {
    "resolved_by_startup_reconciliation",
    "superseded_by_startup_reconciliation",
    "superseded_by_successful_startup_reconciliation",
}

REQUIRED_LABELS = (
    "daemon_tick_starts_durable_reconciliation_barrier",
    "role_output_submitted_while_router_waits",
    "manual_resume_opens_rehydrate_pending_action",
    "manual_resume_opens_rehydrate_pending_action_after_role_output",
    "role_output_submitted_while_rehydrate_pending",
    "controller_writes_complete_rehydrate_receipt",
    "controller_writes_incomplete_rehydrate_receipt",
    "controller_writes_blocked_rehydrate_receipt",
    "daemon_applies_complete_receipt_and_clears_pending",
    "startup_role_flags_written_to_secondary_record_only",
    "daemon_folds_startup_role_flags_from_secondary_record",
    "daemon_sees_transient_controller_action_temp_file",
    "daemon_skips_transient_controller_action_temp_file",
    "daemon_observes_active_runtime_writer",
    "foreground_start_observes_active_runtime_writer",
    "foreground_start_waits_for_active_runtime_writer",
    "foreground_start_retries_after_runtime_writer_finishes",
    "foreground_start_returns_live_daemon_status_after_settlement",
    "daemon_defers_reconciliation_for_active_runtime_writer",
    "daemon_observes_writer_progress_and_keeps_waiting",
    "runtime_writer_finishes_before_next_action",
    "daemon_reconciles_startup_bootloader_receipt_once",
    "daemon_folds_startup_receipt_with_single_owner",
    "startup_receipt_replay_is_noop",
    "daemon_reconciles_mail_delivery_receipt_to_packet_ledger",
    "daemon_blocks_unsupported_mail_delivery_receipt_before_next_action",
    "pm_mail_delivery_repair_decision_submitted",
    "daemon_consumes_pm_mail_delivery_decision_as_reissue",
    "card_bundle_ack_arrives_while_user_intake_waits",
    "daemon_reconciles_card_bundle_ack_wait_without_user_intake_release",
    "daemon_resolves_prior_startup_blocker_and_supersedes_pm_row",
    "controller_boundary_receipt_artifact_seen_with_stale_flags",
    "daemon_reclaims_controller_boundary_projection_from_artifact",
    "daemon_converts_incomplete_receipt_to_control_blocker",
    "daemon_surfaces_blocked_receipt_as_control_blocker",
    "daemon_reconciles_role_output_to_router_event",
    "daemon_idempotently_ignores_already_recorded_role_output",
    "daemon_computes_next_action_after_reconciliation",
    "daemon_returns_control_blocker_after_reconciliation",
    "daemon_queue_stops_at_barrier_and_sleeps",
    "daemon_queue_budget_exhausted_requests_immediate_tick",
    "daemon_queue_finds_no_action_and_sleeps",
    "terminal_stop_after_reconciliation_and_sleep_policy_checked",
)

HAZARD_EXPECTED_FAILURES = {
    "completed_controller_action_repeated": "daemon repeated a completed or blocked Controller action instead of clearing or blocking",
    "done_receipt_without_stateful_postconditions": "stateful Controller receipt was marked done without applying Router postconditions",
    "incomplete_stateful_receipt_silently_done": "incomplete stateful Controller receipt was accepted without a control blocker",
    "mail_delivery_receipt_without_packet_ledger_fold": "mail delivery postcondition was applied without moving the packet ledger and Router flag together",
    "mail_delivery_flag_without_packet_release": "mail delivery Router flag was set while the packet still belonged to Controller",
    "mail_delivery_pm_decision_left_unconsumed": "PM mail delivery repair decision stayed only in durable storage",
    "mail_delivery_reissue_without_repair_transaction": "mail delivery reissue was queued without a repair transaction",
    "card_bundle_ack_wait_row_left_open": "system-card bundle ACK resolved but its wait row stayed open",
    "card_bundle_ack_wait_action_scheduler_disagree": "system-card bundle ACK wait action and scheduler reconciliation disagreed",
    "card_bundle_ack_completion_status_not_normalized": "system-card bundle ACK completion was not normalized to resolved",
    "startup_user_intake_controller_owned": "startup user_intake was Controller-held instead of Router-owned startup material",
    "card_bundle_ack_queued_controller_delivery": "PM system-card ACK queued user_intake deliver_mail before startup activation",
    "card_bundle_ack_released_user_intake_before_activation": "PM system-card ACK released startup user_intake before startup activation",
    "card_bundle_ack_duplicate_user_intake_release": "PM system-card ACK released startup user_intake before startup activation",
    "card_bundle_ack_resolved_unrelated_action_loop": "Router repeated unrelated Controller work after PM ACK before startup fact review",
    "submitted_role_output_left_in_ledger": "submitted expected role output was left only in durable storage",
    "canonical_artifact_flag_not_synced": "canonical role-output artifact existed without synced Router event flag",
    "stale_snapshot_overwrites_role_output_event": "daemon saved a stale router_state snapshot over newer durable role output",
    "computed_from_pending_before_reconciliation": "daemon computed next action from stale pending_action before durable reconciliation",
    "startup_role_flags_left_in_secondary_record": "startup role flags stayed in secondary startup record without Router-state fold",
    "startup_roles_started_without_core_prompt_router_flag": "startup roles_started Router flag was synced without role_core_prompts_injected",
    "temp_controller_action_file_read_as_real_action": "daemon tried to read a transient Controller action temp file",
    "temp_controller_action_file_error_kills_daemon": "transient Controller action temp file race stopped the daemon",
    "active_runtime_writer_false_control_blocker": "active runtime writer was converted into a control blocker before settlement",
    "active_runtime_writer_stops_daemon": "active runtime writer stopped the daemon before settlement",
    "foreground_start_active_writer_fatal": "foreground start command failed on active runtime writer instead of waiting and retrying",
    "foreground_start_reports_before_writer_settles": "foreground start reported live daemon status before runtime writer settled",
    "startup_reconciled_action_false_pm_blocker": "startup bootloader row produced a control blocker after it was already reconciled",
    "startup_receipt_apply_split_requires_later_apply": "startup Controller receipt required a separate apply path to advance",
    "startup_receipt_apply_split_false_pm_blocker": "startup Controller receipt reached next action through split receipt/apply ownership",
    "startup_receipt_single_owner_incomplete_fold": "startup bootloader receipt single-owner fold did not update every durable projection",
    "startup_receipt_reconciled_by_daemon_postcondition_owner": "startup bootloader row was reconciled by the wrong owner",
    "startup_missing_postcondition_pm_lane_before_reissue": "startup bootloader missing postcondition was sent to PM before mechanical reissue budget was exhausted",
    "startup_blocker_not_resolved_after_success": "startup bootloader blocker stayed active after its postcondition was reconciled",
    "startup_reconciled_action_queued_pm_repair": "PM repair action was queued after startup bootloader postcondition reconciliation",
    "startup_unsupported_receipt_escalated_to_pm": "unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied",
    "native_startup_intake_receipt_unsupported": "native startup intake Controller receipt was unsupported despite a complete native UI payload",
    "startup_row_reconciled_without_postcondition": "startup bootloader row was reconciled without its postcondition",
    "startup_row_reconciled_by_wrong_owner": "startup bootloader row was reconciled by the wrong owner",
    "controller_boundary_reconciled_artifact_left_flags_false": "Controller boundary confirmation was reconciled but Router flags stayed false",
    "controller_boundary_reissued_after_reconciled_artifact": "Controller boundary confirmation was reissued after valid reconciled evidence",
    "controller_boundary_returned_without_pending_action": "Controller boundary action was exposed while pending_action was empty",
    "controller_boundary_action_scheduler_disagree": "Controller boundary action and scheduler reconciliation disagreed",
    "daemon_sleeps_after_queue_budget_exhausted": "daemon slept after queue budget exhaustion instead of starting the next tick immediately",
    "daemon_fast_loops_after_barrier": "daemon fast-looped after a real wait instead of sleeping",
    "daemon_fast_loops_after_no_action": "daemon fast-looped after a real wait instead of sleeping",
    "role_wait_not_cleared_after_event": "expected role wait remained current after Router recorded the role output",
    "duplicate_role_output_consumption": "role output durable evidence was consumed more than once",
    "blocked_receipt_repeated_instead_of_blocker": "daemon repeated a completed or blocked Controller action instead of clearing or blocking",
    "invalid_role_output_silently_accepted": "invalid or unauthorized role output was accepted as a Router event",
    "receipt_and_role_output_interleaving_starves_role_output": "submitted expected role output was left only in durable storage",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|daemon={state.daemon_alive}|"
        f"barrier={state.reconciliation_barrier_started}|"
        f"pending={state.pending_action_kind},{state.pending_action_status},"
        f"returned_again={state.pending_action_returned_again}|"
        f"compute={state.next_action_computed},before_reconcile={state.computed_before_reconciliation}|"
        f"receipt={state.controller_receipt_status},{state.controller_receipt_payload_quality},"
        f"class={state.controller_receipt_action_class},"
        f"reconciled={state.controller_receipt_reconciled},cleared={state.pending_cleared_after_receipt},"
        f"post={state.stateful_postconditions_applied},blocker={state.control_blocker_written}|"
        f"blocker_lane={state.control_blocker_lane},retry={state.control_blocker_direct_retry_budget},"
        f"resolved={state.control_blocker_resolved_by_reconciliation},"
        f"pm_action={state.pm_repair_action_queued},pm_superseded={state.pm_repair_action_superseded},"
        f"budget_exhausted={state.startup_reissue_budget_exhausted}|"
        f"startup={state.startup_row_reconciled},{state.startup_postcondition_satisfied},"
        f"owner={state.startup_reconciliation_owner},generic={state.generic_receipt_reconciler_touched_startup_row},"
        f"kind={state.startup_bootloader_receipt_kind},"
        f"unsupported={state.unsupported_startup_receipt_action},"
        f"secondary_roles={state.startup_secondary_record_roles_started},"
        f"secondary_prompts={state.startup_secondary_record_core_prompts_injected},"
        f"router_roles={state.startup_router_state_roles_started},"
        f"router_prompts={state.startup_router_state_core_prompts_injected},"
        f"dual_folded={state.startup_dual_ledger_folded}|"
        f"startup_receipt=split={state.startup_receipt_apply_split},"
        f"requires_apply={state.startup_receipt_requires_apply_to_advance},"
        f"single_owner={state.startup_receipt_single_owner_folded},"
        f"replay_noop={state.startup_receipt_replay_is_noop}|"
        f"mail={state.mail_delivery_receipt_claimed},{state.mail_delivery_postcondition_required},"
        f"applied={state.mail_delivery_postcondition_applied},ledger={state.mail_delivery_packet_ledger_folded},"
        f"released={state.mail_delivery_packet_released_to_role},flag={state.mail_delivery_router_flag_synced},"
        f"unsupported={state.mail_delivery_unsupported_receipt},pm_decision={state.pm_mail_repair_decision_submitted},"
        f"pm_consumed={state.pm_mail_repair_decision_consumed},repair_tx={state.mail_delivery_repair_transaction_started},"
        f"reissue={state.mail_delivery_reissue_queued}|"
        f"card_ack={state.startup_card_bundle_ack_resolved},"
        f"action_reconciled={state.startup_card_bundle_wait_action_reconciled},"
        f"scheduler_reconciled={state.startup_card_bundle_wait_scheduler_reconciled},"
        f"normalized={state.startup_card_bundle_ack_completion_normalized},"
        f"user_intake_router={state.user_intake_router_owned},"
        f"user_intake_controller={state.user_intake_packet_with_controller},"
        f"user_intake_pm={state.user_intake_packet_to_pm},"
        f"user_intake_released={state.user_intake_released_to_pm},"
        f"user_intake_release_count={state.user_intake_release_count},"
        f"user_intake_queued={state.user_intake_delivery_action_queued},"
        f"unrelated_loop={state.unrelated_controller_action_repeated_after_ack}|"
        f"boundary={state.controller_boundary_artifact_exists},{state.controller_boundary_artifact_valid},"
        f"action_reconciled={state.controller_boundary_action_reconciled},"
        f"scheduler_reconciled={state.controller_boundary_scheduler_reconciled},"
        f"flags={state.controller_boundary_flags_synced},"
        f"reissued={state.controller_boundary_reissued_after_reconcile},"
        f"without_pending={state.controller_boundary_action_returned_without_pending},"
        f"scan_temp={state.controller_action_directory_scan_includes_temp_json},"
        f"temp_seen={state.temp_controller_action_file_seen},"
        f"temp_renamed={state.temp_controller_action_file_renamed_before_read},"
        f"temp_read={state.temp_controller_action_file_read_attempted},"
        f"temp_skipped={state.temp_file_race_deferred_or_skipped},"
        f"temp_error={state.daemon_error_from_temp_action_file},"
        f"writer_active={state.runtime_writer_active},"
        f"writer_stalled={state.runtime_writer_stalled},"
        f"settlement_waiting={state.runtime_settlement_waiting},"
        f"settlement_progress={state.runtime_settlement_progress_observed}|"
        f"fg_start=active={state.foreground_start_command_active},"
        f"read_during_writer={state.foreground_start_reads_runtime_during_writer},"
        f"waited={state.foreground_start_waits_for_runtime_writer},"
        f"retried={state.foreground_start_retries_after_writer_finishes},"
        f"returned_live={state.foreground_start_returns_live_daemon_status},"
        f"fatal={state.foreground_start_fatal_from_active_writer}|"
        f"queue={state.queue_stop_reason},sleep={state.sleep_taken},"
        f"immediate={state.immediate_tick_requested}|"
        f"role_output={state.role_output_ledger_submitted},valid={state.role_output_envelope_valid},"
        f"expected={state.role_output_event_expected},artifact={state.canonical_artifact_exists},"
        f"reconciled={state.role_output_reconciled},event={state.router_event_recorded},"
        f"flag={state.router_event_flag_synced},scoped={state.scoped_event_recorded},"
        f"count={state.role_output_consumption_count},wait_cleared={state.role_wait_cleared_after_event}|"
        f"stale={state.stale_daemon_snapshot_loaded},{state.stale_snapshot_saved_after_external_event}|"
        f"invalid_accept={state.invalid_role_output_accepted}"
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


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    labels = set(graph["labels"])
    terminal_states = [state for state in states if model.is_terminal(state)]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(terminal_states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if idx not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
    return {"ok": ok, "hazards": hazards}
















TERMINAL_ACTION_STATES = {"done", "reconciled", "resolved", "superseded", "cancelled", "skipped"}
TERMINAL_ROUTER_ROW_STATES = {"reconciled", "resolved", "superseded", "cancelled", "skipped"}
ACK_COMPLETE_STATUSES = {"resolved", "acknowledged"}











def run_checks(*, json_out_requested: bool = False, skip_live_projection: bool = False) -> dict[str, object]:
    graph = _build_graph()
    safe = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _run_flowguard_explorer()
    hazards = _hazard_report()
    if skip_live_projection:
        live_run_projection: dict[str, object] = {
            "ok": True,
            "classification_ok": False,
            "skipped": True,
            "skip_reason": "model_only_preimplementation_gate",
        }
    else:
        live_run_projection = _live_run_projection()
    skipped_checks: dict[str, str] = {}
    if live_run_projection.get("skipped"):
        skipped_checks["live_run_projection"] = f"skipped_with_reason: {live_run_projection.get('skip_reason')}"
    if not json_out_requested:
        skipped_checks["default_results_file"] = (
            "skipped_with_reason: no --json-out path was provided"
        )
    return {
        "ok": bool(safe["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(live_run_projection["ok"]),
        "safe_graph": safe,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "live_run_projection": live_run_projection,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument(
        "--skip-live-projection",
        action="store_true",
        help="run only the abstract model/hazard gate without auditing the current runtime",
    )
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out), skip_live_projection=args.skip_live_projection)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
