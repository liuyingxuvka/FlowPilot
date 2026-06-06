"""Source-of-truth entry builders for the FlowPilot final ledger."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

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


def _root_requirement_ids(router: ModuleType, contract: dict[str, Any]) -> list[str]:
    _bind_router(router)
    ids = []
    for item in contract.get("root_requirements") or []:
        if isinstance(item, dict) and item.get("requirement_id"):
            ids.append(str(item["requirement_id"]))
    return ids


def _string_list(router: ModuleType, value: Any) -> list[str]:
    _bind_router(router)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _route_nodes_with_requirement_trace(
    router: ModuleType,
    nodes: Any,
    root_requirement_ids: list[str],
) -> list[dict[str, Any]]:
    _bind_router(router)
    traced_nodes: list[dict[str, Any]] = []
    if not isinstance(nodes, list):
        return traced_nodes
    for index, item in enumerate(nodes, start=1):
        if not isinstance(item, dict):
            continue
        node = dict(item)
        node_id = str(node.get("node_id") or node.get("id") or f"node-{index:03d}")
        node.setdefault("node_id", node_id)
        node.setdefault("covers_requirement_ids", root_requirement_ids)
        node.setdefault("covers_scenario_ids", [])
        node.setdefault("source_product_capability_ids", [])
        node.setdefault(
            "why_this_node_exists",
            f"Node {node_id} owns mapped FlowPilot requirements or route proof obligations.",
        )
        node.setdefault(
            "why_not_merged",
            "PM preserves this node while it owns distinct evidence, role authority, failure isolation, recovery, or user-visible milestone value.",
        )
        node.setdefault(
            "why_not_split",
            "PM splits this node only when a child boundary adds distinct proof, role authority, recovery, or user-visible milestone value.",
        )
        traced_nodes.append(node)
    return traced_nodes


def _requirement_trace_closure_from_root_replay(
    router: ModuleType,
    contract: dict[str, Any],
    root_replay: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _bind_router(router)
    requirements_by_id = {
        str(item.get("requirement_id")): item
        for item in contract.get("root_requirements") or []
        if isinstance(item, dict) and item.get("requirement_id")
    }
    closure: list[dict[str, Any]] = []
    for replay in root_replay:
        requirement_id = str(replay.get("requirement_id") or "")
        requirement = requirements_by_id.get(requirement_id, {})
        closure.append(
            {
                "requirement_id": requirement_id,
                "source_requirement_ids": router._string_list(requirement.get("source_requirement_ids"))
                or [requirement_id],
                "change_status": str(requirement.get("change_status") or "UNCHANGED"),
                "status": "resolved",
                "owner_node_ids": router._string_list(replay.get("owner_node_ids")),
                "covering_entry_ids": [f"root_contract:{requirement_id}"],
                "evidence_paths": replay.get("evidence_paths") or [],
                "direct_evidence_required": True,
                "direct_evidence_checked": True,
                "standard_scenario_ids": replay.get("standard_scenarios")
                or replay.get("standard_scenario_ids")
                or [],
                "stale_evidence_refs": [],
                "superseded_by_requirement_ids": router._string_list(
                    requirement.get("superseded_by_requirement_ids")
                ),
                "waiver_authority": None,
                "unresolved_reason": None,
            }
        )
    return closure


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
    _bind_router(router)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    entries: list[dict[str, Any]] = []

    for replay in root_replay:
        entries.append(
            {
                "entry_id": f"root_contract:{replay['requirement_id']}",
                "route_version": route_version,
                "gate_family": "root_acceptance",
                "covers_requirement_ids": [str(replay["requirement_id"])],
                "covers_scenario_ids": replay.get("standard_scenarios")
                or replay.get("standard_scenario_ids")
                or [],
                "required_approver": "human_like_reviewer",
                "status": "approved",
                "source_of_truth_paths": replay.get("evidence_paths") or [],
                "evidence_paths": replay.get("evidence_paths") or [],
            }
        )

    for node in router._effective_route_nodes(route, mutations):
        node_id = str(node["node_id"])
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        source_paths = [
            project_relative(project_root, path)
            for path in (
                node_root / "node_acceptance_plan.json",
                node_root / "reviews" / "node_acceptance_plan_review.json",
                node_root / "node_completion_ledger.json",
                node_root / "parent_backward_replay.json",
                node_root / "pm_parent_segment_decision.json",
            )
            if path.exists()
        ]
        entries.append(
            {
                "entry_id": f"{route_id}:{node_id}",
                "route_version": route_version,
                "node_id": node_id,
                "gate_family": "route_node",
                "covers_requirement_ids": router._string_list(node.get("covers_requirement_ids")),
                "covers_scenario_ids": router._string_list(node.get("covers_scenario_ids")),
                "required_approver": "project_manager",
                "status": "approved"
                if node_id in (frontier.get("completed_nodes") or [])
                or node_id == frontier.get("active_node_id")
                else "pending_review",
                "source_of_truth_paths": source_paths,
                "evidence_paths": list(source_paths),
            }
        )

    for item in mutations.get("items") or []:
        if not isinstance(item, dict):
            continue
        for node_id in router._route_mutation_superseded_nodes(item):
            entries.append(
                {
                    "entry_id": f"superseded:{node_id}",
                    "route_version": item.get("route_version", route_version),
                    "node_id": str(node_id),
                    "gate_family": "superseded_node",
                    "required_approver": "project_manager",
                    "status": "superseded_explained",
                    "source_of_truth_paths": [
                        project_relative(project_root, run_root / "routes" / route_id / "mutations.json")
                    ],
                    "evidence_paths": [
                        project_relative(project_root, run_root / "routes" / route_id / "mutations.json")
                    ],
                }
            )

    for skill in child_manifest.get("selected_skills") or []:
        if not isinstance(skill, dict):
            continue
        skill_name = str(skill.get("skill_name") or skill.get("name") or "child_skill")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                continue
            entries.append(
                {
                    "entry_id": f"child_skill:{skill_name}:{gate.get('gate_id') or len(entries)}",
                    "route_version": route_version,
                    "gate_family": "child_skill_gate",
                    "required_approver": gate.get("required_approver") or "project_manager",
                    "status": "approved",
                    "source_of_truth_paths": [
                        project_relative(project_root, run_root / "child_skill_gate_manifest.json")
                    ],
                    "evidence_paths": [
                        project_relative(project_root, run_root / "child_skill_gate_manifest.json")
                    ],
                }
            )

    for item in evidence_ledger.get("items") or []:
        if isinstance(item, dict) and item.get("evidence_id"):
            entries.append(
                {
                    "entry_id": f"evidence:{item['evidence_id']}",
                    "route_version": route_version,
                    "gate_family": "evidence_integrity",
                    "required_approver": "human_like_reviewer",
                    "status": item.get("status") or "current",
                    "source_of_truth_paths": [item.get("path")] if item.get("path") else [],
                    "evidence_paths": [item.get("path")] if item.get("path") else [],
                }
            )

    for resource in generated_ledger.get("resources") or []:
        if isinstance(resource, dict) and (resource.get("resource_id") or resource.get("path")):
            entries.append(
                {
                    "entry_id": f"generated_resource:{resource.get('resource_id') or resource.get('path')}",
                    "route_version": route_version,
                    "gate_family": "generated_resource_lineage",
                    "required_approver": "project_manager",
                    "status": resource.get("disposition") or "resolved",
                    "source_of_truth_paths": [resource.get("path")] if resource.get("path") else [],
                    "evidence_paths": [resource.get("path")] if resource.get("path") else [],
                }
            )

    if not entries:
        raise RouterError("final ledger source-of-truth scan produced no entries")
    return entries


__all__ = (
    "_root_requirement_ids",
    "_string_list",
    "_route_nodes_with_requirement_trace",
    "_requirement_trace_closure_from_root_replay",
    "_build_source_of_truth_final_entries",
)

_LOCAL_NAMES = set(globals())
