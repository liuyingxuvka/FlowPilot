"""FlowGuard model for FlowPilot blocker repair information flow.

Risk intent brief:
- Model the end-to-end information path from a reviewer or worker blocker to a
  PM repair decision, the next executable repair packet, worker evidence, and
  reviewer recheck.
- Protected harms: PM repair packages that lose the current blocker payload,
  reviewer required-repair text, or fresh work direction; worker packets that
  repeat the old failed packet; PM decisions that close blockers without a
  bound recheck; and same-blocker loops that keep producing no new progress.
- Hard invariant: every repair loop either carries current, concrete blocker
  facts into a new executable packet with a semantic delta and success evidence
  contract, or records an explicit route mutation, terminal stop, or follow-up
  blocker instead of silently continuing.
- Blindspot: this model checks the protocol information contract. Concrete
  runtime tests must still prove packet builders, cards, and result bodies use
  these fields in production code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_blocker_repair_information_flow"

VALID_REVIEWER_BLOCKER_REPAIR_PACKET = "valid_reviewer_blocker_repair_packet"
VALID_WORKER_BLOCKER_REISSUE = "valid_worker_blocker_reissue"
VALID_FOLLOWUP_BLOCKER_RECORDING = "valid_followup_blocker_recording"
VALID_LOOP_ESCAPE_ROUTE_MUTATION = "valid_loop_escape_route_mutation"

CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS = "current_blocker_payload_missing_details"
STALE_BLOCKER_USED_FOR_PM_REPAIR = "stale_blocker_used_for_pm_repair"
PM_DID_NOT_OPEN_REQUIRED_REPORT = "pm_did_not_open_required_report"
REVIEWER_REQUIRED_REPAIR_DROPPED = "reviewer_required_repair_dropped"
REVIEWER_ADVICE_NOT_INTEGRATED = "reviewer_advice_not_integrated"
PM_REPAIR_PACKAGE_OMITS_NEW_BLOCKER_CONTENT = "pm_repair_package_omits_new_blocker_content"
WORKER_PACKET_OMITS_REPAIR_DIRECTION = "worker_packet_omits_repair_direction"
WORKER_PACKET_HAS_NO_SEMANTIC_DELTA = "worker_packet_has_no_semantic_delta"
STALE_CONTEXT_COPIED_WITHOUT_DISPOSITION = "stale_context_copied_without_disposition"
PM_CLOSES_BLOCKER_WITHOUT_RECHECK = "pm_closes_blocker_without_recheck"
REVIEWER_RECHECK_NOT_BOUND_TO_BLOCKER = "reviewer_recheck_not_bound_to_blocker"
FOLLOWUP_BLOCKER_LOST = "followup_blocker_lost"
SAME_BLOCKER_REPEAT_LOOP_ALLOWED = "same_blocker_repeat_loop_allowed"
NO_SUCCESS_EVIDENCE_CONTRACT = "no_success_evidence_contract"
BLOCKER_ROUTED_WITHOUT_PM_DECISION = "blocker_routed_without_pm_decision"

VALID_SCENARIOS = (
    VALID_REVIEWER_BLOCKER_REPAIR_PACKET,
    VALID_WORKER_BLOCKER_REISSUE,
    VALID_FOLLOWUP_BLOCKER_RECORDING,
    VALID_LOOP_ESCAPE_ROUTE_MUTATION,
)

NEGATIVE_SCENARIOS = (
    CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS,
    STALE_BLOCKER_USED_FOR_PM_REPAIR,
    PM_DID_NOT_OPEN_REQUIRED_REPORT,
    REVIEWER_REQUIRED_REPAIR_DROPPED,
    REVIEWER_ADVICE_NOT_INTEGRATED,
    PM_REPAIR_PACKAGE_OMITS_NEW_BLOCKER_CONTENT,
    WORKER_PACKET_OMITS_REPAIR_DIRECTION,
    WORKER_PACKET_HAS_NO_SEMANTIC_DELTA,
    STALE_CONTEXT_COPIED_WITHOUT_DISPOSITION,
    PM_CLOSES_BLOCKER_WITHOUT_RECHECK,
    REVIEWER_RECHECK_NOT_BOUND_TO_BLOCKER,
    FOLLOWUP_BLOCKER_LOST,
    SAME_BLOCKER_REPEAT_LOOP_ALLOWED,
    NO_SUCCESS_EVIDENCE_CONTRACT,
    BLOCKER_ROUTED_WITHOUT_PM_DECISION,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS
MAX_SEQUENCE_LENGTH = 3


@dataclass(frozen=True)
class Tick:
    """One blocker-repair information-flow evaluation."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    blocker_detected: bool = False
    blocker_source_role: str = "none"  # none | reviewer | worker
    blocker_payload_current: bool = False
    blocker_id_present: bool = False
    source_result_ref_present: bool = False
    specific_failure_present: bool = False
    required_repair_present: bool = False
    reviewer_advice_present: bool = False

    pm_required_to_open_body: bool = False
    pm_opened_required_body: bool = False
    pm_repair_decision_recorded: bool = False
    pm_single_owner: bool = True
    pm_decision_references_current_blocker: bool = False
    pm_decision_includes_required_repair: bool = False
    pm_decision_integrates_reviewer_advice: bool = False
    pm_decision_names_new_work: bool = False

    pm_repair_package_issued: bool = False
    pm_package_generation_new: bool = False
    pm_package_references_current_blocker: bool = False
    pm_package_includes_specific_failure: bool = False
    pm_package_includes_required_repair: bool = False
    pm_package_includes_new_work_content: bool = False
    pm_package_disposes_old_context: bool = False

    worker_packet_issued: bool = False
    worker_packet_references_current_blocker: bool = False
    worker_packet_includes_required_repair: bool = False
    worker_packet_includes_success_evidence_contract: bool = False
    worker_packet_has_semantic_delta: bool = False

    worker_result_returned: bool = False
    worker_result_addresses_required_repair: bool = False

    reviewer_recheck_requested: bool = False
    reviewer_recheck_references_current_blocker: bool = False
    reviewer_recheck_uses_worker_evidence: bool = False
    reviewer_recheck_passed: bool = False
    blocker_closed: bool = False

    followup_blocker_returned: bool = False
    followup_blocker_recorded: bool = False

    same_blocker_repeat_count: int = 0
    same_work_packet_hash_repeated: bool = False
    loop_escape_recorded: bool = False
    terminal_stop_or_route_mutation: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _safe_reviewer_base(**changes: object) -> State:
    return replace(
        State(
            status="running",
            blocker_detected=True,
            blocker_source_role="reviewer",
            blocker_payload_current=True,
            blocker_id_present=True,
            source_result_ref_present=True,
            specific_failure_present=True,
            required_repair_present=True,
            reviewer_advice_present=True,
            pm_required_to_open_body=True,
            pm_opened_required_body=True,
            pm_repair_decision_recorded=True,
            pm_single_owner=True,
            pm_decision_references_current_blocker=True,
            pm_decision_includes_required_repair=True,
            pm_decision_integrates_reviewer_advice=True,
            pm_decision_names_new_work=True,
            pm_repair_package_issued=True,
            pm_package_generation_new=True,
            pm_package_references_current_blocker=True,
            pm_package_includes_specific_failure=True,
            pm_package_includes_required_repair=True,
            pm_package_includes_new_work_content=True,
            pm_package_disposes_old_context=True,
            worker_packet_issued=True,
            worker_packet_references_current_blocker=True,
            worker_packet_includes_required_repair=True,
            worker_packet_includes_success_evidence_contract=True,
            worker_packet_has_semantic_delta=True,
            worker_result_returned=True,
            worker_result_addresses_required_repair=True,
            reviewer_recheck_requested=True,
            reviewer_recheck_references_current_blocker=True,
            reviewer_recheck_uses_worker_evidence=True,
            reviewer_recheck_passed=True,
            blocker_closed=True,
        ),
        **changes,
    )


def _safe_worker_base(**changes: object) -> State:
    return replace(
        _safe_reviewer_base(
            blocker_source_role="worker",
            reviewer_advice_present=False,
            pm_decision_integrates_reviewer_advice=False,
        ),
        **changes,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_REVIEWER_BLOCKER_REPAIR_PACKET:
        return replace(_safe_reviewer_base(), scenario=scenario)
    if scenario == VALID_WORKER_BLOCKER_REISSUE:
        return replace(_safe_worker_base(), scenario=scenario)
    if scenario == VALID_FOLLOWUP_BLOCKER_RECORDING:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            reviewer_recheck_passed=False,
            blocker_closed=False,
            followup_blocker_returned=True,
            followup_blocker_recorded=True,
        )
    if scenario == VALID_LOOP_ESCAPE_ROUTE_MUTATION:
        return State(
            status="running",
            scenario=scenario,
            blocker_detected=True,
            blocker_source_role="reviewer",
            blocker_payload_current=True,
            blocker_id_present=True,
            source_result_ref_present=True,
            specific_failure_present=True,
            required_repair_present=True,
            reviewer_advice_present=True,
            pm_required_to_open_body=True,
            pm_opened_required_body=True,
            pm_repair_decision_recorded=True,
            pm_single_owner=True,
            pm_decision_references_current_blocker=True,
            pm_decision_includes_required_repair=True,
            pm_decision_integrates_reviewer_advice=True,
            pm_decision_names_new_work=True,
            same_blocker_repeat_count=2,
            same_work_packet_hash_repeated=True,
            loop_escape_recorded=True,
            terminal_stop_or_route_mutation=True,
        )

    if scenario == CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            blocker_id_present=False,
            source_result_ref_present=False,
            specific_failure_present=False,
        )
    if scenario == STALE_BLOCKER_USED_FOR_PM_REPAIR:
        return replace(_safe_reviewer_base(), scenario=scenario, blocker_payload_current=False)
    if scenario == PM_DID_NOT_OPEN_REQUIRED_REPORT:
        return replace(_safe_reviewer_base(), scenario=scenario, pm_opened_required_body=False)
    if scenario == REVIEWER_REQUIRED_REPAIR_DROPPED:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_decision_includes_required_repair=False,
            pm_package_includes_required_repair=False,
        )
    if scenario == REVIEWER_ADVICE_NOT_INTEGRATED:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_decision_integrates_reviewer_advice=False,
        )
    if scenario == PM_REPAIR_PACKAGE_OMITS_NEW_BLOCKER_CONTENT:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_package_references_current_blocker=False,
            pm_package_includes_specific_failure=False,
            pm_package_includes_new_work_content=False,
        )
    if scenario == WORKER_PACKET_OMITS_REPAIR_DIRECTION:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            worker_packet_includes_required_repair=False,
            worker_result_addresses_required_repair=False,
        )
    if scenario == WORKER_PACKET_HAS_NO_SEMANTIC_DELTA:
        return replace(_safe_reviewer_base(), scenario=scenario, worker_packet_has_semantic_delta=False)
    if scenario == STALE_CONTEXT_COPIED_WITHOUT_DISPOSITION:
        return replace(_safe_reviewer_base(), scenario=scenario, pm_package_disposes_old_context=False)
    if scenario == PM_CLOSES_BLOCKER_WITHOUT_RECHECK:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            reviewer_recheck_requested=False,
            reviewer_recheck_references_current_blocker=False,
            reviewer_recheck_uses_worker_evidence=False,
            reviewer_recheck_passed=False,
            blocker_closed=True,
        )
    if scenario == REVIEWER_RECHECK_NOT_BOUND_TO_BLOCKER:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            reviewer_recheck_references_current_blocker=False,
        )
    if scenario == FOLLOWUP_BLOCKER_LOST:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            reviewer_recheck_passed=False,
            blocker_closed=False,
            followup_blocker_returned=True,
            followup_blocker_recorded=False,
        )
    if scenario == SAME_BLOCKER_REPEAT_LOOP_ALLOWED:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            same_blocker_repeat_count=2,
            same_work_packet_hash_repeated=True,
            loop_escape_recorded=False,
            terminal_stop_or_route_mutation=False,
        )
    if scenario == NO_SUCCESS_EVIDENCE_CONTRACT:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            worker_packet_includes_success_evidence_contract=False,
        )
    if scenario == BLOCKER_ROUTED_WITHOUT_PM_DECISION:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_repair_decision_recorded=False,
            pm_decision_references_current_blocker=False,
            pm_decision_includes_required_repair=False,
            pm_decision_names_new_work=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def information_flow_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.blocker_detected:
        if not state.blocker_payload_current:
            failures.append("PM repair used stale blocker payload instead of current blocker generation")
        if not (
            state.blocker_id_present
            and state.source_result_ref_present
            and state.specific_failure_present
        ):
            failures.append("current blocker payload lacks blocker id, source result reference, or specific failure")

    if state.pm_repair_decision_recorded:
        if not state.pm_single_owner:
            failures.append("PM repair decision lacks single owner")
        if state.blocker_detected and not state.pm_decision_references_current_blocker:
            failures.append("PM repair decision does not reference the current blocker")
        if state.pm_required_to_open_body and not state.pm_opened_required_body:
            failures.append("PM repair decision was made before opening the required report body")
        if state.required_repair_present and not state.pm_decision_includes_required_repair:
            failures.append("PM repair decision dropped the role required_repair")
        if state.reviewer_advice_present and not state.pm_decision_integrates_reviewer_advice:
            failures.append("PM repair decision did not integrate reviewer repair advice")
        if not state.pm_decision_names_new_work:
            failures.append("PM repair decision does not name new executable repair work")

    if state.pm_repair_package_issued:
        if not state.pm_repair_decision_recorded:
            failures.append("repair packet was issued without a PM repair decision")
        if not state.pm_package_generation_new:
            failures.append("PM repair package did not create a fresh generation")
        if not (
            state.pm_package_references_current_blocker
            and state.pm_package_includes_specific_failure
            and state.pm_package_includes_new_work_content
        ):
            failures.append("PM repair package omits current blocker, specific failure, or new work content")
        if state.required_repair_present and not state.pm_package_includes_required_repair:
            failures.append("PM repair package dropped required repair guidance")
        if not state.pm_package_disposes_old_context:
            failures.append("PM repair package copied stale context without disposition or quarantine")

    if state.worker_packet_issued:
        if not state.pm_repair_package_issued:
            failures.append("worker repair packet was issued without PM repair package")
        if not state.worker_packet_references_current_blocker:
            failures.append("worker packet does not reference the current blocker")
        if state.required_repair_present and not state.worker_packet_includes_required_repair:
            failures.append("worker packet lacks concrete repair direction")
        if not state.worker_packet_has_semantic_delta:
            failures.append("worker packet repeats the failed work without semantic delta")
        if not state.worker_packet_includes_success_evidence_contract:
            failures.append("worker packet lacks success evidence contract")

    if (
        state.worker_result_returned
        and state.required_repair_present
        and not state.worker_result_addresses_required_repair
    ):
        failures.append("worker result did not address the required repair")

    if state.reviewer_recheck_requested:
        if not (
            state.reviewer_recheck_references_current_blocker
            and state.reviewer_recheck_uses_worker_evidence
        ):
            failures.append("reviewer recheck is not bound to the current blocker and repair evidence")

    if state.blocker_closed and not (
        state.reviewer_recheck_requested
        and state.reviewer_recheck_references_current_blocker
        and state.reviewer_recheck_uses_worker_evidence
        and state.reviewer_recheck_passed
    ):
        failures.append("blocker was closed without a bound reviewer recheck pass")

    if state.followup_blocker_returned and not state.followup_blocker_recorded:
        failures.append("follow-up blocker returned by recheck was not recorded as current work")

    if (
        state.same_blocker_repeat_count >= 2
        and state.same_work_packet_hash_repeated
        and not (state.loop_escape_recorded and state.terminal_stop_or_route_mutation)
    ):
        failures.append("same blocker repeated with same work packet and no route mutation or terminal blocker")

    return failures


class BlockerRepairInformationFlowStep:
    """Model one FlowPilot blocker repair information-flow transition.

    Input x State -> Set(Output x State)
    reads: blocker payload, role report body-open receipt, PM repair decision,
    PM repair package, worker repair packet, worker result, reviewer recheck,
    repeated blocker/work-package identities
    writes: accepted repair flow, explicit rejection, follow-up blocker, route
    mutation, or terminal stop
    idempotency: current blocker id plus repair package generation determine
    whether a repeated transition is progress or a no-progress loop.
    """

    name = "BlockerRepairInformationFlowStep"
    input_description = "blocker repair information-flow tick"
    output_description = "accepted flow or rejected no-progress repair loop"
    reads = (
        "current_blocker",
        "role_result_report",
        "pm_repair_decision",
        "pm_repair_package",
        "worker_packet",
        "worker_result",
        "reviewer_recheck",
    )
    writes = (
        "repair_flow_decision",
        "worker_packet_generation",
        "reviewer_recheck_binding",
        "followup_blocker_or_loop_escape",
    )
    idempotency = "blocker-id and package-generation scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = information_flow_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="information_flow_complete"),
    )


def accepted_flows_are_complete(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = information_flow_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def pm_packages_carry_current_blocker(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.pm_repair_package_issued:
        if not (
            state.pm_package_references_current_blocker
            and state.pm_package_includes_specific_failure
            and state.pm_package_includes_new_work_content
            and state.pm_package_generation_new
        ):
            return InvariantResult.fail("accepted PM package missed current blocker or fresh work content")
    return InvariantResult.pass_()


def worker_packets_make_progress(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.worker_packet_issued:
        if not (
            state.worker_packet_references_current_blocker
            and state.worker_packet_has_semantic_delta
            and state.worker_packet_includes_success_evidence_contract
        ):
            return InvariantResult.fail("accepted worker packet lacked repair progress contract")
    return InvariantResult.pass_()


def repeated_blockers_escape_or_block(state: State, trace: object) -> InvariantResult:
    del trace
    if (
        state.status == "accepted"
        and state.same_blocker_repeat_count >= 2
        and state.same_work_packet_hash_repeated
        and not (state.loop_escape_recorded and state.terminal_stop_or_route_mutation)
    ):
        return InvariantResult.fail("accepted same-blocker no-progress loop")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_flows_are_complete",
        description="Accepted blocker repair flows preserve current blocker details through PM, worker, and reviewer boundaries.",
        predicate=accepted_flows_are_complete,
    ),
    Invariant(
        name="pm_packages_carry_current_blocker",
        description="PM repair packages carry current blocker identity, specific failure, fresh generation, and new work content.",
        predicate=pm_packages_carry_current_blocker,
    ),
    Invariant(
        name="worker_packets_make_progress",
        description="Worker repair packets reference the blocker, contain semantic delta, and define success evidence.",
        predicate=worker_packets_make_progress,
    ),
    Invariant(
        name="repeated_blockers_escape_or_block",
        description="Repeated same-blocker/same-packet loops must route to mutation, terminal stop, or follow-up blocker.",
        predicate=repeated_blockers_escape_or_block,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def build_workflow() -> Workflow:
    return Workflow((BlockerRepairInformationFlowStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"accepted", "rejected"}


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


EXTERNAL_INPUTS = (Tick(),)


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "information_flow_failures",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
