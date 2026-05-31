"""Read-only relay readiness checks for packet runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packet_runtime_contracts import normalize_output_contract
from packet_runtime_ledger import packet_ledger_record_for_envelope
from packet_runtime_paths import (
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    resolve_project_path,
    verify_body_hash,
)
from packet_runtime_schema import (
    DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS,
    DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS,
    DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS,
    PACKET_ENVELOPE_SCHEMA,
    ROLE_KEYS,
    ROUTER_STARTUP_RELEASE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    validate_packet_id,
)


def _same_project_path(project_root: Path, left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    try:
        return resolve_project_path(project_root, left) == resolve_project_path(project_root, right)
    except PacketRuntimeError:
        return False


def verify_packet_open_receipt(project_root: Path, packet_envelope: dict[str, Any], *, role: str) -> dict[str, Any]:
    packet_envelope = dict(packet_envelope)
    opened = packet_envelope.get("body_opened_by_role")
    if (
        not isinstance(opened, dict)
        or opened.get("role") != role
        or opened.get("body_hash_verified") is not True
    ):
        raise PacketRuntimeError("packet envelope missing verified packet body open receipt")
    record = packet_ledger_record_for_envelope(project_root, packet_envelope)
    if not isinstance(record, dict):
        raise PacketRuntimeError("packet ledger record missing for packet body open receipt")
    if record.get("packet_body_opened_by_role") != role:
        raise PacketRuntimeError("packet ledger missing packet body open receipt")
    if record.get("packet_body_hash") != packet_envelope.get("body_hash"):
        raise PacketRuntimeError("packet ledger packet body hash does not match packet envelope")
    if not _same_project_path(project_root, str(record.get("packet_body_path") or ""), str(packet_envelope.get("body_path") or "")):
        raise PacketRuntimeError("packet ledger packet body path does not match packet envelope")
    return record


def _path_is_inside(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _direct_dispatch_result_paths_run_scoped(project_root: Path, envelope: dict[str, Any], packet_dir: Path) -> bool:
    path_keys = (
        "result_envelope_path",
        "result_body_path",
        "expected_result_envelope_path",
        "expected_result_body_path",
        "write_target_path",
    )
    for key in path_keys:
        raw = envelope.get(key)
        if raw and not _path_is_inside(packet_dir, resolve_project_path(project_root, str(raw))):
            return False
    write_target = envelope.get("result_write_target")
    if isinstance(write_target, dict):
        for key in ("result_envelope_path", "result_body_path"):
            raw = write_target.get(key)
            if raw and not _path_is_inside(packet_dir, resolve_project_path(project_root, str(raw))):
                return False
    return True


def validate_packet_ready_for_direct_relay(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    envelope_path: str | Path | None = None,
    allowed_target_roles: set[str] | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    envelope = dict(packet_envelope)
    blockers: list[str] = []
    missing_fields = [field for field in DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS if field not in envelope or envelope.get(field) in (None, "")]
    if missing_fields:
        blockers.append("packet_envelope_missing_required_fields")
    if envelope.get("schema_version") != PACKET_ENVELOPE_SCHEMA:
        blockers.append("packet_envelope_schema_mismatch")

    packet_id = str(envelope.get("packet_id") or "")
    try:
        validate_packet_id(packet_id)
    except PacketRuntimeError:
        blockers.append("packet_id_invalid")

    to_role = str(envelope.get("to_role") or "")
    from_role = str(envelope.get("from_role") or "")
    packet_type = str(envelope.get("packet_type") or "work_packet")
    if allowed_target_roles is not None and to_role not in {str(role) for role in allowed_target_roles}:
        blockers.append("packet_delivered_to_wrong_role")
    if envelope.get("body_visibility") != SEALED_BODY_VISIBILITY:
        blockers.append("packet_body_visibility_not_sealed")

    body_access = envelope.get("body_access")
    if not isinstance(body_access, dict):
        blockers.append("packet_body_access_missing")
    else:
        if body_access.get("controller_can_read_body") is not False:
            blockers.append("controller_can_read_packet_body")
        if body_access.get("controller_can_execute_body") is not False:
            blockers.append("controller_can_execute_packet_body")
        if body_access.get("body_hash_required") is not True:
            blockers.append("packet_body_hash_not_required")

    allowed_actions = set(envelope.get("controller_allowed_actions") or [])
    forbidden_actions = set(envelope.get("controller_forbidden_actions") or [])
    if DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions:
        blockers.append("controller_forbidden_actions_incomplete")
    if allowed_actions & DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS:
        blockers.append("controller_allowed_actions_violate_body_boundary")

    packet_body_hash_matches = False
    ledger_record_found = False
    ledger_identity_matches = False
    output_contract_present = False
    output_contract_valid = False
    result_paths_run_scoped = False
    paths: dict[str, Any] = {}

    try:
        paths = packet_paths_from_envelope(project_root, envelope)
        project_relative(project_root, paths["packet_envelope"])
        project_relative(project_root, paths["packet_body"])
        packet_body_hash_matches = verify_body_hash(project_root, str(envelope["body_path"]), str(envelope["body_hash"]))
        if not packet_body_hash_matches:
            blockers.append("body_hash_mismatch")
    except (KeyError, PacketRuntimeError, OSError):
        blockers.append("packet_body_path_or_hash_invalid")

    if paths:
        try:
            result_paths_run_scoped = _direct_dispatch_result_paths_run_scoped(project_root, envelope, paths["packet_dir"])
        except PacketRuntimeError:
            result_paths_run_scoped = False
        if not result_paths_run_scoped:
            blockers.append("result_path_escape")

        ledger_record = packet_ledger_record_for_envelope(project_root, envelope)
        ledger_record_found = isinstance(ledger_record, dict)
        if not ledger_record_found:
            blockers.append("packet_ledger_record_missing")
        else:
            ledger_identity_matches = (
                ledger_record.get("packet_body_hash") == envelope.get("body_hash")
                and _same_project_path(project_root, str(ledger_record.get("packet_body_path") or ""), str(envelope.get("body_path") or ""))
                and ledger_record.get("physical_packet_files_written") is True
            )
            if envelope_path is not None:
                ledger_identity_matches = ledger_identity_matches and _same_project_path(
                    project_root,
                    str(ledger_record.get("packet_envelope_path") or ""),
                    project_relative(project_root, resolve_project_path(project_root, str(envelope_path))),
                )
            if not ledger_identity_matches:
                blockers.append("packet_body_envelope_ledger_hash_identity_mismatch")

    output_contract = envelope.get("output_contract")
    output_contract_present = isinstance(output_contract, dict)
    if from_role == "project_manager" and not output_contract_present:
        blockers.append("missing_output_contract")
    if output_contract_present:
        if output_contract.get("recipient_role") != to_role:
            blockers.append("output_contract_recipient_mismatch")
        if from_role == "project_manager" and output_contract.get("selected_by_role") != "project_manager":
            blockers.append("output_contract_selected_by_role_mismatch")
        try:
            normalized_contract = normalize_output_contract(
                output_contract,
                packet_type=packet_type,
                from_role=from_role,
                to_role=to_role,
                node_id=str(envelope.get("node_id") or ""),
            )
            output_contract_valid = True
            for contract_key, envelope_key in (
                ("expected_result_envelope_path", "result_envelope_path"),
                ("expected_result_body_path", "result_body_path"),
                ("write_target_path", "write_target_path"),
            ):
                contract_path = normalized_contract.get(contract_key) if isinstance(normalized_contract, dict) else None
                envelope_target = envelope.get(envelope_key)
                if contract_path and envelope_target and not _same_project_path(project_root, str(contract_path), str(envelope_target)):
                    blockers.append("output_contract_result_path_mismatch")
                    break
        except PacketRuntimeError:
            blockers.append("output_contract_invalid")

    return {
        "schema_version": "flowpilot.packet_ready_for_direct_relay_audit.v1",
        "packet_id": envelope.get("packet_id"),
        "from_role": from_role,
        "to_role": to_role,
        "packet_envelope_checked": True,
        "packet_body_hash_matches_envelope": packet_body_hash_matches,
        "packet_ledger_record_found": ledger_record_found,
        "packet_ledger_identity_matches_envelope": ledger_identity_matches,
        "output_contract_present": output_contract_present,
        "output_contract_valid": output_contract_valid,
        "result_paths_run_scoped": result_paths_run_scoped,
        "controller_body_boundary_checked": True,
        "blockers": blockers,
        "passed": not blockers,
    }


def _completed_agent_id_is_role_key(completed_by_agent_id: Any) -> bool:
    return str(completed_by_agent_id or "").strip() in ROLE_KEYS


def validate_result_ready_for_recipient_relay(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    agent_role_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    packet_envelope = dict(packet_envelope)
    result_envelope = dict(result_envelope)
    blockers: list[str] = []
    expected_role = packet_envelope.get("to_role")
    completed_by_role = result_envelope.get("completed_by_role")
    completed_by_agent_id = result_envelope.get("completed_by_agent_id")

    packet_body_hash_matches = verify_body_hash(project_root, packet_envelope["body_path"], packet_envelope["body_hash"])
    result_body_hash_matches = verify_body_hash(project_root, result_envelope["result_body_path"], result_envelope["result_body_hash"])
    if not packet_body_hash_matches:
        blockers.append("packet_body_hash_mismatch")
    if not result_body_hash_matches:
        blockers.append("result_body_hash_mismatch")
    result_paths = packet_paths_from_result_envelope(project_root, result_envelope)
    ledger_record = packet_ledger_record_for_envelope(project_root, result_envelope)
    ledger_record_found = isinstance(ledger_record, dict)
    ledger_packet_opened = False
    result_ledger_absorbed = False
    if ledger_record_found:
        ledger_packet_opened = (
            ledger_record.get("packet_body_opened_by_role") == expected_role
            and ledger_record.get("packet_body_hash") == packet_envelope.get("body_hash")
        )
        result_ledger_absorbed = (
            ledger_record.get("result_body_hash") == result_envelope.get("result_body_hash")
            and _same_project_path(
                project_root,
                str(ledger_record.get("result_body_path") or ""),
                str(result_envelope.get("result_body_path") or ""),
            )
            and _same_project_path(
                project_root,
                str(ledger_record.get("result_envelope_path") or ""),
                project_relative(project_root, result_paths["result_envelope"]),
            )
        )
    if not ledger_record_found:
        blockers.append("packet_ledger_record_missing_for_result_relay")
    if not ledger_packet_opened:
        blockers.append("packet_ledger_missing_packet_body_open_receipt")
    if not result_ledger_absorbed:
        blockers.append("packet_ledger_missing_result_absorption")
    if completed_by_role == "controller":
        blockers.append("controller_origin_artifact")
    if completed_by_role != expected_role:
        blockers.append("result_completed_by_wrong_role")
    if _completed_agent_id_is_role_key(completed_by_agent_id):
        blockers.append("completed_agent_id_is_role_key_not_agent_id")
    if (
        agent_role_map is not None
        and str(completed_by_agent_id) in agent_role_map
        and agent_role_map.get(str(completed_by_agent_id)) != completed_by_role
    ):
        blockers.append("completed_agent_id_not_assigned_to_role")

    return {
        "schema_version": "flowpilot.result_ready_for_recipient_relay_audit.v1",
        "packet_id": packet_envelope.get("packet_id"),
        "relay_recipient": result_envelope.get("next_recipient"),
        "packet_body_hash_matches_envelope": packet_body_hash_matches,
        "result_body_hash_matches_envelope": result_body_hash_matches,
        "packet_ledger_record_found": ledger_record_found,
        "packet_ledger_packet_body_opened_by_target": ledger_packet_opened,
        "packet_ledger_result_absorbed": result_ledger_absorbed,
        "expected_role": expected_role,
        "completed_by_role": completed_by_role,
        "completed_by_agent_id": completed_by_agent_id,
        "completed_agent_id_belongs_to_role": bool(
            agent_role_map is None
            or str(completed_by_agent_id) not in agent_role_map
            or agent_role_map.get(str(completed_by_agent_id)) == completed_by_role
        )
        and not _completed_agent_id_is_role_key(completed_by_agent_id),
        "blockers": blockers,
        "passed": not blockers,
    }


def validate_result_ready_for_reviewer_relay(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    agent_role_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    audit = validate_result_ready_for_recipient_relay(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result_envelope,
        agent_role_map=agent_role_map,
    )
    audit["recipient_neutral_schema_version"] = audit["schema_version"]
    return audit


def verify_router_startup_release(
    envelope: dict[str, Any],
    *,
    recipient_role: str,
) -> dict[str, Any]:
    release = envelope.get("router_startup_release")
    if not isinstance(release, dict):
        raise PacketRuntimeError("missing router startup release signature")
    if release.get("schema_version") != ROUTER_STARTUP_RELEASE_SCHEMA:
        raise PacketRuntimeError("router startup release schema mismatch")
    if envelope.get("packet_type") != "user_intake":
        raise PacketRuntimeError("router startup release can only open user_intake")
    if release.get("delivered_by_router") is not True:
        raise PacketRuntimeError("router startup release was not delivered by Router")
    if release.get("relayed_to_role") != recipient_role:
        raise PacketRuntimeError(
            f"router startup release target {release.get('relayed_to_role')!r} does not match recipient {recipient_role!r}"
        )
    if release.get("body_was_read_by_router") is not False:
        raise PacketRuntimeError("router startup release did not sign that body was unread")
    if release.get("body_was_executed_by_router") is not False:
        raise PacketRuntimeError("router startup release did not sign that body was unexecuted")
    if not release.get("holder_before") or not release.get("holder_after"):
        raise PacketRuntimeError("router startup release holder chain is incomplete")
    return release


def verify_addressed_envelope(
    envelope: dict[str, Any],
    *,
    recipient_role: str,
) -> dict[str, Any]:
    if envelope.get("controller_return_to_sender", {}).get("contaminated"):
        raise PacketRuntimeError("contaminated envelope cannot be opened; sender must reissue a new packet")
    target = str(envelope.get("to_role") or envelope.get("next_recipient") or "")
    if target and target != recipient_role:
        raise PacketRuntimeError(f"envelope target {target!r} does not match recipient {recipient_role!r}")
    return {
        "schema_version": "flowpilot.addressed_envelope_check.v1",
        "recipient_role": recipient_role,
        "addressed_role": target,
    }
