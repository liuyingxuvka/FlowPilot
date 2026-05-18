"""Generate FlowPilot's realtime user-facing route sign.

The route sign is the simplified Mermaid diagram shown to users in chat and in
Cockpit UI. It is not a raw FlowGuard state graph and it is not the execution
source of truth; route and frontier JSON remain authoritative.
"""

from __future__ import annotations

import flowpilot_user_flow_markdown as _markdown
import flowpilot_user_flow_mermaid as _mermaid
import flowpilot_user_flow_source as _source
import flowpilot_user_flow_stage as _stage
import flowpilot_user_flow_tree as _tree
from flowpilot_user_flow_diagram_cli import main
from flowpilot_user_flow_diagram_generate import generate
from flowpilot_user_flow_markdown import build_chat_markdown
from flowpilot_user_flow_mermaid import build_mermaid, detect_return_path
from flowpilot_user_flow_source import (
    _load_json,
    _load_route_source,
    _review_display,
    _route_source_candidates,
    _route_source_summary,
    _write_json,
)
from flowpilot_user_flow_stage import DISPLAY_TRIGGERS, classify_current_stage
from flowpilot_user_flow_tree import _active_node, _active_route, _truthy


for _owner_module in (_tree, _stage, _mermaid, _markdown, _source):
    for _name in dir(_owner_module):
        if not _name.startswith("__"):
            globals().setdefault(_name, getattr(_owner_module, _name))


__all__ = (
    "generate",
    "main",
)


if __name__ == "__main__":
    raise SystemExit(main())
