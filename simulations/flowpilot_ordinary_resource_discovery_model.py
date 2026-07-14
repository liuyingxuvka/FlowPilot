"""Focused FlowGuard child model for ordinary resource discovery.

The current `task.discovery` family remains the sole preplanning discovery
path. Runtime projects a shallow local skill/capability inventory; PM selects
relevant candidates and deeply reads only selected skills. Material work is
ordinary role work, while the material artifact map is optional navigation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, NamedTuple

from flowguard import (
    ArchitectureReductionCandidate,
    ArchitectureReductionPlan,
    ArchitectureReductionTrigger,
    FunctionResult,
    Invariant,
    InvariantResult,
    ObservableArchitectureContract,
    Workflow,
    review_architecture_reduction,
)
try:
    from .flowpilot_behavior_authority import resolve_behavior_authority
except ImportError:  # direct script execution
    from flowpilot_behavior_authority import resolve_behavior_authority


MODEL_ID = "flowpilot_ordinary_resource_discovery"
MAX_SEQUENCE_LENGTH = 20
DISCOVERY_AUTHORITY = resolve_behavior_authority(
    "commit.local_capability_inventory_precedes_pm_selection"
)
MATERIAL_MAP_AUTHORITY = resolve_behavior_authority(
    "commit.material_map_is_optional_navigation_only"
)


@dataclass(frozen=True)
class Tick:
    """One discovery/resource transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    material_work_needed: bool = False
    material_map_present: bool = False
    runtime_shallow_inventory_projected: bool = False
    inventory_paths_current: bool = False
    inventory_availability_current: bool = False
    runtime_deep_read_all_skills: bool = False
    pm_candidate_selection_recorded: bool = False
    selected_skills_deep_read: bool = False
    selected_skill_obligations_written: bool = False
    pm_material_need_decision_recorded: bool = False
    ordinary_role_work_packet_issued: bool = False
    ordinary_role_work_result_submitted: bool = False
    risk_appropriate_review_completed: bool = False
    material_map_treated_as_optional: bool = True
    planning_ready: bool = False

    # Known-bad compatibility and authority paths.
    dedicated_material_gate_required: bool = False
    dedicated_material_result_family_used: bool = False
    material_sources_discovery_field_accepted: bool = False
    material_sufficiency_discovery_field_accepted: bool = False
    removed_field_translated_or_defaulted: bool = False
    map_absence_blocks: bool = False
    ordinary_material_work_bypasses_review: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_states() -> tuple[State, ...]:
    return tuple(
        State(material_work_needed=material_needed, material_map_present=map_present)
        for material_needed in (False, True)
        for map_present in (False, True)
    )


class OrdinaryResourceDiscoveryStep:
    """Input x State -> Set(Output x State) for current resource discovery.

    Reads packet-only Runtime inventory, PM selection and ordinary work state.
    Writes only abstract discovery progress; it owns no material ledger or
    special material gate.
    """

    name = "OrdinaryResourceDiscoveryStep"
    reads = (
        "runtime_shallow_inventory_projected",
        "pm_candidate_selection_recorded",
        "selected_skills_deep_read",
        "pm_material_need_decision_recorded",
        "ordinary_role_work_result_submitted",
    )
    writes = (
        "packet_only_local_inventory",
        "pm_candidate_selection",
        "selected_skill_obligations",
        "ordinary_role_work",
        "optional_material_map_disposition",
        "planning_ready",
    )
    input_description = "one current resource-discovery tick"
    output_description = "one monotonic discovery or ordinary-work action"
    idempotency = "no tick creates a special material state family"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("resource_discovery_blocks_on_invariant_failure", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("ordinary_resource_discovery_started", replace(state, status="running")),)
    if not state.runtime_shallow_inventory_projected:
        return (
            Transition(
                "runtime_projects_shallow_local_skill_inventory",
                replace(
                    state,
                    runtime_shallow_inventory_projected=True,
                    inventory_paths_current=True,
                    inventory_availability_current=True,
                ),
            ),
        )
    if not state.pm_candidate_selection_recorded:
        return (Transition("pm_selects_relevant_skill_candidates", replace(state, pm_candidate_selection_recorded=True)),)
    if not state.selected_skills_deep_read:
        return (
            Transition(
                "pm_deep_reads_only_selected_skills",
                replace(state, selected_skills_deep_read=True, selected_skill_obligations_written=True),
            ),
        )
    if not state.pm_material_need_decision_recorded:
        return (
            Transition(
                "pm_decides_whether_ordinary_material_work_is_needed",
                replace(state, pm_material_need_decision_recorded=True),
            ),
        )
    if state.material_work_needed:
        if not state.ordinary_role_work_packet_issued:
            return (Transition("pm_issues_ordinary_role_work_packet", replace(state, ordinary_role_work_packet_issued=True)),)
        if not state.ordinary_role_work_result_submitted:
            return (
                Transition(
                    "evidence_role_submits_ordinary_work_result",
                    replace(state, ordinary_role_work_result_submitted=True),
                ),
            )
        if not state.risk_appropriate_review_completed:
            return (
                Transition(
                    "ordinary_material_work_receives_risk_appropriate_review",
                    replace(state, risk_appropriate_review_completed=True),
                ),
            )
    if not state.planning_ready:
        return (
            Transition(
                "optional_material_map_is_navigation_only",
                replace(state, material_map_treated_as_optional=True, planning_ready=True),
            ),
        )
    return (Transition("ordinary_resource_discovery_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.dedicated_material_gate_required:
        failures.append("mandatory dedicated material gate re-entered the current path")
    if state.dedicated_material_result_family_used:
        failures.append("dedicated material result family became current authority")
    if state.material_sources_discovery_field_accepted:
        failures.append("removed material_sources discovery field was accepted")
    if state.material_sufficiency_discovery_field_accepted:
        failures.append("removed material_sufficiency discovery field was accepted")
    if state.removed_field_translated_or_defaulted:
        failures.append("removed discovery material field was translated or defaulted")
    if state.runtime_deep_read_all_skills:
        failures.append("Runtime deep-read every discovered skill instead of shallow inventory")
    if state.pm_candidate_selection_recorded and not state.runtime_shallow_inventory_projected:
        failures.append("PM selected skills before current Runtime inventory projection")
    if state.selected_skills_deep_read and not state.pm_candidate_selection_recorded:
        failures.append("skills were deeply read before PM relevance selection")
    if state.selected_skills_deep_read and not state.selected_skill_obligations_written:
        failures.append("selected skill deep read produced no reviewer-checkable obligations")
    if state.ordinary_role_work_packet_issued and not state.pm_material_need_decision_recorded:
        failures.append("ordinary material work started without PM need decision")
    if state.ordinary_role_work_result_submitted and not state.ordinary_role_work_packet_issued:
        failures.append("material result bypassed the ordinary role-work packet")
    if state.ordinary_material_work_bypasses_review:
        failures.append("risk-applicable ordinary material work bypassed existing review")
    if state.material_work_needed and state.planning_ready and not state.risk_appropriate_review_completed:
        failures.append("planning advanced before required ordinary material work review")
    if state.map_absence_blocks or (not state.material_map_present and not state.material_map_treated_as_optional):
        failures.append("optional material artifact-map absence blocked the flow")
    if state.planning_ready:
        if not state.runtime_shallow_inventory_projected:
            failures.append("planning advanced without mandatory local skill inventory")
        if not state.inventory_paths_current or not state.inventory_availability_current:
            failures.append("planning advanced with stale or incomplete inventory projection")
        if not state.pm_candidate_selection_recorded:
            failures.append("planning advanced without PM skill relevance selection")
        if not state.selected_skills_deep_read or not state.selected_skill_obligations_written:
            failures.append("planning advanced before selected skills became obligations")
    if state.status == "complete" and not state.planning_ready:
        failures.append("resource discovery completed before planning readiness")
    return failures


def invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_ordinary_resource_discovery",
        description=(
            "Runtime shallow-inventories local skills, PM selects and deeply reads relevant skills, "
            "material work uses ordinary packets, and the material map stays optional."
        ),
        predicate=invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((OrdinaryResourceDiscoveryStep(),), name=MODEL_ID)


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def success_state(*, material_work_needed: bool, material_map_present: bool) -> State:
    return State(
        status="complete",
        material_work_needed=material_work_needed,
        material_map_present=material_map_present,
        runtime_shallow_inventory_projected=True,
        inventory_paths_current=True,
        inventory_availability_current=True,
        pm_candidate_selection_recorded=True,
        selected_skills_deep_read=True,
        selected_skill_obligations_written=True,
        pm_material_need_decision_recorded=True,
        ordinary_role_work_packet_issued=material_work_needed,
        ordinary_role_work_result_submitted=material_work_needed,
        risk_appropriate_review_completed=material_work_needed,
        material_map_treated_as_optional=True,
        planning_ready=True,
    )


def hazard_states() -> dict[str, State]:
    base = success_state(material_work_needed=True, material_map_present=False)
    return {
        "missing_local_inventory": replace(base, runtime_shallow_inventory_projected=False),
        "stale_inventory_paths": replace(base, inventory_paths_current=False),
        "runtime_deep_reads_all_skills": replace(base, runtime_deep_read_all_skills=True),
        "missing_pm_selection": replace(base, pm_candidate_selection_recorded=False),
        "missing_selected_skill_obligations": replace(base, selected_skill_obligations_written=False),
        "dedicated_material_gate": replace(base, dedicated_material_gate_required=True),
        "dedicated_material_result": replace(base, dedicated_material_result_family_used=True),
        "old_material_sources_field": replace(base, material_sources_discovery_field_accepted=True),
        "old_material_sufficiency_field": replace(base, material_sufficiency_discovery_field_accepted=True),
        "old_field_translation": replace(base, removed_field_translated_or_defaulted=True),
        "ordinary_packet_bypassed": replace(base, ordinary_role_work_packet_issued=False),
        "ordinary_review_bypassed": replace(base, ordinary_material_work_bypasses_review=True),
        "map_absence_blocks": replace(base, map_absence_blocks=True),
    }


def build_architecture_reduction_plan() -> ArchitectureReductionPlan:
    return ArchitectureReductionPlan(
        reduction_id="flowpilot_material_discovery_path_contraction",
        observable_contract=ObservableArchitectureContract(
            source_model_id=MODEL_ID,
            source_code_boundary_id="flowpilot_current_preplanning_discovery",
            public_entrypoints=("skills/flowpilot/assets/flowpilot_new.py",),
            observable_outputs=(
                "current local skill inventory",
                "PM candidate skill selection",
                "selected skill obligations",
                "ordinary evidence work results when requested",
            ),
            observable_state=("preplanning_discovery", "skill_standard_contract"),
            observable_side_effects=("issue current discovery and ordinary role-work packets",),
            validation_boundaries=(
                "python simulations/run_flowpilot_ordinary_resource_discovery_checks.py",
                "python -m unittest -v tests.test_flowpilot_ordinary_resource_discovery",
            ),
            rationale=(
                "Preserve capability discovery while removing material-specific current authority and state."
            ),
        ),
        companion_route_triggers=(
            ArchitectureReductionTrigger(
                "development_process_flow",
                trigger_reason=(
                    "Discovery removes behavior-bearing material fields, so DevelopmentProcessFlow "
                    "must route field accounting to the existing FieldLifecycleMesh owner."
                ),
                complexity_signal="positive, negative and historical material names coexist",
                recommended_timing="before runtime edits and after source residue audit",
                required=True,
            ),
            ArchitectureReductionTrigger(
                "model_test_alignment",
                trigger_reason="The narrowed family must remain aligned with validators, fake AI and tests.",
                complexity_signal="one family is consumed by several parents",
                recommended_timing="after focused implementation",
                required=True,
            ),
            ArchitectureReductionTrigger(
                "structure_mesh",
                trigger_reason=(
                    "Retained task.discovery and optional material-map public "
                    "facades must preserve one owner and delegation parity."
                ),
                complexity_signal="two retained public facades delegate to exact owner contracts",
                recommended_timing="with focused facade parity validation",
                required=True,
            ),
        ),
        candidates=(
            ArchitectureReductionCandidate(
                candidate_id="remove_mandatory_material_scan_stage",
                candidate_type="remove_branch",
                code_node_id="mandatory_material_scan_startup_path",
                source_model_element="ordinary material role-work equivalence",
                target_action="remove",
                proof_status="safe_by_equivalence",
                required_next_route="model_test_alignment",
                rationale="Ordinary PM role-work already owns requested reading, research and evidence collection.",
                evidence_refs=("test:flowpilot_ordinary_resource_discovery",),
            ),
            ArchitectureReductionCandidate(
                candidate_id="remove_discovery_material_fields",
                candidate_type="remove_branch",
                code_node_id="task.discovery.material_sources_and_sufficiency",
                source_model_element="current discovery result contract",
                target_action="remove",
                proof_status="safe_by_equivalence",
                required_next_route="model_test_alignment",
                rationale="The fields do not own unique mechanics and incorrectly make material work mandatory.",
                evidence_refs=("negative_test:old_material_discovery_shape_rejected",),
            ),
            ArchitectureReductionCandidate(
                candidate_id="merge_material_sufficiency_review",
                candidate_type="merge_handlers",
                code_node_id="dedicated_material_sufficiency_reviewer",
                source_model_element="existing ordinary Reviewer and FlowGuard review path",
                target_action="merge",
                proof_status="safe_by_equivalence",
                required_next_route="model_test_alignment",
                rationale="Risk-appropriate ordinary work review provides the same independent quality boundary.",
                evidence_refs=("test:ordinary_material_work_uses_existing_review",),
            ),
            ArchitectureReductionCandidate(
                candidate_id="retain_discovery_family_facade",
                candidate_type="keep_public_facade",
                code_node_id="task.discovery",
                source_model_element="packet_result_contracts",
                target_action="keep_facade",
                proof_status="safe_by_public_facade",
                required_next_route="structure_mesh",
                affected_public_entrypoints=("task.discovery",),
                rationale="The family remains the single current capability-discovery path and preserves family parity.",
                evidence_refs=("test:packet_result_family_count_unchanged",),
                completion_evidence_refs=(
                    "test:narrowed_discovery_contract_keeps_one_existing_family",
                    "negative_test:old_material_discovery_shape_rejected",
                ),
                business_intent_id=DISCOVERY_AUTHORITY.business_intent_id,
                behavior_commitment_id=DISCOVERY_AUTHORITY.commitment_id,
                primary_path_id=DISCOVERY_AUTHORITY.primary_path_id,
                inventory_revision=DISCOVERY_AUTHORITY.inventory_revision,
                owner_code_contract_id="resource_discovery.current_result_contract",
                delegates_to_code_contract_id="resource_discovery.current_result_contract",
                delegates_to_primary_path_id=DISCOVERY_AUTHORITY.primary_path_id,
                delegation_evidence_id="resource_discovery.happy.current_inventory_and_ordinary_work",
                delegation_evidence_current=True,
                delegation_only=True,
                independent_business_authority=False,
            ),
            ArchitectureReductionCandidate(
                candidate_id="retain_optional_material_map",
                candidate_type="keep_public_facade",
                code_node_id="material_artifact_map_navigation",
                source_model_element="flowpilot_optional_material_artifact_map.OptionalMaterialArtifactMapStep",
                target_action="keep_facade",
                proof_status="safe_by_public_facade",
                required_next_route="structure_mesh",
                affected_public_entrypoints=(
                    "flowpilot_material_artifact_map.material_artifact_map_navigation_status",
                ),
                rationale="The index is useful when present but cannot own acceptance or stage progression.",
                evidence_refs=("test:material_map_absence_nonblocking",),
                completion_evidence_refs=(
                    "test:existing_map_links_current_navigation",
                    "test:missing_or_noncurrent_map_is_omitted_nonblocking",
                ),
                business_intent_id=MATERIAL_MAP_AUTHORITY.business_intent_id,
                behavior_commitment_id=MATERIAL_MAP_AUTHORITY.commitment_id,
                primary_path_id=MATERIAL_MAP_AUTHORITY.primary_path_id,
                inventory_revision=MATERIAL_MAP_AUTHORITY.inventory_revision,
                owner_code_contract_id="material_artifact_map.navigation_status",
                delegates_to_code_contract_id="material_artifact_map.navigation_status",
                delegates_to_primary_path_id=MATERIAL_MAP_AUTHORITY.primary_path_id,
                delegation_evidence_id="source.material_artifact_map.current_navigation",
                delegation_evidence_current=True,
                delegation_only=True,
                independent_business_authority=False,
            ),
        ),
        rationale="Contract the special material path while retaining the single discovery family and mandatory shallow skill scan.",
    )


def architecture_reduction_report() -> Any:
    return review_architecture_reduction(build_architecture_reduction_plan())
