"""Helper module for the role-output runtime facade."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from controller_process_aside import (
    build_controller_aside,
    controller_process_aside_contract,
)
from role_output_runtime_contracts import (
    _apply_runtime_fixed_values,
    _deep_merge,
    _finalize_contract_self_check,
    build_output_skeleton,
    validate_output_body,
)
from role_output_runtime_progress import (
    _default_output_path,
    _load_output_session,
    _role_output_ledger_path,
    _role_output_sessions_dir,
    default_role_output_status_packet_path,
    write_output_progress_status,
)
import role_output_runtime_controller_boundary as controller_boundary
from role_output_runtime_envelope_receipts import (
    runtime_envelope_for_body,
    validate_envelope_runtime_receipt,
)
from role_output_runtime_schema import (
    CONTROLLER_BOUNDARY_CONFIRMATION_EVENT,
    CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
    CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
    ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
    ROLE_OUTPUT_ENVELOPE_SCHEMA,
    ROLE_OUTPUT_LEDGER_SCHEMA,
    ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
    ROLE_OUTPUT_RUNTIME_SCHEMA,
    RoleOutputRuntimeError,
    OutputTypeSpec,
    _contract_by_id,
    _controller_boundary_sources,
    _project_relative,
    _read_json,
    _require_concrete_agent_id,
    _resolve_project_path,
    _role_allowed,
    _run_paths,
    _sha256_file,
    _spec_for,
    _write_json,
    controller_boundary_constraints,
    utc_now,
)

def _read_ledger(path: Path, run_id: str) -> dict[str, Any]:
    if path.exists():
        ledger = _read_json(path)
        ledger.setdefault("outputs", [])
        return ledger
    return {
        "schema_version": ROLE_OUTPUT_LEDGER_SCHEMA,
        "run_id": run_id,
        "outputs": [],
        "created_at": utc_now(),
    }


def _append_ledger(run_root: Path, run_id: str, record: dict[str, Any]) -> None:
    path = _role_output_ledger_path(run_root)
    ledger = _read_ledger(path, run_id)
    outputs = ledger.setdefault("outputs", [])
    if not isinstance(outputs, list):
        outputs = []
        ledger["outputs"] = outputs
    outputs.append(record)
    ledger["updated_at"] = utc_now()
    _write_json(path, ledger)


def _write_receipt(run_root: Path, receipt: dict[str, Any]) -> Path:
    receipt_id = str(receipt["receipt_id"])
    path = _role_output_sessions_dir(run_root) / f"{receipt_id}.json"
    _write_json(path, receipt)
    return path


def _build_envelope(
    project_root: Path,
    *,
    spec: OutputTypeSpec,
    role: str,
    output_path: Path,
    body_hash: str,
    receipt_path: Path,
    receipt_hash: str,
    agent_id: str,
    event_name: str | None,
    controller_status_packet_path: str | None = None,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    envelope = {
        "schema_version": ROLE_OUTPUT_ENVELOPE_SCHEMA,
        "router_submission_schema": ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
        "body_ref": {
            "path": _project_relative(project_root, output_path),
            "hash": body_hash,
            "path_key": spec.path_key,
            "hash_key": spec.hash_key,
        },
        "runtime_receipt_ref": {
            "path": _project_relative(project_root, receipt_path),
            "hash": receipt_hash,
        },
        "controller_visibility": "role_output_envelope_only",
        "chat_response_body_allowed": False,
        "delivery_mode": "direct_to_router",
        "submitted_to": "router",
        "controller_handoff_used": False,
        "controller_receives_role_output": False,
        "controller_next_step_source": "router_status_or_notice",
        "from_role": role,
        "to_role": "router",
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "role_output_runtime_validated": True,
        "runtime_validates_mechanics_only": True,
        "semantic_sufficiency_reviewed_by_runtime": False,
        "controller_process_aside_contract": controller_process_aside_contract(),
    }
    if event_name:
        envelope["event_name"] = event_name
    if controller_status_packet_path:
        envelope["controller_status_packet_path"] = controller_status_packet_path
    try:
        aside = build_controller_aside(
            controller_aside,
            from_role=role,
            source="role_output_runtime.envelope",
        )
    except ValueError as exc:
        raise RoleOutputRuntimeError(str(exc)) from exc
    if aside is not None:
        envelope["controller_aside"] = aside
    return envelope


def submit_output(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    body: dict[str, Any] | None = None,
    body_file: str | Path | None = None,
    output_path: str | Path | None = None,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
    controller_aside: str | None = None,
    router_directed_submission: bool = False,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    session_id = None
    if session_path:
        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("submit-output role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("submit-output agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("submit-output output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        event_name = event_name or session.get("event_name")
        controller_status_packet_path = (
            controller_status_packet_path or session.get("controller_status_packet_path")
        )
        session_id = str(session.get("session_id") or "")
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} may be submitted only by {', '.join(spec.allowed_roles)}")
    contract = _contract_by_id(project_root, spec.contract_id)
    router_event_mode = str(contract.get("router_event_mode") or "").strip()
    fixed_router_event = router_event_mode == "fixed" and bool(spec.event_name)
    if fixed_router_event and not router_directed_submission:
        raise RoleOutputRuntimeError(
            f"{output_type} has fixed Router event {spec.event_name}; use submit-output-to-router"
        )
    if body_file:
        submitted_body = _read_json(_resolve_project_path(project_root, body_file))
    elif body is not None:
        submitted_body = body
    else:
        raise RoleOutputRuntimeError("submit-output requires body-json or body-file")
    skeleton = build_output_skeleton(project_root, output_type=output_type, role=role, run_id=resolved_run_id)
    merged_body = _deep_merge(skeleton, submitted_body)
    _apply_runtime_fixed_values(
        project_root,
        merged_body,
        spec=spec,
        contract=contract,
        role=role,
        run_root=run_root,
    )
    first_validation = validate_output_body(
        project_root,
        output_type=output_type,
        role=role,
        body=merged_body,
        run_id=resolved_run_id,
    )
    _finalize_contract_self_check(merged_body, first_validation, explicit_arrays_required=bool(spec.explicit_array_fields))
    validation = validate_output_body(
        project_root,
        output_type=output_type,
        role=role,
        body=merged_body,
        run_id=resolved_run_id,
    )
    if not validation["ok"]:
        raise RoleOutputRuntimeError(f"role output validation failed: {validation['issues'][0]}")
    resolved_output_path = _resolve_project_path(project_root, output_path) if output_path else _default_output_path(run_root, spec)
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
    _write_json(resolved_output_path, merged_body)
    body_hash = _sha256_file(resolved_output_path)
    receipt_id = f"role-output-receipt-{uuid.uuid4().hex}"
    receipt = {
        "schema_version": ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "runtime_schema_version": ROLE_OUTPUT_RUNTIME_SCHEMA,
        "runtime_entrypoint": "submit_output_to_router" if router_directed_submission else "submit_output",
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "body_path": _project_relative(project_root, resolved_output_path),
        "body_hash": body_hash,
        "path_key": spec.path_key,
        "hash_key": spec.hash_key,
        "validation_status": "passed",
        "validation_issue_count": 0,
        "controller_visibility": "receipt_metadata_only",
        "controller_may_read_body": False,
        "body_text_persisted_in_receipt": False,
        "runtime_validates_mechanics_only": True,
        "semantic_sufficiency_reviewed_by_runtime": False,
        "local_receipt_written": True,
        "router_event_recording_required": fixed_router_event,
        "router_event_recorded": False,
        "created_at": utc_now(),
    }
    receipt_path = _write_receipt(run_root, receipt)
    receipt_hash = _sha256_file(receipt_path)
    envelope = _build_envelope(
        project_root,
        spec=spec,
        role=role,
        output_path=resolved_output_path,
        body_hash=body_hash,
        receipt_path=receipt_path,
        receipt_hash=receipt_hash,
        agent_id=resolved_agent_id,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=_project_relative(project_root, status_path),
        controller_aside=controller_aside,
    )
    ledger_record = {
        "output_id": receipt_id,
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "body_path": _project_relative(project_root, resolved_output_path),
        "body_hash": body_hash,
        "envelope": envelope,
        "receipt_path": _project_relative(project_root, receipt_path),
        "receipt_hash": receipt_hash,
        "controller_status_packet_path": _project_relative(project_root, status_path),
        "controller_visibility": "ledger_metadata_only",
        "controller_may_read_body": False,
        "semantic_sufficiency_reviewed_by_runtime": False,
        "local_receipt_written": True,
        "router_event_recording_required": fixed_router_event,
        "router_event_recorded": False,
        "recorded_at": utc_now(),
    }
    _append_ledger(run_root, resolved_run_id, ledger_record)
    write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=spec.output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="submitted",
        message=f"Role output {spec.output_type} submitted by {role}.",
        progress=999,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=status_path,
        session_id=session_id,
        controller_aside=controller_aside,
        local_receipt_written=True,
        router_event_recording_required=fixed_router_event,
        router_event_recorded=False,
        router_event_name=event_name or spec.event_name,
        router_handoff_status="pending_router_event" if fixed_router_event else "local_receipt_only",
    )
    return envelope


def build_controller_boundary_confirmation_body(
    project_root: Path,
    *,
    run_id: str | None = None,
    action_id: str | None = None,
    source_action_id: str | None = None,
) -> dict[str, Any]:
    return controller_boundary.build_controller_boundary_confirmation_body(
        project_root,
        run_id=run_id,
        action_id=action_id,
        source_action_id=source_action_id,
    )


def submit_controller_boundary_confirmation(
    project_root: Path,
    *,
    agent_id: str,
    run_id: str | None = None,
    action_id: str | None = None,
    source_action_id: str | None = None,
    output_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    return controller_boundary.submit_controller_boundary_confirmation(
        project_root,
        agent_id=agent_id,
        submit_output=submit_output,
        run_id=run_id,
        action_id=action_id,
        source_action_id=source_action_id,
        output_path=output_path,
        controller_status_packet_path=controller_status_packet_path,
    )
