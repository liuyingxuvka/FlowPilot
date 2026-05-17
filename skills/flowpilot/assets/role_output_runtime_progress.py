"""Helper module for the role-output runtime facade."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from role_output_runtime_contracts import build_output_skeleton
from role_output_runtime_schema import (
    ROLE_OUTPUT_RUNTIME_SCHEMA,
    ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA,
    ROLE_OUTPUT_STATUS_SCHEMA,
    PROGRESS_MESSAGE_FORBIDDEN_TERMS,
    PROGRESS_MESSAGE_MAX_LEN,
    RoleOutputRuntimeError,
    OutputTypeSpec,
    _project_relative,
    _read_json,
    _require_concrete_agent_id,
    _resolve_project_path,
    _role_allowed,
    _run_paths,
    _sha256_file,
    _spec_for,
    _write_json,
    utc_now,
)

def _default_output_path(run_root: Path, spec: OutputTypeSpec) -> Path:
    suffix = uuid.uuid4().hex[:12]
    return run_root / spec.default_subdir / f"{spec.default_filename_prefix}-{suffix}.json"


def _role_output_sessions_dir(run_root: Path) -> Path:
    return run_root / "role_output_sessions"


def _role_output_ledger_path(run_root: Path) -> Path:
    return run_root / "role_output_ledger.json"


def _role_output_status_dir(run_root: Path) -> Path:
    return run_root / "role_output_status"


def _safe_status_part(value: str) -> str:
    cleaned: list[str] = []
    for char in str(value or "").strip():
        if char.isalnum() or char in {"-", "_", "."}:
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("._-")[:96] or "unknown"


def default_role_output_status_packet_path(
    run_root: Path,
    *,
    role: str,
    output_type: str,
    event_name: str | None = None,
) -> Path:
    key = event_name or output_type
    return _role_output_status_dir(run_root) / (
        f"{_safe_status_part(role)}--{_safe_status_part(key)}--controller_status_packet.json"
    )


def _validate_progress_value(progress: int) -> int:
    if isinstance(progress, bool) or not isinstance(progress, int) or progress < 0:
        raise RoleOutputRuntimeError("progress must be a nonnegative integer")
    return progress


def _validate_progress_message(message: str) -> str:
    text = str(message or "").strip()
    if not text:
        raise RoleOutputRuntimeError("progress message must be non-empty")
    if len(text) > PROGRESS_MESSAGE_MAX_LEN:
        raise RoleOutputRuntimeError(f"progress message must be {PROGRESS_MESSAGE_MAX_LEN} characters or fewer")
    lowered = text.lower()
    for term in PROGRESS_MESSAGE_FORBIDDEN_TERMS:
        if term in lowered:
            raise RoleOutputRuntimeError("progress message must not include sealed body details")
    return text


def write_output_progress_status(
    project_root: Path,
    *,
    run_root: Path,
    output_type: str,
    role: str,
    agent_id: str,
    status: str,
    message: str,
    progress: int,
    event_name: str | None = None,
    controller_status_packet_path: str | Path | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} progress may be updated only by {', '.join(spec.allowed_roles)}")
    status_path = (
        _resolve_project_path(project_root, controller_status_packet_path)
        if controller_status_packet_path
        else default_role_output_status_packet_path(
            run_root,
            role=role,
            output_type=spec.output_type,
            event_name=event_name or spec.event_name,
        )
    )
    payload = {
        "schema_version": ROLE_OUTPUT_STATUS_SCHEMA,
        "runtime_entrypoint": "role_output_runtime.progress",
        "run_id": run_root.name,
        "holder": role,
        "status": status,
        "message": _validate_progress_message(message),
        "progress": _validate_progress_value(progress),
        "progress_written_by_runtime": True,
        "progress_updated_by_role": role,
        "progress_updated_by_agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "event_name": event_name or spec.event_name,
        "updated_at": utc_now(),
        "controller_visibility": "role_output_status_metadata_only",
        "controller_allowed_actions": ["read_role_output_status", "wait_for_role_output_envelope"],
        "controller_forbidden_actions": [
            "read_role_output_body",
            "read_role_output_directory",
            "infer_role_decision_from_progress",
            "approve_gate",
        ],
        "controller_may_read_body": False,
        "progress_is_decision_evidence": False,
        "body_text_persisted_in_status": False,
    }
    if session_id:
        payload["session_id"] = session_id
    _write_json(status_path, payload)
    payload["controller_status_packet_path"] = _project_relative(project_root, status_path)
    return payload


def _load_output_session(project_root: Path, session_path: str | Path) -> dict[str, Any]:
    session = _read_json(_resolve_project_path(project_root, session_path))
    if session.get("schema_version") != ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA:
        raise RoleOutputRuntimeError("role output session has unsupported schema")
    return session


def update_output_progress(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    progress: int,
    message: str,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    session_id = None
    if session_path:
        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("progress role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("progress agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("progress output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        controller_status_packet_path = (
            controller_status_packet_path or session.get("controller_status_packet_path")
        )
        event_name = event_name or session.get("event_name")
        session_id = str(session.get("session_id") or "")
    return write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="working",
        message=message,
        progress=progress,
        event_name=event_name,
        controller_status_packet_path=controller_status_packet_path,
        session_id=session_id,
    )



def prepare_output_session(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    run_id: str | None = None,
    body_path: str | Path | None = None,
    event_name: str | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    skeleton = build_output_skeleton(project_root, output_type=output_type, role=role, run_id=resolved_run_id)
    output_path = _resolve_project_path(project_root, body_path) if body_path else _default_output_path(run_root, spec)
    status_path = (
        _resolve_project_path(project_root, controller_status_packet_path)
        if controller_status_packet_path
        else default_role_output_status_packet_path(
            run_root,
            role=role,
            output_type=spec.output_type,
            event_name=event_name or spec.event_name,
        )
    )
    session = {
        "schema_version": ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA,
        "runtime_entrypoint": "prepare_output_session",
        "session_id": f"role-output-prepare-{uuid.uuid4().hex}",
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "suggested_body_path": _project_relative(project_root, output_path),
        "controller_status_packet_path": _project_relative(project_root, status_path),
        "path_key": spec.path_key,
        "hash_key": spec.hash_key,
        "event_name": event_name or spec.event_name,
        "controller_visibility": "session_metadata_only",
        "controller_may_read_body": False,
        "runtime_validates_mechanics_only": True,
        "created_at": utc_now(),
    }
    session_path = _role_output_sessions_dir(run_root) / f"{session['session_id']}.json"
    session["session_path"] = _project_relative(project_root, session_path)
    skeleton.setdefault("_role_output_contract", {})
    skeleton["_role_output_contract"]["progress_status"] = {
        "default_progress_required": True,
        "controller_status_packet_path": session["controller_status_packet_path"],
        "runtime_command": "flowpilot_runtime.py progress-output",
        "message_boundary": (
            "Use brief metadata only. Do not include sealed body content, findings, evidence, "
            "recommendations, decisions, or result details."
        ),
    }
    write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=spec.output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="prepared",
        message=f"Role output {spec.output_type} prepared for {role}.",
        progress=0,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=status_path,
        session_id=session["session_id"],
    )
    _write_json(session_path, session)
    return {
        **session,
        "body_skeleton": skeleton,
    }
