"""FlowGuard model for FlowPilot command refinement.

Risk intent brief:
- Treat the original multi-command router loop as the baseline oracle before
  reintroducing any aggregate command.
- Only allow a production fold when it is behaviorally equivalent to the
  unfolded baseline and does not cross user, host, role, card-delivery, packet
  relay, or role-output boundaries.
- Model-critical state: startup next/apply/next order, wait-boundary return,
  candidate fold classification, runtime binding checks, and high-risk fold
  rejection.
- Hard invariants: accepted startup paths must apply `load_router` exactly once
  before returning `ask_startup_questions`; enabled folds must have binding and
  CLI smoke evidence; high-risk card, relay, startup fact-card, and role-output
  folds remain rejected until they get their own conformance replay.
- Blindspot: this model checks command-refinement policy, not concrete Python
  name binding. The package also needs static undefined-name checks and CLI
  smoke tests.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


STARTUP_UNFOLDED = "startup_unfolded"
STARTUP_SAFE_FOLD = "startup_safe_fold"
CARD_BUNDLE_FOLD = "card_bundle_fold"
PACKET_RELAY_FOLD = "packet_relay_fold"
STARTUP_FACT_CARD_FOLD = "startup_fact_card_fold"
ROLE_OUTPUT_PREFLIGHT_FOLD = "role_output_preflight_fold"

NEGATIVE_SCENARIOS = (
    CARD_BUNDLE_FOLD,
    PACKET_RELAY_FOLD,
    STARTUP_FACT_CARD_FOLD,
    ROLE_OUTPUT_PREFLIGHT_FOLD,
)

SCENARIOS = (
    STARTUP_UNFOLDED,
    STARTUP_SAFE_FOLD,
    *NEGATIVE_SCENARIOS,
)

EXPECTED_REJECTIONS = {
    CARD_BUNDLE_FOLD: "multi_card_delivery_requires_dedicated_replay",
    PACKET_RELAY_FOLD: "packet_relay_requires_dedicated_replay",
    STARTUP_FACT_CARD_FOLD: "startup_fact_card_crosses_reviewer_delivery_boundary",
    ROLE_OUTPUT_PREFLIGHT_FOLD: "role_output_preflight_requires_error_semantics_replay",
}


@dataclass(frozen=True)
class Tick:
    """One command-refinement tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    next_load_router_seen: bool = False
    load_router_applied: bool = False
    startup_questions_returned: bool = False
    user_boundary_crossed: bool = False
    host_boundary_crossed: bool = False
    role_boundary_crossed: bool = False
    folded_command_enabled: bool = False
    cli_binding_verified: bool = False
    runtime_smoke_verified: bool = False
    install_smoke_required: bool = True
    install_smoke_verified: bool = False
    high_risk_fold_rejected: bool = False
    router_decision: str = "none"
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class CommandRefinementStep:
    """Model one command refinement transition.

    Input x State -> Set(Output x State)
    reads: selected scenario, startup command order, binding evidence, boundary
    state
    writes: startup command progress, candidate acceptance/rejection, terminal
    decision
    idempotency: terminal decisions do not duplicate router actions
    """

    name = "CommandRefinementStep"
    reads = (
        "scenario",
        "startup_command_order",
        "binding_and_smoke_evidence",
        "boundary_state",
    )
    writes = (
        "startup_progress",
        "fold_candidate_decision",
        "router_terminal_decision",
    )
    input_description = "router command-refinement tick"
    output_description = "one abstract command-refinement step"
    idempotency = "terminal command-refinement decisions are not duplicated"

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


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(
                "router_selects_command_refinement_scenario",
                replace(state, status="running", scenario=scenario),
            )
        return

    if state.scenario == STARTUP_UNFOLDED:
        if not state.next_load_router_seen:
            yield Transition("unfolded_next_returns_load_router", replace(state, next_load_router_seen=True))
            return
        if not state.load_router_applied:
            yield Transition("unfolded_apply_records_load_router", replace(state, load_router_applied=True))
            return
        yield Transition(
            "unfolded_next_returns_startup_questions",
            replace(
                state,
                startup_questions_returned=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == STARTUP_SAFE_FOLD:
        if not state.cli_binding_verified:
            yield Transition("safe_fold_verifies_cli_binding", replace(state, cli_binding_verified=True))
            return
        if not state.runtime_smoke_verified:
            yield Transition("safe_fold_verifies_runtime_smoke", replace(state, runtime_smoke_verified=True))
            return
        if not state.install_smoke_verified:
            yield Transition("safe_fold_requires_install_smoke", replace(state, install_smoke_verified=True))
            return
        yield Transition(
            "safe_fold_applies_load_router_and_returns_startup_questions",
            replace(
                state,
                next_load_router_seen=True,
                load_router_applied=True,
                startup_questions_returned=True,
                folded_command_enabled=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario in EXPECTED_REJECTIONS:
        yield Transition(
            f"{state.scenario}_rejected_pending_dedicated_replay",
            replace(
                state,
                high_risk_fold_rejected=True,
                status="rejected",
                router_decision="reject",
                router_rejection_reason=EXPECTED_REJECTIONS[state.scenario],
            ),
        )
        return


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def accepted_startup_matches_unfolded_baseline(state: State, _trace) -> InvariantResult:
    if state.status == "accepted":
        if not state.load_router_applied:
            return InvariantResult.fail("accepted startup path did not apply load_router")
        if not state.startup_questions_returned:
            return InvariantResult.fail("accepted startup path did not return startup questions")
        if state.user_boundary_crossed or state.host_boundary_crossed or state.role_boundary_crossed:
            return InvariantResult.fail("accepted startup path crossed an external boundary")
    return InvariantResult.pass_()


def enabled_folds_require_binding_and_smoke(state: State, _trace) -> InvariantResult:
    if state.folded_command_enabled:
        if not state.cli_binding_verified:
            return InvariantResult.fail("enabled fold lacks CLI binding verification")
        if not state.runtime_smoke_verified:
            return InvariantResult.fail("enabled fold lacks runtime smoke verification")
        if state.install_smoke_required and not state.install_smoke_verified:
            return InvariantResult.fail("enabled fold lacks installed-skill smoke verification")
    return InvariantResult.pass_()


def only_safe_startup_fold_is_production_enabled(state: State, _trace) -> InvariantResult:
    if state.folded_command_enabled and state.scenario != STARTUP_SAFE_FOLD:
        return InvariantResult.fail(f"high-risk fold was production-enabled: {state.scenario}")
    return InvariantResult.pass_()


def high_risk_candidates_reject_without_replay(state: State, _trace) -> InvariantResult:
    if state.scenario in NEGATIVE_SCENARIOS and state.status == "accepted":
        return InvariantResult.fail(f"high-risk fold was accepted without dedicated replay: {state.scenario}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, _trace) -> InvariantResult:
    if state.status in {"accepted", "rejected"} and state.router_decision not in {"accept", "reject"}:
        return InvariantResult.fail("terminal state lacks explicit router decision")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_startup_matches_unfolded_baseline",
        description="Accepted startup paths apply load_router once and return startup questions without crossing boundaries.",
        predicate=accepted_startup_matches_unfolded_baseline,
    ),
    Invariant(
        name="enabled_folds_require_binding_and_smoke",
        description="Production folds require CLI, runtime, and installed-skill smoke evidence.",
        predicate=enabled_folds_require_binding_and_smoke,
    ),
    Invariant(
        name="only_safe_startup_fold_is_production_enabled",
        description="Only the startup internal load-router fold may be production enabled.",
        predicate=only_safe_startup_fold_is_production_enabled,
    ),
    Invariant(
        name="high_risk_candidates_reject_without_replay",
        description="High-risk fold candidates remain rejected until a dedicated replay model exists.",
        predicate=high_risk_candidates_reject_without_replay,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal model states record explicit accept/reject decisions.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 6
REQUIRED_LABELS = (
    "router_selects_command_refinement_scenario",
    "unfolded_next_returns_load_router",
    "unfolded_apply_records_load_router",
    "unfolded_next_returns_startup_questions",
    "safe_fold_verifies_cli_binding",
    "safe_fold_verifies_runtime_smoke",
    "safe_fold_requires_install_smoke",
    "safe_fold_applies_load_router_and_returns_startup_questions",
    "card_bundle_fold_rejected_pending_dedicated_replay",
    "packet_relay_fold_rejected_pending_dedicated_replay",
    "startup_fact_card_fold_rejected_pending_dedicated_replay",
    "role_output_preflight_fold_rejected_pending_dedicated_replay",
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((CommandRefinementStep(),), name="flowpilot_command_refinement")
