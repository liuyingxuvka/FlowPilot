"""FlowGuard model for FlowPilot planning-quality gates.

Risk intent brief:
- Validate the minimal FlowPilot planning repair before prompt cards or
  templates are changed.
- Protected harms: high-fidelity UI or other complex tasks being planned as a
  generic implementation node, child-skill standards being selected but not
  compiled into route/node/work-packet obligations, reviewer hard-requirement
  blindspots being recorded as harmless residual risk, product FlowGuard
  modeling being treated as an after-the-fact review instead of PM route input,
  PM omitting final-user and higher-standard self-checks, PM naming generic
  quality concerns without task-specific hard parts or proof of depth,
  nonblocking improvement opportunities being turned into current-gate scope
  creep, low-quality-success risks being left without route/node/work-packet
  owners, repair nodes failing to reconnect to the mainline, and small/simple
  tasks being pulled into formal FlowPilot instead of staying outside it.
- Modeled state and side effects: PM planning profile selection, child-skill
  standard compilation, root product behavior model availability, PM route and
  node mapping to that model, process-FlowGuard operator route viability checks, reviewer
  blocking, and the rule that formal FlowPilot uses the full protocol only.
- Hard invariants: accepted routes must have a matching full-protocol planning
  profile, skill standards must expose MUST/DEFAULT/FORBID/VERIFY/
  LOOP/ARTIFACT/WAIVER, inherited standards must be visible at route, node,
  packet, reviewer, and result-matrix boundaries, PM route drafts must be based
  on the product behavior model, process-FlowGuard operator checks must validate route
  viability against that model including repair return-to-mainline, hard
  requirement blindspots cannot pass, and small/simple tasks cannot create a
  light/simple FlowPilot profile.
- Blindspot: this model checks the process contract shape. Runtime cards,
  templates, and tests must still be updated and validated after the model
  passes.
- 2026-05-17 extension: role-scoped quality-repair prompts must pressure
  executable workers to fix in-scope defects before completion while preventing
  reviewer, FlowGuard operator, PM, or generic packet prompts from granting silent target
  repair authority.
- 2026-06-02 extension: route, node, packet, result, repair, and final ledger
  surfaces must converge structure by disposing of fallback-like paths,
  compatibility branches, duplicate adapters, stale generated artifacts, and
  intentionally retained maintenance layers before completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_UI_ROUTE = "valid_ui_route"
VALID_SIMPLE_ROUTE = "simple_task_formal_flowpilot_profile"

UI_WITHOUT_PROFILE = "ui_without_planning_profile"
PROFILE_WITHOUT_CONVERGENCE_LOOP = "profile_without_convergence_loop"
SKILL_SELECTED_NO_CONTRACT = "skill_selected_no_contract"
SKILL_CONTRACT_MISSING_FIELDS = "skill_contract_missing_fields"
SKILL_CONTRACT_NOT_MAPPED = "skill_contract_not_mapped"
LOOP_VERIFY_ARTIFACT_NOT_INHERITED = "loop_verify_artifact_not_inherited"
NODE_PLAN_MISSING_PROJECTION = "node_plan_missing_projection"
WORK_PACKET_MISSING_PROJECTION = "work_packet_missing_projection"
REVIEWER_PASSES_HARD_BLINDSPOT = "reviewer_passes_hard_blindspot"
OVERMERGED_COMPLEX_IMPLEMENTATION_NODE = "overmerged_complex_implementation_node"
ARTIFACTLESS_MAJOR_NODE = "artifactless_major_node"
SIMPLE_TASK_OVERTEMPLATED = "simple_task_overtemplated"
PRODUCT_MODEL_MISSING = "product_model_missing"
PM_ROUTE_NOT_MAPPED_TO_PRODUCT_MODEL = "pm_route_not_mapped_to_product_model"
PROCESS_FLOWGUARD_OPERATOR_ROUTE_VIABILITY_MISSING = "flowguard_operator_route_scope_route_viability_missing"
REPAIR_NODE_NO_MAINLINE_RETURN = "repair_node_no_mainline_return"
NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL = "node_plan_not_mapped_to_product_model"
PM_USER_INTENT_SELF_CHECK_MISSING = "pm_user_intent_self_check_missing"
PM_HIGHER_STANDARD_SELF_CHECK_MISSING = "pm_higher_standard_self_check_missing"
PM_IMPROVEMENT_OPPORTUNITY_UNCLASSIFIED = "pm_improvement_opportunity_unclassified"
PM_IMPROVEMENT_SCOPE_CREEP = "pm_improvement_scope_creep"
PM_CLOSURE_USER_OUTCOME_REPLAY_MISSING = "pm_closure_user_outcome_replay_missing"
PM_LOW_QUALITY_REVIEW_MISSING = "pm_low_quality_review_missing"
PM_LOW_QUALITY_REVIEW_GENERIC = "pm_low_quality_review_generic"
HARD_LOW_QUALITY_RISK_NO_ROUTE_OWNER = "hard_low_quality_risk_no_route_owner"
LOW_QUALITY_RISK_CAUSES_ROUTE_BLOAT = "low_quality_risk_causes_route_bloat"
PM_SHALLOW_COMPLETION_TRAPS_MISSING = "pm_shallow_completion_traps_missing"
PRACTICAL_OUTCOME_DESIGN_ONLY_ROUTE = "practical_outcome_design_only_route"
NODE_PLAN_MISSING_LOW_QUALITY_MAPPING = "node_plan_missing_low_quality_mapping"
NODE_PLAN_MISSING_CURRENT_CHECK_SURFACE = "node_plan_missing_current_check_surface"
WORK_PACKET_MISSING_LOW_QUALITY_WARNING = "work_packet_missing_low_quality_warning"
PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING = "pm_closure_low_quality_risk_disposition_missing"
PM_CLOSURE_SHALLOW_COMPLETION_TRAPS_UNRESOLVED = "pm_closure_shallow_completion_traps_unresolved"
PROCESS_SUPPORT_SKILL_IGNORED = "process_support_skill_ignored"
ROLE_SKILL_BINDING_MISSING = "role_skill_binding_missing"
ROLE_SKILL_USE_SELF_ATTESTED = "role_skill_use_self_attested"
WORKER_PACKET_MISSING_IN_SCOPE_REPAIR = "worker_packet_missing_in_scope_repair"
WORKER_PACKET_REPAIRS_OUT_OF_SCOPE = "worker_packet_repairs_out_of_scope"
EVIDENCE_PACKET_REPAIRS_TARGET_ARTIFACT = "evidence_packet_repairs_target_artifact"
FLOWGUARD_OPERATOR_PACKET_REPAIRS_TARGET_ARTIFACT = "flowguard_operator_packet_repairs_target_artifact"
REVIEWER_PROMPT_GRANTS_DIRECT_REPAIR = "reviewer_prompt_grants_direct_repair"
GENERIC_TEMPLATE_USES_BLANKET_REPAIR = "generic_template_uses_blanket_repair"
PM_STRUCTURE_CONVERGENCE_REVIEW_MISSING = "pm_structure_convergence_review_missing"
NODE_PLAN_MISSING_STRUCTURE_HYGIENE_EXPECTATION = "node_plan_missing_structure_hygiene_expectation"
WORK_PACKET_MISSING_STRUCTURE_HYGIENE_DELTA = "work_packet_missing_structure_hygiene_delta"
WORKER_RESULT_LEAVES_UNOWNED_FALLBACK = "worker_result_leaves_unowned_fallback"
REPAIR_LEAVES_COMPAT_BRANCH = "repair_leaves_compat_branch"
FINAL_LEDGER_STRUCTURE_DEBT_UNRESOLVED = "final_ledger_structure_debt_unresolved"
PM_IMPLEMENTATION_INTENT_MISSING = "pm_implementation_intent_missing"
TARGET_REALIZATION_MODEL_MISSING = "target_realization_model_missing"
TARGET_REALIZATION_MODEL_IGNORES_PM_INTENT = "target_realization_model_ignores_pm_intent"
PM_TARGET_REALIZATION_ACCEPTS_DOWNGRADE = "pm_target_realization_accepts_downgrade"
REVIEWER_IMPLEMENTATION_INTENT_ALIGNMENT_MISSING = "reviewer_implementation_intent_alignment_missing"
ROUTE_MISSING_REALIZATION_OBLIGATIONS = "route_missing_realization_obligations"
NODE_PLAN_MISSING_REALIZATION_OBLIGATIONS = "node_plan_missing_realization_obligations"
WORK_PACKET_MISSING_REALIZATION_OBLIGATIONS = "work_packet_missing_realization_obligations"
FINAL_LEDGER_REALIZATION_OBLIGATIONS_UNRESOLVED = "final_ledger_realization_obligations_unresolved"
ACCEPTANCE_ITEM_REGISTRY_MISSING = "acceptance_item_registry_missing"
ACCEPTANCE_ITEM_NO_ROUTE_OWNER = "acceptance_item_no_route_owner"
NODE_PLAN_MISSING_ACCEPTANCE_ITEM_PROJECTION = "node_plan_missing_acceptance_item_projection"
WORK_PACKET_MISSING_ACCEPTANCE_ITEM_MATRIX = "work_packet_missing_acceptance_item_matrix"
FINAL_LEDGER_ACCEPTANCE_ITEM_UNRESOLVED = "final_ledger_acceptance_item_unresolved"
STARTUP_QUALITY_POSTURE_MISSING = "startup_quality_posture_missing"
PRODUCT_ARCHITECTURE_IGNORES_STARTUP_QUALITY = "product_architecture_ignores_startup_quality"
ROUTE_QUALITY_POSTURE_DROPPED = "route_quality_posture_dropped"
PACKET_QUALITY_FLOOR_DROPPED = "packet_quality_floor_dropped"

VALID_SCENARIOS = (VALID_UI_ROUTE,)
NEGATIVE_SCENARIOS = (
    VALID_SIMPLE_ROUTE,
    UI_WITHOUT_PROFILE,
    PROFILE_WITHOUT_CONVERGENCE_LOOP,
    SKILL_SELECTED_NO_CONTRACT,
    SKILL_CONTRACT_MISSING_FIELDS,
    SKILL_CONTRACT_NOT_MAPPED,
    LOOP_VERIFY_ARTIFACT_NOT_INHERITED,
    NODE_PLAN_MISSING_PROJECTION,
    WORK_PACKET_MISSING_PROJECTION,
    REVIEWER_PASSES_HARD_BLINDSPOT,
    OVERMERGED_COMPLEX_IMPLEMENTATION_NODE,
    ARTIFACTLESS_MAJOR_NODE,
    SIMPLE_TASK_OVERTEMPLATED,
    PRODUCT_MODEL_MISSING,
    PM_ROUTE_NOT_MAPPED_TO_PRODUCT_MODEL,
    PROCESS_FLOWGUARD_OPERATOR_ROUTE_VIABILITY_MISSING,
    REPAIR_NODE_NO_MAINLINE_RETURN,
    NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL,
    PM_USER_INTENT_SELF_CHECK_MISSING,
    PM_HIGHER_STANDARD_SELF_CHECK_MISSING,
    PM_IMPROVEMENT_OPPORTUNITY_UNCLASSIFIED,
    PM_IMPROVEMENT_SCOPE_CREEP,
    PM_CLOSURE_USER_OUTCOME_REPLAY_MISSING,
    PM_LOW_QUALITY_REVIEW_MISSING,
    PM_LOW_QUALITY_REVIEW_GENERIC,
    HARD_LOW_QUALITY_RISK_NO_ROUTE_OWNER,
    LOW_QUALITY_RISK_CAUSES_ROUTE_BLOAT,
    PM_SHALLOW_COMPLETION_TRAPS_MISSING,
    PRACTICAL_OUTCOME_DESIGN_ONLY_ROUTE,
    NODE_PLAN_MISSING_LOW_QUALITY_MAPPING,
    NODE_PLAN_MISSING_CURRENT_CHECK_SURFACE,
    WORK_PACKET_MISSING_LOW_QUALITY_WARNING,
    PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING,
    PM_CLOSURE_SHALLOW_COMPLETION_TRAPS_UNRESOLVED,
    PROCESS_SUPPORT_SKILL_IGNORED,
    ROLE_SKILL_BINDING_MISSING,
    ROLE_SKILL_USE_SELF_ATTESTED,
    WORKER_PACKET_MISSING_IN_SCOPE_REPAIR,
    WORKER_PACKET_REPAIRS_OUT_OF_SCOPE,
    EVIDENCE_PACKET_REPAIRS_TARGET_ARTIFACT,
    FLOWGUARD_OPERATOR_PACKET_REPAIRS_TARGET_ARTIFACT,
    REVIEWER_PROMPT_GRANTS_DIRECT_REPAIR,
    GENERIC_TEMPLATE_USES_BLANKET_REPAIR,
    PM_STRUCTURE_CONVERGENCE_REVIEW_MISSING,
    NODE_PLAN_MISSING_STRUCTURE_HYGIENE_EXPECTATION,
    WORK_PACKET_MISSING_STRUCTURE_HYGIENE_DELTA,
    WORKER_RESULT_LEAVES_UNOWNED_FALLBACK,
    REPAIR_LEAVES_COMPAT_BRANCH,
    FINAL_LEDGER_STRUCTURE_DEBT_UNRESOLVED,
    PM_IMPLEMENTATION_INTENT_MISSING,
    TARGET_REALIZATION_MODEL_MISSING,
    TARGET_REALIZATION_MODEL_IGNORES_PM_INTENT,
    PM_TARGET_REALIZATION_ACCEPTS_DOWNGRADE,
    REVIEWER_IMPLEMENTATION_INTENT_ALIGNMENT_MISSING,
    ROUTE_MISSING_REALIZATION_OBLIGATIONS,
    NODE_PLAN_MISSING_REALIZATION_OBLIGATIONS,
    WORK_PACKET_MISSING_REALIZATION_OBLIGATIONS,
    FINAL_LEDGER_REALIZATION_OBLIGATIONS_UNRESOLVED,
    ACCEPTANCE_ITEM_REGISTRY_MISSING,
    ACCEPTANCE_ITEM_NO_ROUTE_OWNER,
    NODE_PLAN_MISSING_ACCEPTANCE_ITEM_PROJECTION,
    WORK_PACKET_MISSING_ACCEPTANCE_ITEM_MATRIX,
    FINAL_LEDGER_ACCEPTANCE_ITEM_UNRESOLVED,
    STARTUP_QUALITY_POSTURE_MISSING,
    PRODUCT_ARCHITECTURE_IGNORES_STARTUP_QUALITY,
    ROUTE_QUALITY_POSTURE_DROPPED,
    PACKET_QUALITY_FLOOR_DROPPED,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

STANDARD_FIELDS = frozenset(
    {
        "MUST",
        "DEFAULT",
        "FORBID",
        "VERIFY",
        "LOOP",
        "ARTIFACT",
        "WAIVER",
    }
)


@dataclass(frozen=True)
class Tick:
    """One abstract planning-quality evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    task_class: str = "unset"  # unset | ui_product | simple_bug

    startup_release_projects_quality_posture: bool = False
    product_architecture_consumes_startup_quality_posture: bool = False
    route_preserves_startup_product_quality_posture: bool = False
    packet_preserves_current_quality_floor: bool = False
    planning_profile_selected: bool = False
    planning_profile: str = "none"
    simple_task_profile_waiver: bool = False
    route_complexity_matches_profile: bool = False
    required_convergence_loop_planned: bool = False
    route_nodes_have_stage_artifacts: bool = False
    major_node_overmerged: bool = False
    product_behavior_model_written: bool = False
    product_model_risk_boundary_checked: bool = False
    pm_implementation_intent_written: bool = False
    pm_implementation_intent_plain_language_guidance: bool = False
    pm_implementation_intent_names_hard_parts: bool = False
    target_realization_model_written: bool = False
    target_realization_model_preserves_pm_intent: bool = False
    pm_target_realization_model_accepted: bool = False
    reviewer_implementation_intent_alignment_checked: bool = False
    route_consumes_realization_obligations: bool = False
    node_plan_consumes_realization_obligations: bool = False
    work_packet_carries_realization_obligations: bool = False
    final_realization_obligations_disposition_done: bool = False
    acceptance_item_registry_written: bool = False
    acceptance_registry_has_user_and_pm_items: bool = False
    acceptance_items_bound_to_route_nodes: bool = False
    node_plan_projects_acceptance_items: bool = False
    work_packet_carries_acceptance_item_matrix: bool = False
    pm_disposition_closes_acceptance_items: bool = False
    final_acceptance_items_disposition_done: bool = False
    pm_route_maps_to_product_model: bool = False
    flowguard_operator_route_scope_validated_route_viability: bool = False
    repair_return_to_mainline_defined: bool = False
    node_acceptance_plan_maps_product_model_segment: bool = False
    pm_user_intent_self_check_written: bool = False
    pm_higher_standard_self_check_written: bool = False
    pm_improvement_opportunities_classified: bool = False
    pm_higher_standard_opportunity_found: bool = False
    pm_improvement_incorrectly_hard_blocker: bool = False
    pm_low_quality_success_review_written: bool = False
    pm_low_quality_review_task_specific: bool = False
    pm_hard_parts_identified: bool = False
    pm_thin_shortcuts_identified: bool = False
    pm_proof_of_depth_defined: bool = False
    hard_low_quality_risks_bound_to_route_nodes: bool = False
    low_quality_review_caused_unjustified_route_node: bool = False
    practical_next_step_required: bool = False
    shallow_completion_traps_named: bool = False
    route_dominated_by_design_only_nodes: bool = False
    shallow_completion_traps_bound_to_route_work: bool = False
    route_produces_practical_next_step_evidence: bool = False
    node_acceptance_low_quality_mapping_written: bool = False
    node_acceptance_proof_of_depth_defined: bool = False
    node_acceptance_current_check_surface_written: bool = False
    node_acceptance_status_vocabulary_written: bool = False
    node_acceptance_expected_failure_shape_written: bool = False
    node_acceptance_worker_outcome_bounded: bool = False
    work_packet_carries_low_quality_warning: bool = False
    worker_packet_carries_in_scope_quality_repair: bool = False
    worker_packet_escalates_out_of_scope_defects: bool = False
    evidence_packet_self_corrects_only_own_output: bool = False
    flowguard_operator_packet_self_corrects_model_only: bool = False
    reviewer_prompt_forbids_direct_artifact_repair: bool = False
    generic_packet_template_role_scoped: bool = False
    route_structure_convergence_review_written: bool = False
    route_structure_cleanup_targets_named: bool = False
    allowed_current_runtime_recovery_owned: bool = False
    node_structure_hygiene_expectation_written: bool = False
    work_packet_carries_structure_hygiene_delta: bool = False
    worker_result_reports_structure_hygiene_delta: bool = False
    worker_result_retains_unowned_fallback: bool = False
    repair_path_retains_compatibility_branch: bool = False
    final_structure_debt_dispositions_done: bool = False
    final_structure_debt_has_unresolved_entries: bool = False
    negative_rejection_evidence_separated: bool = False
    final_low_quality_risks_disposition_done: bool = False
    final_shallow_completion_traps_disposition_done: bool = False
    final_output_practical_next_step_confirmed: bool = False
    closure_or_final_ledger_decision: bool = False
    closure_replays_final_user_outcome: bool = False

    child_skill_selected: bool = False
    skill_standard_contract_compiled: bool = False
    skill_standard_fields: frozenset[str] = field(default_factory=frozenset)
    skill_standard_source_paths_recorded: bool = False
    standards_mapped_to_route_nodes: bool = False
    standards_mapped_to_work_packets: bool = False
    standards_mapped_to_reviewer_gates: bool = False
    standards_mapped_to_expected_artifacts: bool = False
    loop_verify_artifact_inherited: bool = False
    process_support_skill_candidate_available: bool = False
    process_support_skill_decision_recorded: bool = False
    role_skill_use_binding_written: bool = False
    role_skill_use_evidence_required: bool = False
    role_skill_use_evidence_reviewer_check_bound: bool = False
    role_skill_use_self_attested_without_evidence: bool = False

    node_acceptance_plan_consumes_projection: bool = False
    work_packet_carries_projection: bool = False
    result_matrix_required: bool = False
    reviewer_gate_bound_to_projection: bool = False

    residual_blindspot_touches_hard_requirement: bool = False
    residual_blindspot_touches_required_skill_gate: bool = False
    reviewer_passed_route: bool = False
    reviewer_blocked_route: bool = False

    simple_task_overtemplated: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class PlanningQualityStep:
    """Model one FlowPilot planning-quality transition.

    Input x State -> Set(Output x State)
    reads: task class, route profile, skill standard contract, node/work packet
    projection, reviewer gate, residual blindspots
    writes: selected scenario or terminal planning-quality decision
    idempotency: scenario facts are monotonic; a terminal decision is not
    reinterpreted by later ticks.
    """

    name = "PlanningQualityStep"
    input_description = "FlowPilot planning-quality tick"
    output_description = "one planning-quality transition"
    reads = (
        "task_class",
        "planning_profile",
        "product_behavior_model",
        "skill_standard_contract",
        "node_acceptance_projection",
        "work_packet_projection",
        "reviewer_gate",
    )
    writes = ("scenario_facts", "terminal_planning_quality_decision")
    idempotency = "monotonic planning-quality facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _valid_ui_state() -> State:
    return State(
        status="running",
        scenario=VALID_UI_ROUTE,
        task_class="ui_product",
        startup_release_projects_quality_posture=True,
        product_architecture_consumes_startup_quality_posture=True,
        route_preserves_startup_product_quality_posture=True,
        packet_preserves_current_quality_floor=True,
        planning_profile_selected=True,
        planning_profile="interactive_software_ui_product",
        route_complexity_matches_profile=True,
        required_convergence_loop_planned=True,
        route_nodes_have_stage_artifacts=True,
        product_behavior_model_written=True,
        product_model_risk_boundary_checked=True,
        pm_implementation_intent_written=True,
        pm_implementation_intent_plain_language_guidance=True,
        pm_implementation_intent_names_hard_parts=True,
        target_realization_model_written=True,
        target_realization_model_preserves_pm_intent=True,
        pm_target_realization_model_accepted=True,
        reviewer_implementation_intent_alignment_checked=True,
        route_consumes_realization_obligations=True,
        node_plan_consumes_realization_obligations=True,
        work_packet_carries_realization_obligations=True,
        final_realization_obligations_disposition_done=True,
        acceptance_item_registry_written=True,
        acceptance_registry_has_user_and_pm_items=True,
        acceptance_items_bound_to_route_nodes=True,
        node_plan_projects_acceptance_items=True,
        work_packet_carries_acceptance_item_matrix=True,
        pm_disposition_closes_acceptance_items=True,
        final_acceptance_items_disposition_done=True,
        pm_route_maps_to_product_model=True,
        flowguard_operator_route_scope_validated_route_viability=True,
        repair_return_to_mainline_defined=True,
        node_acceptance_plan_maps_product_model_segment=True,
        pm_user_intent_self_check_written=True,
        pm_higher_standard_self_check_written=True,
        pm_improvement_opportunities_classified=True,
        pm_low_quality_success_review_written=True,
        pm_low_quality_review_task_specific=True,
        pm_hard_parts_identified=True,
        pm_thin_shortcuts_identified=True,
        pm_proof_of_depth_defined=True,
        hard_low_quality_risks_bound_to_route_nodes=True,
        practical_next_step_required=True,
        shallow_completion_traps_named=True,
        shallow_completion_traps_bound_to_route_work=True,
        route_produces_practical_next_step_evidence=True,
        node_acceptance_low_quality_mapping_written=True,
        node_acceptance_proof_of_depth_defined=True,
        node_acceptance_current_check_surface_written=True,
        node_acceptance_status_vocabulary_written=True,
        node_acceptance_expected_failure_shape_written=True,
        node_acceptance_worker_outcome_bounded=True,
        work_packet_carries_low_quality_warning=True,
        worker_packet_carries_in_scope_quality_repair=True,
        worker_packet_escalates_out_of_scope_defects=True,
        evidence_packet_self_corrects_only_own_output=True,
        flowguard_operator_packet_self_corrects_model_only=True,
        reviewer_prompt_forbids_direct_artifact_repair=True,
        generic_packet_template_role_scoped=True,
        route_structure_convergence_review_written=True,
        route_structure_cleanup_targets_named=True,
        allowed_current_runtime_recovery_owned=True,
        node_structure_hygiene_expectation_written=True,
        work_packet_carries_structure_hygiene_delta=True,
        worker_result_reports_structure_hygiene_delta=True,
        final_structure_debt_dispositions_done=True,
        negative_rejection_evidence_separated=True,
        final_low_quality_risks_disposition_done=True,
        final_shallow_completion_traps_disposition_done=True,
        final_output_practical_next_step_confirmed=True,
        child_skill_selected=True,
        skill_standard_contract_compiled=True,
        skill_standard_fields=STANDARD_FIELDS,
        skill_standard_source_paths_recorded=True,
        standards_mapped_to_route_nodes=True,
        standards_mapped_to_work_packets=True,
        standards_mapped_to_reviewer_gates=True,
        standards_mapped_to_expected_artifacts=True,
        loop_verify_artifact_inherited=True,
        process_support_skill_candidate_available=True,
        process_support_skill_decision_recorded=True,
        role_skill_use_binding_written=True,
        role_skill_use_evidence_required=True,
        role_skill_use_evidence_reviewer_check_bound=True,
        node_acceptance_plan_consumes_projection=True,
        work_packet_carries_projection=True,
        result_matrix_required=True,
        reviewer_gate_bound_to_projection=True,
        reviewer_passed_route=True,
    )


def _valid_simple_state() -> State:
    return State(
        status="running",
        scenario=VALID_SIMPLE_ROUTE,
        task_class="simple_bug",
        planning_profile_selected=True,
        planning_profile="simple_repair",
        simple_task_profile_waiver=True,
        route_complexity_matches_profile=True,
        route_nodes_have_stage_artifacts=True,
        pm_user_intent_self_check_written=True,
        pm_improvement_opportunities_classified=True,
        reviewer_passed_route=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_UI_ROUTE:
        return _valid_ui_state()
    if scenario == VALID_SIMPLE_ROUTE:
        return _valid_simple_state()

    state = replace(_valid_ui_state(), scenario=scenario)
    if scenario == UI_WITHOUT_PROFILE:
        return replace(state, planning_profile_selected=False, planning_profile="none")
    if scenario == PROFILE_WITHOUT_CONVERGENCE_LOOP:
        return replace(state, required_convergence_loop_planned=False)
    if scenario == SKILL_SELECTED_NO_CONTRACT:
        return replace(state, skill_standard_contract_compiled=False)
    if scenario == SKILL_CONTRACT_MISSING_FIELDS:
        return replace(state, skill_standard_fields=STANDARD_FIELDS - frozenset({"DEFAULT", "LOOP"}))
    if scenario == SKILL_CONTRACT_NOT_MAPPED:
        return replace(
            state,
            standards_mapped_to_route_nodes=False,
            standards_mapped_to_work_packets=False,
            standards_mapped_to_reviewer_gates=False,
        )
    if scenario == LOOP_VERIFY_ARTIFACT_NOT_INHERITED:
        return replace(state, loop_verify_artifact_inherited=False)
    if scenario == NODE_PLAN_MISSING_PROJECTION:
        return replace(state, node_acceptance_plan_consumes_projection=False)
    if scenario == WORK_PACKET_MISSING_PROJECTION:
        return replace(state, work_packet_carries_projection=False, result_matrix_required=False)
    if scenario == REVIEWER_PASSES_HARD_BLINDSPOT:
        return replace(
            state,
            residual_blindspot_touches_hard_requirement=True,
            residual_blindspot_touches_required_skill_gate=True,
            reviewer_passed_route=True,
            reviewer_blocked_route=False,
        )
    if scenario == OVERMERGED_COMPLEX_IMPLEMENTATION_NODE:
        return replace(state, major_node_overmerged=True, route_complexity_matches_profile=False)
    if scenario == ARTIFACTLESS_MAJOR_NODE:
        return replace(state, route_nodes_have_stage_artifacts=False)
    if scenario == SIMPLE_TASK_OVERTEMPLATED:
        return replace(
            replace(_valid_simple_state(), scenario=scenario),
            simple_task_profile_waiver=False,
            required_convergence_loop_planned=True,
            child_skill_selected=True,
            skill_standard_contract_compiled=True,
            skill_standard_fields=STANDARD_FIELDS,
            simple_task_overtemplated=True,
        )
    if scenario == PRODUCT_MODEL_MISSING:
        return replace(
            state,
            product_behavior_model_written=False,
            product_model_risk_boundary_checked=False,
        )
    if scenario == PM_IMPLEMENTATION_INTENT_MISSING:
        return replace(
            state,
            pm_implementation_intent_written=False,
            pm_implementation_intent_plain_language_guidance=False,
            pm_implementation_intent_names_hard_parts=False,
        )
    if scenario == TARGET_REALIZATION_MODEL_MISSING:
        return replace(
            state,
            target_realization_model_written=False,
            target_realization_model_preserves_pm_intent=False,
            pm_target_realization_model_accepted=False,
        )
    if scenario == TARGET_REALIZATION_MODEL_IGNORES_PM_INTENT:
        return replace(state, target_realization_model_preserves_pm_intent=False)
    if scenario == PM_TARGET_REALIZATION_ACCEPTS_DOWNGRADE:
        return replace(
            state,
            target_realization_model_preserves_pm_intent=False,
            pm_target_realization_model_accepted=True,
        )
    if scenario == REVIEWER_IMPLEMENTATION_INTENT_ALIGNMENT_MISSING:
        return replace(state, reviewer_implementation_intent_alignment_checked=False)
    if scenario == ROUTE_MISSING_REALIZATION_OBLIGATIONS:
        return replace(state, route_consumes_realization_obligations=False)
    if scenario == NODE_PLAN_MISSING_REALIZATION_OBLIGATIONS:
        return replace(state, node_plan_consumes_realization_obligations=False)
    if scenario == WORK_PACKET_MISSING_REALIZATION_OBLIGATIONS:
        return replace(state, work_packet_carries_realization_obligations=False)
    if scenario == FINAL_LEDGER_REALIZATION_OBLIGATIONS_UNRESOLVED:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            final_realization_obligations_disposition_done=False,
        )
    if scenario == ACCEPTANCE_ITEM_REGISTRY_MISSING:
        return replace(
            state,
            acceptance_item_registry_written=False,
            acceptance_registry_has_user_and_pm_items=False,
        )
    if scenario == ACCEPTANCE_ITEM_NO_ROUTE_OWNER:
        return replace(state, acceptance_items_bound_to_route_nodes=False)
    if scenario == NODE_PLAN_MISSING_ACCEPTANCE_ITEM_PROJECTION:
        return replace(state, node_plan_projects_acceptance_items=False)
    if scenario == WORK_PACKET_MISSING_ACCEPTANCE_ITEM_MATRIX:
        return replace(
            state,
            work_packet_carries_acceptance_item_matrix=False,
            pm_disposition_closes_acceptance_items=False,
        )
    if scenario == FINAL_LEDGER_ACCEPTANCE_ITEM_UNRESOLVED:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            final_acceptance_items_disposition_done=False,
        )
    if scenario == STARTUP_QUALITY_POSTURE_MISSING:
        return replace(state, startup_release_projects_quality_posture=False)
    if scenario == PRODUCT_ARCHITECTURE_IGNORES_STARTUP_QUALITY:
        return replace(state, product_architecture_consumes_startup_quality_posture=False)
    if scenario == ROUTE_QUALITY_POSTURE_DROPPED:
        return replace(state, route_preserves_startup_product_quality_posture=False)
    if scenario == PACKET_QUALITY_FLOOR_DROPPED:
        return replace(state, packet_preserves_current_quality_floor=False)
    if scenario == PM_ROUTE_NOT_MAPPED_TO_PRODUCT_MODEL:
        return replace(state, pm_route_maps_to_product_model=False)
    if scenario == PROCESS_FLOWGUARD_OPERATOR_ROUTE_VIABILITY_MISSING:
        return replace(state, flowguard_operator_route_scope_validated_route_viability=False)
    if scenario == REPAIR_NODE_NO_MAINLINE_RETURN:
        return replace(state, repair_return_to_mainline_defined=False)
    if scenario == NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL:
        return replace(state, node_acceptance_plan_maps_product_model_segment=False)
    if scenario == PM_USER_INTENT_SELF_CHECK_MISSING:
        return replace(state, pm_user_intent_self_check_written=False)
    if scenario == PM_HIGHER_STANDARD_SELF_CHECK_MISSING:
        return replace(state, pm_higher_standard_self_check_written=False)
    if scenario == PM_IMPROVEMENT_OPPORTUNITY_UNCLASSIFIED:
        return replace(
            state,
            pm_higher_standard_opportunity_found=True,
            pm_improvement_opportunities_classified=False,
        )
    if scenario == PM_IMPROVEMENT_SCOPE_CREEP:
        return replace(
            state,
            pm_higher_standard_opportunity_found=True,
            pm_improvement_incorrectly_hard_blocker=True,
        )
    if scenario == PM_CLOSURE_USER_OUTCOME_REPLAY_MISSING:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            closure_replays_final_user_outcome=False,
        )
    if scenario == PM_LOW_QUALITY_REVIEW_MISSING:
        return replace(state, pm_low_quality_success_review_written=False)
    if scenario == PM_LOW_QUALITY_REVIEW_GENERIC:
        return replace(
            state,
            pm_low_quality_review_task_specific=False,
            pm_hard_parts_identified=False,
            pm_thin_shortcuts_identified=False,
            pm_proof_of_depth_defined=False,
        )
    if scenario == HARD_LOW_QUALITY_RISK_NO_ROUTE_OWNER:
        return replace(state, hard_low_quality_risks_bound_to_route_nodes=False)
    if scenario == LOW_QUALITY_RISK_CAUSES_ROUTE_BLOAT:
        return replace(state, low_quality_review_caused_unjustified_route_node=True)
    if scenario == PM_SHALLOW_COMPLETION_TRAPS_MISSING:
        return replace(state, shallow_completion_traps_named=False)
    if scenario == PRACTICAL_OUTCOME_DESIGN_ONLY_ROUTE:
        return replace(
            state,
            route_dominated_by_design_only_nodes=True,
            shallow_completion_traps_bound_to_route_work=False,
            route_produces_practical_next_step_evidence=False,
        )
    if scenario == NODE_PLAN_MISSING_LOW_QUALITY_MAPPING:
        return replace(
            state,
            node_acceptance_low_quality_mapping_written=False,
            node_acceptance_proof_of_depth_defined=False,
        )
    if scenario == NODE_PLAN_MISSING_CURRENT_CHECK_SURFACE:
        return replace(
            state,
            node_acceptance_current_check_surface_written=False,
            node_acceptance_status_vocabulary_written=False,
            node_acceptance_expected_failure_shape_written=False,
            node_acceptance_worker_outcome_bounded=False,
        )
    if scenario == WORK_PACKET_MISSING_LOW_QUALITY_WARNING:
        return replace(state, work_packet_carries_low_quality_warning=False)
    if scenario == PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            final_low_quality_risks_disposition_done=False,
        )
    if scenario == PM_CLOSURE_SHALLOW_COMPLETION_TRAPS_UNRESOLVED:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            final_shallow_completion_traps_disposition_done=False,
            final_output_practical_next_step_confirmed=False,
        )
    if scenario == PROCESS_SUPPORT_SKILL_IGNORED:
        return replace(
            state,
            process_support_skill_candidate_available=True,
            process_support_skill_decision_recorded=False,
        )
    if scenario == ROLE_SKILL_BINDING_MISSING:
        return replace(
            state,
            role_skill_use_binding_written=False,
            role_skill_use_evidence_required=False,
            role_skill_use_evidence_reviewer_check_bound=False,
        )
    if scenario == ROLE_SKILL_USE_SELF_ATTESTED:
        return replace(
            state,
            role_skill_use_self_attested_without_evidence=True,
            role_skill_use_evidence_required=False,
            role_skill_use_evidence_reviewer_check_bound=False,
        )
    if scenario == WORKER_PACKET_MISSING_IN_SCOPE_REPAIR:
        return replace(state, worker_packet_carries_in_scope_quality_repair=False)
    if scenario == WORKER_PACKET_REPAIRS_OUT_OF_SCOPE:
        return replace(state, worker_packet_escalates_out_of_scope_defects=False)
    if scenario == EVIDENCE_PACKET_REPAIRS_TARGET_ARTIFACT:
        return replace(state, evidence_packet_self_corrects_only_own_output=False)
    if scenario == FLOWGUARD_OPERATOR_PACKET_REPAIRS_TARGET_ARTIFACT:
        return replace(state, flowguard_operator_packet_self_corrects_model_only=False)
    if scenario == REVIEWER_PROMPT_GRANTS_DIRECT_REPAIR:
        return replace(state, reviewer_prompt_forbids_direct_artifact_repair=False)
    if scenario == GENERIC_TEMPLATE_USES_BLANKET_REPAIR:
        return replace(state, generic_packet_template_role_scoped=False)
    if scenario == PM_STRUCTURE_CONVERGENCE_REVIEW_MISSING:
        return replace(
            state,
            route_structure_convergence_review_written=False,
            route_structure_cleanup_targets_named=False,
            allowed_current_runtime_recovery_owned=False,
        )
    if scenario == NODE_PLAN_MISSING_STRUCTURE_HYGIENE_EXPECTATION:
        return replace(state, node_structure_hygiene_expectation_written=False)
    if scenario == WORK_PACKET_MISSING_STRUCTURE_HYGIENE_DELTA:
        return replace(
            state,
            work_packet_carries_structure_hygiene_delta=False,
            worker_result_reports_structure_hygiene_delta=False,
        )
    if scenario == WORKER_RESULT_LEAVES_UNOWNED_FALLBACK:
        return replace(state, worker_result_retains_unowned_fallback=True)
    if scenario == REPAIR_LEAVES_COMPAT_BRANCH:
        return replace(state, repair_path_retains_compatibility_branch=True)
    if scenario == FINAL_LEDGER_STRUCTURE_DEBT_UNRESOLVED:
        return replace(
            state,
            closure_or_final_ledger_decision=True,
            final_structure_debt_dispositions_done=False,
            final_structure_debt_has_unresolved_entries=True,
        )
    return state


def planning_failures(state: State) -> list[str]:
    failures: list[str] = []

    complex_task = state.task_class not in {"simple_bug", "unset"}
    if complex_task and not state.startup_release_projects_quality_posture:
        failures.append("startup release does not carry high-quality current-run posture into PM product and route work")
    if complex_task and not state.product_architecture_consumes_startup_quality_posture:
        failures.append("product architecture does not consume startup high-quality posture")
    if complex_task and not state.route_preserves_startup_product_quality_posture:
        failures.append("route design lowered the startup/product quality floor")
    if complex_task and not state.packet_preserves_current_quality_floor:
        failures.append("work packet does not preserve the current quality floor")
    if complex_task and not state.planning_profile_selected:
        failures.append("complex task route lacks a selected planning profile")
    if state.planning_profile_selected and not state.route_complexity_matches_profile:
        failures.append("route complexity does not match selected planning profile")
    if state.task_class == "ui_product" and not state.required_convergence_loop_planned:
        failures.append("interactive UI route lacks required convergence loop")
    if complex_task and state.major_node_overmerged:
        failures.append("complex implementation work was overmerged into one unverifiable node")
    if complex_task and not state.route_nodes_have_stage_artifacts:
        failures.append("major route node lacks a concrete acceptance artifact")
    if complex_task and not (
        state.product_behavior_model_written and state.product_model_risk_boundary_checked
    ):
        failures.append("route planning lacks a product behavior model from the FlowGuard operator product-scope")
    if complex_task and not (
        state.pm_implementation_intent_written
        and state.pm_implementation_intent_plain_language_guidance
        and state.pm_implementation_intent_names_hard_parts
    ):
        failures.append("PM implementation intent bridge is missing or too thin before route skeleton")
    if complex_task and not state.target_realization_model_written:
        failures.append("FlowGuard target-realization model is missing before route skeleton")
    if complex_task and not state.target_realization_model_preserves_pm_intent:
        failures.append("target-realization model does not preserve PM implementation intent")
    if (
        complex_task
        and state.pm_target_realization_model_accepted
        and not state.target_realization_model_preserves_pm_intent
    ):
        failures.append("PM accepted a target-realization model that downgrades implementation intent")
    if complex_task and not state.pm_target_realization_model_accepted:
        failures.append("PM has not accepted the target-realization model before route skeleton")
    if complex_task and not state.reviewer_implementation_intent_alignment_checked:
        failures.append("Reviewer did not check implementation-intent and target-realization alignment")
    if complex_task and not state.route_consumes_realization_obligations:
        failures.append("route skeleton does not consume target-realization obligations")
    if complex_task and not state.node_plan_consumes_realization_obligations:
        failures.append("node acceptance plan does not consume target-realization obligations")
    if complex_task and not state.work_packet_carries_realization_obligations:
        failures.append("work packet does not carry target-realization obligations")
    if complex_task and not state.final_realization_obligations_disposition_done:
        failures.append("final ledger or closure leaves target-realization obligations unresolved")
    if complex_task and not (
        state.acceptance_item_registry_written
        and state.acceptance_registry_has_user_and_pm_items
    ):
        failures.append("PM high-standard contract lacks acceptance item registry with user and PM high-standard items")
    if complex_task and not state.acceptance_items_bound_to_route_nodes:
        failures.append("active acceptance item lacks a route node owner")
    if complex_task and not state.node_plan_projects_acceptance_items:
        failures.append("node acceptance plan lacks acceptance item projection")
    if complex_task and not state.work_packet_carries_acceptance_item_matrix:
        failures.append("work packet or result lacks acceptance item result matrix")
    if complex_task and not state.pm_disposition_closes_acceptance_items:
        failures.append("PM disposition does not close node-owned acceptance items")
    if complex_task and state.closure_or_final_ledger_decision and not state.final_acceptance_items_disposition_done:
        failures.append("final ledger or closure leaves acceptance items unresolved")
    if complex_task and not state.pm_route_maps_to_product_model:
        failures.append("PM route is not mapped to the product behavior model")
    if complex_task and not state.flowguard_operator_route_scope_validated_route_viability:
        failures.append("FlowGuard operator route-scope did not validate route viability against the product model")
    if complex_task and not state.repair_return_to_mainline_defined:
        failures.append("repair node lacks a defined return to the mainline product route")
    if complex_task and not state.node_acceptance_plan_maps_product_model_segment:
        failures.append("node acceptance plan is not mapped to a product model segment")
    if complex_task and not state.pm_user_intent_self_check_written:
        failures.append("PM plan lacks final-user intent and product usefulness self-check")
    if complex_task and not state.pm_higher_standard_self_check_written:
        failures.append("PM plan lacks higher-standard improvement-space self-check")
    if (
        complex_task
        and state.pm_higher_standard_opportunity_found
        and not state.pm_improvement_opportunities_classified
    ):
        failures.append("PM left higher-standard improvement opportunity unclassified")
    if state.pm_improvement_incorrectly_hard_blocker:
        failures.append("PM treated a nonblocking higher-standard improvement as a hard current-gate requirement")
    if complex_task and not state.pm_low_quality_success_review_written:
        failures.append("PM product architecture lacks low-quality-success review")
    if complex_task and state.pm_low_quality_success_review_written and not (
        state.pm_low_quality_review_task_specific
        and state.pm_hard_parts_identified
        and state.pm_thin_shortcuts_identified
        and state.pm_proof_of_depth_defined
    ):
        failures.append("PM low-quality-success review is generic or lacks hard parts, thin shortcuts, and proof of depth")
    if complex_task and not state.hard_low_quality_risks_bound_to_route_nodes:
        failures.append("hard low-quality-success risk lacks an existing route or node owner")
    if state.low_quality_review_caused_unjustified_route_node:
        failures.append("PM created unjustified route bloat from low-quality-success review")
    if complex_task and state.practical_next_step_required and not state.shallow_completion_traps_named:
        failures.append("PM did not name the task-specific shallow-completion traps")
    if (
        complex_task
        and state.practical_next_step_required
        and state.route_dominated_by_design_only_nodes
        and not state.route_produces_practical_next_step_evidence
    ):
        failures.append("practical user outcome was planned as a design-only route without next-step evidence")
    if (
        complex_task
        and state.practical_next_step_required
        and not state.shallow_completion_traps_bound_to_route_work
    ):
        failures.append("current shallow-completion traps lack route work, scoped waiver, or blocker")
    if complex_task and not (
        state.node_acceptance_low_quality_mapping_written
        and state.node_acceptance_proof_of_depth_defined
    ):
        failures.append("node acceptance plan lacks local low-quality-success mapping and proof of depth")
    if complex_task and not (
        state.node_acceptance_current_check_surface_written
        and state.node_acceptance_status_vocabulary_written
        and state.node_acceptance_expected_failure_shape_written
        and state.node_acceptance_worker_outcome_bounded
    ):
        failures.append("node acceptance plan lacks current executable check surface, status vocabulary, expected failure shape, or bounded worker outcome")
    if complex_task and not state.work_packet_carries_low_quality_warning:
        failures.append("work packet lacks node low-quality-success warning")
    if complex_task and not state.worker_packet_carries_in_scope_quality_repair:
        failures.append("executable worker packet lacks in-scope quality repair obligation")
    if complex_task and not state.worker_packet_escalates_out_of_scope_defects:
        failures.append("worker packet does not escalate out-of-scope defects to PM")
    if complex_task and not state.evidence_packet_self_corrects_only_own_output:
        failures.append("research or material-scan packet grants target artifact repair instead of report self-correction")
    if complex_task and not state.flowguard_operator_packet_self_corrects_model_only:
        failures.append("FlowGuard operator packet grants target artifact repair instead of model/report self-correction")
    if complex_task and not state.reviewer_prompt_forbids_direct_artifact_repair:
        failures.append("reviewer prompt grants direct repair authority over the reviewed artifact")
    if complex_task and not state.generic_packet_template_role_scoped:
        failures.append("generic packet template uses blanket repair wording instead of role-scoped authority")
    if complex_task and not (
        state.route_structure_convergence_review_written
        and state.route_structure_cleanup_targets_named
        and state.allowed_current_runtime_recovery_owned
    ):
        failures.append("PM route lacks structural convergence review for cleanup targets and owned current-runtime recovery")
    if complex_task and not state.node_structure_hygiene_expectation_written:
        failures.append("node acceptance plan lacks structure hygiene expectation")
    if complex_task and not state.work_packet_carries_structure_hygiene_delta:
        failures.append("work packet lacks structure hygiene delta obligation")
    if complex_task and not state.worker_result_reports_structure_hygiene_delta:
        failures.append("worker result lacks structure hygiene delta")
    if state.worker_result_retains_unowned_fallback:
        failures.append("worker result retained an unowned fallback or compatibility path")
    if state.repair_path_retains_compatibility_branch:
        failures.append("repair path retained a compatibility branch instead of reissuing or blocking current structured work")
    if complex_task and not state.negative_rejection_evidence_separated:
        failures.append("negative rejection evidence is not separated from current completion evidence")
    if (
        complex_task
        and state.closure_or_final_ledger_decision
        and not state.closure_replays_final_user_outcome
    ):
        failures.append("PM closure lacks final-user outcome replay")
    if (
        complex_task
        and state.closure_or_final_ledger_decision
        and not state.final_low_quality_risks_disposition_done
    ):
        failures.append("PM closure lacks low-quality-success risk disposition")
    if (
        complex_task
        and state.closure_or_final_ledger_decision
        and state.practical_next_step_required
        and not (
            state.final_shallow_completion_traps_disposition_done
            and state.final_output_practical_next_step_confirmed
        )
    ):
        failures.append("PM closure leaves shallow-completion traps unresolved for the final user")
    if (
        complex_task
        and state.closure_or_final_ledger_decision
        and (
            not state.final_structure_debt_dispositions_done
            or state.final_structure_debt_has_unresolved_entries
        )
    ):
        failures.append("final ledger leaves structural debt unresolved")

    if state.child_skill_selected:
        if not state.skill_standard_contract_compiled:
            failures.append("selected child skill lacks a compiled Skill Standard Contract")
        missing_fields = STANDARD_FIELDS - state.skill_standard_fields
        if missing_fields:
            failures.append("Skill Standard Contract omits required fields")
        if not state.skill_standard_source_paths_recorded:
            failures.append("Skill Standard Contract lacks source paths")
        if not (
            state.standards_mapped_to_route_nodes
            and state.standards_mapped_to_work_packets
            and state.standards_mapped_to_reviewer_gates
            and state.standards_mapped_to_expected_artifacts
        ):
            failures.append("Skill Standard Contract is not mapped through route, packet, reviewer, and artifact obligations")
        if not state.loop_verify_artifact_inherited:
            failures.append("LOOP/VERIFY/ARTIFACT standards were not inherited into execution")
        if not state.node_acceptance_plan_consumes_projection:
            failures.append("node acceptance plan lacks skill-standard projection")
        if not (state.work_packet_carries_projection and state.result_matrix_required):
            failures.append("work packet or result matrix lacks skill-standard projection")
        if not state.reviewer_gate_bound_to_projection:
            failures.append("reviewer gate is not bound to skill-standard projection")
    if (
        state.process_support_skill_candidate_available
        and not state.process_support_skill_decision_recorded
    ):
        failures.append("PM child-skill selection did not evaluate process-support skill candidates")
    if state.child_skill_selected and not (
        state.role_skill_use_binding_written
        and state.role_skill_use_evidence_required
        and state.role_skill_use_evidence_reviewer_check_bound
    ):
        failures.append("selected process-support skill lacks role-skill binding, evidence requirement, or reviewer check")
    if state.role_skill_use_self_attested_without_evidence:
        failures.append("selected role skill use was self-attested without evidence")

    hard_blindspot = (
        state.residual_blindspot_touches_hard_requirement
        or state.residual_blindspot_touches_required_skill_gate
    )
    if hard_blindspot and state.reviewer_passed_route and not state.reviewer_blocked_route:
        failures.append("reviewer passed a residual blindspot that touches a hard requirement or required child-skill gate")

    if state.task_class == "simple_bug" and (
        state.planning_profile_selected
        or state.simple_task_profile_waiver
        or state.simple_task_overtemplated
        or state.child_skill_selected
        or state.required_convergence_loop_planned
    ):
        failures.append("small/simple task entered formal FlowPilot instead of staying outside FlowPilot")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = planning_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="planning_quality_contract_ok"),
        )


def accepts_only_valid_plans(state: State, trace) -> InvariantResult:
    del trace
    failures = planning_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid planning-quality route was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid planning-quality route was rejected")
    return InvariantResult.pass_()


def profile_matches_task_complexity(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "planning profile" in failure or "route complexity" in failure or "overmerged" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def startup_quality_posture_projects_to_route(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "startup" in failure or "quality floor" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def skill_standards_are_projected(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "Skill Standard Contract" in failure or "skill-standard projection" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def reviewer_blocks_hard_blindspots(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "residual blindspot" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def small_tasks_do_not_enter_formal_flowpilot(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "small/simple task entered formal FlowPilot" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def product_model_drives_route_planning(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "product behavior model" in failure or "product model" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def repairs_rejoin_mainline(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "repair node" in failure or "mainline" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def pm_self_checks_user_value_and_standard(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if (
            "final-user" in failure
            or "higher-standard" in failure
            or "nonblocking" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def low_quality_success_risks_are_owned(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if (
            "low-quality-success" in failure
            or "proof of depth" in failure
            or "route bloat" in failure
            or "shallow-completion" in failure
            or "design-only route" in failure
            or "next-step evidence" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def quality_repair_prompts_preserve_role_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if (
            "in-scope quality repair" in failure
            or "out-of-scope defects" in failure
            or "target artifact repair" in failure
            or "direct repair authority" in failure
            or "blanket repair wording" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def role_skill_use_is_evidence_bound(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if (
            "process-support skill" in failure
            or "role-skill binding" in failure
            or "self-attested" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def structure_hygiene_converges_before_closure(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if (
            "structural convergence" in failure
            or "structure hygiene" in failure
            or "structure debt" in failure
            or "unowned fallback" in failure
            or "compatibility branch" in failure
            or "negative rejection evidence" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_plans",
        description="Only planning routes with profile, standards, projection, and blocking reviewer gates can be accepted.",
        predicate=accepts_only_valid_plans,
    ),
    Invariant(
        name="profile_matches_task_complexity",
        description="Task profile and route complexity must match the requested quality level.",
        predicate=profile_matches_task_complexity,
    ),
    Invariant(
        name="startup_quality_posture_projects_to_route",
        description="Startup release must carry high-quality current-run posture through product architecture, route design, and packets.",
        predicate=startup_quality_posture_projects_to_route,
    ),
    Invariant(
        name="skill_standards_are_projected",
        description="Compiled child-skill standards must project into route, node, packet, reviewer, and result boundaries.",
        predicate=skill_standards_are_projected,
    ),
    Invariant(
        name="reviewer_blocks_hard_blindspots",
        description="Reviewer cannot pass hard requirement or required child-skill gate blindspots as residual risk.",
        predicate=reviewer_blocks_hard_blindspots,
    ),
    Invariant(
        name="small_tasks_do_not_enter_formal_flowpilot",
        description="Small/simple tasks must stay outside formal FlowPilot instead of creating light/simple profiles.",
        predicate=small_tasks_do_not_enter_formal_flowpilot,
    ),
    Invariant(
        name="product_model_drives_route_planning",
        description="Complex routes require a product behavior model, PM route mapping, process-FlowGuard operator viability check, and node mapping.",
        predicate=product_model_drives_route_planning,
    ),
    Invariant(
        name="repairs_rejoin_mainline",
        description="Repair nodes must define how they return to the mainline product route before acceptance.",
        predicate=repairs_rejoin_mainline,
    ),
    Invariant(
        name="pm_self_checks_user_value_and_standard",
        description="PM must self-check final-user value and classify higher-standard improvements without scope creep.",
        predicate=pm_self_checks_user_value_and_standard,
    ),
    Invariant(
        name="low_quality_success_risks_are_owned",
        description="PM must identify hard parts, bind low-quality-success risks to existing route/node owners, project them into node plans and worker packets, and disposition them before closure.",
        predicate=low_quality_success_risks_are_owned,
    ),
    Invariant(
        name="quality_repair_prompts_preserve_role_authority",
        description="Executable worker packets require in-scope repair while evidence, FlowGuard operator, reviewer, and generic prompts preserve role authority boundaries.",
        predicate=quality_repair_prompts_preserve_role_authority,
    ),
    Invariant(
        name="role_skill_use_is_evidence_bound",
        description="Process-support child skills must be considered by PM and bound to role-specific evidence and reviewer checks when selected.",
        predicate=role_skill_use_is_evidence_bound,
    ),
    Invariant(
        name="structure_hygiene_converges_before_closure",
        description="Route, node, packet, result, repair, and final ledger surfaces must dispose of fallback-like structural debt before acceptance.",
        predicate=structure_hygiene_converges_before_closure,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((PlanningQualityStep(),), name="flowpilot_planning_quality")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not planning_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
