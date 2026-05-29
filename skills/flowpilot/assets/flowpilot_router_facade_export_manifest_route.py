"""public view for route-domain router facade exports."""

from __future__ import annotations

from flowpilot_router_facade_export_registry import ExportSpec, OWNER_EXPORTS_ROUTE, RegistryKey


def owner_exports_route() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_ROUTE

__all__ = ["OWNER_EXPORTS_ROUTE", "owner_exports_route"]
