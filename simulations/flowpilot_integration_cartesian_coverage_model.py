"""Full-domain Cartesian coverage for FlowPilot system-integration duty.

This model checks the prompt/workflow authority boundary for integration
quality. It deliberately does not add a runtime hard blocker: semantic
integration findings are routed through PM, Reviewer, FlowGuard operator, and
Worker prompt surfaces while runtime remains mechanical.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_integration_cartesian_coverage"
MAX_SEQUENCE_LENGTH = 2

STAGES = (
    "product_architecture",
    "route_skeleton",
    "node_acceptance",
    "worker_result_absorption",
    "parent_backward_replay",
    "final_ledger",
    "final_backward_replay",
    "model_miss_triage",
)

ROLES = (
    "project_manager",
    "human_like_reviewer",
    "flowguard_operator",
    "worker",
)

ARTIFACT_FAMILIES = (
    "software_code",
    "ui_app",
    "writing_report_novel",
    "research_source_backed",
    "skill_workflow",
)

FAILURE_CLASSES = (
    "missing_integration_intent",
    "flat_checklist_route",
    "duplicate_sibling_work",
    "producer_after_consumer",
    "orphan_output",
    "consumer_missing",
    "child_outputs_do_not_compose",
    "final_output_scattered",
    "integration_issue_downgraded_to_nonblocking",
    "optimization_incorrectly_hard_blocked",
    "model_miss_not_triggered",
)

SEVERITIES = (
    "hard_failure",
    "pm_decision_support",
    "nonblocking_note",
)

AUTHORITIES = (
    "prompt_only",
    "reviewer_suggestion",
    "flowguard_suggestion",
    "pm_hard_disposition",
    "runtime_mechanical_rejection",
)

EVIDENCE_TIMINGS = (
    "pre_work",
    "node_entry",
    "post_worker",
    "parent_closure",
    "terminal_closure",
)

EXPECTED_OUTCOMES = (
    "continue_current_flow",
    "pm_suggestion",
    "same_node_repair",
    "route_mutation",
    "model_miss_triage",
    "terminal_block",
)

AXIS_VALUES = {
    "stage": STAGES,
    "role": ROLES,
    "artifact_family": ARTIFACT_FAMILIES,
    "failure_class": FAILURE_CLASSES,
    "severity": SEVERITIES,
    "authority": AUTHORITIES,
    "evidence_timing": EVIDENCE_TIMINGS,
    "expected_outcome": EXPECTED_OUTCOMES,
}

HARD_ROUTE_FAILURES = {
    "flat_checklist_route",
    "producer_after_consumer",
    "orphan_output",
    "consumer_missing",
}

HARD_PARENT_FAILURES = {
    "child_outputs_do_not_compose",
}

HARD_FINAL_FAILURES = {
    "final_output_scattered",
}

MODEL_MISS_FAILURES = {
    "model_miss_not_triggered",
}

ADVISORY_FAILURES = {
    "duplicate_sibling_work",
    "optimization_incorrectly_hard_blocked",
}


def _sanitize(value: str) -> str:
    return value.replace("_", "-")


def expected_outcome_for(
    *,
    stage: str,
    role: str,
    artifact_family: str,
    failure_class: str,
    severity: str,
    authority: str,
    evidence_timing: str,
) -> str:
    del role, artifact_family, authority, evidence_timing
    if failure_class in ADVISORY_FAILURES:
        return "pm_suggestion"
    if severity == "nonblocking_note":
        return "continue_current_flow"
    if severity == "pm_decision_support":
        return "pm_suggestion"
    if failure_class == "missing_integration_intent":
        return "same_node_repair" if stage == "product_architecture" else "route_mutation"
    if failure_class in HARD_ROUTE_FAILURES:
        return "route_mutation"
    if failure_class in HARD_PARENT_FAILURES:
        return "same_node_repair" if stage == "parent_backward_replay" else "route_mutation"
    if failure_class in HARD_FINAL_FAILURES:
        return "terminal_block" if stage in {"final_ledger", "final_backward_replay"} else "route_mutation"
    if failure_class == "integration_issue_downgraded_to_nonblocking":
        return "terminal_block" if stage in {"final_ledger", "final_backward_replay"} else "same_node_repair"
    if failure_class in MODEL_MISS_FAILURES:
        return "model_miss_triage"
    return "same_node_repair"


def _required_authority_for(role: str, authority: str, expected_outcome: str) -> str:
    if authority == "runtime_mechanical_rejection":
        return "prompt_or_pm_decision_not_runtime_mechanical_rejection"
    if role == "worker":
        return "worker_reports_blocked_needs_pm_or_pm_suggestion"
    if expected_outcome in {"route_mutation", "same_node_repair", "terminal_block", "model_miss_triage"}:
        return "project_manager"
    if role == "human_like_reviewer":
        return "reviewer_pm_decision_support"
    if role == "flowguard_operator":
        return "flowguard_pm_decision_support"
    return "project_manager"


def _cell(
    *,
    stage: str,
    role: str,
    artifact_family: str,
    failure_class: str,
    severity: str,
    authority: str,
    evidence_timing: str,
) -> dict[str, Any]:
    expected_outcome = expected_outcome_for(
        stage=stage,
        role=role,
        artifact_family=artifact_family,
        failure_class=failure_class,
        severity=severity,
        authority=authority,
        evidence_timing=evidence_timing,
    )
    return {
        "cell_id": ".".join(
            _sanitize(value)
            for value in (
                stage,
                role,
                artifact_family,
                failure_class,
                severity,
                authority,
                evidence_timing,
            )
        ),
        "model_id": MODEL_ID,
        "stage": stage,
        "role": role,
        "artifact_family": artifact_family,
        "failure_class": failure_class,
        "severity": severity,
        "authority": authority,
        "evidence_timing": evidence_timing,
        "expected_outcome": expected_outcome,
        "required_authority": _required_authority_for(role, authority, expected_outcome),
        "runtime_hard_blocker_allowed": False,
        "worker_current_gate_blocker_allowed": False,
        "prompt_level_optimization": True,
        "coverage_shard_id": f"integration:{stage}:{role}:{artifact_family}:{failure_class}:{severity}",
    }


def iter_required_cells() -> Iterable[dict[str, Any]]:
    for stage, role, artifact_family, failure_class, severity, authority, evidence_timing in product(
        STAGES,
        ROLES,
        ARTIFACT_FAMILIES,
        FAILURE_CLASSES,
        SEVERITIES,
        AUTHORITIES,
        EVIDENCE_TIMINGS,
    ):
        yield _cell(
            stage=stage,
            role=role,
            artifact_family=artifact_family,
            failure_class=failure_class,
            severity=severity,
            authority=authority,
            evidence_timing=evidence_timing,
        )


def required_cell_count() -> int:
    return (
        len(STAGES)
        * len(ROLES)
        * len(ARTIFACT_FAMILIES)
        * len(FAILURE_CLASSES)
        * len(SEVERITIES)
        * len(AUTHORITIES)
        * len(EVIDENCE_TIMINGS)
    )


def build_required_cells(limit: int | None = None) -> tuple[dict[str, Any], ...]:
    cells: list[dict[str, Any]] = []
    for index, cell in enumerate(iter_required_cells()):
        if limit is not None and index >= limit:
            break
        cells.append(cell)
    return tuple(cells)


def axis_value_coverage() -> dict[str, dict[str, list[str]]]:
    present = {axis: set() for axis in AXIS_VALUES}
    for cell in iter_required_cells():
        for axis in (
            "stage",
            "role",
            "artifact_family",
            "failure_class",
            "severity",
            "authority",
            "evidence_timing",
            "expected_outcome",
        ):
            present[axis].add(str(cell[axis]))
    return {
        axis: {
            "present": sorted(present[axis]),
            "missing": sorted(set(values) - present[axis]),
        }
        for axis, values in AXIS_VALUES.items()
    }


def matrix_counts() -> dict[str, int]:
    return {
        "required_cell_count": required_cell_count(),
        "axis_count": len(AXIS_VALUES),
    }


def matrix_failures(cells: Iterable[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for cell in cells:
        if cell["authority"] == "runtime_mechanical_rejection" and cell["runtime_hard_blocker_allowed"]:
            failures.append(f"{cell['cell_id']}: semantic integration used runtime hard blocker")
        if cell["role"] == "worker" and cell["worker_current_gate_blocker_allowed"]:
            failures.append(f"{cell['cell_id']}: worker claimed current_gate_blocker authority")
        if (
            cell["severity"] == "hard_failure"
            and cell["failure_class"] not in ADVISORY_FAILURES
            and cell["expected_outcome"] in {"continue_current_flow", "pm_suggestion"}
        ):
            failures.append(f"{cell['cell_id']}: hard integration failure underblocked")
        if cell["severity"] != "hard_failure" and cell["expected_outcome"] in {"same_node_repair", "route_mutation", "terminal_block"}:
            failures.append(f"{cell['cell_id']}: advisory integration finding overblocked")
        if cell["failure_class"] == "optimization_incorrectly_hard_blocked" and cell["expected_outcome"] != "pm_suggestion":
            failures.append(f"{cell['cell_id']}: optimization case was not PM decision support")
        if cell["failure_class"] == "model_miss_not_triggered" and cell["severity"] == "hard_failure" and cell["expected_outcome"] != "model_miss_triage":
            failures.append(f"{cell['cell_id']}: model miss case did not route to triage")
    return failures


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    every_axis_value_covered: bool = True
    every_cell_has_expected_outcome: bool = True
    hard_failures_underblocked: bool = False
    advisory_findings_overblocked: bool = False
    runtime_semantic_hard_blocker_added: bool = False
    worker_claimed_current_gate_blocker: bool = False
    model_miss_not_routed: bool = False


@dataclass(frozen=True)
class Tick:
    """One integration Cartesian coverage decision."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


VALID_SCENARIOS = {"valid_integration_cartesian_matrix"}
SCENARIOS = {
    "valid_integration_cartesian_matrix": State(scenario="valid_integration_cartesian_matrix", status="selected"),
    "missing_axis_value": replace(State(scenario="missing_axis_value", status="selected"), every_axis_value_covered=False),
    "missing_expected_outcome": replace(State(scenario="missing_expected_outcome", status="selected"), every_cell_has_expected_outcome=False),
    "hard_failure_underblocked": replace(State(scenario="hard_failure_underblocked", status="selected"), hard_failures_underblocked=True),
    "advisory_overblocked": replace(State(scenario="advisory_overblocked", status="selected"), advisory_findings_overblocked=True),
    "runtime_semantic_hard_blocker": replace(State(scenario="runtime_semantic_hard_blocker", status="selected"), runtime_semantic_hard_blocker_added=True),
    "worker_current_gate_blocker": replace(State(scenario="worker_current_gate_blocker", status="selected"), worker_claimed_current_gate_blocker=True),
    "model_miss_not_routed": replace(State(scenario="model_miss_not_routed", status="selected"), model_miss_not_routed=True),
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def state_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.every_axis_value_covered:
        failures.append("integration_cartesian_axis_value_missing")
    if not state.every_cell_has_expected_outcome:
        failures.append("integration_cartesian_expected_outcome_missing")
    if state.hard_failures_underblocked:
        failures.append("hard_integration_failure_underblocked_as_advisory")
    if state.advisory_findings_overblocked:
        failures.append("advisory_integration_finding_overblocked")
    if state.runtime_semantic_hard_blocker_added:
        failures.append("semantic_integration_added_runtime_hard_blocker")
    if state.worker_claimed_current_gate_blocker:
        failures.append("worker_claimed_current_gate_blocker_for_integration")
    if state.model_miss_not_routed:
        failures.append("scattered_integration_model_miss_not_routed")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = state_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def initial_state() -> State:
    return State()


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted" and state_failures(state):
        return InvariantResult.fail("; ".join(state_failures(state)))
    if state.status == "rejected" and not state_failures(state):
        return InvariantResult.fail("safe integration Cartesian matrix state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted integration Cartesian states cannot miss axes or outcomes, underblock hard failures, overblock advisory findings, add runtime hard blockers, give Worker current_gate_blocker authority, or skip model-miss triage.",
        accepted_states_are_safe,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


class IntegrationCartesianCoverageStep:
    """Classify one integration Cartesian coverage scenario.

    Input x State -> Set(Output x State)
    reads: stage, role, artifact family, failure class, severity, authority,
    evidence timing, prompt/workflow authority boundary
    writes: expected PM/reviewer/FlowGuard/worker outcome and coverage shard
    idempotency: pure classification keyed by Cartesian cell id
    """

    name = "IntegrationCartesianCoverageStep"
    reads = ("integration_cartesian_axes", "prompt_authority_boundary")
    writes = ("integration_expected_outcome", "coverage_shard")
    input_description = "one FlowPilot integration Cartesian scenario"
    output_description = "expected prompt-level integration outcome"
    idempotency = "classification is keyed by integration Cartesian cell id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def build_workflow() -> Workflow:
    return Workflow((IntegrationCartesianCoverageStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    return [
        str(result.message)
        for invariant in INVARIANTS
        for result in (invariant.predicate(state, ()),)
        if not result.ok
    ]


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: state_failures(state) for name, state in hazard_states().items()}
