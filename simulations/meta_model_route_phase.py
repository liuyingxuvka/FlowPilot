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
    "MAX_ROUTE_REVISIONS",
    "State",
    "_live_subagent_startup_resolved",
    "_step",
    "_user_flow_display_gate_passed",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_route_phase"]


def apply_route_phase(self, state: State) -> Iterable[FunctionResult]:
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
            active_node="design_flowguard_route",
        )
        return

    if not state.pm_initial_route_decision_recorded:
        yield _step(
            state,
            label="pm_initial_route_decision_recorded",
            action="ask the project manager to choose the initial route-design direction from the contract, self-interrogation, dependencies, and crew reports",
            pm_initial_route_decision_recorded=True,
            active_node="select_child_skills",
        )
        return

    if not state.pm_child_skill_selection_manifest_written:
        yield _step(
            state,
            label="pm_child_skill_selection_manifest_written",
            action="project manager writes a child-skill selection manifest from the product architecture, route direction, and local skill inventory",
            pm_child_skill_selection_manifest_written=True,
            active_node="record_child_skill_minimum_sufficient_complexity",
        )
        return

    if not state.pm_child_skill_minimum_sufficient_complexity_review_written:
        yield _step(
            state,
            label="pm_child_skill_minimum_sufficient_complexity_review_written",
            action="project manager records simpler-path review for selected child skills and requires each required skill to justify its added handoffs, gates, references, or artifacts",
            pm_child_skill_minimum_sufficient_complexity_review_written=True,
            active_node="classify_child_skill_selection_scope",
        )
        return

    if not state.pm_child_skill_selection_scope_decisions_recorded:
        yield _step(
            state,
            label="pm_child_skill_selection_scope_decisions_recorded",
            action="project manager classifies candidate skills as required, conditional, deferred, or rejected before child-skill gate discovery",
            pm_child_skill_selection_scope_decisions_recorded=True,
            active_node="discover_child_skill_gates",
        )
        return

    if not state.child_skill_route_design_discovery_started:
        yield _step(
            state,
            label="child_skill_route_design_discovery_started",
            action="project manager discovers gate surfaces only from PM-selected child skills, not from raw local skill availability",
            child_skill_route_design_discovery_started=True,
            active_node="extract_child_skill_gate_manifest",
        )
        return

    if not state.child_skill_initial_gate_manifest_extracted:
        yield _step(
            state,
            label="child_skill_initial_gate_manifest_extracted",
            action="project manager extracts child-skill stages, standards, checks, evidence needs, and skipped references into an initial gate manifest",
            child_skill_initial_gate_manifest_extracted=True,
            active_node="assign_child_skill_gate_approvers",
        )
        return

    if not state.child_skill_gate_approvers_assigned:
        yield _step(
            state,
            label="child_skill_gate_approvers_assigned",
            action="project manager assigns required approver roles for every child-skill gate and forbids controller or worker self-approval",
            child_skill_gate_approvers_assigned=True,
            active_node="probe_child_skill_gate_manifest",
        )
        return

    if not state.child_skill_manifest_independent_validation_done:
        yield _step(
            state,
            label="child_skill_manifest_independent_validation_done",
            action="PM and human-like reviewer independently probe child-skill manifest slices instead of accepting the extraction report",
            child_skill_manifest_independent_validation_done=True,
            active_node="review_child_skill_gate_manifest",
        )
        return

    if not state.child_skill_manifest_reviewer_reviewed:
        yield _step(
            state,
            label="child_skill_manifest_reviewer_reviewed",
            action="human-like reviewer reviews product, visual, interaction, and real-use child-skill gates before route freeze",
            child_skill_manifest_reviewer_reviewed=True,
            active_node="pm_approve_child_skill_manifest",
        )
        return

    if not state.child_skill_manifest_pm_approved_for_route:
        yield _step(
            state,
            label="child_skill_manifest_pm_approved_for_route",
            action="project manager approves the child-skill gate manifest for inclusion in route modeling, the execution frontier, and the PM runway",
            child_skill_manifest_pm_approved_for_route=True,
            active_node="design_flowguard_route",
        )
        return

    if not state.flowguard_process_design_done:
        yield _step(
            state,
            label="flowguard_process_designed",
            action="process FlowGuard officer uses FlowGuard to design the route before implementation",
            flowguard_process_design_done=True,
            active_node="generate_candidate_route_tree",
        )
        return

    if not state.candidate_route_tree_generated:
        yield _step(
            state,
            label="candidate_route_tree_generated",
            action="generate candidate route tree from the frozen contract",
            candidate_route_tree_generated=True,
            active_node="write_recursive_decomposition_policy",
        )
        return

    if not state.recursive_route_decomposition_policy_written:
        yield _step(
            state,
            label="recursive_route_decomposition_policy_written",
            action="project manager records arbitrary-depth route decomposition, shallow display projection, PMK route memory, and split/merge stop rules before route checks",
            recursive_route_decomposition_policy_written=True,
            route_reviewer_depth_review_required=True,
            active_node="define_leaf_readiness_gates",
        )
        return

    if not state.route_leaf_readiness_gates_defined:
        yield _step(
            state,
            label="route_leaf_readiness_gates_defined",
            action="project manager defines leaf-readiness gates for dispatchable leaves and marks parent/module nodes as non-worker-dispatchable",
            route_leaf_readiness_gates_defined=True,
            active_node="check_root_route_model",
        )
        return

    if not state.flowguard_officer_model_adversarial_probe_done:
        yield _step(
            state,
            label="flowguard_officer_model_adversarial_probe_done",
            action="FlowGuard officers run or validate model checks, inspect counterexamples, cite state fields, labels, counts, commands, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, and blindspots before model approvals",
            flowguard_officer_model_adversarial_probe_done=True,
            flowguard_model_report_risk_tiers_done=True,
            flowguard_model_report_pm_review_agenda_done=True,
            flowguard_model_report_toolchain_recommendations_done=True,
            flowguard_model_report_confidence_boundary_done=True,
            active_node="check_root_route_model",
        )
        return

    if not state.root_route_model_checked:
        yield _step(
            state,
            label="root_route_model_checked",
            action="process FlowGuard officer approves checks against the candidate route tree from officer-owned adversarial model evidence",
            root_route_model_checked=True,
            root_route_model_process_officer_approved=True,
            active_node="check_root_product_function_model",
        )
        return

    if not state.root_product_function_model_checked:
        yield _step(
            state,
            label="root_product_function_model_checked",
            action="product FlowGuard officer approves checks against the root product-function model from officer-owned adversarial model evidence",
            root_product_function_model_checked=True,
            root_product_function_model_product_officer_approved=True,
            active_node="check_strict_gate_obligation_review_model",
        )
        return

    if not state.strict_gate_obligation_review_model_checked:
        yield _step(
            state,
            label="strict_gate_obligation_review_model_checked",
            action="process FlowGuard officer runs the strict gate-obligation model so current-scope caveats cannot close a review gate",
            strict_gate_obligation_review_model_checked=True,
            active_node="create_initial_route",
        )
        return

    if state.route_version == 0:
        yield _step(
            state,
            label="route_created",
            action="freeze checked candidate tree as canonical flow.json route",
            route_version=1,
            route_checked=False,
            markdown_synced=False,
            execution_frontier_written=False,
            codex_plan_synced=False,
            frontier_version=0,
            plan_version=0,
            active_node="run_meta_model_checks",
        )
        return

    if not state.route_checked:
        if state.route_revisions > MAX_ROUTE_REVISIONS:
            yield _step(
                state,
                label="blocked_after_repeated_route_failures",
                action="block because route model cannot be stabilized and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                active_node="blocked",
            )
            return
        yield _step(
            state,
            label="route_model_checked",
            action="run FlowGuard checks for active route",
            route_checked=True,
            active_node="check_router_leaf_only_dispatch_policy",
        )
        return

    if not state.router_leaf_only_dispatch_policy_checked:
        yield _step(
            state,
            label="router_leaf_only_dispatch_policy_checked",
            action="process model verifies Router can traverse the full route tree, dispatch only ready leaf/repair nodes, and send parent/module nodes to child subtree or backward replay",
            router_leaf_only_dispatch_policy_checked=True,
            active_node="record_parent_backward_trigger_rule",
        )
        return

    if not state.parent_backward_structural_trigger_rule_recorded:
        yield _step(
            state,
            label="parent_backward_structural_trigger_rule_recorded",
            action="project manager records the structural trigger: every effective route node with children requires local parent backward replay, without semantic importance guessing",
            parent_backward_structural_trigger_rule_recorded=True,
            active_node="enumerate_parent_backward_targets",
        )
        return

    if not state.parent_backward_review_targets_enumerated:
        yield _step(
            state,
            label="parent_backward_review_targets_enumerated",
            action="project manager enumerates all effective parent/composite nodes directly from flow.json before route execution or after route mutation",
            parent_backward_review_targets_enumerated=True,
            active_node="record_user_flow_shallow_projection_policy",
        )
        return

    if not state.user_flow_diagram_shallow_projection_policy_recorded:
        yield _step(
            state,
            label="user_flow_diagram_shallow_projection_policy_recorded",
            action="record that user-visible route signs render only the shallow route projection while showing the active deep path and hidden leaf progress",
            user_flow_diagram_shallow_projection_policy_recorded=True,
            active_node="sync_markdown_summary",
        )
        return

    if not state.markdown_synced:
        yield _step(
            state,
            label="markdown_summary_synced",
            action="sync English Markdown summary from canonical JSON",
            markdown_synced=True,
            active_node="write_execution_frontier",
        )
        return

    if not state.execution_frontier_written:
        yield _step(
            state,
            label="execution_frontier_written",
            action="write execution_frontier.json from checked route, active node, next node, and current mainline",
            execution_frontier_written=True,
            frontier_version=state.route_version,
            active_node="sync_codex_plan",
        )
        return

    if not state.codex_plan_synced:
        yield _step(
            state,
            label="codex_plan_synced",
            action="sync current visible Codex plan from execution frontier without changing heartbeat automation prompt",
            codex_plan_synced=True,
            plan_version=state.frontier_version,
            active_node="refresh_user_flow_diagram",
        )
        return

    if not state.user_flow_diagram_refreshed:
        yield _step(
            state,
            label="user_flow_diagram_refreshed",
            action="refresh single user flow diagram from checked flow.json and execution_frontier.json before chat or UI display",
            user_flow_diagram_refreshed=True,
            active_node="emit_user_flow_diagram",
        )
        return

    if (
        state.route_version > 0
        and state.route_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and not state.visible_user_flow_diagram_emitted
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="visible_user_flow_diagram_emitted",
            action="emit simplified English FlowPilot Route Sign Mermaid in chat when Cockpit UI is not open, with current node, next jumps, checks, fallback branches, and simulated path",
            visible_user_flow_diagram_emitted=True,
            user_flow_diagram_chat_display_required=True,
            user_flow_diagram_chat_displayed=True,
            user_flow_diagram_return_edge_present=state.user_flow_diagram_return_edge_required,
            user_flow_diagram_reviewer_display_checked=False,
            user_flow_diagram_reviewer_route_match_checked=False,
            user_flow_diagram_fresh_for_current_node=False,
            active_node="resolve_live_subagent_startup",
        )
        return

    if (
        state.visible_user_flow_diagram_emitted
        and state.user_flow_diagram_refreshed
        and not state.user_flow_diagram_reviewer_display_checked
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="user_flow_diagram_reviewer_display_checked",
            action="human-like reviewer checks the visible chat Mermaid route sign, active route/node match, and return-for-repair edge before route progress",
            user_flow_diagram_reviewer_display_checked=True,
            user_flow_diagram_reviewer_route_match_checked=True,
            user_flow_diagram_fresh_for_current_node=True,
            active_node="resolve_live_subagent_startup",
        )
        return

    if (
        state.route_version > 0
        and state.route_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.user_flow_diagram_refreshed
        and _user_flow_display_gate_passed(state)
        and not state.live_subagent_decision_recorded
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="live_subagent_start_authorized",
            action="ask for and record user authorization to start the six live FlowPilot background agents",
            live_subagent_decision_recorded=True,
            active_node="start_live_subagents",
        )
        return

    if (
        state.route_version > 0
        and state.route_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.user_flow_diagram_refreshed
        and _user_flow_display_gate_passed(state)
        and state.live_subagent_decision_recorded
        and not state.live_subagents_started
        and not state.single_agent_role_continuity_authorized
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="fresh_six_live_subagents_started",
            action="start all six live FlowPilot background agents as fresh current-task subagents and record nonreuse evidence",
            live_subagents_started=True,
            live_subagents_current_task_fresh=True,
            fresh_agents_spawned_after_startup_answers=True,
            fresh_agents_spawned_after_route_allocation=True,
            historical_agent_ids_compared=True,
            reused_historical_agent_ids=False,
            active_node="startup_preflight_review",
        )
        return

    if (
        state.route_version > 0
        and state.route_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.user_flow_diagram_refreshed
        and _user_flow_display_gate_passed(state)
        and _live_subagent_startup_resolved(state)
        and not state.startup_preflight_review_report_written
        and not state.startup_worker_remediation_completed
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="startup_preflight_reviewer_fact_report_blocked",
            action="human-like reviewer independently checks startup facts including run isolation, prior-work boundary, and current-task live-agent freshness, then reports blockers to PM without opening the start gate",
            startup_preflight_review_report_written=True,
            startup_preflight_review_blocking_findings=True,
            startup_reviewer_fact_evidence_checked=True,
            startup_reviewer_checked_run_isolation=True,
            startup_reviewer_checked_prior_work_boundary=True,
            startup_reviewer_checked_live_agent_freshness=True,
            startup_reviewer_checked_no_historical_agent_reuse=True,
            startup_reviewer_checked_capability_resolution=True,
            startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
            active_node="pm_interprets_startup_review",
        )
        return

    if (
        state.startup_preflight_review_report_written
        and state.startup_preflight_review_blocking_findings
        and not state.pm_returned_startup_blockers
        and not state.startup_worker_remediation_completed
        and not state.pm_start_gate_opened
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="pm_returns_startup_blockers_to_worker",
            action="project manager reads reviewer startup report and returns concrete blockers to workers for remediation",
            pm_returned_startup_blockers=True,
            active_node="startup_worker_remediation",
        )
        return

    if (
        state.startup_preflight_review_report_written
        and state.startup_preflight_review_blocking_findings
        and state.pm_returned_startup_blockers
        and not state.startup_worker_remediation_completed
        and not state.pm_start_gate_opened
        and state.issue == "none"
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
            active_node="startup_preflight_review",
        )
        return

    if (
        state.route_version > 0
        and state.route_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.user_flow_diagram_refreshed
        and _user_flow_display_gate_passed(state)
        and _live_subagent_startup_resolved(state)
        and not state.startup_preflight_review_report_written
        and state.startup_worker_remediation_completed
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="startup_preflight_reviewer_fact_report_clean",
            action="human-like reviewer independently checks user answers, current run directory, current/index pointers, prior-work import boundary, real route state, continuation mode, cleanup boundary, current-task fresh crew evidence, and writes a clean fact report for PM",
            startup_preflight_review_report_written=True,
            startup_preflight_review_blocking_findings=False,
            startup_reviewer_fact_evidence_checked=True,
            startup_reviewer_checked_run_isolation=True,
            startup_reviewer_checked_prior_work_boundary=True,
            startup_reviewer_checked_live_agent_freshness=True,
            startup_reviewer_checked_no_historical_agent_reuse=True,
            startup_reviewer_checked_capability_resolution=True,
            startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
            active_node="pm_interprets_startup_review",
        )
        return

    if (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and not state.startup_pm_independent_gate_audit_done
        and not state.pm_start_gate_opened
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="startup_pm_independent_gate_audit_done",
            action="PM independently audits startup run isolation, prior-work boundary, live-agent freshness or authorized continuity, reviewer evidence paths, and report-only failure hypotheses before opening the start gate",
            startup_pm_independent_gate_audit_done=True,
            startup_pm_capability_resolution_recorded=True,
            active_node="pm_start_gate_decision",
        )
        return

    if (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and state.startup_pm_independent_gate_audit_done
        and not state.pm_start_gate_opened
        and state.issue == "none"
    ):
        yield _step(
            state,
            label="pm_start_gate_opened_from_fact_report",
            action="project manager opens startup and allows work beyond startup from the current clean factual reviewer report",
            pm_start_gate_opened=True,
            work_beyond_startup_allowed=True,
            active_node="ready_for_chunk",
        )
        return

    if state.high_risk_gate == "pending":
        yield _step(
            state,
            label="high_risk_gate_approved",
            action="user approves hard safety gate",
            high_risk_gate="approved",
            active_node="ready_for_chunk",
        )
        yield _step(
            state,
            label="blocked_by_high_risk_denial",
            action="block because high-risk gate was denied and emit a nonterminal resume notice",
            status="blocked",
            heartbeat_active=False,
            controlled_stop_notice_recorded=True,
            pause_snapshot_written=True,
            high_risk_gate="denied",
            active_node="blocked",
        )
        return
