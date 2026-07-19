"""Startup and Router daemon liveness helpers for FlowPilot router."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from flowpilot_router_io import _parse_utc_timestamp
from flowpilot_process_liveness import (
    process_descendant_identities as _process_descendant_identities,
    process_identity as _process_identity,
    process_identity_is_live as _process_identity_is_live,
    process_is_live as _process_is_live,
    process_start_token as _process_start_token,
    resolve_current_python_process_launch as _resolve_current_python_process_launch,
    terminate_process_tree as _terminate_process_tree,
)


ROUTER_DAEMON_LOCK_SCHEMA = "flowpilot.router_daemon_lock.v1"
ROUTER_DAEMON_STATUS_SCHEMA = "flowpilot.router_daemon_status.v1"
ROUTER_DAEMON_EVENT_LOG_SCHEMA = "flowpilot.router_daemon_event_log.v1"
ROUTER_DAEMON_TICK_SECONDS = 1
ROUTER_DAEMON_PATROL_CHECK_SECONDS = 300.0
ROUTER_DAEMON_LOCK_STALE_SECONDS = 300
ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS = 5.0
ROUTER_DAEMON_STARTUP_POLL_SECONDS = 0.1
ROUTER_DAEMON_STOP_TIMEOUT_SECONDS = 5.0
ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK = 16


def _router_daemon_owner(
    *,
    process_kind: str | None = None,
    daemon_instance_id: str | None = None,
) -> dict[str, Any]:
    identity = _process_identity(os.getpid())
    owner = {
        **(identity or {"pid": os.getpid(), "start_token": None}),
        "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "",
        "process_kind": process_kind
        or (
            "dedicated_daemon"
            if os.environ.get("FLOWPILOT_ROUTER_DAEMON_DEDICATED") == "1"
            else "bounded_inline"
        ),
    }
    instance_id = daemon_instance_id or os.environ.get("FLOWPILOT_ROUTER_DAEMON_INSTANCE_ID")
    if not instance_id and identity is not None:
        instance_id = f"daemon-{identity['pid']}-{identity['start_token']}"
    owner["daemon_instance_id"] = instance_id
    return owner


def _lock_age_seconds(lock: dict[str, Any]) -> float | None:
    parsed = _parse_utc_timestamp(lock.get("last_tick_at") or lock.get("created_at"))
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()


def _router_daemon_lock_liveness(lock: dict[str, Any]) -> dict[str, Any]:
    owner = lock.get("owner") if isinstance(lock.get("owner"), dict) else {}
    age = _lock_age_seconds(lock)
    schema_ok = lock.get("schema_version") == ROUTER_DAEMON_LOCK_SCHEMA
    status_active = lock.get("status") == "active"
    fresh = age is not None and age <= ROUTER_DAEMON_LOCK_STALE_SECONDS
    pid_live = _process_is_live(owner.get("pid")) if isinstance(owner, dict) else False
    process_live = _process_identity_is_live(owner)
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
        reasons.append("owner_process_identity_mismatch" if pid_live else "owner_process_not_live")
    return {
        "live": bool(schema_ok and status_active and fresh and process_live),
        "schema_ok": schema_ok,
        "status_active": status_active,
        "fresh": fresh,
        "age_seconds": age,
        "process_live": process_live,
        "pid_live": pid_live,
        "reasons": reasons,
        "owner": owner,
    }


def _router_daemon_lock_has_live_owner(liveness: dict[str, Any]) -> bool:
    return bool(
        liveness.get("schema_ok")
        and liveness.get("status_active")
        and liveness.get("process_live")
    )


def _router_daemon_patrol_monitor(
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
        reasons.append("daemon_patrol_timestamp_missing_or_invalid")
    elif float(age) > ROUTER_DAEMON_PATROL_CHECK_SECONDS:
        reasons.append("daemon_patrol_older_than_five_minutes")
    if not liveness.get("process_live"):
        reasons.append("owner_process_liveness_needs_check")
    status = "check_liveness" if reasons else "ok"
    instruction = (
        "Daemon patrol is normal; Controller should stay attached to the existing Router daemon."
        if status == "ok"
        else (
            "Daemon patrol needs a Controller liveness check. Check the daemon process, lock, "
            "and status for this run. If the daemon is alive, stay attached and continue. If it "
            "is dead, recover the current-run Router daemon without starting a second live writer."
        )
    )
    return {
        "status": status,
        "check_after_seconds": ROUTER_DAEMON_PATROL_CHECK_SECONDS,
        "age_seconds": age,
        "last_tick_at": lock.get("last_tick_at") or lock.get("created_at"),
        "controller_liveness_check_required": status == "check_liveness",
        "monitor_can_decide_recovery": False,
        "reasons": reasons,
        "controller_instruction": instruction,
    }


def _router_daemon_lock_is_live(lock: dict[str, Any]) -> bool:
    return bool(_router_daemon_lock_liveness(lock).get("live"))
