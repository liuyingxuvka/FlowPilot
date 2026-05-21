"""Compatibility view for controller-domain router facade exports."""

from __future__ import annotations

from flowpilot_router_facade_export_registry import ExportSpec, OWNER_EXPORTS_CONTROLLER, RegistryKey


def owner_exports_controller() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_CONTROLLER

__all__ = ["OWNER_EXPORTS_CONTROLLER", "owner_exports_controller"]
