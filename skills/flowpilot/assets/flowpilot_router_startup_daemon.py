"""Startup and Router daemon liveness helpers for FlowPilot router."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from flowpilot_router_io import _parse_utc_timestamp


ROUTER_DAEMON_LOCK_SCHEMA = "flowpilot.router_daemon_lock.v1"
ROUTER_DAEMON_STATUS_SCHEMA = "flowpilot.router_daemon_status.v1"
ROUTER_DAEMON_EVENT_LOG_SCHEMA = "flowpilot.router_daemon_event_log.v1"
ROUTER_DAEMON_TICK_SECONDS = 1
ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS = 5.0
ROUTER_DAEMON_LOCK_STALE_SECONDS = 10
ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS = 5.0
ROUTER_DAEMON_STARTUP_POLL_SECONDS = 0.1
ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK = 16


def _router_daemon_owner() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "",
    }


def _lock_age_seconds(lock: dict[str, Any]) -> float | None:
    parsed = _parse_utc_timestamp(lock.get("last_tick_at") or lock.get("created_at"))
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()


def _process_is_live(pid: object) -> bool:
    try:
        value = int(pid)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    if value == os.getpid():
        return True
    if sys.platform == "win32":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, value)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _router_daemon_lock_liveness(lock: dict[str, Any]) -> dict[str, Any]:
    owner = lock.get("owner") if isinstance(lock.get("owner"), dict) else {}
    age = _lock_age_seconds(lock)
    schema_ok = lock.get("schema_version") == ROUTER_DAEMON_LOCK_SCHEMA
    status_active = lock.get("status") == "active"
    fresh = age is not None and age <= ROUTER_DAEMON_LOCK_STALE_SECONDS
    process_live = _process_is_live(owner.get("pid")) if isinstance(owner, dict) else False
    reasons: list[str] = []
    if not schema_ok:
        reasons.append("invalid_or_missing_lock_schema")
    if not status_active:
        reasons.append(f"lock_status_{lock.get('status') or 'missing'}")
    if age is None:
        reasons.append("missing_or_invalid_lock_timestamp")
    elif not fresh:
        reasons.append("lock_stale")
    if not process_live:
        reasons.append("owner_process_not_live")
    return {
        "live": bool(schema_ok and status_active and fresh and process_live),
        "schema_ok": schema_ok,
        "status_active": status_active,
        "fresh": fresh,
        "age_seconds": age,
        "process_live": process_live,
        "reasons": reasons,
        "owner": owner,
    }


def _router_daemon_lock_has_live_owner(liveness: dict[str, Any]) -> bool:
    return bool(
        liveness.get("schema_ok")
        and liveness.get("status_active")
        and liveness.get("process_live")
    )


def _router_daemon_heartbeat_monitor(
    lock: dict[str, Any],
    liveness: dict[str, Any],
    *,
    status_exists: bool,
    status_ok: bool,
) -> dict[str, Any]:
    age = liveness.get("age_seconds")
    reasons: list[str] = []
    if not status_exists:
        reasons.append("status_file_missing")
    elif not status_ok:
        reasons.append("status_file_invalid")
    if not liveness.get("schema_ok"):
        reasons.append("lock_schema_missing_or_invalid")
    if not liveness.get("status_active"):
        reasons.append(f"lock_status_{lock.get('status') or 'missing'}")
    if age is None:
        reasons.append("heartbeat_timestamp_missing_or_invalid")
    elif float(age) > ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS:
        reasons.append("heartbeat_older_than_five_seconds")
    if not liveness.get("process_live"):
        reasons.append("owner_process_liveness_needs_check")
    status = "check_liveness" if reasons else "ok"
    instruction = (
        "Daemon heartbeat is normal; Controller should stay attached to the existing Router daemon."
        if status == "ok"
        else (
            "Daemon heartbeat needs a Controller liveness check. Check the daemon process, lock, "
            "and status for this run. If the daemon is alive, stay attached and continue. If it "
            "is dead, recover the current-run Router daemon without starting a second live writer."
        )
    )
    return {
        "status": status,
        "check_after_seconds": ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS,
        "age_seconds": age,
        "last_tick_at": lock.get("last_tick_at") or lock.get("created_at"),
        "controller_liveness_check_required": status == "check_liveness",
        "monitor_can_decide_recovery": False,
        "reasons": reasons,
        "controller_instruction": instruction,
    }


def _router_daemon_lock_is_live(lock: dict[str, Any]) -> bool:
    return bool(_router_daemon_lock_liveness(lock).get("live"))
