"""Startup user-intake packet helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from packet_runtime_active_holder import (
    _load_active_holder_lease,
    _require_concrete_agent_id,
    active_holder_ack,
    active_holder_progress,
    active_holder_submit_existing_result,
    active_holder_submit_result,
    issue_active_holder_lease,
)
from packet_runtime_contracts import (
    contract_self_check_metadata,
    default_output_contract,
    ensure_packet_identity_boundary,
    ensure_packet_output_contract_section,
    ensure_result_identity_boundary,
    mutual_role_reminder,
    normalize_output_contract,
    output_contract_id,
    packet_open_work_authority,
    validate_packet_identity_boundary,
    validate_result_identity_boundary,
)
from packet_runtime_ledger import (
    _empty_packet_ledger,
    _packet_ledger_record,
    _update_packet_record,
    _upsert_packet_record,
    packet_ledger_record_for_envelope,
)
from packet_runtime_paths import (
    active_run_root,
    load_envelope,
    packet_paths,
    packet_paths_from_any_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    read_json_if_exists,
    resolve_project_path,
    verify_body_hash,
)
from packet_runtime_relay import (
    _completed_agent_id_is_role_key,
    _same_project_path,
    deliver_envelope_metadata,
    mark_controller_contamination,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_reviewer_relay,
    verify_addressed_envelope,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    CHAIN_AUDIT_SCHEMA,
    CONTROLLER_HANDOFF_SCHEMA,
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
    DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
    DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
    DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS,
    DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS,
    DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS,
    OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS,
    OUTPUT_CONTRACT_SCHEMA,
    PACKET_ENVELOPE_SCHEMA,
    PACKET_IDENTITY_MARKER,
    PACKET_LEDGER_SCHEMA,
    PROGRESS_MESSAGE_FORBIDDEN_TERMS,
    PROGRESS_MESSAGE_MAX_LEN,
    RESULT_CONTROLLER_ALLOWED_ACTIONS,
    RESULT_CONTROLLER_FORBIDDEN_ACTIONS,
    RESULT_ENVELOPE_SCHEMA,
    RESULT_IDENTITY_MARKER,
    RESULT_REVIEW_SESSION_SCHEMA,
    ROLE_KEYS,
    ROLE_PACKET_SESSION_SCHEMA,
    ROUTER_STARTUP_RELEASE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    USER_INTAKE_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    sha256_file,
    stable_json_hash,
    utc_now,
    validate_packet_id,
    write_json_atomic,
    write_text_atomic,
)
from packet_runtime_sessions import (
    _load_role_packet_session,
    begin_result_review_session,
    begin_role_packet_session,
    complete_role_packet_session,
    run_role_packet_session,
)




















from packet_runtime_progress import write_controller_status_packet


from packet_runtime_creation_core import create_packet


_CURRENT_STARTUP_OPTION_KEYS = {"background_collaboration_authorized"}
_CURRENT_STARTUP_METADATA = {"provenance": "explicit_user_reply"}


def _append_user_intake_recovery_contract(body_text: str) -> str:
    if "pm_startup_repair_request" in body_text:
        return body_text
    recovery_contract = (
        "\n\n## Startup Recovery Contract\n"
        "- pm_startup_repair_request: if startup metadata or release evidence is mechanically invalid, "
        "use the current packet output contract or pm_control_blocker_repair_decision; do not revive "
        "legacy startup reviewer gates, chat-history recovery, or ordinary Controller repair prose.\n"
    )
    return body_text.rstrip() + recovery_contract


def _current_startup_options(startup_options: dict[str, Any] | None) -> dict[str, Any]:
    options = dict(startup_options or {})
    supported_keys = _CURRENT_STARTUP_OPTION_KEYS | set(_CURRENT_STARTUP_METADATA)
    unsupported_keys = sorted(set(options) - supported_keys)
    if unsupported_keys:
        raise PacketRuntimeError(f"unsupported startup option field(s): {', '.join(unsupported_keys)}")
    for key, expected in _CURRENT_STARTUP_METADATA.items():
        if key in options and options.get(key) != expected:
            raise PacketRuntimeError(f"startup option metadata {key} must be {expected}")
    if options.get("background_collaboration_authorized") is not True:
        raise PacketRuntimeError("user intake requires background_collaboration_authorized=true")
    return {key: options[key] for key in _CURRENT_STARTUP_OPTION_KEYS}

def router_release_startup_user_intake(
    project_root: Path,
    *,
    envelope: dict[str, Any],
    envelope_path: str | Path,
    released_to_role: str = "project_manager",
    source: str = "router_return_settlement_finalizer",
) -> dict[str, Any]:
    if envelope.get("packet_type") != "user_intake":
        raise PacketRuntimeError("router startup release is only valid for user_intake packets")
    if envelope.get("to_role") != released_to_role:
        raise PacketRuntimeError("router startup release target does not match user_intake target role")
    if envelope.get("body_visibility") == USER_INTAKE_BODY_VISIBILITY:
        raise PacketRuntimeError("router startup release requires sealed startup intake body visibility")

    paths = packet_paths_from_any_envelope(project_root, envelope)
    resolved_envelope_path = resolve_project_path(project_root, str(envelope_path))
    ledger_record = _packet_ledger_record(paths["packet_ledger"], str(envelope.get("packet_id") or ""))
    holder_before = (
        str(ledger_record.get("active_packet_holder") or "")
        if isinstance(ledger_record, dict)
        else str(envelope.get("from_role") or "router")
    )
    existing_release = envelope.get("router_startup_release")
    if (
        isinstance(existing_release, dict)
        and existing_release.get("schema_version") == ROUTER_STARTUP_RELEASE_SCHEMA
        and existing_release.get("delivered_by_router") is True
        and existing_release.get("relayed_to_role") == released_to_role
    ):
        return envelope

    release = {
        "schema_version": ROUTER_STARTUP_RELEASE_SCHEMA,
        "delivered_by_router": True,
        "source": source,
        "released_at": utc_now(),
        "received_from_role": "user",
        "relayed_to_role": released_to_role,
        "holder_before": holder_before or "router",
        "holder_after": released_to_role,
        "body_was_read_by_router": False,
        "body_was_executed_by_router": False,
        "body_visibility": envelope.get("body_visibility", SEALED_BODY_VISIBILITY),
        "startup_release_condition": "startup_intake_router_release_only",
        "controller_bypass_scope": "startup_user_intake_only",
        "deprecated_for_open_authority": True,
        "recipient_open_authority": "current_assignment_required",
        "envelope_hash": envelope_hash(envelope),
    }
    envelope["router_startup_release"] = release
    history = list(envelope.get("router_startup_release_history") or [])
    history.append(release)
    envelope["router_startup_release_history"] = history
    write_json_atomic(resolved_envelope_path, envelope)

    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "packet_router_release": release,
            "router_startup_release_history": release,
            "router_owned_startup_material": True,
            "router_direct_dispatch_decision": "released_by_router_startup_finalizer",
            "recipient_must_verify_router_startup_release_before_body_open": True,
            "active_packet_status": "envelope-relayed",
            "active_packet_holder": released_to_role,
            "holder_history": {
                "holder": released_to_role,
                "status": "envelope-relayed",
                "changed_at": release["released_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope.get("controller_status_packet_path"),
                "source": source,
            },
        },
    )
    write_controller_status_packet(
        project_root,
        envelope,
        holder=released_to_role,
        status="envelope-relayed",
        message=f"Router startup release recorded for {released_to_role}; current assignment and body hash checks authorize body open.",
        progress=0,
    )
    return envelope



def create_user_intake_packet(
    project_root: Path,
    *,
    packet_id: str,
    node_id: str,
    body_text: str,
    run_id: str | None = None,
    startup_options: dict[str, Any] | None = None,
    source: str = "user_chat_prompt",
    body_visibility: str | None = None,
    startup_intake_ref: dict[str, Any] | None = None,
    router_owned_startup_material: bool = False,
) -> dict[str, Any]:
    """Preserve the user's initial prompt as the first PM-bound physical packet."""

    resolved_body_visibility = body_visibility or USER_INTAKE_BODY_VISIBILITY
    current_startup_options = _current_startup_options(startup_options)
    metadata = {
        "source": source,
        "controller_bootstrap_scope": current_startup_options,
        "controller_may_bootstrap_required_background_collaboration": True,
        "controller_may_read_user_intake_body": resolved_body_visibility == USER_INTAKE_BODY_VISIBILITY,
        "controller_must_not_make_pm_route_or_gate_decision": True,
        "startup_runtime_release_required": True,
        "startup_runtime_release_status": "router_held_until_mechanical_audit_and_display_status",
        "router_owned_startup_material": router_owned_startup_material,
    }
    if startup_intake_ref is not None:
        metadata.update(
            {
                "startup_intake_ref": startup_intake_ref,
                "controller_may_read_user_intake_body": False,
                "router_mechanical_audit_source": "startup_intake_record",
                "controller_must_not_use_chat_history_for_startup_intake": True,
            }
        )
    body_text = _append_user_intake_recovery_contract(body_text)
    return create_packet(
        project_root,
        run_id=run_id,
        packet_id=packet_id,
        from_role="user",
        to_role="project_manager",
        node_id=node_id,
        body_text=body_text,
        packet_type="user_intake",
        body_visibility=resolved_body_visibility,
        metadata=metadata,
        next_holder="project_manager",
        return_to="router" if router_owned_startup_material else "controller",
        initial_holder="router" if router_owned_startup_material else "controller",
        initial_ledger_status="router-held-startup-material" if router_owned_startup_material else "packet-with-controller",
        initial_status_packet_status="router-held-startup-material" if router_owned_startup_material else "envelope-created",
        router_owned_startup_material=router_owned_startup_material,
    )
