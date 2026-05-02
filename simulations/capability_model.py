"""FlowGuard model for flowpilot capability routing.

This model checks the planned skill-composition layer for FlowPilot. FlowPilot
starts only at showcase-grade scope, exposes its grill-me style
self-interrogation, creates heartbeat continuity, uses FlowGuard as process
designer before routing capabilities, and refuses completion while obvious
high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


CREW_SIZE = 6
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
# State-space bound for exploring repeat UI loop branches. This is not a
# runtime limit; the child UI skill owns the actual iteration standard.
MAX_UI_VISUAL_ITERATIONS = 2
MIN_FULL_GRILLME_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_GRILLME_QUESTIONS = 20
MAX_FOCUSED_GRILLME_QUESTIONS = 50
DEFAULT_FOCUSED_GRILLME_QUESTIONS = 30
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
    """One capability-routing decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    task_kind: str = "unknown"  # unknown | backend | ui
    flowpilot_enabled: bool = False
    mode_choice_offered: bool = False
    mode_selected: bool = False
    showcase_floor_committed: bool = False
    self_interrogation_done: bool = False
    self_interrogation_evidence: bool = False
    visible_self_interrogation_done: bool = False
    self_interrogation_questions: int = 0
    self_interrogation_layer_count: int = 0
    self_interrogation_questions_per_layer: int = 0
    self_interrogation_layers: int = 0
    self_interrogation_pm_ratified: bool = False
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
    contract_frozen: bool = False
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
    crew_memory_policy_written: bool = False
    crew_memory_packets_written: int = 0
    pm_initial_capability_decision_recorded: bool = False
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
    pm_capability_work_decision_recorded: bool = False
    crew_archived: bool = False
    crew_memory_archived: bool = False
    continuation_probe_done: bool = False
    host_continuation_supported: bool = False
    manual_resume_mode_recorded: bool = False

    capabilities_manifest_written: bool = False
    child_skill_route_design_discovery_started: bool = False
    child_skill_initial_gate_manifest_extracted: bool = False
    child_skill_gate_approvers_assigned: bool = False
    child_skill_manifest_reviewer_reviewed: bool = False
    child_skill_manifest_process_officer_approved: bool = False
    child_skill_manifest_product_officer_approved: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    child_skill_focused_interrogation_done: bool = False
    child_skill_focused_interrogation_questions: int = 0
    child_skill_focused_interrogation_scope_id: str = ""
    child_skill_contracts_loaded: bool = False
    child_skill_exact_source_verified: bool = False
    child_skill_substitutes_rejected: bool = False
    flowpilot_invocation_policy_mapped: bool = False
    child_skill_requirements_mapped: bool = False
    child_skill_evidence_plan_written: bool = False
    child_skill_subroute_projected: bool = False
    child_skill_node_gate_manifest_refined: bool = False
    child_skill_gate_authority_records_written: bool = False
    child_skill_conformance_model_checked: bool = False
    child_skill_conformance_model_process_officer_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
    child_skill_execution_evidence_audited: bool = False
    child_skill_evidence_matches_outputs: bool = False
    child_skill_domain_quality_checked: bool = False
    child_skill_iteration_loop_closed: bool = False
    child_skill_current_gates_role_approved: bool = False
    child_skill_completion_verified: bool = False
    dependency_plan_recorded: bool = False
    future_installs_deferred: bool = False
    flowguard_dependency_checked: bool = False
    heartbeat_schedule_created: bool = False
    stable_heartbeat_launcher_recorded: bool = False
    heartbeat_health_checked: bool = False
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
    global_watchdog_supervisor_conversation_quiet: bool = False
    external_watchdog_stopped_before_heartbeat: bool = False
    terminal_lifecycle_frontier_written: bool = False
    lifecycle_reconciliation_done: bool = False
    flowguard_process_design_done: bool = False
    meta_route_checked: bool = False
    meta_route_process_officer_approved: bool = False
    capability_route_process_officer_approved: bool = False
    capability_product_function_model_checked: bool = False
    capability_product_function_model_product_officer_approved: bool = False

    ui_inspected: bool = False
    ui_concept_done: bool = False
    ui_concept_target_ready: bool = False
    ui_concept_target_visible: bool = False
    ui_concept_aesthetic_review_done: bool = False
    ui_concept_aesthetic_reasons_recorded: bool = False
    ui_frontend_design_plan_done: bool = False
    visual_asset_scope: str = "unknown"  # unknown | none | required
    visual_asset_style_review_done: bool = False
    visual_asset_aesthetic_review_done: bool = False
    visual_asset_aesthetic_reasons_recorded: bool = False
    ui_implemented: bool = False
    ui_screenshot_qa_done: bool = False
    ui_implementation_aesthetic_review_done: bool = False
    ui_implementation_aesthetic_reasons_recorded: bool = False
    ui_divergence_review_done: bool = False
    ui_visual_iteration_loop_closed: bool = False
    ui_visual_iterations: int = 0

    non_ui_implemented: bool = False
    implementation_human_review_context_loaded: bool = False
    implementation_human_neutral_observation_written: bool = False
    implementation_human_manual_experiments_run: bool = False
    implementation_human_inspection_passed: bool = False
    implementation_human_review_reviewer_approved: bool = False
    capability_backward_context_loaded: bool = False
    capability_child_evidence_replayed: bool = False
    capability_backward_neutral_observation_written: bool = False
    capability_structure_decision_recorded: bool = False
    capability_backward_human_review_passed: bool = False
    capability_backward_review_reviewer_approved: bool = False
    capability_backward_issue_grilled: bool = False
    capability_backward_issue_strategy: str = "none"
    pm_repair_decision_interrogations: int = 0
    capability_structural_route_repairs: int = 0
    capability_new_sibling_nodes: int = 0
    capability_subtree_rebuilds: int = 0
    quality_package_done: bool = False
    quality_candidate_registry_checked: bool = False
    quality_raise_decision_recorded: bool = False
    validation_matrix_defined: bool = False
    anti_rough_finish_done: bool = False
    role_memory_refreshed_after_work: bool = False
    quality_route_raises: int = 0
    quality_reworks: int = 0
    final_verification_done: bool = False
    completion_self_interrogation_done: bool = False
    completion_self_interrogation_questions: int = 0
    completion_self_interrogation_layer_count: int = 0
    completion_self_interrogation_questions_per_layer: int = 0
    completion_self_interrogation_layers: int = 0
    completion_visible_route_map_emitted: bool = False
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
    final_route_wide_gate_ledger_stale_evidence_checked: bool = False
    final_route_wide_gate_ledger_superseded_nodes_explained: bool = False
    final_route_wide_gate_ledger_unresolved_count_zero: bool = False
    final_route_wide_gate_ledger_pm_built: bool = False
    final_route_wide_gate_ledger_reviewer_backward_checked: bool = False
    final_route_wide_gate_ledger_pm_completion_approved: bool = False
    high_value_work_review: str = "unknown"  # unknown | exhausted
    standard_expansions: int = 0
    pm_completion_decision_recorded: bool = False

    child_node_sidecar_scan_done: bool = False
    sidecar_need: str = "unknown"  # unknown | none | needed
    subagent_pool_exists: bool = False
    subagent_idle_available: bool = False
    subagent_status: str = "none"  # none | idle | pending | returned | merged
    subagent_scope_checked: bool = False
    critical_path_blocked: bool = False

    capability_route_version: int = 0
    capability_route_checked: bool = False
    capability_evidence_synced: bool = False
    execution_frontier_written: bool = False
    codex_plan_synced: bool = False
    frontier_version: int = 0
    plan_version: int = 0
    capability_route_mermaid_diagram_refreshed: bool = False
    capability_route_map_emitted: bool = False


def _step(state: State, *, label: str, action: str, **changes) -> FunctionResult:
    return FunctionResult(
        output=Action(action),
        new_state=replace(state, **changes),
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


def _reset_human_inspection_gates() -> dict[str, object]:
    gates = {
        "implementation_human_review_context_loaded": False,
        "implementation_human_neutral_observation_written": False,
        "implementation_human_manual_experiments_run": False,
        "implementation_human_inspection_passed": False,
        "implementation_human_review_reviewer_approved": False,
        "capability_backward_context_loaded": False,
        "capability_child_evidence_replayed": False,
        "capability_backward_neutral_observation_written": False,
        "capability_structure_decision_recorded": False,
        "capability_backward_human_review_passed": False,
        "capability_backward_review_reviewer_approved": False,
        "capability_backward_issue_grilled": False,
        "capability_backward_issue_strategy": "none",
        "final_product_function_model_replayed": False,
        "final_product_function_model_product_officer_approved": False,
        "final_human_review_context_loaded": False,
        "final_human_neutral_observation_written": False,
        "final_human_manual_experiments_run": False,
        "final_human_inspection_passed": False,
        "final_human_review_reviewer_approved": False,
        "pm_completion_decision_recorded": False,
    }
    gates.update(_reset_final_route_wide_gate_ledger())
    return gates


def _reset_final_route_wide_gate_ledger() -> dict[str, object]:
    return {
        "final_route_wide_gate_ledger_current_route_scanned": False,
        "final_route_wide_gate_ledger_effective_nodes_resolved": False,
        "final_route_wide_gate_ledger_child_skill_gates_collected": False,
        "final_route_wide_gate_ledger_human_review_gates_collected": False,
        "final_route_wide_gate_ledger_product_process_gates_collected": False,
        "final_route_wide_gate_ledger_stale_evidence_checked": False,
        "final_route_wide_gate_ledger_superseded_nodes_explained": False,
        "final_route_wide_gate_ledger_unresolved_count_zero": False,
        "final_route_wide_gate_ledger_pm_built": False,
        "final_route_wide_gate_ledger_reviewer_backward_checked": False,
        "final_route_wide_gate_ledger_pm_completion_approved": False,
    }


def _reset_execution_quality_gates() -> dict[str, object]:
    gates = _reset_quality_gates()
    gates.update(_reset_human_inspection_gates())
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
            "pm_capability_work_decision_recorded": False,
            "child_skill_node_gate_manifest_refined": False,
            "child_skill_gate_authority_records_written": False,
            "child_skill_current_gates_role_approved": False,
            "child_node_sidecar_scan_done": False,
            "sidecar_need": "unknown",
            "subagent_scope_checked": False,
            "role_memory_refreshed_after_work": False,
            "critical_path_blocked": False,
        }
    )
    return gates


def _capability_structural_repair_changes(state: State) -> dict[str, object]:
    return {
        "capability_route_version": state.capability_route_version + 1,
        "capability_route_checked": False,
        "capability_route_process_officer_approved": False,
        "capability_product_function_model_checked": False,
        "capability_product_function_model_product_officer_approved": False,
        "capability_evidence_synced": False,
        "execution_frontier_written": False,
        "codex_plan_synced": False,
        "frontier_version": 0,
        "plan_version": 0,
        "capability_route_mermaid_diagram_refreshed": False,
        "capability_route_map_emitted": False,
        "heartbeat_health_checked": False,
        "final_verification_done": False,
        "child_skill_route_design_discovery_started": False,
        "child_skill_initial_gate_manifest_extracted": False,
        "child_skill_gate_approvers_assigned": False,
        "child_skill_manifest_reviewer_reviewed": False,
        "child_skill_manifest_process_officer_approved": False,
        "child_skill_manifest_product_officer_approved": False,
        "child_skill_manifest_pm_approved_for_route": False,
        "child_skill_contracts_loaded": False,
        "child_skill_focused_interrogation_done": False,
        "child_skill_focused_interrogation_questions": 0,
        "child_skill_focused_interrogation_scope_id": "",
        "child_skill_exact_source_verified": False,
        "child_skill_substitutes_rejected": False,
        "flowpilot_invocation_policy_mapped": False,
        "child_skill_requirements_mapped": False,
        "child_skill_evidence_plan_written": False,
        "child_skill_subroute_projected": False,
        "non_ui_implemented": False,
        "ui_concept_target_ready": False,
        "ui_concept_target_visible": False,
        "ui_frontend_design_plan_done": False,
        "visual_asset_scope": "unknown",
        "visual_asset_style_review_done": False,
        "ui_implemented": False,
        "ui_screenshot_qa_done": False,
        "ui_implementation_aesthetic_review_done": False,
        "ui_implementation_aesthetic_reasons_recorded": False,
        "ui_divergence_review_done": False,
        "ui_visual_iteration_loop_closed": False,
        "ui_concept_aesthetic_review_done": False,
        "ui_concept_aesthetic_reasons_recorded": False,
        "visual_asset_aesthetic_review_done": False,
        "visual_asset_aesthetic_reasons_recorded": False,
        "child_skill_completion_verified": False,
        "child_skill_conformance_model_checked": False,
        "child_skill_conformance_model_process_officer_approved": False,
        "strict_gate_obligation_review_model_checked": False,
        "child_skill_execution_evidence_audited": False,
        "child_skill_evidence_matches_outputs": False,
        "child_skill_domain_quality_checked": False,
        "child_skill_iteration_loop_closed": False,
        "flowguard_dependency_checked": False,
        "dependency_plan_recorded": False,
        "future_installs_deferred": False,
        "flowguard_process_design_done": False,
        "meta_route_checked": False,
        "meta_route_process_officer_approved": False,
        "subagent_status": "none",
        "capability_structural_route_repairs": state.capability_structural_route_repairs + 1,
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
        state.self_interrogation_pm_ratified
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
        and state.global_watchdog_supervisor_cadence_minutes == 10
        and state.global_watchdog_supervisor_conversation_quiet
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
        and not state.global_watchdog_supervisor_conversation_quiet
    )


def _continuation_ready(state: State) -> bool:
    return _automated_continuation_ready(state) or _manual_resume_ready(state)


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
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_route_wide_gate_ledger_pm_completion_approved
    )


def _base_ready(state: State) -> bool:
    return (
        state.status == "running"
        and _gates_ready(state)
    )


def _route_scaffold_ready(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and state.mode_choice_offered
        and state.mode_selected
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_ready(state)
        and state.flowguard_process_design_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_route_mermaid_diagram_refreshed
        and state.capability_route_map_emitted
    )


def _route_scaffold_lifecycle_valid(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and state.mode_choice_offered
        and state.mode_selected
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_route_mermaid_diagram_refreshed
        and state.capability_route_map_emitted
    )


def _route_scaffold_lifecycle_valid(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and state.mode_choice_offered
        and state.mode_selected
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_route_mermaid_diagram_refreshed
        and state.capability_route_map_emitted
    )


def _gates_ready(state: State) -> bool:
    return _route_scaffold_ready(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _subagent_clear(state: State) -> bool:
    return state.subagent_status in {"none", "idle", "merged"}


def _capability_backward_review_steps(
    state: State, *, domain: str
) -> Iterable[FunctionResult]:
    if not state.capability_backward_context_loaded:
        yield _step(
            state,
            label="capability_backward_context_loaded",
            action=f"load {domain} child-skill evidence, parent node goal, product model, and route structure before capability closure",
            capability_backward_context_loaded=True,
        )
        return
    if not state.capability_child_evidence_replayed:
        yield _step(
            state,
            label="capability_child_evidence_replayed",
            action=f"replay {domain} child-skill evidence backward against the parent capability goal",
            capability_child_evidence_replayed=True,
        )
        return
    if not state.capability_backward_neutral_observation_written:
        yield _step(
            state,
            label="capability_backward_neutral_observation_written",
            action=f"write a neutral observation of what the {domain} child-skill rollup actually shows before judging capability closure",
            capability_backward_neutral_observation_written=True,
        )
        return
    if not state.capability_structure_decision_recorded:
        yield _step(
            state,
            label="capability_structure_decision_recorded",
            action=f"classify whether the {domain} capability can close, needs an existing child node rework, needs a sibling node, or needs subtree rebuild",
            capability_structure_decision_recorded=True,
        )
        return
    if not state.capability_backward_human_review_passed:
        if (
            state.capability_structural_route_repairs == 0
            and state.capability_backward_issue_strategy == "none"
        ):
            yield _step(
                state,
                label="capability_backward_review_found_existing_child_gap",
                action=f"{domain} composite reviewer rejects closure and targets an existing child node for rework",
                capability_backward_issue_strategy="existing_child",
            )
            yield _step(
                state,
                label="capability_backward_review_found_missing_sibling",
                action=f"{domain} composite reviewer rejects closure because an adjacent sibling child node is missing",
                capability_backward_issue_strategy="add_sibling",
            )
            yield _step(
                state,
                label="capability_backward_review_found_subtree_mismatch",
                action=f"{domain} composite reviewer rejects closure and requires child subtree rebuild",
                capability_backward_issue_strategy="rebuild_subtree",
            )
            return
        yield _step(
            state,
            label="capability_backward_review_passed",
            action=f"human-like backward reviewer accepts the {domain} capability rollup before child-skill completion closure",
            capability_backward_human_review_passed=True,
            capability_backward_review_reviewer_approved=True,
        )


def _final_route_wide_gate_ledger_steps(
    state: State, *, domain: str
) -> Iterable[FunctionResult]:
    if not state.final_route_wide_gate_ledger_current_route_scanned:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_current_route_scanned",
            action=f"PM scans the current {domain} route, execution frontier, and mutation history for final gate ledger replay",
            final_route_wide_gate_ledger_current_route_scanned=True,
        )
        return
    if not state.final_route_wide_gate_ledger_effective_nodes_resolved:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_effective_nodes_resolved",
            action=f"PM resolves current, repaired, inserted, waived, and superseded {domain} nodes before final approval",
            final_route_wide_gate_ledger_effective_nodes_resolved=True,
        )
        return
    if not state.final_route_wide_gate_ledger_child_skill_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_child_skill_gates_collected",
            action=f"PM collects every current {domain} child-skill gate, completion standard, evidence path, waiver, blocker, and role approval",
            final_route_wide_gate_ledger_child_skill_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_human_review_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_human_review_gates_collected",
            action=f"PM collects all {domain} human-review, parent-review, strict-obligation, and same-inspector gates",
            final_route_wide_gate_ledger_human_review_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_product_process_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_product_process_gates_collected",
            action=f"PM collects all {domain} product-function and development-process model gates",
            final_route_wide_gate_ledger_product_process_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_stale_evidence_checked:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_stale_evidence_checked",
            action=f"PM checks no stale {domain} evidence is closing a current route obligation",
            final_route_wide_gate_ledger_stale_evidence_checked=True,
        )
        return
    if not state.final_route_wide_gate_ledger_superseded_nodes_explained:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_superseded_nodes_explained",
            action=f"PM explains every superseded {domain} node or gate as replaced, waived, or no longer effective",
            final_route_wide_gate_ledger_superseded_nodes_explained=True,
        )
        return
    if not state.final_route_wide_gate_ledger_unresolved_count_zero:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_unresolved_count_zero",
            action=f"PM records zero unresolved current-route {domain} obligations before final reviewer replay",
            final_route_wide_gate_ledger_unresolved_count_zero=True,
        )
        return
    if not state.final_route_wide_gate_ledger_pm_built:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_pm_built",
            action=f"PM writes the final route-wide {domain} gate ledger from current route state and evidence",
            final_route_wide_gate_ledger_pm_built=True,
        )
        return
    if not state.final_route_wide_gate_ledger_reviewer_backward_checked:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_reviewer_backward_checked",
            action=f"human-like reviewer checks final {domain} output backward through the PM-built route-wide ledger",
            final_route_wide_gate_ledger_reviewer_backward_checked=True,
        )
        return
    if not state.final_route_wide_gate_ledger_pm_completion_approved:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_pm_completion_approved",
            action=f"PM approves the clean route-wide {domain} gate ledger before lifecycle closure and final completion decision",
            final_route_wide_gate_ledger_pm_completion_approved=True,
        )


class CapabilityRouterStep:
    name = "CapabilityRouterStep"
    reads = (
        "status",
        "task_kind",
        "flowpilot_enabled",
        "mode_choice_offered",
        "mode_selected",
        "showcase_floor_committed",
        "self_interrogation_done",
        "self_interrogation_questions",
        "self_interrogation_layer_count",
        "self_interrogation_questions_per_layer",
        "self_interrogation_layers",
        "self_interrogation_pm_ratified",
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
        "visible_self_interrogation_done",
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
        "crew_memory_policy_written",
        "crew_memory_packets_written",
        "pm_initial_capability_decision_recorded",
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
        "pm_capability_work_decision_recorded",
        "crew_archived",
        "crew_memory_archived",
        "continuation_probe_done",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
        "capabilities_manifest_written",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "child_skill_focused_interrogation_done",
        "child_skill_focused_interrogation_questions",
        "child_skill_focused_interrogation_scope_id",
        "child_skill_contracts_loaded",
        "child_skill_exact_source_verified",
        "child_skill_substitutes_rejected",
        "flowpilot_invocation_policy_mapped",
        "child_skill_requirements_mapped",
        "child_skill_evidence_plan_written",
        "child_skill_subroute_projected",
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "child_skill_execution_evidence_audited",
        "child_skill_evidence_matches_outputs",
        "child_skill_domain_quality_checked",
        "child_skill_iteration_loop_closed",
        "child_skill_current_gates_role_approved",
        "child_skill_completion_verified",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "flowguard_dependency_checked",
        "heartbeat_schedule_created",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
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
        "global_watchdog_supervisor_conversation_quiet",
        "external_watchdog_stopped_before_heartbeat",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "flowguard_process_design_done",
        "meta_route_checked",
        "capability_route_checked",
        "meta_route_process_officer_approved",
        "capability_route_process_officer_approved",
        "capability_product_function_model_checked",
        "capability_product_function_model_product_officer_approved",
        "capability_evidence_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "capability_route_mermaid_diagram_refreshed",
        "capability_route_map_emitted",
        "ui_concept_done",
        "ui_concept_target_ready",
        "ui_concept_target_visible",
        "ui_concept_aesthetic_review_done",
        "ui_concept_aesthetic_reasons_recorded",
        "visual_asset_scope",
        "visual_asset_style_review_done",
        "visual_asset_aesthetic_review_done",
        "visual_asset_aesthetic_reasons_recorded",
        "ui_screenshot_qa_done",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_visual_iteration_loop_closed",
        "ui_visual_iterations",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "role_memory_refreshed_after_work",
        "implementation_human_review_context_loaded",
        "implementation_human_neutral_observation_written",
        "implementation_human_manual_experiments_run",
        "implementation_human_inspection_passed",
        "implementation_human_review_reviewer_approved",
        "capability_backward_context_loaded",
        "capability_child_evidence_replayed",
        "capability_backward_neutral_observation_written",
        "capability_structure_decision_recorded",
        "capability_backward_human_review_passed",
        "capability_backward_review_reviewer_approved",
        "capability_backward_issue_grilled",
        "capability_backward_issue_strategy",
        "capability_structural_route_repairs",
        "capability_new_sibling_nodes",
        "capability_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_visible_route_map_emitted",
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
        "final_route_wide_gate_ledger_stale_evidence_checked",
        "final_route_wide_gate_ledger_superseded_nodes_explained",
        "final_route_wide_gate_ledger_unresolved_count_zero",
        "final_route_wide_gate_ledger_pm_built",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "pm_completion_decision_recorded",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_status",
    )
    writes = (
        "status",
        "task_kind",
        "flowpilot_enabled",
        "mode_choice_offered",
        "mode_selected",
        "showcase_floor_committed",
        "self_interrogation_done",
        "self_interrogation_evidence",
        "visible_self_interrogation_done",
        "self_interrogation_questions",
        "self_interrogation_layer_count",
        "self_interrogation_questions_per_layer",
        "self_interrogation_layers",
        "self_interrogation_pm_ratified",
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
        "crew_memory_policy_written",
        "crew_memory_packets_written",
        "pm_initial_capability_decision_recorded",
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
        "pm_capability_work_decision_recorded",
        "crew_archived",
        "crew_memory_archived",
        "capabilities_manifest_written",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "child_skill_focused_interrogation_done",
        "child_skill_focused_interrogation_questions",
        "child_skill_focused_interrogation_scope_id",
        "child_skill_contracts_loaded",
        "child_skill_exact_source_verified",
        "child_skill_substitutes_rejected",
        "flowpilot_invocation_policy_mapped",
        "child_skill_requirements_mapped",
        "child_skill_evidence_plan_written",
        "child_skill_subroute_projected",
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "child_skill_execution_evidence_audited",
        "child_skill_evidence_matches_outputs",
        "child_skill_domain_quality_checked",
        "child_skill_iteration_loop_closed",
        "child_skill_current_gates_role_approved",
        "child_skill_completion_verified",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "flowguard_dependency_checked",
        "heartbeat_schedule_created",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
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
        "global_watchdog_supervisor_conversation_quiet",
        "external_watchdog_stopped_before_heartbeat",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "flowguard_process_design_done",
        "meta_route_checked",
        "meta_route_process_officer_approved",
        "capability_route_process_officer_approved",
        "capability_product_function_model_checked",
        "capability_product_function_model_product_officer_approved",
        "ui_inspected",
        "ui_concept_done",
        "ui_concept_target_ready",
        "ui_concept_target_visible",
        "ui_concept_aesthetic_review_done",
        "ui_concept_aesthetic_reasons_recorded",
        "ui_frontend_design_plan_done",
        "visual_asset_scope",
        "visual_asset_style_review_done",
        "visual_asset_aesthetic_review_done",
        "visual_asset_aesthetic_reasons_recorded",
        "ui_implemented",
        "ui_screenshot_qa_done",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_divergence_review_done",
        "ui_visual_iteration_loop_closed",
        "ui_visual_iterations",
        "non_ui_implemented",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "role_memory_refreshed_after_work",
        "implementation_human_review_context_loaded",
        "implementation_human_neutral_observation_written",
        "implementation_human_manual_experiments_run",
        "implementation_human_inspection_passed",
        "implementation_human_review_reviewer_approved",
        "capability_backward_context_loaded",
        "capability_child_evidence_replayed",
        "capability_backward_neutral_observation_written",
        "capability_structure_decision_recorded",
        "capability_backward_human_review_passed",
        "capability_backward_review_reviewer_approved",
        "capability_backward_issue_grilled",
        "capability_backward_issue_strategy",
        "capability_structural_route_repairs",
        "capability_new_sibling_nodes",
        "capability_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "final_verification_done",
        "completion_self_interrogation_done",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_visible_route_map_emitted",
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
        "final_route_wide_gate_ledger_stale_evidence_checked",
        "final_route_wide_gate_ledger_superseded_nodes_explained",
        "final_route_wide_gate_ledger_unresolved_count_zero",
        "final_route_wide_gate_ledger_pm_built",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "high_value_work_review",
        "standard_expansions",
        "pm_completion_decision_recorded",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_status",
        "subagent_scope_checked",
        "capability_route_version",
        "capability_route_checked",
        "capability_evidence_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "capability_route_mermaid_diagram_refreshed",
        "capability_route_map_emitted",
    )
    accepted_input_type = Tick
    input_description = "one autopilot capability-routing decision"
    output_description = "next allowed capability gate or implementation action"
    idempotency = (
        "Capability routing records evidence for each invoked child skill and "
        "does not let dependent work proceed before the required gate is done."
    )

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        if state.status == "new":
            yield _step(
                state,
                label="autopilot_started",
                action="start capability router",
                status="running",
                flowpilot_enabled=True,
            )
            return

        if not state.mode_choice_offered:
            yield _step(
                state,
                label="mode_choice_offered",
                action="offer full-auto, autonomous, guided, and strict-gated modes from loosest to strictest",
                mode_choice_offered=True,
            )
            return

        if not state.mode_selected:
            yield _step(
                state,
                label="mode_selected_by_user",
                action="record user-selected run mode",
                mode_selected=True,
            )
            yield _step(
                state,
                label="default_mode_recorded",
                action="record full-auto mode because user asked to continue or host cannot pause",
                mode_selected=True,
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
                label="project_manager_spawned_or_restored",
                action="spawn or restore the persistent project manager before capability routing",
                crew_count=1,
                project_manager_ready=True,
            )
            return

        if state.crew_count == 1:
            yield _step(
                state,
                label="human_like_reviewer_spawned_or_restored",
                action="spawn or restore the persistent reviewer before capability routing",
                crew_count=2,
                reviewer_ready=True,
            )
            return

        if state.crew_count == 2:
            yield _step(
                state,
                label="process_flowguard_officer_spawned_or_restored",
                action="spawn or restore the process FlowGuard officer before capability routing",
                crew_count=3,
                process_flowguard_officer_ready=True,
            )
            return

        if state.crew_count == 3:
            yield _step(
                state,
                label="product_flowguard_officer_spawned_or_restored",
                action="spawn or restore the product FlowGuard officer before capability routing",
                crew_count=4,
                product_flowguard_officer_ready=True,
            )
            return

        if state.crew_count == 4:
            yield _step(
                state,
                label="worker_a_spawned_or_restored",
                action="spawn or restore worker A for bounded capability sidecar work",
                crew_count=5,
                worker_a_ready=True,
            )
            return

        if state.crew_count == 5:
            yield _step(
                state,
                label="worker_b_spawned_or_restored",
                action="spawn or restore worker B for bounded capability sidecar work",
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

        if not state.crew_memory_policy_written:
            yield _step(
                state,
                label="crew_memory_packets_written",
                action="write compact role memory packets for all six capability-routing roles before PM ratification",
                crew_memory_policy_written=True,
                crew_memory_packets_written=CREW_SIZE,
            )
            return

        if not state.self_interrogation_pm_ratified:
            yield _step(
                state,
                label="self_interrogation_pm_ratified",
                action="project manager ratifies capability startup self-interrogation scope, risk layers, question count, and decision set",
                self_interrogation_pm_ratified=True,
            )
            return

        if not state.material_sources_scanned:
            yield _step(
                state,
                label="material_sources_scanned",
                action="main executor scans user-provided and repository-local materials before capability route design",
                material_sources_scanned=True,
            )
            return

        if not state.material_source_summaries_written:
            yield _step(
                state,
                label="material_source_summaries_written",
                action="main executor writes purpose, contents, and current-state summaries for capability-relevant materials",
                material_source_summaries_written=True,
            )
            return

        if not state.material_source_quality_classified:
            yield _step(
                state,
                label="material_source_quality_classified",
                action="main executor classifies source authority, freshness, contradictions, missing context, and readiness",
                material_source_quality_classified=True,
            )
            return

        if not state.material_intake_packet_written:
            yield _step(
                state,
                label="material_intake_packet_written",
                action="main executor writes the Material Intake Packet before PM capability planning",
                material_intake_packet_written=True,
            )
            return

        if not state.material_reviewer_sufficiency_checked:
            yield _step(
                state,
                label="material_reviewer_sufficiency_checked",
                action="human-like reviewer checks whether the material packet is clear and complete enough for PM capability planning",
                material_reviewer_sufficiency_checked=True,
            )
            return

        if not state.material_reviewer_sufficiency_approved:
            yield _step(
                state,
                label="material_reviewer_sufficiency_approved",
                action="human-like reviewer approves that the Material Intake Packet is PM-ready or blocks capability planning",
                material_reviewer_sufficiency_approved=True,
            )
            return

        if not state.pm_material_understanding_memo_written:
            yield _step(
                state,
                label="pm_material_understanding_memo_written",
                action="project manager writes a material understanding memo with source-claim matrix, open questions, and capability implications",
                pm_material_understanding_memo_written=True,
            )
            return

        if not state.pm_material_complexity_classified:
            yield _step(
                state,
                label="pm_material_complexity_classified",
                action="project manager classifies material complexity as simple, normal, or messy/raw before capability planning",
                pm_material_complexity_classified=True,
            )
            return

        if not state.pm_material_discovery_decision_recorded:
            yield _step(
                state,
                label="pm_material_discovery_decision_recorded",
                action="project manager records whether materials can feed capability routing directly or require a formal discovery, cleanup, modeling, or validation subtree",
                pm_material_discovery_decision_recorded=True,
            )
            return

        if not state.product_function_architecture_pm_synthesized:
            yield _step(
                state,
                label="product_function_architecture_pm_synthesized",
                action="project manager synthesizes grilled capability ideas into a product-function architecture decision package before contract freeze",
                product_function_architecture_pm_synthesized=True,
            )
            return

        if not state.product_function_user_task_map_written:
            yield _step(
                state,
                label="product_function_user_task_map_written",
                action="write target users, situations, jobs-to-be-done, and decision points before capability routing",
                product_function_user_task_map_written=True,
            )
            return

        if not state.product_function_capability_map_written:
            yield _step(
                state,
                label="product_function_capability_map_written",
                action="write must, should, optional, and rejected capability decisions before child-skill route discovery",
                product_function_capability_map_written=True,
            )
            return

        if not state.product_function_feature_decisions_written:
            yield _step(
                state,
                label="product_function_feature_decisions_written",
                action="bind each accepted capability to a user task and reject feature ideas that do not earn their place",
                product_function_feature_decisions_written=True,
            )
            return

        if not state.product_function_display_rationale_written:
            yield _step(
                state,
                label="product_function_display_rationale_written",
                action="record why each visible text, state, control, or status belongs in the product and what user decision it changes",
                product_function_display_rationale_written=True,
            )
            return

        if not state.product_function_gap_review_done:
            yield _step(
                state,
                label="product_function_missing_feature_review_done",
                action="review likely missing high-value capabilities before the route turns them into local implementation tasks",
                product_function_gap_review_done=True,
            )
            return

        if not state.product_function_negative_scope_written:
            yield _step(
                state,
                label="product_function_negative_scope_written",
                action="write non-goals and rejected displays to keep capability routing from adding accidental work",
                product_function_negative_scope_written=True,
            )
            return

        if not state.product_function_acceptance_matrix_written:
            yield _step(
                state,
                label="product_function_acceptance_matrix_written",
                action="write functional acceptance matrix with inputs, outputs, states, failure cases, and evidence for each core capability",
                product_function_acceptance_matrix_written=True,
            )
            return

        if not state.product_function_architecture_product_officer_approved:
            yield _step(
                state,
                label="product_function_architecture_product_officer_approved",
                action="product FlowGuard officer approves that the PM product-function architecture can drive capability and child-skill routing",
                product_function_architecture_product_officer_approved=True,
            )
            return

        if not state.product_function_architecture_reviewer_challenged:
            yield _step(
                state,
                label="product_function_architecture_reviewer_challenged",
                action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
                product_function_architecture_reviewer_challenged=True,
            )
            return

        if not state.contract_frozen:
            yield _step(
                state,
                label="contract_frozen",
                action="freeze acceptance contract from the PM product-function architecture",
                contract_frozen=True,
            )
            return

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

        if not state.child_skill_route_design_discovery_started:
            yield _step(
                state,
                label="child_skill_route_design_discovery_started",
                action="project manager starts route-design discovery of likely child skills from the frozen contract and capability manifest",
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
                action="assign required approver roles for every child-skill gate and forbid main-executor or worker self-approval",
                child_skill_gate_approvers_assigned=True,
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

        if not state.child_skill_manifest_process_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_process_officer_approved",
                action="process FlowGuard officer approves child-skill process and conformance gates before route modeling",
                child_skill_manifest_process_officer_approved=True,
            )
            return

        if not state.child_skill_manifest_product_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_product_officer_approved",
                action="product FlowGuard officer approves product-function impact gates derived from child skills",
                child_skill_manifest_product_officer_approved=True,
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
                action="run 20-50 focused grill-me questions for invoked child-skill boundaries",
                child_skill_focused_interrogation_done=True,
                child_skill_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                child_skill_focused_interrogation_scope_id="invoked-child-skills",
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
                action="process FlowGuard officer models and approves child-skill contract conformance before capability work",
                child_skill_conformance_model_checked=True,
                child_skill_conformance_model_process_officer_approved=True,
            )
            return

        if not state.strict_gate_obligation_review_model_checked:
            yield _step(
                state,
                label="strict_gate_obligation_review_model_checked",
                action="process FlowGuard officer runs the strict gate-obligation model so child-skill review caveats cannot close the active gate",
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
                action="probe host automation capability and confirm real heartbeat, watchdog, and global supervisor setup is supported",
                continuation_probe_done=True,
                host_continuation_supported=True,
            )
            yield _step(
                state,
                label="host_continuation_capability_unsupported_manual_resume",
                action="probe host automation capability, find no real wakeup support, and record manual-resume mode without creating heartbeat, watchdog, or global supervisor automation",
                continuation_probe_done=True,
                host_continuation_supported=False,
                manual_resume_mode_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.heartbeat_schedule_created:
            yield _step(
                state,
                label="heartbeat_schedule_created",
                action="create real continuation heartbeat as a stable launcher that reads state and execution frontier",
                heartbeat_schedule_created=True,
                stable_heartbeat_launcher_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_policy_recorded",
                action="record external watchdog stale threshold, evidence path, and official automation reset action",
                external_watchdog_policy_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_busy_lease_autowrap_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_busy_lease_autowrap_policy_recorded",
                action="record busy-lease suppression plus automatic bounded-operation wrapper policy for long commands and waits",
                external_watchdog_busy_lease_policy_recorded=True,
                external_watchdog_busy_lease_autowrap_policy_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.external_watchdog_source_drift_policy_recorded:
            yield _step(
                state,
                label="external_watchdog_source_drift_policy_recorded",
                action="record watchdog source-status policy: trust state, latest heartbeat, and busy lease only; record frontier/lifecycle drift diagnostics; never inspect live subagent busy state",
                external_watchdog_source_drift_policy_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.global_watchdog_supervisor_checked:
            yield _step(
                state,
                label="global_watchdog_supervisor_verified",
                action="look up the singleton Codex global watchdog supervisor; reuse or create a quiet thread-bound heartbeat supervisor by default, and do not create a high-frequency cron unless the user explicitly accepts new conversation noise",
                global_watchdog_supervisor_checked=True,
                global_watchdog_supervisor_singleton_ready=True,
                global_watchdog_supervisor_cadence_minutes=10,
                global_watchdog_supervisor_conversation_quiet=True,
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
            )
            return

        if not state.pm_initial_capability_decision_recorded:
            yield _step(
                state,
                label="pm_initial_capability_decision_recorded",
                action="ask the project manager to choose the capability-route direction from the contract, child-skill map, dependency plan, and crew reports",
                pm_initial_capability_decision_recorded=True,
            )
            return

        if not state.flowguard_process_design_done:
            yield _step(
                state,
                label="flowguard_process_designed",
                action="process FlowGuard officer uses FlowGuard as the capability-route process designer",
                flowguard_process_design_done=True,
            )
            return

        if not state.meta_route_checked:
            yield _step(
                state,
                label="meta_route_checked",
                action="process FlowGuard officer runs and approves meta-route checks",
                meta_route_checked=True,
                meta_route_process_officer_approved=True,
            )
            return

        if not state.capability_route_checked:
            yield _step(
                state,
                label="capability_route_checked",
                action="process FlowGuard officer runs and approves capability-route checks",
                capability_route_version=state.capability_route_version or 1,
                capability_route_checked=True,
                capability_route_process_officer_approved=True,
            )
            return

        if not state.capability_product_function_model_checked:
            yield _step(
                state,
                label="capability_product_function_model_checked",
                action="product FlowGuard officer runs and approves the capability product-function model",
                capability_product_function_model_checked=True,
                capability_product_function_model_product_officer_approved=True,
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

        if not state.capability_route_mermaid_diagram_refreshed:
            yield _step(
                state,
                label="capability_route_mermaid_diagram_refreshed",
                action="refresh canonical Mermaid route map from checked capability route and execution frontier before chat or UI display",
                capability_route_mermaid_diagram_refreshed=True,
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
            and state.capability_route_mermaid_diagram_refreshed
            and not state.capability_route_map_emitted
        ):
            yield _step(
                state,
                label="capability_route_map_emitted",
                action="emit visible capability route map with next gates, checks, and fallback branches",
                capability_route_map_emitted=True,
            )
            return

        if state.capability_backward_issue_strategy != "none":
            if not state.capability_backward_issue_grilled:
                yield _step(
                    state,
                    label="capability_backward_issue_grilled",
                    action="grill the failed capability backward review into an affected child, sibling gap, or subtree rebuild target",
                    capability_backward_issue_grilled=True,
                )
                return
            if (
                state.pm_repair_decision_interrogations
                <= state.capability_structural_route_repairs
            ):
                yield _step(
                    state,
                    label="pm_repair_decision_interrogated",
                    action="grill the project manager on capability repair strategy before choosing child rework, sibling insertion, or subtree rebuild",
                    pm_repair_decision_interrogations=(
                        state.pm_repair_decision_interrogations + 1
                    ),
                )
                return

            reset_changes = _reset_execution_quality_gates()
            route_changes = _capability_structural_repair_changes(state)
            if state.capability_backward_issue_strategy == "existing_child":
                yield _step(
                    state,
                    label="capability_route_updated_to_rework_child_node",
                    action="mutate the capability route back to the affected existing child node and invalidate the parent rollup",
                    **route_changes,
                    **reset_changes,
                )
                return
            if state.capability_backward_issue_strategy == "add_sibling":
                yield _step(
                    state,
                    label="capability_route_updated_to_add_sibling_child_node",
                    action="mutate the capability route to add an adjacent sibling child node before parent closure",
                    capability_new_sibling_nodes=state.capability_new_sibling_nodes + 1,
                    **route_changes,
                    **reset_changes,
                )
                return
            yield _step(
                state,
                label="capability_route_updated_to_rebuild_child_subtree",
                action="mutate the capability route to rebuild the child subtree from the capability product model",
                capability_subtree_rebuilds=state.capability_subtree_rebuilds + 1,
                **route_changes,
                **reset_changes,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_state:
            yield _step(
                state,
                label="heartbeat_loaded_state",
                action="heartbeat loads local state, active route, capability evidence, watchdog evidence, lifecycle evidence, and crew ledger",
                heartbeat_loaded_state=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_frontier:
            yield _step(
                state,
                label="heartbeat_loaded_execution_frontier",
                action="heartbeat loads execution_frontier.json before selecting capability work",
                heartbeat_loaded_frontier=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_crew_memory:
            yield _step(
                state,
                label="heartbeat_loaded_crew_memory",
                action="heartbeat loads all six compact role memory packets before restoring or replacing crew roles",
                heartbeat_loaded_crew_memory=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_restored_crew:
            yield _step(
                state,
                label="heartbeat_restored_six_agent_crew",
                action="heartbeat restores live crew roles when available and prepares memory-seeded replacements otherwise",
                heartbeat_restored_crew=True,
                replacement_roles_seeded_from_memory=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_rehydrated_crew:
            yield _step(
                state,
                label="heartbeat_rehydrated_six_agent_crew",
                action="rehydrate the six FlowPilot roles from role memory packets before asking the project manager for the next capability runway",
                heartbeat_rehydrated_crew=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_pm_decision_requested:
            yield _step(
                state,
                label="heartbeat_asked_project_manager",
                action="heartbeat asks the project manager what capability gate to run next",
                heartbeat_pm_decision_requested=True,
            )
            return

        if _route_scaffold_ready(state) and not state.pm_resume_decision_recorded:
            yield _step(
                state,
                label="pm_resume_completion_runway_recorded",
                action="project manager records a completion-oriented capability runway from the current gate toward completion, including hard stops and checkpoint cadence",
                pm_resume_decision_recorded=True,
                pm_completion_runway_recorded=True,
                pm_runway_hard_stops_recorded=True,
                pm_runway_checkpoint_cadence_recorded=True,
            )
            return

        if _route_scaffold_ready(state) and not state.pm_runway_synced_to_plan:
            yield _step(
                state,
                label="pm_runway_synced_to_visible_plan",
                action="main executor calls the host native plan tool when available, or records the fallback method, and replaces the visible capability plan with a downstream PM runway projection",
                pm_runway_synced_to_plan=True,
                plan_sync_method_recorded=True,
                visible_plan_has_runway_depth=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_health_checked:
            yield _step(
                state,
                label="heartbeat_health_checked",
                action="verify continuation heartbeat before capability work",
                heartbeat_health_checked=True,
            )
            return

        if _base_ready(state) and not state.pm_capability_work_decision_recorded:
            yield _step(
                state,
                label="pm_capability_work_decision_recorded",
                action="project manager assigns the current capability work package before implementation or child-skill execution",
                pm_capability_work_decision_recorded=True,
            )
            return

        if (
            _base_ready(state)
            and state.pm_capability_work_decision_recorded
            and not state.child_skill_node_gate_manifest_refined
        ):
            yield _step(
                state,
                label="child_skill_node_gate_manifest_refined",
                action="project manager refines the child-skill gate manifest for the current node context before sidecar work or implementation",
                child_skill_node_gate_manifest_refined=True,
            )
            return

        if (
            _base_ready(state)
            and state.pm_capability_work_decision_recorded
            and not state.child_skill_gate_authority_records_written
        ):
            yield _step(
                state,
                label="child_skill_gate_authority_records_written",
                action="write current child-skill gate authority records into the execution frontier before execution evidence is drafted",
                child_skill_gate_authority_records_written=True,
            )
            return

        if _base_ready(state) and not state.child_node_sidecar_scan_done:
            yield _step(
                state,
                label="child_node_sidecar_scan_no_need",
                action="enter the current child node and find no useful bounded sidecar task",
                child_node_sidecar_scan_done=True,
                sidecar_need="none",
            )
            yield _step(
                state,
                label="child_node_sidecar_scan_need_found_no_pool",
                action="enter the current child node and find a bounded sidecar task with no existing idle subagent",
                child_node_sidecar_scan_done=True,
                sidecar_need="needed",
                subagent_pool_exists=False,
                subagent_idle_available=False,
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
            )
            return

        if (
            _base_ready(state)
            and state.sidecar_need == "needed"
            and not state.subagent_scope_checked
        ):
            yield _step(
                state,
                label="sidecar_scope_checked",
                action="confirm the sidecar task is bounded, non-blocking, and disjoint from node ownership and route advancement",
                subagent_scope_checked=True,
            )
            return

        if (
            _base_ready(state)
            and state.sidecar_need == "needed"
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
                )
            else:
                yield _step(
                    state,
                    label="subagent_spawned_on_demand",
                    action="spawn a subagent only after the current child node has a bounded sidecar task and no suitable idle subagent exists",
                    subagent_pool_exists=True,
                    subagent_status="pending",
                )
            return

        if state.subagent_status == "pending":
            yield _step(
                state,
                label="sidecar_report_returned",
                action="sidecar subagent returns findings, evidence, changed paths if any, risks, and suggestions",
                subagent_status="returned",
            )
            return

        if state.subagent_status == "returned":
            yield _step(
                state,
                label="main_agent_merged_sidecar_report",
                action="main agent reviews, merges, and verifies the sidecar result while keeping node ownership",
                sidecar_need="none",
                subagent_status="idle",
                subagent_idle_available=True,
            )
            return

        if not _base_ready(state) or not _subagent_clear(state):
            yield _step(
                state,
                label="blocked_unready_capability_state",
                action="block because capability state is not ready for implementation",
                status="blocked",
            )
            return

        if not state.quality_package_done:
            yield _step(
                state,
                label="quality_package_passed_no_raise",
                action="run one quality package for feature thinness, worthwhile raises, child-skill mini-route visibility, validation strength, and rough-finish risk; record no scope raise",
                quality_package_done=True,
                quality_candidate_registry_checked=True,
                quality_raise_decision_recorded=True,
                validation_matrix_defined=True,
            )
            yield _step(
                state,
                label="quality_package_small_raise_in_current_node",
                action="record a low-risk high-value improvement inside the current capability node without changing the route",
                quality_package_done=True,
                quality_candidate_registry_checked=True,
                quality_raise_decision_recorded=True,
                validation_matrix_defined=True,
            )
            if (
                state.quality_route_raises < MAX_QUALITY_ROUTE_RAISES
                and not (state.non_ui_implemented or state.ui_implemented)
                and not state.final_verification_done
            ):
                yield _step(
                    state,
                    label="quality_package_route_raise_needed",
                    action="classify a medium or large capability improvement as route mutation, not unbounded immediate expansion",
                    capability_route_version=state.capability_route_version + 1,
                    capability_route_checked=False,
                    capability_route_process_officer_approved=False,
                    capability_product_function_model_checked=False,
                    capability_product_function_model_product_officer_approved=False,
                    capability_evidence_synced=False,
                    execution_frontier_written=False,
                    codex_plan_synced=False,
                    frontier_version=0,
                    plan_version=0,
                    capability_route_mermaid_diagram_refreshed=False,
                    capability_route_map_emitted=False,
                    child_skill_route_design_discovery_started=False,
                    child_skill_initial_gate_manifest_extracted=False,
                    child_skill_gate_approvers_assigned=False,
                    child_skill_manifest_reviewer_reviewed=False,
                    child_skill_manifest_process_officer_approved=False,
                    child_skill_manifest_product_officer_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    child_skill_contracts_loaded=False,
                    child_skill_focused_interrogation_done=False,
                    child_skill_focused_interrogation_questions=0,
                    child_skill_focused_interrogation_scope_id="",
                    child_skill_exact_source_verified=False,
                    child_skill_substitutes_rejected=False,
                    flowpilot_invocation_policy_mapped=False,
                    child_skill_requirements_mapped=False,
                    child_skill_evidence_plan_written=False,
                    child_skill_subroute_projected=False,
                    child_skill_conformance_model_checked=False,
                    child_skill_conformance_model_process_officer_approved=False,
                    strict_gate_obligation_review_model_checked=False,
                    flowguard_dependency_checked=False,
                    dependency_plan_recorded=False,
                    future_installs_deferred=False,
                    flowguard_process_design_done=False,
                    meta_route_checked=False,
                    meta_route_process_officer_approved=False,
                    subagent_status="none",
                    heartbeat_health_checked=False,
                    quality_route_raises=state.quality_route_raises + 1,
                    **_reset_execution_quality_gates(),
                )
            return

        if state.task_kind == "backend":
            if not state.non_ui_implemented:
                yield _step(
                    state,
                    label="non_ui_implemented",
                    action="implement non-UI project chunk",
                    non_ui_implemented=True,
                    role_memory_refreshed_after_work=False,
                )
                return
            if not state.child_skill_execution_evidence_audited:
                yield _step(
                    state,
                    label="child_skill_execution_evidence_audited",
                    action="audit child-skill step evidence against mapped requirements",
                    child_skill_execution_evidence_audited=True,
                )
                return
            if not state.child_skill_evidence_matches_outputs:
                yield _step(
                    state,
                    label="child_skill_evidence_matches_outputs",
                    action="confirm child-skill evidence matches actual outputs",
                    child_skill_evidence_matches_outputs=True,
                )
                return
            if not state.child_skill_domain_quality_checked:
                yield _step(
                    state,
                    label="child_skill_domain_quality_checked",
                    action="check child-skill output quality against parent node goal",
                    child_skill_domain_quality_checked=True,
                )
                return
            if not state.child_skill_iteration_loop_closed:
                yield _step(
                    state,
                    label="child_skill_iteration_loop_closed",
                    action="close child-skill iteration loop before final verification",
                    child_skill_iteration_loop_closed=True,
                )
                return
            if not state.role_memory_refreshed_after_work:
                yield _step(
                    state,
                    label="role_memory_packets_refreshed_after_capability_work",
                    action="refresh compact role memory packets after backend implementation evidence and before final verification",
                    role_memory_refreshed_after_work=True,
                )
                return
            if not state.final_verification_done:
                yield _step(
                    state,
                    label="final_verification_done",
                    action="run final verification",
                    final_verification_done=True,
                )
                return
            if not state.anti_rough_finish_done:
                yield _step(
                    state,
                    label="anti_rough_finish_passed",
                    action="review the verified backend result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                    anti_rough_finish_done=True,
                )
                if (
                    state.quality_reworks < MAX_QUALITY_REWORKS
                    and state.standard_expansions == 0
                ):
                    yield _step(
                        state,
                        label="anti_rough_finish_found_rework",
                        action="record bounded backend rework because the route is still too thin or weakly evidenced",
                        non_ui_implemented=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        final_verification_done=False,
                        heartbeat_health_checked=False,
                        quality_reworks=state.quality_reworks + 1,
                        **_reset_execution_quality_gates(),
                    )
                return
            if not state.implementation_human_review_context_loaded:
                yield _step(
                    state,
                    label="implementation_human_review_context_loaded",
                    action="load backend product model, outputs, logs, evidence, and acceptance context for human-like inspection",
                    implementation_human_review_context_loaded=True,
                )
                return
            if not state.implementation_human_neutral_observation_written:
                yield _step(
                    state,
                    label="implementation_human_neutral_observation_written",
                    action="write a neutral observation of backend outputs and behavior before pass/fail inspection judgement",
                    implementation_human_neutral_observation_written=True,
                )
                return
            if not state.implementation_human_manual_experiments_run:
                yield _step(
                    state,
                    label="implementation_human_manual_experiments_run",
                    action="exercise the backend behavior or inspect representative data like a human reviewer",
                    implementation_human_manual_experiments_run=True,
                )
                return
            if not state.implementation_human_inspection_passed:
                yield _step(
                    state,
                    label="implementation_human_inspection_passed",
                    action="human-like reviewer accepts the backend product behavior and evidence",
                    implementation_human_inspection_passed=True,
                    implementation_human_review_reviewer_approved=True,
                )
                return
            capability_backward_steps = tuple(
                _capability_backward_review_steps(state, domain="backend")
            )
            if capability_backward_steps:
                yield from capability_backward_steps
                return
            if not state.child_skill_current_gates_role_approved:
                yield _step(
                    state,
                    label="child_skill_current_gates_role_approved",
                    action="required reviewer, process officer, product officer, or PM approvals close the current child-skill gates; main-executor drafts are not approvals",
                    child_skill_current_gates_role_approved=True,
                )
                return
            if not state.child_skill_completion_verified:
                yield _step(
                    state,
                    label="child_skill_completion_verified",
                    action="verify invoked child skills met their own completion standards",
                    child_skill_completion_verified=True,
                )
                return
            if not state.completion_visible_route_map_emitted:
                yield _step(
                    state,
                    label="completion_visible_route_map_emitted",
                    action="emit visible completion route map before backend route close",
                    completion_visible_route_map_emitted=True,
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review backend feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review backend acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize backend quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer replays and approves backend final behavior against the capability product-function model",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final backend output, evidence, acceptance, and product model for completion inspection",
                    final_human_review_context_loaded=True,
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of final backend artifacts before completion judgement",
                    final_human_neutral_observation_written=True,
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="run final human-like backend experiments before completion grill-me",
                    final_human_manual_experiments_run=True,
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts backend product completeness",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer before backend route close",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_capability_gap_found",
                        action="raise backend capability standard and recheck route",
                        capability_route_version=state.capability_route_version + 1,
                        capability_route_checked=False,
                        capability_route_process_officer_approved=False,
                        capability_product_function_model_checked=False,
                        capability_product_function_model_product_officer_approved=False,
                        capability_evidence_synced=False,
                        execution_frontier_written=False,
                        codex_plan_synced=False,
                        frontier_version=0,
                        plan_version=0,
                        capability_route_mermaid_diagram_refreshed=False,
                        capability_route_map_emitted=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
                        child_skill_manifest_reviewer_reviewed=False,
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        child_skill_contracts_loaded=False,
                        child_skill_focused_interrogation_done=False,
                        child_skill_focused_interrogation_questions=0,
                        child_skill_focused_interrogation_scope_id="",
                        child_skill_exact_source_verified=False,
                        child_skill_substitutes_rejected=False,
                        flowpilot_invocation_policy_mapped=False,
                        child_skill_requirements_mapped=False,
                        child_skill_evidence_plan_written=False,
                        child_skill_subroute_projected=False,
                        child_skill_conformance_model_checked=False,
                        child_skill_conformance_model_process_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        flowguard_dependency_checked=False,
                        dependency_plan_recorded=False,
                        future_installs_deferred=False,
                        flowguard_process_design_done=False,
                        meta_route_checked=False,
                        meta_route_process_officer_approved=False,
                        subagent_status="none",
                        non_ui_implemented=False,
                        final_verification_done=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_visible_route_map_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_quality_candidate_review_done=False,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        external_watchdog_stopped_before_heartbeat=False,
                        terminal_lifecycle_frontier_written=False,
                        standard_expansions=state.standard_expansions + 1,
                        **_reset_execution_quality_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                )
                return
            final_ledger_steps = tuple(
                _final_route_wide_gate_ledger_steps(state, domain="backend")
            )
            if final_ledger_steps:
                yield from final_ledger_steps
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex automations, global supervisor records, Windows scheduled tasks, local state, execution frontier, and watchdog evidence before backend route close",
                    lifecycle_reconciliation_done=True,
                )
                return
            if not state.external_watchdog_stopped_before_heartbeat:
                yield _step(
                    state,
                    label="external_watchdog_stopped_before_heartbeat",
                    action="stop paired external watchdog automation before stopping heartbeat",
                    external_watchdog_active=False,
                    external_watchdog_stopped_before_heartbeat=True,
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write stopped watchdog and terminal heartbeat lifecycle back to execution frontier before route close",
                    terminal_lifecycle_frontier_written=True,
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive compact role memory packets with final capability statuses before backend route close",
                    crew_memory_archived=True,
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger after role memory and backend lifecycle reconciliation",
                    crew_archived=True,
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves backend completion after final reviews and lifecycle cleanup",
                    pm_completion_decision_recorded=True,
                )
                return
            yield _step(
                state,
                label="completed",
                action="complete backend project route",
                status="complete",
            )
            return

        if state.task_kind == "ui":
            if not state.ui_inspected:
                yield _step(
                    state,
                    label="ui_inspected",
                    action="inspect current UI/product before concept work",
                    ui_inspected=True,
                )
                return
            if not state.ui_concept_done:
                yield _step(
                    state,
                    label="ui_concept_done",
                    action="run concept-led UI redesign gate",
                    ui_concept_done=True,
                )
                return
            if not state.ui_concept_target_ready:
                yield _step(
                    state,
                    label="ui_concept_target_ready",
                    action="record the source UI skill's pre-implementation concept-target or reference decision",
                    ui_concept_target_ready=True,
                )
                return
            if not state.ui_concept_target_visible:
                yield _step(
                    state,
                    label="ui_concept_target_visible",
                    action="show the source UI skill's target/reference decision or record its waiver before implementation planning",
                    ui_concept_target_visible=True,
                )
                return
            if not state.ui_concept_aesthetic_review_done:
                yield _step(
                    state,
                    label="ui_concept_aesthetic_review_passed",
                    action="human-like reviewer records aesthetic verdict and concrete reasons for concept beauty, weakness, or polish before implementation planning",
                    ui_concept_aesthetic_review_done=True,
                    ui_concept_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_concept_aesthetic_review_failed",
                        action="human-like reviewer rejects the concept aesthetics with concrete ugly/weak reasons and sends it back for concept regeneration",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_frontend_design_plan_done:
                yield _step(
                    state,
                    label="ui_frontend_design_plan_done",
                    action="run frontend-design implementation planning gate",
                    ui_frontend_design_plan_done=True,
                )
                return
            if state.visual_asset_scope == "unknown":
                yield _step(
                    state,
                    label="visual_asset_not_required",
                    action="record that this UI route has no app icon or product imagery changes",
                    visual_asset_scope="none",
                )
                yield _step(
                    state,
                    label="visual_asset_required",
                    action="record that this UI route creates app icons or product imagery",
                    visual_asset_scope="required",
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_style_review_done
            ):
                yield _step(
                    state,
                    label="visual_asset_style_review_done",
                    action="record source UI skill evidence for in-scope product-facing visual assets",
                    visual_asset_style_review_done=True,
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_aesthetic_review_done
            ):
                yield _step(
                    state,
                    label="visual_asset_aesthetic_review_passed",
                    action="human-like reviewer records app-icon or visual-asset aesthetic verdict with concrete reasons before UI implementation",
                    visual_asset_aesthetic_review_done=True,
                    visual_asset_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="visual_asset_aesthetic_review_failed",
                        action="human-like reviewer rejects app-icon or visual-asset aesthetics with concrete ugly/weak reasons and sends it back for regeneration",
                        visual_asset_style_review_done=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_implemented:
                yield _step(
                    state,
                    label="ui_implemented",
                    action="implement UI using local architecture",
                    ui_implemented=True,
                    role_memory_refreshed_after_work=False,
                )
                return
            if not state.ui_screenshot_qa_done:
                yield _step(
                    state,
                    label="ui_screenshot_qa_done",
                    action="run rendered screenshot QA",
                    ui_screenshot_qa_done=True,
                )
                return
            if not state.ui_implementation_aesthetic_review_done:
                yield _step(
                    state,
                    label="ui_implementation_aesthetic_review_passed",
                    action="human-like reviewer records rendered UI aesthetic verdict with concrete reasons before divergence closure",
                    ui_implementation_aesthetic_review_done=True,
                    ui_implementation_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_implementation_aesthetic_review_failed",
                        action="human-like reviewer rejects rendered UI aesthetics with concrete ugly/weak reasons and sends it back for UI repair",
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_divergence_review_done:
                yield _step(
                    state,
                    label="ui_divergence_review_done",
                    action="record the source UI skill's divergence or comparison decision",
                    ui_divergence_review_done=True,
                )
                return
            if not state.ui_visual_iteration_loop_closed:
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_visual_iteration_needed",
                        action="rerun UI child-skill work after its loop decision changes required evidence",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                yield _step(
                    state,
                    label="ui_visual_iteration_loop_closed",
                    action="record the source UI skill's loop-closure decision",
                    ui_visual_iteration_loop_closed=True,
                )
                return
            if not state.child_skill_execution_evidence_audited:
                yield _step(
                    state,
                    label="child_skill_execution_evidence_audited",
                    action="audit UI child-skill step evidence against mapped requirements",
                    child_skill_execution_evidence_audited=True,
                )
                return
            if not state.child_skill_evidence_matches_outputs:
                yield _step(
                    state,
                    label="child_skill_evidence_matches_outputs",
                    action="confirm UI child-skill evidence matches actual rendered outputs",
                    child_skill_evidence_matches_outputs=True,
                )
                return
            if not state.child_skill_domain_quality_checked:
                yield _step(
                    state,
                    label="child_skill_domain_quality_checked",
                    action="check UI child-skill output quality against parent node goal",
                    child_skill_domain_quality_checked=True,
                )
                return
            if not state.child_skill_iteration_loop_closed:
                yield _step(
                    state,
                    label="child_skill_iteration_loop_closed",
                    action="close UI child-skill conformance loop before final verification",
                    child_skill_iteration_loop_closed=True,
                )
                return
            if not state.role_memory_refreshed_after_work:
                yield _step(
                    state,
                    label="role_memory_packets_refreshed_after_capability_work",
                    action="refresh compact role memory packets after UI implementation evidence and before final verification",
                    role_memory_refreshed_after_work=True,
                )
                return
            if not state.final_verification_done:
                yield _step(
                    state,
                    label="final_verification_done",
                    action="run final functional and visual verification",
                    final_verification_done=True,
                )
                return
            if not state.anti_rough_finish_done:
                yield _step(
                    state,
                    label="anti_rough_finish_passed",
                    action="review the verified UI result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                    anti_rough_finish_done=True,
                )
                if (
                    state.quality_reworks < MAX_QUALITY_REWORKS
                    and state.standard_expansions == 0
                ):
                    yield _step(
                        state,
                        label="anti_rough_finish_found_rework",
                        action="record bounded UI rework because the route is still too thin or weakly evidenced",
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        ui_visual_iteration_loop_closed=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        final_verification_done=False,
                        heartbeat_health_checked=False,
                        quality_reworks=state.quality_reworks + 1,
                        **_reset_execution_quality_gates(),
                    )
                return
            if not state.implementation_human_review_context_loaded:
                yield _step(
                    state,
                    label="implementation_human_review_context_loaded",
                    action="load UI product model, screenshots, concept target, interaction evidence, and acceptance context for human-like inspection",
                    implementation_human_review_context_loaded=True,
                )
                return
            if not state.implementation_human_neutral_observation_written:
                yield _step(
                    state,
                    label="implementation_human_neutral_observation_written",
                    action="write a neutral observation of the UI screenshot and exercised states before pass/fail inspection judgement",
                    implementation_human_neutral_observation_written=True,
                )
                return
            if not state.implementation_human_manual_experiments_run:
                yield _step(
                    state,
                    label="implementation_human_manual_experiments_run",
                    action="operate the UI like a human reviewer before accepting UI evidence",
                    implementation_human_manual_experiments_run=True,
                )
                return
            if not state.implementation_human_inspection_passed:
                yield _step(
                    state,
                    label="implementation_human_inspection_passed",
                    action="human-like reviewer accepts the UI product behavior, visual quality, and evidence",
                    implementation_human_inspection_passed=True,
                    implementation_human_review_reviewer_approved=True,
                )
                return
            capability_backward_steps = tuple(
                _capability_backward_review_steps(state, domain="UI")
            )
            if capability_backward_steps:
                yield from capability_backward_steps
                return
            if not state.child_skill_current_gates_role_approved:
                yield _step(
                    state,
                    label="child_skill_current_gates_role_approved",
                    action="required reviewer, process officer, product officer, or PM approvals close the current UI child-skill gates; main-executor drafts are not approvals",
                    child_skill_current_gates_role_approved=True,
                )
                return
            if not state.child_skill_completion_verified:
                yield _step(
                    state,
                    label="child_skill_completion_verified",
                    action="verify invoked child skills met their own completion standards",
                    child_skill_completion_verified=True,
                )
                return
            if not state.completion_visible_route_map_emitted:
                yield _step(
                    state,
                    label="completion_visible_route_map_emitted",
                    action="emit visible completion route map before UI route close",
                    completion_visible_route_map_emitted=True,
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review UI feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review UI acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize UI quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer replays and approves UI final behavior against the capability product-function model",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final UI screenshot, interaction evidence, concept target, acceptance, and product model for completion inspection",
                    final_human_review_context_loaded=True,
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of final UI artifacts and exercised states before completion judgement",
                    final_human_neutral_observation_written=True,
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="operate the final UI like a human reviewer before completion grill-me",
                    final_human_manual_experiments_run=True,
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts UI product completeness and visual quality",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer before UI route close",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_capability_gap_found",
                        action="raise UI capability standard and recheck route",
                        capability_route_version=state.capability_route_version + 1,
                        capability_route_checked=False,
                        capability_route_process_officer_approved=False,
                        capability_product_function_model_checked=False,
                        capability_product_function_model_product_officer_approved=False,
                        capability_evidence_synced=False,
                        execution_frontier_written=False,
                        codex_plan_synced=False,
                        frontier_version=0,
                        plan_version=0,
                        capability_route_mermaid_diagram_refreshed=False,
                        capability_route_map_emitted=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
                        child_skill_manifest_reviewer_reviewed=False,
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        child_skill_contracts_loaded=False,
                        child_skill_focused_interrogation_done=False,
                        child_skill_focused_interrogation_questions=0,
                        child_skill_focused_interrogation_scope_id="",
                        child_skill_exact_source_verified=False,
                        child_skill_substitutes_rejected=False,
                        flowpilot_invocation_policy_mapped=False,
                        child_skill_requirements_mapped=False,
                        child_skill_evidence_plan_written=False,
                        child_skill_subroute_projected=False,
                        child_skill_conformance_model_checked=False,
                        child_skill_conformance_model_process_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        flowguard_dependency_checked=False,
                        dependency_plan_recorded=False,
                        future_installs_deferred=False,
                        flowguard_process_design_done=False,
                        meta_route_checked=False,
                        meta_route_process_officer_approved=False,
                        subagent_status="none",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        ui_visual_iteration_loop_closed=False,
                        ui_visual_iterations=0,
                        final_verification_done=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_visible_route_map_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_quality_candidate_review_done=False,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        external_watchdog_stopped_before_heartbeat=False,
                        terminal_lifecycle_frontier_written=False,
                        standard_expansions=state.standard_expansions + 1,
                        **_reset_execution_quality_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                )
                return
            final_ledger_steps = tuple(
                _final_route_wide_gate_ledger_steps(state, domain="UI")
            )
            if final_ledger_steps:
                yield from final_ledger_steps
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex automations, global supervisor records, Windows scheduled tasks, local state, execution frontier, and watchdog evidence before UI route close",
                    lifecycle_reconciliation_done=True,
                )
                return
            if not state.external_watchdog_stopped_before_heartbeat:
                yield _step(
                    state,
                    label="external_watchdog_stopped_before_heartbeat",
                    action="stop paired external watchdog automation before stopping heartbeat",
                    external_watchdog_active=False,
                    external_watchdog_stopped_before_heartbeat=True,
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write stopped watchdog and terminal heartbeat lifecycle back to execution frontier before route close",
                    terminal_lifecycle_frontier_written=True,
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive compact role memory packets with final capability statuses before UI route close",
                    crew_memory_archived=True,
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger after role memory and UI lifecycle reconciliation",
                    crew_archived=True,
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves UI completion after final reviews and lifecycle cleanup",
                    pm_completion_decision_recorded=True,
                )
                return
            yield _step(
                state,
                label="completed",
                action="complete UI project route",
                status="complete",
            )
            return

        yield _step(
            state,
            label="blocked_unknown_task_kind",
            action="block because task kind is unknown",
            status="blocked",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del current_output, trace
    return state.status in {"blocked", "complete"}


def self_interrogation_before_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.contract_frozen and not (
        state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _full_interrogation_ready(
            total_questions=state.self_interrogation_questions,
            layer_count=state.self_interrogation_layer_count,
            questions_per_layer=state.self_interrogation_questions_per_layer,
            risk_family_mask=state.self_interrogation_layers,
        )
        and _crew_ready(state)
        and _product_function_architecture_ready(state)
    ):
        return InvariantResult.fail("contract frozen before showcase floor, dynamic per-layer visible self-interrogation evidence, crew recovery, PM product-function architecture, candidate pool, and validation direction")
    return InvariantResult.pass_()


def mode_choice_before_showcase_and_self_interrogation(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.showcase_floor_committed
        or state.self_interrogation_done
        or state.visible_self_interrogation_done
    ) and not (
        state.flowpilot_enabled and state.mode_choice_offered and state.mode_selected
    ):
        return InvariantResult.fail("showcase/self-interrogation ran before FlowPilot mode selection gate")
    return InvariantResult.pass_()


def implementation_requires_flowguard_gates(state: State, trace) -> InvariantResult:
    del trace
    if state.non_ui_implemented or state.ui_implemented:
        if not _gates_lifecycle_valid(state):
            return InvariantResult.fail("implementation started before capability route was ready")
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
            and state.pm_capability_work_decision_recorded
            and state.child_skill_node_gate_manifest_refined
            and state.child_skill_gate_authority_records_written
        ):
            return InvariantResult.fail(
                "implementation started before heartbeat loaded role memory, rehydrated the crew, synced the PM completion runway into a sufficiently deep visible plan, and wrote node-level child-skill gate authority records"
            )
        if not (
            state.quality_package_done
            and state.quality_candidate_registry_checked
            and state.quality_raise_decision_recorded
            and state.validation_matrix_defined
        ):
            return InvariantResult.fail(
                "implementation started before quality package recorded thinness, raise decision, child-skill mini-route visibility, and validation matrix"
            )
    return InvariantResult.pass_()


def dependency_plan_before_route_or_implementation(
    state: State, trace
) -> InvariantResult:
    del trace
    route_or_work_started = (
        state.meta_route_checked
        or state.capability_route_checked
        or state.capability_evidence_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.capability_route_map_emitted
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.completion_visible_route_map_emitted
        or state.final_feature_matrix_review_done
        or state.final_acceptance_matrix_review_done
        or state.final_quality_candidate_review_done
        or state.status == "complete"
    )
    if route_or_work_started and not (
        _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.dependency_plan_recorded and state.future_installs_deferred
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
    ):
        return InvariantResult.fail(
            "capability route or implementation started before six-agent crew, PM capability decision, product-function architecture, frozen contract, dependency plan, host continuation decision, and FlowGuard process design"
        )
    return InvariantResult.pass_()


def child_skill_fidelity_before_capability_work(
    state: State, trace
) -> InvariantResult:
    del trace
    dependent_work_started = (
        state.flowguard_dependency_checked
        or state.dependency_plan_recorded
        or state.flowguard_process_design_done
        or state.meta_route_checked
        or state.capability_route_checked
        or state.capability_evidence_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.capability_route_map_emitted
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.completion_visible_route_map_emitted
        or state.completion_self_interrogation_done
        or state.high_value_work_review == "exhausted"
        or state.status == "complete"
    )
    if dependent_work_started and not (
        state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and _focused_interrogation_ready(
            total_questions=state.child_skill_focused_interrogation_questions,
            scope_id=state.child_skill_focused_interrogation_scope_id,
        )
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.strict_gate_obligation_review_model_checked
    ):
        return InvariantResult.fail(
            "capability work started before PM-owned child-skill gate manifest extraction, approver assignment, reviewer/officer/PM approvals, focused child-skill grill-me, exact source, substitute rejection, invocation policy, requirement mapping, evidence plan, visible child-skill mini-route, conformance model, and strict gate-obligation review model"
        )
    node_child_skill_work_started = (
        state.child_node_sidecar_scan_done
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.child_skill_execution_evidence_audited
        or state.final_verification_done
        or state.completion_visible_route_map_emitted
        or state.status == "complete"
    )
    if node_child_skill_work_started and not (
        state.child_skill_node_gate_manifest_refined
        and state.child_skill_gate_authority_records_written
    ):
        return InvariantResult.fail(
            "node child-skill work started before PM node-level gate-manifest refinement and execution-frontier authority records"
        )
    completion_closure_started = (
        state.completion_visible_route_map_emitted
        or state.completion_self_interrogation_done
        or state.high_value_work_review == "exhausted"
        or state.status == "complete"
    )
    if completion_closure_started and not state.child_skill_completion_verified:
        return InvariantResult.fail(
            "completion closure started before child skill completion standards were verified"
        )
    if completion_closure_started and not state.anti_rough_finish_done:
        return InvariantResult.fail(
            "completion closure started before anti-rough-finish review"
        )
    if completion_closure_started and not (
        state.implementation_human_review_context_loaded
        and state.implementation_human_neutral_observation_written
        and state.implementation_human_manual_experiments_run
        and state.implementation_human_inspection_passed
    ):
        return InvariantResult.fail(
            "completion closure started before human-like implementation inspection with neutral observation"
        )
    if completion_closure_started and not (
        state.capability_backward_context_loaded
        and state.capability_child_evidence_replayed
        and state.capability_backward_neutral_observation_written
        and state.capability_structure_decision_recorded
        and state.capability_backward_human_review_passed
    ):
        return InvariantResult.fail(
            "completion closure started before capability backward composite review with neutral observation"
        )
    if state.child_skill_completion_verified and not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
        and state.child_skill_current_gates_role_approved
    ):
        return InvariantResult.fail(
            "child skill completion verified before evidence audit, output match, domain quality, iteration closure, and required role approvals for current child-skill gates"
        )
    if state.final_verification_done and not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "final verification started before child-skill evidence audit, output match, domain quality, and iteration closure"
        )
    if state.final_verification_done and not state.validation_matrix_defined:
        return InvariantResult.fail("final verification started before validation matrix")
    return InvariantResult.pass_()


def ui_route_requires_ui_capabilities(state: State, trace) -> InvariantResult:
    del trace
    if state.task_kind != "ui":
        return InvariantResult.pass_()
    if state.ui_implemented and not (
        state.ui_inspected
        and state.ui_concept_done
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_frontend_design_plan_done
    ):
        return InvariantResult.fail(
            "UI implemented before inspect/concept target visibility/aesthetic/frontend design gates"
        )
    if state.ui_frontend_design_plan_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "frontend design planning started before concept aesthetic verdict and reasons"
        )
    if state.ui_implemented and state.visual_asset_scope == "unknown":
        return InvariantResult.fail("UI implemented before visual asset scope decision")
    if state.ui_implemented and state.visual_asset_scope == "required":
        if not (
            state.visual_asset_style_review_done
            and state.visual_asset_aesthetic_review_done
            and state.visual_asset_aesthetic_reasons_recorded
        ):
            return InvariantResult.fail(
                "UI implemented before required visual asset style and aesthetic review"
            )
    if state.visual_asset_style_review_done and not (
        state.ui_inspected
        and state.ui_concept_done
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_frontend_design_plan_done
    ):
        return InvariantResult.fail("visual asset style review ran before UI style and concept aesthetic gates")
    if state.visual_asset_aesthetic_review_done and not (
        state.visual_asset_scope == "required"
        and state.visual_asset_style_review_done
        and state.visual_asset_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "visual asset aesthetic review completed without required scope, style review, and reasons"
        )
    if state.ui_screenshot_qa_done and not (
        state.ui_concept_target_ready and state.ui_concept_target_visible
    ):
        return InvariantResult.fail("rendered QA ran before the source UI skill's pre-implementation decision was ready and visible or waived")
    if state.ui_implementation_aesthetic_review_done and not (
        state.ui_screenshot_qa_done
        and state.ui_implementation_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "rendered UI aesthetic review completed without screenshot QA and concrete reasons"
        )
    if state.ui_divergence_review_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_screenshot_qa_done
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "UI child-skill comparison reviewed before pre-implementation UI evidence, rendered QA, and aesthetic verdict"
        )
    if state.ui_visual_iteration_loop_closed and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_screenshot_qa_done
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_divergence_review_done
    ):
        return InvariantResult.fail(
            "UI child-skill loop closed before pre-implementation UI evidence, rendered QA, aesthetic verdict, and comparison evidence"
        )
    if state.final_verification_done and not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail("final verification ran before child-skill conformance audit and quality loop closure")
    if state.final_verification_done and state.task_kind == "ui" and not (
        state.ui_screenshot_qa_done
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_divergence_review_done
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI final verification before aesthetic/screenshot/divergence/iteration-loop gates")
    if state.final_verification_done and state.visual_asset_scope == "required":
        if not (
            state.visual_asset_style_review_done
            and state.visual_asset_aesthetic_review_done
            and state.visual_asset_aesthetic_reasons_recorded
        ):
            return InvariantResult.fail(
                "UI final verification before required visual asset style and aesthetic review"
            )
    return InvariantResult.pass_()


def capability_route_updates_force_recheck_and_resync(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.capability_route_map_emitted and not state.capability_route_mermaid_diagram_refreshed:
        return InvariantResult.fail(
            "capability route map emitted before refreshing the canonical Mermaid route diagram"
        )
    if state.capability_structural_route_repairs > state.pm_repair_decision_interrogations:
        return InvariantResult.fail(
            "capability structural route repair written before PM repair strategy interrogation"
        )
    if state.non_ui_implemented or state.ui_implemented or state.final_verification_done:
        if not (
            state.capability_route_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_route_mermaid_diagram_refreshed
            and state.capability_route_map_emitted
        ):
            return InvariantResult.fail(
                "capability route update was not checked, product-modeled, evidence-synced, frontier-synced, plan-synced, and visibly mapped before work"
            )
    return InvariantResult.pass_()


def stable_heartbeat_prompt_not_capability_route_state(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.capability_route_version > 1
        and state.host_continuation_supported
        and not state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail(
            "capability route changed without a stable heartbeat launcher that reads persisted state"
        )
    if (
        state.capability_route_version > 1
        and state.manual_resume_mode_recorded
        and state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail(
            "manual-resume capability route unexpectedly created a stable heartbeat launcher"
        )
    return InvariantResult.pass_()


def external_watchdog_policy_is_lifecycle_state(state: State, trace) -> InvariantResult:
    del trace
    automation_bits = (
        state.heartbeat_schedule_created
        or state.stable_heartbeat_launcher_recorded
        or state.external_watchdog_policy_recorded
        or state.external_watchdog_busy_lease_policy_recorded
        or state.external_watchdog_busy_lease_autowrap_policy_recorded
        or state.external_watchdog_source_drift_policy_recorded
        or state.external_watchdog_automation_created
        or state.external_watchdog_hidden_noninteractive_configured
        or state.external_watchdog_active
        or state.global_watchdog_supervisor_checked
        or state.global_watchdog_supervisor_singleton_ready
        or state.global_watchdog_supervisor_cadence_minutes != 0
        or state.global_watchdog_supervisor_conversation_quiet
    )
    if state.manual_resume_mode_recorded and automation_bits:
        return InvariantResult.fail(
            "manual-resume mode recorded but heartbeat/watchdog/global-supervisor automation state was still created"
        )
    formal_started = (
        state.capability_route_checked
        or state.non_ui_implemented
        or state.ui_implemented
        or state.status == "complete"
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
            "active external watchdog automation lost its lifecycle policy gate during capability routing"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_busy_lease_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks busy-lease suppression policy during capability routing"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_busy_lease_autowrap_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks automatic busy-lease wrapper policy during capability routing"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_source_drift_policy_recorded
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks source-status drift policy during capability routing"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not state.external_watchdog_hidden_noninteractive_configured
    ):
        return InvariantResult.fail(
            "active external watchdog automation is not configured for hidden/noninteractive execution during capability routing"
        )
    if (
        state.status == "running"
        and state.external_watchdog_automation_created
        and state.external_watchdog_active
        and not (
            state.global_watchdog_supervisor_checked
            and state.global_watchdog_supervisor_singleton_ready
            and state.global_watchdog_supervisor_cadence_minutes == 10
            and state.global_watchdog_supervisor_conversation_quiet
        )
    ):
        return InvariantResult.fail(
            "active external watchdog automation lacks a verified quiet singleton Codex global supervisor during capability routing"
        )
    return InvariantResult.pass_()


def backend_route_does_not_run_ui_gates(state: State, trace) -> InvariantResult:
    del trace
    if state.task_kind != "backend":
        return InvariantResult.pass_()
    if (
        state.ui_inspected
        or state.ui_concept_done
        or state.ui_concept_target_ready
        or state.ui_concept_target_visible
        or state.ui_frontend_design_plan_done
        or state.visual_asset_scope == "required"
        or state.visual_asset_style_review_done
        or state.ui_implemented
        or state.ui_screenshot_qa_done
        or state.ui_divergence_review_done
        or state.ui_visual_iteration_loop_closed
        or state.ui_visual_iterations > 0
    ):
        return InvariantResult.fail("backend route invoked UI-only gates")
    return InvariantResult.pass_()


def subagent_result_must_merge_before_implementation_or_completion(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.subagent_status in {"pending", "returned"}:
        if state.non_ui_implemented or state.ui_implemented or state.status == "complete":
            return InvariantResult.fail(
                "implementation/completion proceeded before subagent merge"
            )
    if state.subagent_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("subagent used before child-node sidecar scan")
    if state.subagent_status == "pending" and not state.subagent_scope_checked:
        return InvariantResult.fail("sidecar subagent assigned before disjoint scope check")
    if state.subagent_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("subagent assigned without a bounded sidecar need")
    return InvariantResult.pass_()


def human_review_judgement_requires_neutral_observation(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.implementation_human_inspection_passed
        and not state.implementation_human_neutral_observation_written
    ):
        return InvariantResult.fail("implementation inspection passed without neutral observation")
    if (
        state.capability_backward_human_review_passed
        and not state.capability_backward_neutral_observation_written
    ):
        return InvariantResult.fail("capability backward review passed without neutral observation")
    if state.final_human_inspection_passed and not state.final_human_neutral_observation_written:
        return InvariantResult.fail("final inspection passed without neutral observation")
    return InvariantResult.pass_()


def final_completion_requires_right_verification(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "complete":
        return InvariantResult.pass_()
    if not _gates_lifecycle_valid(state):
        return InvariantResult.fail("completed before showcase, heartbeat, and FlowGuard capability gates")
    if not (
        _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.pm_resume_decision_recorded
        and state.pm_capability_work_decision_recorded
        and state.crew_memory_archived
        and state.crew_archived
    ):
        return InvariantResult.fail(
            "completed before six-agent crew, PM decisions, role memory archive, and terminal crew archive"
        )
    if not state.final_verification_done:
        return InvariantResult.fail("completed before final verification")
    if not state.child_skill_completion_verified:
        return InvariantResult.fail("completed before child skill completion standards were verified")
    if not state.child_skill_current_gates_role_approved:
        return InvariantResult.fail(
            "completed before required roles approved the current child-skill gates"
        )
    if not _terminal_continuation_reconciled(state):
        return InvariantResult.fail(
            "completed before continuation lifecycle state was written back to execution frontier"
        )
    if not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail("completed before child-skill conformance audit and quality loop closure")
    if not (
        state.quality_package_done
        and state.quality_candidate_registry_checked
        and state.quality_raise_decision_recorded
        and state.validation_matrix_defined
        and state.anti_rough_finish_done
    ):
        return InvariantResult.fail("completed before quality package and anti-rough-finish review")
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
            "completed before final feature, acceptance, quality-candidate, product-model replay, and human-like reviews"
        )
    if not _final_route_wide_gate_ledger_ready(state):
        return InvariantResult.fail(
            "completed before PM-built dynamic route-wide gate ledger, reviewer backward replay, and PM ledger approval"
        )
    if not (
        state.capability_product_function_model_checked
        and state.implementation_human_review_context_loaded
        and state.implementation_human_neutral_observation_written
        and state.implementation_human_manual_experiments_run
        and state.implementation_human_inspection_passed
        and state.capability_backward_context_loaded
        and state.capability_child_evidence_replayed
        and state.capability_backward_neutral_observation_written
        and state.capability_structure_decision_recorded
        and state.capability_backward_human_review_passed
    ):
        return InvariantResult.fail(
            "completed before capability product-function model, implementation inspection, and backward composite review"
        )
    if not (
        state.completion_self_interrogation_done
        and state.high_value_work_review == "exhausted"
    ):
        return InvariantResult.fail("completed before completion grill-me exhausted obvious high-value work")
    if not state.completion_visible_route_map_emitted:
        return InvariantResult.fail("completed before visible completion route map")
    if not _full_interrogation_ready(
        total_questions=state.completion_self_interrogation_questions,
        layer_count=state.completion_self_interrogation_layer_count,
        questions_per_layer=state.completion_self_interrogation_questions_per_layer,
        risk_family_mask=state.completion_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "completed before completion self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    if state.task_kind == "backend" and not state.non_ui_implemented:
        return InvariantResult.fail("backend route completed before implementation")
    if state.task_kind == "ui" and not (
        state.ui_implemented
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_screenshot_qa_done
        and state.ui_divergence_review_done
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI route completed before visual verification gates")
    if state.task_kind == "ui" and state.visual_asset_scope == "required":
        if not state.visual_asset_style_review_done:
            return InvariantResult.fail(
                "UI route completed before required visual asset style review"
            )
    return InvariantResult.pass_()


def material_handoff_before_capability_route_design(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.material_intake_packet_written and not (
        state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
    ):
        return InvariantResult.fail(
            "capability Material Intake Packet was written before sources were scanned, summarized, and quality-classified"
        )
    if state.material_reviewer_sufficiency_approved and not (
        state.material_intake_packet_written
        and state.material_reviewer_sufficiency_checked
    ):
        return InvariantResult.fail(
            "capability material packet was approved before reviewer sufficiency check"
        )
    if state.pm_material_understanding_memo_written and not (
        state.material_reviewer_sufficiency_approved
    ):
        return InvariantResult.fail(
            "PM capability material understanding memo was written before reviewer-approved intake evidence"
        )
    if state.pm_material_discovery_decision_recorded and not (
        state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
    ):
        return InvariantResult.fail(
            "PM capability material discovery decision was recorded before understanding memo and complexity classification"
        )
    if state.pm_initial_capability_decision_recorded and not _material_handoff_ready(state):
        return InvariantResult.fail(
            "PM capability route decision was recorded before reviewed material handoff"
        )
    return InvariantResult.pass_()


def actor_authority_gates_require_correct_role(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.self_interrogation_pm_ratified and not _crew_ready(state):
        return InvariantResult.fail(
            "capability startup self-interrogation was ratified before six-agent crew readiness"
        )
    if state.product_function_architecture_pm_synthesized and not (
        _crew_ready(state) and _material_handoff_ready(state)
    ):
        return InvariantResult.fail(
            "capability product-function architecture was synthesized before crew recovery and reviewed material handoff"
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
            "capability product-function architecture approval was recorded before all PM product artifacts existed"
        )
    if state.product_function_architecture_reviewer_challenged and not (
        state.product_function_architecture_product_officer_approved
        and state.reviewer_ready
    ):
        return InvariantResult.fail(
            "capability product-function architecture reviewer challenge ran before product officer approval or reviewer recovery"
        )
    if state.flowguard_process_design_done and not (
        state.self_interrogation_pm_ratified
        and _product_function_architecture_ready(state)
        and state.contract_frozen
    ):
        return InvariantResult.fail(
            "capability FlowGuard process design started before PM startup ratification, product-function architecture, and contract freeze"
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
    if state.child_skill_manifest_process_officer_approved and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
    ):
        return InvariantResult.fail(
            "process FlowGuard officer approved child-skill process gates before manifest extraction and approver assignment"
        )
    if state.child_skill_manifest_product_officer_approved and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
    ):
        return InvariantResult.fail(
            "product FlowGuard officer approved child-skill product gates before manifest extraction and approver assignment"
        )
    if state.child_skill_manifest_reviewer_reviewed and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
    ):
        return InvariantResult.fail(
            "human-like reviewer reviewed child-skill gates before manifest extraction and approver assignment"
        )
    if state.child_skill_gate_authority_records_written and not (
        state.child_skill_node_gate_manifest_refined
        and state.child_skill_manifest_pm_approved_for_route
    ):
        return InvariantResult.fail(
            "current child-skill gate authority records were written before PM-approved route manifest and node-level refinement"
        )
    if state.child_skill_current_gates_role_approved and not (
        state.child_skill_gate_authority_records_written
        and state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "current child-skill gates were role-approved before authority records, evidence audit, output match, domain quality, and loop closure"
        )
    if (
        state.child_skill_conformance_model_process_officer_approved
        and not state.child_skill_conformance_model_checked
    ):
        return InvariantResult.fail(
            "child-skill conformance approval is stale without conformance model check"
        )
    if (
        state.child_skill_conformance_model_checked
        and not state.child_skill_conformance_model_process_officer_approved
    ):
        return InvariantResult.fail(
            "child-skill conformance model lacks process FlowGuard officer approval"
        )
    if state.meta_route_process_officer_approved and not state.meta_route_checked:
        return InvariantResult.fail("meta-route approval is stale without meta-route check")
    if state.meta_route_checked and not state.meta_route_process_officer_approved:
        return InvariantResult.fail("meta-route check lacks process FlowGuard officer approval")
    if state.capability_route_process_officer_approved and not state.capability_route_checked:
        return InvariantResult.fail(
            "capability-route approval is stale without capability-route check"
        )
    if state.capability_route_checked and not state.capability_route_process_officer_approved:
        return InvariantResult.fail(
            "capability-route check lacks process FlowGuard officer approval"
        )
    if (
        state.capability_product_function_model_product_officer_approved
        and not state.capability_product_function_model_checked
    ):
        return InvariantResult.fail(
            "capability product-function approval is stale without product-function model check"
        )
    if (
        state.capability_product_function_model_checked
        and not state.capability_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "capability product-function model lacks product FlowGuard officer approval"
        )
    if (
        state.implementation_human_review_reviewer_approved
        and not state.implementation_human_inspection_passed
    ):
        return InvariantResult.fail(
            "implementation reviewer approval is stale without implementation human review pass"
        )
    if (
        state.implementation_human_inspection_passed
        and not state.implementation_human_review_reviewer_approved
    ):
        return InvariantResult.fail("implementation human review pass lacks reviewer approval")
    if (
        state.capability_backward_review_reviewer_approved
        and not state.capability_backward_human_review_passed
    ):
        return InvariantResult.fail(
            "capability backward reviewer approval is stale without backward review pass"
        )
    if (
        state.capability_backward_human_review_passed
        and not state.capability_backward_review_reviewer_approved
    ):
        return InvariantResult.fail("capability backward review pass lacks reviewer approval")
    if (
        state.final_product_function_model_product_officer_approved
        and not state.final_product_function_model_replayed
    ):
        return InvariantResult.fail(
            "final product replay approval is stale without final product replay"
        )
    if (
        state.final_product_function_model_replayed
        and not state.final_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "final product replay lacks product FlowGuard officer approval"
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
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM built final route-wide capability gate ledger before current route scan, gate collection, stale-evidence check, superseded explanations, and zero unresolved count"
        )
    if state.final_route_wide_gate_ledger_reviewer_backward_checked and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "final route-wide capability ledger reviewer replay ran before PM-built clean ledger"
        )
    if state.final_route_wide_gate_ledger_pm_completion_approved and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_route_wide_gate_ledger_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM approved final route-wide capability ledger before reviewer replay and zero unresolved count"
        )
    if state.pm_completion_decision_recorded and not state.final_route_wide_gate_ledger_pm_completion_approved:
        return InvariantResult.fail(
            "PM completion decision recorded before final route-wide capability gate ledger approval"
        )
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew ledger archived before compact role memory archive")
    if state.pm_completion_decision_recorded and not state.crew_archived:
        return InvariantResult.fail("PM completion decision recorded before crew archive")
    if state.status == "complete" and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("capability route completed before PM completion approval")
    return InvariantResult.pass_()


def crew_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.self_interrogation_pm_ratified and not (
        state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
    ):
        return InvariantResult.fail(
            "PM ratified capability startup before six compact role memory packets existed"
        )
    if state.heartbeat_pm_decision_requested and not (
        state.heartbeat_loaded_state
        and state.heartbeat_loaded_frontier
        and state.heartbeat_loaded_crew_memory
        and state.heartbeat_restored_crew
        and state.heartbeat_rehydrated_crew
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "heartbeat asked PM for capability work before crew role memory was loaded and rehydrated"
        )
    if state.final_verification_done and (
        state.non_ui_implemented or state.ui_implemented
    ) and not state.role_memory_refreshed_after_work:
        return InvariantResult.fail(
            "final verification started before role memory packets were refreshed after implementation work"
        )
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew archive written before role memory archive")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="self_interrogation_before_contract",
        description="Freeze the contract only after showcase floor and visible grill-me style self-review evidence exist.",
        predicate=self_interrogation_before_contract,
    ),
    Invariant(
        name="mode_choice_before_showcase_and_self_interrogation",
        description="FlowPilot offers run-mode choice before showcase commitment and self-interrogation.",
        predicate=mode_choice_before_showcase_and_self_interrogation,
    ),
    Invariant(
        name="implementation_requires_flowguard_gates",
        description="Formal implementation requires FlowGuard dependency, heartbeat, meta-route, and capability-route checks.",
        predicate=implementation_requires_flowguard_gates,
    ),
    Invariant(
        name="dependency_plan_before_route_or_implementation",
        description="Capability route checks and implementation require demand-driven dependency planning, heartbeat, and FlowGuard design first.",
        predicate=dependency_plan_before_route_or_implementation,
    ),
    Invariant(
        name="child_skill_fidelity_before_capability_work",
        description="Child skill contracts, mapped requirements, evidence plan, and completion verification gate capability work and closure.",
        predicate=child_skill_fidelity_before_capability_work,
    ),
    Invariant(
        name="ui_route_requires_ui_capabilities",
        description="UI implementation requires child-skill-routed UI evidence before implementation, rendered QA after implementation, and source-skill loop closure before completion.",
        predicate=ui_route_requires_ui_capabilities,
    ),
    Invariant(
        name="capability_route_updates_force_recheck_and_resync",
        description="Capability route changes force recheck, evidence sync, execution-frontier sync, plan sync, and visible remapping before more work.",
        predicate=capability_route_updates_force_recheck_and_resync,
    ),
    Invariant(
        name="stable_heartbeat_prompt_not_capability_route_state",
        description="Heartbeat automation stays a stable launcher while persisted capability route/frontier state carries next-gate changes.",
        predicate=stable_heartbeat_prompt_not_capability_route_state,
    ),
    Invariant(
        name="external_watchdog_policy_is_lifecycle_state",
        description="External watchdog policy is established with the paired automation lifecycle and is not reset by capability gates.",
        predicate=external_watchdog_policy_is_lifecycle_state,
    ),
    Invariant(
        name="backend_route_does_not_run_ui_gates",
        description="Non-UI routes must not invoke UI-only gates.",
        predicate=backend_route_does_not_run_ui_gates,
    ),
    Invariant(
        name="subagent_result_must_merge_before_implementation_or_completion",
        description="Subagent work must be scope-checked, returned, and merged before dependent implementation or completion.",
        predicate=subagent_result_must_merge_before_implementation_or_completion,
    ),
    Invariant(
        name="human_review_judgement_requires_neutral_observation",
        description="Human-like implementation, backward, and final reviews observe before judging.",
        predicate=human_review_judgement_requires_neutral_observation,
    ),
    Invariant(
        name="final_completion_requires_right_verification",
        description="Completion requires route-appropriate implementation and verification evidence.",
        predicate=final_completion_requires_right_verification,
    ),
    Invariant(
        name="material_handoff_before_capability_route_design",
        description="Material intake, reviewer sufficiency, and PM understanding happen before capability route design.",
        predicate=material_handoff_before_capability_route_design,
    ),
    Invariant(
        name="actor_authority_gates_require_correct_role",
        description="Authority-sensitive capability gates require PM, reviewer, or matching FlowGuard officer approval and reject stale approvals.",
        predicate=actor_authority_gates_require_correct_role,
    ),
    Invariant(
        name="crew_memory_rehydration_required",
        description="Heartbeat recovery must load compact role memory, rehydrate or seed replacements, refresh memory after work, and archive it before crew closure.",
        predicate=crew_memory_rehydration_required,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 120


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((CapabilityRouterStep(),), name="flowpilot_capability_router")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple(
        (result.label, result.new_state)
        for result in CapabilityRouterStep().apply(Tick(), state)
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
