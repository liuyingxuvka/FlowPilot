"""Role assignment and sealed-body commands for the FlowPilot entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

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


def _json_object_from_body(body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item)]
    return []


def _mapping_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _submission_checklist_from_packet_body(
    body: str,
    authorized_input_materials: list[dict[str, Any]],
    current_handoff_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet_body = _json_object_from_body(body)
    handoff_contract = _mapping_or_empty(current_handoff_contract)
    if not handoff_contract:
        handoff_contract = _mapping_or_empty(packet_body.get("current_handoff_contract"))
    report_contract = _mapping_or_empty(handoff_contract.get("required_report_contract"))
    input_material_manifest = _mapping_or_empty(handoff_contract.get("input_material_manifest"))
    required_materials = [
        material
        for material in authorized_input_materials
        if isinstance(material, Mapping) and material.get("required_before_submit") is True
    ]
    required_result_body_fields = _string_list(
        packet_body.get("required_result_body_fields") or report_contract.get("required_result_body_fields")
    )
    conditional_required_fields = _mapping_or_empty(packet_body.get("conditional_required_fields"))
    result_skeleton = _mapping_or_none(packet_body.get("minimal_valid_shape")) or _mapping_or_empty(
        report_contract.get("minimal_valid_shape")
    )
    branch_valid_shapes = _mapping_or_empty(packet_body.get("branch_valid_shapes") or report_contract.get("branch_valid_shapes"))
    required_read_ids = _string_list(input_material_manifest.get("required_authorized_reads_before_submit")) or [
        str(material.get("result_id") or "") for material in required_materials if str(material.get("result_id") or "")
    ]
    authorized_result_read_ids = _string_list(input_material_manifest.get("authorized_result_read_ids"))
    required_read_count = input_material_manifest.get("required_authorized_read_count")
    if not isinstance(required_read_count, int):
        required_read_count = len(required_read_ids)
    all_required_reads_must_be_opened = input_material_manifest.get(
        "all_required_authorized_result_bodies_must_be_opened_before_submit"
    )
    if not isinstance(all_required_reads_must_be_opened, bool):
        all_required_reads_must_be_opened = bool(required_read_ids)
    return {
        "schema_version": "black_box_flowpilot.submission_checklist.v1",
        "source": "current_handoff_contract_and_sealed_packet_body",
        "contract_family_id": str(handoff_contract.get("contract_family_id") or ""),
        "current_packet_body_inspected": bool(packet_body),
        "current_handoff_contract_inspected": bool(handoff_contract),
        "required_result_body_fields": required_result_body_fields,
        "required_child_fields": _string_list(report_contract.get("required_child_fields")),
        "explicit_array_fields": _string_list(report_contract.get("explicit_array_fields")),
        "non_empty_array_fields": _string_list(report_contract.get("non_empty_array_fields")),
        "conditional_required_fields": conditional_required_fields,
        "allowed_value_options": _mapping_or_empty(report_contract.get("allowed_value_options")),
        "field_type_requirements": _mapping_or_empty(report_contract.get("field_type_requirements")),
        "result_skeleton": result_skeleton,
        "has_result_skeleton": bool(result_skeleton),
        "branch_valid_shapes": branch_valid_shapes,
        "missing_information_response": _mapping_or_empty(handoff_contract.get("missing_information_response")),
        "downstream_consumer": _mapping_or_empty(handoff_contract.get("downstream_consumer")),
        "input_material_manifest": input_material_manifest,
        "authorized_input_materials_count": len(authorized_input_materials),
        "required_authorized_input_materials_count": len(required_materials),
        "authorized_result_read_ids": authorized_result_read_ids,
        "required_authorized_result_read_ids": required_read_ids,
        "required_authorized_read_count": required_read_count,
        "all_required_authorized_result_bodies_must_be_opened_before_submit": all_required_reads_must_be_opened,
        "pre_submit_checks": [
            "Read every required authorized input material delivered by open-packet.",
            "Open every required authorized result body before submit when the checklist requires it.",
            "Fill every required_result_body_fields entry for this packet.",
            "Fill every required_child_fields path for this packet.",
            "Keep explicit_array_fields present as arrays, even when empty.",
            "Keep non_empty_array_fields present as non-empty arrays.",
            "Apply the conditional_required_fields branch for the chosen decision.",
            "Use only allowed_value_options for finite fields and match field_type_requirements exactly.",
            "Apply branch_valid_shapes for the chosen branch when present.",
            "Use result_skeleton as the current mechanical example when present.",
            "Do not submit a fixed short shape when result_skeleton contains additional required fields.",
        ],
    }


def _dispatch_retry_command(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    host_kind: str,
) -> str:
    args = [
        "dispatch-current-role",
        "--packet-id",
        packet_id,
        "--responsibility",
        responsibility,
        "--host-kind",
        host_kind,
        "--agent-id",
        "<role-surface-agent-id>",
    ]
    return (
        f"python {_quote_cli(ENTRYPOINT_PATH.resolve())} --root {_quote_cli(root.resolve())} --json "
        + " ".join(args)
    )


def dispatch_current_role(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    host_kind: str,
    agent_id: str = "",
) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    existing_lease_id = runtime.active_assigned_lease_for_packet(ledger, packet_id, responsibility)
    if existing_lease_id:
        existing_lease = ledger.get("leases", {}).get(existing_lease_id, {})
        role_assignment_id = str(existing_lease.get("role_assignment_id") or "")
        handoff = role_handoff.render_current_packet_handoff(
            ledger,
            root=root,
            script_path=ENTRYPOINT_PATH,
            run_id=shell.run_id,
            packet_id=packet_id,
            lease_id=existing_lease_id,
        )
        return {
            "ok": True,
            "lease_id": existing_lease_id,
            "role_assignment_id": role_assignment_id,
            "role_assignment": ledger.get("role_assignments", {}).get(role_assignment_id, {}),
            "role_handoff": handoff,
            "role_handoff_text": handoff["text"],
            "sealed_bodies_visible": False,
            **_runtime_state(ledger),
        }
    assignment = runtime.resolve_role_assignment(
        ledger,
        responsibility,
        packet_id=packet_id,
        host_kind=host_kind,
    )
    disposition = str(assignment.get("disposition") or "")
    if str(assignment.get("status") or "") == "blocked":
        run_shell.save_run_ledger(shell, ledger, guard_trigger="dispatch_current_role")
        return {
            "ok": False,
            "error": str(assignment.get("blocker_reason") or "role dispatch blocked"),
            "assignment_id": str(assignment.get("assignment_id") or ""),
            "role_assignment": assignment,
            "disposition": disposition,
            "sealed_bodies_visible": False,
            **_runtime_state(ledger),
        }
    if disposition == "create_new_role" and not agent_id:
        run_shell.save_run_ledger(shell, ledger, guard_trigger="dispatch_current_role")
        return {
            "ok": False,
            "error": "create-new role dispatch requires --agent-id after opening the role surface",
            "assignment_id": str(assignment.get("assignment_id") or ""),
            "role_assignment": assignment,
            "disposition": disposition,
            "role_surface_required": True,
            "role_memory_seed_required": bool(assignment.get("role_memory_seed_required") is True),
            "dispatch_current_role_command": _dispatch_retry_command(
                root,
                packet_id=packet_id,
                responsibility=responsibility,
                host_kind=host_kind,
            ),
            "sealed_bodies_visible": False,
            **_runtime_state(ledger),
        }
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        agent_id=agent_id,
        host_kind=host_kind,
        packet_id=packet_id,
        scope="current_run",
        assignment_id=str(assignment.get("assignment_id") or ""),
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="dispatch_current_role")
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
        "role_assignment_id": str(assignment.get("assignment_id") or ""),
        "role_assignment": ledger.get("role_assignments", {}).get(str(assignment.get("assignment_id") or ""), {}),
        "role_handoff": handoff,
        "role_handoff_text": handoff["text"],
        "sealed_bodies_visible": False,
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
    submission_checklist = _submission_checklist_from_packet_body(
        body,
        authorized_input_materials,
        envelope.get("current_handoff_contract", {}),
    )
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
        "submission_checklist": submission_checklist,
        "submission_checklist_visibility": "assigned_role_only",
        "controller_may_read_packet_body": False,
        "controller_may_read_authorized_input_materials": False,
        "controller_may_read_submission_checklist": False,
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
