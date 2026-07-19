"""Controller-safe role handoff rendering for current-run packets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import host, runtime


SUBSTANTIVE_WORKSTREAM_INSTRUCTIONS = (
    "Treat this packet as one independently accountable complete workstream, not as a quick isolated reply.",
    "Before planning or execution, reconstruct the role-scoped global target from the current packet, its node context, and the current authoritative references it delivers or authorizes. Chat memory, summaries, labels, and completed-history indexes are navigation only; if a mandatory reference is missing, generic, stale, cross-run, or inaccessible, use the blocker or PM-routing outcome allowed by the current contract instead of inventing the standard.",
    "Identify every current packet-owned hard obligation, unresolved blocker, stale or missing evidence item, upstream dependency, and downstream handoff before optional improvements. Write a specific numbered plan that covers those unclosed obligations in dependency- and risk-aware order, not merely the smallest actions that can be marked complete.",
    "You may use bounded delegation, parallel role-local assistance, and role-local FlowGuard when useful, but you must integrate every delegated output yourself.",
    "Execute the plan, inspect the actual artifacts and evidence, verify the result, repair every in-scope defect you find, and escalate out-of-scope product, route, acceptance, or authority changes to PM instead of silently expanding scope.",
    "In `contract_self_check.workstream_plan_and_completion`, report every numbered step with status, evidence refs, deviations, and unresolved work; also report delegation/integration, verification, and repair. Every completion claim must map the accepted goal or current obligation to the actual artifact or observable state and then to current direct evidence; otherwise keep it unresolved or blocked. This is a semantic Reviewer contract, not a Runtime mechanical quality score.",
    "Role-local FlowGuard may improve your plan, model, evidence, or report, but it cannot self-approve your work or replace any required independent FlowGuard or Reviewer gate.",
    "Workers may plan how to execute this bounded workstream, but only PM may change product scope, route nodes or ordering, cross-node dependencies, or acceptance boundaries.",
    "Controller is excluded from substantive workstream planning: Controller follows only the Runtime-derived foreground action ledger and must not invent a project, role, or product plan.",
)


def _quote(value: str | Path) -> str:
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _role_label(responsibility: str) -> str:
    return host.current_responsibility_label(responsibility)


def _current_assignment_source(
    ledger: Mapping[str, Any],
    *,
    packet_id: str,
    lease_id: str,
    lease: Mapping[str, Any],
    responsibility: str,
) -> tuple[str, str]:
    assignment_id = str(lease.get("role_assignment_id") or "")
    if not assignment_id:
        raise runtime.BlackBoxRuntimeError("handoff lease has no current role assignment source")
    assignments = ledger.get("role_assignments")
    if not isinstance(assignments, Mapping):
        raise runtime.BlackBoxRuntimeError("handoff role assignment table is missing")
    assignment = assignments.get(assignment_id)
    if not isinstance(assignment, Mapping):
        raise runtime.BlackBoxRuntimeError("handoff role assignment source is missing")
    if str(assignment.get("responsibility") or "") != responsibility:
        raise runtime.BlackBoxRuntimeError("handoff role assignment responsibility mismatch")
    if str(assignment.get("packet_id") or "") not in {"", packet_id}:
        raise runtime.BlackBoxRuntimeError("handoff role assignment packet mismatch")
    assignment_status = str(assignment.get("status") or "")
    if assignment_status not in {"resolved", "consumed"}:
        raise runtime.BlackBoxRuntimeError("handoff role assignment source is not current")
    if assignment_status == "consumed" and str(assignment.get("consumed_lease_id") or "") != lease_id:
        raise runtime.BlackBoxRuntimeError("handoff role assignment lease mismatch")
    assignment_host_kind = host.require_current_host_kind(str(assignment.get("host_kind") or ""))
    lease_host_kind = str(lease.get("host_kind") or assignment_host_kind)
    host.require_current_host_kind(lease_host_kind)
    if lease_host_kind != assignment_host_kind:
        raise runtime.BlackBoxRuntimeError("handoff lease host kind does not match role assignment source")
    return assignment_id, assignment_host_kind


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
    lease_responsibility = host.require_current_responsibility(str(lease.get("responsibility") or ""))
    envelope_responsibility = host.require_current_responsibility(str(envelope.get("responsibility") or ""))
    if envelope_responsibility != lease_responsibility:
        raise runtime.BlackBoxRuntimeError("handoff responsibility mismatch")
    responsibility = lease_responsibility
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
        f"submit-result --lease-id {lease_id} --packet-id {packet_id} --body-file <sealed_result_body_file>"
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
    role_assignment_id, host_kind = _current_assignment_source(
        ledger,
        packet_id=packet_id,
        lease_id=lease_id,
        lease=lease,
        responsibility=responsibility,
    )
    agent_id = str(lease.get("agent_id") or "")
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
            "Before submit-result, use `submission_checklist.result_skeleton` from the current handoff contract as the single mechanical checklist.",
            "The skeleton is not answer prose. Replace every example sentence with packet-specific evidence, challenge, and PM-action reasoning; copying generic skeleton style is low-quality role work.",
            "If the checklist lists required fields, required child fields, explicit or non-empty arrays, branch-valid shapes, forbidden fields, or required authorized reads, follow those rows for this packet instead of using a remembered or shortened result shape.",
            "",
            "Complete Workstream Plan and Completion:",
            *SUBSTANTIVE_WORKSTREAM_INSTRUCTIONS,
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
