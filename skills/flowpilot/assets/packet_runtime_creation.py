"""Compatibility facade for packet creation, startup intake, and body handoff helpers."""

from __future__ import annotations

from packet_runtime_creation_core import create_packet
from packet_runtime_creation_handoff import (
    build_controller_handoff,
    controller_handoff_text,
    read_packet_body_for_role,
)
from packet_runtime_creation_startup import (
    create_user_intake_packet,
    router_release_startup_user_intake,
)

__all__ = [
    "router_release_startup_user_intake",
    "create_packet",
    "create_user_intake_packet",
    "build_controller_handoff",
    "controller_handoff_text",
    "read_packet_body_for_role",
]
