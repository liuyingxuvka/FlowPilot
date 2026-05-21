"""Runtime JSON read and write helpers for the FlowPilot router."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
import flowpilot_router_io_locks as io_locks


def _read_json_for_runtime_scan(path: Path) -> dict[str, Any] | None:
    if io_locks._is_transient_runtime_json_scan_artifact(path):
        return None
    try:
        io_locks._raise_if_runtime_write_active(path)
        return read_json_if_exists(path)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = io_locks._json_write_lock_liveness(path)
        if write_lock["active"]:
            raise RouterLedgerWriteInProgress(path, write_lock, str(exc)) from exc
        raise


def write_json_atomic(path: Path, payload: dict[str, Any], *, sort_keys: bool = True, verify: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = io_locks._acquire_json_write_lock(path)
    tmp_path = path.with_name(f".tmp-{os.getpid()}-{time.time_ns():x}.json")
    target_verified = False
    try:
        body = json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n"
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + io_locks.RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
        while True:
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError as exc:
                if time.monotonic() >= deadline:
                    write_lock = io_locks._json_write_lock_liveness(path)
                    write_lock["replace_permission_error"] = True
                    raise RouterLedgerWriteInProgress(
                        path,
                        write_lock,
                        f"timed out replacing JSON target after PermissionError: {exc}",
                    ) from exc
                time.sleep(io_locks.RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)
        if verify:
            try:
                read_json(path)
            except OSError as exc:
                write_lock = io_locks._json_write_lock_liveness(path)
                if isinstance(exc, PermissionError) or write_lock.get("active") or write_lock.get("fresh"):
                    write_lock["verification_readback_error"] = True
                    write_lock["verification_error_type"] = type(exc).__name__
                    write_lock["verification_error_message"] = str(exc)
                    raise RouterLedgerWriteInProgress(
                        path,
                        write_lock,
                        f"could not verify JSON target after runtime readback error: {exc}",
                    ) from exc
                raise
            target_verified = True
        else:
            target_verified = io_locks._runtime_json_target_valid(path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        io_locks._cleanup_runtime_json_write_lock(
            path,
            lock_path,
            phase="write_json_atomic_finally",
            target_verified=target_verified,
        )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload, sort_keys=True, verify=True)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RouterError(f"expected JSON object: {path}")
    return payload


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def read_daemon_critical_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = io_locks._json_write_lock_liveness(path)
        if write_lock["active"]:
            raise RouterLedgerWriteInProgress(path, write_lock, str(exc)) from exc
        raise RouterLedgerCorruptionError(path, str(exc)) from exc


def read_json_if_valid(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError):
        return {}
