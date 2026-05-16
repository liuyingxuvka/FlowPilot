"""Generate FlowPilot's realtime user-facing route sign.

The route sign is the simplified Mermaid diagram shown to users in chat and in
Cockpit UI. It is not a raw FlowGuard state graph and it is not the execution
source of truth; route and frontier JSON remain authoritative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


DISPLAY_TRIGGERS = {
    "startup",
    "major_node_entry",
    "parent_node_entry",
    "leaf_node_entry",
    "pm_work_brief",
    "key_node_change",
    "route_mutation",
    "review_failure",
    "validation_failure",
    "completion",
    "user_request",
}
RETURN_TRIGGERS = {"route_mutation", "review_failure", "validation_failure"}
ALLOWED_STAGES = {
    "intake",
    "product",
    "modeling",
    "route",
    "execution",
    "verification",
    "completion",
    "repair",
}
FALLBACK_STAGES = (
    ("intake", "Start & Scope"),
    ("product", "Product Map"),
    ("modeling", "FlowGuard Model"),
    ("route", "Route Plan"),
    ("execution", "Build / Execute"),
    ("verification", "Review & QA"),
    ("completion", "Completion"),
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _normalize(text: Any) -> str:
    return str(text or "").lower().replace("_", "-")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _stage_from_text(text: str, *, completed: bool, route_mutation_pending: bool) -> str:
    if route_mutation_pending or any(token in text for token in ("route-mutation", "repair", "rework")):
        return "repair"
    if completed:
        return "completion"
    if any(
        token in text
        for token in (
            "final-verification",
            "verification",
            "verify",
            "validate",
            "validation",
            "qa",
            "review",
            "checkpoint",
            "test",
        )
    ):
        return "verification"
    if any(token in text for token in ("implement", "execution", "child-skill", "concept", "asset", "build")):
        return "execution"
    if any(token in text for token in ("flowguard", "model", "strict-gate")):
        return "modeling"
    if any(token in text for token in ("route", "frontier", "node", "architecture")):
        return "route"
    if any(token in text for token in ("product", "function", "contract", "acceptance")):
        return "product"
    return "intake"


def _route_mutation_pending(frontier: dict[str, Any]) -> bool:
    route_mutation = frontier.get("route_mutation") or {}
    failed_review = route_mutation.get("failed_review") or {}
    return bool(route_mutation.get("pending") or failed_review.get("blocking"))


def _snapshot_route(snapshot: dict[str, Any]) -> dict[str, Any]:
    route = snapshot.get("route") if isinstance(snapshot.get("route"), dict) else {}
    if not route:
        return {}
    nodes = _all_route_nodes(route)
    return {
        "schema_version": "flowpilot.route.snapshot_projection.v1",
        "route_id": route.get("route_id"),
        "route_version": route.get("route_version"),
        "active_node_id": route.get("active_node_id"),
        "display_depth": _route_display_depth(route),
        "status": "snapshot",
        "nodes": nodes,
    }


def _node_id(node: dict[str, Any]) -> str:
    return str(node.get("id") or node.get("node_id") or "")


def _raw_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("nodes", "route_nodes"):
        nodes = route.get(key)
        if isinstance(nodes, list):
            return [node for node in nodes if isinstance(node, dict)]
    for key in ("full_route_tree", "route_tree"):
        tree = route.get(key)
        if isinstance(tree, dict):
            nodes = tree.get("nodes")
            if isinstance(nodes, list):
                return [node for node in nodes if isinstance(node, dict)]
    return []


def _inline_child_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    for key in ("children", "child_nodes", "subnodes"):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            children.extend(child for child in raw_children if isinstance(child, dict))
    return children


def _node_child_ids(node: dict[str, Any]) -> list[str]:
    child_ids: list[str] = []
    for key in ("child_node_ids", "children_ids", "subnode_ids"):
        raw_ids = node.get(key)
        if isinstance(raw_ids, list):
            child_ids.extend(str(item) for item in raw_ids if item)
    for child in _inline_child_nodes(node):
        child_id = _node_id(child)
        if child_id:
            child_ids.append(child_id)
    return list(dict.fromkeys(child_ids))


def _flatten_route_nodes(
    raw_nodes: list[dict[str, Any]],
    *,
    parent_node_id: str | None = None,
    depth: int = 1,
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for node in raw_nodes:
        node_id = _node_id(node)
        if not node_id:
            continue
        children = _inline_child_nodes(node)
        child_ids = _node_child_ids(node)
        projected = dict(node)
        projected_depth = depth
        explicit_kind = str(node.get("node_kind") or node.get("kind") or "").strip().lower()
        if explicit_kind == "root" and "depth" not in node and "route_depth" not in node:
            projected_depth = 0
        projected.setdefault("parent_node_id", parent_node_id)
        projected.setdefault("depth", projected_depth)
        if child_ids:
            projected["child_node_ids"] = child_ids
        flattened.append(projected)
        flattened.extend(_flatten_route_nodes(children, parent_node_id=node_id, depth=projected_depth + 1))
    return flattened


def _all_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return _flatten_route_nodes(_raw_route_nodes(route))


def _route_node_depth(node: dict[str, Any]) -> int:
    raw = node["depth"] if "depth" in node else node.get("route_depth")
    try:
        depth = int(raw)
    except (TypeError, ValueError):
        depth = 1
    return max(0, depth)


def _route_display_depth(route: dict[str, Any]) -> int:
    display_plan = route.get("display_plan") if isinstance(route.get("display_plan"), dict) else {}
    raw = route.get("display_depth") or display_plan.get("display_depth") or 1
    try:
        depth = int(raw)
    except (TypeError, ValueError):
        depth = 1
    return max(1, depth)


def _node_kind(node: dict[str, Any]) -> str:
    explicit = str(node.get("node_kind") or node.get("kind") or "").strip().lower()
    if explicit:
        return explicit
    topology = _node_topology(node)
    if topology.get("topology_strategy"):
        return "repair"
    if _node_child_ids(node):
        return "parent"
    return "leaf"


def _is_route_root_node(node: dict[str, Any]) -> bool:
    explicit = str(node.get("node_kind") or node.get("kind") or "").strip().lower()
    if explicit == "root":
        return True
    raw_depth = node["depth"] if "depth" in node else node.get("route_depth")
    try:
        return int(raw_depth) == 0
    except (TypeError, ValueError):
        return False


def _display_depth_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    display_depth = _route_display_depth(route)
    visible: list[dict[str, Any]] = []
    for node in _all_route_nodes(route):
        if _is_route_root_node(node):
            continue
        if _route_node_depth(node) <= display_depth or _truthy(node.get("user_visible")):
            visible.append(node)
    return visible


def _route_active_path(
    frontier: dict[str, Any],
    route: dict[str, Any],
    active_node: str | None,
) -> list[dict[str, Any]]:
    raw_path = frontier.get("active_path")
    if isinstance(raw_path, list) and raw_path:
        path: list[dict[str, Any]] = []
        nodes_by_id = {_node_id(node): node for node in _all_route_nodes(route)}
        for item in raw_path:
            if isinstance(item, dict):
                node_id = str(item.get("node_id") or item.get("id") or "")
                node = nodes_by_id.get(node_id, {})
                node_kind = str(item.get("node_kind") or (_node_kind(node) if node else "") or "")
                path_item = {
                    "node_id": node_id,
                    "label": str(item.get("label") or item.get("title") or _node_label(node) or node_id),
                    "depth": int(item.get("depth") or _route_node_depth(node) or 1),
                    "node_kind": node_kind,
                }
                if not _is_route_root_node({**node, **path_item}):
                    path.append(path_item)
            elif item:
                node_id = str(item)
                node = nodes_by_id.get(node_id, {})
                path_item = {
                    "node_id": node_id,
                    "label": _node_label(node) if node else node_id,
                    "depth": _route_node_depth(node) if node else 1,
                    "node_kind": _node_kind(node) if node else "",
                }
                if not _is_route_root_node({**node, **path_item}):
                    path.append(path_item)
        return [item for item in path if item.get("node_id")]

    if not active_node:
        return []
    nodes = _all_route_nodes(route)
    by_id = {_node_id(node): node for node in nodes}
    current = by_id.get(str(active_node))
    if not current:
        return []
    reversed_path: list[dict[str, Any]] = []
    seen: set[str] = set()
    while current:
        node_id = _node_id(current)
        if not node_id or node_id in seen:
            break
        seen.add(node_id)
        reversed_path.append(
            {
                "node_id": node_id,
                "label": _node_label(current),
                "depth": _route_node_depth(current),
                "node_kind": _node_kind(current),
            }
        )
        parent_id = current.get("parent_node_id")
        current = by_id.get(str(parent_id)) if parent_id else None
    return [item for item in reversed(reversed_path) if item.get("node_kind") != "root" and item.get("depth") != 0]


def _hidden_leaf_progress(route: dict[str, Any]) -> dict[str, Any]:
    display_depth = _route_display_depth(route)
    hidden_leaves = [
        node
        for node in _all_route_nodes(route)
        if _route_node_depth(node) > display_depth and _node_kind(node) in {"leaf", "repair"}
    ]
    completed = [
        node
        for node in hidden_leaves
        if _normalize(node.get("status")) in {"complete", "completed", "done"}
    ]
    return {
        "display_depth": display_depth,
        "hidden_leaf_count": len(hidden_leaves),
        "completed_hidden_leaf_count": len(completed),
        "has_hidden_leaves": bool(hidden_leaves),
    }


def _node_map(route: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_node_id(node): node for node in _all_route_nodes(route) if _node_id(node)}


def _descendant_ids(node_id: str, nodes_by_id: dict[str, dict[str, Any]]) -> set[str]:
    descendants: set[str] = set()
    stack = [node_id]
    while stack:
        current_id = stack.pop()
        if current_id in descendants:
            continue
        descendants.add(current_id)
        node = nodes_by_id.get(current_id, {})
        stack.extend(child_id for child_id in _node_child_ids(node) if child_id in nodes_by_id)
    return descendants


def _terminal_descendant_ids(node_id: str, nodes_by_id: dict[str, dict[str, Any]]) -> set[str]:
    terminals: set[str] = set()
    for descendant_id in _descendant_ids(node_id, nodes_by_id):
        descendant = nodes_by_id.get(descendant_id, {})
        child_ids = [child_id for child_id in _node_child_ids(descendant) if child_id in nodes_by_id]
        if not child_ids or _node_kind(descendant) in {"leaf", "repair"}:
            terminals.add(descendant_id)
    return terminals or {node_id}


def _completed_node_ids(frontier: dict[str, Any], route: dict[str, Any]) -> set[str]:
    completed = {str(item) for item in frontier.get("completed_nodes") or [] if item}
    for node in _all_route_nodes(route):
        if _normalize(node.get("status")) in {"complete", "completed", "done"}:
            node_id = _node_id(node)
            if node_id:
                completed.add(node_id)
    return completed


def _visible_active_node_id(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    visible_nodes: list[dict[str, Any]],
    active_node: str | None,
) -> str | None:
    if not active_node:
        return None
    visible_ids = {_node_id(node) for node in visible_nodes if _node_id(node)}
    if active_node in visible_ids:
        return active_node
    active_path = _route_active_path(frontier, route, active_node)
    for item in reversed(active_path):
        node_id = str(item.get("node_id") or item.get("id") or "")
        if node_id in visible_ids:
            return node_id
    nodes_by_id = _node_map(route)
    candidates = [
        node
        for node in visible_nodes
        if active_node in _descendant_ids(_node_id(node), nodes_by_id)
    ]
    if not candidates:
        return None
    return _node_id(max(candidates, key=_route_node_depth))


def _node_status(
    node: dict[str, Any],
    active_node: str | None,
    *,
    active_visible_node: str | None = None,
    frontier: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
) -> str:
    node_id = _node_id(node)
    status = _normalize(node.get("status"))
    if node_id == (active_visible_node or active_node):
        return "active"
    if status in {"superseded", "stale"}:
        return "superseded"
    if status in {"blocked", "failed"}:
        return "blocked"
    if status in {"complete", "completed", "done"}:
        return "done"
    if route is not None:
        nodes_by_id = _node_map(route)
        completed = _completed_node_ids(frontier or {}, route)
        if node_id in completed:
            return "done"
        descendant_ids = _descendant_ids(node_id, nodes_by_id)
        for descendant_id in descendant_ids:
            descendant = nodes_by_id.get(descendant_id, {})
            if _normalize(descendant.get("status")) in {"blocked", "failed"}:
                return "blocked"
        terminal_ids = _terminal_descendant_ids(node_id, nodes_by_id)
        if terminal_ids and terminal_ids.issubset(completed):
            if _node_child_ids(node):
                return "review"
            return "done"
    return "pending"


def _active_route(frontier: dict[str, Any], state: dict[str, Any], route: dict[str, Any] | None = None) -> str | None:
    route = route or {}
    value = (
        frontier.get("active_route_id")
        or frontier.get("active_route")
        or frontier.get("route_id")
        or state.get("active_route_id")
        or state.get("active_route")
        or state.get("route_id")
        or route.get("route_id")
    )
    return str(value) if value else None


def _active_node(frontier: dict[str, Any], state: dict[str, Any] | None = None, route: dict[str, Any] | None = None) -> str | None:
    state = state or {}
    route = route or {}
    value = (
        frontier.get("active_node_id")
        or frontier.get("active_node")
        or frontier.get("current_node")
        or state.get("active_node_id")
        or state.get("active_node")
        or state.get("current_node")
        or route.get("active_node_id")
        or route.get("active_node")
        or route.get("current_node")
    )
    return str(value) if value else None


def classify_current_stage(frontier: dict[str, Any], route: dict[str, Any]) -> str:
    active_node = _active_node(frontier, route=route)
    status = _normalize(frontier.get("status"))
    route_status = _normalize(route.get("status"))
    route_mutation = frontier.get("route_mutation") or {}
    route_mutation_pending = _route_mutation_pending(frontier)
    known_route_nodes = {_node_id(node) for node in _all_route_nodes(route) if _node_id(node)}
    text = " ".join(
        _normalize(value)
        for value in (
            active_node,
            frontier.get("current_subnode"),
            frontier.get("next_gate"),
            frontier.get("current_chunk"),
            frontier.get("next_chunk"),
            route_mutation.get("reason"),
        )
    )
    completed = (
        active_node == "complete"
        or status in {"complete", "completed"}
        or (route_status in {"complete", "completed"} and str(active_node) not in known_route_nodes)
    )
    return _stage_from_text(text, completed=completed, route_mutation_pending=route_mutation_pending)


def _escape_label(text: str) -> str:
    return text.replace('"', "&quot;")


def _title_from_id(raw: str) -> str:
    text = re.sub(r"^node-\d+-?", "", raw)
    text = text.replace("_", "-").replace("-", " ").strip()
    return text.title() if text else raw


def _shorten(text: str, *, limit: int = 48) -> str:
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "..."


def _node_label(node: dict[str, Any]) -> str:
    for key in ("display_name", "name", "title", "label"):
        if node.get(key):
            return _shorten(str(node[key]))
    node_id = _node_id(node) or "node"
    return _shorten(_title_from_id(node_id))


def _node_topology(node: dict[str, Any]) -> dict[str, Any]:
    topology = node.get("route_topology") if isinstance(node.get("route_topology"), dict) else {}
    strategy = str(node.get("topology_strategy") or topology.get("topology_strategy") or "").strip()
    superseded = node.get("supersedes_node_ids")
    if superseded is None:
        superseded = topology.get("superseded_nodes")
    affected_siblings = node.get("affected_sibling_nodes")
    if affected_siblings is None:
        affected_siblings = topology.get("affected_sibling_nodes")
    return {
        "topology_strategy": strategy,
        "repair_of_node_id": node.get("repair_of_node_id") or topology.get("repair_of_node_id"),
        "repair_return_to_node_id": node.get("repair_return_to_node_id") or topology.get("repair_return_to_node_id"),
        "superseded_nodes": [str(item) for item in (superseded or [])],
        "affected_sibling_nodes": [str(item) for item in (affected_siblings or [])],
        "replay_scope_node_id": node.get("replay_scope_node_id") or topology.get("replay_scope_node_id"),
        "continue_after_node_id": node.get("continue_after_node_id") or topology.get("continue_after_node_id"),
    }


def _is_mutation_node(node: dict[str, Any]) -> bool:
    return bool(node.get("created_by_mutation") or _node_topology(node)["topology_strategy"])


def _route_nodes(frontier: dict[str, Any], route: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [node for node in _display_depth_nodes(route) if _node_id(node)]
    mainline = [str(item) for item in frontier.get("current_mainline") or []]
    if mainline:
        by_id = {_node_id(node): node for node in nodes}
        ordered = [by_id[node_id] for node_id in mainline if node_id in by_id]
        if ordered:
            included = {_node_id(node) for node in ordered}
            active_node = str(_active_node(frontier, route=route) or "")
            ordered.extend(
                node
                for node in nodes
                if _node_id(node) not in included
                and (_node_id(node) == active_node or _is_mutation_node(node))
            )
            return ordered
    return nodes


def _use_route_node_layout(nodes: list[dict[str, Any]]) -> bool:
    return bool(nodes)


def detect_return_path(
    *,
    frontier: dict[str, Any],
    route_nodes: list[dict[str, Any]],
    active_node: str | None,
    trigger: str,
) -> dict[str, Any]:
    route_mutation = frontier.get("route_mutation") or {}
    failed_review = route_mutation.get("failed_review") or {}
    node_ids = [_node_id(node) for node in route_nodes if _node_id(node)]
    completed_indexes = [
        index
        for index, node in enumerate(route_nodes)
        if _normalize(node.get("status")) in {"complete", "completed", "done"}
    ]
    active_index = node_ids.index(str(active_node)) if active_node in node_ids else -1
    max_completed_index = max(completed_indexes) if completed_indexes else -1
    is_backtrack = active_index >= 0 and max_completed_index > active_index
    return_required = (
        trigger in RETURN_TRIGGERS
        or bool(route_mutation.get("pending"))
        or bool(failed_review.get("blocking"))
        or is_backtrack
    )
    repair_target = (
        failed_review.get("repair_target")
        or route_mutation.get("repair_target")
        or (active_node if is_backtrack else None)
    )
    failed_child = failed_review.get("failed_child")
    return_source = None
    if failed_child in node_ids:
        return_source = failed_child
    elif active_index >= 0 and max_completed_index > active_index:
        return_source = node_ids[max_completed_index]
    elif active_index >= 0 and active_index + 1 < len(node_ids):
        return_source = node_ids[active_index + 1]
    elif frontier.get("next_node") in node_ids:
        return_source = frontier.get("next_node")

    if return_required and not repair_target:
        repair_target = active_node if active_node in node_ids else (node_ids[active_index] if active_index >= 0 else None)
    if return_required and repair_target in node_ids and not return_source:
        return_source = "review_gate"
    return {
        "required": return_required,
        "is_backtrack": is_backtrack,
        "repair_target": repair_target,
        "return_source": return_source,
        "edge_present": bool(
            return_required
            and repair_target in node_ids
            and (return_source in node_ids or return_source == "review_gate")
        ),
    }


def _class_line(ids: list[str], class_name: str) -> str | None:
    if not ids:
        return None
    return f"  class {','.join(ids)} {class_name};"


def _build_route_node_mermaid(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    nodes: list[dict[str, Any]],
    active_node: str | None,
    return_path: dict[str, Any],
) -> str:
    active_route = _active_route(frontier, {}, route) or "unknown route"
    route_version = frontier.get("route_version") or route.get("route_version") or "unknown"
    active_node_label = active_node or ("not-started" if nodes else "unknown")
    active_visible_node = _visible_active_node_id(
        frontier=frontier,
        route=route,
        visible_nodes=nodes,
        active_node=active_node,
    )
    node_ids = [_node_id(node) for node in nodes]
    mermaid_ids = {node_id: f"n{index + 1:02d}" for index, node_id in enumerate(node_ids)}
    lines = [
        "flowchart LR",
        f"  %% FlowPilot realtime route sign. Source: route={active_route}, version={route_version}, node={active_node_label}",
    ]
    done_ids: list[str] = []
    review_ids: list[str] = []
    pending_ids: list[str] = []
    blocked_ids: list[str] = []
    active_ids: list[str] = []
    superseded_ids: list[str] = []
    for node in nodes:
        node_id = _node_id(node)
        mermaid_id = mermaid_ids[node_id]
        status = _node_status(
            node,
            active_node,
            active_visible_node=active_visible_node,
            frontier=frontier,
            route=route,
        )
        lines.append(f'  {mermaid_id}["{_escape_label(_node_label(node))}"]')
        if status == "active":
            active_ids.append(mermaid_id)
        elif status == "done":
            done_ids.append(mermaid_id)
        elif status == "review":
            review_ids.append(mermaid_id)
        elif status == "blocked":
            blocked_ids.append(mermaid_id)
        elif status == "superseded":
            superseded_ids.append(mermaid_id)
        else:
            pending_ids.append(mermaid_id)

    def add_edge(edge: str, seen: set[str]) -> None:
        if edge not in seen:
            lines.append(edge)
            seen.add(edge)

    edge_lines: set[str] = set()
    topology_by_id = {node_id: _node_topology(node) for node_id, node in zip(node_ids, nodes)}
    replacement_by_superseded: dict[str, str] = {}
    for node_id, topology in topology_by_id.items():
        if topology["topology_strategy"] in {"supersede_original", "sibling_branch_replacement"}:
            for superseded_node in topology["superseded_nodes"] + topology["affected_sibling_nodes"]:
                replacement_by_superseded[str(superseded_node)] = node_id

    mainline_ids: list[str] = []
    for node in nodes:
        node_id = _node_id(node)
        if not node_id:
            continue
        topology = topology_by_id.get(node_id, {})
        strategy = topology.get("topology_strategy")
        if (
            _node_status(
                node,
                active_node,
                active_visible_node=active_visible_node,
                frontier=frontier,
                route=route,
            )
            == "superseded"
        ):
            replacement = replacement_by_superseded.get(node_id)
            if replacement in mermaid_ids and replacement not in mainline_ids:
                mainline_ids.append(replacement)
            continue
        if strategy in {"return_to_original", "branch_then_continue"}:
            continue
        if node_id not in mainline_ids:
            mainline_ids.append(node_id)

    for left, right in zip(mainline_ids, mainline_ids[1:]):
        add_edge(f"  {mermaid_ids[left]} --> {mermaid_ids[right]}", edge_lines)

    topology_edge_present = False
    for node_id, topology in topology_by_id.items():
        strategy = topology.get("topology_strategy")
        if strategy == "return_to_original":
            repair_of = str(topology.get("repair_of_node_id") or "")
            return_to = str(topology.get("repair_return_to_node_id") or repair_of)
            if repair_of in mermaid_ids:
                add_edge(f"  {mermaid_ids[repair_of]} --> {mermaid_ids[node_id]}", edge_lines)
                topology_edge_present = True
            if return_to in mermaid_ids:
                add_edge(f'  {mermaid_ids[node_id]} -- "returns for repair" --> {mermaid_ids[return_to]}', edge_lines)
                topology_edge_present = True
        elif strategy == "supersede_original":
            for superseded_node in topology.get("superseded_nodes") or []:
                if superseded_node in mermaid_ids:
                    add_edge(f'  {mermaid_ids[superseded_node]} -. "superseded by" .-> {mermaid_ids[node_id]}', edge_lines)
                    topology_edge_present = True
        elif strategy == "branch_then_continue":
            repair_of = str(topology.get("repair_of_node_id") or "")
            continue_after = str(topology.get("continue_after_node_id") or "")
            if repair_of in mermaid_ids:
                add_edge(f"  {mermaid_ids[repair_of]} --> {mermaid_ids[node_id]}", edge_lines)
                topology_edge_present = True
            if continue_after in mermaid_ids:
                add_edge(f"  {mermaid_ids[node_id]} --> {mermaid_ids[continue_after]}", edge_lines)
                topology_edge_present = True
        elif strategy == "sibling_branch_replacement":
            for sibling_node in topology.get("affected_sibling_nodes") or []:
                if sibling_node in mermaid_ids:
                    add_edge(f'  {mermaid_ids[sibling_node]} -. "replaced by" .-> {mermaid_ids[node_id]}', edge_lines)
                    topology_edge_present = True
            replay_scope = str(topology.get("replay_scope_node_id") or "")
            if replay_scope in mermaid_ids:
                add_edge(f'  {mermaid_ids[node_id]} -- "replays scope" --> {mermaid_ids[replay_scope]}', edge_lines)
                topology_edge_present = True

    if return_path["edge_present"] and not topology_edge_present:
        if return_path["return_source"] == "review_gate":
            lines.append('  reviewGate["Review / validation gate"]')
            source = "reviewGate"
        else:
            source = mermaid_ids[str(return_path["return_source"])]
        target = mermaid_ids[str(return_path["repair_target"])]
        lines.append(f'  {source} -- "returns for repair" --> {target}')

    if str(frontier.get("next_node") or "") == "complete":
        lines.append(f'  done["Completion"]')
        if mainline_ids:
            lines.append(f"  {mermaid_ids[mainline_ids[-1]]} --> done")
    lines.extend(
        [
            "",
            "  classDef active fill:#e6fbff,stroke:#00bcd4,stroke-width:4px,color:#0f172a;",
            "  classDef done fill:#ecfdf5,stroke:#10b981,color:#064e3b;",
            "  classDef review fill:#fff7ed,stroke:#f97316,color:#7c2d12;",
            "  classDef pending fill:#f8fafc,stroke:#cbd5e1,color:#334155;",
            "  classDef blocked fill:#fef2f2,stroke:#ef4444,color:#7f1d1d;",
            "  classDef superseded fill:#f1f5f9,stroke:#94a3b8,stroke-dasharray: 4 3,color:#64748b;",
        ]
    )
    for class_line in (
        _class_line(done_ids, "done"),
        _class_line(review_ids, "review"),
        _class_line(pending_ids, "pending"),
        _class_line(blocked_ids, "blocked"),
        _class_line(superseded_ids, "superseded"),
        _class_line(active_ids, "active"),
    ):
        if class_line:
            lines.append(class_line)
    return "\n".join(lines)


def _build_stage_mermaid(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    current_stage: str,
    active_node: str | None,
    return_path: dict[str, Any],
) -> str:
    active_route = _active_route(frontier, {}, route) or "unknown route"
    route_version = frontier.get("route_version") or route.get("route_version") or "unknown"
    active_node_label = active_node or "unknown"
    lines = [
        "flowchart LR",
        f"  %% FlowPilot temporary startup placeholder route sign. Replace with canonical route when available. Source: route={active_route}, version={route_version}, node={active_node_label}",
    ]
    for key, label in FALLBACK_STAGES:
        lines.append(f'  {key}["{_escape_label(label)}"]')

    lines.extend(
        [
            "  intake --> product",
            "  product --> modeling",
            "  modeling --> route",
            "  route --> execution",
            "  execution --> verification",
            "  verification --> completion",
        ]
    )
    needs_repair_stage = return_path["required"] or current_stage == "repair"
    if needs_repair_stage:
        lines.append('  repair["Repair Return"]')
    if return_path["required"]:
        lines.append('  verification -- "returns for repair" --> repair')
        lines.append(f"  repair --> {current_stage if current_stage in ALLOWED_STAGES and current_stage != 'completion' else 'route'}")
    lines.extend(
        [
            "",
            "  classDef active fill:#e6fbff,stroke:#00bcd4,stroke-width:4px,color:#0f172a;",
            "  classDef normal fill:#f8fafc,stroke:#cbd5e1,color:#334155;",
            "  classDef repair fill:#fff7ed,stroke:#fb923c,color:#7c2d12;",
            "  class intake,product,modeling,route,execution,verification,completion normal;",
            f"  class {current_stage if current_stage in ALLOWED_STAGES else 'route'} active;",
        ]
    )
    if needs_repair_stage:
        lines.append("  class repair repair;")
    return "\n".join(lines)


def build_mermaid(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    current_stage: str,
    trigger: str,
) -> tuple[str, dict[str, Any]]:
    active_node = _active_node(frontier, route=route)
    nodes = _route_nodes(frontier, route)
    active_path = _route_active_path(frontier, route, str(active_node) if active_node else None)
    hidden_leaf_progress = _hidden_leaf_progress(route)
    return_path = detect_return_path(
        frontier=frontier,
        route_nodes=nodes,
        active_node=str(active_node) if active_node else None,
        trigger=trigger,
    )
    if _use_route_node_layout(nodes):
        active_visible_node = _visible_active_node_id(
            frontier=frontier,
            route=route,
            visible_nodes=nodes,
            active_node=str(active_node) if active_node else None,
        )
        source = _build_route_node_mermaid(
            frontier=frontier,
            route=route,
            nodes=nodes,
            active_node=str(active_node) if active_node else None,
            return_path=return_path,
        )
        layout = "route_nodes"
        node_ids = [_node_id(node) for node in nodes]
        mermaid_ids = {node_id: f"n{index + 1:02d}" for index, node_id in enumerate(node_ids)}
        active_highlight = {
            "mode": "visible_route_node",
            "active_node": active_node,
            "visible_node_id": active_visible_node,
            "visible_mermaid_id": mermaid_ids.get(str(active_visible_node)) if active_visible_node else None,
            "visible_node_is_active_node": bool(active_visible_node and active_visible_node == active_node),
        }
    else:
        source = _build_stage_mermaid(
            frontier=frontier,
            route=route,
            current_stage=current_stage,
            active_node=str(active_node) if active_node else None,
            return_path=return_path,
        )
        layout = "stage_summary"
        active_highlight = {
            "mode": "stage_placeholder",
            "active_node": active_node,
            "visible_node_id": current_stage if current_stage in ALLOWED_STAGES else "route",
            "visible_mermaid_id": current_stage if current_stage in ALLOWED_STAGES else "route",
            "visible_node_is_active_node": False,
        }
    return source, {
        **return_path,
        "layout": layout,
        "display_depth": _route_display_depth(route),
        "active_path": active_path,
        "active_highlight": active_highlight,
        "graph_labels_surface_neutral": True,
        "hidden_leaf_progress": hidden_leaf_progress,
    }


def build_chat_markdown(
    source: str,
    *,
    generated_at: str,
    current_stage: str,
    active_route: str | None,
    active_node: str | None,
    trigger: str,
    cockpit_open: bool,
    chat_display_required: bool,
    return_path: dict[str, Any],
    active_path: list[dict[str, Any]] | None = None,
    hidden_leaf_progress: dict[str, Any] | None = None,
    source_status: str,
    source_findings: list[str],
) -> str:
    """Build only the user-visible route sign body.

    Display-gate, evidence, source-health, and confirmation details are
    internal control-plane data. They stay in the display packet and ledgers.
    """
    lines = [
        "# FlowPilot Route Sign",
        "",
        "```mermaid",
        source,
        "```",
        "",
    ]
    status_items = []
    if active_route:
        status_items.append(f"route `{active_route}`")
    if active_node:
        status_items.append(f"node `{active_node}`")
    if current_stage:
        status_items.append(f"stage `{current_stage}`")
    if status_items:
        lines.extend(["Current status: " + ", ".join(status_items), ""])
    elif source_status != "ok":
        lines.extend(["Current status: waiting for a healthy FlowPilot route source.", ""])
    else:
        lines.extend(["Current status: temporary placeholder until the PM-approved route exists.", ""])
    if active_path:
        path_labels = [
            f"{item.get('label') or item.get('node_id')} ({item.get('node_id')})"
            for item in active_path
            if item.get("node_id")
        ]
        if path_labels:
            lines.extend(["Current path: " + " > ".join(path_labels), ""])
    if hidden_leaf_progress and hidden_leaf_progress.get("has_hidden_leaves"):
        lines.extend(
            [
                "Hidden leaf progress: "
                f"{hidden_leaf_progress.get('completed_hidden_leaf_count', 0)}/"
                f"{hidden_leaf_progress.get('hidden_leaf_count', 0)} complete",
                "",
            ]
        )
    return "\n".join(lines)


def _route_source_summary(route: dict[str, Any]) -> dict[str, int]:
    nodes = _all_route_nodes(route)
    checklist_count = 0
    for node in nodes:
        checklist = node.get("checklist")
        if isinstance(checklist, list):
            checklist_count += len(checklist)
    return {
        "node_count": len(nodes),
        "checklist_item_count": checklist_count,
    }


def _route_source_candidates(
    routes_root: Path,
    active_route: str | None,
    snapshot_route_id: str | None,
    *,
    include_drafts: bool = False,
) -> list[Path]:
    route_ids: list[str] = []
    for raw in (active_route, snapshot_route_id, "route-001"):
        if raw and raw not in route_ids:
            route_ids.append(str(raw))
    candidates: list[Path] = []
    for route_id in route_ids:
        route_dir = routes_root / route_id
        candidates.append(route_dir / "flow.json")
        if include_drafts:
            candidates.append(route_dir / "flow.draft.json")
    if routes_root.exists():
        candidates.extend(sorted(routes_root.glob("*/flow.json")))
        if include_drafts:
            candidates.extend(sorted(routes_root.glob("*/flow.draft.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _load_route_source(
    paths: dict[str, Any],
    *,
    active_route: str | None,
    snapshot: dict[str, Any],
    include_drafts: bool = False,
) -> tuple[dict[str, Any], Path, str]:
    routes_root = Path(paths["routes_root"])
    snapshot_path = Path(paths["run_root"]) / "route_state_snapshot.json"
    snapshot_route = _snapshot_route(snapshot)
    snapshot_route_id = str(snapshot_route.get("route_id") or "") or None
    for path in _route_source_candidates(
        routes_root,
        active_route,
        snapshot_route_id,
        include_drafts=include_drafts,
    ):
        route = _load_json(path)
        if route.get("nodes"):
            suffix = "flow_json" if path.name == "flow.json" else "flow_draft"
            return route, path, suffix
    committed_route_exists = any(
        path.exists()
        for path in _route_source_candidates(
            routes_root,
            active_route,
            snapshot_route_id,
            include_drafts=False,
        )
    )
    if snapshot_route.get("nodes") and committed_route_exists:
        return snapshot_route, snapshot_path, "route_state_snapshot"
    fallback_route_id = active_route or snapshot_route_id or "route-001"
    return {}, routes_root / fallback_route_id / "flow.json", "none"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _review_display(
    *,
    display_packet: dict[str, Any],
    mermaid: str,
    chat_displayed: bool,
    ui_displayed: bool,
) -> dict[str, Any]:
    findings: list[str] = []
    if display_packet["chat_display_required"] and not chat_displayed:
        findings.append("Cockpit UI is closed, but the Mermaid route sign was not confirmed in chat.")
    if not display_packet["simplified_flowpilot_english_mermaid"]:
        findings.append("The display artifact is not the simplified English FlowPilot route sign.")
    if display_packet["raw_flowguard_mermaid"]["enabled"]:
        findings.append("Raw FlowGuard Mermaid cannot satisfy the user route sign gate.")
    if display_packet["source_health"]["status"] != "ok":
        findings.extend(display_packet["source_health"]["findings"])
    if display_packet["return_or_repair"]["required"] and not display_packet["return_or_repair"]["edge_present"]:
        findings.append("A review/validation return or route mutation lacks a visible repair edge.")
    active_node = str(display_packet.get("active_node") or "")
    active_path_ids = {
        str(item.get("node_id") or item.get("id") or "")
        for item in display_packet.get("active_path", [])
        if isinstance(item, dict)
    }
    active_highlight = display_packet.get("active_highlight") if isinstance(display_packet.get("active_highlight"), dict) else {}
    visible_mermaid_id = str(active_highlight.get("visible_mermaid_id") or "")
    active_graph_highlighted = bool(
        visible_mermaid_id
        and re.search(rf"\bclass\s+[^;\n]*\b{re.escape(visible_mermaid_id)}\b[^;\n]*\sactive\s*;", mermaid)
    )
    active_node_visible = bool(active_node and (active_node in mermaid or active_node in active_path_ids))
    canonical_route = bool(display_packet.get("canonical_route_available"))
    if canonical_route and active_node and not active_graph_highlighted:
        findings.append("The route sign does not highlight the active node or its nearest visible route ancestor.")
    elif active_node and not active_node_visible:
        findings.append("The route sign does not include the active node in either the visible diagram or current path.")
    if not display_packet.get("graph_labels_surface_neutral", True):
        findings.append("The shared Mermaid route sign labels are not surface-neutral.")
    if not chat_displayed and not ui_displayed:
        findings.append("No visible display surface was confirmed.")
    return {
        "schema_version": "flowpilot.user_flow_diagram.review.v1",
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reviewer_role": "human_like_reviewer",
        "status": "pass" if not findings else "blocked",
        "checked_chat_display": chat_displayed,
        "checked_cockpit_ui_display": ui_displayed,
        "checked_active_route_node_match": active_graph_highlighted if canonical_route and active_node else active_node_visible if active_node else False,
        "checked_active_graph_highlight": active_graph_highlighted,
        "checked_return_or_repair_edge": not display_packet["return_or_repair"]["required"]
        or display_packet["return_or_repair"]["edge_present"],
        "blocking_findings": findings,
    }


def generate(
    root: Path,
    *,
    write: bool,
    trigger: str,
    cockpit_open: bool,
    display_surface: str,
    mark_chat_displayed: bool,
    mark_ui_displayed: bool,
    reviewer_check: bool,
    include_drafts: bool = False,
) -> dict[str, Any]:
    paths = resolve_flowpilot_paths(root)
    frontier_path = Path(paths["frontier_path"])
    source_health = {
        "status": paths["path_status"],
        "findings": list(paths["path_findings"]),
        "current_declares_run": paths["current_declares_run"],
        "active_run_root_valid": paths["active_run_root_valid"],
    }
    if source_health["status"] == "ok":
        frontier = _load_json(frontier_path)
        state = _load_json(Path(paths["state_path"]))
        snapshot = _load_json(Path(paths["run_root"]) / "route_state_snapshot.json")
    else:
        frontier = {}
        state = {}
        snapshot = {}
    snapshot_route = _snapshot_route(snapshot)
    active_route = _active_route(frontier, state, snapshot_route)
    if source_health["status"] == "ok":
        route, route_path, route_source_kind = _load_route_source(
            paths,
            active_route=active_route,
            snapshot=snapshot,
            include_drafts=include_drafts,
        )
    else:
        route = {}
        route_path = Path(paths["routes_root"]) / str(active_route or "route-001") / "flow.json"
        route_source_kind = "none"
    current_stage = classify_current_stage(frontier, route)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source, route_sign = build_mermaid(
        frontier=frontier,
        route=route,
        current_stage=current_stage,
        trigger=trigger,
    )
    active_route = _active_route(frontier, state, route)
    active_node = _active_node(frontier, state, route)
    route_source_summary = _route_source_summary(route)
    chat_display_required = trigger in DISPLAY_TRIGGERS and not cockpit_open
    markdown = build_chat_markdown(
        source,
        generated_at=generated_at,
        current_stage=current_stage,
        active_route=str(active_route) if active_route else None,
        active_node=str(active_node) if active_node else None,
        trigger=trigger,
        cockpit_open=cockpit_open,
        chat_display_required=chat_display_required,
        return_path=route_sign,
        active_path=route_sign["active_path"],
        hidden_leaf_progress=route_sign["hidden_leaf_progress"],
        source_status=source_health["status"],
        source_findings=source_health["findings"],
    )
    mermaid_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    canonical_route_available = (
        source_health["status"] == "ok"
        and route_source_kind in {"flow_json", "route_state_snapshot"}
        and route_source_summary["node_count"] > 0
    )
    display_role = "canonical_route" if canonical_route_available else "startup_placeholder"
    is_placeholder = not canonical_route_available
    replacement_rule = "replace_when_canonical_route_available" if is_placeholder else None

    diagram_dir = Path(paths["diagrams_dir"])
    mmd_path = diagram_dir / "user-flow-diagram.mmd"
    md_path = diagram_dir / "user-flow-diagram.md"
    display_packet_path = diagram_dir / "user-flow-diagram-display.json"
    review_path = diagram_dir / "user-flow-diagram-review.json"
    display_packet = {
        "schema_version": "flowpilot.user_flow_diagram.display.v1",
        "diagram_kind": "flowpilot_realtime_route_sign",
        "language": "en",
        "generated_at": generated_at,
        "display_trigger": trigger,
        "display_role": display_role,
        "is_placeholder": is_placeholder,
        "replacement_rule": replacement_rule,
        "display_surface": display_surface,
        "cockpit_open": cockpit_open,
        "chat_display_required": chat_display_required,
        "chat_displayed_in_chat": mark_chat_displayed,
        "cockpit_ui_displayed": mark_ui_displayed,
        "display_gate_status": "passed"
        if (
            source_health["status"] == "ok"
            and (not chat_display_required or mark_chat_displayed)
            and (not cockpit_open or mark_ui_displayed or display_surface in {"chat", "both"})
        )
        else "blocked_degraded_source"
        if source_health["status"] != "ok"
        else "pending_visible_display",
        "source_health": source_health,
        "same_graph_for_chat_and_ui": False,
        "chat_mermaid_is_shallow_route_projection": True,
        "cockpit_ui_should_render_full_route_tree": True,
        "simplified_flowpilot_english_mermaid": True,
        "user_visible_display_text": {
            "clean": True,
            "content": "title_mermaid_current_status_current_path_and_hidden_leaf_progress",
            "contains_internal_display_evidence": False,
            "internal_evidence_location": "display_packet_and_user_dialog_display_ledger",
        },
        "raw_flowguard_mermaid": {
            "enabled": False,
            "satisfies_user_route_sign_gate": False,
        },
        "stage_count_target": "startup_placeholder_only; canonical_route_renders_real_route_nodes",
        "layout": route_sign["layout"],
        "display_depth": route_sign["display_depth"],
        "active_path": route_sign["active_path"],
        "active_highlight": route_sign["active_highlight"],
        "graph_labels_surface_neutral": route_sign["graph_labels_surface_neutral"],
        "hidden_leaf_progress": route_sign["hidden_leaf_progress"],
        "current_stage": current_stage,
        "active_route": active_route,
        "active_node": active_node,
        "route_version_rendered": frontier.get("route_version") or route.get("route_version"),
        "frontier_version_rendered": frontier.get("frontier_version"),
        "route_source_kind": route_source_kind,
        "canonical_route_available": canonical_route_available,
        "route_node_count": route_source_summary["node_count"],
        "route_checklist_item_count": route_source_summary["checklist_item_count"],
        "source_route_path": str(route_path),
        "source_frontier_path": str(frontier_path),
        "mermaid_path": str(mmd_path),
        "markdown_preview_path": str(md_path),
        "mermaid_sha256": mermaid_hash,
        "return_or_repair": {
            "required": route_sign["required"],
            "is_backtrack": route_sign["is_backtrack"],
            "return_source": route_sign["return_source"],
            "repair_target": route_sign["repair_target"],
            "edge_present": route_sign["edge_present"],
        },
        "reviewer_gate": {
            "required": True,
            "review_path": str(review_path),
            "must_check_chat_when_cockpit_closed": True,
            "must_check_active_route_node_match": True,
            "must_check_return_edge_when_required": True,
        },
    }

    review_payload: dict[str, Any] | None = None
    if reviewer_check:
        review_payload = _review_display(
            display_packet=display_packet,
            mermaid=source,
            chat_displayed=mark_chat_displayed,
            ui_displayed=mark_ui_displayed,
        )

    if write:
        diagram_dir.mkdir(parents=True, exist_ok=True)
        mmd_path.write_text(source + "\n", encoding="utf-8")
        md_path.write_text(markdown, encoding="utf-8")
        _write_json(display_packet_path, display_packet)
        if review_payload is not None:
            _write_json(review_path, review_payload)

    return {
        "ok": source_health["status"] == "ok" and (review_payload is None or review_payload["status"] == "pass"),
        "write": write,
        "diagram_kind": "flowpilot_realtime_route_sign",
        "language": "en",
        "display_trigger": trigger,
        "display_surface": display_surface,
        "cockpit_open": cockpit_open,
        "chat_display_required": chat_display_required,
        "current_stage": current_stage,
        "layout": paths["layout"],
        "flowpilot_layout": paths["layout"],
        "flowpilot_path_status": paths["path_status"],
        "flowpilot_path_findings": list(paths["path_findings"]),
        "current_declares_run": paths["current_declares_run"],
        "active_run_root_valid": paths["active_run_root_valid"],
        "display_gate_status": display_packet["display_gate_status"],
        "display_role": display_role,
        "is_placeholder": is_placeholder,
        "replacement_rule": replacement_rule,
        "route_sign_layout": route_sign["layout"],
        "display_depth": route_sign["display_depth"],
        "active_path": route_sign["active_path"],
        "active_highlight": route_sign["active_highlight"],
        "graph_labels_surface_neutral": route_sign["graph_labels_surface_neutral"],
        "hidden_leaf_progress": route_sign["hidden_leaf_progress"],
        "route_source_kind": route_source_kind,
        "canonical_route_available": canonical_route_available,
        "route_node_count": route_source_summary["node_count"],
        "route_checklist_item_count": route_source_summary["checklist_item_count"],
        "run_id": paths["run_id"],
        "run_root": str(paths["run_root"]),
        "active_route": active_route,
        "active_node": active_node,
        "source_route_path": str(route_path),
        "source_frontier_path": str(frontier_path),
        "mermaid_path": str(mmd_path),
        "markdown_preview_path": str(md_path),
        "display_packet_path": str(display_packet_path),
        "review_path": str(review_path),
        "mermaid_sha256": mermaid_hash,
        "return_or_repair": display_packet["return_or_repair"],
        "review": review_payload,
        "mermaid": source,
        "markdown": markdown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--write", action="store_true", help="Write active-run diagrams/user-flow-diagram.*")
    parser.add_argument("--json", action="store_true", help="Print JSON metadata")
    parser.add_argument("--markdown", action="store_true", help="Print chat-ready Markdown instead of Mermaid source")
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Diagnostic only: allow flow.draft.json as a route-sign source.",
    )
    parser.add_argument(
        "--trigger",
        default="user_request",
        choices=sorted(DISPLAY_TRIGGERS),
        help="Why the route sign is being refreshed",
    )
    parser.add_argument(
        "--display-surface",
        default="chat",
        choices=("chat", "cockpit_ui", "both"),
        help="Visible surface intended for this display",
    )
    parser.add_argument("--cockpit-open", action="store_true", help="Set when Cockpit UI is open and visible")
    parser.add_argument(
        "--mark-chat-displayed",
        action="store_true",
        help="Record that this exact Mermaid was displayed in the chat response",
    )
    parser.add_argument(
        "--mark-ui-displayed",
        action="store_true",
        help="Record that this exact Mermaid was displayed in Cockpit UI",
    )
    parser.add_argument(
        "--reviewer-check",
        action="store_true",
        help="Write/check reviewer display evidence for the route sign gate",
    )
    args = parser.parse_args()

    payload = generate(
        Path(args.root).resolve(),
        write=args.write,
        trigger=args.trigger,
        cockpit_open=_truthy(args.cockpit_open),
        display_surface=args.display_surface,
        mark_chat_displayed=_truthy(args.mark_chat_displayed),
        mark_ui_displayed=_truthy(args.mark_ui_displayed),
        reviewer_check=_truthy(args.reviewer_check),
        include_drafts=_truthy(args.include_drafts),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.markdown:
        print(payload["markdown"])
    else:
        print(payload["mermaid"])
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
