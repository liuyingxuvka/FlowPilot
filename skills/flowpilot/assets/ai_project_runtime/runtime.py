"""Clean black-box runtime for dynamic AI project execution.

The runtime is deliberately small and serializable. It is not the old
FlowPilot router. It implements the clean protocol rules needed for a project
ledger, dynamic agent leases, sealed packets, FlowGuard work orders,
independent review, safe console projection, and final backward closure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "black_box_flowpilot_runtime.v1"
DEFAULT_PROJECT_ID = "project-001"
REQUIRED_FLOWGUARD_TARGET = "development_process"
RESPONSIBILITIES = {"planner", "worker", "reviewer", "flowguard_operator"}

_DEFAULT_FLOWGUARD_ROUTES = {
    "target_product_behavior": "model-first-function-flow",
    "development_process": "flowguard-development-process-flow",
    "ui_interaction_flow": "flowguard-ui-flow-structure",
    "code_structure_plan": "flowguard-code-structure-recommendation",
    "large_structure_split": "flowguard-structure-mesh",
    "test_and_evidence_hierarchy": "flowguard-test-mesh",
    "model_test_alignment": "flowguard-model-test-alignment",
    "model_hierarchy": "flowguard-model-mesh",
    "model_miss": "flowguard-model-miss-review",
    "architecture_reduction": "flowguard-architecture-reduction",
}


class BlackBoxRuntimeError(ValueError):
    """Raised when a caller asks for an impossible runtime transition."""


@dataclass(frozen=True)
class RuntimeAction:
    """Router-selected next action."""

    action_type: str
    reason: str
    subject_id: str = ""
    responsibility: str = ""
    modeled_target: str = ""

    def to_json(self) -> dict[str, str]:
        return asdict(self)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _next_id(ledger: dict[str, Any], prefix: str) -> str:
    counters = ledger.setdefault("counters", {})
    counters[prefix] = int(counters.get(prefix, 0)) + 1
    return f"{prefix}-{counters[prefix]:04d}"


def _event(ledger: dict[str, Any], event_type: str, **payload: Any) -> None:
    ledger.setdefault("events", []).append(
        {
            "event_id": _next_id(ledger, "event"),
            "event_type": event_type,
            "created_at": now_iso(),
            "payload": payload,
        }
    )


def _copy_jsonable(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def _route_table() -> dict[str, str]:
    protocol_scheduler = (
        Path(__file__).resolve().parents[1]
        / "ai_project_protocol"
        / "flowguard_route_scheduler.json"
    )
    try:
        payload = json.loads(protocol_scheduler.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_FLOWGUARD_ROUTES)

    routes: dict[str, str] = {}
    for route in payload.get("routes", []):
        if isinstance(route, dict):
            target = route.get("modeled_target")
            skill = route.get("selected_skill")
            if isinstance(target, str) and isinstance(skill, str):
                routes[target] = skill
    return routes or dict(_DEFAULT_FLOWGUARD_ROUTES)


def selected_flowguard_skill(modeled_target: str) -> str:
    routes = _route_table()
    try:
        return routes[modeled_target]
    except KeyError as exc:
        raise BlackBoxRuntimeError(f"unknown FlowGuard modeled target: {modeled_target}") from exc


def new_ledger(
    goal: str,
    acceptance_contract: str,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    if not goal.strip():
        raise BlackBoxRuntimeError("goal is required")
    if not acceptance_contract.strip():
        raise BlackBoxRuntimeError("acceptance_contract is required")
    ledger: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "created_at": now_iso(),
        "goal": goal,
        "acceptance_contract": acceptance_contract,
        "source_generation": 1,
        "active_route_version": None,
        "routes": {},
        "leases": {},
        "packets": {},
        "results": {},
        "reviews": {},
        "flowguard_work_orders": {},
        "validation_evidence": {},
        "closure": None,
        "events": [],
        "counters": {},
    }
    _event(ledger, "project_started", project_id=project_id)
    return ledger


def save_ledger(ledger: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_ledger(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise BlackBoxRuntimeError("unsupported ledger schema")
    return payload


def create_route(ledger: dict[str, Any], summary: str, steps: list[str]) -> str:
    if not summary.strip():
        raise BlackBoxRuntimeError("route summary is required")
    if not steps:
        raise BlackBoxRuntimeError("route needs at least one step")

    old_version = ledger.get("active_route_version")
    new_version = int(old_version or 0) + 1
    route_id = f"route-v{new_version}"
    ledger["routes"][str(new_version)] = {
        "route_id": route_id,
        "route_version": new_version,
        "summary": summary,
        "steps": list(steps),
        "status": "active",
        "created_at": now_iso(),
        "source_generation": ledger["source_generation"],
    }
    ledger["active_route_version"] = new_version

    for packet in ledger["packets"].values():
        if packet["envelope"]["route_version"] != new_version and packet["status"] in {
            "open",
            "assigned",
            "acknowledged",
            "result_submitted",
        }:
            packet["status"] = "quarantined_after_route_mutation"
            packet["old_route_disposition"] = "quarantined"

    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    return route_id


def record_source_change(ledger: dict[str, Any], reason: str) -> int:
    ledger["source_generation"] = int(ledger.get("source_generation", 1)) + 1
    _event(ledger, "source_generation_changed", reason=reason, generation=ledger["source_generation"])
    return ledger["source_generation"]


def lease_agent(
    ledger: dict[str, Any],
    responsibility: str,
    *,
    agent_id: str | None = None,
    packet_id: str = "",
) -> str:
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    lease_id = _next_id(ledger, "lease")
    lease = {
        "lease_id": lease_id,
        "agent_id": agent_id or f"{responsibility}-{lease_id}",
        "responsibility": responsibility,
        "status": "active",
        "packet_id": packet_id,
        "ack_received": False,
        "progress_count": 0,
        "created_at": now_iso(),
        "closed_at": None,
        "close_reason": "",
    }
    ledger["leases"][lease_id] = lease
    _event(ledger, "lease_created", lease_id=lease_id, responsibility=responsibility)
    return lease_id


def close_lease(ledger: dict[str, Any], lease_id: str, reason: str = "closed") -> None:
    lease = _require(ledger["leases"], lease_id, "lease")
    lease["status"] = "closed"
    lease["closed_at"] = now_iso()
    lease["close_reason"] = reason
    _event(ledger, "lease_closed", lease_id=lease_id, reason=reason)


def expire_lease(ledger: dict[str, Any], lease_id: str, reason: str = "timeout") -> None:
    lease = _require(ledger["leases"], lease_id, "lease")
    lease["status"] = "expired"
    lease["closed_at"] = now_iso()
    lease["close_reason"] = reason
    _event(ledger, "lease_expired", lease_id=lease_id, reason=reason)


def issue_task_packet(
    ledger: dict[str, Any],
    responsibility: str,
    objective: str,
    body: str,
    *,
    allowed_tools: list[str] | None = None,
    required_output_type: str = "artifact",
    required_flowguard_target: str = REQUIRED_FLOWGUARD_TARGET,
) -> str:
    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot issue a packet without an active route")
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    packet_id = _next_id(ledger, "packet")
    body_hash = hash_text(body)
    envelope = {
        "packet_id": packet_id,
        "route_version": ledger["active_route_version"],
        "responsibility": responsibility,
        "objective": objective,
        "allowed_tools": list(allowed_tools or []),
        "required_output_type": required_output_type,
        "required_reviewer": "independent",
        "required_flowguard_target": required_flowguard_target,
        "body_hash": body_hash,
        "body_visibility": "sealed",
        "source_generation": ledger["source_generation"],
    }
    ledger["packets"][packet_id] = {
        "packet_id": packet_id,
        "status": "open",
        "envelope": envelope,
        "body": body,
        "assigned_lease_id": "",
        "result_ids": [],
        "accepted_result_id": "",
        "old_route_disposition": "",
    }
    _event(ledger, "task_packet_issued", packet_id=packet_id, responsibility=responsibility)
    return packet_id


def assign_packet(ledger: dict[str, Any], packet_id: str, lease_id: str) -> None:
    packet = _require(ledger["packets"], packet_id, "packet")
    lease = _require(ledger["leases"], lease_id, "lease")
    if lease["status"] != "active":
        raise BlackBoxRuntimeError("cannot assign packet to inactive lease")
    if lease["responsibility"] != packet["envelope"]["responsibility"]:
        raise BlackBoxRuntimeError("lease responsibility does not match packet")
    packet["assigned_lease_id"] = lease_id
    packet["status"] = "assigned"
    lease["packet_id"] = packet_id
    _event(ledger, "packet_assigned", packet_id=packet_id, lease_id=lease_id)


def ack_lease(ledger: dict[str, Any], lease_id: str, packet_id: str) -> None:
    lease = _require(ledger["leases"], lease_id, "lease")
    packet = _require(ledger["packets"], packet_id, "packet")
    if lease["status"] != "active":
        raise BlackBoxRuntimeError("inactive lease cannot ACK")
    if packet["assigned_lease_id"] != lease_id:
        raise BlackBoxRuntimeError("lease is not assigned to packet")
    lease["ack_received"] = True
    packet["status"] = "acknowledged"
    _event(ledger, "lease_ack", lease_id=lease_id, packet_id=packet_id)


def record_progress(ledger: dict[str, Any], lease_id: str, packet_id: str, status: str) -> None:
    lease = _require(ledger["leases"], lease_id, "lease")
    if lease.get("packet_id") != packet_id:
        raise BlackBoxRuntimeError("progress packet mismatch")
    lease["progress_count"] = int(lease.get("progress_count", 0)) + 1
    lease["last_progress_status"] = status
    _event(ledger, "lease_progress", lease_id=lease_id, packet_id=packet_id, status=status)


def submit_result(
    ledger: dict[str, Any],
    lease_id: str,
    packet_id: str,
    body: str,
    *,
    output_type: str = "artifact",
    evidence_ids: list[str] | None = None,
    evidence_generation: int | None = None,
    valid_shape: bool = True,
) -> str:
    lease = _require(ledger["leases"], lease_id, "lease")
    packet = _require(ledger["packets"], packet_id, "packet")
    result_id = _next_id(ledger, "result")
    generation = evidence_generation if evidence_generation is not None else ledger["source_generation"]
    body_hash = hash_text(body)
    blockers = _result_mechanical_blockers(
        ledger,
        lease=lease,
        packet=packet,
        output_type=output_type,
        evidence_generation=generation,
        valid_shape=valid_shape,
    )
    status = "mechanically_valid" if not blockers else "blocked"
    result = {
        "result_id": result_id,
        "packet_id": packet_id,
        "producer_lease_id": lease_id,
        "producer_agent_id": lease["agent_id"],
        "route_version": packet["envelope"]["route_version"],
        "status": status,
        "mechanical_blockers": blockers,
        "envelope": {
            "packet_id": packet_id,
            "result_id": result_id,
            "route_version": packet["envelope"]["route_version"],
            "output_type": output_type,
            "evidence_ids": list(evidence_ids or []),
            "evidence_generation": generation,
            "body_hash": body_hash,
            "body_visibility": "sealed",
        },
        "body": body,
        "review_id": "",
        "accepted": False,
    }
    ledger["results"][result_id] = result
    packet["result_ids"].append(result_id)
    packet["status"] = "result_submitted" if not blockers else "result_blocked"
    _event(
        ledger,
        "result_submitted",
        result_id=result_id,
        packet_id=packet_id,
        lease_id=lease_id,
        status=status,
    )
    return result_id


def _result_mechanical_blockers(
    ledger: Mapping[str, Any],
    *,
    lease: Mapping[str, Any],
    packet: Mapping[str, Any],
    output_type: str,
    evidence_generation: int,
    valid_shape: bool,
) -> list[str]:
    blockers: list[str] = []
    if lease["status"] != "active":
        blockers.append("closed_or_inactive_lease")
    if not lease.get("ack_received"):
        blockers.append("missing_ack")
    if packet.get("assigned_lease_id") != lease["lease_id"]:
        blockers.append("wrong_lease_for_packet")
    if packet["envelope"]["route_version"] != ledger.get("active_route_version"):
        blockers.append("stale_route_version")
    if output_type != packet["envelope"]["required_output_type"] or not valid_shape:
        blockers.append("wrong_result_shape")
    if evidence_generation < int(ledger.get("source_generation", 1)):
        blockers.append("stale_evidence")
    return blockers


def create_flowguard_work_order(
    ledger: dict[str, Any],
    modeled_target: str,
    risk_type: str,
    subject_id: str,
) -> str:
    selected_skill = selected_flowguard_skill(modeled_target)
    order_id = _next_id(ledger, "flowguard")
    ledger["flowguard_work_orders"][order_id] = {
        "order_id": order_id,
        "modeled_target": modeled_target,
        "risk_type": risk_type,
        "selected_skill": selected_skill,
        "subject_id": subject_id,
        "status": "open",
        "decision": "",
        "evidence_id": "",
        "progress_only": False,
        "skipped_checks": [],
        "source_generation": ledger["source_generation"],
        "created_at": now_iso(),
        "completed_at": None,
    }
    _event(
        ledger,
        "flowguard_work_order_created",
        order_id=order_id,
        modeled_target=modeled_target,
        selected_skill=selected_skill,
    )
    return order_id


def complete_flowguard_work_order(
    ledger: dict[str, Any],
    order_id: str,
    *,
    decision: str = "pass",
    evidence_id: str = "flowguard-report",
    progress_only: bool = False,
    skipped_checks: list[str] | None = None,
) -> None:
    order = _require(ledger["flowguard_work_orders"], order_id, "flowguard order")
    order["status"] = "complete"
    order["decision"] = decision
    order["evidence_id"] = evidence_id
    order["progress_only"] = progress_only
    order["skipped_checks"] = list(skipped_checks or [])
    order["source_generation"] = ledger["source_generation"]
    order["completed_at"] = now_iso()
    _event(ledger, "flowguard_work_order_completed", order_id=order_id, decision=decision)


def review_result(
    ledger: dict[str, Any],
    result_id: str,
    reviewer_lease_id: str,
    *,
    decision: str = "accept",
    checks_evidence: bool = True,
) -> str:
    result = _require(ledger["results"], result_id, "result")
    packet = _require(ledger["packets"], result["packet_id"], "packet")
    reviewer = _require(ledger["leases"], reviewer_lease_id, "lease")
    producer = _require(ledger["leases"], result["producer_lease_id"], "lease")
    review_id = _next_id(ledger, "review")
    blockers = _review_blockers(
        ledger,
        result=result,
        packet=packet,
        reviewer=reviewer,
        producer=producer,
        checks_evidence=checks_evidence,
    )
    accepted = decision == "accept" and not blockers
    ledger["reviews"][review_id] = {
        "review_id": review_id,
        "result_id": result_id,
        "reviewer_lease_id": reviewer_lease_id,
        "reviewer_agent_id": reviewer["agent_id"],
        "decision": "accept" if accepted else "block",
        "checks_evidence": checks_evidence,
        "independent_from_producer": reviewer["agent_id"] != producer["agent_id"],
        "blockers": blockers,
        "created_at": now_iso(),
    }
    result["review_id"] = review_id
    result["accepted"] = accepted
    if accepted:
        result["status"] = "accepted"
        packet["status"] = "accepted"
        packet["accepted_result_id"] = result_id
    else:
        result["status"] = "review_blocked"
        packet["status"] = "review_blocked"
    _event(ledger, "result_reviewed", review_id=review_id, result_id=result_id, accepted=accepted)
    return review_id


def _review_blockers(
    ledger: Mapping[str, Any],
    *,
    result: Mapping[str, Any],
    packet: Mapping[str, Any],
    reviewer: Mapping[str, Any],
    producer: Mapping[str, Any],
    checks_evidence: bool,
) -> list[str]:
    blockers: list[str] = []
    if reviewer["status"] != "active":
        blockers.append("inactive_reviewer_lease")
    if reviewer["responsibility"] != "reviewer":
        blockers.append("reviewer_responsibility_required")
    if reviewer["agent_id"] == producer["agent_id"] or reviewer["lease_id"] == producer["lease_id"]:
        blockers.append("self_review")
    if not checks_evidence:
        blockers.append("weak_review_no_evidence_check")
    if result["status"] != "mechanically_valid":
        blockers.extend(result.get("mechanical_blockers", []) or ["result_not_mechanically_valid"])
    if result["envelope"]["evidence_generation"] < ledger.get("source_generation", 1):
        blockers.append("stale_evidence")
    if packet["envelope"]["route_version"] != ledger.get("active_route_version"):
        blockers.append("stale_route_version")
    if not _has_matching_flowguard_report(ledger, packet["packet_id"], packet["envelope"]["required_flowguard_target"]):
        blockers.append("missing_matching_flowguard_report")
    return sorted(set(blockers))


def record_validation_evidence(
    ledger: dict[str, Any],
    evidence_id: str,
    *,
    status: str = "passed",
    generation: int | None = None,
) -> None:
    ledger["validation_evidence"][evidence_id] = {
        "evidence_id": evidence_id,
        "status": status,
        "source_generation": generation if generation is not None else ledger["source_generation"],
        "created_at": now_iso(),
    }
    _event(ledger, "validation_evidence_recorded", evidence_id=evidence_id, status=status)


def attempt_final_closure(
    ledger: dict[str, Any],
    validation_evidence_id: str,
    *,
    required_flowguard_target: str = REQUIRED_FLOWGUARD_TARGET,
) -> dict[str, Any]:
    blockers = _closure_blockers(
        ledger,
        validation_evidence_id=validation_evidence_id,
        required_flowguard_target=required_flowguard_target,
    )
    closure = {
        "decision": "complete" if not blockers else "blocked",
        "blockers": blockers,
        "validation_evidence_id": validation_evidence_id,
        "required_flowguard_target": required_flowguard_target,
        "active_route_version": ledger.get("active_route_version"),
        "created_at": now_iso(),
        "backward_chain": _backward_chain(ledger) if not blockers else [],
    }
    ledger["closure"] = closure
    _event(ledger, "final_closure_attempted", decision=closure["decision"], blockers=blockers)
    return closure


def _closure_blockers(
    ledger: Mapping[str, Any],
    *,
    validation_evidence_id: str,
    required_flowguard_target: str,
) -> list[str]:
    blockers: list[str] = []
    if not ledger.get("goal"):
        blockers.append("missing_goal")
    active_route = ledger.get("active_route_version")
    if active_route is None:
        blockers.append("missing_active_route")

    active_packets = [
        packet
        for packet in ledger.get("packets", {}).values()
        if packet["envelope"]["route_version"] == active_route
    ]
    accepted_packets = [packet for packet in active_packets if packet.get("accepted_result_id")]
    if not accepted_packets:
        blockers.append("missing_accepted_packet_result")
    for packet in active_packets:
        if packet["status"] not in {"accepted", "quarantined_after_route_mutation"}:
            blockers.append(f"packet_not_accepted:{packet['packet_id']}")
    for packet in accepted_packets:
        result = ledger["results"][packet["accepted_result_id"]]
        review = ledger["reviews"].get(result.get("review_id", ""))
        if not review or review.get("decision") != "accept":
            blockers.append(f"missing_independent_review:{packet['packet_id']}")
        if not _has_matching_flowguard_report(ledger, packet["packet_id"], required_flowguard_target):
            blockers.append(f"missing_flowguard:{packet['packet_id']}")

    evidence = ledger.get("validation_evidence", {}).get(validation_evidence_id)
    if not evidence:
        blockers.append("missing_validation_evidence")
    elif evidence.get("status") != "passed":
        blockers.append("validation_not_passing")
    elif evidence.get("source_generation") != ledger.get("source_generation"):
        blockers.append("stale_validation_evidence")
    return sorted(set(blockers))


def _has_matching_flowguard_report(
    ledger: Mapping[str, Any],
    subject_id: str,
    modeled_target: str,
) -> bool:
    for order in ledger.get("flowguard_work_orders", {}).values():
        if order.get("subject_id") != subject_id:
            continue
        if order.get("modeled_target") != modeled_target:
            continue
        if order.get("status") != "complete":
            continue
        if order.get("decision") != "pass":
            continue
        if order.get("progress_only"):
            continue
        if order.get("skipped_checks"):
            continue
        if order.get("source_generation") != ledger.get("source_generation"):
            continue
        return True
    return False


def _backward_chain(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    chain = [
        {"kind": "goal", "id": ledger["project_id"], "summary": ledger["goal"]},
        {"kind": "route", "id": f"route-v{ledger['active_route_version']}"},
    ]
    for packet in ledger.get("packets", {}).values():
        if packet["envelope"]["route_version"] != ledger.get("active_route_version"):
            continue
        if not packet.get("accepted_result_id"):
            continue
        result = ledger["results"][packet["accepted_result_id"]]
        chain.append({"kind": "packet", "id": packet["packet_id"]})
        chain.append({"kind": "result", "id": result["result_id"]})
        chain.append({"kind": "review", "id": result["review_id"]})
        for order in ledger.get("flowguard_work_orders", {}).values():
            if order.get("subject_id") == packet["packet_id"] and order.get("decision") == "pass":
                chain.append({"kind": "flowguard", "id": order["order_id"]})
    return chain


def router_next_action(ledger: Mapping[str, Any]) -> RuntimeAction:
    if ledger.get("active_route_version") is None:
        return RuntimeAction("create_route", "no active route exists")

    active_route = ledger["active_route_version"]
    active_packets = [
        packet
        for packet in ledger.get("packets", {}).values()
        if packet["envelope"]["route_version"] == active_route
    ]
    if not active_packets:
        return RuntimeAction("issue_task_packet", "active route has no task packets", responsibility="worker")

    for packet in active_packets:
        if packet["status"] == "open":
            return RuntimeAction(
                "lease_agent",
                "packet has no assigned lease",
                packet["packet_id"],
                packet["envelope"]["responsibility"],
            )
        lease_id = packet.get("assigned_lease_id", "")
        lease = ledger.get("leases", {}).get(lease_id)
        if lease and lease.get("status") != "active":
            return RuntimeAction("replace_lease", "assigned lease is inactive", packet["packet_id"])
        if lease and not lease.get("ack_received"):
            return RuntimeAction("wait_for_ack", "assigned lease has not acknowledged", packet["packet_id"])
        if packet["status"] == "acknowledged":
            return RuntimeAction("wait_for_result", "ACK is liveness only", packet["packet_id"])
        if packet["status"] in {"result_blocked", "review_blocked"}:
            return RuntimeAction("repair_packet", "packet result or review is blocked", packet["packet_id"])
        if packet["status"] == "result_submitted":
            required_target = packet["envelope"]["required_flowguard_target"]
            if not _has_matching_flowguard_report(ledger, packet["packet_id"], required_target):
                return RuntimeAction(
                    "create_flowguard_order",
                    "result needs matching FlowGuard evidence",
                    packet["packet_id"],
                    "flowguard_operator",
                    required_target,
                )
            return RuntimeAction("review_result", "result needs independent review", packet["packet_id"], "reviewer")

    if ledger.get("closure", {}).get("decision") == "complete":
        return RuntimeAction("terminal_complete", "final backward chain is complete")
    return RuntimeAction("close_project", "all active packets are accepted")


def render_console(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Return public status without sealed task or result bodies."""

    packet_rows = []
    for packet in ledger.get("packets", {}).values():
        envelope = packet["envelope"]
        packet_rows.append(
            {
                "packet_id": packet["packet_id"],
                "status": packet["status"],
                "route_version": envelope["route_version"],
                "responsibility": envelope["responsibility"],
                "objective": envelope["objective"],
                "body_hash": envelope["body_hash"],
                "sealed_body_hidden": True,
                "accepted_result_id": packet.get("accepted_result_id", ""),
            }
        )

    return {
        "project_id": ledger.get("project_id"),
        "goal": ledger.get("goal"),
        "active_route_version": ledger.get("active_route_version"),
        "source_generation": ledger.get("source_generation"),
        "next_action": router_next_action(ledger).to_json(),
        "packets": packet_rows,
        "leases": [
            {
                "lease_id": lease["lease_id"],
                "agent_id": lease["agent_id"],
                "responsibility": lease["responsibility"],
                "status": lease["status"],
                "ack_received": lease["ack_received"],
                "packet_id": lease.get("packet_id", ""),
            }
            for lease in ledger.get("leases", {}).values()
        ],
        "flowguard": [
            {
                "order_id": order["order_id"],
                "modeled_target": order["modeled_target"],
                "selected_skill": order["selected_skill"],
                "subject_id": order["subject_id"],
                "status": order["status"],
                "decision": order["decision"],
            }
            for order in ledger.get("flowguard_work_orders", {}).values()
        ],
        "closure": _copy_jsonable(ledger.get("closure") or {"decision": "not_attempted"}),
    }


def _require(mapping: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise BlackBoxRuntimeError(f"unknown {label}: {key}")
    return value
