"""FlowGuard model for reviewer independent challenge gates.

Risk intent brief:
- Validate that every human-like reviewer approval performs an independent
  challenge beyond the PM checklist.
- Protected harms: reviewer pass-through of low-standard PM packets, visible
  or exposed commitments being treated as decoration, hard failures being
  downgraded to residual notes, and simple reviews being overloaded with
  irrelevant heavyweight probes.
- Modeled state and side effects: reviewer scope restatement, explicit and
  implicit commitment extraction, failure-hypothesis generation, task-specific
  challenge actions, direct evidence or waiver handling, blocker triage, and
  PM reroute/repair requests.
- Hard invariants: a pass requires a complete independent challenge report;
  hard requirement or core-commitment failures must block; challenge actions
  must fit the current task family; uncheckable surfaces need a waiver or
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
VALID_SIMPLE_REVIEW = "valid_simple_review"

CHECKLIST_ONLY_PASS = "checklist_only_pass"
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
SIMPLE_REVIEW_OVERBURDENED = "simple_review_overburdened"

VALID_SCENARIOS = (
    VALID_UI_REVIEW,
    VALID_CODE_REVIEW,
    VALID_DOCUMENT_REVIEW,
    VALID_SIMPLE_REVIEW,
)
NEGATIVE_SCENARIOS = (
    CHECKLIST_ONLY_PASS,
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
    SIMPLE_REVIEW_OVERBURDENED,
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
    task_family: str = "unset"  # ui_product | code_change | document | simple_review

    pm_review_context_present: bool = False
    pm_checklist_treated_as_floor: bool = False

    scope_restatement_written: bool = False
    explicit_commitments_extracted: bool = False
    implicit_commitments_extracted: bool = False
    failure_hypotheses_generated: bool = False
    challenge_actions_recorded: bool = False
    challenge_actions_task_specific: bool = False
    challenge_actions_executed_or_blocker_recorded: bool = False
    direct_evidence_or_approved_waiver_present: bool = False
    core_commitments_verified_or_blocked: bool = False

    hard_issue_found: bool = False
    hard_issue_classified_blocker: bool = False
    hard_issue_downgraded_to_residual: bool = False
    uncheckable_surface_present: bool = False
    waiver_or_blocker_for_uncheckable: bool = False
    reroute_request_recorded_when_needed: bool = True

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
    return State(
        status="running",
        scenario=scenario,
        task_family=task_family,
        pm_review_context_present=True,
        pm_checklist_treated_as_floor=True,
        scope_restatement_written=True,
        explicit_commitments_extracted=True,
        implicit_commitments_extracted=True,
        failure_hypotheses_generated=True,
        challenge_actions_recorded=True,
        challenge_actions_task_specific=True,
        challenge_actions_executed_or_blocker_recorded=True,
        direct_evidence_or_approved_waiver_present=True,
        core_commitments_verified_or_blocked=True,
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
    if scenario == SIMPLE_REVIEW_OVERBURDENED:
        return replace(
            _valid_review_state(scenario, "simple_review"),
            simple_review_overburdened=True,
        )
    return state


def reviewer_challenge_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.reviewer_passed and not state.pm_review_context_present:
        failures.append("reviewer passed without PM review context")
    if state.reviewer_passed and not state.pm_checklist_treated_as_floor:
        failures.append("reviewer treated PM checklist as the full review instead of the floor")
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
    if state.reviewer_passed and not state.report_schema_complete:
        failures.append("reviewer pass lacks independent challenge report fields")

    if state.hard_issue_found and (
        not state.hard_issue_classified_blocker
        or state.hard_issue_downgraded_to_residual
        or state.reviewer_passed
    ):
        failures.append("reviewer did not block a hard requirement or core commitment failure")
    if state.uncheckable_surface_present and not state.waiver_or_blocker_for_uncheckable:
        failures.append("reviewer found an uncheckable surface without waiver or blocker")
    if state.reviewer_blocked and state.hard_issue_found and not state.reroute_request_recorded_when_needed:
        failures.append("reviewer blocker lacks PM reroute or repair request")
    if state.task_family == "simple_review" and state.simple_review_overburdened:
        failures.append("simple review was overburdened with irrelevant heavyweight challenge work")
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
        if "task family" in failure or "direct evidence" in failure or "uncheckable" in failure:
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
