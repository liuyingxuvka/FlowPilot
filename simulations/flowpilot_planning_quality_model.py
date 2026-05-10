"""FlowGuard model for FlowPilot planning-quality gates.

Risk intent brief:
- Validate the minimal FlowPilot planning repair before prompt cards or
  templates are changed.
- Protected harms: high-fidelity UI or other complex tasks being planned as a
  generic implementation node, child-skill standards being selected but not
  compiled into route/node/work-packet obligations, reviewer hard-requirement
  blindspots being recorded as harmless residual risk, product FlowGuard
  modeling being treated as an after-the-fact review instead of PM route input,
  repair nodes failing to reconnect to the mainline, and simple tasks being
  over-templated.
- Modeled state and side effects: PM planning profile selection, child-skill
  standard compilation, root product behavior model availability, PM route and
  node mapping to that model, process-officer route viability checks, reviewer
  blocking, and simple-task waiver discipline.
- Hard invariants: accepted routes must have a matching planning profile or a
  simple-task waiver, skill standards must expose MUST/DEFAULT/FORBID/VERIFY/
  LOOP/ARTIFACT/WAIVER, inherited standards must be visible at route, node,
  packet, reviewer, and result-matrix boundaries, PM route drafts must be based
  on the product behavior model, process-officer checks must validate route
  viability against that model including repair return-to-mainline, and hard
  requirement blindspots cannot pass.
- Blindspot: this model checks the process contract shape. Runtime cards,
  templates, and tests must still be updated and validated after the model
  passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_UI_ROUTE = "valid_ui_route"
VALID_SIMPLE_ROUTE = "valid_simple_route"

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
PROCESS_OFFICER_ROUTE_VIABILITY_MISSING = "process_officer_route_viability_missing"
REPAIR_NODE_NO_MAINLINE_RETURN = "repair_node_no_mainline_return"
NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL = "node_plan_not_mapped_to_product_model"

VALID_SCENARIOS = (VALID_UI_ROUTE, VALID_SIMPLE_ROUTE)
NEGATIVE_SCENARIOS = (
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
    PROCESS_OFFICER_ROUTE_VIABILITY_MISSING,
    REPAIR_NODE_NO_MAINLINE_RETURN,
    NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL,
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

    planning_profile_selected: bool = False
    planning_profile: str = "none"
    simple_task_profile_waiver: bool = False
    route_complexity_matches_profile: bool = False
    required_convergence_loop_planned: bool = False
    route_nodes_have_stage_artifacts: bool = False
    major_node_overmerged: bool = False
    product_behavior_model_written: bool = False
    product_model_risk_boundary_checked: bool = False
    pm_route_maps_to_product_model: bool = False
    process_officer_validated_route_viability: bool = False
    repair_return_to_mainline_defined: bool = False
    node_acceptance_plan_maps_product_model_segment: bool = False

    child_skill_selected: bool = False
    skill_standard_contract_compiled: bool = False
    skill_standard_fields: frozenset[str] = field(default_factory=frozenset)
    skill_standard_source_paths_recorded: bool = False
    standards_mapped_to_route_nodes: bool = False
    standards_mapped_to_work_packets: bool = False
    standards_mapped_to_reviewer_gates: bool = False
    standards_mapped_to_expected_artifacts: bool = False
    loop_verify_artifact_inherited: bool = False

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
        planning_profile_selected=True,
        planning_profile="interactive_software_ui_product",
        route_complexity_matches_profile=True,
        required_convergence_loop_planned=True,
        route_nodes_have_stage_artifacts=True,
        product_behavior_model_written=True,
        product_model_risk_boundary_checked=True,
        pm_route_maps_to_product_model=True,
        process_officer_validated_route_viability=True,
        repair_return_to_mainline_defined=True,
        node_acceptance_plan_maps_product_model_segment=True,
        child_skill_selected=True,
        skill_standard_contract_compiled=True,
        skill_standard_fields=STANDARD_FIELDS,
        skill_standard_source_paths_recorded=True,
        standards_mapped_to_route_nodes=True,
        standards_mapped_to_work_packets=True,
        standards_mapped_to_reviewer_gates=True,
        standards_mapped_to_expected_artifacts=True,
        loop_verify_artifact_inherited=True,
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
    if scenario == PM_ROUTE_NOT_MAPPED_TO_PRODUCT_MODEL:
        return replace(state, pm_route_maps_to_product_model=False)
    if scenario == PROCESS_OFFICER_ROUTE_VIABILITY_MISSING:
        return replace(state, process_officer_validated_route_viability=False)
    if scenario == REPAIR_NODE_NO_MAINLINE_RETURN:
        return replace(state, repair_return_to_mainline_defined=False)
    if scenario == NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL:
        return replace(state, node_acceptance_plan_maps_product_model_segment=False)
    return state


def planning_failures(state: State) -> list[str]:
    failures: list[str] = []

    complex_task = state.task_class not in {"simple_bug", "unset"}
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
        failures.append("route planning lacks a product behavior model from the Product FlowGuard Officer")
    if complex_task and not state.pm_route_maps_to_product_model:
        failures.append("PM route is not mapped to the product behavior model")
    if complex_task and not state.process_officer_validated_route_viability:
        failures.append("Process FlowGuard Officer did not validate route viability against the product model")
    if complex_task and not state.repair_return_to_mainline_defined:
        failures.append("repair node lacks a defined return to the mainline product route")
    if complex_task and not state.node_acceptance_plan_maps_product_model_segment:
        failures.append("node acceptance plan is not mapped to a product model segment")

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

    hard_blindspot = (
        state.residual_blindspot_touches_hard_requirement
        or state.residual_blindspot_touches_required_skill_gate
    )
    if hard_blindspot and state.reviewer_passed_route and not state.reviewer_blocked_route:
        failures.append("reviewer passed a residual blindspot that touches a hard requirement or required child-skill gate")

    if state.task_class == "simple_bug" and (
        state.simple_task_overtemplated
        or (state.child_skill_selected and not state.simple_task_profile_waiver)
        or state.required_convergence_loop_planned
    ):
        failures.append("simple task was over-templated instead of using a justified lightweight profile")

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


def simple_tasks_stay_lightweight(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in planning_failures(state):
        if "simple task was over-templated" in failure:
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
        name="simple_tasks_stay_lightweight",
        description="Simple tasks must not receive heavyweight UI/product planning loops without justification.",
        predicate=simple_tasks_stay_lightweight,
    ),
    Invariant(
        name="product_model_drives_route_planning",
        description="Complex routes require a product behavior model, PM route mapping, process-officer viability check, and node mapping.",
        predicate=product_model_drives_route_planning,
    ),
    Invariant(
        name="repairs_rejoin_mainline",
        description="Repair nodes must define how they return to the mainline product route before acceptance.",
        predicate=repairs_rejoin_mainline,
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
