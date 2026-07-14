"""Shared contracts for FlowPilot router action providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ComputeAgain = Callable[[Path, dict[str, Any], Path, int], dict[str, Any]]


@dataclass(frozen=True)
class ProviderOutcome:
    action: dict[str, Any]
    finalized: bool = False


PROVIDER_ORDER = (
    "lifecycle",
    "pending_action",
    "role_recovery",
    "resume",
    "control_blocker",
    "display_plan",
    "controller_boundary",
    "startup_mechanical_audit",
    "startup_display",
    "pending_card_return",
    "system_card_bundle",
    "system_card",
    "resume_wait",
    "mail",
    "research_packet",
    "parent_child_entry",
    "current_node_packet",
    "pm_role_work_request",
    "model_miss_followup",
    "model_miss_controlled_stop",
    "expected_role_decision_wait",
    "no_legal_next_action_blocker",
)
