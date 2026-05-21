"""Runtime JSON write-lock helpers for the FlowPilot router."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from flowpilot_process_liveness import process_is_live as _process_is_live
from flowpilot_router_errors import RouterLedgerWriteInProgress
from flowpilot_router_io_paths import utc_now


RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS = 5.0
RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS = 30.0
RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS = 0.02
RUNTIME_JSON_WRITE_LOCK_CLEANUP_RETRY_SECONDS = 0.2


def _json_write_lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".write.lock")


def _json_write_lock_cleanup_log_path(path: Path) -> Path:
    return path.parent / "runtime_json_write_lock_cleanup_failures.jsonl"


def _runtime_json_target_valid(path: Path) -> bool:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(parsed, dict)


def _runtime_json_tmp_artifact_present(path: Path) -> bool:
    try:
        return any(path.parent.glob(".tmp-*.json"))
    except OSError:
        return True


def _json_write_lock_liveness(path: Path) -> dict[str, Any]:
    lock_path = _json_write_lock_path(path)
    if not lock_path.exists():
        return {
            "exists": False,
            "fresh": False,
            "active": False,
            "stale": False,
            "takeover_allowed": False,
            "classification": "missing",
            "path": str(lock_path),
            "age_seconds": None,
            "owner_pid": None,
            "owner_pid_present": False,
            "owner_process_live": False,
            "owner_is_self": False,
            "target_valid_json": _runtime_json_target_valid(path),
            "tmp_artifact_present": _runtime_json_tmp_artifact_present(path),
        }
    try:
        age = time.time() - lock_path.stat().st_mtime
    except OSError:
        age = None
    payload: dict[str, Any] = {}
    try:
        parsed = json.loads(lock_path.read_text(encoding="utf-8-sig"))
        if isinstance(parsed, dict):
            payload = parsed
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    owner_pid_present = "pid" in payload
    owner_pid = payload.get("pid")
    owner_process_live = _process_is_live(owner_pid)
    try:
        owner_is_self = int(owner_pid) == os.getpid()  # type: ignore[arg-type]
    except (TypeError, ValueError):
        owner_is_self = False
    fresh = age is not None and age <= RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS
    stale_by_age = age is not None and age > RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS
    target_valid_json = _runtime_json_target_valid(path)
    tmp_artifact_present = _runtime_json_tmp_artifact_present(path)
    if owner_is_self and owner_process_live and stale_by_age:
        if target_valid_json and not tmp_artifact_present:
            classification = "self_owned_stale_takeover"
            active = False
            takeover_allowed = True
        else:
            classification = "self_owned_stale_unsafe"
            active = True
            takeover_allowed = False
    elif owner_is_self and owner_process_live:
        classification = "active_self_owner"
        active = True
        takeover_allowed = False
    elif owner_process_live:
        classification = "active_live_owner"
        active = True
        takeover_allowed = False
    elif owner_pid_present:
        classification = "dead_owner_takeover"
        active = False
        takeover_allowed = True
    elif stale_by_age:
        classification = "stale_takeover"
        active = False
        takeover_allowed = True
    elif fresh:
        classification = "active_unknown_owner"
        active = True
        takeover_allowed = False
    else:
        classification = "stale_takeover"
        active = False
        takeover_allowed = True
    return {
        "exists": True,
        "fresh": bool(fresh),
        "active": active,
        "stale": bool(stale_by_age and not active),
        "takeover_allowed": takeover_allowed,
        "classification": classification,
        "path": str(lock_path),
        "age_seconds": age,
        "stale_after_seconds": RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS,
        "owner_pid": owner_pid,
        "owner_pid_present": owner_pid_present,
        "owner_process_live": owner_process_live,
        "owner_is_self": owner_is_self,
        "target_valid_json": target_valid_json,
        "tmp_artifact_present": tmp_artifact_present,
    }


def _json_write_lock_takeover_log_path(path: Path) -> Path:
    return path.parent / "runtime_json_write_lock_takeovers.jsonl"


def _record_json_write_lock_takeover(path: Path, liveness: dict[str, Any], *, reason: str) -> None:
    record = {
        "schema_version": "flowpilot.runtime_json_write_lock_takeover.v1",
        "target_path": str(path),
        "lock_path": liveness.get("path") or str(_json_write_lock_path(path)),
        "classification": liveness.get("classification"),
        "reason": reason,
        "owner_pid": liveness.get("owner_pid"),
        "owner_process_live": bool(liveness.get("owner_process_live")),
        "owner_is_self": bool(liveness.get("owner_is_self")),
        "fresh": bool(liveness.get("fresh")),
        "stale": bool(liveness.get("stale")),
        "age_seconds": liveness.get("age_seconds"),
        "target_valid_json": bool(liveness.get("target_valid_json")),
        "tmp_artifact_present": bool(liveness.get("tmp_artifact_present")),
        "recorded_at": utc_now(),
    }
    log_path = _json_write_lock_takeover_log_path(path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def _record_json_write_lock_cleanup_failure(
    path: Path,
    lock_path: Path,
    *,
    error: BaseException,
    phase: str,
    target_verified: bool,
    cleanup_attempts: int,
) -> None:
    record = {
        "schema_version": "flowpilot.runtime_json_write_lock_cleanup_failure.v1",
        "target_path": str(path),
        "lock_path": str(lock_path),
        "phase": phase,
        "pid": os.getpid(),
        "target_verified": bool(target_verified),
        "target_valid_json": _runtime_json_target_valid(path),
        "tmp_artifact_present": _runtime_json_tmp_artifact_present(path),
        "cleanup_attempts": cleanup_attempts,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "recorded_at": utc_now(),
    }
    log_path = _json_write_lock_cleanup_log_path(path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def _unlink_runtime_json_write_lock(lock_path: Path) -> None:
    lock_path.unlink()


def _cleanup_runtime_json_write_lock(
    path: Path,
    lock_path: Path,
    *,
    phase: str,
    target_verified: bool,
    timeout_seconds: float | None = None,
) -> bool:
    if timeout_seconds is None:
        timeout_seconds = RUNTIME_JSON_WRITE_LOCK_CLEANUP_RETRY_SECONDS
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    attempts = 0
    while True:
        attempts += 1
        try:
            _unlink_runtime_json_write_lock(lock_path)
            return True
        except FileNotFoundError:
            return True
        except OSError as exc:
            if time.monotonic() >= deadline:
                _record_json_write_lock_cleanup_failure(
                    path,
                    lock_path,
                    error=exc,
                    phase=phase,
                    target_verified=target_verified,
                    cleanup_attempts=attempts,
                )
                return False
            time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)


def _raise_if_runtime_write_active(path: Path) -> None:
    write_lock = _json_write_lock_liveness(path)
    if write_lock["active"]:
        raise RouterLedgerWriteInProgress(path, write_lock, "active runtime JSON write lock")


def _runtime_write_progress_signature(path: Path, lock_path: Path) -> tuple[object, ...]:
    def _stat_signature(target: Path) -> tuple[bool, int | None, int | None]:
        try:
            stat = target.stat()
        except OSError:
            return (False, None, None)
        return (True, int(stat.st_mtime_ns), int(stat.st_size))

    return (*_stat_signature(path), *_stat_signature(lock_path))


def _wait_for_runtime_json_writer_to_settle(exc: RouterLedgerWriteInProgress) -> dict[str, Any]:
    path = exc.path
    lock_path = _json_write_lock_path(path)
    started = time.monotonic()
    poll_count = 0
    last_liveness = dict(exc.write_lock)
    last_signature = _runtime_write_progress_signature(path, lock_path)
    last_progress_at = started
    progress_count = 0
    while True:
        liveness = _json_write_lock_liveness(path)
        last_liveness = liveness
        signature = _runtime_write_progress_signature(path, lock_path)
        if signature != last_signature:
            last_signature = signature
            last_progress_at = time.monotonic()
            progress_count += 1
        progress_recent = progress_count > 0 and (
            time.monotonic() - last_progress_at <= RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS
        )
        if not liveness.get("active") and not progress_recent:
            return {
                "path": str(path),
                "lock_path": str(lock_path),
                "waited_seconds": max(0.0, time.monotonic() - started),
                "poll_count": poll_count,
                "progress_count": progress_count,
                "initial_liveness": dict(exc.write_lock),
                "final_liveness": last_liveness,
            }
        poll_count += 1
        time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)


def _run_foreground_with_runtime_writer_settlement(
    operation: Callable[[], dict[str, Any]],
    *,
    command_name: str,
) -> dict[str, Any]:
    waits: list[dict[str, Any]] = []
    while True:
        try:
            result = operation()
            break
        except RouterLedgerWriteInProgress as exc:
            waits.append(_wait_for_runtime_json_writer_to_settle(exc))
    if waits:
        result = dict(result)
        result["runtime_write_settlement"] = {
            "waited": True,
            "command": command_name,
            "wait_count": len(waits),
            "waits": waits,
        }
    return result


def _is_transient_runtime_json_scan_artifact(path: Path) -> bool:
    return path.name.startswith(".tmp-") or path.name.endswith(".write.lock")


def _acquire_json_write_lock(path: Path) -> Path:
    lock_path = _json_write_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            liveness = _json_write_lock_liveness(path)
            if liveness.get("takeover_allowed"):
                _record_json_write_lock_takeover(path, liveness, reason=str(liveness.get("classification") or "takeover"))
                if _cleanup_runtime_json_write_lock(
                    path,
                    lock_path,
                    phase=str(liveness.get("classification") or "takeover"),
                    target_verified=bool(liveness.get("target_valid_json")),
                ):
                    continue
            if time.monotonic() >= deadline:
                raise RouterLedgerWriteInProgress(path, liveness, "timed out waiting for JSON write lock")
            time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "schema_version": "flowpilot.runtime_json_write_lock.v1",
                        "path": str(path),
                        "pid": os.getpid(),
                        "created_at": utc_now(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        return lock_path
