"""FlowGuard model for FlowPilot control transaction registry safety.

Risk intent brief:
- Promote FlowPilot control movement from separate table checks into one
  registered transaction authority.
- Protected harms: route or packet state moving from only contract validity,
  only event validity, unchecked packet authority, collapsed repair outcomes,
  parent repair leaf-event reuse, partial state commits, and old invalid repair
  transactions being treated as current permission.
- Hard invariant: a FlowPilot control write is safe only when the transaction
  type is registered and its referenced contract, event capability, packet
  authority, repair transaction, outcome policy, and commit targets agree.
- Blindspot: this model validates the transaction architecture. Runtime tests
  and source checks must still prove concrete Router functions and JSON
  registry rows use the same rules.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_ROUTE_PROGRESSION = "valid_route_progression"
VALID_PACKET_DISPATCH = "valid_packet_dispatch"
VALID_RESULT_ABSORPTION = "valid_result_absorption"
VALID_REVIEWER_GATE_RESULT = "valid_reviewer_gate_result"
VALID_CONTROL_BLOCKER_REPAIR = "valid_control_blocker_repair"
VALID_CONTROL_PLANE_REISSUE = "valid_control_plane_reissue"
VALID_ROUTE_MUTATION = "valid_route_mutation"
VALID_LEGACY_QUARANTINE = "valid_legacy_quarantine"

UNREGISTERED_TRANSACTION_TYPE = "unregistered_transaction_type"
CONTRACT_PASS_EVENT_CAPABILITY_MISSING = "contract_pass_event_capability_missing"
EVENT_PASS_CONTRACT_MISSING = "event_pass_contract_missing"
PACKET_AUTHORITY_MISSING = "packet_authority_missing"
COMPLETED_AGENT_INVALID = "completed_agent_invalid"
COLLAPSED_REPAIR_OUTCOMES = "collapsed_repair_outcomes"
REPAIR_WITHOUT_TRANSACTION = "repair_without_transaction"
PARENT_REPAIR_LEAF_EVENT = "parent_repair_leaf_event"
PARTIAL_COMMIT_TARGETS = "partial_commit_targets"
ACTIVE_BLOCKER_MARKED_GREEN = "active_blocker_marked_green"
LEGACY_BAD_TRANSACTION_CONTINUES = "legacy_bad_transaction_continues"
REGISTRY_REFERENCE_MISSING = "registry_reference_missing"
ROUTE_MUTATION_WITHOUT_STALE_POLICY = "route_mutation_without_stale_policy"
REVIEWER_NON_SUCCESS_USES_SUCCESS_EVENT = "reviewer_non_success_uses_success_event"
ATOMIC_COMMIT_TARGET_MISSING = "atomic_commit_target_missing"
CONTROL_PLANE_REISSUE_WITHOUT_DELIVERY_AUTHORITY = "control_plane_reissue_without_delivery_authority"

VALID_SCENARIOS = (
    VALID_ROUTE_PROGRESSION,
    VALID_PACKET_DISPATCH,
    VALID_RESULT_ABSORPTION,
    VALID_REVIEWER_GATE_RESULT,
    VALID_CONTROL_BLOCKER_REPAIR,
    VALID_CONTROL_PLANE_REISSUE,
    VALID_ROUTE_MUTATION,
    VALID_LEGACY_QUARANTINE,
)
NEGATIVE_SCENARIOS = (
    UNREGISTERED_TRANSACTION_TYPE,
    CONTRACT_PASS_EVENT_CAPABILITY_MISSING,
    EVENT_PASS_CONTRACT_MISSING,
    PACKET_AUTHORITY_MISSING,
    COMPLETED_AGENT_INVALID,
    COLLAPSED_REPAIR_OUTCOMES,
    REPAIR_WITHOUT_TRANSACTION,
    PARENT_REPAIR_LEAF_EVENT,
    PARTIAL_COMMIT_TARGETS,
    ACTIVE_BLOCKER_MARKED_GREEN,
    LEGACY_BAD_TRANSACTION_CONTINUES,
    REGISTRY_REFERENCE_MISSING,
    ROUTE_MUTATION_WITHOUT_STALE_POLICY,
    REVIEWER_NON_SUCCESS_USES_SUCCESS_EVENT,
    ATOMIC_COMMIT_TARGET_MISSING,
    CONTROL_PLANE_REISSUE_WITHOUT_DELIVERY_AUTHORITY,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

REGISTERED_TRANSACTION_TYPES = {
    "route_progression",
    "packet_dispatch",
    "result_absorption",
    "reviewer_gate_result",
    "control_blocker_repair",
    "control_plane_reissue",
    "route_mutation",
    "legacy_reconcile",
}
COMMIT_TARGETS = {
    "frontier",
    "run_state",
    "status_summary",
    "packet_ledger",
    "blocker_index",
    "repair_transaction",
    "route",
    "stale_evidence",
    "repair_transaction_index",
}
REQUIRED_TARGETS_BY_TYPE = {
    "route_progression": frozenset({"frontier", "run_state", "status_summary"}),
    "packet_dispatch": frozenset({"packet_ledger", "run_state", "status_summary"}),
    "result_absorption": frozenset({"packet_ledger", "run_state", "status_summary"}),
    "reviewer_gate_result": frozenset({"run_state", "blocker_index", "status_summary"}),
    "control_blocker_repair": frozenset({"repair_transaction", "blocker_index", "run_state", "status_summary"}),
    "control_plane_reissue": frozenset({"blocker_index", "run_state", "status_summary"}),
    "route_mutation": frozenset({"route", "frontier", "stale_evidence", "run_state", "status_summary"}),
    "legacy_reconcile": frozenset({"blocker_index", "repair_transaction_index", "status_summary"}),
}


@dataclass(frozen=True)
class Tick:
    """One control transaction registry evaluation."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | selected | accepted | rejected
    scenario: str = "unset"
    transaction_type: str = "none"
    registry_row_present: bool = False
    registry_references_exist: bool = True
    contract_required: bool = True
    contract_binding_ok: bool = True
    event_capability_required: bool = True
    event_capability_ok: bool = True
    packet_authority_required: bool = False
    role_origin_checked: bool = True
    completed_agent_id_belongs_to_role: bool = True
    completed_agent_id_is_role_key: bool = False
    repair_transaction_required: bool = False
    repair_transaction_present: bool = True
    outcome_policy: str = "none"  # none | single_event | three_distinct_outcomes
    outcome_events_distinct: bool = True
    non_success_uses_success_event: bool = False
    parent_repair: bool = False
    repair_target_is_leaf_event: bool = False
    commit_targets: tuple[str, ...] = ()
    atomic_commit_declared: bool = True
    active_blocker_present: bool = False
    safe_to_continue_claimed: bool = False
    legacy_transaction: bool = False
    legacy_transaction_invalid: bool = False
    legacy_quarantined: bool = False
    route_mutation: bool = False
    stale_evidence_policy_applied: bool = False
    control_plane_reissue: bool = False
    reissue_delivery_authority_present: bool = False
    original_event_flag_currently_set: bool = True
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_ROUTE_PROGRESSION:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="route_progression",
            registry_row_present=True,
            commit_targets=("frontier", "run_state", "status_summary"),
        )
    if scenario == VALID_PACKET_DISPATCH:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="packet_dispatch",
            registry_row_present=True,
            commit_targets=("packet_ledger", "run_state", "status_summary"),
        )
    if scenario == VALID_RESULT_ABSORPTION:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="result_absorption",
            registry_row_present=True,
            packet_authority_required=True,
            commit_targets=("packet_ledger", "run_state", "status_summary"),
        )
    if scenario == VALID_REVIEWER_GATE_RESULT:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="reviewer_gate_result",
            registry_row_present=True,
            outcome_policy="single_event",
            commit_targets=("run_state", "blocker_index", "status_summary"),
        )
    if scenario == VALID_CONTROL_BLOCKER_REPAIR:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="control_blocker_repair",
            registry_row_present=True,
            repair_transaction_required=True,
            outcome_policy="three_distinct_outcomes",
            commit_targets=("repair_transaction", "blocker_index", "run_state", "status_summary"),
        )
    if scenario == VALID_CONTROL_PLANE_REISSUE:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="control_plane_reissue",
            registry_row_present=True,
            contract_required=False,
            event_capability_ok=False,
            commit_targets=("blocker_index", "run_state", "status_summary"),
            control_plane_reissue=True,
            reissue_delivery_authority_present=True,
            original_event_flag_currently_set=False,
        )
    if scenario == VALID_ROUTE_MUTATION:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="route_mutation",
            registry_row_present=True,
            route_mutation=True,
            stale_evidence_policy_applied=True,
            commit_targets=("route", "frontier", "stale_evidence", "run_state", "status_summary"),
        )
    if scenario == VALID_LEGACY_QUARANTINE:
        return State(
            status="selected",
            scenario=scenario,
            transaction_type="legacy_reconcile",
            registry_row_present=True,
            contract_required=False,
            legacy_transaction=True,
            legacy_transaction_invalid=True,
            legacy_quarantined=True,
            active_blocker_present=True,
            commit_targets=("blocker_index", "repair_transaction_index", "status_summary"),
        )
    if scenario == UNREGISTERED_TRANSACTION_TYPE:
        return replace(_scenario_state(VALID_ROUTE_PROGRESSION), scenario=scenario, transaction_type="ad_hoc_next_step")
    if scenario == CONTRACT_PASS_EVENT_CAPABILITY_MISSING:
        return replace(_scenario_state(VALID_ROUTE_PROGRESSION), scenario=scenario, event_capability_ok=False)
    if scenario == EVENT_PASS_CONTRACT_MISSING:
        return replace(_scenario_state(VALID_ROUTE_PROGRESSION), scenario=scenario, contract_binding_ok=False)
    if scenario == PACKET_AUTHORITY_MISSING:
        return replace(_scenario_state(VALID_RESULT_ABSORPTION), scenario=scenario, role_origin_checked=False)
    if scenario == COMPLETED_AGENT_INVALID:
        return replace(
            _scenario_state(VALID_RESULT_ABSORPTION),
            scenario=scenario,
            completed_agent_id_belongs_to_role=False,
            completed_agent_id_is_role_key=True,
        )
    if scenario == COLLAPSED_REPAIR_OUTCOMES:
        return replace(_scenario_state(VALID_CONTROL_BLOCKER_REPAIR), scenario=scenario, outcome_events_distinct=False)
    if scenario == REPAIR_WITHOUT_TRANSACTION:
        return replace(_scenario_state(VALID_CONTROL_BLOCKER_REPAIR), scenario=scenario, repair_transaction_present=False)
    if scenario == PARENT_REPAIR_LEAF_EVENT:
        return replace(
            _scenario_state(VALID_CONTROL_BLOCKER_REPAIR),
            scenario=scenario,
            parent_repair=True,
            repair_target_is_leaf_event=True,
        )
    if scenario == PARTIAL_COMMIT_TARGETS:
        return replace(_scenario_state(VALID_CONTROL_BLOCKER_REPAIR), scenario=scenario, commit_targets=("run_state",))
    if scenario == ACTIVE_BLOCKER_MARKED_GREEN:
        return replace(
            _scenario_state(VALID_ROUTE_PROGRESSION),
            scenario=scenario,
            active_blocker_present=True,
            safe_to_continue_claimed=True,
        )
    if scenario == LEGACY_BAD_TRANSACTION_CONTINUES:
        return replace(
            _scenario_state(VALID_LEGACY_QUARANTINE),
            scenario=scenario,
            legacy_quarantined=False,
            safe_to_continue_claimed=True,
        )
    if scenario == REGISTRY_REFERENCE_MISSING:
        return replace(_scenario_state(VALID_PACKET_DISPATCH), scenario=scenario, registry_references_exist=False)
    if scenario == ROUTE_MUTATION_WITHOUT_STALE_POLICY:
        return replace(_scenario_state(VALID_ROUTE_MUTATION), scenario=scenario, stale_evidence_policy_applied=False)
    if scenario == REVIEWER_NON_SUCCESS_USES_SUCCESS_EVENT:
        return replace(
            _scenario_state(VALID_REVIEWER_GATE_RESULT),
            scenario=scenario,
            outcome_policy="three_distinct_outcomes",
            non_success_uses_success_event=True,
        )
    if scenario == ATOMIC_COMMIT_TARGET_MISSING:
        return replace(_scenario_state(VALID_RESULT_ABSORPTION), scenario=scenario, atomic_commit_declared=True, commit_targets=("run_state", "status_summary"))
    if scenario == CONTROL_PLANE_REISSUE_WITHOUT_DELIVERY_AUTHORITY:
        return replace(
            _scenario_state(VALID_CONTROL_PLANE_REISSUE),
            scenario=scenario,
            reissue_delivery_authority_present=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def control_transaction_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.transaction_type not in REGISTERED_TRANSACTION_TYPES or not state.registry_row_present:
        failures.append("transaction type is not registered")
    if not state.registry_references_exist:
        failures.append("control transaction registry references missing contract or event")
    if state.contract_required and not state.contract_binding_ok:
        failures.append("contract binding is missing or mismatched")
    reissue_flag_override = (
        state.control_plane_reissue
        and state.reissue_delivery_authority_present
        and not state.original_event_flag_currently_set
    )
    if state.event_capability_required and not state.event_capability_ok and not reissue_flag_override:
        failures.append("event capability was not validated or failed")
    if state.control_plane_reissue and not state.reissue_delivery_authority_present:
        failures.append("control-plane reissue lacks delivery authority")
    if state.packet_authority_required:
        if not state.role_origin_checked:
            failures.append("packet authority role origin was not checked")
        if not state.completed_agent_id_belongs_to_role or state.completed_agent_id_is_role_key:
            failures.append("completed agent identity is not authorized for role")
    if state.repair_transaction_required and not state.repair_transaction_present:
        failures.append("repair transaction is required before commit")
    if state.outcome_policy == "three_distinct_outcomes":
        if not state.outcome_events_distinct:
            failures.append("repair outcomes are not three distinct events")
        if state.non_success_uses_success_event:
            failures.append("non-success outcome uses a success-only event")
    if state.parent_repair and state.repair_target_is_leaf_event:
        failures.append("parent repair targets a leaf-only event")
    required_targets = REQUIRED_TARGETS_BY_TYPE.get(state.transaction_type, frozenset())
    if required_targets and not required_targets.issubset(set(state.commit_targets)):
        failures.append("transaction commit targets are incomplete")
    if state.atomic_commit_declared and required_targets and not required_targets.issubset(set(state.commit_targets)):
        failures.append("atomic commit target is missing")
    if state.active_blocker_present and state.safe_to_continue_claimed:
        failures.append("active blocker cannot be marked safe to continue")
    if state.legacy_transaction and state.legacy_transaction_invalid and not state.legacy_quarantined:
        failures.append("invalid legacy transaction was not quarantined")
    if state.route_mutation and not state.stale_evidence_policy_applied:
        failures.append("route mutation omitted stale-evidence policy")
    return failures


class ControlTransactionRegistryStep:
    """One FlowPilot control transaction evaluation.

    Input x State -> Set(Output x State)
    reads: transaction registry row, contract registry row, event capability,
    packet ledger authority facts, repair transaction facts, run blockers
    writes: accepted transaction or explicit rejection/blocker classification
    idempotency: transaction id and commit targets determine repeated commits
    """

    name = "ControlTransactionRegistryStep"
    input_description = "control transaction tick"
    output_description = "accepted or rejected transaction classification"
    reads = (
        "control_transaction_registry",
        "contract_registry",
        "event_capability_registry",
        "packet_ledger",
        "repair_transaction_index",
        "run_state",
    )
    writes = ("transaction_decision", "blocker_classification")
    idempotency = "transaction-type and target scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return
    failures = control_transaction_failures(state)
    if failures:
        yield Transition(f"reject_{state.scenario}", replace(state, status="rejected", terminal_reason="; ".join(failures)))
        return
    yield Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="transaction_ok"))


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not control_transaction_failures(state)


def accepted_transactions_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = control_transaction_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe control transaction was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe control transaction was rejected")
    return InvariantResult.pass_()


def packet_authority_is_hard_gate(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.packet_authority_required:
        if not state.role_origin_checked or not state.completed_agent_id_belongs_to_role or state.completed_agent_id_is_role_key:
            return InvariantResult.fail("packet authority was bypassed")
    return InvariantResult.pass_()


def repair_outcomes_are_distinct(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.outcome_policy == "three_distinct_outcomes":
        if not state.outcome_events_distinct or state.non_success_uses_success_event:
            return InvariantResult.fail("unsafe repair outcome policy accepted")
    return InvariantResult.pass_()


def commits_are_complete(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    required = REQUIRED_TARGETS_BY_TYPE.get(state.transaction_type, frozenset())
    if required and not required.issubset(set(state.commit_targets)):
        return InvariantResult.fail("accepted transaction omitted required commit targets")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_transactions_are_safe",
        description="Only registered transactions with matching sub-registry facts can be accepted.",
        predicate=accepted_transactions_are_safe,
    ),
    Invariant(
        name="packet_authority_is_hard_gate",
        description="Packet/result transactions cannot pass without role-origin and agent authority.",
        predicate=packet_authority_is_hard_gate,
    ),
    Invariant(
        name="repair_outcomes_are_distinct",
        description="Repair transactions must keep success, blocker, and protocol-blocker outcomes distinct.",
        predicate=repair_outcomes_are_distinct,
    ),
    Invariant(
        name="commits_are_complete",
        description="Accepted transactions must commit all required state surfaces together.",
        predicate=commits_are_complete,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((ControlTransactionRegistryStep(),), name="flowpilot_control_transaction_registry")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "control_transaction_failures",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
