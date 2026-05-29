"""Hazard states for the FlowPilot cross-plane friction model."""

from __future__ import annotations

from dataclasses import replace

from flowpilot_cross_plane_friction_model_state import State


def _safe_base(**changes: object) -> State:
    return replace(
        State(
            status="complete",
            step=10,
            controller_boundary_preserved=True,
            material_scan_packets_observed=True,
            terminal_closure_observed=True,
            completed_nodes_observed=True,
            route_snapshot_visible=True,
            cockpit_projection_visible=True,
            reviewer_block_events_observed=True,
            role_event_artifacts_scanned=True,
            gate_outcome_contracts_observed=True,
            node_completion_observed=True,
            cockpit_source_present_in_tree=True,
            standard_six_roles_requested=True,
            active_task_policy_observed=True,
            minimal_repair_strategy_selected=True,
        ),
        **changes,
    )


def repair_solution_state() -> State:
    return _safe_base()


def hazard_states() -> dict[str, State]:
    return {
        "controller_reads_sealed_body_during_audit": _safe_base(
            sealed_body_files_opened_by_controller=True,
        ),
        "material_dispatch_output_contract_role_drift": _safe_base(
            material_output_contract_role_scoped=False,
        ),
        "material_dispatch_write_target_missing": _safe_base(
            material_dispatch_write_target_explicit=False,
        ),
        "retired_material_packets_left_unrejected": _safe_base(
            retired_material_packets_rejected=False,
        ),
        "terminal_closure_missing_run_lifecycle": _safe_base(
            run_lifecycle_record_written=False,
        ),
        "terminal_authority_mismatch": _safe_base(
            router_frontier_lifecycle_terminal_consistent=False,
        ),
        "terminal_control_blocker_not_cleared": _safe_base(
            terminal_control_blocker_cleared=False,
        ),
        "terminal_heartbeat_still_active": _safe_base(
            heartbeat_inactive_after_terminal=False,
        ),
        "route_state_snapshot_status_mismatch": _safe_base(
            route_snapshot_status_derived_from_frontier=False,
        ),
        "route_state_snapshot_completed_checklists_pending": _safe_base(
            route_snapshot_checklists_complete_for_completed_nodes=False,
        ),
        "selected_state_conflated_with_completed_state": _safe_base(
            selected_status_separate_from_completion=False,
        ),
        "cockpit_status_mismatch": _safe_base(
            cockpit_status_derived_from_frontier=False,
        ),
        "cockpit_completed_checklists_pending": _safe_base(
            cockpit_checklists_complete_for_completed_nodes=False,
        ),
        "cockpit_closed_run_exposed_as_active_tab": _safe_base(
            cockpit_closed_runs_hidden_from_active_tabs=False,
        ),
        "reviewer_block_event_taxonomy_gap": _safe_base(
            reviewer_block_events_registered=False,
        ),
        "role_output_event_artifact_scan_missing": _safe_base(
            role_event_artifacts_scanned=False,
        ),
        "reviewer_officer_gate_outcome_pass_only": _safe_base(
            gate_outcome_contracts_complete=False,
        ),
        "node_completion_idempotency_global_only": _safe_base(
            node_completion_idempotency_scoped_to_active_node=False,
        ),
        "install_audit_layout_policy_conflict": _safe_base(
            install_audit_policy_accepts_first_class_cockpit=False,
        ),
        "installed_skill_source_drift": _safe_base(
            installed_skill_matches_repository_source=False,
        ),
        "six_role_liveness_unproven": _safe_base(
            role_liveness_ready_or_blocked=False,
        ),
        "active_history_visible_by_default": _safe_base(
            history_default_hidden=False,
        ),
        "current_pointer_used_as_daemon_authority": _safe_base(
            current_pointer_is_ui_focus_only=False,
        ),
        "active_task_set_missing_explicit_authority": _safe_base(
            active_task_set_has_explicit_authority=False,
        ),
    }


__all__ = ["hazard_states", "repair_solution_state"]
