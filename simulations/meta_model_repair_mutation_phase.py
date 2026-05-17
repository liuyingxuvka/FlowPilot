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
    "MAX_COMPOSITE_STRUCTURAL_REPAIRS",
    "MAX_EXPERIMENTS",
    "MAX_IMPL_RETRIES",
    "MAX_ROUTE_REVISIONS",
    "State",
    "TARGET_CHUNKS",
    "_reset_execution_scope_gates",
    "_reset_user_flow_diagram_gate",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_repair_mutation_phase"]


def apply_repair_mutation_phase(self, state: State) -> Iterable[FunctionResult]:
    if state.issue == "terminal_backward_review_failure":
        if (
            state.pm_repair_decision_interrogations
            <= state.human_inspection_repairs
            + state.composite_structural_route_repairs
            + state.terminal_human_backward_replay_repairs
        ):
            yield _step(
                state,
                label="terminal_human_backward_pm_repair_decision_interrogated",
                action="PM decides the terminal backward replay repair target, affected downstream nodes, stale evidence, and whether the restarted final review begins at the delivered product or an impacted ancestor",
                pm_repair_decision_interrogations=(
                    state.pm_repair_decision_interrogations + 1
                ),
                active_node="pm_terminal_backward_replay_repair_strategy",
            )
            return
        yield _step(
            state,
            label="route_updated_after_terminal_human_backward_replay_failure",
            action="mutate the route to repair a terminal human backward replay finding, invalidate affected downstream evidence, and require a rebuilt ledger plus restarted final review",
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
            issue="none",
            terminal_human_backward_replay_repairs=(
                state.terminal_human_backward_replay_repairs + 1
            ),
            required_chunks=state.required_chunks,
            completed_chunks=max(0, state.completed_chunks - 1),
            node_human_inspections_passed=max(
                0, state.node_human_inspections_passed - 1
            ),
            composite_backward_reviews_passed=max(
                0, state.composite_backward_reviews_passed - 1
            ),
            composite_backward_pm_segment_decisions_recorded=max(
                0, state.composite_backward_pm_segment_decisions_recorded - 1
            ),
            chunk_state="none",
            verification_defined=False,
            checkpoint_written=False,
            parent_focused_interrogation_done=False,
            parent_focused_interrogation_questions=0,
            parent_focused_interrogation_scope_id="",
            unfinished_current_node_recovery_checked=False,
            node_focused_interrogation_done=False,
            node_focused_interrogation_questions=0,
            node_focused_interrogation_scope_id="",
            lightweight_self_check_done=False,
            lightweight_self_check_questions=0,
            lightweight_self_check_scope_id="",
            node_visible_roadmap_emitted=False,
            completion_self_interrogation_done=False,
            completion_self_interrogation_questions=0,
            completion_self_interrogation_layer_count=0,
            completion_self_interrogation_questions_per_layer=0,
            completion_self_interrogation_layers=0,
            completion_self_interrogation_record_written=False,
            completion_self_interrogation_findings_dispositioned=False,
            completion_visible_roadmap_emitted=False,
            high_value_work_review="unknown",
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
            active_node="run_terminal_backward_replay_repair_route_checks",
            **_reset_execution_scope_gates(),
        )
        return

    if state.issue == "model_gap":
        if state.route_revisions >= MAX_ROUTE_REVISIONS:
            yield _step(
                state,
                label="blocked_after_model_gap_budget",
                action="block after exhausting model update budget and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                active_node="blocked",
            )
            return
        yield _step(
            state,
            label="route_updated_after_model_gap",
            action="create new route version from refined model",
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
            issue="none",
            route_revisions=state.route_revisions + 1,
            chunk_state="none",
            verification_defined=False,
            checkpoint_written=False,
            node_focused_interrogation_done=False,
            node_focused_interrogation_questions=0,
            node_focused_interrogation_scope_id="",
            lightweight_self_check_done=False,
            lightweight_self_check_questions=0,
            lightweight_self_check_scope_id="",
            node_visible_roadmap_emitted=False,
            active_node="run_updated_meta_model_checks",
            **_reset_execution_scope_gates(),
        )
        return

    if state.issue == "composite_backward_failure":
        if not state.composite_issue_grilled:
            yield _step(
                state,
                label="composite_backward_issue_grilled",
                action="grill the failed composite backward review until it names the affected child, sibling gap, or subtree rebuild target",
                composite_issue_grilled=True,
                active_node="route_mutation_from_composite_backward_issue",
            )
            return
        if state.route_revisions >= MAX_ROUTE_REVISIONS:
            yield _step(
                state,
                label="blocked_after_composite_backward_repair_budget",
                action="block after exhausting composite backward structural repair route budget and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                active_node="blocked",
            )
            return
        if (
            state.pm_repair_decision_interrogations
            <= state.human_inspection_repairs
            + state.composite_structural_route_repairs
        ):
            yield _step(
                state,
                label="pm_repair_decision_interrogated",
                action="grill the project manager on composite repair strategy before choosing existing-child rework, sibling insertion, subtree rebuild, or parent impact bubbling",
                pm_repair_decision_interrogations=(
                    state.pm_repair_decision_interrogations + 1
                ),
                active_node="pm_composite_repair_strategy_decision",
            )
            return

        common_changes = {
            "route_version": state.route_version + 1,
            "route_checked": False,
            "markdown_synced": False,
            "execution_frontier_written": False,
            "codex_plan_synced": False,
            "frontier_version": 0,
            "plan_version": 0,
            "visible_user_flow_diagram_emitted": False,
            "user_flow_diagram_refreshed": False,
            "user_flow_diagram_reviewer_display_checked": False,
            "user_flow_diagram_reviewer_route_match_checked": False,
            "candidate_route_tree_generated": False,
            "root_route_model_checked": False,
            "root_route_model_process_officer_approved": False,
            "root_product_function_model_checked": False,
            "root_product_function_model_product_officer_approved": False,
            "strict_gate_obligation_review_model_checked": False,
            "parent_backward_review_targets_enumerated": False,
            "parent_subtree_review_checked": False,
            "parent_focused_interrogation_done": False,
            "parent_focused_interrogation_questions": 0,
            "parent_focused_interrogation_scope_id": "",
            "unfinished_current_node_recovery_checked": False,
            "issue": "none",
            "route_revisions": state.route_revisions + 1,
            "chunk_state": "none",
            "verification_defined": False,
            "checkpoint_written": False,
            "node_focused_interrogation_done": False,
            "node_focused_interrogation_questions": 0,
            "node_focused_interrogation_scope_id": "",
            "lightweight_self_check_done": False,
            "lightweight_self_check_questions": 0,
            "lightweight_self_check_scope_id": "",
            "node_visible_roadmap_emitted": False,
            "composite_structural_route_repairs": state.composite_structural_route_repairs + 1,
            "active_node": "run_composite_backward_structural_route_checks",
        }

        if state.composite_issue_strategy == "existing_child":
            yield _step(
                state,
                label="route_updated_to_rework_composite_child",
                action="mutate the route to jump back to the affected existing child node and invalidate its parent rollup",
                completed_chunks=max(0, state.completed_chunks - 1),
                node_human_inspections_passed=max(
                    0, state.node_human_inspections_passed - 1
                ),
                composite_backward_reviews_passed=max(
                    0, state.composite_backward_reviews_passed - 1
                ),
                composite_backward_pm_segment_decisions_recorded=max(
                    0, state.composite_backward_pm_segment_decisions_recorded - 1
                ),
                **common_changes,
                **_reset_execution_scope_gates(),
            )
            return

        if state.composite_issue_strategy == "add_sibling":
            yield _step(
                state,
                label="route_updated_to_add_composite_sibling",
                action="mutate the route to insert an adjacent sibling child before the parent can close",
                required_chunks=state.required_chunks + 1,
                completed_chunks=max(0, state.completed_chunks - 1),
                node_human_inspections_passed=max(
                    0, state.node_human_inspections_passed - 1
                ),
                composite_backward_reviews_passed=max(
                    0, state.composite_backward_reviews_passed - 1
                ),
                composite_backward_pm_segment_decisions_recorded=max(
                    0, state.composite_backward_pm_segment_decisions_recorded - 1
                ),
                composite_new_sibling_nodes=state.composite_new_sibling_nodes + 1,
                **common_changes,
                **_reset_execution_scope_gates(),
            )
            return

        yield _step(
            state,
            label="route_updated_to_rebuild_composite_subtree",
            action="mutate the route to rebuild the whole child subtree from the parent model",
            required_chunks=TARGET_CHUNKS,
            completed_chunks=0,
            node_human_inspections_passed=0,
            composite_backward_reviews_passed=0,
            composite_backward_pm_segment_decisions_recorded=0,
            composite_subtree_rebuilds=state.composite_subtree_rebuilds + 1,
            **common_changes,
            **_reset_execution_scope_gates(),
        )
        return

    if state.issue == "inspection_failure":
        if state.blocking_defect_open and not state.pm_defect_triage_done:
            yield _step(
                state,
                label="pm_triages_blocking_human_review_defect",
                action="PM reads the defect ledger entry, assigns severity, owner, route impact, and same-class recheck condition before repair routing",
                pm_defect_triage_done=True,
                active_node="pm_inspection_repair_strategy_decision",
            )
            return
        if not state.inspection_issue_grilled:
            yield _step(
                state,
                label="human_inspection_issue_grilled",
                action="grill the failed human-like inspection until it has evidence, severity, repair target, and recheck condition",
                inspection_issue_grilled=True,
                active_node="route_mutation_from_inspection_issue",
            )
            return
        if state.route_revisions >= MAX_ROUTE_REVISIONS:
            yield _step(
                state,
                label="blocked_after_inspection_repair_budget",
                action="block after exhausting inspection-driven repair route budget and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                active_node="blocked",
            )
            return
        if (
            state.pm_repair_decision_interrogations
            <= state.human_inspection_repairs
            + state.composite_structural_route_repairs
        ):
            yield _step(
                state,
                label="pm_repair_decision_interrogated",
                action="grill the project manager on inspection-failure repair strategy before route mutation: affected level, reset/add/split/rebuild choice, stale evidence, and recheck condition",
                pm_repair_decision_interrogations=(
                    state.pm_repair_decision_interrogations + 1
                ),
                active_node="pm_inspection_repair_strategy_decision",
            )
            return
        yield _step(
            state,
            label="route_updated_after_human_inspection_failure",
            action="mutate the route with a repair node after human-like inspection rejects the current product evidence",
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
            issue="none",
            route_revisions=state.route_revisions + 1,
            human_inspection_repairs=state.human_inspection_repairs + 1,
            blocking_defect_open=False,
            blocking_defect_fixed_pending_recheck=True,
            defect_same_class_recheck_done=False,
            chunk_state="none",
            verification_defined=False,
            checkpoint_written=False,
            node_focused_interrogation_done=False,
            node_focused_interrogation_questions=0,
            node_focused_interrogation_scope_id="",
            lightweight_self_check_done=False,
            lightweight_self_check_questions=0,
            lightweight_self_check_scope_id="",
            node_visible_roadmap_emitted=False,
            active_node="run_human_inspection_repair_model_checks",
            **_reset_execution_scope_gates(),
        )
        return

    if state.issue == "impl_failure":
        if state.impl_retries < MAX_IMPL_RETRIES:
            yield _step(
                state,
                label="implementation_fixed_for_retry",
                action="fix implementation and retry same verified chunk boundary",
                issue="none",
                impl_retries=state.impl_retries + 1,
                chunk_state="ready",
                verification_defined=True,
                active_node="execute_chunk",
            )
            return
        yield _step(
            state,
            label="implementation_failure_to_experiment",
            action="switch repeated implementation failure into bounded experiment",
            issue="unknown_failure",
            chunk_state="none",
            verification_defined=False,
            active_node="bounded_experiment",
            **_reset_execution_scope_gates(),
        )
        return

    if state.issue in {"unknown_failure", "no_progress"}:
        if state.experiments < MAX_EXPERIMENTS:
            yield _step(
                state,
                label="experiment_found_new_path",
                action="record bounded experiment and create revised route",
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
                issue="none",
                experiments=state.experiments + 1,
                route_revisions=state.route_revisions + 1,
                node_focused_interrogation_done=False,
                node_focused_interrogation_questions=0,
                node_focused_interrogation_scope_id="",
                lightweight_self_check_done=False,
                lightweight_self_check_questions=0,
                lightweight_self_check_scope_id="",
                node_visible_roadmap_emitted=False,
                active_node="run_experiment_route_checks",
                **_reset_execution_scope_gates(),
            )
            return
        yield _step(
            state,
            label="blocked_after_experiment_budget",
            action="block after bounded experiments fail to find a path and emit a nonterminal resume notice",
            status="blocked",
            heartbeat_active=False,
            controlled_stop_notice_recorded=True,
            pause_snapshot_written=True,
            active_node="blocked",
        )
        return

    if state.chunk_state == "checkpoint_pending":
        if not state.composite_backward_context_loaded:
            yield _step(
                state,
                label="composite_backward_context_loaded",
                action="load child evidence, parent goal, product-function model, and route structure before composite closure",
                composite_backward_context_loaded=True,
                active_node="replay_composite_child_evidence",
            )
            return
        if not state.composite_child_evidence_replayed:
            yield _step(
                state,
                label="composite_child_evidence_replayed",
                action="replay child evidence backward against the parent/composite product model",
                composite_child_evidence_replayed=True,
                active_node="observe_composite_rollup",
            )
            return
        if not state.composite_backward_neutral_observation_written:
            yield _step(
                state,
                label="composite_backward_neutral_observation_written",
                action="write a neutral observation of what the child rollup actually shows before judging parent closure",
                composite_backward_neutral_observation_written=True,
                active_node="decide_composite_structure_fit",
            )
            return
        if not state.composite_structure_decision_recorded:
            yield _step(
                state,
                label="composite_structure_decision_recorded",
                action="classify whether the parent can close, needs an existing child rework, needs a sibling child, or needs subtree rebuild",
                composite_structure_decision_recorded=True,
                active_node="composite_backward_human_review",
            )
            return
        if not state.composite_reviewer_independent_probe_done:
            yield _step(
                state,
                label="composite_reviewer_independent_probe_done",
                action="composite backward reviewer independently probes child evidence, parent model fit, missing sibling paths, stale artifacts, and report-only failure hypotheses before approving closure",
                composite_reviewer_independent_probe_done=True,
                active_node="composite_backward_human_review",
            )
            return
        if not state.composite_backward_human_review_passed:
            if state.composite_structural_route_repairs < MAX_COMPOSITE_STRUCTURAL_REPAIRS:
                yield _step(
                    state,
                    label="composite_backward_review_found_existing_child_gap",
                    action="composite backward reviewer rejects parent closure and targets an existing child for rework",
                    issue="composite_backward_failure",
                    composite_issue_strategy="existing_child",
                    chunk_state="none",
                    verification_defined=False,
                    checkpoint_written=False,
                    active_node="grill_composite_backward_issue",
                )
                yield _step(
                    state,
                    label="composite_backward_review_found_missing_sibling",
                    action="composite backward reviewer rejects parent closure because an adjacent sibling child is missing",
                    issue="composite_backward_failure",
                    composite_issue_strategy="add_sibling",
                    chunk_state="none",
                    verification_defined=False,
                    checkpoint_written=False,
                    active_node="grill_composite_backward_issue",
                )
                yield _step(
                    state,
                    label="composite_backward_review_found_subtree_mismatch",
                    action="composite backward reviewer rejects parent closure and requires child subtree rebuild",
                    issue="composite_backward_failure",
                    composite_issue_strategy="rebuild_subtree",
                    chunk_state="none",
                    verification_defined=False,
                    checkpoint_written=False,
                    active_node="grill_composite_backward_issue",
                )
                return
            yield _step(
                state,
                label="composite_backward_review_passed",
                action="human-like composite backward reviewer accepts the child rollup before PM decides the parent segment",
                composite_backward_human_review_passed=True,
                composite_backward_review_reviewer_approved=True,
                composite_backward_reviews_passed=state.composite_backward_reviews_passed + 1,
                active_node="record_parent_backward_pm_segment_decision",
            )
            return
        if not state.composite_backward_pm_segment_decision_recorded:
            yield _step(
                state,
                label="composite_backward_pm_segment_decision_recorded",
                action="project manager records the parent backward replay segment decision before parent checkpoint closure",
                composite_backward_pm_segment_decision_recorded=True,
                composite_backward_pm_segment_decisions_recorded=state.composite_backward_pm_segment_decisions_recorded
                + 1,
                active_node="write_checkpoint",
            )
            return
        if not state.role_memory_refreshed_after_work:
            yield _step(
                state,
                label="role_memory_packets_refreshed_after_work",
                action="refresh compact role memory packets after meaningful role work and before checkpoint",
                role_memory_refreshed_after_work=True,
                active_node="write_checkpoint",
            )
            return
        yield _step(
            state,
            label="checkpoint_written",
            action="write verified checkpoint; when another route node remains, invalidate old route-sign display evidence before the next node entry",
            checkpoint_written=True,
            chunk_state="none",
            heartbeat_health_checked=False,
            parent_focused_interrogation_done=False,
            parent_focused_interrogation_questions=0,
            parent_focused_interrogation_scope_id="",
            node_focused_interrogation_done=False,
            node_focused_interrogation_questions=0,
            node_focused_interrogation_scope_id="",
            lightweight_self_check_done=False,
            lightweight_self_check_questions=0,
            lightweight_self_check_scope_id="",
            node_visible_roadmap_emitted=False,
            parent_subtree_review_checked=False,
            unfinished_current_node_recovery_checked=False,
            active_node="refresh_user_flow_diagram"
            if state.completed_chunks < state.required_chunks
            else "ready_to_complete",
            **(
                _reset_user_flow_diagram_gate()
                if state.completed_chunks < state.required_chunks
                else {}
            ),
            **_reset_execution_scope_gates(),
        )
        return
