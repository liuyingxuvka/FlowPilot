"""Diagnostics helpers for FlowPilot router daemon runtime."""

from __future__ import annotations

from pathlib import Path
import traceback
from types import ModuleType
from typing import Any


def _router_daemon_artifact_size_summary(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    key_paths = {
        "router_state": router.run_state_path(run_root),
        "router_daemon_status": router._router_daemon_status_path(run_root),
        "router_daemon_lock": router._router_daemon_lock_path(run_root),
        "router_daemon_events": router._router_daemon_event_log_path(run_root),
        "controller_action_ledger": router._controller_action_ledger_path(run_root),
        "router_scheduler_ledger": router._router_scheduler_ledger_path(run_root),
        "packet_ledger": run_root / "packet_ledger.json",
    }
    key_sizes: dict[str, Any] = {}
    for name, path in key_paths.items():
        try:
            key_sizes[name] = {
                "path": router.project_relative(project_root, path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            }
        except OSError as exc:
            key_sizes[name] = {"path": router.project_relative(project_root, path), "exists": False, "error": str(exc)}
    runtime_dir = run_root / "runtime"
    total_bytes = 0
    file_count = 0
    largest: list[dict[str, Any]] = []
    if runtime_dir.exists():
        for path in runtime_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total_bytes += size
            file_count += 1
            largest.append({"path": router.project_relative(project_root, path), "size_bytes": size})
    largest.sort(key=lambda item: int(item.get("size_bytes") or 0), reverse=True)
    return {
        "key_files": key_sizes,
        "runtime_file_count": file_count,
        "runtime_total_bytes": total_bytes,
        "largest_runtime_files": largest[:10],
    }


def _router_daemon_error_diagnostics(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    exc: BaseException,
) -> dict[str, Any]:
    pending = run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else {}
    try:
        current_wait = router._pending_wait_summary(run_state, project_root=project_root)
    except Exception as wait_exc:
        current_wait = {"unavailable": True, "error": str(wait_exc)}
    traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    traceback_limit = 12000
    traceback_payload = traceback_text[-traceback_limit:] if traceback_text else ""
    diagnostics = {
        "type": type(exc).__name__,
        "message": str(exc),
        "current_action": {
            "action_type": pending.get("action_type"),
            "label": pending.get("label"),
            "controller_action_id": pending.get("controller_action_id"),
            "router_scheduler_row_id": pending.get("router_scheduler_row_id"),
        }
        if pending
        else None,
        "current_wait": current_wait,
        "artifact_size_summary": router._router_daemon_artifact_size_summary(project_root, run_root),
        "traceback": traceback_payload,
        "traceback_truncated": bool(traceback_text and len(traceback_text) > traceback_limit),
        "traceback_unavailable_reason": None if traceback_text else "no_traceback_available",
    }
    if isinstance(exc, router.RouterLedgerCorruptionError):
        diagnostics["path"] = str(exc.path)
    return diagnostics
