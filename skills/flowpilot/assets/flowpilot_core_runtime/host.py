"""Dynamic host and responsibility-lease helpers for the complete runtime."""

from __future__ import annotations

from typing import Any

from . import runtime


HOST_KINDS = frozenset({"fake", "dry_run", "live"})
CURRENT_RESPONSIBILITY_LABELS = {
    "pm": "PM",
    "worker": "Worker",
    "research_worker": "Research worker",
    "reviewer": "Reviewer",
    "flowguard_operator": "FlowGuard operator",
    "ui_qa": "UI QA",
}
CURRENT_RESPONSIBILITIES = frozenset(CURRENT_RESPONSIBILITY_LABELS)


def require_current_responsibility(responsibility: str) -> str:
    if responsibility not in CURRENT_RESPONSIBILITIES:
        raise runtime.BlackBoxRuntimeError(f"unknown current responsibility: {responsibility}")
    return responsibility


def require_current_host_kind(host_kind: str) -> str:
    if host_kind not in HOST_KINDS:
        raise runtime.BlackBoxRuntimeError(f"unknown current host kind: {host_kind}")
    return host_kind


def current_responsibility_label(responsibility: str) -> str:
    return CURRENT_RESPONSIBILITY_LABELS[require_current_responsibility(responsibility)]


def lease_responsibility(
    ledger: dict[str, Any],
    responsibility: str,
    *,
    host_kind: str = "fake",
    agent_id: str | None = None,
    packet_id: str = "",
    scope: str = "",
    assignment_id: str = "",
) -> str:
    responsibility = require_current_responsibility(responsibility)
    host_kind = require_current_host_kind(host_kind)
    if not assignment_id:
        assignment = runtime.resolve_role_assignment(
            ledger,
            responsibility,
            packet_id=packet_id,
            host_kind=host_kind,
        )
        assignment_id = str(assignment.get("assignment_id") or "")
    else:
        assignment = ledger.setdefault("role_assignments", {}).get(assignment_id)
        if not isinstance(assignment, dict):
            raise runtime.BlackBoxRuntimeError("role assignment record is invalid")
        if str(assignment.get("responsibility") or "") != responsibility:
            raise runtime.BlackBoxRuntimeError("role assignment responsibility mismatch")
        if str(assignment.get("packet_id") or "") not in {"", packet_id}:
            raise runtime.BlackBoxRuntimeError("role assignment packet mismatch")
        if str(assignment.get("host_kind") or "") != host_kind:
            raise runtime.BlackBoxRuntimeError("role assignment host kind mismatch")
    if str(assignment.get("disposition") or "") == "blocked":
        reason = str(assignment.get("blocker_reason") or "role assignment blocked")
        raise runtime.BlackBoxRuntimeError(reason)
    effective_agent_id = agent_id
    if str(assignment.get("disposition") or "") == "reuse_existing_role":
        effective_agent_id = None
    lease_id = runtime.lease_agent(
        ledger,
        responsibility,
        agent_id=effective_agent_id,
        packet_id=packet_id,
        assignment_id=assignment_id,
    )
    lease = ledger["leases"][lease_id]
    lease["host_kind"] = host_kind
    lease["scope"] = scope
    lease["role_assignment_id"] = assignment_id
    ledger.setdefault("host_driver_state", {})[lease_id] = {
        "lease_id": lease_id,
        "host_kind": host_kind,
        "responsibility": responsibility,
        "scope": scope,
        "role_assignment_id": assignment_id,
        "state": "leased",
        "current_run_only": True,
    }
    ledger.setdefault("host_evidence", {})[lease_id] = {
        "lease_id": lease_id,
        "host_kind": host_kind,
        "role_assignment_id": assignment_id,
        "confidence": "live" if host_kind == "live" else "scoped",
        "live_confidence": host_kind == "live",
        "current_run_only": True,
        "created_at": runtime.now_iso(),
    }
    runtime._event(ledger, "responsibility_lease_created", lease_id=lease_id, host_kind=host_kind, scope=scope)
    return lease_id


def record_role_memory_seed(
    ledger: dict[str, Any],
    lease_id: str,
    *,
    memory_packet_id: str,
    prior_agent_id: str = "",
) -> None:
    lease = runtime._require(ledger["leases"], lease_id, "lease")
    lease["memory_packet_id"] = memory_packet_id
    lease["prior_agent_id"] = prior_agent_id
    lease["prior_agent_authority"] = "audit_only"
    ledger.setdefault("role_memory", {})[lease_id] = {
        "lease_id": lease_id,
        "memory_packet_id": memory_packet_id,
        "prior_agent_id": prior_agent_id,
        "prior_agent_authority": "audit_only",
        "current_run_seed": True,
        "created_at": runtime.now_iso(),
    }
    runtime._event(
        ledger,
        "role_memory_seed_recorded",
        lease_id=lease_id,
        memory_packet_id=memory_packet_id,
        prior_agent_authority="audit_only",
    )


def submit_host_result(
    ledger: dict[str, Any],
    lease_id: str,
    packet_id: str,
    body: str,
    **kwargs: Any,
) -> str:
    return runtime.submit_result(ledger, lease_id, packet_id, body, **kwargs)


def host_confidence_boundary(ledger: dict[str, Any]) -> dict[str, Any]:
    rows = list(ledger.get("host_evidence", {}).values())
    live_rows = [row for row in rows if row.get("live_confidence")]
    return {
        "has_live_host_evidence": bool(live_rows),
        "confidence": "live" if live_rows else "scoped",
        "rows": rows,
    }
