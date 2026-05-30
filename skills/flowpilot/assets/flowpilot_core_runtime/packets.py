"""Packet facade for the complete black-box runtime."""

from __future__ import annotations

from typing import Any

from . import runtime


def issue_packet(ledger: dict[str, Any], responsibility: str, objective: str, body: str, **kwargs: Any) -> str:
    return runtime.issue_task_packet(ledger, responsibility, objective, body, **kwargs)


def submit_result(ledger: dict[str, Any], lease_id: str, packet_id: str, body: str, **kwargs: Any) -> str:
    return runtime.submit_result(ledger, lease_id, packet_id, body, **kwargs)


def open_sealed_body_for_role(ledger: dict[str, Any], packet_id: str, lease_id: str) -> str:
    packet = runtime._require(ledger["packets"], packet_id, "packet")
    lease = runtime._require(ledger["leases"], lease_id, "lease")
    if packet.get("assigned_lease_id") != lease_id:
        raise runtime.BlackBoxRuntimeError("lease cannot open this sealed packet body")
    if lease.get("status") != "active":
        raise runtime.BlackBoxRuntimeError("inactive lease cannot open sealed packet body")
    runtime._event(ledger, "sealed_packet_body_opened", packet_id=packet_id, lease_id=lease_id)
    return str(packet["body"])
