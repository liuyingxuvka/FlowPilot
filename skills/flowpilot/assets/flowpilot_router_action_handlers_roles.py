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

CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD = "current_role_agent_binding"
CURRENT_ROLE_AGENT_BINDING_RESULT = "opened_for_current_packet"


def _normalize_current_role_agent_binding(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    role: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    allowed_payload_keys = {
        "runtime_role_assistance_capability_status",
        CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD,
    }
    unsupported = sorted(str(key) for key in payload if key not in allowed_payload_keys)
    if unsupported:
        raise router.RouterError(f"unsupported current role agent payload fields: {', '.join(unsupported)}")
    if payload.get("runtime_role_assistance_capability_status") != "available":
        raise router.RouterError("current role agent binding requires runtime_role_assistance_capability_status=available")
    raw = payload.get(CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD)
    if not isinstance(raw, dict):
        raise router.RouterError(f"current role agent binding requires payload.{CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD}")
    allowed_record_keys = {
        "role_key",
        "agent_id",
        "model_policy",
        "reasoning_effort_policy",
        "binding_open_result",
        "opened_for_run_id",
        "host_liveness_status",
        "liveness_decision",
    }
    extra_record_keys = sorted(str(key) for key in raw if key not in allowed_record_keys)
    if extra_record_keys:
        raise router.RouterError(f"unsupported current role agent binding fields: {', '.join(extra_record_keys)}")
    if raw.get("role_key") != role:
        raise router.RouterError(f"current role agent binding must target role_key={role}")
    agent_id = raw.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise router.RouterError(f"{role} requires a non-empty current role agent_id")
    if raw.get("model_policy") != router.ROLE_BINDING_MODEL_POLICY:
        raise router.RouterError(f"{role} requires model_policy={router.ROLE_BINDING_MODEL_POLICY}")
    if raw.get("reasoning_effort_policy") != router.ROLE_BINDING_REASONING_EFFORT_POLICY:
        raise router.RouterError(f"{role} requires reasoning_effort_policy={router.ROLE_BINDING_REASONING_EFFORT_POLICY}")
    if raw.get("binding_open_result") != CURRENT_ROLE_AGENT_BINDING_RESULT:
        raise router.RouterError(f"{role} requires binding_open_result={CURRENT_ROLE_AGENT_BINDING_RESULT}")
    if raw.get("opened_for_run_id") != run_state["run_id"]:
        raise router.RouterError(f"{role} must be opened_for_run_id={run_state['run_id']}")
    if raw.get("host_liveness_status") != "active":
        raise router.RouterError(f"{role} requires active host_liveness_status")
    if raw.get("liveness_decision") != "confirmed_existing_agent":
        raise router.RouterError(f"{role} requires liveness_decision=confirmed_existing_agent")
    core_prompt_path = router._role_core_prompt_path(run_root, role)
    return {
        "role_key": role,
        "status": "live_agent_started",
        "agent_id": agent_id.strip(),
        "model_policy": router.ROLE_BINDING_MODEL_POLICY,
        "reasoning_effort_policy": router.ROLE_BINDING_REASONING_EFFORT_POLICY,
        "preferred_reasoning_effort": router.ROLE_BINDING_PREFERRED_REASONING_EFFORT,
        "binding_open_result": CURRENT_ROLE_AGENT_BINDING_RESULT,
        "opened_for_run_id": run_state["run_id"],
        "host_liveness_status": "active",
        "liveness_decision": "confirmed_existing_agent",
        "host_liveness_verified": True,
        "core_prompt_path": router.project_relative(project_root, core_prompt_path),
        "core_prompt_hash": router._path_hash(core_prompt_path),
        "recorded_at": router.utc_now(),
    }


def _write_current_role_agent_binding(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    role: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    startup_answers = run_state.get("startup_answers") if isinstance(run_state.get("startup_answers"), dict) else {}
    if startup_answers.get("background_collaboration_authorized") is not True:
        raise router.RouterError("current role agent binding requires background_collaboration_authorized=true")
    record = _normalize_current_role_agent_binding(router, project_root, run_root, run_state, role, payload)
    role_binding_path = run_root / "role_binding_ledger.json"
    existing = router.read_json_if_exists(role_binding_path)
    existing_slots = existing.get("role_slots") if isinstance(existing.get("role_slots"), list) else []
    preserved_slots: list[dict[str, Any]] = []
    unsupported_roles: list[str] = []
    for slot in existing_slots:
        if not isinstance(slot, dict):
            raise router.RouterError("current role_binding_ledger contains a non-object role slot")
        slot_role = str(slot.get("role_key") or "")
        if slot_role not in router.RUNTIME_ROLE_KEYS:
            unsupported_roles.append(slot_role or "<missing>")
            continue
        if slot_role != role:
            preserved_slots.append(slot)
    if unsupported_roles:
        raise router.RouterError(f"current role_binding_ledger contains unsupported role slots: {', '.join(unsupported_roles)}")
    generation = int(existing.get("role_binding_generation") or 0) + 1 if existing else 1
    record["role_binding_generation"] = generation
    record["role_binding_epoch"] = generation
    slots = [*preserved_slots, record]
    role_order = {role_key: index for index, role_key in enumerate(router.RUNTIME_ROLE_KEYS)}
    slots.sort(key=lambda item: role_order.get(str(item.get("role_key") or ""), 999))
    memory_root = run_root / "role_binding_memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    memory_path = router._role_memory_path(run_root, role)
    memory = {
        "schema_version": "flowpilot.role_memory.v1",
        "run_id": run_state["run_id"],
        "role_key": role,
        "agent_id": record["agent_id"],
        "identity_policy": {
            "agent_id_is_diagnostic_only": True,
            "current_authority_source": "role_binding_ledger",
        },
        "current_role_agent_binding": {
            "opened_for_current_run": True,
            "binding_open_result": record["binding_open_result"],
            "host_liveness_status": record["host_liveness_status"],
            "liveness_decision": record["liveness_decision"],
            "source_action": "open_current_role_agent",
        },
        "core_prompt_path": record["core_prompt_path"],
        "core_prompt_hash": record["core_prompt_hash"],
        "controller_decision_authority": False,
        "role_memory_used_for_completion_authority": False,
        "last_rehydration": {
            "historical_agent_id_reused": False,
            "current_role_agent_binding": True,
        },
        "recorded_at": router.utc_now(),
    }
    router.write_json(memory_path, memory)
    ledger = {
        "schema_version": "flowpilot.role_binding_ledger.v1",
        "run_id": run_state["run_id"],
        "role_binding_mode": "current_on_demand_role_binding",
        "background_collaboration_authorized": True,
        "runtime_role_assistance_capability_status": "available",
        "role_binding_generation": generation,
        "role_slots": slots,
        "role_binding_memory_paths": [
            router.project_relative(project_root, router._role_memory_path(run_root, str(slot["role_key"])))
            for slot in slots
            if (router._role_memory_path(run_root, str(slot["role_key"]))).exists()
        ],
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
        "updated_at": router.utc_now(),
    }
    router.write_json(role_binding_path, ledger)
    receipts = router._append_role_io_protocol_injections(
        project_root,
        run_root,
        str(run_state["run_id"]),
        [record],
        default_lifecycle_phase="current_role_agent_binding",
        resume_tick_id=router._latest_resume_tick_id(run_state),
        source_action="open_current_role_agent",
    )
    run_state.setdefault("flags", {})[f"current_role_agent_bound_{role}"] = True
    run_state["flags"]["background_collaboration_authorized"] = True
    run_state.setdefault("current_role_agent_bindings", {})[role] = {
        "role_binding_ledger_path": router.project_relative(project_root, role_binding_path),
        "role_binding_memory_path": router.project_relative(project_root, memory_path),
        "agent_id": record["agent_id"],
        "role_binding_generation": generation,
        "opened_at": router.utc_now(),
    }
    return {
        "role_key": role,
        "agent_id": record["agent_id"],
        "role_binding_ledger_path": router.project_relative(project_root, role_binding_path),
        "role_binding_memory_path": router.project_relative(project_root, memory_path),
        "role_io_protocol_receipts": receipts,
    }


def _apply_open_current_role_agent(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    role = str(pending.get("target_role_key") or pending.get("to_role") or "")
    if role not in router.RUNTIME_ROLE_KEYS:
        raise router.RouterError("open_current_role_agent requires a current runtime role")
    result = _write_current_role_agent_binding(router, project_root, run_root, run_state, role, payload or {})
    return ActionHandlerOutcome(result_extra={"current_role_agent_binding": result})


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
    if role not in router.RUNTIME_ROLE_KEYS or not agent_id:
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
    role_binding_memory_files = sorted((run_root / "role_binding_memory").glob("*.json")) if (run_root / "role_binding_memory").exists() else []
    display_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    role_recovery_context = router._role_recovery_ready_context(project_root, run_root, run_state)
    roles_ready_from_recovery = role_recovery_context is not None
    pm_resume_decision_required = True
    if role_recovery_context is not None:
        recovery_report = role_recovery_context["report"]
        pm_resume_decision_required = bool(recovery_report.get("pm_decision_required_before_normal_work"))
    ambiguous_state = bool(missing) or (
        len(role_binding_memory_files) != len(router.RUNTIME_ROLE_KEYS) and not roles_ready_from_recovery
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
        "role_binding_memory_count": len(role_binding_memory_files),
        "role_binding_memory_ready_for_rehydration": len(role_binding_memory_files) == len(router.RUNTIME_ROLE_KEYS),
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

__all__ = (
    '_apply_open_current_role_agent',
    '_apply_inject_role_io_protocol',
    '_apply_deliver_mail',
    '_apply_controller_repair_work_packet',
    '_apply_load_role_recovery_state',
    '_apply_recover_role_bindings',
    '_apply_load_resume_state',
    '_apply_rehydrate_role_bindings',
    '_apply_write_display_surface_status',
    '_apply_handle_control_blocker',
)
