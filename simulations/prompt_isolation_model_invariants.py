"""Invariants for the FlowPilot prompt-isolation model."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from prompt_isolation_model_state import State
from prompt_isolation_model_transitions import _bootloader_fact_count


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
    if state.startup_intake_ui_completed and not state.router_loaded:
        failures.append("startup intake options were asked without loading the bootloader router")
    if state.router_loaded and not state.run_scoped_bootstrap_created:
        failures.append("new invocation loaded router without a run-scoped bootstrap")
    if state.stale_top_level_bootstrap_reused and (
        state.startup_answers_recorded
        or state.banner_emitted
        or state.run_shell_created
        or state.controller_core_loaded
    ):
        failures.append("new invocation reused stale top-level bootstrap as current startup state")
    if state.startup_intake_ui_completed and not (
        state.startup_intake_result_recorded
        and state.startup_intake_body_boundary_enforced
    ):
        failures.append("startup intake options did not atomically record the waiting stop boundary")
    if (
        state.startup_intake_ui_completed
        and not state.startup_answers_recorded
        and state.startup_state != "awaiting_answers_stopped"
    ):
        failures.append("startup waiting stop boundary did not hold before answers were recorded")
    if (state.startup_intake_result_recorded or state.startup_intake_body_boundary_enforced) and not state.startup_intake_ui_completed:
        failures.append("startup waiting stop boundary appeared before startup intake options")
    if state.startup_answers_recorded and not state.startup_intake_body_boundary_enforced:
        failures.append("startup answers were recorded before the waiting stop boundary")
    if state.startup_answers_recorded and not (
        state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    ):
        failures.append("startup answers were recorded without legal enum values and explicit user reply provenance")
    if state.banner_emitted and not (
        state.startup_answers_recorded and state.startup_intake_body_boundary_enforced
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
    if state.roles_started and not state.fresh_role_bindings_started:
        failures.append("roles were marked started without fresh current-run role-binding evidence")
    if state.startup_runtime_mechanical_audit_written and not state.startup_runtime_entry_completed:
        failures.append("startup mechanical audit was recorded before Runtime startup entry completed")
    if state.startup_user_intake_released_to_pm and not (
        state.startup_runtime_mechanical_audit_written and state.startup_display_status_written
    ):
        failures.append("startup user intake was released before Runtime mechanical audit and display status")
    if state.user_intake_delivered_to_pm and not (
        state.controller_core_loaded
        and state.pm_core_delivered
        and state.pm_phase_map_delivered
        and state.pm_startup_intake_card_delivered
        and state.startup_user_intake_released_to_pm
        and state.user_intake_ready
    ):
        failures.append("user intake delivered before Controller, PM startup cards, and Runtime startup entry")
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
            state.startup_runtime_mechanical_audit_written,
            state.startup_user_intake_released_to_pm,
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
            state.child_skill_flowguard_operator_route_scope_passed,
            state.child_skill_flowguard_operator_product_scope_passed,
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
            and state.product_architecture_flowguard_operator_result_ledger_checked
        )
    ):
        failures.append("product architecture modelability result reached PM before FlowGuard operator card and packet-ledger check")
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
        failures.append("root contract FlowGuard operator product-scope card emitted in reviewer-only flow")
    if state.root_contract_modelability_passed:
        failures.append("root contract FlowGuard operator product-scope pass recorded in reviewer-only flow")
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
    if state.flowguard_operator_child_skill_route_card_delivered:
        failures.append("child-skill FlowGuard operator route-scope card emitted in reviewer-only flow")
    if state.child_skill_flowguard_operator_route_scope_passed:
        failures.append("child-skill FlowGuard operator route-scope pass recorded in reviewer-only flow")
    if state.flowguard_operator_child_skill_product_card_delivered:
        failures.append("child-skill FlowGuard operator product-scope card emitted in reviewer-only flow")
    if state.child_skill_flowguard_operator_product_scope_passed:
        failures.append("child-skill FlowGuard operator product-scope pass recorded in reviewer-only flow")
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
        and state.continuation_boundary_recorded
        and state.role_binding_ledger_archived
    ):
        failures.append("PM completion decision before closure card, final replay, lifecycle, continuation cleanup, and role binding archive")
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
            "Bootloader, Controller, PM, Reviewer, Worker, and FlowGuard operator can only "
            "act from current prompt cards, manifest checks, ledger checks, and "
            "reviewed packet evidence."
        ),
        predicate=prompt_isolation_invariant,
    ),
)


__all__ = ["INVARIANTS", "invariant_failures", "prompt_isolation_invariant"]

