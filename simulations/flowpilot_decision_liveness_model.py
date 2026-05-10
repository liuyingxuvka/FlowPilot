"""FlowGuard model for FlowPilot PM role-work-request liveness.

Risk intent brief:
- Prevent accepted PM decisions from becoming legal-but-unroutable states.
- Preserve PM freedom to ask any FlowPilot role for support before making a
  decision, while keeping the router envelope-only and ledger-driven.
- Model-critical durable state: PM decision context, always-open work-request
  channel, request id, recipient role, output contract, blocking/advisory mode,
  packet relay, result return, packet-ledger check, PM absorption, controlled
  user stop, model-miss triage closure, repair opening, and terminal closure.
- Adversarial branches include nonterminal PM decisions that loop back to the
  same event, PM work requests with missing recipient/contract, duplicate open
  request ids, wrong-role or wrong-request results, result relay before ledger
  check, Controller body reads, blocking requests ignored by PM final decisions,
  unresolved advisory results at terminal closure, and special-cased
  model-miss officer requests that bypass the generic PM work-request channel.
- Hard invariants: PM can open role-work requests whenever PM owns a decision;
  every accepted nonterminal PM decision opens a distinct role/user channel;
  PM work requests must have recipient, contract, id, and ledger state; results
  return to PM by default and are absorbed before use; blocking requests block
  dependent final decisions; advisory results are resolved before terminal
  closure; Controller never reads sealed bodies.
- Blindspot: this model checks the protocol shape and companion static audit.
  It is not a full external-event replay adapter for every runtime packet path.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DECISION_REQUEST_OFFICER = "request_officer_model_miss_analysis"
DECISION_PROCEED_REPAIR = "proceed_with_model_backed_repair"
DECISION_OUT_OF_SCOPE = "out_of_scope_not_modelable"
DECISION_NEEDS_EVIDENCE = "needs_evidence_before_modeling"
DECISION_STOP_FOR_USER = "stop_for_user"

REPAIR_AUTHORIZING_DECISIONS = frozenset(
    {
        DECISION_PROCEED_REPAIR,
        DECISION_OUT_OF_SCOPE,
    }
)
NONTERMINAL_HANDOFF_DECISIONS = frozenset(
    {
        DECISION_REQUEST_OFFICER,
        DECISION_NEEDS_EVIDENCE,
        DECISION_STOP_FOR_USER,
    }
)
PM_REQUEST_TARGET_ROLES = frozenset(
    {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
        "worker_a",
        "worker_b",
    }
)
CONTRACT_MODEL_MISS = "flowpilot.output_contract.flowguard_model_miss_report.v1"
CONTRACT_WORKER_RESEARCH = "flowpilot.output_contract.worker_research_result.v1"
CONTRACT_REVIEW = "flowpilot.output_contract.reviewer_review_report.v1"


@dataclass(frozen=True)
class Tick:
    """One router/controller decision-liveness tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    holder: str = "none"  # none | controller | pm | role | user

    pm_decision_context_open: bool = False
    pm_work_request_channel_available: bool = False
    controller_spawned_work_without_pm_request: bool = False
    controller_read_sealed_body: bool = False

    decision: str = "none"
    decision_recorded: bool = False
    next_channel_opened: bool = False
    same_event_wait_materialized: bool = False
    pm_decision_required_blocker_written: bool = False

    request_id: str = "none"
    duplicate_open_request_id: bool = False
    request_registered: bool = False
    request_recipient_role: str = "none"
    request_output_contract_id: str = "none"
    request_mode: str = "none"  # none | blocking | advisory
    request_kind: str = "none"  # none | model_miss | evidence | review | implementation
    request_status: str = "none"  # none | open | returned | absorbed | canceled | superseded
    request_marked_as_generic_channel: bool = False

    request_packet_created: bool = False
    request_packet_relayed: bool = False
    result_returned: bool = False
    result_request_id_matches: bool = False
    result_from_expected_role: bool = False
    result_ledger_checked: bool = False
    result_routed_to_pm: bool = False
    pm_absorbed_result: bool = False

    model_miss_triage_closed: bool = False
    repair_authorized: bool = False
    repair_packet_opened: bool = False
    dependent_pm_final_decision_recorded: bool = False
    controlled_user_stop_recorded: bool = False
    terminal_closure_recorded: bool = False
    prior_advisory_round_absorbed: bool = False
    supporting_role_result_absorbed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class DecisionLivenessStep:
    """Model one accepted decision or PM role-work-request transition.

    Input x State -> Set(Output x State)
    reads: PM decision context, PM work-request channel, request ledger,
    packet/result relay state, PM absorption, repair/stop/terminal state
    writes: one PM decision, one PM request fact, one packet/result relay fact,
    one absorption/cancel/supersede fact, repair opening, controlled stop, or
    terminal status
    idempotency: repeat ticks observe existing request state and add at most one
    missing fact.
    """

    name = "DecisionLivenessStep"
    reads = (
        "pm_decision_context",
        "pm_work_request_channel",
        "decision_value",
        "request_ledger",
        "packet_ledger",
        "result_envelope",
        "pm_absorption",
        "repair_authorization",
        "controlled_stop",
    )
    writes = (
        "decision_record",
        "request_record",
        "packet_handoff",
        "packet_ledger_check",
        "pm_absorption_record",
        "terminal_status",
    )
    input_description = "PM decision or role-work-request liveness tick"
    output_description = "one abstract FlowPilot PM-decision or request action"
    idempotency = "repeat ticks do not duplicate decisions, requests, reports, or packets"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _register_pm_work_request(
    state: State,
    *,
    label: str,
    request_id: str,
    recipient: str,
    contract: str,
    mode: str,
    kind: str,
    decision: str | None = None,
) -> Transition:
    return Transition(
        label,
        replace(
            state,
            holder="pm",
            decision=decision if decision is not None else state.decision,
            decision_recorded=True if decision is not None else state.decision_recorded,
            next_channel_opened=True,
            request_id=request_id,
            request_registered=True,
            request_recipient_role=recipient,
            request_output_contract_id=contract,
            request_mode=mode,
            request_kind=kind,
            request_status="open",
            request_marked_as_generic_channel=True,
        ),
    )


def _clear_absorbed_request(state: State, **changes: object) -> State:
    return replace(
        state,
        request_id="none",
        duplicate_open_request_id=False,
        request_registered=False,
        request_recipient_role="none",
        request_output_contract_id="none",
        request_mode="none",
        request_kind="none",
        request_status="none",
        request_marked_as_generic_channel=False,
        request_packet_created=False,
        request_packet_relayed=False,
        result_returned=False,
        result_request_id_matches=False,
        result_from_expected_role=False,
        result_ledger_checked=False,
        result_routed_to_pm=False,
        pm_absorbed_result=False,
        **changes,
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if not state.pm_decision_context_open:
        yield Transition(
            "pm_decision_context_opened_with_always_available_work_request_channel",
            replace(
                state,
                status="running",
                holder="pm",
                pm_decision_context_open=True,
                pm_work_request_channel_available=True,
            ),
        )
        return

    if state.request_registered and state.request_status == "open":
        if not state.request_packet_created:
            yield Transition(
                "pm_role_work_request_packet_created",
                replace(state, holder="controller", request_packet_created=True),
            )
            return
        if not state.request_packet_relayed:
            yield Transition(
                "pm_role_work_request_packet_relayed_to_role",
                replace(state, holder="role", request_packet_relayed=True),
            )
            return
        if not state.result_returned:
            yield Transition(
                "role_work_result_returned_to_packet_ledger",
                replace(
                    state,
                    holder="controller",
                    result_returned=True,
                    result_request_id_matches=True,
                    result_from_expected_role=True,
                    request_status="returned",
                ),
            )
            return

    if state.request_registered and state.request_status == "returned":
        if not state.result_ledger_checked:
            yield Transition(
                "role_work_result_ledger_checked_before_pm_relay",
                replace(state, holder="controller", result_ledger_checked=True),
            )
            return
        if not state.result_routed_to_pm:
            yield Transition(
                "role_work_result_routed_to_pm_after_ledger_check",
                replace(state, holder="pm", result_routed_to_pm=True),
            )
            return
        if not state.pm_absorbed_result:
            yield Transition(
                "pm_absorbs_role_work_result_before_dependent_decision",
                replace(
                    state,
                    holder="pm",
                    pm_absorbed_result=True,
                    request_status="absorbed",
                ),
            )
            return

    if state.request_registered and state.request_status == "absorbed":
        if state.decision == DECISION_REQUEST_OFFICER and not state.repair_authorized:
            yield Transition(
                "pm_authorizes_model_backed_repair_after_generic_officer_result",
                _clear_absorbed_request(
                    state,
                    holder="pm",
                    decision=DECISION_PROCEED_REPAIR,
                    decision_recorded=True,
                    model_miss_triage_closed=True,
                    repair_authorized=True,
                    supporting_role_result_absorbed=True,
                ),
            )
            return
        if state.decision == DECISION_NEEDS_EVIDENCE:
            yield Transition(
                "pm_reopens_triage_after_absorbing_evidence_request",
                _clear_absorbed_request(
                    state,
                    holder="pm",
                    decision="none",
                    decision_recorded=False,
                    next_channel_opened=False,
                    prior_advisory_round_absorbed=True,
                ),
            )
            return
        if state.decision == "none":
            yield Transition(
                "pm_continues_decision_after_absorbing_advisory_request",
                _clear_absorbed_request(
                    state,
                    holder="pm",
                    prior_advisory_round_absorbed=True,
                ),
            )
            return

    if state.repair_authorized:
        if not state.repair_packet_opened:
            yield Transition(
                "repair_packet_opened_after_closed_model_miss_triage",
                replace(state, holder="pm", repair_packet_opened=True),
            )
            return
        if not state.terminal_closure_recorded:
            yield Transition(
                "terminal_closure_after_resolved_pm_requests",
                replace(state, holder="pm", terminal_closure_recorded=True),
            )
            return
        yield Transition(
            "decision_liveness_complete",
            replace(state, status="complete", holder="pm"),
        )
        return

    if state.decision == "none" and not state.request_registered:
        if not state.prior_advisory_round_absorbed:
            yield _register_pm_work_request(
                state,
                label="pm_opens_advisory_role_work_request_before_final_decision",
                request_id="pm-advisory-001",
                recipient="human_like_reviewer",
                contract=CONTRACT_REVIEW,
                mode="advisory",
                kind="review",
            )
        yield _register_pm_work_request(
            state,
            label="pm_requests_model_miss_officer_analysis_via_generic_work_request",
            request_id="pm-model-miss-001",
            recipient="product_flowguard_officer",
            contract=CONTRACT_MODEL_MISS,
            mode="blocking",
            kind="model_miss",
            decision=DECISION_REQUEST_OFFICER,
        )
        yield _register_pm_work_request(
            state,
            label="pm_requests_evidence_before_modeling_via_generic_work_request",
            request_id="pm-evidence-001",
            recipient="worker_a",
            contract=CONTRACT_WORKER_RESEARCH,
            mode="blocking",
            kind="evidence",
            decision=DECISION_NEEDS_EVIDENCE,
        )
        yield Transition(
            "pm_records_controlled_stop_for_user",
            replace(
                state,
                holder="pm",
                decision=DECISION_STOP_FOR_USER,
                decision_recorded=True,
                next_channel_opened=True,
            ),
        )
        yield Transition(
            "pm_records_out_of_scope_model_miss_decision",
            replace(
                state,
                holder="pm",
                decision=DECISION_OUT_OF_SCOPE,
                decision_recorded=True,
                next_channel_opened=True,
                model_miss_triage_closed=True,
                repair_authorized=True,
            ),
        )
        return

    if state.decision == DECISION_STOP_FOR_USER:
        if not state.controlled_user_stop_recorded:
            yield Transition(
                "controlled_user_stop_recorded_after_pm_stop_decision",
                replace(state, holder="user", controlled_user_stop_recorded=True),
            )
            return
        yield Transition(
            "decision_liveness_paused_for_user",
            replace(state, status="blocked", holder="user"),
        )
        return


def _request_has_valid_recipient(state: State) -> bool:
    return state.request_recipient_role in PM_REQUEST_TARGET_ROLES


def _request_has_contract(state: State) -> bool:
    return state.request_output_contract_id != "none"


def _request_unresolved(state: State) -> bool:
    return state.request_registered and state.request_status in {"open", "returned"}


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed PM work-request or result body")
    if state.controller_spawned_work_without_pm_request:
        failures.append("Controller spawned role work without a PM work request")
    if state.pm_decision_context_open and not state.pm_work_request_channel_available:
        failures.append("PM decision context opened without always-available role-work-request channel")
    if state.request_registered and not state.pm_work_request_channel_available:
        failures.append("PM work request registered while work-request channel was unavailable")
    if state.request_registered and not state.pm_decision_context_open:
        failures.append("PM work request registered outside a PM decision context")
    if state.request_registered and state.request_id == "none":
        failures.append("PM work request registered without request_id")
    if state.duplicate_open_request_id:
        failures.append("duplicate open PM work request id would overwrite request ledger state")
    if state.request_registered and not _request_has_valid_recipient(state):
        failures.append("PM work request registered without a valid recipient role")
    if state.request_registered and not _request_has_contract(state):
        failures.append("PM work request registered without an output contract")
    if state.request_registered and state.request_mode not in {"blocking", "advisory"}:
        failures.append("PM work request registered without blocking/advisory mode")
    if state.request_registered and not state.request_marked_as_generic_channel:
        failures.append("PM role work was special-cased instead of using the generic request channel")

    if state.decision_recorded and not state.pm_decision_context_open:
        failures.append("PM decision recorded outside a PM decision context")
    if state.decision in NONTERMINAL_HANDOFF_DECISIONS and not state.next_channel_opened:
        failures.append("accepted nonterminal PM decision has no next route channel")
    if state.decision in NONTERMINAL_HANDOFF_DECISIONS and state.same_event_wait_materialized:
        failures.append("accepted nonterminal PM decision looped back to same PM event instead of opening next channel")
    if (
        state.decision in NONTERMINAL_HANDOFF_DECISIONS
        and state.pm_decision_required_blocker_written
    ):
        failures.append("accepted nonterminal PM decision materialized as a PM blocker instead of a role/user handoff")
    if state.decision in {DECISION_REQUEST_OFFICER, DECISION_NEEDS_EVIDENCE} and not (
        state.request_registered or state.request_status == "absorbed" or state.repair_authorized
    ):
        failures.append("PM information-gathering decision did not use the generic role-work-request channel")
    if state.decision == DECISION_STOP_FOR_USER and state.request_registered:
        failures.append("stop_for_user incorrectly opened role work instead of controlled pause")

    if state.request_packet_created and not state.request_registered:
        failures.append("PM work request packet created before request registration")
    if state.request_packet_relayed and not state.request_packet_created:
        failures.append("PM work request packet relayed before packet creation")
    if state.result_returned and not state.request_packet_relayed:
        failures.append("role work result returned before request packet relay")
    if state.result_returned and not state.result_request_id_matches:
        failures.append("role work result returned for the wrong PM request id")
    if state.result_returned and not state.result_from_expected_role:
        failures.append("role work result returned from the wrong recipient role")
    if state.result_ledger_checked and not state.result_returned:
        failures.append("role work result ledger checked before result return")
    if state.result_routed_to_pm and not state.result_ledger_checked:
        failures.append("role work result routed to PM before packet-ledger check")
    if state.pm_absorbed_result and not state.result_routed_to_pm:
        failures.append("PM absorbed role work result before result relay")
    if state.request_status == "absorbed" and not state.pm_absorbed_result:
        failures.append("PM work request marked absorbed before PM absorption")

    if (
        state.request_registered
        and state.request_mode == "blocking"
        and state.dependent_pm_final_decision_recorded
        and state.request_status != "absorbed"
    ):
        failures.append("PM recorded dependent final decision while blocking role work request was unresolved")
    if (
        state.terminal_closure_recorded
        and state.request_registered
        and state.request_mode == "advisory"
        and state.request_status not in {"absorbed", "canceled", "superseded"}
    ):
        failures.append("terminal closure recorded with unresolved advisory role work request")
    if state.model_miss_triage_closed and state.decision not in REPAIR_AUTHORIZING_DECISIONS:
        failures.append("non-authorizing model-miss decision closed repair triage")
    if (
        state.decision == DECISION_PROCEED_REPAIR
        and state.repair_authorized
        and not state.supporting_role_result_absorbed
    ):
        failures.append("model-backed repair authorized before PM reviewed supporting role work result")
    if state.repair_packet_opened and not state.model_miss_triage_closed:
        failures.append("repair packet opened before model-miss triage closed")
    if state.repair_packet_opened and not state.repair_authorized:
        failures.append("repair packet opened before PM repair authorization")
    if state.terminal_closure_recorded and _request_unresolved(state):
        failures.append("terminal closure recorded while PM work request was unresolved")
    if state.status == "complete" and not state.terminal_closure_recorded:
        failures.append("decision liveness completed before terminal closure record")

    return failures


def decision_liveness_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_pm_role_work_request_liveness",
        description=(
            "PM decision contexts keep a generic role-work-request channel open; "
            "accepted nonterminal PM decisions must open a role/user handoff; "
            "PM work requests require id, recipient, output contract, request "
            "mode, packet/result ledger checks, and PM absorption before dependent "
            "decisions; Controller remains envelope-only."
        ),
        predicate=decision_liveness_invariant,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 50


def build_workflow() -> Workflow:
    return Workflow((DecisionLivenessStep(),), name="flowpilot_pm_role_work_request_liveness")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _open_pm_context(**changes: object) -> State:
    base = State(
        status="running",
        holder="pm",
        pm_decision_context_open=True,
        pm_work_request_channel_available=True,
    )
    return replace(base, **changes)


def _valid_open_request(**changes: object) -> State:
    base = _open_pm_context(
        decision=DECISION_REQUEST_OFFICER,
        decision_recorded=True,
        next_channel_opened=True,
        request_id="pm-model-miss-001",
        request_registered=True,
        request_recipient_role="product_flowguard_officer",
        request_output_contract_id=CONTRACT_MODEL_MISS,
        request_mode="blocking",
        request_kind="model_miss",
        request_status="open",
        request_marked_as_generic_channel=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "request_officer_decision_dead_ends_on_same_pm_event": _open_pm_context(
            decision=DECISION_REQUEST_OFFICER,
            decision_recorded=True,
            same_event_wait_materialized=True,
            pm_decision_required_blocker_written=True,
        ),
        "needs_evidence_decision_dead_ends_on_same_pm_event": _open_pm_context(
            decision=DECISION_NEEDS_EVIDENCE,
            decision_recorded=True,
            same_event_wait_materialized=True,
            pm_decision_required_blocker_written=True,
        ),
        "stop_for_user_decision_dead_ends_on_same_pm_event": _open_pm_context(
            decision=DECISION_STOP_FOR_USER,
            decision_recorded=True,
            same_event_wait_materialized=True,
            pm_decision_required_blocker_written=True,
        ),
        "pm_context_without_work_request_channel": _open_pm_context(
            pm_work_request_channel_available=False,
        ),
        "pm_work_request_without_recipient": _valid_open_request(
            request_recipient_role="none",
        ),
        "pm_work_request_without_output_contract": _valid_open_request(
            request_output_contract_id="none",
        ),
        "duplicate_open_pm_work_request_id": _valid_open_request(
            duplicate_open_request_id=True,
        ),
        "controller_spawned_work_without_pm_request": _open_pm_context(
            controller_spawned_work_without_pm_request=True,
        ),
        "controller_reads_pm_work_request_body": _valid_open_request(
            controller_read_sealed_body=True,
        ),
        "pm_work_request_special_cased_outside_generic_channel": _valid_open_request(
            request_marked_as_generic_channel=False,
        ),
        "blocking_request_ignored_by_pm_final_decision": _valid_open_request(
            dependent_pm_final_decision_recorded=True,
        ),
        "advisory_result_unresolved_at_terminal_closure": _open_pm_context(
            request_id="pm-advisory-001",
            request_registered=True,
            request_recipient_role="human_like_reviewer",
            request_output_contract_id=CONTRACT_REVIEW,
            request_mode="advisory",
            request_kind="review",
            request_status="returned",
            request_marked_as_generic_channel=True,
            result_returned=True,
            result_request_id_matches=True,
            result_from_expected_role=True,
            result_ledger_checked=True,
            result_routed_to_pm=True,
            terminal_closure_recorded=True,
        ),
        "role_work_result_routed_without_ledger_check": _valid_open_request(
            request_packet_created=True,
            request_packet_relayed=True,
            result_returned=True,
            result_request_id_matches=True,
            result_from_expected_role=True,
            request_status="returned",
            result_routed_to_pm=True,
            result_ledger_checked=False,
        ),
        "role_work_result_wrong_request_id": _valid_open_request(
            request_packet_created=True,
            request_packet_relayed=True,
            result_returned=True,
            result_request_id_matches=False,
            result_from_expected_role=True,
            request_status="returned",
        ),
        "role_work_result_wrong_role": _valid_open_request(
            request_packet_created=True,
            request_packet_relayed=True,
            result_returned=True,
            result_request_id_matches=True,
            result_from_expected_role=False,
            request_status="returned",
        ),
        "model_backed_repair_without_supporting_role_result": _open_pm_context(
            decision=DECISION_PROCEED_REPAIR,
            decision_recorded=True,
            next_channel_opened=True,
            model_miss_triage_closed=True,
            repair_authorized=True,
            repair_packet_opened=True,
        ),
        "repair_packet_opened_after_unclosed_triage": _valid_open_request(
            repair_packet_opened=True,
            repair_authorized=False,
            model_miss_triage_closed=False,
        ),
    }


__all__ = [
    "CONTRACT_MODEL_MISS",
    "CONTRACT_REVIEW",
    "CONTRACT_WORKER_RESEARCH",
    "DECISION_NEEDS_EVIDENCE",
    "DECISION_OUT_OF_SCOPE",
    "DECISION_PROCEED_REPAIR",
    "DECISION_REQUEST_OFFICER",
    "DECISION_STOP_FOR_USER",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "DecisionLivenessStep",
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
]
