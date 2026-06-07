"""Resume and role-recovery controller-action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome


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


def _apply_recover_role_bindings(
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
        "role_binding_ledger": run_root / "role_binding_ledger.json",
        "role_binding_memory": run_root / "role_binding_memory",
        "continuation_binding": router._continuation_binding_path(run_root),
        "continuation_quarantine": router._continuation_quarantine_path(run_root),
        "route_history_index": router._route_history_index_path(run_root),
        "pm_prior_path_context": router._pm_prior_path_context_path(run_root),
        "router_daemon_status": router._router_daemon_status_path(run_root),
        "controller_action_ledger": router._controller_action_ledger_path(run_root),
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    current_resume_role_keys = router._current_resume_role_keys(project_root, run_root, run_state)
    role_binding_memory_files = (
        sorted((run_root / "role_binding_memory").glob("*.json"))
        if (run_root / "role_binding_memory").exists()
        else []
    )
    current_role_memory_files = [
        path
        for path in role_binding_memory_files
        if path.stem in current_resume_role_keys
    ]
    display_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    role_recovery_context = router._role_recovery_ready_context(project_root, run_root, run_state)
    roles_ready_from_recovery = role_recovery_context is not None
    pm_resume_decision_required = True
    if role_recovery_context is not None:
        recovery_report = role_recovery_context["report"]
        pm_resume_decision_required = bool(recovery_report.get("pm_decision_required_before_normal_work"))
    ambiguous_state = bool(missing) or (
        len(current_role_memory_files) != len(current_resume_role_keys) and not roles_ready_from_recovery
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
        "role_binding_memory_count": len(current_role_memory_files),
        "role_binding_memory_target_role_keys": current_resume_role_keys,
        "role_binding_memory_ready_for_rehydration": len(current_role_memory_files) == len(current_resume_role_keys),
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


def _apply_rehydrate_role_bindings(
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


__all__ = (
    "_apply_load_role_recovery_state",
    "_apply_recover_role_bindings",
    "_apply_load_resume_state",
    "_apply_rehydrate_role_bindings",
)
