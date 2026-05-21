"""Runtime session helpers for packet and result review workflows."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from packet_runtime_active_holder import _require_concrete_agent_id
from packet_runtime_contracts import output_contract_id, packet_open_work_authority
from packet_runtime_ledger import _update_packet_record
from packet_runtime_paths import (
    load_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    resolve_project_path,
)
from packet_runtime_relay import verify_packet_open_receipt
from packet_runtime_schema import (
    RESULT_REVIEW_SESSION_SCHEMA,
    ROLE_PACKET_SESSION_SCHEMA,
    PacketRuntimeError,
    utc_now,
    write_json_atomic,
)


def read_packet_body_for_role(*args: Any, **kwargs: Any) -> str:
    import packet_runtime

    return packet_runtime.read_packet_body_for_role(*args, **kwargs)


def read_result_body_for_role(*args: Any, **kwargs: Any) -> str:
    import packet_runtime

    return packet_runtime.read_result_body_for_role(*args, **kwargs)


def write_controller_status_packet(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import packet_runtime

    return packet_runtime.write_controller_status_packet(*args, **kwargs)


def write_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import packet_runtime

    return packet_runtime.write_result(*args, **kwargs)


def _runtime_sessions_dir(project_root: Path, envelope_path: Path) -> Path:
    del project_root
    return envelope_path.parent / "runtime_sessions"

def _write_runtime_session(
    project_root: Path,
    *,
    envelope_path: Path,
    prefix: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    session_id = f"{prefix}-{uuid.uuid4().hex}"
    session_path = _runtime_sessions_dir(project_root, envelope_path) / f"{session_id}.json"
    session = dict(session)
    session["session_id"] = session_id
    session["session_path"] = project_relative(project_root, session_path)
    write_json_atomic(session_path, session)
    return session

def begin_role_packet_session(
    project_root: Path,
    *,
    envelope_path: str | Path,
    role: str,
    agent_id: str,
) -> dict[str, Any]:
    """Open a packet through the role runtime and persist the audit-only session."""

    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    packet_envelope_path = resolve_project_path(project_root, str(envelope_path))
    envelope = load_envelope(project_root, str(envelope_path))
    body_text = read_packet_body_for_role(project_root, envelope, role=role)
    opened_envelope = load_envelope(project_root, str(envelope_path))
    opened = opened_envelope.get("body_opened_by_role") if isinstance(opened_envelope, dict) else None
    if not isinstance(opened, dict):
        raise PacketRuntimeError("packet runtime session could not confirm packet body open receipt")
    work_authority = opened.get("work_authority")
    if not isinstance(work_authority, dict):
        work_authority = packet_open_work_authority(
            role=role,
            packet_type=str(opened_envelope.get("packet_type", "work_packet")),
            source="runtime_open_receipt",
        )
    paths = packet_paths_from_envelope(project_root, opened_envelope)
    session = _write_runtime_session(
        project_root,
        envelope_path=packet_envelope_path,
        prefix="packet-open-session",
        session={
            "schema_version": ROLE_PACKET_SESSION_SCHEMA,
            "runtime_entrypoint": "begin_role_packet_session",
            "packet_id": opened_envelope.get("packet_id"),
            "run_id": opened_envelope.get("run_id", str(paths["run_id"])),
            "node_id": opened_envelope.get("node_id"),
            "role": role,
            "agent_id": resolved_agent_id,
            "packet_envelope_path": project_relative(project_root, paths["packet_envelope"]),
            "packet_body_path": opened_envelope.get("body_path"),
            "packet_body_hash": opened_envelope.get("body_hash"),
            "packet_body_opened_by_role": opened,
            "controller_relay_verified": opened.get("controller_relay_verified") is True,
            "body_hash_verified": opened.get("body_hash_verified") is True,
            "work_authority": work_authority,
            "packet_open_authorizes_work": True,
            "required_exit": work_authority["required_exit"],
            "output_contract_id": output_contract_id(
                opened_envelope.get("output_contract") if isinstance(opened_envelope.get("output_contract"), dict) else None
            ),
            "controller_visibility": "session_metadata_only",
            "controller_may_read_body": False,
            "sealed_body_returned_to_role": True,
            "body_text_persisted_in_session": False,
            "created_at": utc_now(),
        },
    )
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        str(opened_envelope.get("packet_id") or ""),
        {
            "packet_runtime_session_id": session["session_id"],
            "packet_runtime_session_path": session["session_path"],
            "packet_runtime_session_entrypoint": "begin_role_packet_session",
            "packet_body_opened_by_agent_id": resolved_agent_id,
            "packet_body_opened_by_runtime_session": True,
            "packet_open_authorizes_work": True,
            "packet_open_work_authority": work_authority,
            "packet_open_required_exit": work_authority["required_exit"],
        },
    )
    write_controller_status_packet(
        project_root,
        opened_envelope,
        holder=role,
        status="working",
        message=f"Packet {opened_envelope['packet_id']} opened by {role}.",
        progress=1,
        progress_updated_by_role=role,
        progress_updated_by_agent_id=resolved_agent_id,
        work_authority=work_authority,
    )
    returned = dict(session)
    returned["body_text"] = body_text
    return returned

def _load_role_packet_session(project_root: Path, session_path: str | Path) -> dict[str, Any]:
    resolved_path = resolve_project_path(project_root, str(session_path))
    session = read_json(resolved_path)
    if session.get("schema_version") != ROLE_PACKET_SESSION_SCHEMA:
        raise PacketRuntimeError("runtime session is not a role packet session")
    if session.get("session_path") and resolve_project_path(project_root, str(session["session_path"])) != resolved_path:
        raise PacketRuntimeError("runtime session path does not match session record")
    return session

def complete_role_packet_session(
    project_root: Path,
    *,
    session_path: str | Path,
    result_body_text: str,
    next_recipient: str,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    session = _load_role_packet_session(project_root, session_path)
    role = str(session.get("role") or "")
    agent_id = _require_concrete_agent_id(str(session.get("agent_id") or ""), role=role)
    envelope = load_envelope(project_root, str(session["packet_envelope_path"]))
    if envelope.get("packet_id") != session.get("packet_id") or envelope.get("to_role") != role:
        raise PacketRuntimeError("runtime session does not match the current packet envelope")
    verify_packet_open_receipt(project_root, envelope, role=role)
    result = write_result(
        project_root,
        packet_envelope=envelope,
        completed_by_role=role,
        completed_by_agent_id=agent_id,
        result_body_text=result_body_text,
        next_recipient=next_recipient,
        strict_role=True,
        controller_aside=controller_aside,
    )
    paths = packet_paths_from_result_envelope(project_root, result)
    result.update(
        {
            "source_packet_runtime_session_id": session["session_id"],
            "source_packet_runtime_session_path": session["session_path"],
            "result_generated_by_runtime_session": True,
            "runtime_entrypoint": "complete_role_packet_session",
        }
    )
    write_json_atomic(paths["result_envelope"], result)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        str(result.get("packet_id") or ""),
        {
            "result_runtime_session_id": session["session_id"],
            "result_runtime_session_path": session["session_path"],
            "result_generated_by_runtime_session": True,
            "result_runtime_entrypoint": "complete_role_packet_session",
            "completed_by_agent_id": agent_id,
        },
    )
    return result

def run_role_packet_session(
    project_root: Path,
    *,
    envelope_path: str | Path,
    role: str,
    agent_id: str,
    result_body_text: str,
    next_recipient: str,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    session = begin_role_packet_session(project_root, envelope_path=envelope_path, role=role, agent_id=agent_id)
    result = complete_role_packet_session(
        project_root,
        session_path=session["session_path"],
        result_body_text=result_body_text,
        next_recipient=next_recipient,
        controller_aside=controller_aside,
    )
    return {
        "schema_version": "flowpilot.role_packet_runtime_run.v1",
        "session_path": session["session_path"],
        "session_id": session["session_id"],
        "result_envelope": result,
    }

def begin_result_review_session(
    project_root: Path,
    *,
    result_envelope_path: str | Path,
    role: str,
    agent_id: str,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    resolved_result_path = resolve_project_path(project_root, str(result_envelope_path))
    result = load_envelope(project_root, str(result_envelope_path))
    body_text = read_result_body_for_role(project_root, result, role=role)
    opened_result = load_envelope(project_root, str(result_envelope_path))
    opened = opened_result.get("result_body_opened_by_role") if isinstance(opened_result, dict) else None
    if not isinstance(opened, dict):
        raise PacketRuntimeError("result review runtime session could not confirm result body open receipt")
    paths = packet_paths_from_result_envelope(project_root, opened_result)
    session = _write_runtime_session(
        project_root,
        envelope_path=resolved_result_path,
        prefix="result-open-session",
        session={
            "schema_version": RESULT_REVIEW_SESSION_SCHEMA,
            "runtime_entrypoint": "begin_result_review_session",
            "packet_id": opened_result.get("packet_id"),
            "run_id": opened_result.get("run_id", str(paths["run_id"])),
            "node_id": opened_result.get("node_id"),
            "role": role,
            "agent_id": resolved_agent_id,
            "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
            "result_body_path": opened_result.get("result_body_path"),
            "result_body_hash": opened_result.get("result_body_hash"),
            "result_body_opened_by_role": opened,
            "source_packet_runtime_session_id": opened_result.get("source_packet_runtime_session_id"),
            "controller_relay_verified": opened.get("controller_relay_verified") is True,
            "body_hash_verified": opened.get("body_hash_verified") is True,
            "controller_visibility": "session_metadata_only",
            "controller_may_read_body": False,
            "sealed_body_returned_to_role": True,
            "body_text_persisted_in_session": False,
            "created_at": utc_now(),
        },
    )
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        str(opened_result.get("packet_id") or ""),
        {
            "result_review_runtime_session_id": session["session_id"],
            "result_review_runtime_session_path": session["session_path"],
            "result_review_runtime_session_entrypoint": "begin_result_review_session",
            "result_body_opened_by_agent_id": resolved_agent_id,
            "result_body_opened_by_runtime_session": True,
        },
    )
    returned = dict(session)
    returned["body_text"] = body_text
    return returned
