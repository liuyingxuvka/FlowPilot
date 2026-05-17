"""Controller-action application handlers for FlowPilot router.

This module is a thin extraction layer. It keeps state persistence and
post-apply finalization in `flowpilot_router.apply_controller_action` while
moving low-risk action bodies behind an action-type registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


@dataclass(frozen=True)
class ActionHandlerOutcome:
    result_extra: dict[str, Any] = field(default_factory=dict)
    early_return: dict[str, Any] | None = None


ActionHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any] | None],
    ActionHandlerOutcome,
]


def _apply_sync_display_plan(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    router._apply_sync_display_plan_state(project_root, run_root, run_state, pending, payload or {})
    return ActionHandlerOutcome()


def _apply_terminal_summary(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending
    mode = router._terminal_lifecycle_mode(run_state)
    if not mode:
        raise router.RouterError("write_terminal_summary is allowed only after the run is terminal")
    record = router._write_terminal_summary(project_root, run_root, run_state, payload, mode=mode)
    if not router._terminal_summary_written(project_root, run_state, run_root):
        raise router.RouterError("terminal summary write did not produce a valid indexed summary")
    return ActionHandlerOutcome(
        result_extra={
            "terminal_summary_path": record["summary_markdown_path"],
            "terminal_summary_json_path": record["summary_json_path"],
            "terminal_summary_sha256": record["summary_sha256"],
            "final_user_report_schema_version": record["final_user_report"]["schema_version"],
            "final_user_report_is_completion_authority": False,
        }
    )


def _apply_relay_only_system_card(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del project_root, run_root, run_state, pending, payload
    raise router.RouterError(
        "deliver_system_card is relay-only; Router commits the card envelope internally and Controller must only relay it"
    )


def _apply_relay_only_system_card_bundle(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del project_root, run_root, run_state, pending, payload
    raise router.RouterError(
        "deliver_system_card_bundle is relay-only; Router commits the card bundle envelope internally and Controller must only relay it"
    )


def _apply_await_card_return_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="waiting",
        payload={"waiting_for": "card_return_event", "expected_return_path": pending.get("expected_return_path")},
    )
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(
        early_return={
            "ok": True,
            "applied": "await_card_return_event",
            "waiting": True,
            "expected_return_path": pending.get("expected_return_path"),
        }
    )


def _apply_await_card_bundle_return_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="waiting",
        payload={"waiting_for": "card_bundle_return_event", "expected_return_path": pending.get("expected_return_path")},
    )
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(
        early_return={
            "ok": True,
            "applied": "await_card_bundle_return_event",
            "waiting": True,
            "expected_return_path": pending.get("expected_return_path"),
        }
    )


def _apply_await_user_after_model_miss_stop(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="waiting",
        payload={"waiting_for": "user"},
    )
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(
        early_return={"ok": True, "applied": "await_user_after_model_miss_stop", "waiting": True, "waiting_for": "user"}
    )


def _apply_lifecycle_terminal(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="done",
        payload={"terminal": True, "run_lifecycle_status": router._terminal_lifecycle_mode(run_state)},
    )
    router._mark_router_daemon_terminal(project_root, run_root, run_state, reason="run_lifecycle_terminal_observed")
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(
        early_return={
            "ok": True,
            "applied": "run_lifecycle_terminal",
            "terminal": True,
            "run_lifecycle_status": router._terminal_lifecycle_mode(run_state),
        }
    )


def _apply_await_role_decision(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="waiting",
        payload={"waiting_for": pending.get("to_role"), "allowed_external_events": pending.get("allowed_external_events") or []},
    )
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(early_return={"ok": True, "applied": "await_role_decision", "waiting": True})


def _request_ledger_check(
    router: ModuleType,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    *,
    error_message: str,
    verify_after_request: bool = False,
) -> None:
    combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
    if not run_state.get("ledger_check_requested"):
        if not combined_ledger_check:
            raise router.RouterError(error_message)
        run_state["ledger_check_requested"] = True
        run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
        run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
    if verify_after_request and not run_state.get("ledger_check_requested"):
        raise router.RouterError(error_message)


def _apply_check_packet_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del router, project_root, run_root, pending, payload
    run_state["ledger_check_requested"] = True
    run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
    run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
    return ActionHandlerOutcome()


def _apply_check_card_return_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._apply_card_return_event_check(project_root, run_root, run_state, pending)
    return ActionHandlerOutcome()


def _apply_check_card_bundle_return_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    bundle_result = router._apply_card_bundle_return_event_check(project_root, run_root, run_state, pending)
    if bundle_result.get("status") != "bundle_ack_incomplete":
        return ActionHandlerOutcome()
    router.append_history(run_state, "bundle_ack_incomplete", bundle_result["record"])
    run_state["pending_action"] = None
    router._refresh_route_memory(project_root, run_root, run_state, trigger="after_controller_action:bundle_ack_incomplete")
    router._sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_controller_action:bundle_ack_incomplete",
        update_display=True,
    )
    router.save_run_state(run_root, run_state)
    return ActionHandlerOutcome(
        early_return={
            "ok": False,
            "applied": "check_card_bundle_return_event",
            "waiting": True,
            "status": "bundle_ack_incomplete",
            "missing_card_ids": bundle_result["missing_card_ids"],
            "expected_return_path": bundle_result["expected_return_path"],
            "waiting_for_role": bundle_result["waiting_for_role"],
        }
    )


def _apply_relay_material_scan_packets(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="material scan packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._material_scan_index_path(run_root), label="material scan")
    router._relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
    router._mark_parallel_batch_packets_relayed(run_root, "material_scan")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        index["packets"],
        packet_family="material_scan",
        mode="lease_on_material_scan_relay",
    )
    run_state["flags"]["material_scan_packets_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})


def _apply_relay_material_scan_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="material scan result relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._material_scan_index_path(run_root), label="material scan")
    router._relay_result_records(project_root, run_state, index["packets"], to_role="project_manager", controller_agent_id="controller")
    run_state["flags"]["material_scan_results_relayed_to_pm"] = True
    batch = router._active_parallel_packet_batch(run_root, "material_scan")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()


def _apply_relay_research_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="research packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._research_packet_index_path(run_root), label="research")
    router._relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
    router._mark_parallel_batch_packets_relayed(run_root, "research")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        index["packets"],
        packet_family="research",
        mode="lease_on_research_packet_relay",
    )
    run_state["flags"]["research_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})


def _apply_relay_research_result(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="research result relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._research_packet_index_path(run_root), label="research")
    router._relay_result_records(project_root, run_state, index["packets"], to_role="project_manager", controller_agent_id="controller")
    batch = router._active_parallel_packet_batch(run_root, "research")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["flags"]["research_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()


def _apply_relay_pm_role_work_request_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="PM role-work request relay requires a current packet-ledger check",
    )
    index = router._load_pm_role_work_request_index(run_root, run_state)
    batch_records = router._active_pm_role_work_batch_records(index)
    records = [record for record in batch_records if record.get("status") == "open"] if batch_records else []
    if not records:
        active = router._active_pm_role_work_request(index)
        records = [active] if isinstance(active, dict) and active.get("status") == "open" else []
    if not records:
        raise router.RouterError("PM role-work request relay requires an open active request")
    router._relay_packet_records(project_root, run_state, records, controller_agent_id="controller")
    for record in records:
        record["status"] = "packet_relayed"
        record["packet_relayed_at"] = router.utc_now()
        router._record_officer_lifecycle_status(
            project_root,
            run_root,
            run_state,
            record,
            lifecycle_status="packet_relayed",
        )
    router._mark_parallel_batch_packets_relayed(run_root, "pm_role_work")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        records,
        packet_family="pm_role_work",
        mode="lease_on_pm_role_work_request_relay",
    )
    index["active_request_id"] = records[0].get("request_id")
    router._write_pm_role_work_request_index(run_root, index)
    run_state["flags"]["pm_role_work_request_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    run_state["pm_role_work_requests"] = {
        "index_path": router.project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
        "active_batch_id": index.get("active_batch_id"),
        "active_request_ids": [record.get("request_id") for record in records],
        "active_packet_ids": [record.get("packet_id") for record in records],
        "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
        "active_request_mode": records[0].get("request_mode"),
    }
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})


def _apply_relay_pm_role_work_result_to_pm(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="PM role-work result relay requires a current packet-ledger check",
    )
    index = router._load_pm_role_work_request_index(run_root, run_state)
    batch_records = router._active_pm_role_work_batch_records(index)
    records = [record for record in batch_records if record.get("status") == "result_returned"] if batch_records else []
    if not records:
        active = router._active_pm_role_work_request(index)
        records = [active] if isinstance(active, dict) and active.get("status") == "result_returned" else []
    if not records:
        raise router.RouterError("PM role-work result relay requires an active returned result")
    router._relay_result_records(project_root, run_state, records, to_role="project_manager", controller_agent_id="controller")
    for record in records:
        record["status"] = "result_relayed_to_pm"
        record["result_relayed_to_pm_at"] = router.utc_now()
        router._record_officer_lifecycle_status(
            project_root,
            run_root,
            run_state,
            record,
            lifecycle_status="result_relayed_to_pm",
        )
    batch = router._active_parallel_packet_batch(run_root, "pm_role_work")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    index["active_request_id"] = records[0].get("request_id")
    router._write_pm_role_work_request_index(run_root, index)
    run_state["flags"]["pm_role_work_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    run_state["pm_role_work_requests"] = {
        "index_path": router.project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
        "active_batch_id": index.get("active_batch_id"),
        "active_request_ids": [record.get("request_id") for record in records],
        "active_packet_ids": [record.get("packet_id") for record in records],
        "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
        "active_request_mode": records[0].get("request_mode"),
    }
    return ActionHandlerOutcome()


def _apply_enter_next_child_node(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    return ActionHandlerOutcome(result_extra=router._enter_next_child_node(project_root, run_root, run_state, pending))


def _apply_relay_current_node_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="current-node packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    frontier = router._active_frontier(run_root)
    router._require_clean_self_interrogation(
        project_root,
        run_root,
        gate_name="current-node packet relay",
        scopes=("node_entry",),
        node_id=str(frontier["active_node_id"]),
        route_version=int(frontier.get("route_version") or 0),
    )
    records = router._current_node_packet_records(project_root, run_state)
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = router.packet_runtime.load_envelope(project_root, envelope_path)
        audit = router.packet_runtime.validate_packet_ready_for_direct_relay(
            project_root,
            packet_envelope=envelope,
            envelope_path=envelope_path,
        )
        if not audit.get("passed"):
            raise router.RouterError(f"current-node packet envelope is not ready for direct relay: {audit.get('blockers')}")
        router._ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
        router.packet_runtime.controller_relay_envelope(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role=str(envelope.get("from_role") or "project_manager"),
            relayed_to_role=str(envelope.get("to_role")),
        )
    lease_summary = router._issue_current_node_active_holder_leases(project_root, run_root, run_state, records)
    router._mark_parallel_batch_packets_relayed(run_root, "current_node")
    run_state["flags"]["current_node_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})


def _apply_relay_current_node_result(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="current-node result relay requires a current packet-ledger check",
    )
    if not run_state["flags"].get("current_node_worker_result_returned"):
        raise router.RouterError("current-node result relay requires worker result event")
    records = router._current_node_packet_records(project_root, run_state)
    router._validate_results_exist_for_packets(project_root, run_state, records, next_recipient="project_manager")
    router._relay_result_records(project_root, run_state, records, to_role="project_manager", controller_agent_id="controller")
    batch = router._active_parallel_packet_batch(run_root, "current_node")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["flags"]["current_node_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()


PASSIVE_WAIT_HANDLER_ACTION_TYPES = (
    "await_role_decision",
    "await_card_return_event",
    "await_card_bundle_return_event",
    "await_user_after_model_miss_stop",
)

SYSTEM_CARD_DELIVERY_HANDLER_ACTION_TYPES = (
    "deliver_system_card",
    "deliver_system_card_bundle",
)

ACTION_HANDLERS: dict[str, ActionHandler] = {
    "sync_display_plan": _apply_sync_display_plan,
    "write_terminal_summary": _apply_terminal_summary,
    "deliver_system_card": _apply_relay_only_system_card,
    "deliver_system_card_bundle": _apply_relay_only_system_card_bundle,
    "await_card_return_event": _apply_await_card_return_event,
    "await_card_bundle_return_event": _apply_await_card_bundle_return_event,
    "await_user_after_model_miss_stop": _apply_await_user_after_model_miss_stop,
    "run_lifecycle_terminal": _apply_lifecycle_terminal,
    "await_role_decision": _apply_await_role_decision,
    "check_packet_ledger": _apply_check_packet_ledger,
    "check_card_return_event": _apply_check_card_return_event,
    "check_card_bundle_return_event": _apply_check_card_bundle_return_event,
    "relay_material_scan_packets": _apply_relay_material_scan_packets,
    "relay_material_scan_results_to_pm": _apply_relay_material_scan_results,
    "relay_material_scan_results_to_reviewer": _apply_relay_material_scan_results,
    "relay_research_packet": _apply_relay_research_packet,
    "relay_research_result_to_pm": _apply_relay_research_result,
    "relay_research_result_to_reviewer": _apply_relay_research_result,
    "relay_pm_role_work_request_packet": _apply_relay_pm_role_work_request_packet,
    "relay_pm_role_work_result_to_pm": _apply_relay_pm_role_work_result_to_pm,
    "enter_next_child_node": _apply_enter_next_child_node,
    "relay_current_node_packet": _apply_relay_current_node_packet,
    "relay_current_node_result_to_pm": _apply_relay_current_node_result,
    "relay_current_node_result_to_reviewer": _apply_relay_current_node_result,
}


def apply_registered_action(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    action_type: str,
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome | None:
    handler = ACTION_HANDLERS.get(action_type)
    if handler is None:
        return None
    return handler(router, project_root, run_root, run_state, pending, payload)


def auto_commit_system_card_delivery_action(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    planned = dict(action)
    planned["resource_lifecycle"] = "planned_internal_action"
    planned["artifact_committed"] = False
    planned["relay_allowed"] = False
    planned["apply_required"] = True
    planned.setdefault(
        "planned_artifacts",
        {
            "card_envelope_path": planned.get("card_envelope_path"),
            "expected_receipt_path": planned.get("expected_receipt_path"),
            "expected_return_path": planned.get("expected_return_path"),
        },
    )
    run_state["pending_action"] = planned
    router.append_history(
        run_state,
        "router_auto_commits_internal_system_card_delivery",
        {
            "action_type": planned.get("action_type"),
            "card_id": planned.get("card_id"),
            "planned_artifacts_exposed_to_controller": False,
        },
    )
    commit_result = router._commit_system_card_delivery_artifact(project_root, run_state, run_root, planned)
    router.append_history(
        run_state,
        "router_committed_system_card_delivery_artifact",
        {
            "card_id": planned.get("card_id"),
            "card_envelope_path": commit_result.get("card_envelope_path"),
            "relay_allowed": commit_result.get("relay_allowed"),
        },
    )
    run_state["pending_action"] = None
    router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_internal_commit:deliver_system_card")
    router._sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_internal_commit:deliver_system_card",
        update_display=True,
    )
    router.save_run_state(run_root, run_state)
    record = router._pending_return_record_for_action(run_root, str(run_state["run_id"]), planned)
    if record is None:
        raise router.RouterError("system card auto-commit did not establish a pending return record")
    committed_extra = router._committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    if not committed_extra["relay_allowed"]:
        raise router.RouterError("system card auto-commit did not produce a relay-ready committed artifact")
    committed = {
        **planned,
        **committed_extra,
        "ack_clearance_scope": record.get("ack_clearance_scope"),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
        "summary": (
            f"Relay committed system card envelope {planned.get('card_id')} to {planned.get('to_role')}; "
            f"the role must open it through runtime and return {planned.get('card_return_event')}."
        ),
        "allowed_writes": [],
        "auto_committed_by_router": True,
        "auto_commit_result": commit_result,
        "next_after_relay": "await_card_return_event",
    }
    committed["next_step_contract"] = {
        **committed.get("next_step_contract", {}),
        "resource_lifecycle": committed["resource_lifecycle"],
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "ack_clearance_scope": committed.get("ack_clearance_scope"),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
    run_state["pending_action"] = committed
    router.append_history(
        run_state,
        "router_returned_committed_system_card_relay_action",
        {
            "card_id": committed.get("card_id"),
            "card_envelope_path": committed.get("card_envelope_path"),
            "relay_allowed": committed.get("relay_allowed"),
        },
    )
    router.save_run_state(run_root, run_state)
    return committed


def auto_commit_system_card_bundle_delivery_action(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    planned = dict(action)
    planned["resource_lifecycle"] = "planned_internal_action"
    planned["artifact_committed"] = False
    planned["relay_allowed"] = False
    planned["apply_required"] = True
    planned.setdefault(
        "planned_artifacts",
        {
            "card_bundle_envelope_path": planned.get("card_bundle_envelope_path"),
            "expected_receipt_paths": planned.get("expected_receipt_paths"),
            "expected_return_path": planned.get("expected_return_path"),
        },
    )
    run_state["pending_action"] = planned
    router.append_history(
        run_state,
        "router_auto_commits_internal_system_card_bundle_delivery",
        {
            "action_type": planned.get("action_type"),
            "card_ids": planned.get("card_ids"),
            "planned_artifacts_exposed_to_controller": False,
        },
    )
    commit_result = router._commit_system_card_bundle_delivery_artifact(project_root, run_state, run_root, planned)
    router.append_history(
        run_state,
        "router_committed_system_card_bundle_delivery_artifact",
        {
            "card_bundle_id": planned.get("card_bundle_id"),
            "card_bundle_envelope_path": commit_result.get("card_bundle_envelope_path"),
            "relay_allowed": commit_result.get("relay_allowed"),
        },
    )
    run_state["pending_action"] = None
    router._refresh_route_memory(
        project_root,
        run_root,
        run_state,
        trigger="after_router_internal_commit:deliver_system_card_bundle",
    )
    router._sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_internal_commit:deliver_system_card_bundle",
        update_display=True,
    )
    router.save_run_state(run_root, run_state)
    record = router._pending_bundle_return_record_for_action(run_root, str(run_state["run_id"]), planned)
    if record is None:
        raise router.RouterError("system card bundle auto-commit did not establish a pending return record")
    committed_extra = router._committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    if not committed_extra["relay_allowed"]:
        raise router.RouterError("system card bundle auto-commit did not produce a relay-ready committed artifact")
    committed = {
        **planned,
        **committed_extra,
        "card_bundle_envelope_hash": record.get("card_bundle_envelope_hash"),
        "ack_clearance_scope": record.get("ack_clearance_scope"),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
        "summary": (
            f"Relay committed system-card bundle {planned.get('card_bundle_id')} to {planned.get('to_role')}; "
            f"the role must open it through runtime and return {planned.get('card_return_event')}."
        ),
        "allowed_writes": [],
        "auto_committed_by_router": True,
        "auto_commit_result": commit_result,
        "next_after_relay": "await_card_bundle_return_event",
    }
    committed["next_step_contract"] = {
        **committed.get("next_step_contract", {}),
        "resource_lifecycle": committed["resource_lifecycle"],
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "ack_clearance_scope": committed.get("ack_clearance_scope"),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
    run_state["pending_action"] = committed
    router.append_history(
        run_state,
        "router_returned_committed_system_card_bundle_relay_action",
        {
            "card_bundle_id": committed.get("card_bundle_id"),
            "card_ids": committed.get("card_ids"),
            "card_bundle_envelope_path": committed.get("card_bundle_envelope_path"),
            "relay_allowed": committed.get("relay_allowed"),
        },
    )
    router.save_run_state(run_root, run_state)
    return committed
