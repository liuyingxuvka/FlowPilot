"""Gate pass-clear mappings derived from the gate registry."""

from __future__ import annotations

from flowpilot_router_protocol_external_events import EXTERNAL_EVENTS
from flowpilot_router_protocol_gate_registry import (
    GATE_OUTCOME_PASS_CLEAR_FLAGS,
    gate_outcome_pass_clears_events,
)

GATE_OUTCOME_PASS_CLEARS_EVENTS: dict[str, tuple[str, ...]] = gate_outcome_pass_clears_events(EXTERNAL_EVENTS)

__all__ = (
    'GATE_OUTCOME_PASS_CLEAR_FLAGS',
    'GATE_OUTCOME_PASS_CLEARS_EVENTS',
)
