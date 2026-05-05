"""FlowGuard model for FlowPilot prompt-isolated packet startup.

This model checks the proposed FlowPilot rewrite where the main assistant is a
small bootloader and then a packet Controller. The model intentionally does not
cover implementation quality. It covers prompt visibility, mailbox routing,
PM/Controller role reset, phase/event prompt delivery, reviewer dispatch, and
PM decisions from reviewed evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One prompt-isolation controller tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    startup_state: str = "none"  # none | awaiting_answers | answers_complete | controller_ready
    holder: str = "none"  # none | user | controller | pm | reviewer | worker | officer
    phase: str = "none"
    event: str = "none"

    router_loaded: bool = False
    startup_questions_asked: bool = False
    startup_state_written_awaiting_answers: bool = False
    dialog_stopped_for_answers: bool = False
    startup_answers_recorded: bool = False
    banner_emitted: bool = False
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    runtime_kit_copied: bool = False
    bootloader_generated_prompt_body: bool = False
    placeholders_filled: bool = False
    mailbox_initialized: bool = False
    user_intake_ready: bool = False
    roles_started: bool = False
    role_core_prompts_injected: bool = False
    controller_core_loaded: bool = False
    pm_core_delivered: bool = False
    pm_controller_reset_card_delivered: bool = False
    pm_phase_map_delivered: bool = False
    pm_startup_intake_card_delivered: bool = False
    user_intake_delivered_to_pm: bool = False
    pm_controller_reset_decision_returned: bool = False
    controller_role_confirmed: bool = False

    pm_material_packets_issued: bool = False
    reviewer_dispatch_card_delivered: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_packets_delivered: bool = False
    worker_scan_results_returned: bool = False
    reviewer_worker_result_card_delivered: bool = False
    material_review: str = "unknown"  # unknown | insufficient | sufficient
    pm_reviewer_report_event_delivered: bool = False
    pm_repair_scan_packet_issued: bool = False
    worker_repair_result_returned: bool = False
    reviewer_repair_result_passed: bool = False
    material_accepted_by_pm: bool = False

    pm_product_understanding_card_delivered: bool = False
    product_understanding_written: bool = False
    product_understanding_reviewer_passed: bool = False

    pm_route_skeleton_card_delivered: bool = False
    route_draft_written: bool = False
    process_officer_route_check_passed: bool = False
    product_officer_route_check_passed: bool = False
    reviewer_route_check_passed: bool = False
    route_activated_by_pm: bool = False

    pm_current_node_card_delivered: bool = False
    pm_node_started_event_delivered: bool = False
    pm_node_packet_issued: bool = False
    node_dispatch_allowed: bool = False
    node_worker_body_delivered: bool = False
    node_worker_result_returned: bool = False
    node_reviewer_reviewed_result: bool = False
    node_review_blocked: bool = False
    pm_review_repair_card_delivered: bool = False
    pm_reviewer_blocked_event_delivered: bool = False
    pm_node_repair_packet_issued: bool = False
    node_repair_result_returned: bool = False
    node_repair_review_passed: bool = False
    node_completed_by_pm: bool = False

    pm_final_ledger_card_delivered: bool = False
    final_ledger_built_by_pm: bool = False
    final_backward_replay_passed: bool = False
    pm_closure_card_delivered: bool = False
    lifecycle_reconciled: bool = False
    heartbeat_stopped_or_manual_recorded: bool = False
    crew_archived: bool = False
    pm_completion_decision: bool = False

    prompt_deliveries: int = 0
    manifest_check_requests: int = 0
    manifest_checks: int = 0
    manifest_check_requested: bool = False
    mail_deliveries: int = 0
    ledger_check_requests: int = 0
    ledger_checks: int = 0
    ledger_check_requested: bool = False
    controller_read_forbidden_body: bool = False
    controller_origin_project_evidence: bool = False
    wrong_role_prompt_delivered: bool = False
    wrong_role_body_delivered: bool = False
    pm_used_unreviewed_evidence: bool = False
    bootloader_actions: int = 0
    router_action_requests: int = 0
    router_action_requested: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class PromptIsolationStep:
    name = "PromptIsolationStep"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _prompt(state: State, **changes: object) -> State:
    return replace(
        state,
        prompt_deliveries=state.prompt_deliveries + 1,
        manifest_checks=state.manifest_checks + 1,
        manifest_check_requested=False,
        **changes,
    )


def _mail(state: State, **changes: object) -> State:
    return replace(
        state,
        mail_deliveries=state.mail_deliveries + 1,
        ledger_checks=state.ledger_checks + 1,
        ledger_check_requested=False,
        **changes,
    )


def _request_manifest_check(state: State) -> State:
    return replace(
        state,
        manifest_check_requests=state.manifest_check_requests + 1,
        manifest_check_requested=True,
    )


def _request_ledger_check(state: State) -> State:
    return replace(
        state,
        ledger_check_requests=state.ledger_check_requests + 1,
        ledger_check_requested=True,
    )


def _request_router_action(state: State) -> State:
    return replace(
        state,
        router_action_requests=state.router_action_requests + 1,
        router_action_requested=True,
    )


def _boot(state: State, **changes: object) -> State:
    return replace(
        state,
        bootloader_actions=state.bootloader_actions + 1,
        router_action_requested=False,
        **changes,
    )


def _next_required_bootloader_action(state: State) -> str:
    """Return whether the bootloader needs an explicit router next-action."""

    if not state.router_loaded:
        return "none"
    if not state.startup_questions_asked:
        return "boot"
    if not state.startup_state_written_awaiting_answers:
        return "boot"
    if not state.dialog_stopped_for_answers:
        return "boot"
    if not state.startup_answers_recorded:
        return "boot"
    if not state.banner_emitted:
        return "boot"
    if not state.run_shell_created:
        return "boot"
    if not state.current_pointer_written:
        return "boot"
    if not state.run_index_updated:
        return "boot"
    if not state.runtime_kit_copied:
        return "boot"
    if not state.placeholders_filled:
        return "boot"
    if not state.mailbox_initialized:
        return "boot"
    if not state.user_intake_ready:
        return "boot"
    if not state.roles_started:
        return "boot"
    if not state.role_core_prompts_injected:
        return "boot"
    if not state.controller_core_loaded:
        return "boot"
    return "none"


def _bootloader_fact_count(state: State) -> int:
    """Count startup facts that can only be created by a router-approved boot action."""

    return sum(
        (
            state.startup_questions_asked,
            state.startup_state_written_awaiting_answers,
            state.dialog_stopped_for_answers,
            state.startup_answers_recorded,
            state.banner_emitted,
            state.run_shell_created,
            state.current_pointer_written,
            state.run_index_updated,
            state.runtime_kit_copied,
            state.placeholders_filled,
            state.mailbox_initialized,
            state.user_intake_ready,
            state.roles_started,
            state.role_core_prompts_injected,
            state.controller_core_loaded,
        )
    )


def _next_required_channel(state: State) -> str:
    """Return the next Controller delivery channel that needs an explicit prompt.

    The narrow model assumes Controller does not know to inspect either
    manifest or ledger unless the current PM/role card instructed it to do so.
    """

    if state.status == "complete":
        return "none"
    if state.controller_core_loaded:
        if not (
            state.pm_core_delivered
            and state.pm_controller_reset_card_delivered
            and state.pm_phase_map_delivered
            and state.pm_startup_intake_card_delivered
        ):
            return "prompt"
        if not state.user_intake_delivered_to_pm and state.user_intake_ready:
            return "mail"
    if state.pm_material_packets_issued and not state.reviewer_dispatch_card_delivered:
        return "prompt"
    if state.reviewer_dispatch_allowed and not state.worker_packets_delivered:
        return "mail"
    if state.worker_scan_results_returned and not state.reviewer_worker_result_card_delivered:
        return "prompt"
    if state.material_review != "unknown" and not state.pm_reviewer_report_event_delivered:
        return "prompt"
    if (
        state.material_review == "insufficient"
        and state.pm_repair_scan_packet_issued
        and not state.worker_repair_result_returned
    ):
        return "mail"
    if state.material_accepted_by_pm and not state.pm_product_understanding_card_delivered:
        return "prompt"
    if (
        state.product_understanding_reviewer_passed
        and not state.pm_route_skeleton_card_delivered
    ):
        return "prompt"
    if state.route_activated_by_pm and not (
        state.pm_current_node_card_delivered and state.pm_node_started_event_delivered
    ):
        return "prompt"
    if state.node_dispatch_allowed and not state.node_worker_body_delivered:
        return "mail"
    if state.node_review_blocked and not (
        state.pm_review_repair_card_delivered and state.pm_reviewer_blocked_event_delivered
    ):
        return "prompt"
    if (
        state.node_review_blocked
        and state.pm_node_repair_packet_issued
        and not state.node_repair_result_returned
    ):
        return "mail"
    if state.node_completed_by_pm and not state.pm_final_ledger_card_delivered:
        return "prompt"
    if state.final_backward_replay_passed and not state.pm_closure_card_delivered:
        return "prompt"
    return "none"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    next_bootloader_action = _next_required_bootloader_action(state)
    if next_bootloader_action == "boot" and not state.router_action_requested:
        yield Transition(
            "router_computed_next_bootloader_action",
            _request_router_action(state),
        )
        return

    next_channel = _next_required_channel(state)
    if next_channel == "prompt" and not state.manifest_check_requested:
        yield Transition(
            "controller_instructed_to_check_prompt_manifest",
            _request_manifest_check(state),
        )
        return
    if next_channel == "mail" and not state.ledger_check_requested:
        yield Transition(
            "controller_instructed_to_check_packet_ledger",
            _request_ledger_check(state),
        )
        return

    if not state.router_loaded:
        yield Transition(
            "bootloader_router_loaded",
            replace(state, status="running", router_loaded=True, holder="controller"),
        )
        return
    if not state.startup_questions_asked:
        yield Transition(
            "startup_questions_asked_from_router",
            _boot(
                state,
                startup_questions_asked=True,
                startup_state="awaiting_answers",
                holder="user",
            ),
        )
        return
    if not state.startup_state_written_awaiting_answers:
        yield Transition(
            "startup_state_written_awaiting_answers",
            _boot(state, startup_state_written_awaiting_answers=True),
        )
        return
    if not state.dialog_stopped_for_answers:
        yield Transition(
            "dialog_stopped_for_startup_answers",
            _boot(state, dialog_stopped_for_answers=True),
        )
        return
    if not state.startup_answers_recorded:
        yield Transition(
            "startup_answers_recorded_by_router",
            _boot(
                state,
                startup_answers_recorded=True,
                startup_state="answers_complete",
                holder="controller",
            ),
        )
        return
    if not state.banner_emitted:
        yield Transition(
            "startup_banner_emitted_after_answers",
            _boot(state, banner_emitted=True),
        )
        return
    if not state.run_shell_created:
        yield Transition("run_shell_created", _boot(state, run_shell_created=True))
        return
    if not state.current_pointer_written:
        yield Transition("current_pointer_written", _boot(state, current_pointer_written=True))
        return
    if not state.run_index_updated:
        yield Transition("run_index_updated", _boot(state, run_index_updated=True))
        return
    if not state.runtime_kit_copied:
        yield Transition(
            "bootstrap_runtime_kit_copied",
            _boot(state, runtime_kit_copied=True),
        )
        return
    if not state.placeholders_filled:
        yield Transition("bootstrap_placeholders_filled", _boot(state, placeholders_filled=True))
        return
    if not state.mailbox_initialized:
        yield Transition(
            "mailbox_initialized_from_copied_kit",
            _boot(state, mailbox_initialized=True),
        )
        return
    if not state.user_intake_ready:
        yield Transition(
            "user_intake_template_filled_from_raw_user_request",
            _boot(state, user_intake_ready=True),
        )
        return
    if not state.roles_started:
        yield Transition("six_roles_started_from_user_answer", _boot(state, roles_started=True))
        return
    if not state.role_core_prompts_injected:
        yield Transition(
            "role_core_prompts_injected_from_copied_kit",
            _boot(state, role_core_prompts_injected=True),
        )
        return
    if not state.controller_core_loaded:
        yield Transition("controller_core_loaded", _boot(state, controller_core_loaded=True))
        return
    if not state.pm_core_delivered:
        yield Transition("pm_core_card_delivered", _prompt(state, pm_core_delivered=True))
        return
    if not state.pm_controller_reset_card_delivered:
        yield Transition(
            "pm_controller_reset_duty_card_delivered",
            _prompt(state, pm_controller_reset_card_delivered=True),
        )
        return
    if not state.pm_phase_map_delivered:
        yield Transition("pm_phase_map_card_delivered", _prompt(state, pm_phase_map_delivered=True))
        return
    if not state.pm_startup_intake_card_delivered:
        yield Transition(
            "pm_startup_intake_phase_card_delivered",
            _prompt(state, pm_startup_intake_card_delivered=True, phase="startup_intake"),
        )
        return
    if not state.user_intake_delivered_to_pm:
        yield Transition(
            "user_intake_delivered_to_pm",
            _mail(state, user_intake_delivered_to_pm=True, holder="pm"),
        )
        return
    if not state.pm_controller_reset_decision_returned:
        yield Transition(
            "pm_first_decision_resets_controller",
            replace(state, pm_controller_reset_decision_returned=True, holder="controller"),
        )
        return
    if not state.controller_role_confirmed:
        yield Transition(
            "controller_role_confirmed_from_pm_reset",
            replace(state, controller_role_confirmed=True),
        )
        return
    if not state.pm_material_packets_issued:
        yield Transition(
            "pm_issues_material_and_capability_scan_packets",
            replace(state, pm_material_packets_issued=True, holder="controller"),
        )
        return
    if not state.reviewer_dispatch_card_delivered:
        yield Transition(
            "reviewer_dispatch_request_card_delivered",
            _prompt(state, reviewer_dispatch_card_delivered=True, holder="reviewer"),
        )
        return
    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "reviewer_allows_material_scan_dispatch",
            replace(state, reviewer_dispatch_allowed=True, holder="controller"),
        )
        return
    if not state.worker_packets_delivered:
        yield Transition(
            "worker_scan_packet_bodies_delivered_after_dispatch",
            _mail(state, worker_packets_delivered=True, holder="worker"),
        )
        return
    if not state.worker_scan_results_returned:
        yield Transition(
            "worker_scan_results_returned",
            replace(state, worker_scan_results_returned=True, holder="controller"),
        )
        return
    if not state.reviewer_worker_result_card_delivered:
        yield Transition(
            "reviewer_worker_result_review_card_delivered",
            _prompt(state, reviewer_worker_result_card_delivered=True, holder="reviewer"),
        )
        return
    if state.material_review == "unknown":
        yield Transition(
            "reviewer_reports_material_sufficient",
            replace(state, material_review="sufficient", holder="controller"),
        )
        yield Transition(
            "reviewer_reports_material_insufficient",
            replace(state, material_review="insufficient", holder="controller"),
        )
        return
    if not state.pm_reviewer_report_event_delivered:
        yield Transition(
            "pm_reviewer_report_event_card_delivered",
            _prompt(state, pm_reviewer_report_event_delivered=True, holder="pm"),
        )
        return
    if state.material_review == "insufficient" and not state.pm_repair_scan_packet_issued:
        yield Transition(
            "pm_issues_repair_scan_packet",
            replace(state, pm_repair_scan_packet_issued=True, holder="controller"),
        )
        return
    if state.material_review == "insufficient" and not state.worker_repair_result_returned:
        yield Transition(
            "repair_scan_dispatched_and_result_returned",
            _mail(state, worker_repair_result_returned=True, holder="reviewer"),
        )
        return
    if state.material_review == "insufficient" and not state.reviewer_repair_result_passed:
        yield Transition(
            "reviewer_passes_repair_scan_result",
            replace(state, reviewer_repair_result_passed=True, holder="controller"),
        )
        return
    if state.material_review == "insufficient" and not state.material_accepted_by_pm:
        yield Transition(
            "pm_accepts_reviewed_repair_material",
            replace(state, material_accepted_by_pm=True, holder="controller"),
        )
        return
    if state.material_review == "sufficient" and not state.material_accepted_by_pm:
        yield Transition(
            "pm_accepts_reviewed_material",
            replace(state, material_accepted_by_pm=True, holder="controller"),
        )
        return
    if not state.pm_product_understanding_card_delivered:
        yield Transition(
            "pm_product_understanding_phase_card_delivered",
            _prompt(state, pm_product_understanding_card_delivered=True, phase="product_understanding", holder="pm"),
        )
        return
    if not state.product_understanding_written:
        yield Transition(
            "pm_writes_product_understanding_from_reviewed_material",
            replace(state, product_understanding_written=True, holder="controller"),
        )
        return
    if not state.product_understanding_reviewer_passed:
        yield Transition(
            "reviewer_passes_product_understanding",
            replace(state, product_understanding_reviewer_passed=True),
        )
        return
    if not state.pm_route_skeleton_card_delivered:
        yield Transition(
            "pm_route_skeleton_phase_card_delivered",
            _prompt(state, pm_route_skeleton_card_delivered=True, phase="route_skeleton", holder="pm"),
        )
        return
    if not state.route_draft_written:
        yield Transition("pm_writes_route_draft", replace(state, route_draft_written=True, holder="controller"))
        return
    if not state.process_officer_route_check_passed:
        yield Transition("process_officer_route_check_passed", replace(state, process_officer_route_check_passed=True))
        return
    if not state.product_officer_route_check_passed:
        yield Transition("product_officer_route_check_passed", replace(state, product_officer_route_check_passed=True))
        return
    if not state.reviewer_route_check_passed:
        yield Transition("reviewer_route_check_passed", replace(state, reviewer_route_check_passed=True))
        return
    if not state.route_activated_by_pm:
        yield Transition("pm_activates_reviewed_route", replace(state, route_activated_by_pm=True, holder="controller"))
        return
    if not state.pm_current_node_card_delivered:
        yield Transition(
            "pm_current_node_loop_phase_card_delivered",
            _prompt(state, pm_current_node_card_delivered=True, phase="current_node_loop", holder="pm"),
        )
        return
    if not state.pm_node_started_event_delivered:
        yield Transition(
            "pm_node_started_event_card_delivered",
            _prompt(state, pm_node_started_event_delivered=True, event="node_started"),
        )
        return
    if not state.pm_node_packet_issued:
        yield Transition("pm_issues_current_node_packet", replace(state, pm_node_packet_issued=True, holder="controller"))
        return
    if not state.node_dispatch_allowed:
        yield Transition("reviewer_allows_current_node_dispatch", replace(state, node_dispatch_allowed=True))
        return
    if not state.node_worker_body_delivered:
        yield Transition(
            "current_node_worker_body_delivered_after_dispatch",
            _mail(state, node_worker_body_delivered=True, holder="worker"),
        )
        return
    if not state.node_worker_result_returned:
        yield Transition("current_node_worker_result_returned", replace(state, node_worker_result_returned=True, holder="reviewer"))
        return
    if not state.node_reviewer_reviewed_result:
        yield Transition(
            "current_node_reviewer_blocks_result",
            replace(state, node_reviewer_reviewed_result=True, node_review_blocked=True, holder="controller"),
        )
        yield Transition(
            "current_node_reviewer_passes_result",
            replace(state, node_reviewer_reviewed_result=True, node_review_blocked=False, holder="controller"),
        )
        return
    if state.node_review_blocked and not state.pm_review_repair_card_delivered:
        yield Transition(
            "pm_review_repair_phase_card_delivered",
            _prompt(state, pm_review_repair_card_delivered=True, phase="review_repair", holder="pm"),
        )
        return
    if state.node_review_blocked and not state.pm_reviewer_blocked_event_delivered:
        yield Transition(
            "pm_reviewer_blocked_event_card_delivered",
            _prompt(state, pm_reviewer_blocked_event_delivered=True, event="reviewer_blocked"),
        )
        return
    if state.node_review_blocked and not state.pm_node_repair_packet_issued:
        yield Transition("pm_issues_current_node_repair_packet", replace(state, pm_node_repair_packet_issued=True, holder="controller"))
        return
    if state.node_review_blocked and not state.node_repair_result_returned:
        yield Transition(
            "current_node_repair_result_returned",
            _mail(state, node_repair_result_returned=True, holder="reviewer"),
        )
        return
    if state.node_review_blocked and not state.node_repair_review_passed:
        yield Transition("reviewer_passes_current_node_repair", replace(state, node_repair_review_passed=True, holder="controller"))
        return
    if not state.node_completed_by_pm:
        yield Transition("pm_completes_current_node_from_reviewed_result", replace(state, node_completed_by_pm=True, holder="controller"))
        return
    if not state.pm_final_ledger_card_delivered:
        yield Transition(
            "pm_final_ledger_phase_card_delivered",
            _prompt(state, pm_final_ledger_card_delivered=True, phase="final_ledger", holder="pm"),
        )
        return
    if not state.final_ledger_built_by_pm:
        yield Transition("pm_builds_final_ledger", replace(state, final_ledger_built_by_pm=True, holder="reviewer"))
        return
    if not state.final_backward_replay_passed:
        yield Transition("reviewer_final_backward_replay_passed", replace(state, final_backward_replay_passed=True, holder="controller"))
        return
    if not state.pm_closure_card_delivered:
        yield Transition(
            "pm_closure_phase_card_delivered",
            _prompt(state, pm_closure_card_delivered=True, phase="closure", holder="pm"),
        )
        return
    if not state.lifecycle_reconciled:
        yield Transition("lifecycle_reconciled", replace(state, lifecycle_reconciled=True))
        return
    if not state.heartbeat_stopped_or_manual_recorded:
        yield Transition("heartbeat_stopped_or_manual_resume_recorded", replace(state, heartbeat_stopped_or_manual_recorded=True))
        return
    if not state.crew_archived:
        yield Transition("crew_archived", replace(state, crew_archived=True))
        return
    if not state.pm_completion_decision:
        yield Transition("pm_completion_decision_recorded", replace(state, pm_completion_decision=True))
        return
    yield Transition("completed", replace(state, status="complete", holder="controller"))


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    expected_boot_facts = _bootloader_fact_count(state)
    if state.bootloader_actions < expected_boot_facts:
        failures.append("startup fact appeared without a router-approved bootloader action")
    if state.router_action_requests < state.bootloader_actions:
        failures.append("bootloader action ran before router computed a next action")
    if state.router_action_requested:
        if state.router_action_requests != state.bootloader_actions + 1:
            failures.append("pending router next-action request does not match the bootloader action count")
    elif state.router_action_requests != state.bootloader_actions:
        failures.append("router next-action requests and completed bootloader actions are out of sync")
    if state.bootloader_actions > expected_boot_facts:
        failures.append("bootloader action was recorded without the matching startup fact")
    if state.startup_questions_asked and not state.router_loaded:
        failures.append("startup questions were asked without loading the bootloader router")
    if state.banner_emitted and not (
        state.startup_answers_recorded and state.dialog_stopped_for_answers
    ):
        failures.append("startup banner emitted before explicit answers after a stopped dialog")
    if state.run_shell_created and not state.banner_emitted:
        failures.append("run shell created before startup banner")
    if state.runtime_kit_copied and not (
        state.run_shell_created and state.current_pointer_written and state.run_index_updated
    ):
        failures.append("runtime kit copied before run shell and pointer/index files")
    if state.bootloader_generated_prompt_body:
        failures.append("bootloader generated prompt or packet body instead of copying the audited runtime kit")
    if state.roles_started and not (
        state.runtime_kit_copied and state.placeholders_filled and state.mailbox_initialized
    ):
        failures.append("roles started before copied kit, placeholders, and mailbox were ready")
    if state.user_intake_delivered_to_pm and not (
        state.controller_core_loaded
        and state.pm_core_delivered
        and state.pm_controller_reset_card_delivered
        and state.pm_phase_map_delivered
        and state.pm_startup_intake_card_delivered
        and state.user_intake_ready
    ):
        failures.append("user intake delivered before Controller and PM bootstrap prompt cards were delivered")
    if state.controller_role_confirmed and not state.pm_controller_reset_decision_returned:
        failures.append("Controller role confirmed before PM returned the reset decision")
    if state.pm_material_packets_issued and not (
        state.controller_role_confirmed and state.pm_startup_intake_card_delivered
    ):
        failures.append("PM issued material packets before Controller reset and startup-intake phase card")
    if state.worker_packets_delivered and not state.reviewer_dispatch_allowed:
        failures.append("worker packet bodies delivered before reviewer dispatch approval")
    if state.material_accepted_by_pm and not (
        state.pm_reviewer_report_event_delivered
        and (
            state.material_review == "sufficient"
            or (state.reviewer_repair_result_passed and state.worker_repair_result_returned)
        )
    ):
        failures.append("PM accepted material before reviewer report event and reviewed sufficient evidence")
    if state.pm_used_unreviewed_evidence:
        failures.append("PM used unreviewed evidence for a route or phase decision")
    if state.product_understanding_written and not (
        state.pm_product_understanding_card_delivered and state.material_accepted_by_pm
    ):
        failures.append("PM wrote product understanding before phase card and reviewed material")
    if state.route_draft_written and not (
        state.pm_route_skeleton_card_delivered and state.product_understanding_reviewer_passed
    ):
        failures.append("PM wrote route draft before route phase card and reviewed product understanding")
    if state.route_activated_by_pm and not (
        state.route_draft_written
        and state.process_officer_route_check_passed
        and state.product_officer_route_check_passed
        and state.reviewer_route_check_passed
    ):
        failures.append("PM activated route before officer and reviewer checks")
    if state.pm_node_packet_issued and not (
        state.pm_current_node_card_delivered and state.pm_node_started_event_delivered
    ):
        failures.append("PM issued node packet before current-node phase card and node-started event card")
    if state.node_worker_body_delivered and not state.node_dispatch_allowed:
        failures.append("current-node worker body delivered before reviewer dispatch")
    if state.pm_node_repair_packet_issued and not (
        state.pm_review_repair_card_delivered and state.pm_reviewer_blocked_event_delivered
    ):
        failures.append("PM issued repair packet before repair phase and reviewer-blocked event cards")
    if state.node_completed_by_pm and not (
        (state.node_reviewer_reviewed_result and not state.node_review_blocked)
        or (state.node_repair_result_returned and state.node_repair_review_passed)
    ):
        failures.append("PM completed node before passing reviewer result or repaired recheck")
    if state.final_ledger_built_by_pm and not (
        state.node_completed_by_pm and state.pm_final_ledger_card_delivered
    ):
        failures.append("PM built final ledger before node completion and final-ledger phase card")
    if state.pm_completion_decision and not (
        state.pm_closure_card_delivered
        and state.final_ledger_built_by_pm
        and state.final_backward_replay_passed
        and state.lifecycle_reconciled
        and state.heartbeat_stopped_or_manual_recorded
        and state.crew_archived
    ):
        failures.append("PM completion decision before closure card, final replay, lifecycle, continuation cleanup, and crew archive")
    if state.prompt_deliveries > state.manifest_checks:
        failures.append("prompt card delivered without a matching manifest check")
    if state.mail_deliveries > state.ledger_checks:
        failures.append("mail delivered without a matching packet-ledger check")
    if state.prompt_deliveries > state.manifest_check_requests:
        failures.append("prompt card delivered before Controller was instructed to check the prompt manifest")
    if state.mail_deliveries > state.ledger_check_requests:
        failures.append("mail delivered before Controller was instructed to check the packet ledger")
    if state.manifest_checks > state.manifest_check_requests:
        failures.append("Controller checked prompt manifest without a current instruction")
    if state.ledger_checks > state.ledger_check_requests:
        failures.append("Controller checked packet ledger without a current instruction")
    if state.controller_read_forbidden_body:
        failures.append("Controller read a packet/result body that was not addressed to Controller")
    if state.controller_origin_project_evidence:
        failures.append("Controller-origin project evidence was created")
    if state.wrong_role_prompt_delivered:
        failures.append("system prompt card was delivered to the wrong role")
    if state.wrong_role_body_delivered:
        failures.append("packet/result body was delivered to the wrong role")
    if state.status == "complete" and not state.pm_completion_decision:
        failures.append("run completed before PM completion decision")
    return failures


def prompt_isolation_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="prompt_isolation_packet_control",
        description=(
            "Bootloader, Controller, PM, Reviewer, Worker, and Officer can only "
            "act from current prompt cards, manifest checks, ledger checks, and "
            "reviewed packet evidence."
        ),
        predicate=prompt_isolation_invariant,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 90


def build_workflow() -> Workflow:
    return Workflow((PromptIsolationStep(),), name="flowpilot_prompt_isolation")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _ready(**changes: object) -> State:
    base = State(
        status="running",
        startup_state="controller_ready",
        holder="controller",
        phase="startup_intake",
        router_loaded=True,
        startup_questions_asked=True,
        startup_state_written_awaiting_answers=True,
        dialog_stopped_for_answers=True,
        startup_answers_recorded=True,
        banner_emitted=True,
        run_shell_created=True,
        current_pointer_written=True,
        run_index_updated=True,
        runtime_kit_copied=True,
        placeholders_filled=True,
        mailbox_initialized=True,
        user_intake_ready=True,
        roles_started=True,
        role_core_prompts_injected=True,
        controller_core_loaded=True,
        pm_core_delivered=True,
        pm_controller_reset_card_delivered=True,
        pm_phase_map_delivered=True,
        pm_startup_intake_card_delivered=True,
        user_intake_delivered_to_pm=True,
        pm_controller_reset_decision_returned=True,
        controller_role_confirmed=True,
        prompt_deliveries=4,
        manifest_check_requests=4,
        manifest_checks=4,
        mail_deliveries=1,
        ledger_check_requests=1,
        ledger_checks=1,
        bootloader_actions=15,
        router_action_requests=15,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "questions_without_router": State(startup_questions_asked=True),
        "banner_before_answers": State(router_loaded=True, startup_questions_asked=True, banner_emitted=True),
        "run_shell_before_banner": State(router_loaded=True, startup_questions_asked=True, run_shell_created=True),
        "banner_without_router_next_action": State(
            router_loaded=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answers_recorded=True,
            banner_emitted=True,
            bootloader_actions=5,
            router_action_requests=4,
        ),
        "run_shell_after_banner_without_router_next_action": State(
            router_loaded=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answers_recorded=True,
            banner_emitted=True,
            run_shell_created=True,
            bootloader_actions=6,
            router_action_requests=5,
        ),
        "bootloader_generates_prompts": _ready(bootloader_generated_prompt_body=True),
        "roles_before_runtime_kit": State(
            router_loaded=True,
            startup_questions_asked=True,
            startup_answers_recorded=True,
            banner_emitted=True,
            roles_started=True,
        ),
        "user_intake_before_pm_cards": _ready(pm_controller_reset_card_delivered=False),
        "work_before_pm_resets_controller": _ready(controller_role_confirmed=False, pm_material_packets_issued=True),
        "worker_body_without_dispatch": _ready(
            pm_material_packets_issued=True,
            worker_packets_delivered=True,
            reviewer_dispatch_allowed=False,
        ),
        "pm_accepts_unreviewed_worker_result": _ready(
            worker_scan_results_returned=True,
            material_accepted_by_pm=True,
            pm_used_unreviewed_evidence=True,
        ),
        "product_understanding_without_phase_card": _ready(
            material_accepted_by_pm=True,
            pm_product_understanding_card_delivered=False,
            product_understanding_written=True,
        ),
        "route_draft_without_reviewed_product": _ready(
            material_accepted_by_pm=True,
            pm_product_understanding_card_delivered=True,
            product_understanding_written=True,
            product_understanding_reviewer_passed=False,
            pm_route_skeleton_card_delivered=True,
            route_draft_written=True,
        ),
        "route_activated_without_officer_checks": _ready(route_draft_written=True, route_activated_by_pm=True),
        "node_packet_without_node_cards": _ready(route_activated_by_pm=True, pm_node_packet_issued=True),
        "repair_issued_without_block_event_card": _ready(
            node_reviewer_reviewed_result=True,
            node_review_blocked=True,
            pm_node_repair_packet_issued=True,
        ),
        "final_ledger_before_node_completion": _ready(
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
        ),
        "complete_before_closure_cleanup": _ready(
            node_completed_by_pm=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
            final_backward_replay_passed=True,
            pm_completion_decision=True,
        ),
        "prompt_delivery_without_manifest_check": _ready(prompt_deliveries=5, manifest_checks=4),
        "mail_delivery_without_ledger_check": _ready(mail_deliveries=2, ledger_checks=1),
        "controller_reads_body": _ready(controller_read_forbidden_body=True),
        "controller_creates_project_evidence": _ready(controller_origin_project_evidence=True),
        "wrong_role_prompt": _ready(wrong_role_prompt_delivered=True),
        "wrong_role_body": _ready(wrong_role_body_delivered=True),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
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
    "next_states",
    "next_safe_states",
    "prompt_isolation_invariant",
]
