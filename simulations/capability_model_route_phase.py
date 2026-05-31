"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "DEFAULT_FOCUSED_SELF_INTERROGATION_QUESTIONS",
    "FunctionResult",
    "Iterable",
    "State",
    "TARGET_PARENT_NODES",
    "_capability_structural_repair_changes",
    "_runtime_role_binding_startup_resolved",
    "_merged_changes",
    "_reset_execution_quality_gates",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_route_phase"]


def apply_route_phase(self, state: State) -> Iterable[FunctionResult]:
    if state.task_kind == "unknown":
        yield _step(
            state,
            label="classified_backend_task",
            action="classify task as non-UI software project",
            task_kind="backend",
        )
        yield _step(
            state,
            label="classified_ui_task",
            action="classify task as substantial user-facing UI project",
            task_kind="ui",
        )
        return

    if not state.capabilities_manifest_written:
        yield _step(
            state,
            label="capabilities_manifest_written",
            action="write capabilities manifest for required and conditional skills",
            capabilities_manifest_written=True,
        )
        return

    if not state.pm_child_skill_selection_manifest_written:
        yield _step(
            state,
            label="pm_child_skill_selection_manifest_written",
            action="project manager writes a child-skill selection manifest from the product architecture, capability map, and local skill inventory",
            pm_child_skill_selection_manifest_written=True,
        )
        return

    if not state.pm_child_skill_minimum_sufficient_complexity_review_written:
        yield _step(
            state,
            label="pm_child_skill_minimum_sufficient_complexity_review_written",
            action="project manager records simpler-path review for selected child skills and requires each required skill to justify its added handoffs, gates, references, or artifacts",
            pm_child_skill_minimum_sufficient_complexity_review_written=True,
        )
        return

    if not state.pm_child_skill_selection_scope_decisions_recorded:
        yield _step(
            state,
            label="pm_child_skill_selection_scope_decisions_recorded",
            action="project manager classifies candidate skills as required, conditional, deferred, or rejected before child-skill route discovery",
            pm_child_skill_selection_scope_decisions_recorded=True,
        )
        return

    if not state.child_skill_route_design_discovery_started:
        yield _step(
            state,
            label="child_skill_route_design_discovery_started",
            action="project manager starts route-design discovery only from PM-selected child skills, not from raw local skill availability",
            child_skill_route_design_discovery_started=True,
        )
        return

    if not state.child_skill_initial_gate_manifest_extracted:
        yield _step(
            state,
            label="child_skill_initial_gate_manifest_extracted",
            action="extract child-skill stages, checks, standards, evidence needs, and skipped-reference reasons into an initial gate manifest before route modeling",
            child_skill_initial_gate_manifest_extracted=True,
        )
        return

    if not state.child_skill_gate_approvers_assigned:
        yield _step(
            state,
            label="child_skill_gate_approvers_assigned",
            action="assign required approver roles for every child-skill gate and forbid controller or worker self-approval",
            child_skill_gate_approvers_assigned=True,
        )
        return

    if not state.child_skill_manifest_independent_validation_done:
        yield _step(
            state,
            label="child_skill_manifest_independent_validation_done",
            action="PM and human-like reviewer independently probe the child-skill manifest slices instead of accepting the extraction report",
            child_skill_manifest_independent_validation_done=True,
        )
        return

    if not state.child_skill_manifest_reviewer_reviewed:
        yield _step(
            state,
            label="child_skill_manifest_reviewer_reviewed",
            action="human-like reviewer reviews human/product/visual/interaction child-skill gates before they enter the route",
            child_skill_manifest_reviewer_reviewed=True,
        )
        return

    if not state.child_skill_manifest_pm_approved_for_route:
        yield _step(
            state,
            label="child_skill_manifest_pm_approved_for_route",
            action="project manager approves the child-skill gate manifest for inclusion in the initial route, PM runway, and visible plan",
            child_skill_manifest_pm_approved_for_route=True,
        )
        return

    if not state.child_skill_focused_interrogation_done:
        yield _step(
            state,
            label="child_skill_focused_interrogation_completed",
            action="run 20-50 focused self-interrogation questions for invoked child-skill boundaries",
            child_skill_focused_interrogation_done=True,
            child_skill_focused_interrogation_questions=DEFAULT_FOCUSED_SELF_INTERROGATION_QUESTIONS,
            child_skill_focused_interrogation_scope_id="invoked-child-skills",
        )
        return

    if not state.node_self_interrogation_record_written:
        yield _step(
            state,
            label="node_self_interrogation_record_written",
            action="write a durable current-node self-interrogation record before child-skill contract loading, acceptance planning, or worker packet dispatch can rely on the self-interrogation result",
            node_self_interrogation_record_written=True,
        )
        return

    if not state.node_self_interrogation_findings_dispositioned:
        yield _step(
            state,
            label="node_self_interrogation_findings_dispositioned",
            action="PM binds current-node self-interrogation findings into the node acceptance plan, a later gate, the suggestion ledger, a rejection, or an explicit waiver before packet dispatch",
            node_self_interrogation_findings_dispositioned=True,
        )
        return

    if not state.child_skill_contracts_loaded:
        yield _step(
            state,
            label="child_skill_contracts_loaded",
            action="read each invoked source skill's SKILL.md and relevant references",
            child_skill_contracts_loaded=True,
        )
        return

    if not state.child_skill_exact_source_verified:
        yield _step(
            state,
            label="child_skill_exact_source_verified",
            action="verify the exact source skill was loaded instead of a similar local substitute",
            child_skill_exact_source_verified=True,
        )
        return

    if not state.child_skill_substitutes_rejected:
        yield _step(
            state,
            label="child_skill_substitutes_rejected",
            action="record that ad hoc concept substitutes cannot satisfy child-skill gates",
            child_skill_substitutes_rejected=True,
        )
        return

    if not state.child_skill_original_standards_extracted:
        yield _step(
            state,
            label="child_skill_original_standards_extracted",
            action="extract the invoked skills' original standards, defaults, iteration budgets, review obligations, and waiver rules before PM packaging",
            child_skill_original_standards_extracted=True,
        )
        return

    if not state.child_skill_standards_promoted_to_node_contract:
        yield _step(
            state,
            label="child_skill_standards_promoted_to_node_contract",
            action="promote extracted child-skill standards into the current node contract so PM packages cannot silently lower them",
            child_skill_standards_promoted_to_node_contract=True,
        )
        return

    if not state.child_skill_gate_evidence_obligations_bound:
        yield _step(
            state,
            label="child_skill_gate_evidence_obligations_bound",
            action="bind every child-skill gate to concrete execution artifacts, reviewer-owned checks, and non-manifest evidence obligations",
            child_skill_gate_evidence_obligations_bound=True,
        )
        return

    if not state.flowpilot_invocation_policy_mapped:
        yield _step(
            state,
            label="flowpilot_invocation_policy_mapped",
            action="map FlowPilot-owned formal invocation policy for general-purpose child skills",
            flowpilot_invocation_policy_mapped=True,
        )
        return

    if not state.child_skill_requirements_mapped:
        yield _step(
            state,
            label="child_skill_requirements_mapped",
            action="map child skill workflow, hard gates, and completion standard into route gates",
            child_skill_requirements_mapped=True,
        )
        return

    if not state.child_skill_evidence_plan_written:
        yield _step(
            state,
            label="child_skill_evidence_plan_written",
            action="write evidence checklist for each invoked child skill",
            child_skill_evidence_plan_written=True,
        )
        return

    if not state.child_skill_subroute_projected:
        yield _step(
            state,
            label="child_skill_subroute_projected",
            action="project each invoked child skill into a visible mini-route of key milestones, not copied prompt details",
            child_skill_subroute_projected=True,
        )
        return

    if not state.child_skill_conformance_model_checked:
        yield _step(
            state,
            label="child_skill_conformance_model_checked",
            action="FlowGuard operator models and approves child-skill contract conformance before capability work",
            child_skill_conformance_model_checked=True,
            child_skill_conformance_model_flowguard_operator_route_scope_approved=True,
        )
        return

    if not state.strict_gate_obligation_review_model_checked:
        yield _step(
            state,
            label="strict_gate_obligation_review_model_checked",
            action="route-scope FlowGuard operator runs the strict gate-obligation model so child-skill review caveats cannot close the active gate",
            strict_gate_obligation_review_model_checked=True,
        )
        return

    if not state.flowguard_dependency_checked:
        yield _step(
            state,
            label="flowguard_dependency_checked",
            action="verify real FlowGuard package and model-first skill",
            flowguard_dependency_checked=True,
        )
        return

    if not state.dependency_plan_recorded:
        yield _step(
            state,
            label="dependency_plan_recorded",
            action="record dependency inventory and defer non-current installs",
            dependency_plan_recorded=True,
            future_installs_deferred=True,
        )
        return

    if not state.continuation_probe_done:
        yield _step(
            state,
            label="host_continuation_capability_supported",
            action="probe host automation capability, record host-kind continuation evidence, and confirm real heartbeat setup is supported",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            host_continuation_supported=True,
        )
        yield _step(
            state,
            label="host_continuation_capability_unsupported_manual_resume",
            action="probe host automation capability, record host-kind evidence, find no real wakeup support, and record manual-resume mode without creating heartbeat automation",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            host_continuation_supported=False,
            manual_resume_mode_recorded=True,
        )
        return

    if state.host_continuation_supported and not state.heartbeat_schedule_created:
        yield _step(
            state,
            label="heartbeat_schedule_created",
            action="create one-minute route heartbeat as a stable launcher that reads state and execution frontier",
            heartbeat_schedule_created=True,
            route_heartbeat_interval_minutes=1,
            stable_heartbeat_launcher_recorded=True,
            heartbeat_bound_to_current_run=True,
            heartbeat_same_name_only_checked=False,
        )
        return

    if not state.pm_initial_capability_decision_recorded:
        yield _step(
            state,
            label="pm_initial_capability_decision_recorded",
            action="ask the project manager to choose the capability-route direction from the contract, child-skill map, dependency plan, and role binding reports",
            pm_initial_capability_decision_recorded=True,
        )
        return

    if not state.flowguard_process_design_done:
        yield _step(
            state,
            label="flowguard_process_designed",
            action="route-scope FlowGuard operator uses FlowGuard as the capability-route process designer",
            flowguard_process_design_done=True,
        )
        return

    if not state.flowguard_operator_model_adversarial_probe_done:
        yield _step(
            state,
            label="flowguard_operator_model_adversarial_probe_done",
            action="FlowGuard operators run or validate model checks, inspect counterexamples, cite state fields, labels, counts, commands, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, and blindspots before model approvals",
            flowguard_operator_model_adversarial_probe_done=True,
            flowguard_model_report_risk_tiers_done=True,
            flowguard_model_report_pm_review_agenda_done=True,
            flowguard_model_report_toolchain_recommendations_done=True,
            flowguard_model_report_confidence_boundary_done=True,
        )
        return

    if not state.meta_route_checked:
        yield _step(
            state,
            label="meta_route_checked",
            action="route-scope FlowGuard operator approves meta-route checks from FlowGuard operator-owned adversarial model evidence",
            meta_route_checked=True,
            meta_route_flowguard_operator_route_scope_approved=True,
        )
        return

    if not state.capability_route_checked:
        yield _step(
            state,
            label="capability_route_checked",
            action="route-scope FlowGuard operator approves capability-route checks from FlowGuard operator-owned adversarial model evidence",
            capability_route_version=state.capability_route_version or 1,
            capability_route_checked=True,
            capability_route_flowguard_operator_route_scope_approved=True,
        )
        return

    if not state.parent_backward_structural_trigger_rule_recorded:
        yield _step(
            state,
            label="parent_backward_structural_trigger_rule_recorded",
            action="project manager records that every effective capability route node with children requires local parent backward replay without semantic importance guessing",
            parent_backward_structural_trigger_rule_recorded=True,
        )
        return

    if (
        not state.parent_backward_review_targets_enumerated
        or state.parent_backward_review_targets_route_version
        != state.capability_route_version
    ):
        yield _step(
            state,
            label="parent_backward_review_targets_enumerated",
            action="project manager enumerates all effective capability parent/composite nodes directly from the current route structure",
            parent_backward_review_targets_enumerated=True,
            parent_backward_review_targets_route_version=state.capability_route_version,
            parent_backward_targets_count=TARGET_PARENT_NODES,
        )
        return

    if not state.capability_product_function_model_checked:
        yield _step(
            state,
            label="capability_product_function_model_checked",
            action="product-scope FlowGuard operator approves the capability product-function model from FlowGuard operator-owned adversarial model evidence",
            capability_product_function_model_checked=True,
            capability_product_function_model_flowguard_operator_product_scope_approved=True,
        )
        return

    if not state.capability_evidence_synced:
        yield _step(
            state,
            label="capability_evidence_synced",
            action="sync capability evidence JSON and English summary",
            capability_evidence_synced=True,
        )
        return

    if not state.execution_frontier_written:
        yield _step(
            state,
            label="execution_frontier_written",
            action="write capability execution frontier from checked route, active gate, next gate, and current mainline",
            execution_frontier_written=True,
            frontier_version=state.capability_route_version,
        )
        return

    if not state.codex_plan_synced:
        yield _step(
            state,
            label="codex_plan_synced",
            action="sync visible Codex plan from capability execution frontier without changing heartbeat automation prompt",
            codex_plan_synced=True,
            plan_version=state.frontier_version,
        )
        return

    if not state.capability_user_flow_diagram_refreshed:
        yield _step(
            state,
            label="capability_user_flow_diagram_refreshed",
            action="refresh single user flow diagram from checked capability route and execution frontier before chat or UI display",
            capability_user_flow_diagram_refreshed=True,
        )
        return

    if (
        state.capability_route_checked
        and state.capability_product_function_model_checked
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and not state.capability_user_flow_diagram_emitted
    ):
        yield _step(
            state,
            label="capability_user_flow_diagram_emitted",
            action="emit visible capability user flow diagram with next gates, checks, and fallback branches",
            capability_user_flow_diagram_emitted=True,
        )
        return

    if (
        state.capability_route_checked
        and state.capability_product_function_model_checked
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and not state.runtime_role_assistance_decision_recorded
    ):
        yield _step(
            state,
            label="runtime_role_binding_start_authorized",
            action="ask for and record user authorization to request runtime FlowPilot role assistance from the host",
            runtime_role_assistance_decision_recorded=True,
        )
        return

    if (
        state.capability_route_checked
        and state.capability_product_function_model_checked
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and state.runtime_role_assistance_decision_recorded
        and not state.runtime_role_bindings_opened
        and not state.single_agent_role_continuity_authorized
    ):
        yield _step(
            state,
            label="fresh_six_runtime_role_bindings_opened",
            action="open runtime-requested FlowPilot role bindings as fresh current-task bindings and record nonreuse evidence",
            runtime_role_bindings_opened=True,
            runtime_role_bindings_current_task_ready=True,
            role_bindings_opened_after_startup_answers=True,
            role_bindings_opened_after_route_allocation=True,
            historical_agent_ids_compared=True,
            reused_historical_agent_ids=False,
        )
        return

    if (
        state.capability_route_checked
        and state.capability_product_function_model_checked
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and _runtime_role_binding_startup_resolved(state)
        and not state.startup_preflight_review_report_written
        and not state.startup_worker_remediation_completed
    ):
        yield _step(
            state,
            label="startup_preflight_reviewer_fact_report_blocked",
            action="human-like reviewer independently checks startup facts including run isolation, prior-work boundary, and current-task role-binding freshness, then reports blockers to PM without opening the start gate",
            startup_preflight_review_report_written=True,
            startup_preflight_review_blocking_findings=True,
            startup_reviewer_fact_evidence_checked=True,
            startup_reviewer_checked_run_isolation=True,
            startup_reviewer_checked_prior_work_boundary=True,
            startup_reviewer_checked_live_agent_freshness=True,
            startup_reviewer_checked_no_historical_agent_reuse=True,
            startup_reviewer_checked_capability_resolution=True,
            startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
        )
        return

    if (
        state.startup_preflight_review_report_written
        and state.startup_preflight_review_blocking_findings
        and not state.pm_returned_startup_blockers
        and not state.startup_worker_remediation_completed
        and not state.pm_start_gate_opened
    ):
        yield _step(
            state,
            label="pm_returns_startup_blockers_to_worker",
            action="project manager reads reviewer startup report and returns concrete blockers to workers for remediation",
            pm_returned_startup_blockers=True,
        )
        return

    if (
        state.startup_preflight_review_report_written
        and state.startup_preflight_review_blocking_findings
        and state.pm_returned_startup_blockers
        and not state.startup_worker_remediation_completed
        and not state.pm_start_gate_opened
    ):
        yield _step(
            state,
            label="startup_worker_remediation_completed",
            action="workers remediate startup blockers and invalidate the old reviewer report for recheck",
            startup_worker_remediation_completed=True,
            pm_returned_startup_blockers=False,
            startup_preflight_review_report_written=False,
            startup_preflight_review_blocking_findings=False,
            startup_reviewer_fact_evidence_checked=False,
            startup_reviewer_checked_run_isolation=False,
            startup_reviewer_checked_prior_work_boundary=False,
            startup_reviewer_checked_live_agent_freshness=False,
            startup_reviewer_checked_no_historical_agent_reuse=False,
            startup_reviewer_checked_capability_resolution=False,
            startup_reviewer_checked_current_run_heartbeat_binding=False,
            startup_pm_independent_gate_audit_done=False,
            startup_pm_capability_resolution_recorded=False,
        )
        return

    if (
        state.capability_route_checked
        and state.capability_product_function_model_checked
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and _runtime_role_binding_startup_resolved(state)
        and not state.startup_preflight_review_report_written
        and state.startup_worker_remediation_completed
    ):
        yield _step(
            state,
            label="startup_preflight_reviewer_fact_report_clean",
            action="human-like reviewer independently checks user answers, current run directory, current/index pointers, prior-work import boundary, real route state, continuation mode, cleanup boundary, current-task fresh role binding evidence, and writes a clean fact report for PM",
            startup_preflight_review_report_written=True,
            startup_preflight_review_blocking_findings=False,
            startup_reviewer_fact_evidence_checked=True,
            startup_reviewer_checked_run_isolation=True,
            startup_reviewer_checked_prior_work_boundary=True,
            startup_reviewer_checked_live_agent_freshness=True,
            startup_reviewer_checked_no_historical_agent_reuse=True,
            startup_reviewer_checked_capability_resolution=True,
            startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
        )
        return

    if (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and not state.startup_pm_independent_gate_audit_done
        and not state.pm_start_gate_opened
    ):
        yield _step(
            state,
            label="startup_pm_independent_gate_audit_done",
            action="PM independently audits capability startup run isolation, prior-work boundary, role-binding freshness or authorized continuity, reviewer evidence paths, and report-only failure hypotheses before opening the start gate",
            startup_pm_independent_gate_audit_done=True,
            startup_pm_capability_resolution_recorded=True,
        )
        return

    if (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and state.startup_pm_independent_gate_audit_done
        and not state.pm_start_gate_opened
    ):
        yield _step(
            state,
            label="pm_start_gate_opened_from_fact_report",
            action="project manager opens startup and allows work beyond startup from the current clean factual reviewer report",
            pm_start_gate_opened=True,
            work_beyond_startup_allowed=True,
        )
        return

    if state.capability_backward_issue_strategy != "none":
        if not state.capability_backward_issue_interrogated:
            yield _step(
                state,
                label="capability_backward_issue_interrogated",
                action="interrogate the failed capability backward review into an affected child, sibling gap, or subtree rebuild target",
                capability_backward_issue_interrogated=True,
            )
            return
        if (
            state.pm_repair_decision_interrogations
            <= state.capability_structural_route_repairs
        ):
            yield _step(
                state,
                label="pm_repair_decision_interrogated",
                action="interrogate the project manager on capability repair strategy before choosing child rework, sibling insertion, or subtree rebuild",
                pm_repair_decision_interrogations=(
                    state.pm_repair_decision_interrogations + 1
                ),
            )
            return

        reset_changes = _reset_execution_quality_gates()
        route_changes = _capability_structural_repair_changes(state)
        repair_changes = _merged_changes(route_changes, reset_changes)
        if state.capability_backward_issue_strategy == "existing_child":
            yield _step(
                state,
                label="capability_route_updated_to_rework_child_node",
                action="mutate the capability route back to the affected existing child node and invalidate the parent rollup",
                **repair_changes,
            )
            return
        if state.capability_backward_issue_strategy == "add_sibling":
            yield _step(
                state,
                label="capability_route_updated_to_add_sibling_child_node",
                action="mutate the capability route to add an adjacent sibling child node before parent closure",
                capability_new_sibling_nodes=state.capability_new_sibling_nodes + 1,
                **repair_changes,
            )
            return
        yield _step(
            state,
            label="capability_route_updated_to_rebuild_child_subtree",
            action="mutate the capability route to rebuild the child subtree from the capability product model",
            capability_subtree_rebuilds=state.capability_subtree_rebuilds + 1,
            **repair_changes,
        )
        return
