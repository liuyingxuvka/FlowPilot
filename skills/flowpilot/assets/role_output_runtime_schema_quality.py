"""Quality-pack declaration helpers for role-output schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from role_output_runtime_schema_io import _project_relative, _read_json
from role_output_runtime_schema_payload import _choose_placeholder
from role_output_runtime_schema_specs import (
    ATTACHED_QUALITY_PACK_REL_PATHS,
    QUALITY_PACK_CATALOG_PATH,
    QUALITY_PACK_STATUS_VALUES,
    RoleOutputRuntimeError,
)


def _quality_pack_catalog_path(project_root: Path) -> Path:
    return project_root.resolve() / QUALITY_PACK_CATALOG_PATH


def load_quality_pack_catalog(project_root: Path) -> dict[str, Any]:
    path = _quality_pack_catalog_path(project_root)
    if not path.exists():
        return {"schema_version": "flowpilot.quality_pack_catalog.v1", "quality_packs": []}
    return _read_json(path)


def _catalog_quality_pack_ids(project_root: Path) -> set[str]:
    catalog = load_quality_pack_catalog(project_root)
    packs = catalog.get("quality_packs")
    if not isinstance(packs, list):
        return set()
    return {str(item.get("pack_id")) for item in packs if isinstance(item, dict) and item.get("pack_id")}


def _pack_ids_from_payload(payload: Any) -> list[str]:
    raw: Any = payload
    if isinstance(payload, dict):
        for key in ("quality_packs", "attached_quality_packs", "route_quality_packs"):
            if key in payload:
                raw = payload[key]
                break
    if not isinstance(raw, list):
        return []
    pack_ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            pack_id = item.strip()
        elif isinstance(item, dict):
            pack_id = str(item.get("pack_id") or item.get("id") or "").strip()
        else:
            pack_id = ""
        if pack_id and pack_id not in pack_ids:
            pack_ids.append(pack_id)
    return pack_ids


def quality_pack_checks_for_run(project_root: Path, run_root: Path) -> list[dict[str, Any]]:
    """Return generic quality-pack check rows required by the current run.

    The runtime treats quality packs as data. It checks that declared pack IDs
    are answered and evidence references are well-formed; it does not encode
    UI, desktop, localization, or product-quality semantics.
    """

    pack_ids: list[str] = []
    for rel_path in ATTACHED_QUALITY_PACK_REL_PATHS:
        path = run_root / rel_path
        if path.exists():
            try:
                pack_ids.extend(_pack_ids_from_payload(_read_json(path)))
            except (OSError, json.JSONDecodeError, RoleOutputRuntimeError):
                raise RoleOutputRuntimeError(f"quality pack declaration is invalid: {_project_relative(project_root, path)}")
    unique = []
    for pack_id in pack_ids:
        if pack_id not in unique:
            unique.append(pack_id)
    return [
        {
            "pack_id": pack_id,
            "status": _choose_placeholder(f"quality_pack_checks.{pack_id}.status", list(QUALITY_PACK_STATUS_VALUES)),
            "evidence_refs": [],
            "blockers": [],
            "waivers": [],
            "detail_path": None,
        }
        for pack_id in unique
    ]
