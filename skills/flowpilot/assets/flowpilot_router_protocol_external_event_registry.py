"""Canonical external-event phase registry for FlowPilot router protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from flowpilot_router_protocol_external_event_data import EXTERNAL_EVENT_DATA_BY_PHASE


@dataclass(frozen=True, slots=True)
class ExternalEventPhase:
    phase: str
    events: Mapping[str, Mapping[str, Any]]


EXTERNAL_EVENT_PHASES: tuple[ExternalEventPhase, ...] = (
    ExternalEventPhase("startup", EXTERNAL_EVENT_DATA_BY_PHASE["startup"]),
    ExternalEventPhase("material", EXTERNAL_EVENT_DATA_BY_PHASE["material"]),
    ExternalEventPhase("route", EXTERNAL_EVENT_DATA_BY_PHASE["route"]),
    ExternalEventPhase("terminal", EXTERNAL_EVENT_DATA_BY_PHASE["terminal"]),
)

EXTERNAL_EVENT_PHASE_BY_NAME = {
    event_name: phase.phase
    for phase in EXTERNAL_EVENT_PHASES
    for event_name in phase.events
}

EXTERNAL_EVENTS: dict[str, dict[str, Any]] = {
    event_name: dict(contract)
    for phase in EXTERNAL_EVENT_PHASES
    for event_name, contract in phase.events.items()
}


def external_events_for_phase(phase_name: str) -> dict[str, dict[str, Any]]:
    for phase in EXTERNAL_EVENT_PHASES:
        if phase.phase == phase_name:
            return {event_name: dict(contract) for event_name, contract in phase.events.items()}
    raise KeyError(phase_name)


def external_event_contract(event: str) -> dict[str, Any]:
    return dict(EXTERNAL_EVENTS[event])


def external_event_phase(event: str) -> str:
    return EXTERNAL_EVENT_PHASE_BY_NAME[event]


__all__ = (
    "ExternalEventPhase",
    "EXTERNAL_EVENT_PHASES",
    "EXTERNAL_EVENT_PHASE_BY_NAME",
    "EXTERNAL_EVENTS",
    "external_events_for_phase",
    "external_event_contract",
    "external_event_phase",
)
