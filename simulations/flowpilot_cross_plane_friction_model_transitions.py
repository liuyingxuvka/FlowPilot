"""Transition rules for the FlowPilot cross-plane friction model."""

from __future__ import annotations

from typing import Iterable

from flowguard import FunctionResult

from flowpilot_cross_plane_friction_model_state import Action, State, Tick, Transition, _inc


class CrossPlaneReconciliationStep:
    """One FlowPilot cross-plane reconciliation transition.

    Input x State -> Set(Output x State)
    reads: router_state, execution_frontier, packet ledger/envelopes,
      terminal closure suite, run lifecycle record, route_state_snapshot,
      Cockpit adapter output, external-event taxonomy, install sync policy
    writes: abstract proof facts only; this model never mutates production
      runtime files
    idempotency: reconciliation is keyed by run_id, route_version, active node,
      and packet/result envelope identity rather than a single global flag
    """

    name = "CrossPlaneReconciliationStep"
    input_description = "cross-plane runtime reconciliation tick"
    output_description = "one FlowPilot cross-plane consistency transition"
    reads = (
        "router_state",
        "execution_frontier",
        "packet_envelopes",
        "terminal_lifecycle",
        "route_state_snapshot",
        "cockpit_projection",
        "external_event_taxonomy",
        "install_sync_policy",
    )
    writes = ("abstract_consistency_fact",)
    idempotency = "run_id/route_version/active_node/packet identity scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.controller_boundary_preserved:
        yield Transition(
            "controller_boundary_preserved_for_cross_plane_audit",
            _inc(state, controller_boundary_preserved=True),
        )
        return

    if not state.material_scan_packets_observed:
        yield Transition(
            "material_scan_envelopes_have_role_contracts_and_write_targets",
            _inc(
                state,
                material_scan_packets_observed=True,
                material_output_contract_role_scoped=True,
                material_dispatch_write_target_explicit=True,
                material_legacy_packets_quarantined_or_migrated=True,
            ),
        )
        return

    if not state.terminal_closure_observed:
        yield Transition(
            "terminal_closure_writes_single_lifecycle_authority",
            _inc(
                state,
                terminal_closure_observed=True,
                run_lifecycle_record_written=True,
                router_frontier_lifecycle_terminal_consistent=True,
                terminal_control_blocker_cleared=True,
                heartbeat_inactive_after_terminal=True,
            ),
        )
        return

    if not state.completed_nodes_observed:
        yield Transition(
            "route_snapshot_projects_completed_frontier_nodes",
            _inc(
                state,
                completed_nodes_observed=True,
                route_snapshot_visible=True,
                route_snapshot_status_derived_from_frontier=True,
                route_snapshot_checklists_complete_for_completed_nodes=True,
                selected_status_separate_from_completion=True,
            ),
        )
        return

    if not state.cockpit_projection_visible:
        yield Transition(
            "cockpit_projects_completed_nodes_and_hides_closed_runs",
            _inc(
                state,
                cockpit_projection_visible=True,
                cockpit_status_derived_from_frontier=True,
                cockpit_checklists_complete_for_completed_nodes=True,
                cockpit_closed_runs_hidden_from_active_tabs=True,
            ),
        )
        return

    if not state.reviewer_block_events_observed:
        yield Transition(
            "reviewer_block_events_registered_in_router_taxonomy",
            _inc(
                state,
                reviewer_block_events_observed=True,
                reviewer_block_events_registered=True,
            ),
        )
        return

    if not state.role_event_artifacts_scanned:
        yield Transition(
            "role_output_event_artifacts_scanned",
            _inc(state, role_event_artifacts_scanned=True),
        )
        return

    if not state.gate_outcome_contracts_observed:
        yield Transition(
            "gate_outcome_contracts_cover_non_pass_paths",
            _inc(
                state,
                gate_outcome_contracts_observed=True,
                gate_outcome_contracts_complete=True,
            ),
        )
        return

    if not state.node_completion_observed:
        yield Transition(
            "node_completion_idempotency_scoped_to_active_node",
            _inc(
                state,
                node_completion_observed=True,
                node_completion_idempotency_scoped_to_active_node=True,
            ),
        )
        return

    if not state.cockpit_source_present_in_tree:
        yield Transition(
            "install_policy_accepts_first_class_cockpit_source",
            _inc(
                state,
                cockpit_source_present_in_tree=True,
                install_audit_policy_accepts_first_class_cockpit=True,
                installed_skill_matches_repository_source=True,
            ),
        )
        return

    if not state.standard_six_roles_requested:
        yield Transition(
            "standard_six_roles_ready_or_blocked_before_route_work",
            _inc(
                state,
                standard_six_roles_requested=True,
                role_liveness_ready_or_blocked=True,
            ),
        )
        return

    if not state.active_task_policy_observed:
        yield Transition(
            "active_task_catalog_uses_focus_pointer_and_explicit_active_set",
            _inc(
                state,
                active_task_policy_observed=True,
                history_default_hidden=True,
                current_pointer_is_ui_focus_only=True,
                active_task_set_has_explicit_authority=True,
            ),
        )
        return

    if not state.minimal_repair_strategy_selected:
        yield Transition(
            "minimal_repair_strategy_satisfies_cross_plane_invariants",
            _inc(state, minimal_repair_strategy_selected=True, status="complete"),
        )


__all__ = ["CrossPlaneReconciliationStep", "next_safe_states"]
