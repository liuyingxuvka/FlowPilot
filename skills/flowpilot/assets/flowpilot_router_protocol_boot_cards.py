"""Startup questions, boot actions, and system-card catalogs extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_decision_tables import *
from flowpilot_router_protocol_card_metadata import (
    CARD_PHASE_BY_ID,
    CARD_REQUIRED_SOURCE_PATHS,
    system_card_metadata_catalog,
)
from flowpilot_router_protocol_planning_cards import (
    PLANNING_SYSTEM_CARD_SEQUENCE,
    planning_system_card_catalog,
)
from flowpilot_router_protocol_runtime_cards import (
    RUNTIME_SYSTEM_CARD_SEQUENCE,
    runtime_system_card_catalog,
)
from flowpilot_router_protocol_startup_catalog import (
    BOOT_ACTIONS,
    PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS,
    STARTUP_QUESTIONS,
    startup_boot_catalog,
)

SYSTEM_CARD_SEQUENCE: tuple[dict[str, Any], ...] = (
    PLANNING_SYSTEM_CARD_SEQUENCE + RUNTIME_SYSTEM_CARD_SEQUENCE
)


def system_card_catalog() -> dict[str, object]:
    """Return externally visible system-card sequence and metadata indexes."""

    return {
        "card_count": len(SYSTEM_CARD_SEQUENCE),
        "card_ids": tuple(card["card_id"] for card in SYSTEM_CARD_SEQUENCE),
        "flags": tuple(card["flag"] for card in SYSTEM_CARD_SEQUENCE),
        "planning_card_count": len(PLANNING_SYSTEM_CARD_SEQUENCE),
        "runtime_card_count": len(RUNTIME_SYSTEM_CARD_SEQUENCE),
        "phase_card_ids": tuple(CARD_PHASE_BY_ID),
        "source_path_card_ids": tuple(CARD_REQUIRED_SOURCE_PATHS),
    }


__all__ = (
    "PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS",
    "STARTUP_QUESTIONS",
    "BOOT_ACTIONS",
    "startup_boot_catalog",
    "SYSTEM_CARD_SEQUENCE",
    "PLANNING_SYSTEM_CARD_SEQUENCE",
    "RUNTIME_SYSTEM_CARD_SEQUENCE",
    "CARD_PHASE_BY_ID",
    "CARD_REQUIRED_SOURCE_PATHS",
    "system_card_catalog",
    "planning_system_card_catalog",
    "runtime_system_card_catalog",
    "system_card_metadata_catalog",
)
