"""FlowGuard model for FlowPilot route hard gates.

Risk intent brief:
- Validate the hard-gate version of the product-model-first route workflow
  before Router or card changes.
- Protected harms: PM route drafting before Product Officer modeling, route
  activation without product-model review, route activation without Process
  Officer viability, PM ignoring repair_required or blocked verdicts, repair
  nodes that cannot return to the mainline, repair routes that continue without
  fresh Process Officer checks, and Router overreaching into semantic route
  judgment.
- Modeled state and side effects: product behavior model report, PM route
  draft, route-product review pass, process viability verdict, PM response to
  non-pass verdicts, route activation, route mutation, repair return target,
  and post-mutation route recheck.
- Hard invariants: Router gates require role-owned pass reports and verdicts;
  Router must not judge whether the route semantically covers the product
  model; stale route approvals cannot survive repair mutation.
- Blindspot: this model checks the abstract control contract. Runtime tests
  must still prove the concrete Router code and cards enforce the same gates.

Optimization checklist:
1. Product Officer produces the product behavior model before PM route drafting.
2. PM route gets role-owned product-model review before activation.
3. Process Officer gives a route viability verdict before activation.
4. PM cannot continue normally after repair_required or blocked.
5. Repair mutation needs a mainline return target.
6. Repair mutation clears old route approvals and requires fresh route checks.

Risk checklist:
1. Missing product behavior model.
2. Missing product-model review pass.
3. Missing Process Officer process verdict.
4. Ignored repair_required verdict.
5. Ignored blocked verdict.
6. Repair node has no mainline return.
7. Repair route has no fresh process recheck.
8. Router tries to do semantic route judgment itself.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_INITIAL_ROUTE = "valid_initial_route"
VALID_REPAIR_ROUTE = "valid_repair_route"

MISSING_PRODUCT_MODEL = "missing_product_model"
MISSING_ROUTE_MODEL_REVIEW = "missing_route_model_review"
MISSING_PROCESS_VERDICT = "missing_process_verdict"
REPAIR_REQUIRED_IGNORED = "repair_required_ignored"
BLOCKED_IGNORED = "blocked_ignored"
REPAIR_MISSING_MAINLINE_RETURN = "repair_missing_mainline_return"
REPAIR_WITHOUT_PROCESS_RECHECK = "repair_without_process_recheck"
ROUTER_SEMANTIC_OVERREACH = "router_semantic_overreach"

VALID_SCENARIOS = (VALID_INITIAL_ROUTE, VALID_REPAIR_ROUTE)
NEGATIVE_SCENARIOS = (
    MISSING_PRODUCT_MODEL,
    MISSING_ROUTE_MODEL_REVIEW,
    MISSING_PROCESS_VERDICT,
    REPAIR_REQUIRED_IGNORED,
    BLOCKED_IGNORED,
    REPAIR_MISSING_MAINLINE_RETURN,
    REPAIR_WITHOUT_PROCESS_RECHECK,
    ROUTER_SEMANTIC_OVERREACH,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract route-hard-gate evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    product_model_report_exists: bool = False
    route_draft_written: bool = False
    route_product_review_verdict: str = "missing"  # missing | pass | repair_required | blocked
    process_viability_verdict: str = "missing"  # missing | pass | repair_required | blocked
    pm_response_to_process_verdict: str = "unset"  # unset | continue | repair | stop_or_human
    route_activated: bool = False
    repair_node_created: bool = False
    repair_return_to_mainline_defined: bool = False
    fresh_process_recheck_after_repair: bool = False
    stale_route_approvals_cleared_after_repair: bool = False
    router_attempts_semantic_route_judgment: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RouteHardGateStep:
    """Model one FlowPilot route hard-gate transition.

    Input x State -> Set(Output x State)
    reads: product model report, route draft, role review verdicts, repair
    mutation state, and Router decision boundary
    writes: accepted or rejected route-hard-gate decision
    idempotency: scenario facts are monotonic; terminal decisions do not change
    on retry.
    """

    name = "RouteHardGateStep"
    input_description = "FlowPilot route-hard-gate tick"
    output_description = "one route-hard-gate transition"
    reads = (
        "product_model_report",
        "route_draft",
        "route_product_review_verdict",
        "process_viability_verdict",
        "repair_mutation",
        "router_boundary",
    )
    writes = ("scenario_facts", "terminal_route_gate_decision")
    idempotency = "monotonic route-hard-gate facts"

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


def _valid_initial_route() -> State:
    return State(
        status="running",
        scenario=VALID_INITIAL_ROUTE,
        product_model_report_exists=True,
        route_draft_written=True,
        route_product_review_verdict="pass",
        process_viability_verdict="pass",
        pm_response_to_process_verdict="continue",
        route_activated=True,
    )


def _valid_repair_route() -> State:
    return State(
        status="running",
        scenario=VALID_REPAIR_ROUTE,
        product_model_report_exists=True,
        route_draft_written=True,
        route_product_review_verdict="pass",
        process_viability_verdict="pass",
        pm_response_to_process_verdict="repair",
        route_activated=True,
        repair_node_created=True,
        repair_return_to_mainline_defined=True,
        fresh_process_recheck_after_repair=True,
        stale_route_approvals_cleared_after_repair=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_INITIAL_ROUTE:
        return _valid_initial_route()
    if scenario == VALID_REPAIR_ROUTE:
        return _valid_repair_route()

    state = _valid_initial_route()
    state = replace(state, scenario=scenario)
    if scenario == MISSING_PRODUCT_MODEL:
        return replace(state, product_model_report_exists=False)
    if scenario == MISSING_ROUTE_MODEL_REVIEW:
        return replace(state, route_product_review_verdict="missing")
    if scenario == MISSING_PROCESS_VERDICT:
        return replace(state, process_viability_verdict="missing")
    if scenario == REPAIR_REQUIRED_IGNORED:
        return replace(state, process_viability_verdict="repair_required", pm_response_to_process_verdict="continue")
    if scenario == BLOCKED_IGNORED:
        return replace(state, process_viability_verdict="blocked", pm_response_to_process_verdict="continue")
    if scenario == REPAIR_MISSING_MAINLINE_RETURN:
        return replace(
            _valid_repair_route(),
            scenario=scenario,
            repair_return_to_mainline_defined=False,
        )
    if scenario == REPAIR_WITHOUT_PROCESS_RECHECK:
        return replace(
            _valid_repair_route(),
            scenario=scenario,
            fresh_process_recheck_after_repair=False,
            stale_route_approvals_cleared_after_repair=False,
        )
    if scenario == ROUTER_SEMANTIC_OVERREACH:
        return replace(state, router_attempts_semantic_route_judgment=True)
    return state


def route_gate_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.route_draft_written and not state.product_model_report_exists:
        failures.append("PM route draft requires Product Officer product behavior model report")
    if state.route_activated and state.route_product_review_verdict != "pass":
        failures.append("route activation requires passed product-model route review")
    if state.route_activated and state.process_viability_verdict != "pass":
        failures.append("route activation requires Process Officer process_viability_verdict=pass")
    if state.process_viability_verdict == "repair_required" and state.pm_response_to_process_verdict == "continue":
        failures.append("PM cannot continue normally after process verdict repair_required")
    if state.process_viability_verdict == "blocked" and state.pm_response_to_process_verdict == "continue":
        failures.append("PM cannot continue normally after process verdict blocked")
    if state.repair_node_created and not state.repair_return_to_mainline_defined:
        failures.append("repair mutation requires a mainline return target")
    if state.repair_node_created and not state.fresh_process_recheck_after_repair:
        failures.append("repair route requires fresh Process Officer recheck before continuing")
    if state.repair_node_created and not state.stale_route_approvals_cleared_after_repair:
        failures.append("repair mutation must clear stale route approvals before continuing")
    if state.router_attempts_semantic_route_judgment:
        failures.append("Router must not judge semantic product-model coverage itself")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = route_gate_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="route_hard_gate_contract_ok"),
        )


def accepts_only_valid_hard_gate_flows(state: State, trace) -> InvariantResult:
    del trace
    failures = route_gate_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid hard-gate route flow was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid hard-gate route flow was rejected")
    return InvariantResult.pass_()


def product_model_precedes_route_activation(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.route_activated and not state.product_model_report_exists:
        return InvariantResult.fail("route activated without Product Officer product model")
    return InvariantResult.pass_()


def route_activation_requires_role_passes(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or not state.route_activated:
        return InvariantResult.pass_()
    if state.route_product_review_verdict != "pass":
        return InvariantResult.fail("route activated without product-model review pass")
    if state.process_viability_verdict != "pass":
        return InvariantResult.fail("route activated without process viability pass")
    return InvariantResult.pass_()


def repairs_return_and_recheck(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or not state.repair_node_created:
        return InvariantResult.pass_()
    if not state.repair_return_to_mainline_defined:
        return InvariantResult.fail("accepted repair route has no mainline return")
    if not state.fresh_process_recheck_after_repair:
        return InvariantResult.fail("accepted repair route has no fresh process recheck")
    if not state.stale_route_approvals_cleared_after_repair:
        return InvariantResult.fail("accepted repair route reused stale route approvals")
    return InvariantResult.pass_()


def router_stays_mechanical(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.router_attempts_semantic_route_judgment:
        return InvariantResult.fail("Router accepted semantic overreach")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_hard_gate_flows",
        description="Only route flows with required role-owned hard gates can be accepted.",
        predicate=accepts_only_valid_hard_gate_flows,
    ),
    Invariant(
        name="product_model_precedes_route_activation",
        description="Product Officer product behavior model must precede route activation.",
        predicate=product_model_precedes_route_activation,
    ),
    Invariant(
        name="route_activation_requires_role_passes",
        description="Route activation requires product-model review pass and process viability pass.",
        predicate=route_activation_requires_role_passes,
    ),
    Invariant(
        name="repairs_return_and_recheck",
        description="Repair routes must return to mainline and receive fresh process recheck.",
        predicate=repairs_return_and_recheck,
    ),
    Invariant(
        name="router_stays_mechanical",
        description="Router enforces pass artifacts but does not judge semantic route coverage itself.",
        predicate=router_stays_mechanical,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((RouteHardGateStep(),), name="flowpilot_route_hard_gate")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not route_gate_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
