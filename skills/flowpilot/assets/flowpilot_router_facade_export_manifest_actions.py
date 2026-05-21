"""Compatibility view for action-domain router facade exports."""

from __future__ import annotations

from flowpilot_router_facade_export_registry import ExportSpec, OWNER_EXPORTS_ACTIONS, RegistryKey


def owner_exports_actions() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_ACTIONS

__all__ = ["OWNER_EXPORTS_ACTIONS", "owner_exports_actions"]
