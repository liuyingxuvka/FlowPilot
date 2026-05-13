"""FlowGuard model for FlowPilot Reviewer-only pre-route gate simplification.

Risk Purpose Header:
- This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to
  review the Reviewer-only speed profile for the root-contract and
  child-skill-manifest gates.
- It guards against freezing or approving before Reviewer pass, keeping removed
  officer gates as hidden requirements, emitting removed officer cards by
  default, dropping Reviewer evidence obligations, or starting route work before
  both simplified gates are closed.
- Future agents should run `python simulations/run_flowpilot_reviewer_only_gate_checks.py`
  before changing root-contract or child-skill-manifest gate sequencing,
  prompt-card requirements, or related Router event prerequisites.

Risk intent brief:
- The user explicitly chose Reviewer-only default gates for root contract and
  child-skill manifest. Product/Process Officer checks must not remain default
  gates or special consultation tails for these two gates.
- Protected harms: fake speedup from hidden officer waits, unsafe approval
  without Reviewer, loss of verifiability/evidence scrutiny, removed officer
  cards being emitted by default, and route work starting before both simplified
  gates close.
- Modeled state and side effects: PM writes, Reviewer card/pass, officer card
  emissions, officer pass flags, PM freeze/approval, Reviewer checklist scope,
  and route-ready transition.
- Hard invariants: Reviewer is still mandatory; removed officer gates are not
  required or emitted in the Reviewer-only default path; Reviewer checklist
  inherits the proof/evidence burden; route work waits for both simplified
  gates.
- Blindspot: this model does not inspect live files. Runtime tests must still
  verify the Router card sequence, event prerequisites, and prompt text.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 12


@dataclass(frozen=True)
class Tick:
    """One Reviewer-only gate transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete

    pm_root_contract_written: bool = False
    root_reviewer_card_emitted: bool = False
    root_reviewer_passed: bool = False
    root_product_officer_card_emitted: bool = False
    root_product_officer_required: bool = False
    root_product_officer_artifact_required_for_freeze: bool = False
    root_product_officer_passed: bool = False
    pm_root_contract_frozen: bool = False

    pm_child_manifest_written: bool = False
    child_reviewer_card_emitted: bool = False
    child_reviewer_passed: bool = False
    child_process_officer_card_emitted: bool = False
    child_process_officer_required: bool = False
    child_process_officer_artifact_required_for_approval: bool = False
    child_process_officer_passed: bool = False
    child_product_officer_card_emitted: bool = False
    child_product_officer_required: bool = False
    child_product_officer_artifact_required_for_approval: bool = False
    child_product_officer_passed: bool = False
    pm_child_manifest_approved: bool = False

    reviewer_root_checks_user_requirements: bool = True
    reviewer_root_checks_verifiability: bool = True
    reviewer_root_checks_proof_obligations: bool = True
    reviewer_root_checks_scenario_coverage: bool = True
    reviewer_root_rejects_report_only_closure: bool = True

    reviewer_child_checks_skill_standards: bool = True
    reviewer_child_checks_evidence_obligations: bool = True
    reviewer_child_checks_approvers: bool = True
    reviewer_child_checks_skipped_steps: bool = True
    reviewer_child_rejects_self_approval: bool = True

    pm_consultation_used: bool = False
    pm_consultation_required_for_gate: bool = False
    role_body_boundary_preserved: bool = True
    legacy_officer_events_preserved: bool = True
    route_ready: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class ReviewerOnlyGateStep:
    """Model one gate-sequencing step.

    Input x State -> Set(Output x State)
    reads: current PM/reviewer/officer flags, Reviewer checklist coverage,
    route-ready flag
    writes: the next PM write, Reviewer card/pass, PM freeze/approval, or
    route-ready marker
    idempotency: each tick only advances a missing monotonic flag; removed
    officer cards are never emitted by the safe transition relation.
    """

    name = "ReviewerOnlyGateStep"
    reads = (
        "pm_root_contract_written",
        "root_reviewer_passed",
        "pm_root_contract_frozen",
        "pm_child_manifest_written",
        "child_reviewer_passed",
        "pm_child_manifest_approved",
        "reviewer_checklist_coverage",
        "removed_officer_gate_flags",
    )
    writes = ("pm_write", "reviewer_card", "reviewer_pass", "pm_gate_close", "route_ready")
    input_description = "Reviewer-only pre-route gate tick"
    output_description = "one abstract Reviewer-only gate action"
    idempotency = "safe ticks are monotonic and do not emit removed officer default cards"

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
    if state.status == "new":
        return (Transition("reviewer_only_gate_run_started", replace(state, status="running")),)
    if invariant_failures(state):
        return (Transition("reviewer_only_gate_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if not state.pm_root_contract_written:
        return (Transition("pm_writes_root_contract", replace(state, pm_root_contract_written=True)),)
    if not state.root_reviewer_card_emitted:
        return (Transition("reviewer_root_contract_card_emitted", replace(state, root_reviewer_card_emitted=True)),)
    if not state.root_reviewer_passed:
        return (Transition("reviewer_passes_root_contract", replace(state, root_reviewer_passed=True)),)
    if not state.pm_root_contract_frozen:
        return (Transition("pm_freezes_root_contract_after_reviewer", replace(state, pm_root_contract_frozen=True)),)
    if not state.pm_child_manifest_written:
        return (Transition("pm_writes_child_skill_manifest", replace(state, pm_child_manifest_written=True)),)
    if not state.child_reviewer_card_emitted:
        return (Transition("reviewer_child_skill_manifest_card_emitted", replace(state, child_reviewer_card_emitted=True)),)
    if not state.child_reviewer_passed:
        return (Transition("reviewer_passes_child_skill_manifest", replace(state, child_reviewer_passed=True)),)
    if not state.pm_child_manifest_approved:
        return (Transition("pm_approves_child_skill_manifest_after_reviewer", replace(state, pm_child_manifest_approved=True)),)
    if not state.route_ready:
        return (Transition("route_ready_after_reviewer_only_gates", replace(state, route_ready=True)),)
    return (Transition("reviewer_only_gate_flow_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_root_contract_frozen and not state.pm_root_contract_written:
        failures.append("PM froze root contract before PM wrote it")
    if state.pm_root_contract_frozen and not state.root_reviewer_passed:
        failures.append("PM froze root contract before Reviewer pass")
    if state.root_reviewer_passed and not state.root_reviewer_card_emitted:
        failures.append("Reviewer passed root contract before Reviewer card")
    if state.root_reviewer_card_emitted and not state.pm_root_contract_written:
        failures.append("Reviewer root contract card emitted before PM contract write")
    if state.root_product_officer_card_emitted:
        failures.append("Reviewer-only root contract flow emitted removed Product Officer card")
    if state.root_product_officer_required:
        failures.append("Reviewer-only root contract flow still required Product Officer")
    if state.root_product_officer_artifact_required_for_freeze:
        failures.append("root contract freeze still required Product Officer artifact")
    if state.pm_root_contract_frozen and state.root_product_officer_required:
        failures.append("root contract freeze still depended on Product Officer")

    if state.pm_child_manifest_approved and not state.pm_child_manifest_written:
        failures.append("PM approved child-skill manifest before PM wrote it")
    if state.pm_child_manifest_approved and not state.child_reviewer_passed:
        failures.append("PM approved child-skill manifest before Reviewer pass")
    if state.child_reviewer_passed and not state.child_reviewer_card_emitted:
        failures.append("Reviewer passed child-skill manifest before Reviewer card")
    if state.child_reviewer_card_emitted and not state.pm_child_manifest_written:
        failures.append("Reviewer child-skill manifest card emitted before PM manifest write")
    if state.child_process_officer_card_emitted:
        failures.append("Reviewer-only child-skill flow emitted removed Process Officer card")
    if state.child_product_officer_card_emitted:
        failures.append("Reviewer-only child-skill flow emitted removed Product Officer card")
    if state.child_process_officer_required:
        failures.append("Reviewer-only child-skill flow still required Process Officer")
    if state.child_product_officer_required:
        failures.append("Reviewer-only child-skill flow still required Product Officer")
    if state.child_process_officer_artifact_required_for_approval:
        failures.append("child-skill approval still required Process Officer artifact")
    if state.child_product_officer_artifact_required_for_approval:
        failures.append("child-skill approval still required Product Officer artifact")
    if state.pm_child_manifest_approved and (
        state.child_process_officer_required or state.child_product_officer_required
    ):
        failures.append("child-skill manifest approval still depended on removed officer gate")

    if state.pm_consultation_required_for_gate:
        failures.append("PM consultation was reintroduced as a required gate tail")
    if not state.role_body_boundary_preserved:
        failures.append("Reviewer-only gate simplification broke role/body boundary isolation")
    if not state.legacy_officer_events_preserved:
        failures.append("Reviewer-only gate simplification removed legacy officer event compatibility")
    if state.route_ready and not state.pm_root_contract_frozen:
        failures.append("route became ready before PM froze root contract")
    if state.route_ready and not state.pm_child_manifest_approved:
        failures.append("route became ready before PM approved child-skill manifest")

    if state.root_reviewer_passed and not state.reviewer_root_checks_user_requirements:
        failures.append("Reviewer root contract pass omitted user requirement preservation")
    if state.root_reviewer_passed and not state.reviewer_root_checks_verifiability:
        failures.append("Reviewer root contract pass omitted verifiability/testability check")
    if state.root_reviewer_passed and not state.reviewer_root_checks_proof_obligations:
        failures.append("Reviewer root contract pass omitted proof obligation check")
    if state.root_reviewer_passed and not state.reviewer_root_checks_scenario_coverage:
        failures.append("Reviewer root contract pass omitted scenario coverage check")
    if state.root_reviewer_passed and not state.reviewer_root_rejects_report_only_closure:
        failures.append("Reviewer root contract pass omitted report-only closure rejection")

    if state.child_reviewer_passed and not state.reviewer_child_checks_skill_standards:
        failures.append("Reviewer child-skill pass omitted skill standard contract check")
    if state.child_reviewer_passed and not state.reviewer_child_checks_evidence_obligations:
        failures.append("Reviewer child-skill pass omitted evidence obligation check")
    if state.child_reviewer_passed and not state.reviewer_child_checks_approvers:
        failures.append("Reviewer child-skill pass omitted approver check")
    if state.child_reviewer_passed and not state.reviewer_child_checks_skipped_steps:
        failures.append("Reviewer child-skill pass omitted skipped-step check")
    if state.child_reviewer_passed and not state.reviewer_child_rejects_self_approval:
        failures.append("Reviewer child-skill pass omitted self-approval rejection")
    return failures


def reviewer_only_gate_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_reviewer_only_gate_simplification",
        description=(
            "Reviewer-only root-contract and child-skill-manifest gates may "
            "speed up FlowPilot only when Reviewer remains mandatory, removed "
            "officer gates are not default requirements, Reviewer proof/evidence "
            "checks absorb the protected review burden, and route readiness waits "
            "for both PM gate closures."
        ),
        predicate=reviewer_only_gate_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ReviewerOnlyGateStep(),), name="flowpilot_reviewer_only_gate_simplification")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def target_reviewer_only_state() -> State:
    return State(
        status="complete",
        pm_root_contract_written=True,
        root_reviewer_card_emitted=True,
        root_reviewer_passed=True,
        pm_root_contract_frozen=True,
        pm_child_manifest_written=True,
        child_reviewer_card_emitted=True,
        child_reviewer_passed=True,
        pm_child_manifest_approved=True,
        route_ready=True,
    )


def hazard_states() -> dict[str, State]:
    base = target_reviewer_only_state()
    return {
        "root_freeze_without_reviewer": replace(base, root_reviewer_passed=False),
        "root_freeze_waits_for_product_officer": replace(base, root_product_officer_required=True),
        "root_freeze_requires_product_officer_artifact": replace(
            base,
            root_product_officer_artifact_required_for_freeze=True,
        ),
        "root_product_officer_card_emitted": replace(base, root_product_officer_card_emitted=True),
        "child_approval_without_reviewer": replace(base, child_reviewer_passed=False),
        "child_approval_waits_for_process_officer": replace(base, child_process_officer_required=True),
        "child_approval_waits_for_product_officer": replace(base, child_product_officer_required=True),
        "child_approval_requires_process_officer_artifact": replace(
            base,
            child_process_officer_artifact_required_for_approval=True,
        ),
        "child_approval_requires_product_officer_artifact": replace(
            base,
            child_product_officer_artifact_required_for_approval=True,
        ),
        "child_process_officer_card_emitted": replace(base, child_process_officer_card_emitted=True),
        "child_product_officer_card_emitted": replace(base, child_product_officer_card_emitted=True),
        "root_reviewer_omits_verifiability": replace(base, reviewer_root_checks_verifiability=False),
        "root_reviewer_omits_proof_obligations": replace(base, reviewer_root_checks_proof_obligations=False),
        "child_reviewer_omits_skill_standards": replace(base, reviewer_child_checks_skill_standards=False),
        "child_reviewer_omits_evidence_obligations": replace(base, reviewer_child_checks_evidence_obligations=False),
        "pm_consultation_tail_required": replace(base, pm_consultation_required_for_gate=True),
        "role_body_boundary_broken": replace(base, role_body_boundary_preserved=False),
        "legacy_officer_event_handlers_removed": replace(base, legacy_officer_events_preserved=False),
        "route_ready_without_root_freeze": replace(base, pm_root_contract_frozen=False),
        "route_ready_without_child_manifest_approval": replace(base, pm_child_manifest_approved=False),
    }


def optimization_plan() -> dict[str, object]:
    return {
        "schema_version": "flowpilot.reviewer_only_gate_plan.v1",
        "optimization_sequence": [
            {
                "order": 1,
                "gate": "root_contract",
                "change": "PM freeze depends on PM root contract write and Reviewer pass only",
                "removed_default_gates": ["product_officer.root_contract_modelability"],
            },
            {
                "order": 2,
                "gate": "child_skill_manifest",
                "change": "PM approval depends on PM manifest write and Reviewer pass only",
                "removed_default_gates": [
                    "process_officer.child_skill_conformance_model",
                    "product_officer.child_skill_product_fit",
                ],
            },
            {
                "order": 3,
                "gate": "reviewer_cards",
                "change": "Reviewer cards retain proof, evidence, approver, skipped-step, and report-only-closure checks",
                "removed_default_gates": [],
            },
        ],
        "risk_ids_modeled": [
            "R1",
            "R2",
            "R3",
            "R4",
            "R5",
            "R6",
            "R7",
            "R8",
            "R9",
            "R10",
            "R11",
            "R12",
            "R13",
            "R14",
        ],
    }
