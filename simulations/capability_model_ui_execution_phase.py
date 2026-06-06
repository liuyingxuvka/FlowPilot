"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS",
    "FunctionResult",
    "Iterable",
    "MAX_QUALITY_REWORKS",
    "MAX_STANDARD_EXPANSIONS",
    "MAX_UI_VISUAL_ITERATIONS",
    "MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER",
    "MODEL_DYNAMIC_LAYER_COUNT",
    "REQUIRED_RISK_FAMILY_MASK",
    "State",
    "_capability_backward_review_steps",
    "_final_route_wide_gate_ledger_steps",
    "_reset_execution_quality_gates",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_ui_execution_phase"]


def apply_ui_execution_phase(self, state: State) -> Iterable[FunctionResult]:
    if state.task_kind == "ui":
        if not state.ui_autonomous_pipeline_selected:
            yield _step(
                state,
                label="ui_autonomous_pipeline_selected",
                action="PM selects autonomous-concept-ui-redesign as the default UI child-skill orchestrator",
                ui_autonomous_pipeline_selected=True,
            )
            return
        if not state.ui_inspected:
            yield _step(
                state,
                label="ui_inspected",
                action="autonomous UI pipeline inspects current UI/product before concept or implementation work",
                ui_inspected=True,
            )
            return
        if not state.ui_concept_done:
            yield _step(
                state,
                label="ui_concept_done",
                action="run autonomous UI pipeline product framing and concept-led design contract gate",
                ui_concept_done=True,
            )
            return
        if not state.ui_palette_contract_written:
            yield _step(
                state,
                label="ui_palette_contract_written",
                action="extract UI skill color, background, accent, theme-default, and override rules into the design contract",
                ui_palette_contract_written=True,
            )
            return
        if not state.ui_palette_default_or_override_rationale_recorded:
            yield _step(
                state,
                label="ui_palette_default_or_override_rationale_recorded",
                action="record the default palette/background decision or the explicit user-backed override rationale before concept review continues",
                ui_palette_default_or_override_rationale_recorded=True,
            )
            return
        if not state.ui_concept_target_ready:
            yield _step(
                state,
                label="ui_concept_target_ready",
                action="record the source UI skill's pre-implementation concept-target or reference decision",
                ui_concept_target_ready=True,
            )
            return
        if not state.ui_concept_target_visible:
            yield _step(
                state,
                label="ui_concept_target_visible",
                action="show the source UI skill's target/reference decision or record its waiver before implementation planning",
                ui_concept_target_visible=True,
            )
            return
        if not state.ui_selected_concept_bound_to_review_packet:
            yield _step(
                state,
                label="ui_selected_concept_bound_to_review_packet",
                action="bind the selected concept image, icon direction, palette contract, and reference target into the reviewer packet",
                ui_selected_concept_bound_to_review_packet=True,
            )
            return
        if not state.ui_concept_personal_visual_review_done:
            yield _step(
                state,
                label="ui_concept_personal_visual_review_done",
                action="human-like reviewer personally inspects the concept image instead of relying on a worker summary",
                ui_concept_personal_visual_review_done=True,
            )
            return
        if not state.ui_concept_design_recommendations_recorded:
            yield _step(
                state,
                label="ui_concept_design_recommendations_recorded",
                action="human-like reviewer records concrete concept improvement ideas or states why no concept repair is needed",
                ui_concept_design_recommendations_recorded=True,
            )
            return
        if not state.ui_concept_aesthetic_review_done:
            yield _step(
                state,
                label="ui_concept_aesthetic_review_passed",
                action="human-like reviewer records aesthetic verdict and concrete reasons for concept beauty, weakness, or polish before implementation planning",
                ui_concept_aesthetic_review_done=True,
                ui_concept_aesthetic_reasons_recorded=True,
            )
            if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                yield _step(
                    state,
                    label="ui_concept_aesthetic_review_failed",
                    action="human-like reviewer rejects the concept aesthetics with concrete ugly/weak reasons and sends it back for concept regeneration",
                    ui_concept_target_ready=False,
                    ui_concept_target_visible=False,
                    ui_selected_concept_bound_to_review_packet=False,
                    ui_concept_personal_visual_review_done=False,
                    ui_concept_design_recommendations_recorded=False,
                    ui_concept_aesthetic_review_done=False,
                    ui_concept_aesthetic_reasons_recorded=False,
                    ui_frontend_design_plan_done=False,
                    ui_frontend_design_execution_report_written=False,
                    ui_iteration_budget_recorded=False,
                    ui_iteration_rounds_required=0,
                    ui_iteration_rounds_completed=0,
                    ui_major_visual_deviation_triaged=False,
                    ui_structural_redesign_route_considered=False,
                    visual_asset_scope="unknown",
                    visual_asset_style_review_done=False,
                    visual_asset_personal_visual_review_done=False,
                    visual_asset_design_recommendations_recorded=False,
                    visual_asset_aesthetic_review_done=False,
                    visual_asset_aesthetic_reasons_recorded=False,
                    ui_visual_iterations=state.ui_visual_iterations + 1,
                )
            return
        if not state.ui_frontend_design_plan_done:
            yield _step(
                state,
                label="ui_frontend_design_plan_done",
                action="autonomous UI pipeline briefs frontend-design for implementation planning",
                ui_frontend_design_plan_done=True,
            )
            return
        if not state.ui_frontend_design_execution_report_written:
            yield _step(
                state,
                label="ui_frontend_design_execution_report_written",
                action="write the frontend-design execution report with selected concept, palette contract, layout rules, interaction map, and deviations",
                ui_frontend_design_execution_report_written=True,
            )
            return
        if not state.ui_iteration_budget_recorded:
            yield _step(
                state,
                label="ui_iteration_budget_recorded",
                action="record UI child-skill iteration budget from source skill defaults and PM risk level before implementation starts",
                ui_iteration_budget_recorded=True,
                ui_iteration_rounds_required=DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS,
                ui_iteration_rounds_completed=0,
            )
            return
        if state.visual_asset_scope == "unknown":
            yield _step(
                state,
                label="visual_asset_not_required",
                action="record that this UI route has no app icon or product imagery changes",
                visual_asset_scope="none",
            )
            yield _step(
                state,
                label="visual_asset_required",
                action="record that this UI route creates app icons or product imagery",
                visual_asset_scope="required",
            )
            return
        if (
            state.visual_asset_scope == "required"
            and not state.visual_asset_style_review_done
        ):
            yield _step(
                state,
                label="visual_asset_style_review_done",
                action="record source UI skill evidence for in-scope product-facing visual assets",
                visual_asset_style_review_done=True,
            )
            return
        if (
            state.visual_asset_scope == "required"
            and not state.visual_asset_personal_visual_review_done
        ):
            yield _step(
                state,
                label="visual_asset_personal_visual_review_done",
                action="human-like reviewer personally inspects product-facing visual assets instead of relying on an asset report",
                visual_asset_personal_visual_review_done=True,
            )
            return
        if (
            state.visual_asset_scope == "required"
            and not state.visual_asset_design_recommendations_recorded
        ):
            yield _step(
                state,
                label="visual_asset_design_recommendations_recorded",
                action="human-like reviewer records concrete visual-asset improvement ideas or states why no asset repair is needed",
                visual_asset_design_recommendations_recorded=True,
            )
            return
        if (
            state.visual_asset_scope == "required"
            and not state.visual_asset_aesthetic_review_done
        ):
            yield _step(
                state,
                label="visual_asset_aesthetic_review_passed",
                action="human-like reviewer records app-icon or visual-asset aesthetic verdict with concrete reasons before UI implementation",
                visual_asset_aesthetic_review_done=True,
                visual_asset_aesthetic_reasons_recorded=True,
            )
            if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                yield _step(
                    state,
                    label="visual_asset_aesthetic_review_failed",
                    action="human-like reviewer rejects app-icon or visual-asset aesthetics with concrete ugly/weak reasons and sends it back for regeneration",
                    visual_asset_style_review_done=False,
                    visual_asset_personal_visual_review_done=False,
                    visual_asset_design_recommendations_recorded=False,
                    visual_asset_aesthetic_review_done=False,
                    visual_asset_aesthetic_reasons_recorded=False,
                    ui_visual_iterations=state.ui_visual_iterations + 1,
                )
            return
        if not state.ui_implemented:
            yield _step(
                state,
                label="ui_implemented",
                action="implement UI using local architecture",
                ui_implemented=True,
                role_memory_refreshed_after_work=False,
            )
            return
        if not state.ui_screenshot_qa_done:
            if not state.worker_child_skill_use_evidence_returned:
                yield _step(
                    state,
                    label="worker_child_skill_use_evidence_returned",
                    action="UI worker returns Child Skill Use Evidence proving the bound child skill source was opened, applied to the current node slice, and any stricter child-skill standard was followed or explicitly waived",
                    worker_child_skill_use_evidence_returned=True,
                )
                return
            yield _step(
                state,
                label="ui_screenshot_qa_done",
                action="run rendered screenshot QA after autonomous UI implementation",
                ui_screenshot_qa_done=True,
            )
            return
        if not state.ui_geometry_qa_done:
            yield _step(
                state,
                label="ui_geometry_qa_done",
                action="run autonomous UI geometry QA for text overflow, overlap, viewport fit, and high-DPI/window-size risks",
                ui_geometry_qa_done=True,
            )
            return
        if not state.ui_reviewer_personal_walkthrough_done:
            yield _step(
                state,
                label="ui_reviewer_personal_walkthrough_done",
                action="human-like reviewer personally launches or opens the UI and walks through rendered states instead of reading the QA report only",
                ui_reviewer_personal_walkthrough_done=True,
            )
            return
        if not state.ui_visible_affordance_interaction_matrix_written:
            yield _step(
                state,
                label="ui_visible_affordance_interaction_matrix_written",
                action="enumerate every visible button, tab, nav item, window control, tray action, language toggle, and route control into an interaction matrix",
                ui_visible_affordance_interaction_matrix_written=True,
            )
            return
        if not state.ui_visible_affordance_interaction_matrix_complete:
            yield _step(
                state,
                label="ui_visible_affordance_interaction_matrix_complete",
                action="verify every visible interactive affordance has an expected response, tested result, and repair decision before reachability passes",
                ui_visible_affordance_interaction_matrix_complete=True,
            )
            return
        if not state.ui_interaction_reachability_checked:
            yield _step(
                state,
                label="ui_interaction_reachability_checked",
                action="human-like reviewer personally checks clicks, tabs, language switching, settings, support, tray lifecycle, and required interactive reachability",
                ui_interaction_reachability_checked=True,
            )
            return
        if not state.ui_layout_overlap_density_checked:
            yield _step(
                state,
                label="ui_layout_overlap_density_checked",
                action="human-like reviewer personally checks text overlap, clipping, whitespace, density, crowded controls, hierarchy, and responsive layout fit",
                ui_layout_overlap_density_checked=True,
            )
            return
        if not state.ui_reviewer_design_recommendations_recorded:
            yield _step(
                state,
                label="ui_reviewer_design_recommendations_recorded",
                action="human-like reviewer records concrete UI repair or enhancement suggestions before passing aesthetic/divergence closure",
                ui_reviewer_design_recommendations_recorded=True,
            )
            return
        if not state.ui_implementation_aesthetic_review_done:
            yield _step(
                state,
                label="ui_implementation_aesthetic_review_passed",
                action="human-like reviewer records rendered UI aesthetic verdict with concrete reasons before divergence closure",
                ui_implementation_aesthetic_review_done=True,
                ui_implementation_aesthetic_reasons_recorded=True,
            )
            if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                yield _step(
                    state,
                    label="ui_implementation_aesthetic_review_failed",
                    action="human-like reviewer rejects rendered UI aesthetics with concrete ugly/weak reasons and sends it back for UI repair",
                    ui_implemented=False,
                    ui_screenshot_qa_done=False,
                    ui_geometry_qa_done=False,
                    ui_reviewer_personal_walkthrough_done=False,
                    ui_visible_affordance_interaction_matrix_written=False,
                    ui_visible_affordance_interaction_matrix_complete=False,
                    ui_interaction_reachability_checked=False,
                    ui_layout_overlap_density_checked=False,
                    ui_reviewer_design_recommendations_recorded=False,
                    ui_implementation_aesthetic_review_done=False,
                    ui_implementation_aesthetic_reasons_recorded=False,
                    ui_concept_vs_implementation_deviation_table_written=False,
                    ui_iteration_rounds_completed=0,
                    ui_major_visual_deviation_triaged=False,
                    ui_structural_redesign_route_considered=False,
                    ui_visual_iterations=state.ui_visual_iterations + 1,
                )
            return
        if not state.ui_concept_vs_implementation_deviation_table_written:
            yield _step(
                state,
                label="ui_concept_vs_implementation_deviation_table_written",
                action="write concept-vs-implementation deviation table covering palette, typography, layout, controls, icon direction, animation, density, and interaction gaps",
                ui_concept_vs_implementation_deviation_table_written=True,
            )
            return
        if not state.ui_divergence_review_done:
            yield _step(
                state,
                label="ui_divergence_review_done",
                action="record the source UI skill's divergence or comparison decision",
                ui_divergence_review_done=True,
            )
            return
        if not state.ui_major_visual_deviation_triaged:
            yield _step(
                state,
                label="ui_major_visual_deviation_triaged",
                action="classify concept divergence, inert controls, style collapse, palette override, and missing skill-loop evidence as pass, repair, or structural blocker",
                ui_major_visual_deviation_triaged=True,
            )
            return
        if not state.ui_structural_redesign_route_considered:
            yield _step(
                state,
                label="ui_structural_redesign_route_considered",
                action="record whether UI deviations require a structural redesign route instead of cosmetic iteration closure",
                ui_structural_redesign_route_considered=True,
            )
            return
        if (
            state.ui_iteration_budget_recorded
            and state.ui_iteration_rounds_completed
            < state.ui_iteration_rounds_required
        ):
            yield _step(
                state,
                label="ui_iteration_budget_satisfied",
                action="complete the required UI child-skill design/review/repair iteration budget before closing the visual loop",
                ui_iteration_rounds_completed=state.ui_iteration_rounds_required,
            )
            return
        if not state.ui_visual_iteration_loop_closed:
            if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                yield _step(
                    state,
                    label="ui_visual_iteration_needed",
                    action="rerun UI child-skill work after its loop decision changes required evidence",
                    ui_concept_target_ready=False,
                    ui_concept_target_visible=False,
                    ui_selected_concept_bound_to_review_packet=False,
                    ui_concept_personal_visual_review_done=False,
                    ui_concept_design_recommendations_recorded=False,
                    ui_concept_aesthetic_review_done=False,
                    ui_concept_aesthetic_reasons_recorded=False,
                    ui_frontend_design_plan_done=False,
                    ui_frontend_design_execution_report_written=False,
                    ui_iteration_budget_recorded=False,
                    ui_iteration_rounds_required=0,
                    ui_iteration_rounds_completed=0,
                    ui_major_visual_deviation_triaged=False,
                    ui_structural_redesign_route_considered=False,
                    visual_asset_scope="unknown",
                    visual_asset_style_review_done=False,
                    visual_asset_personal_visual_review_done=False,
                    visual_asset_design_recommendations_recorded=False,
                    visual_asset_aesthetic_review_done=False,
                    visual_asset_aesthetic_reasons_recorded=False,
                    ui_implemented=False,
                    ui_screenshot_qa_done=False,
                    ui_geometry_qa_done=False,
                    ui_reviewer_personal_walkthrough_done=False,
                    ui_visible_affordance_interaction_matrix_written=False,
                    ui_visible_affordance_interaction_matrix_complete=False,
                    ui_interaction_reachability_checked=False,
                    ui_layout_overlap_density_checked=False,
                    ui_reviewer_design_recommendations_recorded=False,
                    ui_implementation_aesthetic_review_done=False,
                    ui_implementation_aesthetic_reasons_recorded=False,
                    ui_concept_vs_implementation_deviation_table_written=False,
                    ui_divergence_review_done=False,
                    worker_child_skill_use_evidence_returned=False,
                    reviewer_child_skill_use_evidence_checked=False,
                    child_skill_manifest_only_evidence_rejected=False,
                    child_skill_execution_reports_written=False,
                    child_skill_execution_evidence_audited=False,
                    child_skill_evidence_matches_outputs=False,
                    child_skill_domain_quality_checked=False,
                    child_skill_iteration_loop_closed=False,
                    child_skill_completion_verified=False,
                    ui_visual_iterations=state.ui_visual_iterations + 1,
                )
            yield _step(
                state,
                label="ui_visual_iteration_loop_closed",
                action="record the source UI skill's loop-closure decision",
                ui_visual_iteration_loop_closed=True,
            )
            return
        if not state.child_skill_manifest_only_evidence_rejected:
            yield _step(
                state,
                label="child_skill_manifest_only_evidence_rejected",
                action="reject manifest-only UI child-skill evidence and require execution artifacts, screenshots, interaction matrix, deviation table, or reviewer-owned observations",
                child_skill_manifest_only_evidence_rejected=True,
            )
            return
        if not state.child_skill_execution_reports_written:
            yield _step(
                state,
                label="child_skill_execution_reports_written",
                action="write per-invoked-UI-skill execution reports covering required steps, palette decisions, iteration budget, deviations, waivers, and reviewer findings",
                child_skill_execution_reports_written=True,
            )
            return
        if not state.child_skill_execution_evidence_audited:
            yield _step(
                state,
                label="child_skill_execution_evidence_audited",
                action="audit UI child-skill step evidence against mapped requirements",
                child_skill_execution_evidence_audited=True,
            )
            return
        if not state.child_skill_evidence_matches_outputs:
            yield _step(
                state,
                label="child_skill_evidence_matches_outputs",
                action="confirm UI child-skill evidence matches actual rendered outputs",
                child_skill_evidence_matches_outputs=True,
            )
            return
        if not state.child_skill_domain_quality_checked:
            yield _step(
                state,
                label="child_skill_domain_quality_checked",
                action="check UI child-skill output quality against parent node goal",
                child_skill_domain_quality_checked=True,
            )
            return
        if not state.child_skill_iteration_loop_closed:
            yield _step(
                state,
                label="child_skill_iteration_loop_closed",
                action="close UI child-skill conformance loop before final verification",
                child_skill_iteration_loop_closed=True,
            )
            return
        if not state.current_node_skill_improvement_check_done:
            yield _step(
                state,
                label="skill_improvement_observation_check_no_issue",
                action="PM asks the UI capability roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found",
                current_node_skill_improvement_check_done=True,
            )
            yield _step(
                state,
                label="skill_improvement_observation_logged",
                action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance while continuing the UI project",
                current_node_skill_improvement_check_done=True,
                flowpilot_improvement_live_report_updated=True,
            )
            return
        if not state.role_memory_refreshed_after_work:
            yield _step(
                state,
                label="role_memory_packets_refreshed_after_capability_work",
                action="refresh compact role memory packets after UI implementation evidence and before final verification",
                role_memory_refreshed_after_work=True,
            )
            return
        if not state.final_verification_done:
            yield _step(
                state,
                label="final_verification_done",
                action="run final functional and visual verification",
                final_verification_done=True,
            )
            return
        if not state.anti_rough_finish_done:
            yield _step(
                state,
                label="anti_rough_finish_passed",
                action="review the verified UI result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                anti_rough_finish_done=True,
            )
            if (
                state.quality_reworks < MAX_QUALITY_REWORKS
                and state.standard_expansions == 0
            ):
                yield _step(
                    state,
                    label="anti_rough_finish_found_rework",
                    action="record bounded UI rework because the route is still too thin or weakly evidenced",
                    ui_implemented=False,
                    ui_screenshot_qa_done=False,
                    ui_geometry_qa_done=False,
                    ui_reviewer_personal_walkthrough_done=False,
                    ui_visible_affordance_interaction_matrix_written=False,
                    ui_visible_affordance_interaction_matrix_complete=False,
                    ui_interaction_reachability_checked=False,
                    ui_layout_overlap_density_checked=False,
                    ui_reviewer_design_recommendations_recorded=False,
                    ui_implementation_aesthetic_review_done=False,
                    ui_implementation_aesthetic_reasons_recorded=False,
                    ui_concept_vs_implementation_deviation_table_written=False,
                    ui_divergence_review_done=False,
                    ui_iteration_rounds_completed=0,
                    ui_major_visual_deviation_triaged=False,
                    ui_structural_redesign_route_considered=False,
                    ui_visual_iteration_loop_closed=False,
                    child_skill_execution_evidence_audited=False,
                    child_skill_evidence_matches_outputs=False,
                    child_skill_domain_quality_checked=False,
                    child_skill_iteration_loop_closed=False,
                    child_skill_completion_verified=False,
                    final_verification_done=False,
                    manual_resume_binding_health_checked=False,
                    quality_reworks=state.quality_reworks + 1,
                    **_reset_execution_quality_gates(),
                )
            return
        if not state.worker_output_ready_for_review:
            yield _step(
                state,
                label="worker_output_ready_for_review",
                action="record that UI worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                worker_output_ready_for_review=True,
            )
            return
        if not state.pm_review_release_order_written:
            yield _step(
                state,
                label="pm_review_release_order_written",
                action="project manager writes the UI review release order naming the gate, evidence paths, reviewer scope, and required inspections",
                pm_review_release_order_written=True,
            )
            return
        if not state.pm_released_reviewer_for_current_gate:
            yield _step(
                state,
                label="pm_released_reviewer_for_current_gate",
                action="project manager explicitly releases the reviewer to start UI inspection after worker output is ready",
                pm_released_reviewer_for_current_gate=True,
            )
            return
        if not state.packet_runtime_physical_files_written:
            yield _step(
                state,
                label="packet_runtime_physical_isolation_verified",
                action="packet runtime writes UI physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                packet_runtime_physical_files_written=True,
                controller_context_body_exclusion_verified=True,
            )
            return
        if not state.packet_mail_chain_audit_done:
            yield _step(
                state,
                label="controller_mail_relay_chain_audit_done",
                action="reviewer verifies UI packet/result controller relay signatures, recipient pre-open checks, no private role-to-role mail, and PM restart/repair/reissue handling for unopened or contaminated mail",
                controller_relay_signature_audit_done=True,
                recipient_pre_open_relay_check_done=True,
                packet_mail_chain_audit_done=True,
                unopened_mail_pm_recovery_policy_recorded=True,
            )
            return
        if not state.packet_envelope_body_audit_done:
            yield _step(
                state,
                label="packet_envelope_body_audit_done",
                action="human-like reviewer checks UI packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content inspection",
                packet_envelope_body_audit_done=True,
                packet_envelope_to_role_checked=True,
                packet_body_hash_verified=True,
                result_envelope_checked=True,
                result_body_hash_verified=True,
                completed_agent_id_role_verified=True,
                controller_body_boundary_verified=True,
                wrong_role_relabel_forbidden_verified=True,
            )
            return
        if not state.packet_role_origin_audit_done:
            yield _step(
                state,
                label="packet_role_origin_audit_done",
                action="human-like reviewer verifies every UI packet's PM author, router direct-dispatch evidence, assigned worker, and actual result author after envelope/body integrity passes",
                packet_role_origin_audit_done=True,
                packet_result_author_verified=True,
                packet_result_author_matches_assignment=True,
            )
            return
        if not state.blocker_repair_policy_snapshot_written:
            yield _step(
                state,
                label="blocker_repair_policy_snapshot_written",
                action="write the run-visible blocker repair policy table before any router control blocker is materialized",
                blocker_repair_policy_snapshot_written=True,
            )
            return
        if not state.router_hard_rejection_seen:
            yield _step(
                state,
                label="control_blocker_policy_row_attached",
                action="router materializes a UI mechanical control blocker with policy row, first handler, retry budget, and return policy metadata",
                router_hard_rejection_seen=True,
                control_blocker_artifact_written=True,
                blocker_policy_row_attached=True,
                control_blocker_handling_lane="control_plane_reissue",
                control_blocker_first_handler="responsible_role",
                control_blocker_direct_retry_budget=2,
                control_blocker_direct_retry_attempts=0,
            )
            return
        if (
            state.control_blocker_handling_lane == "control_plane_reissue"
            and not state.control_blocker_delivered_to_responsible_role
        ):
            yield _step(
                state,
                label="control_blocker_first_handler_delivered",
                action="controller delivers the first UI mechanical blocker to the responsible role without opening sealed bodies or making a PM decision",
                control_blocker_delivered_to_responsible_role=True,
            )
            return
        if (
            state.control_blocker_delivered_to_responsible_role
            and not state.control_blocker_retry_budget_exhausted
        ):
            yield _step(
                state,
                label="control_blocker_retry_budget_escalated_to_pm",
                action="after two failed direct reissue attempts, router escalates the same blocker family to PM instead of looping the responsible role",
                control_blocker_handling_lane="pm_repair_decision_required",
                control_blocker_direct_retry_attempts=2,
                control_blocker_retry_budget_exhausted=True,
                control_blocker_escalated_to_pm=True,
                control_blocker_delivered_to_pm=True,
            )
            return
        if state.control_blocker_escalated_to_pm and not state.pm_blocker_recovery_option_recorded:
            yield _step(
                state,
                label="pm_blocker_recovery_option_recorded",
                action="PM chooses a policy-listed recovery option instead of silently passing the blocked gate",
                pm_blocker_recovery_option_recorded=True,
                pm_blocker_hard_stop_checked=True,
                pm_blocker_silent_pass_forbidden=True,
            )
            return
        if state.pm_blocker_recovery_option_recorded and not state.pm_blocker_return_gate_recorded:
            yield _step(
                state,
                label="pm_blocker_return_gate_recorded",
                action="PM names the gate or terminal stop that follows the blocker recovery decision",
                pm_blocker_return_gate_recorded=True,
            )
            return
        if not state.reviewer_child_skill_use_evidence_checked:
            yield _step(
                state,
                label="reviewer_child_skill_use_evidence_checked",
                action="human-like reviewer checks UI Child Skill Use Evidence, source-skill opening, current-node slice fit, and stricter child-skill standard precedence before content inspection",
                reviewer_child_skill_use_evidence_checked=True,
            )
            return
        if not state.implementation_human_review_context_loaded:
            yield _step(
                state,
                label="implementation_human_review_context_loaded",
                action="load UI product model, screenshots, concept target, interaction evidence, and acceptance context for human-like inspection",
                implementation_human_review_context_loaded=True,
            )
            return
        if not state.implementation_human_neutral_observation_written:
            yield _step(
                state,
                label="implementation_human_neutral_observation_written",
                action="write a neutral observation of the UI screenshot and exercised states before pass/fail inspection judgement",
                implementation_human_neutral_observation_written=True,
            )
            return
        if not state.implementation_human_manual_experiments_run:
            yield _step(
                state,
                label="implementation_human_manual_experiments_run",
                action="operate the UI like a human reviewer before accepting UI evidence",
                implementation_human_manual_experiments_run=True,
            )
            return
        if not state.implementation_reviewer_independent_probe_done:
            yield _step(
                state,
                label="implementation_reviewer_independent_probe_done",
                action="human-like reviewer attacks UI evidence with direct operation, screenshots, state references, reachability, layout, aesthetics, and report-only failure hypotheses before approval",
                implementation_reviewer_independent_probe_done=True,
            )
            return
        if not state.implementation_human_inspection_passed:
            yield _step(
                state,
                label="implementation_human_inspection_passed",
                action="human-like reviewer accepts the UI product behavior, visual quality, and evidence from independent adversarial inspection evidence",
                implementation_human_inspection_passed=True,
                implementation_human_review_reviewer_approved=True,
            )
            return
        capability_backward_steps = tuple(
            _capability_backward_review_steps(state, domain="UI")
        )
        if capability_backward_steps:
            yield from capability_backward_steps
            return
        if not state.child_skill_current_gates_role_approved:
            if not state.current_child_skill_gate_independent_validation_done:
                yield _step(
                    state,
                    label="current_child_skill_gate_independent_validation_done",
                    action="required child-skill approvers run independent probes and cite concrete evidence before closing current UI child-skill gates",
                    current_child_skill_gate_independent_validation_done=True,
                )
                return
            yield _step(
                state,
                label="child_skill_current_gates_role_approved",
                action="required reviewer, route-scope FlowGuard operator, product-scope FlowGuard operator, or PM approvals close the current UI child-skill gates; controller drafts are not approvals",
                child_skill_current_gates_role_approved=True,
            )
            return
        if not state.child_skill_completion_verified:
            yield _step(
                state,
                label="child_skill_completion_verified",
                action="verify invoked child skills met their own completion standards",
                child_skill_completion_verified=True,
            )
            return
        if not state.completion_visible_user_flow_diagram_emitted:
            yield _step(
                state,
                label="completion_visible_user_flow_diagram_emitted",
                action="emit visible completion user flow diagram before UI route close",
                completion_visible_user_flow_diagram_emitted=True,
            )
            return
        if not state.final_feature_matrix_review_done:
            yield _step(
                state,
                label="final_feature_matrix_reviewed",
                action="review UI feature matrix and mark thin areas before completion self-interrogation",
                final_feature_matrix_review_done=True,
            )
            return
        if not state.final_acceptance_matrix_review_done:
            yield _step(
                state,
                label="final_acceptance_matrix_reviewed",
                action="review UI acceptance matrix and identify missing verification evidence before completion self-interrogation",
                final_acceptance_matrix_review_done=True,
            )
            return
        if not state.final_standard_scenario_pack_replayed:
            yield _step(
                state,
                label="final_standard_scenario_pack_replayed",
                action="replay the standard scenario pack and UI node-risk scenarios against the final product before completion closure",
                final_standard_scenario_pack_replayed=True,
            )
            return
        if not state.final_quality_candidate_review_done:
            yield _step(
                state,
                label="final_quality_candidate_reviewed",
                action="summarize UI quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion self-interrogation",
                final_quality_candidate_review_done=True,
            )
            return
        if not state.final_product_model_flowguard_operator_adversarial_probe_done:
            yield _step(
                state,
                label="final_product_model_flowguard_operator_adversarial_probe_done",
                action="product-scope FlowGuard operator adversarially rechecks final UI product model replay, state fields, counterexamples, counts, and blindspots before approval",
                final_product_model_flowguard_operator_adversarial_probe_done=True,
            )
            return
        if not state.final_product_function_model_replayed:
            yield _step(
                state,
                label="final_product_function_model_replayed",
                action="product-scope FlowGuard operator approves UI final behavior from adversarial model replay evidence",
                final_product_function_model_replayed=True,
                final_product_function_model_flowguard_operator_product_scope_approved=True,
            )
            return
        if not state.final_human_review_context_loaded:
            yield _step(
                state,
                label="final_human_review_context_loaded",
                action="load final UI screenshot, interaction evidence, concept target, acceptance, and product model for completion inspection",
                final_human_review_context_loaded=True,
            )
            return
        if not state.final_human_neutral_observation_written:
            yield _step(
                state,
                label="final_human_neutral_observation_written",
                action="write a neutral observation of final UI artifacts and exercised states before completion judgement",
                final_human_neutral_observation_written=True,
            )
            return
        if not state.final_human_manual_experiments_run:
            yield _step(
                state,
                label="final_human_manual_experiments_run",
                action="operate the final UI like a human reviewer before completion self-interrogation",
                final_human_manual_experiments_run=True,
            )
            return
        if not state.final_human_reviewer_independent_probe_done:
            yield _step(
                state,
                label="final_human_reviewer_independent_probe_done",
                action="final human-like reviewer attacks UI completion with direct operation, screenshots, reachability, layout, aesthetics, missing-gate hypotheses, and report-only checks",
                final_human_reviewer_independent_probe_done=True,
            )
            return
        if not state.final_human_inspection_passed:
            yield _step(
                state,
                label="final_human_inspection_passed",
                action="final human-like reviewer accepts UI product completeness and visual quality from independent adversarial inspection evidence",
                final_human_inspection_passed=True,
                final_human_review_reviewer_approved=True,
            )
            return
        if not state.completion_self_interrogation_done:
            yield _step(
                state,
                label="completion_self_interrogation_completed",
                action="derive completion layers and run at least 100 self-interrogation questions per active layer before UI route close",
                completion_self_interrogation_done=True,
                completion_self_interrogation_questions=(
                    MODEL_DYNAMIC_LAYER_COUNT
                    * MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
                ),
                completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                completion_self_interrogation_questions_per_layer=MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER,
                completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
            )
            return
        if not state.completion_self_interrogation_record_written:
            yield _step(
                state,
                label="completion_self_interrogation_record_written",
                action="write a durable completion self-interrogation record so final high-value-work decisions are traceable into the final ledger",
                completion_self_interrogation_record_written=True,
            )
            return
        if not state.completion_self_interrogation_findings_dispositioned:
            yield _step(
                state,
                label="completion_self_interrogation_findings_dispositioned",
                action="PM dispositions completion self-interrogation findings as exhausted, routed to repair, entered into the suggestion ledger, rejected, or explicitly waived before final ledger work",
                completion_self_interrogation_findings_dispositioned=True,
            )
            return
        if state.high_value_work_review == "unknown":
            if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                yield _step(
                    state,
                    label="high_value_capability_gap_found",
                    action="raise UI capability standard and recheck route",
                    capability_route_version=state.capability_route_version + 1,
                    capability_route_checked=False,
                    capability_route_flowguard_operator_route_scope_approved=False,
                    capability_product_function_model_checked=False,
                    capability_product_function_model_flowguard_operator_product_scope_approved=False,
                    capability_evidence_synced=False,
                    execution_frontier_written=False,
                    codex_plan_synced=False,
                    frontier_version=0,
                    plan_version=0,
                    capability_user_flow_diagram_refreshed=False,
                    capability_user_flow_diagram_emitted=False,
                    child_skill_route_design_discovery_started=False,
                    child_skill_initial_gate_manifest_extracted=False,
                    child_skill_gate_approvers_assigned=False,
                    child_skill_manifest_independent_validation_done=False,
                    child_skill_manifest_reviewer_reviewed=False,
                    child_skill_manifest_flowguard_operator_route_scope_approved=False,
                    child_skill_manifest_flowguard_operator_product_scope_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    child_skill_contracts_loaded=False,
                    child_skill_focused_interrogation_done=False,
                    child_skill_focused_interrogation_questions=0,
                    child_skill_focused_interrogation_scope_id="",
                    child_skill_exact_source_verified=False,
                    child_skill_substitutes_rejected=False,
                    flowpilot_invocation_policy_mapped=False,
                    child_skill_requirements_mapped=False,
                    child_skill_evidence_plan_written=False,
                    child_skill_subroute_projected=False,
                    child_skill_conformance_model_checked=False,
                    child_skill_conformance_model_flowguard_operator_route_scope_approved=False,
                    strict_gate_obligation_review_model_checked=False,
                    child_skill_execution_evidence_audited=False,
                    child_skill_evidence_matches_outputs=False,
                    child_skill_domain_quality_checked=False,
                    child_skill_iteration_loop_closed=False,
                    child_skill_completion_verified=False,
                    flowguard_dependency_checked=False,
                    dependency_plan_recorded=False,
                    future_installs_deferred=False,
                    flowguard_process_design_done=False,
                    flowguard_operator_model_adversarial_probe_done=False,
                    flowguard_model_report_risk_tiers_done=False,
                    flowguard_model_report_pm_review_agenda_done=False,
                    flowguard_model_report_toolchain_recommendations_done=False,
                    flowguard_model_report_confidence_boundary_done=False,
                    meta_route_checked=False,
                    meta_route_flowguard_operator_route_scope_approved=False,
                    sidecar_role_status="none",
                    ui_palette_contract_written=False,
                    ui_palette_default_or_override_rationale_recorded=False,
                    ui_selected_concept_bound_to_review_packet=False,
                    ui_concept_target_ready=False,
                    ui_concept_target_visible=False,
                    ui_concept_personal_visual_review_done=False,
                    ui_concept_design_recommendations_recorded=False,
                    ui_concept_aesthetic_review_done=False,
                    ui_concept_aesthetic_reasons_recorded=False,
                    ui_frontend_design_plan_done=False,
                    ui_frontend_design_execution_report_written=False,
                    visual_asset_scope="unknown",
                    visual_asset_style_review_done=False,
                    visual_asset_personal_visual_review_done=False,
                    visual_asset_design_recommendations_recorded=False,
                    visual_asset_aesthetic_review_done=False,
                    visual_asset_aesthetic_reasons_recorded=False,
                    ui_implemented=False,
                    ui_screenshot_qa_done=False,
                    ui_geometry_qa_done=False,
                    ui_reviewer_personal_walkthrough_done=False,
                    ui_visible_affordance_interaction_matrix_written=False,
                    ui_visible_affordance_interaction_matrix_complete=False,
                    ui_interaction_reachability_checked=False,
                    ui_layout_overlap_density_checked=False,
                    ui_reviewer_design_recommendations_recorded=False,
                    ui_implementation_aesthetic_review_done=False,
                    ui_implementation_aesthetic_reasons_recorded=False,
                    ui_concept_vs_implementation_deviation_table_written=False,
                    ui_divergence_review_done=False,
                    ui_iteration_budget_recorded=False,
                    ui_iteration_rounds_required=0,
                    ui_iteration_rounds_completed=0,
                    ui_major_visual_deviation_triaged=False,
                    ui_structural_redesign_route_considered=False,
                    ui_visual_iteration_loop_closed=False,
                    ui_visual_iterations=0,
                    final_verification_done=False,
                    completion_self_interrogation_done=False,
                    completion_self_interrogation_questions=0,
                    completion_self_interrogation_layer_count=0,
                    completion_self_interrogation_questions_per_layer=0,
                    completion_self_interrogation_layers=0,
                    completion_self_interrogation_record_written=False,
                    completion_self_interrogation_findings_dispositioned=False,
                    completion_visible_user_flow_diagram_emitted=False,
                    final_feature_matrix_review_done=False,
                    final_acceptance_matrix_review_done=False,
                    final_quality_candidate_review_done=False,
                    manual_resume_binding_health_checked=False,
                    lifecycle_reconciliation_done=False,
                    terminal_lifecycle_frontier_written=False,
                    standard_expansions=state.standard_expansions + 1,
                    **_reset_execution_quality_gates(),
                )
            yield _step(
                state,
                label="no_obvious_high_value_work_remaining",
                action="record that completion self-interrogation found no obvious high-value work",
                high_value_work_review="exhausted",
            )
            return
        final_ledger_steps = tuple(
            _final_route_wide_gate_ledger_steps(state, domain="UI")
        )
        if final_ledger_steps:
            yield from final_ledger_steps
            return
        if not state.terminal_closure_suite_run:
            yield _step(
                state,
                label="terminal_closure_suite_run",
                action="run terminal closure suite after UI final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                terminal_closure_suite_run=True,
            )
            return
        if not state.terminal_state_and_evidence_refreshed:
            yield _step(
                state,
                label="terminal_state_and_evidence_refreshed",
                action="refresh UI terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route close",
                terminal_state_and_evidence_refreshed=True,
            )
            return
        if not state.lifecycle_reconciliation_done:
            yield _step(
                state,
                label="lifecycle_reconciliation_completed",
                action="scan manual resume binding and manual-resume lifecycle records, local state, and execution frontier before UI route close",
                lifecycle_reconciliation_done=True,
            )
            return
        if not state.terminal_router_daemon_stopped:
            yield _step(
                state,
                label="terminal_router_daemon_stopped",
                action="stop the persistent Router daemon, release its run lock, stop Controller action watching, and write terminal daemon status before final capability route close",
                router_daemon_started=False,
                router_daemon_lock_acquired=False,
                router_daemon_tick_seconds=0,
                controller_action_watch_active=False,
                terminal_router_daemon_stopped=True,
            )
            return
        if not state.terminal_lifecycle_frontier_written:
            yield _step(
                state,
                label="terminal_lifecycle_frontier_written",
                action="write terminal foreground-patrol and manual-resume lifecycle back to execution frontier before route close",
                terminal_lifecycle_frontier_written=True,
            )
            return
        if not state.role_binding_memory_archived:
            yield _step(
                state,
                label="role_binding_memory_archived_at_terminal",
                action="archive compact role memory packets with final capability statuses before UI route close",
                role_binding_memory_archived=True,
            )
            return
        if not state.role_binding_ledger_archived:
            yield _step(
                state,
                label="role_binding_ledger_archived_at_terminal",
                action="archive persistent role-binding ledger after role memory and UI lifecycle reconciliation",
                role_binding_ledger_archived=True,
            )
            return
        if not state.flowpilot_skill_improvement_report_written:
            yield _step(
                state,
                label="flowpilot_skill_improvement_report_written",
                action="PM writes a nonblocking FlowPilot skill improvement report from UI capability observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                flowpilot_skill_improvement_report_written=True,
            )
            return
        if not state.pm_completion_decision_recorded:
            yield _step(
                state,
                label="pm_completion_decision_recorded",
                action="project manager approves UI completion after final reviews and lifecycle cleanup",
                pm_completion_decision_recorded=True,
            )
            return
        yield _step(
            state,
            label="completed",
            action="complete UI project route and emit terminal completion notice",
            status="complete",
            terminal_completion_notice_recorded=True,
        )
        return

