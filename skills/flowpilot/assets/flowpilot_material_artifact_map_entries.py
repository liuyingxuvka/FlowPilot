"""Entry-policy helpers for FlowPilot material artifact maps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import packet_runtime

ORDINARY_WORK_MATERIAL_ROLES = [
    "project_manager",
    "worker",
    "flowguard_operator",
    "human_like_reviewer",
]


def read_json_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = packet_runtime.read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def safe_source_ref(project_root: Path, path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        source_path = path.relative_to(project_root).as_posix()
    except ValueError:
        source_path = packet_runtime.project_relative(project_root, path)
    return {
        "path": source_path,
        "hash": packet_runtime.sha256_file(path),
        "hash_algorithm": "sha256",
    }


def sealed_body_ref(path: str | None, body_hash: str | None, *, visibility: str) -> dict[str, Any] | None:
    if not path:
        return None
    return {
        "path": str(path),
        "hash": str(body_hash or ""),
        "hash_algorithm": "sha256" if body_hash else None,
        "visibility": visibility,
        "requires_runtime_open": True,
        "ordinary_file_read_allowed": False,
    }


def make_entry(
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
        "allowed_role_reads": allowed_role_reads or list(ORDINARY_WORK_MATERIAL_ROLES),
        "related_entries": related_entries or [],
        "metadata": metadata or {},
    }


def status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def entry_for_artifact(
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
    source_ref = safe_source_ref(project_root, path)
    if source_ref is None:
        return None
    return make_entry(
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


def artifact_status(kind: str, data: dict[str, Any]) -> str:
    declared_status = str(data.get("status") or "")
    if declared_status in {"blocked", "stale", "unresolved"}:
        return declared_status
    if kind == "pm_package_result_disposition":
        decision = str(data.get("decision") or "")
        return "current" if decision == "absorbed" else (decision or "blocked")
    return "current"


STATIC_ARTIFACT_SPECS = (
    (
        "research:package",
        "research_package",
        ("research", "research_package.json"),
        "project_manager",
        "project_manager",
        "pm_decision_support",
        "PM research package.",
    ),
    (
        "research:capability_decision",
        "research_capability_decision",
        ("research", "research_capability_decision.json"),
        "project_manager",
        "project_manager",
        "pm_decision_support",
        "PM research capability decision.",
    ),
    (
        "research:worker_report",
        "research_worker_report",
        ("research", "worker_research_report.json"),
        "worker",
        "project_manager",
        "pm_decision_support",
        "Worker research report metadata.",
    ),
    (
        "research:reviewer_report",
        "research_reviewer_report",
        ("research", "research_reviewer_report.json"),
        "human_like_reviewer",
        "project_manager",
        "reviewable_evidence",
        "Reviewer research direct-source report.",
    ),
    (
        "research:pm_absorption",
        "pm_research_absorption",
        ("research", "pm_research_absorption.json"),
        "project_manager",
        "project_manager",
        "accepted_material_basis",
        "PM research absorption record.",
    ),
    (
        "self_interrogation:index",
        "self_interrogation_index",
        ("self_interrogation_index.json",),
        "project_manager",
        "project_manager",
        "pm_decision_support",
        "Self-interrogation index.",
    ),
    (
        "generated_resources:ledger",
        "generated_resource_ledger",
        ("generated_resource_ledger.json",),
        "project_manager",
        "project_manager",
        "generated_resource_lineage",
        "Generated resource ledger.",
    ),
)


def static_artifact_entries(project_root: Path, run_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry_id, kind, rel_parts, producer, owner, authority, summary in STATIC_ARTIFACT_SPECS:
        path = run_root.joinpath(*rel_parts)
        data = read_json_document(path)
        entry = entry_for_artifact(
            project_root,
            path,
            entry_id=entry_id,
            kind=kind,
            producer_role=producer,
            owner_role=owner,
            authority_level=authority,
            safe_summary=summary,
            status=artifact_status(kind, data),
            metadata={
                "decision": data.get("decision"),
                "source_status": data.get("status"),
            },
        )
        if entry is not None:
            entries.append(entry)
    return entries


__all__ = [
    "ORDINARY_WORK_MATERIAL_ROLES",
    "artifact_status",
    "entry_for_artifact",
    "make_entry",
    "read_json_document",
    "safe_source_ref",
    "sealed_body_ref",
    "static_artifact_entries",
    "status_counts",
]
