"""Reviewer mechanical audit helpers for packet runtime results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packet_runtime_paths import (
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    verify_body_hash,
)
from packet_runtime_relay import _completed_agent_id_is_role_key, _same_project_path


def validate_for_reviewer(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    agent_role_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    packet_envelope = dict(packet_envelope)
    result_envelope = dict(result_envelope)
    blockers: list[str] = []
    packet_body_hash_matches = verify_body_hash(project_root, packet_envelope["body_path"], packet_envelope["body_hash"])
    result_body_hash_matches = verify_body_hash(
        project_root,
        result_envelope["result_body_path"],
        result_envelope["result_body_hash"],
    )
    expected_role = packet_envelope.get("to_role")
    completed_by_role = result_envelope.get("completed_by_role")
    completed_by_agent_id = result_envelope.get("completed_by_agent_id")
    agent_role = (agent_role_map or {}).get(str(completed_by_agent_id))
    agent_role_matches = (
        agent_role == completed_by_role
        if agent_role_map is not None and str(completed_by_agent_id) in agent_role_map
        else completed_by_role != "controller"
    )
    packet_open_record = packet_envelope.get("body_opened_by_role")
    packet_opened_by_target = (
        isinstance(packet_open_record, dict)
        and packet_open_record.get("role") == expected_role
        and packet_open_record.get("body_hash_verified") is True
    )
    result_open_record = result_envelope.get("result_body_opened_by_role")
    result_opened_by_recipient = isinstance(result_open_record, dict) and result_open_record.get("role") in {
        result_envelope.get("next_recipient"),
        "human_like_reviewer",
        "project_manager",
    } and result_open_record.get("body_hash_verified") is True
    ledger_packet_opened_by_target = False
    ledger_result_opened_by_recipient = False
    ledger_result_absorbed = False
    ledger_record_found = False
    try:
        paths = packet_paths_from_result_envelope(project_root, result_envelope)
        ledger = read_json(paths["packet_ledger"])
        records = ledger.get("packets") if isinstance(ledger.get("packets"), list) else []
        ledger_record = next(
            (
                record
                for record in records
                if isinstance(record, dict)
                and record.get("packet_id") == packet_envelope.get("packet_id") == result_envelope.get("packet_id")
            ),
            None,
        )
        if isinstance(ledger_record, dict):
            ledger_record_found = True
            ledger_packet_opened_by_target = (
                ledger_record.get("packet_body_opened_by_role") == expected_role
            )
            ledger_result_opened_by_recipient = (
                ledger_record.get("result_body_opened_by_role")
                in {result_envelope.get("next_recipient"), "human_like_reviewer", "project_manager"}
            )
            ledger_result_absorbed = (
                ledger_record.get("result_body_hash") == result_envelope.get("result_body_hash")
                and _same_project_path(
                    project_root,
                    str(ledger_record.get("result_body_path") or ""),
                    str(result_envelope.get("result_body_path") or ""),
                )
                and _same_project_path(
                    project_root,
                    str(ledger_record.get("result_envelope_path") or ""),
                    project_relative(project_root, paths["result_envelope"]),
                )
            )
    except Exception:
        ledger_record_found = False

    if not packet_body_hash_matches:
        blockers.append("packet_body_hash_mismatch")
    if not result_body_hash_matches:
        blockers.append("result_body_hash_mismatch")
    if not packet_opened_by_target:
        blockers.append("packet_body_not_opened_by_target_after_relay_check")
    if not result_opened_by_recipient:
        blockers.append("result_body_not_opened_by_reviewer_or_pm_after_relay_check")
    if not ledger_record_found:
        blockers.append("packet_ledger_record_missing_for_reviewer_audit")
    if not ledger_packet_opened_by_target:
        blockers.append("packet_ledger_missing_packet_body_open_receipt")
    if not ledger_result_absorbed:
        blockers.append("packet_ledger_missing_result_absorption")
    if not ledger_result_opened_by_recipient:
        blockers.append("packet_ledger_missing_result_body_open_receipt")
    if completed_by_role == "controller":
        blockers.append("controller_origin_artifact")
    if completed_by_role != expected_role:
        blockers.append("result_completed_by_wrong_role")
    if _completed_agent_id_is_role_key(completed_by_agent_id):
        blockers.append("completed_agent_id_is_role_key_not_agent_id")
        agent_role_matches = False
    if not agent_role_matches:
        blockers.append("completed_agent_id_not_assigned_to_role")

    return {
        "schema_version": "flowpilot.packet_runtime_review_audit.v1",
        "packet_id": packet_envelope.get("packet_id"),
        "packet_envelope_checked": True,
        "packet_runtime_physical_files_checked": True,
        "controller_context_body_exclusion_checked": True,
        "packet_body_opened_by_target": packet_opened_by_target,
        "result_body_opened_by_reviewer_or_pm": result_opened_by_recipient,
        "packet_ledger_record_found": ledger_record_found,
        "packet_ledger_packet_body_opened_by_target": ledger_packet_opened_by_target,
        "packet_ledger_result_absorbed": ledger_result_absorbed,
        "packet_ledger_result_body_opened_by_reviewer_or_pm": ledger_result_opened_by_recipient,
        "packet_envelope_to_role_checked": True,
        "packet_body_hash_checked": True,
        "packet_body_hash_matches_envelope": packet_body_hash_matches,
        "result_envelope_checked": True,
        "result_envelope_completed_by_role_checked": True,
        "result_envelope_completed_by_agent_id_checked": True,
        "result_body_hash_checked": True,
        "result_body_hash_matches_envelope": result_body_hash_matches,
        "expected_role": expected_role,
        "completed_by_role": completed_by_role,
        "completed_by_agent_id": completed_by_agent_id,
        "completed_agent_id_belongs_to_role": agent_role_matches,
        "controller_origin_evidence_detected": completed_by_role == "controller",
        "wrong_role_completion_detected": completed_by_role != expected_role,
        "wrong_role_completion_cosign_or_relabel_forbidden": True,
        "blockers": blockers,
        "passed": not blockers,
    }
