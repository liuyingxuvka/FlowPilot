"""Derived material artifact map helpers for FlowPilot runs.

The map is an index, not authority. It records safe metadata, source paths,
hashes, status, and access boundaries for artifacts that already exist under a
run. It never reads sealed packet or result bodies. Ordinary non-sealed
project/run files remain readable to PM, Worker, FlowGuard operator, and
Reviewer even when they are absent from this index.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import flowpilot_material_artifact_map_entries as entry_policy
import flowpilot_material_artifact_map_ordinary as ordinary_entries
import flowpilot_material_artifact_map_packets as packet_entries
import packet_runtime


MATERIAL_ARTIFACT_MAP_SCHEMA = "flowpilot.material_artifact_map.v1"
MATERIAL_ARTIFACT_MAP_FILENAME = "material_artifact_map.json"


def material_artifact_map_path(run_root: Path) -> Path:
    return run_root / "material" / MATERIAL_ARTIFACT_MAP_FILENAME


def refresh_material_artifact_map(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = str((run_state or {}).get("run_id") or run_root.name)
    entries: list[dict[str, Any]] = []

    packet_entries.add_packet_index_entries(
        project_root,
        entries,
        index_path=run_root / "material" / "material_scan_packets.json",
        batch_kind="material_scan",
    )
    packet_entries.add_packet_index_entries(
        project_root,
        entries,
        index_path=run_root / "research" / "research_packet.json",
        batch_kind="research",
    )

    entries.extend(entry_policy.static_artifact_entries(project_root, run_root))
    ordinary_entries.add_ordinary_work_artifact_entries(
        project_root,
        run_root,
        entries,
        material_artifact_map_filename=MATERIAL_ARTIFACT_MAP_FILENAME,
    )

    entries = sorted(entries, key=lambda item: str(item.get("entry_id")))
    counts = entry_policy.status_counts(entries)
    doc = {
        "schema_version": MATERIAL_ARTIFACT_MAP_SCHEMA,
        "run_id": run_id,
        "generated_by": "router",
        "controller_decision_authority": False,
        "controller_may_read_sealed_bodies": False,
        "sealed_packet_or_result_bodies_read": False,
        "body_text_excluded": True,
        "authority_boundary": (
            "navigation_index_only_ordinary_non_sealed_project_run_material_is_readable_by_pm_worker_"
            "flowguard_operator_reviewer_sealed_bodies_require_runtime_open"
        ),
        "ordinary_material_policy": {
            "map_is_allowlist": False,
            "ordinary_non_sealed_project_run_files_readable": True,
            "controller_may_read_ordinary_material_for_decision": False,
            "roles_with_ordinary_read_access": list(entry_policy.ORDINARY_WORK_MATERIAL_ROLES),
            "sealed_body_text_requires_runtime_open": True,
        },
        "entry_count": len(entries),
        "status_counts": counts,
        "blocked_count": counts.get("blocked", 0),
        "stale_count": counts.get("stale", 0),
        "unresolved_count": counts.get("unresolved", 0),
        "entries": entries,
        "written_at": packet_runtime.utc_now(),
    }
    path = material_artifact_map_path(run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    packet_runtime.write_json_atomic(path, doc)
    return doc


def read_material_artifact_map(run_root: Path) -> dict[str, Any]:
    return entry_policy.read_json_document(material_artifact_map_path(run_root))


def material_artifact_map_source_ref(project_root: Path, run_root: Path) -> dict[str, Any] | None:
    return entry_policy.safe_source_ref(project_root, material_artifact_map_path(run_root))


def material_artifact_map_summary(doc: dict[str, Any]) -> dict[str, Any]:
    entries = [item for item in doc.get("entries") or [] if isinstance(item, dict)]
    status_counts = entry_policy.status_counts(entries)
    return {
        "schema_version": doc.get("schema_version"),
        "entry_count": len(entries),
        "status_counts": status_counts,
        "blocked_count": status_counts.get("blocked", 0),
        "stale_count": status_counts.get("stale", 0),
        "unresolved_count": status_counts.get("unresolved", 0),
        "body_text_excluded": doc.get("body_text_excluded") is True,
        "controller_decision_authority": bool(doc.get("controller_decision_authority")),
    }


def review_source_entry_ids(doc: dict[str, Any], *, batch_kind: str) -> list[str]:
    prefixes = {
        "material_scan": ("material_scan:", "material:"),
        "research": ("research:",),
        "current_node": ("current_node:",),
    }.get(batch_kind, (f"{batch_kind}:",))
    return [
        str(entry.get("entry_id"))
        for entry in doc.get("entries") or []
        if isinstance(entry, dict)
        and any(str(entry.get("entry_id") or "").startswith(prefix) for prefix in prefixes)
    ]


def reviewable_source_paths(doc: dict[str, Any], *, entry_ids: list[str]) -> list[str]:
    wanted = set(entry_ids)
    paths: list[str] = []
    for entry in doc.get("entries") or []:
        if not isinstance(entry, dict) or str(entry.get("entry_id")) not in wanted:
            continue
        for path in entry.get("source_paths") or []:
            if isinstance(path, str) and path not in paths:
                paths.append(path)
        for ref in entry.get("envelope_refs") or []:
            path = ref.get("path") if isinstance(ref, dict) else None
            if isinstance(path, str) and path not in paths:
                paths.append(path)
    return paths


__all__ = [
    "MATERIAL_ARTIFACT_MAP_FILENAME",
    "MATERIAL_ARTIFACT_MAP_SCHEMA",
    "material_artifact_map_path",
    "material_artifact_map_source_ref",
    "material_artifact_map_summary",
    "read_material_artifact_map",
    "refresh_material_artifact_map",
    "review_source_entry_ids",
    "reviewable_source_paths",
]
