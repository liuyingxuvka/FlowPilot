"""Mermaid rendering for FlowPilot's user route sign."""

from __future__ import annotations

from typing import Any

from flowpilot_user_flow_stage import ALLOWED_STAGES, FALLBACK_STAGES, RETURN_TRIGGERS
from flowpilot_user_flow_tree import (
    _active_node,
    _active_route,
    _descendant_ids,
    _display_depth_nodes,
    _hidden_leaf_progress,
    _is_mutation_node,
    _node_id,
    _node_label,
    _node_status,
    _node_topology,
    _normalize,
    _route_active_path,
    _route_display_depth,
    _visible_active_node_id,
)


def _escape_label(text: str) -> str:
    return text.replace('"', "&quot;")




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
