"""Aggregated router facade export manifest.

The registry is split into domain shards to keep the public facade export map
readable without changing the installer contract.
"""

from __future__ import annotations

from typing import TypeAlias

from flowpilot_router_facade_export_manifest_actions import OWNER_EXPORTS_ACTIONS
from flowpilot_router_facade_export_manifest_controller import OWNER_EXPORTS_CONTROLLER
from flowpilot_router_facade_export_manifest_route import OWNER_EXPORTS_ROUTE
from flowpilot_router_facade_export_manifest_startup import OWNER_EXPORTS_STARTUP
from flowpilot_router_facade_export_manifest_terminal_work import OWNER_EXPORTS_TERMINAL_WORK

ExportSpec: TypeAlias = tuple[str, str]
RegistryKey: TypeAlias = tuple[str, bool, bool]

OWNER_EXPORTS: dict[RegistryKey, tuple[ExportSpec, ...]] = {}
for _owner_exports in (
    OWNER_EXPORTS_ACTIONS,
    OWNER_EXPORTS_CONTROLLER,
    OWNER_EXPORTS_ROUTE,
    OWNER_EXPORTS_STARTUP,
    OWNER_EXPORTS_TERMINAL_WORK,
):
    OWNER_EXPORTS.update(_owner_exports)

PUBLIC_EXPORT_NAMES = frozenset(
    public_name
    for exports in OWNER_EXPORTS.values()
    for public_name, _target_name in exports
)

__all__ = ["ExportSpec", "RegistryKey", "OWNER_EXPORTS", "PUBLIC_EXPORT_NAMES"]
