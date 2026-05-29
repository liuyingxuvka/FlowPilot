"""FlowGuard model for FlowPilot router action payload contracts.

Risk intent brief:
- Prevent ``open_startup_intake_ui`` from hiding the native startup intake
  result path or allowing Controller to synthesize startup answers directly.
- Protect the Controller from body-text leakage: startup intake can expose
  paths, hashes, status, and startup options, but not the user's work-request
  body.
- Model-critical state: action contract publication, Controller payload
  construction from the contract, native-interactive startup result evidence,
  display-confirmation payload templates, and router validation.
- Adversarial branches include a contract that omits the required result path,
  a payload that omits the result path, a headless startup result, a result
  that exposes body text to Controller, and a display template without a hash.
- Hard invariants: accepted startup intake actions must publish a complete
  visible contract, accepted startup intake results must be native-interactive,
  accepted startup intake must keep body text out of Controller-visible
  payloads, display actions must publish a copyable confirmation payload
  template, valid scenarios must be accepted, and negative scenarios must be
  rejected with explicit reasons.
- Blindspot: this is an abstract action-contract model, not a replay adapter
  for concrete router files or filesystem writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_CONFIRMED_STARTUP_INTAKE = "valid_confirmed_startup_intake_result"
VALID_CANCELLED_STARTUP_INTAKE = "valid_cancelled_startup_intake_result"
VALID_DISPLAY_CONFIRMATION = "valid_display_confirmation_action"
CONTRACT_MISSING_RESULT_PATH = "contract_missing_startup_intake_result_path"
PAYLOAD_MISSING_RESULT_PATH = "payload_missing_startup_intake_result_path"
RESULT_HEADLESS = "startup_intake_result_headless"
RESULT_BODY_TEXT_EXPOSED = "startup_intake_result_exposes_body_text"
DISPLAY_TEMPLATE_MISSING_HASH = "display_confirmation_template_missing_hash"

NEGATIVE_SCENARIOS = (
    CONTRACT_MISSING_RESULT_PATH,
    PAYLOAD_MISSING_RESULT_PATH,
    RESULT_HEADLESS,
    RESULT_BODY_TEXT_EXPOSED,
    DISPLAY_TEMPLATE_MISSING_HASH,
)

SCENARIOS = (
    VALID_CONFIRMED_STARTUP_INTAKE,
    VALID_CANCELLED_STARTUP_INTAKE,
    VALID_DISPLAY_CONFIRMATION,
    *NEGATIVE_SCENARIOS,
)

STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS = frozenset(
    {"startup_intake_result.result_path"}
)

STARTUP_INTAKE_CANCELLED_RESULT_REQUIRED_FIELDS = frozenset(
    {
        "result.schema_version",
        "result.status",
        "result.launch_mode",
        "result.headless",
        "result.formal_startup_allowed",
        "result.receipt_path",
    }
)

STARTUP_INTAKE_CONFIRMED_RESULT_REQUIRED_FIELDS = frozenset(
    {
        *STARTUP_INTAKE_CANCELLED_RESULT_REQUIRED_FIELDS,
        "result.envelope_path",
        "result.body_path",
        "result.body_hash",
        "result.startup_answers",
        "result.controller_may_read_body",
        "result.body_text_included",
    }
)

STARTUP_INTAKE_INTERACTIVE_FIELDS = frozenset(
    {
        "result.launch_mode",
        "result.headless",
        "result.formal_startup_allowed",
    }
)

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
    CONTRACT_MISSING_RESULT_PATH: "payload_contract_missing_startup_intake_result_path",
    PAYLOAD_MISSING_RESULT_PATH: "payload_missing_startup_intake_result_path",
    RESULT_HEADLESS: "startup_intake_result_not_native_interactive",
    RESULT_BODY_TEXT_EXPOSED: "startup_intake_result_exposes_body_text",
    DISPLAY_TEMPLATE_MISSING_HASH: "display_confirmation_payload_template_missing_required_fields",
}


@dataclass(frozen=True)
class PayloadContract:
    name: str = "startup_intake_result_path"
    action_type: str = "open_startup_intake_ui"
    required_object: str = "payload.startup_intake_result"
    required_fields: frozenset[str] = STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS
    controller_may_fill_missing_fields: bool = False

    @property
    def exposes_result_path(self) -> bool:
        return STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS.issubset(self.required_fields)


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
    action_family: str = "unset"  # startup_intake | display_confirmation
    contract: PayloadContract = field(default_factory=PayloadContract)
    payload_contract_published: bool = False
    payload_built_from_contract: bool = False
    payload_startup_intake_fields: frozenset[str] = field(default_factory=frozenset)
    startup_result_status: str = "unset"  # unset | confirmed | cancelled
    startup_result_fields: frozenset[str] = field(default_factory=frozenset)
    startup_result_headless: bool = False
    startup_result_formal_allowed: bool = True
    startup_result_body_text_included: bool = False
    startup_result_controller_may_read_body: bool = False
    display_payload_template_fields: frozenset[str] = field(default_factory=frozenset)
    payload_display_confirmation_fields: frozenset[str] = field(default_factory=frozenset)
    validator_checked: bool = False
    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RouterActionContractStep:
    """Model one ``open_startup_intake_ui`` action-contract transition.

    Input x State -> Set(Output x State)
    reads: scenario, published payload contract, payload fields, validator state
    writes: contract publication, Controller-built payload, validator check,
    router terminal decision
    idempotency: repeated ticks do not republish contracts, rebuild payloads,
    or duplicate terminal router decisions.
    """

    name = "RouterActionContractStep"
    reads = (
        "scenario",
        "payload_contract",
        "payload_fields",
        "native_startup_intake_requirements",
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
    if scenario == CONTRACT_MISSING_RESULT_PATH:
        return PayloadContract(required_fields=frozenset())
    return PayloadContract()


def _action_family_for(scenario: str) -> str:
    if scenario in {VALID_DISPLAY_CONFIRMATION, DISPLAY_TEMPLATE_MISSING_HASH}:
        return "display_confirmation"
    return "startup_intake"


def _display_template_fields_for(scenario: str) -> frozenset[str]:
    if scenario == DISPLAY_TEMPLATE_MISSING_HASH:
        return DISPLAY_CONFIRMATION_REQUIRED_FIELDS - frozenset({DISPLAY_HASH_FIELD})
    if scenario == VALID_DISPLAY_CONFIRMATION:
        return DISPLAY_CONFIRMATION_REQUIRED_FIELDS
    return frozenset()


def _startup_result_for(
    scenario: str,
) -> tuple[frozenset[str], str, frozenset[str], bool, bool, bool, bool]:
    payload_fields = STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS
    result_status = "confirmed"
    result_fields = STARTUP_INTAKE_CONFIRMED_RESULT_REQUIRED_FIELDS
    headless = False
    formal_allowed = True
    body_text_included = False
    controller_may_read_body = False
    if scenario == VALID_CANCELLED_STARTUP_INTAKE:
        result_status = "cancelled"
        result_fields = STARTUP_INTAKE_CANCELLED_RESULT_REQUIRED_FIELDS
    elif scenario == PAYLOAD_MISSING_RESULT_PATH:
        payload_fields = frozenset()
    elif scenario == RESULT_HEADLESS:
        headless = True
        formal_allowed = False
    elif scenario == RESULT_BODY_TEXT_EXPOSED:
        body_text_included = True
        controller_may_read_body = True
    return (
        payload_fields,
        result_status,
        result_fields,
        headless,
        formal_allowed,
        body_text_included,
        controller_may_read_body,
    )


def _missing_contract_fields(contract: PayloadContract) -> frozenset[str]:
    return STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS - contract.required_fields


def _contract_rejection_reason(contract: PayloadContract) -> str:
    missing = _missing_contract_fields(contract)
    if "startup_intake_result.result_path" in missing:
        return "payload_contract_missing_startup_intake_result_path"
    return "none"


def _required_result_fields_for(status: str) -> frozenset[str]:
    if status == "cancelled":
        return STARTUP_INTAKE_CANCELLED_RESULT_REQUIRED_FIELDS
    return STARTUP_INTAKE_CONFIRMED_RESULT_REQUIRED_FIELDS


def _validator_rejection_reason(state: State) -> str:
    missing_payload = (
        STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS - state.payload_startup_intake_fields
    )
    if missing_payload:
        return "payload_missing_startup_intake_result_path"
    missing_result = _required_result_fields_for(state.startup_result_status) - state.startup_result_fields
    if missing_result:
        return "startup_intake_result_missing_required_fields"
    if (
        state.startup_result_headless
        or not state.startup_result_formal_allowed
        or not STARTUP_INTAKE_INTERACTIVE_FIELDS.issubset(state.startup_result_fields)
    ):
        return "startup_intake_result_not_native_interactive"
    if state.startup_result_status == "confirmed" and (
        state.startup_result_body_text_included
        or state.startup_result_controller_may_read_body
    ):
        return "startup_intake_result_exposes_body_text"
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
                else "router_selects_startup_intake_ui_action_contract"
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
            yield Transition(
                "router_rejects_payload_contract_missing_startup_intake_result_path",
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
            "router_publishes_startup_intake_result_path_contract",
            replace(state, payload_contract_published=True),
        )
        return

    if not state.payload_built_from_contract:
        (
            payload_fields,
            result_status,
            result_fields,
            headless,
            formal_allowed,
            body_text_included,
            controller_may_read_body,
        ) = _startup_result_for(state.scenario)
        label = {
            VALID_CONFIRMED_STARTUP_INTAKE: "controller_submits_confirmed_startup_intake_result_path",
            VALID_CANCELLED_STARTUP_INTAKE: "controller_submits_cancelled_startup_intake_result_path",
            PAYLOAD_MISSING_RESULT_PATH: "controller_submits_startup_intake_payload_without_result_path",
            RESULT_HEADLESS: "controller_submits_headless_startup_intake_result",
            RESULT_BODY_TEXT_EXPOSED: "controller_submits_startup_intake_result_with_body_text_visible",
        }[state.scenario]
        yield Transition(
            label,
            replace(
                state,
                payload_built_from_contract=True,
                payload_startup_intake_fields=payload_fields,
                startup_result_status=result_status,
                startup_result_fields=result_fields,
                startup_result_headless=headless,
                startup_result_formal_allowed=formal_allowed,
                startup_result_body_text_included=body_text_included,
                startup_result_controller_may_read_body=controller_may_read_body,
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
        label = (
            "router_validator_accepts_cancelled_startup_intake_result"
            if state.startup_result_status == "cancelled"
            else "router_validator_accepts_native_startup_intake_result"
        )
        yield Transition(
            label,
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


def accepted_startup_intake_actions_have_result_path_contract(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.action_family != "startup_intake":
        return InvariantResult.pass_()
    if _missing_contract_fields(state.contract):
        return InvariantResult.fail(
            "router accepted startup intake with result_path absent from payload_contract"
        )
    if not STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS.issubset(
        state.payload_startup_intake_fields
    ):
        return InvariantResult.fail(
            "router accepted startup intake payload without result_path"
        )
    if state.contract.controller_may_fill_missing_fields:
        return InvariantResult.fail("router accepted contract that allowed Controller field guessing")
    return InvariantResult.pass_()


def accepted_startup_intake_payloads_are_native_interactive(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.action_family != "startup_intake":
        return InvariantResult.pass_()
    if (
        state.startup_result_headless
        or not state.startup_result_formal_allowed
        or not STARTUP_INTAKE_INTERACTIVE_FIELDS.issubset(state.startup_result_fields)
    ):
        return InvariantResult.fail(
            "router accepted startup intake result without native interactive proof"
        )
    return InvariantResult.pass_()


def accepted_startup_intake_keeps_body_out_of_controller_payload(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.action_family != "startup_intake":
        return InvariantResult.pass_()
    if state.startup_result_status == "confirmed" and (
        state.startup_result_body_text_included
        or state.startup_result_controller_may_read_body
    ):
        return InvariantResult.fail(
            "router accepted startup intake result that exposed body text to Controller"
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
        name="accepted_startup_intake_actions_have_result_path_contract",
        description="Router acceptance requires startup intake result_path to be visible in the payload contract and payload.",
        predicate=accepted_startup_intake_actions_have_result_path_contract,
    ),
    Invariant(
        name="accepted_startup_intake_payloads_are_native_interactive",
        description="Accepted startup intake results carry native interactive launch proof.",
        predicate=accepted_startup_intake_payloads_are_native_interactive,
    ),
    Invariant(
        name="accepted_startup_intake_keeps_body_out_of_controller_payload",
        description="Accepted startup intake results keep user body text out of Controller-visible payloads.",
        predicate=accepted_startup_intake_keeps_body_out_of_controller_payload,
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
    "router_selects_startup_intake_ui_action_contract",
    "router_selects_display_confirmation_action_template",
    "router_publishes_startup_intake_result_path_contract",
    "router_publishes_display_confirmation_payload_template",
    "controller_submits_confirmed_startup_intake_result_path",
    "controller_submits_cancelled_startup_intake_result_path",
    "controller_submits_startup_intake_payload_without_result_path",
    "controller_submits_headless_startup_intake_result",
    "controller_submits_startup_intake_result_with_body_text_visible",
    "controller_submits_display_confirmation_from_payload_template",
    "router_validator_accepts_native_startup_intake_result",
    "router_validator_accepts_cancelled_startup_intake_result",
    "router_validator_accepts_display_confirmation_payload",
    "router_validator_rejects_payload_missing_startup_intake_result_path",
    "router_validator_rejects_startup_intake_result_not_native_interactive",
    "router_validator_rejects_startup_intake_result_exposes_body_text",
    "router_rejects_payload_contract_missing_startup_intake_result_path",
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


def _accepted_startup_base(**changes: object) -> State:
    base = State(
        status="accepted",
        scenario=VALID_CONFIRMED_STARTUP_INTAKE,
        action_family="startup_intake",
        contract=PayloadContract(),
        payload_contract_published=True,
        payload_built_from_contract=True,
        payload_startup_intake_fields=STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS,
        startup_result_status="confirmed",
        startup_result_fields=STARTUP_INTAKE_CONFIRMED_RESULT_REQUIRED_FIELDS,
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
        CONTRACT_MISSING_RESULT_PATH: _accepted_startup_base(
            scenario=CONTRACT_MISSING_RESULT_PATH,
            contract=_contract_for(CONTRACT_MISSING_RESULT_PATH),
        ),
        PAYLOAD_MISSING_RESULT_PATH: _accepted_startup_base(
            scenario=PAYLOAD_MISSING_RESULT_PATH,
            payload_startup_intake_fields=frozenset(),
        ),
        RESULT_HEADLESS: _accepted_startup_base(
            scenario=RESULT_HEADLESS,
            startup_result_headless=True,
            startup_result_formal_allowed=False,
        ),
        RESULT_BODY_TEXT_EXPOSED: _accepted_startup_base(
            scenario=RESULT_BODY_TEXT_EXPOSED,
            startup_result_body_text_included=True,
            startup_result_controller_may_read_body=True,
        ),
        "controller_may_fill_missing_fields": _accepted_startup_base(
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
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_EXPECTED_REJECTIONS",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "SCENARIOS",
    "STARTUP_INTAKE_CANCELLED_RESULT_REQUIRED_FIELDS",
    "STARTUP_INTAKE_CONFIRMED_RESULT_REQUIRED_FIELDS",
    "STARTUP_INTAKE_INTERACTIVE_FIELDS",
    "STARTUP_INTAKE_PAYLOAD_REQUIRED_FIELDS",
    "VALID_CANCELLED_STARTUP_INTAKE",
    "VALID_CONFIRMED_STARTUP_INTAKE",
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
