"""FlowGuard parent model for FlowPilot project-control information sufficiency.

Risk intent brief:
- Review whether every project-control continuation path carries enough current
  information for the next actor to make real progress.
- Covered surfaces: ordinary repair work packets, interruption/manual resume,
  reopened continuation runs, Controller break-glass repair, route mutation,
  on-demand role assignment/replacement, follow-up blockers, repeated same-work
  loops, and closure.
- Protected harm: FlowPilot appears busy but repeats the previous work because
  the PM runway, repair packet, role assignment/replacement packet,
  break-glass incident, or route mutation omitted the current blocker, new
  repair direction, executable evidence contract, or stale-evidence
  disposition.
- Hard invariant: any nonterminal next action must either carry current run
  state plus a new information delta to a single owner, or stop/mutate/record a
  current blocker. Historical state is allowed only as history, never as the
  current authority for progress.
- Blindspot: this model checks the parent information contract. Focused child
  models and runtime tests still own concrete packet schemas, cards, and
  command behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_project_control_information_flow"
MAX_SEQUENCE_LENGTH = 3

VALID_REPAIR_PACKET_PROGRESS = "valid_repair_packet_progress"
VALID_INTERRUPT_RESUME_WITH_BLOCKER_CONTEXT = "valid_interrupt_resume_with_blocker_context"
VALID_REOPEN_IMPORTS_HISTORY_AND_CURRENT_RUN = "valid_reopen_imports_history_and_current_run"
VALID_BREAK_GLASS_CONTROL_REPAIR = "valid_break_glass_control_repair"
VALID_ROUTE_MUTATION_WITH_REPLAY_SCOPE = "valid_route_mutation_with_replay_scope"
VALID_ROLE_ASSIGNMENT_REISSUES_CURRENT_PACKET = "valid_role_assignment_reissues_current_packet"
VALID_TERMINAL_STOP_PRESERVES_UNRESOLVED_WORK = "valid_terminal_stop_preserves_unresolved_work"
VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF = "valid_packet_contract_and_review_evidence_handoff"
VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT = "valid_actor_handoff_material_and_report_contract"

RESUME_FROM_CHAT_HISTORY_LOSES_BLOCKER = "resume_from_chat_history_loses_blocker"
RESUME_LOADS_OLD_RUN_AS_CURRENT = "resume_loads_old_run_as_current"
REOPEN_REUSES_OLD_AGENT_IDS_AS_CURRENT = "reopen_reuses_old_agent_ids_as_current"
PM_RUNWAY_OMITS_ACTIVE_BLOCKER = "pm_runway_omits_active_blocker"
WORK_PACKET_LACKS_MINIMUM_INFORMATION = "work_packet_lacks_minimum_information"
SAME_WORK_REPEATED_WITH_NO_NEW_INFO = "same_work_repeated_with_no_new_info"
BREAK_GLASS_WITHOUT_NORMAL_REPAIR_FAILURE = "break_glass_without_normal_repair_failure"
BREAK_GLASS_UNBOUNDED_OR_TARGET_PROJECT_REPAIR = "break_glass_unbounded_or_target_project_repair"
BREAK_GLASS_BYPASSES_PM_REVIEWER_REINTEGRATION = "break_glass_bypasses_pm_reviewer_reintegration"
ROUTE_MUTATION_OMITS_BLOCKER_OR_ACCEPTANCE_PLAN = "route_mutation_omits_blocker_or_acceptance_plan"
ROUTE_MUTATION_DOES_NOT_INVALIDATE_STALE_EVIDENCE = "route_mutation_does_not_invalidate_stale_evidence"
ROLE_ASSIGNMENT_WITHOUT_CURRENT_PACKET_CONTEXT = "role_assignment_without_current_packet_context"
FOLLOWUP_BLOCKER_NOT_PROPAGATED_TO_NEXT_RUNWAY = "followup_blocker_not_propagated_to_next_runway"
FINAL_CLOSURE_WITH_UNRESOLVED_INFORMATION_GAP = "final_closure_with_unresolved_information_gap"
HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT = "historical_evidence_promoted_to_current"
PACKET_RESULT_CONTRACT_NOT_VISIBLE_TO_ROLE = "packet_result_contract_not_visible_to_role"
FLOWGUARD_EVIDENCE_NOT_BOUND_TO_REVIEWER = "flowguard_evidence_not_bound_to_reviewer"
BLOCKER_REPAIR_STAGE_HIDDEN_FROM_STATUS = "blocker_repair_stage_hidden_from_status"
SYNTHETIC_TRACE_BYPASSES_VISIBLE_CONTRACT = "synthetic_trace_bypasses_visible_contract"
WORK_PACKET_MISSING_INPUT_MATERIALS = "work_packet_missing_input_materials"
WORK_PACKET_MISSING_REPORT_REQUIREMENTS = "work_packet_missing_report_requirements"
DOWNSTREAM_REPORT_NOT_AUTHORIZED = "downstream_report_not_authorized"
MISSING_INFO_RESPONSE_NOT_DEFINED = "missing_info_response_not_defined"
BRANCH_CONTRACT_SHAPE_NOT_VISIBLE = "branch_contract_shape_not_visible"

VALID_SCENARIOS = (
    VALID_REPAIR_PACKET_PROGRESS,
    VALID_INTERRUPT_RESUME_WITH_BLOCKER_CONTEXT,
    VALID_REOPEN_IMPORTS_HISTORY_AND_CURRENT_RUN,
    VALID_BREAK_GLASS_CONTROL_REPAIR,
    VALID_ROUTE_MUTATION_WITH_REPLAY_SCOPE,
    VALID_ROLE_ASSIGNMENT_REISSUES_CURRENT_PACKET,
    VALID_TERMINAL_STOP_PRESERVES_UNRESOLVED_WORK,
    VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF,
    VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT,
)

NEGATIVE_SCENARIOS = (
    RESUME_FROM_CHAT_HISTORY_LOSES_BLOCKER,
    RESUME_LOADS_OLD_RUN_AS_CURRENT,
    REOPEN_REUSES_OLD_AGENT_IDS_AS_CURRENT,
    PM_RUNWAY_OMITS_ACTIVE_BLOCKER,
    WORK_PACKET_LACKS_MINIMUM_INFORMATION,
    SAME_WORK_REPEATED_WITH_NO_NEW_INFO,
    BREAK_GLASS_WITHOUT_NORMAL_REPAIR_FAILURE,
    BREAK_GLASS_UNBOUNDED_OR_TARGET_PROJECT_REPAIR,
    BREAK_GLASS_BYPASSES_PM_REVIEWER_REINTEGRATION,
    ROUTE_MUTATION_OMITS_BLOCKER_OR_ACCEPTANCE_PLAN,
    ROUTE_MUTATION_DOES_NOT_INVALIDATE_STALE_EVIDENCE,
    ROLE_ASSIGNMENT_WITHOUT_CURRENT_PACKET_CONTEXT,
    FOLLOWUP_BLOCKER_NOT_PROPAGATED_TO_NEXT_RUNWAY,
    FINAL_CLOSURE_WITH_UNRESOLVED_INFORMATION_GAP,
    HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT,
    PACKET_RESULT_CONTRACT_NOT_VISIBLE_TO_ROLE,
    FLOWGUARD_EVIDENCE_NOT_BOUND_TO_REVIEWER,
    BLOCKER_REPAIR_STAGE_HIDDEN_FROM_STATUS,
    SYNTHETIC_TRACE_BYPASSES_VISIBLE_CONTRACT,
    WORK_PACKET_MISSING_INPUT_MATERIALS,
    WORK_PACKET_MISSING_REPORT_REQUIREMENTS,
    DOWNSTREAM_REPORT_NOT_AUTHORIZED,
    MISSING_INFO_RESPONSE_NOT_DEFINED,
    BRANCH_CONTRACT_SHAPE_NOT_VISIBLE,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One project-control information-sufficiency evaluation."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    surface: str = "none"

    current_run_loaded: bool = False
    active_run_id_current: bool = False
    frontier_loaded: bool = False
    packet_ledger_loaded: bool = False
    active_blocker_loaded: bool = False
    current_packet_context_loaded: bool = False
    role_assignment_current_or_replaced: bool = False
    historical_state_imported_as_history_only: bool = True
    old_evidence_marked_historical: bool = True
    historical_evidence_used_as_current: bool = False

    pm_runway_requested: bool = False
    pm_runway_recorded: bool = False
    pm_runway_references_current_state: bool = False
    pm_runway_includes_active_blocker: bool = False
    pm_runway_names_next_owner: bool = False
    pm_runway_names_next_command_or_packet: bool = False

    work_packet_issued: bool = False
    work_packet_current_generation: bool = False
    work_packet_names_owner: bool = False
    work_packet_names_objective: bool = False
    work_packet_carries_current_blocker: bool = False
    work_packet_carries_new_repair_direction: bool = False
    work_packet_carries_allowed_reads_writes: bool = False
    work_packet_carries_forbidden_actions: bool = False
    work_packet_carries_success_evidence: bool = False
    work_packet_disposes_stale_context: bool = False
    work_packet_carries_output_contract: bool = False
    work_packet_carries_minimal_valid_result_shape: bool = False
    work_packet_carries_forbidden_result_fields: bool = False
    work_packet_carries_input_material_manifest: bool = False
    work_packet_carries_required_report_contract: bool = False
    work_packet_carries_branch_valid_shapes: bool = False
    work_packet_names_downstream_consumer: bool = False
    work_packet_names_missing_info_response: bool = False
    result_report_submitted: bool = False
    result_report_satisfies_required_contract: bool = False
    downstream_packet_authorized_to_read_report: bool = False
    new_information_delta_present: bool = False
    synthetic_trace_uses_hidden_contract: bool = False

    flowguard_gate_required: bool = False
    flowguard_result_current_for_subject: bool = False
    flowguard_evidence_manifest_attached: bool = False
    flowguard_evidence_subject_matches_result: bool = False
    reviewer_packet_issued: bool = False
    reviewer_packet_authorized_to_read_subject_result: bool = False
    reviewer_packet_authorized_to_read_flowguard_evidence: bool = False
    reviewer_packet_names_flowguard_evidence_id: bool = False

    blocker_repair_chain_open: bool = False
    blocker_status_reflects_current_stage: bool = False
    status_projection_shows_repair_chain: bool = False

    repeated_same_work: bool = False
    loop_escape_or_blocker_recorded: bool = False

    followup_blocker_returned: bool = False
    followup_blocker_recorded: bool = False
    followup_blocker_in_next_runway: bool = False

    break_glass_used: bool = False
    normal_repair_path_failed: bool = False
    break_glass_incident_recorded: bool = False
    break_glass_bounded_reads_writes: bool = False
    break_glass_control_plane_only: bool = True
    break_glass_target_project_repair: bool = False
    break_glass_pm_authorized: bool = False
    break_glass_validation_evidence: bool = False
    break_glass_reenters_normal_flow: bool = False
    reviewer_or_pm_recheck_after_break_glass: bool = False

    route_mutation_used: bool = False
    route_mutation_references_blocker: bool = False
    route_version_advanced: bool = False
    stale_evidence_invalidated: bool = False
    replacement_acceptance_plan_created: bool = False
    replay_scope_declared: bool = False

    role_assignment_used: bool = False
    requested_role_known: bool = False
    assigned_role_bound_to_current_task: bool = False
    old_agent_id_treated_as_current: bool = False

    terminal_stop_recorded: bool = False
    unresolved_work_visible: bool = False
    closure_claimed: bool = False
    unresolved_information_gap_present: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _base_current(**changes: object) -> State:
    return replace(
        State(
            status="running",
            current_run_loaded=True,
            active_run_id_current=True,
            frontier_loaded=True,
            packet_ledger_loaded=True,
            active_blocker_loaded=True,
            current_packet_context_loaded=True,
            role_assignment_current_or_replaced=True,
            historical_state_imported_as_history_only=True,
            old_evidence_marked_historical=True,
            pm_runway_requested=True,
            pm_runway_recorded=True,
            pm_runway_references_current_state=True,
            pm_runway_includes_active_blocker=True,
            pm_runway_names_next_owner=True,
            pm_runway_names_next_command_or_packet=True,
        ),
        **changes,
    )


def _base_work_packet(**changes: object) -> State:
    return replace(
        _base_current(
            work_packet_issued=True,
            work_packet_current_generation=True,
            work_packet_names_owner=True,
            work_packet_names_objective=True,
            work_packet_carries_current_blocker=True,
            work_packet_carries_new_repair_direction=True,
            work_packet_carries_allowed_reads_writes=True,
            work_packet_carries_forbidden_actions=True,
            work_packet_carries_success_evidence=True,
            work_packet_disposes_stale_context=True,
            work_packet_carries_output_contract=True,
            work_packet_carries_minimal_valid_result_shape=True,
            work_packet_carries_forbidden_result_fields=True,
            work_packet_carries_input_material_manifest=True,
            work_packet_carries_required_report_contract=True,
            work_packet_carries_branch_valid_shapes=True,
            work_packet_names_downstream_consumer=True,
            work_packet_names_missing_info_response=True,
            result_report_submitted=True,
            result_report_satisfies_required_contract=True,
            downstream_packet_authorized_to_read_report=True,
            new_information_delta_present=True,
        ),
        **changes,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_REPAIR_PACKET_PROGRESS:
        return replace(_base_work_packet(), scenario=scenario, surface="repair_packet")
    if scenario == VALID_INTERRUPT_RESUME_WITH_BLOCKER_CONTEXT:
        return replace(_base_work_packet(), scenario=scenario, surface="interrupt_resume")
    if scenario == VALID_REOPEN_IMPORTS_HISTORY_AND_CURRENT_RUN:
        return replace(_base_work_packet(), scenario=scenario, surface="reopen")
    if scenario == VALID_BREAK_GLASS_CONTROL_REPAIR:
        return replace(
            _base_current(),
            scenario=scenario,
            surface="break_glass",
            break_glass_used=True,
            normal_repair_path_failed=True,
            break_glass_incident_recorded=True,
            break_glass_bounded_reads_writes=True,
            break_glass_control_plane_only=True,
            break_glass_target_project_repair=False,
            break_glass_pm_authorized=True,
            break_glass_validation_evidence=True,
            break_glass_reenters_normal_flow=True,
            reviewer_or_pm_recheck_after_break_glass=True,
            new_information_delta_present=True,
        )
    if scenario == VALID_ROUTE_MUTATION_WITH_REPLAY_SCOPE:
        return replace(
            _base_current(),
            scenario=scenario,
            surface="route_mutation",
            route_mutation_used=True,
            route_mutation_references_blocker=True,
            route_version_advanced=True,
            stale_evidence_invalidated=True,
            replacement_acceptance_plan_created=True,
            replay_scope_declared=True,
            new_information_delta_present=True,
        )
    if scenario == VALID_ROLE_ASSIGNMENT_REISSUES_CURRENT_PACKET:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="role_assignment",
            role_assignment_used=True,
            requested_role_known=True,
            assigned_role_bound_to_current_task=True,
        )
    if scenario == VALID_TERMINAL_STOP_PRESERVES_UNRESOLVED_WORK:
        return replace(
            _base_current(),
            scenario=scenario,
            surface="terminal_stop",
            terminal_stop_recorded=True,
            unresolved_work_visible=True,
            closure_claimed=False,
            new_information_delta_present=False,
        )
    if scenario == VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="packet_review_handoff",
            flowguard_gate_required=True,
            flowguard_result_current_for_subject=True,
            flowguard_evidence_manifest_attached=True,
            flowguard_evidence_subject_matches_result=True,
            reviewer_packet_issued=True,
            reviewer_packet_authorized_to_read_subject_result=True,
            reviewer_packet_authorized_to_read_flowguard_evidence=True,
            reviewer_packet_names_flowguard_evidence_id=True,
            blocker_repair_chain_open=True,
            blocker_status_reflects_current_stage=True,
            status_projection_shows_repair_chain=True,
        )
    if scenario == VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="actor_handoff",
        )

    if scenario == RESUME_FROM_CHAT_HISTORY_LOSES_BLOCKER:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="interrupt_resume",
            current_run_loaded=False,
            frontier_loaded=False,
            packet_ledger_loaded=False,
            active_blocker_loaded=False,
            pm_runway_references_current_state=False,
        )
    if scenario == RESUME_LOADS_OLD_RUN_AS_CURRENT:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="interrupt_resume",
            active_run_id_current=False,
            historical_state_imported_as_history_only=False,
            historical_evidence_used_as_current=True,
        )
    if scenario == REOPEN_REUSES_OLD_AGENT_IDS_AS_CURRENT:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="reopen",
            role_assignment_used=True,
            requested_role_known=True,
            role_assignment_current_or_replaced=False,
            assigned_role_bound_to_current_task=False,
            old_agent_id_treated_as_current=True,
        )
    if scenario == PM_RUNWAY_OMITS_ACTIVE_BLOCKER:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            pm_runway_includes_active_blocker=False,
            work_packet_carries_current_blocker=False,
        )
    if scenario == WORK_PACKET_LACKS_MINIMUM_INFORMATION:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            work_packet_names_objective=False,
            work_packet_carries_allowed_reads_writes=False,
            work_packet_carries_success_evidence=False,
        )
    if scenario == SAME_WORK_REPEATED_WITH_NO_NEW_INFO:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            repeated_same_work=True,
            new_information_delta_present=False,
            loop_escape_or_blocker_recorded=False,
        )
    if scenario == BREAK_GLASS_WITHOUT_NORMAL_REPAIR_FAILURE:
        return replace(
            _scenario_state(VALID_BREAK_GLASS_CONTROL_REPAIR),
            scenario=scenario,
            normal_repair_path_failed=False,
        )
    if scenario == BREAK_GLASS_UNBOUNDED_OR_TARGET_PROJECT_REPAIR:
        return replace(
            _scenario_state(VALID_BREAK_GLASS_CONTROL_REPAIR),
            scenario=scenario,
            break_glass_bounded_reads_writes=False,
            break_glass_control_plane_only=False,
            break_glass_target_project_repair=True,
        )
    if scenario == BREAK_GLASS_BYPASSES_PM_REVIEWER_REINTEGRATION:
        return replace(
            _scenario_state(VALID_BREAK_GLASS_CONTROL_REPAIR),
            scenario=scenario,
            break_glass_pm_authorized=False,
            break_glass_validation_evidence=False,
            break_glass_reenters_normal_flow=False,
            reviewer_or_pm_recheck_after_break_glass=False,
        )
    if scenario == ROUTE_MUTATION_OMITS_BLOCKER_OR_ACCEPTANCE_PLAN:
        return replace(
            _scenario_state(VALID_ROUTE_MUTATION_WITH_REPLAY_SCOPE),
            scenario=scenario,
            route_mutation_references_blocker=False,
            replacement_acceptance_plan_created=False,
            replay_scope_declared=False,
        )
    if scenario == ROUTE_MUTATION_DOES_NOT_INVALIDATE_STALE_EVIDENCE:
        return replace(
            _scenario_state(VALID_ROUTE_MUTATION_WITH_REPLAY_SCOPE),
            scenario=scenario,
            stale_evidence_invalidated=False,
        )
    if scenario == ROLE_ASSIGNMENT_WITHOUT_CURRENT_PACKET_CONTEXT:
        return replace(
            _scenario_state(VALID_ROLE_ASSIGNMENT_REISSUES_CURRENT_PACKET),
            scenario=scenario,
            requested_role_known=False,
            current_packet_context_loaded=False,
            assigned_role_bound_to_current_task=False,
        )
    if scenario == FOLLOWUP_BLOCKER_NOT_PROPAGATED_TO_NEXT_RUNWAY:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            followup_blocker_returned=True,
            followup_blocker_recorded=True,
            followup_blocker_in_next_runway=False,
            pm_runway_includes_active_blocker=False,
        )
    if scenario == FINAL_CLOSURE_WITH_UNRESOLVED_INFORMATION_GAP:
        return replace(
            _base_current(),
            scenario=scenario,
            surface="closure",
            closure_claimed=True,
            unresolved_information_gap_present=True,
            unresolved_work_visible=False,
        )
    if scenario == HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT:
        return replace(
            _base_work_packet(),
            scenario=scenario,
            surface="repair_packet",
            historical_state_imported_as_history_only=False,
            old_evidence_marked_historical=False,
            historical_evidence_used_as_current=True,
        )
    if scenario == PACKET_RESULT_CONTRACT_NOT_VISIBLE_TO_ROLE:
        return replace(
            _scenario_state(VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF),
            scenario=scenario,
            work_packet_carries_output_contract=False,
            work_packet_carries_minimal_valid_result_shape=False,
            work_packet_carries_forbidden_result_fields=False,
        )
    if scenario == FLOWGUARD_EVIDENCE_NOT_BOUND_TO_REVIEWER:
        return replace(
            _scenario_state(VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF),
            scenario=scenario,
            flowguard_evidence_manifest_attached=False,
            flowguard_evidence_subject_matches_result=False,
            reviewer_packet_authorized_to_read_flowguard_evidence=False,
            reviewer_packet_names_flowguard_evidence_id=False,
        )
    if scenario == BLOCKER_REPAIR_STAGE_HIDDEN_FROM_STATUS:
        return replace(
            _scenario_state(VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF),
            scenario=scenario,
            blocker_status_reflects_current_stage=False,
            status_projection_shows_repair_chain=False,
        )
    if scenario == SYNTHETIC_TRACE_BYPASSES_VISIBLE_CONTRACT:
        return replace(
            _scenario_state(VALID_PACKET_CONTRACT_AND_REVIEW_EVIDENCE_HANDOFF),
            scenario=scenario,
            work_packet_carries_output_contract=False,
            synthetic_trace_uses_hidden_contract=True,
        )
    if scenario == WORK_PACKET_MISSING_INPUT_MATERIALS:
        return replace(
            _scenario_state(VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT),
            scenario=scenario,
            work_packet_carries_input_material_manifest=False,
        )
    if scenario == WORK_PACKET_MISSING_REPORT_REQUIREMENTS:
        return replace(
            _scenario_state(VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT),
            scenario=scenario,
            work_packet_carries_required_report_contract=False,
            result_report_satisfies_required_contract=False,
        )
    if scenario == DOWNSTREAM_REPORT_NOT_AUTHORIZED:
        return replace(
            _scenario_state(VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT),
            scenario=scenario,
            work_packet_names_downstream_consumer=False,
            downstream_packet_authorized_to_read_report=False,
        )
    if scenario == MISSING_INFO_RESPONSE_NOT_DEFINED:
        return replace(
            _scenario_state(VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT),
            scenario=scenario,
            work_packet_names_missing_info_response=False,
        )
    if scenario == BRANCH_CONTRACT_SHAPE_NOT_VISIBLE:
        return replace(
            _scenario_state(VALID_ACTOR_HANDOFF_MATERIAL_AND_REPORT_CONTRACT),
            scenario=scenario,
            work_packet_carries_branch_valid_shapes=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def information_sufficiency_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.historical_evidence_used_as_current or not (
        state.historical_state_imported_as_history_only and state.old_evidence_marked_historical
    ):
        failures.append("historical state or evidence was promoted to current authority")

    if state.surface in {"interrupt_resume", "reopen", "role_assignment", "repair_packet", "route_mutation", "break_glass", "closure", "terminal_stop"}:
        if not (state.current_run_loaded and state.active_run_id_current and state.frontier_loaded and state.packet_ledger_loaded):
            failures.append("current run, frontier, and packet ledger were not loaded before next action")

    if state.active_blocker_loaded and state.pm_runway_recorded:
        if not (
            state.pm_runway_references_current_state
            and state.pm_runway_includes_active_blocker
            and state.pm_runway_names_next_owner
            and state.pm_runway_names_next_command_or_packet
        ):
            failures.append("PM runway lacks current state, active blocker, next owner, or executable command")

    if state.work_packet_issued:
        if not state.pm_runway_recorded:
            failures.append("work packet issued without PM runway")
        if not state.work_packet_current_generation:
            failures.append("work packet is not a fresh current generation")
        if not (
            state.work_packet_names_owner
            and state.work_packet_names_objective
            and state.work_packet_carries_current_blocker
            and state.work_packet_carries_new_repair_direction
            and state.work_packet_carries_allowed_reads_writes
            and state.work_packet_carries_forbidden_actions
            and state.work_packet_carries_success_evidence
            and state.work_packet_disposes_stale_context
        ):
            failures.append("work packet lacks minimum executable information")
        if not (
            state.work_packet_carries_output_contract
            and state.work_packet_carries_minimal_valid_result_shape
            and state.work_packet_carries_forbidden_result_fields
        ):
            failures.append("work packet lacks role-visible result output contract, minimal valid shape, or forbidden fields")
        if not state.work_packet_carries_input_material_manifest:
            failures.append("work packet lacks the required input material manifest for the actor")
        if not state.work_packet_carries_required_report_contract:
            failures.append("work packet lacks required report contract for the actor output")
        if not state.work_packet_carries_branch_valid_shapes:
            failures.append("work packet lacks branch-specific current result shapes for branch outputs")
        if not state.work_packet_names_downstream_consumer:
            failures.append("work packet does not name the downstream consumer for its report")
        if not state.work_packet_names_missing_info_response:
            failures.append("work packet does not define the current-runtime response when required information is missing")
        if state.result_report_submitted and not state.result_report_satisfies_required_contract:
            failures.append("submitted report does not satisfy the packet's required report contract")
        if state.result_report_submitted and not state.downstream_packet_authorized_to_read_report:
            failures.append("downstream packet is not authorized to read the required report")
        if not state.new_information_delta_present and not state.loop_escape_or_blocker_recorded:
            failures.append("work packet has no new information delta and no loop escape")
        if state.synthetic_trace_uses_hidden_contract:
            failures.append("synthetic trace used hidden success contract instead of visible packet output contract")

    if state.flowguard_gate_required:
        if not (
            state.flowguard_result_current_for_subject
            and state.flowguard_evidence_manifest_attached
            and state.flowguard_evidence_subject_matches_result
        ):
            failures.append("FlowGuard evidence handoff lacks current subject result, attached evidence manifest, or subject-result match")
        if state.reviewer_packet_issued and not (
            state.reviewer_packet_authorized_to_read_subject_result
            and state.reviewer_packet_authorized_to_read_flowguard_evidence
            and state.reviewer_packet_names_flowguard_evidence_id
        ):
            failures.append("reviewer packet lacks authorized subject result and FlowGuard evidence reads")

    if state.blocker_repair_chain_open and not (
        state.blocker_status_reflects_current_stage and state.status_projection_shows_repair_chain
    ):
        failures.append("blocker repair chain stage is hidden or stale in status projection")

    if state.repeated_same_work and not (
        state.new_information_delta_present or state.loop_escape_or_blocker_recorded
    ):
        failures.append("same work repeated without new information, blocker, terminal stop, or route mutation")

    if state.followup_blocker_returned and not (
        state.followup_blocker_recorded and state.followup_blocker_in_next_runway
    ):
        failures.append("follow-up blocker did not propagate into the next PM runway")

    if state.break_glass_used:
        if not state.normal_repair_path_failed:
            failures.append("break-glass used before normal PM/control-blocker repair was proven blocked")
        if not (state.break_glass_incident_recorded and state.break_glass_bounded_reads_writes):
            failures.append("break-glass incident lacks record or bounded reads/writes")
        if not state.break_glass_control_plane_only or state.break_glass_target_project_repair:
            failures.append("break-glass attempted target-project repair instead of control-plane repair")
        if not (
            state.break_glass_pm_authorized
            and state.break_glass_validation_evidence
            and state.break_glass_reenters_normal_flow
            and state.reviewer_or_pm_recheck_after_break_glass
        ):
            failures.append("break-glass did not reintegrate through PM/reviewer validation")

    if state.route_mutation_used:
        if not (
            state.route_mutation_references_blocker
            and state.route_version_advanced
            and state.stale_evidence_invalidated
            and state.replacement_acceptance_plan_created
            and state.replay_scope_declared
        ):
            failures.append("route mutation lacks blocker context, new route version, stale-evidence invalidation, acceptance plan, or replay scope")

    if state.role_assignment_used:
        if not (
            state.requested_role_known
            and state.current_packet_context_loaded
            and state.role_assignment_current_or_replaced
            and state.assigned_role_bound_to_current_task
        ):
            failures.append("role assignment lacks requested role, packet context, or current-task binding")
        if state.old_agent_id_treated_as_current:
            failures.append("old agent id was treated as current role-binding evidence")

    if state.closure_claimed and state.unresolved_information_gap_present:
        failures.append("closure was claimed with unresolved information gap")

    if state.terminal_stop_recorded and not state.unresolved_work_visible:
        failures.append("terminal stop did not preserve unresolved work visibility")

    return failures


class ProjectControlInformationFlowStep:
    """Model one project-control information-sufficiency transition.

    Input x State -> Set(Output x State)
    reads: current run, frontier, packet ledger, active blocker, PM runway,
    work packet, role assignment, break-glass incident, route mutation, follow-up
    blocker, actor input material manifest, required report contract,
    FlowGuard evidence handoff, reviewer packet reads, and closure state
    writes: accepted information flow, explicit rejection, terminal stop,
    route mutation, or current follow-up blocker
    idempotency: current run id plus current packet/blocker generation decide
    whether repeated work is progress or stale replay.
    """

    name = "ProjectControlInformationFlowStep"
    input_description = "project-control information sufficiency tick"
    output_description = "accepted continuation or rejected insufficient-information path"
    reads = (
        "current_run",
        "execution_frontier",
        "packet_ledger",
        "active_blocker",
        "pm_runway",
        "work_packet",
        "role_assignment",
        "break_glass_incident",
        "route_mutation",
        "closure_state",
    )
    writes = (
        "information_flow_decision",
        "next_action_permission",
        "followup_blocker",
        "route_mutation_gate",
        "terminal_stop",
    )
    idempotency = "run-id and blocker/packet-generation scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return
    failures = information_sufficiency_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="information_sufficient"),
    )


def accepted_paths_are_information_sufficient(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = information_sufficiency_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def historical_state_is_not_current_authority(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.historical_evidence_used_as_current:
        return InvariantResult.fail("accepted historical evidence as current authority")
    return InvariantResult.pass_()


def nonterminal_work_has_new_information(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.work_packet_issued:
        if not state.new_information_delta_present and not state.loop_escape_or_blocker_recorded:
            return InvariantResult.fail("accepted work packet without new information or loop escape")
    return InvariantResult.pass_()


def break_glass_rejoins_normal_validation(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.break_glass_used:
        if not (
            state.normal_repair_path_failed
            and state.break_glass_bounded_reads_writes
            and state.break_glass_control_plane_only
            and state.break_glass_pm_authorized
            and state.break_glass_validation_evidence
            and state.break_glass_reenters_normal_flow
            and state.reviewer_or_pm_recheck_after_break_glass
        ):
            return InvariantResult.fail("accepted unsafe break-glass information flow")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_paths_are_information_sufficient",
        description="Accepted project-control paths carry current run state, active blockers, next owner, executable work, and evidence boundaries.",
        predicate=accepted_paths_are_information_sufficient,
    ),
    Invariant(
        name="historical_state_is_not_current_authority",
        description="Historical state and old evidence cannot become current progress authority.",
        predicate=historical_state_is_not_current_authority,
    ),
    Invariant(
        name="nonterminal_work_has_new_information",
        description="Nonterminal work packets need new information or an explicit loop escape/blocker.",
        predicate=nonterminal_work_has_new_information,
    ),
    Invariant(
        name="break_glass_rejoins_normal_validation",
        description="Break-glass repair stays bounded, control-plane only, PM-authorized, validated, and reintegrated.",
        predicate=break_glass_rejoins_normal_validation,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def build_workflow() -> Workflow:
    return Workflow((ProjectControlInformationFlowStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"accepted", "rejected"}


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


EXTERNAL_INPUTS = (Tick(),)


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "information_sufficiency_failures",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
