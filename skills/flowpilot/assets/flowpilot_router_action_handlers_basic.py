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

def _apply_check_prompt_manifest(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del router, project_root, run_root, pending, payload
    run_state["manifest_check_requested"] = True
    run_state["manifest_check_requests"] = int(run_state.get("manifest_check_requests", 0)) + 1
    run_state["manifest_checks"] = int(run_state.get("manifest_checks", 0)) + 1
    return ActionHandlerOutcome()

def _apply_confirm_controller_core_boundary(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    confirmation = router._write_controller_boundary_confirmation(
        project_root,
        run_root,
        run_state,
        controller_agent_id=str((payload or {}).get("controller_agent_id") or router.CONTROLLER_RUNTIME_HELPER_AGENT_ID),
        action_id=str(pending.get("controller_action_id") or ""),
        source_action_id=str(pending.get("action_id") or ""),
    )
    if router._controller_boundary_confirmation_context(project_root, run_root, run_state) is None:
        raise router.RouterError("controller boundary confirmation was not written with current controller.core evidence")
    run_state["flags"]["controller_role_confirmed"] = True
    run_state["flags"]["controller_role_confirmed_from_router_core"] = True
    run_state["flags"]["controller_boundary_confirmation_written"] = True
    run_state["controller_boundary_confirmation"] = confirmation
    run_state["events"].append(
        {
            "event": "controller_role_confirmed_from_router_core",
            "summary": "Controller confirmed the Router-delivered controller.core boundary.",
            "payload": confirmation,
            "recorded_at": router.utc_now(),
        }
    )
    return ActionHandlerOutcome()

def _apply_controller_deliverable_repair(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    repair_target = str(pending.get("repair_target_action_type") or "")
    if repair_target != "confirm_controller_core_boundary":
        raise router.RouterError(f"unsupported controller deliverable repair target: {repair_target}")
    confirmation = router._write_controller_boundary_confirmation(
        project_root,
        run_root,
        run_state,
        controller_agent_id=str((payload or {}).get("controller_agent_id") or router.CONTROLLER_RUNTIME_HELPER_AGENT_ID),
        action_id=str(pending.get("controller_action_id") or ""),
        source_action_id=str(pending.get("source_receipt_action_id") or pending.get("repair_of_controller_action_id") or ""),
    )
    applied = router._sync_controller_boundary_confirmation_from_artifact(
        project_root,
        run_root,
        run_state,
        pending,
        payload or {"applied": CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE},
        source="controller_deliverable_repair_apply",
    )
    if not applied.get("applied"):
        raise router.RouterError("controller deliverable repair did not produce a valid boundary confirmation")
    router._mark_controller_deliverable_repair_resolved(
        project_root,
        run_root,
        run_state,
        repair_action=pending,
        applied_postcondition=applied,
    )
    return ActionHandlerOutcome(
        result_extra={
            "repair_of_controller_action_id": pending.get("repair_of_controller_action_id"),
            "repair_target_action_type": repair_target,
            "controller_boundary_confirmation": confirmation,
            "applied_postcondition": applied,
        }
    )

def _apply_write_startup_mechanical_audit(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending, payload
    computed_checks = router._startup_fact_checks(project_root, run_root, run_state)
    router._write_startup_mechanical_audit(project_root, run_root, run_state, computed_checks)
    context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise router.RouterError("startup mechanical audit was not written with a valid proof")
    run_state["flags"]["startup_mechanical_audit_written"] = True
    run_state["startup_mechanical_audit"] = {
        "path": router.project_relative(project_root, context["audit_path"]),
        "sha256": context["audit_hash"],
        "proof_path": router.project_relative(project_root, context["proof_path"]),
        "proof_sha256": context["proof_hash"],
        "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
    }
    return ActionHandlerOutcome()

__all__ = (
    '_apply_sync_display_plan',
    '_apply_terminal_summary',
    '_apply_relay_only_system_card',
    '_apply_relay_only_system_card_bundle',
    '_apply_await_card_return_event',
    '_apply_await_card_bundle_return_event',
    '_apply_await_user_after_model_miss_stop',
    '_apply_lifecycle_terminal',
    '_apply_await_role_decision',
    '_request_ledger_check',
    '_apply_check_packet_ledger',
    '_apply_check_card_return_event',
    '_apply_check_card_bundle_return_event',
    '_apply_check_prompt_manifest',
    '_apply_confirm_controller_core_boundary',
    '_apply_controller_deliverable_repair',
    '_apply_write_startup_mechanical_audit',
)
