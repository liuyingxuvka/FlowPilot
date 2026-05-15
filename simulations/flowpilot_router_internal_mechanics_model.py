"""FlowGuard model for FlowPilot Router-internal mechanical actions.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  ownership refactor that lets the Router consume local mechanical work
  internally while preserving Controller work packages for host and role
  interactions.
- Guards against the bug class where Router bookkeeping leaks into Controller
  rows, Controller-owned role/host work is swallowed by Router, repeated ticks
  duplicate local side effects, missing external evidence is marked done, or
  local projection is treated as user-visible confirmation.
- Update and run this model whenever FlowPilot changes action ownership,
  Router daemon queueing, Controller action row creation, local proof writers,
  ACK/wait reconciliation, or display projection behavior.
- Companion check command:
  `python simulations/run_flowpilot_router_internal_mechanics_checks.py`.

Risk intent brief:
- Protected harm: Controller becomes a button-pusher for Router bookkeeping,
  or the opposite bug appears and Router bypasses Controller for host/role
  communication.
- Model-critical state: action ownership classification, Controller row
  writes, Router-internal evidence/proof writes, external evidence presence,
  wait/blocker state, side-effect idempotency, sealed-body access, user-display
  confirmation, host boundary, and role-facing contact.
- Adversarial branches: local action still writes a Controller row, Controller
  work package is marked done internally, role interaction bypasses Controller,
  sealed body is read during local work, missing ACK/result becomes done,
  repeated ticks repeat side effects, display projection is counted as user
  confirmation, host-boundary work is consumed locally, and internal failure is
  recorded as success.
- Hard invariants: Router-internal actions never create Controller rows;
  Controller work packages must not be self-completed by Router; Router must
  not read sealed bodies or directly contact roles; missing external evidence
  records wait/blocker rather than done; local side effects are idempotent; and
  display projection cannot prove user display.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


LOCAL_CHECK_CONSUMED_INTERNALLY = "local_check_consumed_internally"
MISSING_ACK_RECORDS_WAIT_NOT_DONE = "missing_ack_records_wait_not_done"
ACK_PRESENT_ADVANCES_ONCE = "ack_present_advances_once"
LOCAL_PROOF_WRITTEN_ONCE = "local_proof_written_once"
DISPLAY_PROJECTION_SPLIT = "display_projection_split"
CONTROLLER_WORK_PACKAGE_PRESERVED = "controller_work_package_preserved"
HOST_BOUNDARY_PRESERVED = "host_boundary_preserved"
ROLE_RELAY_PRESERVED = "role_relay_preserved"

ROUTER_INTERNAL_LEAKED_TO_CONTROLLER_ROW = "router_internal_leaked_to_controller_row"
CONTROLLER_WORK_PACKAGE_SWALLOWED_BY_ROUTER = "controller_work_package_swallowed_by_router"
ROLE_INTERACTION_BYPASSED_CONTROLLER = "role_interaction_bypassed_controller"
SEALED_BODY_READ_DURING_INTERNAL_WORK = "sealed_body_read_during_internal_work"
MISSING_EXTERNAL_EVIDENCE_MARKED_DONE = "missing_external_evidence_marked_done"
ROUTER_INTERNAL_REPEATED_SIDE_EFFECT = "router_internal_repeated_side_effect"
DISPLAY_PROJECTION_CLAIMED_AS_USER_CONFIRMATION = "display_projection_claimed_as_user_confirmation"
HOST_BOUNDARY_CONSUMED_LOCALLY = "host_boundary_consumed_locally"
ROUTER_INTERNAL_FAILURE_MARKED_DONE = "router_internal_failure_marked_done"

VALID_SCENARIOS = (
    LOCAL_CHECK_CONSUMED_INTERNALLY,
    MISSING_ACK_RECORDS_WAIT_NOT_DONE,
    ACK_PRESENT_ADVANCES_ONCE,
    LOCAL_PROOF_WRITTEN_ONCE,
    DISPLAY_PROJECTION_SPLIT,
    CONTROLLER_WORK_PACKAGE_PRESERVED,
    HOST_BOUNDARY_PRESERVED,
    ROLE_RELAY_PRESERVED,
)

NEGATIVE_SCENARIOS = (
    ROUTER_INTERNAL_LEAKED_TO_CONTROLLER_ROW,
    CONTROLLER_WORK_PACKAGE_SWALLOWED_BY_ROUTER,
    ROLE_INTERACTION_BYPASSED_CONTROLLER,
    SEALED_BODY_READ_DURING_INTERNAL_WORK,
    MISSING_EXTERNAL_EVIDENCE_MARKED_DONE,
    ROUTER_INTERNAL_REPEATED_SIDE_EFFECT,
    DISPLAY_PROJECTION_CLAIMED_AS_USER_CONFIRMATION,
    HOST_BOUNDARY_CONSUMED_LOCALLY,
    ROUTER_INTERNAL_FAILURE_MARKED_DONE,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One Router ownership decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"

    classified: bool = False
    action_type: str = "none"
    action_owner: str = "none"  # none | router_internal | controller_work_package | host_boundary

    controller_row_written: bool = False
    router_event_written: bool = False
    router_proof_written: bool = False
    router_wait_recorded: bool = False
    router_blocker_written: bool = False
    done_recorded: bool = False
    failure_seen: bool = False
    side_effect_count: int = 0

    external_evidence_required: bool = False
    external_evidence_present: bool = False
    host_automation_required: bool = False
    host_proof_present: bool = False
    role_interaction_required: bool = False
    system_card_or_packet_delivery: bool = False
    role_contacted_by_router: bool = False

    sealed_body_read: bool = False
    display_projection_written: bool = False
    user_display_confirmation_required: bool = False
    user_display_confirmed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    defaults = {
        "status": "accepted",
        "scenario": scenario,
        "classified": True,
        "router_event_written": True,
        "done_recorded": True,
    }
    defaults.update(changes)
    return replace(State(), **defaults)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(), status="rejected", scenario=scenario, classified=True, **changes)


def scenario_state(scenario: str) -> State:
    if scenario == LOCAL_CHECK_CONSUMED_INTERNALLY:
        return _accepted(
            scenario,
            action_type="check_packet_ledger",
            action_owner="router_internal",
            controller_row_written=False,
            side_effect_count=1,
        )
    if scenario == MISSING_ACK_RECORDS_WAIT_NOT_DONE:
        return _accepted(
            scenario,
            action_type="check_card_return_event",
            action_owner="router_internal",
            external_evidence_required=True,
            external_evidence_present=False,
            router_event_written=True,
            router_wait_recorded=True,
            done_recorded=False,
            side_effect_count=1,
        )
    if scenario == ACK_PRESENT_ADVANCES_ONCE:
        return _accepted(
            scenario,
            action_type="check_card_return_event",
            action_owner="router_internal",
            external_evidence_required=True,
            external_evidence_present=True,
            done_recorded=True,
            side_effect_count=1,
        )
    if scenario == LOCAL_PROOF_WRITTEN_ONCE:
        return _accepted(
            scenario,
            action_type="write_startup_mechanical_audit",
            action_owner="router_internal",
            router_proof_written=True,
            side_effect_count=1,
        )
    if scenario == DISPLAY_PROJECTION_SPLIT:
        return _accepted(
            scenario,
            action_type="sync_display_plan",
            action_owner="router_internal",
            display_projection_written=True,
            user_display_confirmation_required=True,
            user_display_confirmed=False,
            done_recorded=True,
            side_effect_count=1,
        )
    if scenario == CONTROLLER_WORK_PACKAGE_PRESERVED:
        return _accepted(
            scenario,
            action_type="deliver_system_card",
            action_owner="controller_work_package",
            controller_row_written=True,
            router_event_written=False,
            done_recorded=False,
            role_interaction_required=True,
            system_card_or_packet_delivery=True,
        )
    if scenario == HOST_BOUNDARY_PRESERVED:
        return _accepted(
            scenario,
            action_type="create_heartbeat_automation",
            action_owner="host_boundary",
            controller_row_written=True,
            router_event_written=False,
            done_recorded=False,
            host_automation_required=True,
            host_proof_present=False,
        )
    if scenario == ROLE_RELAY_PRESERVED:
        return _accepted(
            scenario,
            action_type="relay_current_node_packet",
            action_owner="controller_work_package",
            controller_row_written=True,
            router_event_written=False,
            done_recorded=False,
            role_interaction_required=True,
            system_card_or_packet_delivery=True,
        )

    if scenario == ROUTER_INTERNAL_LEAKED_TO_CONTROLLER_ROW:
        return _rejected(
            scenario,
            action_type="check_packet_ledger",
            action_owner="router_internal",
            controller_row_written=True,
            router_event_written=True,
            done_recorded=True,
            side_effect_count=1,
        )
    if scenario == CONTROLLER_WORK_PACKAGE_SWALLOWED_BY_ROUTER:
        return _rejected(
            scenario,
            action_type="deliver_system_card",
            action_owner="controller_work_package",
            controller_row_written=False,
            router_event_written=True,
            done_recorded=True,
            role_interaction_required=True,
            system_card_or_packet_delivery=True,
        )
    if scenario == ROLE_INTERACTION_BYPASSED_CONTROLLER:
        return _rejected(
            scenario,
            action_type="relay_current_node_packet",
            action_owner="controller_work_package",
            controller_row_written=False,
            role_interaction_required=True,
            system_card_or_packet_delivery=True,
            role_contacted_by_router=True,
            done_recorded=True,
        )
    if scenario == SEALED_BODY_READ_DURING_INTERNAL_WORK:
        return _rejected(
            scenario,
            action_type="write_startup_mechanical_audit",
            action_owner="router_internal",
            sealed_body_read=True,
            router_event_written=True,
            router_proof_written=True,
            done_recorded=True,
        )
    if scenario == MISSING_EXTERNAL_EVIDENCE_MARKED_DONE:
        return _rejected(
            scenario,
            action_type="check_card_return_event",
            action_owner="router_internal",
            external_evidence_required=True,
            external_evidence_present=False,
            done_recorded=True,
            router_wait_recorded=False,
        )
    if scenario == ROUTER_INTERNAL_REPEATED_SIDE_EFFECT:
        return _rejected(
            scenario,
            action_type="check_packet_ledger",
            action_owner="router_internal",
            router_event_written=True,
            done_recorded=True,
            side_effect_count=2,
        )
    if scenario == DISPLAY_PROJECTION_CLAIMED_AS_USER_CONFIRMATION:
        return _rejected(
            scenario,
            action_type="sync_display_plan",
            action_owner="router_internal",
            display_projection_written=True,
            user_display_confirmation_required=True,
            user_display_confirmed=True,
            done_recorded=True,
        )
    if scenario == HOST_BOUNDARY_CONSUMED_LOCALLY:
        return _rejected(
            scenario,
            action_type="create_heartbeat_automation",
            action_owner="host_boundary",
            host_automation_required=True,
            host_proof_present=False,
            controller_row_written=False,
            router_event_written=True,
            done_recorded=True,
        )
    if scenario == ROUTER_INTERNAL_FAILURE_MARKED_DONE:
        return _rejected(
            scenario,
            action_type="write_startup_mechanical_audit",
            action_owner="router_internal",
            failure_seen=True,
            router_blocker_written=False,
            done_recorded=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(state, scenario=scenario))
        return
    if state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", scenario_state(state.scenario))
        return
    if state.scenario in NEGATIVE_SCENARIOS:
        yield Transition(f"reject_{state.scenario}", scenario_state(state.scenario))
        return


def ownership_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.action_owner == "router_internal" and state.controller_row_written:
        failures.append("Router-internal action leaked into Controller action row")
    if state.action_owner in {"controller_work_package", "host_boundary"} and state.done_recorded and not state.controller_row_written:
        failures.append("Controller work package was swallowed by Router internal completion")
    if state.role_interaction_required and state.role_contacted_by_router:
        failures.append("Router bypassed Controller for role interaction")
    if state.action_owner == "router_internal" and state.sealed_body_read:
        failures.append("Router-internal mechanical work read a sealed body")
    if state.external_evidence_required and not state.external_evidence_present and state.done_recorded:
        failures.append("Missing external evidence was marked done")
    if state.action_owner == "router_internal" and state.side_effect_count > 1:
        failures.append("Router-internal action repeated local side effects")
    if state.display_projection_written and state.user_display_confirmation_required and state.user_display_confirmed:
        failures.append("Local display projection was claimed as user display confirmation")
    if state.host_automation_required and not state.host_proof_present and state.done_recorded:
        failures.append("Host-boundary action was consumed locally without host proof")
    if state.failure_seen and state.done_recorded and not state.router_blocker_written:
        failures.append("Router-internal failure was marked done")
    return failures


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def accepts_only_valid_ownership_states(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "rejected":
        return InvariantResult.pass_()
    failures = ownership_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def hazard_states() -> dict[str, State]:
    return {name: scenario_state(name) for name in NEGATIVE_SCENARIOS}


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


class RouterInternalMechanicsBlock:
    """Model one Router ownership decision.

    Input x State -> Set(Output x State)
    reads: next action metadata, action owner classification, local ledgers,
    pending-return evidence, display projection state, and host/role boundary
    flags
    writes: Router internal event/proof/wait/blocker state or Controller action
    ledger rows
    idempotency: Router-internal work writes at most one local side effect per
    logical action and never marks missing evidence or local failure as done.
    """

    name = "RouterInternalMechanicsBlock"
    input_description = "one Router ownership decision"
    output_description = "Router evidence update or Controller work package row"
    reads = (
        "next_action",
        "action_owner_classification",
        "router_ledgers",
        "pending_return_evidence",
        "display_projection_state",
        "host_boundary_flags",
        "role_interaction_flags",
    )
    writes = (
        "router_internal_events",
        "router_internal_proofs",
        "router_wait_records",
        "router_blockers",
        "controller_action_ledger",
    )
    idempotency = "one internal side effect per logical Router action"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="router_internal_mechanics_ownership",
        description=(
            "Router-internal work must not leak into Controller rows, and "
            "Controller/host/role work packages must not be swallowed by Router."
        ),
        predicate=accepts_only_valid_ownership_states,
    ),
)


def build_workflow() -> Workflow:
    return Workflow((RouterInternalMechanicsBlock(),), name="flowpilot_router_internal_mechanics")


def terminal_predicate(input_obj: Tick, state: State, trace: tuple[object, ...]) -> bool:
    del input_obj, trace
    return is_terminal(state)
