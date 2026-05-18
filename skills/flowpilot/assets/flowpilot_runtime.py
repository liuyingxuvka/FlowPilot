"""Unified FlowPilot CLI for card, packet, and role-output runtimes."""

from __future__ import annotations

import flowpilot_runtime_args as _runtime_args
import flowpilot_runtime_commands as _runtime_commands
from flowpilot_runtime_args import *
from flowpilot_runtime_commands import *

card_runtime = _runtime_commands.card_runtime
flowpilot_router = _runtime_commands.flowpilot_router
packet_runtime = _runtime_commands.packet_runtime
role_output_runtime = _runtime_commands.role_output_runtime

ROLE_OUTPUT_RUNTIME_COMMANDS = ("progress-output", "submit-output-to-router")

__all__ = (*_runtime_args.__all__, *_runtime_commands.__all__)


def main(argv: list[str] | None = None) -> int:
    _runtime_commands.card_runtime = card_runtime
    _runtime_commands.flowpilot_router = flowpilot_router
    _runtime_commands.packet_runtime = packet_runtime
    _runtime_commands.role_output_runtime = role_output_runtime
    return _runtime_commands.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
