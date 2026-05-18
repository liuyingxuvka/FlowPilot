"""Router facade controller export manifest aggregation shard.

The parent preserves the public OWNER_EXPORTS_CONTROLLER contract while child
modules own declarative registry rows by controller domain.
"""

from __future__ import annotations

from typing import TypeAlias

from flowpilot_router_facade_export_manifest_controller_events import OWNER_EXPORTS_CONTROLLER_EVENTS
from flowpilot_router_facade_export_manifest_controller_lifecycle import OWNER_EXPORTS_CONTROLLER_LIFECYCLE
from flowpilot_router_facade_export_manifest_controller_repair import OWNER_EXPORTS_CONTROLLER_REPAIR
from flowpilot_router_facade_export_manifest_controller_scheduler import OWNER_EXPORTS_CONTROLLER_SCHEDULER

ExportSpec: TypeAlias = tuple[str, str]
RegistryKey: TypeAlias = tuple[str, bool, bool]

OWNER_EXPORTS_CONTROLLER: dict[RegistryKey, tuple[ExportSpec, ...]] = {
    **OWNER_EXPORTS_CONTROLLER_REPAIR,
    **OWNER_EXPORTS_CONTROLLER_SCHEDULER,
    **OWNER_EXPORTS_CONTROLLER_EVENTS,
    **OWNER_EXPORTS_CONTROLLER_LIFECYCLE,
}


def owner_exports_controller() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_CONTROLLER


__all__ = ["OWNER_EXPORTS_CONTROLLER", "owner_exports_controller"]
