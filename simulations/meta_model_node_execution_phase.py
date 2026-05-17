"""Phase helper extracted from :mod:`meta_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import meta_model as _model
else:
    import meta_model as _model

_REQUIRED_MODEL_NAMES = (
    "DEFAULT_FOCUSED_GRILLME_QUESTIONS",
    "DEFAULT_LIGHTWEIGHT_SELF_CHECK_QUESTIONS",
    "FunctionResult",
    "Iterable",
    "MAX_QUALITY_REWORKS",
    "MAX_QUALITY_ROUTE_RAISES",
    "State",
    "TARGET_CHUNKS",
    "_reset_execution_scope_gates",
    "_route_ready",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_node_execution_phase"]


def apply_node_execution_phase(self, state: State) -> Iterable[FunctionResult]:
    if _route_ready(state) and state.completed_chunks < TARGET_CHUNKS:
        if not state.heartbeat_loaded_state:
            yield _step(
                state,
                label="heartbeat_loaded_state",
                action="continuation turn loads local state, active route, latest heartbeat or manual-resume evidence, lifecycle evidence, and crew ledger",
                heartbeat_loaded_state=True,
                active_node="heartbeat_load_frontier",
            )
            return
        if not state.heartbeat_loaded_frontier:
            yield _step(
                state,
                label="heartbeat_loaded_execution_frontier",
                action="continuation turn loads execution_frontier.json before selecting work",
                heartbeat_loaded_frontier=True,
                active_node="heartbeat_load_packet_ledger",
            )
            return
        if not state.heartbeat_loaded_packet_ledger:
            yield _step(
                state,
                label="heartbeat_loaded_packet_ledger",
                action="continuation turn loads packet_ledger.json before asking PM or dispatching worker work",
                heartbeat_loaded_packet_ledger=True,
                active_node="heartbeat_load_crew_memory",
            )
            return
        if (
            not state.router_daemon_recovered_on_resume
            and not state.terminal_router_daemon_stopped
        ):
            yield _step(
                state,
                label="heartbeat_checked_or_restarted_persistent_router_daemon",
                action="continuation turn checks the persistent Router daemon lock/status, restarts only a dead or stale daemon, and rescans the Controller action ledger before role recovery or PM resume",
                router_daemon_started=True,
                router_daemon_lock_acquired=True,
                router_daemon_tick_seconds=1,
                router_daemon_status_written=True,
                controller_action_ledger_initialized=True,
                controller_action_watch_active=True,
                router_daemon_recovered_on_resume=True,
                terminal_router_daemon_stopped=False,
                active_node="heartbeat_load_crew_memory",
            )
            return
        if not state.heartbeat_loaded_crew_memory:
            yield _step(
                state,
                label="heartbeat_loaded_crew_memory",
                action="continuation turn loads structured role memory packets before restoring or replacing roles",
                heartbeat_loaded_crew_memory=True,
                active_node="heartbeat_rehydrate_crew",
            )
            return
        if not state.heartbeat_host_rehydrate_requested:
            yield _step(
                state,
                label="heartbeat_host_spawn_or_rehydrate_six_roles",
                action="router asks the host to restore or spawn all six live roles before PM resume",
                heartbeat_host_rehydrate_requested=True,
                active_node="heartbeat_rehydrate_crew",
            )
            return
        if not state.heartbeat_restored_crew:
            yield _step(
                state,
                label="heartbeat_restored_six_agent_crew",
                action="continuation turn resumes available role agents or prepares replacements from role memory",
                heartbeat_restored_crew=True,
                replacement_roles_seeded_from_memory=True,
                active_node="heartbeat_rehydrate_crew",
            )
            return
        if not state.heartbeat_rehydrated_crew:
            yield _step(
                state,
                label="heartbeat_rehydrated_six_agent_crew",
                action="continuation turn records full six-role rehydration status before asking the PM",
                heartbeat_rehydrated_crew=True,
                active_node="write_crew_rehydration_report",
            )
            return
        if not state.heartbeat_injected_current_run_memory_into_roles:
            yield _step(
                state,
                label="heartbeat_injected_current_run_memory_into_roles",
                action="host injects each role's current-run memory and PM resume context before PM runway",
                heartbeat_injected_current_run_memory_into_roles=True,
                active_node="write_crew_rehydration_report",
            )
            return
        if not state.crew_rehydration_report_written:
            yield _step(
                state,
                label="crew_rehydration_report_written",
                action="write the six-role rehydration report with restored, replaced, blocked, and memory-seeded role status before any PM resume decision",
                crew_rehydration_report_written=True,
                active_node="heartbeat_ask_project_manager",
            )
            return
        if not state.heartbeat_pm_decision_requested:
            yield _step(
                state,
                label="heartbeat_asked_project_manager",
                action="continuation turn asks the project manager for PM_DECISION from the current frontier and packet ledger",
                heartbeat_pm_decision_requested=True,
                active_node="check_pm_controller_reminder",
            )
            return
        if not state.heartbeat_pm_controller_reminder_checked:
            yield _step(
                state,
                label="heartbeat_pm_controller_reminder_checked",
                action="controller requires PM_DECISION to include controller_reminder before dispatching any packet",
                heartbeat_pm_controller_reminder_checked=True,
                active_node="check_router_direct_dispatch_policy",
            )
            return
        if not state.heartbeat_reviewer_dispatch_policy_checked:
            yield _step(
                state,
                label="heartbeat_reviewer_dispatch_policy_checked",
                action="controller confirms NODE_PACKET dispatch requires router direct-dispatch preflight and ambiguous worker state blocks controller execution",
                heartbeat_reviewer_dispatch_policy_checked=True,
                active_node="await_pm_resume_decision",
            )
            return
        if not state.pm_resume_decision_recorded:
            yield _step(
                state,
                label="pm_resume_completion_runway_recorded",
                action="project manager records a completion-oriented runway from the current gate toward project completion, including hard stops and checkpoint cadence",
                pm_resume_decision_recorded=True,
                pm_completion_runway_recorded=True,
                pm_runway_hard_stops_recorded=True,
                pm_runway_checkpoint_cadence_recorded=True,
                active_node="sync_pm_runway_to_plan",
            )
            return
        if not state.pm_runway_synced_to_plan:
            yield _step(
                state,
                label="pm_runway_synced_to_visible_plan",
                action="controller calls the host native plan tool when available, or records the fallback method, and replaces the visible plan with a downstream PM runway projection",
                pm_runway_synced_to_plan=True,
                plan_sync_method_recorded=True,
                visible_plan_has_runway_depth=True,
                active_node="check_continuation_resume_ready",
            )
            return
        if not state.heartbeat_health_checked:
            yield _step(
                state,
                label="continuation_resume_ready_checked",
                action="check automated heartbeat health when supported, or check manual-resume state/frontier/crew-memory readiness when no real wakeup exists",
                heartbeat_health_checked=True,
                active_node="check_unfinished_current_node",
            )
            return
        if not state.pm_node_decision_recorded:
            yield _step(
                state,
                label="pm_node_work_decision_recorded",
                action="project manager assigns the current node work package before the controller dispatches authorized work",
                pm_node_decision_recorded=True,
                active_node="check_unfinished_current_node",
            )
            return
        if not state.unfinished_current_node_recovery_checked:
            yield _step(
                state,
                label="unfinished_current_node_recovery_checked",
                action="confirm heartbeat should resume the current node or may advance",
                unfinished_current_node_recovery_checked=True,
                active_node="parent_focused_interrogation",
            )
            return
        if not state.parent_focused_interrogation_done:
            yield _step(
                state,
                label="parent_focused_interrogation_completed",
                action="run 20-50 focused grill-me questions for the active parent scope before subtree FlowGuard review",
                parent_focused_interrogation_done=True,
                parent_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                parent_focused_interrogation_scope_id="active-parent",
                active_node="review_parent_subtree",
            )
            return
        if not state.parent_subtree_review_checked:
            yield _step(
                state,
                label="parent_subtree_review_checked",
                action="rerun FlowGuard against the current parent child-subtree before child work",
                parent_subtree_review_checked=True,
                active_node="check_parent_product_function_model",
            )
            return
        if not state.parent_product_function_model_checked:
            yield _step(
                state,
                label="parent_product_function_model_checked",
                action="product FlowGuard officer runs and approves the parent product-function model before entering the active child node",
                parent_product_function_model_checked=True,
                parent_product_function_model_product_officer_approved=True,
                active_node="emit_node_visible_roadmap",
            )
            return
        if not state.node_visible_roadmap_emitted:
            yield _step(
                state,
                label="node_visible_roadmap_emitted",
                action="emit visible node roadmap before defining implementation work",
                node_visible_roadmap_emitted=True,
                active_node="node_focused_interrogation",
            )
            return
        if not state.node_focused_interrogation_done:
            yield _step(
                state,
                label="node_focused_interrogation_completed",
                action="run 20-50 focused grill-me questions for the active leaf node before defining implementation work",
                node_focused_interrogation_done=True,
                node_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                node_focused_interrogation_scope_id="active-leaf-node",
                active_node="check_node_product_function_model",
            )
            return
        if not state.node_self_interrogation_record_written:
            yield _step(
                state,
                label="node_self_interrogation_record_written",
                action="write a durable current-node self-interrogation record before node modeling, acceptance planning, or worker packet dispatch can rely on the grill-me result",
                node_self_interrogation_record_written=True,
                active_node="check_node_product_function_model",
            )
            return
        if not state.node_self_interrogation_findings_dispositioned:
            yield _step(
                state,
                label="node_self_interrogation_findings_dispositioned",
                action="PM binds current-node self-interrogation findings into the node acceptance plan, a later gate, the suggestion ledger, a rejection, or an explicit waiver before packet dispatch",
                node_self_interrogation_findings_dispositioned=True,
                active_node="check_node_product_function_model",
            )
            return
        if not state.node_product_function_model_checked:
            yield _step(
                state,
                label="node_product_function_model_checked",
                action="product FlowGuard officer runs and approves the active leaf's product-function model before defining implementation work",
                node_product_function_model_checked=True,
                node_product_function_model_product_officer_approved=True,
                active_node="current_node_high_standard_recheck",
            )
            return
        if not state.current_node_high_standard_recheck_written:
            yield _step(
                state,
                label="current_node_high_standard_recheck_written",
                action="project manager rechecks the current node against the highest achievable product target, unacceptable-result bar, semantic-fidelity policy, and likely local downgrade risks before writing node acceptance",
                current_node_high_standard_recheck_written=True,
                active_node="current_node_minimum_sufficient_complexity_review",
            )
            return
        if not state.current_node_minimum_sufficient_complexity_review_written:
            yield _step(
                state,
                label="current_node_minimum_sufficient_complexity_review_written",
                action="project manager records why the current node packet, checks, handoffs, and evidence are the minimum sufficient structure for the node proof obligations",
                current_node_minimum_sufficient_complexity_review_written=True,
                active_node="write_node_acceptance_plan",
            )
            return
        if not state.node_acceptance_plan_written:
            yield _step(
                state,
                label="node_acceptance_plan_written",
                action="project manager writes the current node acceptance plan with root mappings, local criteria, concrete experiments, evidence paths, and approver",
                node_acceptance_plan_written=True,
                current_node_skill_improvement_check_done=False,
                checkpoint_written=False,
                active_node="check_current_node_leaf_readiness",
            )
            return
        if not state.active_node_leaf_readiness_gate_passed:
            yield _step(
                state,
                label="active_node_leaf_readiness_gate_passed",
                action="project manager and reviewer confirm a leaf/repair node has a passing readiness gate before worker dispatch",
                active_node_leaf_readiness_gate_passed=True,
                active_node="block_parent_node_direct_dispatch",
            )
            return
        if not state.active_node_parent_dispatch_blocked:
            yield _step(
                state,
                label="active_node_parent_dispatch_blocked",
                action="Router/PM path confirms parent or module nodes cannot receive worker packets and must enter child subtree or parent backward replay",
                active_node_parent_dispatch_blocked=True,
                active_node="map_node_acceptance_risk_experiments",
            )
            return
        if not state.node_acceptance_risk_experiments_mapped:
            if not state.active_child_skill_bindings_written:
                yield _step(
                    state,
                    label="active_child_skill_bindings_written",
                    action="project manager writes current-node active child-skill bindings with source skill paths, node-slice scope, selected standards, and stricter-than-PM precedence before worker dispatch",
                    active_child_skill_bindings_written=True,
                    active_child_skill_binding_scope_limited=True,
                    child_skill_stricter_standard_precedence_bound=True,
                    active_node="map_node_acceptance_risk_experiments",
                )
                return
            yield _step(
                state,
                label="node_acceptance_risk_experiments_mapped",
                action="project manager maps current-node risk hypotheses to experiments and terminal replay scenarios before implementation starts",
                node_acceptance_risk_experiments_mapped=True,
                active_node="pm_review_hold_instruction",
            )
            return
        if not state.worker_packet_child_skill_use_instruction_written:
            yield _step(
                state,
                label="worker_packet_child_skill_binding_projected",
                action="project active child-skill bindings into the current-node worker packet with direct use instructions and allowed source SKILL.md/reference paths",
                worker_packet_child_skill_use_instruction_written=True,
                active_child_skill_source_paths_allowed=True,
                active_node="pm_review_hold_instruction",
            )
            return
        if not state.pm_review_hold_instruction_written:
            yield _step(
                state,
                label="pm_review_hold_instruction_written",
                action="project manager tells the human-like reviewer to wait and not review current-node work until worker output and verification are ready for a PM release order",
                pm_review_hold_instruction_written=True,
                active_node="lightweight_self_check",
            )
            return
        if not state.lightweight_self_check_done:
            yield _step(
                state,
                label="lightweight_self_check_completed",
                action="run 5-10 lightweight self-check questions for the current heartbeat micro-step",
                lightweight_self_check_done=True,
                lightweight_self_check_questions=DEFAULT_LIGHTWEIGHT_SELF_CHECK_QUESTIONS,
                lightweight_self_check_scope_id="active-micro-step",
                active_node="ready_for_chunk",
            )
            return
        if not state.quality_package_done:
            yield _step(
                state,
                label="quality_package_passed_no_raise",
                action="run one quality package for feature thinness, worthwhile raises, child-skill visibility, validation strength, and rough-finish risk; record no scope raise",
                quality_package_done=True,
                quality_candidate_registry_checked=True,
                quality_raise_decision_recorded=True,
                validation_matrix_defined=True,
                active_node="ready_for_chunk",
            )
            yield _step(
                state,
                label="quality_package_small_raise_in_current_node",
                action="record a low-risk high-value improvement inside the current node without changing the route",
                quality_package_done=True,
                quality_candidate_registry_checked=True,
                quality_raise_decision_recorded=True,
                validation_matrix_defined=True,
                active_node="ready_for_chunk",
            )
            if (
                state.completed_chunks == 0
                and state.quality_route_raises < MAX_QUALITY_ROUTE_RAISES
            ):
                yield _step(
                    state,
                    label="quality_package_route_raise_needed",
                    action="classify a medium or large improvement as route mutation, not an unbounded immediate expansion",
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
                    node_focused_interrogation_done=False,
                    node_focused_interrogation_questions=0,
                    node_focused_interrogation_scope_id="",
                    lightweight_self_check_done=False,
                    lightweight_self_check_questions=0,
                    lightweight_self_check_scope_id="",
                    child_node_sidecar_scan_done=False,
                    sidecar_need="unknown",
                    subagent_scope_checked=False,
                    node_visible_roadmap_emitted=False,
                    quality_route_raises=state.quality_route_raises + 1,
                    active_node="run_quality_route_checks",
                    **_reset_execution_scope_gates(),
                )
            return
        if state.high_risk_gate == "none":
            yield _step(
                state,
                label="high_risk_gate_requested",
                action="pause for hard safety gate before risky operation",
                high_risk_gate="pending",
                active_node="await_high_risk_approval",
            )
        if not state.child_node_sidecar_scan_done:
            yield _step(
                state,
                label="child_node_sidecar_scan_no_need",
                action="enter the current child node and find no useful bounded sidecar task",
                child_node_sidecar_scan_done=True,
                sidecar_need="none",
                active_node="ready_for_chunk",
            )
            yield _step(
                state,
                label="child_node_sidecar_scan_need_found_no_pool",
                action="enter the current child node and find a bounded sidecar task with no existing idle subagent",
                child_node_sidecar_scan_done=True,
                sidecar_need="needed",
                subagent_pool_exists=False,
                subagent_idle_available=False,
                active_node="sidecar_scope_check",
            )
            yield _step(
                state,
                label="child_node_sidecar_scan_need_found_existing_idle",
                action="enter the current child node and find a bounded sidecar task plus an existing idle subagent",
                child_node_sidecar_scan_done=True,
                sidecar_need="needed",
                subagent_pool_exists=True,
                subagent_idle_available=True,
                subagent_status="idle",
                active_node="sidecar_scope_check",
            )
            return
        if state.sidecar_need == "needed" and not state.subagent_scope_checked:
            yield _step(
                state,
                label="sidecar_scope_checked",
                action="confirm the sidecar task is bounded, non-blocking, and cannot own the node, route, acceptance, or checkpoint",
                subagent_scope_checked=True,
                active_node="assign_sidecar",
            )
            return
        if (
            state.sidecar_need == "needed"
            and state.subagent_scope_checked
            and state.subagent_status in {"none", "idle"}
        ):
            if state.subagent_pool_exists and state.subagent_idle_available:
                yield _step(
                    state,
                    label="idle_subagent_reused",
                    action="reuse an existing idle subagent for the child-node sidecar task",
                    subagent_status="pending",
                    subagent_idle_available=False,
                    active_node="await_sidecar_report",
                )
            else:
                yield _step(
                    state,
                    label="subagent_spawned_on_demand",
                    action="spawn a subagent only after the current child node has a bounded sidecar task and no suitable idle subagent exists",
                    subagent_pool_exists=True,
                    subagent_status="pending",
                    active_node="await_sidecar_report",
                )
            return
        if state.subagent_status == "pending":
            yield _step(
                state,
                label="sidecar_report_returned",
                action="sidecar subagent returns findings, evidence, changed paths if any, risks, and suggestions",
                subagent_status="returned",
                active_node="merge_sidecar_report",
            )
            return
        if state.subagent_status == "returned":
            yield _step(
                state,
                label="authorized_integration_review_packet_completed",
                action="authorized integration/review packet verifies the sidecar report while PM keeps node ownership",
                sidecar_need="none",
                subagent_status="idle",
                subagent_idle_available=True,
                active_node="ready_for_chunk",
            )
            return
        yield _step(
            state,
            label="chunk_verification_defined",
            action="define chunk-level verification before execution",
            chunk_state="ready",
            verification_defined=True,
            checkpoint_written=False,
            active_node="execute_chunk",
        )
        return

    if state.chunk_state == "ready" and state.verification_defined:
        yield _step(
            state,
            label="chunk_executed",
            action="execute bounded chunk",
            chunk_state="executed",
            role_memory_refreshed_after_work=False,
            active_node="verify_chunk",
        )
        return

    if state.chunk_state == "executed":
        if not state.worker_child_skill_use_evidence_returned:
            yield _step(
                state,
                label="worker_child_skill_use_evidence_returned",
                action="worker returns Child Skill Use Evidence proving the bound child skill source was opened, applied to the current node slice, and any stricter child-skill standard was followed or explicitly waived",
                worker_child_skill_use_evidence_returned=True,
                active_node="verify_chunk",
            )
            return
        yield _step(
            state,
            label="chunk_verification_passed",
            action="real verification passes for chunk before anti-rough-finish review",
            chunk_state="verified",
            verification_defined=False,
            active_node="anti_rough_finish_review",
        )
        yield _step(
            state,
            label="verification_found_model_gap",
            action="real verification exposes model gap",
            issue="model_gap",
            chunk_state="none",
            verification_defined=False,
            checkpoint_written=False,
            active_node="update_model",
        )
        yield _step(
            state,
            label="verification_found_impl_failure",
            action="real verification exposes implementation failure",
            issue="impl_failure",
            chunk_state="none",
            verification_defined=False,
            checkpoint_written=False,
            active_node="recover_implementation",
        )
        return

    if state.chunk_state == "verified":
        if not state.anti_rough_finish_done:
            yield _step(
                state,
                label="anti_rough_finish_passed",
                action="review the verified chunk for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                anti_rough_finish_done=True,
                active_node="mark_worker_output_ready_for_pm_review_release",
            )
            if (
                state.completed_chunks == 0
                and state.quality_reworks < MAX_QUALITY_REWORKS
            ):
                yield _step(
                    state,
                    label="anti_rough_finish_found_rework",
                    action="record bounded rework because the verified chunk is still too thin or weakly evidenced",
                    chunk_state="none",
                    verification_defined=False,
                    checkpoint_written=False,
                    heartbeat_health_checked=False,
                    parent_focused_interrogation_done=False,
                    parent_focused_interrogation_questions=0,
                    parent_focused_interrogation_scope_id="",
                    parent_subtree_review_checked=False,
                    unfinished_current_node_recovery_checked=False,
                    node_focused_interrogation_done=False,
                    node_focused_interrogation_questions=0,
                    node_focused_interrogation_scope_id="",
                    lightweight_self_check_done=False,
                    lightweight_self_check_questions=0,
                    lightweight_self_check_scope_id="",
                    node_visible_roadmap_emitted=False,
                    quality_reworks=state.quality_reworks + 1,
                    active_node="quality_rework",
                    **_reset_execution_scope_gates(),
                )
            return
        if not state.worker_output_ready_for_review:
            yield _step(
                state,
                label="worker_output_ready_for_review",
                action="record that current-node worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                worker_output_ready_for_review=True,
                active_node="pm_review_release_order",
            )
            return
        if not state.pm_review_release_order_written:
            yield _step(
                state,
                label="pm_review_release_order_written",
                action="project manager writes the review release order naming the gate, evidence paths, reviewer scope, and what the reviewer must inspect",
                pm_review_release_order_written=True,
                active_node="pm_release_reviewer_for_current_gate",
            )
            return
        if not state.pm_released_reviewer_for_current_gate:
            yield _step(
                state,
                label="pm_released_reviewer_for_current_gate",
                action="project manager explicitly releases the reviewer to start current-gate review after worker output is ready",
                pm_released_reviewer_for_current_gate=True,
                active_node="review_packet_role_origin",
            )
            return
        if not state.packet_runtime_physical_files_written:
            yield _step(
                state,
                label="packet_runtime_physical_isolation_verified",
                action="packet runtime writes physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                packet_runtime_physical_files_written=True,
                controller_context_body_exclusion_verified=True,
                active_node="review_packet_role_origin",
            )
            return
        if not state.packet_mail_chain_audit_done:
            yield _step(
                state,
                label="controller_mail_relay_chain_audit_done",
                action="human-like reviewer verifies every packet/result envelope has controller relay signatures, recipients opened bodies only after relay checks, private role-to-role mail is absent, and unopened or contaminated mail is routed to PM for restart, repair node, or sender reissue",
                controller_relay_signature_audit_done=True,
                recipient_pre_open_relay_check_done=True,
                packet_mail_chain_audit_done=True,
                unopened_mail_pm_recovery_policy_recorded=True,
                active_node="review_packet_role_origin",
            )
            return
        if not state.packet_envelope_body_audit_done:
            yield _step(
                state,
                label="packet_envelope_body_audit_done",
                action="human-like reviewer checks packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content review",
                packet_envelope_body_audit_done=True,
                packet_envelope_to_role_checked=True,
                packet_body_hash_verified=True,
                result_envelope_checked=True,
                result_body_hash_verified=True,
                completed_agent_id_role_verified=True,
                controller_body_boundary_verified=True,
                wrong_role_relabel_forbidden_verified=True,
                active_node="review_packet_role_origin",
            )
            return
        if not state.packet_role_origin_audit_done:
            yield _step(
                state,
                label="packet_role_origin_audit_done",
                action="human-like reviewer verifies every packet's PM author, router direct-dispatch evidence, assigned worker, and actual result author after envelope/body integrity passes",
                packet_role_origin_audit_done=True,
                packet_result_author_verified=True,
                packet_result_author_matches_assignment=True,
                active_node="load_human_inspection_context",
            )
            return
        if not state.blocker_repair_policy_snapshot_written:
            yield _step(
                state,
                label="blocker_repair_policy_snapshot_written",
                action="write the run-visible blocker repair policy table before any router control blocker is materialized",
                blocker_repair_policy_snapshot_written=True,
                active_node="exercise_control_blocker_policy",
            )
            return
        if not state.router_hard_rejection_seen:
            yield _step(
                state,
                label="control_blocker_policy_row_attached",
                action="router materializes a mechanical control blocker with policy row, first handler, retry budget, and return policy metadata",
                router_hard_rejection_seen=True,
                control_blocker_artifact_written=True,
                blocker_policy_row_attached=True,
                control_blocker_handling_lane="control_plane_reissue",
                control_blocker_first_handler="responsible_role",
                control_blocker_direct_retry_budget=2,
                control_blocker_direct_retry_attempts=0,
                active_node="deliver_control_blocker_first_handler",
            )
            return
        if (
            state.control_blocker_handling_lane == "control_plane_reissue"
            and not state.control_blocker_delivered_to_responsible_role
        ):
            yield _step(
                state,
                label="control_blocker_first_handler_delivered",
                action="controller delivers the first mechanical blocker to the responsible role without opening sealed bodies or making a PM decision",
                control_blocker_delivered_to_responsible_role=True,
                active_node="retry_control_plane_reissue",
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
                active_node="pm_control_blocker_recovery_decision",
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
                active_node="pm_control_blocker_return_gate",
            )
            return
        if state.pm_blocker_recovery_option_recorded and not state.pm_blocker_return_gate_recorded:
            yield _step(
                state,
                label="pm_blocker_return_gate_recorded",
                action="PM names the gate or terminal stop that follows the blocker recovery decision",
                pm_blocker_return_gate_recorded=True,
                active_node="load_human_inspection_context",
            )
            return
        if not state.reviewer_child_skill_use_evidence_checked:
            yield _step(
                state,
                label="reviewer_child_skill_use_evidence_checked",
                action="human-like reviewer checks Child Skill Use Evidence, source-skill opening, current-node slice fit, and stricter child-skill standard precedence before content inspection",
                reviewer_child_skill_use_evidence_checked=True,
                active_node="load_human_inspection_context",
            )
            return
        if not state.node_human_review_context_loaded:
            yield _step(
                state,
                label="node_human_inspection_context_loaded",
                action="load requirement, product model, evidence, screenshots or logs, and parent contract for human-like node inspection",
                node_human_review_context_loaded=True,
                active_node="write_node_human_neutral_observation",
            )
            return
        if not state.node_human_neutral_observation_written:
            yield _step(
                state,
                label="node_human_neutral_observation_written",
                action="write a neutral observation of what the node artifact, output, or UI screenshot actually appears to be",
                node_human_neutral_observation_written=True,
                active_node="run_human_inspection_experiments",
            )
            return
        if not state.node_human_manual_experiments_run:
            yield _step(
                state,
                label="node_human_manual_experiments_run",
                action="operate or inspect the product like a human reviewer before accepting node evidence",
                node_human_manual_experiments_run=True,
                active_node="human_inspection_decision",
            )
            return
        if not state.node_reviewer_independent_probe_done:
            yield _step(
                state,
                label="node_reviewer_independent_probe_done",
                action="human-like reviewer independently attacks node evidence with direct probes, concrete artifact or state references, missing-path hypotheses, and report-only failure checks before approval",
                node_reviewer_independent_probe_done=True,
                active_node="human_inspection_decision",
            )
            return
        if not state.node_human_inspection_passed:
            if (
                state.completed_chunks == 0
                and state.human_inspection_repairs < 1
            ):
                yield _step(
                    state,
                    label="human_inspection_found_blocking_issue",
                    action="human-like reviewer rejects the node evidence, writes a blocking defect event, and requires a route-mutating repair",
                    issue="inspection_failure",
                    defect_event_logged_for_blocker=True,
                    blocking_defect_open=True,
                    pm_defect_triage_done=False,
                    blocking_defect_fixed_pending_recheck=False,
                    defect_same_class_recheck_done=False,
                    defect_ledger_zero_blocking=False,
                    chunk_state="none",
                    verification_defined=False,
                    checkpoint_written=False,
                    active_node="grill_human_inspection_issue",
                )
                return
            yield _step(
                state,
                label="node_human_inspection_passed",
                action="human-like reviewer accepts the repaired node evidence and product behavior, closing any fixed-pending same-class blocker",
                node_human_inspection_passed=True,
                node_human_review_reviewer_approved=True,
                blocking_defect_fixed_pending_recheck=False,
                defect_same_class_recheck_done=(
                    state.blocking_defect_fixed_pending_recheck
                    or state.defect_same_class_recheck_done
                ),
                defect_ledger_zero_blocking=True,
                active_node="write_checkpoint",
            )
            return
        if not state.current_node_skill_improvement_check_done:
            yield _step(
                state,
                label="skill_improvement_observation_check_no_issue",
                action="PM asks the roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found before checkpoint path",
                current_node_skill_improvement_check_done=True,
                active_node="write_checkpoint",
            )
            yield _step(
                state,
                label="skill_improvement_observation_logged",
                action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance before checkpoint path",
                current_node_skill_improvement_check_done=True,
                flowpilot_improvement_live_report_updated=True,
                active_node="write_checkpoint",
            )
            return
        yield _step(
            state,
            label="chunk_verified",
            action="accept the anti-rough-finish-reviewed chunk for checkpoint",
            completed_chunks=state.completed_chunks + 1,
            node_human_inspections_passed=state.node_human_inspections_passed + 1,
            chunk_state="checkpoint_pending",
            active_node="write_checkpoint",
        )
        return
