"""FlowGuard model for recursive route execution in the new FlowPilot runtime."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_recursive_route_execution"
MAX_SEQUENCE_LENGTH = 18


@dataclass(frozen=True)
class State:
    status: str = "new"
    startup_recorded: bool = False
    pm_planning_packet_accepted: bool = False
    route_materialized: bool = False
    frontier_ready: bool = False
    node_1_packet_loop_closed: bool = False
    node_1_pm_disposition: bool = False
    node_2_packet_loop_closed: bool = False
    node_2_pm_disposition: bool = False
    node_3_packet_loop_closed: bool = False
    node_3_pm_disposition: bool = False
    final_route_wide_ledger_built: bool = False
    terminal_complete: bool = False
    repair_boundary_observed: bool = False
    route_mutation_rewrites_frontier: bool = False
    pm_plan_terminal_complete: bool = False
    missing_node_terminal_complete: bool = False
    wrong_flowguard_target_accepted: bool = False
    stale_node_evidence_accepted: bool = False
    dead_lease_advances_node: bool = False
    mutation_without_frontier_rewrite: bool = False


@dataclass(frozen=True)
class Tick:
    """One recursive-route runtime transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_startup_intake",
    "accept_pm_planning_packet",
    "materialize_route_nodes",
    "initialize_execution_frontier",
    "complete_node_1_packet_loop",
    "record_node_1_pm_disposition",
    "complete_node_2_packet_loop",
    "record_node_2_pm_disposition",
    "complete_node_3_packet_loop",
    "record_node_3_pm_disposition",
    "build_final_route_wide_ledger",
    "complete_terminal_closure",
)


def initial_state() -> State:
    return State()


class RecursiveRouteExecutionStep:
    name = "RecursiveRouteExecutionStep"
    reads = (
        "startup_state",
        "pm_planning_packet",
        "route_nodes",
        "execution_frontier",
        "node_packet_loops",
        "pm_dispositions",
        "route_wide_ledger",
    )
    writes = (
        "route_materialization",
        "frontier_state",
        "node_acceptance",
        "repair_or_mutation_records",
        "terminal_closure",
    )
    input_description = "Input x State: one requested recursive FlowPilot runtime action"
    output_description = "Set(Output x State): legal next runtime states or blocked hazard states"
    idempotency = "each safe transition records current-run evidence and never promotes old route state"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_recursive_route_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("record_startup_intake", replace(state, status="running", startup_recorded=True)),)
    if not state.pm_planning_packet_accepted:
        return (Transition("accept_pm_planning_packet", replace(state, pm_planning_packet_accepted=True)),)
    if not state.route_materialized:
        return (Transition("materialize_route_nodes", replace(state, route_materialized=True)),)
    if not state.frontier_ready:
        return (Transition("initialize_execution_frontier", replace(state, frontier_ready=True)),)
    if not state.node_1_packet_loop_closed:
        return (Transition("complete_node_1_packet_loop", replace(state, node_1_packet_loop_closed=True)),)
    if not state.node_1_pm_disposition:
        return (Transition("record_node_1_pm_disposition", replace(state, node_1_pm_disposition=True)),)
    if not state.node_2_packet_loop_closed:
        return (Transition("complete_node_2_packet_loop", replace(state, node_2_packet_loop_closed=True)),)
    if not state.node_2_pm_disposition:
        return (Transition("record_node_2_pm_disposition", replace(state, node_2_pm_disposition=True)),)
    if not state.node_3_packet_loop_closed:
        return (Transition("complete_node_3_packet_loop", replace(state, node_3_packet_loop_closed=True)),)
    if not state.node_3_pm_disposition:
        return (Transition("record_node_3_pm_disposition", replace(state, node_3_pm_disposition=True)),)
    if not state.final_route_wide_ledger_built:
        return (Transition("build_final_route_wide_ledger", replace(state, final_route_wide_ledger_built=True)),)
    if not state.terminal_complete:
        return (Transition("complete_terminal_closure", replace(state, terminal_complete=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_planning_packet_accepted and not state.startup_recorded:
        failures.append("PM planning packet accepted before startup intake")
    if state.route_materialized and not state.pm_planning_packet_accepted:
        failures.append("route materialized before PM planning packet")
    if state.frontier_ready and not state.route_materialized:
        failures.append("frontier initialized before route materialization")
    if state.node_1_packet_loop_closed and not state.frontier_ready:
        failures.append("node 1 packet loop closed before frontier")
    if state.node_1_pm_disposition and not state.node_1_packet_loop_closed:
        failures.append("node 1 PM disposition recorded before node packet loop closed")
    if state.node_2_packet_loop_closed and not state.node_1_pm_disposition:
        failures.append("node 2 started before node 1 PM disposition")
    if state.node_2_pm_disposition and not state.node_2_packet_loop_closed:
        failures.append("node 2 PM disposition recorded before node packet loop closed")
    if state.node_3_packet_loop_closed and not state.node_2_pm_disposition:
        failures.append("node 3 started before node 2 PM disposition")
    if state.node_3_pm_disposition and not state.node_3_packet_loop_closed:
        failures.append("node 3 PM disposition recorded before node packet loop closed")
    if state.final_route_wide_ledger_built and not state.node_3_pm_disposition:
        failures.append("final route-wide ledger built before all node dispositions")
    if state.terminal_complete and not state.final_route_wide_ledger_built:
        failures.append("terminal closure completed before final route-wide ledger")
    if state.pm_plan_terminal_complete:
        failures.append("PM planning packet chain reached terminal completion")
    if state.missing_node_terminal_complete:
        failures.append("terminal closure passed with an incomplete effective node")
    if state.wrong_flowguard_target_accepted:
        failures.append("wrong FlowGuard modeled target satisfied a node")
    if state.stale_node_evidence_accepted:
        failures.append("stale node evidence was accepted after route/source change")
    if state.dead_lease_advances_node:
        failures.append("dead or inactive lease advanced a node")
    if state.mutation_without_frontier_rewrite:
        failures.append("route mutation did not rewrite execution frontier")
    return failures


def hazard_states() -> dict[str, State]:
    target = target_state()
    return {
        "pm_plan_terminal_complete": replace(target, pm_plan_terminal_complete=True),
        "missing_node_terminal_complete": replace(target, node_3_pm_disposition=False, missing_node_terminal_complete=True),
        "wrong_flowguard_target_accepted": replace(target, wrong_flowguard_target_accepted=True),
        "stale_node_evidence_accepted": replace(target, stale_node_evidence_accepted=True),
        "dead_lease_advances_node": replace(target, dead_lease_advances_node=True),
        "mutation_without_frontier_rewrite": replace(target, mutation_without_frontier_rewrite=True),
    }


def target_state() -> State:
    state = initial_state()
    for label in REQUIRED_SAFE_LABELS:
        transitions = {transition.label: transition for transition in next_safe_states(state)}
        state = transitions[label].state
    return state


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: Any) -> bool:
    return state.status in {"complete", "blocked"}


def state_summary(state: State) -> dict[str, Any]:
    return dict(state.__dict__)


def _invariant(state: State, trace: Any) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "recursive_route_execution_order",
        (
            "PM planning closure must materialize route nodes and frontier, "
            "then execute every node through packet loops and PM disposition "
            "before final route-wide closure."
        ),
        _invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((RecursiveRouteExecutionStep(),), name=MODEL_ID)
