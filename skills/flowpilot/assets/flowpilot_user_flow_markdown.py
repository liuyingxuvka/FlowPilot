"""Markdown rendering for FlowPilot's user route sign."""

from __future__ import annotations

from typing import Any


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
    replacement_history: dict[str, Any] | None = None,
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
    history = replacement_history or {}
    if history.get("history_available"):
        if history.get("rendered_visible"):
            lines.extend(
                [
                    "Repair history: shown as history-only context; the active replacement remains current authority. Use “Hide repair history” to return to the current-only view.",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "Repair history: available on demand. Use “Show repair history” to reveal it; current work remains replacement-only.",
                    "",
                ]
            )
    elif history.get("requested_visible") and history.get("producer_identity_status") == "incomplete":
        lines.extend(
            [
                "Repair history: unavailable because the current route source does not provide complete replacement identity.",
                "",
            ]
        )
    return "\n".join(lines)
