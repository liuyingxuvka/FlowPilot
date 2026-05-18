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

from flowpilot_router_controller_boundary import CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE


@dataclass(frozen=True)
class ActionHandlerOutcome:
    result_extra: dict[str, Any] = field(default_factory=dict)
    early_return: dict[str, Any] | None = None


ActionHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any] | None],
    ActionHandlerOutcome,
]

from flowpilot_router_action_handlers_basic import *
from flowpilot_router_action_handlers_roles import *
from flowpilot_router_action_handlers_packets import *

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
    "check_prompt_manifest": _apply_check_prompt_manifest,
    "confirm_controller_core_boundary": _apply_confirm_controller_core_boundary,
    CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE: _apply_controller_deliverable_repair,
    "write_startup_mechanical_audit": _apply_write_startup_mechanical_audit,
    "inject_role_io_protocol": _apply_inject_role_io_protocol,
    "deliver_mail": _apply_deliver_mail,
    "controller_repair_work_packet": _apply_controller_repair_work_packet,
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
    "load_role_recovery_state": _apply_load_role_recovery_state,
    "recover_role_agents": _apply_recover_role_agents,
    "load_resume_state": _apply_load_resume_state,
    "rehydrate_role_agents": _apply_rehydrate_role_agents,
    "create_heartbeat_automation": _apply_create_heartbeat_automation,
    "write_display_surface_status": _apply_write_display_surface_status,
    "handle_control_blocker": _apply_handle_control_blocker,
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
