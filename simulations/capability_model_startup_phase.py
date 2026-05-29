"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "CREW_SIZE",
    "FunctionResult",
    "Iterable",
    "MIN_FULL_GRILLME_QUESTIONS_PER_LAYER",
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
            label="autopilot_started",
            action="start capability router",
            status="running",
            flowpilot_enabled=True,
            run_scoped_startup_bootstrap_created=True,
        )
        return

    if not state.startup_intake_ui_completed:
        yield _step(
            state,
            label="startup_intake_ui_completed",
            action="open the native startup intake UI for background-agent, continuation, and display-surface options",
            startup_intake_ui_completed=True,
        )
        return

    if not state.startup_intake_result_recorded:
        yield _step(
            state,
            label="startup_intake_result_recorded",
            action="record the confirmed native startup intake result without accepting chat-body substitutes",
            startup_intake_result_recorded=True,
        )
        return

    if not state.startup_background_agent_option_recorded:
        yield _step(
            state,
            label="startup_background_agent_option_recorded",
            action="record the startup intake background-agent option for live background agents versus single-agent continuity",
            startup_background_agent_option_recorded=True,
        )
        return

    if not state.startup_continuation_option_recorded:
        yield _step(
            state,
            label="startup_continuation_option_recorded",
            action="record the startup intake continuation option for heartbeat/automation versus manual resume",
            startup_continuation_option_recorded=True,
        )
        return

    if not state.startup_display_surface_option_recorded:
        yield _step(
            state,
            label="startup_display_surface_option_recorded",
            action="record the startup intake display-surface option for Cockpit UI versus chat route signs",
            startup_display_surface_option_recorded=True,
            startup_answer_values_valid=True,
            startup_answer_provenance="explicit_user_reply",
        )
        return

    if not state.run_directory_created:
        yield _step(
            state,
            label="run_directory_created",
            action="create a fresh .flowpilot/runs/<run-id>/ directory for this formal FlowPilot invocation",
            run_directory_created=True,
        )
        return

    if not state.current_pointer_written:
        yield _step(
            state,
            label="current_pointer_written",
            action="write .flowpilot/current.json to point at the current run directory",
            current_pointer_written=True,
        )
        return

    if not state.run_index_updated:
        yield _step(
            state,
            label="run_index_updated",
            action="update .flowpilot/index.json with the new run identity and creation metadata",
            run_index_updated=True,
        )
        return

    if not state.startup_display_entry_action_done:
        yield _step(
            state,
            label="startup_display_entry_action_done",
            action="open Cockpit UI immediately when requested, or display the chat route sign when the user chose chat",
            startup_display_entry_action_done=True,
        )
        return

    if not state.defect_ledger_initialized:
        yield _step(
            state,
            label="defect_ledger_initialized",
            action="create the run-level defect ledger before capability reviews, repairs, pauses, or completion can record findings",
            defect_ledger_initialized=True,
        )
        return

    if not state.evidence_ledger_initialized:
        yield _step(
            state,
            label="evidence_ledger_initialized",
            action="create the run-level evidence credibility ledger before capability evidence can close gates",
            evidence_ledger_initialized=True,
        )
        return

    if not state.generated_resource_ledger_initialized:
        yield _step(
            state,
            label="generated_resource_ledger_initialized",
            action="create the run-level generated-resource ledger before concepts, UI assets, screenshots, route diagrams, or model reports are produced or discarded",
            generated_resource_ledger_initialized=True,
        )
        return

    if not state.activity_stream_initialized:
        yield _step(
            state,
            label="activity_stream_initialized",
            action="create the run-level activity stream so PM, reviewer, officer, worker, route, heartbeat, and user-visible progress events can be displayed without manual refresh",
            activity_stream_initialized=True,
            activity_stream_latest_event_written=True,
        )
        return

    if not state.flowpilot_improvement_live_report_initialized:
        yield _step(
            state,
            label="flowpilot_improvement_live_report_initialized",
            action="initialize the live FlowPilot improvement report before capability work can expose skill or process defects",
            flowpilot_improvement_live_report_initialized=True,
        )
        return

    if state.prior_work_mode == "unknown":
        yield _step(
            state,
            label="new_task_no_prior_import",
            action="record that this capability run starts without importing prior FlowPilot control state",
            prior_work_mode="new",
        )
        yield _step(
            state,
            label="continue_previous_work_selected",
            action="record that this capability run continues prior work but imports prior outputs as read-only evidence",
            prior_work_mode="continue",
        )
        return

    if state.prior_work_mode == "continue" and not state.prior_work_import_packet_written:
        yield _step(
            state,
            label="prior_work_import_packet_written",
            action="write a prior-work import packet under the new run without making old state current",
            prior_work_import_packet_written=True,
        )
        return

    if not state.control_state_written_under_run_root:
        yield _step(
            state,
            label="control_state_written_under_run_root",
            action="write state, frontier, capability evidence, crew, and review control artifacts only under the current run directory",
            control_state_written_under_run_root=True,
        )
        return

    if not state.prior_control_state_quarantined:
        yield _step(
            state,
            label="prior_control_state_quarantined",
            action="verify prior top-level control state is absent, retired-only, or quarantined before capability work continues",
            prior_control_state_quarantined=True,
        )
        return

    if not state.preflow_visible_plan_cleared:
        yield _step(
            state,
            label="preflow_visible_plan_cleared",
            action="controller replaces any ordinary pre-FlowPilot Codex plan with the waiting-for-PM display projection before capability route work",
            preflow_visible_plan_cleared=True,
        )
        return

    if not state.showcase_floor_committed:
        yield _step(
            state,
            label="showcase_floor_committed",
            action="commit capability routing to showcase-grade long-horizon scope",
            showcase_floor_committed=True,
        )
        return

    if not state.self_interrogation_done:
        yield _step(
            state,
            label="visible_self_interrogation_completed",
            action="derive dynamic layers, expose at least 100 grill-me questions per active layer, seed the improvement candidate pool, and seed initial validation direction",
            self_interrogation_done=True,
            self_interrogation_evidence=True,
            visible_self_interrogation_done=True,
            self_interrogation_questions=(
                MODEL_DYNAMIC_LAYER_COUNT
                * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
            ),
            self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
            self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
            self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
            quality_candidate_pool_seeded=True,
            validation_strategy_seeded=True,
        )
        return

    if not state.self_interrogation_record_written:
        yield _step(
            state,
            label="self_interrogation_record_written",
            action="write a durable startup self-interrogation record with findings, source event, scope, and PM disposition slots before capability routing can rely on it",
            self_interrogation_record_written=True,
        )
        return

    if not state.crew_policy_written:
        yield _step(
            state,
            label="six_agent_crew_policy_written",
            action="write fixed six-agent crew policy for capability routing",
            crew_policy_written=True,
        )
        return

    if state.crew_count == 0:
        yield _step(
            state,
            label="project_manager_spawned_fresh_for_task",
            action="spawn a fresh project manager for the new formal FlowPilot task before capability routing",
            crew_count=1,
            project_manager_ready=True,
        )
        return

    if state.crew_count == 1:
        yield _step(
            state,
            label="human_like_reviewer_spawned_fresh_for_task",
            action="spawn a fresh reviewer for the new formal FlowPilot task before capability routing",
            crew_count=2,
            reviewer_ready=True,
        )
        return

    if state.crew_count == 2:
        yield _step(
            state,
            label="process_flowguard_officer_spawned_fresh_for_task",
            action="spawn a fresh process FlowGuard officer for the new formal FlowPilot task before capability routing",
            crew_count=3,
            process_flowguard_officer_ready=True,
        )
        return

    if state.crew_count == 3:
        yield _step(
            state,
            label="product_flowguard_officer_spawned_fresh_for_task",
            action="spawn a fresh product FlowGuard officer for the new formal FlowPilot task before capability routing",
            crew_count=4,
            product_flowguard_officer_ready=True,
        )
        return

    if state.crew_count == 4:
        yield _step(
            state,
            label="worker_a_spawned_fresh_for_task",
            action="spawn a fresh worker A for bounded capability sidecar work in the new formal FlowPilot task",
            crew_count=5,
            worker_a_ready=True,
        )
        return

    if state.crew_count == 5:
        yield _step(
            state,
            label="worker_b_spawned_fresh_for_task",
            action="spawn a fresh worker B for bounded capability sidecar work in the new formal FlowPilot task",
            crew_count=CREW_SIZE,
            worker_b_ready=True,
        )
        return

    if not state.crew_ledger_written:
        yield _step(
            state,
            label="crew_ledger_written",
            action="persist crew names, role authority, agent ids, status, and recovery rules before capability work",
            crew_ledger_written=True,
        )
        return

    if not state.role_identity_protocol_recorded:
        yield _step(
            state,
            label="role_identity_protocol_recorded",
            action="record distinct role_key, display_name, and diagnostic-only agent_id fields before capability work",
            role_identity_protocol_recorded=True,
        )
        return

    if not state.pm_flowguard_delegation_policy_recorded:
        yield _step(
            state,
            label="pm_flowguard_delegation_policy_recorded",
            action="record that the project manager creates structured FlowGuard modeling requests for uncertain capability, process, product, object/reference-system, migration-equivalence, experiment-derived behavior, or validation decisions and assigns them to the process or product FlowGuard officer",
            pm_flowguard_delegation_policy_recorded=True,
        )
        return

    if not state.officer_owned_async_modeling_policy_recorded:
        yield _step(
            state,
            label="officer_owned_async_modeling_policy_recorded",
            action="record that capability FlowGuard model gates dispatch to officer-owned run directories while the controller may relay only non-dependent coordination",
            officer_owned_async_modeling_policy_recorded=True,
        )
        return

    if not state.officer_model_report_provenance_policy_recorded:
        yield _step(
            state,
            label="officer_model_report_provenance_policy_recorded",
            action="require capability officer model reports to prove model author, runner, interpreter, commands, input snapshots, state counts, counterexample inspection, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, blindspots, and decision",
            officer_model_report_provenance_policy_recorded=True,
        )
        return

    if not state.controller_coordination_boundary_recorded:
        yield _step(
            state,
            label="controller_coordination_boundary_recorded",
            action="record that controller coordination during capability officer modeling cannot satisfy route checks, implementation, checkpoint, completion, or protected model gates",
            controller_coordination_boundary_recorded=True,
        )
        return

    if not state.independent_approval_protocol_recorded:
        yield _step(
            state,
            label="independent_approval_protocol_recorded",
            action="record that every PM, reviewer, and FlowGuard officer approval requires independent adversarial validation evidence and cannot be completion-report-only",
            independent_approval_protocol_recorded=True,
        )
        return

    if not state.crew_memory_policy_written:
        yield _step(
            state,
            label="crew_memory_packets_written",
            action="write compact role memory packets for all six capability-routing roles before PM ratification",
            crew_memory_policy_written=True,
            crew_memory_packets_written=CREW_SIZE,
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
        )
        return

    if not state.controller_core_loaded:
        yield _step(
            state,
            label="controller_core_loaded_before_startup_obligations",
            action="load Controller core after the Router daemon and Controller action ledger are ready, before Controller-ledger startup obligations",
            controller_core_loaded=True,
        )
        return

    if not state.continuation_probe_done:
        yield _step(
            state,
            label="host_continuation_capability_supported",
            action="after Controller core loads, record host-kind continuation evidence and confirm real heartbeat setup is supported before startup review or capability work",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            host_continuation_supported=True,
        )
        yield _step(
            state,
            label="host_continuation_capability_unsupported_manual_resume",
            action="after Controller core loads, record manual-resume mode when host automation is unavailable or not requested",
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
            action="create one-minute route heartbeat as a stable launcher bound to the current run before startup review or capability work",
            heartbeat_schedule_created=True,
            route_heartbeat_interval_minutes=1,
            stable_heartbeat_launcher_recorded=True,
            heartbeat_bound_to_current_run=True,
            heartbeat_same_name_only_checked=False,
        )
        return

    if not state.self_interrogation_pm_ratified:
        yield _step(
            state,
            label="self_interrogation_pm_ratified",
            action="project manager ratifies capability startup self-interrogation scope, risk layers, question count, decision set, and PM disposition of durable findings",
            self_interrogation_pm_ratified=True,
            self_interrogation_findings_dispositioned=True,
        )
        return
