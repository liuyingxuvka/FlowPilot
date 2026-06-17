"""FlowGuard model for FlowPilot rejection-feedback and retry liveness.

The model is intentionally a parent matrix, not a replacement for packet,
reviewer, FlowGuard, PM, or terminal child models. It checks that rejected
outputs either get actionable repair guidance and a semantic-delta retry, or
become a stable blocker/repair/stop/wait/break-glass disposition.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_rejection_liveness_matrix"
MAX_SEQUENCE_LENGTH = 2

CONTRACT_FAMILIES = (
    "startup_intake",
    "packet_envelope",
    "packet_body",
    "result_envelope",
    "result_body",
    "flowguard_report",
    "reviewer_report",
    "pm_repair_decision",
    "route_mutation",
    "terminal_replay",
    "acceptance_item",
)

MALFORMED_DEFECT_CLASSES = (
    "missing_field",
    "missing_body",
    "missing_path",
    "missing_hash",
    "wrong_owner",
    "wrong_id",
    "unsupported_enum",
    "stale_evidence",
    "prose_only_critical_content",
    "contradictory_pass_blocker",
)

RETRY_DEFECT_CLASSES = (
    "same_payload_retry",
    "same_action_retry",
    "corrected_retry",
)

REQUIRED_REJECTION_LIVENESS_CELLS = tuple(
    {
        "cell_id": f"{family}.{defect}",
        "family": family,
        "defect_class": defect,
        "branch_kind": "negative_path" if defect != "corrected_retry" else "repair_path",
        "confidence_boundary": "contract_bound_control_flow",
        "required_evidence_owner": (
            "rejection_liveness_fake_ai_matrix"
            if defect in RETRY_DEFECT_CLASSES
            else "rejection_liveness_contract_matrix"
        ),
    }
    for family, defect in product(CONTRACT_FAMILIES, MALFORMED_DEFECT_CLASSES + RETRY_DEFECT_CLASSES)
)


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    rejected_output_seen: bool = False
    feedback_precise: bool = False
    feedback_names_subject: bool = False
    feedback_names_owner: bool = False
    feedback_names_missing_or_invalid_fields: bool = False
    feedback_names_legal_command_or_event: bool = False
    feedback_names_minimum_valid_shape: bool = False
    next_attempt_seen: bool = False
    next_attempt_semantic_delta: bool = False
    current_external_or_user_event_seen: bool = False
    explicit_wait_evidence: bool = False
    blocker_or_repair_disposition: bool = False
    stop_or_break_glass_disposition: bool = False
    same_payload_retry: bool = False
    same_action_retry: bool = False
    repeated_same_action_over_threshold: bool = False
    stuck_previously_detected: bool = False
    stuck_absorbed: bool = False
    parent_mesh_green_claimed: bool = False
    safe_to_continue_claimed: bool = False
    synthetic_evidence_only: bool = False
    live_ai_quality_claimed: bool = False
    required_cell_owner_complete: bool = True
    required_cell_test_current: bool = True


@dataclass(frozen=True)
class Tick:
    """One rejection/liveness matrix decision."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_rejected_corrected() -> State:
    return State(
        scenario="valid_rejected_corrected",
        status="selected",
        rejected_output_seen=True,
        feedback_precise=True,
        feedback_names_subject=True,
        feedback_names_owner=True,
        feedback_names_missing_or_invalid_fields=True,
        feedback_names_legal_command_or_event=True,
        feedback_names_minimum_valid_shape=True,
        next_attempt_seen=True,
        next_attempt_semantic_delta=True,
        safe_to_continue_claimed=True,
    )


def _valid_blocker_absorption() -> State:
    return State(
        scenario="valid_blocker_absorption",
        status="selected",
        rejected_output_seen=True,
        feedback_precise=True,
        feedback_names_subject=True,
        feedback_names_owner=True,
        feedback_names_missing_or_invalid_fields=True,
        feedback_names_legal_command_or_event=True,
        feedback_names_minimum_valid_shape=True,
        next_attempt_seen=True,
        same_payload_retry=True,
        blocker_or_repair_disposition=True,
        safe_to_continue_claimed=False,
    )


def _valid_stuck_absorbed() -> State:
    return State(
        scenario="valid_stuck_absorbed",
        status="selected",
        repeated_same_action_over_threshold=True,
        stuck_previously_detected=True,
        stuck_absorbed=True,
        blocker_or_repair_disposition=True,
        safe_to_continue_claimed=False,
        parent_mesh_green_claimed=False,
    )


def _valid_user_wait() -> State:
    return State(
        scenario="valid_user_wait",
        status="selected",
        repeated_same_action_over_threshold=True,
        explicit_wait_evidence=True,
        current_external_or_user_event_seen=True,
        stuck_absorbed=True,
        safe_to_continue_claimed=True,
    )


SCENARIOS = {
    "valid_rejected_corrected": _valid_rejected_corrected(),
    "valid_blocker_absorption": _valid_blocker_absorption(),
    "valid_stuck_absorbed": _valid_stuck_absorbed(),
    "valid_user_wait": _valid_user_wait(),
    "vague_feedback_continues": replace(
        _valid_rejected_corrected(),
        scenario="vague_feedback_continues",
        feedback_precise=False,
        feedback_names_missing_or_invalid_fields=False,
    ),
    "missing_subject_feedback_continues": replace(
        _valid_rejected_corrected(),
        scenario="missing_subject_feedback_continues",
        feedback_names_subject=False,
    ),
    "missing_owner_feedback_continues": replace(
        _valid_rejected_corrected(),
        scenario="missing_owner_feedback_continues",
        feedback_names_owner=False,
    ),
    "missing_legal_repair_shape_continues": replace(
        _valid_rejected_corrected(),
        scenario="missing_legal_repair_shape_continues",
        feedback_names_legal_command_or_event=False,
        feedback_names_minimum_valid_shape=False,
    ),
    "same_payload_retry_claims_progress": replace(
        _valid_rejected_corrected(),
        scenario="same_payload_retry_claims_progress",
        next_attempt_semantic_delta=False,
        same_payload_retry=True,
        safe_to_continue_claimed=True,
    ),
    "same_action_retry_claims_progress": replace(
        _valid_rejected_corrected(),
        scenario="same_action_retry_claims_progress",
        next_attempt_semantic_delta=False,
        same_action_retry=True,
        safe_to_continue_claimed=True,
    ),
    "stuck_detected_not_absorbed": State(
        scenario="stuck_detected_not_absorbed",
        status="selected",
        repeated_same_action_over_threshold=True,
        stuck_previously_detected=True,
        stuck_absorbed=False,
        safe_to_continue_claimed=True,
    ),
    "mesh_green_live_repeated_action": State(
        scenario="mesh_green_live_repeated_action",
        status="selected",
        repeated_same_action_over_threshold=True,
        stuck_previously_detected=True,
        parent_mesh_green_claimed=True,
        safe_to_continue_claimed=True,
    ),
    "synthetic_live_quality_overclaim": replace(
        _valid_rejected_corrected(),
        scenario="synthetic_live_quality_overclaim",
        synthetic_evidence_only=True,
        live_ai_quality_claimed=True,
    ),
    "required_cell_missing_owner": replace(
        _valid_rejected_corrected(),
        scenario="required_cell_missing_owner",
        required_cell_owner_complete=False,
    ),
    "required_cell_stale_test": replace(
        _valid_rejected_corrected(),
        scenario="required_cell_stale_test",
        required_cell_test_current=False,
    ),
}

VALID_SCENARIOS = {
    "valid_rejected_corrected",
    "valid_blocker_absorption",
    "valid_stuck_absorbed",
    "valid_user_wait",
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def rejection_liveness_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.rejected_output_seen:
        if not state.feedback_precise:
            failures.append("rejection_feedback_not_precise")
        if not state.feedback_names_subject:
            failures.append("rejection_feedback_missing_subject")
        if not state.feedback_names_owner:
            failures.append("rejection_feedback_missing_owner")
        if not state.feedback_names_missing_or_invalid_fields:
            failures.append("rejection_feedback_missing_field_details")
        if not state.feedback_names_legal_command_or_event:
            failures.append("rejection_feedback_missing_legal_command_or_event")
        if not state.feedback_names_minimum_valid_shape:
            failures.append("rejection_feedback_missing_minimum_valid_shape")
        if state.next_attempt_seen:
            disposition = (
                state.current_external_or_user_event_seen
                or state.explicit_wait_evidence
                or state.blocker_or_repair_disposition
                or state.stop_or_break_glass_disposition
            )
            if not state.next_attempt_semantic_delta and not disposition:
                failures.append("post_rejection_continuation_has_no_delta_or_disposition")
            if state.safe_to_continue_claimed and (state.same_payload_retry or state.same_action_retry) and not state.next_attempt_semantic_delta:
                failures.append("same_payload_or_action_retry_claimed_progress")
    if state.repeated_same_action_over_threshold:
        clearance = (
            state.current_external_or_user_event_seen
            or state.explicit_wait_evidence
            or state.blocker_or_repair_disposition
            or state.stop_or_break_glass_disposition
        )
        if not state.stuck_absorbed and not clearance:
            failures.append("repeated_action_stuck_not_absorbed")
        if state.safe_to_continue_claimed and not clearance:
            failures.append("repeated_action_safe_to_continue_without_progress")
        if state.parent_mesh_green_claimed:
            failures.append("parent_mesh_green_over_repeated_action")
    if state.synthetic_evidence_only and state.live_ai_quality_claimed:
        failures.append("synthetic_evidence_overclaims_live_ai_quality")
    if not state.required_cell_owner_complete:
        failures.append("required_rejection_liveness_cell_missing_owner")
    if not state.required_cell_test_current:
        failures.append("required_rejection_liveness_cell_stale_or_missing_test")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = rejection_liveness_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


class RejectionLivenessStep:
    """Classify one rejected output and follow-up continuation.

    Input x State -> Set(Output x State)
    reads: packet/result/report contract status, rejection feedback, current
    run lifecycle history, synthetic coverage ownership, live projection
    writes: rejection liveness decision or blocking finding
    idempotency: pure classification over immutable run and contract evidence
    """

    name = "RejectionLivenessStep"
    reads = (
        "contract_family",
        "rejection_feedback",
        "next_attempt_projection",
        "lifecycle_guard_history",
        "model_mesh_live_projection",
        "synthetic_coverage_rows",
    )
    writes = ("rejection_liveness_decision", "required_cell_coverage_finding")
    input_description = "one rejected output or repeated current-run action"
    output_description = "one accepted continuation or one blocker classification"
    idempotency = "classification is keyed by run id, subject id, and cell id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        failures = rejection_liveness_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not rejection_liveness_failures(state):
        return InvariantResult.fail("safe rejection/liveness state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted rejection/liveness states cannot contain missing feedback, no-delta retry, unabsorbed stuck, or stale matrix evidence.",
        accepted_states_are_safe,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((RejectionLivenessStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: rejection_liveness_failures(state) for name, state in hazard_states().items()}

