"""Event dispatch helpers for the FlowPilot router.

This module is intentionally a thin extraction layer. It keeps event names,
payloads, state writes, and persistence behavior owned by `flowpilot_router`
while giving the large external-event entrypoint a table-driven boundary.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable


PrecheckEventHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], str, dict[str, Any], dict[str, Any] | None],
    dict[str, Any],
]
SideEffectEventHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], str, dict[str, Any]],
    None,
]


def _handle_heartbeat_or_manual_resume_requested(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    meta: dict[str, Any],
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    tick = router._append_heartbeat_tick(project_root, run_root, run_state, payload or {})
    router._reset_resume_cycle_for_wakeup(run_state)
    trigger_source = "manual_resume" if str((payload or {}).get("source") or "").startswith("manual") else "heartbeat_resume"
    router._open_role_recovery_transaction(
        project_root,
        run_root,
        run_state,
        trigger_source=trigger_source,
        recovery_scope="all_six_sweep",
        target_role_keys=list(router.CREW_ROLE_KEYS),
        fault_payload=payload or {},
    )
    run_state["flags"]["resume_reentry_requested"] = True
    run_state["flags"]["role_recovery_requested"] = True
    run_state["pending_action"] = None
    record = {
        "event": event,
        "summary": meta["summary"],
        "payload": payload or {},
        "recorded_at": router.utc_now(),
    }
    run_state["events"].append(record)
    router.append_history(run_state, event, {"heartbeat_tick": tick})
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
    router._sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
    router.save_run_state(run_root, run_state)
    return {"ok": True, "event": event, "heartbeat_tick": tick, "resume_requested": True}


def _apply_lifecycle_request(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> None:
    router._write_run_lifecycle_request(project_root, run_root, run_state, event=event, payload=payload)


def _apply_route_activation(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> None:
    del event
    router._write_route_activation(project_root, run_root, run_state, payload)


def _apply_host_heartbeat_binding(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> None:
    del event
    router._write_host_heartbeat_binding(project_root, run_root, run_state, payload)


PRECHECK_EVENT_HANDLERS: dict[str, PrecheckEventHandler] = {
    "heartbeat_or_manual_resume_requested": _handle_heartbeat_or_manual_resume_requested,
}

SIDE_EFFECT_EVENT_HANDLERS: dict[str, SideEffectEventHandler] = {
    "user_requests_run_stop": _apply_lifecycle_request,
    "user_requests_run_cancel": _apply_lifecycle_request,
    "pm_activates_reviewed_route": _apply_route_activation,
    "host_records_heartbeat_binding": _apply_host_heartbeat_binding,
}


def handle_precheck_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    meta: dict[str, Any],
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    handler = PRECHECK_EVENT_HANDLERS.get(event)
    if handler is None:
        return None
    return handler(router, project_root, run_root, run_state, event, meta, payload)


def apply_migrated_event_side_effect(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    handler = SIDE_EFFECT_EVENT_HANDLERS.get(event)
    if handler is None:
        return False
    handler(router, project_root, run_root, run_state, event, payload)
    return True


def finalize_external_event_record(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    meta: dict[str, Any],
    payload: dict[str, Any],
    *,
    flag: str,
    scoped_identity: dict[str, Any] | None,
    model_miss_triage_decision: str | None,
    parent_segment_decision: str | None,
) -> dict[str, Any]:
    for clear_flag in router.GATE_OUTCOME_PASS_CLEAR_FLAGS.get(event, ()):
        run_state.setdefault("flags", {})[clear_flag] = False
    router._clear_active_gate_outcome_block_for_pass(run_state, event=event)
    record = {
        "event": event,
        "summary": meta["summary"],
        "payload": payload,
        "recorded_at": router.utc_now(),
    }
    run_state["flags"][flag] = True
    router._sync_model_gate_flags(run_state, event)
    if event == "pm_accepts_product_behavior_model":
        run_state["flags"]["pm_product_behavior_model_rebuild_requested"] = False
    elif event == "pm_accepts_process_route_model":
        run_state["flags"]["pm_process_route_model_rebuild_requested"] = False
    elif event in {"pm_requests_product_behavior_model_rebuild", "pm_requests_process_route_model_rebuild"}:
        run_state["flags"][flag] = False
    if event in {
        "pm_completes_current_node_from_reviewed_result",
        "pm_completes_parent_node_from_backward_replay",
    } and router._node_completion_event_advanced_to_next_node(
        run_root,
        payload,
    ):
        run_state["flags"][flag] = False
    if event in router.MODEL_MISS_REVIEW_BLOCK_EVENTS:
        run_state["flags"]["pm_model_miss_triage_card_delivered"] = False
        run_state["flags"]["model_miss_triage_closed"] = False
        run_state["flags"]["pm_review_repair_card_delivered"] = False
        run_state["model_miss_triage"] = None
        run_state["model_miss_triage_followup_request"] = None
        run_state["model_miss_evidence_followup_request"] = None
        run_state["model_miss_triage_controlled_stop"] = None
        run_state["flags"]["model_miss_triage_followup_request_pending"] = False
        run_state["flags"]["model_miss_triage_controlled_stop_recorded"] = False
    if (
        event == router.PM_MODEL_MISS_TRIAGE_DECISION_EVENT
        and model_miss_triage_decision not in router.PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES
    ):
        run_state["flags"][flag] = False
    if event == "pm_records_parent_segment_decision" and (parent_segment_decision or "continue") != "continue":
        run_state["flags"][flag] = False
    if event == "pm_absorbs_reviewed_research":
        run_state["flags"]["material_accepted_by_pm"] = True
    run_state["events"].append(record)
    router._mark_scoped_event_recorded(run_state, scoped_identity)
    startup_release: dict[str, Any] | None = None
    if event == "pm_approves_startup_activation":
        startup_release = {
            "released": False,
            "reason": "controller_deliver_mail_required",
            "requires_action": "deliver_mail",
            "mail_id": "user_intake",
            "to_role": "project_manager",
            "source": "pm_startup_activation",
        }
    wait_closure = router._close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="record_external_event",
    )
    if event == "router_direct_material_scan_dispatch_recheck_passed":
        router._finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
        run_state["flags"]["material_scan_dispatch_blocked"] = False
        run_state["material_dispatch_block"] = None
    else:
        router._finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    if event == "reviewer_reports_material_sufficient":
        run_state["material_review"] = "sufficient"
    elif event == "reviewer_reports_material_insufficient":
        run_state["material_review"] = "insufficient"
    history_payload = {"payload": payload, "wait_closure": wait_closure}
    if startup_release is not None:
        history_payload["startup_user_intake_release"] = startup_release
    router.append_history(run_state, event, history_payload)
    role_memory_delta = router._append_role_memory_delta(run_root, run_state, event=event, payload=payload)
    if role_memory_delta is not None:
        deltas = run_state.setdefault("role_memory_deltas", [])
        deltas.append(role_memory_delta)
        run_state["role_memory_deltas"] = deltas[-32:]
    router._resolve_delivered_control_blocker(project_root, run_root, run_state, resolved_by_event=event)
    run_state["pending_action"] = None
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
    router._sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
    router.save_run_state(run_root, run_state)
    result = {"ok": True, "event": event}
    if wait_closure.get("changed"):
        result["wait_closure"] = wait_closure
    return result
