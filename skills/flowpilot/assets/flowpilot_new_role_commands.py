"""Role assignment and sealed-body commands for the FlowPilot entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_new_shared import (
    ENTRYPOINT_PATH,
    _runtime_state,
    packets,
    role_handoff,
    run_shell,
    runtime,
    host,
)


def _first_active_packet(ledger: dict[str, Any]) -> str:
    active_version = ledger.get("active_route_version")
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"]["route_version"] == active_version and packet["status"] != "accepted":
            return packet_id
    raise runtime.BlackBoxRuntimeError("no active packet found")


def _packet_by_kind(ledger: dict[str, Any], packet_kind: str) -> str:
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"].get("packet_kind", "task") == packet_kind and packet["status"] == "open":
            return packet_id
    raise runtime.BlackBoxRuntimeError(f"no open {packet_kind} packet found")


def _quote_cli(value: str | Path) -> str:
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _role_assignment_commit_command(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    assignment: dict[str, Any],
) -> str:
    args = [
        "lease-agent",
        "--packet-id",
        packet_id,
        "--responsibility",
        responsibility,
        "--assignment-id",
        str(assignment.get("assignment_id") or ""),
        "--host-kind",
        str(assignment.get("host_kind") or "live"),
    ]
    if str(assignment.get("disposition") or "") == "create_new_role":
        args.extend(["--agent-id", "<role-surface-agent-id>"])
    return (
        f"python {_quote_cli(ENTRYPOINT_PATH.resolve())} --root {_quote_cli(root.resolve())} --json "
        + " ".join(args)
    )


def resolve_role_assignment(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    host_kind: str,
) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    assignment = runtime.resolve_role_assignment(
        ledger,
        responsibility,
        packet_id=packet_id,
        host_kind=host_kind,
    )
    run_shell.save_run_ledger(shell, ledger, guard_trigger="resolve_role_assignment")
    payload = {
        "ok": str(assignment.get("status") or "") != "blocked",
        "assignment_id": str(assignment.get("assignment_id") or ""),
        "role_assignment": assignment,
        "disposition": str(assignment.get("disposition") or ""),
        "role_surface_required": bool(assignment.get("role_surface_required") is True),
        "role_memory_seed_required": bool(assignment.get("role_memory_seed_required") is True),
        "effective_agent_id": str(assignment.get("effective_agent_id") or ""),
        "sealed_bodies_visible": False,
        **_runtime_state(ledger),
    }
    if payload["ok"]:
        payload["lease_commit_command"] = _role_assignment_commit_command(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            assignment=assignment,
        )
    else:
        payload["error"] = str(assignment.get("blocker_reason") or "role assignment blocked")
    return payload


def lease_agent(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    assignment_id: str,
    agent_id: str = "",
    host_kind: str,
) -> dict[str, Any]:
    if not assignment_id:
        raise runtime.BlackBoxRuntimeError(
            "lease-agent requires role assignment authorization; run resolve-role-assignment first"
        )
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    assignment = ledger.get("role_assignments", {}).get(assignment_id)
    if not isinstance(assignment, dict):
        raise runtime.BlackBoxRuntimeError("role assignment record is invalid")
    disposition = str(assignment.get("disposition") or "")
    if disposition == "reuse_existing_role" and agent_id:
        raise runtime.BlackBoxRuntimeError("reuse role assignment does not accept --agent-id")
    if disposition == "create_new_role" and not agent_id:
        raise runtime.BlackBoxRuntimeError("create-new role assignment requires --agent-id after opening the role surface")
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        agent_id=agent_id,
        host_kind=host_kind,
        packet_id=packet_id,
        scope="current_run",
        assignment_id=assignment_id,
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="lease_agent")
    handoff = role_handoff.render_current_packet_handoff(
        ledger,
        root=root,
        script_path=ENTRYPOINT_PATH,
        run_id=shell.run_id,
        packet_id=packet_id,
        lease_id=lease_id,
    )
    return {
        "ok": True,
        "lease_id": lease_id,
        "role_assignment_id": assignment_id,
        "role_assignment": ledger.get("role_assignments", {}).get(assignment_id, {}),
        "role_handoff": handoff,
        "role_handoff_text": handoff["text"],
        **_runtime_state(ledger),
    }


def ack(root: Path, *, lease_id: str, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    runtime.ack_lease(ledger, lease_id, packet_id)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="ack")
    return {"ok": True, **_runtime_state(ledger)}


def role_handoff_payload(root: Path, *, lease_id: str, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    handoff = role_handoff.render_current_packet_handoff(
        ledger,
        root=root,
        script_path=ENTRYPOINT_PATH,
        run_id=shell.run_id,
        packet_id=packet_id,
        lease_id=lease_id,
    )
    return {"ok": True, "role_handoff": handoff, "role_handoff_text": handoff["text"], **_runtime_state(ledger)}


def open_packet(root: Path, *, lease_id: str, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    role_memory = runtime.role_memory_seed_for_lease(ledger, lease_id, packet_id)
    body = packets.open_sealed_body_for_role(ledger, packet_id, lease_id)
    authorized_input_materials = runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    packet = ledger["packets"][packet_id]
    lease = ledger["leases"][lease_id]
    envelope = packet["envelope"]
    run_shell.save_run_ledger(shell, ledger, guard_trigger="open_packet")
    return {
        "ok": True,
        "schema_version": "black_box_flowpilot.open_packet_result.v1",
        "run_id": shell.run_id,
        "packet": {
            "packet_id": packet_id,
            "packet_kind": envelope.get("packet_kind", "task"),
            "responsibility": envelope["responsibility"],
            "objective": envelope["objective"],
            "route_version": envelope["route_version"],
            "body_hash": envelope["body_hash"],
            "output_contract": envelope.get("output_contract", {}),
            "current_handoff_contract": envelope.get("current_handoff_contract", {}),
        },
        "lease": {
            "lease_id": lease_id,
            "agent_id": lease.get("agent_id", ""),
            "responsibility": lease.get("responsibility", ""),
            "ack_received": bool(lease.get("ack_received")),
            "role_memory_present": bool(role_memory),
            "role_memory_seed_required": bool(lease.get("role_memory_seed_required")),
            "role_memory_seed_id": str(lease.get("role_memory_seed_id") or ""),
        },
        "role_memory": role_memory,
        "role_memory_visibility": "assigned_role_only",
        "sealed_packet_body": body,
        "sealed_body_visibility": "assigned_role_only",
        "authorized_input_materials": authorized_input_materials,
        "authorized_input_materials_delivered": True,
        "controller_may_read_packet_body": False,
        "controller_may_read_authorized_input_materials": False,
        "sealed_body_text_included": True,
        "open_receipt": {
            "event_type": "sealed_packet_body_opened",
            "packet_id": packet_id,
            "lease_id": lease_id,
            "body_hash": envelope["body_hash"],
        },
    }


def open_result(root: Path, *, lease_id: str, packet_id: str, result_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    opened = packets.open_result_body_for_role(ledger, packet_id, lease_id, result_id)
    packet = ledger["packets"][packet_id]
    lease = ledger["leases"][lease_id]
    result = ledger["results"][result_id]
    result_envelope = result.get("envelope", {})
    receipt = opened["receipt"]
    run_shell.save_run_ledger(shell, ledger, guard_trigger="open_result")
    return {
        "ok": True,
        "schema_version": "black_box_flowpilot.open_result_result.v1",
        "run_id": shell.run_id,
        "packet": {
            "packet_id": packet_id,
            "packet_kind": packet["envelope"].get("packet_kind", "task"),
            "responsibility": packet["envelope"]["responsibility"],
        },
        "lease": {
            "lease_id": lease_id,
            "agent_id": lease.get("agent_id", ""),
            "responsibility": lease.get("responsibility", ""),
            "ack_received": bool(lease.get("ack_received")),
        },
        "result": {
            "result_id": result_id,
            "source_packet_id": result.get("packet_id", ""),
            "body_hash": result_envelope.get("body_hash", ""),
        },
        "sealed_result_body": opened["body"],
        "sealed_body_visibility": "assigned_role_only",
        "controller_may_read_result_body": False,
        "sealed_body_text_included": True,
        "open_receipt": receipt,
    }
