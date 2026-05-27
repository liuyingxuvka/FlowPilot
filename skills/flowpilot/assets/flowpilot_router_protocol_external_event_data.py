"""Canonical external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_external_event_data_material import MATERIAL_EXTERNAL_EVENT_DATA
from flowpilot_router_protocol_external_event_data_route import ROUTE_EXTERNAL_EVENT_DATA
from flowpilot_router_protocol_external_event_data_startup import STARTUP_EXTERNAL_EVENT_DATA
from flowpilot_router_protocol_external_event_data_terminal import TERMINAL_EXTERNAL_EVENT_DATA

EXTERNAL_EVENT_DATA_BY_PHASE: dict[str, dict[str, dict[str, Any]]] = {
    'startup': STARTUP_EXTERNAL_EVENT_DATA,
    'material': MATERIAL_EXTERNAL_EVENT_DATA,
    'route': ROUTE_EXTERNAL_EVENT_DATA,
    'terminal': TERMINAL_EXTERNAL_EVENT_DATA,
}

__all__ = ["EXTERNAL_EVENT_DATA_BY_PHASE"]
