"""Router daemon run-root and lock lifecycle helpers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write


def _resolve_run_root_target(
    router: ModuleType,
    project_root: Path,
    *,
    run_id: str | None = None,
    run_root: str | Path | None = None,
    bootstrap_state: dict[str, Any] | None = None,
) -> Path | None:
    if run_root:
        candidate = Path(run_root)
        return candidate if candidate.is_absolute() else project_root / candidate
    if run_id:
        return project_root / ".flowpilot" / "runs" / str(run_id)
    return router.active_run_root(project_root, bootstrap_state)


def _append_router_daemon_event(
    router: ModuleType,
    run_root: Path,
    event: str,
    details: dict[str, Any] | None = None,
) -> None:
    path = router._router_daemon_event_log_path(run_root)
    assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="append_router_daemon_event")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": router.ROUTER_DAEMON_EVENT_LOG_SCHEMA,
        "event": event,
        "recorded_at": router.utc_now(),
        "details": details or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(router.json.dumps(record, sort_keys=True) + "\n")


def _acquire_router_daemon_lock(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    replace_stale: bool = False,
    process_kind: str | None = None,
    daemon_instance_id: str | None = None,
) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = router.utc_now()
    lock = {
        "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
        "run_id": run_state.get("run_id"),
        "run_root": router.project_relative(project_root, run_root),
        "status": "active",
        "created_at": now,
        "last_tick_at": now,
        "tick_interval_seconds": router.ROUTER_DAEMON_TICK_SECONDS,
        "stale_after_seconds": router.ROUTER_DAEMON_LOCK_STALE_SECONDS,
        "owner": router._router_daemon_owner(
            process_kind=process_kind,
            daemon_instance_id=daemon_instance_id,
        ),
        "single_writer_lock": True,
    }
    try:
        assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="acquire_router_daemon_lock")
        with path.open("x", encoding="utf-8") as handle:
            handle.write(router.json.dumps(lock, indent=2, sort_keys=True) + "\n")
            handle.flush()
            router.os.fsync(handle.fileno())
        router._append_router_daemon_event(run_root, "router_daemon_lock_acquired", {"lock_path": router.project_relative(project_root, path)})
        return lock
    except FileExistsError:
        existing = router.read_daemon_critical_json_if_exists(path)
        existing_liveness = router._router_daemon_lock_liveness(existing)
        existing_status = str(existing.get("status") or "")
        if (
            existing_liveness.get("live")
            or router._router_daemon_lock_has_live_owner(existing_liveness)
            or (
                existing_status in {"active", "stop_requested", "terminal_exit_pending", "cleanup_unconfirmed", "error"}
                and existing_liveness.get("process_live")
            )
        ):
            raise router.RouterError("router daemon lock is already active for this run; attach to the existing daemon instead of starting a second writer")
        if existing_status in {"active", "stop_requested", "terminal_exit_pending", "cleanup_unconfirmed"} and (not replace_stale):
            raise router.RouterError("router daemon lock is stale; restart with --replace-stale-lock so stale ownership is explicit")
        lock["replaced_lock"] = {
            "status": existing.get("status"),
            "created_at": existing.get("created_at"),
            "last_tick_at": existing.get("last_tick_at"),
            "owner": existing.get("owner"),
        }
        router.write_json(path, lock)
        router._append_router_daemon_event(run_root, "router_daemon_lock_replaced", {"lock_path": router.project_relative(project_root, path), "previous_status": existing.get("status")})
        return lock


def _refresh_router_daemon_lock(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    lock = router.read_daemon_critical_json_if_exists(path)
    if lock.get("schema_version") != router.ROUTER_DAEMON_LOCK_SCHEMA:
        raise router.RouterError("router daemon lock is missing or invalid")
    if lock.get("status") != "active":
        return lock
    owner = lock.get("owner") if isinstance(lock.get("owner"), dict) else {}
    current_owner = router._router_daemon_owner(
        process_kind=str(owner.get("process_kind") or "bounded_inline"),
        daemon_instance_id=str(owner.get("daemon_instance_id") or "") or None,
    )
    if (
        owner.get("pid") != current_owner.get("pid")
        or owner.get("start_token") != current_owner.get("start_token")
        or owner.get("daemon_instance_id") != current_owner.get("daemon_instance_id")
    ):
        raise router.RouterError("router daemon lock refresh rejected non-owner process identity")
    lock["status"] = "active"
    lock["last_tick_at"] = router.utc_now()
    router.write_json(path, lock)
    return lock


def _request_router_daemon_stop(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    *,
    reason: str,
) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    lock = router.read_daemon_critical_json_if_exists(path)
    if lock.get("schema_version") != router.ROUTER_DAEMON_LOCK_SCHEMA:
        return {"status": "missing", "reason": reason}
    if lock.get("status") in {"released", "terminal_stopped"}:
        return lock
    lock["status"] = "stop_requested"
    lock["stop_requested_at"] = router.utc_now()
    lock["stop_reason"] = reason
    lock["stop_requested_by"] = router._router_daemon_owner(process_kind="stop_requester")
    router.write_json(path, lock)
    router._append_router_daemon_event(
        run_root,
        "router_daemon_stop_requested",
        {"reason": reason, "owner": lock.get("owner")},
    )
    return lock


def _release_router_daemon_lock(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    *,
    reason: str,
    status: str = "released",
    cleanup_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    lock = router.read_daemon_critical_json_if_exists(path)
    if lock.get("schema_version") != router.ROUTER_DAEMON_LOCK_SCHEMA:
        return {"status": "missing", "reason": reason}
    original_owner = dict(lock.get("owner") or {}) if isinstance(lock.get("owner"), dict) else {}
    lock["status"] = status
    lock["released_at"] = router.utc_now()
    lock["release_reason"] = reason
    lock["released_owner"] = original_owner
    lock["release_actor"] = router._router_daemon_owner(process_kind="release_actor")
    if cleanup_proof is not None:
        lock["cleanup_proof"] = cleanup_proof
    router.write_json(path, lock)
    router._append_router_daemon_event(
        run_root,
        "router_daemon_lock_released",
        {
            "status": status,
            "reason": reason,
            "released_owner": original_owner,
            "cleanup_confirmed": (cleanup_proof or {}).get("cleanup_confirmed"),
        },
    )
    return lock
