"""Internal router owner helpers extracted from flowpilot_router.

The public compatibility names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so legacy private helper lookups remain
stable while the implementation body lives outside the facade.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_route_artifacts"

def _write_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str = "pm_writes_node_acceptance_plan",
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="node acceptance plan")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("node acceptance plan must be PM-owned")
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier["active_node_id"])
    active_route_id = str(frontier["active_route_id"])
    if payload.get("node_id") and str(payload["node_id"]) != active_node_id:
        raise RouterError("node acceptance plan node_id must match active frontier")
    route_version = int(frontier.get("route_version") or 0)
    if payload.get("route_version") is not None and int(payload["route_version"]) != route_version:
        raise RouterError("node acceptance plan route_version must match active frontier")
    node_requirements = payload.get("node_requirements")
    if not isinstance(node_requirements, list) or not node_requirements:
        raise RouterError("node acceptance plan requires a non-empty node_requirements list")
    experiment_plan = payload.get("experiment_plan")
    if not isinstance(experiment_plan, list):
        raise RouterError("node acceptance plan requires experiment_plan list")
    high_standard = payload.get("high_standard_recheck")
    if not isinstance(high_standard, dict):
        raise RouterError("node acceptance plan requires high_standard_recheck")
    required_high_standard_fields = {
        "ideal_outcome",
        "unacceptable_outcomes",
        "higher_standard_opportunities",
        "semantic_downgrade_risks",
        "decision",
        "why_current_plan_meets_highest_reasonable_standard",
    }
    def _blank(value: Any) -> bool:
        return value is None or value == "" or value == []

    missing_high_standard = [
        name
        for name in sorted(required_high_standard_fields)
        if name not in high_standard or _blank(high_standard.get(name))
    ]
    if missing_high_standard:
        raise RouterError(f"node high-standard recheck missing fields: {', '.join(missing_high_standard)}")
    if str(high_standard.get("decision")) != "proceed":
        raise RouterError("node acceptance can proceed only after high_standard_recheck.decision=proceed")
    if high_standard.get("controller_can_downgrade_standard") is True:
        raise RouterError("Controller cannot downgrade node standards")
    node = _active_node_definition(run_root, frontier)
    contract = read_json_if_exists(run_root / "root_acceptance_contract.json")
    root_requirement_ids = _root_requirement_ids(contract) if isinstance(contract, dict) else []
    route_node_requirement_ids = _string_list(node.get("covers_requirement_ids")) or root_requirement_ids
    route_node_scenario_ids = _string_list(node.get("covers_scenario_ids"))
    route_node_capability_ids = _string_list(node.get("source_product_capability_ids"))
    node_requirement_ids = [
        str(item.get("requirement_id"))
        for item in node_requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]
    traced_node_requirements: list[dict[str, Any]] = []
    for item in node_requirements:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("source_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_scenario_ids", route_node_scenario_ids)
        traced.setdefault("source_product_capability_ids", route_node_capability_ids)
        traced.setdefault("change_status", "UNCHANGED")
        traced.setdefault("supersedes_requirement_ids", [])
        traced_node_requirements.append(traced)
    traced_experiment_plan: list[dict[str, Any]] = []
    for item in experiment_plan:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("covers_requirements", node_requirement_ids or route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_product_requirement_ids", _string_list(traced.get("covers_product_requirement_ids")))
        traced_experiment_plan.append(traced)
    node_requirements = traced_node_requirements
    experiment_plan = traced_experiment_plan
    child_ids = _node_child_ids(node)
    payload_leaf_gate = payload.get("leaf_readiness_gate") if isinstance(payload.get("leaf_readiness_gate"), dict) else None
    if payload_leaf_gate is not None:
        leaf_readiness_gate = dict(payload_leaf_gate)
    elif child_ids:
        leaf_readiness_gate = {
            "status": "not_applicable_parent",
            "reason": "Parent/module nodes are composition boundaries and cannot receive worker packets directly.",
        }
    else:
        leaf_readiness_gate = {
            "status": "pass",
            "legacy_inferred_from_reviewed_node_plan": True,
            "single_outcome": True,
            "worker_executable_without_replanning": True,
            "proof_defined": bool(experiment_plan),
            "dependency_boundary_defined": True,
            "failure_isolation_defined": True,
        }
    plan = {
        "schema_version": "flowpilot.node_acceptance_plan.v1",
        "run_id": run_state["run_id"],
        "route_id": active_route_id,
        "route_version": route_version,
        "node_id": active_node_id,
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "route_flow": project_relative(project_root, _active_route_path(run_root, frontier)),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "requirement_traceability": {
            "schema_version": "flowpilot.node_requirement_traceability.v1",
            "source_route_node_id": active_node_id,
            "source_route_node_covers_requirement_ids": route_node_requirement_ids,
            "source_route_node_covers_scenario_ids": route_node_scenario_ids,
            "source_product_capability_ids": route_node_capability_ids,
            "full_protocol_required_when_flowpilot_invoked": True,
            "all_covered_requirements_must_close_or_be_triaged": True,
            "closure_by_report_only_forbidden": True,
            "external_spec_material_advisory_until_pm_imported": True,
            "legacy_trace_defaults_inferred_by_router": "requirement_traceability" not in payload,
        },
        "prior_path_context_review": prior_review,
        "node_structure": {
            "node_kind": _node_kind(node),
            "has_children": bool(child_ids),
            "child_node_ids": child_ids,
            "parent_backward_replay_required": bool(child_ids),
            "semantic_importance_used_to_trigger_review": False,
        },
        "leaf_readiness_gate": leaf_readiness_gate,
        "node_requirements": node_requirements,
        "experiment_plan": experiment_plan,
        "high_standard_recheck": {
            "ideal_outcome": high_standard.get("ideal_outcome"),
            "unacceptable_outcomes": high_standard.get("unacceptable_outcomes"),
            "higher_standard_opportunities": high_standard.get("higher_standard_opportunities"),
            "semantic_downgrade_risks": high_standard.get("semantic_downgrade_risks"),
            "decision": "proceed",
            "why_current_plan_meets_highest_reasonable_standard": high_standard.get("why_current_plan_meets_highest_reasonable_standard"),
            "controller_can_downgrade_standard": False,
        },
        "advance_gate": {
            "required_before_chunk_execution": True,
            "required_before_node_checkpoint": True,
            "reviewer_or_officer_direct_check_required": True,
            "all_covered_requirements_closed_or_triaged": False,
            "unresolved_requirement_ids": route_node_requirement_ids,
        },
        "written_by_role": "project_manager",
        "source_event": source_event,
    }
    for optional_field in [
        "controller_summary_used_as_evidence",
        "identity",
        "node_title",
        "node_objective",
        "product_behavior_model_segment",
        "proof_obligations",
        "recheck_criteria",
        "repair_context",
        "fixtures_and_evidence_paths",
        "forbidden_low_standard_outcomes",
        "minimum_sufficient_complexity_review",
        "inherited_gate_obligations",
        "skill_standard_projection",
        "active_child_skill_bindings",
        "work_packet_projection",
        "result_matrix_requirements",
        "inherited_root_requirements",
    ]:
        if optional_field in payload:
            plan[optional_field] = payload.get(optional_field)
    issues = _node_acceptance_traceability_issues(plan)
    if issues:
        raise RouterError("node acceptance plan traceability invalid: " + "; ".join(str(issue["message"]) for issue in issues[:5]))
    write_json(_active_node_acceptance_plan_path(run_root, frontier), plan)
    _update_display_plan_current_node(
        project_root,
        run_root,
        run_state,
        node_id=str(frontier["active_node_id"]),
        node_title=str(node.get("title") or node.get("label") or frontier["active_node_id"]),
        checklist=[
            {
                "id": str(item.get("requirement_id") or f"requirement-{index:03d}"),
                "label": str(item.get("acceptance_statement") or item.get("label") or item.get("requirement_id") or f"Requirement {index}"),
                "status": "pending",
            }
            for index, item in enumerate(node_requirements, start=1)
            if isinstance(item, dict)
        ],
        source_event=source_event,
    )

def _write_pm_revised_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    if not run_state["flags"].get("node_acceptance_plan_review_blocked"):
        raise RouterError("same-node node acceptance-plan repair requires active node_acceptance_plan_review_blocked flag")
    frontier = _active_frontier(run_root)
    node_root = _active_node_root(run_root, frontier)
    block_path = node_root / "reviews" / "node_acceptance_plan_block.json"
    if not block_path.exists():
        raise RouterError("same-node node acceptance-plan repair requires reviewer block report")
    _write_node_acceptance_plan(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_revises_node_acceptance_plan",
    )
    revised_plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    repair_record_path = node_root / "repairs" / "node_acceptance_plan_revision.json"
    write_json(
        repair_record_path,
        {
            "schema_version": "flowpilot.node_acceptance_plan_revision.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "repair_scope": "same_node_plan_revision",
            "source_block_path": project_relative(project_root, block_path),
            "revised_plan_path": project_relative(project_root, revised_plan_path),
            "stale_blocked_plan_is_context_only": True,
            "reviewer_recheck_required": True,
            "recorded_at": utc_now(),
            "recorded_by": "project_manager",
        },
    )
    run_state["flags"]["node_acceptance_plan_review_blocked"] = False
    run_state["flags"]["node_acceptance_plan_reviewer_passed"] = False
    run_state["flags"]["reviewer_node_acceptance_plan_card_delivered"] = False

def _write_parent_backward_targets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    frontier = _active_frontier(run_root)
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    active_node_id = str(frontier["active_node_id"])
    node_root = _active_node_root(run_root, frontier)
    targets = [
        {
            "parent_node_id": active_node_id,
            "child_node_ids": child_ids,
            "parent_backward_replay_path": project_relative(project_root, node_root / "parent_backward_replay.json"),
            "status": "not_started" if child_ids else "not_required",
            "pm_segment_decision": "not_reviewed" if child_ids else "not_required",
            "latest_repair_requires_rerun": False,
            "latest_replay_route_version": route_version,
        }
    ] if child_ids else []
    record = {
        "schema_version": "flowpilot.parent_backward_targets.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "pm_owned": True,
        "status": "current",
        "built_from_flow_path": project_relative(project_root, _active_route_path(run_root, frontier)),
        "built_at": utc_now(),
        "trigger_rule": {
            "structural_trigger": "any_effective_route_node_with_children",
            "semantic_importance_classification_required": False,
            "leaf_nodes_exempt_from_parent_backward_replay": True,
        },
        "targets": targets,
        "coverage": {
            "parent_targets_total": len(targets),
            "parent_targets_with_replay_passed": 0,
            "parent_targets_with_pm_decision": 0,
            "all_required_parent_replays_passed": not child_ids,
        },
        "written_by_role": "project_manager",
    }
    write_json(run_root / "routes" / route_id / "parent_backward_targets.json", record)

def _write_parent_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    frontier = _active_frontier(run_root)
    if not _active_node_has_children(run_root, frontier):
        raise RouterError("parent backward replay is required only for active nodes with children")
    targets_path = run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if not targets_path.exists():
        raise RouterError("parent backward replay requires parent_backward_targets.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("parent backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("parent backward replay must explicitly pass")
    active_node_id = str(frontier["active_node_id"])
    replay = {
        "schema_version": "flowpilot.parent_backward_replay.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": active_node_id,
        "pm_owned": True,
        "status": "passed",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "parent_backward_targets": project_relative(project_root, targets_path),
            "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
        },
        "reviewer_report": {
            "reviewer_role": "human_like_reviewer",
            "neutral_observation_written": bool(payload.get("neutral_observation_written", True)),
            "independent_probe_done": bool(payload.get("independent_probe_done", True)),
            "child_evidence_replayed": bool(payload.get("child_evidence_replayed", True)),
            "children_compose_into_parent_goal": True,
            "blocking_findings": [],
            "approval_valid": True,
        },
        "closure_gate": {
            "required_before_parent_checkpoint": True,
            "reviewer_passed": True,
            "unresolved_blocking_findings": 0,
            "parent_closure_allowed": False,
        },
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "parent_backward_replay.json", replay)

def _write_parent_segment_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("parent segment decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="parent segment decision")
    frontier = _active_frontier(run_root)
    replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
    if not replay_path.exists():
        raise RouterError("parent segment decision requires parent_backward_replay.json")
    decision = str(payload.get("decision") or "continue")
    if decision not in PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported parent segment decision: {decision}")
    record = {
        "schema_version": "flowpilot.parent_segment_decision.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": str(frontier["active_node_id"]),
        "decision_owner": "project_manager",
        "decision": decision,
        "route_mutation_required": decision != "continue",
        "same_parent_replay_rerun_required": decision != "continue",
        "prior_path_context_review": prior_review,
        "source_paths": {
            "parent_backward_replay": project_relative(project_root, replay_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "pm_parent_segment_decision.json", record)
    if decision != "continue":
        repair_node_id = str(payload.get("repair_node_id") or f"{frontier['active_node_id']}-repair-{int(frontier.get('route_version') or 1) + 1}")
        _write_route_mutation(
            project_root,
            run_root,
            run_state,
            {
                "route_id": frontier["active_route_id"],
                "repair_node_id": repair_node_id,
                "reason": f"parent_segment_decision:{decision}",
                "stale_evidence": [project_relative(project_root, replay_path)],
                "superseded_nodes": payload.get("superseded_nodes") or [],
                "repair_return_to_node_id": payload.get("repair_return_to_node_id") or payload.get("return_to_node_id"),
                "prior_path_context_review": payload.get("prior_path_context_review"),
            },
        )
    return decision

def _write_pm_research_absorption(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_pm_research_absorption(_bound_router(), project_root, run_root, run_state)

def _validate_current_node_packet_envelope(project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_current_node_packet_envelope(_bound_router(), project_root, run_root, run_state, envelope, envelope_path, frontier, plan)

def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_packet_event(_bound_router(), project_root, run_root, run_state, payload)

def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_result_event(_bound_router(), project_root, run_state, payload)

def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_reviewer_pass(_bound_router(), project_root, run_state, payload)

def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_route.route_payload_from_reviewed_draft(
        _bound_router(),
        project_root,
        run_root,
        payload,
    )

def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_activation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_mutation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

__all__ = (
    '_write_node_acceptance_plan',
    '_write_pm_revised_node_acceptance_plan',
    '_write_parent_backward_targets',
    '_write_parent_backward_replay',
    '_write_parent_segment_decision',
    '_write_pm_research_absorption',
    '_validate_current_node_packet_envelope',
    '_validate_current_node_packet_event',
    '_validate_current_node_result_event',
    '_validate_current_node_reviewer_pass',
    '_route_payload_from_reviewed_draft',
    '_write_route_activation',
    '_write_route_mutation',
)

_LOCAL_NAMES = set(globals())
