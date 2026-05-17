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


def _apply_inject_role_io_protocol(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    role = str(pending.get("to_role") or "")
    agent_id = str(pending.get("target_agent_id") or "")
    if role not in router.CREW_ROLE_KEYS or not agent_id:
        raise router.RouterError("role I/O protocol injection requires a live target role and agent")
    resume_tick_id = str(pending.get("resume_tick_id") or router._latest_resume_tick_id(run_state))
    receipts = router._append_role_io_protocol_injections(
        project_root,
        run_root,
        str(run_state["run_id"]),
        [{"role_key": role, "agent_id": agent_id}],
        default_lifecycle_phase="router_repair_injection",
        resume_tick_id=resume_tick_id,
        source_action="inject_role_io_protocol",
    )
    if not receipts:
        receipt = router._role_io_protocol_receipt_for_agent(
            run_root,
            str(run_state["run_id"]),
            role=role,
            agent_id=agent_id,
            resume_tick_id=resume_tick_id,
        )
        if receipt is None:
            raise router.RouterError("role I/O protocol injection did not produce a usable receipt")
        receipts = [receipt]
    run_state["role_io_protocol_injections"] = int(run_state.get("role_io_protocol_injections", 0)) + len(receipts)
    return ActionHandlerOutcome(
        result_extra={
            "role_io_protocol_receipts": receipts,
            "protocol_hash": router._role_io_protocol_hash(),
        }
    )


def _apply_deliver_mail(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    return ActionHandlerOutcome(
        result_extra={
            "mail_delivery": router._fold_mail_delivery_postcondition(
                project_root,
                run_root,
                run_state,
                pending,
                payload,
                source="direct_controller_action_mail_delivery_fold",
            )
        }
    )


def _apply_controller_repair_work_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del project_root, run_state
    if pending.get("controller_may_approve_gate") or pending.get("controller_may_mutate_route") or pending.get("controller_may_read_sealed_bodies"):
        raise router.RouterError("controller_repair_work_packet cannot grant gate approval, route mutation, or sealed body access")
    transaction_id = str(pending.get("repair_transaction_id") or "")
    if not transaction_id:
        raise router.RouterError("controller_repair_work_packet requires repair_transaction_id")
    transaction_path = router._repair_transaction_path(run_root, transaction_id)
    transaction = router.read_json_if_exists(transaction_path)
    if transaction.get("schema_version") != router.REPAIR_TRANSACTION_SCHEMA:
        raise router.RouterError("controller_repair_work_packet transaction is missing")
    repair_result = {
        "schema_version": "flowpilot.controller_repair_work_packet_result.v1",
        "status": str((payload or {}).get("status") or "done"),
        "evidence": (payload or {}).get("evidence") if isinstance(payload, dict) else None,
        "recorded_at": router.utc_now(),
        "controller_action_id": pending.get("controller_action_id"),
    }
    transaction["controller_repair_work_packet_result"] = repair_result
    transaction["status"] = "awaiting_recheck"
    transaction["updated_at"] = repair_result["recorded_at"]
    router.write_json(transaction_path, transaction)
    return ActionHandlerOutcome(
        result_extra={
            "repair_transaction_id": transaction_id,
            "controller_repair_work_packet_result": repair_result,
        }
    )


def _apply_load_role_recovery_state(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending, payload
    router._load_role_recovery_state(project_root, run_root, run_state)
    return ActionHandlerOutcome()


def _apply_recover_role_agents(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending
    if not run_state["flags"].get("role_recovery_state_loaded"):
        raise router.RouterError("role recovery requires load_role_recovery_state first")
    router._write_role_recovery_report(project_root, run_root, run_state, payload or {})
    return ActionHandlerOutcome()


def _apply_load_resume_state(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending, payload
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    daemon_recovery = router._router_daemon_resume_recovery_summary(project_root, run_root)
    continuation_quarantine = router._write_continuation_quarantine(project_root, run_root, run_state)
    required_paths = {
        "current_pointer": project_root / ".flowpilot" / "current.json",
        "router_state": router.run_state_path(run_root),
        "prompt_delivery_ledger": run_root / "prompt_delivery_ledger.json",
        "packet_ledger": run_root / "packet_ledger.json",
        "execution_frontier": run_root / "execution_frontier.json",
        "crew_ledger": run_root / "crew_ledger.json",
        "crew_memory": run_root / "crew_memory",
        "continuation_binding": router._continuation_binding_path(run_root),
        "continuation_quarantine": router._continuation_quarantine_path(run_root),
        "route_history_index": router._route_history_index_path(run_root),
        "pm_prior_path_context": router._pm_prior_path_context_path(run_root),
        "router_daemon_status": router._router_daemon_status_path(run_root),
        "controller_action_ledger": router._controller_action_ledger_path(run_root),
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    crew_memory_files = sorted((run_root / "crew_memory").glob("*.json")) if (run_root / "crew_memory").exists() else []
    display_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    role_recovery_context = router._role_recovery_ready_context(project_root, run_root, run_state)
    roles_ready_from_recovery = role_recovery_context is not None
    pm_resume_decision_required = True
    if role_recovery_context is not None:
        recovery_report = role_recovery_context["report"]
        pm_resume_decision_required = bool(recovery_report.get("pm_decision_required_before_normal_work"))
    ambiguous_state = bool(missing) or (
        len(crew_memory_files) != len(router.CREW_ROLE_KEYS) and not roles_ready_from_recovery
    )
    resume_record = {
        "schema_version": router.RESUME_EVIDENCE_SCHEMA,
        "run_id": run_state["run_id"],
        "resume_tick_id": router._latest_resume_tick_id(run_state),
        "recorded_at": router.utc_now(),
        "recorded_by": "controller",
        "stable_launcher": True,
        "wake_recorded_to_router": True,
        "controller_only": True,
        "loaded_paths": {
            name: router.project_relative(project_root, path)
            for name, path in required_paths.items()
            if path.exists()
        },
        "observed_optional_paths": {
            "router_daemon_lock": router.project_relative(project_root, router._router_daemon_lock_path(run_root))
            if router._router_daemon_lock_path(run_root).exists()
            else None,
        },
        "missing_paths": missing,
        "crew_memory_count": len(crew_memory_files),
        "crew_memory_ready_for_rehydration": len(crew_memory_files) == len(router.CREW_ROLE_KEYS),
        "roles_restored_or_replaced": roles_ready_from_recovery,
        "role_rehydration_required": not roles_ready_from_recovery,
        "controller_visibility": "state_and_envelopes_only",
        "controller_may_read_packet_body": False,
        "controller_may_read_result_body": False,
        "controller_may_infer_route_progress_from_chat_history": False,
        "display_plan_path": router.project_relative(project_root, router._display_plan_path(run_root)),
        "visible_plan_restore_required": True,
        "visible_plan_restored_from_run": True,
        "display_plan_exists": display_payload["display_plan_exists"],
        "display_plan_projection_hash": display_payload["projection_hash"],
        "display_plan_projection": display_payload["native_plan_projection"],
        "resume_next_recipient_from_packet_ledger": resume_next,
        "router_daemon_resume_recovery": daemon_recovery,
        "router_daemon_status_loaded": daemon_recovery["router_daemon_status_exists"],
        "router_daemon_liveness_checked": True,
        "router_daemon_restarted_if_dead": daemon_recovery["decision"] == "restart_router_daemon_from_current_state",
        "controller_action_ledger_loaded": daemon_recovery["controller_action_ledger_exists"],
        "controller_action_ledger_rescanned": daemon_recovery["controller_action_ledger_rescanned"],
        "role_recovery_report_reclaimed": roles_ready_from_recovery,
        "role_recovery_report_path": role_recovery_context["report_relpath"] if role_recovery_context else None,
        "pm_resume_decision_required": pm_resume_decision_required,
        "ambiguous_state_blocks_controller_execution": ambiguous_state,
        "continuation_quarantine": continuation_quarantine,
    }
    router.write_json(run_root / "continuation" / "resume_reentry.json", resume_record)
    run_state["flags"]["resume_state_loaded"] = True
    run_state["flags"]["resume_state_ambiguous"] = bool(resume_record["ambiguous_state_blocks_controller_execution"])
    if roles_ready_from_recovery:
        router._reclaim_role_recovery_postcondition_from_report(
            project_root,
            run_root,
            run_state,
            source="load_resume_state_role_recovery_report_reclaim",
        )
    else:
        run_state["flags"]["resume_roles_restored"] = False
    if router._latest_role_recovery_transaction(run_root).get("schema_version") == router.ROLE_RECOVERY_TRANSACTION_SCHEMA:
        run_state["flags"]["role_recovery_state_loaded"] = True
    return ActionHandlerOutcome()


def _apply_rehydrate_role_agents(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending
    if not run_state["flags"].get("resume_state_loaded"):
        raise router.RouterError("resume role rehydration requires load_resume_state first")
    router._write_resume_role_rehydration_report(project_root, run_root, run_state, payload or {})
    return ActionHandlerOutcome()


def _apply_create_heartbeat_automation(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del pending
    router._write_host_heartbeat_binding(project_root, run_root, run_state, payload or {})
    run_state["flags"]["continuation_binding_recorded"] = True
    run_state["events"].append(
        {
            "event": "host_records_heartbeat_binding",
            "summary": router.EXTERNAL_EVENTS["host_records_heartbeat_binding"]["summary"],
            "payload": payload or {},
            "recorded_at": router.utc_now(),
            "source_action": "create_heartbeat_automation",
        }
    )
    return ActionHandlerOutcome()


def _apply_write_display_surface_status(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    confirmation = router._display_confirmation_for_action(payload, pending)
    router._write_display_surface_status(project_root, run_root, run_state, confirmation, payload or {})
    router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
    run_state["flags"]["startup_display_status_written"] = True
    return ActionHandlerOutcome()


def _apply_handle_control_blocker(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._mark_control_blocker_delivered(project_root, run_root, run_state, pending)
    return ActionHandlerOutcome()


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
