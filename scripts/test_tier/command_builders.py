"""Command value objects and builders for FlowPilot test tiers."""

from __future__ import annotations

import sys
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TierCommand:
    name: str
    command: tuple[str, ...]
    description: str
    long_running: bool = False
    release_only: bool = False
    background_recommended: bool = False
    background_stage: int = 0


def _py(*args: str) -> tuple[str, ...]:
    return (sys.executable, *args)


def _pytest(name: str, *paths: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "pytest", *paths, "-q"), description=description)


def _unittest(name: str, *modules: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "unittest", "-v", *modules), description=description)


def _unittest_k(name: str, *modules: str, patterns: tuple[str, ...], description: str) -> TierCommand:
    pattern_args: list[str] = []
    for pattern in patterns:
        pattern_args.extend(("-k", pattern))
    return TierCommand(
        name=name,
        command=_py("-m", "unittest", "-v", *pattern_args, *modules),
        description=description,
    )
