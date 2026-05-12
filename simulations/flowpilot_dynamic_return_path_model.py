"""FlowGuard model for FlowPilot dynamic return-path authority.

Risk intent brief:
- Prevent role-output reports from inventing a formal Router event when an
  output contract says the event is router supplied.
- Model the difference between static prompt/card guidance, mechanical
  role-output validation, and the live Router wait state that can actually
  receive an event.
- Protected harms: system-card-only work causing a formal model report with no
  concrete return lease, a role guessing an event name, a registered event being
  unavailable in the current wait state, and green role-output validation being
  mistaken for permission to continue.
- Hard invariants: router-supplied contracts require a concrete event from the
  current Router wait or a PM role-work packet result contract; system cards do
  not authorize formal output by themselves; mechanical output validation cannot
  imply Router acceptance; and a current run with rejected role-output events
  must be classified as blocked even when the report content was meaningful.
- Blindspot: this model reads only metadata for live-run projection. It does
  not inspect sealed report bodies or judge the semantic quality of a report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_IDENTITY_CARD_ACK_ONLY = "valid_identity_card_ack_only"
VALID_PM_ROLE_WORK_PACKET_RESULT = "valid_pm_role_work_packet_result"
VALID_DIRECT_ROUTER_WAIT_EVENT = "valid_direct_router_wait_event"
VALID_ROUTER_REGISTERED_TASK_CARD_RESULT = "valid_router_registered_task_card_result"
VALID_ACTIVE_HOLDER_PACKET_RESULT = "valid_active_holder_packet_result"
VALID_FIXED_EVENT_CONTRACT = "valid_fixed_event_contract"

SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT = "system_card_only_router_supplied_report"
TASK_CARD_WITHOUT_WORK_AUTHORITY = "task_card_without_work_authority"
IDENTITY_CARD_CARRIES_HIDDEN_WORK = "identity_card_carries_hidden_work"
ROLE_GUESSES_UNKNOWN_EVENT = "role_guesses_unknown_event"
REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED = "registered_event_not_currently_allowed"
MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE = "mechanical_green_used_as_router_acceptance"
STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE = "static_card_guidance_used_as_dynamic_lease"
LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET = "legacy_direct_event_competes_with_pm_packet"
PM_ROLE_WORK_WRONG_RECIPIENT = "pm_role_work_wrong_recipient"
WRONG_ROLE_USES_WORK_AUTHORITY = "wrong_role_uses_work_authority"
WRONG_CONTRACT_USES_WORK_AUTHORITY = "wrong_contract_uses_work_authority"
STALE_WORK_AUTHORITY_USED = "stale_work_authority_used"

VALID_SCENARIOS = (
    VALID_IDENTITY_CARD_ACK_ONLY,
    VALID_PM_ROLE_WORK_PACKET_RESULT,
    VALID_DIRECT_ROUTER_WAIT_EVENT,
    VALID_ROUTER_REGISTERED_TASK_CARD_RESULT,
    VALID_ACTIVE_HOLDER_PACKET_RESULT,
    VALID_FIXED_EVENT_CONTRACT,
)
NEGATIVE_SCENARIOS = (
    SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT,
    TASK_CARD_WITHOUT_WORK_AUTHORITY,
    IDENTITY_CARD_CARRIES_HIDDEN_WORK,
    ROLE_GUESSES_UNKNOWN_EVENT,
    REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED,
    MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE,
    STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE,
    LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET,
    PM_ROLE_WORK_WRONG_RECIPIENT,
    WRONG_ROLE_USES_WORK_AUTHORITY,
    WRONG_CONTRACT_USES_WORK_AUTHORITY,
    STALE_WORK_AUTHORITY_USED,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

ASSIGNMENT_SYSTEM_CARD = "system_card"
ASSIGNMENT_IDENTITY_CARD = "identity_card"
ASSIGNMENT_TASK_CARD = "task_card"
ASSIGNMENT_PM_ROLE_WORK_PACKET = "pm_role_work_packet"
ASSIGNMENT_DIRECT_ROUTER_WAIT = "direct_router_wait"
ASSIGNMENT_ACTIVE_HOLDER_LEASE = "active_holder_lease"

EVENT_MODE_FIXED = "fixed"
EVENT_MODE_ROUTER_SUPPLIED = "router_supplied"

EVENT_SOURCE_NONE = "none"
EVENT_SOURCE_FIXED_CONTRACT = "fixed_contract"
EVENT_SOURCE_CURRENT_ROUTER_WAIT = "current_router_wait"
EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT = "pm_packet_result_contract"
EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY = "router_registered_task_authority"
EVENT_SOURCE_ACTIVE_HOLDER_LEASE = "active_holder_lease"
EVENT_SOURCE_ROLE_GUESS = "role_guess"
EVENT_SOURCE_STATIC_CARD_TEXT = "static_card_text"


@dataclass(frozen=True)
class Tick:
    """One dynamic return-path transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    assignment_surface: str = ASSIGNMENT_SYSTEM_CARD
    output_contract_id: str = "officer_model_report"
    output_type: str = "officer_model_report"
    contract_event_mode: str = EVENT_MODE_ROUTER_SUPPLIED

    formal_output_requested: bool = True
    identity_ack_only: bool = False
    task_like_card: bool = False
    router_registered_work_authority_present: bool = False
    authority_role_matches: bool = True
    authority_contract_matches: bool = True
    authority_recipient_matches: bool = True
    authority_route_frontier_fresh: bool = True
    required_result_next_recipient: str = "project_manager"

    static_card_guidance_present: bool = False
    mechanical_role_output_valid: bool = False
    semantic_report_meaningful: bool = False

    concrete_return_event_present: bool = False
    return_event_source: str = EVENT_SOURCE_NONE
    return_event_name: str = "none"
    return_event_registered: bool = False
    return_event_currently_allowed: bool = False

    pm_role_work_packet_present: bool = False
    pm_role_work_result_contract_present: bool = False
    direct_router_wait_present: bool = False
    legacy_direct_event_present: bool = False

    router_accepted_event: bool = False
    current_run_allowed_to_continue: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_IDENTITY_CARD_ACK_ONLY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_IDENTITY_CARD,
            contract_event_mode=EVENT_MODE_FIXED,
            formal_output_requested=False,
            identity_ack_only=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=False,
            semantic_report_meaningful=False,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_FIXED_CONTRACT,
            return_event_name="role_card_acknowledged",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_PM_ROLE_WORK_PACKET_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="pm_records_role_work_result_decision",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            required_result_next_recipient="project_manager",
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_DIRECT_ROUTER_WAIT_EVENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_ROUTER_REGISTERED_TASK_CARD_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_ACTIVE_HOLDER_PACKET_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_ACTIVE_HOLDER_LEASE,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
            return_event_name="active_holder_result_mechanics_passed",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_FIXED_EVENT_CONTRACT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_FIXED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_FIXED_CONTRACT,
            return_event_name="pm_registers_role_work_request",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == TASK_CARD_WITHOUT_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == IDENTITY_CARD_CARRIES_HIDDEN_WORK:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_IDENTITY_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            identity_ack_only=True,
            task_like_card=True,
            router_registered_work_authority_present=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == ROLE_GUESSES_UNKNOWN_EVENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_model_report",
            return_event_registered=False,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=True,
        )
    if scenario == STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=False,
            semantic_report_meaningful=False,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_STATIC_CARD_TEXT,
            return_event_name="use_router_supplied_event_name",
            return_event_registered=False,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            legacy_direct_event_present=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == PM_ROLE_WORK_WRONG_RECIPIENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="pm_records_role_work_result_decision",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            required_result_next_recipient="human_like_reviewer",
            authority_recipient_matches=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == WRONG_ROLE_USES_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_role_matches=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == WRONG_CONTRACT_USES_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_contract_matches=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == STALE_WORK_AUTHORITY_USED:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_ACTIVE_HOLDER_LEASE,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_route_frontier_fresh=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
            return_event_name="active_holder_result_mechanics_passed",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    raise ValueError(f"Unknown scenario: {scenario}")


def return_path_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures

    if state.identity_ack_only and state.formal_output_requested:
        failures.append("identity card carried hidden formal work")
    if state.task_like_card and state.formal_output_requested and not state.router_registered_work_authority_present:
        failures.append("task-like card lacks Router-registered work authority")
    if state.formal_output_requested and state.router_registered_work_authority_present:
        if not state.authority_role_matches:
            failures.append("work authority role does not match submitting role")
        if not state.authority_contract_matches:
            failures.append("work authority contract does not match submitted output")
        if not state.authority_recipient_matches:
            failures.append("work authority recipient does not match required recipient")
        if not state.authority_route_frontier_fresh:
            failures.append("work authority route or frontier is stale")
    if state.pm_role_work_packet_present and state.required_result_next_recipient != "project_manager":
        failures.append("PM role-work result does not return to project_manager")

    if not state.formal_output_requested:
        if state.router_accepted_event and not state.return_event_currently_allowed:
            failures.append("Router accepted an ACK event that was not currently allowed")
        return failures

    if state.contract_event_mode == EVENT_MODE_ROUTER_SUPPLIED:
        if not state.concrete_return_event_present:
            failures.append("router-supplied contract has no concrete return event")
        if state.return_event_source not in {
            EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
        }:
            failures.append("router-supplied return event was not supplied by current Router wait, PM packet, or registered work authority")
        if state.assignment_surface == ASSIGNMENT_SYSTEM_CARD:
            failures.append("system card alone cannot authorize formal router-supplied output")

    if state.return_event_source == EVENT_SOURCE_ROLE_GUESS:
        failures.append("role guessed a formal return event")
    if state.return_event_source == EVENT_SOURCE_STATIC_CARD_TEXT:
        failures.append("static card text was treated as a dynamic event lease")
    if state.concrete_return_event_present and not state.return_event_registered:
        failures.append("formal return event is not registered")
    if state.concrete_return_event_present and not state.return_event_currently_allowed:
        failures.append("formal return event is not currently allowed by Router wait state")
    if state.router_accepted_event and not state.return_event_currently_allowed:
        failures.append("Router accepted an event that was not currently allowed")
    if state.mechanical_role_output_valid and state.current_run_allowed_to_continue and not state.router_accepted_event:
        failures.append("mechanical role-output validation was treated as Router acceptance")
    if state.legacy_direct_event_present and state.pm_role_work_packet_present:
        failures.append("legacy direct officer event competes with PM role-work result contract")
    if state.pm_role_work_packet_present and not state.pm_role_work_result_contract_present:
        failures.append("PM role-work packet has no result contract")
    return failures


class DynamicReturnPathStep:
    """Model one FlowPilot role-output return path decision.

    Input x State -> Set(Output x State)
    reads: task assignment surface, output contract event mode, role-output
    runtime validation, current Router wait, PM role-work packet result contract
    writes: accepted/rejected dynamic return-path classification
    idempotency: repeated analysis of the same output attempt must produce the
    same blocked/accepted classification.
    """

    name = "DynamicReturnPathStep"
    input_description = "dynamic return-path authority tick"
    output_description = "one return-path authority classification"
    reads = (
        "task_assignment_surface",
        "output_contract_index",
        "role_output_runtime_result",
        "current_router_wait_state",
        "pm_role_work_packet_result_contract",
    )
    writes = ("dynamic_return_path_classification",)
    idempotency = "classification is derived from immutable event and packet facts"

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
    failures = return_path_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="dynamic_return_path_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not return_path_failures(state)


def accepted_states_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = return_path_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe dynamic return path was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe dynamic return path was rejected")
    return InvariantResult.pass_()


def router_supplied_outputs_have_runtime_lease(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.contract_event_mode != EVENT_MODE_ROUTER_SUPPLIED:
        return InvariantResult.pass_()
    if state.return_event_source not in {
        EVENT_SOURCE_CURRENT_ROUTER_WAIT,
        EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
        EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
        EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
    }:
        return InvariantResult.fail("accepted router-supplied output without runtime lease")
    return InvariantResult.pass_()


def mechanical_green_does_not_imply_continuation(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.current_run_allowed_to_continue and not state.router_accepted_event:
        return InvariantResult.fail("accepted continuation without Router acceptance")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_are_safe",
        description="Only safe dynamic return paths can be accepted.",
        predicate=accepted_states_are_safe,
    ),
    Invariant(
        name="router_supplied_outputs_have_runtime_lease",
        description="Router-supplied output contracts require a concrete runtime lease.",
        predicate=router_supplied_outputs_have_runtime_lease,
    ),
    Invariant(
        name="mechanical_green_does_not_imply_continuation",
        description="Role-output format validation cannot imply current-run continuation.",
        predicate=mechanical_green_does_not_imply_continuation,
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
    return Workflow((DynamicReturnPathStep(),), name="flowpilot_dynamic_return_path")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _iter_json_files(root: Path, pattern: str) -> Iterable[tuple[Path, dict]]:
    if not root.exists():
        return
    for path in sorted(root.glob(pattern)):
        if path.is_file():
            yield path, _read_json(path)


def router_supplied_contracts(project_root: Path) -> dict[str, dict]:
    index_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
    data = _read_json(index_path)
    contracts: dict[str, dict] = {}
    for item in data.get("contracts", []):
        if item.get("runtime_channel") == "role_output_runtime" and item.get("router_event_mode") == "router_supplied":
            contracts[item.get("contract_id", "")] = item
    return contracts


def project_live_run_projection(project_root: Path) -> dict[str, object]:
    current = _read_json(project_root / ".flowpilot" / "current.json")
    run_root_value = current.get("current_run_root")
    run_root = project_root / run_root_value if run_root_value else None
    contracts = router_supplied_contracts(project_root)
    contract_ids = set(contracts)
    output_types = {item.get("output_type") for item in contracts.values()}
    output_types.discard(None)

    projection: dict[str, object] = {
        "ok": True,
        "current_run_id": current.get("current_run_id"),
        "current_run_root": run_root_value,
        "router_supplied_contracts": sorted(contract_ids),
        "current_findings": [],
        "risk_surfaces": [],
        "mitigated_paths": [],
        "current_run_can_continue": True,
        "classification": "no_active_dynamic_return_path_findings",
    }
    if not run_root or not run_root.exists():
        projection["ok"] = False
        projection["classification"] = "current_run_missing"
        projection["current_run_can_continue"] = False
        return projection

    sessions: dict[str, dict] = {}
    for path, data in _iter_json_files(run_root / "role_output_sessions", "*.json"):
        contract_id = data.get("output_contract_id") or data.get("contract_id")
        output_type = data.get("output_type")
        event_name = data.get("event_name")
        if contract_id in contract_ids or output_type in output_types:
            sessions[str(event_name)] = {
                "path": str(path.relative_to(project_root)),
                "contract_id": contract_id,
                "output_type": output_type,
                "from_role": data.get("from_role"),
                "event_name": event_name,
            }

    for path, data in _iter_json_files(run_root / "control_blocks", "control-blocker-*.json"):
        if ".sealed_repair_packet" in path.name:
            continue
        error_code = str(data.get("error_code") or "")
        event = data.get("originating_event")
        if not event:
            event = data.get("event_name")
        rejected_router_supplied_output = event in sessions and (
            "unknown_external_event" in error_code or "not_currently_allowed" in error_code
        )
        if rejected_router_supplied_output:
            session = sessions[str(event)]
            projection["current_findings"].append(
                {
                    "kind": "rejected_router_supplied_role_output",
                    "event_name": event,
                    "error_code": error_code,
                    "role_output_session": session["path"],
                    "control_blocker": str(path.relative_to(project_root)),
                    "contract_id": session.get("contract_id"),
                    "output_type": session.get("output_type"),
                    "from_role": session.get("from_role"),
                    "model_meaning": (
                        "The report may be semantically useful, but the formal return path was not "
                        "authorized by the current Router wait or a PM role-work result contract."
                    ),
                }
            )

    for contract_id, item in sorted(contracts.items()):
        projection["risk_surfaces"].append(
            {
                "kind": "router_supplied_contract_needs_dynamic_lease",
                "contract_id": contract_id,
                "output_type": item.get("output_type"),
                "task_family": item.get("task_family"),
                "recipient_roles": item.get("recipient_roles", []),
                "packet_type": item.get("packet_type"),
            }
        )

    for path, data in _iter_json_files(run_root / "packet_batches", "*.json"):
        for item in data.get("packets", []):
            contract_id = item.get("output_contract_id")
            if contract_id in contract_ids:
                projection["mitigated_paths"].append(
                    {
                        "kind": "pm_role_work_result_contract",
                        "path": str(path.relative_to(project_root)),
                        "packet_id": item.get("packet_id"),
                        "status": item.get("status"),
                        "contract_id": contract_id,
                        "strict_process_contract_binding": item.get("strict_process_contract_binding"),
                        "required_result_next_recipient": item.get("required_result_next_recipient"),
                    }
                )

    findings = projection["current_findings"]
    if findings:
        projection["current_run_can_continue"] = False
        projection["classification"] = "blocked_by_dynamic_return_path_findings"
    projection["current_finding_count"] = len(findings)
    projection["risk_surface_count"] = len(projection["risk_surfaces"])
    projection["mitigated_path_count"] = len(projection["mitigated_paths"])
    return projection


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
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "project_live_run_projection",
    "return_path_failures",
    "router_supplied_contracts",
    "terminal_predicate",
]
