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
    ("repair", "Repair Return"),
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


def _active_route(frontier: dict[str, Any], state: dict[str, Any], route: dict[str, Any] | None = None) -> str | None:
    route = route or {}
    value = (
        frontier.get("active_route")
        or frontier.get("route_id")
        or state.get("active_route")
        or state.get("route_id")
        or route.get("route_id")
    )
    return str(value) if value else None


def _active_node(frontier: dict[str, Any], state: dict[str, Any] | None = None, route: dict[str, Any] | None = None) -> str | None:
    state = state or {}
    route = route or {}
    value = (
        frontier.get("active_node")
        or frontier.get("current_node")
        or state.get("active_node")
        or state.get("current_node")
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
    known_route_nodes = {str(node.get("id")) for node in route.get("nodes", []) if node.get("id")}
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
    node_id = str(node.get("id") or "node")
    return _shorten(_title_from_id(node_id))


def _route_nodes(frontier: dict[str, Any], route: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [node for node in route.get("nodes", []) if isinstance(node, dict) and node.get("id")]
    mainline = [str(item) for item in frontier.get("current_mainline") or []]
    if mainline:
        by_id = {str(node.get("id")): node for node in nodes}
        ordered = [by_id[node_id] for node_id in mainline if node_id in by_id]
        if ordered:
            return ordered
    return nodes


def _use_route_node_layout(nodes: list[dict[str, Any]]) -> bool:
    return 2 <= len(nodes) <= 8


def _node_status(node: dict[str, Any], active_node: str | None) -> str:
    node_id = str(node.get("id") or "")
    status = _normalize(node.get("status"))
    if node_id == active_node:
        return "active"
    if status in {"complete", "completed", "done"}:
        return "done"
    if status in {"blocked", "failed"}:
        return "blocked"
    return "pending"


def detect_return_path(
    *,
    frontier: dict[str, Any],
    route_nodes: list[dict[str, Any]],
    active_node: str | None,
    trigger: str,
) -> dict[str, Any]:
    route_mutation = frontier.get("route_mutation") or {}
    failed_review = route_mutation.get("failed_review") or {}
    node_ids = [str(node.get("id")) for node in route_nodes if node.get("id")]
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
    node_ids = [str(node.get("id")) for node in nodes]
    mermaid_ids = {node_id: f"n{index + 1:02d}" for index, node_id in enumerate(node_ids)}
    lines = [
        "flowchart LR",
        f"  %% FlowPilot realtime route sign. Source: route={active_route}, version={route_version}, node={active_node or 'unknown'}",
    ]
    done_ids: list[str] = []
    pending_ids: list[str] = []
    blocked_ids: list[str] = []
    active_ids: list[str] = []
    for node in nodes:
        node_id = str(node.get("id"))
        mermaid_id = mermaid_ids[node_id]
        status = _node_status(node, active_node)
        status_label = {"active": "Now", "done": "Done", "blocked": "Blocked"}.get(status, "Next")
        label = f"{_node_label(node)}<br/>{status_label}: {_escape_label(node_id)}"
        lines.append(f'  {mermaid_id}["{_escape_label(label)}"]')
        if status == "active":
            active_ids.append(mermaid_id)
        elif status == "done":
            done_ids.append(mermaid_id)
        elif status == "blocked":
            blocked_ids.append(mermaid_id)
        else:
            pending_ids.append(mermaid_id)

    for left, right in zip(node_ids, node_ids[1:]):
        lines.append(f"  {mermaid_ids[left]} --> {mermaid_ids[right]}")

    if return_path["edge_present"]:
        if return_path["return_source"] == "review_gate":
            lines.append('  reviewGate["Review / validation gate"]')
            source = "reviewGate"
        else:
            source = mermaid_ids[str(return_path["return_source"])]
        target = mermaid_ids[str(return_path["repair_target"])]
        lines.append(f'  {source} -- "returns for repair" --> {target}')

    if str(frontier.get("next_node") or "") == "complete":
        lines.append(f'  done["Completion"]')
        if node_ids:
            lines.append(f"  {mermaid_ids[node_ids[-1]]} --> done")
    lines.extend(
        [
            "",
            "  classDef active fill:#e6fbff,stroke:#00bcd4,stroke-width:3px,color:#0f172a;",
            "  classDef done fill:#ecfdf5,stroke:#10b981,color:#064e3b;",
            "  classDef pending fill:#f8fafc,stroke:#cbd5e1,color:#334155;",
            "  classDef blocked fill:#fef2f2,stroke:#ef4444,color:#7f1d1d;",
        ]
    )
    for class_line in (
        _class_line(done_ids, "done"),
        _class_line(pending_ids, "pending"),
        _class_line(blocked_ids, "blocked"),
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
    lines = [
        "flowchart LR",
        f"  %% FlowPilot realtime route sign. Source: route={active_route}, version={route_version}, node={active_node or 'unknown'}",
    ]
    for key, label in FALLBACK_STAGES:
        detail = ""
        if key == current_stage:
            detail = f"<br/>Now: {_escape_label(str(active_node or 'unknown node'))}"
        lines.append(f'  {key}["{_escape_label(label)}{detail}"]')

    lines.extend(
        [
            "  intake --> product",
            "  product --> modeling",
            "  modeling --> route",
            "  route --> execution",
            "  execution --> verification",
            "  verification --> completion",
            '  verification -- "needs change" --> repair',
            "  repair --> modeling",
        ]
    )
    if return_path["required"]:
        lines.append(f'  verification -- "returns for repair" --> {current_stage if current_stage != "completion" else "repair"}')
    lines.extend(
        [
            "",
            "  classDef active fill:#e6fbff,stroke:#00bcd4,stroke-width:3px,color:#0f172a;",
            "  classDef normal fill:#f8fafc,stroke:#cbd5e1,color:#334155;",
            "  classDef repair fill:#fff7ed,stroke:#fb923c,color:#7c2d12;",
            "  class intake,product,modeling,route,execution,verification,completion normal;",
            "  class repair repair;",
            f"  class {current_stage if current_stage in ALLOWED_STAGES else 'route'} active;",
        ]
    )
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
    return_path = detect_return_path(
        frontier=frontier,
        route_nodes=nodes,
        active_node=str(active_node) if active_node else None,
        trigger=trigger,
    )
    if _use_route_node_layout(nodes):
        source = _build_route_node_mermaid(
            frontier=frontier,
            route=route,
            nodes=nodes,
            active_node=str(active_node) if active_node else None,
            return_path=return_path,
        )
        layout = "route_nodes"
    else:
        source = _build_stage_mermaid(
            frontier=frontier,
            route=route,
            current_stage=current_stage,
            active_node=str(active_node) if active_node else None,
            return_path=return_path,
        )
        layout = "stage_summary"
    return source, {**return_path, "layout": layout}


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
    source_status: str,
    source_findings: list[str],
) -> str:
    gate_text = (
        "Chat Mermaid is required because Cockpit UI is not open."
        if chat_display_required
        else "Cockpit UI may display this same Mermaid source."
    )
    repair_text = "none"
    if return_path["required"]:
        repair_text = f"{return_path.get('return_source') or 'review gate'} returns to {return_path.get('repair_target') or active_node or 'current node'}"
    source_text = source_status
    if source_findings:
        source_text = f"{source_status}: {'; '.join(source_findings)}"
    return "\n".join(
        [
            "# FlowPilot Route Sign",
            "",
            f"- Trigger: `{trigger}`",
            f"- Source status: `{source_text}`",
            f"- Current route: `{active_route or 'unknown'}`",
            f"- Current node: `{active_node or 'unknown'}`",
            f"- Current stage: `{current_stage}`",
            f"- Display gate: {gate_text}",
            "- Chat evidence: mark displayed only after this exact Mermaid block appears in the assistant message.",
            f"- Return/repair: `{repair_text}`",
            f"- Generated at: `{generated_at}`",
            "",
            "```mermaid",
            source,
            "```",
            "",
        ]
    )


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
    if active_node and active_node not in mermaid:
        findings.append("The Mermaid source does not include the active node.")
    if not chat_displayed and not ui_displayed:
        findings.append("No visible display surface was confirmed.")
    return {
        "schema_version": "flowpilot.user_flow_diagram.review.v1",
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reviewer_role": "human_like_reviewer",
        "status": "pass" if not findings else "blocked",
        "checked_chat_display": chat_displayed,
        "checked_cockpit_ui_display": ui_displayed,
        "checked_active_route_node_match": active_node in mermaid if active_node else False,
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
    else:
        frontier = {}
        state = {}
    active_route = _active_route(frontier, state)
    route_path = Path(paths["routes_root"]) / str(active_route or "route-001") / "flow.json"
    route = _load_json(route_path) if source_health["status"] == "ok" else {}
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
        source_status=source_health["status"],
        source_findings=source_health["findings"],
    )
    mermaid_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

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
        "same_graph_for_chat_and_ui": True,
        "simplified_flowpilot_english_mermaid": True,
        "raw_flowguard_mermaid": {
            "enabled": False,
            "satisfies_user_route_sign_gate": False,
        },
        "stage_count_target": "6-8",
        "layout": route_sign["layout"],
        "current_stage": current_stage,
        "active_route": active_route,
        "active_node": active_node,
        "route_version_rendered": frontier.get("route_version") or route.get("route_version"),
        "frontier_version_rendered": frontier.get("frontier_version"),
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
        "route_sign_layout": route_sign["layout"],
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
