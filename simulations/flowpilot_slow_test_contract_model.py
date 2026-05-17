"""FlowGuard model for semantic parent/child slow-test contracts.

Risk Purpose Header:
This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to
review FlowPilot slow-test decomposition. It guards against turning a slow
end-to-end test into a "fast" parent test that still replays child setup,
reads child-owned internals, hides stale child evidence, or claims parent
confidence without a bound child input/output contract. Run or update it when
splitting slow pytest families into parent contract tests and child oracle
suites.

Companion command:
python simulations/run_flowpilot_slow_test_contract_checks.py --json-out simulations/flowpilot_slow_test_contract_results.json
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple, Sequence

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True, slots=True)
class State:
    scenario: str = "new"
    status: str = "new"  # new | selected | accepted | rejected
    test_family: str = "route_mutation"
    parent_layer_declared: bool = False
    child_contract_declared: bool = False
    child_owner_registered: bool = False
    duplicate_state_owner: bool = False
    input_contract_bound: bool = False
    output_contract_bound: bool = False
    child_evidence_current: bool = True
    hidden_child_skip: bool = False
    parent_replays_child_boot: bool = False
    parent_replays_packet_worker_flow: bool = False
    parent_reads_child_internal_state: bool = False
    parent_only_calls_parent_event: bool = True
    legal_route_action_state_provided: bool = True
    mutation_outputs_owned_by_parent: bool = True
    release_oracle_visible: bool = True
    release_scope: bool = False
    release_oracle_current: bool = False


@dataclass(frozen=True, slots=True)
class Tick:
    """One TestMesh parent/child contract decision."""


@dataclass(frozen=True, slots=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_parent(name: str) -> State:
    return State(
        scenario=name,
        status="selected",
        parent_layer_declared=True,
        child_contract_declared=True,
        child_owner_registered=True,
        input_contract_bound=True,
        output_contract_bound=True,
        child_evidence_current=True,
        parent_only_calls_parent_event=True,
        legal_route_action_state_provided=True,
        mutation_outputs_owned_by_parent=True,
    )


def _valid_release(name: str) -> State:
    return replace(
        _valid_parent(name),
        release_scope=True,
        release_oracle_current=True,
    )


SCENARIOS: dict[str, State] = {
    "valid_route_mutation_parent_contract": _valid_parent(
        "valid_route_mutation_parent_contract"
    ),
    "valid_release_with_child_oracle": _valid_release(
        "valid_release_with_child_oracle"
    ),
    "missing_child_contract": replace(
        _valid_parent("missing_child_contract"),
        child_contract_declared=False,
    ),
    "missing_child_owner": replace(
        _valid_parent("missing_child_owner"),
        child_owner_registered=False,
    ),
    "duplicate_state_owner": replace(
        _valid_parent("duplicate_state_owner"),
        duplicate_state_owner=True,
    ),
    "unbound_input_contract": replace(
        _valid_parent("unbound_input_contract"),
        input_contract_bound=False,
    ),
    "unbound_output_contract": replace(
        _valid_parent("unbound_output_contract"),
        output_contract_bound=False,
    ),
    "parent_replays_child_boot": replace(
        _valid_parent("parent_replays_child_boot"),
        parent_replays_child_boot=True,
        parent_only_calls_parent_event=False,
    ),
    "parent_replays_packet_worker_flow": replace(
        _valid_parent("parent_replays_packet_worker_flow"),
        parent_replays_packet_worker_flow=True,
        parent_only_calls_parent_event=False,
    ),
    "parent_reads_child_internal_state": replace(
        _valid_parent("parent_reads_child_internal_state"),
        parent_reads_child_internal_state=True,
    ),
    "missing_legal_route_action_state": replace(
        _valid_parent("missing_legal_route_action_state"),
        legal_route_action_state_provided=False,
    ),
    "parent_owns_no_mutation_outputs": replace(
        _valid_parent("parent_owns_no_mutation_outputs"),
        mutation_outputs_owned_by_parent=False,
    ),
    "stale_child_evidence": replace(
        _valid_parent("stale_child_evidence"),
        child_evidence_current=False,
    ),
    "hidden_child_skip": replace(
        _valid_parent("hidden_child_skip"),
        hidden_child_skip=True,
    ),
    "release_oracle_hidden": replace(
        _valid_parent("release_oracle_hidden"),
        release_scope=True,
        release_oracle_visible=False,
        release_oracle_current=False,
    ),
    "release_oracle_stale": replace(
        _valid_parent("release_oracle_stale"),
        release_scope=True,
        release_oracle_current=False,
    ),
}

VALID_SCENARIOS = {
    "valid_route_mutation_parent_contract",
    "valid_release_with_child_oracle",
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def contract_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.parent_layer_declared:
        failures.append("parent_layer_missing")
    if not state.child_contract_declared:
        failures.append("child_contract_missing")
    if not state.child_owner_registered:
        failures.append("child_owner_missing")
    if state.duplicate_state_owner:
        failures.append("duplicate_state_owner")
    if not state.input_contract_bound:
        failures.append("input_contract_unbound")
    if not state.output_contract_bound:
        failures.append("output_contract_unbound")
    if not state.child_evidence_current:
        failures.append("child_evidence_stale")
    if state.hidden_child_skip:
        failures.append("hidden_child_skip")
    if state.parent_replays_child_boot:
        failures.append("parent_replays_child_boot")
    if state.parent_replays_packet_worker_flow:
        failures.append("parent_replays_packet_worker_flow")
    if state.parent_reads_child_internal_state:
        failures.append("parent_reads_child_internal_state")
    if not state.parent_only_calls_parent_event:
        failures.append("parent_boundary_not_isolated")
    if not state.legal_route_action_state_provided:
        failures.append("legal_route_action_state_missing")
    if not state.mutation_outputs_owned_by_parent:
        failures.append("parent_mutation_output_owner_missing")
    if state.release_scope and not state.release_oracle_current:
        failures.append("release_child_oracle_not_current")
    if state.release_scope and not state.release_oracle_visible:
        failures.append("release_child_oracle_hidden")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        terminal = "rejected" if contract_failures(state) else "accepted"
        label = f"{terminal.removesuffix('ed')}_{state.scenario}"
        yield Transition(label, replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


class SlowTestContractStep:
    """Model one parent/child slow-test contract decision.

    Input x State -> Set(Output x State)
    reads: child test contract, freshness evidence, parent owned assertions
    writes: accepted or rejected parent confidence
    idempotency: pure classification keyed by test family and contract id
    """

    name = "SlowTestContractStep"
    input_description = "slow-test contract tick"
    output_description = "accepted or rejected parent contract confidence"
    reads = (
        "child_test_contract",
        "child_evidence_freshness",
        "parent_test_boundary",
        "route_action_contract",
    )
    writes = ("parent_contract_confidence", "visible_release_oracle_obligation")
    idempotency = "pure classification of parent/child test contract evidence"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: Sequence[object]) -> InvariantResult:
    if state.status == "accepted":
        failures = contract_failures(state)
        if failures:
            return InvariantResult.fail(f"accepted unsafe slow-test contract: {failures}")
    if state.status == "rejected" and not contract_failures(state):
        return InvariantResult.fail("rejected a valid slow-test contract")
    return InvariantResult.pass_()


def parent_does_not_replay_child_flow(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if state.status == "accepted" and (
        state.parent_replays_child_boot or state.parent_replays_packet_worker_flow
    ):
        return InvariantResult.fail("accepted parent test that replays child flow")
    return InvariantResult.pass_()


def parent_consumes_bound_io_contract(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if state.status == "accepted" and (
        not state.input_contract_bound or not state.output_contract_bound
    ):
        return InvariantResult.fail("accepted parent test without bound child I/O")
    return InvariantResult.pass_()


def release_scope_requires_current_child_oracle(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if state.status == "accepted" and state.release_scope and not state.release_oracle_current:
        return InvariantResult.fail("accepted release scope without current child oracle")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted slow-test contracts cannot contain known TestMesh hazards.",
        accepted_states_are_safe,
    ),
    Invariant(
        "parent_does_not_replay_child_flow",
        "Parent contract tests cannot replay boot/current-node packet worker flow.",
        parent_does_not_replay_child_flow,
    ),
    Invariant(
        "parent_consumes_bound_io_contract",
        "Parent tests must consume a bound child input/output contract.",
        parent_consumes_bound_io_contract,
    ),
    Invariant(
        "release_scope_requires_current_child_oracle",
        "Release scope requires current child oracle evidence.",
        release_scope_requires_current_child_oracle,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


def build_workflow() -> Workflow:
    return Workflow((SlowTestContractStep(),), name="flowpilot_slow_test_contract")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {
        name: contract_failures(SCENARIOS[name])
        for name in sorted(NEGATIVE_SCENARIOS)
    }
