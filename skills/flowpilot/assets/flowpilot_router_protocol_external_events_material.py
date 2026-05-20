"""External event material shard for the FlowPilot router protocol."""

from __future__ import annotations

from flowpilot_router_protocol_external_event_registry import external_events_for_phase

EXTERNAL_EVENTS_MATERIAL = external_events_for_phase('material')

__all__ = ["EXTERNAL_EVENTS_MATERIAL"]
