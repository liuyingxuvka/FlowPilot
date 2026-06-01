"""Direct Router submission authority helpers for role outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from role_output_runtime_schema_io import _read_json, _require_concrete_agent_id, _run_paths, load_contract_registry
from role_output_runtime_schema_specs import RoleOutputRuntimeError, _role_allowed, _spec_for


def _contract_by_id(project_root: Path, contract_id: str, run_root: Path | None = None) -> dict[str, Any]:
    registry = load_contract_registry(project_root, run_root)
    for item in registry.get("contracts", []):
        if isinstance(item, dict) and item.get("contract_id") == contract_id:
            return item
    raise RoleOutputRuntimeError(f"output contract is missing from registry: {contract_id}")


def _contract_router_event_mode(project_root: Path, contract_id: str, run_root: Path | None = None) -> str:
    contract = _contract_by_id(project_root, contract_id, run_root)
    mode = str(contract.get("router_event_mode") or "").strip()
    if mode not in {"fixed", "router_supplied"}:
        raise RoleOutputRuntimeError(f"{contract_id} has unsupported router_event_mode: {mode!r}")
    return mode


def _current_allowed_external_events(run_root: Path) -> tuple[str, ...]:
    state_path = run_root / "state.json"
    if not state_path.exists():
        state_path = run_root / "router_state.json"
    if not state_path.exists():
        return ()
    state = _read_json(state_path)
    pending = state.get("pending_action")
    if not isinstance(pending, dict):
        return ()
    raw_events = pending.get("allowed_external_events")
    if not isinstance(raw_events, list):
        return ()
    events: list[str] = []
    for event in raw_events:
        name = str(event or "").strip()
        if name and name not in events:
            events.append(name)
    return tuple(events)


def validate_direct_router_submission_authority(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate that a direct role-output Router submission has live authority."""

    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    resolved_event = str(event_name or "").strip() or None
    session_id = None
    if session_path:
        from role_output_runtime_progress import _load_output_session

        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("direct Router submission role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("direct Router submission agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("direct Router submission output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        resolved_event = resolved_event or str(session.get("event_name") or "").strip() or None
        session_id = str(session.get("session_id") or "")
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} may be submitted only by {', '.join(spec.allowed_roles)}")

    mode = _contract_router_event_mode(project_root, spec.contract_id, run_root)
    resolved_event = resolved_event or spec.event_name
    if mode == "fixed":
        if not resolved_event:
            raise RoleOutputRuntimeError("fixed-event role output has no router event")
        if spec.event_name and resolved_event != spec.event_name:
            raise RoleOutputRuntimeError("direct Router submission event_name does not match fixed contract event")
        return {
            "ok": True,
            "authority_source": "fixed_contract_event",
            "run_id": resolved_run_id,
            "event_name": resolved_event,
            "output_type": spec.output_type,
            "output_contract_id": spec.contract_id,
            "session_id": session_id,
        }

    if not resolved_event:
        raise RoleOutputRuntimeError(
            "router_supplied role output requires a Router-supplied event from the current wait; "
            "PM packet and active-holder work must return through packet runtime"
        )
    allowed_events = _current_allowed_external_events(run_root)
    if resolved_event not in allowed_events:
        raise RoleOutputRuntimeError(
            "router_supplied role output event_name is not currently allowed by Router wait state"
        )
    return {
        "ok": True,
        "authority_source": "current_router_wait",
        "run_id": resolved_run_id,
        "event_name": resolved_event,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "allowed_external_events": list(allowed_events),
        "session_id": session_id,
    }
