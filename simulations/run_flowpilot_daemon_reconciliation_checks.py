"""Run checks for the FlowPilot daemon durable reconciliation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_daemon_reconciliation_model as model


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
    "heartbeat_opens_rehydrate_pending_action",
    "heartbeat_opens_rehydrate_pending_action_after_role_output",
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
    "daemon_reconciles_card_bundle_ack_wait_and_releases_user_intake",
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
    "card_bundle_ack_resolved_user_intake_not_dispatched": "PM system-card ACK resolved while Router-owned user_intake was not released to PM",
    "startup_user_intake_controller_owned": "startup user_intake was Controller-held instead of Router-owned startup material",
    "card_bundle_ack_queued_controller_delivery": "PM system-card ACK queued a Controller deliver_mail row instead of Router release",
    "card_bundle_ack_duplicate_user_intake_release": "Router released startup user_intake more than once",
    "card_bundle_ack_resolved_unrelated_action_loop": "PM system-card ACK resolved while Router-owned user_intake was not released to PM",
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _router_daemon_events(run_root: Path) -> list[dict[str, Any]]:
    return _iter_jsonl(run_root / "runtime" / "router_daemon_events.jsonl")


def _event_details(event: dict[str, Any]) -> dict[str, Any]:
    details = event.get("details")
    return details if isinstance(details, dict) else {}


def _startup_dual_ledger_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    startup_state_path = run_root / "bootstrap" / "startup_state.json"
    router_state_path = run_root / "runtime" / "router_state.json"
    startup_state = _read_json(startup_state_path) if startup_state_path.exists() else {}
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}

    startup_roles = bool(startup_state.get("roles_started"))
    startup_prompts = bool(startup_state.get("role_core_prompts_injected"))
    router_roles = bool(router_state.get("roles_started"))
    router_prompts = bool(router_state.get("role_core_prompts_injected"))
    if (startup_roles or startup_prompts) and not (router_roles and router_prompts):
        findings.append(
            {
                "id": "startup_role_flags_left_in_secondary_record",
                "startup_roles_started": startup_roles,
                "startup_role_core_prompts_injected": startup_prompts,
                "router_roles_started": router_roles,
                "router_role_core_prompts_injected": router_prompts,
            }
        )
    if router_roles and not router_prompts:
        findings.append(
            {
                "id": "startup_roles_started_without_core_prompt_router_flag",
                "router_roles_started": router_roles,
                "router_role_core_prompts_injected": router_prompts,
            }
        )

    for event in _router_daemon_events(run_root):
        if event.get("event") != "router_daemon_lock_released":
            continue
        details = _event_details(event)
        reason = str(event.get("reason") or details.get("reason") or "")
        if "start_role_flags_not_folded" not in reason:
            continue
        findings.append(
            {
                "id": "startup_role_flag_fold_required_manual_daemon_restart",
                "reason": reason,
                "time": event.get("time") or event.get("recorded_at"),
            }
        )
    return findings


def _temp_action_file_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for event in _router_daemon_events(run_root):
        if event.get("event") != "router_daemon_error":
            continue
        details = _event_details(event)
        error_type = event.get("error_type") or details.get("error_type")
        error_message = str(
            event.get("error_message")
            or details.get("error_message")
            or event.get("error")
            or details.get("error")
            or ""
        )
        normalized = error_message.replace("\\", "/")
        if (
            error_type == "FileNotFoundError"
            and "controller_actions" in normalized
            and ".tmp-" in normalized
            and ".json" in normalized
        ):
            findings.append(
                {
                    "id": "temp_controller_action_file_race_stopped_daemon",
                    "error_type": error_type,
                    "error_message": error_message,
                    "time": event.get("time") or event.get("recorded_at"),
                }
            )
    return findings


def _runtime_write_lock_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    runtime_dir = run_root / "runtime"
    if not runtime_dir.exists():
        return findings
    needles = (
        "runtime ledger write is still in progress",
        "fresh runtime JSON write lock",
        "runtime JSON write lock",
    )
    candidates: list[Path] = []
    for pattern in ("*.err.txt", "*.out.txt", "*.combined.txt", "*.log"):
        candidates.extend(sorted(runtime_dir.glob(pattern)))
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            normalized = line.lower()
            if not any(needle.lower() in normalized for needle in needles):
                continue
            findings.append(
                {
                    "id": "foreground_start_failed_on_fresh_runtime_writer",
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "line": line_no,
                    "message": line.strip()[:500],
                }
            )
            return findings
    return findings


def _resolve_current_run_root() -> tuple[Path | None, str]:
    current_path = PROJECT_ROOT / ".flowpilot" / "current.json"
    if not current_path.exists():
        return None, "no .flowpilot/current.json found"
    current = _read_json(current_path)
    run_root_text = current.get("current_run_root")
    if not isinstance(run_root_text, str) or not run_root_text:
        return None, ".flowpilot/current.json has no current_run_root"
    run_root = PROJECT_ROOT / run_root_text
    if not run_root.exists():
        return None, f"current run root does not exist: {run_root_text}"
    return run_root, ""


def _action_is_startup_bootloader(action: dict[str, Any]) -> bool:
    nested = action.get("action") if isinstance(action.get("action"), dict) else {}
    return bool(
        action.get("scope_kind") == "startup"
        and (
            nested.get("startup_daemon_scheduled") is True
            or nested.get("startup_daemon_scheduler_source")
        )
    )


def _startup_reconciliation_satisfied(
    action: dict[str, Any],
    row_by_id: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, Any] | None]:
    action_reconciliation = action.get("router_reconciliation")
    if not isinstance(action_reconciliation, dict):
        action_reconciliation = {}
    row = row_by_id.get(str(action.get("router_scheduler_row_id")))
    row_reconciliation = row.get("reconciliation", {}) if row else {}
    if not isinstance(row_reconciliation, dict):
        row_reconciliation = {}

    action_source = action_reconciliation.get("source")
    row_source = row_reconciliation.get("source")
    action_satisfied = bool(
        action.get("status") == "done"
        and action.get("router_reconciliation_status") == "reconciled"
        and (
            (
                action_source == STARTUP_RECONCILIATION_SOURCE
                and action_reconciliation.get("bootstrap_flag_satisfied") is True
            )
            or (
                action_source == STARTUP_BOOTLOADER_RECEIPT_SOURCE
                and action_reconciliation.get("applied") is True
                and bool(action_reconciliation.get("postcondition"))
            )
        )
    )
    row_satisfied = bool(
        row
        and row.get("router_state") == "reconciled"
        and (
            (
                row_source == STARTUP_RECONCILIATION_SOURCE
                and row_reconciliation.get("bootstrap_flag_satisfied") is True
            )
            or (
                row_source == STARTUP_BOOTLOADER_RECEIPT_SOURCE
                and row_reconciliation.get("applied") is True
                and bool(row_reconciliation.get("postcondition"))
            )
        )
    )
    return action_satisfied or row_satisfied, row


def _controller_boundary_artifact_status(run_root: Path) -> dict[str, Any]:
    path = run_root / "startup" / "controller_boundary_confirmation.json"
    if not path.exists():
        return {"valid": False, "exists": False, "path": str(path.relative_to(PROJECT_ROOT))}
    try:
        payload = _read_json(path)
    except Exception as exc:  # pragma: no cover - defensive live-run audit
        return {
            "valid": False,
            "exists": True,
            "path": str(path.relative_to(PROJECT_ROOT)),
            "read_error": str(exc),
        }
    valid = bool(
        payload.get("schema_version") == "flowpilot.controller_boundary_confirmation.v1"
        and payload.get("router_owned_confirmation") is True
        and payload.get("event") == "controller_role_confirmed_from_router_core"
    )
    return {
        "valid": valid,
        "exists": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "schema_version": payload.get("schema_version"),
        "event": payload.get("event"),
        "router_owned_confirmation": payload.get("router_owned_confirmation"),
        "controller_action_id": payload.get("controller_action_id"),
    }


def _controller_boundary_receipt_status(run_root: Path, action: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    rel_path = action.get("receipt_path") or action.get("expected_receipt_path")
    if not rel_path and row:
        rel_path = row.get("controller_receipt_path")
    if not rel_path:
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        rel_path = nested.get("controller_receipt_path")
    if not isinstance(rel_path, str) or not rel_path:
        return {"done": False, "path": None}
    receipt_path = PROJECT_ROOT / rel_path
    if not receipt_path.exists():
        receipt_path = run_root / Path(rel_path).name
    if not receipt_path.exists():
        return {"done": False, "path": rel_path, "exists": False}
    try:
        receipt = _read_json(receipt_path)
    except Exception as exc:  # pragma: no cover - defensive live-run audit
        return {"done": False, "path": rel_path, "exists": True, "read_error": str(exc)}
    return {
        "done": receipt.get("status") == "done",
        "path": rel_path,
        "exists": True,
        "status": receipt.get("status"),
        "recorded_at": receipt.get("recorded_at"),
    }


def _controller_boundary_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    router_state_path = run_root / "router_state.json"
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    boundary_flags_synced = bool(
        flags.get("controller_boundary_confirmation_written") is True
        and flags.get("controller_role_confirmed") is True
        and flags.get("controller_role_confirmed_from_router_core") is True
    )
    artifact = _controller_boundary_artifact_status(run_root)
    history = router_state.get("history") if isinstance(router_state.get("history"), list) else []
    boundary_next_events = [
        item for item in history
        if isinstance(item, dict)
        and item.get("label") == "router_computed_next_controller_action"
        and isinstance(item.get("details"), dict)
        and item["details"].get("action_type") == "confirm_controller_core_boundary"
    ]
    pending_empty = router_state.get("pending_action") is None

    for action in actions:
        if action.get("action_type") != "confirm_controller_core_boundary":
            continue
        row = row_by_id.get(str(action.get("router_scheduler_row_id")))
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        row_reconciliation = row.get("reconciliation", {}) if row else {}
        if not isinstance(row_reconciliation, dict):
            row_reconciliation = {}
        receipt = _controller_boundary_receipt_status(run_root, action, row)
        action_reconciled = bool(
            action.get("status") == "done"
            and action.get("router_reconciliation_status") == "reconciled"
            and action_reconciliation.get("source") == CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE
        )
        row_reconciled = bool(
            row
            and row.get("router_state") == "reconciled"
            and row_reconciliation.get("source") == CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE
        )
        evidence = {
            "action_id": action.get("action_id"),
            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
            "action_reconciled": action_reconciled,
            "scheduler_reconciled": row_reconciled,
            "receipt": receipt,
            "artifact": artifact,
            "flags": {
                "controller_boundary_confirmation_written": flags.get("controller_boundary_confirmation_written"),
                "controller_role_confirmed": flags.get("controller_role_confirmed"),
                "controller_role_confirmed_from_router_core": flags.get("controller_role_confirmed_from_router_core"),
            },
        }
        if artifact.get("valid") and receipt.get("done") and action_reconciled != row_reconciled:
            findings.append(
                {
                    "id": "controller_boundary_action_scheduler_disagree",
                    "action_type": "confirm_controller_core_boundary",
                    **evidence,
                }
            )
        if artifact.get("valid") and receipt.get("done") and action_reconciled and row_reconciled and not boundary_flags_synced:
            findings.append(
                {
                    "id": "controller_boundary_reconciled_artifact_left_flags_false",
                    "action_type": "confirm_controller_core_boundary",
                    **evidence,
                }
            )
            nested = action.get("action") if isinstance(action.get("action"), dict) else {}
            if boundary_next_events:
                findings.append(
                    {
                        "id": "controller_boundary_reissued_after_reconciled_artifact",
                        "action_type": "confirm_controller_core_boundary",
                        "latest_computed_at": boundary_next_events[-1].get("at"),
                        "action_created_at": nested.get("created_at") or action.get("created_at"),
                        **evidence,
                    }
                )
            if pending_empty and boundary_next_events:
                findings.append(
                    {
                        "id": "controller_boundary_action_returned_without_pending_action",
                        "action_type": "confirm_controller_core_boundary",
                        "latest_computed_at": boundary_next_events[-1].get("at"),
                        **evidence,
                    }
                )
    return findings


def _mail_delivery_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    router_state_path = run_root / "router_state.json"
    packet_ledger_path = run_root / "packet_ledger.json"
    role_output_ledger_path = run_root / "role_output_ledger.json"
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}
    packet_ledger = _read_json(packet_ledger_path) if packet_ledger_path.exists() else {}
    role_output_ledger = _read_json(role_output_ledger_path) if role_output_ledger_path.exists() else {}
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    mail_entries = packet_ledger.get("mail") if isinstance(packet_ledger.get("mail"), list) else []
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    role_outputs = role_output_ledger.get("outputs") if isinstance(role_output_ledger.get("outputs"), list) else []

    repair_decisions_by_blocker: dict[str, list[dict[str, Any]]] = {}
    for output in role_outputs:
        if not isinstance(output, dict):
            continue
        if output.get("output_type") != "pm_control_blocker_repair_decision":
            continue
        body_path = output.get("body_path")
        if not isinstance(body_path, str):
            continue
        path = PROJECT_ROOT / body_path
        if not path.exists():
            continue
        try:
            decision = _read_json(path)
        except Exception:  # pragma: no cover - defensive live-run audit
            continue
        blocker_id = str(decision.get("blocker_id") or "")
        if blocker_id:
            repair_decisions_by_blocker.setdefault(blocker_id, []).append(
                {
                    "body_path": body_path,
                    "decision": decision.get("decision"),
                    "recovery_option": decision.get("recovery_option"),
                    "return_gate": decision.get("return_gate"),
                    "rerun_target": decision.get("rerun_target"),
                }
            )

    action_by_id = {str(action.get("action_id")): action for action in actions if action.get("action_id")}
    for action in actions:
        if action.get("action_type") != "deliver_mail":
            continue
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        mail_id = str(action.get("mail_id") or nested.get("mail_id") or "")
        to_role = str(action.get("to_role") or nested.get("to_role") or "")
        completion = action.get("completion_class") if isinstance(action.get("completion_class"), dict) else {}
        postcondition = str(
            completion.get("postcondition")
            or action.get("postcondition")
            or nested.get("postcondition")
            or ""
        )
        row = row_by_id.get(str(action.get("router_scheduler_row_id")))
        row_reconciliation = row.get("reconciliation", {}) if row else {}
        if not isinstance(row_reconciliation, dict):
            row_reconciliation = {}
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        receipt = _controller_boundary_receipt_status(run_root, action, row)
        mail_folded = any(
            isinstance(entry, dict)
            and str(entry.get("mail_id") or "") == mail_id
            and (not to_role or str(entry.get("to_role") or "") == to_role)
            for entry in mail_entries
        )
        flag_synced = bool(postcondition and flags.get(postcondition) is True)
        packet = next(
            (
                item for item in packets
                if isinstance(item, dict) and str(item.get("packet_id") or "") == mail_id
            ),
            {},
        )
        action_done = action.get("status") == "done"
        action_blocked = action.get("router_reconciliation_status") == "blocked"
        action_reconciled = action.get("router_reconciliation_status") == "reconciled"
        row_state = row.get("router_state") if row else None
        apply_result = action_reconciliation.get("apply_result")
        if not isinstance(apply_result, dict):
            apply_result = {}
        nested_apply = apply_result.get("apply_result")
        if not isinstance(nested_apply, dict):
            nested_apply = {}
        unsupported_reason = (
            nested_apply.get("reason") == "unsupported_stateful_controller_receipt"
            or apply_result.get("reason") == "unsupported_stateful_controller_receipt"
        )
        evidence = {
            "action_id": action.get("action_id"),
            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
            "row_state": row_state,
            "receipt": receipt,
            "mail_id": mail_id,
            "to_role": to_role,
            "postcondition": postcondition,
            "mail_folded": mail_folded,
            "flag_synced": flag_synced,
            "packet_holder": packet.get("active_packet_holder"),
            "packet_status": packet.get("active_packet_status"),
            "router_reconciliation_status": action.get("router_reconciliation_status"),
            "router_reconciliation_reason": action_reconciliation.get("reason"),
            "router_reconciliation_apply_reason": nested_apply.get("reason") or apply_result.get("reason"),
        }
        if action_done and receipt.get("done") and action_blocked and unsupported_reason:
            findings.append(
                {
                    "id": "mail_delivery_receipt_unfolded_to_packet_ledger",
                    "action_type": "deliver_mail",
                    **evidence,
                }
            )
        if action_reconciled and (not mail_folded or not flag_synced):
            findings.append(
                {
                    "id": "mail_delivery_reconciled_without_packet_ledger_fold",
                    "action_type": "deliver_mail",
                    **evidence,
                }
            )

    control_block_dir = run_root / "control_blocks"
    if control_block_dir.exists():
        repair_transactions = router_state.get("repair_transactions")
        repair_transaction_count = len(repair_transactions) if isinstance(repair_transactions, list) else 0
        active_repair_transaction = router_state.get("active_repair_transaction")
        flags_pm_decision = bool(flags.get("pm_control_blocker_repair_decision_recorded") is True)
        for path in sorted(control_block_dir.glob("*.json")):
            if path.name.endswith(".sealed_repair_packet.json") or path.name == "blocker_repair_policy_snapshot.json":
                continue
            blocker = _read_json(path)
            if blocker.get("source") != MISSING_POSTCONDITION_BLOCKER_SOURCE:
                continue
            if blocker.get("originating_action_type") != "deliver_mail":
                continue
            blocker_id = str(blocker.get("blocker_id") or "")
            decisions = repair_decisions_by_blocker.get(blocker_id, [])
            if decisions and not flags_pm_decision and not active_repair_transaction and repair_transaction_count == 0:
                origin_action = action_by_id.get(str(blocker.get("originating_controller_action_id") or ""))
                findings.append(
                    {
                        "id": "mail_delivery_pm_repair_decision_unconsumed",
                        "action_type": "deliver_mail",
                        "blocker_id": blocker_id,
                        "originating_controller_action_id": blocker.get("originating_controller_action_id"),
                        "originating_postcondition": blocker.get("originating_postcondition"),
                        "handling_lane": blocker.get("handling_lane"),
                        "direct_retry_attempts_used": blocker.get("direct_retry_attempts_used"),
                        "direct_retry_budget": blocker.get("direct_retry_budget"),
                        "direct_retry_budget_exhausted": blocker.get("direct_retry_budget_exhausted"),
                        "pm_decisions": decisions,
                        "pm_decision_flag": flags.get("pm_control_blocker_repair_decision_recorded"),
                        "active_repair_transaction": active_repair_transaction,
                        "repair_transaction_count": repair_transaction_count,
                        "origin_action_reconciliation_status": origin_action.get("router_reconciliation_status") if origin_action else None,
                    }
                )

    return findings


TERMINAL_ACTION_STATES = {"done", "reconciled", "resolved", "superseded", "cancelled", "skipped"}
TERMINAL_ROUTER_ROW_STATES = {"reconciled", "resolved", "superseded", "cancelled", "skipped"}
ACK_COMPLETE_STATUSES = {"resolved", "acknowledged"}


def _bundle_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("card_bundle_id") or ""),
        str(record.get("expected_return_path") or record.get("ack_path") or ""),
        str(record.get("card_return_event") or ""),
    )


def _record_matches_bundle(record: dict[str, Any], bundle_id: str, expected_return_path: str, event: str) -> bool:
    nested = record.get("action") if isinstance(record.get("action"), dict) else {}
    record_bundle = str(record.get("card_bundle_id") or nested.get("card_bundle_id") or "")
    record_return = str(record.get("expected_return_path") or nested.get("expected_return_path") or "")
    record_event = str(record.get("card_return_event") or nested.get("card_return_event") or "")
    return bool(
        (bundle_id and record_bundle == bundle_id)
        or (expected_return_path and record_return == expected_return_path)
        or (event and record_event == event and (record_bundle or record_return))
    )


def _user_intake_packet_summary(packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("packet_id") != "user_intake":
            continue
        envelope = packet.get("packet_envelope") if isinstance(packet.get("packet_envelope"), dict) else {}
        holder = str(packet.get("active_packet_holder") or packet_ledger.get("active_packet_holder") or "")
        status = str(packet.get("active_packet_status") or "")
        router_release = packet.get("packet_router_release") or packet.get("router_startup_release")
        if not isinstance(router_release, dict):
            router_release = {}
        return {
            "packet_id": packet.get("packet_id"),
            "packet_holder": holder,
            "packet_status": status,
            "to_role": envelope.get("to_role") or packet.get("assigned_worker_role"),
            "next_holder": envelope.get("next_holder"),
            "router_direct_dispatch_decision": packet.get("router_direct_dispatch_decision"),
            "router_owned_startup_material": bool(packet.get("router_owned_startup_material")),
            "router_release_recorded": bool(
                router_release
                and router_release.get("delivered_by_router") is True
                and str(router_release.get("relayed_to_role") or "") == "project_manager"
            ),
            "top_level_active_packet_status": packet_ledger.get("active_packet_status"),
            "terminal_lifecycle": packet_ledger.get("terminal_lifecycle"),
        }
    return None


def _user_intake_delivery_action_exists(actions: list[dict[str, Any]]) -> bool:
    for action in actions:
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        if action.get("action_type") != "deliver_mail":
            continue
        mail_id = str(action.get("mail_id") or nested.get("mail_id") or "")
        if mail_id == "user_intake":
            return True
    return False


def _mail_ledger_has_user_intake(packet_ledger: dict[str, Any]) -> bool:
    mail_entries = packet_ledger.get("mail") if isinstance(packet_ledger.get("mail"), list) else []
    return any(isinstance(item, dict) and item.get("mail_id") == "user_intake" for item in mail_entries)


def _user_intake_router_released(packet: dict[str, Any] | None, packet_ledger: dict[str, Any]) -> bool:
    if not isinstance(packet, dict):
        return False
    released_statuses = {
        "envelope-relayed",
        "packet-body-opened-by-recipient",
        "result-returned",
        "result-returned-to-router",
        "stopped_by_user",
    }
    terminal_lifecycle = packet.get("terminal_lifecycle")
    terminal_ok = isinstance(terminal_lifecycle, dict) and terminal_lifecycle.get("status") in {
        "stopped_by_user",
        "cancelled_by_user",
        "closed",
    }
    packet_status = str(packet.get("packet_status") or "")
    top_level_status = str(packet_ledger.get("active_packet_status") or "")
    return (
        str(packet.get("packet_holder") or "") == "project_manager"
        and packet_status in released_statuses
        and packet.get("router_release_recorded") is True
        and (
            (
                packet_ledger.get("active_packet_holder") == "project_manager"
                and top_level_status in released_statuses
            )
            or terminal_ok
        )
    )


def _computed_actions_after(router_state: dict[str, Any], after_time: str) -> list[str]:
    history = router_state.get("history") if isinstance(router_state.get("history"), list) else []
    actions: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        if item.get("label") != "router_computed_next_controller_action":
            continue
        at = str(item.get("at") or "")
        if after_time and at and at < after_time:
            continue
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        action_type = str(details.get("action_type") or "")
        if action_type:
            actions.append(action_type)
    return actions


def _card_ack_handoff_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    return_ledger_path = run_root / "return_event_ledger.json"
    packet_ledger_path = run_root / "packet_ledger.json"
    router_state_path = run_root / "router_state.json"
    return_ledger = _read_json(return_ledger_path) if return_ledger_path.exists() else {}
    packet_ledger = _read_json(packet_ledger_path) if packet_ledger_path.exists() else {}
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}

    completed_returns = [
        item for item in return_ledger.get("completed_returns", [])
        if isinstance(item, dict)
        and item.get("return_kind") == "system_card_bundle"
        and str(item.get("status") or "") in ACK_COMPLETE_STATUSES
    ]
    pending_resolved = [
        item for item in return_ledger.get("pending_returns", [])
        if isinstance(item, dict)
        and item.get("return_kind") == "system_card_bundle"
        and (item.get("status") == "resolved" or bool(item.get("resolved_at")))
    ]

    resolved_by_bundle: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in pending_resolved + completed_returns:
        key = _bundle_identity(item)
        if key[0] or key[1]:
            resolved_by_bundle[key] = item

    if not resolved_by_bundle:
        return findings

    user_intake_packet = _user_intake_packet_summary(packet_ledger)
    user_intake_released = _user_intake_router_released(user_intake_packet, packet_ledger)
    user_intake_delivery_exists = _user_intake_delivery_action_exists(actions)
    user_intake_mail_folded = _mail_ledger_has_user_intake(packet_ledger)

    for key, resolved in sorted(resolved_by_bundle.items()):
        bundle_id, expected_return_path, event = key
        completed_for_key = [
            item for item in completed_returns
            if _record_matches_bundle(item, bundle_id, expected_return_path, event)
        ]
        pending_for_key = [
            item for item in pending_resolved
            if _record_matches_bundle(item, bundle_id, expected_return_path, event)
        ]
        if completed_for_key and any(item.get("status") != "resolved" for item in completed_for_key):
            findings.append(
                {
                    "id": "card_bundle_ack_completion_status_not_normalized",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "completed_statuses": sorted({str(item.get("status") or "") for item in completed_for_key}),
                    "pending_statuses": sorted({str(item.get("status") or "") for item in pending_for_key}),
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                }
            )

        matching_wait_actions = [
            action for action in actions
            if action.get("action_type") in {"await_card_bundle_return_event", "check_card_bundle_return_event"}
            and _record_matches_bundle(action, bundle_id, expected_return_path, event)
        ]
        for action in matching_wait_actions:
            row = row_by_id.get(str(action.get("router_scheduler_row_id") or ""))
            row_state = str(row.get("router_state") or "") if row else ""
            action_done = str(action.get("status") or "") in TERMINAL_ACTION_STATES
            action_reconciled = str(action.get("router_reconciliation_status") or "") in TERMINAL_ACTION_STATES
            row_reconciled = row_state in TERMINAL_ROUTER_ROW_STATES
            if not (action_done and action_reconciled and row_reconciled):
                findings.append(
                    {
                        "id": "card_bundle_ack_resolved_wait_row_still_open",
                        "action_type": action.get("action_type"),
                        "action_id": action.get("action_id"),
                        "action_status": action.get("status"),
                        "router_reconciliation_status": action.get("router_reconciliation_status"),
                        "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                        "row_state": row_state or None,
                        "card_bundle_id": bundle_id,
                        "card_return_event": event,
                        "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    }
                )

        if (
            user_intake_packet
            and user_intake_packet.get("packet_holder") == "controller"
            and user_intake_packet.get("packet_status") == "packet-with-controller"
        ):
            findings.append(
                {
                    "id": "startup_user_intake_owned_by_controller",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_packet": user_intake_packet,
                }
            )
        if user_intake_delivery_exists:
            findings.append(
                {
                    "id": "pm_ack_resolved_queued_controller_user_intake_delivery",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_delivery_action_exists": user_intake_delivery_exists,
                }
            )
        if (
            user_intake_packet
            and str(user_intake_packet.get("to_role") or user_intake_packet.get("next_holder") or "") == "project_manager"
            and not user_intake_released
        ):
            findings.append(
                {
                    "id": "pm_ack_resolved_user_intake_not_released",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_packet": user_intake_packet,
                    "user_intake_mail_folded": user_intake_mail_folded,
                    "user_intake_router_released": user_intake_released,
                }
            )
            ack_time = str(resolved.get("resolved_at") or resolved.get("returned_at") or resolved.get("checked_at") or "")
            computed_actions = _computed_actions_after(router_state, ack_time)
            unrelated = [action for action in computed_actions if action != "router_release_startup_user_intake"]
            if len(unrelated) >= 3:
                findings.append(
                    {
                        "id": "pm_ack_resolved_unrelated_action_loop_before_user_intake_release",
                        "card_bundle_id": bundle_id,
                        "after_ack_time": ack_time,
                        "sample_computed_actions": unrelated[:10],
                    }
                )

    return findings


def _live_run_projection() -> dict[str, object]:
    run_root, skip_reason = _resolve_current_run_root()
    if run_root is None:
        return {
            "ok": True,
            "classification_ok": False,
            "skipped": True,
            "skip_reason": skip_reason,
        }

    scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
    action_dir = run_root / "runtime" / "controller_actions"
    control_block_dir = run_root / "control_blocks"

    if not scheduler_path.exists() or not action_dir.exists():
        return {
            "ok": True,
            "classification_ok": False,
            "skipped": True,
            "run_root": str(run_root.relative_to(PROJECT_ROOT)),
            "skip_reason": "current run does not have runtime scheduler/action ledgers",
        }

    scheduler = _read_json(scheduler_path)
    rows = [row for row in scheduler.get("rows", []) if isinstance(row, dict)]
    row_by_id = {str(row.get("row_id")): row for row in rows if row.get("row_id")}

    actions = []
    for path in sorted(action_dir.glob("*.json")):
        if path.name.startswith(".tmp-") or path.name.endswith(".write.lock"):
            continue
        try:
            payload = _read_json(path)
        except FileNotFoundError:
            continue
        if isinstance(payload, dict):
            actions.append(payload)

    startup_dual_ledger_findings = _startup_dual_ledger_projection_findings(run_root)
    temp_file_findings = _temp_action_file_projection_findings(run_root)
    runtime_write_lock_findings = _runtime_write_lock_projection_findings(run_root)
    boundary_findings = _controller_boundary_projection_findings(run_root, row_by_id, actions)
    mail_findings = _mail_delivery_projection_findings(run_root, row_by_id, actions)
    card_ack_findings = _card_ack_handoff_projection_findings(run_root, row_by_id, actions)

    startup_actions_by_type: dict[str, list[dict[str, Any]]] = {}
    row_findings: list[dict[str, object]] = []
    for action in actions:
        if not _action_is_startup_bootloader(action):
            continue
        action_type = str(action.get("action_type", ""))
        startup_actions_by_type.setdefault(action_type, []).append(action)

        satisfied, row = _startup_reconciliation_satisfied(action, row_by_id)
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        action_source = action_reconciliation.get("source")
        receipt_status = _controller_boundary_receipt_status(run_root, action, row)
        receipt_done = bool(action.get("receipt_recorded_at") or receipt_status.get("done"))
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and receipt_done
            and action_source == STARTUP_RECONCILIATION_SOURCE
        ):
            row_findings.append(
                {
                    "id": "startup_receipt_reconciled_by_daemon_postcondition_owner",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                    "owner": action_source,
                    "receipt_path": action.get("receipt_path") or action.get("expected_receipt_path"),
                }
            )
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and receipt_done
            and action_source == STARTUP_RECONCILIATION_SOURCE
            and action.get("router_pending_apply_required") is True
        ):
            row_findings.append(
                {
                    "id": "startup_receipt_apply_split_requires_later_apply",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                    "router_pending_apply_required": action.get("router_pending_apply_required"),
                    "owner": action_source,
                }
            )
        if action.get("router_reconciliation_status") == "reconciled" and not satisfied:
            row_findings.append(
                {
                    "id": "startup_reconciled_without_satisfied_postcondition",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                }
            )
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and action_reconciliation.get("source") not in ("", *STARTUP_RECONCILIATION_SOURCES)
        ):
            row_findings.append(
                {
                    "id": "startup_reconciled_by_wrong_owner",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "owner": action_reconciliation.get("source"),
                }
            )
        if row and row.get("router_state") == "reconciled":
            row_reconciliation = row.get("reconciliation", {})
            if not isinstance(row_reconciliation, dict):
                row_reconciliation = {}
            if receipt_done and row_reconciliation.get("source") == STARTUP_RECONCILIATION_SOURCE:
                row_findings.append(
                    {
                        "id": "startup_scheduler_row_reconciled_by_daemon_postcondition_owner",
                        "action_id": action.get("action_id"),
                        "action_type": action_type,
                        "row_id": row.get("row_id"),
                        "owner": row_reconciliation.get("source"),
                    }
                )
            if row_reconciliation.get("source") not in ("", *STARTUP_RECONCILIATION_SOURCES):
                row_findings.append(
                    {
                        "id": "startup_scheduler_row_reconciled_by_wrong_owner",
                        "action_id": action.get("action_id"),
                        "action_type": action_type,
                        "row_id": row.get("row_id"),
                        "owner": row_reconciliation.get("source"),
                    }
                )

    blocker_findings: list[dict[str, object]] = []
    if control_block_dir.exists():
        for path in sorted(control_block_dir.glob("*.json")):
            if path.name.endswith(".sealed_repair_packet.json") or path.name == "blocker_repair_policy_snapshot.json":
                continue
            blocker = _read_json(path)
            if blocker.get("source") != MISSING_POSTCONDITION_BLOCKER_SOURCE:
                continue
            blocker_id = str(blocker.get("blocker_id") or "")
            action_type = str(blocker.get("originating_action_type", ""))
            matching_startup_actions = startup_actions_by_type.get(action_type, [])
            reconciled_matches = []
            for action in matching_startup_actions:
                satisfied, row = _startup_reconciliation_satisfied(action, row_by_id)
                if satisfied:
                    reconciled_matches.append(
                        {
                            "action_id": action.get("action_id"),
                            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                            "row_state": row.get("router_state") if row else None,
                        }
                    )
            resolved_by_reconciliation = (
                str(blocker.get("resolution_status") or "")
                in STARTUP_BLOCKER_RECONCILIATION_RESOLUTIONS
            )
            queued_pm_actions = []
            if blocker_id:
                for action in actions:
                    nested = action.get("action") if isinstance(action.get("action"), dict) else {}
                    if action.get("action_type") != "handle_control_blocker":
                        continue
                    if action.get("status") in {"done", "reconciled", "cancelled", "skipped", "resolved", "superseded"}:
                        continue
                    target_role = str(action.get("to_role") or nested.get("to_role") or "")
                    if target_role != "project_manager":
                        continue
                    if blocker_id not in json.dumps(action, sort_keys=True):
                        continue
                    queued_pm_actions.append(
                        {
                            "action_id": action.get("action_id"),
                            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                            "status": action.get("status"),
                            "target_role": target_role,
                        }
                    )
            if (
                matching_startup_actions
                and blocker.get("handling_lane") == "pm_repair_decision_required"
                and not bool(blocker.get("direct_retry_budget_exhausted"))
                and int(blocker.get("direct_retry_budget") or 0) < 1
            ):
                blocker_findings.append(
                    {
                        "id": "startup_missing_postcondition_pm_lane_before_reissue",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "policy_row_id": blocker.get("policy_row_id"),
                        "direct_retry_budget": blocker.get("direct_retry_budget"),
                        "direct_retry_budget_exhausted": blocker.get("direct_retry_budget_exhausted"),
                    }
                )
            if reconciled_matches and not resolved_by_reconciliation:
                blocker_findings.append(
                    {
                        "id": "startup_reconciled_action_false_pm_blocker",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "resolution_status": blocker.get("resolution_status"),
                        "reconciled_matches": reconciled_matches,
                    }
                )
                blocker_findings.append(
                    {
                        "id": "startup_blocker_not_resolved_after_success",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "resolution_status": blocker.get("resolution_status"),
                        "reconciled_matches": reconciled_matches,
                    }
                )
            if reconciled_matches and queued_pm_actions:
                blocker_findings.append(
                    {
                        "id": "startup_reconciled_action_queued_pm_repair",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "queued_pm_actions": queued_pm_actions,
                        "reconciled_matches": reconciled_matches,
                    }
                )

    findings = (
        startup_dual_ledger_findings
        + temp_file_findings
        + runtime_write_lock_findings
        + boundary_findings
        + mail_findings
        + card_ack_findings
        + row_findings
        + blocker_findings
    )
    return {
        "ok": not findings,
        "classification_ok": True,
        "skipped": False,
        "run_id": run_root.name,
        "run_root": str(run_root.relative_to(PROJECT_ROOT)),
        "current_run_can_continue": not findings,
        "decision": "blocked_by_daemon_reconciliation_projection_gap" if findings else "no_daemon_reconciliation_projection_gap",
        "finding_count": len(findings),
        "findings": findings,
    }


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
