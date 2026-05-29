"""Transition rules for the FlowPilot prompt-isolation model."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from flowguard import FunctionResult

from prompt_isolation_model_state import Action, State, Tick, Transition


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
    if not state.startup_intake_ui_completed:
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
        state.startup_intake_ui_completed
        or state.startup_intake_result_recorded
        or state.startup_intake_body_boundary_enforced
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
    if not state.startup_intake_ui_completed:
        yield Transition(
            "startup_intake_ui_completed_from_router",
            _boot(
                state,
                startup_intake_ui_completed=True,
                startup_intake_result_recorded=True,
                startup_intake_body_boundary_enforced=True,
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


__all__ = [
    "PromptIsolationStep",
    "next_safe_states",
    "_boot",
    "_bootloader_fact_count",
    "_mail",
    "_next_required_bootloader_action",
    "_next_required_channel",
    "_pm_reads_history_context",
    "_prompt",
    "_refresh_history_context",
    "_request_ledger_check",
    "_request_manifest_check",
    "_request_router_action",
    "_role_return",
    "_stale_history_context",
]
