"""FlowGuard model for FlowPilot startup-control handoffs.

Risk intent brief:
- Prevent the assistant from applying interpreted startup answers until a
  receipt has been reviewed against the user's actual text.
- Protect router apply calls from payload-free actions.
- Make the reviewer startup fact report a real pass/block gate before work
  beyond startup.
- Keep router repair packets sealed and addressed to the responsible role while
  Controller sees only envelope metadata.
- Ensure a formal user stop or cancel signal is terminal for future next
  actions.

Modeled state writes: startup questions, user text, answer receipt, receipt
review, pending action payload contract, action apply, reviewer fact report,
PM startup release, next action, router error, sealed repair packet, repair
result, and formal lifecycle stop/cancel.

Blindspot: this is an abstract control-plane model. It does not inspect the
current router implementation and should be paired with runtime conformance
tests before claiming production behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


RESPONSIBLE_REPAIR_ROLES = frozenset(
    {"project_manager", "human_like_reviewer", "worker_a", "worker_b"}
)

REQUIRED_LABELS = (
    "startup_questions_asked",
    "startup_user_text_recorded",
    "formal_user_stop_recorded",
    "formal_user_cancel_recorded",
    "ai_startup_answer_interpretation_receipt_written",
    "reviewer_receipt_reviewed_against_user_text",
    "reviewer_receipt_blocks_mismatch_against_user_text",
    "router_issues_startup_apply_action_with_payload_contract",
    "controller_applies_startup_action_after_payload_contract",
    "reviewer_startup_fact_report_blocks",
    "reviewer_startup_fact_report_passes",
    "pm_allows_work_beyond_startup_from_pass_report",
    "router_issues_next_action_after_startup_pass",
    "next_action_completes_without_router_error",
    "router_error_detected_for_next_action",
    "router_routes_sealed_repair_packet_to_responsible_role",
    "responsible_role_returns_repair_result_without_controller_body_access",
    "router_recovers_after_responsible_repair",
)


@dataclass(frozen=True)
class Tick:
    """One router/controller startup-control tick."""


@dataclass(frozen=True)
class Action:
    name: str
    recipient: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | awaiting_user | running | blocked | stopped | cancelled | complete
    holder: str = "controller"

    startup_questions_asked: bool = False
    waiting_for_user_text: bool = False
    user_text_recorded: bool = False

    formal_lifecycle_signal: str = "none"  # none | stop | cancel
    future_actions_prevented: bool = False
    action_issued_after_lifecycle_signal: bool = False

    interpretation_receipt_written: bool = False
    receipt_reviewed_against_user_text: bool = False
    receipt_matches_user_text: bool = False

    pending_action_type: str = "none"
    payload_contract_exists: bool = False
    startup_action_applied: bool = False

    startup_fact_report_status: str = "none"  # none | pass | block
    startup_fact_report_file_backed: bool = False
    work_beyond_startup_allowed: bool = False
    next_action_issued: bool = False

    router_error_seen: bool = False
    repair_packet_registered: bool = False
    repair_packet_sealed: bool = False
    repair_packet_responsible_role: str = "none"
    repair_packet_recipient: str = "none"
    repair_packet_routed_to_role: bool = False
    controller_knows_repair_details: bool = False
    controller_relayed_repair_details: bool = False

    repair_result_returned_to_router: bool = False
    repair_result_body_read_by_controller: bool = False
    router_recovered_after_repair: bool = False


class Transition(NamedTuple):
    label: str
    recipient: str
    state: State


def initial_state() -> State:
    return State()


class StartupControlStep:
    """Model one startup-control transition.

    Input x State -> Set(Output x State)
    reads: user startup text, answer receipt review, payload contract,
    reviewer fact report, PM startup release, router error lane, lifecycle stop
    writes: one startup-control action, report status, next action, sealed
    repair packet, repair result, or terminal lifecycle marker
    idempotency: repeat ticks observe completed facts and cannot duplicate
    action applies, repair packet delivery, or lifecycle terminal actions.
    """

    name = "StartupControlStep"
    reads = (
        "startup_user_text",
        "answer_interpretation_receipt",
        "payload_contract",
        "reviewer_fact_report",
        "pm_startup_release",
        "router_error_lane",
        "formal_lifecycle_signal",
    )
    writes = (
        "startup_receipt",
        "payload_contract",
        "startup_apply",
        "reviewer_fact_report",
        "pm_release",
        "next_action",
        "sealed_repair_packet",
        "formal_lifecycle_terminal",
    )
    input_description = "one controller tick in FlowPilot startup control"
    output_description = "one legal startup-control action"
    idempotency = "completed startup, repair, and stop/cancel facts are not duplicated"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label, transition.recipient),
                new_state=transition.state,
                label=transition.label,
            )


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "stopped", "cancelled", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _formal_lifecycle_transitions(state: State) -> tuple[Transition, ...]:
    if state.formal_lifecycle_signal != "none":
        return ()
    if state.status not in {"awaiting_user", "running"}:
        return ()
    return (
        Transition(
            "formal_user_stop_recorded",
            "controller",
            replace(
                state,
                status="stopped",
                holder="controller",
                formal_lifecycle_signal="stop",
                waiting_for_user_text=False,
                future_actions_prevented=True,
            ),
        ),
        Transition(
            "formal_user_cancel_recorded",
            "controller",
            replace(
                state,
                status="cancelled",
                holder="controller",
                formal_lifecycle_signal="cancel",
                waiting_for_user_text=False,
                future_actions_prevented=True,
            ),
        ),
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if is_terminal(state):
        return ()

    if invariant_failures(state):
        return (
            Transition(
                "blocked_on_startup_control_invariant",
                "controller",
                replace(state, status="blocked", holder="controller"),
            ),
        )

    lifecycle = _formal_lifecycle_transitions(state)

    if not state.startup_questions_asked:
        return (
            Transition(
                "startup_questions_asked",
                "user",
                replace(
                    state,
                    status="awaiting_user",
                    holder="user",
                    startup_questions_asked=True,
                    waiting_for_user_text=True,
                ),
            ),
        )

    if state.waiting_for_user_text and not state.user_text_recorded:
        return lifecycle + (
            Transition(
                "startup_user_text_recorded",
                "controller",
                replace(
                    state,
                    status="running",
                    holder="controller",
                    waiting_for_user_text=False,
                    user_text_recorded=True,
                ),
            ),
        )

    if not state.interpretation_receipt_written:
        return lifecycle + (
            Transition(
                "ai_startup_answer_interpretation_receipt_written",
                "human_like_reviewer",
                replace(
                    state,
                    holder="human_like_reviewer",
                    interpretation_receipt_written=True,
                ),
            ),
        )

    if not state.receipt_reviewed_against_user_text:
        return lifecycle + (
            Transition(
                "reviewer_receipt_reviewed_against_user_text",
                "controller",
                replace(
                    state,
                    holder="controller",
                    receipt_reviewed_against_user_text=True,
                    receipt_matches_user_text=True,
                ),
            ),
            Transition(
                "reviewer_receipt_blocks_mismatch_against_user_text",
                "controller",
                replace(
                    state,
                    status="blocked",
                    holder="controller",
                    receipt_reviewed_against_user_text=True,
                    receipt_matches_user_text=False,
                ),
            ),
        )

    if state.pending_action_type == "none":
        return lifecycle + (
            Transition(
                "router_issues_startup_apply_action_with_payload_contract",
                "controller",
                replace(
                    state,
                    holder="controller",
                    pending_action_type="apply_startup_answers",
                    payload_contract_exists=True,
                ),
            ),
        )

    if not state.startup_action_applied:
        return lifecycle + (
            Transition(
                "controller_applies_startup_action_after_payload_contract",
                "human_like_reviewer",
                replace(state, holder="human_like_reviewer", startup_action_applied=True),
            ),
        )

    if state.startup_fact_report_status == "none":
        return lifecycle + (
            Transition(
                "reviewer_startup_fact_report_blocks",
                "project_manager",
                replace(
                    state,
                    status="blocked",
                    holder="project_manager",
                    startup_fact_report_status="block",
                    startup_fact_report_file_backed=True,
                ),
            ),
            Transition(
                "reviewer_startup_fact_report_passes",
                "project_manager",
                replace(
                    state,
                    holder="project_manager",
                    startup_fact_report_status="pass",
                    startup_fact_report_file_backed=True,
                ),
            ),
        )

    if not state.work_beyond_startup_allowed:
        return lifecycle + (
            Transition(
                "pm_allows_work_beyond_startup_from_pass_report",
                "controller",
                replace(state, holder="controller", work_beyond_startup_allowed=True),
            ),
        )

    if not state.next_action_issued:
        return lifecycle + (
            Transition(
                "router_issues_next_action_after_startup_pass",
                "controller",
                replace(state, holder="controller", next_action_issued=True),
            ),
        )

    if not state.router_error_seen and not state.router_recovered_after_repair:
        return lifecycle + (
            Transition(
                "next_action_completes_without_router_error",
                "project_manager",
                replace(state, status="complete", holder="project_manager"),
            ),
            Transition(
                "router_error_detected_for_next_action",
                "router",
                replace(state, holder="router", router_error_seen=True),
            ),
        )

    if state.router_error_seen and not state.repair_packet_routed_to_role:
        return lifecycle + (
            Transition(
                "router_routes_sealed_repair_packet_to_responsible_role",
                "worker_a",
                replace(
                    state,
                    holder="worker_a",
                    repair_packet_registered=True,
                    repair_packet_sealed=True,
                    repair_packet_responsible_role="worker_a",
                    repair_packet_recipient="worker_a",
                    repair_packet_routed_to_role=True,
                ),
            ),
        )

    if state.repair_packet_routed_to_role and not state.repair_result_returned_to_router:
        return lifecycle + (
            Transition(
                "responsible_role_returns_repair_result_without_controller_body_access",
                "router",
                replace(state, holder="router", repair_result_returned_to_router=True),
            ),
        )

    if state.repair_result_returned_to_router and not state.router_recovered_after_repair:
        return lifecycle + (
            Transition(
                "router_recovers_after_responsible_repair",
                "project_manager",
                replace(
                    state,
                    status="complete",
                    holder="project_manager",
                    router_recovered_after_repair=True,
                ),
            ),
        )

    return lifecycle


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.user_text_recorded and not state.startup_questions_asked:
        failures.append("startup user text was recorded before startup questions were asked")
    if state.interpretation_receipt_written and not state.user_text_recorded:
        failures.append("AI startup answer interpretation receipt was written before user text was recorded")
    if state.receipt_reviewed_against_user_text and not state.interpretation_receipt_written:
        failures.append("startup answer interpretation receipt was reviewed before the receipt existed")
    if state.receipt_matches_user_text and not state.receipt_reviewed_against_user_text:
        failures.append("startup answer interpretation was treated as matching before review against user text")
    if state.pending_action_type != "none" and not (
        state.receipt_reviewed_against_user_text and state.receipt_matches_user_text
    ):
        failures.append("startup apply action was issued before answer receipt review matched user text")
    if state.payload_contract_exists and state.pending_action_type == "none":
        failures.append("payload contract exists without a pending action")
    if state.startup_action_applied and not state.payload_contract_exists:
        failures.append("startup action was applied before an action payload contract existed")
    if state.startup_action_applied and state.pending_action_type != "apply_startup_answers":
        failures.append("startup action apply used the wrong pending action type")
    if state.startup_action_applied and not (
        state.receipt_reviewed_against_user_text and state.receipt_matches_user_text
    ):
        failures.append("startup action was applied before reviewed answer receipt matched user text")
    if state.startup_fact_report_status in {"pass", "block"} and not state.startup_action_applied:
        failures.append("reviewer startup fact report was written before startup action apply")
    if state.startup_fact_report_status in {"pass", "block"} and not state.startup_fact_report_file_backed:
        failures.append("reviewer startup fact report was accepted without a file-backed report")
    if state.startup_fact_report_status not in {"none", "pass", "block"}:
        failures.append("reviewer startup fact report has an invalid status")
    if state.work_beyond_startup_allowed and not (
        state.startup_fact_report_status == "pass"
        and state.startup_fact_report_file_backed
    ):
        failures.append("work beyond startup was allowed without a passing file-backed reviewer fact report")
    if state.startup_fact_report_status == "block" and state.work_beyond_startup_allowed:
        failures.append("reviewer startup fact report blocked but work beyond startup was allowed")
    if state.next_action_issued and not state.work_beyond_startup_allowed:
        failures.append("next action was issued before PM allowed work beyond startup")

    if state.formal_lifecycle_signal in {"stop", "cancel"}:
        if state.status not in {"stopped", "cancelled"}:
            failures.append("formal user stop/cancel did not move startup control to a terminal lifecycle state")
        if not state.future_actions_prevented:
            failures.append("formal user stop/cancel did not record future-action prevention")
        if state.action_issued_after_lifecycle_signal:
            failures.append("formal user stop/cancel did not prevent further next actions")
    if state.formal_lifecycle_signal == "stop" and state.status != "stopped":
        failures.append("formal user stop signal did not end in stopped status")
    if state.formal_lifecycle_signal == "cancel" and state.status != "cancelled":
        failures.append("formal user cancel signal did not end in cancelled status")

    if state.router_error_seen and not state.next_action_issued:
        failures.append("router error was recorded before any next action was issued")
    if state.repair_packet_registered and not state.router_error_seen:
        failures.append("repair packet was registered before a router error")
    if state.repair_packet_routed_to_role and not state.repair_packet_registered:
        failures.append("repair packet was routed before packet registration")
    if state.repair_packet_routed_to_role and not state.repair_packet_sealed:
        failures.append("router error repair packet was routed without being sealed")
    if state.repair_packet_routed_to_role and (
        state.repair_packet_responsible_role not in RESPONSIBLE_REPAIR_ROLES
        or state.repair_packet_recipient != state.repair_packet_responsible_role
    ):
        failures.append("router error repair packet was not routed to the responsible role")
    if state.repair_packet_recipient == "controller":
        failures.append("router error repair packet was routed to Controller instead of a responsible role")
    if state.controller_knows_repair_details:
        failures.append("Controller learned sealed router repair details")
    if state.controller_relayed_repair_details:
        failures.append("Controller relayed sealed router repair details")
    if state.repair_result_body_read_by_controller:
        failures.append("Controller read sealed router repair result body")
    if state.repair_result_returned_to_router and not state.repair_packet_routed_to_role:
        failures.append("repair result returned before sealed packet reached the responsible role")
    if state.router_recovered_after_repair and not state.repair_result_returned_to_router:
        failures.append("router recovered from error before responsible repair result returned")
    if state.status == "complete" and state.router_error_seen and not state.router_recovered_after_repair:
        failures.append("startup control completed after router error without responsible repair recovery")
    if state.status == "complete" and not state.next_action_issued:
        failures.append("startup control completed before a post-startup next action was issued")

    return failures


def startup_control_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_startup_control",
        description=(
            "Startup apply requires reviewed answer receipts and payload "
            "contracts; reviewer fact reports may pass or block; router repair "
            "packets stay sealed and go to the responsible role; formal user "
            "stop/cancel is terminal for future next actions."
        ),
        predicate=startup_control_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 18


def build_workflow() -> Workflow:
    return Workflow((StartupControlStep(),), name="flowpilot_startup_control")


def _ready_for_apply(**changes: object) -> State:
    base = State(
        status="running",
        holder="controller",
        startup_questions_asked=True,
        user_text_recorded=True,
        interpretation_receipt_written=True,
        receipt_reviewed_against_user_text=True,
        receipt_matches_user_text=True,
        pending_action_type="apply_startup_answers",
        payload_contract_exists=True,
    )
    return replace(base, **changes)


def _startup_passed(**changes: object) -> State:
    base = _ready_for_apply(
        startup_action_applied=True,
        startup_fact_report_status="pass",
        startup_fact_report_file_backed=True,
        work_beyond_startup_allowed=True,
        next_action_issued=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "apply_without_receipt_review": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            interpretation_receipt_written=True,
            pending_action_type="apply_startup_answers",
            payload_contract_exists=True,
            startup_action_applied=True,
        ),
        "apply_without_payload_contract": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            interpretation_receipt_written=True,
            receipt_reviewed_against_user_text=True,
            receipt_matches_user_text=True,
            pending_action_type="apply_startup_answers",
            startup_action_applied=True,
        ),
        "fact_report_pass_before_apply": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            interpretation_receipt_written=True,
            receipt_reviewed_against_user_text=True,
            receipt_matches_user_text=True,
            startup_fact_report_status="pass",
            startup_fact_report_file_backed=True,
        ),
        "blocking_fact_report_allows_work": _ready_for_apply(
            startup_action_applied=True,
            startup_fact_report_status="block",
            startup_fact_report_file_backed=True,
            work_beyond_startup_allowed=True,
        ),
        "next_action_after_stop": _startup_passed(
            status="stopped",
            formal_lifecycle_signal="stop",
            future_actions_prevented=True,
            action_issued_after_lifecycle_signal=True,
        ),
        "next_action_after_cancel": _startup_passed(
            status="cancelled",
            formal_lifecycle_signal="cancel",
            future_actions_prevented=True,
            action_issued_after_lifecycle_signal=True,
        ),
        "unsealed_repair_packet": _startup_passed(
            router_error_seen=True,
            repair_packet_registered=True,
            repair_packet_responsible_role="worker_a",
            repair_packet_recipient="worker_a",
            repair_packet_routed_to_role=True,
        ),
        "repair_packet_to_controller": _startup_passed(
            router_error_seen=True,
            repair_packet_registered=True,
            repair_packet_sealed=True,
            repair_packet_responsible_role="worker_a",
            repair_packet_recipient="controller",
            repair_packet_routed_to_role=True,
        ),
        "controller_knows_repair_details": _startup_passed(
            router_error_seen=True,
            repair_packet_registered=True,
            repair_packet_sealed=True,
            repair_packet_responsible_role="worker_a",
            repair_packet_recipient="worker_a",
            repair_packet_routed_to_role=True,
            controller_knows_repair_details=True,
        ),
        "router_error_complete_without_repair": _startup_passed(
            status="complete",
            router_error_seen=True,
        ),
    }


__all__ = [
    "Action",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "RESPONSIBLE_REPAIR_ROLES",
    "StartupControlStep",
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
]
