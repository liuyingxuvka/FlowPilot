"""Final-ledger traceability facade for the FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_router_terminal_ledger_flowguard_coverage as terminal_flowguard_coverage
import flowpilot_router_terminal_ledger_source_entries as terminal_source_entries
import flowpilot_router_terminal_ledger_writer as terminal_writer
from flowpilot_router_errors import RouterError


FLOWGUARD_TERMINAL_COVERAGE_SCHEMA = terminal_flowguard_coverage.FLOWGUARD_TERMINAL_COVERAGE_SCHEMA
FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY = terminal_flowguard_coverage.FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY
FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID = terminal_flowguard_coverage.FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID
FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES = terminal_flowguard_coverage.FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES

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
    for child_module in globals().get("_OWNER_CHILD_MODULES", ()):
        if hasattr(child_module, "_bind_router"):
            child_module._bind_router(router)


def _root_requirement_ids(router: ModuleType, contract: dict[str, Any]) -> list[str]:
    return terminal_source_entries._root_requirement_ids(router, contract)


def _string_list(router: ModuleType, value: Any) -> list[str]:
    return terminal_source_entries._string_list(router, value)


def _route_nodes_with_requirement_trace(
    router: ModuleType,
    nodes: Any,
    root_requirement_ids: list[str],
) -> list[dict[str, Any]]:
    return terminal_source_entries._route_nodes_with_requirement_trace(router, nodes, root_requirement_ids)


def _node_acceptance_traceability_issues(router: ModuleType, payload: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    trace = payload.get("requirement_traceability") if isinstance(payload.get("requirement_traceability"), dict) else {}
    if not trace:
        issues.append(_artifact_issue("requirement_traceability", "missing node requirement traceability object", "project_manager"))
        return issues
    for field in ("source_route_node_id", "source_route_node_covers_requirement_ids", "full_protocol_required_when_flowpilot_invoked", "all_covered_requirements_must_close_or_be_triaged", "closure_by_report_only_forbidden"):
        if trace.get(field) in (None, "", []):
            issues.append(_artifact_issue(f"requirement_traceability.{field}", "missing required traceability field", "project_manager"))
    if trace.get("full_protocol_required_when_flowpilot_invoked") is not True:
        issues.append(_artifact_issue("requirement_traceability.full_protocol_required_when_flowpilot_invoked", "FlowPilot formal node plan must keep full protocol", "project_manager"))
    if trace.get("closure_by_report_only_forbidden") is not True:
        issues.append(_artifact_issue("requirement_traceability.closure_by_report_only_forbidden", "covered requirements cannot close by report-only evidence", "project_manager"))
    node_requirements = payload.get("node_requirements")
    if isinstance(node_requirements, list):
        for index, item in enumerate(node_requirements, start=1):
            if isinstance(item, dict) and (not (router._string_list(item.get("source_requirement_ids")) or router._string_list(item.get("covers_root_requirement_ids")))):
                issues.append(_artifact_issue(f"node_requirements[{index}].source_requirement_ids", "node requirement must map to source/root requirement ids", "project_manager"))
    experiments = payload.get("experiment_plan")
    if isinstance(experiments, list):
        for index, item in enumerate(experiments, start=1):
            if isinstance(item, dict) and (not (router._string_list(item.get("covers_requirements")) or router._string_list(item.get("covers_root_requirement_ids")))):
                issues.append(_artifact_issue(f"experiment_plan[{index}].covers_requirements", "experiment must name covered requirement ids", "project_manager"))
    advance_gate = payload.get("advance_gate") if isinstance(payload.get("advance_gate"), dict) else {}
    if "all_covered_requirements_closed_or_triaged" not in advance_gate:
        issues.append(_artifact_issue("advance_gate.all_covered_requirements_closed_or_triaged", "advance gate must track covered requirement closure", "project_manager"))
    return issues


def _requirement_trace_closure_from_root_replay(
    router: ModuleType,
    contract: dict[str, Any],
    root_replay: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return terminal_source_entries._requirement_trace_closure_from_root_replay(router, contract, root_replay)


def _flowguard_terminal_coverage_issues(
    router: ModuleType,
    report: dict[str, Any],
    route_version: int,
) -> list[str]:
    return terminal_flowguard_coverage._flowguard_terminal_coverage_issues(router, report, route_version)


def _validated_flowguard_terminal_coverage_status(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    route_version: int,
    closure_payload: Any,
) -> dict[str, Any]:
    return terminal_flowguard_coverage._validated_flowguard_terminal_coverage_status(
        router,
        project_root,
        run_root,
        route_version,
        closure_payload,
    )


def _flowguard_terminal_coverage_ledger_entry(
    router: ModuleType,
    route_version: int,
    status: dict[str, Any],
) -> dict[str, Any]:
    return terminal_flowguard_coverage._flowguard_terminal_coverage_ledger_entry(router, route_version, status)


def _final_ledger_traceability_issues(router: ModuleType, payload: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    closure = payload.get("requirement_trace_closure")
    if not isinstance(closure, list) or not closure:
        issues.append(_artifact_issue("requirement_trace_closure", "final ledger requires requirement trace closure rows", "project_manager"))
        return issues
    for index, item in enumerate(closure, start=1):
        if not isinstance(item, dict):
            issues.append(_artifact_issue(f"requirement_trace_closure[{index}]", "closure row must be an object", "project_manager"))
            continue
        if not item.get("requirement_id"):
            issues.append(_artifact_issue(f"requirement_trace_closure[{index}].requirement_id", "missing requirement id", "project_manager"))
        if item.get("status") not in {"resolved", "superseded", "waived"}:
            issues.append(_artifact_issue(f"requirement_trace_closure[{index}].status", "effective requirement must be resolved, superseded, or waived", "project_manager"))
        if item.get("status") == "resolved" and (not item.get("evidence_paths") or item.get("direct_evidence_checked") is not True):
            issues.append(_artifact_issue(f"requirement_trace_closure[{index}].evidence_paths", "resolved requirement needs direct checked evidence", "project_manager"))
        if item.get("status") == "waived" and (not item.get("waiver_authority")):
            issues.append(_artifact_issue(f"requirement_trace_closure[{index}].waiver_authority", "waived requirement needs waiver authority", "project_manager"))
    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    if int(counts.get("unresolved_requirement_count", 0) or 0) != 0:
        issues.append(_artifact_issue("counts.unresolved_requirement_count", "final ledger requires unresolved_requirement_count=0", "project_manager"))
    integrity = payload.get("evidence_integrity") if isinstance(payload.get("evidence_integrity"), dict) else {}
    for field in ("requirement_trace_checked", "every_effective_requirement_closure_row_present", "requirement_direct_evidence_checked", "requirement_waiver_authority_checked", "requirement_stale_status_checked"):
        if integrity.get(field) is not True:
            issues.append(_artifact_issue(f"evidence_integrity.{field}", "final ledger traceability integrity field must be true", "project_manager"))
    coverage_closure = payload.get("flowguard_terminal_coverage_closure")
    if not isinstance(coverage_closure, dict):
        issues.append(_artifact_issue("flowguard_terminal_coverage_closure", "missing PM-accepted terminal FlowGuard coverage closure", "project_manager"))
    else:
        expected = {
            "segment_id": FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID,
            "accepted_by_role": "project_manager",
            "current": True,
            "blockers_resolved": True,
            "pm_suggestion_items_disposed": True,
        }
        for field, value in expected.items():
            if coverage_closure.get(field) != value:
                issues.append(_artifact_issue(f"flowguard_terminal_coverage_closure.{field}", "terminal FlowGuard coverage closure field is invalid", "project_manager"))
        if coverage_closure.get("status") not in FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES:
            issues.append(_artifact_issue("flowguard_terminal_coverage_closure.status", "terminal FlowGuard coverage closure must be accepted", "project_manager"))
        if coverage_closure.get("terminal_replay_segment_status") not in {"pending", "passed"}:
            issues.append(_artifact_issue("flowguard_terminal_coverage_closure.terminal_replay_segment_status", "terminal FlowGuard replay segment status must be pending or passed", "project_manager"))
        for field in ("report_path", "report_hash", "coverage_matrix_path"):
            if not coverage_closure.get(field):
                issues.append(_artifact_issue(f"flowguard_terminal_coverage_closure.{field}", "terminal FlowGuard coverage closure requires report and matrix references", "project_manager"))
    return issues


def _validated_root_replay(router: ModuleType, payload: dict[str, Any], required_ids: list[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    replay = payload.get("root_contract_replay")
    if not isinstance(replay, list) or not replay:
        raise RouterError("final ledger requires root_contract_replay for every frozen root requirement")
    by_id = {str(item.get("requirement_id")): item for item in replay if isinstance(item, dict)}
    missing = [req_id for req_id in required_ids if req_id not in by_id]
    if missing:
        raise RouterError(f"final ledger missing root contract replay for: {', '.join(missing)}")
    failed = [req_id for req_id in required_ids if by_id[req_id].get("status") != "approved" or not by_id[req_id].get("evidence_paths")]
    if failed:
        raise RouterError(f"final ledger root contract replay not approved with evidence for: {', '.join(failed)}")
    return [by_id[req_id] for req_id in required_ids]


def _build_source_of_truth_final_entries(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    frontier: dict[str, Any],
    route: dict[str, Any],
    mutations: dict[str, Any],
    contract: dict[str, Any],
    root_replay: list[dict[str, Any]],
    child_manifest: dict[str, Any],
    evidence_ledger: dict[str, Any],
    generated_ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    return terminal_source_entries._build_source_of_truth_final_entries(
        router,
        project_root,
        run_root,
        frontier,
        route,
        mutations,
        contract,
        root_replay,
        child_manifest,
        evidence_ledger,
        generated_ledger,
    )


def _route_mutation_completion_issues(
    router: ModuleType,
    frontier: dict[str, Any],
    mutations: dict[str, Any],
) -> list[str]:
    _bind_router(router)
    issues: list[str] = []
    if frontier.get("status") == "route_mutation_pending_recheck":
        pending = frontier.get("pending_route_mutation") or {}
        candidate = pending.get("candidate_node_id") or "unknown candidate"
        issues.append(f"route mutation pending recheck for {candidate}")
    completed = {str(item) for item in frontier.get("completed_nodes") or []}
    active_node_id = str(frontier.get("active_node_id") or "")
    for item in mutations.get("items") or []:
        if not isinstance(item, dict):
            continue
        restart_policy = item.get("repair_restart_policy") or {}
        if restart_policy.get("same_scope_replay_rerun_required") is not True:
            continue
        mutation_node_id = str(item.get("active_node_id") or "")
        if not mutation_node_id:
            issues.append(f"route mutation {item.get('route_version', 'unknown')} lacks active mutation node")
            continue
        if mutation_node_id not in completed:
            if mutation_node_id == active_node_id:
                issues.append(f"route mutation node {mutation_node_id} is active but not completed")
            else:
                issues.append(f"route mutation node {mutation_node_id} is not completed after replacement")
    return issues


def _write_final_route_wide_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    terminal_writer._write_final_route_wide_ledger(router, project_root, run_root, run_state, payload)


_OWNER_CHILD_MODULES = (
    terminal_flowguard_coverage,
    terminal_source_entries,
    terminal_writer,
)

__all__ = (
    "_root_requirement_ids",
    "_string_list",
    "_route_nodes_with_requirement_trace",
    "_node_acceptance_traceability_issues",
    "_requirement_trace_closure_from_root_replay",
    "_final_ledger_traceability_issues",
    "_flowguard_terminal_coverage_issues",
    "_validated_flowguard_terminal_coverage_status",
    "_flowguard_terminal_coverage_ledger_entry",
    "_validated_root_replay",
    "_build_source_of_truth_final_entries",
    "_route_mutation_completion_issues",
    "_write_final_route_wide_ledger",
    "FLOWGUARD_TERMINAL_COVERAGE_SCHEMA",
    "FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY",
    "FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID",
    "FLOWGUARD_TERMINAL_COVERAGE_ACCEPTED_STATUSES",
)

_LOCAL_NAMES = set(globals())
