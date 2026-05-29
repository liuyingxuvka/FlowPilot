"""FlowGuard model for the clean AI project protocol kernel."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "ai_project_protocol_kernel"

SUCCESS = "success"
MISSING_ACK = "missing_ack"
ACK_WITHOUT_OUTPUT = "ack_without_output"
WRONG_PACKET_SHAPE = "wrong_packet_shape"
CLOSED_AGENT_OUTPUT = "closed_agent_output"
SELF_REVIEW = "self_review"
WEAK_REVIEW = "weak_review"
STALE_EVIDENCE = "stale_evidence"
ROUTE_MUTATION_OLD_PACKET = "route_mutation_old_packet"
FLOWGUARD_WRONG_TARGET = "flowguard_wrong_target"
FINAL_CLOSURE_GAP = "final_closure_gap"

SCENARIOS = (
    SUCCESS,
    MISSING_ACK,
    ACK_WITHOUT_OUTPUT,
    WRONG_PACKET_SHAPE,
    CLOSED_AGENT_OUTPUT,
    SELF_REVIEW,
    WEAK_REVIEW,
    STALE_EVIDENCE,
    ROUTE_MUTATION_OLD_PACKET,
    FLOWGUARD_WRONG_TARGET,
    FINAL_CLOSURE_GAP,
)

SAFE_SCENARIOS = {SUCCESS}
RISK_SCENARIOS = set(SCENARIOS) - SAFE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Action:
    label: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = ""
    active_route_version: str = "route-v1"
    packet_route_version: str = "route-v1"
    result_route_version: str = "route-v1"
    lease_status: str = "none"
    ack_received: bool = False
    result_submitted: bool = False
    result_packet_valid: bool = False
    producer_matches_lease: bool = False
    output_after_close: bool = False
    reviewer_independent: bool = False
    review_checks_evidence: bool = False
    review_decision: str = ""
    required_model_target: str = "development_process"
    flowguard_model_target: str = "development_process"
    flowguard_decision: str = ""
    evidence_fresh: bool = False
    old_route_packets_open: bool = False
    old_packet_disposition: str = ""
    final_backward_chain: bool = False
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _happy_path() -> State:
    return State(
        status="running",
        scenario=SUCCESS,
        active_route_version="route-v1",
        packet_route_version="route-v1",
        result_route_version="route-v1",
        lease_status="active",
        ack_received=True,
        result_submitted=True,
        result_packet_valid=True,
        producer_matches_lease=True,
        reviewer_independent=True,
        review_checks_evidence=True,
        review_decision="accept",
        flowguard_decision="pass",
        evidence_fresh=True,
        final_backward_chain=True,
    )


def _selected_state(scenario: str) -> State:
    base = _happy_path()
    if scenario == SUCCESS:
        return base
    if scenario == MISSING_ACK:
        return replace(base, scenario=scenario, ack_received=False, result_submitted=False)
    if scenario == ACK_WITHOUT_OUTPUT:
        return replace(base, scenario=scenario, result_submitted=False)
    if scenario == WRONG_PACKET_SHAPE:
        return replace(base, scenario=scenario, result_packet_valid=False)
    if scenario == CLOSED_AGENT_OUTPUT:
        return replace(
            base,
            scenario=scenario,
            lease_status="closed",
            output_after_close=True,
        )
    if scenario == SELF_REVIEW:
        return replace(base, scenario=scenario, reviewer_independent=False)
    if scenario == WEAK_REVIEW:
        return replace(base, scenario=scenario, review_checks_evidence=False)
    if scenario == STALE_EVIDENCE:
        return replace(base, scenario=scenario, evidence_fresh=False)
    if scenario == ROUTE_MUTATION_OLD_PACKET:
        return replace(
            base,
            scenario=scenario,
            active_route_version="route-v2",
            packet_route_version="route-v1",
            result_route_version="route-v1",
            old_route_packets_open=True,
            old_packet_disposition="",
        )
    if scenario == FLOWGUARD_WRONG_TARGET:
        return replace(base, scenario=scenario, flowguard_model_target="target_product_behavior")
    if scenario == FINAL_CLOSURE_GAP:
        return replace(base, scenario=scenario, final_backward_chain=False)
    raise ValueError(f"unknown scenario: {scenario}")


def _old_packets_safe(state: State) -> bool:
    if not state.old_route_packets_open:
        return True
    return state.old_packet_disposition in {"closed", "quarantined", "rebound"}


def acceptance_ready(state: State) -> bool:
    """True only when the ledger may accept a result as project progress."""

    return (
        state.status == "running"
        and state.lease_status == "active"
        and state.ack_received
        and state.result_submitted
        and state.result_packet_valid
        and state.producer_matches_lease
        and not state.output_after_close
        and state.packet_route_version == state.active_route_version
        and state.result_route_version == state.active_route_version
        and state.reviewer_independent
        and state.review_checks_evidence
        and state.review_decision == "accept"
        and state.flowguard_model_target == state.required_model_target
        and state.flowguard_decision == "pass"
        and state.evidence_fresh
        and _old_packets_safe(state)
        and state.final_backward_chain
    )


def _block_label(state: State) -> str:
    if not state.ack_received:
        return "block_missing_ack"
    if not state.result_submitted:
        return "block_ack_without_output"
    if state.lease_status != "active" or state.output_after_close:
        return "block_closed_agent_output"
    if not state.result_packet_valid:
        return "block_wrong_packet_shape"
    if state.packet_route_version != state.active_route_version:
        return "block_route_mutation_old_packet"
    if state.result_route_version != state.active_route_version:
        return "block_result_route_mismatch"
    if not state.reviewer_independent:
        return "block_self_review"
    if not state.review_checks_evidence:
        return "block_weak_review"
    if state.flowguard_model_target != state.required_model_target:
        return "block_flowguard_wrong_target"
    if not state.evidence_fresh:
        return "block_stale_evidence"
    if not _old_packets_safe(state):
        return "block_open_old_route_packets"
    if not state.final_backward_chain:
        return "block_final_closure_gap"
    return "block_insufficient_acceptance_evidence"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if acceptance_ready(state):
        yield Transition(
            "accept_verified_result",
            replace(state, status="complete", classification="accepted"),
        )
        return
    label = _block_label(state)
    yield Transition(label, replace(state, status="blocked", classification=label))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def is_success(state: State) -> bool:
    return is_terminal(state)


def hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "complete" and not acceptance_ready(replace(state, status="running")):
        failures.append("project completion was accepted without the full protocol gate")
    if state.status == "complete" and state.scenario in RISK_SCENARIOS:
        failures.append(f"risk scenario was accepted: {state.scenario}")
    if state.status == "blocked" and state.scenario in SAFE_SCENARIOS:
        failures.append("happy path was blocked despite complete fresh evidence")
    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "ai_project_protocol_completion_gate",
        "Completion requires lease, packet, route, review, FlowGuard, freshness, and backward closure gates.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


class AIProjectProtocolStep:
    """Input x State -> Set(Output x State) for the AI project protocol."""

    name = "AIProjectProtocolStep"
    reads = (
        "black_box_ledger",
        "agent_lease",
        "task_packet",
        "result_packet",
        "review_report",
        "flowguard_work_order",
        "evidence_freshness",
        "final_backward_closure",
    )
    writes = ("ledger_acceptance_or_block",)
    input_description = "protocol event or fake-agent scenario"
    output_description = "accepted completion or explicit blocked path"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def build_workflow() -> Workflow:
    return Workflow((AIProjectProtocolStep(),), name=MODEL_ID)


def scenario_matrix() -> dict[str, str]:
    matrix: dict[str, str] = {}
    for scenario in SCENARIOS:
        transitions = list(next_safe_states(_selected_state(scenario)))
        if len(transitions) != 1:
            matrix[scenario] = "missing_transition"
        else:
            matrix[scenario] = transitions[0].label
    return matrix


def hazard_states() -> dict[str, State]:
    hazards = {
        f"{scenario}_accepted": replace(_selected_state(scenario), status="complete")
        for scenario in RISK_SCENARIOS
    }
    hazards["success_overblocked"] = replace(_selected_state(SUCCESS), status="blocked")
    return hazards
