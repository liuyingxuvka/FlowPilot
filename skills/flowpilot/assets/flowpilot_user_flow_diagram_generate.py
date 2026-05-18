"""FlowPilot route sign generation implementation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths
from flowpilot_user_flow_markdown import build_chat_markdown
from flowpilot_user_flow_mermaid import build_mermaid
from flowpilot_user_flow_source import (
    _load_json,
    _load_route_source,
    _review_display,
    _route_source_summary,
    _write_json,
)
from flowpilot_user_flow_stage import DISPLAY_TRIGGERS, classify_current_stage
from flowpilot_user_flow_tree import _active_node, _active_route, _snapshot_route


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


__all__ = ("generate",)
