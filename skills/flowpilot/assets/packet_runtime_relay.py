"""Relay mutation helpers for packet runtime.

Read-only relay readiness checks live in ``packet_runtime_relay_checks``. This
module keeps the historical import surface while owning relay writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packet_runtime_contracts import mutual_role_reminder
from packet_runtime_ledger import _update_packet_record
from packet_runtime_paths import (
    normalize_envelope_aliases,
    packet_paths_from_any_envelope,
    resolve_project_path,
)
from packet_runtime_relay_checks import (
    _completed_agent_id_is_role_key,
    _same_project_path,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_recipient_relay,
    validate_result_ready_for_reviewer_relay,
    verify_controller_relay,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_schema import (
    CONTROLLER_RELAY_SCHEMA,
    RESULT_ENVELOPE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    USER_INTAKE_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    utc_now,
    write_json_atomic,
)


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
