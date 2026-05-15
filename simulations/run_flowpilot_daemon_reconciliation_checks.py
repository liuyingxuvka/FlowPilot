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
    "daemon_reconciles_startup_bootloader_receipt_once",
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
    "submitted_role_output_left_in_ledger": "submitted expected role output was left only in durable storage",
    "canonical_artifact_flag_not_synced": "canonical role-output artifact existed without synced Router event flag",
    "stale_snapshot_overwrites_role_output_event": "daemon saved a stale router_state snapshot over newer durable role output",
    "computed_from_pending_before_reconciliation": "daemon computed next action from stale pending_action before durable reconciliation",
    "startup_reconciled_action_false_pm_blocker": "startup bootloader row produced a control blocker after it was already reconciled",
    "startup_missing_postcondition_pm_lane_before_reissue": "startup bootloader missing postcondition was sent to PM before mechanical reissue budget was exhausted",
    "startup_blocker_not_resolved_after_success": "startup bootloader blocker stayed active after its postcondition was reconciled",
    "startup_reconciled_action_queued_pm_repair": "PM repair action was queued after startup bootloader postcondition reconciliation",
    "startup_unsupported_receipt_escalated_to_pm": "unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied",
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
        f"unsupported={state.unsupported_startup_receipt_action}|"
        f"boundary={state.controller_boundary_artifact_exists},{state.controller_boundary_artifact_valid},"
        f"action_reconciled={state.controller_boundary_action_reconciled},"
        f"scheduler_reconciled={state.controller_boundary_scheduler_reconciled},"
        f"flags={state.controller_boundary_flags_synced},"
        f"reissued={state.controller_boundary_reissued_after_reconcile},"
        f"without_pending={state.controller_boundary_action_returned_without_pending}|"
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
        payload = _read_json(path)
        if isinstance(payload, dict):
            actions.append(payload)

    boundary_findings = _controller_boundary_projection_findings(run_root, row_by_id, actions)

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

    findings = boundary_findings + row_findings + blocker_findings
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
