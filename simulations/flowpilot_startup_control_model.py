"""FlowGuard model for FlowPilot startup-control handoffs.

Risk intent brief:
- Prevent FlowPilot from requiring a reviewer to prove original chat
  authenticity when the runtime cannot expose an independent host receipt.
- Treat the router-accepted startup task contract as the internal authority
  for startup answers, while preserving aggressive reviewer checks for facts
  that are actually reachable through files, host receipts, tools, or UI.
- Treat router-computable mechanical facts as router-owned. The reviewer should
  not be required to re-prove router hashes, flags, event order, or proof-file
  existence before doing external/semantic review.
- Ensure every required startup fact has exactly one accountable lane:
  router-owned, reviewer-owned, or PM-owned unreviewable decision. Unowned
  facts fail the model even if duplicate review has been removed.
- Protect router apply calls from payload-free actions.
- Make the reviewer startup fact report produce either a pass or PM-addressed
  findings; PM owns repair, waiver/demotion, user escalation, or dead-end.
- Ensure the router writes and exposes startup mechanical audit/proof before
  reviewer fact reporting.
- Ensure startup findings are followed by a PM decision instead of a reviewer
  hard stop.
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
    "router_records_startup_task_contract",
    "startup_user_authenticity_gate_demoted_to_router_contract",
    "router_issues_startup_apply_action_with_payload_contract",
    "controller_applies_startup_action_after_payload_contract",
    "router_writes_startup_mechanical_audit_for_reviewer",
    "router_delivers_startup_mechanical_audit_to_reviewer",
    "router_accepts_mechanical_facts_without_reviewer_reproof",
    "router_assigns_all_startup_fact_review_owners",
    "reviewer_external_fact_review_preserves_aggressive_checks",
    "reviewer_reports_startup_findings_for_pm_decision",
    "reviewer_reports_unreviewable_requirement_for_pm_decision",
    "reviewer_startup_fact_report_passes",
    "pm_requests_startup_repair_for_findings",
    "pm_demotes_unreviewable_startup_requirement",
    "pm_waives_startup_findings_with_reason",
    "pm_declares_protocol_dead_end_for_unroutable_startup_findings",
    "pm_allows_work_beyond_startup_after_pass_or_pm_decision",
    "pm_material_scan_card_delivered_after_startup_activation",
    "pm_activates_route_after_startup_activation",
    "router_issues_next_action_after_startup_pass",
    "next_action_completes_without_router_error",
    "router_error_detected_for_next_action",
    "router_routes_sealed_repair_packet_to_responsible_role",
    "responsible_role_returns_repair_result_without_controller_body_access",
    "router_recovers_after_responsible_repair",
    "pm_closure_approved_before_heartbeat_removal",
    "heartbeat_removed_after_pm_closure",
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
    status: str = "new"  # new | awaiting_user | running | blocked | protocol_dead_end | stopped | cancelled | complete
    holder: str = "controller"

    startup_questions_asked: bool = False
    waiting_for_user_text: bool = False
    user_text_recorded: bool = False
    startup_task_contract_recorded: bool = False
    user_authenticity_gate_required: bool = False
    user_authenticity_gate_demoted: bool = False

    formal_lifecycle_signal: str = "none"  # none | stop | cancel
    future_actions_prevented: bool = False
    action_issued_after_lifecycle_signal: bool = False

    # Legacy receipt fields are retained as modeled hazards only. The current
    # design must not require reviewer proof of original user-chat authenticity.
    interpretation_receipt_written: bool = False
    receipt_reviewed_against_user_text: bool = False
    receipt_matches_user_text: bool = False

    pending_action_type: str = "none"
    payload_contract_exists: bool = False
    startup_action_applied: bool = False

    startup_fact_report_status: str = "none"  # none | pass | findings
    startup_fact_report_file_backed: bool = False
    startup_mechanical_audit_written: bool = False
    startup_mechanical_audit_proof_written: bool = False
    startup_mechanical_audit_delivered_to_reviewer: bool = False
    router_owned_mechanical_facts_enforced: bool = False
    startup_fact_report_references_current_audit: bool = False
    reviewer_required_to_reprove_router_owned_facts: bool = False
    all_startup_fact_review_owners_assigned: bool = False
    startup_fact_without_review_owner: bool = False
    reviewer_aggressive_external_checks_preserved: bool = False
    reviewer_finding_reason_kind: str = "none"  # none | reviewable_external_fact | unreviewable_requirement
    startup_repair_request_file_backed: bool = False
    startup_repair_request_targeted: bool = False
    pm_demoted_unreviewable_requirement: bool = False
    pm_startup_findings_waived: bool = False
    pm_startup_findings_waiver_file_backed: bool = False
    protocol_dead_end_declared: bool = False
    protocol_dead_end_file_backed: bool = False
    protocol_dead_end_has_no_repair_path: bool = False
    protocol_dead_end_pending_mail_suspended: bool = False
    work_beyond_startup_allowed: bool = False
    material_scan_card_delivered: bool = False
    active_route_exists: bool = False
    controller_product_work_started: bool = False
    next_action_issued: bool = False
    route_work_completed: bool = False
    pm_closure_approved: bool = False
    heartbeat_removed: bool = False
    stage_precondition_error_materialized_as_control_blocker: bool = False

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
    return state.status in {"blocked", "protocol_dead_end", "stopped", "cancelled", "complete"}


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

    if not state.startup_task_contract_recorded:
        return lifecycle + (
            Transition(
                "router_records_startup_task_contract",
                "controller",
                replace(
                    state,
                    holder="controller",
                    startup_task_contract_recorded=True,
                ),
            ),
        )

    if not state.user_authenticity_gate_demoted:
        return lifecycle + (
            Transition(
                "startup_user_authenticity_gate_demoted_to_router_contract",
                "controller",
                replace(
                    state,
                    holder="controller",
                    user_authenticity_gate_demoted=True,
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

    if not (
        state.startup_mechanical_audit_written
        and state.startup_mechanical_audit_proof_written
    ):
        return lifecycle + (
            Transition(
                "router_writes_startup_mechanical_audit_for_reviewer",
                "controller",
                replace(
                    state,
                    holder="controller",
                    startup_mechanical_audit_written=True,
                    startup_mechanical_audit_proof_written=True,
                ),
            ),
        )

    if not state.startup_mechanical_audit_delivered_to_reviewer:
        return lifecycle + (
            Transition(
                "router_delivers_startup_mechanical_audit_to_reviewer",
                "human_like_reviewer",
                replace(
                    state,
                    holder="human_like_reviewer",
                    startup_mechanical_audit_delivered_to_reviewer=True,
                ),
            ),
        )

    if not state.router_owned_mechanical_facts_enforced:
        return lifecycle + (
            Transition(
                "router_accepts_mechanical_facts_without_reviewer_reproof",
                "controller",
                replace(state, holder="controller", router_owned_mechanical_facts_enforced=True),
            ),
        )

    if not state.all_startup_fact_review_owners_assigned:
        return lifecycle + (
            Transition(
                "router_assigns_all_startup_fact_review_owners",
                "controller",
                replace(state, holder="controller", all_startup_fact_review_owners_assigned=True),
            ),
        )

    if state.startup_fact_report_status == "none":
        return lifecycle + (
            Transition(
                "reviewer_external_fact_review_preserves_aggressive_checks",
                "human_like_reviewer",
                replace(
                    state,
                    holder="human_like_reviewer",
                    reviewer_aggressive_external_checks_preserved=True,
                ),
            ),
            Transition(
                "reviewer_reports_startup_findings_for_pm_decision",
                "project_manager",
                replace(
                    state,
                    holder="project_manager",
                    startup_fact_report_status="findings",
                    startup_fact_report_file_backed=True,
                    reviewer_aggressive_external_checks_preserved=True,
                    reviewer_finding_reason_kind="reviewable_external_fact",
                ),
            ),
            Transition(
                "reviewer_reports_unreviewable_requirement_for_pm_decision",
                "project_manager",
                replace(
                    state,
                    holder="project_manager",
                    startup_fact_report_status="findings",
                    startup_fact_report_file_backed=True,
                    reviewer_aggressive_external_checks_preserved=True,
                    reviewer_finding_reason_kind="unreviewable_requirement",
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
                    reviewer_aggressive_external_checks_preserved=True,
                ),
            ),
        )

    if state.startup_fact_report_status == "findings" and not state.pm_startup_findings_waived:
        if not state.startup_repair_request_file_backed:
            pm_options = [
                Transition(
                    "pm_requests_startup_repair_for_findings",
                    "router",
                    replace(
                        state,
                        holder="router",
                        startup_fact_report_status="none",
                        startup_fact_report_file_backed=False,
                        reviewer_finding_reason_kind="none",
                        startup_mechanical_audit_written=False,
                        startup_mechanical_audit_proof_written=False,
                        startup_mechanical_audit_delivered_to_reviewer=False,
                        startup_repair_request_file_backed=True,
                        startup_repair_request_targeted=True,
                    ),
                ),
                Transition(
                    "pm_waives_startup_findings_with_reason",
                    "controller",
                    replace(
                        state,
                        holder="controller",
                        pm_startup_findings_waived=True,
                        pm_startup_findings_waiver_file_backed=True,
                    ),
                ),
                Transition(
                    "pm_declares_protocol_dead_end_for_unroutable_startup_findings",
                    "controller",
                    replace(
                        state,
                        status="protocol_dead_end",
                        holder="controller",
                        protocol_dead_end_declared=True,
                        protocol_dead_end_file_backed=True,
                        protocol_dead_end_has_no_repair_path=True,
                        protocol_dead_end_pending_mail_suspended=True,
                        future_actions_prevented=True,
                    ),
                ),
            ]
            if state.reviewer_finding_reason_kind == "unreviewable_requirement":
                pm_options.insert(
                    1,
                    Transition(
                        "pm_demotes_unreviewable_startup_requirement",
                        "controller",
                        replace(
                            state,
                            holder="controller",
                            pm_demoted_unreviewable_requirement=True,
                            pm_startup_findings_waived=True,
                            pm_startup_findings_waiver_file_backed=True,
                        ),
                    ),
                )
            return lifecycle + tuple(pm_options)
        return lifecycle + (
            Transition(
                "pm_declares_protocol_dead_end_for_unroutable_startup_findings",
                "controller",
                replace(
                    state,
                    status="protocol_dead_end",
                    holder="controller",
                    protocol_dead_end_declared=True,
                    protocol_dead_end_file_backed=True,
                    protocol_dead_end_has_no_repair_path=True,
                    protocol_dead_end_pending_mail_suspended=True,
                    future_actions_prevented=True,
                ),
            ),
        )

    if not state.work_beyond_startup_allowed:
        return lifecycle + (
            Transition(
                "pm_allows_work_beyond_startup_after_pass_or_pm_decision",
                "controller",
                replace(state, holder="controller", work_beyond_startup_allowed=True),
            ),
        )

    if not state.material_scan_card_delivered:
        return lifecycle + (
            Transition(
                "pm_material_scan_card_delivered_after_startup_activation",
                "project_manager",
                replace(state, holder="project_manager", material_scan_card_delivered=True),
            ),
        )

    if not state.active_route_exists:
        return lifecycle + (
            Transition(
                "pm_activates_route_after_startup_activation",
                "project_manager",
                replace(state, holder="project_manager", active_route_exists=True),
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
                replace(state, holder="project_manager", route_work_completed=True),
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
                    holder="project_manager",
                    router_recovered_after_repair=True,
                    route_work_completed=True,
                ),
            ),
        )

    if state.route_work_completed and not state.pm_closure_approved:
        return lifecycle + (
            Transition(
                "pm_closure_approved_before_heartbeat_removal",
                "project_manager",
                replace(state, holder="project_manager", pm_closure_approved=True),
            ),
        )

    if state.pm_closure_approved and not state.heartbeat_removed:
        return lifecycle + (
            Transition(
                "heartbeat_removed_after_pm_closure",
                "controller",
                replace(state, status="complete", holder="controller", heartbeat_removed=True),
            ),
        )

    return lifecycle


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.user_text_recorded and not state.startup_questions_asked:
        failures.append("startup user text was recorded before startup questions were asked")
    if state.startup_task_contract_recorded and not state.user_text_recorded:
        failures.append("startup task contract was recorded before user startup text was recorded")
    if state.user_authenticity_gate_required:
        failures.append("reviewer was required to prove unreviewable user-chat authenticity")
    if state.reviewer_required_to_reprove_router_owned_facts or state.startup_fact_report_references_current_audit:
        failures.append("reviewer was required to re-prove router-computable startup facts")
    if state.startup_fact_without_review_owner or (
        state.startup_fact_report_status in {"pass", "findings"}
        and not state.all_startup_fact_review_owners_assigned
    ):
        failures.append("startup fact requirement had no router, reviewer, or PM decision owner")
    if state.stage_precondition_error_materialized_as_control_blocker:
        failures.append("normal event precondition failure was materialized as an active control blocker")
    if state.user_authenticity_gate_demoted and not state.startup_task_contract_recorded:
        failures.append("user authenticity gate was demoted before router recorded the startup task contract")
    if state.interpretation_receipt_written and not state.user_text_recorded:
        failures.append("AI startup answer interpretation receipt was written before user text was recorded")
    if state.receipt_reviewed_against_user_text or state.receipt_matches_user_text:
        failures.append("startup answer receipt review against original user text remained a hard reviewer gate")
    if state.pending_action_type != "none" and not (
        state.startup_task_contract_recorded and state.user_authenticity_gate_demoted
    ):
        failures.append("startup apply action was issued before router task contract authority was established")
    if state.payload_contract_exists and state.pending_action_type == "none":
        failures.append("payload contract exists without a pending action")
    if state.startup_action_applied and not state.payload_contract_exists:
        failures.append("startup action was applied before an action payload contract existed")
    if state.startup_action_applied and state.pending_action_type != "apply_startup_answers":
        failures.append("startup action apply used the wrong pending action type")
    if state.startup_action_applied and not (
        state.startup_task_contract_recorded and state.user_authenticity_gate_demoted
    ):
        failures.append("startup action was applied before router task contract authority was established")
    if state.startup_fact_report_status in {"pass", "findings"} and not state.startup_action_applied:
        failures.append("reviewer startup fact report was written before startup action apply")
    if state.startup_fact_report_status in {"pass", "findings"} and not state.startup_fact_report_file_backed:
        failures.append("reviewer startup fact report was accepted without a file-backed report")
    if state.startup_fact_report_status in {"pass", "findings"} and not (
        state.startup_mechanical_audit_written
        and state.startup_mechanical_audit_proof_written
        and state.startup_mechanical_audit_delivered_to_reviewer
        and state.router_owned_mechanical_facts_enforced
    ):
        failures.append("reviewer startup fact report was accepted without the current prewritten startup mechanical audit")
    if state.startup_fact_report_status in {"pass", "findings"} and not state.reviewer_aggressive_external_checks_preserved:
        failures.append("reviewer startup fact report did not preserve aggressive checks for reviewable external facts")
    if state.startup_fact_report_status not in {"none", "pass", "findings"}:
        failures.append("reviewer startup fact report has an invalid status")
    if state.work_beyond_startup_allowed and not (
        state.startup_fact_report_file_backed
        and (
            state.startup_fact_report_status == "pass"
            or (
                state.startup_fact_report_status == "findings"
                and state.pm_startup_findings_waived
                and state.pm_startup_findings_waiver_file_backed
            )
        )
    ):
        failures.append("work beyond startup was allowed without a passing report or file-backed PM findings decision")
    if (
        state.startup_fact_report_status == "findings"
        and state.work_beyond_startup_allowed
        and not (state.pm_startup_findings_waived and state.pm_startup_findings_waiver_file_backed)
    ):
        failures.append("reviewer findings allowed work without a PM repair/waiver/demotion decision")
    if (
        state.startup_fact_report_status == "findings"
        and state.holder != "project_manager"
        and state.status not in {"stopped", "cancelled"}
        and not (
        (
            state.startup_repair_request_file_backed
            and state.startup_repair_request_targeted
        )
        or (
            state.pm_startup_findings_waived
            and state.pm_startup_findings_waiver_file_backed
        )
        or (
            state.protocol_dead_end_declared
            and state.protocol_dead_end_file_backed
            and state.protocol_dead_end_has_no_repair_path
        )
        )
    ):
        failures.append("reviewer startup findings had no PM repair, waiver/demotion, or protocol dead-end decision")
    if state.pm_demoted_unreviewable_requirement and state.reviewer_finding_reason_kind != "unreviewable_requirement":
        failures.append("PM demoted a reviewer requirement that was not marked unreviewable")
    if state.pm_startup_findings_waived and not state.pm_startup_findings_waiver_file_backed:
        failures.append("PM startup findings waiver was not file-backed")
    if state.protocol_dead_end_declared and not (
        state.status == "protocol_dead_end"
        and state.protocol_dead_end_file_backed
        and state.protocol_dead_end_has_no_repair_path
        and state.protocol_dead_end_pending_mail_suspended
        and state.future_actions_prevented
    ):
        failures.append("protocol dead-end did not stop startup with a complete file-backed emergency record")
    if state.protocol_dead_end_declared and (
        state.work_beyond_startup_allowed
        or state.next_action_issued
        or state.material_scan_card_delivered
        or state.active_route_exists
        or state.route_work_completed
    ):
        failures.append("startup control issued further work after protocol dead-end")
    if state.material_scan_card_delivered and not state.work_beyond_startup_allowed:
        failures.append("material/product card was delivered before PM allowed work beyond startup")
    if state.active_route_exists and not (
        state.work_beyond_startup_allowed and state.material_scan_card_delivered
    ):
        failures.append("route was activated before startup activation and material scan entry")
    if state.controller_product_work_started and not state.active_route_exists:
        failures.append("Controller or outer thread started product work before an active route existed")
    if state.next_action_issued and not state.work_beyond_startup_allowed:
        failures.append("next action was issued before PM allowed work beyond startup")
    if state.next_action_issued and not state.active_route_exists:
        failures.append("next action was issued before PM activated a route")
    if state.route_work_completed and not state.next_action_issued:
        failures.append("route work completed before a router-authorized post-startup action")
    if state.pm_closure_approved and not state.route_work_completed:
        failures.append("PM closure was approved before route work completed")
    if state.heartbeat_removed and not state.pm_closure_approved:
        failures.append("heartbeat was removed before PM closure approval")

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
    if state.status == "complete" and not (
        state.route_work_completed
        and state.pm_closure_approved
        and state.heartbeat_removed
    ):
        failures.append("startup control completed before route work, PM closure, and heartbeat removal")

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
            "Startup apply requires router task-contract authority and payload "
            "contracts, without forcing reviewer proof of original chat "
            "authenticity; reviewer fact reports may pass or report findings on "
            "facts; router repair packets stay sealed and go to the responsible "
            "role; formal user stop/cancel is terminal for future next actions."
        ),
        predicate=startup_control_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 24


def build_workflow() -> Workflow:
    return Workflow((StartupControlStep(),), name="flowpilot_startup_control")


def _ready_for_apply(**changes: object) -> State:
    base = State(
        status="running",
        holder="controller",
        startup_questions_asked=True,
        user_text_recorded=True,
        startup_task_contract_recorded=True,
        user_authenticity_gate_demoted=True,
        pending_action_type="apply_startup_answers",
        payload_contract_exists=True,
    )
    return replace(base, **changes)


def _startup_passed(**changes: object) -> State:
    base = _ready_for_apply(
        startup_action_applied=True,
        startup_mechanical_audit_written=True,
        startup_mechanical_audit_proof_written=True,
        startup_mechanical_audit_delivered_to_reviewer=True,
        startup_fact_report_status="pass",
        startup_fact_report_file_backed=True,
        router_owned_mechanical_facts_enforced=True,
        all_startup_fact_review_owners_assigned=True,
        reviewer_aggressive_external_checks_preserved=True,
        work_beyond_startup_allowed=True,
        material_scan_card_delivered=True,
        active_route_exists=True,
        next_action_issued=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "apply_without_task_contract": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            pending_action_type="apply_startup_answers",
            payload_contract_exists=True,
            startup_action_applied=True,
        ),
        "apply_without_payload_contract": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            startup_task_contract_recorded=True,
            user_authenticity_gate_demoted=True,
            pending_action_type="apply_startup_answers",
            startup_action_applied=True,
        ),
        "fact_report_pass_before_apply": State(
            status="running",
            startup_questions_asked=True,
            user_text_recorded=True,
            startup_task_contract_recorded=True,
            user_authenticity_gate_demoted=True,
            startup_fact_report_status="pass",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
        ),
        "reviewer_user_authenticity_gate_required": _ready_for_apply(
            user_authenticity_gate_required=True,
        ),
        "reviewer_reproves_router_computable_startup_facts": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            startup_fact_report_status="pass",
            startup_fact_report_file_backed=True,
            startup_fact_report_references_current_audit=True,
            reviewer_required_to_reprove_router_owned_facts=True,
            reviewer_aggressive_external_checks_preserved=True,
        ),
        "stage_precondition_error_materialized_as_control_blocker": _ready_for_apply(
            stage_precondition_error_materialized_as_control_blocker=True,
        ),
        "startup_fact_without_review_owner": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            startup_fact_without_review_owner=True,
        ),
        "unreviewable_startup_finding_without_pm_decision": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            all_startup_fact_review_owners_assigned=True,
            startup_fact_report_status="findings",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
            reviewer_finding_reason_kind="unreviewable_requirement",
        ),
        "startup_report_without_aggressive_external_checks": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            all_startup_fact_review_owners_assigned=True,
            startup_fact_report_status="pass",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=False,
        ),
        "fact_report_without_mechanical_audit": _ready_for_apply(
            startup_action_applied=True,
            startup_fact_report_status="pass",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
        ),
        "reviewer_findings_allow_work_without_pm_decision": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            all_startup_fact_review_owners_assigned=True,
            startup_fact_report_status="findings",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
            work_beyond_startup_allowed=True,
        ),
        "reviewer_findings_without_pm_decision": _ready_for_apply(
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            all_startup_fact_review_owners_assigned=True,
            startup_fact_report_status="findings",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
        ),
        "protocol_dead_end_without_file_backed_record": _ready_for_apply(
            status="protocol_dead_end",
            startup_action_applied=True,
            startup_mechanical_audit_written=True,
            startup_mechanical_audit_proof_written=True,
            startup_mechanical_audit_delivered_to_reviewer=True,
            router_owned_mechanical_facts_enforced=True,
            all_startup_fact_review_owners_assigned=True,
            startup_fact_report_status="findings",
            startup_fact_report_file_backed=True,
            reviewer_aggressive_external_checks_preserved=True,
            protocol_dead_end_declared=True,
            protocol_dead_end_file_backed=False,
        ),
        "material_card_before_startup_activation": _ready_for_apply(
            material_scan_card_delivered=True,
        ),
        "route_activation_before_startup_activation": _ready_for_apply(
            active_route_exists=True,
        ),
        "product_work_without_active_route": _ready_for_apply(
            work_beyond_startup_allowed=True,
            controller_product_work_started=True,
        ),
        "next_action_before_active_route": _ready_for_apply(
            work_beyond_startup_allowed=True,
            next_action_issued=True,
        ),
        "heartbeat_removed_before_pm_closure": _startup_passed(
            route_work_completed=True,
            heartbeat_removed=True,
            pm_closure_approved=False,
        ),
        "completion_before_pm_closure": _startup_passed(
            status="complete",
            route_work_completed=True,
            pm_closure_approved=False,
            heartbeat_removed=False,
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
