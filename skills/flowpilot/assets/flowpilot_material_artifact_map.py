"""Derived material artifact map helpers for FlowPilot runs.

The map is an index, not authority. It records safe metadata, source paths,
hashes, status, and access boundaries for artifacts that already exist under a
run. It never reads sealed packet or result bodies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import flowpilot_material_artifact_map_entries as entry_policy
import packet_runtime


MATERIAL_ARTIFACT_MAP_SCHEMA = "flowpilot.material_artifact_map.v1"
MATERIAL_ARTIFACT_MAP_FILENAME = "material_artifact_map.json"


def _runtime_open_roles(result: dict[str, Any]) -> list[str]:
    roles: list[str] = []

    def add_role(value: Any) -> None:
        role = str(value or "")
        if role and role not in roles:
            roles.append(role)

    add_role(result.get("next_recipient"))
    return roles


def material_artifact_map_path(run_root: Path) -> Path:
    return run_root / "material" / MATERIAL_ARTIFACT_MAP_FILENAME


def _add_packet_index_entries(
    project_root: Path,
    run_root: Path,
    entries: list[dict[str, Any]],
    *,
    index_path: Path,
    batch_kind: str,
) -> None:
    index = entry_policy.read_json_document(index_path)
    if not index:
        return
    index_ref = entry_policy.safe_source_ref(project_root, index_path)
    packet_records = [item for item in index.get("packets") or [] if isinstance(item, dict)]
    packet_ids = [str(item.get("packet_id")) for item in packet_records if item.get("packet_id")]
    if index_ref is not None:
        entries.append(
            entry_policy.make_entry(
                entry_id=f"{batch_kind}:packet_index",
                kind=f"{batch_kind}_packet_index",
                producer_role=str(index.get("written_by_role") or "project_manager"),
                owner_role="project_manager",
                status="current",
                authority_level="navigation_only",
                safe_summary=f"{batch_kind} packet index with {len(packet_records)} packet record(s).",
                source_refs=[index_ref],
                metadata={"batch_id": index.get("batch_id"), "packet_ids": packet_ids},
            )
        )
    for record in packet_records:
        packet_id = str(record.get("packet_id") or "")
        packet_rel = str(record.get("packet_envelope_path") or "")
        packet_path = packet_runtime.resolve_project_path(project_root, packet_rel) if packet_rel else None
        packet_ref = entry_policy.safe_source_ref(project_root, packet_path) if packet_path else None
        envelope = entry_policy.read_json_document(packet_path) if packet_path else {}
        body_ref = entry_policy.sealed_body_ref(
            str(record.get("packet_body_path") or record.get("body_path") or envelope.get("body_path") or ""),
            str(record.get("packet_body_hash") or record.get("body_hash") or envelope.get("body_hash") or ""),
            visibility=str(envelope.get("body_visibility") or "sealed_target_role_only"),
        )
        if packet_ref is not None:
            entries.append(
                entry_policy.make_entry(
                    entry_id=f"{batch_kind}:packet:{packet_id}",
                    kind=f"{batch_kind}_packet",
                    producer_role=str(envelope.get("from_role") or "project_manager"),
                    owner_role=str(envelope.get("to_role") or record.get("to_role") or "worker"),
                    status="current",
                    authority_level="navigation_only",
                    safe_summary=f"{batch_kind} packet envelope metadata for {packet_id}; body remains sealed.",
                    source_refs=[index_ref] if index_ref else [],
                    envelope_refs=[packet_ref],
                    body_refs=[body_ref] if body_ref else [],
                    allowed_role_reads=[str(envelope.get("to_role") or record.get("to_role") or "worker")],
                    metadata={"packet_id": packet_id, "batch_id": index.get("batch_id")},
                )
            )
        result_rel = str(record.get("result_envelope_path") or "")
        result_path = packet_runtime.resolve_project_path(project_root, result_rel) if result_rel else None
        if not result_path or not result_path.exists():
            continue
        result_ref = entry_policy.safe_source_ref(project_root, result_path)
        result = entry_policy.read_json_document(result_path)
        body_ref = entry_policy.sealed_body_ref(
            str(result.get("result_body_path") or ""),
            str(result.get("result_body_hash") or ""),
            visibility=str(result.get("body_visibility") or "sealed_target_role_only"),
        )
        if result_ref is not None:
            runtime_open_roles = _runtime_open_roles(result)
            entries.append(
                entry_policy.make_entry(
                    entry_id=f"{batch_kind}:result:{packet_id}",
                    kind=f"{batch_kind}_result_envelope",
                    producer_role=str(result.get("completed_by_role") or record.get("to_role") or "worker"),
                    owner_role=str(result.get("next_recipient") or "project_manager"),
                    status="current",
                    authority_level="runtime_open_required",
                    safe_summary=f"{batch_kind} result envelope metadata for {packet_id}; result body remains sealed.",
                    source_refs=[index_ref] if index_ref else [],
                    envelope_refs=[result_ref],
                    body_refs=[body_ref] if body_ref else [],
                    allowed_role_reads=runtime_open_roles,
                    related_entries=[f"{batch_kind}:packet:{packet_id}"],
                    metadata={
                        "packet_id": packet_id,
                        "contract_self_check": result.get("contract_self_check") if isinstance(result.get("contract_self_check"), dict) else {},
                        "runtime_open_roles": runtime_open_roles,
                        "reviewer_raw_body_access_runtime_backed": "human_like_reviewer" in runtime_open_roles,
                        "pm_formal_gate_package_is_reviewer_evidence_surface": True,
                    },
                )
            )


def refresh_material_artifact_map(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = str((run_state or {}).get("run_id") or run_root.name)
    entries: list[dict[str, Any]] = []

    _add_packet_index_entries(
        project_root,
        run_root,
        entries,
        index_path=run_root / "material" / "material_scan_packets.json",
        batch_kind="material_scan",
    )
    _add_packet_index_entries(
        project_root,
        run_root,
        entries,
        index_path=run_root / "research" / "research_packet.json",
        batch_kind="research",
    )

    entries.extend(entry_policy.static_artifact_entries(project_root, run_root))

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
        "authority_boundary": "index_only_existing_pm_reviewer_runtime_ledgers_remain_authoritative",
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
