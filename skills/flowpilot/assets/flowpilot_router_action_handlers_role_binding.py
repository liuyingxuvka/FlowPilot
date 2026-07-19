"""Current role-agent binding controller-action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome

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
        "role_surface_addressable",
        "current_run_binding_decision",
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
    if raw.get("role_surface_addressable") is not True:
        raise router.RouterError(f"{role} requires role_surface_addressable=true")
    if raw.get("current_run_binding_decision") != "existing_current_agent_reused":
        raise router.RouterError(f"{role} requires current_run_binding_decision=existing_current_agent_reused")
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
        "role_surface_addressable": True,
        "current_run_binding_decision": "existing_current_agent_reused",
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
    if existing:
        if existing.get("schema_version") != "flowpilot.role_binding_ledger.v1":
            raise router.RouterError("current role_binding_ledger schema_version mismatch")
        if str(existing.get("run_id") or "") != str(run_state["run_id"]):
            raise router.RouterError("current role_binding_ledger run_id mismatch")
    existing_slots = existing.get("role_slots") if isinstance(existing.get("role_slots"), list) else []
    preserved_slots: list[dict[str, Any]] = []
    unsupported_roles: list[str] = []
    prior_slot: dict[str, Any] | None = None
    for slot in existing_slots:
        if not isinstance(slot, dict):
            raise router.RouterError("current role_binding_ledger contains a non-object role slot")
        slot_role = str(slot.get("role_key") or "")
        if slot_role not in router.RUNTIME_ROLE_KEYS:
            unsupported_roles.append(slot_role or "<missing>")
            continue
        if slot_role != role:
            preserved_slots.append(slot)
        elif prior_slot is not None:
            raise router.RouterError(f"current role_binding_ledger contains duplicate role slot for {role}")
        else:
            prior_slot = slot
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
    prior_memory = router.read_json_if_exists(memory_path)
    if prior_memory:
        prior_generation = prior_slot.get("role_binding_generation") if isinstance(prior_slot, dict) else None
        if prior_slot is None:
            raise router.RouterError(f"current role memory for {role} has no owning role-binding slot")
        if prior_memory.get("schema_version") != "flowpilot.role_memory.v1":
            raise router.RouterError(f"current role memory schema mismatch for {role}")
        if str(prior_memory.get("run_id") or "") != str(run_state["run_id"]):
            raise router.RouterError(f"current role memory run_id mismatch for {role}")
        if str(prior_memory.get("role_key") or "") != role:
            raise router.RouterError(f"current role memory role_key mismatch for {role}")
        if prior_memory.get("role_binding_generation") != prior_generation:
            raise router.RouterError(f"current role memory generation mismatch for {role}")
        if str(prior_memory.get("agent_id") or "") != str(prior_slot.get("agent_id") or ""):
            raise router.RouterError(f"current role memory agent mismatch for {role}")
    now = router.utc_now()
    memory = {
        **prior_memory,
        "schema_version": "flowpilot.role_memory.v1",
        "run_id": run_state["run_id"],
        "role_key": role,
        "agent_id": record["agent_id"],
        "role_binding_generation": generation,
        "identity_policy": {
            "agent_id_is_diagnostic_only": True,
            "current_authority_source": "role_binding_ledger",
        },
        "current_role_agent_binding": {
            "opened_for_current_run": True,
            "binding_open_result": record["binding_open_result"],
            "role_surface_addressable": record["role_surface_addressable"],
            "current_run_binding_decision": record["current_run_binding_decision"],
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
        "status": prior_memory.get("status") or "available",
        "summary": prior_memory.get("summary") or "",
        "recent_deltas": list(prior_memory.get("recent_deltas") or [])
        if isinstance(prior_memory.get("recent_deltas"), list)
        else [],
        "recorded_at": prior_memory.get("recorded_at") or now,
        "updated_at": now,
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


__all__ = (
    "CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD",
    "CURRENT_ROLE_AGENT_BINDING_RESULT",
    "_normalize_current_role_agent_binding",
    "_write_current_role_agent_binding",
    "_apply_open_current_role_agent",
    "_apply_inject_role_io_protocol",
)
