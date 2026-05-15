"""FlowGuard model for FlowPilot current-scope pre-review reconciliation.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot rule that reviewer work starts only after local startup/current-node
  obligations are reconciled.
- Guards against reviewer passes over moving local state, local reconciliation
  clearing future/sibling work, deferred local obligations without explicit
  carry-forward, review-created obligations crossing node boundaries, and
  no-review scopes transitioning before local reconciliation.
- Update and run this model whenever Router review-start, current-node
  completion, startup review, pending-return, or node-scope obligation logic
  changes.
- Companion check command:
  `python simulations/run_flowpilot_current_scope_pre_review_reconciliation_checks.py`.

Risk intent brief:
- Protected harm: Reviewer gates become meaningless when they judge a package
  that can still change because hidden current-scope work is pending.
- Model-critical state: active scope identity, local pending obligations, future
  pending obligations, explicit carry-forward, reviewer start/pass, review
  created follow-up obligations, no-final-review transition, and scope exit.
- Adversarial branches: review starts before local join, local join clears
  future obligations, carry-forward lacks target/reason, scope exits before
  review-created obligations close, no-review scope exits before reconciliation,
  and ACK/read receipt is treated as semantic completion.
- Hard invariants: reconciliation is local to the active scope; reviewer work
  waits for local reconciliation; carried-forward local items have explicit
  metadata; review-created obligations close before scope exit; no-review
  scopes reconcile before transition; ACK does not imply semantic work done.
- Blindspot: this is a focused control-plane model. Runtime tests must still
  exercise concrete Router actions, ledgers, cards, and install sync.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


STARTUP_CLEAN_REVIEW = "startup_clean_review"
NODE_CLEAN_REVIEW = "node_clean_review"
FUTURE_OBLIGATION_IGNORED_LOCALLY = "future_obligation_ignored_locally"
LOCAL_CARRY_FORWARD_EXPLICIT = "local_carry_forward_explicit"
REVIEW_CREATED_OBLIGATION_CLOSED = "review_created_obligation_closed"
NO_REVIEW_SCOPE_CLEAN_TRANSITION = "no_review_scope_clean_transition"

REVIEW_STARTED_BEFORE_LOCAL_RECONCILIATION = "review_started_before_local_reconciliation"
LOCAL_RECONCILIATION_CLEARS_FUTURE_SCOPE = "local_reconciliation_clears_future_scope"
LOCAL_DEFERRED_WITHOUT_CARRY_FORWARD = "local_deferred_without_carry_forward"
SCOPE_EXIT_BEFORE_REVIEW_CREATED_CLOSURE = "scope_exit_before_review_created_closure"
NO_REVIEW_SCOPE_EXIT_WITHOUT_RECONCILIATION = "no_review_scope_exit_without_reconciliation"
ACK_USED_AS_SEMANTIC_COMPLETION = "ack_used_as_semantic_completion"

VALID_SCENARIOS = (
    STARTUP_CLEAN_REVIEW,
    NODE_CLEAN_REVIEW,
    FUTURE_OBLIGATION_IGNORED_LOCALLY,
    LOCAL_CARRY_FORWARD_EXPLICIT,
    REVIEW_CREATED_OBLIGATION_CLOSED,
    NO_REVIEW_SCOPE_CLEAN_TRANSITION,
)

NEGATIVE_SCENARIOS = (
    REVIEW_STARTED_BEFORE_LOCAL_RECONCILIATION,
    LOCAL_RECONCILIATION_CLEARS_FUTURE_SCOPE,
    LOCAL_DEFERRED_WITHOUT_CARRY_FORWARD,
    SCOPE_EXIT_BEFORE_REVIEW_CREATED_CLOSURE,
    NO_REVIEW_SCOPE_EXIT_WITHOUT_RECONCILIATION,
    ACK_USED_AS_SEMANTIC_COMPLETION,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract reconciliation transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    active_scope: str = "none"  # none | startup | node
    has_final_review: bool = True

    local_obligation_pending: bool = False
    local_reconciliation_checked: bool = False
    local_reconciliation_clean: bool = False
    local_obligation_carried_forward: bool = False
    carry_forward_target_scope: bool = False
    carry_forward_reason_recorded: bool = False

    future_obligation_pending: bool = False
    future_obligation_cleared_by_local_reconciliation: bool = False

    reviewer_work_started: bool = False
    reviewer_passed: bool = False
    review_created_obligation_pending: bool = False
    review_created_obligation_closed: bool = False
    scope_exited: bool = False

    ack_returned: bool = False
    semantic_work_completed: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="accepted", terminal_reason="valid", **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="rejected", terminal_reason="invalid", **changes)


def scenario_state(scenario: str) -> State:
    if scenario == STARTUP_CLEAN_REVIEW:
        return _accepted(
            scenario,
            active_scope="startup",
            local_obligation_pending=False,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_closed=True,
            scope_exited=True,
            ack_returned=True,
            semantic_work_completed=True,
        )
    if scenario == NODE_CLEAN_REVIEW:
        return _accepted(
            scenario,
            active_scope="node",
            local_obligation_pending=False,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_closed=True,
            scope_exited=True,
            ack_returned=True,
            semantic_work_completed=True,
        )
    if scenario == FUTURE_OBLIGATION_IGNORED_LOCALLY:
        return _accepted(
            scenario,
            active_scope="node",
            future_obligation_pending=True,
            future_obligation_cleared_by_local_reconciliation=False,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_closed=True,
        )
    if scenario == LOCAL_CARRY_FORWARD_EXPLICIT:
        return _accepted(
            scenario,
            active_scope="node",
            local_obligation_pending=True,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            local_obligation_carried_forward=True,
            carry_forward_target_scope=True,
            carry_forward_reason_recorded=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_closed=True,
        )
    if scenario == REVIEW_CREATED_OBLIGATION_CLOSED:
        return _accepted(
            scenario,
            active_scope="node",
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_pending=False,
            review_created_obligation_closed=True,
            scope_exited=True,
            semantic_work_completed=True,
        )
    if scenario == NO_REVIEW_SCOPE_CLEAN_TRANSITION:
        return _accepted(
            scenario,
            active_scope="node",
            has_final_review=False,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=False,
            scope_exited=True,
            semantic_work_completed=True,
        )
    if scenario == REVIEW_STARTED_BEFORE_LOCAL_RECONCILIATION:
        return _rejected(
            scenario,
            active_scope="node",
            local_obligation_pending=True,
            local_reconciliation_checked=False,
            reviewer_work_started=True,
        )
    if scenario == LOCAL_RECONCILIATION_CLEARS_FUTURE_SCOPE:
        return _rejected(
            scenario,
            active_scope="node",
            future_obligation_pending=True,
            future_obligation_cleared_by_local_reconciliation=True,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
        )
    if scenario == LOCAL_DEFERRED_WITHOUT_CARRY_FORWARD:
        return _rejected(
            scenario,
            active_scope="node",
            local_obligation_pending=True,
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            local_obligation_carried_forward=True,
            carry_forward_target_scope=False,
            carry_forward_reason_recorded=False,
            reviewer_work_started=True,
        )
    if scenario == SCOPE_EXIT_BEFORE_REVIEW_CREATED_CLOSURE:
        return _rejected(
            scenario,
            active_scope="node",
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            reviewer_work_started=True,
            reviewer_passed=True,
            review_created_obligation_pending=True,
            review_created_obligation_closed=False,
            scope_exited=True,
        )
    if scenario == NO_REVIEW_SCOPE_EXIT_WITHOUT_RECONCILIATION:
        return _rejected(
            scenario,
            active_scope="node",
            has_final_review=False,
            local_obligation_pending=True,
            local_reconciliation_checked=False,
            local_reconciliation_clean=False,
            scope_exited=True,
        )
    if scenario == ACK_USED_AS_SEMANTIC_COMPLETION:
        return _rejected(
            scenario,
            active_scope="node",
            local_reconciliation_checked=True,
            local_reconciliation_clean=True,
            ack_returned=True,
            semantic_work_completed=False,
            reviewer_work_started=True,
            reviewer_passed=True,
            scope_exited=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), status="new", scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = current_scope_reconciliation_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected", terminal_reason=failures[0] if failures else "negative scenario rejected"),
        )


class CurrentScopeReconciliationStep:
    """Model one current-scope reconciliation transition.

    Input x State -> Set(Output x State)
    reads: active scope, local pending obligations, future pending obligations,
    review-created obligations, ACK/read-receipt state, and completion state
    writes: local reconciliation summary, reviewer-start permission,
    carry-forward metadata, and scope-exit permission
    idempotency: reconciliation is scope-id keyed and monotonic for a stable
    review package
    """

    name = "CurrentScopeReconciliationStep"
    input_description = "current-scope reconciliation tick"
    output_description = "one reconciliation state transition"
    reads = (
        "active_scope",
        "local_obligations",
        "future_obligations",
        "review_created_obligations",
        "ack_receipts",
        "semantic_completion",
    )
    writes = (
        "local_reconciliation_summary",
        "review_start_permission",
        "carry_forward_record",
        "scope_exit_permission",
    )
    idempotency = "scope_id-keyed reconciliation summaries are monotonic for a stable package"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def current_scope_reconciliation_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.reviewer_work_started and not (
        state.local_reconciliation_checked and state.local_reconciliation_clean
    ):
        failures.append("reviewer work started before current-scope reconciliation was clean")
    if state.future_obligation_cleared_by_local_reconciliation:
        failures.append("local reconciliation cleared a future or sibling scope obligation")
    if state.local_obligation_carried_forward and not (
        state.carry_forward_target_scope and state.carry_forward_reason_recorded
    ):
        failures.append("local obligation was carried forward without target scope and reason")
    if state.scope_exited and state.review_created_obligation_pending and not state.review_created_obligation_closed:
        failures.append("scope exited before review-created obligations closed")
    if not state.has_final_review and state.scope_exited and not (
        state.local_reconciliation_checked and state.local_reconciliation_clean
    ):
        failures.append("no-final-review scope exited before local reconciliation")
    if state.ack_returned and state.reviewer_passed and state.scope_exited and not state.semantic_work_completed:
        failures.append("ACK/read receipt was treated as semantic work completion")
    return failures


def accepts_only_reconciled_current_scope_reviews(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = current_scope_reconciliation_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow(
        (CurrentScopeReconciliationStep(),),
        name="flowpilot_current_scope_pre_review_reconciliation",
    )


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="current_scope_pre_review_reconciliation",
        description="Reviewer work and scope exit require clean local reconciliation without touching future scopes.",
        predicate=accepts_only_reconciled_current_scope_reviews,
    ),
)


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
