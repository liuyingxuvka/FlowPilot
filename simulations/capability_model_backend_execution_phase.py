"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "MAX_QUALITY_REWORKS",
    "MAX_STANDARD_EXPANSIONS",
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

__all__ = ["apply_backend_execution_phase"]


def apply_backend_execution_phase(self, state: State) -> Iterable[FunctionResult]:
    if state.task_kind == "backend":
        if not state.non_ui_implemented:
            yield _step(
                state,
                label="non_ui_implemented",
                action="implement non-UI project chunk",
                non_ui_implemented=True,
                role_memory_refreshed_after_work=False,
            )
            return
        if not state.worker_child_skill_use_evidence_returned:
            yield _step(
                state,
                label="worker_child_skill_use_evidence_returned",
                action="worker returns Child Skill Use Evidence proving the bound child skill source was opened, applied to the current node slice, and any stricter child-skill standard was followed or explicitly waived",
                worker_child_skill_use_evidence_returned=True,
            )
            return
        if not state.child_skill_manifest_only_evidence_rejected:
            yield _step(
                state,
                label="child_skill_manifest_only_evidence_rejected",
                action="reject manifest-only child-skill evidence and require execution artifacts, logs, screenshots, diffs, or reviewer-owned observations",
                child_skill_manifest_only_evidence_rejected=True,
            )
            return
        if not state.child_skill_execution_reports_written:
            yield _step(
                state,
                label="child_skill_execution_reports_written",
                action="write per-invoked-skill execution reports covering required steps, iteration budget, deviations, waivers, and reviewer findings",
                child_skill_execution_reports_written=True,
            )
            return
        if not state.child_skill_execution_evidence_audited:
            yield _step(
                state,
                label="child_skill_execution_evidence_audited",
                action="audit child-skill step evidence against mapped requirements",
                child_skill_execution_evidence_audited=True,
            )
            return
        if not state.child_skill_evidence_matches_outputs:
            yield _step(
                state,
                label="child_skill_evidence_matches_outputs",
                action="confirm child-skill evidence matches actual outputs",
                child_skill_evidence_matches_outputs=True,
            )
            return
        if not state.child_skill_domain_quality_checked:
            yield _step(
                state,
                label="child_skill_domain_quality_checked",
                action="check child-skill output quality against parent node goal",
                child_skill_domain_quality_checked=True,
            )
            return
        if not state.child_skill_iteration_loop_closed:
            yield _step(
                state,
                label="child_skill_iteration_loop_closed",
                action="close child-skill iteration loop before final verification",
                child_skill_iteration_loop_closed=True,
            )
            return
        if not state.current_node_skill_improvement_check_done:
            yield _step(
                state,
                label="skill_improvement_observation_check_no_issue",
                action="PM asks the backend capability roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found",
                current_node_skill_improvement_check_done=True,
            )
            yield _step(
                state,
                label="skill_improvement_observation_logged",
                action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance while continuing the backend project",
                current_node_skill_improvement_check_done=True,
                flowpilot_improvement_live_report_updated=True,
            )
            return
        if not state.role_memory_refreshed_after_work:
            yield _step(
                state,
                label="role_memory_packets_refreshed_after_capability_work",
                action="refresh compact role memory packets after backend implementation evidence and before final verification",
                role_memory_refreshed_after_work=True,
            )
            return
        if not state.final_verification_done:
            yield _step(
                state,
                label="final_verification_done",
                action="run final verification",
                final_verification_done=True,
            )
            return
        if not state.anti_rough_finish_done:
            yield _step(
                state,
                label="anti_rough_finish_passed",
                action="review the verified backend result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                anti_rough_finish_done=True,
            )
            if (
                state.quality_reworks < MAX_QUALITY_REWORKS
                and state.standard_expansions == 0
            ):
                yield _step(
                    state,
                    label="anti_rough_finish_found_rework",
                    action="record bounded backend rework because the route is still too thin or weakly evidenced",
                    non_ui_implemented=False,
                    child_skill_execution_evidence_audited=False,
                    child_skill_evidence_matches_outputs=False,
                    child_skill_domain_quality_checked=False,
                    child_skill_iteration_loop_closed=False,
                    child_skill_completion_verified=False,
                    final_verification_done=False,
                    heartbeat_health_checked=False,
                    quality_reworks=state.quality_reworks + 1,
                    **_reset_execution_quality_gates(),
                )
            return
        if not state.worker_output_ready_for_review:
            yield _step(
                state,
                label="worker_output_ready_for_review",
                action="record that backend worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                worker_output_ready_for_review=True,
            )
            return
        if not state.pm_review_release_order_written:
            yield _step(
                state,
                label="pm_review_release_order_written",
                action="project manager writes the backend review release order naming the gate, evidence paths, reviewer scope, and required inspections",
                pm_review_release_order_written=True,
            )
            return
        if not state.pm_released_reviewer_for_current_gate:
            yield _step(
                state,
                label="pm_released_reviewer_for_current_gate",
                action="project manager explicitly releases the reviewer to start backend inspection after worker output is ready",
                pm_released_reviewer_for_current_gate=True,
            )
            return
        if not state.packet_runtime_physical_files_written:
            yield _step(
                state,
                label="packet_runtime_physical_isolation_verified",
                action="packet runtime writes backend physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                packet_runtime_physical_files_written=True,
                controller_context_body_exclusion_verified=True,
            )
            return
        if not state.packet_mail_chain_audit_done:
            yield _step(
                state,
                label="controller_mail_relay_chain_audit_done",
                action="reviewer verifies backend packet/result controller relay signatures, recipient pre-open checks, no private role-to-role mail, and PM restart/repair/reissue handling for unopened or contaminated mail",
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
                action="human-like reviewer checks backend packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content inspection",
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
                action="human-like reviewer verifies every backend packet's PM author, router direct-dispatch evidence, assigned worker, and actual result author after envelope/body integrity passes",
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
                action="router materializes a backend mechanical control blocker with policy row, first handler, retry budget, and return policy metadata",
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
                action="controller delivers the first backend mechanical blocker to the responsible role without opening sealed bodies or making a PM decision",
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
                action="human-like reviewer checks backend Child Skill Use Evidence, source-skill opening, current-node slice fit, and stricter child-skill standard precedence before content inspection",
                reviewer_child_skill_use_evidence_checked=True,
            )
            return
        if not state.implementation_human_review_context_loaded:
            yield _step(
                state,
                label="implementation_human_review_context_loaded",
                action="load backend product model, outputs, logs, evidence, and acceptance context for human-like inspection",
                implementation_human_review_context_loaded=True,
            )
            return
        if not state.implementation_human_neutral_observation_written:
            yield _step(
                state,
                label="implementation_human_neutral_observation_written",
                action="write a neutral observation of backend outputs and behavior before pass/fail inspection judgement",
                implementation_human_neutral_observation_written=True,
            )
            return
        if not state.implementation_human_manual_experiments_run:
            yield _step(
                state,
                label="implementation_human_manual_experiments_run",
                action="exercise the backend behavior or inspect representative data like a human reviewer",
                implementation_human_manual_experiments_run=True,
            )
            return
        if not state.implementation_reviewer_independent_probe_done:
            yield _step(
                state,
                label="implementation_reviewer_independent_probe_done",
                action="human-like reviewer attacks backend evidence with direct probes, checked state/log references, and report-only failure hypotheses before approval",
                implementation_reviewer_independent_probe_done=True,
            )
            return
        if not state.implementation_human_inspection_passed:
            yield _step(
                state,
                label="implementation_human_inspection_passed",
                action="human-like reviewer accepts the backend product behavior from independent adversarial inspection evidence",
                implementation_human_inspection_passed=True,
                implementation_human_review_reviewer_approved=True,
            )
            return
        capability_backward_steps = tuple(
            _capability_backward_review_steps(state, domain="backend")
        )
        if capability_backward_steps:
            yield from capability_backward_steps
            return
        if not state.child_skill_current_gates_role_approved:
            if not state.current_child_skill_gate_independent_validation_done:
                yield _step(
                    state,
                    label="current_child_skill_gate_independent_validation_done",
                    action="required child-skill approvers run independent probes and cite concrete evidence before closing current backend child-skill gates",
                    current_child_skill_gate_independent_validation_done=True,
                )
                return
            yield _step(
                state,
                label="child_skill_current_gates_role_approved",
                action="required reviewer, process officer, product officer, or PM approvals close the current child-skill gates; controller drafts are not approvals",
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
                action="emit visible completion user flow diagram before backend route close",
                completion_visible_user_flow_diagram_emitted=True,
            )
            return
        if not state.final_feature_matrix_review_done:
            yield _step(
                state,
                label="final_feature_matrix_reviewed",
                action="review backend feature matrix and mark thin areas before completion self-interrogation",
                final_feature_matrix_review_done=True,
            )
            return
        if not state.final_acceptance_matrix_review_done:
            yield _step(
                state,
                label="final_acceptance_matrix_reviewed",
                action="review backend acceptance matrix and identify missing verification evidence before completion self-interrogation",
                final_acceptance_matrix_review_done=True,
            )
            return
        if not state.final_standard_scenario_pack_replayed:
            yield _step(
                state,
                label="final_standard_scenario_pack_replayed",
                action="replay the standard scenario pack and backend node-risk scenarios against the final product before completion closure",
                final_standard_scenario_pack_replayed=True,
            )
            return
        if not state.final_quality_candidate_review_done:
            yield _step(
                state,
                label="final_quality_candidate_reviewed",
                action="summarize backend quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion self-interrogation",
                final_quality_candidate_review_done=True,
            )
            return
        if not state.final_product_model_officer_adversarial_probe_done:
            yield _step(
                state,
                label="final_product_model_officer_adversarial_probe_done",
                action="product FlowGuard officer adversarially rechecks final backend product model replay, state fields, counterexamples, counts, and blindspots before approval",
                final_product_model_officer_adversarial_probe_done=True,
            )
            return
        if not state.final_product_function_model_replayed:
            yield _step(
                state,
                label="final_product_function_model_replayed",
                action="product FlowGuard officer approves backend final behavior from adversarial model replay evidence",
                final_product_function_model_replayed=True,
                final_product_function_model_product_officer_approved=True,
            )
            return
        if not state.final_human_review_context_loaded:
            yield _step(
                state,
                label="final_human_review_context_loaded",
                action="load final backend output, evidence, acceptance, and product model for completion inspection",
                final_human_review_context_loaded=True,
            )
            return
        if not state.final_human_neutral_observation_written:
            yield _step(
                state,
                label="final_human_neutral_observation_written",
                action="write a neutral observation of final backend artifacts before completion judgement",
                final_human_neutral_observation_written=True,
            )
            return
        if not state.final_human_manual_experiments_run:
            yield _step(
                state,
                label="final_human_manual_experiments_run",
                action="run final human-like backend experiments before completion self-interrogation",
                final_human_manual_experiments_run=True,
            )
            return
        if not state.final_human_reviewer_independent_probe_done:
            yield _step(
                state,
                label="final_human_reviewer_independent_probe_done",
                action="final human-like reviewer attacks backend completion with direct probes, state/log references, missing-gate hypotheses, and report-only checks",
                final_human_reviewer_independent_probe_done=True,
            )
            return
        if not state.final_human_inspection_passed:
            yield _step(
                state,
                label="final_human_inspection_passed",
                action="final human-like reviewer accepts backend product completeness from independent adversarial inspection evidence",
                final_human_inspection_passed=True,
                final_human_review_reviewer_approved=True,
            )
            return
        if not state.completion_self_interrogation_done:
            yield _step(
                state,
                label="completion_self_interrogation_completed",
                action="derive completion layers and run at least 100 self-interrogation questions per active layer before backend route close",
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
                    action="raise backend capability standard and recheck route",
                    capability_route_version=state.capability_route_version + 1,
                    capability_route_checked=False,
                    capability_route_process_officer_approved=False,
                    capability_product_function_model_checked=False,
                    capability_product_function_model_product_officer_approved=False,
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
                    child_skill_manifest_process_officer_approved=False,
                    child_skill_manifest_product_officer_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    child_skill_contracts_loaded=False,
                    child_skill_focused_interrogation_done=False,
                    child_skill_focused_interrogation_questions=0,
                    child_skill_focused_interrogation_scope_id="",
                    child_skill_exact_source_verified=False,
                    child_skill_substitutes_rejected=False,
                    child_skill_original_standards_extracted=False,
                    child_skill_standards_promoted_to_node_contract=False,
                    child_skill_gate_evidence_obligations_bound=False,
                    flowpilot_invocation_policy_mapped=False,
                    child_skill_requirements_mapped=False,
                    child_skill_evidence_plan_written=False,
                    child_skill_subroute_projected=False,
                    child_skill_conformance_model_checked=False,
                    child_skill_conformance_model_process_officer_approved=False,
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
                    flowguard_officer_model_adversarial_probe_done=False,
                    flowguard_model_report_risk_tiers_done=False,
                    flowguard_model_report_pm_review_agenda_done=False,
                    flowguard_model_report_toolchain_recommendations_done=False,
                    flowguard_model_report_confidence_boundary_done=False,
                    meta_route_checked=False,
                    meta_route_process_officer_approved=False,
                    subagent_status="none",
                    non_ui_implemented=False,
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
                    heartbeat_health_checked=False,
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
            _final_route_wide_gate_ledger_steps(state, domain="backend")
        )
        if final_ledger_steps:
            yield from final_ledger_steps
            return
        if not state.terminal_closure_suite_run:
            yield _step(
                state,
                label="terminal_closure_suite_run",
                action="run terminal closure suite after backend final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                terminal_closure_suite_run=True,
            )
            return
        if not state.terminal_state_and_evidence_refreshed:
            yield _step(
                state,
                label="terminal_state_and_evidence_refreshed",
                action="refresh backend terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route close",
                terminal_state_and_evidence_refreshed=True,
            )
            return
        if not state.lifecycle_reconciliation_done:
            yield _step(
                state,
                label="lifecycle_reconciliation_completed",
                action="scan Codex heartbeat automations, local state, and execution frontier before backend route close",
                lifecycle_reconciliation_done=True,
            )
            return
        if not state.terminal_router_daemon_stopped:
            yield _step(
                state,
                label="terminal_router_daemon_stopped",
                action="stop the persistent Router daemon, release its run lock, stop Controller action watching, and write terminal daemon status before final backend capability route close",
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
                action="write terminal heartbeat lifecycle back to execution frontier before route close",
                terminal_lifecycle_frontier_written=True,
            )
            return
        if not state.crew_memory_archived:
            yield _step(
                state,
                label="crew_memory_archived_at_terminal",
                action="archive compact role memory packets with final capability statuses before backend route close",
                crew_memory_archived=True,
            )
            return
        if not state.crew_archived:
            yield _step(
                state,
                label="crew_archived_at_terminal",
                action="archive persistent crew ledger after role memory and backend lifecycle reconciliation",
                crew_archived=True,
            )
            return
        if not state.flowpilot_skill_improvement_report_written:
            yield _step(
                state,
                label="flowpilot_skill_improvement_report_written",
                action="PM writes a nonblocking FlowPilot skill improvement report from backend capability observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                flowpilot_skill_improvement_report_written=True,
            )
            return
        if not state.pm_completion_decision_recorded:
            yield _step(
                state,
                label="pm_completion_decision_recorded",
                action="project manager approves backend completion after final reviews and lifecycle cleanup",
                pm_completion_decision_recorded=True,
            )
            return
        yield _step(
            state,
            label="completed",
            action="complete backend project route and emit terminal completion notice",
            status="complete",
            terminal_completion_notice_recorded=True,
        )
        return
