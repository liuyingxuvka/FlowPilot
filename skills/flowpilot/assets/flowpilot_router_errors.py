"""Shared FlowPilot router exception types."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RouterError(ValueError):
    """Raised when a router operation violates the state machine."""

    def __init__(self, message: str, *, control_blocker: dict[str, Any] | None = None):
        super().__init__(message)
        self.control_blocker = control_blocker


class RouterLedgerCorruptionError(RouterError):
    """Raised when a daemon-critical runtime ledger is not parseable."""

    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(f"runtime ledger is not valid JSON: {path} ({message})")


class RouterLedgerWriteInProgress(RouterError):
    """Raised when a daemon-critical runtime ledger is temporarily locked by a writer."""

    def __init__(self, path: Path, write_lock: dict[str, Any], message: str):
        self.path = path
        self.write_lock = write_lock
        super().__init__(f"runtime ledger write is still in progress: {path} ({message})")


def router_error_record(error: BaseException) -> dict[str, Any]:
    """Return Controller-visible metadata without exposing sealed runtime bodies."""

    record: dict[str, Any] = {
        "error_type": type(error).__name__,
        "message": str(error),
    }
    control_blocker = getattr(error, "control_blocker", None)
    if isinstance(control_blocker, dict):
        record["control_blocker"] = dict(control_blocker)
    path = getattr(error, "path", None)
    if isinstance(path, Path):
        record["path"] = str(path)
    write_lock = getattr(error, "write_lock", None)
    if isinstance(write_lock, dict):
        record["write_lock_status"] = str(write_lock.get("status") or "")
    return record
