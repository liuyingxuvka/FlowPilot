"""public view for startup-domain router facade exports."""

from __future__ import annotations

from flowpilot_router_facade_export_registry import ExportSpec, OWNER_EXPORTS_STARTUP, RegistryKey


def owner_exports_startup() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_STARTUP

__all__ = ["OWNER_EXPORTS_STARTUP", "owner_exports_startup"]
