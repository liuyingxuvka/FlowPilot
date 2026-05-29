"""Canonical router facade export registry.

The row data lives in ``runtime_kit/router_facade_owner_exports.json`` so the
Python surface stays small. ``flowpilot_router_facade_export_manifest*`` modules
import these constants as public views.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeAlias

ExportSpec: TypeAlias = tuple[str, str]
RegistryKey: TypeAlias = tuple[str, bool, bool]

_REGISTRY_DATA_PATH = Path(__file__).resolve().parent / "runtime_kit" / "router_facade_owner_exports.json"
_CONTROLLER_DOMAINS = (
    "controller_repair",
    "controller_scheduler",
    "controller_events",
    "controller_lifecycle",
)
_ROOT_DOMAINS = ("actions", "controller", "route", "startup", "terminal_work")


def _load_payload(path: Path = _REGISTRY_DATA_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported router facade export registry schema: {payload.get('schema_version')!r}")
    return payload


def _decode_domain(rows: list[dict[str, Any]]) -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    decoded: dict[RegistryKey, tuple[ExportSpec, ...]] = {}
    for row in rows:
        key = (str(row["module"]), bool(row["bind_router"]), bool(row["inject_router"]))
        decoded[key] = tuple(
            (str(item["public"]), str(item["target"]))
            for item in row.get("exports", ())
        )
    return decoded


def _merge_domains(*domains: dict[RegistryKey, tuple[ExportSpec, ...]]) -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    merged: dict[RegistryKey, tuple[ExportSpec, ...]] = {}
    for domain in domains:
        merged.update(domain)
    return merged


def _load_domain_owner_exports() -> dict[str, dict[RegistryKey, tuple[ExportSpec, ...]]]:
    payload = _load_payload()
    raw_domains = payload.get("domains", {})
    domains = {
        str(domain): _decode_domain(rows)
        for domain, rows in raw_domains.items()
    }
    domains["controller"] = _merge_domains(*(domains[name] for name in _CONTROLLER_DOMAINS))
    return domains


DOMAIN_OWNER_EXPORTS = _load_domain_owner_exports()

OWNER_EXPORTS_ACTIONS = DOMAIN_OWNER_EXPORTS["actions"]
OWNER_EXPORTS_CONTROLLER_REPAIR = DOMAIN_OWNER_EXPORTS["controller_repair"]
OWNER_EXPORTS_CONTROLLER_SCHEDULER = DOMAIN_OWNER_EXPORTS["controller_scheduler"]
OWNER_EXPORTS_CONTROLLER_EVENTS = DOMAIN_OWNER_EXPORTS["controller_events"]
OWNER_EXPORTS_CONTROLLER_LIFECYCLE = DOMAIN_OWNER_EXPORTS["controller_lifecycle"]
OWNER_EXPORTS_CONTROLLER = DOMAIN_OWNER_EXPORTS["controller"]
OWNER_EXPORTS_ROUTE = DOMAIN_OWNER_EXPORTS["route"]
OWNER_EXPORTS_STARTUP = DOMAIN_OWNER_EXPORTS["startup"]
OWNER_EXPORTS_TERMINAL_WORK = DOMAIN_OWNER_EXPORTS["terminal_work"]
OWNER_EXPORTS = _merge_domains(*(DOMAIN_OWNER_EXPORTS[name] for name in _ROOT_DOMAINS))

PUBLIC_EXPORT_NAMES = frozenset(
    public_name
    for exports in OWNER_EXPORTS.values()
    for public_name, _target_name in exports
)


def owner_exports_actions() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_ACTIONS


def owner_exports_controller() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_CONTROLLER


def owner_exports_route() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_ROUTE


def owner_exports_startup() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_STARTUP


def owner_exports_terminal_work() -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return OWNER_EXPORTS_TERMINAL_WORK


def owner_exports_for_domain(domain: str) -> dict[RegistryKey, tuple[ExportSpec, ...]]:
    return DOMAIN_OWNER_EXPORTS[domain]


__all__ = [
    "ExportSpec",
    "RegistryKey",
    "OWNER_EXPORTS",
    "PUBLIC_EXPORT_NAMES",
    "OWNER_EXPORTS_ACTIONS",
    "OWNER_EXPORTS_CONTROLLER",
    "OWNER_EXPORTS_CONTROLLER_REPAIR",
    "OWNER_EXPORTS_CONTROLLER_SCHEDULER",
    "OWNER_EXPORTS_CONTROLLER_EVENTS",
    "OWNER_EXPORTS_CONTROLLER_LIFECYCLE",
    "OWNER_EXPORTS_ROUTE",
    "OWNER_EXPORTS_STARTUP",
    "OWNER_EXPORTS_TERMINAL_WORK",
    "DOMAIN_OWNER_EXPORTS",
    "owner_exports_actions",
    "owner_exports_controller",
    "owner_exports_route",
    "owner_exports_startup",
    "owner_exports_terminal_work",
    "owner_exports_for_domain",
]
