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
