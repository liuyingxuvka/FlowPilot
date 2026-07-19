"""Command-line entrypoint for FlowPilot route sign generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowpilot_user_flow_diagram_generate import generate
from flowpilot_user_flow_stage import DISPLAY_TRIGGERS
from flowpilot_user_flow_tree import _truthy


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
        "--show-superseded-history",
        action="store_true",
        help=(
            "Show runtime-identity-bound superseded repair history. "
            "Omit this option to return to the default current-only view."
        ),
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
        include_superseded_history=_truthy(args.show_superseded_history),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.markdown:
        print(payload["markdown"])
    else:
        print(payload["mermaid"])
    return 0 if payload["ok"] else 2


__all__ = ("main",)
