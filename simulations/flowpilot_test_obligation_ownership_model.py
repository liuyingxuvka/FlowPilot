"""FlowGuard model for FlowPilot test-obligation ownership.

This focused model checks the responsibility chain behind FlowGuard model
reports, ordinary tests, and node closure. The main rule is that FlowGuard
officers identify obligations and missing test kinds, PM turns those gaps into
explicit dispositions, workers maintain packet-scoped tests when assigned, and
reviewers block closure when PM's matrix is missing or stale.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 14
GAP_KINDS = ("none", "ordinary_worker", "broad_validation", "alignment_mismatch")
REQUIRED_LABELS = (
    "flowpilot_test_obligation_flow_started",
    "pm_writes_pre_worker_test_obligation_matrix",
    "officer_report_absorbed_with_no_test_gap",
    "officer_report_absorbed_with_ordinary_worker_gap",
    "officer_report_absorbed_with_broad_validation_gap",
    "officer_report_absorbed_with_alignment_mismatch_gap",
    "worker_result_absorbed_for_test_matrix_refresh",
    "pm_updates_post_worker_test_obligation_matrix",
    "worker_test_packet_returns_coverage_rows",
    "testmesh_evidence_completed_for_broad_validation",
    "model_test_alignment_completed_for_mismatch",
    "pm_waives_test_gap_with_authority",
    "pm_records_test_obligation_disposition",
    "reviewer_checks_test_obligation_matrix",
    "pm_node_completion_approved_after_test_disposition",
    "evidence_quality_package_carries_test_rows",
    "final_ledger_carries_test_rows",
    "test_obligation_flow_completed",
)


@dataclass(frozen=True)
class Tick:
    """One FlowPilot test-obligation control transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    pre_worker_matrix_written: bool = False
    officer_report_absorbed: bool = False
    worker_result_absorbed: bool = False
    post_worker_matrix_written: bool = False
    gap_kind: str = "unknown"  # unknown | none | ordinary_worker | broad_validation | alignment_mismatch
    worker_test_packet_completed: bool = False
    worker_test_coverage_rows_returned: bool = False
    testmesh_completed: bool = False
    model_test_alignment_completed: bool = False
    waived_with_authority: bool = False
    all_test_obligations_dispositioned: bool = False
    reviewer_checked_matrix: bool = False
    node_completion_approved: bool = False
    evidence_quality_package_carries_rows: bool = False
    final_ledger_carries_rows: bool = False
    controller_decided_test_disposition: bool = False
    officer_maintained_ordinary_test_code: bool = False
    background_progress_counted_as_pass: bool = False
    missing_test_kinds_left_as_residual_prose: bool = False
    stale_test_evidence_used: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class TestObligationOwnershipStep:
    """Model one PM/officer/worker/reviewer test-obligation handoff.

    Input x State -> Set(Output x State)
    reads: node acceptance plan, officer report rows, worker result evidence,
    background validation artifacts, PM dispositions, reviewer gate package
    writes: matrix rows, owner-specific evidence, PM dispositions, gate status
    idempotency: each tick advances at most one ownership obligation and never
    lets Controller or an officer become the ordinary test-code owner.
    """

    name = "TestObligationOwnershipStep"
    reads = (
        "node_acceptance_plan",
        "officer_model_report",
        "worker_result",
        "pm_disposition",
        "reviewer_gate_package",
        "final_ledger",
    )
    writes = (
        "test_obligation_matrix",
        "test_gap_disposition",
        "reviewer_gate_status",
        "ledger_test_rows",
    )
    input_description = "FlowPilot current-node test obligation tick"
    output_description = "one role-owned test obligation transition"
    idempotency = "test obligation rows are monotonic until route mutation or stale evidence invalidates them"

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


def _gap_ready_for_disposition(state: State) -> bool:
    if state.gap_kind == "none":
        return True
    if state.waived_with_authority:
        return True
    if state.gap_kind == "ordinary_worker":
        return state.worker_test_packet_completed and state.worker_test_coverage_rows_returned
    if state.gap_kind == "broad_validation":
        return state.testmesh_completed
    if state.gap_kind == "alignment_mismatch":
        return state.model_test_alignment_completed
    return False


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    if state.status == "new":
        return (
            Transition(
                "flowpilot_test_obligation_flow_started",
                replace(state, status="running"),
            ),
        )
    if invariant_failures(state):
        return (
            Transition(
                "test_obligation_flow_blocked_on_invariant_failure",
                replace(state, status="blocked"),
            ),
        )
    if not state.pre_worker_matrix_written:
        return (
            Transition(
                "pm_writes_pre_worker_test_obligation_matrix",
                replace(state, pre_worker_matrix_written=True),
            ),
        )
    if not state.officer_report_absorbed:
        return tuple(
            Transition(
                "officer_report_absorbed_with_no_test_gap"
                if gap_kind == "none"
                else f"officer_report_absorbed_with_{gap_kind}_gap",
                replace(state, officer_report_absorbed=True, gap_kind=gap_kind),
            )
            for gap_kind in GAP_KINDS
        )
    if not state.worker_result_absorbed:
        return (
            Transition(
                "worker_result_absorbed_for_test_matrix_refresh",
                replace(state, worker_result_absorbed=True),
            ),
        )
    if not state.post_worker_matrix_written:
        return (
            Transition(
                "pm_updates_post_worker_test_obligation_matrix",
                replace(state, post_worker_matrix_written=True),
            ),
        )
    if state.gap_kind == "ordinary_worker" and not (
        state.worker_test_packet_completed or state.waived_with_authority
    ):
        return (
            Transition(
                "worker_test_packet_returns_coverage_rows",
                replace(
                    state,
                    worker_test_packet_completed=True,
                    worker_test_coverage_rows_returned=True,
                ),
            ),
            Transition(
                "pm_waives_test_gap_with_authority",
                replace(state, waived_with_authority=True),
            ),
        )
    if state.gap_kind == "broad_validation" and not (
        state.testmesh_completed or state.waived_with_authority
    ):
        return (
            Transition(
                "testmesh_evidence_completed_for_broad_validation",
                replace(state, testmesh_completed=True),
            ),
            Transition(
                "pm_waives_test_gap_with_authority",
                replace(state, waived_with_authority=True),
            ),
        )
    if state.gap_kind == "alignment_mismatch" and not (
        state.model_test_alignment_completed or state.waived_with_authority
    ):
        return (
            Transition(
                "model_test_alignment_completed_for_mismatch",
                replace(state, model_test_alignment_completed=True),
            ),
            Transition(
                "pm_waives_test_gap_with_authority",
                replace(state, waived_with_authority=True),
            ),
        )
    if not state.all_test_obligations_dispositioned and _gap_ready_for_disposition(state):
        return (
            Transition(
                "pm_records_test_obligation_disposition",
                replace(state, all_test_obligations_dispositioned=True),
            ),
        )
    if not state.reviewer_checked_matrix:
        return (
            Transition(
                "reviewer_checks_test_obligation_matrix",
                replace(state, reviewer_checked_matrix=True),
            ),
        )
    if not state.node_completion_approved:
        return (
            Transition(
                "pm_node_completion_approved_after_test_disposition",
                replace(state, node_completion_approved=True),
            ),
        )
    if not state.evidence_quality_package_carries_rows:
        return (
            Transition(
                "evidence_quality_package_carries_test_rows",
                replace(state, evidence_quality_package_carries_rows=True),
            ),
        )
    if not state.final_ledger_carries_rows:
        return (
            Transition(
                "final_ledger_carries_test_rows",
                replace(state, final_ledger_carries_rows=True),
            ),
        )
    return (
        Transition(
            "test_obligation_flow_completed",
            replace(state, status="complete"),
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.gap_kind not in {"unknown", *GAP_KINDS}:
        failures.append("test obligation matrix uses an unknown gap kind")
    if state.controller_decided_test_disposition:
        failures.append("Controller decided test obligation disposition")
    if state.officer_maintained_ordinary_test_code:
        failures.append("FlowGuard officer maintained ordinary test code by default")
    if state.background_progress_counted_as_pass:
        failures.append("background progress was counted as passing test evidence")
    if state.missing_test_kinds_left_as_residual_prose:
        failures.append("missing test kinds were left as residual prose")
    if state.stale_test_evidence_used:
        failures.append("stale ordinary test evidence was used for closure")
    if state.worker_result_absorbed and not state.pre_worker_matrix_written:
        failures.append("worker result was absorbed before pre-worker test matrix")
    if state.post_worker_matrix_written and not (
        state.pre_worker_matrix_written and state.officer_report_absorbed and state.worker_result_absorbed
    ):
        failures.append("post-worker test matrix was written before required inputs")
    if state.worker_test_packet_completed and not state.worker_test_coverage_rows_returned:
        failures.append("worker test packet completed without test obligation coverage rows")
    if state.all_test_obligations_dispositioned and not (
        state.pre_worker_matrix_written
        and state.officer_report_absorbed
        and state.worker_result_absorbed
        and state.post_worker_matrix_written
    ):
        failures.append("PM disposition recorded before both test matrix passes")
    if state.all_test_obligations_dispositioned and not _gap_ready_for_disposition(state):
        failures.append("PM disposition recorded before required test owner evidence")
    if state.gap_kind == "ordinary_worker" and state.all_test_obligations_dispositioned and not (
        state.worker_test_packet_completed
        and state.worker_test_coverage_rows_returned
        or state.waived_with_authority
    ):
        failures.append("ordinary missing test kind was closed without worker coverage or waiver")
    if state.gap_kind == "broad_validation" and state.all_test_obligations_dispositioned and not (
        state.testmesh_completed or state.waived_with_authority
    ):
        failures.append("broad validation gap was closed without TestMesh evidence or waiver")
    if state.gap_kind == "alignment_mismatch" and state.all_test_obligations_dispositioned and not (
        state.model_test_alignment_completed or state.waived_with_authority
    ):
        failures.append("model/test mismatch was closed without Model-Test Alignment evidence or waiver")
    if state.reviewer_checked_matrix and not state.all_test_obligations_dispositioned:
        failures.append("reviewer checked package before PM dispositioned test obligations")
    if state.node_completion_approved and not (
        state.reviewer_checked_matrix and state.all_test_obligations_dispositioned
    ):
        failures.append("node completion approved before reviewer checked test dispositions")
    if state.evidence_quality_package_carries_rows and not state.node_completion_approved:
        failures.append("evidence package carried test rows before node completion approval")
    if state.final_ledger_carries_rows and not state.evidence_quality_package_carries_rows:
        failures.append("final ledger carried test rows before evidence quality package")
    if state.status == "complete" and not (
        state.node_completion_approved
        and state.evidence_quality_package_carries_rows
        and state.final_ledger_carries_rows
    ):
        failures.append("test obligation flow completed before node and final ledgers were covered")
    return failures


def test_obligation_ownership_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_test_obligation_ownership",
        description=(
            "PM owns test-obligation matrix and disposition, officers own model "
            "obligations and missing test kinds, workers own packet-scoped test "
            "maintenance, reviewers block unsupported closure, and final ledgers "
            "carry explicit evidence freshness."
        ),
        predicate=test_obligation_ownership_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((TestObligationOwnershipStep(),), name="flowpilot_test_obligation_ownership")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _safe_complete_state(gap_kind: str = "ordinary_worker") -> State:
    state = State(
        status="running",
        pre_worker_matrix_written=True,
        officer_report_absorbed=True,
        worker_result_absorbed=True,
        post_worker_matrix_written=True,
        gap_kind=gap_kind,
    )
    if gap_kind == "ordinary_worker":
        state = replace(
            state,
            worker_test_packet_completed=True,
            worker_test_coverage_rows_returned=True,
        )
    elif gap_kind == "broad_validation":
        state = replace(state, testmesh_completed=True)
    elif gap_kind == "alignment_mismatch":
        state = replace(state, model_test_alignment_completed=True)
    state = replace(
        state,
        all_test_obligations_dispositioned=True,
        reviewer_checked_matrix=True,
        node_completion_approved=True,
        evidence_quality_package_carries_rows=True,
        final_ledger_carries_rows=True,
    )
    return state


def hazard_states() -> dict[str, State]:
    base = _safe_complete_state()
    return {
        "controller_decides_tests": replace(base, controller_decided_test_disposition=True),
        "officer_writes_ordinary_tests": replace(base, officer_maintained_ordinary_test_code=True),
        "background_progress_counted": replace(base, background_progress_counted_as_pass=True),
        "missing_tests_left_as_prose": replace(base, missing_test_kinds_left_as_residual_prose=True),
        "stale_test_evidence_used": replace(base, stale_test_evidence_used=True),
        "post_matrix_before_worker_result": replace(
            base,
            worker_result_absorbed=False,
            post_worker_matrix_written=True,
        ),
        "worker_packet_no_coverage_rows": replace(
            base,
            worker_test_packet_completed=True,
            worker_test_coverage_rows_returned=False,
        ),
        "ordinary_gap_without_worker_or_waiver": replace(
            base,
            worker_test_packet_completed=False,
            worker_test_coverage_rows_returned=False,
            waived_with_authority=False,
        ),
        "broad_gap_without_testmesh": replace(
            _safe_complete_state("broad_validation"),
            testmesh_completed=False,
            waived_with_authority=False,
        ),
        "alignment_gap_without_alignment": replace(
            _safe_complete_state("alignment_mismatch"),
            model_test_alignment_completed=False,
            waived_with_authority=False,
        ),
        "reviewer_before_disposition": replace(
            base,
            all_test_obligations_dispositioned=False,
            reviewer_checked_matrix=True,
        ),
        "node_completion_before_reviewer": replace(
            base,
            reviewer_checked_matrix=False,
            node_completion_approved=True,
        ),
        "final_ledger_before_evidence_package": replace(
            base,
            evidence_quality_package_carries_rows=False,
            final_ledger_carries_rows=True,
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
]
