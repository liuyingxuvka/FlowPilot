"""State and constants for the FlowPilot cross-plane friction model."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import NamedTuple


TERMINAL_STATUSES = frozenset(
    {
        "closed",
        "complete",
        "completed",
        "terminal",
        "stopped",
        "stopped_by_user",
        "cancelled",
        "cancelled_by_user",
        "protocol_dead_end",
    }
)
ACTIVE_STATUSES = frozenset({"running", "active", "in_progress", "current"})
DONE_ITEM_STATUSES = frozenset({"complete", "completed", "done", "passed", "closed"})
STANDARD_SIX_ROLES = frozenset(
    {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
        "worker_a",
        "worker_b",
    }
)
BODY_PATH_NAMES = frozenset(
    {
        "packet_body.md",
        "result_body.md",
        "report_body.md",
        "decision_body.md",
    }
)


@dataclass(frozen=True)
class Tick:
    """One cross-plane reconciliation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    step: int = 0

    controller_boundary_preserved: bool = False
    sealed_body_files_opened_by_controller: bool = False

    material_scan_packets_observed: bool = False
    material_output_contract_role_scoped: bool = True
    material_dispatch_write_target_explicit: bool = True
    unsupported_material_packets_rejected: bool = True

    terminal_closure_observed: bool = False
    run_lifecycle_record_written: bool = True
    router_frontier_lifecycle_terminal_consistent: bool = True
    terminal_control_blocker_cleared: bool = True
    heartbeat_inactive_after_terminal: bool = True

    completed_nodes_observed: bool = False
    route_snapshot_visible: bool = False
    route_snapshot_status_derived_from_frontier: bool = True
    route_snapshot_checklists_complete_for_completed_nodes: bool = True
    selected_status_separate_from_completion: bool = True

    cockpit_projection_visible: bool = False
    cockpit_status_derived_from_frontier: bool = True
    cockpit_checklists_complete_for_completed_nodes: bool = True
    cockpit_closed_runs_hidden_from_active_tabs: bool = True

    reviewer_block_events_observed: bool = False
    reviewer_block_events_registered: bool = True
    role_event_artifacts_scanned: bool = False
    gate_outcome_contracts_observed: bool = False
    gate_outcome_contracts_complete: bool = True

    node_completion_observed: bool = False
    node_completion_idempotency_scoped_to_active_node: bool = True

    cockpit_source_present_in_tree: bool = False
    install_audit_policy_accepts_first_class_cockpit: bool = True
    installed_skill_matches_repository_source: bool = True

    standard_six_roles_requested: bool = False
    role_liveness_ready_or_blocked: bool = True

    active_task_policy_observed: bool = False
    history_default_hidden: bool = True
    current_pointer_is_ui_focus_only: bool = True
    active_task_set_has_explicit_authority: bool = True

    minimal_repair_strategy_selected: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    next_status = str(changes.pop("status", "running"))
    return replace(state, step=state.step + 1, status=next_status, **changes)


__all__ = [
    "ACTIVE_STATUSES",
    "BODY_PATH_NAMES",
    "DONE_ITEM_STATUSES",
    "STANDARD_SIX_ROLES",
    "TERMINAL_STATUSES",
    "Action",
    "State",
    "Tick",
    "Transition",
    "initial_state",
    "_inc",
]
