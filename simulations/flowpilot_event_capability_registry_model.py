"""FlowGuard model for FlowPilot event-capability registry safety.

Risk intent brief:
- Make every Router wait and repair outcome pass through the same event
  capability facts: node-kind compatibility, repair-origin compatibility,
  producer role, current receivability, rerun-target eligibility, and repair
  outcome-row eligibility.
- Protected harms: parent/module repairs waiting for leaf-only current-node
  packet events, parent backward replay jumping into worker dispatch, success,
  blocker, and protocol-blocker repair rows collapsing onto one business event,
  and Controller waits being delivered to a role that cannot emit the event.
- Hard invariant: an event is not executable merely because it is registered.
  It must be executable for the current route state, repair origin, and usage
  before the Router persists it as a wait, rerun target, or repair outcome.
- Blindspot: this is a capability model. Runtime tests must still prove the
  concrete Router helper functions and persisted JSON artifacts use the same
  registry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


PROJECT_MANAGER = "project_manager"
REVIEWER = "human_like_reviewer"
WORKER = "worker_a"
CONTROLLER = "controller"

NODE_KINDS = ("leaf", "parent", "module", "repair", "pre_route")
PARENT_NODE_KINDS = ("parent", "module")
REPAIR_ORIGINS = ("none", "current_node_result", "parent_backward_replay", "material_dispatch")

PM_REPAIR_EVENT = "pm_records_control_blocker_repair_decision"
ACK_EVENT = "pm_route_skeleton_card_returned"
UNKNOWN_EVENT = "pm_registers_current_node_packte"

CURRENT_NODE_PACKET_EVENT = "pm_registers_current_node_packet"
WORKER_RESULT_EVENT = "worker_current_node_result_returned"
PARENT_TARGETS_EVENT = "pm_builds_parent_backward_targets"
PARENT_REPLAY_PASS_EVENT = "reviewer_passes_parent_backward_replay"
PARENT_REPLAY_BLOCK_EVENT = "reviewer_blocks_parent_backward_replay"
PARENT_SEGMENT_DECISION_EVENT = "pm_records_parent_segment_decision"
PARENT_PROTOCOL_BLOCKER_EVENT = "pm_records_parent_protocol_blocker"
PARENT_COMPLETION_EVENT = "pm_completes_parent_node_from_backward_replay"
GENERIC_BLOCKER_EVENT = "pm_records_control_blocker_followup_blocker"
GENERIC_PROTOCOL_EVENT = "pm_records_control_blocker_protocol_blocker"
MATERIAL_SUCCESS_EVENT = "router_direct_material_scan_dispatch_recheck_passed"
MATERIAL_BLOCKER_EVENT = "router_direct_material_scan_dispatch_recheck_blocked"
MATERIAL_PROTOCOL_EVENT = "router_protocol_blocker_material_scan_dispatch_recheck"

ACK_EVENTS = frozenset({ACK_EVENT})
PARENT_REPAIR_SAFE_EVENTS = frozenset(
    {
        PARENT_TARGETS_EVENT,
        PARENT_REPLAY_PASS_EVENT,
        PARENT_REPLAY_BLOCK_EVENT,
        PARENT_SEGMENT_DECISION_EVENT,
        PARENT_PROTOCOL_BLOCKER_EVENT,
        PARENT_COMPLETION_EVENT,
    }
)
BUSINESS_SUCCESS_EVENTS = frozenset(
    {
        CURRENT_NODE_PACKET_EVENT,
        WORKER_RESULT_EVENT,
        PARENT_TARGETS_EVENT,
        PARENT_REPLAY_PASS_EVENT,
        PARENT_SEGMENT_DECISION_EVENT,
        PARENT_COMPLETION_EVENT,
    }
)


@dataclass(frozen=True)
class EventCapability:
    event_name: str
    producer_role: str
    node_kinds: tuple[str, ...]
    repair_origins: tuple[str, ...]
    waitable: bool = True
    rerun_target: bool = True
    outcome_rows: tuple[str, ...] = ("success",)


EVENT_CAPABILITIES: dict[str, EventCapability] = {
    CURRENT_NODE_PACKET_EVENT: EventCapability(
        event_name=CURRENT_NODE_PACKET_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=("leaf", "repair"),
        repair_origins=("none", "current_node_result"),
        outcome_rows=("success",),
    ),
    WORKER_RESULT_EVENT: EventCapability(
        event_name=WORKER_RESULT_EVENT,
        producer_role=WORKER,
        node_kinds=("leaf", "repair"),
        repair_origins=("none", "current_node_result"),
        outcome_rows=("success",),
    ),
    PARENT_TARGETS_EVENT: EventCapability(
        event_name=PARENT_TARGETS_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("none", "parent_backward_replay"),
        outcome_rows=("success",),
    ),
    PARENT_REPLAY_PASS_EVENT: EventCapability(
        event_name=PARENT_REPLAY_PASS_EVENT,
        producer_role=REVIEWER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("none", "parent_backward_replay"),
        outcome_rows=("success",),
    ),
    PARENT_REPLAY_BLOCK_EVENT: EventCapability(
        event_name=PARENT_REPLAY_BLOCK_EVENT,
        producer_role=REVIEWER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("none", "parent_backward_replay"),
        outcome_rows=("blocker", "protocol_blocker"),
    ),
    PARENT_SEGMENT_DECISION_EVENT: EventCapability(
        event_name=PARENT_SEGMENT_DECISION_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("none", "parent_backward_replay"),
        outcome_rows=("success",),
    ),
    PARENT_PROTOCOL_BLOCKER_EVENT: EventCapability(
        event_name=PARENT_PROTOCOL_BLOCKER_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("parent_backward_replay",),
        outcome_rows=("protocol_blocker",),
    ),
    PARENT_COMPLETION_EVENT: EventCapability(
        event_name=PARENT_COMPLETION_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=PARENT_NODE_KINDS,
        repair_origins=("none", "parent_backward_replay"),
        outcome_rows=("success",),
    ),
    GENERIC_BLOCKER_EVENT: EventCapability(
        event_name=GENERIC_BLOCKER_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=NODE_KINDS,
        repair_origins=("none", "current_node_result"),
        rerun_target=False,
        outcome_rows=("blocker",),
    ),
    GENERIC_PROTOCOL_EVENT: EventCapability(
        event_name=GENERIC_PROTOCOL_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=NODE_KINDS,
        repair_origins=("none", "current_node_result"),
        rerun_target=False,
        outcome_rows=("protocol_blocker",),
    ),
    MATERIAL_SUCCESS_EVENT: EventCapability(
        event_name=MATERIAL_SUCCESS_EVENT,
        producer_role=CONTROLLER,
        node_kinds=NODE_KINDS,
        repair_origins=("material_dispatch",),
        outcome_rows=("success",),
    ),
    MATERIAL_BLOCKER_EVENT: EventCapability(
        event_name=MATERIAL_BLOCKER_EVENT,
        producer_role=CONTROLLER,
        node_kinds=NODE_KINDS,
        repair_origins=("material_dispatch",),
        outcome_rows=("blocker",),
    ),
    MATERIAL_PROTOCOL_EVENT: EventCapability(
        event_name=MATERIAL_PROTOCOL_EVENT,
        producer_role=CONTROLLER,
        node_kinds=NODE_KINDS,
        repair_origins=("material_dispatch",),
        outcome_rows=("protocol_blocker",),
    ),
    PM_REPAIR_EVENT: EventCapability(
        event_name=PM_REPAIR_EVENT,
        producer_role=PROJECT_MANAGER,
        node_kinds=NODE_KINDS,
        repair_origins=REPAIR_ORIGINS,
        waitable=True,
        rerun_target=False,
        outcome_rows=(),
    ),
}

VALID_LEAF_CURRENT_PACKET_WAIT = "valid_leaf_current_packet_wait"
VALID_PARENT_BACKWARD_WAIT = "valid_parent_backward_wait"
VALID_GENERIC_REPAIR_OUTCOME_TABLE = "valid_generic_repair_outcome_table"
VALID_PARENT_REPAIR_OUTCOME_TABLE = "valid_parent_repair_outcome_table"
VALID_MATERIAL_REPAIR_OUTCOME_TABLE = "valid_material_repair_outcome_table"
VALID_WORKER_LEAF_RESULT_WAIT = "valid_worker_leaf_result_wait"

UNREGISTERED_EVENT_ACCEPTED = "unregistered_event_accepted"
FALSE_PRECONDITION_WAIT_ACCEPTED = "false_precondition_wait_accepted"
WRONG_PRODUCER_ROLE_WAIT_ACCEPTED = "wrong_producer_role_wait_accepted"
ACK_EVENT_WAIT_ACCEPTED = "ack_event_wait_accepted"
PARENT_CURRENT_PACKET_WAIT_ACCEPTED = "parent_current_packet_wait_accepted"
PARENT_BACKWARD_RERUN_TARGETS_LEAF_DISPATCH = "parent_backward_rerun_targets_leaf_dispatch"
PARENT_BACKWARD_SUCCESS_OUTCOME_LEAF_EVENT = "parent_backward_success_outcome_leaf_event"
COLLAPSED_REPAIR_OUTCOMES_ON_BUSINESS_EVENT = "collapsed_repair_outcomes_on_business_event"
BLOCKER_OUTCOME_USES_SUCCESS_EVENT = "blocker_outcome_uses_success_event"
PROTOCOL_OUTCOME_USES_SUCCESS_EVENT = "protocol_outcome_uses_success_event"
PM_REPAIR_EVENT_AS_RERUN_TARGET = "pm_repair_event_as_rerun_target"

VALID_SCENARIOS = (
    VALID_LEAF_CURRENT_PACKET_WAIT,
    VALID_PARENT_BACKWARD_WAIT,
    VALID_GENERIC_REPAIR_OUTCOME_TABLE,
    VALID_PARENT_REPAIR_OUTCOME_TABLE,
    VALID_MATERIAL_REPAIR_OUTCOME_TABLE,
    VALID_WORKER_LEAF_RESULT_WAIT,
)
NEGATIVE_SCENARIOS = (
    UNREGISTERED_EVENT_ACCEPTED,
    FALSE_PRECONDITION_WAIT_ACCEPTED,
    WRONG_PRODUCER_ROLE_WAIT_ACCEPTED,
    ACK_EVENT_WAIT_ACCEPTED,
    PARENT_CURRENT_PACKET_WAIT_ACCEPTED,
    PARENT_BACKWARD_RERUN_TARGETS_LEAF_DISPATCH,
    PARENT_BACKWARD_SUCCESS_OUTCOME_LEAF_EVENT,
    COLLAPSED_REPAIR_OUTCOMES_ON_BUSINESS_EVENT,
    BLOCKER_OUTCOME_USES_SUCCESS_EVENT,
    PROTOCOL_OUTCOME_USES_SUCCESS_EVENT,
    PM_REPAIR_EVENT_AS_RERUN_TARGET,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One event-capability evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    active_node_kind: str = "leaf"
    repair_origin: str = "none"
    target_role: str = PROJECT_MANAGER
    currently_receivable: bool = True

    wait_events: tuple[str, ...] = ()
    rerun_target: str = "none"
    repair_success_event: str = "none"
    repair_blocker_event: str = "none"
    repair_protocol_event: str = "none"
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_LEAF_CURRENT_PACKET_WAIT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="none",
            target_role=PROJECT_MANAGER,
            wait_events=(CURRENT_NODE_PACKET_EVENT,),
        )
    if scenario == VALID_PARENT_BACKWARD_WAIT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="parent",
            repair_origin="parent_backward_replay",
            target_role=PROJECT_MANAGER,
            wait_events=(PARENT_SEGMENT_DECISION_EVENT,),
            rerun_target=PARENT_SEGMENT_DECISION_EVENT,
        )
    if scenario == VALID_GENERIC_REPAIR_OUTCOME_TABLE:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="current_node_result",
            target_role=f"{WORKER},{PROJECT_MANAGER}",
            wait_events=(WORKER_RESULT_EVENT, GENERIC_BLOCKER_EVENT, GENERIC_PROTOCOL_EVENT),
            rerun_target=WORKER_RESULT_EVENT,
            repair_success_event=WORKER_RESULT_EVENT,
            repair_blocker_event=GENERIC_BLOCKER_EVENT,
            repair_protocol_event=GENERIC_PROTOCOL_EVENT,
        )
    if scenario == VALID_PARENT_REPAIR_OUTCOME_TABLE:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="module",
            repair_origin="parent_backward_replay",
            target_role=f"{PROJECT_MANAGER},{REVIEWER}",
            wait_events=(PARENT_SEGMENT_DECISION_EVENT, PARENT_REPLAY_BLOCK_EVENT),
            rerun_target=PARENT_SEGMENT_DECISION_EVENT,
            repair_success_event=PARENT_SEGMENT_DECISION_EVENT,
            repair_blocker_event=PARENT_REPLAY_BLOCK_EVENT,
            repair_protocol_event=PARENT_PROTOCOL_BLOCKER_EVENT,
        )
    if scenario == VALID_MATERIAL_REPAIR_OUTCOME_TABLE:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="pre_route",
            repair_origin="material_dispatch",
            target_role=CONTROLLER,
            wait_events=(MATERIAL_SUCCESS_EVENT, MATERIAL_BLOCKER_EVENT, MATERIAL_PROTOCOL_EVENT),
            rerun_target=MATERIAL_SUCCESS_EVENT,
            repair_success_event=MATERIAL_SUCCESS_EVENT,
            repair_blocker_event=MATERIAL_BLOCKER_EVENT,
            repair_protocol_event=MATERIAL_PROTOCOL_EVENT,
        )
    if scenario == VALID_WORKER_LEAF_RESULT_WAIT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="current_node_result",
            target_role=WORKER,
            wait_events=(WORKER_RESULT_EVENT,),
            rerun_target=WORKER_RESULT_EVENT,
        )

    if scenario == UNREGISTERED_EVENT_ACCEPTED:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            target_role=PROJECT_MANAGER,
            wait_events=(UNKNOWN_EVENT,),
        )
    if scenario == FALSE_PRECONDITION_WAIT_ACCEPTED:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            target_role=PROJECT_MANAGER,
            wait_events=(CURRENT_NODE_PACKET_EVENT,),
            currently_receivable=False,
        )
    if scenario == WRONG_PRODUCER_ROLE_WAIT_ACCEPTED:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            target_role=REVIEWER,
            wait_events=(CURRENT_NODE_PACKET_EVENT,),
        )
    if scenario == ACK_EVENT_WAIT_ACCEPTED:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            target_role=PROJECT_MANAGER,
            wait_events=(ACK_EVENT,),
        )
    if scenario == PARENT_CURRENT_PACKET_WAIT_ACCEPTED:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="parent",
            repair_origin="none",
            target_role=PROJECT_MANAGER,
            wait_events=(CURRENT_NODE_PACKET_EVENT,),
        )
    if scenario == PARENT_BACKWARD_RERUN_TARGETS_LEAF_DISPATCH:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="module",
            repair_origin="parent_backward_replay",
            target_role=PROJECT_MANAGER,
            rerun_target=CURRENT_NODE_PACKET_EVENT,
            wait_events=(CURRENT_NODE_PACKET_EVENT,),
        )
    if scenario == PARENT_BACKWARD_SUCCESS_OUTCOME_LEAF_EVENT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="parent",
            repair_origin="parent_backward_replay",
            target_role=PROJECT_MANAGER,
            rerun_target=PARENT_SEGMENT_DECISION_EVENT,
            repair_success_event=CURRENT_NODE_PACKET_EVENT,
            repair_blocker_event=PARENT_REPLAY_BLOCK_EVENT,
            repair_protocol_event=PARENT_REPLAY_BLOCK_EVENT,
        )
    if scenario == COLLAPSED_REPAIR_OUTCOMES_ON_BUSINESS_EVENT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="current_node_result",
            target_role=WORKER,
            rerun_target=WORKER_RESULT_EVENT,
            repair_success_event=WORKER_RESULT_EVENT,
            repair_blocker_event=WORKER_RESULT_EVENT,
            repair_protocol_event=WORKER_RESULT_EVENT,
        )
    if scenario == BLOCKER_OUTCOME_USES_SUCCESS_EVENT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="current_node_result",
            target_role=WORKER,
            rerun_target=WORKER_RESULT_EVENT,
            repair_success_event=WORKER_RESULT_EVENT,
            repair_blocker_event=WORKER_RESULT_EVENT,
            repair_protocol_event=WORKER_RESULT_EVENT,
        )
    if scenario == PROTOCOL_OUTCOME_USES_SUCCESS_EVENT:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="pre_route",
            repair_origin="material_dispatch",
            target_role=CONTROLLER,
            rerun_target=MATERIAL_SUCCESS_EVENT,
            repair_success_event=MATERIAL_SUCCESS_EVENT,
            repair_blocker_event=MATERIAL_BLOCKER_EVENT,
            repair_protocol_event=MATERIAL_SUCCESS_EVENT,
        )
    if scenario == PM_REPAIR_EVENT_AS_RERUN_TARGET:
        return State(
            status="running",
            scenario=scenario,
            active_node_kind="leaf",
            repair_origin="current_node_result",
            target_role=PROJECT_MANAGER,
            rerun_target=PM_REPAIR_EVENT,
            wait_events=(PM_REPAIR_EVENT,),
        )
    raise ValueError(f"unknown scenario: {scenario}")


def _role_set(raw: str) -> set[str]:
    return {part.strip() for part in raw.split(",") if part.strip()}


def _event_failures(
    state: State,
    event_name: str,
    *,
    usage: str,
    outcome_row: str | None = None,
) -> list[str]:
    if event_name == "none":
        return []
    failures: list[str] = []
    if event_name in ACK_EVENTS:
        failures.append("direct ACK/check-in event was accepted as external capability")
    capability = EVENT_CAPABILITIES.get(event_name)
    if capability is None:
        failures.append("event capability row is missing")
        return failures
    if not state.currently_receivable:
        failures.append("event capability precondition is not currently receivable")
    if state.active_node_kind not in capability.node_kinds:
        failures.append("event capability incompatible with active node kind")
    if state.repair_origin not in capability.repair_origins:
        failures.append("event capability incompatible with repair origin")
    if usage == "wait" and not capability.waitable:
        failures.append("event capability is not waitable")
    if usage == "wait" and capability.producer_role not in _role_set(state.target_role):
        failures.append("wait target role does not include event producer role")
    if usage == "rerun_target" and not capability.rerun_target:
        failures.append("event capability cannot be used as repair rerun target")
    if usage == "outcome" and outcome_row and outcome_row not in capability.outcome_rows:
        failures.append(f"repair outcome event is not eligible for {outcome_row} row")
    if state.repair_origin == "parent_backward_replay" and event_name not in PARENT_REPAIR_SAFE_EVENTS:
        failures.append("parent backward replay repair used non-parent-safe event")
    return failures


def event_capability_failures(state: State) -> list[str]:
    failures: list[str] = []
    for event_name in state.wait_events:
        failures.extend(_event_failures(state, event_name, usage="wait"))
    failures.extend(_event_failures(state, state.rerun_target, usage="rerun_target"))
    outcome_events = (
        state.repair_success_event,
        state.repair_blocker_event,
        state.repair_protocol_event,
    )
    outcome_rows = ("success", "blocker", "protocol_blocker")
    if any(event != "none" for event in outcome_events):
        if any(event == "none" for event in outcome_events):
            failures.append("repair outcome table is missing success, blocker, or protocol-blocker row")
        if len(set(outcome_events)) != 3:
            failures.append("repair outcome table collapsed success blocker and protocol-blocker events")
    for row, event_name in zip(outcome_rows, outcome_events):
        failures.extend(_event_failures(state, event_name, usage="outcome", outcome_row=row))
        if row in {"blocker", "protocol_blocker"} and event_name in BUSINESS_SUCCESS_EVENTS:
            failures.append("repair non-success outcome uses success-only business event")
    return sorted(set(failures))


class EventCapabilityRegistryStep:
    """Model one FlowPilot event-capability lookup.

    Input x State -> Set(Output x State)
    reads: external event registry, active node kind, repair origin, producer
    role, currently receivable prerequisites, repair outcome table
    writes: accepted or rejected capability decision before Router persistence
    idempotency: repeated capability lookups are pure and produce the same
    decision for the same registry/state tuple.
    """

    name = "EventCapabilityRegistryStep"
    input_description = "event capability lookup tick"
    output_description = "one event-capability decision"
    reads = (
        "external_event_registry",
        "active_node_kind",
        "repair_origin",
        "producer_role",
        "event_preconditions",
        "repair_outcome_table",
    )
    writes = ("event_capability_decision",)
    idempotency = "capability lookup is deterministic"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = event_capability_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="capability_ok"))


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not event_capability_failures(state)


def accepted_states_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = event_capability_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe event capability state was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe event capability state was rejected")
    return InvariantResult.pass_()


def waits_are_executable_for_current_context(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in event_capability_failures(state):
        if "wait" in failure or "precondition" in failure or "node kind" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def parent_repairs_use_parent_safe_events(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.repair_origin == "parent_backward_replay":
        for event_name in (
            *state.wait_events,
            state.rerun_target,
            state.repair_success_event,
            state.repair_blocker_event,
            state.repair_protocol_event,
        ):
            if event_name != "none" and event_name not in PARENT_REPAIR_SAFE_EVENTS:
                return InvariantResult.fail("accepted parent repair with non-parent-safe event")
    return InvariantResult.pass_()


def repair_outcomes_have_distinct_eligible_events(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in event_capability_failures(state):
        if "repair outcome" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_are_safe",
        description="Only safe event-capability decisions can be accepted.",
        predicate=accepted_states_are_safe,
    ),
    Invariant(
        name="waits_are_executable_for_current_context",
        description="Persisted waits must be executable for node kind, repair origin, producer role, and current prerequisites.",
        predicate=waits_are_executable_for_current_context,
    ),
    Invariant(
        name="parent_repairs_use_parent_safe_events",
        description="Parent backward-replay repairs cannot target leaf-only current-node events.",
        predicate=parent_repairs_use_parent_safe_events,
    ),
    Invariant(
        name="repair_outcomes_have_distinct_eligible_events",
        description="Repair success, blocker, and protocol-blocker rows must use distinct eligible events.",
        predicate=repair_outcomes_have_distinct_eligible_events,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((EventCapabilityRegistryStep(),), name="flowpilot_event_capability_registry")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "event_capability_failures",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "terminal_predicate",
]
