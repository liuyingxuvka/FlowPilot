"""Tier command definitions for scripts.run_test_tier."""

from __future__ import annotations

from .command_builders import TierCommand, _py
from .fast_commands import FAST_COMMANDS, ROUTER_PARENT_COMMANDS
from .final_confidence_commands import FINAL_CONFIDENCE_COMMANDS
from .integration_commands import INTEGRATION_COMMANDS, LEGACY_FULL_COMMANDS, RELEASE_COMMANDS
from .router_packet_route_commands import ROUTER_PACKET_COMMANDS, ROUTER_ROUTE_COMMANDS
from .router_startup_foreground_commands import ROUTER_FOREGROUND_COMMANDS, ROUTER_STARTUP_COMMANDS
from .router_terminal_commands import (
    ROUTER_MATERIAL_MODELING_COMMANDS,
    ROUTER_PM_ROLE_WORK_COMMANDS,
    ROUTER_QUALITY_GATE_COMMANDS,
    ROUTER_TERMINAL_COMMANDS,
)

def commands_for_tier(tier: str) -> tuple[TierCommand, ...]:
    mapping: dict[str, tuple[TierCommand, ...]] = {
        "collect": (
            TierCommand(
                name="pytest_collect_tests",
                command=_py("-m", "pytest", "tests", "--collect-only", "-q"),
                description="Collect only from the real tests/ tree.",
            ),
        ),
        "fast": FAST_COMMANDS,
        "router-startup": ROUTER_STARTUP_COMMANDS,
        "router-foreground": ROUTER_FOREGROUND_COMMANDS,
        "router-packets": ROUTER_PACKET_COMMANDS,
        "router-route": ROUTER_ROUTE_COMMANDS,
        "router-pm-role-work": ROUTER_PM_ROLE_WORK_COMMANDS,
        "router-quality-gates": ROUTER_QUALITY_GATE_COMMANDS,
        "router-material-modeling": ROUTER_MATERIAL_MODELING_COMMANDS,
        "router-terminal": ROUTER_TERMINAL_COMMANDS,
        "integration": INTEGRATION_COMMANDS,
        "release": RELEASE_COMMANDS,
        "final-confidence": FINAL_CONFIDENCE_COMMANDS,
        "legacy-full": LEGACY_FULL_COMMANDS,
    }
    if tier == "router":
        return (
            *ROUTER_PARENT_COMMANDS,
            *ROUTER_STARTUP_COMMANDS,
            *ROUTER_FOREGROUND_COMMANDS,
            *ROUTER_PACKET_COMMANDS,
            *ROUTER_ROUTE_COMMANDS,
            *ROUTER_TERMINAL_COMMANDS,
        )
    if tier == "all":
        return (
            *mapping["collect"],
            *FAST_COMMANDS,
            *commands_for_tier("router"),
            *INTEGRATION_COMMANDS,
        )
    return mapping[tier]


def tier_names() -> tuple[str, ...]:
    return (
        "collect",
        "fast",
        "router-startup",
        "router-foreground",
        "router-packets",
        "router-route",
        "router-pm-role-work",
        "router-quality-gates",
        "router-material-modeling",
        "router-terminal",
        "router",
        "integration",
        "release",
        "final-confidence",
        "legacy-full",
        "all",
    )
