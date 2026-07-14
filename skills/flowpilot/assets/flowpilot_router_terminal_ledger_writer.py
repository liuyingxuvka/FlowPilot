"""Final route-wide ledger writer for the FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_material_artifact_map as material_artifact_map
from flowpilot_router_errors import RouterError


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


def _write_final_route_wide_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    _bind_router(router)
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose="final route-wide ledger")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("final route-wide ledger must be PM-owned")
    frontier = router._active_frontier(run_root)
    route_id = str(frontier["active_route_id"])
    mutations = read_json_if_exists(run_root / "routes" / route_id / "mutations.json")
    mutation_issues = router._route_mutation_completion_issues(frontier, mutations)
    if mutation_issues:
        raise RouterError("final ledger requires completed route mutation replay: " + "; ".join(mutation_issues[:5]))
    required_paths = [run_root / "evidence" / "evidence_ledger.json", run_root / "generated_resource_ledger.json", run_root / "quality" / "quality_package.json", run_root / "reviews" / "evidence_quality_review.json", run_root / "execution_frontier.json", run_root / "root_acceptance_contract.json", run_root / "child_skill_gate_manifest.json"]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"final ledger requires evidence quality package and review: {', '.join(missing)}")
    if not run_state["flags"].get("evidence_quality_reviewer_passed"):
        raise RouterError("final ledger requires reviewer-passed evidence quality package")
    evidence_ledger = read_json(run_root / "evidence" / "evidence_ledger.json")
    generated_ledger = read_json(run_root / "generated_resource_ledger.json")
    map_doc = material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)
    map_status = material_artifact_map.material_artifact_map_navigation_status(
        project_root,
        run_root,
        map_doc,
    )
    map_ref = map_status.get("source_ref") if map_status.get("navigation_usable") else None
    map_summary = {key: value for key, value in map_status.items() if key != "source_ref"}
    quality_package = read_json(run_root / "quality" / "quality_package.json")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("status") != "frozen":
        raise RouterError("final ledger requires frozen root acceptance contract")
    child_manifest = read_json(run_root / "child_skill_gate_manifest.json")
    route_version = int(frontier.get("route_version") or 0)
    flowguard_coverage_status = router._validated_flowguard_terminal_coverage_status(
        project_root,
        run_root,
        route_version,
        payload.get("flowguard_terminal_coverage_closure"),
    )
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("final ledger requires node completion ledger")
    evidence_unresolved_count = int(evidence_ledger.get("unresolved_count", 0) or 0)
    payload_unresolved_count = int(payload.get("unresolved_count", 0) or 0)
    unresolved_count = max(evidence_unresolved_count, payload_unresolved_count)
    unresolved_resource_count = int(payload.get("unresolved_resource_count", generated_ledger.get("unresolved_resource_count", 0) or 0))
    pending_resource_count = int(generated_ledger.get("pending_resource_count", 0) or 0)
    unresolved_residual_risk_count = int(payload.get("unresolved_residual_risk_count", 0))
    stale_count = int(payload.get("stale_count", evidence_ledger.get("stale_count", 0) or 0))
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status["clean"]:
        first_issue = pm_suggestion_status["issues"][0]["message"] if pm_suggestion_status["issues"] else "unknown issue"
        raise RouterError(f"final ledger requires clean PM suggestion ledger: {first_issue}")
    self_interrogation_status = _require_clean_self_interrogation(project_root, run_root, gate_name="final route-wide ledger")
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, run_state)
    if not closure_reconciliation["clean"]:
        raise RouterError("final ledger requires clean terminal closure reconciliation: " + router._closure_reconciliation_blocker_message(closure_reconciliation))
    if unresolved_count != 0:
        raise RouterError("final ledger requires unresolved_count=0")
    if unresolved_resource_count != 0:
        raise RouterError("final ledger requires unresolved_resource_count=0")
    if pending_resource_count != 0:
        raise RouterError("final ledger requires generated resources to have terminal dispositions")
    if unresolved_residual_risk_count != 0:
        raise RouterError("final ledger requires unresolved_residual_risk_count=0")
    if stale_count != 0:
        raise RouterError("final ledger cannot include stale current evidence")
    if quality_package.get("quality_checks", {}).get("completion_report_only_allowed") is not False:
        raise RouterError("final ledger forbids completion report-only closure")
    route_path = router._active_route_path(run_root, frontier)
    route = read_json(route_path)
    root_replay = router._validated_root_replay(payload, router._root_requirement_ids(contract))
    requirement_trace_closure = router._requirement_trace_closure_from_root_replay(contract, root_replay)
    effective_requirement_count = len(requirement_trace_closure)
    resolved_requirement_count = sum((1 for item in requirement_trace_closure if item.get("status") == "resolved"))
    superseded_requirement_count = sum((1 for item in requirement_trace_closure if item.get("status") == "superseded"))
    waived_requirement_count = sum((1 for item in requirement_trace_closure if item.get("status") == "waived"))
    unresolved_requirement_count = sum((1 for item in requirement_trace_closure if item.get("status") not in {"resolved", "superseded", "waived"}))
    entries = router._build_source_of_truth_final_entries(project_root, run_root, frontier, route, mutations, contract, root_replay, child_manifest, evidence_ledger, generated_ledger)
    if isinstance(map_ref, dict):
        entries.append({"entry_id": "material_artifact_map:index", "route_version": route_version, "gate_family": "material_artifact_map", "required_approver": "project_manager", "status": "indexed", "source_of_truth_paths": [map_ref["path"]], "evidence_paths": [map_ref["path"]], "body_text_excluded": bool(map_summary.get("body_text_excluded")), "entry_count": int(map_summary.get("entry_count", 0) or 0)})
    entries.extend(router._closure_reconciliation_entries(project_root, closure_reconciliation, route_version=route_version))
    entries.append(router._flowguard_terminal_coverage_ledger_entry(route_version, flowguard_coverage_status))
    bad_entry_statuses = [str(entry.get("entry_id")) for entry in entries if entry.get("status") in {"pending", "pending_review", "blocked", "unresolved", "stale"}]
    if bad_entry_statuses:
        raise RouterError(f"final ledger has unresolved source-of-truth entries: {', '.join(bad_entry_statuses)}")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
    terminal_segments = [{"segment_id": str(entry["entry_id"]), "source_entry_id": str(entry["entry_id"]), "gate_family": entry.get("gate_family"), "requirement_trace_closure_refs": entry.get("covers_requirement_ids") or [], "status": "not_reviewed", "requires_pm_segment_decision": True} for entry in entries]
    gate_decision_ledger_path = run_root / "gate_decisions" / "gate_decision_ledger.json"
    gate_decisions = list(run_state.get("gate_decisions") or [])
    ledger = {"schema_version": "flowpilot.final_route_wide_gate_ledger.v1", "run_id": run_state["run_id"], "pm_owned": True, "status": "clean", "built_from_route": route_id, "built_from_route_version": route_version, "built_at": utc_now(), "source_paths": {"execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"), "active_flow": project_relative(project_root, route_path), "node_completion_ledger": project_relative(project_root, node_completion_ledger_path), "evidence_ledger": project_relative(project_root, run_root / "evidence" / "evidence_ledger.json"), "generated_resource_ledger": project_relative(project_root, run_root / "generated_resource_ledger.json"), "quality_package": project_relative(project_root, run_root / "quality" / "quality_package.json"), "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json") if (run_root / "product_function_architecture.json").exists() else None, "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"), "standard_scenario_pack": project_relative(project_root, run_root / "standard_scenario_pack.json") if (run_root / "standard_scenario_pack.json").exists() else None, "child_skill_gate_manifest": project_relative(project_root, run_root / "child_skill_gate_manifest.json"), "route_mutations": project_relative(project_root, run_root / "routes" / route_id / "mutations.json") if (run_root / "routes" / route_id / "mutations.json").exists() else None, "pm_prior_path_context": project_relative(project_root, router._pm_prior_path_context_path(run_root)), "route_history_index": project_relative(project_root, router._route_history_index_path(run_root)), "gate_decision_ledger": project_relative(project_root, gate_decision_ledger_path) if gate_decision_ledger_path.exists() else None, "pm_suggestion_ledger": project_relative(project_root, _pm_suggestion_ledger_path(run_root)) if pm_suggestion_status["exists"] else None, "self_interrogation_index": project_relative(project_root, _self_interrogation_index_path(run_root)) if self_interrogation_status["exists"] else None, "defect_ledger": closure_reconciliation["defect_ledger"]["path"], "role_binding_memory": closure_reconciliation["role_memory"]["path"], "continuation_quarantine": closure_reconciliation["continuation_quarantine"]["path"]}, "prior_path_context_review": prior_review, "current_route_scanned": True, "effective_nodes_resolved": True, "gate_families": {"child_skill_gates_collected": True, "human_review_gates_collected": True, "parent_backward_replays_collected": True, "product_process_gates_collected": True, "generated_resource_lineage_collected": True, "material_artifact_map_linked": isinstance(map_ref, dict), "final_completion_gates_collected": True, "gate_decisions_collected": True, "pm_suggestions_disposed": True, "self_interrogation_dispositions_collected": True, "terminal_closure_reconciliation_collected": True}, "evidence_integrity": {"generated_resource_lineage_resolved": True, "material_artifact_map_checked_if_present": True, "material_artifact_map_navigation_usable": bool(map_status.get("navigation_usable")) if map_status.get("present") else None, "material_artifact_map_body_text_excluded": map_summary.get("body_text_excluded") if map_status.get("present") else None, "material_artifact_map_blocked_count_zero": int(map_summary.get("blocked_count", 0) or 0) == 0 if map_status.get("present") else None, "material_artifact_map_stale_count_zero": int(map_summary.get("stale_count", 0) or 0) == 0 if map_status.get("present") else None, "material_artifact_map_unresolved_count_zero": int(map_summary.get("unresolved_count", 0) or 0) == 0 if map_status.get("present") else None, "stale_evidence_checked": True, "superseded_nodes_explained": True, "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True)), "residual_risk_triage_done": True, "unresolved_residual_risk_count_zero": True, "blocked_items_have_pm_repair_or_stop_decision": True, "requirement_trace_checked": True, "every_effective_requirement_closure_row_present": True, "requirement_direct_evidence_checked": True, "requirement_waiver_authority_checked": True, "requirement_stale_status_checked": True, "self_interrogation_index_clean": True, "defect_ledger_reconciled": closure_reconciliation["defect_ledger"]["clean"], "role_memory_reconciled": closure_reconciliation["role_memory"]["clean"], "continuation_quarantine_reconciled": closure_reconciliation["continuation_quarantine"]["clean"], "terminal_closure_reconciliation_clean": closure_reconciliation["clean"]}, "counts": {"effective_node_count": len(router._effective_route_nodes(route, mutations)), "effective_requirement_count": effective_requirement_count, "resolved_requirement_count": resolved_requirement_count, "superseded_requirement_count": superseded_requirement_count, "waived_requirement_count": waived_requirement_count, "unresolved_requirement_count": unresolved_requirement_count, "gate_count": len(entries), "stale_count": stale_count, "generated_resource_count": int(generated_ledger.get("resource_count", 0) or 0), "material_artifact_map_entry_count": int(map_summary.get("entry_count", 0) or 0), "material_artifact_map_blocked_count": int(map_summary.get("blocked_count", 0) or 0), "material_artifact_map_stale_count": int(map_summary.get("stale_count", 0) or 0), "material_artifact_map_unresolved_count": int(map_summary.get("unresolved_count", 0) or 0), "pending_resource_count": pending_resource_count, "unresolved_resource_count": unresolved_resource_count, "unresolved_residual_risk_count": unresolved_residual_risk_count, "unresolved_count": unresolved_count, "gate_decision_count": len(gate_decisions), "pm_suggestion_count": pm_suggestion_status["entry_count"], "pm_suggestion_issue_count": pm_suggestion_status["issue_count"], "self_interrogation_record_count": self_interrogation_status["record_count"], "self_interrogation_issue_count": self_interrogation_status["issue_count"], "self_interrogation_unresolved_hard_finding_count": self_interrogation_status["unresolved_hard_finding_count"], "defect_blocker_open_count": closure_reconciliation["defect_ledger"]["blocker_open_count"], "defect_fixed_pending_recheck_count": closure_reconciliation["defect_ledger"]["fixed_pending_recheck_count"], "role_memory_file_count": closure_reconciliation["role_memory"]["file_count"], "stale_role_memory_path_count": len(closure_reconciliation["role_memory"]["stale_role_memory_paths"]), "imported_artifact_authority_count": closure_reconciliation["continuation_quarantine"].get("imported_artifact_authority_count", 0)}, "material_artifact_map_summary": map_summary, "entries": entries, "gate_decisions": gate_decisions, "terminal_closure_reconciliation": closure_reconciliation, "root_contract_replay": root_replay, "requirement_trace_closure": requirement_trace_closure, "frozen_contract_replay": {"status": "replayed", "root_acceptance_contract_path": project_relative(project_root, run_root / "root_acceptance_contract.json"), "standard_scenario_pack_path": project_relative(project_root, run_root / "standard_scenario_pack.json"), "requirement_count": len(root_replay), "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True))}, "terminal_human_backward_replay": {"required": True, "status": "ready_for_reviewer", "review_map_path": project_relative(project_root, terminal_map_path), "report_only_allowed": False}, "completion_allowed": False}
    if isinstance(map_ref, dict):
        ledger["source_paths"]["material_artifact_map"] = map_ref["path"]
    ledger["source_paths"]["flowguard_terminal_coverage_report"] = flowguard_coverage_status["report_path"]
    ledger["source_paths"]["flowguard_terminal_coverage_matrix"] = flowguard_coverage_status["coverage_matrix_path"]
    ledger["gate_families"]["flowguard_coverage_governance_collected"] = True
    ledger["evidence_integrity"]["flowguard_terminal_coverage_report_current"] = True
    ledger["evidence_integrity"]["flowguard_terminal_coverage_model_test_alignment_clean"] = True
    coverage_report = flowguard_coverage_status["report"]
    ledger["counts"]["flowguard_terminal_required_item_count"] = len(coverage_report.get("flowguard_required_items") or [])
    ledger["counts"]["flowguard_terminal_evidence_found_count"] = len(coverage_report.get("flowguard_evidence_found") or [])
    ledger["counts"]["flowguard_terminal_gap_count"] = len(coverage_report.get("model_test_alignment_gaps") or [])
    ledger["counts"]["flowguard_terminal_blocker_count"] = len(coverage_report.get("blockers") or [])
    ledger["flowguard_terminal_coverage_closure"] = dict(flowguard_coverage_status)
    ledger["flowguard_terminal_coverage_closure"].pop("report", None)
    traceability_issues = router._final_ledger_traceability_issues(ledger)
    if traceability_issues:
        raise RouterError("final ledger traceability invalid: " + "; ".join((str(issue["message"]) for issue in traceability_issues[:5])))
    write_json(final_ledger_path, ledger)
    write_json(terminal_map_path, {"schema_version": "flowpilot.terminal_human_backward_replay_map.v1", "run_id": run_state["run_id"], "route_id": route_id, "route_version": route_version, "pm_owned": True, "status": "ready_for_reviewer", "built_from_ledger_path": project_relative(project_root, final_ledger_path), "built_at": utc_now(), "replay_order": ["delivered_product", "root_acceptance", "parent_or_module_nodes", "leaf_nodes", "pm_segment_decisions", "repair_restart_policy"], "segments": terminal_segments, "coverage": {"effective_nodes_total": len(router._effective_route_nodes(route, mutations)), "requirement_trace_closure_total": effective_requirement_count, "segments_total": len(terminal_segments), "segments_reviewed": 0, "effective_nodes_reviewed_by_human": 0, "root_acceptance_reviewed": False, "parent_nodes_reviewed": False, "leaf_nodes_reviewed": False, "every_effective_node_has_pm_segment_decision": False}, "repair_restart_policy": {"default_restart": "restart_from_delivered_product", "latest_repair_invalidates_affected_segments": True, "latest_repair_requires_ledger_rebuild": True, "latest_repair_requires_replay_rerun": True, "latest_repair_requires_pm_reapproval": True}, "completion_gate": {"reviewer_passed": False, "pm_segment_decisions_recorded": False, "repair_restart_policy_recorded": True, "unresolved_repair_findings": 0, "completion_allowed": False}})
    terminal_map = read_json(terminal_map_path)
    terminal_map.setdefault("replay_order", [])
    if "flowguard_coverage_governance" not in terminal_map["replay_order"]:
        terminal_map["replay_order"].append("flowguard_coverage_governance")
    terminal_map.setdefault("coverage", {})["flowguard_coverage_governance_reviewed"] = False
    write_json(terminal_map_path, terminal_map)


__all__ = ("_write_final_route_wide_ledger",)

_LOCAL_NAMES = set(globals())
