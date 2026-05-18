"""Stage classification for FlowPilot's user route sign."""

from __future__ import annotations

from typing import Any

from flowpilot_user_flow_tree import _active_node, _all_route_nodes, _node_id, _normalize


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
