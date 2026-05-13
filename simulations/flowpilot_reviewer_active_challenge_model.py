"""FlowGuard model for reviewer independent challenge gates.

Risk intent brief:
- Validate that every human-like reviewer approval performs an independent
  challenge beyond the PM checklist.
- Protected harms: reviewer pass-through of low-standard PM packets, visible
  or exposed commitments being treated as decoration, hard failures being
  downgraded to residual notes, known evidence packages being treated as the
  full review boundary, final-user intent and product usefulness being omitted
  from applicable challenges, low-quality success being accepted because an
  artifact merely exists, PM losing useful higher-standard recommendations,
  reviewer role creep into PM route decisions, and simple reviews being
  overloaded with irrelevant heavyweight probes.
- Modeled state and side effects: reviewer scope restatement, explicit and
  implicit commitment extraction, failure-hypothesis generation, task-specific
  challenge actions, final-user/product usefulness challenge, direct evidence
  discovery or waiver handling, blocker triage, and PM reroute/repair/
  recommendation requests.
- Hard invariants: a pass requires a complete independent challenge report;
  hard requirement or core-commitment failures must block; challenge actions
  must fit the current task family; known evidence must be treated as a
  starting point rather than a boundary; uncheckable surfaces need a waiver or
  blocker; simple tasks must stay lightweight.
- Blindspot: this model checks the reviewer process contract shape. It does
  not judge domain quality directly; production cards and tests must bind the
  fields to real reviewer reports.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_UI_REVIEW = "valid_ui_review"
VALID_CODE_REVIEW = "valid_code_review"
VALID_DOCUMENT_REVIEW = "valid_document_review"
VALID_FINAL_REPLAY_REVIEW = "valid_final_replay_review"
VALID_SIMPLE_REVIEW = "valid_simple_review"

CHECKLIST_ONLY_PASS = "checklist_only_pass"
REVIEW_PACKAGE_TREATED_AS_BOUNDARY = "review_package_treated_as_boundary"
NO_EVIDENCE_DISCOVERY_OR_WAIVER = "no_evidence_discovery_or_waiver"
MISSING_SCOPE_RESTATEMENT = "missing_scope_restatement"
MISSING_IMPLICIT_COMMITMENTS = "missing_implicit_commitments"
NO_FAILURE_HYPOTHESES = "no_failure_hypotheses"
NO_CHALLENGE_ACTIONS = "no_challenge_actions"
GENERIC_ACTIONS_NOT_TASK_SPECIFIC = "generic_actions_not_task_specific"
NO_DIRECT_EVIDENCE_OR_WAIVER = "no_direct_evidence_or_waiver"
HARD_ISSUE_DOWNGRADED_TO_RESIDUAL = "hard_issue_downgraded_to_residual"
CORE_COMMITMENT_UNVERIFIED = "core_commitment_unverified"
UNCHECKABLE_WITHOUT_WAIVER = "uncheckable_without_waiver"
MISSING_REROUTE_REQUEST_FOR_BLOCKER = "missing_reroute_request_for_blocker"
PM_IMPROVEMENT_SIGNAL_DROPPED = "pm_improvement_signal_dropped"
SIMPLE_REVIEW_OVERBURDENED = "simple_review_overburdened"
USER_PERSPECTIVE_APPLICABILITY_UNDECIDED = "user_perspective_applicability_undecided"
FINAL_USER_INTENT_OMITTED = "final_user_intent_omitted"
USER_PERSPECTIVE_FAILURE_HYPOTHESIS_MISSING = "user_perspective_failure_hypothesis_missing"
HARD_USER_INTENT_FAILURE_DOWNGRADED = "hard_user_intent_failure_downgraded"
FINAL_REPLAY_LEDGER_ONLY = "final_replay_ledger_only"
USER_FACING_EVIDENCE_EXISTS_ONLY = "user_facing_evidence_exists_only"
REVIEWER_MADE_PM_ROUTE_DECISION = "reviewer_made_pm_route_decision"
LOW_QUALITY_SUCCESS_CHALLENGE_MISSING = "low_quality_success_challenge_missing"
EXISTENCE_ONLY_HARD_PART_EVIDENCE_ACCEPTED = "existence_only_hard_part_evidence_accepted"

VALID_SCENARIOS = (
    VALID_UI_REVIEW,
    VALID_CODE_REVIEW,
    VALID_DOCUMENT_REVIEW,
    VALID_FINAL_REPLAY_REVIEW,
    VALID_SIMPLE_REVIEW,
)
NEGATIVE_SCENARIOS = (
    CHECKLIST_ONLY_PASS,
    REVIEW_PACKAGE_TREATED_AS_BOUNDARY,
    NO_EVIDENCE_DISCOVERY_OR_WAIVER,
    MISSING_SCOPE_RESTATEMENT,
    MISSING_IMPLICIT_COMMITMENTS,
    NO_FAILURE_HYPOTHESES,
    NO_CHALLENGE_ACTIONS,
    GENERIC_ACTIONS_NOT_TASK_SPECIFIC,
    NO_DIRECT_EVIDENCE_OR_WAIVER,
    HARD_ISSUE_DOWNGRADED_TO_RESIDUAL,
    CORE_COMMITMENT_UNVERIFIED,
    UNCHECKABLE_WITHOUT_WAIVER,
    MISSING_REROUTE_REQUEST_FOR_BLOCKER,
    PM_IMPROVEMENT_SIGNAL_DROPPED,
    SIMPLE_REVIEW_OVERBURDENED,
    USER_PERSPECTIVE_APPLICABILITY_UNDECIDED,
    FINAL_USER_INTENT_OMITTED,
    USER_PERSPECTIVE_FAILURE_HYPOTHESIS_MISSING,
    HARD_USER_INTENT_FAILURE_DOWNGRADED,
    FINAL_REPLAY_LEDGER_ONLY,
    USER_FACING_EVIDENCE_EXISTS_ONLY,
    REVIEWER_MADE_PM_ROUTE_DECISION,
    LOW_QUALITY_SUCCESS_CHALLENGE_MISSING,
    EXISTENCE_ONLY_HARD_PART_EVIDENCE_ACCEPTED,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract reviewer challenge evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    task_family: str = "unset"  # ui_product | code_change | document | final_replay | simple_review

    pm_review_context_present: bool = False
    pm_checklist_treated_as_floor: bool = False
    known_evidence_treated_as_starting_points: bool = False
    evidence_discovery_or_reasoned_waiver_performed: bool = False

    scope_restatement_written: bool = False
    explicit_commitments_extracted: bool = False
    implicit_commitments_extracted: bool = False
    failure_hypotheses_generated: bool = False
    challenge_actions_recorded: bool = False
    challenge_actions_task_specific: bool = False
    challenge_actions_executed_or_blocker_recorded: bool = False
    direct_evidence_or_approved_waiver_present: bool = False
    core_commitments_verified_or_blocked: bool = False

    final_user_perspective_applicability_decided: bool = False
    final_user_perspective_required: bool = False
    final_user_intent_considered: bool = False
    user_perspective_failure_hypothesis_recorded: bool = False
    user_facing_evidence_supports_claims: bool = False
    delivery_replay_required: bool = False
    delivered_product_replayed_from_user_perspective: bool = False
    low_quality_success_applicability_decided: bool = False
    low_quality_success_challenge_required: bool = False
    low_quality_success_challenged: bool = False
    thin_success_failure_hypothesis_recorded: bool = False
    proof_of_depth_challenge_performed: bool = False
    hard_part_claim_supported_by_depth_evidence: bool = False

    hard_issue_found: bool = False
    hard_issue_classified_blocker: bool = False
    hard_issue_downgraded_to_residual: bool = False
    hard_user_intent_failure_found: bool = False
    hard_user_intent_failure_classified_blocker: bool = False
    hard_user_intent_failure_downgraded_to_suggestion: bool = False
    uncheckable_surface_present: bool = False
    waiver_or_blocker_for_uncheckable: bool = False
    reroute_request_recorded_when_needed: bool = True
    higher_standard_opportunity_found: bool = False
    pm_decision_support_recommendation_recorded: bool = True
    reviewer_made_pm_route_decision: bool = False

    reviewer_passed: bool = False
    reviewer_blocked: bool = False
    report_schema_complete: bool = False
    simple_review_overburdened: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ReviewerActiveChallengeStep:
    """Model one reviewer independent-challenge transition.

    Input x State -> Set(Output x State)
    reads: PM review context, user requirements, current artifact, reviewer
    report fields, blocker triage
    writes: selected scenario or terminal reviewer challenge decision
    idempotency: scenario facts are monotonic; terminal decisions are final for
    this abstract gate evaluation.
    """

    name = "ReviewerActiveChallengeStep"
    input_description = "FlowPilot reviewer active-challenge tick"
    output_description = "one reviewer active-challenge transition"
    reads = (
        "pm_review_context",
        "user_requirements",
        "current_artifact",
        "reviewer_report_fields",
        "blocker_triage",
    )
    writes = ("scenario_facts", "terminal_reviewer_challenge_decision")
    idempotency = "monotonic reviewer challenge facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _valid_review_state(scenario: str, task_family: str) -> State:
    user_perspective_required = task_family != "simple_review"
    delivery_replay_required = task_family == "final_replay"
    return State(
        status="running",
        scenario=scenario,
        task_family=task_family,
        pm_review_context_present=True,
        pm_checklist_treated_as_floor=True,
        known_evidence_treated_as_starting_points=True,
        evidence_discovery_or_reasoned_waiver_performed=True,
        scope_restatement_written=True,
        explicit_commitments_extracted=True,
        implicit_commitments_extracted=True,
        failure_hypotheses_generated=True,
        challenge_actions_recorded=True,
        challenge_actions_task_specific=True,
        challenge_actions_executed_or_blocker_recorded=True,
        direct_evidence_or_approved_waiver_present=True,
        core_commitments_verified_or_blocked=True,
        final_user_perspective_applicability_decided=True,
        final_user_perspective_required=user_perspective_required,
        final_user_intent_considered=user_perspective_required,
        user_perspective_failure_hypothesis_recorded=user_perspective_required,
        user_facing_evidence_supports_claims=user_perspective_required,
        delivery_replay_required=delivery_replay_required,
        delivered_product_replayed_from_user_perspective=delivery_replay_required,
        low_quality_success_applicability_decided=True,
        low_quality_success_challenge_required=user_perspective_required,
        low_quality_success_challenged=user_perspective_required,
        thin_success_failure_hypothesis_recorded=user_perspective_required,
        proof_of_depth_challenge_performed=user_perspective_required,
        hard_part_claim_supported_by_depth_evidence=user_perspective_required,
        reviewer_passed=True,
        report_schema_complete=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_UI_REVIEW:
        return _valid_review_state(scenario, "ui_product")
    if scenario == VALID_CODE_REVIEW:
        return _valid_review_state(scenario, "code_change")
    if scenario == VALID_DOCUMENT_REVIEW:
        return _valid_review_state(scenario, "document")
    if scenario == VALID_FINAL_REPLAY_REVIEW:
        return _valid_review_state(scenario, "final_replay")
    if scenario == VALID_SIMPLE_REVIEW:
        return _valid_review_state(scenario, "simple_review")

    state = _valid_review_state(scenario, "ui_product")
    if scenario == CHECKLIST_ONLY_PASS:
        return replace(
            state,
            pm_checklist_treated_as_floor=False,
            scope_restatement_written=False,
            explicit_commitments_extracted=False,
            implicit_commitments_extracted=False,
            failure_hypotheses_generated=False,
            challenge_actions_recorded=False,
            challenge_actions_task_specific=False,
            challenge_actions_executed_or_blocker_recorded=False,
            direct_evidence_or_approved_waiver_present=False,
            core_commitments_verified_or_blocked=False,
            report_schema_complete=False,
        )
    if scenario == REVIEW_PACKAGE_TREATED_AS_BOUNDARY:
        return replace(
            state,
            known_evidence_treated_as_starting_points=False,
            evidence_discovery_or_reasoned_waiver_performed=False,
        )
    if scenario == NO_EVIDENCE_DISCOVERY_OR_WAIVER:
        return replace(state, evidence_discovery_or_reasoned_waiver_performed=False)
    if scenario == MISSING_SCOPE_RESTATEMENT:
        return replace(state, scope_restatement_written=False)
    if scenario == MISSING_IMPLICIT_COMMITMENTS:
        return replace(state, implicit_commitments_extracted=False)
    if scenario == NO_FAILURE_HYPOTHESES:
        return replace(state, failure_hypotheses_generated=False)
    if scenario == NO_CHALLENGE_ACTIONS:
        return replace(
            state,
            challenge_actions_recorded=False,
            challenge_actions_executed_or_blocker_recorded=False,
        )
    if scenario == GENERIC_ACTIONS_NOT_TASK_SPECIFIC:
        return replace(state, challenge_actions_task_specific=False)
    if scenario == NO_DIRECT_EVIDENCE_OR_WAIVER:
        return replace(state, direct_evidence_or_approved_waiver_present=False)
    if scenario == HARD_ISSUE_DOWNGRADED_TO_RESIDUAL:
        return replace(
            state,
            hard_issue_found=True,
            hard_issue_classified_blocker=False,
            hard_issue_downgraded_to_residual=True,
            reviewer_passed=True,
            reviewer_blocked=False,
        )
    if scenario == CORE_COMMITMENT_UNVERIFIED:
        return replace(state, core_commitments_verified_or_blocked=False)
    if scenario == UNCHECKABLE_WITHOUT_WAIVER:
        return replace(
            state,
            uncheckable_surface_present=True,
            waiver_or_blocker_for_uncheckable=False,
        )
    if scenario == MISSING_REROUTE_REQUEST_FOR_BLOCKER:
        return replace(
            state,
            hard_issue_found=True,
            hard_issue_classified_blocker=True,
            reviewer_passed=False,
            reviewer_blocked=True,
            reroute_request_recorded_when_needed=False,
        )
    if scenario == PM_IMPROVEMENT_SIGNAL_DROPPED:
        return replace(
            state,
            higher_standard_opportunity_found=True,
            pm_decision_support_recommendation_recorded=False,
        )
    if scenario == SIMPLE_REVIEW_OVERBURDENED:
        return replace(
            _valid_review_state(scenario, "simple_review"),
            simple_review_overburdened=True,
        )
    if scenario == USER_PERSPECTIVE_APPLICABILITY_UNDECIDED:
        return replace(state, final_user_perspective_applicability_decided=False)
    if scenario == FINAL_USER_INTENT_OMITTED:
        return replace(state, final_user_intent_considered=False)
    if scenario == USER_PERSPECTIVE_FAILURE_HYPOTHESIS_MISSING:
        return replace(state, user_perspective_failure_hypothesis_recorded=False)
    if scenario == HARD_USER_INTENT_FAILURE_DOWNGRADED:
        return replace(
            state,
            hard_user_intent_failure_found=True,
            hard_user_intent_failure_classified_blocker=False,
            hard_user_intent_failure_downgraded_to_suggestion=True,
            reviewer_passed=True,
            reviewer_blocked=False,
        )
    if scenario == FINAL_REPLAY_LEDGER_ONLY:
        return replace(
            _valid_review_state(scenario, "final_replay"),
            delivered_product_replayed_from_user_perspective=False,
        )
    if scenario == USER_FACING_EVIDENCE_EXISTS_ONLY:
        return replace(state, user_facing_evidence_supports_claims=False)
    if scenario == REVIEWER_MADE_PM_ROUTE_DECISION:
        return replace(state, reviewer_made_pm_route_decision=True)
    if scenario == LOW_QUALITY_SUCCESS_CHALLENGE_MISSING:
        return replace(
            state,
            low_quality_success_challenged=False,
            thin_success_failure_hypothesis_recorded=False,
            proof_of_depth_challenge_performed=False,
        )
    if scenario == EXISTENCE_ONLY_HARD_PART_EVIDENCE_ACCEPTED:
        return replace(state, hard_part_claim_supported_by_depth_evidence=False)
    return state


def reviewer_challenge_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.reviewer_passed and not state.pm_review_context_present:
        failures.append("reviewer passed without PM review context")
    if state.reviewer_passed and not state.pm_checklist_treated_as_floor:
        failures.append("reviewer treated PM checklist as the full review instead of the floor")
    if state.reviewer_passed and not state.known_evidence_treated_as_starting_points:
        failures.append("reviewer treated delivered evidence as the review boundary")
    if state.reviewer_passed and not state.evidence_discovery_or_reasoned_waiver_performed:
        failures.append("reviewer pass lacks independent evidence discovery or a reasoned waiver")
    if state.reviewer_passed and not state.scope_restatement_written:
        failures.append("reviewer pass lacks scope restatement")
    if state.reviewer_passed and not state.explicit_commitments_extracted:
        failures.append("reviewer pass lacks explicit commitment extraction")
    if state.reviewer_passed and not state.implicit_commitments_extracted:
        failures.append("reviewer pass lacks implicit commitment extraction")
    if state.reviewer_passed and not state.failure_hypotheses_generated:
        failures.append("reviewer pass lacks active failure hypotheses")
    if state.reviewer_passed and not state.challenge_actions_recorded:
        failures.append("reviewer pass lacks recorded challenge actions")
    if state.reviewer_passed and not state.challenge_actions_task_specific:
        failures.append("reviewer challenge actions do not fit the task family")
    if state.reviewer_passed and not state.challenge_actions_executed_or_blocker_recorded:
        failures.append("reviewer pass lacks executed challenge actions or a blocker")
    if state.reviewer_passed and not state.direct_evidence_or_approved_waiver_present:
        failures.append("reviewer pass lacks direct evidence or an approved waiver")
    if state.reviewer_passed and not state.core_commitments_verified_or_blocked:
        failures.append("reviewer pass leaves core commitments unverified and unblocked")
    if state.reviewer_passed and not state.final_user_perspective_applicability_decided:
        failures.append("reviewer pass lacks final-user perspective applicability decision")
    if (
        state.reviewer_passed
        and state.final_user_perspective_required
        and not state.final_user_intent_considered
    ):
        failures.append("reviewer pass omits final-user intent and product usefulness challenge")
    if (
        state.reviewer_passed
        and state.final_user_perspective_required
        and not state.user_perspective_failure_hypothesis_recorded
    ):
        failures.append("reviewer pass lacks final-user failure hypothesis")
    if (
        state.reviewer_passed
        and state.final_user_perspective_required
        and not state.user_facing_evidence_supports_claims
    ):
        failures.append("reviewer accepted user-facing quality claims from existence-only evidence")
    if (
        state.reviewer_passed
        and state.delivery_replay_required
        and not state.delivered_product_replayed_from_user_perspective
    ):
        failures.append("final replay used ledger cleanliness without delivered-product user-perspective replay")
    if state.reviewer_passed and not state.low_quality_success_applicability_decided:
        failures.append("reviewer pass lacks low-quality-success applicability decision")
    if (
        state.reviewer_passed
        and state.low_quality_success_challenge_required
        and not (
            state.low_quality_success_challenged
            and state.thin_success_failure_hypothesis_recorded
            and state.proof_of_depth_challenge_performed
        )
    ):
        failures.append("reviewer pass lacks low-quality-success challenge, thin-success hypothesis, or proof-of-depth probe")
    if (
        state.reviewer_passed
        and state.low_quality_success_challenge_required
        and not state.hard_part_claim_supported_by_depth_evidence
    ):
        failures.append("reviewer accepted hard-part quality claim from existence-only evidence")
    if state.reviewer_passed and not state.report_schema_complete:
        failures.append("reviewer pass lacks independent challenge report fields")

    if state.hard_issue_found and (
        not state.hard_issue_classified_blocker
        or state.hard_issue_downgraded_to_residual
        or state.reviewer_passed
    ):
        failures.append("reviewer did not block a hard requirement or core commitment failure")
    if state.hard_user_intent_failure_found and (
        not state.hard_user_intent_failure_classified_blocker
        or state.hard_user_intent_failure_downgraded_to_suggestion
        or state.reviewer_passed
    ):
        failures.append("reviewer did not block a hard final-user intent or product usefulness failure")
    if state.uncheckable_surface_present and not state.waiver_or_blocker_for_uncheckable:
        failures.append("reviewer found an uncheckable surface without waiver or blocker")
    if state.reviewer_blocked and state.hard_issue_found and not state.reroute_request_recorded_when_needed:
        failures.append("reviewer blocker lacks PM reroute or repair request")
    if state.higher_standard_opportunity_found and not state.pm_decision_support_recommendation_recorded:
        failures.append("reviewer dropped a higher-standard PM decision-support recommendation")
    if state.task_family == "simple_review" and state.simple_review_overburdened:
        failures.append("simple review was overburdened with irrelevant heavyweight challenge work")
    if state.reviewer_made_pm_route_decision:
        failures.append("reviewer made a PM-owned route or repair decision instead of decision-support")
    if state.status in {"accepted", "rejected"} and not (state.reviewer_passed or state.reviewer_blocked):
        failures.append("review ended without pass or block decision")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = reviewer_challenge_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="reviewer_active_challenge_ok"),
        )


def accepts_only_valid_reviews(state: State, trace) -> InvariantResult:
    del trace
    failures = reviewer_challenge_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid reviewer challenge result was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid reviewer challenge result was rejected")
    return InvariantResult.pass_()


def pass_requires_independent_challenge(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if "reviewer pass lacks" in failure or "checklist" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def hard_commitment_failures_block(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if "hard requirement" in failure or "core commitment" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def challenge_actions_fit_scope(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if (
            "task family" in failure
            or "direct evidence" in failure
            or "evidence discovery" in failure
            or "review boundary" in failure
            or "uncheckable" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def higher_standard_signals_reach_pm(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if "higher-standard PM decision-support recommendation" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def user_perspective_challenge_when_applicable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if (
            "final-user" in failure
            or "product usefulness" in failure
            or "user-facing quality claims" in failure
            or "delivered-product user-perspective replay" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def low_quality_success_challenged_when_applicable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if (
            "low-quality-success" in failure
            or "thin-success" in failure
            or "proof-of-depth" in failure
            or "existence-only evidence" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def reviewer_respects_pm_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if "PM-owned route or repair decision" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def simple_reviews_stay_lightweight(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in reviewer_challenge_failures(state):
        if "simple review was overburdened" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_reviews",
        description="Only reviewer reports with complete independent challenge evidence can be accepted.",
        predicate=accepts_only_valid_reviews,
    ),
    Invariant(
        name="pass_requires_independent_challenge",
        description="Reviewer pass decisions require challenge fields beyond the PM checklist.",
        predicate=pass_requires_independent_challenge,
    ),
    Invariant(
        name="hard_commitment_failures_block",
        description="Hard requirement and core-commitment failures cannot be residual notes.",
        predicate=hard_commitment_failures_block,
    ),
    Invariant(
        name="challenge_actions_fit_scope",
        description="Challenge actions must fit the current task family and cite direct evidence or waiver.",
        predicate=challenge_actions_fit_scope,
    ),
    Invariant(
        name="simple_reviews_stay_lightweight",
        description="Simple reviews must not be burdened by irrelevant heavyweight challenge work.",
        predicate=simple_reviews_stay_lightweight,
    ),
    Invariant(
        name="higher_standard_signals_reach_pm",
        description="Reviewer higher-standard findings must reach PM as decision-support.",
        predicate=higher_standard_signals_reach_pm,
    ),
    Invariant(
        name="user_perspective_challenge_when_applicable",
        description="Applicable reviews must challenge final-user intent, product usefulness, and delivered-output evidence.",
        predicate=user_perspective_challenge_when_applicable,
    ),
    Invariant(
        name="reviewer_respects_pm_authority",
        description="Reviewer may block or advise but must not take PM-owned route or repair decisions.",
        predicate=reviewer_respects_pm_authority,
    ),
    Invariant(
        name="low_quality_success_challenged_when_applicable",
        description="Applicable reviewer passes must challenge thin success and require proof of depth for hard-part quality claims.",
        predicate=low_quality_success_challenged_when_applicable,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((ReviewerActiveChallengeStep(),), name="flowpilot_reviewer_active_challenge")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not reviewer_challenge_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
