"""Route-tree projection helpers for FlowPilot's user route sign."""

from __future__ import annotations

import re
from typing import Any


def _normalize(text: Any) -> str:
    return str(text or "").lower().replace("_", "-")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


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


def _display_depth_nodes(
    route: dict[str, Any],
    *,
    include_superseded_history: bool = False,
    history_node_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    display_depth = _route_display_depth(route)
    allowed_history_ids = history_node_ids or set()
    visible: list[dict[str, Any]] = []
    for node in _all_route_nodes(route):
        if _is_route_root_node(node):
            continue
        node_id = _node_id(node)
        if _normalize(node.get("status")) in {"superseded", "stale"} and not (
            include_superseded_history and node_id in allowed_history_ids
        ):
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
        and _normalize(node.get("status")) not in {"superseded", "stale"}
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
        or state.get("active_route_id")
        or route.get("route_id")
    )
    return str(value) if value else None


def _active_node(frontier: dict[str, Any], state: dict[str, Any] | None = None, route: dict[str, Any] | None = None) -> str | None:
    state = state or {}
    route = route or {}
    value = (
        frontier.get("active_node_id")
        or frontier.get("active_node")
        or state.get("active_node_id")
        or state.get("active_node")
        or route.get("active_node_id")
        or route.get("active_node")
    )
    return str(value) if value else None



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


def _integer_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _replacement_history_projection(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    requested_visible: bool,
) -> dict[str, Any]:
    """Bind on-demand history to complete runtime-produced replacement identity.

    The projection deliberately does not infer repair lineage from labels,
    mutation-looking ids, or a one-sided fixture. A superseded source is
    renderable only when the current route source proves both directions of the
    source/replacement relation, its generation edge, stable lineage root, and
    replacement-only current membership.
    """

    nodes = _all_route_nodes(route)
    nodes_by_id = {_node_id(node): node for node in nodes if _node_id(node)}
    current_members = [
        str(item)
        for item in (
            frontier.get("current_mainline")
            or route.get("node_order")
            or route.get("current_mainline")
            or []
        )
        if item
    ]
    current_member_set = set(current_members)
    route_version = route.get("route_version")
    complete_items: list[dict[str, Any]] = []
    incomplete_items: list[dict[str, Any]] = []
    findings: list[str] = []

    for source in nodes:
        if _normalize(source.get("status")) != "superseded":
            continue
        source_id = _node_id(source)
        replacement_id = str(source.get("superseded_by") or "")
        replacement = nodes_by_id.get(replacement_id)
        item_findings: list[str] = []
        if not replacement_id:
            item_findings.append("source.superseded_by is missing")
        if replacement is None:
            item_findings.append("replacement node is absent from the canonical route source")
            replacement = {}

        repair_of_node_id = str(replacement.get("repair_of_node_id") or "")
        repair_root_id = str(replacement.get("repair_root_id") or "")
        previous_repair_node_id = str(replacement.get("previous_repair_node_id") or "")
        source_generation = (
            _integer_or_none(source.get("repair_generation"))
            if "repair_generation" in source
            else None
        )
        replacement_generation = (
            _integer_or_none(replacement.get("repair_generation"))
            if "repair_generation" in replacement
            else None
        )
        replacement_route_version = (
            replacement.get("route_version") if "route_version" in replacement else None
        )

        if repair_of_node_id != source_id:
            item_findings.append("replacement.repair_of_node_id does not name the superseded source")
        if not repair_root_id:
            item_findings.append("replacement.repair_root_id is missing")
        if "previous_repair_node_id" not in replacement:
            item_findings.append("replacement.previous_repair_node_id is missing")
        if source_generation is None:
            item_findings.append("source.repair_generation is missing or invalid")
        if replacement_generation is None:
            item_findings.append("replacement.repair_generation is missing or invalid")
        elif source_generation is not None and replacement_generation != source_generation + 1:
            item_findings.append("replacement repair generation is not source generation plus one")
        if replacement_generation is not None and replacement_generation > 1:
            if previous_repair_node_id != source_id:
                item_findings.append(
                    "repeated replacement.previous_repair_node_id does not name the prior active generation"
                )
            if str(source.get("repair_root_id") or "") != repair_root_id:
                item_findings.append("repeated replacement does not preserve the source repair_root_id")
        elif replacement_generation == 1 and previous_repair_node_id:
            item_findings.append("first replacement must not claim a previous repair generation")
        if replacement_route_version is None:
            item_findings.append("replacement.route_version is missing")
        elif route_version is None or str(replacement_route_version) != str(route_version):
            item_findings.append("replacement.route_version does not match the rendered route version")
        if _normalize(replacement.get("status")) in {"superseded", "stale"}:
            item_findings.append("replacement is not a current authority candidate")
        if not current_member_set:
            item_findings.append("canonical current membership is missing")
        else:
            if source_id in current_member_set:
                item_findings.append("superseded source remains in current membership")
            if replacement_id not in current_member_set:
                item_findings.append("replacement is absent from current membership")

        item = {
            "source_node_id": source_id,
            "replacement_node_id": replacement_id,
            "repair_of_node_id": repair_of_node_id,
            "repair_root_id": repair_root_id,
            "previous_repair_node_id": previous_repair_node_id,
            "source_repair_generation": source_generation,
            "repair_generation": replacement_generation,
            "route_version": replacement_route_version,
            "source_authority": "history_only",
            "current_authority_node_id": replacement_id,
            "lineage_relation": "repaired_by",
        }
        if item_findings:
            incomplete_items.append({**item, "identity_findings": item_findings})
            findings.extend(f"{source_id}: {finding}" for finding in item_findings)
        else:
            complete_items.append(item)

    if not complete_items and not incomplete_items:
        producer_identity_status = "not_applicable"
    elif incomplete_items:
        producer_identity_status = "incomplete"
    else:
        producer_identity_status = "complete"
    history_available = producer_identity_status == "complete" and bool(complete_items)
    rendered_visible = bool(requested_visible and history_available)

    return {
        "schema_version": "flowpilot.replacement_history_projection.v1",
        "content_class": "user_on_demand",
        "default_visibility": "hidden",
        "requested_visible": bool(requested_visible),
        "rendered_visible": rendered_visible,
        "history_available": history_available,
        "producer_identity_status": producer_identity_status,
        "current_authority_policy": "replacement_only",
        "superseded_source_policy": "history_only_never_current_authority",
        "reveal_control": {
            "control_id": "show_superseded_history",
            "label": "Show repair history",
            "action": "regenerate_route_sign",
            "parameter": {"include_superseded_history": True},
            "keyboard_operable": True,
        },
        "return_control": {
            "control_id": "hide_superseded_history",
            "label": "Hide repair history",
            "action": "regenerate_route_sign",
            "parameter": {"include_superseded_history": False},
            "keyboard_operable": True,
        },
        "history_node_ids": [item["source_node_id"] for item in complete_items],
        "current_authority_node_ids": [
            item["current_authority_node_id"] for item in complete_items
        ],
        "identity_items": complete_items,
        "incomplete_identity_items": incomplete_items,
        "blocking_findings": findings,
    }


def _is_mutation_node(node: dict[str, Any]) -> bool:
    return bool(node.get("created_by_mutation") or _node_topology(node)["topology_strategy"])
