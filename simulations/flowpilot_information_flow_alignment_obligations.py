"""Information-flow alignment obligation catalog."""

from __future__ import annotations

from typing import Any

from flowpilot_model_test_alignment_common import (
    EDGE,
    FAILURE,
    HAPPY,
    NEGATIVE,
    PASSED,
    REPLAY,
    _obligation,
)


MODEL_ID = "flowpilot_information_flow_alignment"
CHECK_COMMAND = (
    "python simulations/run_flowpilot_information_flow_alignment_checks.py "
    "--json-out simulations/flowpilot_information_flow_alignment_results.json"
)

OBL_BLOCKER_PAYLOAD = "info_flow.blocker.current_payload_to_pm"
OBL_REQUIRED_REPAIR = "info_flow.blocker.required_repair_to_pm_package"
OBL_WORKER_DELTA = "info_flow.blocker.worker_packet_progress_delta"
OBL_RECHECK_FOLLOWUP = "info_flow.blocker.reviewer_recheck_followup"
OBL_RESUME_CURRENT = "info_flow.resume.current_authority_context"
OBL_REOPEN_HISTORY = "info_flow.reopen.history_not_current_authority"
OBL_BREAK_GLASS = "info_flow.break_glass.bounded_reintegrated_repair"
OBL_ROUTE_MUTATION = "info_flow.route_mutation.blocker_acceptance_replay_scope"
OBL_ROLE_ASSIGNMENT = "info_flow.role_assignment.current_packet_binding"
OBL_CLOSURE_STOP = "info_flow.closure.unresolved_gap_stop_boundary"


def _obligations() -> tuple[Any, ...]:
    return (
        _obligation(
            OBL_BLOCKER_PAYLOAD,
            obligation_type="information_contract",
            description=(
                "Current blocker payload reaches PM with blocker id, source "
                "result, specific failure, PM-visible role summary, and "
                "authorized result reads."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_REQUIRED_REPAIR,
            obligation_type="information_contract",
            description=(
                "Reviewer required_repair and recommendation are preserved "
                "into the PM repair decision/package instead of being replaced "
                "by a generic reason."
            ),
            required_test_kinds=(HAPPY, EDGE, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_WORKER_DELTA,
            obligation_type="progress_contract",
            description=(
                "Repair packets issued to workers carry current blocker "
                "context, new repair direction, allowed reads/writes, "
                "forbidden actions, success evidence, and a fresh generation."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_RECHECK_FOLLOWUP,
            obligation_type="gate_contract",
            description=(
                "Reviewer recheck is bound to the current blocker and worker "
                "evidence; failed recheck produces a visible follow-up blocker "
                "instead of silent closure."
            ),
            required_test_kinds=(HAPPY, EDGE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_RESUME_CURRENT,
            obligation_type="resume_contract",
            description=(
                "Manual resume/reentry loads current run, frontier, packet "
                "ledger, active blocker, and PM decision state before any next "
                "action."
            ),
            required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_REOPEN_HISTORY,
            obligation_type="authority_boundary",
            description=(
                "Reopened continuation may import old state only as history; "
                "old evidence and old agent ids cannot authorize current work."
            ),
            required_test_kinds=(NEGATIVE, REPLAY),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_BREAK_GLASS,
            obligation_type="emergency_control_contract",
            description=(
                "Break-glass is limited to FlowPilot control-plane repair after "
                "normal repair failure and must record bounded scope, evidence, "
                "validation, and PM/reviewer/FlowGuard reintegration."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_ROUTE_MUTATION,
            obligation_type="route_mutation_contract",
            description=(
                "Route mutation carries the blocker context, new route version, "
                "replacement acceptance plan, stale-evidence invalidation, and "
                "replay scope."
            ),
            required_test_kinds=(HAPPY, EDGE, REPLAY),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_ROLE_ASSIGNMENT,
            obligation_type="role_assignment_contract",
            description=(
                "Manual resume and role dispatch name only the currently "
                "requested responsibility, bind any assignment or lease to the "
                "current packet/task, and do not restore, prewarm, or infer a "
                "fixed role set from stale role state."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
        _obligation(
            OBL_CLOSURE_STOP,
            obligation_type="terminal_boundary",
            description=(
                "Closure cannot pass with unresolved information gaps; user or "
                "protocol stop preserves unresolved work and quarantines stale "
                "control-plane artifacts."
            ),
            required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        ),
    )
