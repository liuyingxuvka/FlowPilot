"""Derived material artifact map helpers for FlowPilot runs.

The map is an index, not authority. It records safe metadata, source paths,
hashes, status, and access boundaries for artifacts that already exist under a
run. It never reads sealed packet or result bodies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import packet_runtime


MATERIAL_ARTIFACT_MAP_SCHEMA = "flowpilot.material_artifact_map.v1"
MATERIAL_ARTIFACT_MAP_FILENAME = "material_artifact_map.json"


def material_artifact_map_path(run_root: Path) -> Path:
    return run_root / "material" / MATERIAL_ARTIFACT_MAP_FILENAME


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = packet_runtime.read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _rel(project_root: Path, path: Path) -> str:
    return packet_runtime.project_relative(project_root, path)


def _safe_source_ref(project_root: Path, path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return {
        "path": _rel(project_root, path),
        "hash": packet_runtime.sha256_file(path),
        "hash_algorithm": "sha256",
    }


def _sealed_body_ref(path: str | None, body_hash: str | None, *, visibility: str) -> dict[str, Any] | None:
    if not path:
        return None
    ref: dict[str, Any] = {
        "path": str(path),
        "hash": str(body_hash or ""),
        "hash_algorithm": "sha256" if body_hash else None,
        "visibility": visibility,
        "requires_runtime_open": True,
        "ordinary_file_read_allowed": False,
    }
    return ref


def _entry(
    *,
    entry_id: str,
    kind: str,
    producer_role: str,
    owner_role: str,
    status: str,
    authority_level: str,
    safe_summary: str,
    source_refs: list[dict[str, Any]] | None = None,
    envelope_refs: list[dict[str, Any]] | None = None,
    body_refs: list[dict[str, Any]] | None = None,
    allowed_role_reads: list[str] | None = None,
    related_entries: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body_refs = [ref for ref in (body_refs or []) if ref]
    return {
        "entry_id": entry_id,
        "kind": kind,
        "producer_role": producer_role,
        "owner_role": owner_role,
        "status": status,
        "authority_level": authority_level,
        "safe_summary": safe_summary,
        "source_refs": source_refs or [],
        "source_paths": [ref["path"] for ref in source_refs or [] if ref.get("path")],
        "envelope_refs": envelope_refs or [],
        "body_refs": body_refs,
        "body_text_included": False,
        "sealed_body_boundary_preserved": True,
        "requires_runtime_open": any(bool(ref.get("requires_runtime_open")) for ref in body_refs),
        "allowed_role_reads": allowed_role_reads or ["project_manager", "human_like_reviewer", "worker_a", "worker_b"],
        "related_entries": related_entries or [],
        "metadata": metadata or {},
    }


def _status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _entry_for_artifact(
    project_root: Path,
    path: Path,
    *,
    entry_id: str,
    kind: str,
    producer_role: str,
    owner_role: str,
    authority_level: str,
    safe_summary: str,
    status: str = "current",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    source_ref = _safe_source_ref(project_root, path)
    if source_ref is None:
        return None
    return _entry(
        entry_id=entry_id,
        kind=kind,
        producer_role=producer_role,
        owner_role=owner_role,
        status=status,
        authority_level=authority_level,
        safe_summary=safe_summary,
        source_refs=[source_ref],
        metadata=metadata,
    )


def _artifact_status(kind: str, data: dict[str, Any]) -> str:
    if kind == "material_sufficiency_report":
        if data.get("sufficient") is True and data.get("pm_ready") is True:
            return "current"
        return "blocked"
    if kind == "pm_package_result_disposition":
        decision = str(data.get("decision") or "")
        return "current" if decision == "absorbed" else (decision or "blocked")
    if kind == "pm_material_understanding":
        return "accepted"
    return "current"


def _add_packet_index_entries(
    project_root: Path,
    run_root: Path,
    entries: list[dict[str, Any]],
    *,
    index_path: Path,
    batch_kind: str,
) -> None:
    index = _read_json(index_path)
    if not index:
        return
    index_ref = _safe_source_ref(project_root, index_path)
    packet_records = [item for item in index.get("packets") or [] if isinstance(item, dict)]
    packet_ids = [str(item.get("packet_id")) for item in packet_records if item.get("packet_id")]
    if index_ref is not None:
        entries.append(
            _entry(
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
        packet_ref = _safe_source_ref(project_root, packet_path) if packet_path else None
        envelope = _read_json(packet_path) if packet_path else {}
        body_ref = _sealed_body_ref(
            str(record.get("packet_body_path") or record.get("body_path") or envelope.get("body_path") or ""),
            str(record.get("packet_body_hash") or record.get("body_hash") or envelope.get("body_hash") or ""),
            visibility=str(envelope.get("body_visibility") or "sealed_target_role_only"),
        )
        if packet_ref is not None:
            entries.append(
                _entry(
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
        result_ref = _safe_source_ref(project_root, result_path)
        result = _read_json(result_path)
        body_ref = _sealed_body_ref(
            str(result.get("result_body_path") or ""),
            str(result.get("result_body_hash") or ""),
            visibility=str(result.get("body_visibility") or "sealed_target_role_only"),
        )
        if result_ref is not None:
            entries.append(
                _entry(
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
                    allowed_role_reads=["project_manager", "human_like_reviewer"],
                    related_entries=[f"{batch_kind}:packet:{packet_id}"],
                    metadata={
                        "packet_id": packet_id,
                        "contract_self_check": result.get("contract_self_check") if isinstance(result.get("contract_self_check"), dict) else {},
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

    artifact_specs = (
        (
            "material:pm_result_disposition",
            "pm_package_result_disposition",
            run_root / "material" / "pm_material_scan_result_disposition.json",
            "project_manager",
            "project_manager",
            "pm_decision_support",
            "PM disposition for material scan result package.",
        ),
        (
            "material:pm_formal_gate_package",
            "pm_formal_gate_package",
            run_root / "material" / "pm_material_scan_formal_gate_package.json",
            "project_manager",
            "human_like_reviewer",
            "reviewable_evidence",
            "PM formal material gate package for reviewer.",
        ),
        (
            "material:reviewer_sufficiency",
            "material_sufficiency_report",
            run_root / "material" / "material_sufficiency_report.json",
            "human_like_reviewer",
            "project_manager",
            "reviewable_evidence",
            "Reviewer material sufficiency report.",
        ),
        (
            "material:pm_understanding",
            "pm_material_understanding",
            run_root / "pm_material_understanding.json",
            "project_manager",
            "project_manager",
            "accepted_material_basis",
            "PM material understanding memo.",
        ),
        (
            "research:package",
            "research_package",
            run_root / "research" / "research_package.json",
            "project_manager",
            "project_manager",
            "pm_decision_support",
            "PM research package.",
        ),
        (
            "research:capability_decision",
            "research_capability_decision",
            run_root / "research" / "research_capability_decision.json",
            "project_manager",
            "project_manager",
            "pm_decision_support",
            "PM research capability decision.",
        ),
        (
            "research:worker_report",
            "research_worker_report",
            run_root / "research" / "worker_research_report.json",
            "worker",
            "project_manager",
            "pm_decision_support",
            "Worker research report metadata.",
        ),
        (
            "research:reviewer_report",
            "research_reviewer_report",
            run_root / "research" / "research_reviewer_report.json",
            "human_like_reviewer",
            "project_manager",
            "reviewable_evidence",
            "Reviewer research direct-source report.",
        ),
        (
            "research:pm_absorption",
            "pm_research_absorption",
            run_root / "research" / "pm_research_absorption.json",
            "project_manager",
            "project_manager",
            "accepted_material_basis",
            "PM research absorption record.",
        ),
        (
            "self_interrogation:index",
            "self_interrogation_index",
            run_root / "self_interrogation_index.json",
            "project_manager",
            "project_manager",
            "pm_decision_support",
            "Self-interrogation index.",
        ),
        (
            "generated_resources:ledger",
            "generated_resource_ledger",
            run_root / "generated_resource_ledger.json",
            "project_manager",
            "project_manager",
            "generated_resource_lineage",
            "Generated resource ledger.",
        ),
    )
    for entry_id, kind, path, producer, owner, authority, summary in artifact_specs:
        data = _read_json(path)
        entry = _entry_for_artifact(
            project_root,
            path,
            entry_id=entry_id,
            kind=kind,
            producer_role=producer,
            owner_role=owner,
            authority_level=authority,
            safe_summary=summary,
            status=_artifact_status(kind, data),
            metadata={
                "decision": data.get("decision"),
                "sufficient": data.get("sufficient"),
                "pm_ready": data.get("pm_ready"),
            },
        )
        if entry is not None:
            entries.append(entry)

    entries = sorted(entries, key=lambda item: str(item.get("entry_id")))
    counts = _status_counts(entries)
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
    return _read_json(material_artifact_map_path(run_root))


def material_artifact_map_source_ref(project_root: Path, run_root: Path) -> dict[str, Any] | None:
    return _safe_source_ref(project_root, material_artifact_map_path(run_root))


def material_artifact_map_summary(doc: dict[str, Any]) -> dict[str, Any]:
    entries = [item for item in doc.get("entries") or [] if isinstance(item, dict)]
    status_counts = _status_counts(entries)
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
