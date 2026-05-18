"""Internal router owner helpers extracted from flowpilot_router.

The public compatibility names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so legacy private helper lookups remain
stable while the implementation body lives outside the facade.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_lifecycle_requests"

TERMINAL_CONTROLLER_ACTION_TYPES = {"write_terminal_summary", "run_lifecycle_terminal"}


def _controller_action_is_terminal_cleanup(entry: dict[str, Any]) -> bool:
    action_type = str(entry.get("action_type") or "")
    action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
    return (
        action_type in TERMINAL_CONTROLLER_ACTION_TYPES
        or str(action.get("action_type") or "") in TERMINAL_CONTROLLER_ACTION_TYPES
        or bool(entry.get("terminal_for_route"))
        or bool(action.get("terminal_for_route"))
    )


def _supersede_nonterminal_controller_work_for_terminal(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    fenced_at: str,
) -> dict[str, Any]:
    action_dir = _controller_actions_dir(run_root)
    action_receipts: list[dict[str, Any]] = []
    if action_dir.exists():
        for action_path in sorted(action_dir.glob("*.json")):
            entry = read_json_if_exists(action_path)
            if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
                continue
            previous_status = str(entry.get("status") or "pending")
            if previous_status in CONTROLLER_ACTION_CLOSED_STATUSES:
                continue
            if _controller_action_is_terminal_cleanup(entry):
                continue
            entry["status"] = "superseded"
            entry["superseded_by"] = event
            entry["terminal_lifecycle_status"] = mode
            entry["controller_may_execute"] = False
            entry["updated_at"] = fenced_at
            write_json(action_path, entry)
            action_receipts.append(
                {
                    "authority": "controller_action",
                    "path": project_relative(project_root, action_path),
                    "action_id": entry.get("action_id"),
                    "action_type": entry.get("action_type"),
                    "previous_status": previous_status,
                    "status": "superseded",
                }
            )

    scheduler_receipts: list[dict[str, Any]] = []
    scheduler_path = _router_scheduler_ledger_path(run_root)
    if scheduler_path.exists():
        ledger = _read_router_scheduler_ledger(project_root, run_root, run_state)
        changed = False
        rows: list[dict[str, Any]] = []
        for row in ledger.get("rows", []):
            if not isinstance(row, dict):
                continue
            action_type = str(row.get("action_type") or "")
            router_state = str(row.get("router_state") or "")
            controller_status = str(row.get("controller_status") or "")
            if (
                action_type not in TERMINAL_CONTROLLER_ACTION_TYPES
                and (
                    router_state in {"queued", "waiting", "receipt_done"}
                    or controller_status in {"pending", "waiting", "in_progress", "blocked", "incomplete", "repair_pending"}
                )
            ):
                row["router_state"] = "superseded"
                row["controller_status"] = "superseded"
                row["superseded_by"] = event
                row["terminal_lifecycle_status"] = mode
                row["updated_at"] = fenced_at
                changed = True
                scheduler_receipts.append(
                    {
                        "authority": "router_scheduler_row",
                        "row_id": row.get("row_id"),
                        "controller_action_id": row.get("controller_action_id"),
                        "action_type": action_type,
                        "status": "superseded",
                    }
                )
            rows.append(row)
        if changed:
            ledger["rows"] = rows
            _write_router_scheduler_ledger(project_root, run_root, run_state, ledger)

    bootstrap_receipt: dict[str, Any] | None = None
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action") if isinstance(bootstrap.get("pending_action"), dict) else None
    if pending and str(pending.get("action_type") or "") not in TERMINAL_CONTROLLER_ACTION_TYPES:
        bootstrap_receipt = {
            "authority": "startup_bootstrap",
            "previous_action_type": pending.get("action_type"),
            "previous_label": pending.get("label"),
            "status": "superseded",
        }
        bootstrap["pending_action"] = None
        append_history(
            bootstrap,
            "startup_bootstrap_pending_action_superseded_by_terminal_lifecycle",
            {
                "event": event,
                "terminal_lifecycle_status": mode,
                "previous_action_type": pending.get("action_type"),
            },
        )
        save_bootstrap_state(project_root, bootstrap)

    _rebuild_controller_action_ledger(project_root, run_root, run_state)
    receipts: list[dict[str, Any]] = [*action_receipts, *scheduler_receipts]
    if bootstrap_receipt:
        receipts.append(bootstrap_receipt)
    return {
        "authority": "terminal_controller_work_fence",
        "path": project_relative(project_root, _controller_action_ledger_path(run_root)),
        "superseded_count": len(receipts),
        "receipts": receipts,
    }


def _write_terminal_lifecycle_fence(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    fenced_at = utc_now()
    run_state["daemon_mode_enabled"] = False
    flags = run_state.setdefault("flags", {})
    flags["terminal_daemon_fence_written"] = True
    flags["terminal_projection_refreshed"] = True
    flags["terminal_next_step_cleared"] = True
    daemon_status = _mark_router_daemon_terminal(
        project_root,
        run_root,
        run_state,
        reason=f"{event}_terminal_fence",
    )
    controller_fence = {
        "authority": "terminal_controller_work_fence",
        "status": "pending",
        "superseded_count": 0,
        "receipts": [],
    }
    fence = {
        "schema_version": "flowpilot.terminal_lifecycle_fence.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "fenced_at": fenced_at,
        "daemon_mode_enabled": False,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "terminal_cleanup_actions_allowed": sorted(TERMINAL_CONTROLLER_ACTION_TYPES),
        "controller_work_fence": controller_fence,
        "router_daemon_status": daemon_status,
    }
    fence_path = run_root / "lifecycle" / "terminal_fence.json"
    write_json(fence_path, fence)
    try:
        controller_fence = _supersede_nonterminal_controller_work_for_terminal(
            project_root,
            run_root,
            run_state,
            mode=mode,
            event=event,
            fenced_at=fenced_at,
        )
    except Exception as exc:
        controller_fence = {
            "authority": "terminal_controller_work_fence",
            "status": "best_effort_failed",
            "superseded_count": 0,
            "receipts": [],
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        append_history(
            run_state,
            "terminal_controller_work_fence_best_effort_failed",
            {
                "event": event,
                "terminal_lifecycle_status": mode,
                "error_type": type(exc).__name__,
            },
        )
    fence["controller_work_fence"] = controller_fence
    write_json(fence_path, fence)
    append_history(
        run_state,
        "terminal_lifecycle_fence_written",
        {
            "event": event,
            "terminal_lifecycle_status": mode,
            "terminal_fence_path": project_relative(project_root, fence_path),
            "superseded_count": controller_fence["superseded_count"],
        },
    )
    return {**fence, "terminal_fence_path": project_relative(project_root, fence_path)}

def _clear_active_control_blocker_for_terminal_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    cleared_at: str,
) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return None
    blocker_id = str(active.get("blocker_id") or "")
    if not blocker_id:
        run_state["active_control_blocker"] = None
        run_state["latest_control_blocker_path"] = None
        return {"authority": "control_blocker", "status": "cleared_missing_blocker_id"}
    resolved = dict(active)
    resolved["resolution_status"] = "superseded_by_terminal_lifecycle"
    resolved["resolved_by_event"] = event
    resolved["resolved_at"] = cleared_at
    resolved["terminal_lifecycle_status"] = mode
    existing = run_state.get("resolved_control_blockers")
    if not isinstance(existing, list):
        existing = []
        run_state["resolved_control_blockers"] = existing
    if not any(isinstance(item, dict) and item.get("blocker_id") == blocker_id for item in existing):
        existing.append(resolved)
    artifact_path = resolve_project_path(project_root, str(active.get("blocker_artifact_path") or ""))
    if artifact_path.exists():
        record = read_json(artifact_path)
        record["resolution_status"] = "superseded_by_terminal_lifecycle"
        record["resolved_by_event"] = event
        record["resolved_at"] = cleared_at
        record["terminal_lifecycle_status"] = mode
        write_json(artifact_path, record)
    run_state["active_control_blocker"] = None
    run_state["latest_control_blocker_path"] = None
    _sync_control_plane_indexes(project_root, run_root, run_state)
    return {
        "authority": "control_blocker",
        "blocker_id": blocker_id,
        "resolution_status": "superseded_by_terminal_lifecycle",
    }

def _write_run_lifecycle_request(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    mode = "cancelled_by_user" if event == "user_requests_run_cancel" else "stopped_by_user"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    cleanup_receipts = payload.get("cleanup_receipts") if isinstance(payload.get("cleanup_receipts"), list) else []
    record = {
        "schema_version": "flowpilot.run_lifecycle.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "requested_by": str(payload.get("requested_by") or "user"),
        "request_event": event,
        "reason": payload.get("reason"),
        "previous_pending_action": previous_pending,
        "active_control_blocker_at_request": active_blocker,
        "cleanup_receipts": cleanup_receipts,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "requested_at": utc_now(),
    }
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    flags = run_state.setdefault("flags", {})
    if mode == "stopped_by_user":
        flags["run_stopped_by_user"] = True
    elif mode == "cancelled_by_user":
        flags["run_cancelled_by_user"] = True
    terminal_fence = _write_terminal_lifecycle_fence(project_root, run_root, run_state, mode=mode, event=event)
    reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event=event)
    record["terminal_fence"] = terminal_fence
    record["cleanup_receipts"] = cleanup_receipts + reconciliation["cleanup_receipts"] + [terminal_fence]
    record["reconciliation"] = reconciliation
    write_json(_lifecycle_record_path(run_root), record)
    append_history(run_state, f"run_{mode}", {"event": event, "lifecycle_path": project_relative(project_root, _lifecycle_record_path(run_root))})

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=event)

def _reconcile_terminal_lifecycle_authorities(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    reconciled_at = utc_now()
    receipts: list[dict[str, Any]] = []
    source_paths: dict[str, str] = {}

    continuation_path = _continuation_binding_path(run_root)
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        source_paths["continuation_binding"] = project_relative(project_root, continuation_path)
        previous_heartbeat_active = bool(continuation.get("heartbeat_active"))
        automation_id = str(continuation.get("host_automation_id") or "")
        automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml" if automation_id else None
        automation_exists = bool(automation_path and automation_path.exists())
        if automation_id and not automation_exists:
            cleanup_status = "missing_verified"
        elif automation_id and previous_heartbeat_active:
            cleanup_status = "external_cleanup_may_be_required"
        else:
            cleanup_status = "inactive_verified"
        continuation["heartbeat_active"] = False
        continuation["lifecycle_status"] = mode
        continuation["terminal_event"] = event
        continuation["terminal_reconciled_at"] = reconciled_at
        continuation["host_automation_cleanup_status"] = cleanup_status
        continuation["host_automation_toml_exists"] = automation_exists if automation_id else None
        continuation["host_automation_checked_path"] = str(automation_path) if automation_path else None
        write_json(continuation_path, continuation)
        receipts.append(
            {
                "authority": "continuation_binding",
                "path": project_relative(project_root, continuation_path),
                "previous_heartbeat_active": previous_heartbeat_active,
                "heartbeat_active": False,
                "host_automation_cleanup_status": continuation["host_automation_cleanup_status"],
                "host_automation_toml_exists": continuation["host_automation_toml_exists"],
            }
        )

    crew_path = run_root / "crew_ledger.json"
    if crew_path.exists():
        crew = read_json(crew_path)
        source_paths["crew_ledger"] = project_relative(project_root, crew_path)
        role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
        live_before = sum(1 for slot in role_slots if isinstance(slot, dict) and str(slot.get("status") or "").startswith("live_"))
        for slot in role_slots:
            if isinstance(slot, dict):
                slot["status"] = "stopped_with_run"
                slot["live_agent_active"] = False
                slot["stopped_at"] = reconciled_at
        crew["lifecycle_status"] = mode
        crew["terminal_reconciled_at"] = reconciled_at
        write_json(crew_path, crew)
        receipts.append(
            {
                "authority": "crew_ledger",
                "path": project_relative(project_root, crew_path),
                "live_role_slots_before": live_before,
                "live_role_slots_after": 0,
            }
        )

    packet_ledger_path = run_root / "packet_ledger.json"
    if packet_ledger_path.exists():
        packet_ledger = read_json(packet_ledger_path)
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger_path)
        previous_status = packet_ledger.get("active_packet_status")
        previous_holder = packet_ledger.get("active_packet_holder")
        packet_ledger["active_packet_status"] = mode
        packet_ledger["active_packet_holder"] = "controller"
        packet_ledger["terminal_lifecycle"] = {
            "status": mode,
            "event": event,
            "previous_active_packet_status": previous_status,
            "previous_active_packet_holder": previous_holder,
            "controller_may_continue_packet_loop": False,
            "reconciled_at": reconciled_at,
        }
        packet_ledger["updated_at"] = reconciled_at
        write_json(packet_ledger_path, packet_ledger)
        receipts.append(
            {
                "authority": "packet_ledger",
                "path": project_relative(project_root, packet_ledger_path),
                "previous_active_packet_status": previous_status,
                "active_packet_status": mode,
            }
        )

    frontier_path = run_root / "execution_frontier.json"
    if frontier_path.exists():
        frontier = read_json(frontier_path)
        source_paths["execution_frontier"] = project_relative(project_root, frontier_path)
        previous_status = frontier.get("status")
        frontier["status"] = mode
        frontier["phase"] = "terminal"
        frontier["terminal"] = True
        frontier["terminal_event"] = event
        frontier["updated_at"] = reconciled_at
        frontier["source"] = event
        write_json(frontier_path, frontier)
        receipts.append(
            {
                "authority": "execution_frontier",
                "path": project_relative(project_root, frontier_path),
                "previous_status": previous_status,
                "status": mode,
            }
        )

    blocker_receipt = _clear_active_control_blocker_for_terminal_lifecycle(
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
        cleared_at=reconciled_at,
    )
    if blocker_receipt:
        receipts.append(blocker_receipt)

    report = {
        "schema_version": "flowpilot.terminal_lifecycle_reconciliation.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "cleanup_receipts": receipts,
        "source_paths": source_paths,
        "reconciled_at": reconciled_at,
    }
    write_json(run_root / "lifecycle" / "terminal_reconciliation.json", report)
    report["reconciliation_path"] = project_relative(project_root, run_root / "lifecycle" / "terminal_reconciliation.json")
    return report

def _write_protocol_dead_end_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    dead_end_path: Path,
    reason: str | None,
) -> None:
    mode = "protocol_dead_end"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    write_json(
        _lifecycle_record_path(run_root),
        {
            "schema_version": "flowpilot.run_lifecycle.v1",
            "run_id": run_state.get("run_id"),
            "status": mode,
            "requested_by": "project_manager",
            "request_event": "pm_declares_startup_protocol_dead_end",
            "reason": reason,
            "protocol_dead_end_path": project_relative(project_root, dead_end_path),
            "previous_pending_action": previous_pending,
            "active_control_blocker_at_request": active_blocker,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "requested_at": utc_now(),
        },
    )
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    append_history(
        run_state,
        "run_protocol_dead_end",
        {"protocol_dead_end_path": project_relative(project_root, dead_end_path)},
    )

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)

def _run_lifecycle_terminal_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    mode = _terminal_lifecycle_mode(run_state)
    if not mode:
        return None
    if not _terminal_summary_written(project_root, run_state, run_root):
        run_state.setdefault("flags", {})["terminal_summary_card_delivered"] = True
        return _terminal_summary_action(project_root, run_state, run_root, mode=mode)
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(
        action_type="run_lifecycle_terminal",
        actor="controller",
        label=f"controller_observes_{mode}",
        summary="This FlowPilot run is terminal; no further route work is authorized.",
        allowed_reads=[lifecycle_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        extra={
            "run_lifecycle_status": mode,
            "terminal_for_route": True,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "allowed_external_events": ["user_requests_run_stop", "user_requests_run_cancel"],
        },
    )

def _try_write_control_blocker_for_exception(
    project_root: Path,
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not _should_materialize_control_blocker(
        error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    ):
        return None
    try:
        bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            return None
        return _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source=source,
            error_message=error_message,
            event=event,
            action_type=action_type,
            payload=payload,
        )
    except Exception:
        try:
            fallback = {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
                "recorded_at": utc_now(),
            }
            flowpilot_root = project_root / ".flowpilot"
            failure_path = flowpilot_root / "control_blocker_materialization_failures.jsonl"
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fallback, sort_keys=True) + "\n")
            fallback["fallback_diagnostic_path"] = project_relative(project_root, failure_path)
            return fallback
        except Exception:
            return {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
            }

_LOCAL_NAMES = set(globals())
