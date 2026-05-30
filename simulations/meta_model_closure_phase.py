"""Phase helper extracted from :mod:`meta_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import meta_model as _model
else:
    import meta_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "MAX_STANDARD_EXPANSIONS",
    "MAX_TERMINAL_BACKWARD_REPLAY_REPAIRS",
    "MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER",
    "MODEL_DYNAMIC_LAYER_COUNT",
    "REQUIRED_RISK_FAMILY_MASK",
    "State",
    "TARGET_CHUNKS",
    "TARGET_PARENT_NODES",
    "_reset_execution_scope_gates",
    "_route_ready",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_closure_phase"]


def apply_closure_phase(self, state: State) -> Iterable[FunctionResult]:
    if (
        state.completed_chunks >= state.required_chunks
        and state.checkpoint_written
        and _route_ready(state)
        and state.subagent_status not in {"pending", "returned"}
    ):
        if not state.completion_visible_roadmap_emitted:
            yield _step(
                state,
                label="completion_visible_user_flow_diagram_emitted",
                action="emit visible completion user flow diagram before deciding whether any high-value work remains",
                completion_visible_roadmap_emitted=True,
                active_node="final_feature_matrix_review",
            )
            return
        if not state.final_feature_matrix_review_done:
            yield _step(
                state,
                label="final_feature_matrix_reviewed",
                action="review implemented feature matrix and mark thin areas before completion self-interrogation",
                final_feature_matrix_review_done=True,
                active_node="final_acceptance_matrix_review",
            )
            return
        if not state.final_acceptance_matrix_review_done:
            yield _step(
                state,
                label="final_acceptance_matrix_reviewed",
                action="review acceptance matrix and identify missing verification evidence before completion self-interrogation",
                final_acceptance_matrix_review_done=True,
                active_node="final_standard_scenario_pack_replay",
            )
            return
        if not state.final_standard_scenario_pack_replayed:
            yield _step(
                state,
                label="final_standard_scenario_pack_replayed",
                action="replay the standard scenario pack and node-risk scenarios against the final product before quality-candidate and completion closure",
                final_standard_scenario_pack_replayed=True,
                active_node="final_quality_candidate_review",
            )
            return
        if not state.final_quality_candidate_review_done:
            yield _step(
                state,
                label="final_quality_candidate_reviewed",
                action="summarize quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion self-interrogation",
                final_quality_candidate_review_done=True,
                active_node="final_product_function_replay",
            )
            return
        if not state.final_product_model_officer_adversarial_probe_done:
            yield _step(
                state,
                label="final_product_model_officer_adversarial_probe_done",
                action="product FlowGuard officer adversarially rechecks the final product model boundary, state fields, counterexamples, counts, and blindspots before approving final replay",
                final_product_model_officer_adversarial_probe_done=True,
                active_node="final_product_function_replay",
            )
            return
        if not state.final_product_function_model_replayed:
            yield _step(
                state,
                label="final_product_function_model_replayed",
                action="product FlowGuard officer replays and approves final product behavior against the root product-function model before completion self-interrogation",
                final_product_function_model_replayed=True,
                final_product_function_model_product_officer_approved=True,
                active_node="final_human_inspection_context",
            )
            return
        if not state.final_human_review_context_loaded:
            yield _step(
                state,
                label="final_human_review_context_loaded",
                action="load final output, route evidence, product model, concept or acceptance evidence, and known repairs for final human-like review",
                final_human_review_context_loaded=True,
                active_node="final_human_neutral_observation",
            )
            return
        if not state.final_human_neutral_observation_written:
            yield _step(
                state,
                label="final_human_neutral_observation_written",
                action="write a neutral observation of the final product artifacts before final pass/fail judgement",
                final_human_neutral_observation_written=True,
                active_node="final_human_manual_experiments",
            )
            return
        if not state.final_human_manual_experiments_run:
            yield _step(
                state,
                label="final_human_manual_experiments_run",
                action="operate or inspect the final product as a human reviewer before completion self-interrogation",
                final_human_manual_experiments_run=True,
                active_node="final_human_inspection_decision",
            )
            return
        if not state.final_human_reviewer_independent_probe_done:
            yield _step(
                state,
                label="final_human_reviewer_independent_probe_done",
                action="final human-like reviewer independently attacks the completed product with direct operation or inspection, concrete artifact references, missing-gate hypotheses, and report-only failure checks before approval",
                final_human_reviewer_independent_probe_done=True,
                active_node="final_human_inspection_decision",
            )
            return
        if not state.final_human_inspection_passed:
            yield _step(
                state,
                label="final_human_inspection_passed",
                action="final human-like reviewer accepts the product as a complete showcase candidate",
                final_human_inspection_passed=True,
                final_human_review_reviewer_approved=True,
                active_node="completion_self_interrogation",
            )
            return
        if not state.completion_self_interrogation_done:
            yield _step(
                state,
                label="completion_self_interrogation_completed",
                action="derive completion layers and run at least 100 self-interrogation questions per active layer to find remaining high-value work",
                completion_self_interrogation_done=True,
                completion_self_interrogation_questions=(
                    MODEL_DYNAMIC_LAYER_COUNT
                    * MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
                ),
                completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                completion_self_interrogation_questions_per_layer=MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER,
                completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                active_node="review_high_value_work",
            )
            return
        if not state.completion_self_interrogation_record_written:
            yield _step(
                state,
                label="completion_self_interrogation_record_written",
                action="write a durable completion self-interrogation record so final high-value-work decisions are traceable into the final ledger",
                completion_self_interrogation_record_written=True,
                active_node="review_high_value_work",
            )
            return
        if not state.completion_self_interrogation_findings_dispositioned:
            yield _step(
                state,
                label="completion_self_interrogation_findings_dispositioned",
                action="PM dispositions completion self-interrogation findings as exhausted, routed to repair, entered into the suggestion ledger, rejected, or explicitly waived before final ledger work",
                completion_self_interrogation_findings_dispositioned=True,
                active_node="review_high_value_work",
            )
            return
        if state.high_value_work_review == "unknown":
            if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                yield _step(
                    state,
                    label="high_value_work_found_and_route_expanded",
                    action="raise the standard and route another verified chunk",
                    route_version=state.route_version + 1,
                    route_checked=False,
                    markdown_synced=False,
                    execution_frontier_written=False,
                    codex_plan_synced=False,
                    frontier_version=0,
                    plan_version=0,
                    visible_user_flow_diagram_emitted=False,
                    user_flow_diagram_refreshed=False,
                    user_flow_diagram_reviewer_display_checked=False,
                    user_flow_diagram_reviewer_route_match_checked=False,
                    flowguard_process_design_done=False,
                    flowguard_officer_model_adversarial_probe_done=False,
                    flowguard_model_report_risk_tiers_done=False,
                    flowguard_model_report_pm_review_agenda_done=False,
                    flowguard_model_report_toolchain_recommendations_done=False,
                    flowguard_model_report_confidence_boundary_done=False,
                    child_skill_route_design_discovery_started=False,
                    child_skill_initial_gate_manifest_extracted=False,
                    child_skill_gate_approvers_assigned=False,
                    child_skill_manifest_independent_validation_done=False,
                    child_skill_manifest_reviewer_reviewed=False,
                    child_skill_manifest_process_officer_approved=False,
                    child_skill_manifest_product_officer_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    candidate_route_tree_generated=False,
                    root_route_model_checked=False,
                    root_route_model_process_officer_approved=False,
                    root_product_function_model_checked=False,
                    root_product_function_model_product_officer_approved=False,
                    strict_gate_obligation_review_model_checked=False,
                    parent_backward_review_targets_enumerated=False,
                    parent_subtree_review_checked=False,
                    parent_focused_interrogation_done=False,
                    parent_focused_interrogation_questions=0,
                    parent_focused_interrogation_scope_id="",
                    unfinished_current_node_recovery_checked=False,
                    required_chunks=TARGET_CHUNKS,
                    completed_chunks=TARGET_CHUNKS - 1,
                    node_human_inspections_passed=TARGET_CHUNKS - 1,
                    composite_backward_reviews_passed=TARGET_CHUNKS - 1,
                    composite_backward_pm_segment_decisions_recorded=TARGET_PARENT_NODES
                    - 1,
                    checkpoint_written=False,
                    completion_self_interrogation_done=False,
                    completion_self_interrogation_questions=0,
                    completion_self_interrogation_layer_count=0,
                    completion_self_interrogation_questions_per_layer=0,
                    completion_self_interrogation_layers=0,
                    completion_self_interrogation_record_written=False,
                    completion_self_interrogation_findings_dispositioned=False,
                    completion_visible_roadmap_emitted=False,
                    high_value_work_review="unknown",
                    standard_expansions=state.standard_expansions + 1,
                    heartbeat_health_checked=False,
                    lifecycle_reconciliation_done=False,
                    terminal_lifecycle_frontier_written=False,
                    node_focused_interrogation_done=False,
                    node_focused_interrogation_questions=0,
                    node_focused_interrogation_scope_id="",
                    lightweight_self_check_done=False,
                    lightweight_self_check_questions=0,
                    lightweight_self_check_scope_id="",
                    node_visible_roadmap_emitted=False,
                    final_feature_matrix_review_done=False,
                    final_acceptance_matrix_review_done=False,
                    final_standard_scenario_pack_replayed=False,
                    final_quality_candidate_review_done=False,
                    final_product_function_model_replayed=False,
                    final_product_model_officer_adversarial_probe_done=False,
                    final_product_function_model_product_officer_approved=False,
                    final_human_review_context_loaded=False,
                    final_human_neutral_observation_written=False,
                    final_human_manual_experiments_run=False,
                    final_human_reviewer_independent_probe_done=False,
                    final_human_inspection_passed=False,
                    final_human_review_reviewer_approved=False,
                    pm_completion_decision_recorded=False,
                    active_node="run_expanded_route_checks",
                    **_reset_execution_scope_gates(),
                )
            yield _step(
                state,
                label="no_obvious_high_value_work_remaining",
                action="record that completion self-interrogation found no obvious high-value work",
                high_value_work_review="exhausted",
                active_node="ready_to_complete",
            )
            return
        if state.high_value_work_review != "exhausted":
            return
        if not state.final_route_wide_gate_ledger_current_route_scanned:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_current_route_scanned",
                action="PM starts final route-wide gate ledger by scanning the current active route, execution frontier, and route mutation history",
                final_route_wide_gate_ledger_current_route_scanned=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_effective_nodes_resolved:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_effective_nodes_resolved",
                action="PM resolves active, repaired, inserted, waived, and superseded nodes from the current route before completion approval",
                final_route_wide_gate_ledger_effective_nodes_resolved=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_child_skill_gates_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_child_skill_gates_collected",
                action="PM collects every current child-skill gate, completion standard, evidence path, waiver, blocker, and role approval into the final ledger",
                final_route_wide_gate_ledger_child_skill_gates_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_human_review_gates_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_human_review_gates_collected",
                action="PM collects node, parent, final, strict-obligation, and same-inspector review gates into the final ledger",
                final_route_wide_gate_ledger_human_review_gates_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_parent_backward_replays_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_parent_backward_replays_collected",
                action="PM collects every structurally required local parent backward replay and its PM segment decision into the final ledger",
                final_route_wide_gate_ledger_parent_backward_replays_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_deep_leaf_coverage_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_deep_leaf_coverage_collected",
                action="PM collects every effective deep leaf node, its acceptance plan, review evidence, and parent/module segment mapping into the final ledger",
                final_route_wide_gate_ledger_deep_leaf_coverage_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_product_process_gates_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_product_process_gates_collected",
                action="PM collects product-function and development-process model gates into the final ledger",
                final_route_wide_gate_ledger_product_process_gates_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_resource_lineage_resolved:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_resource_lineage_resolved",
                action=(
                    "PM resolves generated-resource lineage into terminal dispositions: "
                    "consumed_by_implementation, included_in_final_output, "
                    "qa_evidence, flowguard_evidence, user_flow_diagram, "
                    "superseded, quarantined, or discarded_with_reason"
                ),
                final_route_wide_gate_ledger_resource_lineage_resolved=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.evidence_credibility_triage_done:
            yield _step(
                state,
                label="evidence_credibility_triage_done",
                action="PM reconciles the evidence ledger, separating valid live-project evidence from invalid, stale, superseded, fixture-only, synthetic, historical, and generated-concept evidence before final ledger closure",
                evidence_credibility_triage_done=True,
                invalid_evidence_recorded=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_stale_evidence_checked:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_stale_evidence_checked",
                action="PM checks that no stale or invalidated evidence is still closing a current route obligation",
                final_route_wide_gate_ledger_stale_evidence_checked=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_superseded_nodes_explained:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_superseded_nodes_explained",
                action="PM records replacement, waiver, or no-longer-effective explanations for every superseded node and gate",
                final_route_wide_gate_ledger_superseded_nodes_explained=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_unresolved_count_zero:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_unresolved_count_zero",
                action="PM records zero unresolved current-route obligations before final reviewer replay",
                final_route_wide_gate_ledger_unresolved_count_zero=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_self_interrogation_collected:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_self_interrogation_collected",
                action="PM cites the route self-interrogation index and collects startup, product-architecture, node, repair, role-result, and completion self-interrogation dispositions into the final ledger",
                final_route_wide_gate_ledger_self_interrogation_collected=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.self_interrogation_index_clean:
            yield _step(
                state,
                label="self_interrogation_index_clean",
                action="PM proves the self-interrogation index has no unresolved hard or current findings before final ledger build and terminal closure",
                self_interrogation_index_clean=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_residual_risk_triage_done:
            yield _step(
                state,
                label="final_residual_risk_triage_done",
                action="PM triages every remaining risk or blindspot as fixed, routed to repair, current-gate blocker, terminal replay scenario, non-risk note, or explicit exception",
                final_residual_risk_triage_done=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_residual_risk_unresolved_count_zero:
            yield _step(
                state,
                label="final_residual_risk_unresolved_count_zero",
                action="PM records zero unresolved residual risks before final ledger can be built",
                final_residual_risk_unresolved_count_zero=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.defect_ledger_zero_blocking:
            yield _step(
                state,
                label="defect_ledger_zero_blocking",
                action="PM checks the defect ledger and records zero open blocker defects and zero fixed-pending-recheck defects before final ledger can be built",
                defect_ledger_zero_blocking=True,
                active_node="final_route_wide_gate_ledger",
            )
            return
        if not state.final_route_wide_gate_ledger_pm_built:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_pm_built",
                action="PM writes the final route-wide gate ledger from current route state and evidence, not from the startup checklist",
                final_route_wide_gate_ledger_pm_built=True,
                active_node="terminal_human_backward_review_map",
            )
            return
        if not state.terminal_human_backward_review_map_built:
            yield _step(
                state,
                label="terminal_human_backward_review_map_built",
                action="PM converts the clean final ledger into an ordered human backward replay map from delivered product to root, parent, and leaf node obligations",
                terminal_human_backward_review_map_built=True,
                active_node="terminal_human_backward_replay",
            )
            return
        if not state.terminal_human_backward_replay_started_from_delivered_product:
            yield _step(
                state,
                label="terminal_human_backward_replay_started_from_delivered_product",
                action="human-like reviewer starts terminal replay from the delivered product itself, not from ledger entries or worker reports",
                terminal_human_backward_replay_started_from_delivered_product=True,
                active_node="terminal_human_backward_root_review",
            )
            return
        if not state.terminal_human_backward_root_acceptance_reviewed:
            yield _step(
                state,
                label="terminal_human_backward_root_acceptance_reviewed",
                action="human-like reviewer manually checks the final product against root acceptance and baseline functional obligations before drilling into nodes",
                terminal_human_backward_root_acceptance_reviewed=True,
                active_node="terminal_human_backward_parent_reviews",
            )
            return
        if not state.terminal_human_backward_parent_nodes_reviewed:
            yield _step(
                state,
                label="terminal_human_backward_parent_nodes_reviewed",
                action="human-like reviewer walks backward through each effective parent or module node and checks whether child outcomes compose into the parent goal",
                terminal_human_backward_parent_nodes_reviewed=True,
                active_node="terminal_human_backward_leaf_reviews",
            )
            return
        if not state.terminal_human_backward_leaf_nodes_reviewed:
            yield _step(
                state,
                label="terminal_human_backward_leaf_nodes_reviewed",
                action="human-like reviewer manually checks every effective leaf node against its node acceptance plan, experiments, and current product behavior",
                terminal_human_backward_leaf_nodes_reviewed=True,
                active_node="terminal_human_backward_pm_segment_decisions",
            )
            return
        if (
            state.terminal_human_backward_replay_repairs
            < MAX_TERMINAL_BACKWARD_REPLAY_REPAIRS
        ):
            yield _step(
                state,
                label="terminal_human_backward_replay_found_repair_issue",
                action="terminal human backward replay finds a current product or node-detail issue that must return to PM repair routing instead of being parked in the report",
                issue="terminal_backward_review_failure",
                active_node="terminal_human_backward_replay_repair",
            )
            return
        if not state.terminal_human_backward_pm_segment_decisions_recorded:
            yield _step(
                state,
                label="terminal_human_backward_pm_segment_decisions_recorded",
                action="PM reviews each reviewer segment result, records continue or repair decisions, and confirms no segment was accepted from report-only evidence",
                terminal_human_backward_pm_segment_decisions_recorded=True,
                active_node="terminal_human_backward_restart_policy",
            )
            return
        if not state.terminal_human_backward_repair_restart_policy_recorded:
            yield _step(
                state,
                label="terminal_human_backward_repair_restart_policy_recorded",
                action="PM records that any terminal replay repair invalidates affected evidence and restarts final review from the delivered product unless a narrower impacted-ancestor restart is justified",
                terminal_human_backward_repair_restart_policy_recorded=True,
                active_node="final_route_wide_gate_ledger_reviewer_replay",
            )
            return
        if not state.final_route_wide_gate_ledger_reviewer_backward_checked:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_reviewer_backward_checked",
                action="human-like reviewer completes the terminal human backward replay through every effective root, parent, and leaf-node obligation in the PM-built map",
                final_route_wide_gate_ledger_reviewer_backward_checked=True,
                active_node="final_route_wide_gate_ledger_pm_approval",
            )
            return
        if not state.final_ledger_pm_independent_audit_done:
            yield _step(
                state,
                label="final_ledger_pm_independent_audit_done",
                action="PM independently audits route/frontier/ledger entries, stale evidence, waiver authority, unresolved counts, reviewer replay, and blindspots before completion approval",
                final_ledger_pm_independent_audit_done=True,
                active_node="final_route_wide_gate_ledger_pm_approval",
            )
            return
        if not state.final_route_wide_gate_ledger_pm_completion_approved:
            yield _step(
                state,
                label="final_route_wide_gate_ledger_pm_completion_approved",
                action="project manager approves the clean route-wide gate ledger before lifecycle closure and final completion decision",
                final_route_wide_gate_ledger_pm_completion_approved=True,
                active_node="terminal_closure_suite",
            )
            return
        if not state.terminal_closure_suite_run:
            yield _step(
                state,
                label="terminal_closure_suite_run",
                action="run terminal closure suite after final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                terminal_closure_suite_run=True,
                active_node="terminal_state_evidence_refresh",
            )
            return
        if not state.terminal_state_and_evidence_refreshed:
            yield _step(
                state,
                label="terminal_state_and_evidence_refreshed",
                action="refresh terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route shutdown",
                terminal_state_and_evidence_refreshed=True,
                active_node="ready_to_complete",
            )
            return
        if not state.lifecycle_reconciliation_done:
            yield _step(
                state,
                label="lifecycle_reconciliation_completed",
                action="scan Codex heartbeat automations, local state, and execution frontier before route shutdown",
                lifecycle_reconciliation_done=True,
                active_node="reconcile_lifecycle",
            )
            return
        if not state.terminal_router_daemon_stopped:
            yield _step(
                state,
                label="terminal_router_daemon_stopped",
                action="stop the persistent Router daemon, release its run lock, stop Controller action watching, and write terminal daemon status before final route shutdown",
                router_daemon_started=False,
                router_daemon_lock_acquired=False,
                router_daemon_tick_seconds=0,
                controller_action_watch_active=False,
                terminal_router_daemon_stopped=True,
                active_node="terminal_router_daemon_stopped",
            )
            return
        if not state.terminal_lifecycle_frontier_written:
            yield _step(
                state,
                label="terminal_lifecycle_frontier_written",
                action="write terminal heartbeat lifecycle back to execution frontier before stopping heartbeat",
                terminal_lifecycle_frontier_written=True,
                active_node="terminal_lifecycle_frontier_synced",
            )
            return
        if not state.crew_memory_archived:
            yield _step(
                state,
                label="crew_memory_archived_at_terminal",
                action="archive final role memory packet statuses after lifecycle reconciliation and before crew ledger archive",
                crew_memory_archived=True,
                active_node="ready_to_archive_crew",
            )
            return
        if not state.crew_archived:
            yield _step(
                state,
                label="crew_archived_at_terminal",
                action="archive persistent crew ledger and final role statuses after role memory archive and before final report",
                crew_archived=True,
                active_node="ready_to_emit_final_report",
            )
            return
        if not state.flowpilot_skill_improvement_report_written:
            yield _step(
                state,
                label="flowpilot_skill_improvement_report_written",
                action="PM writes a nonblocking FlowPilot skill improvement report from node observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                flowpilot_skill_improvement_report_written=True,
                active_node="ready_to_emit_final_report",
            )
            return
        if not state.pm_completion_decision_recorded:
            yield _step(
                state,
                label="pm_completion_decision_recorded",
                action="project manager approves completion after final product replay, final human review, high-value review, lifecycle cleanup, and crew archive",
                pm_completion_decision_recorded=True,
                active_node="ready_to_emit_final_report",
            )
            return
        yield _step(
            state,
            label="final_report_emitted",
            action="emit final report, emit terminal completion notice, and reconcile continuation lifecycle",
            status="complete",
            heartbeat_active=False,
            final_report_emitted=True,
            terminal_completion_notice_recorded=True,
            active_node="complete",
        )
        return
