"""FlowGuard model for FlowPilot validation artifact canonicalization.

The model captures the maintenance rule for result artifacts: when a current
``*_results.json`` artifact and an older ``*_checks_results.json`` shadow exist
for the same family, the current result is the authority. Shadow artifacts may
remain only as reported duplicates or historical evidence; they must not carry
stale unsupported_historical semantics as current proof.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow

RESOURCE_BOUNDEDNESS_CHILD_BINDING = {
    "model_id": "flowpilot_control_plane_resource_boundedness",
    "owned_obligation": "stdout_stderr_single_raw_authority_and_bounded_combined_index",
    "claim_boundary": "artifact canonicalization retains current evidence selection; the child owns physical duplication bounds",
}


CANONICAL_PAIR_CURRENT = "canonical_pair_current"
SHADOW_ONLY_CURRENT = "shadow_only_current"
EXACT_DUPLICATE_PAIR_REPORTED = "exact_duplicate_pair_reported"
STALE_SHADOW_ALIAS_WITH_CANONICAL = "stale_shadow_alias_with_canonical"
SHADOW_USED_AS_CURRENT_WITH_CANONICAL = "shadow_used_as_current_with_canonical"
READ_ONLY_AUDIT_MUTATES_FILES = "read_only_audit_mutates_files"

VALID_SCENARIOS = (
    CANONICAL_PAIR_CURRENT,
    SHADOW_ONLY_CURRENT,
    EXACT_DUPLICATE_PAIR_REPORTED,
)

NEGATIVE_SCENARIOS = (
    STALE_SHADOW_ALIAS_WITH_CANONICAL,
    SHADOW_USED_AS_CURRENT_WITH_CANONICAL,
    READ_ONLY_AUDIT_MUTATES_FILES,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

EXPECTED_REJECTIONS = {
    STALE_SHADOW_ALIAS_WITH_CANONICAL: "shadow artifact with unsupported alias semantics cannot be current evidence",
    SHADOW_USED_AS_CURRENT_WITH_CANONICAL: "shadow artifact was selected while canonical result exists",
    READ_ONLY_AUDIT_MUTATES_FILES: "read-only artifact audit mutated files",
}

REQUIRED_LABELS = tuple(f"{scenario}_accepted" for scenario in VALID_SCENARIOS) + tuple(
    f"{scenario}_rejected" for scenario in NEGATIVE_SCENARIOS
)


@dataclass(frozen=True)
class Tick:
    """One validation artifact maintenance scenario."""

    scenario: str


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    canonical_result_exists: bool = False
    shadow_result_exists: bool = False
    canonical_preferred: bool = False
    shadow_used_as_current: bool = False
    shadow_has_unsupported_alias_semantics: bool = False
    shadow_pair_reported: bool = False
    exact_duplicate_reported: bool = False
    cleanup_required_reported: bool = False
    audit_read_only: bool = True


class Transition(NamedTuple):
    label: str
    state: State


class ValidationArtifactCanonicalizationStep:
    """Model one artifact-canonicalization decision.

    Input x State -> Set(Output x State)
    reads: artifact pair shape, canonical result presence, shadow semantics,
    audit mode
    writes: selected evidence authority, audit finding, cleanup requirement
    idempotency: read-only audit reports findings without mutating artifacts
    """

    name = "ValidationArtifactCanonicalizationStep"
    reads = ("artifact_pair", "artifact_semantics", "audit_mode")
    writes = ("evidence_authority", "audit_finding", "cleanup_requirement")
    input_description = "validation artifact pair or shadow-only artifact"
    output_description = "accepted canonical evidence or rejected stale shadow evidence"
    idempotency = "read-only artifact audits do not mutate validation files"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        for transition in next_states(input_obj, state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _accept(scenario: str, state: State) -> Transition:
    return Transition(f"{scenario}_accepted", replace(state, status="accepted"))


def _reject(scenario: str, state: State) -> Transition:
    return Transition(f"{scenario}_rejected", replace(state, status="rejected"))


def next_states(input_obj: Tick, state: State) -> tuple[Transition, ...]:
    if state.status in {"accepted", "rejected"}:
        return ()
    scenario = input_obj.scenario
    if scenario == CANONICAL_PAIR_CURRENT:
        next_state = replace(
            state,
            scenario=scenario,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_pair_reported=True,
        )
        return (_accept(scenario, next_state),)
    if scenario == SHADOW_ONLY_CURRENT:
        next_state = replace(
            state,
            scenario=scenario,
            shadow_result_exists=True,
            shadow_used_as_current=True,
            shadow_pair_reported=False,
        )
        return (_accept(scenario, next_state),)
    if scenario == EXACT_DUPLICATE_PAIR_REPORTED:
        next_state = replace(
            state,
            scenario=scenario,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_pair_reported=True,
            exact_duplicate_reported=True,
        )
        return (_accept(scenario, next_state),)
    if scenario == STALE_SHADOW_ALIAS_WITH_CANONICAL:
        next_state = replace(
            state,
            scenario=scenario,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=False,
            shadow_has_unsupported_alias_semantics=True,
            cleanup_required_reported=True,
        )
        return (_reject(scenario, next_state),)
    if scenario == SHADOW_USED_AS_CURRENT_WITH_CANONICAL:
        next_state = replace(
            state,
            scenario=scenario,
            canonical_result_exists=True,
            shadow_result_exists=True,
            shadow_used_as_current=True,
            shadow_pair_reported=True,
        )
        return (_reject(scenario, next_state),)
    if scenario == READ_ONLY_AUDIT_MUTATES_FILES:
        next_state = replace(
            state,
            scenario=scenario,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_pair_reported=True,
            audit_read_only=False,
        )
        return (_reject(scenario, next_state),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "rejected":
        return failures
    if state.canonical_result_exists and state.shadow_result_exists:
        if state.shadow_used_as_current:
            failures.append("shadow artifact was selected while canonical result exists")
        if not state.shadow_pair_reported:
            failures.append("shadow artifact pair was not reported")
    if (
        state.canonical_result_exists
        and state.shadow_result_exists
        and state.shadow_has_unsupported_alias_semantics
        and state.status == "accepted"
    ):
        failures.append("shadow artifact with unsupported alias semantics cannot be current evidence")
    if state.shadow_has_unsupported_alias_semantics and not state.cleanup_required_reported:
        failures.append("stale shadow artifact cleanup requirement was not reported")
    if not state.audit_read_only:
        failures.append("read-only artifact audit mutated files")
    return failures


def canonicalization_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="validation_artifact_canonicalization",
        description=(
            "Canonical result artifacts are preferred over shadow check artifacts, "
            "stale unsupported_historical semantics are not current evidence, and read-only "
            "audits do not mutate files."
        ),
        predicate=canonicalization_invariant,
    ),
)

EXTERNAL_INPUTS = tuple(Tick(scenario) for scenario in SCENARIOS)
MAX_SEQUENCE_LENGTH = 1


def build_workflow() -> Workflow:
    return Workflow((ValidationArtifactCanonicalizationStep(),), name="flowpilot_validation_artifact_canonicalization")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def hazard_states() -> dict[str, State]:
    return {
        "accepted_stale_shadow_alias": State(
            status="accepted",
            scenario=STALE_SHADOW_ALIAS_WITH_CANONICAL,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_has_unsupported_alias_semantics=True,
            shadow_pair_reported=True,
            cleanup_required_reported=True,
        ),
        "unreported_shadow_pair": State(
            status="accepted",
            scenario=CANONICAL_PAIR_CURRENT,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_pair_reported=False,
        ),
        "read_only_mutation": State(
            status="accepted",
            scenario=READ_ONLY_AUDIT_MUTATES_FILES,
            canonical_result_exists=True,
            shadow_result_exists=True,
            canonical_preferred=True,
            shadow_pair_reported=True,
            audit_read_only=False,
        ),
    }


__all__ = [
    "EXPECTED_REJECTIONS",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
