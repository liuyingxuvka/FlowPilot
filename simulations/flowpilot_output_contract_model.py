"""FlowGuard model for FlowPilot output-contract propagation.

Risk intent brief:
- Prevent FlowPilot from accepting role output whose contract was not selected
  by the PM from the system registry for the task family.
- Protect packet bodies from Controller relay and from envelope fields that
  smuggle body content.
- Model-critical state: PM contract selection, packet contract embedding,
  envelope-only Controller relay, role receive/self-check, and router
  accept/reject.
- Adversarial branches include a missing packet contract, a mismatched packet
  contract, a hidden router requirement absent from the contract, a missing
  required body field, and a forbidden body field copied into the envelope.
- Hard invariants: accepted outputs must carry one system-predefined contract
  end to end, satisfy all required body fields, avoid envelope body fields, pass
  role self-check, expose all router requirements through the contract, and
  keep Controller envelope-only.
- Blindspot: this is an abstract contract propagation model, not a replay
  adapter for concrete packet files.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_IMPLEMENTATION = "valid_implementation"
VALID_REVIEW = "valid_review"
MISSING_CONTRACT = "missing_contract"
MISMATCHED_CONTRACT = "mismatched_contract"
HIDDEN_ROUTER_REQUIREMENT = "hidden_router_requirement_absent_from_contract"
MISSING_REQUIRED_BODY_FIELD = "missing_required_body_field"
FORBIDDEN_ENVELOPE_BODY_FIELD = "forbidden_envelope_body_field"

NEGATIVE_SCENARIOS = (
    MISSING_CONTRACT,
    MISMATCHED_CONTRACT,
    HIDDEN_ROUTER_REQUIREMENT,
    MISSING_REQUIRED_BODY_FIELD,
    FORBIDDEN_ENVELOPE_BODY_FIELD,
)

SCENARIOS = (
    VALID_IMPLEMENTATION,
    VALID_REVIEW,
    *NEGATIVE_SCENARIOS,
)

ENVELOPE_FIELDS = frozenset(
    {
        "body_hash",
        "contract_id",
        "packet_id",
        "recipient_role",
        "task_family",
    }
)


@dataclass(frozen=True)
class ContractSpec:
    contract_id: str
    task_family: str
    required_body_fields: frozenset[str]
    allowed_envelope_fields: frozenset[str] = ENVELOPE_FIELDS

    @property
    def forbidden_envelope_fields(self) -> frozenset[str]:
        return self.required_body_fields | frozenset({"body", "body_fields"})


IMPLEMENTATION_CONTRACT = ContractSpec(
    contract_id="flowpilot.output_contract.worker_current_node_result.v1",
    task_family="worker.current_node",
    required_body_fields=frozenset(
        {
            "acceptance_plan_ref",
            "node_id",
            "work_scope",
        }
    ),
)

REVIEW_CONTRACT = ContractSpec(
    contract_id="flowpilot.output_contract.reviewer_review_report.v1",
    task_family="reviewer.review",
    required_body_fields=frozenset(
        {
            "review_scope",
            "reviewer_decision",
            "source_evidence_refs",
        }
    ),
)

CONTRACTS_BY_FAMILY = {
    IMPLEMENTATION_CONTRACT.task_family: IMPLEMENTATION_CONTRACT,
    REVIEW_CONTRACT.task_family: REVIEW_CONTRACT,
}

CONTRACTS_BY_ID = {
    spec.contract_id: spec for spec in CONTRACTS_BY_FAMILY.values()
}

NEGATIVE_EXPECTED_REJECTIONS = {
    MISSING_CONTRACT: "missing_contract",
    MISMATCHED_CONTRACT: "mismatched_contract",
    HIDDEN_ROUTER_REQUIREMENT: "hidden_router_requirement_absent_from_contract",
    MISSING_REQUIRED_BODY_FIELD: "missing_required_body_field",
    FORBIDDEN_ENVELOPE_BODY_FIELD: "forbidden_envelope_body_field",
}


@dataclass(frozen=True)
class Tick:
    """One output-contract propagation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    task_family: str = ""
    selected_contract_id: str = ""
    pm_selected_system_contract: bool = False

    packet_embedded_contract: bool = False
    packet_contract_id: str = ""
    envelope_contract_id: str = ""
    body_contract_id: str = ""
    envelope_fields: frozenset[str] = field(default_factory=frozenset)
    body_fields: frozenset[str] = field(default_factory=frozenset)
    hidden_router_requirement: str = ""

    controller_relayed_envelope_only: bool = False
    controller_read_body: bool = False
    controller_relayed_body_content: bool = False

    role_received_packet: bool = False
    role_self_check: str = "none"  # none | pass | fail
    role_self_check_reason: str = "none"

    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class OutputContractStep:
    """Model one FlowPilot output-contract handoff transition.

    Input x State -> Set(Output x State)
    reads: scenario, selected contract, packet contract fields, controller
    relay boundary, role self-check state, and router decision state
    writes: one propagation fact, self-check result, or terminal router decision
    idempotency: repeated ticks do not duplicate selected contracts, relay
    events, self-checks, or router decisions.
    """

    name = "OutputContractStep"
    reads = (
        "scenario",
        "pm_contract_selection",
        "packet_contract",
        "controller_relay_boundary",
        "role_self_check",
        "router_decision",
    )
    writes = (
        "selected_contract",
        "packet_contract_embedding",
        "envelope_only_relay",
        "role_self_check",
        "router_terminal_decision",
    )
    input_description = "output-contract propagation tick"
    output_description = "one abstract FlowPilot output-contract action"
    idempotency = "repeat ticks do not duplicate contract propagation facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _select_task_family(scenario: str) -> tuple[str, ContractSpec]:
    if scenario == VALID_REVIEW:
        return REVIEW_CONTRACT.task_family, REVIEW_CONTRACT
    return IMPLEMENTATION_CONTRACT.task_family, IMPLEMENTATION_CONTRACT


def _body_fields_for(spec: ContractSpec, scenario: str) -> frozenset[str]:
    if scenario == MISSING_REQUIRED_BODY_FIELD:
        return spec.required_body_fields - frozenset({"work_scope"})
    return spec.required_body_fields


def _packet_contract_for(spec: ContractSpec, scenario: str) -> tuple[str, str, str]:
    if scenario == MISSING_CONTRACT:
        return "", "", ""
    if scenario == MISMATCHED_CONTRACT:
        return (
            REVIEW_CONTRACT.contract_id,
            REVIEW_CONTRACT.contract_id,
            REVIEW_CONTRACT.contract_id,
        )
    return spec.contract_id, spec.contract_id, spec.contract_id


def _envelope_fields_for(spec: ContractSpec, scenario: str) -> frozenset[str]:
    if scenario == FORBIDDEN_ENVELOPE_BODY_FIELD:
        return spec.allowed_envelope_fields | frozenset({"work_scope"})
    return spec.allowed_envelope_fields


def _hidden_requirement_for(scenario: str) -> str:
    if scenario == HIDDEN_ROUTER_REQUIREMENT:
        return "worktree_digest"
    return ""


def _role_self_check_result(state: State) -> tuple[str, str]:
    selected = CONTRACTS_BY_ID.get(state.selected_contract_id)
    packet = CONTRACTS_BY_ID.get(state.packet_contract_id)
    if selected is None or packet is None:
        return "fail", "missing_contract"
    if (
        state.packet_contract_id != state.selected_contract_id
        or state.envelope_contract_id != state.selected_contract_id
        or state.body_contract_id != state.selected_contract_id
        or packet.task_family != state.task_family
    ):
        return "fail", "mismatched_contract"
    missing_fields = packet.required_body_fields - state.body_fields
    if missing_fields:
        return "fail", "missing_required_body_field"
    forbidden_fields = state.envelope_fields & packet.forbidden_envelope_fields
    if forbidden_fields:
        return "fail", "forbidden_envelope_body_field"
    return "pass", "none"


def _hidden_router_requirement_absent_from_contract(state: State) -> bool:
    if not state.hidden_router_requirement:
        return False
    spec = CONTRACTS_BY_ID.get(state.selected_contract_id)
    if spec is None:
        return True
    return state.hidden_router_requirement not in spec.required_body_fields


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            task_family, spec = _select_task_family(scenario)
            yield Transition(
                "pm_selects_system_contract_by_task_family",
                replace(
                    state,
                    status="running",
                    scenario=scenario,
                    task_family=task_family,
                    selected_contract_id=spec.contract_id,
                    pm_selected_system_contract=True,
                ),
            )
        return

    if not state.packet_embedded_contract:
        spec = CONTRACTS_BY_ID[state.selected_contract_id]
        packet_id, envelope_id, body_id = _packet_contract_for(spec, state.scenario)
        label = {
            VALID_IMPLEMENTATION: "packet_embeds_selected_contract",
            VALID_REVIEW: "packet_embeds_selected_contract",
            MISSING_CONTRACT: "packet_omits_selected_contract",
            MISMATCHED_CONTRACT: "packet_embeds_mismatched_contract",
            HIDDEN_ROUTER_REQUIREMENT: "packet_embeds_contract_with_hidden_router_requirement",
            MISSING_REQUIRED_BODY_FIELD: "packet_embeds_contract_with_missing_required_body_field",
            FORBIDDEN_ENVELOPE_BODY_FIELD: "packet_embeds_body_field_in_envelope",
        }[state.scenario]
        yield Transition(
            label,
            replace(
                state,
                packet_embedded_contract=True,
                packet_contract_id=packet_id,
                envelope_contract_id=envelope_id,
                body_contract_id=body_id,
                envelope_fields=_envelope_fields_for(spec, state.scenario),
                body_fields=_body_fields_for(spec, state.scenario),
                hidden_router_requirement=_hidden_requirement_for(state.scenario),
            ),
        )
        return

    if not state.controller_relayed_envelope_only:
        yield Transition(
            "controller_relays_envelope_only",
            replace(state, controller_relayed_envelope_only=True),
        )
        return

    if not state.role_received_packet:
        yield Transition(
            "role_receives_relayed_packet",
            replace(state, role_received_packet=True),
        )
        return

    if state.role_self_check == "none":
        result, reason = _role_self_check_result(state)
        if result == "pass":
            label = "role_self_check_passes_body_envelope_contract"
        else:
            label = f"role_self_check_rejects_{reason}"
        yield Transition(
            label,
            replace(
                state,
                role_self_check=result,
                role_self_check_reason=reason,
            ),
        )
        return

    if state.router_decision == "none":
        if state.role_self_check != "pass":
            reason = state.role_self_check_reason
            yield Transition(
                f"router_rejects_{reason}",
                replace(
                    state,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=reason,
                ),
            )
            return
        if _hidden_router_requirement_absent_from_contract(state):
            reason = "hidden_router_requirement_absent_from_contract"
            yield Transition(
                "router_rejects_hidden_router_requirement_absent_from_contract",
                replace(
                    state,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=reason,
                ),
            )
            return
        yield Transition(
            "router_accepts_self_checked_contract",
            replace(
                state,
                status="accepted",
                router_decision="accept",
            ),
        )
        return


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def _accepted_contract_spec(state: State) -> ContractSpec | None:
    if state.status != "accepted":
        return None
    return CONTRACTS_BY_ID.get(state.selected_contract_id)


def accepted_outputs_match_system_contract(state: State, trace) -> InvariantResult:
    del trace
    spec = _accepted_contract_spec(state)
    if spec is None:
        return InvariantResult.pass_()
    if not state.pm_selected_system_contract:
        return InvariantResult.fail("router accepted output before PM selected a system contract")
    if spec.task_family != state.task_family:
        return InvariantResult.fail("router accepted output with task family not mapped to selected contract")
    if (
        state.packet_contract_id != spec.contract_id
        or state.envelope_contract_id != spec.contract_id
        or state.body_contract_id != spec.contract_id
    ):
        return InvariantResult.fail("router accepted output with missing or mismatched propagated contract")
    return InvariantResult.pass_()


def accepted_outputs_satisfy_body_contract(state: State, trace) -> InvariantResult:
    del trace
    spec = _accepted_contract_spec(state)
    if spec is None:
        return InvariantResult.pass_()
    missing_fields = spec.required_body_fields - state.body_fields
    if missing_fields:
        return InvariantResult.fail("router accepted output with missing required body field")
    return InvariantResult.pass_()


def accepted_envelopes_are_metadata_only(state: State, trace) -> InvariantResult:
    del trace
    spec = _accepted_contract_spec(state)
    if spec is None:
        return InvariantResult.pass_()
    forbidden_fields = state.envelope_fields & spec.forbidden_envelope_fields
    if forbidden_fields:
        return InvariantResult.fail("router accepted output with forbidden envelope body field")
    return InvariantResult.pass_()


def controller_relay_is_envelope_only(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_relayed_envelope_only and (
        state.controller_read_body or state.controller_relayed_body_content
    ):
        return InvariantResult.fail("Controller relayed or read packet body content")
    return InvariantResult.pass_()


def role_self_check_gates_acceptance(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.role_self_check != "pass":
        return InvariantResult.fail("router accepted output before role self-check passed")
    return InvariantResult.pass_()


def router_requirements_are_contract_visible(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and _hidden_router_requirement_absent_from_contract(state):
        return InvariantResult.fail(
            "router accepted output with hidden router requirement absent from contract"
        )
    return InvariantResult.pass_()


def negative_scenarios_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative scenario {state.scenario}")
    if state.status == "rejected" and state.scenario not in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router rejected valid scenario {state.scenario}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.router_decision != "accept":
        return InvariantResult.fail("accepted terminal state lacks router accept decision")
    if state.status == "rejected" and (
        state.router_decision != "reject" or state.router_rejection_reason == "none"
    ):
        return InvariantResult.fail("rejected terminal state lacks explicit router rejection reason")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_outputs_match_system_contract",
        description="Router acceptance requires PM-selected system contract propagation through packet, envelope, and body.",
        predicate=accepted_outputs_match_system_contract,
    ),
    Invariant(
        name="accepted_outputs_satisfy_body_contract",
        description="Router acceptance requires every contract-required body field.",
        predicate=accepted_outputs_satisfy_body_contract,
    ),
    Invariant(
        name="accepted_envelopes_are_metadata_only",
        description="Router acceptance rejects envelopes containing body fields.",
        predicate=accepted_envelopes_are_metadata_only,
    ),
    Invariant(
        name="controller_relay_is_envelope_only",
        description="Controller may relay envelope metadata only and never packet body content.",
        predicate=controller_relay_is_envelope_only,
    ),
    Invariant(
        name="role_self_check_gates_acceptance",
        description="Router acceptance requires the role body/envelope self-check to pass.",
        predicate=role_self_check_gates_acceptance,
    ),
    Invariant(
        name="router_requirements_are_contract_visible",
        description="Router acceptance rejects hidden requirements absent from the selected contract.",
        predicate=router_requirements_are_contract_visible,
    ),
    Invariant(
        name="negative_scenarios_are_rejected",
        description="Invalid contract propagation scenarios must terminate in rejection, while valid scenarios are accepted.",
        predicate=negative_scenarios_are_rejected,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal router states must carry an explicit accept or reject decision.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((OutputContractStep(),), name="flowpilot_output_contract_propagation")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def _accepted_base(**changes: object) -> State:
    spec = IMPLEMENTATION_CONTRACT
    base = State(
        status="accepted",
        scenario=VALID_IMPLEMENTATION,
        task_family=spec.task_family,
        selected_contract_id=spec.contract_id,
        pm_selected_system_contract=True,
        packet_embedded_contract=True,
        packet_contract_id=spec.contract_id,
        envelope_contract_id=spec.contract_id,
        body_contract_id=spec.contract_id,
        envelope_fields=spec.allowed_envelope_fields,
        body_fields=spec.required_body_fields,
        controller_relayed_envelope_only=True,
        role_received_packet=True,
        role_self_check="pass",
        router_decision="accept",
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    spec = IMPLEMENTATION_CONTRACT
    return {
        MISSING_CONTRACT: _accepted_base(
            scenario=MISSING_CONTRACT,
            packet_contract_id="",
            envelope_contract_id="",
            body_contract_id="",
        ),
        MISMATCHED_CONTRACT: _accepted_base(
            scenario=MISMATCHED_CONTRACT,
            packet_contract_id=REVIEW_CONTRACT.contract_id,
            envelope_contract_id=REVIEW_CONTRACT.contract_id,
            body_contract_id=REVIEW_CONTRACT.contract_id,
        ),
        HIDDEN_ROUTER_REQUIREMENT: _accepted_base(
            scenario=HIDDEN_ROUTER_REQUIREMENT,
            hidden_router_requirement="worktree_digest",
        ),
        MISSING_REQUIRED_BODY_FIELD: _accepted_base(
            scenario=MISSING_REQUIRED_BODY_FIELD,
            body_fields=spec.required_body_fields - frozenset({"work_scope"}),
        ),
        FORBIDDEN_ENVELOPE_BODY_FIELD: _accepted_base(
            scenario=FORBIDDEN_ENVELOPE_BODY_FIELD,
            envelope_fields=spec.allowed_envelope_fields | frozenset({"work_scope"}),
        ),
        "controller_reads_body": _accepted_base(controller_read_body=True),
        "controller_relays_body_content": _accepted_base(controller_relayed_body_content=True),
        "accept_without_role_self_check": _accepted_base(role_self_check="fail"),
    }


__all__ = [
    "CONTRACTS_BY_FAMILY",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_EXPECTED_REJECTIONS",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
