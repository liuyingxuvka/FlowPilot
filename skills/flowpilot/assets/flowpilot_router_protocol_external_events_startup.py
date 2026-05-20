"""External event startup shard for the FlowPilot router protocol."""

from __future__ import annotations

from flowpilot_router_protocol_external_event_registry import external_events_for_phase

EXTERNAL_EVENTS_STARTUP = external_events_for_phase('startup')

__all__ = ["EXTERNAL_EVENTS_STARTUP"]
