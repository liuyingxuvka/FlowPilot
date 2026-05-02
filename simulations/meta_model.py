"""FlowGuard model for the FlowPilot meta workflow.

This model treats FlowGuard as both process designer and checker. FlowPilot
must start with a showcase-grade floor, make self-interrogation visible, create
real heartbeat continuity, design the route through FlowGuard before execution,
and avoid completion while obvious high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TARGET_CHUNKS = 2
CREW_SIZE = 6
MAX_ROUTE_REVISIONS = 2
MAX_IMPL_RETRIES = 1
MAX_EXPERIMENTS = 1
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
MAX_COMPOSITE_STRUCTURAL_REPAIRS = 1
MIN_FULL_GRILLME_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_GRILLME_QUESTIONS = 20
MAX_FOCUSED_GRILLME_QUESTIONS = 50
DEFAULT_FOCUSED_GRILLME_QUESTIONS = 30
MIN_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 5
MAX_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 10
DEFAULT_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 7
MODEL_DYNAMIC_LAYER_COUNT = 6
LAYER_GOAL_ACCEPTANCE = 1 << 0
LAYER_FUNCTIONAL_CAPABILITY = 1 << 1
LAYER_DATA_STATE = 1 << 2
LAYER_IMPLEMENTATION_STRATEGY = 1 << 3
LAYER_UI_EXPERIENCE = 1 << 4
LAYER_VALIDATION = 1 << 5
LAYER_RECOVERY_HEARTBEAT = 1 << 6
LAYER_DELIVERY_SHOWCASE = 1 << 7
REQUIRED_RISK_FAMILY_MASK = (
    LAYER_GOAL_ACCEPTANCE
    | LAYER_FUNCTIONAL_CAPABILITY
    | LAYER_DATA_STATE
    | LAYER_IMPLEMENTATION_STRATEGY
    | LAYER_UI_EXPERIENCE
    | LAYER_VALIDATION
    | LAYER_RECOVERY_HEARTBEAT
    | LAYER_DELIVERY_SHOWCASE
)


@dataclass(frozen=True)
class Tick:
    """One heartbeat/autopilot decision step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    flowpilot_enabled: bool = False
    startup_banner_emitted: bool = False
    mode_choice_offered: bool = False
    mode_selected: bool = False
    showcase_floor_committed: bool = False
    visible_self_interrogation_done: bool = False
    startup_self_interrogation_questions: int = 0
    startup_self_interrogation_layer_count: int = 0
    startup_self_interrogation_questions_per_layer: int = 0
    startup_self_interrogation_layers: int = 0
    startup_self_interrogation_pm_ratified: bool = False
    quality_candidate_pool_seeded: bool = False
    validation_strategy_seeded: bool = False
    material_sources_scanned: bool = False
    material_source_summaries_written: bool = False
    material_source_quality_classified: bool = False
    material_intake_packet_written: bool = False
    material_reviewer_sufficiency_checked: bool = False
    material_reviewer_sufficiency_approved: bool = False
    pm_material_understanding_memo_written: bool = False
    pm_material_complexity_classified: bool = False
    pm_material_discovery_decision_recorded: bool = False
    product_function_architecture_pm_synthesized: bool = False
    product_function_user_task_map_written: bool = False
    product_function_capability_map_written: bool = False
    product_function_feature_decisions_written: bool = False
    product_function_display_rationale_written: bool = False
    product_function_gap_review_done: bool = False
    product_function_negative_scope_written: bool = False
    product_function_acceptance_matrix_written: bool = False
    product_function_architecture_product_officer_approved: bool = False
    product_function_architecture_reviewer_challenged: bool = False
    visible_user_flow_diagram_emitted: bool = False
    user_flow_diagram_refreshed: bool = False
    dependency_plan_recorded: bool = False
    future_installs_deferred: bool = False
    contract_frozen: bool = False
    contract_revision: int = 0
    crew_policy_written: bool = False
    crew_count: int = 0
    project_manager_ready: bool = False
    reviewer_ready: bool = False
    process_flowguard_officer_ready: bool = False
    product_flowguard_officer_ready: bool = False
    worker_a_ready: bool = False
    worker_b_ready: bool = False
    crew_ledger_written: bool = False
    role_identity_protocol_recorded: bool = False
    pm_flowguard_delegation_policy_recorded: bool = False
    crew_memory_policy_written: bool = False
    crew_memory_packets_written: int = 0
    pm_initial_route_decision_recorded: bool = False
    child_skill_route_design_discovery_started: bool = False
    child_skill_initial_gate_manifest_extracted: bool = False
    child_skill_gate_approvers_assigned: bool = False
    child_skill_manifest_reviewer_reviewed: bool = False
    child_skill_manifest_process_officer_approved: bool = False
    child_skill_manifest_product_officer_approved: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    heartbeat_loaded_state: bool = False
    heartbeat_loaded_frontier: bool = False
    heartbeat_loaded_crew_memory: bool = False
    heartbeat_restored_crew: bool = False
    heartbeat_rehydrated_crew: bool = False
    replacement_roles_seeded_from_memory: bool = False
    heartbeat_pm_decision_requested: bool = False
    pm_resume_decision_recorded: bool = False
    pm_completion_runway_recorded: bool = False
    pm_runway_hard_stops_recorded: bool = False
    pm_runway_checkpoint_cadence_recorded: bool = False
    pm_runway_synced_to_plan: bool = False
    plan_sync_method_recorded: bool = False
    visible_plan_has_runway_depth: bool = False
    pm_node_decision_recorded: bool = False
    crew_archived: bool = False
    crew_memory_archived: bool = False
    continuation_probe_done: bool = False
    host_continuation_supported: bool = False
    manual_resume_mode_recorded: bool = False
    heartbeat_active: bool = False
    heartbeat_schedule_created: bool = False
    stable_heartbeat_launcher_recorded: bool = False
    heartbeat_health_checked: bool = False
    live_subagent_decision_recorded: bool = False
    live_subagents_started: bool = False
    single_agent_role_continuity_authorized: bool = False
    startup_activation_guard_passed: bool = False
    external_watchdog_policy_recorded: bool = False
    external_watchdog_busy_lease_policy_recorded: bool = False
    external_watchdog_busy_lease_autowrap_policy_recorded: bool = False
    external_watchdog_source_drift_policy_recorded: bool = False
    external_watchdog_automation_created: bool = False
    external_watchdog_hidden_noninteractive_configured: bool = False
    external_watchdog_active: bool = False
    global_watchdog_supervisor_checked: bool = False
    global_watchdog_supervisor_singleton_ready: bool = False
    global_watchdog_supervisor_cadence_minutes: int = 0
    external_watchdog_stopped_before_heartbeat: bool = False
    terminal_lifecycle_frontier_written: bool = False
    lifecycle_reconciliation_done: bool = False
    controlled_stop_notice_recorded: bool = False
    terminal_completion_notice_recorded: bool = False

    route_version: int = 0
    route_checked: bool = False
    markdown_synced: bool = False
    execution_frontier_written: bool = False
    codex_plan_synced: bool = False
    frontier_version: int = 0
    plan_version: int = 0
    flowguard_process_design_done: bool = False
    candidate_route_tree_generated: bool = False
    root_route_model_checked: bool = False
    root_route_model_process_officer_approved: bool = False
    root_product_function_model_checked: bool = False
    root_product_function_model_product_officer_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
    parent_subtree_review_checked: bool = False
    parent_product_function_model_checked: bool = False
    parent_product_function_model_product_officer_approved: bool = False
    parent_focused_interrogation_done: bool = False
    parent_focused_interrogation_questions: int = 0
    parent_focused_interrogation_scope_id: str = ""
    unfinished_current_node_recovery_checked: bool = False
    active_node: str = "new"

    chunk_state: str = "none"  # none | ready | executed | verified | checkpoint_pending
    node_focused_interrogation_done: bool = False
    node_focused_interrogation_questions: int = 0
    node_focused_interrogation_scope_id: str = ""
    node_product_function_model_checked: bool = False
    node_product_function_model_product_officer_approved: bool = False
    lightweight_self_check_done: bool = False
    lightweight_self_check_questions: int = 0
    lightweight_self_check_scope_id: str = ""
    quality_package_done: bool = False
    quality_candidate_registry_checked: bool = False
    quality_raise_decision_recorded: bool = False
    validation_matrix_defined: bool = False
    anti_rough_finish_done: bool = False
    node_human_review_context_loaded: bool = False
    node_human_neutral_observation_written: bool = False
    node_human_manual_experiments_run: bool = False
    node_human_inspection_passed: bool = False
    node_human_review_reviewer_approved: bool = False
    node_human_inspections_passed: int = 0
    inspection_issue_grilled: bool = False
    pm_repair_decision_interrogations: int = 0
    human_inspection_repairs: int = 0
    composite_backward_context_loaded: bool = False
    composite_child_evidence_replayed: bool = False
    composite_backward_neutral_observation_written: bool = False
    composite_structure_decision_recorded: bool = False
    composite_backward_human_review_passed: bool = False
    composite_backward_review_reviewer_approved: bool = False
    composite_backward_reviews_passed: int = 0
    composite_issue_grilled: bool = False
    composite_issue_strategy: str = "none"
    composite_structural_route_repairs: int = 0
    composite_new_sibling_nodes: int = 0
    composite_subtree_rebuilds: int = 0
    quality_route_raises: int = 0
    quality_reworks: int = 0
    node_visible_roadmap_emitted: bool = False
    verification_defined: bool = False
    required_chunks: int = TARGET_CHUNKS
    completed_chunks: int = 0
    checkpoint_written: bool = False
    role_memory_refreshed_after_work: bool = False

    issue: str = "none"  # none | model_gap | inspection_failure | composite_backward_failure | impl_failure | unknown_failure | no_progress
    route_revisions: int = 0
    impl_retries: int = 0
    experiments: int = 0

    child_node_sidecar_scan_done: bool = False
    sidecar_need: str = "unknown"  # unknown | none | needed
    subagent_pool_exists: bool = False
    subagent_idle_available: bool = False
    subagent_scope_checked: bool = False
    subagent_status: str = "none"  # none | idle | pending | returned | merged
    high_risk_gate: str = "none"  # none | pending | approved | denied

    completion_self_interrogation_done: bool = False
    completion_self_interrogation_questions: int = 0
    completion_self_interrogation_layer_count: int = 0
    completion_self_interrogation_questions_per_layer: int = 0
    completion_self_interrogation_layers: int = 0
    completion_visible_roadmap_emitted: bool = False
    final_feature_matrix_review_done: bool = False
    final_acceptance_matrix_review_done: bool = False
    final_quality_candidate_review_done: bool = False
    final_product_function_model_replayed: bool = False
    final_product_function_model_product_officer_approved: bool = False
    final_human_review_context_loaded: bool = False
    final_human_neutral_observation_written: bool = False
    final_human_manual_experiments_run: bool = False
    final_human_inspection_passed: bool = False
    final_human_review_reviewer_approved: bool = False
    final_route_wide_gate_ledger_current_route_scanned: bool = False
    final_route_wide_gate_ledger_effective_nodes_resolved: bool = False
    final_route_wide_gate_ledger_child_skill_gates_collected: bool = False
    final_route_wide_gate_ledger_human_review_gates_collected: bool = False
    final_route_wide_gate_ledger_product_process_gates_collected: bool = False
    final_route_wide_gate_ledger_resource_lineage_resolved: bool = False
    final_route_wide_gate_ledger_stale_evidence_checked: bool = False
    final_route_wide_gate_ledger_superseded_nodes_explained: bool = False
    final_route_wide_gate_ledger_unresolved_count_zero: bool = False
    final_route_wide_gate_ledger_pm_built: bool = False
    final_route_wide_gate_ledger_reviewer_backward_checked: bool = False
    final_route_wide_gate_ledger_pm_completion_approved: bool = False
    high_value_work_review: str = "unknown"  # unknown | exhausted
    standard_expansions: int = 0
    final_report_emitted: bool = False
    pm_completion_decision_recorded: bool = False
    heartbeat_records: int = 0


def _step(state: State, *, label: str, action: str, **changes) -> FunctionResult:
    return FunctionResult(
        output=Action(action),
        new_state=replace(
            state,
            heartbeat_records=1,
            **changes,
        ),
        label=label,
    )


def _reset_quality_gates() -> dict[str, object]:
    return {
        "quality_package_done": False,
        "quality_candidate_registry_checked": False,
        "quality_raise_decision_recorded": False,
        "validation_matrix_defined": False,
        "anti_rough_finish_done": False,
    }


def _reset_dual_layer_scope_gates() -> dict[str, object]:
    return {
        "parent_product_function_model_checked": False,
        "parent_product_function_model_product_officer_approved": False,
        "node_product_function_model_checked": False,
        "node_product_function_model_product_officer_approved": False,
        "node_human_review_context_loaded": False,
        "node_human_neutral_observation_written": False,
        "node_human_manual_experiments_run": False,
        "node_human_inspection_passed": False,
        "node_human_review_reviewer_approved": False,
        "inspection_issue_grilled": False,
        "composite_backward_context_loaded": False,
        "composite_child_evidence_replayed": False,
        "composite_backward_neutral_observation_written": False,
        "composite_structure_decision_recorded": False,
        "composite_backward_human_review_passed": False,
        "composite_backward_review_reviewer_approved": False,
        "composite_issue_grilled": False,
        "composite_issue_strategy": "none",
    }


def _reset_execution_scope_gates() -> dict[str, object]:
    gates = _reset_quality_gates()
    gates.update(_reset_dual_layer_scope_gates())
    gates.update(_reset_final_route_wide_gate_ledger())
    gates.update(
        {
            "heartbeat_loaded_state": False,
            "heartbeat_loaded_frontier": False,
            "heartbeat_loaded_crew_memory": False,
            "heartbeat_restored_crew": False,
            "heartbeat_rehydrated_crew": False,
            "replacement_roles_seeded_from_memory": False,
            "heartbeat_pm_decision_requested": False,
            "pm_resume_decision_recorded": False,
            "pm_completion_runway_recorded": False,
            "pm_runway_hard_stops_recorded": False,
            "pm_runway_checkpoint_cadence_recorded": False,
            "pm_runway_synced_to_plan": False,
            "plan_sync_method_recorded": False,
            "visible_plan_has_runway_depth": False,
            "pm_node_decision_recorded": False,
        }
    )
    return gates


def _reset_final_route_wide_gate_ledger() -> dict[str, object]:
    return {
        "final_route_wide_gate_ledger_current_route_scanned": False,
        "final_route_wide_gate_ledger_effective_nodes_resolved": False,
        "final_route_wide_gate_ledger_child_skill_gates_collected": False,
        "final_route_wide_gate_ledger_human_review_gates_collected": False,
        "final_route_wide_gate_ledger_product_process_gates_collected": False,
        "final_route_wide_gate_ledger_resource_lineage_resolved": False,
        "final_route_wide_gate_ledger_stale_evidence_checked": False,
        "final_route_wide_gate_ledger_superseded_nodes_explained": False,
        "final_route_wide_gate_ledger_unresolved_count_zero": False,
        "final_route_wide_gate_ledger_pm_built": False,
        "final_route_wide_gate_ledger_reviewer_backward_checked": False,
        "final_route_wide_gate_ledger_pm_completion_approved": False,
    }


def _covers_required_risk_families(layer_mask: int) -> bool:
    return (layer_mask & REQUIRED_RISK_FAMILY_MASK) == REQUIRED_RISK_FAMILY_MASK


def _full_interrogation_ready(
    *,
    total_questions: int,
    layer_count: int,
    questions_per_layer: int,
    risk_family_mask: int,
) -> bool:
    return (
        layer_count > 0
        and questions_per_layer >= MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
        and total_questions >= layer_count * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
        and _covers_required_risk_families(risk_family_mask)
    )


def _focused_interrogation_ready(*, total_questions: int, scope_id: str) -> bool:
    return (
        bool(scope_id)
        and MIN_FOCUSED_GRILLME_QUESTIONS
        <= total_questions
        <= MAX_FOCUSED_GRILLME_QUESTIONS
    )


def _lightweight_self_check_ready(*, total_questions: int, scope_id: str) -> bool:
    return (
        bool(scope_id)
        and MIN_LIGHTWEIGHT_SELF_CHECK_QUESTIONS
        <= total_questions
        <= MAX_LIGHTWEIGHT_SELF_CHECK_QUESTIONS
    )


def _product_function_architecture_ready(state: State) -> bool:
    return (
        _material_handoff_ready(state)
        and state.product_function_architecture_pm_synthesized
        and state.product_function_user_task_map_written
        and state.product_function_capability_map_written
        and state.product_function_feature_decisions_written
        and state.product_function_display_rationale_written
        and state.product_function_gap_review_done
        and state.product_function_negative_scope_written
        and state.product_function_acceptance_matrix_written
        and state.product_function_architecture_product_officer_approved
        and state.product_function_architecture_reviewer_challenged
    )


def _material_handoff_ready(state: State) -> bool:
    return (
        state.startup_self_interrogation_pm_ratified
        and state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
        and state.material_intake_packet_written
        and state.material_reviewer_sufficiency_checked
        and state.material_reviewer_sufficiency_approved
        and state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
        and state.pm_material_discovery_decision_recorded
    )


def _crew_ready(state: State) -> bool:
    return (
        state.crew_policy_written
        and state.crew_count == CREW_SIZE
        and state.project_manager_ready
        and state.reviewer_ready
        and state.process_flowguard_officer_ready
        and state.product_flowguard_officer_ready
        and state.worker_a_ready
        and state.worker_b_ready
        and state.crew_ledger_written
        and state.role_identity_protocol_recorded
        and state.pm_flowguard_delegation_policy_recorded
        and state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
    )


def _automated_continuation_configured(state: State) -> bool:
    return (
        state.continuation_probe_done
        and state.host_continuation_supported
        and not state.manual_resume_mode_recorded
        and state.heartbeat_schedule_created
        and state.stable_heartbeat_launcher_recorded
        and state.external_watchdog_policy_recorded
        and state.external_watchdog_busy_lease_policy_recorded
        and state.external_watchdog_busy_lease_autowrap_policy_recorded
        and state.external_watchdog_source_drift_policy_recorded
        and state.external_watchdog_automation_created
        and state.external_watchdog_hidden_noninteractive_configured
        and state.global_watchdog_supervisor_checked
        and state.global_watchdog_supervisor_singleton_ready
        and state.global_watchdog_supervisor_cadence_minutes == 30
    )


def _automated_continuation_ready(state: State) -> bool:
    return (
        _automated_continuation_configured(state)
        and state.external_watchdog_active
        and not state.external_watchdog_stopped_before_heartbeat
    )


def _manual_resume_ready(state: State) -> bool:
    return (
        state.continuation_probe_done
        and not state.host_continuation_supported
        and state.manual_resume_mode_recorded
        and not state.heartbeat_schedule_created
        and not state.stable_heartbeat_launcher_recorded
        and not state.external_watchdog_policy_recorded
        and not state.external_watchdog_busy_lease_policy_recorded
        and not state.external_watchdog_busy_lease_autowrap_policy_recorded
        and not state.external_watchdog_source_drift_policy_recorded
        and not state.external_watchdog_automation_created
        and not state.external_watchdog_hidden_noninteractive_configured
        and not state.external_watchdog_active
        and not state.global_watchdog_supervisor_checked
        and not state.global_watchdog_supervisor_singleton_ready
        and state.global_watchdog_supervisor_cadence_minutes == 0
    )


def _continuation_ready(state: State) -> bool:
    return _automated_continuation_ready(state) or _manual_resume_ready(state)


def _live_subagent_startup_resolved(state: State) -> bool:
    return (
        state.live_subagent_decision_recorded
        and (
            state.live_subagents_started
            or state.single_agent_role_continuity_authorized
        )
    )


def _continuation_lifecycle_valid(state: State) -> bool:
    return (
        _continuation_ready(state)
        or (
            _automated_continuation_configured(state)
            and state.lifecycle_reconciliation_done
            and state.external_watchdog_stopped_before_heartbeat
            and not state.external_watchdog_active
        )
    )


def _terminal_continuation_reconciled(state: State) -> bool:
    if _automated_continuation_configured(state):
        return (
            state.lifecycle_reconciliation_done
            and state.external_watchdog_stopped_before_heartbeat
            and not state.external_watchdog_active
            and state.terminal_lifecycle_frontier_written
        )
    if _manual_resume_ready(state):
        return (
            state.lifecycle_reconciliation_done
            and not state.external_watchdog_active
            and state.terminal_lifecycle_frontier_written
        )
    return False


def _final_route_wide_gate_ledger_ready(state: State) -> bool:
    return (
        state.final_route_wide_gate_ledger_current_route_scanned
        and state.final_route_wide_gate_ledger_effective_nodes_resolved
        and state.final_route_wide_gate_ledger_child_skill_gates_collected
        and state.final_route_wide_gate_ledger_human_review_gates_collected
        and state.final_route_wide_gate_ledger_product_process_gates_collected
        and state.final_route_wide_gate_ledger_resource_lineage_resolved
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_route_wide_gate_ledger_pm_completion_approved
    )


def _route_ready(state: State) -> bool:
    return (
        state.status == "running"
        and state.flowpilot_enabled
        and state.startup_banner_emitted
        and state.mode_choice_offered
        and state.mode_selected
        and state.showcase_floor_committed
        and state.visible_self_interrogation_done
        and state.startup_self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and _continuation_ready(state)
        and state.flowguard_process_design_done
        and state.route_version > 0
        and state.route_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.route_version
        and state.plan_version == state.frontier_version
        and state.user_flow_diagram_refreshed
        and state.visible_user_flow_diagram_emitted
        and _live_subagent_startup_resolved(state)
        and state.startup_activation_guard_passed
        and state.issue == "none"
        and state.high_risk_gate != "pending"
        and state.chunk_state == "none"
    )


class AutopilotStep:
    name = "AutopilotStep"
    reads = (
        "status",
        "flowpilot_enabled",
        "startup_banner_emitted",
        "mode_choice_offered",
        "mode_selected",
        "showcase_floor_committed",
        "visible_self_interrogation_done",
        "startup_self_interrogation_questions",
        "startup_self_interrogation_layer_count",
        "startup_self_interrogation_questions_per_layer",
        "startup_self_interrogation_layers",
        "startup_self_interrogation_pm_ratified",
        "quality_candidate_pool_seeded",
        "validation_strategy_seeded",
        "material_sources_scanned",
        "material_source_summaries_written",
        "material_source_quality_classified",
        "material_intake_packet_written",
        "material_reviewer_sufficiency_checked",
        "material_reviewer_sufficiency_approved",
        "pm_material_understanding_memo_written",
        "pm_material_complexity_classified",
        "pm_material_discovery_decision_recorded",
        "product_function_architecture_pm_synthesized",
        "product_function_user_task_map_written",
        "product_function_capability_map_written",
        "product_function_feature_decisions_written",
        "product_function_display_rationale_written",
        "product_function_gap_review_done",
        "product_function_negative_scope_written",
        "product_function_acceptance_matrix_written",
        "product_function_architecture_product_officer_approved",
        "product_function_architecture_reviewer_challenged",
        "visible_user_flow_diagram_emitted",
        "user_flow_diagram_refreshed",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "contract_frozen",
        "crew_policy_written",
        "crew_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "crew_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "crew_memory_policy_written",
        "crew_memory_packets_written",
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_crew_memory",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "replacement_roles_seeded_from_memory",
        "heartbeat_pm_decision_requested",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_node_decision_recorded",
        "crew_archived",
        "crew_memory_archived",
        "continuation_probe_done",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
        "heartbeat_schedule_created",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
        "live_subagent_decision_recorded",
        "live_subagents_started",
        "single_agent_role_continuity_authorized",
        "startup_activation_guard_passed",
        "external_watchdog_policy_recorded",
        "external_watchdog_busy_lease_policy_recorded",
        "external_watchdog_busy_lease_autowrap_policy_recorded",
        "external_watchdog_source_drift_policy_recorded",
        "external_watchdog_automation_created",
        "external_watchdog_hidden_noninteractive_configured",
        "external_watchdog_active",
        "global_watchdog_supervisor_checked",
        "global_watchdog_supervisor_singleton_ready",
        "global_watchdog_supervisor_cadence_minutes",
        "external_watchdog_stopped_before_heartbeat",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "flowguard_process_design_done",
        "candidate_route_tree_generated",
        "root_route_model_checked",
        "root_route_model_process_officer_approved",
        "root_product_function_model_checked",
        "root_product_function_model_product_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_product_officer_approved",
        "parent_focused_interrogation_done",
        "parent_focused_interrogation_questions",
        "parent_focused_interrogation_scope_id",
        "unfinished_current_node_recovery_checked",
        "route_checked",
        "markdown_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "chunk_state",
        "node_focused_interrogation_done",
        "node_focused_interrogation_questions",
        "node_focused_interrogation_scope_id",
        "node_product_function_model_checked",
        "node_product_function_model_product_officer_approved",
        "lightweight_self_check_done",
        "lightweight_self_check_questions",
        "lightweight_self_check_scope_id",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "node_human_review_context_loaded",
        "node_human_neutral_observation_written",
        "node_human_manual_experiments_run",
        "node_human_inspection_passed",
        "node_human_review_reviewer_approved",
        "node_human_inspections_passed",
        "inspection_issue_grilled",
        "human_inspection_repairs",
        "composite_backward_context_loaded",
        "composite_child_evidence_replayed",
        "composite_backward_neutral_observation_written",
        "composite_structure_decision_recorded",
        "composite_backward_human_review_passed",
        "composite_backward_review_reviewer_approved",
        "composite_backward_reviews_passed",
        "composite_issue_grilled",
        "composite_issue_strategy",
        "composite_structural_route_repairs",
        "composite_new_sibling_nodes",
        "composite_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "node_visible_roadmap_emitted",
        "issue",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_scope_checked",
        "subagent_status",
        "high_risk_gate",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_visible_roadmap_emitted",
        "final_feature_matrix_review_done",
        "final_acceptance_matrix_review_done",
        "final_quality_candidate_review_done",
        "final_product_function_model_replayed",
        "final_product_function_model_product_officer_approved",
        "final_human_review_context_loaded",
        "final_human_neutral_observation_written",
        "final_human_manual_experiments_run",
        "final_human_inspection_passed",
        "final_human_review_reviewer_approved",
        "final_route_wide_gate_ledger_current_route_scanned",
        "final_route_wide_gate_ledger_effective_nodes_resolved",
        "final_route_wide_gate_ledger_child_skill_gates_collected",
        "final_route_wide_gate_ledger_human_review_gates_collected",
        "final_route_wide_gate_ledger_product_process_gates_collected",
        "final_route_wide_gate_ledger_resource_lineage_resolved",
        "final_route_wide_gate_ledger_stale_evidence_checked",
        "final_route_wide_gate_ledger_superseded_nodes_explained",
        "final_route_wide_gate_ledger_unresolved_count_zero",
        "final_route_wide_gate_ledger_pm_built",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "pm_completion_decision_recorded",
    )
    writes = (
        "status",
        "flowpilot_enabled",
        "startup_banner_emitted",
        "mode_choice_offered",
        "mode_selected",
        "showcase_floor_committed",
        "visible_self_interrogation_done",
        "startup_self_interrogation_questions",
        "startup_self_interrogation_layer_count",
        "startup_self_interrogation_questions_per_layer",
        "startup_self_interrogation_layers",
        "startup_self_interrogation_pm_ratified",
        "quality_candidate_pool_seeded",
        "validation_strategy_seeded",
        "material_sources_scanned",
        "material_source_summaries_written",
        "material_source_quality_classified",
        "material_intake_packet_written",
        "material_reviewer_sufficiency_checked",
        "material_reviewer_sufficiency_approved",
        "pm_material_understanding_memo_written",
        "pm_material_complexity_classified",
        "pm_material_discovery_decision_recorded",
        "product_function_architecture_pm_synthesized",
        "product_function_user_task_map_written",
        "product_function_capability_map_written",
        "product_function_feature_decisions_written",
        "product_function_display_rationale_written",
        "product_function_gap_review_done",
        "product_function_negative_scope_written",
        "product_function_acceptance_matrix_written",
        "product_function_architecture_product_officer_approved",
        "product_function_architecture_reviewer_challenged",
        "visible_user_flow_diagram_emitted",
        "user_flow_diagram_refreshed",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "contract_frozen",
        "crew_policy_written",
        "crew_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "crew_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_restored_crew",
        "heartbeat_pm_decision_requested",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_node_decision_recorded",
        "crew_archived",
        "heartbeat_active",
        "heartbeat_schedule_created",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
        "live_subagent_decision_recorded",
        "live_subagents_started",
        "single_agent_role_continuity_authorized",
        "startup_activation_guard_passed",
        "external_watchdog_policy_recorded",
        "external_watchdog_busy_lease_policy_recorded",
        "external_watchdog_busy_lease_autowrap_policy_recorded",
        "external_watchdog_source_drift_policy_recorded",
        "external_watchdog_automation_created",
        "external_watchdog_hidden_noninteractive_configured",
        "external_watchdog_active",
        "global_watchdog_supervisor_checked",
        "global_watchdog_supervisor_singleton_ready",
        "global_watchdog_supervisor_cadence_minutes",
        "external_watchdog_stopped_before_heartbeat",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "route_version",
        "route_checked",
        "markdown_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "flowguard_process_design_done",
        "candidate_route_tree_generated",
        "root_route_model_checked",
        "root_route_model_process_officer_approved",
        "root_product_function_model_checked",
        "root_product_function_model_product_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_product_officer_approved",
        "parent_focused_interrogation_done",
        "parent_focused_interrogation_questions",
        "parent_focused_interrogation_scope_id",
        "unfinished_current_node_recovery_checked",
        "active_node",
        "chunk_state",
        "node_focused_interrogation_done",
        "node_focused_interrogation_questions",
        "node_focused_interrogation_scope_id",
        "node_product_function_model_checked",
        "node_product_function_model_product_officer_approved",
        "lightweight_self_check_done",
        "lightweight_self_check_questions",
        "lightweight_self_check_scope_id",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "node_human_review_context_loaded",
        "node_human_neutral_observation_written",
        "node_human_manual_experiments_run",
        "node_human_inspection_passed",
        "node_human_review_reviewer_approved",
        "node_human_inspections_passed",
        "inspection_issue_grilled",
        "human_inspection_repairs",
        "composite_backward_context_loaded",
        "composite_child_evidence_replayed",
        "composite_backward_neutral_observation_written",
        "composite_structure_decision_recorded",
        "composite_backward_human_review_passed",
        "composite_backward_review_reviewer_approved",
        "composite_backward_reviews_passed",
        "composite_issue_grilled",
        "composite_issue_strategy",
        "composite_structural_route_repairs",
        "composite_new_sibling_nodes",
        "composite_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "node_visible_roadmap_emitted",
        "verification_defined",
        "required_chunks",
        "completed_chunks",
        "checkpoint_written",
        "role_memory_refreshed_after_work",
        "issue",
        "route_revisions",
        "impl_retries",
        "experiments",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_scope_checked",
        "subagent_status",
        "high_risk_gate",
        "completion_self_interrogation_done",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_visible_roadmap_emitted",
        "final_feature_matrix_review_done",
        "final_acceptance_matrix_review_done",
        "final_quality_candidate_review_done",
        "final_product_function_model_replayed",
        "final_product_function_model_product_officer_approved",
        "final_human_review_context_loaded",
        "final_human_neutral_observation_written",
        "final_human_manual_experiments_run",
        "final_human_inspection_passed",
        "final_human_review_reviewer_approved",
        "final_route_wide_gate_ledger_current_route_scanned",
        "final_route_wide_gate_ledger_effective_nodes_resolved",
        "final_route_wide_gate_ledger_child_skill_gates_collected",
        "final_route_wide_gate_ledger_human_review_gates_collected",
        "final_route_wide_gate_ledger_product_process_gates_collected",
        "final_route_wide_gate_ledger_resource_lineage_resolved",
        "final_route_wide_gate_ledger_stale_evidence_checked",
        "final_route_wide_gate_ledger_superseded_nodes_explained",
        "final_route_wide_gate_ledger_unresolved_count_zero",
        "final_route_wide_gate_ledger_pm_built",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "high_value_work_review",
        "standard_expansions",
        "final_report_emitted",
        "pm_completion_decision_recorded",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "heartbeat_records",
    )
    accepted_input_type = Tick
    input_description = "one continuation/autopilot control decision"
    output_description = "next allowed control action"
    idempotency = (
        "Repeated heartbeat decisions do not lower the frozen contract, do not "
        "complete early, and must either advance, recover, update the model, or block."
    )

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        if state.status == "new":
            yield _step(
                state,
                label="autopilot_started",
                action="start the FlowPilot control loop",
                status="running",
                flowpilot_enabled=True,
                heartbeat_active=True,
                active_node="emit_startup_banner",
            )
            return

        if not state.startup_banner_emitted:
            yield _step(
                state,
                label="startup_banner_emitted",
                action="emit a large ASCII FlowPilot startup banner in chat before mode selection",
                startup_banner_emitted=True,
                active_node="select_mode",
            )
            return

        if not state.mode_choice_offered:
            yield _step(
                state,
                label="mode_choice_offered",
                action="offer full-auto, autonomous, guided, and strict-gated modes from loosest to strictest",
                mode_choice_offered=True,
                active_node="await_mode_choice",
            )
            return

        if not state.mode_selected:
            yield _step(
                state,
                label="mode_selected_by_user",
                action="record user-selected run mode",
                mode_selected=True,
                active_node="freeze_contract",
            )
            yield _step(
                state,
                label="default_mode_recorded",
                action="record full-auto mode because user asked to continue or host cannot pause",
                mode_selected=True,
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
                action="derive dynamic layers, expose at least 100 grill-me questions per active layer, seed the improvement candidate pool, and seed initial validation direction before contract freeze",
                visible_self_interrogation_done=True,
                startup_self_interrogation_questions=(
                    MODEL_DYNAMIC_LAYER_COUNT
                    * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                ),
                startup_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                startup_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                startup_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                quality_candidate_pool_seeded=True,
                validation_strategy_seeded=True,
                active_node="establish_six_agent_crew",
            )
            return

        if not state.crew_policy_written:
            yield _step(
                state,
                label="six_agent_crew_policy_written",
                action="write fixed six-agent crew policy: project manager, reviewer, process FlowGuard officer, product FlowGuard officer, worker A, worker B",
                crew_policy_written=True,
                active_node="spawn_project_manager",
            )
            return

        if state.crew_count == 0:
            yield _step(
                state,
                label="project_manager_spawned_or_restored",
                action="spawn or restore the persistent project manager before route work",
                crew_count=1,
                project_manager_ready=True,
                active_node="spawn_reviewer",
            )
            return

        if state.crew_count == 1:
            yield _step(
                state,
                label="human_like_reviewer_spawned_or_restored",
                action="spawn or restore the persistent human-like reviewer before route work",
                crew_count=2,
                reviewer_ready=True,
                active_node="spawn_process_flowguard_officer",
            )
            return

        if state.crew_count == 2:
            yield _step(
                state,
                label="process_flowguard_officer_spawned_or_restored",
                action="spawn or restore the process FlowGuard officer before route work",
                crew_count=3,
                process_flowguard_officer_ready=True,
                active_node="spawn_product_flowguard_officer",
            )
            return

        if state.crew_count == 3:
            yield _step(
                state,
                label="product_flowguard_officer_spawned_or_restored",
                action="spawn or restore the product FlowGuard officer before route work",
                crew_count=4,
                product_flowguard_officer_ready=True,
                active_node="spawn_worker_a",
            )
            return

        if state.crew_count == 4:
            yield _step(
                state,
                label="worker_a_spawned_or_restored",
                action="spawn or restore worker A for bounded sidecar work",
                crew_count=5,
                worker_a_ready=True,
                active_node="spawn_worker_b",
            )
            return

        if state.crew_count == 5:
            yield _step(
                state,
                label="worker_b_spawned_or_restored",
                action="spawn or restore worker B for bounded sidecar work",
                crew_count=CREW_SIZE,
                worker_b_ready=True,
                active_node="write_crew_ledger",
            )
            return

        if not state.crew_ledger_written:
            yield _step(
                state,
                label="crew_ledger_written",
                action="persist crew names, role authority, agent ids, status, and recovery rules before route work",
                crew_ledger_written=True,
                active_node="record_role_identity_protocol",
            )
            return

        if not state.role_identity_protocol_recorded:
            yield _step(
                state,
                label="role_identity_protocol_recorded",
                action="record distinct role_key, display_name, and diagnostic-only agent_id fields before crew memory is authoritative",
                role_identity_protocol_recorded=True,
                active_node="record_pm_flowguard_delegation_policy",
            )
            return

        if not state.pm_flowguard_delegation_policy_recorded:
            yield _step(
                state,
                label="pm_flowguard_delegation_policy_recorded",
                action="record that the project manager may create structured FlowGuard modeling requests for uncertain process or product decisions and assign them to the process or product FlowGuard officer",
                pm_flowguard_delegation_policy_recorded=True,
                active_node="write_crew_memory_packets",
            )
            return

        if not state.crew_memory_policy_written:
            yield _step(
                state,
                label="crew_memory_packets_written",
                action="write compact role memory packets for all six roles before route work",
                crew_memory_policy_written=True,
                crew_memory_packets_written=CREW_SIZE,
                active_node="pm_ratify_startup_self_interrogation",
            )
            return

        if not state.startup_self_interrogation_pm_ratified:
            yield _step(
                state,
                label="startup_self_interrogation_pm_ratified",
                action="project manager ratifies startup self-interrogation scope, risk layers, question count, and decision set before route/model gates",
                startup_self_interrogation_pm_ratified=True,
                active_node="material_intake",
            )
            return

        if not state.material_sources_scanned:
            yield _step(
                state,
                label="material_sources_scanned",
                action="main executor scans user-provided and repository-local materials before PM route design",
                material_sources_scanned=True,
                active_node="summarize_material_sources",
            )
            return

        if not state.material_source_summaries_written:
            yield _step(
                state,
                label="material_source_summaries_written",
                action="main executor writes purpose, contents, and current-state summaries for every relevant material source",
                material_source_summaries_written=True,
                active_node="classify_material_source_quality",
            )
            return

        if not state.material_source_quality_classified:
            yield _step(
                state,
                label="material_source_quality_classified",
                action="main executor classifies source authority, freshness, contradictions, missing context, and readiness",
                material_source_quality_classified=True,
                active_node="write_material_intake_packet",
            )
            return

        if not state.material_intake_packet_written:
            yield _step(
                state,
                label="material_intake_packet_written",
                action="main executor writes the Material Intake Packet as descriptive startup evidence",
                material_intake_packet_written=True,
                active_node="review_material_intake_packet",
            )
            return

        if not state.material_reviewer_sufficiency_checked:
            yield _step(
                state,
                label="material_reviewer_sufficiency_checked",
                action="human-like reviewer checks whether the material packet is clear and complete enough for PM planning",
                material_reviewer_sufficiency_checked=True,
                active_node="approve_material_intake_packet",
            )
            return

        if not state.material_reviewer_sufficiency_approved:
            yield _step(
                state,
                label="material_reviewer_sufficiency_approved",
                action="human-like reviewer approves that the Material Intake Packet is PM-ready or records blockers before PM receives it",
                material_reviewer_sufficiency_approved=True,
                active_node="write_pm_material_understanding_memo",
            )
            return

        if not state.pm_material_understanding_memo_written:
            yield _step(
                state,
                label="pm_material_understanding_memo_written",
                action="project manager writes a material understanding memo with source-claim matrix, open questions, and route implications",
                pm_material_understanding_memo_written=True,
                active_node="classify_material_complexity",
            )
            return

        if not state.pm_material_complexity_classified:
            yield _step(
                state,
                label="pm_material_complexity_classified",
                action="project manager classifies material complexity as simple, normal, or messy/raw before route planning",
                pm_material_complexity_classified=True,
                active_node="record_material_discovery_decision",
            )
            return

        if not state.pm_material_discovery_decision_recorded:
            yield _step(
                state,
                label="pm_material_discovery_decision_recorded",
                action="project manager records whether materials can feed route design directly or require a formal discovery, cleanup, modeling, or validation subtree",
                pm_material_discovery_decision_recorded=True,
                active_node="product_function_architecture",
            )
            return

        if not state.product_function_architecture_pm_synthesized:
            yield _step(
                state,
                label="product_function_architecture_pm_synthesized",
                action="project manager synthesizes grilled ideas into a product-function architecture decision package before contract freeze",
                product_function_architecture_pm_synthesized=True,
                active_node="write_product_function_user_task_map",
            )
            return

        if not state.product_function_user_task_map_written:
            yield _step(
                state,
                label="product_function_user_task_map_written",
                action="write the target users, situations, jobs-to-be-done, and decision points that the product must serve",
                product_function_user_task_map_written=True,
                active_node="write_product_function_capability_map",
            )
            return

        if not state.product_function_capability_map_written:
            yield _step(
                state,
                label="product_function_capability_map_written",
                action="write the must, should, optional, and rejected product capabilities before route generation",
                product_function_capability_map_written=True,
                active_node="write_product_function_feature_decisions",
            )
            return

        if not state.product_function_feature_decisions_written:
            yield _step(
                state,
                label="product_function_feature_decisions_written",
                action="record feature necessity decisions that bind each accepted feature to a user task and reject features without product value",
                product_function_feature_decisions_written=True,
                active_node="write_product_function_display_rationale",
            )
            return

        if not state.product_function_display_rationale_written:
            yield _step(
                state,
                label="product_function_display_rationale_written",
                action="record why each visible text, state, control, card, or status should be shown and what user decision it changes",
                product_function_display_rationale_written=True,
                active_node="review_product_function_gaps",
            )
            return

        if not state.product_function_gap_review_done:
            yield _step(
                state,
                label="product_function_missing_feature_review_done",
                action="review likely missing high-value functions before implementation turns the route into local tasks",
                product_function_gap_review_done=True,
                active_node="write_product_function_negative_scope",
            )
            return

        if not state.product_function_negative_scope_written:
            yield _step(
                state,
                label="product_function_negative_scope_written",
                action="write explicit non-goals and rejected displays so the route does not grow accidental features",
                product_function_negative_scope_written=True,
                active_node="write_product_function_acceptance_matrix",
            )
            return

        if not state.product_function_acceptance_matrix_written:
            yield _step(
                state,
                label="product_function_acceptance_matrix_written",
                action="write a functional acceptance matrix covering inputs, outputs, states, failure cases, and required evidence for each core capability",
                product_function_acceptance_matrix_written=True,
                active_node="approve_product_function_architecture",
            )
            return

        if not state.product_function_architecture_product_officer_approved:
            yield _step(
                state,
                label="product_function_architecture_product_officer_approved",
                action="product FlowGuard officer approves that the PM product-function architecture is modelable and strong enough to freeze the contract from",
                product_function_architecture_product_officer_approved=True,
                active_node="challenge_product_function_architecture",
            )
            return

        if not state.product_function_architecture_reviewer_challenged:
            yield _step(
                state,
                label="product_function_architecture_reviewer_challenged",
                action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
                product_function_architecture_reviewer_challenged=True,
                active_node="freeze_contract",
            )
            return

        if not state.contract_frozen:
            yield _step(
                state,
                label="contract_frozen",
                action="freeze high-ambition acceptance floor from the PM product-function architecture without limiting future standard increases",
                contract_frozen=True,
                active_node="record_dependency_plan",
            )
            return

        if not state.dependency_plan_recorded:
            yield _step(
                state,
                label="dependency_plan_recorded",
                action="record dependency inventory and defer non-current installs",
                dependency_plan_recorded=True,
                future_installs_deferred=True,
                active_node="create_initial_route",
            )
            return

        if not state.continuation_probe_done:
            yield _step(
                state,
                label="host_continuation_capability_supported",
                action="probe host automation capability and confirm real heartbeat, watchdog, and global supervisor setup is supported",
                continuation_probe_done=True,
                host_continuation_supported=True,
                active_node="create_heartbeat_schedule",
            )
            yield _step(
                state,
                label="host_continuation_capability_unsupported_manual_resume",
                action="probe host automation capability, find no real wakeup support, and record manual-resume mode without creating heartbeat, watchdog, or global supervisor automation",
                continuation_probe_done=True,
                host_continuation_supported=False,
                manual_resume_mode_recorded=True,
                active_node="design_flowguard_route",
            )
            return

        if state.host_continuation_supported and not state.heartbeat_schedule_created:
            yield _step(
                state,
                label="heartbeat_schedule_created",
                action="create real continuation heartbeat as a stable launcher that reads state and execution frontier",
                heartbeat_schedule_created=True,
                stable_heartbeat_launcher_recorded=True,
                active_node="record_external_watchdog_policy",
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_policy_recorded",
                action="record external watchdog stale threshold, evidence path, and official automation reset action",
                external_watchdog_policy_recorded=True,
                active_node="record_busy_lease_autowrap_policy",
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_busy_lease_autowrap_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_busy_lease_autowrap_policy_recorded",
                action="record busy-lease suppression plus automatic bounded-operation wrapper policy for long commands and waits",
                external_watchdog_busy_lease_policy_recorded=True,
                external_watchdog_busy_lease_autowrap_policy_recorded=True,
                active_node="record_watchdog_source_drift_policy",
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_source_drift_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_source_drift_policy_recorded",
                action="record watchdog source-status policy: trust state, latest heartbeat, and busy lease only; record frontier/lifecycle drift diagnostics; never inspect live subagent busy state",
                external_watchdog_source_drift_policy_recorded=True,
                active_node="ensure_global_watchdog_supervisor",
            )
            return

        if state.host_continuation_supported and not state.global_watchdog_supervisor_checked:
            yield _step(
                state,
                label="global_watchdog_supervisor_verified",
                action="look up the singleton Codex global watchdog supervisor; if none is active and at least one project registration lease is active, create or reactivate exactly one fixed 30-minute cron automation using the canonical automation_update parameter shape",
                global_watchdog_supervisor_checked=True,
                global_watchdog_supervisor_singleton_ready=True,
                global_watchdog_supervisor_cadence_minutes=30,
                active_node="create_external_watchdog_automation",
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_automation_created:
            yield _step(
                state,
                label="external_watchdog_automation_created",
                action="create paired external watchdog automation immediately after heartbeat schedule creation with hidden/noninteractive execution",
                external_watchdog_automation_created=True,
                external_watchdog_hidden_noninteractive_configured=True,
                external_watchdog_active=True,
                active_node="design_flowguard_route",
            )
            return

        if not state.pm_initial_route_decision_recorded:
            yield _step(
                state,
                label="pm_initial_route_decision_recorded",
                action="ask the project manager to choose the initial route-design direction from the contract, self-interrogation, dependencies, and crew reports",
                pm_initial_route_decision_recorded=True,
                active_node="discover_child_skill_gates",
            )
            return

        if not state.child_skill_route_design_discovery_started:
            yield _step(
                state,
                label="child_skill_route_design_discovery_started",
                action="project manager discovers likely child skills and gate surfaces before FlowGuard route design",
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
                action="project manager assigns required approver roles for every child-skill gate and forbids main-executor or worker self-approval",
                child_skill_gate_approvers_assigned=True,
                active_node="review_child_skill_gate_manifest",
            )
            return

        if not state.child_skill_manifest_reviewer_reviewed:
            yield _step(
                state,
                label="child_skill_manifest_reviewer_reviewed",
                action="human-like reviewer reviews product, visual, interaction, and real-use child-skill gates before route freeze",
                child_skill_manifest_reviewer_reviewed=True,
                active_node="approve_child_skill_process_gates",
            )
            return

        if not state.child_skill_manifest_process_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_process_officer_approved",
                action="process FlowGuard officer approves child-skill process and conformance gates before route modeling",
                child_skill_manifest_process_officer_approved=True,
                active_node="approve_child_skill_product_gates",
            )
            return

        if not state.child_skill_manifest_product_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_product_officer_approved",
                action="product FlowGuard officer approves product-function impact gates derived from child skills",
                child_skill_manifest_product_officer_approved=True,
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
                active_node="check_root_route_model",
            )
            return

        if not state.root_route_model_checked:
            yield _step(
                state,
                label="root_route_model_checked",
                action="process FlowGuard officer runs and approves checks against the candidate route tree before route freeze",
                root_route_model_checked=True,
                root_route_model_process_officer_approved=True,
                active_node="check_root_product_function_model",
            )
            return

        if not state.root_product_function_model_checked:
            yield _step(
                state,
                label="root_product_function_model_checked",
                action="product FlowGuard officer runs and approves checks against the root product-function model before route freeze",
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
                    active_node="blocked",
                )
                return
            yield _step(
                state,
                label="route_model_checked",
                action="run FlowGuard checks for active route",
                route_checked=True,
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
                action="emit visible user flow diagram with current node, next jumps, checks, fallback branches, and simulated path",
                visible_user_flow_diagram_emitted=True,
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
            and state.visible_user_flow_diagram_emitted
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
            and state.visible_user_flow_diagram_emitted
            and state.live_subagent_decision_recorded
            and not state.live_subagents_started
            and not state.single_agent_role_continuity_authorized
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="six_live_subagents_started",
                action="start or resume all six live FlowPilot background agents and record startup evidence",
                live_subagents_started=True,
                active_node="run_startup_activation_guard",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.user_flow_diagram_refreshed
            and state.visible_user_flow_diagram_emitted
            and _live_subagent_startup_resolved(state)
            and not state.startup_activation_guard_passed
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="startup_activation_guard_passed",
                action="run startup hard gate against state, frontier, active route, crew ledger, role memory, live-subagent startup resolution, and continuation evidence before child work",
                startup_activation_guard_passed=True,
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
                high_risk_gate="denied",
                active_node="blocked",
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
                flowguard_process_design_done=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
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
                "candidate_route_tree_generated": False,
                "root_route_model_checked": False,
                "root_route_model_process_officer_approved": False,
                "root_product_function_model_checked": False,
                "root_product_function_model_product_officer_approved": False,
                "strict_gate_obligation_review_model_checked": False,
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
                composite_subtree_rebuilds=state.composite_subtree_rebuilds + 1,
                **common_changes,
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue == "inspection_failure":
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
                flowguard_process_design_done=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
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
                parent_subtree_review_checked=False,
                issue="none",
                route_revisions=state.route_revisions + 1,
                human_inspection_repairs=state.human_inspection_repairs + 1,
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
                    flowguard_process_design_done=False,
                    child_skill_route_design_discovery_started=False,
                    child_skill_initial_gate_manifest_extracted=False,
                    child_skill_gate_approvers_assigned=False,
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
                    action="human-like composite backward reviewer accepts the child rollup before checkpoint",
                    composite_backward_human_review_passed=True,
                    composite_backward_review_reviewer_approved=True,
                    composite_backward_reviews_passed=state.composite_backward_reviews_passed + 1,
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
                action="write verified checkpoint",
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
                active_node="ready_for_chunk"
                if state.completed_chunks < state.required_chunks
                else "ready_to_complete",
                **_reset_execution_scope_gates(),
            )
            return

        if (
            state.completed_chunks >= state.required_chunks
            and state.checkpoint_written
            and _route_ready(state)
            and state.subagent_status not in {"pending", "returned"}
        ):
            if not state.completion_visible_roadmap_emitted:
                yield _step(
                    state,
                    label="completion_visible_user_flow_diagram_emitted",
                    action="emit visible completion user flow diagram before deciding whether any high-value work remains",
                    completion_visible_roadmap_emitted=True,
                    active_node="final_feature_matrix_review",
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review implemented feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                    active_node="final_acceptance_matrix_review",
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                    active_node="final_quality_candidate_review",
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                    active_node="final_product_function_replay",
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer replays and approves final product behavior against the root product-function model before completion grill-me",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                    active_node="final_human_inspection_context",
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final output, route evidence, product model, concept or acceptance evidence, and known repairs for final human-like review",
                    final_human_review_context_loaded=True,
                    active_node="final_human_neutral_observation",
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of the final product artifacts before final pass/fail judgement",
                    final_human_neutral_observation_written=True,
                    active_node="final_human_manual_experiments",
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="operate or inspect the final product as a human reviewer before completion grill-me",
                    final_human_manual_experiments_run=True,
                    active_node="final_human_inspection_decision",
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts the product as a complete showcase candidate",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                    active_node="completion_self_interrogation",
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer to find remaining high-value work",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                    active_node="review_high_value_work",
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_work_found_and_route_expanded",
                        action="raise the standard and route another verified chunk",
                        route_version=state.route_version + 1,
                        route_checked=False,
                        markdown_synced=False,
                        execution_frontier_written=False,
                        codex_plan_synced=False,
                        frontier_version=0,
                        plan_version=0,
                        visible_user_flow_diagram_emitted=False,
                        user_flow_diagram_refreshed=False,
                        flowguard_process_design_done=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
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
                        parent_subtree_review_checked=False,
                        parent_focused_interrogation_done=False,
                        parent_focused_interrogation_questions=0,
                        parent_focused_interrogation_scope_id="",
                        unfinished_current_node_recovery_checked=False,
                        required_chunks=TARGET_CHUNKS,
                        completed_chunks=TARGET_CHUNKS - 1,
                        node_human_inspections_passed=TARGET_CHUNKS - 1,
                        composite_backward_reviews_passed=TARGET_CHUNKS - 1,
                        checkpoint_written=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_visible_roadmap_emitted=False,
                        high_value_work_review="unknown",
                        standard_expansions=state.standard_expansions + 1,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        terminal_lifecycle_frontier_written=False,
                        node_focused_interrogation_done=False,
                        node_focused_interrogation_questions=0,
                        node_focused_interrogation_scope_id="",
                        lightweight_self_check_done=False,
                        lightweight_self_check_questions=0,
                        lightweight_self_check_scope_id="",
                        node_visible_roadmap_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_quality_candidate_review_done=False,
                        final_product_function_model_replayed=False,
                        final_product_function_model_product_officer_approved=False,
                        final_human_review_context_loaded=False,
                        final_human_neutral_observation_written=False,
                        final_human_manual_experiments_run=False,
                        final_human_inspection_passed=False,
                        final_human_review_reviewer_approved=False,
                        pm_completion_decision_recorded=False,
                        active_node="run_expanded_route_checks",
                        **_reset_execution_scope_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                    active_node="ready_to_complete",
                )
                return
            if state.high_value_work_review != "exhausted":
                return
            if not state.final_route_wide_gate_ledger_current_route_scanned:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_current_route_scanned",
                    action="PM starts final route-wide gate ledger by scanning the current active route, execution frontier, and route mutation history",
                    final_route_wide_gate_ledger_current_route_scanned=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_effective_nodes_resolved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_effective_nodes_resolved",
                    action="PM resolves active, repaired, inserted, waived, and superseded nodes from the current route before completion approval",
                    final_route_wide_gate_ledger_effective_nodes_resolved=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_child_skill_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_child_skill_gates_collected",
                    action="PM collects every current child-skill gate, completion standard, evidence path, waiver, blocker, and role approval into the final ledger",
                    final_route_wide_gate_ledger_child_skill_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_human_review_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_human_review_gates_collected",
                    action="PM collects node, parent, final, strict-obligation, and same-inspector review gates into the final ledger",
                    final_route_wide_gate_ledger_human_review_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_product_process_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_product_process_gates_collected",
                    action="PM collects product-function and development-process model gates into the final ledger",
                    final_route_wide_gate_ledger_product_process_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_resource_lineage_resolved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_resource_lineage_resolved",
                    action="PM resolves generated-resource lineage into consumed, final-output, evidence, superseded, quarantined, or intentionally discarded entries",
                    final_route_wide_gate_ledger_resource_lineage_resolved=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_stale_evidence_checked:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_stale_evidence_checked",
                    action="PM checks that no stale or invalidated evidence is still closing a current route obligation",
                    final_route_wide_gate_ledger_stale_evidence_checked=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_superseded_nodes_explained:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_superseded_nodes_explained",
                    action="PM records replacement, waiver, or no-longer-effective explanations for every superseded node and gate",
                    final_route_wide_gate_ledger_superseded_nodes_explained=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_unresolved_count_zero:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_unresolved_count_zero",
                    action="PM records zero unresolved current-route obligations before final reviewer replay",
                    final_route_wide_gate_ledger_unresolved_count_zero=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_pm_built:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_pm_built",
                    action="PM writes the final route-wide gate ledger from current route state and evidence, not from the startup checklist",
                    final_route_wide_gate_ledger_pm_built=True,
                    active_node="final_route_wide_gate_ledger_reviewer_replay",
                )
                return
            if not state.final_route_wide_gate_ledger_reviewer_backward_checked:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_reviewer_backward_checked",
                    action="human-like reviewer checks the final product backward through the PM-built route-wide ledger",
                    final_route_wide_gate_ledger_reviewer_backward_checked=True,
                    active_node="final_route_wide_gate_ledger_pm_approval",
                )
                return
            if not state.final_route_wide_gate_ledger_pm_completion_approved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_pm_completion_approved",
                    action="project manager approves the clean route-wide gate ledger before lifecycle closure and final completion decision",
                    final_route_wide_gate_ledger_pm_completion_approved=True,
                    active_node="ready_to_complete",
                )
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex automations, global supervisor records, Windows scheduled tasks, local state, execution frontier, and watchdog evidence before route shutdown",
                    lifecycle_reconciliation_done=True,
                    active_node="reconcile_lifecycle",
                )
                return
            if not state.external_watchdog_stopped_before_heartbeat:
                yield _step(
                    state,
                    label="external_watchdog_stopped_before_heartbeat",
                    action="stop paired external watchdog automation before stopping heartbeat",
                    external_watchdog_active=False,
                    external_watchdog_stopped_before_heartbeat=True,
                    active_node="ready_to_stop_heartbeat",
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write watchdog inactive and terminal heartbeat lifecycle back to execution frontier before stopping heartbeat",
                    terminal_lifecycle_frontier_written=True,
                    active_node="terminal_lifecycle_frontier_synced",
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive final role memory packet statuses after lifecycle reconciliation and before crew ledger archive",
                    crew_memory_archived=True,
                    active_node="ready_to_archive_crew",
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger and final role statuses after role memory archive and before final report",
                    crew_archived=True,
                    active_node="ready_to_emit_final_report",
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves completion after final product replay, final human review, high-value review, lifecycle cleanup, and crew archive",
                    pm_completion_decision_recorded=True,
                    active_node="ready_to_emit_final_report",
                )
                return
            yield _step(
                state,
                label="final_report_emitted",
                action="emit final report, emit terminal completion notice, and reconcile continuation lifecycle",
                status="complete",
                heartbeat_active=False,
                final_report_emitted=True,
                terminal_completion_notice_recorded=True,
                active_node="complete",
            )
            return

        if _route_ready(state) and state.completed_chunks < TARGET_CHUNKS:
            if not state.heartbeat_loaded_state:
                yield _step(
                    state,
                    label="heartbeat_loaded_state",
                    action="continuation turn loads local state, active route, latest heartbeat or manual-resume evidence, watchdog evidence when present, lifecycle evidence, and crew ledger",
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
                    active_node="heartbeat_ask_project_manager",
                )
                return
            if not state.heartbeat_pm_decision_requested:
                yield _step(
                    state,
                    label="heartbeat_asked_project_manager",
                    action="continuation turn asks the project manager what the main executor should do next",
                    heartbeat_pm_decision_requested=True,
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
                    action="main executor calls the host native plan tool when available, or records the fallback method, and replaces the visible plan with a downstream PM runway projection",
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
                    action="project manager assigns the current node work package before the main executor defines implementation work",
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
            if not state.node_product_function_model_checked:
                yield _step(
                    state,
                    label="node_product_function_model_checked",
                    action="product FlowGuard officer runs and approves the active leaf's product-function model before defining implementation work",
                    node_product_function_model_checked=True,
                    node_product_function_model_product_officer_approved=True,
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
                        flowguard_process_design_done=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
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
                    label="main_agent_merged_sidecar_report",
                    action="main agent verifies and merges the sidecar report while keeping node ownership",
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
                    active_node="load_human_inspection_context",
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
            if not state.node_human_inspection_passed:
                if (
                    state.completed_chunks == 0
                    and state.human_inspection_repairs < 1
                ):
                    yield _step(
                        state,
                        label="human_inspection_found_blocking_issue",
                        action="human-like reviewer rejects the node evidence and requires a route-mutating repair",
                        issue="inspection_failure",
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        active_node="grill_human_inspection_issue",
                    )
                    return
                yield _step(
                    state,
                    label="node_human_inspection_passed",
                    action="human-like reviewer accepts the repaired node evidence and product behavior",
                    node_human_inspection_passed=True,
                    node_human_review_reviewer_approved=True,
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

        yield _step(
            state,
            label="blocked_unhandled_state",
            action="block because no valid transition exists and emit a nonterminal resume notice",
            status="blocked",
            heartbeat_active=False,
            controlled_stop_notice_recorded=True,
            active_node="blocked",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del current_output, trace
    return state.status in {"blocked", "complete"}


def no_completion_before_verified_contract(state: State, trace) -> InvariantResult:
    del trace
    if not state.final_report_emitted:
        return InvariantResult.pass_()
    if not state.flowpilot_enabled:
        return InvariantResult.fail("final report emitted before FlowPilot was enabled")
    if not state.startup_banner_emitted:
        return InvariantResult.fail("final report emitted before FlowPilot startup banner was visible")
    if not (state.mode_choice_offered and state.mode_selected):
        return InvariantResult.fail("final report emitted before mode choice was offered and selected")
    if not (state.showcase_floor_committed and state.visible_self_interrogation_done):
        return InvariantResult.fail("final report emitted before showcase floor and visible self-interrogation")
    if not _full_interrogation_ready(
        total_questions=state.startup_self_interrogation_questions,
        layer_count=state.startup_self_interrogation_layer_count,
        questions_per_layer=state.startup_self_interrogation_questions_per_layer,
        risk_family_mask=state.startup_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "final report emitted before startup self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    if not (state.quality_candidate_pool_seeded and state.validation_strategy_seeded):
        return InvariantResult.fail(
            "final report emitted before startup grill-me seeded the improvement candidate pool and validation direction"
        )
    if not _product_function_architecture_ready(state):
        return InvariantResult.fail(
            "final report emitted before PM-owned product-function architecture, product-officer approval, and reviewer challenge"
        )
    if not (state.dependency_plan_recorded and state.future_installs_deferred):
        return InvariantResult.fail("final report emitted before demand-driven dependency plan was recorded")
    if not state.contract_frozen:
        return InvariantResult.fail("final report emitted before contract was frozen")
    if not (
        _crew_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.crew_archived
    ):
        return InvariantResult.fail(
            "final report emitted before six-agent crew ledger, PM route decision, and terminal crew archive"
        )
    if not (state.heartbeat_active or state.status == "complete"):
        return InvariantResult.fail("final report emitted without heartbeat continuity")
    if not (
        _continuation_ready(state)
        and _terminal_continuation_reconciled(state)
        and state.flowguard_process_design_done
    ):
        return InvariantResult.fail("final report emitted before host continuation probe, lifecycle writeback, and FlowGuard process design")
    if not (
        state.candidate_route_tree_generated
        and state.root_route_model_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
        and state.root_route_model_process_officer_approved
        and state.root_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail("final report emitted before candidate route tree, root process model, root product-function model, and strict gate-obligation review model checks")
    if state.contract_revision != 0:
        return InvariantResult.fail("final report emitted after contract revision")
    if state.completed_chunks < state.required_chunks:
        return InvariantResult.fail("final report emitted before target chunks verified")
    if state.node_human_inspections_passed < state.completed_chunks:
        return InvariantResult.fail("final report emitted before every completed chunk passed human-like product inspection")
    if state.composite_backward_reviews_passed < state.completed_chunks:
        return InvariantResult.fail(
            "final report emitted before every completed composite checkpoint passed backward human-like review"
        )
    if not state.checkpoint_written:
        return InvariantResult.fail("final report emitted without final checkpoint")
    if not state.route_checked:
        return InvariantResult.fail("final report emitted without checked active route")
    if not state.markdown_synced:
        return InvariantResult.fail("final report emitted before Markdown sync")
    if not (
        state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.route_version
        and state.plan_version == state.frontier_version
    ):
        return InvariantResult.fail("final report emitted before execution frontier and Codex plan sync")
    if not state.visible_user_flow_diagram_emitted:
        return InvariantResult.fail("final report emitted before visible user flow diagram")
    if not state.startup_activation_guard_passed:
        return InvariantResult.fail("final report emitted before startup activation guard pass")
    if not (
        state.completion_self_interrogation_done
        and state.high_value_work_review == "exhausted"
    ):
        return InvariantResult.fail("final report emitted before completion grill-me exhausted obvious high-value work")
    if not state.completion_visible_roadmap_emitted:
        return InvariantResult.fail("final report emitted before visible completion user flow diagram")
    if not (
        state.final_feature_matrix_review_done
        and state.final_acceptance_matrix_review_done
        and state.final_quality_candidate_review_done
        and state.final_product_function_model_replayed
        and state.final_human_review_context_loaded
        and state.final_human_neutral_observation_written
        and state.final_human_manual_experiments_run
        and state.final_human_inspection_passed
    ):
        return InvariantResult.fail(
            "final report emitted before final feature, acceptance, quality-candidate, product-model replay, and human-like reviews"
        )
    if not _final_route_wide_gate_ledger_ready(state):
        return InvariantResult.fail(
            "final report emitted before PM-built dynamic route-wide gate ledger, reviewer backward replay, and PM ledger approval"
        )
    if not _full_interrogation_ready(
        total_questions=state.completion_self_interrogation_questions,
        layer_count=state.completion_self_interrogation_layer_count,
        questions_per_layer=state.completion_self_interrogation_questions_per_layer,
        risk_family_mask=state.completion_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "final report emitted before completion self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    return InvariantResult.pass_()


def frozen_contract_never_changes(state: State, trace) -> InvariantResult:
    del trace
    if state.contract_revision != 0:
        return InvariantResult.fail("frozen contract changed")
    return InvariantResult.pass_()


def mode_choice_before_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.contract_frozen and not (
        state.flowpilot_enabled and state.startup_banner_emitted
        and state.mode_choice_offered and state.mode_selected
        and state.showcase_floor_committed and state.visible_self_interrogation_done
        and _full_interrogation_ready(
            total_questions=state.startup_self_interrogation_questions,
            layer_count=state.startup_self_interrogation_layer_count,
            questions_per_layer=state.startup_self_interrogation_questions_per_layer,
            risk_family_mask=state.startup_self_interrogation_layers,
        )
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _crew_ready(state)
        and _product_function_architecture_ready(state)
    ):
        return InvariantResult.fail("contract frozen before FlowPilot startup banner, mode, showcase floor, dynamic per-layer visible self-interrogation, crew recovery, PM product-function architecture, candidate pool, and validation-direction gates")
    return InvariantResult.pass_()


def startup_banner_before_mode_choice(state: State, trace) -> InvariantResult:
    del trace
    if state.mode_choice_offered and not (
        state.flowpilot_enabled and state.startup_banner_emitted
    ):
        return InvariantResult.fail("mode choice offered before visible FlowPilot startup banner")
    return InvariantResult.pass_()


def dependency_plan_before_route_or_work(state: State, trace) -> InvariantResult:
    del trace
    route_version_exists = state.route_version > 0
    formal_route_or_work_started = (
        state.route_checked
        or state.markdown_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.visible_user_flow_diagram_emitted
        or state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
        or state.final_report_emitted
    )
    formal_execution_started = (
        state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
        or state.final_report_emitted
    )
    if route_version_exists and not (
        _crew_ready(state)
        and state.pm_initial_route_decision_recorded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and _continuation_lifecycle_valid(state)
    ):
        return InvariantResult.fail(
            "route version created before six-agent crew, PM route decision, product-function architecture, frozen contract, dependency plan, and host continuation decision"
        )
    if formal_route_or_work_started and not (
        state.flowguard_process_design_done
        and state.child_skill_manifest_pm_approved_for_route
        and state.candidate_route_tree_generated
        and state.root_route_model_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
    ):
        return InvariantResult.fail(
            "formal route or work started before candidate tree plus root process/product/strict-review model checks"
        )
    if formal_execution_started and not state.startup_activation_guard_passed:
        return InvariantResult.fail(
            "formal execution started before the startup activation hard gate passed"
        )
    if state.startup_activation_guard_passed and not _live_subagent_startup_resolved(state):
        return InvariantResult.fail(
            "startup activation hard gate passed before live subagents or explicit single-agent fallback were resolved"
        )
    return InvariantResult.pass_()


def continuation_control_loop_until_terminal(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and not state.heartbeat_health_checked:
        return InvariantResult.fail("formal chunk started before continuation readiness check")
    if state.status == "running" and not state.heartbeat_active:
        return InvariantResult.fail("FlowPilot control loop inactive while task is running")
    if state.status in {"blocked", "complete"} and state.heartbeat_active:
        return InvariantResult.fail("FlowPilot control loop still active after terminal state")
    return InvariantResult.pass_()


def controlled_stop_notice_required(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "blocked" and not state.controlled_stop_notice_recorded:
        return InvariantResult.fail(
            "controlled nonterminal stop reached blocked state without a resume notice"
        )
    if state.status == "complete" and not state.terminal_completion_notice_recorded:
        return InvariantResult.fail(
            "terminal completion reached complete state without a completion notice"
        )
    if state.controlled_stop_notice_recorded and state.status == "complete":
        return InvariantResult.fail(
            "nonterminal resume notice was recorded on a completed route"
        )
    return InvariantResult.pass_()


def formal_chunk_requires_checked_route_and_verification(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if not state.contract_frozen:
            return InvariantResult.fail("chunk started before contract was frozen")
        if not state.route_checked:
            return InvariantResult.fail("chunk started before route model checks")
        if not state.strict_gate_obligation_review_model_checked:
            return InvariantResult.fail("chunk started before strict gate-obligation review model checks")
        if not state.markdown_synced:
            return InvariantResult.fail("chunk started before Markdown sync")
        if not (
            state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.route_version
            and state.plan_version == state.frontier_version
        ):
            return InvariantResult.fail("chunk started before execution frontier and Codex plan were synced")
        if not state.visible_user_flow_diagram_emitted:
            return InvariantResult.fail("chunk started before visible user flow diagram was emitted")
        if not _continuation_ready(state):
            return InvariantResult.fail("chunk started before host continuation capability was probed and recorded")
        if not (
            state.heartbeat_loaded_state
            and state.heartbeat_loaded_frontier
            and state.heartbeat_loaded_crew_memory
            and state.heartbeat_restored_crew
            and state.heartbeat_rehydrated_crew
            and state.replacement_roles_seeded_from_memory
            and state.heartbeat_pm_decision_requested
            and state.pm_resume_decision_recorded
            and state.pm_completion_runway_recorded
            and state.pm_runway_hard_stops_recorded
            and state.pm_runway_checkpoint_cadence_recorded
            and state.pm_runway_synced_to_plan
            and state.plan_sync_method_recorded
            and state.visible_plan_has_runway_depth
            and state.pm_node_decision_recorded
        ):
            return InvariantResult.fail(
                "chunk started before heartbeat rehydrated the crew from role memory and PM completion runway was synced into a sufficiently deep visible plan"
            )
        if state.chunk_state in {"ready", "executed"} and not state.verification_defined:
            return InvariantResult.fail("chunk started without chunk-level verification")
        if state.chunk_state == "checkpoint_pending" and not state.anti_rough_finish_done:
            return InvariantResult.fail("chunk reached checkpoint path before anti-rough-finish review")
        if not state.node_visible_roadmap_emitted:
            return InvariantResult.fail("chunk started before visible node roadmap")
        if not state.unfinished_current_node_recovery_checked:
            return InvariantResult.fail("chunk started before unfinished-current-node recovery check")
        if not state.parent_focused_interrogation_done:
            return InvariantResult.fail("chunk started before focused parent-scope grill-me")
        if not _focused_interrogation_ready(
            total_questions=state.parent_focused_interrogation_questions,
            scope_id=state.parent_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before parent focused grill-me had 20-50 questions and a scope id"
            )
        if not state.parent_subtree_review_checked:
            return InvariantResult.fail("chunk started before parent-subtree FlowGuard review")
        if not state.parent_product_function_model_checked:
            return InvariantResult.fail("chunk started before parent product-function model check")
        if not state.node_focused_interrogation_done:
            return InvariantResult.fail("chunk started before focused node-level grill-me")
        if not _focused_interrogation_ready(
            total_questions=state.node_focused_interrogation_questions,
            scope_id=state.node_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before node focused grill-me had 20-50 questions and a scope id"
            )
        if not state.node_product_function_model_checked:
            return InvariantResult.fail("chunk started before active node product-function model check")
        if not state.lightweight_self_check_done:
            return InvariantResult.fail("chunk started before lightweight heartbeat self-check")
        if not _lightweight_self_check_ready(
            total_questions=state.lightweight_self_check_questions,
            scope_id=state.lightweight_self_check_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before lightweight self-check had 5-10 questions and a scope id"
            )
        if not (
            state.quality_package_done
            and state.quality_candidate_registry_checked
            and state.quality_raise_decision_recorded
            and state.validation_matrix_defined
        ):
            return InvariantResult.fail(
                "chunk started before quality package recorded thinness, raise decision, child-skill visibility, and validation matrix"
            )
    if state.chunk_state == "checkpoint_pending" and not (
        state.node_human_review_context_loaded
        and state.node_human_neutral_observation_written
        and state.node_human_manual_experiments_run
        and state.node_human_inspection_passed
    ):
        return InvariantResult.fail(
            "checkpoint path reached before human-like node inspection context, neutral observation, experiments, and pass decision"
        )
    return InvariantResult.pass_()


def no_work_while_issue_or_gate_open(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and state.issue != "none":
        return InvariantResult.fail("formal chunk active while issue branch is open")
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and state.high_risk_gate == "pending":
        return InvariantResult.fail("formal chunk active while high-risk gate is pending")
    return InvariantResult.pass_()


def human_review_judgement_requires_neutral_observation(state: State, trace) -> InvariantResult:
    del trace
    if state.node_human_inspection_passed and not state.node_human_neutral_observation_written:
        return InvariantResult.fail("node human-like judgement passed without neutral observation")
    if state.composite_backward_human_review_passed and not state.composite_backward_neutral_observation_written:
        return InvariantResult.fail("composite backward judgement passed without neutral observation")
    if state.final_human_inspection_passed and not state.final_human_neutral_observation_written:
        return InvariantResult.fail("final human-like judgement passed without neutral observation")
    return InvariantResult.pass_()


def subagent_must_merge_before_completion(state: State, trace) -> InvariantResult:
    del trace
    if state.final_report_emitted and state.subagent_status in {"pending", "returned"}:
        return InvariantResult.fail("completed while subagent work was not merged")
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if state.subagent_status in {"pending", "returned"}:
            return InvariantResult.fail("formal chunk active while sidecar work was not merged")
    if state.subagent_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("subagent used before child-node sidecar scan")
    if state.subagent_status == "pending" and not state.subagent_scope_checked:
        return InvariantResult.fail("sidecar subagent assigned before bounded/disjoint scope check")
    if state.subagent_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("subagent assigned without a bounded sidecar need")
    return InvariantResult.pass_()


def route_updates_force_recheck_and_resync(state: State, trace) -> InvariantResult:
    del trace
    if state.visible_user_flow_diagram_emitted and not state.user_flow_diagram_refreshed:
        return InvariantResult.fail(
            "visible user flow diagram emitted before refreshing the current user flow diagram"
        )
    if (
        state.human_inspection_repairs + state.composite_structural_route_repairs
        > state.pm_repair_decision_interrogations
    ):
        return InvariantResult.fail(
            "review-driven route repair written before PM repair strategy interrogation"
        )
    if state.route_version > 0 and state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if not (
            state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.route_version
            and state.plan_version == state.frontier_version
            and state.user_flow_diagram_refreshed
            and state.visible_user_flow_diagram_emitted
        ):
            return InvariantResult.fail("route update was not checked, summarized, frontier-synced, plan-synced, and visibly mapped before work")
    return InvariantResult.pass_()


def stable_heartbeat_prompt_not_route_state(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.route_version > 1
        and state.host_continuation_supported
        and not state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail("route changed without a stable heartbeat launcher that reads persisted state")
    if (
        state.route_version > 1
        and state.manual_resume_mode_recorded
        and state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail("manual-resume route unexpectedly created a stable heartbeat launcher")
    return InvariantResult.pass_()


def external_watchdog_policy_is_lifecycle_state(state: State, trace) -> InvariantResult:
    del trace
    automation_bits = (
        state.heartbeat_schedule_created
        or state.stable_heartbeat_launcher_recorded
        or state.external_watchdog_policy_recorded
        or state.external_watchdog_busy_lease_policy_recorded
        or state.external_watchdog_automation_created
        or state.external_watchdog_hidden_noninteractive_configured
        or state.external_watchdog_active
        or state.global_watchdog_supervisor_checked
        or state.global_watchdog_supervisor_singleton_ready
        or state.global_watchdog_supervisor_cadence_minutes != 0
    )
    if state.manual_resume_mode_recorded and automation_bits:
        return InvariantResult.fail(
            "manual-resume mode recorded but heartbeat/watchdog/global-supervisor automation state was still created"
        )
    formal_started = (
        state.route_checked
        or state.chunk_state != "none"
        or state.final_report_emitted
    )
    if formal_started and state.host_continuation_supported and (
        state.heartbeat_schedule_created
        or state.external_watchdog_policy_recorded
        or state.external_watchdog_automation_created
        or state.global_watchdog_supervisor_checked
    ) and not _continuation_lifecycle_valid(state):
        return InvariantResult.fail(
            "host continuation support produced a partial heartbeat/watchdog/global-supervisor setup"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lost its lifecycle policy gate; ordinary node progress must not re-enter watchdog setup"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_busy_lease_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks busy-lease suppression policy; long active work can be misread as a stale heartbeat"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_busy_lease_autowrap_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks automatic busy-lease wrapper policy for long commands and waits"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_source_drift_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks source-status drift policy and could trust stale or unsupported sources"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_hidden_noninteractive_configured
    ):
        return InvariantResult.fail(
            "active external watchdog automation is not configured for hidden/noninteractive execution"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not (
            state.global_watchdog_supervisor_checked
            and state.global_watchdog_supervisor_singleton_ready
            and state.global_watchdog_supervisor_cadence_minutes == 30
        )
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks verified singleton Codex global supervisor at fixed 30-minute cadence"
        )
    return InvariantResult.pass_()


def material_handoff_before_pm_route_design(state: State, trace) -> InvariantResult:
    del trace
    if state.material_intake_packet_written and not (
        state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
    ):
        return InvariantResult.fail(
            "Material Intake Packet was written before sources were scanned, summarized, and quality-classified"
        )
    if state.material_reviewer_sufficiency_approved and not (
        state.material_intake_packet_written
        and state.material_reviewer_sufficiency_checked
    ):
        return InvariantResult.fail(
            "material packet was approved before reviewer sufficiency check"
        )
    if state.pm_material_understanding_memo_written and not (
        state.material_reviewer_sufficiency_approved
    ):
        return InvariantResult.fail(
            "PM material understanding memo was written before reviewer-approved intake evidence"
        )
    if state.pm_material_discovery_decision_recorded and not (
        state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
    ):
        return InvariantResult.fail(
            "PM material discovery decision was recorded before understanding memo and complexity classification"
        )
    if state.pm_initial_route_decision_recorded and not _material_handoff_ready(state):
        return InvariantResult.fail(
            "PM route decision was recorded before reviewed material handoff"
        )
    return InvariantResult.pass_()


def actor_authority_gates_require_correct_role(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.startup_self_interrogation_pm_ratified and not _crew_ready(state):
        return InvariantResult.fail(
            "startup self-interrogation was ratified before the six-agent crew was ready"
        )
    if state.product_function_architecture_pm_synthesized and not (
        _crew_ready(state) and _material_handoff_ready(state)
    ):
        return InvariantResult.fail(
            "PM product-function architecture was synthesized before crew recovery and reviewed material handoff"
        )
    product_architecture_inputs_ready = (
        state.product_function_architecture_pm_synthesized
        and state.product_function_user_task_map_written
        and state.product_function_capability_map_written
        and state.product_function_feature_decisions_written
        and state.product_function_display_rationale_written
        and state.product_function_gap_review_done
        and state.product_function_negative_scope_written
        and state.product_function_acceptance_matrix_written
    )
    if (
        state.product_function_architecture_product_officer_approved
        and not product_architecture_inputs_ready
    ):
        return InvariantResult.fail(
            "product-function architecture approval was recorded before all PM product artifacts existed"
        )
    if state.product_function_architecture_reviewer_challenged and not (
        state.product_function_architecture_product_officer_approved
        and state.reviewer_ready
    ):
        return InvariantResult.fail(
            "human-like reviewer challenged the product-function architecture before product officer approval or reviewer recovery"
        )
    if state.flowguard_process_design_done and not (
        state.startup_self_interrogation_pm_ratified
        and _product_function_architecture_ready(state)
        and state.contract_frozen
    ):
        return InvariantResult.fail(
            "FlowGuard route design started before PM ratified startup self-interrogation, product-function architecture, and contract freeze"
        )
    if state.flowguard_process_design_done and not state.child_skill_manifest_pm_approved_for_route:
        return InvariantResult.fail(
            "FlowGuard route design started before the PM-approved child-skill gate manifest was ready"
        )
    if state.child_skill_manifest_pm_approved_for_route and not (
        state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
    ):
        return InvariantResult.fail(
            "PM approved child-skill gate manifest before discovery, extraction, approver assignment, and reviewer/officer approvals"
        )
    if state.root_route_model_process_officer_approved and not state.root_route_model_checked:
        return InvariantResult.fail("root route approval is stale without a root route model check")
    if state.root_route_model_checked and not state.root_route_model_process_officer_approved:
        return InvariantResult.fail("root route model check lacks process FlowGuard officer approval")
    if (
        state.root_product_function_model_product_officer_approved
        and not state.root_product_function_model_checked
    ):
        return InvariantResult.fail(
            "root product-function approval is stale without a root product-function model check"
        )
    if (
        state.root_product_function_model_checked
        and not state.root_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "root product-function model check lacks product FlowGuard officer approval"
        )
    if (
        state.parent_product_function_model_product_officer_approved
        and not state.parent_product_function_model_checked
    ):
        return InvariantResult.fail(
            "parent product-function approval is stale without a parent product-function model check"
        )
    if (
        state.parent_product_function_model_checked
        and not state.parent_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "parent product-function model check lacks product FlowGuard officer approval"
        )
    if (
        state.node_product_function_model_product_officer_approved
        and not state.node_product_function_model_checked
    ):
        return InvariantResult.fail(
            "node product-function approval is stale without a node product-function model check"
        )
    if (
        state.node_product_function_model_checked
        and not state.node_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "node product-function model check lacks product FlowGuard officer approval"
        )
    if state.node_human_review_reviewer_approved and not state.node_human_inspection_passed:
        return InvariantResult.fail("node reviewer approval is stale without a node human review pass")
    if state.node_human_inspection_passed and not state.node_human_review_reviewer_approved:
        return InvariantResult.fail("node human review pass lacks reviewer approval")
    if (
        state.composite_backward_review_reviewer_approved
        and not state.composite_backward_human_review_passed
    ):
        return InvariantResult.fail(
            "composite reviewer approval is stale without a composite backward review pass"
        )
    if (
        state.composite_backward_human_review_passed
        and not state.composite_backward_review_reviewer_approved
    ):
        return InvariantResult.fail(
            "composite backward review pass lacks reviewer approval"
        )
    if (
        state.final_product_function_model_product_officer_approved
        and not state.final_product_function_model_replayed
    ):
        return InvariantResult.fail(
            "final product-function approval is stale without final product replay"
        )
    if (
        state.final_product_function_model_replayed
        and not state.final_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "final product-function replay lacks product FlowGuard officer approval"
        )
    if state.final_human_review_reviewer_approved and not state.final_human_inspection_passed:
        return InvariantResult.fail("final reviewer approval is stale without final human review pass")
    if state.final_human_inspection_passed and not state.final_human_review_reviewer_approved:
        return InvariantResult.fail("final human review pass lacks reviewer approval")
    if state.final_route_wide_gate_ledger_pm_built and not (
        state.final_route_wide_gate_ledger_current_route_scanned
        and state.final_route_wide_gate_ledger_effective_nodes_resolved
        and state.final_route_wide_gate_ledger_child_skill_gates_collected
        and state.final_route_wide_gate_ledger_human_review_gates_collected
        and state.final_route_wide_gate_ledger_product_process_gates_collected
        and state.final_route_wide_gate_ledger_resource_lineage_resolved
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM built final route-wide gate ledger before current route scan, gate collection, generated-resource lineage, stale-evidence check, superseded explanations, and zero unresolved count"
        )
    if state.final_route_wide_gate_ledger_reviewer_backward_checked and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "final route-wide gate ledger reviewer replay ran before PM-built clean ledger"
        )
    if state.final_route_wide_gate_ledger_pm_completion_approved and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM approved final route-wide gate ledger before reviewer replay and zero unresolved count"
        )
    if state.pm_completion_decision_recorded and not state.final_route_wide_gate_ledger_pm_completion_approved:
        return InvariantResult.fail(
            "PM completion decision recorded before final route-wide gate ledger approval"
        )
    if state.pm_completion_decision_recorded and not state.crew_archived:
        return InvariantResult.fail("PM completion decision recorded before crew archive")
    if state.final_report_emitted and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("final report emitted before PM completion approval")
    return InvariantResult.pass_()


def crew_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.startup_self_interrogation_pm_ratified and not (
        state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
    ):
        return InvariantResult.fail("startup was ratified before all role memory packets were written")
    if state.heartbeat_pm_decision_requested and not (
        state.heartbeat_loaded_state
        and state.heartbeat_loaded_frontier
        and state.heartbeat_loaded_crew_memory
        and state.heartbeat_restored_crew
        and state.heartbeat_rehydrated_crew
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "PM resume was requested before six-role memory rehydration completed"
        )
    if state.checkpoint_written and state.completed_chunks > 0 and not state.role_memory_refreshed_after_work:
        return InvariantResult.fail("checkpoint written before role memory refresh after meaningful role work")
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew ledger archived before role memory archive")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_completion_before_verified_contract",
        description="Final report requires frozen contract, checked route, synced summary, verified chunks, and checkpoint.",
        predicate=no_completion_before_verified_contract,
    ),
    Invariant(
        name="frozen_contract_never_changes",
        description="Autopilot may update routes and models, but not the frozen acceptance contract.",
        predicate=frozen_contract_never_changes,
    ),
    Invariant(
        name="mode_choice_before_contract",
        description="FlowPilot is enabled by default and offers a run-mode choice before contract freeze.",
        predicate=mode_choice_before_contract,
    ),
    Invariant(
        name="startup_banner_before_mode_choice",
        description="FlowPilot emits a visible startup banner before mode selection or other heavy startup work.",
        predicate=startup_banner_before_mode_choice,
    ),
    Invariant(
        name="dependency_plan_before_route_or_work",
        description="Route creation and formal work require demand-driven dependency planning first.",
        predicate=dependency_plan_before_route_or_work,
    ),
    Invariant(
        name="continuation_control_loop_until_terminal",
        description="FlowPilot keeps a control loop active while running; real heartbeat health is required only when automated continuation is supported.",
        predicate=continuation_control_loop_until_terminal,
    ),
    Invariant(
        name="controlled_stop_notice_required",
        description="Controlled nonterminal stops emit a manual/heartbeat resume notice, and terminal completion emits a completion notice.",
        predicate=controlled_stop_notice_required,
    ),
    Invariant(
        name="formal_chunk_requires_checked_route_and_verification",
        description="Formal execution chunks require a checked route, synced summary, and predeclared verification.",
        predicate=formal_chunk_requires_checked_route_and_verification,
    ),
    Invariant(
        name="no_work_while_issue_or_gate_open",
        description="Open issues and hard safety gates block formal chunk execution.",
        predicate=no_work_while_issue_or_gate_open,
    ),
    Invariant(
        name="human_review_judgement_requires_neutral_observation",
        description="Human-like review records what was observed before pass/fail judgement.",
        predicate=human_review_judgement_requires_neutral_observation,
    ),
    Invariant(
        name="subagent_must_merge_before_completion",
        description="Optional subagent results must return to the main agent before completion.",
        predicate=subagent_must_merge_before_completion,
    ),
    Invariant(
        name="route_updates_force_recheck_and_resync",
        description="A changed route must be FlowGuard-checked and summarized before more work.",
        predicate=route_updates_force_recheck_and_resync,
    ),
    Invariant(
        name="stable_heartbeat_prompt_not_route_state",
        description="Heartbeat automation stays a stable launcher while persisted route/frontier state carries next-jump changes.",
        predicate=stable_heartbeat_prompt_not_route_state,
    ),
    Invariant(
        name="external_watchdog_policy_is_lifecycle_state",
        description="External watchdog policy is established with the paired automation lifecycle and is not reset at ordinary checkpoints or node transitions.",
        predicate=external_watchdog_policy_is_lifecycle_state,
    ),
    Invariant(
        name="material_handoff_before_pm_route_design",
        description="Material intake, reviewer sufficiency, and PM understanding happen before PM route design.",
        predicate=material_handoff_before_pm_route_design,
    ),
    Invariant(
        name="actor_authority_gates_require_correct_role",
        description="Authority-sensitive gates require the PM, reviewer, or matching FlowGuard officer and reject stale approvals.",
        predicate=actor_authority_gates_require_correct_role,
    ),
    Invariant(
        name="crew_memory_rehydration_required",
        description="Six-role recovery uses persisted role memory before PM runway, checkpoint, or terminal archive.",
        predicate=crew_memory_rehydration_required,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 120


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((AutopilotStep(),), name="flowguard_project_autopilot_meta")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple(
        (result.label, result.new_state)
        for result in AutopilotStep().apply(Tick(), state)
    )


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "initial_state",
    "is_success",
    "is_terminal",
    "next_states",
    "terminal_predicate",
]
