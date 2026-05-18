"""Shared action-handler packet type aliases."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


@dataclass(frozen=True)
class ActionHandlerOutcome:
    result_extra: dict[str, Any] = field(default_factory=dict)
    early_return: dict[str, Any] | None = None


ActionHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any] | None],
    ActionHandlerOutcome,
]
