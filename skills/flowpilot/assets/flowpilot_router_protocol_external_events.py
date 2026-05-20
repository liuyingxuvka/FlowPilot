"""Compatibility external event exports derived from the event registry."""

from __future__ import annotations

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_decision_tables import *
from flowpilot_router_protocol_boot_cards import *
from typing import Any

from flowpilot_router_protocol_external_event_registry import (
    EXTERNAL_EVENTS,
    external_event_contract as _external_event_contract,
)


def external_event_contract(event: str) -> dict[str, Any]:
    return _external_event_contract(event)


__all__ = (
    "EXTERNAL_EVENTS",
    "external_event_contract",
)
