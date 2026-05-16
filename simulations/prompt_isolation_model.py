"""FlowGuard model for FlowPilot prompt-isolated packet startup.

This model checks the proposed FlowPilot rewrite where the main assistant is a
small bootloader and then a packet Controller. The model intentionally does not
cover implementation quality. It covers prompt visibility, mailbox routing,
Router-owned Controller boundary confirmation, phase/event prompt delivery, router direct dispatch, and
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
    run_scoped_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_answer_values_valid: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    startup_answers_recorded: bool = False
    banner_emitted: bool = False
    startup_banner_user_visible: bool = False
    startup_banner_user_dialog_confirmed: bool = False
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    runtime_kit_copied: bool = False
    bootloader_generated_prompt_body: bool = False
    placeholders_filled: bool = False
    mailbox_initialized: bool = False
    user_request_recorded: bool = False
    user_request_provenance: str = "none"  # none | explicit_user_request | inferred | default
    user_intake_ready: bool = False
    roles_started: bool = False
    fresh_role_agents_started: bool = False
    role_core_prompts_injected: bool = False
    controller_core_loaded: bool = False
    controller_boundary_confirmation_written: bool = False
    controller_boundary_policy_hash_recorded: bool = False
    pm_core_delivered: bool = False
    pm_controller_reset_card_delivered: bool = False
    pm_phase_map_delivered: bool = False
    pm_startup_intake_card_delivered: bool = False
    reviewer_startup_fact_check_card_delivered: bool = False
    startup_fact_reported: bool = False
    pm_startup_activation_card_delivered: bool = False
    startup_activation_approved: bool = False
    user_intake_delivered_to_pm: bool = False
    user_intake_controller_relayed: bool = False
    pm_controller_reset_decision_returned: bool = False
    controller_role_confirmed: bool = False

    pm_material_scan_card_delivered: bool = False
    pm_material_scan_packets_issued: bool = False
    reviewer_dispatch_card_delivered: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_packets_delivered: bool = False
    worker_scan_results_returned: bool = False
    material_scan_result_ledger_checked: bool = False
    reviewer_material_sufficiency_card_delivered: bool = False
    material_review: str = "unknown"  # unknown | sufficient | research_required
    pm_material_absorb_or_research_card_delivered: bool = False
    material_accepted_by_pm: bool = False
    pm_research_package_card_delivered: bool = False
    pm_research_package_written: bool = False
    research_capability_decision_recorded: bool = False
    research_worker_report_card_delivered: bool = False
    research_reviewer_dispatch_card_delivered: bool = False
    research_dispatch_allowed: bool = False
    research_worker_packet_delivered: bool = False
    research_worker_report_returned: bool = False
    research_worker_result_ledger_checked: bool = False
    reviewer_research_direct_source_check_card_delivered: bool = False
    research_reviewer_direct_source_check_done: bool = False
    research_reviewer_passed: bool = False
    pm_research_absorb_or_mutate_card_delivered: bool = False
    research_absorbed_by_pm: bool = False
    pm_material_understanding_card_delivered: bool = False
    material_understanding_written: bool = False

    pm_product_architecture_card_delivered: bool = False
    product_architecture_draft_written: bool = False
    product_architecture_modelability_card_delivered: bool = False
    product_architecture_modelability_passed: bool = False
    product_architecture_officer_result_ledger_checked: bool = False
    product_architecture_challenge_card_delivered: bool = False
    product_architecture_reviewer_challenged: bool = False
    pm_root_contract_card_delivered: bool = False
    root_contract_draft_written: bool = False
    root_contract_challenge_card_delivered: bool = False
    root_contract_reviewer_challenged: bool = False
    root_contract_modelability_card_delivered: bool = False
    root_contract_modelability_passed: bool = False
    root_contract_officer_result_ledger_checked: bool = False
    root_contract_frozen_by_pm: bool = False
    pm_dependency_policy_card_delivered: bool = False
    dependency_policy_recorded: bool = False
    capabilities_manifest_written: bool = False
    pm_child_skill_selection_card_delivered: bool = False
    pm_child_skill_selection_written: bool = False
    pm_child_skill_gate_manifest_card_delivered: bool = False
    child_skill_gate_manifest_written: bool = False
    reviewer_child_skill_gate_manifest_card_delivered: bool = False
    child_skill_manifest_reviewer_passed: bool = False
    process_officer_child_skill_card_delivered: bool = False
    child_skill_process_officer_passed: bool = False
    child_skill_process_officer_result_ledger_checked: bool = False
    product_officer_child_skill_card_delivered: bool = False
    child_skill_product_officer_passed: bool = False
    child_skill_product_officer_result_ledger_checked: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    capability_evidence_synced: bool = False
    pm_prior_path_context_card_delivered: bool = False
    route_history_context_refreshed: bool = False
    pm_prior_path_context_reviewed: bool = False
    route_history_context_stale: bool = False
    route_skeleton_prior_context_used: bool = False
    node_acceptance_plan_prior_context_used: bool = False
    route_mutation_prior_context_used: bool = False
    parent_segment_prior_context_used: bool = False
    evidence_quality_prior_context_used: bool = False
    final_ledger_prior_context_used: bool = False
    pm_route_skeleton_card_delivered: bool = False
    route_skeleton_written: bool = False
    route_activated_by_pm: bool = False
    route_mutated_by_pm: bool = False

    pm_current_node_card_delivered: bool = False
    pm_node_started_event_delivered: bool = False
    pm_node_acceptance_plan_card_delivered: bool = False
    node_acceptance_plan_written: bool = False
    reviewer_node_acceptance_plan_review_card_delivered: bool = False
    node_acceptance_plan_reviewed: bool = False
    pm_node_packet_issued: bool = False
    reviewer_current_node_dispatch_card_delivered: bool = False
    node_dispatch_allowed: bool = False
    node_worker_body_delivered: bool = False
    node_worker_result_returned: bool = False
    node_worker_result_ledger_checked: bool = False
    node_reviewer_reviewed_result: bool = False
    node_review_blocked: bool = False
    pm_review_repair_card_delivered: bool = False
    pm_reviewer_blocked_event_delivered: bool = False
    pm_node_repair_packet_issued: bool = False
    node_repair_result_returned: bool = False
    node_repair_result_ledger_checked: bool = False
    node_repair_review_passed: bool = False
    node_completed_by_pm: bool = False

    pm_parent_backward_targets_card_delivered: bool = False
    parent_backward_targets_enumerated: bool = False
    reviewer_parent_backward_replay_card_delivered: bool = False
    parent_backward_replay_passed: bool = False
    pm_parent_segment_decision_card_delivered: bool = False
    parent_pm_segment_decision_recorded: bool = False
    pm_evidence_quality_package_card_delivered: bool = False
    pm_evidence_quality_package_written: bool = False
    reviewer_evidence_quality_review_card_delivered: bool = False
    evidence_quality_reviewer_passed: bool = False
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
    controller_relayed_body_content: bool = False
    role_output_body_file_written: bool = False
    role_output_envelope_only_to_controller: bool = False
    role_chat_response_disclosed_body: bool = False
    controller_used_role_chat_body: bool = False
    role_output_path_hash_verified: bool = False
    controller_direct_free_text_instruction_used: bool = False
    controller_inspected_router_internal_hard_checks: bool = False
    wrong_role_prompt_delivered: bool = False
    wrong_role_body_delivered: bool = False
    pm_used_unreviewed_evidence: bool = False
    bootloader_actions: int = 0
    router_action_requests: int = 0
    router_action_requested: bool = False
    system_card_identity_boundaries_verified: bool = False
    packet_body_identity_boundaries_verified: bool = False
    result_body_identity_boundaries_verified: bool = False


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
        system_card_identity_boundaries_verified=True,
        **changes,
    )


def _mail(state: State, **changes: object) -> State:
    return replace(
        state,
        mail_deliveries=state.mail_deliveries + 1,
        ledger_checks=state.ledger_checks + 1,
        ledger_check_requested=False,
        packet_body_identity_boundaries_verified=True,
        result_body_identity_boundaries_verified=True,
        **changes,
    )


def _role_return(state: State, **changes: object) -> State:
    return replace(
        state,
        role_output_body_file_written=True,
        role_output_envelope_only_to_controller=True,
        role_output_path_hash_verified=True,
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


def _refresh_history_context(state: State) -> State:
    return replace(
        state,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=False,
        holder="pm",
    )


def _pm_reads_history_context(state: State) -> State:
    return replace(state, pm_prior_path_context_reviewed=True, holder="pm")


def _stale_history_context(state: State) -> State:
    return replace(
        state,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
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
    if not state.user_request_recorded:
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
    """Count startup actions that can only be created by router-approved boot actions."""

    startup_question_stop_boundary = (
        state.startup_questions_asked
        or state.startup_state_written_awaiting_answers
        or state.dialog_stopped_for_answers
    )
    return sum(
        (
            startup_question_stop_boundary,
            state.startup_answers_recorded,
            state.banner_emitted,
            state.run_shell_created,
            state.current_pointer_written,
            state.run_index_updated,
            state.runtime_kit_copied,
            state.placeholders_filled,
            state.mailbox_initialized,
            state.user_request_recorded,
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
        if not state.controller_role_confirmed:
            return "none"
        if not (
            state.pm_core_delivered
            and state.pm_phase_map_delivered
            and state.pm_startup_intake_card_delivered
        ):
            return "prompt"
        if not state.reviewer_startup_fact_check_card_delivered:
            return "prompt"
        if state.startup_fact_reported and not state.pm_startup_activation_card_delivered:
            return "prompt"
        if (
            state.startup_activation_approved
            and not state.user_intake_delivered_to_pm
            and state.user_intake_ready
        ):
            return "mail"
    if (
        state.controller_role_confirmed
        and state.user_intake_delivered_to_pm
        and not state.pm_material_scan_card_delivered
    ):
        return "prompt"
    if state.pm_material_scan_packets_issued and not state.reviewer_dispatch_allowed:
        return "mail"
    if state.reviewer_dispatch_allowed and not state.worker_packets_delivered:
        return "mail"
    if state.worker_packets_delivered and not state.worker_scan_results_returned:
        return "mail"
    if (
        state.worker_scan_results_returned
        and not state.reviewer_material_sufficiency_card_delivered
    ):
        return "prompt"
    if (
        state.material_review != "unknown"
        and not state.pm_material_absorb_or_research_card_delivered
    ):
        return "prompt"
    if (
        state.material_review == "research_required"
        and state.pm_material_absorb_or_research_card_delivered
        and not state.pm_research_package_card_delivered
    ):
        return "prompt"
    if (
        state.research_capability_decision_recorded
        and not state.research_worker_report_card_delivered
    ):
        return "prompt"
    if state.research_worker_report_card_delivered and not state.research_dispatch_allowed:
        return "mail"
    if state.research_dispatch_allowed and not state.research_worker_packet_delivered:
        return "mail"
    if (
        state.research_worker_packet_delivered
        and not state.research_worker_report_returned
    ):
        return "mail"
    if (
        state.research_worker_report_returned
        and not state.reviewer_research_direct_source_check_card_delivered
    ):
        return "prompt"
    if (
        state.research_reviewer_passed
        and not state.pm_research_absorb_or_mutate_card_delivered
    ):
        return "prompt"
    if (
        (state.material_accepted_by_pm or state.research_absorbed_by_pm)
        and not state.pm_material_understanding_card_delivered
    ):
        return "prompt"
    if (
        state.material_understanding_written
        and not state.pm_product_architecture_card_delivered
    ):
        return "prompt"
    if (
        state.product_architecture_draft_written
        and not state.product_architecture_modelability_card_delivered
    ):
        return "prompt"
    if (
        state.product_architecture_modelability_card_delivered
        and not state.product_architecture_modelability_passed
    ):
        return "mail"
    if (
        state.product_architecture_modelability_passed
        and not state.product_architecture_challenge_card_delivered
    ):
        return "prompt"
    if (
        state.product_architecture_reviewer_challenged
        and not state.pm_root_contract_card_delivered
    ):
        return "prompt"
    if (
        state.root_contract_draft_written
        and not state.root_contract_challenge_card_delivered
    ):
        return "prompt"
    if state.root_contract_frozen_by_pm and not state.pm_dependency_policy_card_delivered:
        return "prompt"
    if state.capabilities_manifest_written and not state.pm_child_skill_selection_card_delivered:
        return "prompt"
    if (
        state.pm_child_skill_selection_written
        and not state.pm_child_skill_gate_manifest_card_delivered
    ):
        return "prompt"
    if (
        state.child_skill_gate_manifest_written
        and not state.reviewer_child_skill_gate_manifest_card_delivered
    ):
        return "prompt"
    if state.capability_evidence_synced and not state.pm_prior_path_context_card_delivered:
        return "prompt"
    if (
        state.pm_prior_path_context_card_delivered
        and state.pm_prior_path_context_reviewed
        and not state.pm_route_skeleton_card_delivered
    ):
        return "prompt"
    if state.route_activated_by_pm and not (
        state.pm_current_node_card_delivered and state.pm_node_started_event_delivered
    ):
        return "prompt"
    if (
        state.pm_node_started_event_delivered
        and not state.pm_node_acceptance_plan_card_delivered
    ):
        return "prompt"
    if (
        state.node_acceptance_plan_written
        and not state.reviewer_node_acceptance_plan_review_card_delivered
    ):
        return "prompt"
    if state.pm_node_packet_issued and not state.node_dispatch_allowed:
        return "mail"
    if state.node_dispatch_allowed and not state.node_worker_body_delivered:
        return "mail"
    if state.node_worker_body_delivered and not state.node_worker_result_returned:
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
    if (
        state.node_completed_by_pm
        and not state.pm_parent_backward_targets_card_delivered
    ):
        return "prompt"
    if (
        state.parent_backward_targets_enumerated
        and not state.reviewer_parent_backward_replay_card_delivered
    ):
        return "prompt"
    if (
        state.parent_backward_replay_passed
        and not state.pm_parent_segment_decision_card_delivered
    ):
        return "prompt"
    if (
        state.parent_pm_segment_decision_recorded
        and not state.pm_evidence_quality_package_card_delivered
    ):
        return "prompt"
    if (
        state.pm_evidence_quality_package_written
        and not state.reviewer_evidence_quality_review_card_delivered
    ):
        return "prompt"
    if (
        state.evidence_quality_reviewer_passed
        and state.pm_prior_path_context_reviewed
        and not state.pm_final_ledger_card_delivered
    ):
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
            "router_checks_prompt_manifest",
            _request_manifest_check(state),
        )
        return
    if next_channel == "mail" and not state.ledger_check_requested:
        yield Transition(
            "router_checks_packet_ledger",
            _request_ledger_check(state),
        )
        return

    if not state.router_loaded:
        yield Transition(
            "bootloader_router_loaded",
            replace(
                state,
                status="running",
                router_loaded=True,
                run_scoped_bootstrap_created=True,
                holder="controller",
            ),
        )
        return
    if not state.startup_questions_asked:
        yield Transition(
            "startup_questions_asked_from_router",
            _boot(
                state,
                startup_questions_asked=True,
                startup_state_written_awaiting_answers=True,
                dialog_stopped_for_answers=True,
                startup_state="awaiting_answers_stopped",
                holder="user",
            ),
        )
        return
    if not state.startup_answers_recorded:
        yield Transition(
            "startup_answers_recorded_by_router",
            _boot(
                state,
                startup_answers_recorded=True,
                startup_answer_values_valid=True,
                startup_answer_provenance="explicit_user_reply",
                startup_state="answers_complete",
                holder="controller",
            ),
        )
        return
    if not state.banner_emitted:
        yield Transition(
            "startup_banner_emitted_after_answers",
            _boot(
                state,
                banner_emitted=True,
                startup_banner_user_visible=True,
                startup_banner_user_dialog_confirmed=True,
            ),
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
    if not state.user_request_recorded:
        yield Transition(
            "user_request_recorded_from_explicit_user_request",
            _boot(
                state,
                user_request_recorded=True,
                user_request_provenance="explicit_user_request",
            ),
        )
        return
    if not state.user_intake_ready:
        yield Transition(
            "user_intake_template_filled_from_raw_user_request",
            _boot(state, user_intake_ready=True),
        )
        return
    if not state.roles_started:
        yield Transition(
            "six_roles_started_from_user_answer",
            _boot(state, roles_started=True, fresh_role_agents_started=True),
        )
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
    if not state.controller_role_confirmed:
        yield Transition(
            "controller_role_confirmed_from_router_core",
            replace(
                state,
                controller_role_confirmed=True,
                controller_boundary_confirmation_written=True,
                controller_boundary_policy_hash_recorded=True,
                role_output_body_file_written=True,
                role_output_envelope_only_to_controller=True,
                role_output_path_hash_verified=True,
            ),
        )
        return
    if not state.pm_core_delivered:
        yield Transition("pm_core_card_delivered", _prompt(state, pm_core_delivered=True))
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
    if not state.reviewer_startup_fact_check_card_delivered:
        yield Transition(
            "reviewer_startup_fact_check_card_delivered",
            _prompt(state, reviewer_startup_fact_check_card_delivered=True, holder="reviewer"),
        )
        return
    if not state.startup_fact_reported:
        yield Transition(
            "reviewer_reports_startup_facts_for_pm_activation",
            _role_return(state, startup_fact_reported=True, holder="controller"),
        )
        return
    if not state.pm_startup_activation_card_delivered:
        yield Transition(
            "pm_startup_activation_phase_card_delivered",
            _prompt(state, pm_startup_activation_card_delivered=True, holder="pm"),
        )
        return
    if not state.startup_activation_approved:
        yield Transition(
            "pm_approves_startup_activation_from_reviewed_facts",
            _role_return(state, startup_activation_approved=True, holder="controller"),
        )
        return
    if not state.user_intake_delivered_to_pm:
        yield Transition(
            "controller_relays_user_intake_to_pm",
            _mail(
                state,
                user_intake_delivered_to_pm=True,
                user_intake_controller_relayed=True,
                holder="pm",
            ),
        )
        return
    if not state.pm_material_scan_card_delivered:
        yield Transition(
            "pm_material_scan_phase_card_delivered",
            _prompt(state, pm_material_scan_card_delivered=True, phase="material_scan", holder="pm"),
        )
        return
    if not state.pm_material_scan_packets_issued:
        yield Transition(
            "pm_issues_material_and_capability_scan_packets",
            replace(state, pm_material_scan_packets_issued=True, holder="controller"),
        )
        return
    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "router_direct_material_scan_dispatch_preflight_passed",
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
            _mail(
                state,
                worker_scan_results_returned=True,
                material_scan_result_ledger_checked=True,
                holder="reviewer",
            ),
        )
        return
    if not state.reviewer_material_sufficiency_card_delivered:
        yield Transition(
            "reviewer_material_sufficiency_card_delivered",
            _prompt(state, reviewer_material_sufficiency_card_delivered=True, holder="reviewer"),
        )
        return
    if state.material_review == "unknown":
        yield Transition(
            "reviewer_reports_material_sufficient",
            replace(state, material_review="sufficient", holder="controller"),
        )
        yield Transition(
            "reviewer_reports_research_required",
            replace(state, material_review="research_required", holder="controller"),
        )
        return
    if not state.pm_material_absorb_or_research_card_delivered:
        yield Transition(
            "pm_material_absorb_or_research_card_delivered",
            _prompt(
                state,
                pm_material_absorb_or_research_card_delivered=True,
                phase="material_absorb_or_research",
                holder="pm",
            ),
        )
        return
    if state.material_review == "research_required" and not state.pm_research_package_card_delivered:
        yield Transition(
            "pm_research_package_phase_card_delivered",
            _prompt(state, pm_research_package_card_delivered=True, phase="research_package", holder="pm"),
        )
        return
    if state.material_review == "research_required" and not state.pm_research_package_written:
        yield Transition(
            "pm_writes_bounded_research_package",
            replace(state, pm_research_package_written=True, holder="controller"),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.research_capability_decision_recorded
    ):
        yield Transition(
            "pm_records_research_capability_decision",
            replace(state, research_capability_decision_recorded=True, holder="controller"),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.research_worker_report_card_delivered
    ):
        yield Transition(
            "worker_research_report_card_delivered",
            _prompt(state, research_worker_report_card_delivered=True, holder="worker"),
        )
        return
    if state.material_review == "research_required" and not state.research_dispatch_allowed:
        yield Transition(
            "router_direct_research_dispatch_preflight_passed",
            replace(state, research_dispatch_allowed=True, holder="controller"),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.research_worker_packet_delivered
    ):
        yield Transition(
            "research_worker_packet_body_delivered_after_dispatch",
            _mail(state, research_worker_packet_delivered=True, holder="worker"),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.research_worker_report_returned
    ):
        yield Transition(
            "research_worker_report_returned",
            _mail(
                state,
                research_worker_report_returned=True,
                research_worker_result_ledger_checked=True,
                holder="reviewer",
            ),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.reviewer_research_direct_source_check_card_delivered
    ):
        yield Transition(
            "reviewer_research_direct_source_check_card_delivered",
            _prompt(
                state,
                reviewer_research_direct_source_check_card_delivered=True,
                holder="reviewer",
            ),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.research_reviewer_direct_source_check_done
    ):
        yield Transition(
            "reviewer_direct_source_research_check_done",
            replace(state, research_reviewer_direct_source_check_done=True),
        )
        return
    if state.material_review == "research_required" and not state.research_reviewer_passed:
        yield Transition(
            "reviewer_passes_research_result",
            replace(state, research_reviewer_passed=True, holder="controller"),
        )
        return
    if (
        state.material_review == "research_required"
        and not state.pm_research_absorb_or_mutate_card_delivered
    ):
        yield Transition(
            "pm_research_absorb_or_mutate_card_delivered",
            _prompt(
                state,
                pm_research_absorb_or_mutate_card_delivered=True,
                phase="research_absorb_or_mutate",
                holder="pm",
            ),
        )
        return
    if state.material_review == "research_required" and not state.research_absorbed_by_pm:
        yield Transition(
            "pm_absorbs_reviewed_research",
            replace(state, research_absorbed_by_pm=True, holder="controller"),
        )
        return
    if state.material_review == "sufficient" and not state.material_accepted_by_pm:
        yield Transition(
            "pm_absorbs_reviewed_material",
            replace(state, material_accepted_by_pm=True, holder="controller"),
        )
        return
    if not state.pm_material_understanding_card_delivered:
        yield Transition(
            "pm_material_understanding_card_delivered",
            _prompt(
                state,
                pm_material_understanding_card_delivered=True,
                phase="material_understanding",
                holder="pm",
            ),
        )
        return
    if not state.material_understanding_written:
        yield Transition(
            "pm_writes_material_understanding_from_reviewed_sources",
            replace(state, material_understanding_written=True, holder="controller"),
        )
        return
    if not state.pm_product_architecture_card_delivered:
        yield Transition(
            "pm_product_architecture_phase_card_delivered",
            _prompt(
                state,
                pm_product_architecture_card_delivered=True,
                phase="product_architecture",
                holder="pm",
            ),
        )
        return
    if not state.product_architecture_draft_written:
        yield Transition(
            "pm_writes_product_architecture_draft",
            replace(state, product_architecture_draft_written=True, holder="controller"),
        )
        return
    if not state.product_architecture_modelability_card_delivered:
        yield Transition(
            "product_officer_product_architecture_modelability_card_delivered",
            _prompt(
                state,
                product_architecture_modelability_card_delivered=True,
                holder="officer",
            ),
        )
        return
    if not state.product_architecture_modelability_passed:
        yield Transition(
            "product_officer_product_architecture_modelability_passed",
            _mail(
                state,
                product_architecture_modelability_passed=True,
                product_architecture_officer_result_ledger_checked=True,
                holder="controller",
            ),
        )
        return
    if not state.product_architecture_challenge_card_delivered:
        yield Transition(
            "reviewer_product_architecture_challenge_card_delivered",
            _prompt(
                state,
                product_architecture_challenge_card_delivered=True,
                holder="reviewer",
            ),
        )
        return
    if not state.product_architecture_reviewer_challenged:
        yield Transition(
            "reviewer_challenges_product_architecture",
            replace(state, product_architecture_reviewer_challenged=True, holder="controller"),
        )
        return
    if not state.pm_root_contract_card_delivered:
        yield Transition(
            "pm_root_contract_phase_card_delivered",
            _prompt(state, pm_root_contract_card_delivered=True, phase="root_contract", holder="pm"),
        )
        return
    if not state.root_contract_draft_written:
        yield Transition(
            "pm_writes_root_contract_draft",
            replace(state, root_contract_draft_written=True, holder="controller"),
        )
        return
    if not state.root_contract_challenge_card_delivered:
        yield Transition(
            "reviewer_root_contract_challenge_card_delivered",
            _prompt(state, root_contract_challenge_card_delivered=True, holder="reviewer"),
        )
        return
    if not state.root_contract_reviewer_challenged:
        yield Transition(
            "reviewer_challenges_root_contract",
            replace(state, root_contract_reviewer_challenged=True, holder="controller"),
        )
        return
    if not state.root_contract_frozen_by_pm:
        yield Transition(
            "pm_freezes_root_contract",
            replace(state, root_contract_frozen_by_pm=True, holder="controller"),
        )
        return
    if not state.pm_dependency_policy_card_delivered:
        yield Transition(
            "pm_dependency_policy_phase_card_delivered",
            _prompt(state, pm_dependency_policy_card_delivered=True, phase="dependency_policy", holder="pm"),
        )
        return
    if not state.dependency_policy_recorded:
        yield Transition(
            "pm_records_dependency_policy",
            replace(state, dependency_policy_recorded=True, holder="controller"),
        )
        return
    if not state.capabilities_manifest_written:
        yield Transition(
            "pm_writes_capabilities_manifest",
            replace(state, capabilities_manifest_written=True, holder="controller"),
        )
        return
    if not state.pm_child_skill_selection_card_delivered:
        yield Transition(
            "pm_child_skill_selection_phase_card_delivered",
            _prompt(
                state,
                pm_child_skill_selection_card_delivered=True,
                phase="child_skill_selection",
                holder="pm",
            ),
        )
        return
    if not state.pm_child_skill_selection_written:
        yield Transition(
            "pm_writes_child_skill_selection",
            replace(state, pm_child_skill_selection_written=True, holder="controller"),
        )
        return
    if not state.pm_child_skill_gate_manifest_card_delivered:
        yield Transition(
            "pm_child_skill_gate_manifest_phase_card_delivered",
            _prompt(
                state,
                pm_child_skill_gate_manifest_card_delivered=True,
                phase="child_skill_gate_manifest",
                holder="pm",
            ),
        )
        return
    if not state.child_skill_gate_manifest_written:
        yield Transition(
            "pm_writes_child_skill_gate_manifest",
            replace(state, child_skill_gate_manifest_written=True, holder="controller"),
        )
        return
    if not state.reviewer_child_skill_gate_manifest_card_delivered:
        yield Transition(
            "reviewer_child_skill_gate_manifest_review_card_delivered",
            _prompt(
                state,
                reviewer_child_skill_gate_manifest_card_delivered=True,
                holder="reviewer",
            ),
        )
        return
    if not state.child_skill_manifest_reviewer_passed:
        yield Transition(
            "reviewer_passes_child_skill_gate_manifest",
            replace(state, child_skill_manifest_reviewer_passed=True, holder="controller"),
        )
        return
    if not state.child_skill_manifest_pm_approved_for_route:
        yield Transition(
            "pm_approves_child_skill_manifest_for_route",
            replace(state, child_skill_manifest_pm_approved_for_route=True, holder="controller"),
        )
        return
    if not state.capability_evidence_synced:
        yield Transition(
            "capability_evidence_synced",
            replace(state, capability_evidence_synced=True, holder="controller"),
        )
        return
    if not state.pm_prior_path_context_card_delivered:
        yield Transition(
            "pm_prior_path_context_phase_card_delivered",
            _prompt(state, pm_prior_path_context_card_delivered=True, phase="prior_path_context", holder="pm"),
        )
        return
    if (
        state.pm_prior_path_context_card_delivered
        and not state.pm_route_skeleton_card_delivered
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition("controller_refreshes_route_history_context", _refresh_history_context(state))
        return
    if (
        state.pm_prior_path_context_card_delivered
        and not state.pm_route_skeleton_card_delivered
        and not state.pm_prior_path_context_reviewed
    ):
        yield Transition("pm_reads_prior_path_context", _pm_reads_history_context(state))
        return
    if not state.pm_route_skeleton_card_delivered:
        yield Transition(
            "pm_route_skeleton_phase_card_delivered",
            _prompt(
                state,
                pm_route_skeleton_card_delivered=True,
                route_skeleton_prior_context_used=True,
                phase="route_skeleton",
                holder="pm",
            ),
        )
        return
    if not state.route_skeleton_written:
        yield Transition(
            "pm_writes_route_skeleton",
            replace(state, route_skeleton_written=True, route_skeleton_prior_context_used=True, holder="controller"),
        )
        return
    if not state.route_activated_by_pm:
        yield Transition("pm_activates_route_skeleton", _stale_history_context(replace(state, route_activated_by_pm=True, holder="controller")))
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
    if not state.pm_node_acceptance_plan_card_delivered:
        yield Transition(
            "pm_node_acceptance_plan_phase_card_delivered",
            _prompt(
                state,
                pm_node_acceptance_plan_card_delivered=True,
                phase="node_acceptance_plan",
                holder="pm",
            ),
        )
        return
    if (
        not state.node_acceptance_plan_written
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition("controller_refreshes_route_history_context_for_node", _refresh_history_context(state))
        return
    if not state.node_acceptance_plan_written and not state.pm_prior_path_context_reviewed:
        yield Transition("pm_reads_prior_path_context_for_node", _pm_reads_history_context(state))
        return
    if not state.node_acceptance_plan_written:
        yield Transition(
            "pm_writes_node_acceptance_plan_before_packet",
            replace(
                state,
                node_acceptance_plan_written=True,
                node_acceptance_plan_prior_context_used=True,
                holder="reviewer",
            ),
        )
        return
    if not state.reviewer_node_acceptance_plan_review_card_delivered:
        yield Transition(
            "reviewer_node_acceptance_plan_review_card_delivered",
            _prompt(
                state,
                reviewer_node_acceptance_plan_review_card_delivered=True,
                phase="node_acceptance_plan_review",
                holder="reviewer",
            ),
        )
        return
    if not state.node_acceptance_plan_reviewed:
        yield Transition(
            "reviewer_passes_node_acceptance_plan",
            replace(state, node_acceptance_plan_reviewed=True, holder="controller"),
        )
        return
    if not state.pm_node_packet_issued:
        yield Transition("pm_issues_current_node_packet", replace(state, pm_node_packet_issued=True, holder="controller"))
        return
    if not state.node_dispatch_allowed:
        yield Transition(
            "router_direct_current_node_dispatch_from_reviewed_acceptance_plan",
            replace(state, node_dispatch_allowed=True),
        )
        return
    if not state.node_worker_body_delivered:
        yield Transition(
            "current_node_worker_body_delivered_after_dispatch",
            _mail(state, node_worker_body_delivered=True, holder="worker"),
        )
        return
    if not state.node_worker_result_returned:
        yield Transition(
            "current_node_worker_result_returned",
            _mail(
                state,
                node_worker_result_returned=True,
                node_worker_result_ledger_checked=True,
                holder="reviewer",
            ),
        )
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
            _mail(
                state,
                node_repair_result_returned=True,
                node_repair_result_ledger_checked=True,
                holder="reviewer",
            ),
        )
        return
    if state.node_review_blocked and not state.node_repair_review_passed:
        yield Transition("reviewer_passes_current_node_repair", replace(state, node_repair_review_passed=True, holder="controller"))
        return
    if not state.node_completed_by_pm:
        yield Transition(
            "pm_completes_current_node_from_reviewed_result",
            _stale_history_context(replace(state, node_completed_by_pm=True, holder="controller")),
        )
        return
    if not state.pm_parent_backward_targets_card_delivered:
        yield Transition(
            "pm_parent_backward_targets_phase_card_delivered",
            _prompt(
                state,
                pm_parent_backward_targets_card_delivered=True,
                phase="parent_backward_targets",
                holder="pm",
            ),
        )
        return
    if not state.parent_backward_targets_enumerated:
        yield Transition(
            "pm_enumerates_parent_backward_targets",
            replace(state, parent_backward_targets_enumerated=True, holder="reviewer"),
        )
        return
    if not state.reviewer_parent_backward_replay_card_delivered:
        yield Transition(
            "reviewer_parent_backward_replay_card_delivered",
            _prompt(
                state,
                reviewer_parent_backward_replay_card_delivered=True,
                phase="parent_backward_replay",
                holder="reviewer",
            ),
        )
        return
    if not state.parent_backward_replay_passed:
        yield Transition(
            "reviewer_parent_backward_replay_passed",
            replace(state, parent_backward_replay_passed=True, holder="pm"),
        )
        return
    if not state.pm_parent_segment_decision_card_delivered:
        yield Transition(
            "pm_parent_backward_segment_decision_card_delivered",
            _prompt(
                state,
                pm_parent_segment_decision_card_delivered=True,
                phase="parent_backward_segment_decision",
                holder="pm",
            ),
        )
        return
    if (
        not state.parent_pm_segment_decision_recorded
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition("controller_refreshes_route_history_context_for_parent_segment", _refresh_history_context(state))
        return
    if not state.parent_pm_segment_decision_recorded and not state.pm_prior_path_context_reviewed:
        yield Transition("pm_reads_prior_path_context_for_parent_segment", _pm_reads_history_context(state))
        return
    if not state.parent_pm_segment_decision_recorded:
        yield Transition(
            "pm_records_parent_backward_segment_decision",
            replace(
                state,
                parent_pm_segment_decision_recorded=True,
                parent_segment_prior_context_used=True,
                holder="controller",
            ),
        )
        return
    if not state.pm_evidence_quality_package_card_delivered:
        yield Transition(
            "pm_evidence_quality_package_phase_card_delivered",
            _prompt(
                state,
                pm_evidence_quality_package_card_delivered=True,
                phase="evidence_quality_package",
                holder="pm",
            ),
        )
        return
    if not state.pm_evidence_quality_package_written:
        yield Transition(
            "pm_writes_evidence_quality_package",
            replace(
                state,
                pm_evidence_quality_package_written=True,
                evidence_quality_prior_context_used=True,
                holder="reviewer",
            ),
        )
        return
    if not state.reviewer_evidence_quality_review_card_delivered:
        yield Transition(
            "reviewer_evidence_quality_review_card_delivered",
            _prompt(
                state,
                reviewer_evidence_quality_review_card_delivered=True,
                phase="evidence_quality_review",
                holder="reviewer",
            ),
        )
        return
    if not state.evidence_quality_reviewer_passed:
        yield Transition(
            "reviewer_passes_evidence_quality_review",
            _stale_history_context(replace(state, evidence_quality_reviewer_passed=True, holder="controller")),
        )
        return
    if not state.route_history_context_refreshed or state.route_history_context_stale:
        yield Transition("controller_refreshes_route_history_context_for_final_ledger", _refresh_history_context(state))
        return
    if not state.pm_prior_path_context_reviewed:
        yield Transition("pm_reads_prior_path_context_for_final_ledger", _pm_reads_history_context(state))
        return
    if not state.pm_final_ledger_card_delivered:
        yield Transition(
            "pm_final_ledger_phase_card_delivered",
            _prompt(
                state,
                pm_final_ledger_card_delivered=True,
                final_ledger_prior_context_used=True,
                phase="final_ledger",
                holder="pm",
            ),
        )
        return
    if not state.final_ledger_built_by_pm:
        yield Transition(
            "pm_builds_final_ledger",
            replace(state, final_ledger_built_by_pm=True, final_ledger_prior_context_used=True, holder="reviewer"),
        )
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
    if state.router_loaded and not state.run_scoped_bootstrap_created:
        failures.append("new invocation loaded router without a run-scoped bootstrap")
    if state.stale_top_level_bootstrap_reused and (
        state.startup_answers_recorded
        or state.banner_emitted
        or state.run_shell_created
        or state.controller_core_loaded
    ):
        failures.append("new invocation reused stale top-level bootstrap as current startup state")
    if state.startup_questions_asked and not (
        state.startup_state_written_awaiting_answers
        and state.dialog_stopped_for_answers
    ):
        failures.append("startup questions did not atomically record the waiting stop boundary")
    if (
        state.startup_questions_asked
        and not state.startup_answers_recorded
        and state.startup_state != "awaiting_answers_stopped"
    ):
        failures.append("startup waiting stop boundary did not hold before answers were recorded")
    if (state.startup_state_written_awaiting_answers or state.dialog_stopped_for_answers) and not state.startup_questions_asked:
        failures.append("startup waiting stop boundary appeared before startup questions")
    if state.startup_answers_recorded and not state.dialog_stopped_for_answers:
        failures.append("startup answers were recorded before the waiting stop boundary")
    if state.startup_answers_recorded and not (
        state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    ):
        failures.append("startup answers were recorded without legal enum values and explicit user reply provenance")
    if state.banner_emitted and not (
        state.startup_answers_recorded and state.dialog_stopped_for_answers
    ):
        failures.append("startup banner emitted before explicit answers after a stopped dialog")
    if state.banner_emitted and not state.startup_banner_user_visible:
        failures.append("startup banner was marked emitted without user-visible display text")
    if state.banner_emitted and not state.startup_banner_user_dialog_confirmed:
        failures.append("startup banner was marked emitted without user dialog display confirmation")
    if state.run_shell_created and not state.banner_emitted:
        failures.append("run shell created before startup banner")
    if state.runtime_kit_copied and not (
        state.run_shell_created and state.current_pointer_written and state.run_index_updated
    ):
        failures.append("runtime kit copied before run shell and pointer/index files")
    if state.bootloader_generated_prompt_body:
        failures.append("bootloader generated prompt or packet body instead of copying the audited runtime kit")
    if state.user_intake_ready and not (
        state.user_request_recorded and state.user_request_provenance == "explicit_user_request"
    ):
        failures.append("user intake was prepared without an explicit user request packet source")
    if state.roles_started and not (
        state.runtime_kit_copied and state.placeholders_filled and state.mailbox_initialized
    ):
        failures.append("roles started before copied kit, placeholders, and mailbox were ready")
    if state.roles_started and not state.fresh_role_agents_started:
        failures.append("roles were marked started without fresh live role-agent evidence")
    if state.startup_fact_reported and not state.reviewer_startup_fact_check_card_delivered:
        failures.append("reviewer startup fact report was accepted before startup fact-check card delivery")
    if state.startup_activation_approved and not (
        state.startup_fact_reported and state.pm_startup_activation_card_delivered
    ):
        failures.append("startup activation was approved before reviewer facts and PM activation card")
    if state.user_intake_delivered_to_pm and not (
        state.controller_core_loaded
        and state.pm_core_delivered
        and state.pm_phase_map_delivered
        and state.pm_startup_intake_card_delivered
        and state.startup_activation_approved
        and state.user_intake_ready
    ):
        failures.append("user intake delivered before Controller, PM startup cards, and startup activation")
    if state.user_intake_delivered_to_pm and not state.user_intake_controller_relayed:
        failures.append("user intake delivered to PM without Controller relay")
    if state.controller_role_confirmed and not (
        state.controller_core_loaded
        and state.controller_boundary_confirmation_written
        and state.controller_boundary_policy_hash_recorded
    ):
        failures.append("Controller role confirmed without Router-owned controller.core boundary confirmation")
    role_output_exists = any(
        (
            state.startup_fact_reported,
            state.startup_activation_approved,
            state.pm_controller_reset_decision_returned,
            state.pm_material_scan_packets_issued,
            state.reviewer_dispatch_allowed,
            state.worker_scan_results_returned,
            state.material_review != "unknown",
            state.pm_research_package_written,
            state.research_worker_report_returned,
            state.research_reviewer_passed,
            state.material_accepted_by_pm,
            state.material_understanding_written,
            state.product_architecture_draft_written,
            state.product_architecture_modelability_passed,
            state.product_architecture_reviewer_challenged,
            state.root_contract_draft_written,
            state.root_contract_reviewer_challenged,
            state.root_contract_modelability_passed,
            state.root_contract_frozen_by_pm,
            state.dependency_policy_recorded,
            state.capabilities_manifest_written,
            state.pm_child_skill_selection_written,
            state.child_skill_gate_manifest_written,
            state.child_skill_manifest_reviewer_passed,
            state.child_skill_process_officer_passed,
            state.child_skill_product_officer_passed,
            state.child_skill_manifest_pm_approved_for_route,
            state.route_skeleton_written,
            state.route_activated_by_pm,
            state.node_acceptance_plan_written,
            state.node_acceptance_plan_reviewed,
            state.pm_node_packet_issued,
            state.node_dispatch_allowed,
            state.node_worker_result_returned,
            state.node_reviewer_reviewed_result,
            state.pm_node_repair_packet_issued,
            state.node_repair_result_returned,
            state.node_repair_review_passed,
            state.node_completed_by_pm,
            state.parent_backward_targets_enumerated,
            state.parent_backward_replay_passed,
            state.parent_pm_segment_decision_recorded,
            state.pm_evidence_quality_package_written,
            state.evidence_quality_reviewer_passed,
            state.final_ledger_built_by_pm,
            state.final_backward_replay_passed,
            state.pm_completion_decision,
        )
    )
    if role_output_exists and not (
        state.role_output_body_file_written
        and state.role_output_envelope_only_to_controller
        and state.role_output_path_hash_verified
    ):
        failures.append("role output reached Controller without file-backed body, verified path/hash, and envelope-only chat return")
    if state.role_chat_response_disclosed_body:
        failures.append("role response disclosed body, blocker, evidence, or repair details in chat")
    if state.controller_used_role_chat_body:
        failures.append("Controller used role chat body content instead of treating it as contaminated mail")
    if state.controller_direct_free_text_instruction_used:
        failures.append("Controller direct free text was treated as authority instead of router-authorized mail")
    if state.controller_inspected_router_internal_hard_checks:
        failures.append("Controller inspected router hard-check internals instead of using black-box router actions")
    if state.pm_material_scan_card_delivered and not state.controller_role_confirmed:
        failures.append("PM material scan card delivered before Controller boundary confirmation")
    if state.pm_material_scan_card_delivered and not state.user_intake_delivered_to_pm:
        failures.append("PM material scan card delivered before PM received full user intake")
    if state.pm_material_scan_card_delivered and not state.user_intake_controller_relayed:
        failures.append("PM material scan card delivered before user intake Controller relay")
    if state.pm_material_scan_packets_issued and not (
        state.controller_role_confirmed
        and state.pm_startup_intake_card_delivered
        and state.user_intake_delivered_to_pm
        and state.pm_material_scan_card_delivered
    ):
        failures.append(
            "PM issued material packets before Controller boundary confirmation, full intake delivery, and material scan card"
        )
    if state.worker_packets_delivered and not state.reviewer_dispatch_allowed:
        failures.append("worker packet bodies delivered before router direct dispatch approval")
    if state.worker_scan_results_returned and not (
        state.worker_packets_delivered and state.material_scan_result_ledger_checked
    ):
        failures.append("worker material scan result reached reviewer before packet-ledger check")
    if state.reviewer_material_sufficiency_card_delivered and not state.worker_scan_results_returned:
        failures.append("reviewer material sufficiency card delivered before worker material scan results")
    if state.material_review != "unknown" and not state.reviewer_material_sufficiency_card_delivered:
        failures.append("reviewer material sufficiency decision recorded before sufficiency card")
    if (
        state.pm_material_absorb_or_research_card_delivered
        and state.material_review == "unknown"
    ):
        failures.append("PM material absorb-or-research card delivered before reviewer material decision")
    if state.material_accepted_by_pm and not (
        state.pm_material_absorb_or_research_card_delivered
        and state.material_review == "sufficient"
    ):
        failures.append("PM absorbed material before sufficiency pass and absorb-or-research card")
    if state.pm_research_package_card_delivered and not (
        state.pm_material_absorb_or_research_card_delivered
        and state.material_review == "research_required"
    ):
        failures.append("PM research package card delivered before reviewer-required research branch")
    if state.pm_research_package_written and not state.pm_research_package_card_delivered:
        failures.append("PM wrote research package before research-package card")
    if state.research_capability_decision_recorded and not state.pm_research_package_written:
        failures.append("research capability decision recorded before PM research package")
    if (
        state.research_worker_report_card_delivered
        and not state.research_capability_decision_recorded
    ):
        failures.append("worker research report card delivered before research capability decision")
    if state.research_dispatch_allowed and not state.research_worker_report_card_delivered:
        failures.append("research direct dispatch preflight passed before worker research card")
    if state.research_worker_packet_delivered and not state.research_dispatch_allowed:
        failures.append("research worker packet body delivered before router direct dispatch approval")
    if state.research_worker_report_returned and not (
        state.research_worker_report_card_delivered
        and state.research_worker_packet_delivered
        and state.research_worker_result_ledger_checked
    ):
        failures.append("worker research report reached reviewer before packet, card, and ledger check")
    if (
        state.reviewer_research_direct_source_check_card_delivered
        and not state.research_worker_report_returned
    ):
        failures.append("reviewer research direct-source check card delivered before worker research report")
    if state.research_reviewer_direct_source_check_done and not (
        state.reviewer_research_direct_source_check_card_delivered
        and state.research_worker_report_returned
    ):
        failures.append("reviewer direct-source research check ran before card and worker report")
    if state.research_reviewer_passed and not state.research_reviewer_direct_source_check_done:
        failures.append("reviewer passed research before direct-source check")
    if state.pm_research_absorb_or_mutate_card_delivered and not state.research_reviewer_passed:
        failures.append("PM research absorb-or-mutate card delivered before reviewer research pass")
    if state.research_absorbed_by_pm and not (
        state.pm_research_absorb_or_mutate_card_delivered and state.research_reviewer_passed
    ):
        failures.append("PM absorbed research before reviewer pass and research absorb card")
    if state.pm_material_understanding_card_delivered and not (
        state.material_accepted_by_pm or state.research_absorbed_by_pm
    ):
        failures.append("PM material understanding card delivered before material or research absorption")
    if state.material_understanding_written and not (
        state.pm_material_understanding_card_delivered
        and (
            (state.material_review == "sufficient" and state.material_accepted_by_pm)
            or (
                state.material_review == "research_required"
                and state.research_absorbed_by_pm
            )
        )
    ):
        failures.append(
            "PM wrote material understanding before reviewed material or reviewed research was absorbed"
        )
    if state.pm_used_unreviewed_evidence:
        failures.append("PM used unreviewed evidence for a route or phase decision")
    if (
        state.pm_product_architecture_card_delivered
        and not state.material_understanding_written
    ):
        failures.append("product architecture card delivered before PM material understanding")
    if state.product_architecture_draft_written and not (
        state.pm_product_architecture_card_delivered and state.material_understanding_written
    ):
        failures.append("PM wrote product architecture before card and material understanding")
    if (
        state.product_architecture_modelability_card_delivered
        and not state.product_architecture_draft_written
    ):
        failures.append("product architecture modelability card delivered before architecture draft")
    if (
        state.product_architecture_modelability_passed
        and not (
            state.product_architecture_modelability_card_delivered
            and state.product_architecture_officer_result_ledger_checked
        )
    ):
        failures.append("product architecture modelability result reached PM before officer card and packet-ledger check")
    if (
        state.product_architecture_challenge_card_delivered
        and not state.product_architecture_modelability_passed
    ):
        failures.append("product architecture reviewer challenge card delivered before modelability pass")
    if (
        state.product_architecture_reviewer_challenged
        and not state.product_architecture_challenge_card_delivered
    ):
        failures.append("reviewer challenged product architecture before challenge card")
    if (
        state.pm_root_contract_card_delivered
        and not state.product_architecture_reviewer_challenged
    ):
        failures.append("PM root contract card delivered before reviewer product architecture challenge")
    if state.root_contract_draft_written and not (
        state.pm_root_contract_card_delivered
        and state.product_architecture_reviewer_challenged
    ):
        failures.append("PM wrote root contract draft before card and product architecture challenge")
    if state.root_contract_challenge_card_delivered and not state.root_contract_draft_written:
        failures.append("root contract reviewer challenge card delivered before root contract draft")
    if state.root_contract_reviewer_challenged and not state.root_contract_challenge_card_delivered:
        failures.append("reviewer challenged root contract before root contract challenge card")
    if state.root_contract_modelability_card_delivered:
        failures.append("root contract Product Officer card emitted in reviewer-only flow")
    if state.root_contract_modelability_passed:
        failures.append("root contract Product Officer pass recorded in reviewer-only flow")
    if state.root_contract_frozen_by_pm and not (
        state.root_contract_draft_written
        and state.root_contract_reviewer_challenged
    ):
        failures.append("PM froze root contract before draft and reviewer challenge")
    if state.pm_dependency_policy_card_delivered and not state.root_contract_frozen_by_pm:
        failures.append("PM dependency policy card delivered before root contract freeze")
    if state.dependency_policy_recorded and not state.pm_dependency_policy_card_delivered:
        failures.append("PM recorded dependency policy before dependency-policy card")
    if state.capabilities_manifest_written and not state.dependency_policy_recorded:
        failures.append("PM wrote capabilities manifest before dependency policy")
    if (
        state.pm_child_skill_selection_card_delivered
        and not state.capabilities_manifest_written
    ):
        failures.append("PM child-skill selection card delivered before capabilities manifest")
    if state.pm_child_skill_selection_written and not (
        state.pm_child_skill_selection_card_delivered
        and state.capabilities_manifest_written
    ):
        failures.append("PM wrote child-skill selection before card and capabilities manifest")
    if (
        state.pm_child_skill_gate_manifest_card_delivered
        and not state.pm_child_skill_selection_written
    ):
        failures.append("PM child-skill gate manifest card delivered before PM child-skill selection")
    if state.child_skill_gate_manifest_written and not (
        state.pm_child_skill_gate_manifest_card_delivered
        and state.pm_child_skill_selection_written
    ):
        failures.append("PM wrote child-skill gate manifest before PM-selected child skills")
    if (
        state.reviewer_child_skill_gate_manifest_card_delivered
        and not state.child_skill_gate_manifest_written
    ):
        failures.append("reviewer child-skill gate manifest card delivered before manifest")
    if state.child_skill_manifest_reviewer_passed and not (
        state.reviewer_child_skill_gate_manifest_card_delivered
        and state.child_skill_gate_manifest_written
    ):
        failures.append("reviewer passed child-skill manifest before review card and manifest")
    if state.process_officer_child_skill_card_delivered:
        failures.append("child-skill Process Officer card emitted in reviewer-only flow")
    if state.child_skill_process_officer_passed:
        failures.append("child-skill Process Officer pass recorded in reviewer-only flow")
    if state.product_officer_child_skill_card_delivered:
        failures.append("child-skill Product Officer card emitted in reviewer-only flow")
    if state.child_skill_product_officer_passed:
        failures.append("child-skill Product Officer pass recorded in reviewer-only flow")
    if state.child_skill_manifest_pm_approved_for_route and not state.child_skill_manifest_reviewer_passed:
        failures.append("PM approved child-skill manifest before reviewer pass")
    if state.capability_evidence_synced and not state.child_skill_manifest_pm_approved_for_route:
        failures.append("capability evidence synced before PM child-skill manifest approval")
    if state.pm_prior_path_context_card_delivered and not state.capability_evidence_synced:
        failures.append("PM prior path context card delivered before capability evidence sync")
    if state.pm_route_skeleton_card_delivered and not state.capability_evidence_synced:
        failures.append("PM route skeleton card delivered before capability evidence sync")
    if state.pm_route_skeleton_card_delivered and not (
        state.pm_prior_path_context_card_delivered
        and state.route_skeleton_prior_context_used
    ):
        failures.append("PM route skeleton card delivered before PM read fresh prior path context")
    if state.route_skeleton_written and not (
        state.pm_route_skeleton_card_delivered and state.capability_evidence_synced
    ):
        failures.append("PM wrote route skeleton before card and capability evidence sync")
    if state.route_skeleton_written and not state.route_skeleton_prior_context_used:
        failures.append("PM wrote route skeleton before reading fresh route history context")
    if state.route_activated_by_pm and not state.route_skeleton_written:
        failures.append("PM activated route before route skeleton")
    if state.node_acceptance_plan_written and not state.pm_node_acceptance_plan_card_delivered:
        failures.append("PM wrote node acceptance plan before node acceptance plan card")
    if state.node_acceptance_plan_written and not state.node_acceptance_plan_prior_context_used:
        failures.append("PM wrote node acceptance plan before reading fresh route history context")
    if state.route_mutated_by_pm and not state.route_mutation_prior_context_used:
        failures.append("PM mutated route before reading fresh route history context")
    if (
        state.reviewer_node_acceptance_plan_review_card_delivered
        and not state.node_acceptance_plan_written
    ):
        failures.append("reviewer node acceptance plan review card delivered before node acceptance plan")
    if state.node_acceptance_plan_reviewed and not (
        state.reviewer_node_acceptance_plan_review_card_delivered
        and state.node_acceptance_plan_written
    ):
        failures.append("reviewer passed node acceptance plan before review card and plan")
    if state.pm_node_packet_issued and not (
        state.pm_current_node_card_delivered
        and state.pm_node_started_event_delivered
        and state.pm_node_acceptance_plan_card_delivered
        and state.node_acceptance_plan_written
        and state.reviewer_node_acceptance_plan_review_card_delivered
        and state.node_acceptance_plan_reviewed
    ):
        failures.append("PM issued node packet before current-node cards and reviewed node acceptance plan")
    if state.node_dispatch_allowed and not (
        state.pm_node_packet_issued
        and state.node_acceptance_plan_reviewed
    ):
        failures.append("router direct current-node dispatch passed before packet and reviewed node acceptance plan")
    if state.node_worker_body_delivered and not state.node_dispatch_allowed:
        failures.append("current-node worker body delivered before router direct dispatch")
    if state.node_worker_result_returned and not (
        state.node_worker_body_delivered and state.node_worker_result_ledger_checked
    ):
        failures.append("current-node worker result reached reviewer before packet-ledger check")
    if state.pm_node_repair_packet_issued and not (
        state.pm_review_repair_card_delivered and state.pm_reviewer_blocked_event_delivered
    ):
        failures.append("PM issued repair packet before repair phase and reviewer-blocked event cards")
    if state.node_repair_result_returned and not (
        state.pm_node_repair_packet_issued and state.node_repair_result_ledger_checked
    ):
        failures.append("repair worker result reached reviewer before repair packet and packet-ledger check")
    if state.node_repair_review_passed and not state.node_repair_result_returned:
        failures.append("repair recheck passed before repair result returned to reviewer")
    if state.node_completed_by_pm and not (
        (state.node_reviewer_reviewed_result and not state.node_review_blocked)
        or (state.node_repair_result_returned and state.node_repair_review_passed)
    ):
        failures.append("PM completed node before passing reviewer result or repaired recheck")
    if state.parent_backward_targets_enumerated and not (
        state.node_completed_by_pm and state.pm_parent_backward_targets_card_delivered
    ):
        failures.append("PM enumerated parent backward targets before node completion and parent-targets card")
    if (
        state.reviewer_parent_backward_replay_card_delivered
        and not state.parent_backward_targets_enumerated
    ):
        failures.append("reviewer parent backward replay card delivered before PM parent targets")
    if state.parent_backward_replay_passed and not (
        state.reviewer_parent_backward_replay_card_delivered
        and state.parent_backward_targets_enumerated
    ):
        failures.append("parent backward replay passed before reviewer card and PM target enumeration")
    if (
        state.pm_parent_segment_decision_card_delivered
        and not state.parent_backward_replay_passed
    ):
        failures.append("PM parent segment decision card delivered before parent backward replay")
    if state.parent_pm_segment_decision_recorded and not (
        state.pm_parent_segment_decision_card_delivered
        and state.parent_backward_replay_passed
    ):
        failures.append("PM parent segment decision recorded before replay and decision card")
    if state.parent_pm_segment_decision_recorded and not state.parent_segment_prior_context_used:
        failures.append("PM parent segment decision recorded before reading fresh route history context")
    if state.pm_evidence_quality_package_written and not (
        state.pm_evidence_quality_package_card_delivered
        and state.parent_pm_segment_decision_recorded
    ):
        failures.append("PM wrote evidence/quality package before package card and parent segment decision")
    if state.pm_evidence_quality_package_written and not state.evidence_quality_prior_context_used:
        failures.append("PM wrote evidence/quality package before reading fresh route history context")
    if state.reviewer_evidence_quality_review_card_delivered and not state.pm_evidence_quality_package_written:
        failures.append("reviewer evidence quality review card delivered before PM evidence/quality package")
    if state.evidence_quality_reviewer_passed and not (
        state.reviewer_evidence_quality_review_card_delivered
        and state.pm_evidence_quality_package_written
    ):
        failures.append("reviewer passed evidence quality before review card and PM package")
    if state.pm_final_ledger_card_delivered and not state.pm_evidence_quality_package_card_delivered:
        failures.append("PM final ledger card delivered before PM evidence/quality package card")
    if state.pm_final_ledger_card_delivered and not state.evidence_quality_reviewer_passed:
        failures.append("PM final ledger card delivered before reviewer evidence quality pass")
    if state.final_ledger_built_by_pm and not (
        state.node_completed_by_pm
        and state.parent_backward_targets_enumerated
        and state.parent_backward_replay_passed
        and state.parent_pm_segment_decision_recorded
        and state.pm_final_ledger_card_delivered
        and state.evidence_quality_reviewer_passed
    ):
        failures.append("PM built final ledger before node completion, parent backward replay, PM segment decision, evidence quality reviewer pass, and final-ledger phase card")
    if state.final_ledger_built_by_pm and not state.final_ledger_prior_context_used:
        failures.append("PM built final ledger before reading fresh route history context")
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
    if state.prompt_deliveries and not state.system_card_identity_boundaries_verified:
        failures.append("system prompt delivered without verified identity-boundary header")
    if state.mail_deliveries > state.ledger_checks:
        failures.append("mail delivered without a matching packet-ledger check")
    if state.mail_deliveries and not state.packet_body_identity_boundaries_verified:
        failures.append("packet body delivered without verified recipient identity boundary")
    if (
        state.worker_scan_results_returned
        or state.research_worker_report_returned
        or state.node_worker_result_returned
        or state.node_repair_result_returned
    ) and not state.result_body_identity_boundaries_verified:
        failures.append("result body returned without verified completed-by identity boundary")
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
    if state.controller_relayed_body_content:
        failures.append("Controller relayed packet/result body content instead of envelope-only metadata")
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
        run_scoped_bootstrap_created=True,
        startup_questions_asked=True,
        startup_state_written_awaiting_answers=True,
        dialog_stopped_for_answers=True,
        startup_answer_values_valid=True,
        startup_answer_provenance="explicit_user_reply",
        startup_answers_recorded=True,
        banner_emitted=True,
        startup_banner_user_visible=True,
        run_shell_created=True,
        current_pointer_written=True,
        run_index_updated=True,
        runtime_kit_copied=True,
        placeholders_filled=True,
        mailbox_initialized=True,
        user_request_recorded=True,
        user_request_provenance="explicit_user_request",
        user_intake_ready=True,
        roles_started=True,
        fresh_role_agents_started=True,
        role_core_prompts_injected=True,
        controller_core_loaded=True,
        controller_boundary_confirmation_written=True,
        controller_boundary_policy_hash_recorded=True,
        pm_core_delivered=True,
        pm_phase_map_delivered=True,
        pm_startup_intake_card_delivered=True,
        reviewer_startup_fact_check_card_delivered=True,
        startup_fact_reported=True,
        pm_startup_activation_card_delivered=True,
        startup_activation_approved=True,
        user_intake_delivered_to_pm=True,
        user_intake_controller_relayed=True,
        controller_role_confirmed=True,
        prompt_deliveries=5,
        manifest_check_requests=5,
        manifest_checks=5,
        mail_deliveries=1,
        ledger_check_requests=1,
        ledger_checks=1,
        system_card_identity_boundaries_verified=True,
        packet_body_identity_boundaries_verified=True,
        result_body_identity_boundaries_verified=True,
        role_output_body_file_written=True,
        role_output_envelope_only_to_controller=True,
        role_output_path_hash_verified=True,
        bootloader_actions=14,
        router_action_requests=14,
    )
    return replace(base, **changes)


def _root_contract_ready(**changes: object) -> State:
    return _ready(
        pm_material_scan_card_delivered=True,
        pm_material_scan_packets_issued=True,
        reviewer_dispatch_allowed=True,
        worker_packets_delivered=True,
        worker_scan_results_returned=True,
        material_scan_result_ledger_checked=True,
        reviewer_material_sufficiency_card_delivered=True,
        material_review="sufficient",
        pm_material_absorb_or_research_card_delivered=True,
        material_accepted_by_pm=True,
        pm_material_understanding_card_delivered=True,
        material_understanding_written=True,
        pm_product_architecture_card_delivered=True,
        product_architecture_draft_written=True,
        product_architecture_modelability_card_delivered=True,
        product_architecture_modelability_passed=True,
        product_architecture_officer_result_ledger_checked=True,
        product_architecture_challenge_card_delivered=True,
        product_architecture_reviewer_challenged=True,
        pm_root_contract_card_delivered=True,
        root_contract_draft_written=True,
        root_contract_challenge_card_delivered=True,
        root_contract_reviewer_challenged=True,
        root_contract_frozen_by_pm=True,
        **changes,
    )


def _step5_ready(**changes: object) -> State:
    return _root_contract_ready(
        pm_dependency_policy_card_delivered=True,
        dependency_policy_recorded=True,
        capabilities_manifest_written=True,
        pm_child_skill_selection_card_delivered=True,
        pm_child_skill_selection_written=True,
        pm_child_skill_gate_manifest_card_delivered=True,
        child_skill_gate_manifest_written=True,
        reviewer_child_skill_gate_manifest_card_delivered=True,
        child_skill_manifest_reviewer_passed=True,
        child_skill_manifest_pm_approved_for_route=True,
        capability_evidence_synced=True,
        **changes,
    )


def _node_completed_ready(**changes: object) -> State:
    return _step5_ready(
        route_activated_by_pm=True,
        pm_current_node_card_delivered=True,
        pm_node_started_event_delivered=True,
        pm_node_acceptance_plan_card_delivered=True,
        node_acceptance_plan_written=True,
        reviewer_node_acceptance_plan_review_card_delivered=True,
        node_acceptance_plan_reviewed=True,
        pm_node_packet_issued=True,
        node_dispatch_allowed=True,
        node_worker_body_delivered=True,
        node_worker_result_returned=True,
        node_worker_result_ledger_checked=True,
        node_reviewer_reviewed_result=True,
        node_review_blocked=False,
        node_completed_by_pm=True,
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "questions_without_router": State(startup_questions_asked=True),
        "router_loaded_without_run_scoped_bootstrap": State(router_loaded=True),
        "stale_top_level_bootstrap_reused_for_answers": State(
            router_loaded=True,
            run_scoped_bootstrap_created=False,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            stale_top_level_bootstrap_reused=True,
            startup_answers_recorded=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
        ),
        "banner_before_answers": State(router_loaded=True, startup_questions_asked=True, banner_emitted=True),
        "answers_with_naked_provenance": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answers_recorded=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="naked",
        ),
        "answers_with_inferred_provenance": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answers_recorded=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="inferred",
        ),
        "answers_with_invalid_values": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answers_recorded=True,
            startup_answer_values_valid=False,
            startup_answer_provenance="explicit_user_reply",
        ),
        "run_shell_before_banner": State(router_loaded=True, startup_questions_asked=True, run_shell_created=True),
        "banner_without_router_next_action": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
            startup_answers_recorded=True,
            banner_emitted=True,
            bootloader_actions=5,
            router_action_requests=4,
        ),
        "run_shell_after_banner_without_router_next_action": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_state_written_awaiting_answers=True,
            dialog_stopped_for_answers=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
            startup_answers_recorded=True,
            banner_emitted=True,
            run_shell_created=True,
            bootloader_actions=6,
            router_action_requests=5,
        ),
        "bootloader_generates_prompts": _ready(bootloader_generated_prompt_body=True),
        "banner_emitted_without_user_visible_text": _ready(startup_banner_user_visible=False),
        "user_intake_without_explicit_user_request": _ready(
            user_request_recorded=False,
            user_request_provenance="none",
        ),
        "roles_started_without_fresh_live_agents": _ready(fresh_role_agents_started=False),
        "roles_before_runtime_kit": State(
            router_loaded=True,
            run_scoped_bootstrap_created=True,
            startup_questions_asked=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
            startup_answers_recorded=True,
            banner_emitted=True,
            roles_started=True,
        ),
        "user_intake_before_pm_cards": _ready(pm_phase_map_delivered=False),
        "startup_activation_without_reviewer_facts": _ready(
            startup_fact_reported=False,
            startup_activation_approved=True,
        ),
        "user_intake_before_startup_activation": _ready(startup_activation_approved=False),
        "user_intake_without_controller_relay": _ready(
            user_intake_delivered_to_pm=True,
            user_intake_controller_relayed=False,
        ),
        "material_scan_before_full_user_intake": _ready(
            user_intake_delivered_to_pm=False,
            user_intake_controller_relayed=False,
            pm_material_scan_card_delivered=True,
        ),
        "material_scan_without_card": _ready(pm_material_scan_packets_issued=True),
        "worker_body_without_dispatch": _ready(
            pm_material_scan_card_delivered=True,
            pm_material_scan_packets_issued=True,
            worker_packets_delivered=True,
            reviewer_dispatch_allowed=False,
        ),
        "material_scan_result_without_ledger_check": _ready(
            pm_material_scan_card_delivered=True,
            pm_material_scan_packets_issued=True,
            reviewer_dispatch_allowed=True,
            worker_packets_delivered=True,
            worker_scan_results_returned=True,
            material_scan_result_ledger_checked=False,
        ),
        "pm_accepts_unreviewed_worker_result": _ready(
            worker_scan_results_returned=True,
            material_accepted_by_pm=True,
            pm_used_unreviewed_evidence=True,
        ),
        "material_sufficiency_without_worker_result": _ready(
            reviewer_material_sufficiency_card_delivered=True,
            worker_scan_results_returned=False,
        ),
        "pm_absorbs_material_without_absorb_card": _ready(
            material_review="sufficient",
            material_accepted_by_pm=True,
        ),
        "research_package_without_required_branch": _ready(
            material_review="sufficient",
            pm_material_absorb_or_research_card_delivered=True,
            pm_research_package_card_delivered=True,
        ),
        "research_worker_report_without_capability_decision": _ready(
            material_review="research_required",
            pm_material_absorb_or_research_card_delivered=True,
            pm_research_package_card_delivered=True,
            pm_research_package_written=True,
            research_worker_report_card_delivered=True,
            research_worker_report_returned=True,
        ),
        "research_packet_without_reviewer_dispatch": _ready(
            material_review="research_required",
            pm_material_absorb_or_research_card_delivered=True,
            pm_research_package_card_delivered=True,
            pm_research_package_written=True,
            research_capability_decision_recorded=True,
            research_worker_report_card_delivered=True,
            research_worker_packet_delivered=True,
            research_dispatch_allowed=False,
        ),
        "research_worker_result_without_ledger_check": _ready(
            material_review="research_required",
            pm_material_absorb_or_research_card_delivered=True,
            pm_research_package_card_delivered=True,
            pm_research_package_written=True,
            research_capability_decision_recorded=True,
            research_worker_report_card_delivered=True,
            research_dispatch_allowed=True,
            research_worker_packet_delivered=True,
            research_worker_report_returned=True,
            research_worker_result_ledger_checked=False,
        ),
        "research_pass_without_direct_source_check": _ready(
            material_review="research_required",
            research_worker_report_card_delivered=True,
            research_dispatch_allowed=True,
            research_worker_packet_delivered=True,
            research_worker_report_returned=True,
            research_worker_result_ledger_checked=True,
            research_reviewer_passed=True,
        ),
        "officer_result_without_ledger_check": _ready(
            pm_material_understanding_card_delivered=True,
            material_understanding_written=True,
            pm_product_architecture_card_delivered=True,
            product_architecture_draft_written=True,
            product_architecture_modelability_card_delivered=True,
            product_architecture_modelability_passed=True,
            product_architecture_officer_result_ledger_checked=False,
        ),
        "product_architecture_before_research_absorbed": _ready(
            material_review="research_required",
            pm_material_absorb_or_research_card_delivered=True,
            pm_product_architecture_card_delivered=True,
        ),
        "root_contract_without_product_architecture_challenge": _ready(
            material_review="sufficient",
            material_accepted_by_pm=True,
            pm_material_understanding_card_delivered=True,
            material_understanding_written=True,
            pm_product_architecture_card_delivered=True,
            product_architecture_draft_written=True,
            product_architecture_modelability_card_delivered=True,
            product_architecture_modelability_passed=True,
            pm_root_contract_card_delivered=True,
            root_contract_draft_written=True,
        ),
        "contract_frozen_without_root_reviewer": _ready(
            root_contract_draft_written=True,
            root_contract_challenge_card_delivered=True,
            root_contract_frozen_by_pm=True,
        ),
        "capabilities_manifest_without_dependency_policy": _root_contract_ready(
            capabilities_manifest_written=True,
        ),
        "child_skill_selection_before_capabilities_manifest": _root_contract_ready(
            pm_child_skill_selection_card_delivered=True,
            pm_child_skill_selection_written=True,
        ),
        "child_skill_gate_manifest_without_pm_selection": _root_contract_ready(
            child_skill_gate_manifest_written=True,
        ),
        "child_skill_pm_approval_without_reviewer": _root_contract_ready(
            child_skill_manifest_pm_approved_for_route=True,
        ),
        "capability_evidence_sync_without_pm_approval": _root_contract_ready(
            capability_evidence_synced=True,
        ),
        "route_skeleton_before_capability_evidence_sync": _root_contract_ready(
            pm_route_skeleton_card_delivered=True,
            route_skeleton_written=True,
        ),
        "route_skeleton_before_contract_freeze": _ready(
            pm_route_skeleton_card_delivered=True,
            route_skeleton_written=True,
        ),
        "route_skeleton_without_prior_path_context": _step5_ready(
            pm_prior_path_context_card_delivered=True,
            pm_route_skeleton_card_delivered=True,
            route_skeleton_written=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
        ),
        "route_activated_without_route_skeleton": _ready(
            route_activated_by_pm=True,
        ),
        "node_acceptance_plan_without_prior_path_context": _step5_ready(
            pm_prior_path_context_card_delivered=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_acceptance_plan_card_delivered=True,
            node_acceptance_plan_written=True,
        ),
        "node_packet_without_node_cards": _step5_ready(
            route_activated_by_pm=True,
            pm_node_packet_issued=True,
        ),
        "node_packet_without_acceptance_plan_review": _step5_ready(
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_packet_issued=True,
        ),
        "direct_dispatch_without_reviewed_acceptance_plan": _step5_ready(
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_acceptance_plan_card_delivered=True,
            node_acceptance_plan_written=True,
            pm_node_packet_issued=True,
            node_dispatch_allowed=True,
        ),
        "direct_dispatch_without_packet": _step5_ready(
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_acceptance_plan_card_delivered=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_review_card_delivered=True,
            node_acceptance_plan_reviewed=True,
            pm_node_packet_issued=False,
            node_dispatch_allowed=True,
        ),
        "node_worker_result_without_ledger_check": _step5_ready(
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_acceptance_plan_card_delivered=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_review_card_delivered=True,
            node_acceptance_plan_reviewed=True,
            pm_node_packet_issued=True,
            node_dispatch_allowed=True,
            node_worker_body_delivered=True,
            node_worker_result_returned=True,
            node_worker_result_ledger_checked=False,
        ),
        "repair_issued_without_block_event_card": _ready(
            node_reviewer_reviewed_result=True,
            node_review_blocked=True,
            pm_node_repair_packet_issued=True,
        ),
        "repair_result_without_ledger_check": _ready(
            node_reviewer_reviewed_result=True,
            node_review_blocked=True,
            pm_review_repair_card_delivered=True,
            pm_reviewer_blocked_event_delivered=True,
            pm_node_repair_packet_issued=True,
            node_repair_result_returned=True,
            node_repair_result_ledger_checked=False,
        ),
        "repair_recheck_bypasses_reviewer_result": _ready(
            node_reviewer_reviewed_result=True,
            node_review_blocked=True,
            pm_review_repair_card_delivered=True,
            pm_reviewer_blocked_event_delivered=True,
            pm_node_repair_packet_issued=True,
            node_repair_review_passed=True,
            node_repair_result_returned=False,
        ),
        "route_mutation_without_prior_path_context": _step5_ready(
            pm_prior_path_context_card_delivered=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_activated_by_pm=True,
            pm_current_node_card_delivered=True,
            pm_node_started_event_delivered=True,
            pm_node_acceptance_plan_card_delivered=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_review_card_delivered=True,
            node_acceptance_plan_reviewed=True,
            pm_node_packet_issued=True,
            node_dispatch_allowed=True,
            node_worker_body_delivered=True,
            node_worker_result_returned=True,
            node_worker_result_ledger_checked=True,
            node_reviewer_reviewed_result=True,
            node_review_blocked=True,
            route_mutated_by_pm=True,
        ),
        "parent_backward_replay_without_targets": _node_completed_ready(
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
        ),
        "parent_pm_segment_decision_without_replay": _node_completed_ready(
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
        ),
        "final_ledger_card_before_evidence_quality_package_card": _node_completed_ready(
            pm_parent_backward_targets_card_delivered=True,
            parent_backward_targets_enumerated=True,
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
            pm_final_ledger_card_delivered=True,
        ),
        "final_ledger_card_before_reviewer_evidence_quality_pass": _node_completed_ready(
            pm_parent_backward_targets_card_delivered=True,
            parent_backward_targets_enumerated=True,
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
            pm_evidence_quality_package_card_delivered=True,
            pm_evidence_quality_package_written=True,
            reviewer_evidence_quality_review_card_delivered=True,
            pm_final_ledger_card_delivered=True,
        ),
        "final_ledger_built_before_reviewer_evidence_quality_pass": _node_completed_ready(
            pm_parent_backward_targets_card_delivered=True,
            parent_backward_targets_enumerated=True,
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
            pm_evidence_quality_package_card_delivered=True,
            pm_evidence_quality_package_written=True,
            reviewer_evidence_quality_review_card_delivered=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
        ),
        "final_ledger_before_parent_backward_decision": _node_completed_ready(
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
        ),
        "final_ledger_before_node_completion": _ready(
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
        ),
        "final_ledger_without_prior_path_context": _node_completed_ready(
            pm_parent_backward_targets_card_delivered=True,
            parent_backward_targets_enumerated=True,
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
            pm_evidence_quality_package_card_delivered=True,
            pm_evidence_quality_package_written=True,
            reviewer_evidence_quality_review_card_delivered=True,
            evidence_quality_reviewer_passed=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
        ),
        "complete_before_closure_cleanup": _node_completed_ready(
            pm_parent_backward_targets_card_delivered=True,
            parent_backward_targets_enumerated=True,
            reviewer_parent_backward_replay_card_delivered=True,
            parent_backward_replay_passed=True,
            pm_parent_segment_decision_card_delivered=True,
            parent_pm_segment_decision_recorded=True,
            pm_evidence_quality_package_card_delivered=True,
            pm_evidence_quality_package_written=True,
            reviewer_evidence_quality_review_card_delivered=True,
            evidence_quality_reviewer_passed=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built_by_pm=True,
            final_backward_replay_passed=True,
            pm_completion_decision=True,
        ),
        "prompt_delivery_without_manifest_check": _ready(prompt_deliveries=4, manifest_checks=3),
        "mail_delivery_without_ledger_check": _ready(mail_deliveries=2, ledger_checks=1),
        "controller_reads_body": _ready(controller_read_forbidden_body=True),
        "controller_creates_project_evidence": _ready(controller_origin_project_evidence=True),
        "controller_relays_body_content": _ready(controller_relayed_body_content=True),
        "role_chat_response_discloses_body": _ready(role_chat_response_disclosed_body=True),
        "controller_uses_role_chat_body": _ready(controller_used_role_chat_body=True),
        "controller_direct_free_text_instruction": _ready(controller_direct_free_text_instruction_used=True),
        "controller_inspects_router_hard_checks": _ready(controller_inspected_router_internal_hard_checks=True),
        "role_output_without_file_backed_envelope": _ready(
            role_output_body_file_written=False,
            role_output_envelope_only_to_controller=False,
            role_output_path_hash_verified=False,
        ),
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
