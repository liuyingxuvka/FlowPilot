"""Controller-safe role handoff rendering for current-run packets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import runtime


ROLE_LABELS = {
    "pm": "PM",
    "project_manager": "PM",
    "worker": "Worker",
    "research_worker": "Research worker",
    "reviewer": "Reviewer",
    "human_like_reviewer": "Reviewer",
    "flowguard_operator": "FlowGuard operator",
    "ui_qa": "UI QA",
    "planner": "Planner",
}


def _quote(value: str | Path) -> str:
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _role_label(responsibility: str) -> str:
    return ROLE_LABELS.get(responsibility, responsibility.replace("_", " ").title())


def _require_pair(ledger: Mapping[str, Any], packet_id: str, lease_id: str) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    packets = ledger.get("packets")
    leases = ledger.get("leases")
    if not isinstance(packets, Mapping) or not isinstance(leases, Mapping):
        raise runtime.BlackBoxRuntimeError("ledger does not contain packet/lease tables")
    packet = runtime._require(packets, packet_id, "packet")
    lease = runtime._require(leases, lease_id, "lease")
    if not isinstance(packet, Mapping) or not isinstance(lease, Mapping):
        raise runtime.BlackBoxRuntimeError("packet and lease records must be mappings")
    return packet, lease


def render_current_packet_handoff(
    ledger: Mapping[str, Any],
    *,
    root: Path,
    script_path: Path,
    run_id: str,
    packet_id: str,
    lease_id: str,
) -> dict[str, Any]:
    """Return Controller-safe handoff text for the assigned role.

    The returned text intentionally contains no sealed packet/result body text.
    It gives the role the exact commands it should run inside its own role
    surface.
    """

    packet, lease = _require_pair(ledger, packet_id, lease_id)
    envelope = packet.get("envelope")
    if not isinstance(envelope, Mapping):
        raise runtime.BlackBoxRuntimeError("packet envelope is missing")
    responsibility = str(lease.get("responsibility") or envelope.get("responsibility") or "")
    if not responsibility:
        raise runtime.BlackBoxRuntimeError("lease responsibility is missing")
    if str(envelope.get("responsibility") or "") != responsibility:
        raise runtime.BlackBoxRuntimeError("handoff responsibility mismatch")
    if str(packet.get("assigned_lease_id") or "") != lease_id:
        raise runtime.BlackBoxRuntimeError("handoff lease is not assigned to packet")
    if str(lease.get("packet_id") or "") not in {"", packet_id}:
        raise runtime.BlackBoxRuntimeError("handoff lease packet mismatch")

    root = root.resolve()
    script_path = script_path.resolve()
    ack_command = (
        f"python {_quote(script_path)} --root {_quote(root)} --json "
        f"ack --lease-id {lease_id} --packet-id {packet_id}"
    )
    open_command = (
        f"python {_quote(script_path)} --root {_quote(root)} --json "
        f"open-packet --lease-id {lease_id} --packet-id {packet_id}"
    )
    submit_command = (
        f"python {_quote(script_path)} --root {_quote(root)} --json "
        f"submit-result --lease-id {lease_id} --packet-id {packet_id} --body <sealed_result_summary>"
    )
    authorized_result_reads = [
        dict(row)
        for row in envelope.get("authorized_result_reads", [])
        if isinstance(row, Mapping)
    ]
    current_handoff_contract = (
        dict(envelope.get("current_handoff_contract"))
        if isinstance(envelope.get("current_handoff_contract"), Mapping)
        else {}
    )
    label = _role_label(responsibility)
    host_kind = str(lease.get("host_kind") or "")
    agent_id = str(lease.get("agent_id") or "")
    role_assignment_id = str(lease.get("role_assignment_id") or "")
    objective = str(envelope.get("objective") or "")
    role_memory_seed_id = str(lease.get("role_memory_seed_id") or "")
    role_memory_present = bool(role_memory_seed_id)
    role_memory_required = bool(lease.get("role_memory_seed_required"))

    text = "\n".join(
        [
            "FlowPilot lease is registered.",
            "",
            f"Workspace root: `{root}`",
            f"FlowPilot script: `{script_path}`",
            f"Run id: `{run_id}`",
            f"Packet id: `{packet_id}`",
            f"Lease id: `{lease_id}`",
            f"Role assignment id: `{role_assignment_id}`" if role_assignment_id else "Role assignment id: `<unspecified>`",
            f"Responsibility: `{responsibility}`",
            f"Host kind: `{host_kind}`" if host_kind else "Host kind: `<unspecified>`",
            f"Agent id: `{agent_id}`" if agent_id else "Agent id: `<unspecified>`",
            f"Packet objective: `{objective}`" if objective else "Packet objective: `<unspecified>`",
            (
                "Role memory: present in open-packet output."
                if role_memory_present
                else "Role memory: no prior current-run memory seed for this lease."
            ),
            "Role memory required before open: yes." if role_memory_required else "Role memory required before open: no.",
            "",
            f"Act as the {label} role only for this packet.",
            "First ACK the lease with:",
            f"`{ack_command}`",
            "",
            "Then open only this assigned packet through the runtime command:",
            f"`{open_command}`",
            "The open-packet output includes `current_handoff_contract`, `submission_checklist`, and any authorized input materials this packet may use.",
            "Before submit-result, use `submission_checklist.result_skeleton` or the packet body's `minimal_valid_shape` as the current mechanical checklist.",
            "If the checklist lists required fields, required child fields, explicit or non-empty arrays, branch-valid shapes, forbidden fields, or required authorized reads, follow those rows for this packet instead of using a remembered or shortened result shape.",
            "",
            *(
                [
                    "Authorized result/report bodies are delivered by open-packet for this role surface only.",
                    "Read every delivered authorized body before submit-result; blocker, target, and upstream context bodies each carry required context when present.",
                    "Do not work from only the packet body, a summary, or one selected result body when multiple authorized bodies were delivered.",
                    "Controller must not run role-only open commands or read sealed bodies.",
                    "",
                ]
                if authorized_result_reads
                else []
            ),
            "The open command is for the addressed role surface only. Controller must not run it.",
            "Use the returned sealed packet body only inside this role and do not expose sealed packet body text in chat.",
            "Do not access sibling packets, old-run packets, or sealed bodies addressed to another role.",
            "",
            "Submit the formal result through the runtime, normally:",
            f"`{submit_command}`",
            "",
            "Your chat response to Controller should only state whether ACK/result were submitted and any public blocker id if the runtime blocks you.",
        ]
    )
    return {
        "schema_version": "black_box_flowpilot.role_handoff.v1",
        "run_id": run_id,
        "packet_id": packet_id,
        "lease_id": lease_id,
        "role_assignment_id": role_assignment_id,
        "responsibility": responsibility,
        "host_kind": host_kind,
        "agent_id": agent_id,
        "controller_may_read": True,
        "controller_may_read_packet_body": False,
        "sealed_body_text_included": False,
        "role_memory_present": role_memory_present,
        "role_memory_seed_required": role_memory_required,
        "role_memory_seed_id": role_memory_seed_id,
        "role_memory_body_included": False,
        "role_must_not_expose_sealed_body_in_chat": True,
        "authorized_result_reads": authorized_result_reads,
        "current_handoff_contract": current_handoff_contract,
        "commands": {
            "ack": ack_command,
            "open_packet": open_command,
            "open_results": [],
            "submit_result": submit_command,
        },
        "text": text,
    }
