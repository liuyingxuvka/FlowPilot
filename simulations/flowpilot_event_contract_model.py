"""FlowGuard model for FlowPilot external-event contract safety.

Risk intent brief:
- Prevent Router from persisting a wait for an event that `record-event` cannot
  later accept.
- Model the PM control-blocker repair decision path, direct Router ACK/check-in
  path, and repair outcome-table path as one event-class contract.
- Protected harms: internal Router action labels or arbitrary strings becoming
  external role events, ACK/check-in receipts replacing semantic role outcomes,
  material repair losing blocker/protocol outcomes, and duplicate PM repair
  decisions creating extra blocker state.
- Hard invariants: every persisted `allowed_external_events` item is registered
  and currently receivable; invalid PM rerun targets are rejected before wait
  state is persisted; PM repair cannot rerun itself; ACK/check-in events stay
  outside role-event waits; direct ACK consumption preserves the next semantic
  wait; material repair exposes success, blocker, and protocol-blocker events;
  duplicate PM repair decisions are idempotent.
- Blindspot: this is a control-plane protocol model. Runtime tests must still
  verify concrete JSON files, helper functions, and installed skill sync.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


PM_REPAIR_EVENT = "pm_records_control_blocker_repair_decision"
INTERNAL_ROUTER_ACTION = "router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"
UNKNOWN_EVENT = "pm_writes_route_darft"
ACK_EVENT = "pm_route_skeleton_card_returned"

PM_ROUTE_DRAFT_EVENT = "pm_writes_route_draft"
REVIEWER_MATERIAL_EVENT = "reviewer_reports_material_sufficient"
GENERIC_BLOCKER_EVENT = "pm_records_control_blocker_followup_blocker"
GENERIC_PROTOCOL_EVENT = "pm_records_control_blocker_protocol_blocker"
MATERIAL_SUCCESS_EVENT = "router_direct_material_scan_dispatch_recheck_passed"
MATERIAL_BLOCKER_EVENT = "router_direct_material_scan_dispatch_recheck_blocked"
MATERIAL_PROTOCOL_EVENT = "router_protocol_blocker_material_scan_dispatch_recheck"

REGISTERED_EXTERNAL_EVENTS = frozenset(
    {
        PM_REPAIR_EVENT,
        PM_ROUTE_DRAFT_EVENT,
        REVIEWER_MATERIAL_EVENT,
        GENERIC_BLOCKER_EVENT,
        GENERIC_PROTOCOL_EVENT,
        MATERIAL_SUCCESS_EVENT,
        MATERIAL_BLOCKER_EVENT,
        MATERIAL_PROTOCOL_EVENT,
    }
)
CURRENTLY_RECEIVABLE_EVENTS = frozenset(
    {
        PM_ROUTE_DRAFT_EVENT,
        REVIEWER_MATERIAL_EVENT,
        GENERIC_BLOCKER_EVENT,
        GENERIC_PROTOCOL_EVENT,
        MATERIAL_SUCCESS_EVENT,
        MATERIAL_BLOCKER_EVENT,
        MATERIAL_PROTOCOL_EVENT,
    }
)
INTERNAL_ROUTER_ACTIONS = frozenset({INTERNAL_ROUTER_ACTION})
DIRECT_ACK_EVENTS = frozenset({ACK_EVENT})
MATERIAL_REPAIR_TARGETS = frozenset({MATERIAL_SUCCESS_EVENT, "reviewer_allows_material_scan_dispatch"})


VALID_ROUTE_DRAFT_RERUN = "valid_route_draft_rerun"
VALID_REVIEWER_MATERIAL_RERUN = "valid_reviewer_material_rerun"
VALID_MATERIAL_REPAIR_OUTCOME_TABLE = "valid_material_repair_outcome_table"
VALID_DIRECT_ACK_PRESERVES_SEMANTIC_WAIT = "valid_direct_ack_preserves_semantic_wait"
VALID_DUPLICATE_PM_REPAIR_IDEMPOTENT = "valid_duplicate_pm_repair_idempotent"

INTERNAL_ROUTER_ACTION_AS_PM_RERUN_TARGET = "internal_router_action_as_pm_rerun_target"
UNKNOWN_STRING_AS_PM_RERUN_TARGET = "unknown_string_as_pm_rerun_target"
PM_REPAIR_EVENT_AS_RERUN_TARGET = "pm_repair_event_as_rerun_target"
WAIT_REQUIRES_FALSE_FLAG = "wait_requires_false_flag"
ACK_EVENT_IN_ALLOWED_EXTERNAL_EVENTS = "ack_event_in_allowed_external_events"
ACK_CONSUMED_SEMANTIC_WAIT_LOST = "ack_consumed_semantic_wait_lost"
GENERIC_REPAIR_COLLAPSED_OUTCOMES = "generic_repair_collapsed_outcomes"
MATERIAL_REPAIR_SUCCESS_ONLY = "material_repair_success_only"
DUPLICATE_PM_REPAIR_CREATED_NEW_BLOCKER = "duplicate_pm_repair_created_new_blocker"
POSTWRITE_CLEANUP_ONLY_FOR_INVALID_WAIT = "postwrite_cleanup_only_for_invalid_wait"

VALID_SCENARIOS = (
    VALID_ROUTE_DRAFT_RERUN,
    VALID_REVIEWER_MATERIAL_RERUN,
    VALID_MATERIAL_REPAIR_OUTCOME_TABLE,
    VALID_DIRECT_ACK_PRESERVES_SEMANTIC_WAIT,
    VALID_DUPLICATE_PM_REPAIR_IDEMPOTENT,
)
NEGATIVE_SCENARIOS = (
    INTERNAL_ROUTER_ACTION_AS_PM_RERUN_TARGET,
    UNKNOWN_STRING_AS_PM_RERUN_TARGET,
    PM_REPAIR_EVENT_AS_RERUN_TARGET,
    WAIT_REQUIRES_FALSE_FLAG,
    ACK_EVENT_IN_ALLOWED_EXTERNAL_EVENTS,
    ACK_CONSUMED_SEMANTIC_WAIT_LOST,
    GENERIC_REPAIR_COLLAPSED_OUTCOMES,
    MATERIAL_REPAIR_SUCCESS_ONLY,
    DUPLICATE_PM_REPAIR_CREATED_NEW_BLOCKER,
    POSTWRITE_CLEANUP_ONLY_FOR_INVALID_WAIT,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One event-contract transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    pm_repair_decision_received: bool = False
    rerun_target: str = "none"
    rerun_target_registered_external: bool = False
    rerun_target_currently_receivable: bool = False
    rerun_target_rejected_before_persist: bool = False
    rerun_target_is_internal_router_action: bool = False
    rerun_target_is_ack_event: bool = False
    rerun_target_is_pm_repair_event: bool = False

    pending_wait_written: bool = False
    allowed_external_events: tuple[str, ...] = ()
    allowed_events_registered: bool = True
    allowed_events_currently_receivable: bool = True
    invalid_wait_ever_persisted: bool = False
    cleanup_after_bad_persist: bool = False

    direct_ack_consumed: bool = False
    ack_event_exposed_as_external_wait: bool = False
    semantic_wait_required_after_ack: bool = False
    semantic_wait_written_after_ack: bool = False
    semantic_wait_valid_after_ack: bool = True

    repair_outcome_table_written: bool = False
    repair_success_event: str = "none"
    repair_blocker_event: str = "none"
    repair_protocol_event: str = "none"
    material_repair_target: bool = False

    duplicate_pm_repair_decision_seen: bool = False
    duplicate_repair_created_new_blocker: bool = False
    duplicate_repair_created_new_transaction: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_ROUTE_DRAFT_RERUN:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=PM_ROUTE_DRAFT_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            pending_wait_written=True,
            allowed_external_events=(PM_ROUTE_DRAFT_EVENT, GENERIC_BLOCKER_EVENT, GENERIC_PROTOCOL_EVENT),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
            repair_outcome_table_written=True,
            repair_success_event=PM_ROUTE_DRAFT_EVENT,
            repair_blocker_event=GENERIC_BLOCKER_EVENT,
            repair_protocol_event=GENERIC_PROTOCOL_EVENT,
        )
    if scenario == VALID_REVIEWER_MATERIAL_RERUN:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=REVIEWER_MATERIAL_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            pending_wait_written=True,
            allowed_external_events=(REVIEWER_MATERIAL_EVENT, GENERIC_BLOCKER_EVENT, GENERIC_PROTOCOL_EVENT),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
            repair_outcome_table_written=True,
            repair_success_event=REVIEWER_MATERIAL_EVENT,
            repair_blocker_event=GENERIC_BLOCKER_EVENT,
            repair_protocol_event=GENERIC_PROTOCOL_EVENT,
        )
    if scenario == VALID_MATERIAL_REPAIR_OUTCOME_TABLE:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=MATERIAL_SUCCESS_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            pending_wait_written=True,
            allowed_external_events=(MATERIAL_SUCCESS_EVENT, MATERIAL_BLOCKER_EVENT, MATERIAL_PROTOCOL_EVENT),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
            repair_outcome_table_written=True,
            material_repair_target=True,
            repair_success_event=MATERIAL_SUCCESS_EVENT,
            repair_blocker_event=MATERIAL_BLOCKER_EVENT,
            repair_protocol_event=MATERIAL_PROTOCOL_EVENT,
        )
    if scenario == VALID_DIRECT_ACK_PRESERVES_SEMANTIC_WAIT:
        return State(
            status="running",
            scenario=scenario,
            direct_ack_consumed=True,
            semantic_wait_required_after_ack=True,
            semantic_wait_written_after_ack=True,
            semantic_wait_valid_after_ack=True,
            pending_wait_written=True,
            allowed_external_events=(PM_ROUTE_DRAFT_EVENT,),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
        )
    if scenario == VALID_DUPLICATE_PM_REPAIR_IDEMPOTENT:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=PM_ROUTE_DRAFT_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            duplicate_pm_repair_decision_seen=True,
            duplicate_repair_created_new_blocker=False,
            duplicate_repair_created_new_transaction=False,
            pending_wait_written=True,
            allowed_external_events=(PM_ROUTE_DRAFT_EVENT, GENERIC_BLOCKER_EVENT, GENERIC_PROTOCOL_EVENT),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
            repair_outcome_table_written=True,
            repair_success_event=PM_ROUTE_DRAFT_EVENT,
            repair_blocker_event=GENERIC_BLOCKER_EVENT,
            repair_protocol_event=GENERIC_PROTOCOL_EVENT,
        )

    if scenario == INTERNAL_ROUTER_ACTION_AS_PM_RERUN_TARGET:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=INTERNAL_ROUTER_ACTION,
            rerun_target_is_internal_router_action=True,
            pending_wait_written=True,
            allowed_external_events=(INTERNAL_ROUTER_ACTION,),
            allowed_events_registered=False,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
        )
    if scenario == UNKNOWN_STRING_AS_PM_RERUN_TARGET:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=UNKNOWN_EVENT,
            pending_wait_written=True,
            allowed_external_events=(UNKNOWN_EVENT,),
            allowed_events_registered=False,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
        )
    if scenario == PM_REPAIR_EVENT_AS_RERUN_TARGET:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=PM_REPAIR_EVENT,
            rerun_target_registered_external=True,
            rerun_target_is_pm_repair_event=True,
            pending_wait_written=True,
            allowed_external_events=(PM_REPAIR_EVENT,),
            allowed_events_registered=True,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
        )
    if scenario == WAIT_REQUIRES_FALSE_FLAG:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=PM_ROUTE_DRAFT_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=False,
            pending_wait_written=True,
            allowed_external_events=(PM_ROUTE_DRAFT_EVENT,),
            allowed_events_registered=True,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
        )
    if scenario == ACK_EVENT_IN_ALLOWED_EXTERNAL_EVENTS:
        return State(
            status="running",
            scenario=scenario,
            ack_event_exposed_as_external_wait=True,
            rerun_target_is_ack_event=True,
            rerun_target=ACK_EVENT,
            pending_wait_written=True,
            allowed_external_events=(ACK_EVENT,),
            allowed_events_registered=False,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
        )
    if scenario == ACK_CONSUMED_SEMANTIC_WAIT_LOST:
        return State(
            status="running",
            scenario=scenario,
            direct_ack_consumed=True,
            semantic_wait_required_after_ack=True,
            semantic_wait_written_after_ack=False,
            semantic_wait_valid_after_ack=False,
        )
    if scenario == GENERIC_REPAIR_COLLAPSED_OUTCOMES:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=PM_ROUTE_DRAFT_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            pending_wait_written=True,
            allowed_external_events=(PM_ROUTE_DRAFT_EVENT,),
            allowed_events_registered=True,
            allowed_events_currently_receivable=True,
            repair_outcome_table_written=True,
            repair_success_event=PM_ROUTE_DRAFT_EVENT,
            repair_blocker_event=PM_ROUTE_DRAFT_EVENT,
            repair_protocol_event=PM_ROUTE_DRAFT_EVENT,
        )
    if scenario == MATERIAL_REPAIR_SUCCESS_ONLY:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=MATERIAL_SUCCESS_EVENT,
            rerun_target_registered_external=True,
            rerun_target_currently_receivable=True,
            material_repair_target=True,
            repair_outcome_table_written=True,
            repair_success_event=MATERIAL_SUCCESS_EVENT,
            repair_blocker_event=MATERIAL_SUCCESS_EVENT,
            repair_protocol_event=MATERIAL_SUCCESS_EVENT,
        )
    if scenario == DUPLICATE_PM_REPAIR_CREATED_NEW_BLOCKER:
        return State(
            status="running",
            scenario=scenario,
            duplicate_pm_repair_decision_seen=True,
            duplicate_repair_created_new_blocker=True,
            duplicate_repair_created_new_transaction=True,
        )
    if scenario == POSTWRITE_CLEANUP_ONLY_FOR_INVALID_WAIT:
        return State(
            status="running",
            scenario=scenario,
            pm_repair_decision_received=True,
            rerun_target=INTERNAL_ROUTER_ACTION,
            rerun_target_is_internal_router_action=True,
            pending_wait_written=True,
            allowed_external_events=(INTERNAL_ROUTER_ACTION,),
            allowed_events_registered=False,
            allowed_events_currently_receivable=False,
            invalid_wait_ever_persisted=True,
            cleanup_after_bad_persist=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def event_contract_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.pending_wait_written:
        if not state.allowed_external_events:
            failures.append("persisted role wait has no allowed external events")
        for event in state.allowed_external_events:
            if event in INTERNAL_ROUTER_ACTIONS:
                failures.append("persisted role wait contains internal Router action")
            if event in DIRECT_ACK_EVENTS or state.ack_event_exposed_as_external_wait:
                failures.append("persisted role wait contains direct ACK/check-in event")
            if event not in REGISTERED_EXTERNAL_EVENTS:
                failures.append("persisted role wait contains unregistered external event")
            if event not in CURRENTLY_RECEIVABLE_EVENTS:
                failures.append("persisted role wait contains event whose prerequisite is not currently satisfied")
        if not state.allowed_events_registered:
            failures.append("persisted role wait contains unregistered external event")
        if not state.allowed_events_currently_receivable:
            failures.append("persisted role wait contains event whose prerequisite is not currently satisfied")

    if state.pm_repair_decision_received:
        invalid_target = (
            state.rerun_target_is_internal_router_action
            or state.rerun_target_is_ack_event
            or state.rerun_target_is_pm_repair_event
            or state.rerun_target not in REGISTERED_EXTERNAL_EVENTS
            or state.rerun_target not in CURRENTLY_RECEIVABLE_EVENTS
        )
        if invalid_target and not state.rerun_target_rejected_before_persist:
            failures.append("invalid PM repair rerun_target was not rejected before persistence")
        if invalid_target and state.pending_wait_written:
            failures.append("invalid PM repair rerun_target produced persisted wait state")
        if (
            not invalid_target
            and state.rerun_target != "none"
            and not (state.rerun_target_registered_external and state.rerun_target_currently_receivable)
        ):
            failures.append("valid PM repair rerun_target was not proven registered and receivable")

    if state.rerun_target_is_internal_router_action and not state.rerun_target_rejected_before_persist:
        failures.append("internal Router action was accepted as PM rerun target")
    if state.rerun_target_is_ack_event and not state.rerun_target_rejected_before_persist:
        failures.append("direct ACK/check-in event was accepted as PM rerun target")
    if state.rerun_target_is_pm_repair_event and not state.rerun_target_rejected_before_persist:
        failures.append("PM repair decision event was accepted as its own rerun target")

    if state.direct_ack_consumed and state.semantic_wait_required_after_ack:
        if not (state.semantic_wait_written_after_ack and state.semantic_wait_valid_after_ack):
            failures.append("direct ACK consumption erased the required semantic role wait")

    if state.repair_outcome_table_written:
        outcome_events = (state.repair_success_event, state.repair_blocker_event, state.repair_protocol_event)
        if any(event == "none" for event in outcome_events):
            failures.append("repair outcome table is missing success, blocker, or protocol-blocker row")
        if len(set(outcome_events)) != 3:
            failures.append("repair outcome table collapsed success, blocker, and protocol-blocker events")

    if state.material_repair_target and state.repair_outcome_table_written:
        expected = (MATERIAL_SUCCESS_EVENT, MATERIAL_BLOCKER_EVENT, MATERIAL_PROTOCOL_EVENT)
        actual = (state.repair_success_event, state.repair_blocker_event, state.repair_protocol_event)
        if actual != expected:
            failures.append("material repair outcome table did not route success, blocker, and protocol outcomes")

    if state.duplicate_pm_repair_decision_seen and (
        state.duplicate_repair_created_new_blocker or state.duplicate_repair_created_new_transaction
    ):
        failures.append("duplicate PM repair decision created new blocker or transaction")

    if state.invalid_wait_ever_persisted and state.cleanup_after_bad_persist:
        failures.append("invalid wait was persisted and only repaired by post-write cleanup")

    return sorted(set(failures))


class EventContractStep:
    """Model one FlowPilot event-contract transition.

    Input x State -> Set(Output x State)
    reads: PM repair decision, event registry, pending wait, ACK/check-in state,
    repair transaction outcome table, duplicate event ledger
    writes: accepted/rejected event contract state and persisted wait boundary
    idempotency: duplicate PM repair decisions cannot create extra blocker or
    repair-transaction state.
    """

    name = "EventContractStep"
    input_description = "control-plane event contract tick"
    output_description = "one event-contract transition"
    reads = (
        "pm_repair_decision",
        "external_event_registry",
        "pending_action",
        "card_ack_state",
        "repair_outcome_table",
        "event_idempotency_ledger",
    )
    writes = (
        "control_blocker_repair_decision",
        "repair_transaction",
        "pending_action_allowed_external_events",
        "event_idempotency_ledger",
    )
    idempotency = "blocker-id scoped PM repair decisions are monotonic"

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

    failures = event_contract_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="event_contract_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not event_contract_failures(state)


def accepted_states_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = event_contract_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe event contract state was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe event contract state was rejected")
    return InvariantResult.pass_()


def persisted_waits_are_recordable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in event_contract_failures(state):
        if "persisted role wait" in failure or "persistence" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def pm_repair_targets_are_external_events(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in event_contract_failures(state):
        if "PM repair rerun_target" in failure or "PM repair decision event" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def ack_keeps_semantic_wait(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.direct_ack_consumed:
        if not (state.semantic_wait_written_after_ack and state.semantic_wait_valid_after_ack):
            return InvariantResult.fail("accepted direct ACK without semantic follow-up wait")
    return InvariantResult.pass_()


def repair_transactions_remain_routable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in event_contract_failures(state):
        if "material repair outcome table" in failure or "duplicate PM repair" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_are_safe",
        description="Only safe event-contract paths can be accepted.",
        predicate=accepted_states_are_safe,
    ),
    Invariant(
        name="persisted_waits_are_recordable",
        description="Every persisted allowed_external_events entry is registered and currently receivable.",
        predicate=persisted_waits_are_recordable,
    ),
    Invariant(
        name="pm_repair_targets_are_external_events",
        description="PM repair rerun targets cannot be internal actions, ACKs, unknown strings, or the PM repair event itself.",
        predicate=pm_repair_targets_are_external_events,
    ),
    Invariant(
        name="ack_keeps_semantic_wait",
        description="Direct Router ACK consumption cannot erase the semantic role decision wait.",
        predicate=ack_keeps_semantic_wait,
    ),
    Invariant(
        name="repair_transactions_remain_routable",
        description="Repair outcome tables and duplicate PM repairs remain routable and idempotent.",
        predicate=repair_transactions_remain_routable,
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
    return Workflow((EventContractStep(),), name="flowpilot_event_contract")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    hazards: dict[str, State] = {}
    for scenario in NEGATIVE_SCENARIOS:
        state = _scenario_state(scenario)
        hazards[scenario] = state
    return hazards


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
    "event_contract_failures",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
