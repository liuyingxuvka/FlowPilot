"""Packet and result envelope indexing for FlowPilot material maps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import flowpilot_material_artifact_map_entries as entry_policy
import packet_runtime


def _runtime_open_roles(result: dict[str, Any]) -> list[str]:
    roles: list[str] = []

    def add_role(value: Any) -> None:
        role = str(value or "")
        if role and role not in roles:
            roles.append(role)

    add_role(result.get("next_recipient"))
    add_role("project_manager")
    add_role("human_like_reviewer")
    return roles


def add_packet_index_entries(
    project_root: Path,
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


__all__ = ["add_packet_index_entries"]
