"""Invariants for the FlowPilot cross-plane friction model."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from flowpilot_cross_plane_friction_model_state import State


def _ok(message: str = "") -> InvariantResult:
    return InvariantResult(True, message)


def _fail(message: str) -> InvariantResult:
    return InvariantResult(False, message)


def controller_keeps_envelope_only_boundary(state: State, _trace: object) -> InvariantResult:
    if state.sealed_body_files_opened_by_controller:
        return _fail("Controller opened sealed body files during cross-plane reconciliation")
    return _ok()


def material_dispatch_contract_is_explicit(state: State, _trace: object) -> InvariantResult:
    if not state.material_scan_packets_observed:
        return _ok()
    missing: list[str] = []
    if not state.material_output_contract_role_scoped:
        missing.append("role-scoped output contract")
    if not state.material_dispatch_write_target_explicit:
        missing.append("explicit result write target")
    if not state.retired_material_packets_rejected:
        missing.append("retired packet rejection")
    if missing:
        return _fail(
            "material-scan dispatch lacks "
            + ", ".join(missing)
        )
    return _ok()


def terminal_closure_has_single_authority(state: State, _trace: object) -> InvariantResult:
    if not state.terminal_closure_observed:
        return _ok()
    missing: list[str] = []
    if not state.run_lifecycle_record_written:
        missing.append("run_lifecycle.json")
    if not state.router_frontier_lifecycle_terminal_consistent:
        missing.append("router/frontier/lifecycle terminal agreement")
    if not state.terminal_control_blocker_cleared:
        missing.append("cleared active control blocker")
    if not state.heartbeat_inactive_after_terminal:
        missing.append("inactive heartbeat")
    if missing:
        return _fail("terminal closure is missing " + ", ".join(missing))
    return _ok()


def route_snapshot_uses_frontier_completion(state: State, _trace: object) -> InvariantResult:
    if not (state.completed_nodes_observed and state.route_snapshot_visible):
        return _ok()
    missing: list[str] = []
    if not state.route_snapshot_status_derived_from_frontier:
        missing.append("completed-node status from execution_frontier")
    if not state.route_snapshot_checklists_complete_for_completed_nodes:
        missing.append("completed-node checklist projection")
    if not state.selected_status_separate_from_completion:
        missing.append("selected/current state separated from completion")
    if missing:
        return _fail("route_state_snapshot is missing " + ", ".join(missing))
    return _ok()


def cockpit_uses_same_completion_projection(state: State, _trace: object) -> InvariantResult:
    if not state.cockpit_projection_visible:
        return _ok()
    missing: list[str] = []
    if not state.cockpit_status_derived_from_frontier:
        missing.append("node status from execution_frontier")
    if not state.cockpit_checklists_complete_for_completed_nodes:
        missing.append("completed-node checklist projection")
    if not state.cockpit_closed_runs_hidden_from_active_tabs:
        missing.append("closed runs hidden from active tabs")
    if missing:
        return _fail("Cockpit projection is missing " + ", ".join(missing))
    return _ok()


def reviewer_block_events_are_known(state: State, _trace: object) -> InvariantResult:
    if state.minimal_repair_strategy_selected and not state.role_event_artifacts_scanned:
        return _fail("role output event artifacts were not scanned during event taxonomy audit")
    if state.reviewer_block_events_observed and not state.reviewer_block_events_registered:
        return _fail("reviewer blocker events are outside EXTERNAL_EVENTS taxonomy")
    return _ok()


def gate_outcome_contracts_have_non_pass_paths(state: State, _trace: object) -> InvariantResult:
    if state.gate_outcome_contracts_observed and not state.gate_outcome_contracts_complete:
        return _fail("reviewer/officer gate outcome contracts have pass-only paths")
    return _ok()


def node_completion_is_idempotent_per_active_node(state: State, _trace: object) -> InvariantResult:
    if (
        state.node_completion_observed
        and not state.node_completion_idempotency_scoped_to_active_node
    ):
        return _fail("node completion idempotency is not scoped to the active node")
    return _ok()


def install_policy_matches_first_class_sources(state: State, _trace: object) -> InvariantResult:
    if not state.cockpit_source_present_in_tree:
        return _ok()
    if not state.install_audit_policy_accepts_first_class_cockpit:
        return _fail("install audit still rejects first-class flowpilot_cockpit source")
    if not state.installed_skill_matches_repository_source:
        return _fail("installed FlowPilot skill source differs from repository source")
    return _ok()


def standard_six_roles_have_liveness_gate(state: State, _trace: object) -> InvariantResult:
    if state.standard_six_roles_requested and not state.role_liveness_ready_or_blocked:
        return _fail("runtime-requested role bindings have neither readiness proof nor an early blocker")
    return _ok()


def active_task_policy_hides_history(state: State, _trace: object) -> InvariantResult:
    if not state.active_task_policy_observed:
        return _ok()
    if not state.history_default_hidden:
        return _fail("completed, abandoned, or stale history is visible by default")
    if not state.current_pointer_is_ui_focus_only:
        return _fail("current pointer is not limited to UI focus/default target")
    if not state.active_task_set_has_explicit_authority:
        return _fail("active UI task set lacks explicit run-index authority")
    return _ok()


INVARIANTS = (
    Invariant(
        name="controller_keeps_envelope_only_boundary",
        description="Cross-plane reconciliation does not open sealed bodies.",
        predicate=controller_keeps_envelope_only_boundary,
    ),
    Invariant(
        name="material_dispatch_contract_is_explicit",
        description="Material-scan dispatch carries role contract, write target, and legacy policy.",
        predicate=material_dispatch_contract_is_explicit,
    ),
    Invariant(
        name="terminal_closure_has_single_authority",
        description="Terminal closure reconciles lifecycle, router, frontier, blocker, and heartbeat authorities.",
        predicate=terminal_closure_has_single_authority,
    ),
    Invariant(
        name="route_snapshot_uses_frontier_completion",
        description="route_state_snapshot derives completed node and checklist status from frontier completion.",
        predicate=route_snapshot_uses_frontier_completion,
    ),
    Invariant(
        name="cockpit_uses_same_completion_projection",
        description="Cockpit uses the same completed-node projection and hides closed runs from active tabs.",
        predicate=cockpit_uses_same_completion_projection,
    ),
    Invariant(
        name="reviewer_block_events_are_known",
        description="Reviewer blocker events are registered in router EXTERNAL_EVENTS.",
        predicate=reviewer_block_events_are_known,
    ),
    Invariant(
        name="gate_outcome_contracts_have_non_pass_paths",
        description="Reviewer/officer gate outcome contracts include a non-pass repair route.",
        predicate=gate_outcome_contracts_have_non_pass_paths,
    ),
    Invariant(
        name="node_completion_is_idempotent_per_active_node",
        description="Node completion repeatability is scoped to the active node, not a global done flag.",
        predicate=node_completion_is_idempotent_per_active_node,
    ),
    Invariant(
        name="install_policy_matches_first_class_sources",
        description="Install audit policy matches first-class Cockpit source and installed skill source.",
        predicate=install_policy_matches_first_class_sources,
    ),
    Invariant(
        name="standard_six_roles_have_liveness_gate",
        description="Standard role-binding runs prove readiness or stop at an early blocker.",
        predicate=standard_six_roles_have_liveness_gate,
    ),
    Invariant(
        name="active_task_policy_hides_history",
        description="Active task catalog hides completed, abandoned, and stale history by default.",
        predicate=active_task_policy_hides_history,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


__all__ = [
    "INVARIANTS",
    "active_task_policy_hides_history",
    "cockpit_uses_same_completion_projection",
    "controller_keeps_envelope_only_boundary",
    "gate_outcome_contracts_have_non_pass_paths",
    "install_policy_matches_first_class_sources",
    "invariant_failures",
    "material_dispatch_contract_is_explicit",
    "node_completion_is_idempotent_per_active_node",
    "reviewer_block_events_are_known",
    "route_snapshot_uses_frontier_completion",
    "standard_six_roles_have_liveness_gate",
    "terminal_closure_has_single_authority",
]
