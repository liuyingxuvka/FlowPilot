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
VALID_THRESHOLD_BREAK_GLASS_LOOP_ESCAPE = "valid_threshold_break_glass_loop_escape"
VALID_CROSS_NODE_SIMILAR_FAILURES_NORMAL_REPAIR = "valid_cross_node_similar_failures_normal_repair"

CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS = "current_blocker_payload_missing_details"
STALE_BLOCKER_USED_FOR_PM_REPAIR = "stale_blocker_used_for_pm_repair"
PM_REQUIRED_REPORT_NOT_DELIVERED = "pm_required_report_not_delivered"
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
FLOWGUARD_RECHECK_EVIDENCE_NOT_DELIVERED_TO_REVIEWER = "flowguard_recheck_evidence_not_delivered_to_reviewer"
REPAIR_STAGE_NOT_UPDATED_AFTER_FLOWGUARD_PASS = "repair_stage_not_updated_after_flowguard_pass"
FORMAL_BLOCKER_ID_ONLY_IN_PROSE_REACHES_REVIEWER = "formal_blocker_id_only_in_prose_reaches_reviewer"
GATE_DERIVED_PM_FLOWGUARD_ACCEPTANCE_IDENTITY_DROPPED = (
    "gate_derived_pm_flowguard_acceptance_identity_dropped"
)
FLOWGUARD_EVIDENCE_HAS_BLOCKER_BUT_STAGED_EFFECT_EMPTY = (
    "flowguard_evidence_has_blocker_but_staged_effect_empty"
)
SUPERSEDED_REPAIR_BLOCKER_LEFT_OPEN = "superseded_repair_blocker_left_open"
ACCEPTED_NONCURRENT_REPAIR_PACKET_BLOCKS_FINAL_PREFLIGHT = (
    "accepted_noncurrent_repair_packet_blocks_final_preflight"
)
STALE_PRIOR_ROUTE_REPAIR_BLOCKER_LEFT_OPEN = "stale_prior_route_repair_blocker_left_open"
REPAIR_LOOP_OVER_THRESHOLD_ALLOWED_PM_REPAIR = "repair_loop_over_threshold_allowed_pm_repair"

VALID_SCENARIOS = (
    VALID_REVIEWER_BLOCKER_REPAIR_PACKET,
    VALID_WORKER_BLOCKER_REISSUE,
    VALID_FOLLOWUP_BLOCKER_RECORDING,
    VALID_LOOP_ESCAPE_ROUTE_MUTATION,
    VALID_THRESHOLD_BREAK_GLASS_LOOP_ESCAPE,
    VALID_CROSS_NODE_SIMILAR_FAILURES_NORMAL_REPAIR,
)

NEGATIVE_SCENARIOS = (
    CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS,
    STALE_BLOCKER_USED_FOR_PM_REPAIR,
    PM_REQUIRED_REPORT_NOT_DELIVERED,
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
    FLOWGUARD_RECHECK_EVIDENCE_NOT_DELIVERED_TO_REVIEWER,
    REPAIR_STAGE_NOT_UPDATED_AFTER_FLOWGUARD_PASS,
    FORMAL_BLOCKER_ID_ONLY_IN_PROSE_REACHES_REVIEWER,
    GATE_DERIVED_PM_FLOWGUARD_ACCEPTANCE_IDENTITY_DROPPED,
    FLOWGUARD_EVIDENCE_HAS_BLOCKER_BUT_STAGED_EFFECT_EMPTY,
    SUPERSEDED_REPAIR_BLOCKER_LEFT_OPEN,
    ACCEPTED_NONCURRENT_REPAIR_PACKET_BLOCKS_FINAL_PREFLIGHT,
    STALE_PRIOR_ROUTE_REPAIR_BLOCKER_LEFT_OPEN,
    REPAIR_LOOP_OVER_THRESHOLD_ALLOWED_PM_REPAIR,
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

    pm_requires_authorized_report_body: bool = False
    pm_authorized_report_delivered: bool = False
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
    pm_package_formal_blocker_id_bound: bool = False

    worker_packet_issued: bool = False
    worker_packet_references_current_blocker: bool = False
    worker_packet_includes_required_repair: bool = False
    worker_packet_includes_success_evidence_contract: bool = False
    worker_packet_has_semantic_delta: bool = False

    worker_result_returned: bool = False
    worker_result_addresses_required_repair: bool = False

    flowguard_recheck_requested: bool = False
    flowguard_recheck_references_repair_result: bool = False
    flowguard_recheck_passed: bool = False
    flowguard_evidence_manifest_attached: bool = False
    flowguard_evidence_formal_blocker_id_bound: bool = False
    pm_flowguard_acceptance_identity_bound: bool = False

    reviewer_recheck_requested: bool = False
    reviewer_recheck_references_current_blocker: bool = False
    reviewer_packet_inherits_repair_identity: bool = False
    reviewer_recheck_uses_worker_evidence: bool = False
    reviewer_recheck_uses_flowguard_evidence: bool = False
    reviewer_recheck_passed: bool = False
    blocker_closed: bool = False
    blocker_stage_current: bool = True
    runtime_mechanical_identity_gate_passed: bool = False
    staged_effect_blocker_id_bound: bool = False
    blocker_identity_in_prose_only: bool = False
    formal_identity_missing_reached_reviewer: bool = False
    route_replacement_supersedes_prior_repair: bool = False
    superseded_blocker_disposition_recorded: bool = True
    superseded_blocker_still_repair_open: bool = False
    final_preflight_uses_current_effective_blockers: bool = True
    final_preflight_reports_noncurrent_repair_blocker: bool = False

    followup_blocker_returned: bool = False
    followup_blocker_recorded: bool = False

    same_blocker_repeat_count: int = 0
    same_work_packet_hash_repeated: bool = False
    loop_escape_recorded: bool = False
    terminal_stop_or_route_mutation: bool = False
    same_family_repair_attempt_count: int = 0
    repair_loop_threshold: int = 5
    repair_loop_same_node_consecutive: bool = False
    repair_loop_threshold_evidence_visible: bool = False
    break_glass_duty_projected: bool = False
    ordinary_pm_repair_continued_over_threshold: bool = False
    same_family_pm_packets_superseded: bool = True

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
            pm_requires_authorized_report_body=True,
            pm_authorized_report_delivered=True,
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
            pm_package_formal_blocker_id_bound=True,
            worker_packet_issued=True,
            worker_packet_references_current_blocker=True,
            worker_packet_includes_required_repair=True,
            worker_packet_includes_success_evidence_contract=True,
            worker_packet_has_semantic_delta=True,
            worker_result_returned=True,
            worker_result_addresses_required_repair=True,
            flowguard_recheck_requested=True,
            flowguard_recheck_references_repair_result=True,
            flowguard_recheck_passed=True,
            flowguard_evidence_manifest_attached=True,
            flowguard_evidence_formal_blocker_id_bound=True,
            pm_flowguard_acceptance_identity_bound=True,
            reviewer_recheck_requested=True,
            reviewer_recheck_references_current_blocker=True,
            reviewer_packet_inherits_repair_identity=True,
            reviewer_recheck_uses_worker_evidence=True,
            reviewer_recheck_uses_flowguard_evidence=True,
            reviewer_recheck_passed=True,
            blocker_closed=True,
            blocker_stage_current=True,
            runtime_mechanical_identity_gate_passed=True,
            staged_effect_blocker_id_bound=True,
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
            pm_requires_authorized_report_body=True,
            pm_authorized_report_delivered=True,
            pm_repair_decision_recorded=True,
            pm_single_owner=True,
            pm_decision_references_current_blocker=True,
            pm_decision_includes_required_repair=True,
            pm_decision_integrates_reviewer_advice=True,
            pm_decision_names_new_work=True,
            pm_package_formal_blocker_id_bound=True,
            pm_flowguard_acceptance_identity_bound=True,
            same_blocker_repeat_count=2,
            same_work_packet_hash_repeated=True,
            loop_escape_recorded=True,
            terminal_stop_or_route_mutation=True,
            runtime_mechanical_identity_gate_passed=True,
            staged_effect_blocker_id_bound=True,
            flowguard_evidence_formal_blocker_id_bound=True,
        )
    if scenario == VALID_THRESHOLD_BREAK_GLASS_LOOP_ESCAPE:
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
            pm_requires_authorized_report_body=True,
            pm_authorized_report_delivered=True,
            pm_single_owner=True,
            same_blocker_repeat_count=6,
            same_work_packet_hash_repeated=True,
            loop_escape_recorded=True,
            same_family_repair_attempt_count=5,
            repair_loop_threshold=5,
            repair_loop_same_node_consecutive=True,
            repair_loop_threshold_evidence_visible=True,
            break_glass_duty_projected=True,
            ordinary_pm_repair_continued_over_threshold=False,
            same_family_pm_packets_superseded=True,
            runtime_mechanical_identity_gate_passed=True,
        )

    if scenario == VALID_CROSS_NODE_SIMILAR_FAILURES_NORMAL_REPAIR:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            blocker_closed=False,
            same_family_repair_attempt_count=5,
            repair_loop_threshold=5,
            repair_loop_same_node_consecutive=False,
            repair_loop_threshold_evidence_visible=True,
            break_glass_duty_projected=False,
            ordinary_pm_repair_continued_over_threshold=True,
            same_family_pm_packets_superseded=False,
            loop_escape_recorded=True,
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
    if scenario == PM_REQUIRED_REPORT_NOT_DELIVERED:
        return replace(_safe_reviewer_base(), scenario=scenario, pm_authorized_report_delivered=False)
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
    if scenario == FLOWGUARD_RECHECK_EVIDENCE_NOT_DELIVERED_TO_REVIEWER:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            flowguard_evidence_manifest_attached=False,
            reviewer_recheck_uses_flowguard_evidence=False,
        )
    if scenario == REPAIR_STAGE_NOT_UPDATED_AFTER_FLOWGUARD_PASS:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            blocker_stage_current=False,
        )
    if scenario == FORMAL_BLOCKER_ID_ONLY_IN_PROSE_REACHES_REVIEWER:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_package_formal_blocker_id_bound=False,
            staged_effect_blocker_id_bound=False,
            flowguard_evidence_formal_blocker_id_bound=False,
            runtime_mechanical_identity_gate_passed=False,
            blocker_identity_in_prose_only=True,
            formal_identity_missing_reached_reviewer=True,
        )
    if scenario == GATE_DERIVED_PM_FLOWGUARD_ACCEPTANCE_IDENTITY_DROPPED:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            pm_flowguard_acceptance_identity_bound=False,
            reviewer_packet_inherits_repair_identity=False,
            runtime_mechanical_identity_gate_passed=False,
        )
    if scenario == FLOWGUARD_EVIDENCE_HAS_BLOCKER_BUT_STAGED_EFFECT_EMPTY:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            staged_effect_blocker_id_bound=False,
            flowguard_evidence_formal_blocker_id_bound=True,
            runtime_mechanical_identity_gate_passed=False,
        )
    if scenario == SUPERSEDED_REPAIR_BLOCKER_LEFT_OPEN:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            route_replacement_supersedes_prior_repair=True,
            superseded_blocker_disposition_recorded=False,
            superseded_blocker_still_repair_open=True,
        )
    if scenario == ACCEPTED_NONCURRENT_REPAIR_PACKET_BLOCKS_FINAL_PREFLIGHT:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            final_preflight_uses_current_effective_blockers=False,
            final_preflight_reports_noncurrent_repair_blocker=True,
        )
    if scenario == STALE_PRIOR_ROUTE_REPAIR_BLOCKER_LEFT_OPEN:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            route_replacement_supersedes_prior_repair=True,
            superseded_blocker_disposition_recorded=False,
            superseded_blocker_still_repair_open=True,
        )
    if scenario == REPAIR_LOOP_OVER_THRESHOLD_ALLOWED_PM_REPAIR:
        return replace(
            _safe_reviewer_base(),
            scenario=scenario,
            same_blocker_repeat_count=6,
            same_work_packet_hash_repeated=True,
            loop_escape_recorded=False,
            terminal_stop_or_route_mutation=False,
            same_family_repair_attempt_count=6,
            repair_loop_threshold=5,
            repair_loop_same_node_consecutive=True,
            repair_loop_threshold_evidence_visible=True,
            break_glass_duty_projected=False,
            ordinary_pm_repair_continued_over_threshold=True,
            same_family_pm_packets_superseded=False,
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
        if state.pm_requires_authorized_report_body and not state.pm_authorized_report_delivered:
            failures.append("PM repair decision was made before the required report body was delivered")
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
        if state.blocker_detected and not state.pm_package_formal_blocker_id_bound:
            failures.append("PM repair package did not bind blocker identity as a formal runtime field")

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

    if state.flowguard_recheck_requested:
        if not (
            state.flowguard_recheck_references_repair_result
            and state.flowguard_recheck_passed
            and state.flowguard_evidence_manifest_attached
        ):
            failures.append("FlowGuard recheck did not bind current repair result to an attached evidence manifest")
        if state.blocker_detected and not state.flowguard_evidence_formal_blocker_id_bound:
            failures.append("FlowGuard recheck evidence did not bind blocker identity as a formal evidence field")

    if state.flowguard_evidence_formal_blocker_id_bound and not state.staged_effect_blocker_id_bound:
        failures.append("FlowGuard evidence contains blocker identity but staged_effect.blocker_id is empty")

    if state.pm_repair_decision_recorded and not state.pm_flowguard_acceptance_identity_bound:
        failures.append("PM FlowGuard acceptance lost gate-derived repair blocker identity")

    if state.reviewer_recheck_requested:
        if not state.runtime_mechanical_identity_gate_passed:
            failures.append("reviewer received repair package before Runtime mechanical blocker identity gate passed")
        if not state.reviewer_packet_inherits_repair_identity:
            failures.append("reviewer recheck packet did not inherit repair blocker identity")
        if not (
            state.reviewer_recheck_references_current_blocker
            and state.reviewer_recheck_uses_worker_evidence
        ):
            failures.append("reviewer recheck is not bound to the current blocker and repair evidence")
        if state.flowguard_recheck_requested and not state.reviewer_recheck_uses_flowguard_evidence:
            failures.append("reviewer recheck lacks the current FlowGuard evidence produced for the repair")

    if state.blocker_closed and not (
        state.reviewer_recheck_requested
        and state.reviewer_recheck_references_current_blocker
        and state.reviewer_recheck_uses_worker_evidence
        and (not state.flowguard_recheck_requested or state.reviewer_recheck_uses_flowguard_evidence)
        and state.reviewer_recheck_passed
    ):
        failures.append("blocker was closed without a bound reviewer recheck pass")

    if state.flowguard_recheck_passed and not state.blocker_stage_current:
        failures.append("blocker repair stage was not updated after FlowGuard recheck pass")

    if state.blocker_identity_in_prose_only:
        failures.append("blocker identity appeared only in prose instead of formal repair fields")

    if state.formal_identity_missing_reached_reviewer:
        failures.append("formal blocker identity missing reached Reviewer instead of Runtime reissue")

    if (
        state.route_replacement_supersedes_prior_repair
        and (
            state.superseded_blocker_still_repair_open
            or not state.superseded_blocker_disposition_recorded
        )
    ):
        failures.append("prior-route repair blocker was not dispositioned after route replacement")

    if (
        not state.final_preflight_uses_current_effective_blockers
        or state.final_preflight_reports_noncurrent_repair_blocker
    ):
        failures.append("final preflight treated a noncurrent repair blocker as current authority")

    if state.followup_blocker_returned and not state.followup_blocker_recorded:
        failures.append("follow-up blocker returned by recheck was not recorded as current work")

    if (
        state.same_blocker_repeat_count >= 2
        and state.same_work_packet_hash_repeated
        and not (
            (state.loop_escape_recorded and state.terminal_stop_or_route_mutation)
            or state.break_glass_duty_projected
        )
    ):
        failures.append("same blocker repeated with same work packet and no route mutation or terminal blocker")

    if state.same_family_repair_attempt_count >= state.repair_loop_threshold and state.repair_loop_same_node_consecutive:
        if not state.repair_loop_threshold_evidence_visible:
            failures.append("same-node repair loop threshold exceeded without visible evidence")
        if (
            state.ordinary_pm_repair_continued_over_threshold
            or not state.break_glass_duty_projected
            or not state.same_family_pm_packets_superseded
        ):
            failures.append("same-node repair loop threshold exceeded but ordinary PM repair continued")

    return failures


class BlockerRepairInformationFlowStep:
    """Model one FlowPilot blocker repair information-flow transition.

    Input x State -> Set(Output x State)
    reads: blocker payload, delivered authorized report body, PM repair decision,
    PM repair package, worker repair packet, worker result, FlowGuard recheck
    evidence, reviewer recheck, repeated blocker/work-package identities
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
        "staged_effect_blocker_id",
        "flowguard_evidence_blocker_id",
        "superseded_repair_blocker_status",
        "final_preflight_current_effective_blockers",
    )
    writes = (
        "repair_flow_decision",
        "worker_packet_generation",
        "runtime_mechanical_identity_gate",
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
        and not (
            (state.loop_escape_recorded and state.terminal_stop_or_route_mutation)
            or state.break_glass_duty_projected
        )
    ):
        return InvariantResult.fail("accepted same-blocker no-progress loop")
    return InvariantResult.pass_()


def mechanical_identity_gate_precedes_review(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.reviewer_recheck_requested:
        if not (
            state.runtime_mechanical_identity_gate_passed
            and state.pm_package_formal_blocker_id_bound
            and state.staged_effect_blocker_id_bound
            and state.flowguard_evidence_formal_blocker_id_bound
        ):
            return InvariantResult.fail("accepted review reached before formal blocker identity gate")
    return InvariantResult.pass_()


def superseded_repair_blockers_are_dispositioned(state: State, trace: object) -> InvariantResult:
    del trace
    if (
        state.status == "accepted"
        and state.route_replacement_supersedes_prior_repair
        and (
            state.superseded_blocker_still_repair_open
            or not state.superseded_blocker_disposition_recorded
        )
    ):
        return InvariantResult.fail("accepted route replacement left prior-route repair blocker undispositioned")
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
    Invariant(
        name="mechanical_identity_gate_precedes_review",
        description="Runtime/Router mechanical blocker identity fields must be bound before Reviewer receives repair review.",
        predicate=mechanical_identity_gate_precedes_review,
    ),
    Invariant(
        name="superseded_repair_blockers_are_dispositioned",
        description="Route replacement must disposition superseded repair blockers instead of leaving them active.",
        predicate=superseded_repair_blockers_are_dispositioned,
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
