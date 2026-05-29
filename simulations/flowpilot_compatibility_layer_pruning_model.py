"""FlowGuard model for FlowPilot compatibility-layer pruning.

The model keeps the new-only maintenance contract explicit: old workflow
acceptance branches and active prompt/spec references must be removed or
rewritten, while current safety fallbacks, negative rejection evidence, and
public facade work that still needs StructureMesh parity evidence are not
silently deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DELETE_RUNTIME_ACCEPTANCE_BRANCH = "delete_runtime_acceptance_branch"
REWRITE_ACTIVE_PROMPT_OR_SPEC = "rewrite_active_prompt_or_spec"
KEEP_NEGATIVE_REJECTION_EVIDENCE = "keep_negative_rejection_evidence"
KEEP_CURRENT_SAFETY_FALLBACK = "keep_current_safety_fallback"
NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE = "needs_structuremesh_before_facade_delete"
KEEP_CHANGE_RATIONALE_OR_HISTORICAL_NOTE = "keep_change_rationale_or_historical_note"
KEEP_CURRENT_STRUCTURAL_TERM = "keep_current_structural_term"
MANUAL_REVIEW = "manual_review"

TERMINAL_ACTIONS = (
    DELETE_RUNTIME_ACCEPTANCE_BRANCH,
    REWRITE_ACTIVE_PROMPT_OR_SPEC,
    KEEP_NEGATIVE_REJECTION_EVIDENCE,
    KEEP_CURRENT_SAFETY_FALLBACK,
    NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE,
    KEEP_CHANGE_RATIONALE_OR_HISTORICAL_NOTE,
    KEEP_CURRENT_STRUCTURAL_TERM,
    MANUAL_REVIEW,
)


@dataclass(frozen=True)
class Candidate:
    """One scanned compatibility/fallback/alias occurrence."""

    candidate_id: str
    path: str
    line: int
    text: str
    surface: str
    has_compatibility_term: bool = False
    has_legacy_term: bool = False
    has_retired_term: bool = False
    has_alias_term: bool = False
    has_fallback_term: bool = False
    has_old_term: bool = False
    teaches_acceptance: bool = False
    rejects_old_path: bool = False
    is_runtime_acceptance_code: bool = False
    is_active_prompt_or_card: bool = False
    is_active_spec: bool = False
    is_change_context: bool = False
    is_test_or_model_evidence: bool = False
    is_current_safety_fallback: bool = False
    is_public_facade_boundary: bool = False
    is_historical_doc: bool = False


@dataclass(frozen=True)
class Action:
    name: str
    candidate_id: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    candidate_id: str = ""
    action: str = ""
    delete_required: bool = False
    rewrite_required: bool = False
    kept_negative_evidence: bool = False
    kept_current_safety_fallback: bool = False
    structuremesh_gate_required: bool = False
    kept_context_note: bool = False
    kept_current_structural_term: bool = False
    manual_review_required: bool = False
    wrongly_kept_old_acceptance: bool = False
    wrongly_deleted_current_safety: bool = False
    wrongly_deleted_negative_evidence: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class CompatibilityLayerPruningStep:
    """Classify one compatibility-layer pruning candidate.

    Input x State -> Set(Output x State)
    reads: candidate surface, old-path terms, acceptance/rejection wording,
    fallback kind, facade boundary
    writes: pruning action, retained-evidence action, or gated follow-up action
    idempotency: classification is read-only and does not mutate files
    """

    name = "CompatibilityLayerPruningStep"
    reads = (
        "candidate_surface",
        "compatibility_terms",
        "acceptance_or_rejection_semantics",
        "fallback_kind",
        "facade_boundary",
    )
    writes = ("pruning_action", "retention_gate", "manual_review_gate")
    input_description = "compatibility-layer source occurrence"
    output_description = "delete, rewrite, keep, or gate classification"
    idempotency = "candidate classification is read-only"

    def apply(self, input_obj: Candidate, state: State) -> Iterable[FunctionResult]:
        for transition in next_states(input_obj, state):
            yield FunctionResult(
                output=Action(transition.label, input_obj.candidate_id),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _terminal(candidate: Candidate, action: str, **updates: object) -> Transition:
    base = State(status="classified", candidate_id=candidate.candidate_id, action=action)
    return Transition(action, replace(base, **updates))


def next_states(input_obj: Candidate, state: State) -> tuple[Transition, ...]:
    if state.status == "classified":
        return ()

    candidate = input_obj

    if candidate.is_current_safety_fallback:
        return (
            _terminal(
                candidate,
                KEEP_CURRENT_SAFETY_FALLBACK,
                kept_current_safety_fallback=True,
            ),
        )

    if candidate.is_test_or_model_evidence and candidate.rejects_old_path:
        return (
            _terminal(
                candidate,
                KEEP_NEGATIVE_REJECTION_EVIDENCE,
                kept_negative_evidence=True,
            ),
        )

    if candidate.is_change_context or candidate.is_historical_doc:
        return (
            _terminal(
                candidate,
                KEEP_CHANGE_RATIONALE_OR_HISTORICAL_NOTE,
                kept_context_note=True,
            ),
        )

    if candidate.is_public_facade_boundary:
        return (
            _terminal(
                candidate,
                NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE,
                structuremesh_gate_required=True,
            ),
        )

    if candidate.is_runtime_acceptance_code and candidate.teaches_acceptance:
        return (
            _terminal(
                candidate,
                DELETE_RUNTIME_ACCEPTANCE_BRANCH,
                delete_required=True,
            ),
        )

    if (
        candidate.is_active_prompt_or_card or candidate.is_active_spec
    ) and candidate.teaches_acceptance:
        return (
            _terminal(
                candidate,
                REWRITE_ACTIVE_PROMPT_OR_SPEC,
                rewrite_required=True,
            ),
        )

    if candidate.rejects_old_path:
        return (
            _terminal(
                candidate,
                KEEP_NEGATIVE_REJECTION_EVIDENCE,
                kept_negative_evidence=True,
            ),
        )

    if (
        candidate.has_compatibility_term
        or candidate.has_legacy_term
        or candidate.has_retired_term
        or candidate.has_alias_term
        or candidate.has_old_term
    ):
        return (
            _terminal(
                candidate,
                MANUAL_REVIEW,
                manual_review_required=True,
            ),
        )

    return (
        _terminal(
            candidate,
            KEEP_CURRENT_STRUCTURAL_TERM,
            kept_current_structural_term=True,
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.wrongly_kept_old_acceptance:
        failures.append("old workflow acceptance was kept as current behavior")
    if state.wrongly_deleted_current_safety:
        failures.append("current safety fallback was classified for deletion")
    if state.wrongly_deleted_negative_evidence:
        failures.append("negative rejection evidence was classified for deletion")
    if state.status == "classified" and state.action not in TERMINAL_ACTIONS:
        failures.append("candidate classified to unknown action")
    if state.status == "classified" and state.action == DELETE_RUNTIME_ACCEPTANCE_BRANCH and not state.delete_required:
        failures.append("delete action did not mark deletion required")
    if state.status == "classified" and state.action == REWRITE_ACTIVE_PROMPT_OR_SPEC and not state.rewrite_required:
        failures.append("rewrite action did not mark rewrite required")
    if state.status == "classified" and state.action == KEEP_CURRENT_SAFETY_FALLBACK and not state.kept_current_safety_fallback:
        failures.append("safety fallback keep action did not preserve fallback gate")
    if state.status == "classified" and state.action == KEEP_NEGATIVE_REJECTION_EVIDENCE and not state.kept_negative_evidence:
        failures.append("negative evidence keep action did not preserve rejection evidence")
    if state.status == "classified" and state.action == NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE and not state.structuremesh_gate_required:
        failures.append("facade deletion candidate lacked StructureMesh gate")
    return failures


def pruning_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="compatibility_layer_pruning",
        description=(
            "Old workflow acceptance branches and active prompt/spec old-path "
            "guidance must be pruned, while current safety fallbacks, negative "
            "rejection evidence, and StructureMesh-gated public facades are not "
            "silently removed."
        ),
        predicate=pruning_invariant,
    ),
)


def build_workflow() -> Workflow:
    return Workflow((CompatibilityLayerPruningStep(),), name="flowpilot_compatibility_layer_pruning")


def is_terminal(state: State) -> bool:
    return state.status == "classified"


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def hazard_states() -> dict[str, State]:
    return {
        "old_acceptance_kept": State(
            status="classified",
            action=KEEP_CURRENT_STRUCTURAL_TERM,
            wrongly_kept_old_acceptance=True,
        ),
        "current_safety_deleted": State(
            status="classified",
            action=DELETE_RUNTIME_ACCEPTANCE_BRANCH,
            wrongly_deleted_current_safety=True,
        ),
        "negative_evidence_deleted": State(
            status="classified",
            action=DELETE_RUNTIME_ACCEPTANCE_BRANCH,
            wrongly_deleted_negative_evidence=True,
        ),
        "facade_deleted_without_gate": State(
            status="classified",
            action=NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE,
            structuremesh_gate_required=False,
        ),
    }


__all__ = [
    "DELETE_RUNTIME_ACCEPTANCE_BRANCH",
    "KEEP_CHANGE_RATIONALE_OR_HISTORICAL_NOTE",
    "KEEP_CURRENT_SAFETY_FALLBACK",
    "KEEP_CURRENT_STRUCTURAL_TERM",
    "KEEP_NEGATIVE_REJECTION_EVIDENCE",
    "MANUAL_REVIEW",
    "NEEDS_STRUCTUREMESH_BEFORE_FACADE_DELETE",
    "REWRITE_ACTIVE_PROMPT_OR_SPEC",
    "Candidate",
    "INVARIANTS",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
