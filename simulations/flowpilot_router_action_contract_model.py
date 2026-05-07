"""FlowGuard model for FlowPilot router action payload contracts.

Risk intent brief:
- Prevent ``next_action.payload_contract`` from hiding fields that the router's
  internal ``record_startup_answers`` validator requires.
- Protect the Controller from trial-and-error payload repair when startup
  answers are AI-interpreted from an explicit user reply.
- Model-critical state: action contract publication, required top-level
  startup answers, optional interpretation receipt contract, Controller payload
  construction from the published contract, and internal router validation.
- Adversarial branches include a contract that omits the hidden
  ``startup_answer_interpretation.schema_version`` requirement, a payload that
  omits that schema version despite a complete contract, and a contract that
  allows the interpretation receipt without listing all required nested fields.
- Hard invariants: accepted actions must have complete visible contracts,
  interpreted payloads must include every internally required receipt field,
  display actions must publish a copyable confirmation payload template,
  valid scenarios must be accepted, and negative scenarios must be rejected with
  explicit reasons.
- Blindspot: this is an abstract action-contract model, not a replay adapter
  for concrete router files or filesystem writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_EXPLICIT_STARTUP = "valid_explicit_startup_answers"
VALID_AI_INTERPRETED_STARTUP = "valid_ai_interpreted_startup_answers"
VALID_DISPLAY_CONFIRMATION = "valid_display_confirmation_action"
CONTRACT_MISSING_INTERPRETATION_SCHEMA = (
    "contract_missing_interpretation_schema_version"
)
PAYLOAD_MISSING_INTERPRETATION_SCHEMA = (
    "payload_missing_interpretation_schema_version"
)
CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS = (
    "contract_incomplete_interpretation_required_fields"
)
DISPLAY_TEMPLATE_MISSING_HASH = "display_confirmation_template_missing_hash"

NEGATIVE_SCENARIOS = (
    CONTRACT_MISSING_INTERPRETATION_SCHEMA,
    PAYLOAD_MISSING_INTERPRETATION_SCHEMA,
    CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS,
    DISPLAY_TEMPLATE_MISSING_HASH,
)

SCENARIOS = (
    VALID_EXPLICIT_STARTUP,
    VALID_AI_INTERPRETED_STARTUP,
    VALID_DISPLAY_CONFIRMATION,
    *NEGATIVE_SCENARIOS,
)

STARTUP_REQUIRED_FIELDS = frozenset(
    {
        "startup_answers.background_agents",
        "startup_answers.scheduled_continuation",
        "startup_answers.display_surface",
        "startup_answers.provenance",
    }
)

INTERPRETATION_REQUIRED_FIELDS = frozenset(
    {
        "startup_answer_interpretation.schema_version",
        "startup_answer_interpretation.raw_user_reply_text",
        "startup_answer_interpretation.interpreted_by",
        "startup_answer_interpretation.interpretation_provenance",
        "startup_answer_interpretation.ambiguity_status",
        "startup_answer_interpretation.interpreted_answers",
        "startup_answer_interpretation.interpreted_answers.background_agents",
        "startup_answer_interpretation.interpreted_answers.scheduled_continuation",
        "startup_answer_interpretation.interpreted_answers.display_surface",
    }
)

SCHEMA_FIELD = "startup_answer_interpretation.schema_version"
DISPLAY_HASH_FIELD = "display_confirmation.display_text_sha256"

DISPLAY_CONFIRMATION_REQUIRED_FIELDS = frozenset(
    {
        "display_confirmation.action_type",
        "display_confirmation.display_kind",
        DISPLAY_HASH_FIELD,
        "display_confirmation.provenance",
        "display_confirmation.rendered_to",
    }
)

NEGATIVE_EXPECTED_REJECTIONS = {
    CONTRACT_MISSING_INTERPRETATION_SCHEMA: "hidden_schema_version_not_exposed_by_payload_contract",
    PAYLOAD_MISSING_INTERPRETATION_SCHEMA: "payload_missing_interpretation_schema_version",
    CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS: "payload_contract_incomplete_interpretation_required_fields",
    DISPLAY_TEMPLATE_MISSING_HASH: "display_confirmation_payload_template_missing_required_fields",
}


@dataclass(frozen=True)
class PayloadContract:
    name: str = "startup_answers_with_optional_ai_interpretation_receipt"
    action_type: str = "record_startup_answers"
    required_object: str = "payload.startup_answers"
    required_fields: frozenset[str] = STARTUP_REQUIRED_FIELDS
    optional_fields: frozenset[str] = frozenset(
        {"payload.startup_answer_interpretation"}
    )
    required_nested_fields: frozenset[str] = INTERPRETATION_REQUIRED_FIELDS
    controller_may_fill_missing_fields: bool = False

    @property
    def exposes_interpretation(self) -> bool:
        return "payload.startup_answer_interpretation" in self.optional_fields


@dataclass(frozen=True)
class Tick:
    """One router action-contract tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    action_family: str = "unset"  # startup_answers | display_confirmation
    contract: PayloadContract = field(default_factory=PayloadContract)
    payload_contract_published: bool = False
    payload_built_from_contract: bool = False
    payload_startup_fields: frozenset[str] = field(default_factory=frozenset)
    payload_includes_interpretation: bool = False
    payload_interpretation_fields: frozenset[str] = field(default_factory=frozenset)
    display_payload_template_fields: frozenset[str] = field(default_factory=frozenset)
    payload_display_confirmation_fields: frozenset[str] = field(default_factory=frozenset)
    internal_interpretation_required_fields: frozenset[str] = (
        INTERPRETATION_REQUIRED_FIELDS
    )
    validator_checked: bool = False
    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RouterActionContractStep:
    """Model one ``record_startup_answers`` action-contract transition.

    Input x State -> Set(Output x State)
    reads: scenario, published payload contract, payload fields, validator state
    writes: contract publication, Controller-built payload, router terminal
    decision
    idempotency: repeated ticks do not republish contracts, rebuild payloads, or
    duplicate terminal router decisions.
    """

    name = "RouterActionContractStep"
    reads = (
        "scenario",
        "payload_contract",
        "payload_fields",
        "internal_validator_requirements",
        "router_decision",
    )
    writes = (
        "payload_contract_publication",
        "controller_payload_from_contract",
        "validator_check",
        "router_terminal_decision",
    )
    input_description = "router action-contract tick"
    output_description = "one abstract router action-contract step"
    idempotency = "repeat ticks do not duplicate action-contract decisions"

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


def _contract_for(scenario: str) -> PayloadContract:
    if scenario == CONTRACT_MISSING_INTERPRETATION_SCHEMA:
        return PayloadContract(
            required_nested_fields=INTERPRETATION_REQUIRED_FIELDS
            - frozenset({SCHEMA_FIELD})
        )
    if scenario == CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS:
        return PayloadContract(
            required_nested_fields=INTERPRETATION_REQUIRED_FIELDS
            - frozenset(
                {
                    "startup_answer_interpretation.interpreted_by",
                    "startup_answer_interpretation.interpreted_answers",
                    "startup_answer_interpretation.interpreted_answers.display_surface",
                }
            )
        )
    return PayloadContract()


def _action_family_for(scenario: str) -> str:
    if scenario in {VALID_DISPLAY_CONFIRMATION, DISPLAY_TEMPLATE_MISSING_HASH}:
        return "display_confirmation"
    return "startup_answers"


def _display_template_fields_for(scenario: str) -> frozenset[str]:
    if scenario == DISPLAY_TEMPLATE_MISSING_HASH:
        return DISPLAY_CONFIRMATION_REQUIRED_FIELDS - frozenset({DISPLAY_HASH_FIELD})
    if scenario == VALID_DISPLAY_CONFIRMATION:
        return DISPLAY_CONFIRMATION_REQUIRED_FIELDS
    return frozenset()


def _payload_fields_for(scenario: str, contract: PayloadContract) -> tuple[bool, frozenset[str]]:
    if scenario == VALID_EXPLICIT_STARTUP:
        return False, frozenset()
    if scenario == PAYLOAD_MISSING_INTERPRETATION_SCHEMA:
        return True, INTERPRETATION_REQUIRED_FIELDS - frozenset({SCHEMA_FIELD})
    if scenario in {
        VALID_AI_INTERPRETED_STARTUP,
        CONTRACT_MISSING_INTERPRETATION_SCHEMA,
        CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS,
    }:
        return True, contract.required_nested_fields
    return False, frozenset()


def _missing_contract_fields(contract: PayloadContract) -> frozenset[str]:
    if not contract.exposes_interpretation:
        return INTERPRETATION_REQUIRED_FIELDS
    return INTERPRETATION_REQUIRED_FIELDS - contract.required_nested_fields


def _contract_rejection_reason(contract: PayloadContract) -> str:
    missing = _missing_contract_fields(contract)
    if SCHEMA_FIELD in missing:
        return "hidden_schema_version_not_exposed_by_payload_contract"
    if missing:
        return "payload_contract_incomplete_interpretation_required_fields"
    return "none"


def _validator_rejection_reason(state: State) -> str:
    missing_startup = STARTUP_REQUIRED_FIELDS - state.payload_startup_fields
    if missing_startup:
        return "payload_missing_startup_answers_required_fields"
    if not state.payload_includes_interpretation:
        return "none"
    missing_interpretation = (
        state.internal_interpretation_required_fields - state.payload_interpretation_fields
    )
    if SCHEMA_FIELD in missing_interpretation:
        return "payload_missing_interpretation_schema_version"
    if missing_interpretation:
        return "payload_missing_interpretation_required_fields"
    return "none"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            family = _action_family_for(scenario)
            label = (
                "router_selects_display_confirmation_action_template"
                if family == "display_confirmation"
                else "router_selects_record_startup_answers_action_contract"
            )
            yield Transition(
                label,
                replace(
                    state,
                    status="running",
                    scenario=scenario,
                    action_family=family,
                    contract=_contract_for(scenario),
                    display_payload_template_fields=_display_template_fields_for(scenario),
                ),
            )
        return

    if state.action_family == "display_confirmation":
        missing_template_fields = (
            DISPLAY_CONFIRMATION_REQUIRED_FIELDS - state.display_payload_template_fields
        )
        if not state.payload_contract_published:
            if missing_template_fields:
                yield Transition(
                    "router_rejects_display_confirmation_payload_template_missing_hash",
                    replace(
                        state,
                        status="rejected",
                        payload_contract_published=True,
                        router_decision="reject",
                        router_rejection_reason=(
                            "display_confirmation_payload_template_missing_required_fields"
                        ),
                    ),
                )
                return
            yield Transition(
                "router_publishes_display_confirmation_payload_template",
                replace(state, payload_contract_published=True),
            )
            return

        if not state.payload_built_from_contract:
            yield Transition(
                "controller_submits_display_confirmation_from_payload_template",
                replace(
                    state,
                    payload_built_from_contract=True,
                    payload_display_confirmation_fields=state.display_payload_template_fields,
                ),
            )
            return

        if not state.validator_checked:
            missing_payload_fields = (
                DISPLAY_CONFIRMATION_REQUIRED_FIELDS - state.payload_display_confirmation_fields
            )
            if missing_payload_fields:
                yield Transition(
                    "router_validator_rejects_display_confirmation_missing_required_fields",
                    replace(
                        state,
                        status="rejected",
                        validator_checked=True,
                        router_decision="reject",
                        router_rejection_reason="display_confirmation_missing_required_fields",
                    ),
                )
                return
            yield Transition(
                "router_validator_accepts_display_confirmation_payload",
                replace(
                    state,
                    status="accepted",
                    validator_checked=True,
                    router_decision="accept",
                ),
            )
            return

    if not state.payload_contract_published:
        contract_reason = _contract_rejection_reason(state.contract)
        if contract_reason != "none":
            label = {
                "hidden_schema_version_not_exposed_by_payload_contract": (
                    "router_rejects_payload_contract_missing_interpretation_schema_version"
                ),
                "payload_contract_incomplete_interpretation_required_fields": (
                    "router_rejects_payload_contract_incomplete_interpretation_required_fields"
                ),
            }[contract_reason]
            yield Transition(
                label,
                replace(
                    state,
                    status="rejected",
                    payload_contract_published=True,
                    router_decision="reject",
                    router_rejection_reason=contract_reason,
                ),
            )
            return
        yield Transition(
            "router_publishes_complete_payload_contract",
            replace(state, payload_contract_published=True),
        )
        return

    if not state.payload_built_from_contract:
        includes_interpretation, interpretation_fields = _payload_fields_for(
            state.scenario, state.contract
        )
        label = {
            VALID_EXPLICIT_STARTUP: "controller_submits_explicit_startup_answers_without_interpretation",
            VALID_AI_INTERPRETED_STARTUP: "controller_submits_ai_interpreted_startup_answers_with_full_receipt",
            PAYLOAD_MISSING_INTERPRETATION_SCHEMA: (
                "controller_submits_ai_interpreted_startup_answers_without_schema_version"
            ),
        }[state.scenario]
        yield Transition(
            label,
            replace(
                state,
                payload_built_from_contract=True,
                payload_startup_fields=STARTUP_REQUIRED_FIELDS,
                payload_includes_interpretation=includes_interpretation,
                payload_interpretation_fields=interpretation_fields,
            ),
        )
        return

    if not state.validator_checked:
        reason = _validator_rejection_reason(state)
        if reason != "none":
            yield Transition(
                f"router_validator_rejects_{reason}",
                replace(
                    state,
                    status="rejected",
                    validator_checked=True,
                    router_decision="reject",
                    router_rejection_reason=reason,
                ),
            )
            return
        yield Transition(
            "router_validator_accepts_contract_visible_payload",
            replace(
                state,
                status="accepted",
                validator_checked=True,
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


def accepted_actions_have_complete_visible_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.action_family != "startup_answers":
        return InvariantResult.pass_()
    missing = _missing_contract_fields(state.contract)
    if missing:
        return InvariantResult.fail(
            "router accepted action with internal required fields absent from payload_contract"
        )
    if not STARTUP_REQUIRED_FIELDS.issubset(state.contract.required_fields):
        return InvariantResult.fail(
            "router accepted action without exposing all startup_answers required fields"
        )
    if state.contract.controller_may_fill_missing_fields:
        return InvariantResult.fail("router accepted contract that allowed Controller field guessing")
    return InvariantResult.pass_()


def accepted_ai_interpretations_include_schema_version(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status != "accepted"
        or state.action_family != "startup_answers"
        or not state.payload_includes_interpretation
    ):
        return InvariantResult.pass_()
    if SCHEMA_FIELD not in state.contract.required_nested_fields:
        return InvariantResult.fail(
            "router accepted AI interpretation without schema_version in payload_contract"
        )
    if SCHEMA_FIELD not in state.payload_interpretation_fields:
        return InvariantResult.fail(
            "router accepted AI interpretation payload without schema_version"
        )
    return InvariantResult.pass_()


def accepted_ai_interpretations_satisfy_internal_validator(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status != "accepted"
        or state.action_family != "startup_answers"
        or not state.payload_includes_interpretation
    ):
        return InvariantResult.pass_()
    missing = state.internal_interpretation_required_fields - state.payload_interpretation_fields
    if missing:
        return InvariantResult.fail(
            "router accepted AI interpretation missing internal validator required fields"
        )
    return InvariantResult.pass_()


def accepted_display_actions_publish_copyable_payload_template(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.action_family != "display_confirmation":
        return InvariantResult.pass_()
    missing_template = DISPLAY_CONFIRMATION_REQUIRED_FIELDS - state.display_payload_template_fields
    if missing_template:
        return InvariantResult.fail(
            "router accepted display action without complete display_confirmation payload_template"
        )
    missing_payload = DISPLAY_CONFIRMATION_REQUIRED_FIELDS - state.payload_display_confirmation_fields
    if missing_payload:
        return InvariantResult.fail(
            "router accepted display action payload missing template-required fields"
        )
    return InvariantResult.pass_()


def scenarios_end_in_expected_decisions(state: State, trace) -> InvariantResult:
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
        name="accepted_actions_have_complete_visible_contract",
        description="Router acceptance requires every internal startup-answer validator requirement to be visible in the payload contract.",
        predicate=accepted_actions_have_complete_visible_contract,
    ),
    Invariant(
        name="accepted_ai_interpretations_include_schema_version",
        description="AI-interpreted startup answers require schema_version in both the contract and payload receipt.",
        predicate=accepted_ai_interpretations_include_schema_version,
    ),
    Invariant(
        name="accepted_ai_interpretations_satisfy_internal_validator",
        description="Accepted interpretation receipts satisfy all internal validator-required nested fields.",
        predicate=accepted_ai_interpretations_satisfy_internal_validator,
    ),
    Invariant(
        name="accepted_display_actions_publish_copyable_payload_template",
        description="Accepted display actions expose a copyable display_confirmation payload template.",
        predicate=accepted_display_actions_publish_copyable_payload_template,
    ),
    Invariant(
        name="scenarios_end_in_expected_decisions",
        description="Valid scenarios are accepted and negative scenarios are rejected.",
        predicate=scenarios_end_in_expected_decisions,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal action states carry explicit router accept or reject decisions.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 5
REQUIRED_LABELS = (
    "router_selects_record_startup_answers_action_contract",
    "router_selects_display_confirmation_action_template",
    "router_publishes_complete_payload_contract",
    "router_publishes_display_confirmation_payload_template",
    "controller_submits_explicit_startup_answers_without_interpretation",
    "controller_submits_ai_interpreted_startup_answers_with_full_receipt",
    "controller_submits_ai_interpreted_startup_answers_without_schema_version",
    "controller_submits_display_confirmation_from_payload_template",
    "router_validator_accepts_contract_visible_payload",
    "router_validator_accepts_display_confirmation_payload",
    "router_validator_rejects_payload_missing_interpretation_schema_version",
    "router_rejects_payload_contract_missing_interpretation_schema_version",
    "router_rejects_payload_contract_incomplete_interpretation_required_fields",
    "router_rejects_display_confirmation_payload_template_missing_hash",
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((RouterActionContractStep(),), name="flowpilot_router_action_contract")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def _accepted_base(**changes: object) -> State:
    base = State(
        status="accepted",
        scenario=VALID_AI_INTERPRETED_STARTUP,
        action_family="startup_answers",
        contract=PayloadContract(),
        payload_contract_published=True,
        payload_built_from_contract=True,
        payload_startup_fields=STARTUP_REQUIRED_FIELDS,
        payload_includes_interpretation=True,
        payload_interpretation_fields=INTERPRETATION_REQUIRED_FIELDS,
        validator_checked=True,
        router_decision="accept",
    )
    return replace(base, **changes)


def _accepted_display_base(**changes: object) -> State:
    base = State(
        status="accepted",
        scenario=VALID_DISPLAY_CONFIRMATION,
        action_family="display_confirmation",
        payload_contract_published=True,
        payload_built_from_contract=True,
        display_payload_template_fields=DISPLAY_CONFIRMATION_REQUIRED_FIELDS,
        payload_display_confirmation_fields=DISPLAY_CONFIRMATION_REQUIRED_FIELDS,
        validator_checked=True,
        router_decision="accept",
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        CONTRACT_MISSING_INTERPRETATION_SCHEMA: _accepted_base(
            scenario=CONTRACT_MISSING_INTERPRETATION_SCHEMA,
            contract=_contract_for(CONTRACT_MISSING_INTERPRETATION_SCHEMA),
            payload_interpretation_fields=INTERPRETATION_REQUIRED_FIELDS
            - frozenset({SCHEMA_FIELD}),
        ),
        PAYLOAD_MISSING_INTERPRETATION_SCHEMA: _accepted_base(
            scenario=PAYLOAD_MISSING_INTERPRETATION_SCHEMA,
            payload_interpretation_fields=INTERPRETATION_REQUIRED_FIELDS
            - frozenset({SCHEMA_FIELD}),
        ),
        CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS: _accepted_base(
            scenario=CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS,
            contract=_contract_for(CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS),
        ),
        "controller_may_fill_missing_fields": _accepted_base(
            contract=PayloadContract(controller_may_fill_missing_fields=True)
        ),
        DISPLAY_TEMPLATE_MISSING_HASH: _accepted_display_base(
            scenario=DISPLAY_TEMPLATE_MISSING_HASH,
            display_payload_template_fields=DISPLAY_CONFIRMATION_REQUIRED_FIELDS
            - frozenset({DISPLAY_HASH_FIELD}),
            payload_display_confirmation_fields=DISPLAY_CONFIRMATION_REQUIRED_FIELDS
            - frozenset({DISPLAY_HASH_FIELD}),
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "DISPLAY_CONFIRMATION_REQUIRED_FIELDS",
    "DISPLAY_HASH_FIELD",
    "DISPLAY_TEMPLATE_MISSING_HASH",
    "INTERPRETATION_REQUIRED_FIELDS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_EXPECTED_REJECTIONS",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "SCENARIOS",
    "SCHEMA_FIELD",
    "STARTUP_REQUIRED_FIELDS",
    "VALID_DISPLAY_CONFIRMATION",
    "Action",
    "PayloadContract",
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
