"""Route-domain writers for FlowPilot router.

The route module owns route activation and route mutation bodies while the
router facade keeps the historical helper names for compatibility.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType
from typing import Any


def route_payload_from_reviewed_draft(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    draft_path = router._current_route_draft_path(run_root)
    draft = router.read_json(draft_path)
    supplied_route = payload.get("route")
    route_payload = dict(supplied_route) if isinstance(supplied_route, dict) else dict(draft)
    route_payload["schema_version"] = "flowpilot.route.v1"
    route_payload["activated_from_draft_path"] = router.project_relative(project_root, draft_path)
    route_payload["activated_from_draft_hash"] = hashlib.sha256(draft_path.read_bytes()).hexdigest()
    route_payload["reviewed_route_activation_source"] = "flow.draft.json"
    if not route_payload.get("nodes"):
        raise router.RouterError("reviewed route activation requires non-empty reviewed route draft nodes")
    return route_payload, draft_path


def write_route_activation(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    router._require_product_behavior_model_report(project_root, run_root)
    router._require_route_process_pass(project_root, run_root)
    if not run_state["flags"].get("reviewer_route_check_passed"):
        raise router.RouterError("route activation requires reviewer-passed route challenge")
    route_payload, draft_path = route_payload_from_reviewed_draft(router, project_root, run_root, payload)
    route_id = str(payload.get("route_id") or route_payload.get("route_id") or draft_path.parent.name or "route-001")
    route_payload["route_id"] = route_id
    route_version = int(payload.get("route_version") or route_payload.get("route_version") or 1)
    route_payload["route_version"] = route_version
    contract = router.read_json(run_root / "root_acceptance_contract.json")
    route_payload["nodes"] = router._route_nodes_with_requirement_trace(
        route_payload.get("nodes") or [],
        router._root_requirement_ids(contract),
    )
    route_payload.setdefault(
        "requirement_traceability_policy",
        {
            "schema_version": "flowpilot.route_requirement_traceability.v1",
            "source_root_contract": router.project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "source_product_architecture": router.project_relative(project_root, run_root / "product_function_architecture.json"),
            "full_protocol_required_when_flowpilot_invoked": True,
            "light_or_simple_profiles_forbidden": True,
            "every_node_requires_requirement_or_risk_rationale": True,
            "external_spec_material_advisory_until_pm_imported": True,
        },
    )
    route_nodes = router._iter_route_nodes(route_payload)
    first_node = route_nodes[0] if route_nodes else {}
    active_node_id = str(
        payload.get("active_node_id")
        or payload.get("node_id")
        or route_payload.get("active_node_id")
        or first_node.get("node_id")
        or first_node.get("id")
        or "node-001"
    )
    active_node_definition = router._active_node_definition_from_route(route_payload, active_node_id)
    route_root = run_root / "routes" / route_id
    route_payload["active_node_id"] = active_node_id
    route_payload["source"] = "pm_activates_reviewed_route"
    route_payload["updated_at"] = router.utc_now()
    router.write_json(route_root / "flow.json", route_payload)
    frontier = {
        "schema_version": "flowpilot.execution_frontier.v1",
        "run_id": run_state["run_id"],
        "status": "current_node_loop",
        "active_route_id": route_id,
        "active_node_id": active_node_id,
        "active_path": router._route_active_path(route_payload, active_node_id),
        "active_leaf_node_id": active_node_id if router._node_kind(active_node_definition) in {"leaf", "repair"} else None,
        "route_version": route_version,
        "updated_at": router.utc_now(),
        "source": "pm_activates_reviewed_route",
    }
    router.write_json(run_root / "execution_frontier.json", frontier)
    router._write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=route_id,
        route_version=route_version,
        route_payload=route_payload,
        active_node_id=active_node_id,
        source_event="pm_activates_reviewed_route",
    )


def write_route_mutation(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose="route mutation")
    frontier = router.read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(payload.get("route_id") or frontier.get("active_route_id") or "route-001")
    current_active_node_id = str(frontier.get("active_node_id") or "node-001")
    active_node_id = str(payload.get("active_node_id") or payload.get("repair_node_id") or current_active_node_id)
    repair_return_to_node_id = str(
        payload.get("repair_return_to_node_id")
        or payload.get("mainline_return_node_id")
        or payload.get("return_to_node_id")
        or ""
    ).strip()
    repair_of_node_id = str(
        payload.get("repair_of_node_id")
        or payload.get("affected_node_id")
        or payload.get("original_node_id")
        or current_active_node_id
    ).strip()
    continue_after_node_id = str(
        payload.get("continue_after_node_id")
        or payload.get("mainline_continue_node_id")
        or payload.get("replacement_continues_to_node_id")
        or ""
    ).strip()
    route_version = int(payload.get("route_version") or int(frontier.get("route_version") or 1) + 1)
    superseded_nodes = [str(item) for item in (payload.get("superseded_nodes") or [])]
    affected_sibling_nodes = [
        str(item)
        for item in (
            payload.get("affected_sibling_nodes")
            or payload.get("sibling_nodes_to_replace")
            or payload.get("replaced_sibling_nodes")
            or []
        )
    ]
    replay_scope_node_id = str(
        payload.get("replay_scope_node_id")
        or payload.get("ancestor_replay_scope_node_id")
        or payload.get("affected_ancestor_node_id")
        or ""
    ).strip()
    stale_evidence = [str(item) for item in (payload.get("stale_evidence") or [])]
    router._validate_route_mutation_phase_boundary(
        run_root,
        run_state,
        route_id=route_id,
        current_active_node_id=current_active_node_id,
    )
    topology_strategy = str(
        payload.get("topology_strategy")
        or payload.get("mutation_topology")
        or payload.get("mutation_strategy")
        or ""
    ).strip()
    current_node_incapability_reason = str(
        payload.get("why_current_node_cannot_contain_repair")
        or payload.get("current_node_cannot_contain_repair_reason")
        or ""
    ).strip()
    if not topology_strategy:
        if repair_return_to_node_id:
            topology_strategy = "return_to_original"
        elif superseded_nodes:
            topology_strategy = "supersede_original"
        elif affected_sibling_nodes:
            topology_strategy = "sibling_branch_replacement"
        elif continue_after_node_id:
            topology_strategy = "branch_then_continue"
    if topology_strategy not in {"return_to_original", "supersede_original", "branch_then_continue", "sibling_branch_replacement"}:
        raise router.RouterError(
            "route mutation requires topology_strategy=return_to_original, supersede_original, "
            "branch_then_continue, or sibling_branch_replacement"
        )
    if not repair_of_node_id:
        raise router.RouterError("route mutation requires repair_of_node_id")
    if topology_strategy == "return_to_original" and not repair_return_to_node_id:
        raise router.RouterError("return_to_original route mutation requires repair_return_to_node_id")
    if topology_strategy == "supersede_original":
        if not superseded_nodes:
            raise router.RouterError("supersede_original route mutation requires superseded_nodes")
        if repair_return_to_node_id:
            raise router.RouterError("supersede_original route mutation must not force repair_return_to_node_id")
    if topology_strategy == "branch_then_continue" and not continue_after_node_id:
        raise router.RouterError("branch_then_continue route mutation requires continue_after_node_id")
    if topology_strategy == "sibling_branch_replacement":
        if not affected_sibling_nodes:
            raise router.RouterError("sibling_branch_replacement route mutation requires affected_sibling_nodes")
        if not replay_scope_node_id:
            raise router.RouterError("sibling_branch_replacement route mutation requires replay_scope_node_id")
        if repair_return_to_node_id:
            raise router.RouterError("sibling_branch_replacement route mutation must not force repair_return_to_node_id")
        superseded_nodes = sorted({*superseded_nodes, *affected_sibling_nodes})
    route_topology = {
        "topology_strategy": topology_strategy,
        "inserted_node_id": active_node_id,
        "replacement_branch_root_node_id": active_node_id if topology_strategy == "sibling_branch_replacement" else None,
        "repair_of_node_id": repair_of_node_id,
        "repair_return_to_node_id": repair_return_to_node_id or None,
        "superseded_nodes": superseded_nodes,
        "affected_sibling_nodes": affected_sibling_nodes,
        "replay_scope_node_id": replay_scope_node_id or None,
        "continue_after_node_id": continue_after_node_id or None,
        "process_officer_recheck_required": True,
        "route_activation_recheck_required": True,
        "display_current_route_on_node_entry_only": True,
    }
    mutation_record = {
        "schema_version": "flowpilot.route_mutation.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "active_node_id": active_node_id,
        "reason": payload.get("reason") or "reviewer_block",
        "current_node_cannot_contain_repair_reason": current_node_incapability_reason or None,
        "stale_evidence": stale_evidence,
        "superseded_nodes": superseded_nodes,
        "affected_sibling_nodes": affected_sibling_nodes,
        "replay_scope_node_id": replay_scope_node_id or None,
        "prior_path_context_review": prior_review,
        "topology_strategy": topology_strategy,
        "route_topology": route_topology,
        "repair_return_policy": {
            "repair_node_id": active_node_id,
            "repair_of_node_id": repair_of_node_id,
            "repair_return_to_node_id": repair_return_to_node_id or None,
            "superseded_nodes": superseded_nodes,
            "affected_sibling_nodes": affected_sibling_nodes,
            "replay_scope_node_id": replay_scope_node_id or None,
            "continue_after_node_id": continue_after_node_id or None,
            "topology_strategy": topology_strategy,
            "process_officer_recheck_required": True,
            "route_activation_recheck_required": True,
        },
        "repair_restart_policy": {
            "same_scope_replay_rerun_required": True,
            "final_ledger_rebuild_required": True,
            "terminal_replay_restart_default": "restart_from_delivered_product",
        },
        "recorded_at": router.utc_now(),
        "recorded_by": "project_manager",
    }
    mutation_path = run_root / "routes" / route_id / "mutations.json"
    mutations = router.read_json_if_exists(mutation_path) or {"schema_version": "flowpilot.route_mutations.v1", "items": []}
    mutations.setdefault("items", []).append(mutation_record)
    mutations["updated_at"] = router.utc_now()
    router.write_json(mutation_path, mutations)
    route_path = run_root / "routes" / route_id / "flow.json"
    route = router.read_json_if_exists(route_path)
    repaired_node = {}
    try:
        repaired_node = router._active_node_definition_from_route(route, repair_of_node_id) if route else {}
    except router.RouterError:
        repaired_node = {}
    route.setdefault("schema_version", "flowpilot.route.v1")
    route.setdefault("route_id", route_id)
    draft_route = dict(route)
    draft_route["schema_version"] = "flowpilot.route_draft.v1"
    draft_route["route_id"] = route_id
    draft_route["route_version"] = route_version
    draft_route["source"] = "pm_mutates_route_after_review_block"
    draft_route["candidate_activation_required"] = True
    draft_route["candidate_activation_status"] = "pending_route_recheck"
    draft_route["active_node_id"] = active_node_id
    draft_route["route_topology"] = route_topology
    draft_route["route_mutation_source_path"] = router.project_relative(project_root, mutation_path)
    draft_route["updated_at"] = router.utc_now()
    nodes = [
        dict(node)
        for node in draft_route.get("nodes", [])
        if isinstance(node, dict)
    ]
    for node in nodes:
        if isinstance(node, dict) and str(node.get("node_id") or node.get("id")) in superseded_nodes:
            node["status"] = "superseded"
            node["superseded_by"] = active_node_id
            node["superseded_at"] = router.utc_now()
    if not any(isinstance(node, dict) and str(node.get("node_id") or node.get("id")) == active_node_id for node in nodes):
        nodes.append(
            {
                "node_id": active_node_id,
                "node_kind": "repair",
                "status": "pending_activation",
                "title": str(payload.get("repair_node_title") or "Repair node"),
                "parent_node_id": payload.get("parent_node_id") or repaired_node.get("parent_node_id"),
                "depth": int(payload.get("repair_node_depth") or repaired_node.get("depth") or repaired_node.get("_computed_depth") or 1),
                "child_node_ids": [],
                "user_visible": bool(payload.get("user_visible", True)),
                "leaf_readiness_gate": {
                    "status": "pass",
                    "repair_node": True,
                    "worker_executable_without_replanning": True,
                    "reviewed_route_reactivation_required_before_dispatch": True,
                },
                "created_by_mutation": True,
                "mutation_reason": mutation_record["reason"],
                "topology_strategy": topology_strategy,
                "repair_of_node_id": repair_of_node_id,
                "repair_return_to_node_id": repair_return_to_node_id or None,
                "supersedes_node_ids": superseded_nodes,
                "affected_sibling_nodes": affected_sibling_nodes,
                "replacement_branch_root_node_id": active_node_id if topology_strategy == "sibling_branch_replacement" else None,
                "replay_scope_node_id": replay_scope_node_id or None,
                "continue_after_node_id": continue_after_node_id or None,
                "route_topology": route_topology,
            }
        )
    draft_route["nodes"] = nodes
    router.write_json(run_root / "routes" / route_id / "flow.draft.json", draft_route)
    stale_ledger_path = run_root / "evidence" / "stale_evidence_ledger.json"
    stale_ledger = router.read_json_if_exists(stale_ledger_path) or {"schema_version": "flowpilot.stale_evidence_ledger.v1", "items": []}
    for evidence_id in stale_evidence:
        stale_ledger.setdefault("items", []).append(
            {
                "evidence_id": evidence_id,
                "status": "stale",
                "reason": mutation_record["reason"],
                "route_version": route_version,
                "recorded_at": router.utc_now(),
            }
        )
    stale_ledger["updated_at"] = router.utc_now()
    router.write_json(stale_ledger_path, stale_ledger)
    router._supersede_active_current_node_packet_for_route_mutation(
        project_root,
        run_root,
        frontier=frontier,
        mutation_record=mutation_record,
    )
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "route_mutation_pending_recheck",
            "active_route_id": route_id,
            "active_node_id": current_active_node_id,
            "latest_mutation_path": router.project_relative(project_root, mutation_path),
            "pending_route_mutation": {
                "candidate_node_id": active_node_id,
                "candidate_route_version": route_version,
                "candidate_route_draft_path": router.project_relative(project_root, run_root / "routes" / route_id / "flow.draft.json"),
                "topology_strategy": topology_strategy,
                "affected_sibling_nodes": affected_sibling_nodes,
                "replay_scope_node_id": replay_scope_node_id or None,
                "display_current_route_on_node_entry_only": True,
            },
            "updated_at": router.utc_now(),
            "source": "pm_mutates_route_after_review_block",
        }
    )
    router.write_json(run_root / "execution_frontier.json", frontier)
    router._reset_route_hard_gate_approvals_for_recheck(run_state)
    run_state.setdefault("flags", {})["pm_route_skeleton_card_delivered"] = True
    run_state.setdefault("flags", {})["route_draft_written_by_pm"] = True
    router._reset_flags(run_state, router.CURRENT_NODE_CYCLE_FLAGS + router.ROUTE_COMPLETION_FLAGS)
