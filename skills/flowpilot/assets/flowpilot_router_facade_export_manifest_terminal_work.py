"""public view for terminal/work router facade exports."""

from __future__ import annotations

from flowpilot_router_facade_export_registry import ExportSpec, OWNER_EXPORTS_TERMINAL_WORK, RegistryKey


def owner_exports_terminal_work() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_TERMINAL_WORK

__all__ = ["OWNER_EXPORTS_TERMINAL_WORK", "owner_exports_terminal_work"]
