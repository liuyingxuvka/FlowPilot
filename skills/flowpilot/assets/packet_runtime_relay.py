"""Relay, direct-dispatch, and reviewer-readiness helpers for packet runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packet_runtime_contracts import mutual_role_reminder, normalize_output_contract
from packet_runtime_ledger import _packet_ledger_record, _update_packet_record
from packet_runtime_paths import (
    normalize_envelope_aliases,
    packet_paths_from_any_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    resolve_project_path,
    verify_body_hash,
)
from packet_runtime_schema import (
    CONTROLLER_RELAY_SCHEMA,
    DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS,
    DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS,
    DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS,
    PACKET_ENVELOPE_SCHEMA,
    RESULT_ENVELOPE_SCHEMA,
    ROLE_KEYS,
    ROUTER_STARTUP_RELEASE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    USER_INTAKE_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    utc_now,
    validate_packet_id,
    write_json_atomic,
)


def _same_project_path(project_root: Path, left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    try:
        return resolve_project_path(project_root, left) == resolve_project_path(project_root, right)
    except PacketRuntimeError:
        return False

def verify_packet_open_receipt(project_root: Path, packet_envelope: dict[str, Any], *, role: str) -> dict[str, Any]:
    packet_envelope = normalize_envelope_aliases(packet_envelope)
    opened = packet_envelope.get("body_opened_by_role")
    if (
        not isinstance(opened, dict)
        or opened.get("role") != role
        or opened.get("controller_relay_verified") is not True
        or opened.get("body_hash_verified") is not True
    ):
        raise PacketRuntimeError("packet envelope missing verified packet body open receipt")
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    record = _packet_ledger_record(paths["packet_ledger"], str(packet_envelope.get("packet_id") or ""))
    if not isinstance(record, dict):
        raise PacketRuntimeError("packet ledger record missing for packet body open receipt")
    if record.get("packet_body_opened_by_role") != role or record.get("packet_body_opened_after_controller_relay_check") is not True:
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
    envelope = normalize_envelope_aliases(packet_envelope)
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

        ledger_record = _packet_ledger_record(paths["packet_ledger"], packet_id)
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

def validate_result_ready_for_reviewer_relay(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    agent_role_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    packet_envelope = normalize_envelope_aliases(packet_envelope)
    result_envelope = normalize_envelope_aliases(result_envelope)
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
    try:
        verify_controller_relay(packet_envelope, recipient_role=str(expected_role))
    except PacketRuntimeError:
        blockers.append("missing_or_invalid_packet_controller_relay")

    result_paths = packet_paths_from_result_envelope(project_root, result_envelope)
    ledger_record = _packet_ledger_record(result_paths["packet_ledger"], str(result_envelope.get("packet_id") or ""))
    ledger_record_found = isinstance(ledger_record, dict)
    ledger_packet_opened = False
    result_ledger_absorbed = False
    if ledger_record_found:
        ledger_packet_opened = (
            ledger_record.get("packet_body_opened_by_role") == expected_role
            and ledger_record.get("packet_body_opened_after_controller_relay_check") is True
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
        "schema_version": "flowpilot.result_ready_for_reviewer_relay_audit.v1",
        "packet_id": packet_envelope.get("packet_id"),
        "packet_body_hash_matches_envelope": packet_body_hash_matches,
        "result_body_hash_matches_envelope": result_body_hash_matches,
        "packet_ledger_record_found": ledger_record_found,
        "packet_ledger_packet_body_opened_by_target_after_relay_check": ledger_packet_opened,
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

def mark_controller_contamination(
    project_root: Path,
    *,
    envelope: dict[str, Any],
    envelope_path: str | Path,
    controller_agent_id: str,
    received_from_role: str,
    reason: str = "controller_body_access_detected",
) -> dict[str, Any]:
    paths = packet_paths_from_any_envelope(project_root, envelope)
    resolved_envelope_path = resolve_project_path(project_root, str(envelope_path))
    record = {
        "schema_version": "flowpilot.controller_return_to_sender.v1",
        "packet_id": envelope["packet_id"],
        "controller_agent_id": controller_agent_id,
        "received_from_role": received_from_role,
        "returned_to_role": received_from_role,
        "reason": reason,
        "contaminated": True,
        "controller_must_not_relay": True,
        "must_reissue_new_packet": True,
        "replacement_packet_id": None,
        "created_at": utc_now(),
    }
    envelope["controller_return_to_sender"] = record
    write_json_atomic(resolved_envelope_path, envelope)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "active_packet_status": "contaminated-returned-to-sender",
            "active_packet_holder": received_from_role,
            "controller_packet_body_access_detected": True,
            "contaminated_evidence_disposition": "discarded",
            "controller_return_to_sender": record,
            "holder_history": {
                "holder": received_from_role,
                "status": "contaminated-returned-to-sender",
                "changed_at": record["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope.get("controller_status_packet_path"),
            },
        },
    )
    return record

def controller_relay_envelope(
    project_root: Path,
    *,
    envelope: dict[str, Any],
    envelope_path: str | Path,
    controller_agent_id: str,
    received_from_role: str | None = None,
    relayed_to_role: str | None = None,
    holder_before: str | None = None,
    holder_after: str | None = None,
    body_was_read_by_controller: bool = False,
    body_was_executed_by_controller: bool = False,
    private_role_to_role_delivery_detected: bool = False,
) -> dict[str, Any]:
    envelope.update(normalize_envelope_aliases(envelope))
    source_role = received_from_role or envelope.get("from_role") or envelope.get("completed_by_role") or "unknown"
    target_role = relayed_to_role or envelope.get("to_role") or envelope.get("next_recipient") or "unknown"
    if envelope.get("controller_return_to_sender", {}).get("contaminated"):
        raise PacketRuntimeError("contaminated envelope cannot be relayed; sender must reissue a new packet")
    if body_was_read_by_controller or body_was_executed_by_controller or private_role_to_role_delivery_detected:
        reason = "private_role_to_role_delivery_detected" if private_role_to_role_delivery_detected else "controller_body_read_or_executed"
        mark_controller_contamination(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id=controller_agent_id,
            received_from_role=source_role,
            reason=reason,
        )
        raise PacketRuntimeError("controller relay violation detected; envelope returned to sender for reissue")

    paths = packet_paths_from_any_envelope(project_root, envelope)
    resolved_envelope_path = resolve_project_path(project_root, str(envelope_path))
    body_visibility = envelope.get("body_visibility", SEALED_BODY_VISIBILITY)
    envelope_kind = (
        "result_envelope"
        if envelope.get("schema_version") == RESULT_ENVELOPE_SCHEMA or "completed_by_role" in envelope
        else "packet_envelope"
    )
    if envelope_kind == "packet_envelope" and envelope.get("packet_type") != "user_intake":
        audit = validate_packet_ready_for_direct_relay(
            project_root,
            packet_envelope=envelope,
            envelope_path=envelope_path,
            allowed_target_roles={str(target_role)},
        )
        if not audit.get("passed"):
            raise PacketRuntimeError(f"packet envelope is not ready for direct relay: {audit.get('blockers')}")
    mutual_reminder = mutual_role_reminder(
        source_role=str(source_role),
        target_role=str(target_role),
        envelope_kind=envelope_kind,
    )
    relay = {
        "schema_version": CONTROLLER_RELAY_SCHEMA,
        "delivered_via_controller": True,
        "controller_agent_id": controller_agent_id,
        "received_from_role": source_role,
        "relayed_to_role": target_role,
        "received_at": utc_now(),
        "relayed_at": utc_now(),
        "envelope_hash": envelope_hash(envelope),
        "body_was_read_by_controller": False,
        "body_was_executed_by_controller": False,
        "body_visibility": body_visibility,
        "external_user_input_visible_to_controller": body_visibility == USER_INTAKE_BODY_VISIBILITY,
        "holder_before": holder_before or source_role,
        "holder_after": holder_after or target_role,
        "private_role_to_role_delivery_detected": False,
        "recipient_must_verify_before_body_open": True,
        "mutual_role_reminder": mutual_reminder,
        "reply_continuation_reminder": mutual_reminder["reply_continuation_reminder"],
        "recipient_role_reminder": f"This mail is for `{target_role}` only.",
        "mail_only_reminder": "The recipient must answer through a file-backed packet/result/report body and submit the runtime envelope to Router; Controller sees only Router-authorized metadata.",
        "chat_response_body_allowed": False,
    }
    envelope["controller_relay"] = relay
    history = list(envelope.get("controller_relay_history") or [])
    history.append(relay)
    envelope["controller_relay_history"] = history
    write_json_atomic(resolved_envelope_path, envelope)

    relay_kind = "packet_controller_relay" if "body_path" in envelope else "result_controller_relay"
    active_status = "envelope-relayed" if "body_path" in envelope else "result-envelope-relayed"
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            relay_kind: relay,
            "controller_relay_history": relay,
            "controller_relay_signature_required": True,
            "recipient_must_verify_controller_relay_before_body_open": True,
            "private_role_to_role_delivery_detected": False,
            "active_packet_status": active_status,
            "active_packet_holder": target_role,
            "holder_history": {
                "holder": target_role,
                "status": active_status,
                "changed_at": relay["relayed_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope.get("controller_status_packet_path"),
            },
        },
    )
    return envelope

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

def verify_controller_relay(
    envelope: dict[str, Any],
    *,
    recipient_role: str,
) -> dict[str, Any]:
    relay = envelope.get("controller_relay")
    if envelope.get("controller_return_to_sender", {}).get("contaminated"):
        raise PacketRuntimeError("contaminated envelope cannot be opened; sender must reissue a new packet")
    if not isinstance(relay, dict):
        raise PacketRuntimeError("missing controller relay signature")
    if relay.get("delivered_via_controller") is not True:
        raise PacketRuntimeError("envelope was not delivered via controller")
    if relay.get("relayed_to_role") != recipient_role:
        raise PacketRuntimeError(
            f"controller relay target {relay.get('relayed_to_role')!r} does not match recipient {recipient_role!r}"
        )
    if relay.get("body_was_read_by_controller") is not False:
        raise PacketRuntimeError("controller did not sign that body was unread")
    if relay.get("body_was_executed_by_controller") is not False:
        raise PacketRuntimeError("controller did not sign that body was unexecuted")
    if relay.get("private_role_to_role_delivery_detected"):
        raise PacketRuntimeError("private role-to-role delivery detected")
    if relay.get("envelope_hash") != envelope_hash(envelope):
        raise PacketRuntimeError("controller relay envelope hash mismatch")
    if not relay.get("holder_before") or not relay.get("holder_after"):
        raise PacketRuntimeError("controller relay holder chain is incomplete")
    return relay
