"""External event catalog extracted from ``flowpilot_router_protocol_catalog.py``.

The parent preserves the public EXTERNAL_EVENTS table and lookup helper while
child modules own declarative event families.
"""

from __future__ import annotations

from typing import Any

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_decision_tables import *
from flowpilot_router_protocol_boot_cards import *
from flowpilot_router_protocol_external_events_material import EXTERNAL_EVENTS_MATERIAL
from flowpilot_router_protocol_external_events_route import EXTERNAL_EVENTS_ROUTE
from flowpilot_router_protocol_external_events_startup import EXTERNAL_EVENTS_STARTUP
from flowpilot_router_protocol_external_events_terminal import EXTERNAL_EVENTS_TERMINAL

EXTERNAL_EVENTS: dict[str, dict[str, Any]] = {
    **EXTERNAL_EVENTS_STARTUP,
    **EXTERNAL_EVENTS_MATERIAL,
    **EXTERNAL_EVENTS_ROUTE,
    **EXTERNAL_EVENTS_TERMINAL,
}


def external_event_contract(event: str) -> dict[str, Any]:
    return dict(EXTERNAL_EVENTS[event])


__all__ = (
    "EXTERNAL_EVENTS",
    "external_event_contract",
)
