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
