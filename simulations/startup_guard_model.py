"""Small FlowPilot startup hard-gate model.

This model isolates the failure class where a route-local file or generated
asset appears before canonical state, frontier, crew, and continuation
activation agree. The safe path requires an explicit startup guard pass before
child-skill, imagegen, implementation, or route-execution work can start.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple


REQUIRED_ROLE_MEMORY_PACKETS = 6


@dataclass(frozen=True)
class State:
    route_file_written: bool = False
    canonical_state_written: bool = False
    execution_frontier_written: bool = False
    crew_ledger_current: bool = False
    role_memory_packets_current: int = 0
    continuation_ready: bool = False
    startup_guard_passed: bool = False
    child_skill_started: bool = False
    imagegen_started: bool = False
    implementation_started: bool = False
    route_execution_started: bool = False
    shadow_route_detected: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def startup_ready_for_guard(state: State) -> bool:
    return (
        state.route_file_written
        and state.canonical_state_written
        and state.execution_frontier_written
        and state.crew_ledger_current
        and state.role_memory_packets_current == REQUIRED_ROLE_MEMORY_PACKETS
        and state.continuation_ready
        and not state.shadow_route_detected
    )


def work_started(state: State) -> bool:
    return (
        state.child_skill_started
        or state.imagegen_started
        or state.implementation_started
        or state.route_execution_started
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.route_file_written:
        yield Transition("route_file_written", replace(state, route_file_written=True))
        return
    if not state.canonical_state_written:
        yield Transition("canonical_state_written", replace(state, canonical_state_written=True))
        return
    if not state.execution_frontier_written:
        yield Transition("execution_frontier_written", replace(state, execution_frontier_written=True))
        return
    if not state.crew_ledger_current:
        yield Transition("crew_ledger_current", replace(state, crew_ledger_current=True))
        return
    if state.role_memory_packets_current < REQUIRED_ROLE_MEMORY_PACKETS:
        yield Transition(
            "role_memory_packets_current",
            replace(
                state,
                role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
            ),
        )
        return
    if not state.continuation_ready:
        yield Transition("continuation_ready", replace(state, continuation_ready=True))
        return
    if not state.startup_guard_passed:
        yield Transition("startup_activation_guard_passed", replace(state, startup_guard_passed=True))
        return
    if not state.route_execution_started:
        yield Transition("route_execution_started", replace(state, route_execution_started=True))
        return
    if not state.child_skill_started:
        yield Transition("child_skill_started", replace(state, child_skill_started=True))
        return
    if not state.imagegen_started:
        yield Transition("imagegen_started", replace(state, imagegen_started=True))
        return
    if not state.implementation_started:
        yield Transition("implementation_started", replace(state, implementation_started=True))


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.startup_guard_passed and not startup_ready_for_guard(state):
        failures.append("startup guard passed before canonical startup activation was complete")
    if work_started(state) and not state.startup_guard_passed:
        failures.append("work beyond startup started before the startup guard passed")
    if state.shadow_route_detected and state.startup_guard_passed:
        failures.append("shadow route was allowed through the startup guard")
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "shadow_route_child_skill": State(
            route_file_written=True,
            child_skill_started=True,
            shadow_route_detected=True,
        ),
        "imagegen_before_frontier": State(
            route_file_written=True,
            canonical_state_written=True,
            imagegen_started=True,
        ),
        "implementation_before_crew": State(
            route_file_written=True,
            canonical_state_written=True,
            execution_frontier_written=True,
            implementation_started=True,
        ),
        "guard_before_continuation": State(
            route_file_written=True,
            canonical_state_written=True,
            execution_frontier_written=True,
            crew_ledger_current=True,
            role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
            startup_guard_passed=True,
        ),
        "route_execution_before_guard": State(
            route_file_written=True,
            canonical_state_written=True,
            execution_frontier_written=True,
            crew_ledger_current=True,
            role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
            continuation_ready=True,
            route_execution_started=True,
        ),
    }
