"""FlowGuard model for the FlowPilot GateDecision implementation contract.

Risk intent brief:
- Prevent the GateDecision plan from becoming prose that cannot be checked by
  FlowPilot's existing prompt, router, reviewer-scope, and control-plane models.
- Model only post-start FlowPilot gate decisions. Invocation/startup routing is
  deliberately out of scope because formal FlowPilot is already user-selected.
- Protected harms include missing worker/report fields, router semantic
  overreach, reviewer semantic gaps, wrong proof-method selection, advisory
  blockers, over-escalated repairs, stale route evidence, low-risk parent replay
  hard blockers, resource-disposition mistakes, and split stage refresh.
- The safe scenario is a directly implementable contract: prompt fields are
  visible, router checks mechanical conformance only, PM/reviewer/officers own
  semantic sufficiency, and state-affecting decisions have route-visible
  evidence.
- Blindspot: this model validates the contract shape. It does not prove that
  FlowPilot runtime/cards already implement it unless paired with source scans
  and the existing conformance models.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_CONTRACT = "valid_gate_decision_contract"
MISSING_PROMPT_FIELDS = "missing_prompt_fields"
ROUTER_MISSING_FIELDS = "router_missing_fields"
ROUTER_SEMANTIC_OVERREACH = "router_semantic_overreach"
REVIEWER_SEMANTIC_GAP = "reviewer_semantic_gap"
VISUAL_FLOWGUARD_ONLY = "visual_flowguard_only"
PRODUCT_WITHOUT_FLOWGUARD = "product_without_flowguard"
MIXED_WITHOUT_REVIEWER = "mixed_without_reviewer"
DOCUMENTATION_FORCED_PRODUCT_FLOWGUARD = "documentation_forced_product_flowguard"
ADVISORY_BLOCKS_COMPLETION = "advisory_blocks_completion"
SKIP_WITHOUT_REASON = "skip_without_reason"
LOCAL_DEFECT_FORCES_MUTATION = "local_defect_forces_mutation"
ROUTE_MUTATION_WITHOUT_STALE_INVALIDATION = "route_mutation_without_stale_invalidation"
LOW_RISK_PARENT_REPLAY_HARD = "low_risk_parent_replay_hard"
DIAGNOSTIC_RESOURCE_BLOCKS = "diagnostic_resource_blocks"
DELIVERY_EVIDENCE_UNRESOLVED = "delivery_evidence_unresolved"
STAGE_ADVANCE_SPLIT_REFRESH = "stage_advance_split_refresh"

NEGATIVE_SCENARIOS = (
    MISSING_PROMPT_FIELDS,
    ROUTER_MISSING_FIELDS,
    ROUTER_SEMANTIC_OVERREACH,
    REVIEWER_SEMANTIC_GAP,
    VISUAL_FLOWGUARD_ONLY,
    PRODUCT_WITHOUT_FLOWGUARD,
    MIXED_WITHOUT_REVIEWER,
    DOCUMENTATION_FORCED_PRODUCT_FLOWGUARD,
    ADVISORY_BLOCKS_COMPLETION,
    SKIP_WITHOUT_REASON,
    LOCAL_DEFECT_FORCES_MUTATION,
    ROUTE_MUTATION_WITHOUT_STALE_INVALIDATION,
    LOW_RISK_PARENT_REPLAY_HARD,
    DIAGNOSTIC_RESOURCE_BLOCKS,
    DELIVERY_EVIDENCE_UNRESOLVED,
    STAGE_ADVANCE_SPLIT_REFRESH,
)

SCENARIOS = (VALID_CONTRACT, *NEGATIVE_SCENARIOS)

GATE_DECISION_REQUIRED_FIELDS = frozenset(
    {
        "gate_decision_version",
        "gate_id",
        "gate_kind",
        "owner_role",
        "risk_type",
        "gate_strength",
        "decision",
        "blocking",
        "required_evidence",
        "evidence_refs",
        "reason",
        "next_action",
    }
)

ROUTER_MECHANICAL_CHECKS = frozenset(
    {
        "required_fields_present",
        "enum_values_valid",
        "blocking_decision_compatible",
        "evidence_refs_have_path_hash_shape",
        "next_action_routeable",
        "stage_advance_refresh_atomic",
    }
)

REVIEWER_SEMANTIC_CHECKS = frozenset(
    {
        "risk_type_fits_issue",
        "proof_method_matches_risk",
        "hard_gate_has_safety_delta",
        "visual_quality_has_reviewer_walkthrough",
        "product_state_has_product_flowguard",
        "documentation_not_forced_to_product_flowguard",
        "repair_strategy_matches_issue_type",
        "parent_replay_risk_based_or_waived",
        "resource_disposition_matches_scope",
    }
)


@dataclass(frozen=True)
class Tick:
    """One GateDecision contract tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    prompt_fields: frozenset[str] = field(default_factory=frozenset)
    router_fields: frozenset[str] = field(default_factory=frozenset)
    router_mechanical_checks: frozenset[str] = field(default_factory=frozenset)
    reviewer_semantic_checks: frozenset[str] = field(default_factory=frozenset)

    router_semantic_overreach: bool = False
    reviewer_defers_semantics_to_router: bool = False

    visual_requires_reviewer_walkthrough: bool = True
    visual_uses_product_flowguard_only: bool = False
    product_requires_product_flowguard: bool = True
    product_flowguard_present: bool = True
    mixed_requires_both: bool = True
    mixed_product_flowguard_present: bool = True
    mixed_reviewer_walkthrough_present: bool = True
    documentation_uses_light_review_or_skip_reason: bool = True
    documentation_forced_to_product_flowguard: bool = False

    advisory_nonblocking: bool = True
    skip_or_waive_has_reason: bool = True

    local_defect_uses_local_repair: bool = True
    route_mutation_invalidates_stale_evidence: bool = True

    parent_replay_risk_based: bool = True
    low_risk_parent_replay_waivable: bool = True

    diagnostic_resource_nonblocking: bool = True
    delivery_evidence_resolved_before_completion: bool = True

    stage_advance_atomic_refresh: bool = True

    gate_registered_in_router_visible_state: bool = True
    final_ledger_can_collect_gate_decision: bool = True

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class GateDecisionContractStep:
    """Model one GateDecision implementation-contract transition.

    Input x State -> Set(Output x State)
    reads: prompt fields, router fields, router mechanical checks, reviewer
    semantic checks, proof method facts, repair facts, resource facts, and state
    refresh facts
    writes: one scenario selection or terminal contract decision
    idempotency: once selected, a scenario has one terminal accept/reject path;
    repeated ticks do not reinterpret semantic ownership
    """

    name = "GateDecisionContractStep"
    reads = (
        "prompt_fields",
        "router_fields",
        "router_mechanical_checks",
        "reviewer_semantic_checks",
        "proof_method_facts",
        "repair_facts",
        "resource_facts",
        "state_refresh_facts",
    )
    writes = ("scenario_facts", "terminal_contract_decision")
    input_description = "GateDecision contract tick"
    output_description = "one contract validation action"
    idempotency = "scenario and terminal decision are monotonic"

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


def _valid_state() -> State:
    return State(
        status="running",
        scenario=VALID_CONTRACT,
        prompt_fields=GATE_DECISION_REQUIRED_FIELDS,
        router_fields=GATE_DECISION_REQUIRED_FIELDS,
        router_mechanical_checks=ROUTER_MECHANICAL_CHECKS,
        reviewer_semantic_checks=REVIEWER_SEMANTIC_CHECKS,
        router_semantic_overreach=False,
        reviewer_defers_semantics_to_router=False,
        visual_requires_reviewer_walkthrough=True,
        visual_uses_product_flowguard_only=False,
        product_requires_product_flowguard=True,
        product_flowguard_present=True,
        mixed_requires_both=True,
        mixed_product_flowguard_present=True,
        mixed_reviewer_walkthrough_present=True,
        documentation_uses_light_review_or_skip_reason=True,
        documentation_forced_to_product_flowguard=False,
        advisory_nonblocking=True,
        skip_or_waive_has_reason=True,
        local_defect_uses_local_repair=True,
        route_mutation_invalidates_stale_evidence=True,
        parent_replay_risk_based=True,
        low_risk_parent_replay_waivable=True,
        diagnostic_resource_nonblocking=True,
        delivery_evidence_resolved_before_completion=True,
        stage_advance_atomic_refresh=True,
        gate_registered_in_router_visible_state=True,
        final_ledger_can_collect_gate_decision=True,
    )


def _scenario_state(scenario: str) -> State:
    state = replace(_valid_state(), scenario=scenario)
    if scenario == MISSING_PROMPT_FIELDS:
        return replace(state, prompt_fields=state.prompt_fields - frozenset({"required_evidence"}))
    if scenario == ROUTER_MISSING_FIELDS:
        return replace(state, router_fields=state.router_fields - frozenset({"evidence_refs"}))
    if scenario == ROUTER_SEMANTIC_OVERREACH:
        return replace(state, router_semantic_overreach=True)
    if scenario == REVIEWER_SEMANTIC_GAP:
        return replace(
            state,
            reviewer_semantic_checks=state.reviewer_semantic_checks
            - frozenset({"proof_method_matches_risk", "repair_strategy_matches_issue_type"}),
            reviewer_defers_semantics_to_router=True,
        )
    if scenario == VISUAL_FLOWGUARD_ONLY:
        return replace(state, visual_uses_product_flowguard_only=True, visual_requires_reviewer_walkthrough=False)
    if scenario == PRODUCT_WITHOUT_FLOWGUARD:
        return replace(state, product_flowguard_present=False)
    if scenario == MIXED_WITHOUT_REVIEWER:
        return replace(state, mixed_reviewer_walkthrough_present=False)
    if scenario == DOCUMENTATION_FORCED_PRODUCT_FLOWGUARD:
        return replace(
            state,
            documentation_uses_light_review_or_skip_reason=False,
            documentation_forced_to_product_flowguard=True,
        )
    if scenario == ADVISORY_BLOCKS_COMPLETION:
        return replace(state, advisory_nonblocking=False)
    if scenario == SKIP_WITHOUT_REASON:
        return replace(state, skip_or_waive_has_reason=False)
    if scenario == LOCAL_DEFECT_FORCES_MUTATION:
        return replace(state, local_defect_uses_local_repair=False)
    if scenario == ROUTE_MUTATION_WITHOUT_STALE_INVALIDATION:
        return replace(state, route_mutation_invalidates_stale_evidence=False)
    if scenario == LOW_RISK_PARENT_REPLAY_HARD:
        return replace(state, parent_replay_risk_based=False, low_risk_parent_replay_waivable=False)
    if scenario == DIAGNOSTIC_RESOURCE_BLOCKS:
        return replace(state, diagnostic_resource_nonblocking=False)
    if scenario == DELIVERY_EVIDENCE_UNRESOLVED:
        return replace(state, delivery_evidence_resolved_before_completion=False)
    if scenario == STAGE_ADVANCE_SPLIT_REFRESH:
        return replace(state, stage_advance_atomic_refresh=False)
    return state


def contract_failures(state: State) -> list[str]:
    failures: list[str] = []

    missing_prompt = GATE_DECISION_REQUIRED_FIELDS - state.prompt_fields
    if missing_prompt:
        failures.append("prompt contract omitted GateDecision fields")

    missing_router_fields = GATE_DECISION_REQUIRED_FIELDS - state.router_fields
    missing_router_checks = ROUTER_MECHANICAL_CHECKS - state.router_mechanical_checks
    if missing_router_fields or missing_router_checks:
        failures.append("router mechanical contract omitted GateDecision checks")

    if state.router_semantic_overreach:
        failures.append("router overreached into semantic gate judgment")

    missing_reviewer_checks = REVIEWER_SEMANTIC_CHECKS - state.reviewer_semantic_checks
    if missing_reviewer_checks or state.reviewer_defers_semantics_to_router:
        failures.append("reviewer scope omitted semantic gate sufficiency")

    if state.visual_uses_product_flowguard_only or not state.visual_requires_reviewer_walkthrough:
        failures.append("visual-quality GateDecision lacks reviewer walkthrough proof")

    if state.product_requires_product_flowguard and not state.product_flowguard_present:
        failures.append("product/state GateDecision lacks Product FlowGuard proof")

    if state.mixed_requires_both and not (
        state.mixed_product_flowguard_present and state.mixed_reviewer_walkthrough_present
    ):
        failures.append("mixed product/visual GateDecision lacks both proof paths")

    if (
        not state.documentation_uses_light_review_or_skip_reason
        or state.documentation_forced_to_product_flowguard
    ):
        failures.append("documentation-only GateDecision was forced through Product FlowGuard")

    if not state.advisory_nonblocking:
        failures.append("advisory GateDecision blocked completion")

    if not state.skip_or_waive_has_reason:
        failures.append("skip or waiver GateDecision lacked a concrete reason")

    if not state.local_defect_uses_local_repair:
        failures.append("local defect GateDecision forced route mutation")

    if not state.route_mutation_invalidates_stale_evidence:
        failures.append("route mutation GateDecision did not invalidate stale evidence")

    if not (state.parent_replay_risk_based and state.low_risk_parent_replay_waivable):
        failures.append("parent replay GateDecision is not risk based or waivable")

    if not state.diagnostic_resource_nonblocking:
        failures.append("diagnostic temporary resource GateDecision blocked completion")

    if not state.delivery_evidence_resolved_before_completion:
        failures.append("delivery evidence GateDecision was unresolved at completion")

    if not state.stage_advance_atomic_refresh:
        failures.append("stage advance GateDecision did not require atomic state refresh")

    if not (state.gate_registered_in_router_visible_state and state.final_ledger_can_collect_gate_decision):
        failures.append("accepted GateDecision is not route-visible or final-ledger collectable")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = contract_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            "accept_valid_gate_decision_contract",
            replace(state, status="accepted", terminal_reason="contract_ok"),
        )


def contract_accepts_only_valid_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and contract_failures(state):
        return InvariantResult.fail("invalid GateDecision contract was accepted")
    if state.status == "rejected" and not contract_failures(state):
        return InvariantResult.fail("valid GateDecision contract was rejected")
    return InvariantResult.pass_()


def router_scope_stays_mechanical(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if state.router_semantic_overreach:
        return InvariantResult.fail("router overreached into semantic gate judgment")
    return InvariantResult.pass_()


def reviewer_scope_keeps_semantics(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    missing = REVIEWER_SEMANTIC_CHECKS - state.reviewer_semantic_checks
    if missing or state.reviewer_defers_semantics_to_router:
        return InvariantResult.fail("reviewer scope omitted semantic gate sufficiency")
    return InvariantResult.pass_()


def prompt_and_router_have_required_fields(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if GATE_DECISION_REQUIRED_FIELDS - state.prompt_fields:
        return InvariantResult.fail("prompt contract omitted GateDecision fields")
    if GATE_DECISION_REQUIRED_FIELDS - state.router_fields:
        return InvariantResult.fail("router mechanical contract omitted GateDecision checks")
    return InvariantResult.pass_()


def proof_method_matches_risk_type(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    failures = contract_failures(state)
    for needle in (
        "visual-quality GateDecision lacks reviewer walkthrough proof",
        "product/state GateDecision lacks Product FlowGuard proof",
        "mixed product/visual GateDecision lacks both proof paths",
        "documentation-only GateDecision was forced through Product FlowGuard",
    ):
        if needle in failures:
            return InvariantResult.fail(needle)
    return InvariantResult.pass_()


def gate_strength_and_repair_are_risk_based(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    failures = contract_failures(state)
    for needle in (
        "advisory GateDecision blocked completion",
        "skip or waiver GateDecision lacked a concrete reason",
        "local defect GateDecision forced route mutation",
        "route mutation GateDecision did not invalidate stale evidence",
        "parent replay GateDecision is not risk based or waivable",
    ):
        if needle in failures:
            return InvariantResult.fail(needle)
    return InvariantResult.pass_()


def resources_and_stage_advance_are_route_visible(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    failures = contract_failures(state)
    for needle in (
        "diagnostic temporary resource GateDecision blocked completion",
        "delivery evidence GateDecision was unresolved at completion",
        "stage advance GateDecision did not require atomic state refresh",
        "accepted GateDecision is not route-visible or final-ledger collectable",
    ):
        if needle in failures:
            return InvariantResult.fail(needle)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="contract_accepts_only_valid_contract",
        description="Only the valid GateDecision contract can be accepted.",
        predicate=contract_accepts_only_valid_contract,
    ),
    Invariant(
        name="prompt_and_router_have_required_fields",
        description="Prompt and router contracts expose the required GateDecision fields.",
        predicate=prompt_and_router_have_required_fields,
    ),
    Invariant(
        name="router_scope_stays_mechanical",
        description="Router validation stays limited to mechanical conformance.",
        predicate=router_scope_stays_mechanical,
    ),
    Invariant(
        name="reviewer_scope_keeps_semantics",
        description="Reviewer/PM/officer checks own semantic gate sufficiency.",
        predicate=reviewer_scope_keeps_semantics,
    ),
    Invariant(
        name="proof_method_matches_risk_type",
        description="Proof method selection matches GateDecision risk type.",
        predicate=proof_method_matches_risk_type,
    ),
    Invariant(
        name="gate_strength_and_repair_are_risk_based",
        description="Gate strength, skips, repair, and parent replay are risk based.",
        predicate=gate_strength_and_repair_are_risk_based,
    ),
    Invariant(
        name="resources_and_stage_advance_are_route_visible",
        description="Resource disposition and stage advance remain route visible and atomic.",
        predicate=resources_and_stage_advance_are_route_visible,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((GateDecisionContractStep(),), name="flowpilot_gate_decision_contract")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "GATE_DECISION_REQUIRED_FIELDS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "REVIEWER_SEMANTIC_CHECKS",
    "ROUTER_MECHANICAL_CHECKS",
    "SCENARIOS",
    "VALID_CONTRACT",
    "State",
    "Tick",
    "build_workflow",
    "contract_failures",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
