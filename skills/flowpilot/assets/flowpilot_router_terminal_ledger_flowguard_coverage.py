"""Terminal FlowGuard coverage validation helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_errors import RouterError


FLOWGUARD_TERMINAL_COVERAGE_SCHEMA = "flowpilot.flowguard_terminal_coverage_report.v1"
FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY = "terminal_flowguard_coverage"
FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID = "flowguard-coverage-governance"
FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES = {"accepted", "repaired_and_accepted"}

_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _flowguard_terminal_coverage_issues(
    router: ModuleType,
    report: dict[str, Any],
    route_version: int,
) -> list[str]:
    _bind_router(router)
    issues: list[str] = []
    if not isinstance(report, dict):
        return ["terminal FlowGuard coverage report must be an object"]
    if report.get("schema_version") != FLOWGUARD_TERMINAL_COVERAGE_SCHEMA:
        issues.append("schema_version must be flowpilot.flowguard_terminal_coverage_report.v1")
    if report.get("reviewed_by_role") != "flowguard_operator":
        issues.append("reviewed_by_role must be flowguard_operator")
    if report.get("passed") is not True:
        issues.append("terminal FlowGuard coverage report must pass")
    if report.get("modeled_boundary") != FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY:
        issues.append("modeled_boundary must be terminal_flowguard_coverage")
    if _as_int(report.get("route_version"), default=-1) != route_version:
        issues.append("route_version must match the active route version")
    if report.get("progress_only") is True:
        issues.append("progress-only FlowGuard reports cannot close terminal coverage")

    matrix_ref = report.get("coverage_matrix_ref")
    if not isinstance(matrix_ref, dict) or not str(matrix_ref.get("path") or ""):
        issues.append("coverage_matrix_ref.path is required")
    elif matrix_ref.get("fresh") is not True:
        issues.append("coverage_matrix_ref.fresh must be true")
    elif _as_int(matrix_ref.get("route_version"), default=-1) != route_version:
        issues.append("coverage_matrix_ref.route_version must match the active route version")

    for field in (
        "acceptance_item_closure",
        "route_nodes_examined",
        "flowguard_required_items",
        "flowguard_evidence_found",
        "commands_run",
        "hard_invariants",
        "counterexamples_or_absence",
    ):
        if not _nonempty_list(report.get(field)):
            issues.append(f"{field} must be a non-empty list")
    for field in (
        "missing_or_stale_evidence",
        "model_test_alignment_gaps",
        "blockers",
        "pm_suggestion_items",
        "supplemental_repair_recommendations",
    ):
        if report.get(field) != []:
            issues.append(f"{field} must be an explicit empty list")
    if not isinstance(report.get("confidence_boundary"), str) or not report.get("confidence_boundary").strip():
        issues.append("confidence_boundary must explain the claim boundary")

    self_check = report.get("contract_self_check")
    if not isinstance(self_check, dict):
        issues.append("contract_self_check is required")
    else:
        for field in (
            "all_required_fields_present",
            "no_progress_only_claim",
            "no_unresolved_blockers",
            "pm_acceptance_required",
        ):
            if self_check.get(field) is not True:
                issues.append(f"contract_self_check.{field} must be true")
    return issues


def _validated_flowguard_terminal_coverage_status(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    route_version: int,
    closure_payload: Any,
) -> dict[str, Any]:
    _bind_router(router)
    if not isinstance(closure_payload, dict):
        raise RouterError("final ledger requires flowguard_terminal_coverage_closure")
    if closure_payload.get("status") not in FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES:
        raise RouterError("flowguard terminal coverage closure must be accepted by PM")
    if closure_payload.get("accepted_by_role") != "project_manager":
        raise RouterError("flowguard terminal coverage closure requires accepted_by_role=project_manager")
    if _as_int(closure_payload.get("route_version"), default=-1) != route_version:
        raise RouterError("flowguard terminal coverage closure route_version must match the active route version")
    for field in ("current", "blockers_resolved", "pm_suggestion_items_disposed"):
        if closure_payload.get(field) is not True:
            raise RouterError(f"flowguard terminal coverage closure requires {field}=true")

    report_rel = str(closure_payload.get("report_path") or "")
    matrix_rel = str(closure_payload.get("coverage_matrix_path") or "")
    if not report_rel:
        raise RouterError("flowguard terminal coverage closure requires report_path")
    if not matrix_rel:
        raise RouterError("flowguard terminal coverage closure requires coverage_matrix_path")

    report_path = Path(report_rel)
    if not report_path.is_absolute():
        report_path = project_root / report_path
    report_path = report_path.resolve()
    if not report_path.exists() or not report_path.is_file():
        raise RouterError(f"flowguard terminal coverage report does not exist: {report_rel}")
    expected_hash = str(closure_payload.get("report_hash") or "")
    actual_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    if not expected_hash:
        raise RouterError("flowguard terminal coverage closure requires report_hash")
    if actual_hash != expected_hash:
        raise RouterError("flowguard terminal coverage report_hash does not match report_path")

    matrix_path = Path(matrix_rel)
    if not matrix_path.is_absolute():
        matrix_path = project_root / matrix_path
    if not matrix_path.exists():
        raise RouterError(f"flowguard terminal coverage matrix does not exist: {matrix_rel}")

    report = read_json(report_path)
    report_issues = _flowguard_terminal_coverage_issues(router, report, route_version)
    if report_issues:
        raise RouterError("flowguard terminal coverage report invalid: " + "; ".join(report_issues[:5]))
    return {
        "schema_version": "flowpilot.terminal_flowguard_coverage_closure.v1",
        "segment_id": FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID,
        "status": closure_payload["status"],
        "accepted_by_role": "project_manager",
        "report_path": project_relative(project_root, report_path),
        "report_hash": actual_hash,
        "coverage_matrix_path": project_relative(project_root, matrix_path),
        "route_version": route_version,
        "current": True,
        "blockers_resolved": True,
        "pm_suggestion_items_disposed": True,
        "terminal_replay_segment_status": str(closure_payload.get("terminal_replay_segment_status") or "pending"),
        "report": report,
    }


def _flowguard_terminal_coverage_ledger_entry(
    router: ModuleType,
    route_version: int,
    status: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    return {
        "entry_id": FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID,
        "route_version": route_version,
        "gate_family": "flowguard_terminal_coverage",
        "required_approver": "project_manager",
        "status": "passed",
        "source_of_truth_paths": [status["report_path"], status["coverage_matrix_path"]],
        "evidence_paths": [status["report_path"], status["coverage_matrix_path"]],
        "modeled_boundary": FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY,
        "report_status": status["status"],
        "report_hash": status["report_hash"],
        "current": True,
        "blockers_resolved": True,
        "pm_suggestion_items_disposed": True,
    }


__all__ = (
    "_flowguard_terminal_coverage_issues",
    "_validated_flowguard_terminal_coverage_status",
    "_flowguard_terminal_coverage_ledger_entry",
    "FLOWGUARD_TERMINAL_COVERAGE_SCHEMA",
    "FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY",
    "FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID",
    "FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES",
)

_LOCAL_NAMES = set(globals())
