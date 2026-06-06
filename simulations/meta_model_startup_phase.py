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
    "MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER",
    "MODEL_DYNAMIC_LAYER_COUNT",
    "REQUIRED_RISK_FAMILY_MASK",
    "State",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_startup_phase"]


def apply_startup_phase(self, state: State) -> Iterable[FunctionResult]:
    if state.status == "new":
        yield _step(
            state,
            label="flowpilot_runtime_started",
            action="start the FlowPilot control loop",
            status="running",
            flowpilot_enabled=True,
            run_scoped_startup_bootstrap_created=True,
            foreground_control_loop_active=True,
            active_node="open_startup_intake_ui",
        )
        return

    if not state.startup_intake_ui_completed:
        yield _step(
            state,
            label="startup_intake_ui_completed",
            action="open the native startup intake UI for the work request and background-collaboration permission",
            startup_intake_ui_completed=True,
            active_node="await_startup_intake_result",
        )
        return

    if not state.startup_intake_result_recorded:
        yield _step(
            state,
            label="startup_intake_result_recorded",
            action="record the confirmed native startup intake result without accepting chat-body substitutes",
            startup_intake_result_recorded=True,
            active_node="record_startup_background_collaboration_ack",
        )
        return

    if not state.startup_background_collaboration_ack_recorded:
        yield _step(
            state,
            label="startup_background_collaboration_ack_recorded",
            action="record explicit user acknowledgement that FlowPilot must use host-supported addressable background or parallel agents",
            startup_background_collaboration_ack_recorded=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
            active_node="create_run_directory",
        )
        return

    if not state.run_directory_created:
        yield _step(
            state,
            label="run_directory_created",
            action="create a fresh .flowpilot/runs/<run-id>/ directory for this formal FlowPilot invocation",
            run_directory_created=True,
            active_node="write_current_pointer",
        )
        return

    if not state.current_pointer_written:
        yield _step(
            state,
            label="current_pointer_written",
            action="write .flowpilot/current.json to point at the current run directory",
            current_pointer_written=True,
            active_node="update_run_index",
        )
        return

    if not state.run_index_updated:
        yield _step(
            state,
            label="run_index_updated",
            action="update .flowpilot/index.json with the new run identity and creation metadata",
            run_index_updated=True,
            active_node="initialize_defect_ledger",
        )
        return

    if not state.defect_ledger_initialized:
        yield _step(
            state,
            label="defect_ledger_initialized",
            action="create the run-level defect ledger and event log before any review, repair, pause, or completion gate can record findings",
            defect_ledger_initialized=True,
            active_node="initialize_evidence_ledger",
        )
        return

    if not state.evidence_ledger_initialized:
        yield _step(
            state,
            label="evidence_ledger_initialized",
            action="create the run-level evidence credibility ledger before screenshots, fixture reports, generated assets, or model outputs can close gates",
            evidence_ledger_initialized=True,
            active_node="initialize_generated_resource_ledger",
        )
        return

    if not state.generated_resource_ledger_initialized:
        yield _step(
            state,
            label="generated_resource_ledger_initialized",
            action="create the run-level generated-resource ledger before imagegen concepts, visual assets, screenshots, diagrams, or model reports are produced or discarded",
            generated_resource_ledger_initialized=True,
            active_node="initialize_activity_stream",
        )
        return

    if not state.activity_stream_initialized:
        yield _step(
            state,
            label="activity_stream_initialized",
            action="create the run-level activity stream so PM, reviewer, FlowGuard operator, worker, route, manual resume binding, and user-visible progress events can be displayed without manual refresh",
            activity_stream_initialized=True,
            activity_stream_latest_event_written=True,
            active_node="initialize_flowpilot_improvement_report",
        )
        return

    if not state.flowpilot_improvement_live_report_initialized:
        yield _step(
            state,
            label="flowpilot_improvement_live_report_initialized",
            action="initialize the live FlowPilot improvement report so skill or process defects are captured even if the run pauses before terminal closure",
            flowpilot_improvement_live_report_initialized=True,
            active_node="resolve_prior_work_boundary",
        )
        return

    if state.prior_work_mode == "unknown":
        yield _step(
            state,
            label="new_task_no_prior_import",
            action="record that this run starts without importing prior FlowPilot control state",
            prior_work_mode="new",
            active_node="write_run_scoped_control_state",
        )
        yield _step(
            state,
            label="continue_previous_work_selected",
            action="record that this run continues prior work but must import prior outputs as read-only evidence",
            prior_work_mode="continue",
            active_node="write_prior_work_import_packet",
        )
        return

    if state.prior_work_mode == "continue" and not state.prior_work_import_packet_written:
        yield _step(
            state,
            label="prior_work_import_packet_written",
            action="write a prior-work import packet under the new run without making old state current",
            prior_work_import_packet_written=True,
            active_node="write_run_scoped_control_state",
        )
        return

    if not state.control_state_written_under_run_root:
        yield _step(
            state,
            label="control_state_written_under_run_root",
            action="write state, frontier, route, runtime roles, and review control artifacts only under the current run directory",
            control_state_written_under_run_root=True,
            active_node="quarantine_prior_top_level_control_state",
        )
        return

    if not state.prior_control_state_quarantined:
        yield _step(
            state,
            label="prior_control_state_quarantined",
            action="verify prior top-level control state is absent, unsupported-only, or quarantined before current work continues",
            prior_control_state_quarantined=True,
            active_node="clear_preflow_visible_plan",
        )
        return

    if not state.preflow_visible_plan_cleared:
        yield _step(
            state,
            label="preflow_visible_plan_cleared",
            action="controller replaces any ordinary pre-FlowPilot Codex plan with the waiting-for-PM display projection before PM route work",
            preflow_visible_plan_cleared=True,
            active_node="resolve_startup_display_surface",
        )
        return

    if not state.startup_display_entry_action_done:
        yield _step(
            state,
            label="startup_display_entry_action_done",
            action="display the chat route sign after startup state is ready",
            startup_display_entry_action_done=True,
            active_node="freeze_contract",
        )
        return

    if not state.showcase_floor_committed:
        yield _step(
            state,
            label="showcase_floor_committed",
            action="commit to showcase-grade long-horizon FlowPilot scope",
            showcase_floor_committed=True,
            active_node="visible_self_interrogation",
        )
        return

    if not state.visible_self_interrogation_done:
        yield _step(
            state,
            label="visible_self_interrogation_completed",
            action="derive dynamic layers, expose at least 100 self-interrogation questions per active layer, seed the improvement candidate pool, and seed initial validation direction before contract freeze",
            visible_self_interrogation_done=True,
            startup_self_interrogation_questions=(
                MODEL_DYNAMIC_LAYER_COUNT
                * MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
            ),
            startup_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
            startup_self_interrogation_questions_per_layer=MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER,
            startup_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
            quality_candidate_pool_seeded=True,
            validation_strategy_seeded=True,
            active_node="establish_required_role_binding_coverage",
        )
        return

    if not state.startup_self_interrogation_record_written:
        yield _step(
            state,
            label="startup_self_interrogation_record_written",
            action="write a durable startup self-interrogation record with findings, source event, scope, and PM disposition slots before later route gates can use it",
            startup_self_interrogation_record_written=True,
            active_node="establish_required_role_binding_coverage",
        )
        return

    if not state.role_binding_policy_written:
        yield _step(
            state,
            label="current_background_collaboration_policy_written",
            action="write the current background or parallel agent authority policy without prewarming a fixed role roster",
            role_binding_policy_written=True,
            active_node="write_role_binding_ledger",
        )
        return

    if not state.role_binding_ledger_written:
        yield _step(
            state,
            label="current_background_collaboration_ledger_written",
            action="persist current task background-collaboration authority, agent-id freshness rules, and recovery rules before route work",
            role_binding_ledger_written=True,
            active_node="record_role_identity_protocol",
        )
        return

    if not state.role_identity_protocol_recorded:
        yield _step(
            state,
            label="role_identity_protocol_recorded",
            action="record distinct role_key, display_name, and diagnostic-only agent_id fields before role-binding memory is authoritative",
            role_identity_protocol_recorded=True,
            active_node="record_pm_flowguard_delegation_policy",
        )
        return

    if not state.pm_flowguard_delegation_policy_recorded:
        yield _step(
            state,
            label="pm_flowguard_delegation_policy_recorded",
            action="record that the project manager creates structured FlowGuard modeling requests for uncertain process, product, reference-system, migration-equivalence, experiment-derived behavior, or validation decisions and assigns them to the process or product-scope FlowGuard operator",
            pm_flowguard_delegation_policy_recorded=True,
            active_node="record_flowguard_operator_owned_async_modeling_policy",
        )
        return

    if not state.flowguard_operator_owned_async_modeling_policy_recorded:
        yield _step(
            state,
            label="flowguard_operator_owned_async_modeling_policy_recorded",
            action="record that FlowGuard model gates dispatch to FlowGuard operator-owned run directories while the controller may relay only non-dependent coordination",
            flowguard_operator_owned_async_modeling_policy_recorded=True,
            active_node="record_flowguard_operator_model_report_provenance_policy",
        )
        return

    if not state.flowguard_operator_model_report_provenance_policy_recorded:
        yield _step(
            state,
            label="flowguard_operator_model_report_provenance_policy_recorded",
            action="require FlowGuard operator model reports to prove model author, runner, interpreter, commands, input snapshots, state counts, counterexample inspection, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, blindspots, and decision",
            flowguard_operator_model_report_provenance_policy_recorded=True,
            active_node="record_controller_coordination_boundary",
        )
        return

    if not state.controller_coordination_boundary_recorded:
        yield _step(
            state,
            label="controller_coordination_boundary_recorded",
            action="record that controller coordination during FlowGuard operator modeling cannot satisfy route freeze, implementation, checkpoint, completion, or protected model gates",
            controller_coordination_boundary_recorded=True,
            active_node="record_independent_approval_protocol",
        )
        return

    if not state.independent_approval_protocol_recorded:
        yield _step(
            state,
            label="independent_approval_protocol_recorded",
            action="record that every PM, reviewer, and FlowGuard operator approval requires independent adversarial validation evidence and cannot be completion-report-only",
            independent_approval_protocol_recorded=True,
            active_node="write_role_binding_memory_packets",
        )
        return

    if not state.role_binding_memory_policy_written:
        yield _step(
            state,
            label="role_binding_memory_packets_written",
            action="write the compact current background-collaboration memory policy before route work",
            role_binding_memory_policy_written=True,
            role_binding_memory_packets_written=1,
            active_node="bootstrap_continuation",
        )
        return

    if not state.router_daemon_started and not state.terminal_router_daemon_stopped:
        yield _step(
            state,
            label="persistent_router_daemon_started_before_controller_core",
            action="start the persistent Router daemon with one run-scoped lock, one-second ticks, a status file, and an initialized Controller action ledger before loading Controller core",
            router_daemon_started=True,
            router_daemon_lock_acquired=True,
            router_daemon_tick_seconds=1,
            router_daemon_status_written=True,
            controller_action_ledger_initialized=True,
            controller_action_watch_active=True,
            terminal_router_daemon_stopped=False,
            active_node="load_controller_core",
        )
        return

    if not state.controller_core_loaded:
        yield _step(
            state,
            label="controller_core_loaded_before_startup_obligations",
            action="load Controller core after the Router daemon and Controller action ledger are ready, before Controller-ledger startup obligations",
            controller_core_loaded=True,
            active_node="emit_startup_banner",
        )
        return

    if not state.startup_banner_emitted:
        yield _step(
            state,
            label="startup_banner_emitted_after_controller_core",
            action="emit the FlowPilot startup banner in the user dialog after Controller core is loaded",
            startup_banner_emitted=True,
            startup_banner_user_dialog_confirmed=True,
            active_node="record_manual_resume_binding_boundary",
        )
        return

    if not state.continuation_probe_done:
        yield _step(
            state,
            label="manual_resume_binding_capability_recorded",
            action="after Controller core loads, record host-kind continuation evidence and confirm real manual resume binding setup is supported before startup review or route work",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            manual_resume_binding_supported=True,
            active_node="configure_manual_resume_binding",
        )
        yield _step(
            state,
            label="manual_resume_binding_unavailable_manual_resume_boundary",
            action="after Controller core loads, record manual-resume mode when host automation is unavailable or not requested",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            manual_resume_binding_supported=False,
            manual_resume_boundary_recorded=True,
            active_node="pm_ratify_startup_self_interrogation",
        )
        return

    if state.manual_resume_binding_supported and not state.manual_resume_binding_configured:
        yield _step(
            state,
            label="manual_resume_binding_configured",
            action="create one-second manual resume binding as a stable launcher bound to the current run before startup review or route work",
            manual_resume_binding_configured=True,
            manual_resume_binding_interval_seconds=1,
            stable_manual_resume_launcher_recorded=True,
            manual_resume_binding_bound_to_current_run=True,
            manual_resume_binding_name_only_checked=False,
            active_node="pm_ratify_startup_self_interrogation",
        )
        return
