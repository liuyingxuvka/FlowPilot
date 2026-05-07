"""FlowGuard model for FlowPilot gate-policy and process-friction audits.

Risk intent brief:
- Prevent FlowPilot's safety gates from becoming self-contradictory,
  no-benefit, or counterproductive process obligations.
- Model the policy layer above concrete router mechanics: formal activation
  eligibility, hard gates, mandatory decisions with variable proof methods,
  advisory records, repair escalation, parent replay, generated-resource
  disposition, and transactional state refresh.
- Protected harms include small tasks accidentally entering formal FlowPilot,
  advisory/nonblocking work blocking completion, quality decisions being
  skipped, wrong proof methods being accepted, local defects forcing route
  mutation, temporary diagnostics blocking closure, and split state writes
  creating stale frontier/display/ledger views.
- Adversarial branches are represented as hazard states. The safe graph uses
  risk-adaptive choices and should pass all invariants; each hazard should
  produce a clear counterexample message.
- Blindspot: this model audits control-policy shape. It does not prove product
  quality, UI taste, reviewer judgement quality, or the real runtime's full
  conformance unless paired with source/replay checks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TASK_SMALL = "small"
TASK_COMPLEX = "complex"

RISK_PRODUCT_STATE = "product_state"
RISK_VISUAL_QUALITY = "visual_quality"
RISK_MIXED_PRODUCT_VISUAL = "mixed_product_visual"
RISK_DOCUMENTATION_ONLY = "documentation_only"

METHOD_PRODUCT_FLOWGUARD = "product_flowguard"
METHOD_REVIEWER_WALKTHROUGH = "reviewer_walkthrough"
METHOD_BOTH = "both"
METHOD_LIGHT_REVIEW = "light_review"
METHOD_NOT_NEEDED_WITH_REASON = "not_needed_with_reason"
METHOD_NOT_NEEDED_NO_REASON = "not_needed_no_reason"

ISSUE_NONE = "none"
ISSUE_LOCAL_DEFECT = "local_defect"
ISSUE_ROUTE_INVALIDATING = "route_invalidating"

REPAIR_NONE = "none"
REPAIR_LOCAL = "local_repair"
REPAIR_ROUTE_MUTATION = "route_mutation"

RESOURCE_NONE = "none"
RESOURCE_DIAGNOSTIC_TEMP = "diagnostic_temp"
RESOURCE_DELIVERY_EVIDENCE = "delivery_evidence"


@dataclass(frozen=True)
class Tick:
    """One gate-policy audit tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    task_scale: str = "unknown"  # unknown | small | complex
    formal_flowpilot_started: bool = False
    six_role_crew_started: bool = False

    startup_questions_asked: bool = False
    startup_wait_boundary_recorded: bool = False
    startup_explanatory_text_emitted: bool = False
    startup_side_effects_before_answers: bool = False
    startup_boundary_invalidated_for_text: bool = False

    gate_policy_catalog_written: bool = False
    hard_startup_gate_passed: bool = False
    hard_controller_boundary_passed: bool = False

    quality_risk_decision_done: bool = False
    risk_type: str = "unknown"
    selected_quality_method: str = "none"
    product_flowguard_done: bool = False
    reviewer_walkthrough_done: bool = False
    light_review_done: bool = False
    not_needed_reason_recorded: bool = False

    advisory_observation_missing: bool = True
    advisory_blocks_completion: bool = False

    issue_type: str = "unknown"
    repair_strategy: str = REPAIR_NONE
    local_repair_done: bool = False
    route_mutation_done: bool = False
    stale_evidence_invalidated: bool = False

    parent_has_children: bool = True
    composition_risk: str = "unknown"  # unknown | low | high
    parent_replay_policy: str = "none"  # none | risk_based | structural_hard
    parent_replay_done: bool = False
    parent_replay_waived_with_reason: bool = False
    completion_blocked_by_parent_replay: bool = False

    generated_resource_scope: str = "unknown"
    generated_resource_disposed: bool = False
    generated_resource_excluded_as_diagnostic: bool = False
    generated_resource_blocks_completion: bool = False

    no_benefit_hard_gate_required: bool = False
    hard_gate_safety_delta: str = "unknown"  # unknown | none | prevents_hazard

    stage_advanced: bool = False
    frontier_updated: bool = False
    display_updated: bool = False
    ledger_updated: bool = False
    blocker_index_updated: bool = False

    completion_review_passed: bool = False
    completion_recorded: bool = False
    handoff_steps: int = 0


class Transition(NamedTuple):
    label: str
    state: State


class GatePolicyStep:
    """Model one FlowPilot gate-policy transition.

    Input x State -> Set(Output x State)
    reads: task scale, risk type, selected quality method, issue type,
    resource scope, advisory status, and state-refresh facts
    writes: one policy decision, proof path, repair/disposition choice, or
    terminal completion fact
    idempotency: state facts are monotonic; repeated ticks should not create a
    second route mutation, second completion, or contradictory method choice
    """

    name = "GatePolicyStep"

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


def _step(state: State, **changes: object) -> State:
    return replace(state, handoff_steps=state.handoff_steps + 1, **changes)


def _quality_satisfied(state: State) -> bool:
    if not state.quality_risk_decision_done:
        return False
    if state.risk_type == RISK_PRODUCT_STATE:
        return state.product_flowguard_done
    if state.risk_type == RISK_VISUAL_QUALITY:
        return state.reviewer_walkthrough_done
    if state.risk_type == RISK_MIXED_PRODUCT_VISUAL:
        return state.product_flowguard_done and state.reviewer_walkthrough_done
    if state.risk_type == RISK_DOCUMENTATION_ONLY:
        return state.light_review_done or (
            state.selected_quality_method == METHOD_NOT_NEEDED_WITH_REASON
            and state.not_needed_reason_recorded
        )
    return False


def _repair_satisfied(state: State) -> bool:
    if state.issue_type == ISSUE_NONE:
        return True
    if state.issue_type == ISSUE_LOCAL_DEFECT:
        return state.repair_strategy == REPAIR_LOCAL and state.local_repair_done
    if state.issue_type == ISSUE_ROUTE_INVALIDATING:
        return (
            state.repair_strategy == REPAIR_ROUTE_MUTATION
            and state.route_mutation_done
            and state.stale_evidence_invalidated
        )
    return False


def _parent_replay_satisfied(state: State) -> bool:
    if not state.parent_has_children:
        return True
    if state.composition_risk == "high":
        return state.parent_replay_done
    if state.composition_risk == "low":
        return state.parent_replay_waived_with_reason
    return False


def _resource_satisfied(state: State) -> bool:
    if state.generated_resource_scope == RESOURCE_NONE:
        return True
    if state.generated_resource_scope == RESOURCE_DIAGNOSTIC_TEMP:
        return state.generated_resource_excluded_as_diagnostic
    if state.generated_resource_scope == RESOURCE_DELIVERY_EVIDENCE:
        return state.generated_resource_disposed
    return False


def _state_refresh_satisfied(state: State) -> bool:
    return (
        state.stage_advanced
        and state.frontier_updated
        and state.display_updated
        and state.ledger_updated
        and state.blocker_index_updated
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"complete", "blocked"}:
        return

    if state.task_scale == "unknown":
        yield Transition(
            "small_task_stays_outside_formal_flowpilot",
            _step(state, status="complete", task_scale=TASK_SMALL, completion_recorded=True),
        )
        yield Transition(
            "complex_task_enters_formal_flowpilot",
            _step(
                state,
                status="running",
                task_scale=TASK_COMPLEX,
                formal_flowpilot_started=True,
                six_role_crew_started=True,
            ),
        )
        return

    if not state.startup_questions_asked:
        yield Transition(
            "startup_questions_record_wait_without_side_effects",
            _step(
                state,
                startup_questions_asked=True,
                startup_wait_boundary_recorded=True,
                startup_explanatory_text_emitted=True,
            ),
        )
        return

    if not state.gate_policy_catalog_written:
        yield Transition(
            "pm_writes_gate_policy_catalog",
            _step(
                state,
                gate_policy_catalog_written=True,
                hard_startup_gate_passed=True,
                hard_controller_boundary_passed=True,
            ),
        )
        return

    if not state.quality_risk_decision_done:
        yield Transition(
            "pm_classifies_product_state_risk",
            _step(
                state,
                quality_risk_decision_done=True,
                risk_type=RISK_PRODUCT_STATE,
                selected_quality_method=METHOD_PRODUCT_FLOWGUARD,
            ),
        )
        yield Transition(
            "pm_classifies_visual_quality_risk",
            _step(
                state,
                quality_risk_decision_done=True,
                risk_type=RISK_VISUAL_QUALITY,
                selected_quality_method=METHOD_REVIEWER_WALKTHROUGH,
            ),
        )
        yield Transition(
            "pm_classifies_mixed_product_visual_risk",
            _step(
                state,
                quality_risk_decision_done=True,
                risk_type=RISK_MIXED_PRODUCT_VISUAL,
                selected_quality_method=METHOD_BOTH,
            ),
        )
        yield Transition(
            "pm_classifies_documentation_only_risk",
            _step(
                state,
                quality_risk_decision_done=True,
                risk_type=RISK_DOCUMENTATION_ONLY,
                selected_quality_method=METHOD_LIGHT_REVIEW,
            ),
        )
        return

    if not _quality_satisfied(state):
        if state.selected_quality_method == METHOD_PRODUCT_FLOWGUARD:
            yield Transition(
                "product_flowguard_runs_for_product_state_risk",
                _step(state, product_flowguard_done=True),
            )
        elif state.selected_quality_method == METHOD_REVIEWER_WALKTHROUGH:
            yield Transition(
                "reviewer_walkthrough_runs_for_visual_quality_risk",
                _step(state, reviewer_walkthrough_done=True),
            )
        elif state.selected_quality_method == METHOD_BOTH:
            if not state.product_flowguard_done:
                yield Transition(
                    "product_flowguard_runs_for_mixed_risk",
                    _step(state, product_flowguard_done=True),
                )
            else:
                yield Transition(
                    "reviewer_walkthrough_runs_for_mixed_risk",
                    _step(state, reviewer_walkthrough_done=True),
                )
        elif state.selected_quality_method == METHOD_LIGHT_REVIEW:
            yield Transition(
                "light_review_runs_for_documentation_only_risk",
                _step(state, light_review_done=True),
            )
        return

    if state.issue_type == "unknown":
        yield Transition("pm_records_no_blocking_issue", _step(state, issue_type=ISSUE_NONE))
        yield Transition(
            "pm_routes_local_defect_to_local_repair",
            _step(state, issue_type=ISSUE_LOCAL_DEFECT, repair_strategy=REPAIR_LOCAL),
        )
        yield Transition(
            "pm_routes_invalidating_finding_to_route_mutation",
            _step(state, issue_type=ISSUE_ROUTE_INVALIDATING, repair_strategy=REPAIR_ROUTE_MUTATION),
        )
        return

    if not _repair_satisfied(state):
        if state.issue_type == ISSUE_LOCAL_DEFECT:
            yield Transition("local_repair_completed_without_route_mutation", _step(state, local_repair_done=True))
        elif state.issue_type == ISSUE_ROUTE_INVALIDATING:
            yield Transition(
                "route_mutation_invalidates_stale_evidence",
                _step(state, route_mutation_done=True, stale_evidence_invalidated=True),
            )
        return

    if state.composition_risk == "unknown":
        yield Transition(
            "pm_records_low_composition_risk_and_waives_parent_replay",
            _step(
                state,
                composition_risk="low",
                parent_replay_policy="risk_based",
                parent_replay_waived_with_reason=True,
            ),
        )
        yield Transition(
            "pm_records_high_composition_risk_and_requires_parent_replay",
            _step(state, composition_risk="high", parent_replay_policy="risk_based"),
        )
        return

    if not _parent_replay_satisfied(state):
        yield Transition("parent_backward_replay_runs_for_high_composition_risk", _step(state, parent_replay_done=True))
        return

    if state.generated_resource_scope == "unknown":
        yield Transition(
            "pm_records_no_generated_resource_scope",
            _step(state, generated_resource_scope=RESOURCE_NONE),
        )
        yield Transition(
            "pm_excludes_temporary_diagnostic_resource_from_completion_gate",
            _step(
                state,
                generated_resource_scope=RESOURCE_DIAGNOSTIC_TEMP,
                generated_resource_excluded_as_diagnostic=True,
            ),
        )
        yield Transition(
            "pm_disposes_delivery_evidence_resource",
            _step(
                state,
                generated_resource_scope=RESOURCE_DELIVERY_EVIDENCE,
                generated_resource_disposed=True,
            ),
        )
        return

    if not _resource_satisfied(state):
        return

    if not state.stage_advanced:
        yield Transition(
            "stage_advance_uses_transactional_state_refresh",
            _step(
                state,
                stage_advanced=True,
                frontier_updated=True,
                display_updated=True,
                ledger_updated=True,
                blocker_index_updated=True,
            ),
        )
        return

    if not state.completion_review_passed:
        yield Transition("final_review_passes_after_policy_gates", _step(state, completion_review_passed=True))
        return

    if not state.completion_recorded:
        yield Transition("completion_records_without_advisory_blocker", _step(state, status="complete", completion_recorded=True))


def formal_flowpilot_only_for_complex_tasks(state: State, trace) -> InvariantResult:
    del trace
    if state.formal_flowpilot_started and state.task_scale != TASK_COMPLEX:
        return InvariantResult.fail("formal FlowPilot was started for a small or nonformal task")
    if state.formal_flowpilot_started and not state.six_role_crew_started:
        return InvariantResult.fail("formal FlowPilot started without the standard six-role crew")
    return InvariantResult.pass_()


def startup_boundary_is_side_effect_based(state: State, trace) -> InvariantResult:
    del trace
    if state.startup_boundary_invalidated_for_text and not state.startup_side_effects_before_answers:
        return InvariantResult.fail("startup boundary treated side-effect-free explanatory text as a protocol violation")
    if state.startup_side_effects_before_answers and state.startup_wait_boundary_recorded:
        return InvariantResult.fail("startup wait boundary allowed startup side effects before answers")
    return InvariantResult.pass_()


def mandatory_quality_decision_and_method_match(state: State, trace) -> InvariantResult:
    del trace
    if state.completion_recorded and state.formal_flowpilot_started and not state.quality_risk_decision_done:
        return InvariantResult.fail("completion recorded before mandatory quality-risk decision")
    if state.risk_type == RISK_PRODUCT_STATE and state.completion_recorded and not state.product_flowguard_done:
        return InvariantResult.fail("product-state risk completed without Product FlowGuard")
    if state.risk_type == RISK_VISUAL_QUALITY:
        if state.product_flowguard_done and not state.reviewer_walkthrough_done:
            return InvariantResult.fail("visual-quality risk used FlowGuard as the only quality proof")
        if state.completion_recorded and not state.reviewer_walkthrough_done:
            return InvariantResult.fail("visual-quality risk completed without reviewer walkthrough")
    if state.risk_type == RISK_MIXED_PRODUCT_VISUAL and state.completion_recorded:
        if not (state.product_flowguard_done and state.reviewer_walkthrough_done):
            return InvariantResult.fail("mixed product/visual risk completed without both FlowGuard and reviewer walkthrough")
    if state.risk_type == RISK_DOCUMENTATION_ONLY and state.product_flowguard_done:
        return InvariantResult.fail("documentation-only risk was forced through Product FlowGuard")
    if state.selected_quality_method == METHOD_NOT_NEEDED_NO_REASON:
        return InvariantResult.fail("quality gate was skipped without a recorded reason")
    return InvariantResult.pass_()


def advisory_records_do_not_block_completion(state: State, trace) -> InvariantResult:
    del trace
    if state.advisory_blocks_completion:
        return InvariantResult.fail("advisory or nonblocking record blocked completion")
    return InvariantResult.pass_()


def repair_escalation_matches_issue_type(state: State, trace) -> InvariantResult:
    del trace
    if state.issue_type == ISSUE_LOCAL_DEFECT and state.repair_strategy == REPAIR_ROUTE_MUTATION:
        return InvariantResult.fail("local defect forced structural route mutation")
    if state.issue_type == ISSUE_ROUTE_INVALIDATING and state.repair_strategy == REPAIR_LOCAL:
        return InvariantResult.fail("route-invalidating finding was treated as local repair only")
    if state.route_mutation_done and not state.stale_evidence_invalidated:
        return InvariantResult.fail("route mutation did not invalidate stale evidence")
    return InvariantResult.pass_()


def parent_replay_is_risk_based_or_justified(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.parent_has_children
        and state.composition_risk == "low"
        and state.parent_replay_policy == "structural_hard"
        and state.completion_blocked_by_parent_replay
    ):
        return InvariantResult.fail("low-composition-risk parent replay was a structural hard blocker")
    return InvariantResult.pass_()


def generated_resource_policy_is_scope_aware(state: State, trace) -> InvariantResult:
    del trace
    if state.generated_resource_scope == RESOURCE_DIAGNOSTIC_TEMP and state.generated_resource_blocks_completion:
        return InvariantResult.fail("temporary diagnostic resource blocked completion")
    if (
        state.generated_resource_scope == RESOURCE_DELIVERY_EVIDENCE
        and state.completion_recorded
        and not state.generated_resource_disposed
    ):
        return InvariantResult.fail("delivery evidence resource was unresolved at completion")
    return InvariantResult.pass_()


def no_benefit_hard_gates_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.no_benefit_hard_gate_required and state.hard_gate_safety_delta == "none":
        return InvariantResult.fail("hard gate had no modeled safety delta")
    return InvariantResult.pass_()


def state_updates_are_transactional(state: State, trace) -> InvariantResult:
    del trace
    if state.stage_advanced and not (
        state.frontier_updated
        and state.display_updated
        and state.ledger_updated
        and state.blocker_index_updated
    ):
        return InvariantResult.fail("stage advanced without transactional frontier/display/ledger/blocker-index refresh")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="formal_flowpilot_only_for_complex_tasks",
        description="Small or nonformal tasks must not enter formal six-role FlowPilot.",
        predicate=formal_flowpilot_only_for_complex_tasks,
    ),
    Invariant(
        name="startup_boundary_is_side_effect_based",
        description="Startup wait boundary forbids side effects before answers, not harmless explanatory text.",
        predicate=startup_boundary_is_side_effect_based,
    ),
    Invariant(
        name="mandatory_quality_decision_and_method_match",
        description="Quality-risk decisions are mandatory, and proof methods must match the risk class.",
        predicate=mandatory_quality_decision_and_method_match,
    ),
    Invariant(
        name="advisory_records_do_not_block_completion",
        description="Advisory and nonblocking records cannot become completion blockers.",
        predicate=advisory_records_do_not_block_completion,
    ),
    Invariant(
        name="repair_escalation_matches_issue_type",
        description="Local defects stay local; route-invalidating findings mutate routes and stale evidence.",
        predicate=repair_escalation_matches_issue_type,
    ),
    Invariant(
        name="parent_replay_is_risk_based_or_justified",
        description="Parent backward replay must be risk-based or explicitly justified, not structural friction only.",
        predicate=parent_replay_is_risk_based_or_justified,
    ),
    Invariant(
        name="generated_resource_policy_is_scope_aware",
        description="Delivery evidence is resolved, while temporary diagnostics do not block completion.",
        predicate=generated_resource_policy_is_scope_aware,
    ),
    Invariant(
        name="no_benefit_hard_gates_are_rejected",
        description="A hard gate must prevent a modeled hazard or it is a no-benefit blocker.",
        predicate=no_benefit_hard_gates_are_rejected,
    ),
    Invariant(
        name="state_updates_are_transactional",
        description="Stage advancement refreshes frontier, display, ledger, and blocker index together.",
        predicate=state_updates_are_transactional,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 40


def build_workflow() -> Workflow:
    return Workflow((GatePolicyStep(),), name="flowpilot_gate_policy_audit")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    base = State(status="running", task_scale=TASK_COMPLEX, formal_flowpilot_started=True, six_role_crew_started=True)
    complete_base = replace(base, completion_recorded=True, completion_review_passed=True)
    return {
        "small_task_enters_formal_flowpilot": replace(
            complete_base,
            task_scale=TASK_SMALL,
            formal_flowpilot_started=True,
            six_role_crew_started=True,
        ),
        "formal_flowpilot_without_six_roles": replace(
            base,
            formal_flowpilot_started=True,
            six_role_crew_started=False,
        ),
        "startup_text_invalidated_without_side_effect": replace(
            base,
            startup_questions_asked=True,
            startup_wait_boundary_recorded=True,
            startup_explanatory_text_emitted=True,
            startup_boundary_invalidated_for_text=True,
            startup_side_effects_before_answers=False,
        ),
        "startup_side_effects_before_answers": replace(
            base,
            startup_questions_asked=True,
            startup_wait_boundary_recorded=True,
            startup_side_effects_before_answers=True,
        ),
        "completion_without_quality_decision": replace(
            complete_base,
            quality_risk_decision_done=False,
        ),
        "product_state_without_product_flowguard": replace(
            complete_base,
            quality_risk_decision_done=True,
            risk_type=RISK_PRODUCT_STATE,
            selected_quality_method=METHOD_PRODUCT_FLOWGUARD,
            product_flowguard_done=False,
        ),
        "visual_quality_flowguard_only": replace(
            complete_base,
            quality_risk_decision_done=True,
            risk_type=RISK_VISUAL_QUALITY,
            selected_quality_method=METHOD_PRODUCT_FLOWGUARD,
            product_flowguard_done=True,
            reviewer_walkthrough_done=False,
        ),
        "mixed_quality_without_reviewer": replace(
            complete_base,
            quality_risk_decision_done=True,
            risk_type=RISK_MIXED_PRODUCT_VISUAL,
            selected_quality_method=METHOD_BOTH,
            product_flowguard_done=True,
            reviewer_walkthrough_done=False,
        ),
        "documentation_only_forced_product_flowguard": replace(
            base,
            quality_risk_decision_done=True,
            risk_type=RISK_DOCUMENTATION_ONLY,
            selected_quality_method=METHOD_PRODUCT_FLOWGUARD,
            product_flowguard_done=True,
        ),
        "quality_not_needed_without_reason": replace(
            base,
            quality_risk_decision_done=True,
            risk_type=RISK_DOCUMENTATION_ONLY,
            selected_quality_method=METHOD_NOT_NEEDED_NO_REASON,
            not_needed_reason_recorded=False,
        ),
        "advisory_blocks_completion": replace(
            complete_base,
            advisory_observation_missing=True,
            advisory_blocks_completion=True,
        ),
        "local_defect_forces_route_mutation": replace(
            base,
            issue_type=ISSUE_LOCAL_DEFECT,
            repair_strategy=REPAIR_ROUTE_MUTATION,
            route_mutation_done=True,
            stale_evidence_invalidated=True,
        ),
        "route_invalidating_finding_gets_local_repair": replace(
            base,
            issue_type=ISSUE_ROUTE_INVALIDATING,
            repair_strategy=REPAIR_LOCAL,
            local_repair_done=True,
        ),
        "route_mutation_without_stale_invalidation": replace(
            base,
            issue_type=ISSUE_ROUTE_INVALIDATING,
            repair_strategy=REPAIR_ROUTE_MUTATION,
            route_mutation_done=True,
            stale_evidence_invalidated=False,
        ),
        "low_risk_parent_replay_hard_blocker": replace(
            base,
            parent_has_children=True,
            composition_risk="low",
            parent_replay_policy="structural_hard",
            completion_blocked_by_parent_replay=True,
        ),
        "diagnostic_resource_blocks_completion": replace(
            base,
            generated_resource_scope=RESOURCE_DIAGNOSTIC_TEMP,
            generated_resource_blocks_completion=True,
        ),
        "delivery_resource_unresolved_at_completion": replace(
            complete_base,
            generated_resource_scope=RESOURCE_DELIVERY_EVIDENCE,
            generated_resource_disposed=False,
        ),
        "no_benefit_hard_gate_required": replace(
            base,
            no_benefit_hard_gate_required=True,
            hard_gate_safety_delta="none",
        ),
        "stage_advance_without_transactional_refresh": replace(
            base,
            stage_advanced=True,
            frontier_updated=True,
            display_updated=False,
            ledger_updated=True,
            blocker_index_updated=False,
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
    "next_safe_states",
]
