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
import re
from typing import Any, Mapping


SCHEMA_VERSION = "black_box_flowpilot_runtime.v1"
DEFAULT_PROJECT_ID = "project-001"
REQUIRED_FLOWGUARD_TARGET = "development_process"
RESPONSIBILITIES = {
    "planner",
    "pm",
    "worker",
    "research_worker",
    "reviewer",
    "flowguard_operator",
    "validator",
    "closure_officer",
    "ui_qa",
}

EVENT_FAMILY_BY_TYPE = {
    "project_started": "lifecycle",
    "startup_intake_recorded": "startup",
    "route_created": "route",
    "route_nodes_materialized": "route",
    "execution_frontier_updated": "route",
    "route_node_accepted": "route",
    "pm_disposition_recorded": "route",
    "final_route_wide_gate_ledger_built": "closure",
    "source_generation_changed": "route",
    "contract_frozen": "route",
    "route_drafted": "route",
    "lease_created": "lease",
    "lease_closed": "lease",
    "lease_expired": "lease",
    "lease_superseded": "lease",
    "resume_requested": "lifecycle",
    "responsibility_lease_created": "lease",
    "role_memory_seed_recorded": "lease",
    "task_packet_issued": "packet",
    "packet_assigned": "packet",
    "sealed_packet_body_opened": "packet",
    "lease_ack": "lease",
    "lease_progress": "lease",
    "result_submitted": "packet",
    "flowguard_work_order_created": "flowguard",
    "flowguard_work_order_completed": "flowguard",
    "result_reviewed": "review",
    "validation_evidence_recorded": "validation",
    "old_artifact_imported": "migration",
    "cutover_gate_evaluated": "migration",
    "cockpit_event_submitted": "ui",
    "final_closure_attempted": "closure",
    "completion_claim_recorded": "closure",
}

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
            "event_family": EVENT_FAMILY_BY_TYPE.get(event_type, "unknown"),
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
        "contract_frozen": False,
        "contract_hash": "",
        "startup_intake": None,
        "source_generation": 1,
        "lifecycle": {"state": "created"},
        "active_route_version": None,
        "route_mutations": [],
        "routes": {},
        "route_nodes": {},
        "execution_frontier": None,
        "pm_dispositions": {},
        "node_closures": {},
        "final_route_wide_gate_ledger": None,
        "recursive_route_execution_required": False,
        "leases": {},
        "packets": {},
        "results": {},
        "reviews": {},
        "flowguard_work_orders": {},
        "validation_evidence": {},
        "host_driver_state": {},
        "host_evidence": {},
        "imported_evidence": {},
        "cutover_gate": None,
        "user_events": [],
        "status_projection": None,
        "display_surface": {"preferred": "cockpit", "active": "unknown", "fallback_reason": ""},
        "completion_claims": [],
        "open_resources": [],
        "residual_risks": [],
        "old_ui_evidence": [],
        "closure": None,
        "events": [],
        "counters": {},
    }
    _event(ledger, "project_started", project_id=project_id)
    return ledger


def freeze_contract(ledger: dict[str, Any]) -> None:
    ledger["contract_frozen"] = True
    ledger["contract_hash"] = hash_text(f"{ledger['goal']}\n{ledger['acceptance_contract']}")
    ledger["lifecycle"] = {"state": "contract_frozen"}
    _event(ledger, "contract_frozen", contract_hash=ledger["contract_hash"])


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
    if not ledger.get("contract_frozen"):
        freeze_contract(ledger)

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
        "contract_hash": ledger.get("contract_hash", ""),
    }
    ledger["active_route_version"] = new_version
    if old_version is not None:
        mutation = {
            "mutation_id": _next_id(ledger, "mutation"),
            "old_route_version": old_version,
            "new_route_version": new_version,
            "reason": "route_replaced",
            "affected_packets": [],
            "requires_replay_or_rebinding": True,
            "created_at": now_iso(),
        }
        ledger.setdefault("route_mutations", []).append(mutation)

    for packet in ledger["packets"].values():
        if packet["envelope"]["route_version"] != new_version and packet["status"] in {
            "open",
            "assigned",
            "acknowledged",
            "result_submitted",
        }:
            packet["status"] = "quarantined_after_route_mutation"
            packet["old_route_disposition"] = "quarantined"
            if old_version is not None:
                mutation["affected_packets"].append(packet["packet_id"])

    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    return route_id


def draft_route(ledger: dict[str, Any], summary: str, steps: list[str], *, reason: str = "") -> str:
    if not summary.strip():
        raise BlackBoxRuntimeError("route summary is required")
    if not steps:
        raise BlackBoxRuntimeError("route needs at least one step")
    draft_id = _next_id(ledger, "route_draft")
    ledger.setdefault("route_drafts", {})[draft_id] = {
        "draft_id": draft_id,
        "summary": summary,
        "steps": list(steps),
        "reason": reason,
        "status": "draft",
        "created_at": now_iso(),
        "contract_hash": ledger.get("contract_hash", ""),
    }
    _event(ledger, "route_drafted", draft_id=draft_id)
    return draft_id


def record_source_change(ledger: dict[str, Any], reason: str) -> int:
    ledger["source_generation"] = int(ledger.get("source_generation", 1)) + 1
    _event(ledger, "source_generation_changed", reason=reason, generation=ledger["source_generation"])
    return ledger["source_generation"]


def recursive_route_required(ledger: Mapping[str, Any]) -> bool:
    return bool(ledger.get("recursive_route_execution_required"))


def materialize_route_from_planning_result(
    ledger: dict[str, Any],
    planning_result_id: str,
    *,
    nodes: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Create executable route nodes and initialize the frontier from a PM plan."""

    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot materialize route nodes without an active route")
    route_version = int(ledger["active_route_version"])
    plan_result = ledger.get("results", {}).get(planning_result_id, {})
    plan_text = str(plan_result.get("body", ""))
    node_specs = nodes or _extract_route_nodes(plan_text)
    if not node_specs:
        active_route = ledger.get("routes", {}).get(str(route_version), {})
        node_specs = _fallback_route_nodes(active_route.get("steps") or [])

    route_nodes: dict[str, Any] = ledger.setdefault("route_nodes", {})
    materialized_ids: list[str] = []
    for index, spec in enumerate(node_specs, start=1):
        node_id = str(spec.get("node_id") or f"node-{index:03d}")
        title = str(spec.get("title") or spec.get("summary") or f"Route node {index}")
        criteria = spec.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria:
            criteria = [f"Node '{title}' has current accepted work, FlowGuard evidence, review, validation, and PM disposition."]
        route_nodes[node_id] = {
            "node_id": node_id,
            "route_version": route_version,
            "title": title,
            "node_kind": str(spec.get("node_kind") or "leaf"),
            "parent_node_id": str(spec.get("parent_node_id") or ""),
            "child_node_ids": list(spec.get("child_node_ids") or []),
            "responsibility": _normalize_node_responsibility(str(spec.get("responsibility") or "")),
            "modeled_target": _normalize_modeled_target(str(spec.get("modeled_target") or ""), title),
            "acceptance_criteria": [str(item) for item in criteria],
            "status": "pending",
            "packet_ids": [],
            "accepted_result_id": "",
            "flowguard_order_ids": [],
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "superseded_by": "",
            "stale_evidence": [],
            "created_from_result_id": planning_result_id,
            "created_at": now_iso(),
        }
        materialized_ids.append(node_id)

    active_route = ledger["routes"].get(str(route_version), {})
    active_route["node_order"] = materialized_ids
    active_route["route_materialized_from_result_id"] = planning_result_id
    active_route["route_materialized"] = True
    ledger["execution_frontier"] = {
        "active_route_version": route_version,
        "active_node_id": materialized_ids[0] if materialized_ids else "",
        "completed_nodes": [],
        "status": "node_execution" if materialized_ids else "blocked",
        "pending_route_mutation": None,
        "blocked_reason": "" if materialized_ids else "route_materialization_empty",
        "updated_at": now_iso(),
    }
    _event(
        ledger,
        "route_nodes_materialized",
        route_version=route_version,
        planning_result_id=planning_result_id,
        node_ids=materialized_ids,
    )
    _event(ledger, "execution_frontier_updated", status=ledger["execution_frontier"]["status"], active_node_id=ledger["execution_frontier"]["active_node_id"])
    return materialized_ids


def ensure_next_node_task_packet(ledger: dict[str, Any]) -> str:
    frontier = ledger.get("execution_frontier") or {}
    node_id = str(frontier.get("active_node_id") or "")
    if not node_id:
        raise BlackBoxRuntimeError("execution frontier has no active node")
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    if node.get("status") in {"accepted", "superseded", "waived"}:
        raise BlackBoxRuntimeError(f"route node is not executable: {node_id}")
    existing = _open_or_live_node_task_packet(ledger, node_id)
    if existing:
        return str(existing["packet_id"])
    packet_id = issue_task_packet(
        ledger,
        str(node["responsibility"]),
        f"Execute route node {node_id}: {node['title']}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.node_task_packet.v1",
                "route_node_id": node_id,
                "title": node["title"],
                "modeled_target": node["modeled_target"],
                "acceptance_criteria": node["acceptance_criteria"],
                "instruction": "Complete this bounded route node. Return concrete current-run evidence.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_output_type="artifact",
        required_flowguard_target=str(node["modeled_target"]),
        route_node_id=node_id,
        route_scope="node",
        acceptance_criteria=list(node["acceptance_criteria"]),
    )
    node["packet_ids"].append(packet_id)
    node["status"] = "running"
    frontier["status"] = "node_execution"
    frontier["updated_at"] = now_iso()
    _event(ledger, "execution_frontier_updated", status="node_execution", active_node_id=node_id)
    return packet_id


def record_pm_disposition(
    ledger: dict[str, Any],
    node_id: str,
    result_id: str,
    *,
    decision: str = "accept",
    reason: str = "",
) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    disposition_id = _next_id(ledger, "pm_disposition")
    normalized = decision if decision in {"accept", "repair", "mutate_route", "block", "stop"} else "accept"
    ledger.setdefault("pm_dispositions", {})[disposition_id] = {
        "disposition_id": disposition_id,
        "node_id": node_id,
        "result_id": result_id,
        "decision": normalized,
        "reason": reason,
        "route_version": ledger.get("active_route_version"),
        "created_at": now_iso(),
    }
    node["pm_disposition_id"] = disposition_id
    if normalized == "accept":
        node["status"] = "accepted"
        _advance_frontier_after_node_acceptance(ledger, node_id)
        _event(ledger, "route_node_accepted", node_id=node_id, disposition_id=disposition_id)
    elif normalized == "mutate_route":
        _mutate_route_for_node(ledger, node_id, disposition_id=disposition_id, reason=reason or "pm_disposition_mutate_route")
    elif normalized == "repair":
        node["status"] = "repair_required"
        _frontier_update(ledger, node_id, "repair_required", reason or "pm_disposition_repair")
    else:
        node["status"] = "blocked" if normalized == "block" else "stopped"
        _frontier_update(ledger, node_id, node["status"], reason or f"pm_disposition_{normalized}")
    _event(ledger, "pm_disposition_recorded", node_id=node_id, disposition_id=disposition_id, decision=normalized)
    return disposition_id


def build_final_route_wide_gate_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    nodes = list(ledger.get("route_nodes", {}).values())
    effective_nodes = [node for node in nodes if node.get("status") != "superseded"]
    unresolved: list[str] = []
    stale: list[str] = []
    for node in effective_nodes:
        node_id = str(node.get("node_id", ""))
        if node.get("status") not in {"accepted", "waived"}:
            unresolved.append(f"incomplete_node:{node_id}")
        if node.get("stale_evidence"):
            stale.append(node_id)
    for packet in ledger.get("packets", {}).values():
        if packet.get("status") not in {"accepted", "quarantined_after_route_mutation"}:
            unresolved.append(f"packet_not_accepted:{packet['packet_id']}")
    if ledger.get("open_resources"):
        unresolved.append("unresolved_resources")
    if ledger.get("residual_risks"):
        unresolved.append("unresolved_residual_risks")
    if ledger.get("old_ui_evidence"):
        unresolved.append("old_ui_evidence_unresolved")
    ledger_record = {
        "schema_version": "black_box_flowpilot.final_route_wide_gate_ledger.v1",
        "route_version": ledger.get("active_route_version"),
        "effective_node_ids": [str(node.get("node_id", "")) for node in effective_nodes],
        "accepted_node_ids": [str(node.get("node_id", "")) for node in effective_nodes if node.get("status") == "accepted"],
        "superseded_node_ids": [str(node.get("node_id", "")) for node in nodes if node.get("status") == "superseded"],
        "unresolved": sorted(set(unresolved)),
        "stale_node_ids": sorted(set(stale)),
        "unresolved_count": len(set(unresolved)),
        "created_at": now_iso(),
    }
    ledger["final_route_wide_gate_ledger"] = ledger_record
    _event(ledger, "final_route_wide_gate_ledger_built", unresolved_count=ledger_record["unresolved_count"])
    return ledger_record


def _extract_route_nodes(plan_text: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for line in plan_text.splitlines():
        stripped = line.strip()
        match = re.match(r"^(?:[-*]\s*)?(\d+)[.)]\s+(.+)$", stripped)
        if not match:
            continue
        title = match.group(2).strip()
        if not title:
            continue
        nodes.append(
            {
                "node_id": f"node-{len(nodes) + 1:03d}",
                "title": title[:160],
                "responsibility": _responsibility_for_title(title),
                "modeled_target": _normalize_modeled_target("", title),
                "acceptance_criteria": [f"Complete and validate: {title[:180]}"],
            }
        )
    return nodes[:8]


def _fallback_route_nodes(steps: list[Any]) -> list[dict[str, Any]]:
    titles = [str(step) for step in steps if str(step).strip()]
    if len(titles) < 3:
        titles = [
            "Plan executable route and acceptance boundaries",
            "Execute implementation or target project work",
            "Validate evidence and prepare final closure",
        ]
    return [
        {
            "node_id": f"node-{index:03d}",
            "title": title[:160],
            "responsibility": _responsibility_for_title(title),
            "modeled_target": _normalize_modeled_target("", title),
            "acceptance_criteria": [f"Complete and validate: {title[:180]}"],
        }
        for index, title in enumerate(titles[:8], start=1)
    ]


def _responsibility_for_title(title: str) -> str:
    lower = title.lower()
    if any(token in lower for token in ("review", "inspect", "audit")):
        return "reviewer"
    if any(token in lower for token in ("ui", "screenshot", "visual", "interaction", "cockpit")):
        return "ui_qa"
    if any(token in lower for token in ("research", "source", "material")):
        return "research_worker"
    return "worker"


def _normalize_node_responsibility(responsibility: str) -> str:
    if responsibility in RESPONSIBILITIES and responsibility not in {"planner", "closure_officer", "validator", "flowguard_operator"}:
        return responsibility
    return "worker"


def _normalize_modeled_target(modeled_target: str, title: str) -> str:
    if modeled_target in _route_table():
        return modeled_target
    lower = title.lower()
    if any(token in lower for token in ("ui", "visual", "screenshot", "interaction", "cockpit", "window", "tray")):
        return "ui_interaction_flow"
    if any(token in lower for token in ("architecture", "module", "adapter", "structure")):
        return "code_structure_plan"
    if any(token in lower for token in ("test", "validation", "evidence", "qa", "regression")):
        return "test_and_evidence_hierarchy"
    if any(token in lower for token in ("miss", "failure", "repair", "bug")):
        return "model_miss"
    return "development_process"


def _open_or_live_node_task_packet(ledger: Mapping[str, Any], node_id: str) -> dict[str, Any] | None:
    for packet in ledger.get("packets", {}).values():
        envelope = packet.get("envelope", {})
        if envelope.get("packet_kind", "task") != "task":
            continue
        if envelope.get("route_node_id") != node_id:
            continue
        if packet.get("status") not in {"accepted", "quarantined_after_route_mutation", "result_blocked", "review_blocked"}:
            return packet
    return None


def _record_node_closure(ledger: dict[str, Any], node_id: str, result_id: str) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    closure_id = _next_id(ledger, "node_closure")
    ledger.setdefault("node_closures", {})[closure_id] = {
        "closure_id": closure_id,
        "node_id": node_id,
        "result_id": result_id,
        "status": "awaiting_pm_disposition",
        "created_at": now_iso(),
    }
    node["closure_id"] = closure_id
    node["status"] = "awaiting_pm_disposition"
    _frontier_update(ledger, node_id, "awaiting_pm_disposition", "")
    return closure_id


def _ensure_pm_disposition_packet_for_node(ledger: dict[str, Any], node_id: str, subject_packet_id: str) -> str:
    existing = _find_packet(ledger, packet_kind="pm_disposition", subject_id=subject_packet_id)
    if existing:
        return str(existing["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    return issue_task_packet(
        ledger,
        "pm",
        f"Record PM disposition for route node {node_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_disposition_packet.v1",
                "route_node_id": node_id,
                "subject_packet_id": subject_packet_id,
                "instruction": "Return a PM disposition. Default valid decision is accept; other valid decisions are repair, mutate_route, block, or stop.",
            },
            indent=2,
            sort_keys=True,
        ),
        packet_kind="pm_disposition",
        required_flowguard_target="",
        subject_id=subject_packet_id,
        route_node_id=node_id,
        route_scope="node_pm_disposition",
        acceptance_criteria=list(node.get("acceptance_criteria") or []),
    )


def _decision_from_pm_body(body: str) -> tuple[str, str]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        decision = str(payload.get("decision") or payload.get("pm_disposition") or "accept")
        reason = str(payload.get("reason") or payload.get("summary") or "")
        return decision, reason
    lowered = body.lower()
    for decision in ("mutate_route", "repair", "block", "stop", "accept"):
        if decision in lowered:
            return decision, body[:240]
    return "accept", body[:240]


def _advance_frontier_after_node_acceptance(ledger: dict[str, Any], node_id: str) -> None:
    frontier = ledger.get("execution_frontier") or {}
    completed = list(frontier.get("completed_nodes") or [])
    if node_id not in completed:
        completed.append(node_id)
    frontier["completed_nodes"] = completed
    route = ledger.get("routes", {}).get(str(frontier.get("active_route_version") or ledger.get("active_route_version")), {})
    node_order = [str(item) for item in route.get("node_order") or ledger.get("route_nodes", {}).keys()]
    next_node = ""
    for candidate in node_order:
        node = ledger.get("route_nodes", {}).get(candidate, {})
        if node.get("status") not in {"accepted", "superseded", "waived"}:
            next_node = candidate
            break
    frontier["active_node_id"] = next_node
    frontier["status"] = "node_execution" if next_node else "ready_for_final_closure"
    frontier["updated_at"] = now_iso()
    ledger["execution_frontier"] = frontier
    _event(ledger, "execution_frontier_updated", status=frontier["status"], active_node_id=next_node)
    if next_node:
        ensure_next_node_task_packet(ledger)
    else:
        build_final_route_wide_gate_ledger(ledger)
        attempt_final_closure(ledger, str(ledger.get("latest_validation_evidence_id") or "route-wide-validation"))


def _frontier_update(ledger: dict[str, Any], node_id: str, status: str, blocked_reason: str) -> None:
    frontier = ledger.setdefault("execution_frontier", {})
    frontier["active_node_id"] = node_id
    frontier["status"] = status
    frontier["blocked_reason"] = blocked_reason
    frontier["updated_at"] = now_iso()
    _event(ledger, "execution_frontier_updated", status=status, active_node_id=node_id)


def _mutate_route_for_node(ledger: dict[str, Any], node_id: str, *, disposition_id: str, reason: str) -> None:
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    replacement_id = f"{node_id}-repair-v{new_version}"
    affected_packets: list[str] = []
    for packet in ledger.get("packets", {}).values():
        if packet.get("envelope", {}).get("route_node_id") == node_id and packet.get("status") != "accepted":
            packet["status"] = "quarantined_after_route_mutation"
            packet["old_route_disposition"] = "quarantined"
            affected_packets.append(packet["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    node["status"] = "superseded"
    node["superseded_by"] = replacement_id
    node["stale_evidence"].append(disposition_id)
    replacement = dict(node)
    replacement.update(
        {
            "node_id": replacement_id,
            "route_version": new_version,
            "title": f"Repair {node['title']}",
            "status": "pending",
            "packet_ids": [],
            "accepted_result_id": "",
            "flowguard_order_ids": [],
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "superseded_by": "",
            "stale_evidence": [],
            "created_at": now_iso(),
        }
    )
    ledger["route_nodes"][replacement_id] = replacement
    route = dict(ledger.get("routes", {}).get(str(old_version), {}))
    node_order = [replacement_id if item == node_id else item for item in route.get("node_order", [])]
    route.update(
        {
            "route_version": new_version,
            "route_id": f"route-v{new_version}",
            "status": "active",
            "node_order": node_order or [replacement_id],
            "created_at": now_iso(),
        }
    )
    ledger["routes"][str(new_version)] = route
    ledger["active_route_version"] = new_version
    mutation = {
        "mutation_id": _next_id(ledger, "mutation"),
        "old_route_version": old_version,
        "new_route_version": new_version,
        "reason": reason,
        "disposition_id": disposition_id,
        "superseded_node_ids": [node_id],
        "replacement_node_id": replacement_id,
        "affected_packets": affected_packets,
        "requires_replay_or_rebinding": True,
        "created_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(mutation)
    ledger["execution_frontier"] = {
        "active_route_version": new_version,
        "active_node_id": replacement_id,
        "completed_nodes": [item for item in (ledger.get("execution_frontier") or {}).get("completed_nodes", []) if item != node_id],
        "status": "node_execution",
        "pending_route_mutation": mutation,
        "blocked_reason": "",
        "updated_at": now_iso(),
    }
    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    _event(ledger, "execution_frontier_updated", status="node_execution", active_node_id=replacement_id)
    ensure_next_node_task_packet(ledger)


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


def supersede_lease(ledger: dict[str, Any], lease_id: str, replacement_lease_id: str, reason: str = "replaced") -> None:
    lease = _require(ledger["leases"], lease_id, "lease")
    replacement = _require(ledger["leases"], replacement_lease_id, "lease")
    if lease["responsibility"] != replacement["responsibility"]:
        raise BlackBoxRuntimeError("replacement lease responsibility mismatch")
    lease["status"] = "superseded"
    lease["closed_at"] = now_iso()
    lease["close_reason"] = reason
    lease["superseded_by"] = replacement_lease_id
    _event(ledger, "lease_superseded", lease_id=lease_id, replacement_lease_id=replacement_lease_id, reason=reason)


def issue_task_packet(
    ledger: dict[str, Any],
    responsibility: str,
    objective: str,
    body: str,
    *,
    allowed_tools: list[str] | None = None,
    required_output_type: str = "artifact",
    required_flowguard_target: str = REQUIRED_FLOWGUARD_TARGET,
    packet_kind: str = "task",
    subject_id: str = "",
    target_result_id: str = "",
    preassigned_packet_id: str = "",
    route_node_id: str = "",
    route_scope: str = "",
    acceptance_criteria: list[str] | None = None,
) -> str:
    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot issue a packet without an active route")
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    packet_id = preassigned_packet_id or _next_id(ledger, "packet")
    body_hash = hash_text(body)
    envelope = {
        "packet_id": packet_id,
        "packet_kind": packet_kind,
        "route_version": ledger["active_route_version"],
        "responsibility": responsibility,
        "objective": objective,
        "subject_id": subject_id,
        "target_result_id": target_result_id,
        "allowed_tools": list(allowed_tools or []),
        "required_output_type": required_output_type,
        "required_reviewer": "independent",
        "required_flowguard_target": required_flowguard_target,
        "route_node_id": route_node_id,
        "route_scope": route_scope,
        "acceptance_criteria": list(acceptance_criteria or []),
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
    _event(ledger, "task_packet_issued", packet_id=packet_id, responsibility=responsibility, packet_kind=packet_kind)
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
    packet_body_hash: str | None = None,
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
        packet_body_hash=packet_body_hash,
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
        "non_authoritative": bool(blockers),
        "quarantine_reason": ",".join(blockers) if blockers else "",
        "envelope": {
            "packet_id": packet_id,
            "result_id": result_id,
            "route_version": packet["envelope"]["route_version"],
            "output_type": output_type,
            "evidence_ids": list(evidence_ids or []),
            "evidence_generation": generation,
            "body_hash": body_hash,
            "body_visibility": "sealed",
            "referenced_packet_body_hash": packet_body_hash or packet["envelope"]["body_hash"],
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
    if not blockers:
        _apply_valid_packet_result(ledger, packet, result, lease)
    return result_id


def _apply_valid_packet_result(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: dict[str, Any],
) -> None:
    packet_kind = packet["envelope"].get("packet_kind", "task")
    if packet_kind == "task":
        close_lease(ledger, lease["lease_id"], "result_submitted")
        _ensure_flowguard_packet_for_task_result(ledger, packet, result)
        return
    if packet_kind == "flowguard_check":
        _accept_packet_result(ledger, packet, result, lease, reason="flowguard_result_submitted")
        _record_flowguard_from_packet_result(ledger, packet, result)
        _ensure_review_packet_for_task_result(ledger, packet["envelope"]["subject_id"])
        return
    if packet_kind == "review":
        _record_review_from_packet_result(ledger, packet, result)
        _accept_packet_result(ledger, packet, result, lease, reason="review_result_submitted")
        _ensure_validation_packet_for_task(ledger, packet["envelope"]["subject_id"])
        return
    if packet_kind == "validation":
        _accept_packet_result(ledger, packet, result, lease, reason="validation_result_submitted")
        evidence_id = f"validation-{result['result_id']}"
        record_validation_evidence(ledger, evidence_id)
        ledger["latest_validation_evidence_id"] = evidence_id
        subject_packet = ledger.get("packets", {}).get(packet["envelope"].get("subject_id", ""), {})
        node_id = str((subject_packet.get("envelope", {}) if isinstance(subject_packet, dict) else {}).get("route_node_id") or "")
        if node_id and node_id in ledger.get("route_nodes", {}):
            ledger["route_nodes"][node_id].setdefault("validation_evidence_ids", []).append(evidence_id)
        _ensure_closure_packet_for_task(ledger, packet["envelope"]["subject_id"])
        return
    if packet_kind == "closure":
        _accept_packet_result(ledger, packet, result, lease, reason="closure_result_submitted")
        _apply_closure_result_side_effect(ledger, packet, result)
        return
    if packet_kind == "pm_disposition":
        _accept_packet_result(ledger, packet, result, lease, reason="pm_disposition_submitted")
        node_id = str(packet["envelope"].get("route_node_id") or "")
        if not node_id:
            raise BlackBoxRuntimeError("PM disposition packet is missing route_node_id")
        decision, reason = _decision_from_pm_body(str(result.get("body", "")))
        record_pm_disposition(ledger, node_id, result["result_id"], decision=decision, reason=reason)
        return
    raise BlackBoxRuntimeError(f"unknown packet kind: {packet_kind}")


def _apply_closure_result_side_effect(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    subject_packet_id = str(packet["envelope"].get("subject_id") or "")
    subject_packet = ledger.get("packets", {}).get(subject_packet_id, {})
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet, dict) else {}
    route_scope = str(subject_envelope.get("route_scope") or "")
    node_id = str(subject_envelope.get("route_node_id") or packet["envelope"].get("route_node_id") or "")
    if recursive_route_required(ledger) and route_scope == "planning":
        materialize_route_from_planning_result(ledger, str(subject_packet.get("accepted_result_id") or packet["envelope"].get("target_result_id") or ""))
        ensure_next_node_task_packet(ledger)
        return
    if recursive_route_required(ledger) and node_id:
        _record_node_closure(ledger, node_id, str(result["result_id"]))
        _ensure_pm_disposition_packet_for_node(ledger, node_id, subject_packet_id)
        return
    evidence_id = str(ledger.get("latest_validation_evidence_id") or f"validation-{result['result_id']}")
    attempt_final_closure(ledger, evidence_id)


def _accept_packet_result(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: dict[str, Any],
    *,
    reason: str,
) -> None:
    result["status"] = "accepted"
    result["accepted"] = True
    packet["status"] = "accepted"
    packet["accepted_result_id"] = result["result_id"]
    close_lease(ledger, lease["lease_id"], reason)


def _find_packet(
    ledger: Mapping[str, Any],
    *,
    packet_kind: str,
    subject_id: str,
    target_result_id: str = "",
) -> dict[str, Any] | None:
    for packet in ledger.get("packets", {}).values():
        envelope = packet.get("envelope", {})
        if envelope.get("packet_kind", "task") != packet_kind:
            continue
        if envelope.get("subject_id", "") != subject_id:
            continue
        if target_result_id and envelope.get("target_result_id", "") != target_result_id:
            continue
        if packet.get("status") == "quarantined_after_route_mutation":
            continue
        return packet
    return None


def _ensure_flowguard_packet_for_task_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    subject_id = str(packet["packet_id"])
    existing = _find_packet(ledger, packet_kind="flowguard_check", subject_id=subject_id, target_result_id=str(result["result_id"]))
    if existing:
        return str(existing["packet_id"])
    flowguard_packet_id = _next_id(ledger, "packet")
    evidence_root = _flowguard_packet_evidence_root(ledger, flowguard_packet_id)
    return issue_task_packet(
        ledger,
        "flowguard_operator",
        f"Run FlowGuard evidence for {subject_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.flowguard_packet.v1",
                "subject_packet_id": subject_id,
                "target_result_id": result["result_id"],
                "modeled_target": packet["envelope"]["required_flowguard_target"],
                "instruction": "Produce current-run FlowGuard evidence for the subject packet result.",
                "evidence_output_policy": {
                    "run_local_evidence_root": evidence_root,
                    "required_for_formal_run": True,
                    "tracked_baseline_paths_forbidden_unless_explicit_baseline_update": [
                        "simulations/meta_thin_parent_results.json",
                        "simulations/meta_layered_full_results.json",
                        "simulations/capability_thin_parent_results.json",
                        "simulations/capability_layered_full_results.json",
                    ],
                    "operator_rule": (
                        "Write formal-run FlowGuard evidence under run_local_evidence_root. "
                        "Do not write formal-run evidence to tracked simulations/*_results.json baselines "
                        "unless the packet explicitly requests a baseline refresh."
                    ),
                },
                "recommended_runner_commands": [
                    f"python simulations/run_meta_checks.py --fast --json-out {evidence_root}/meta_thin_parent_results.json",
                    f"python simulations/run_capability_checks.py --fast --json-out {evidence_root}/capability_thin_parent_results.json",
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="",
        packet_kind="flowguard_check",
        subject_id=subject_id,
        target_result_id=str(result["result_id"]),
        preassigned_packet_id=flowguard_packet_id,
        route_node_id=str(packet["envelope"].get("route_node_id") or ""),
        route_scope=str(packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(packet["envelope"].get("acceptance_criteria") or []),
    )


def _flowguard_packet_evidence_root(ledger: Mapping[str, Any], packet_id: str) -> str:
    run_id = str(ledger.get("run_id") or "<run-id>")
    relative_root = f".flowpilot/runs/{run_id}/evidence/flowguard/{packet_id}"
    run_root = ledger.get("run_root")
    if not run_root:
        return relative_root
    return (Path(str(run_root)) / "evidence" / "flowguard" / packet_id).as_posix()


def _record_flowguard_from_packet_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    subject_id = str(packet["envelope"]["subject_id"])
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    modeled_target = subject_packet["envelope"]["required_flowguard_target"]
    order_id = create_flowguard_work_order(ledger, modeled_target, "done_claim", subject_id)
    order = ledger["flowguard_work_orders"][order_id]
    order["officer_lease_id"] = result["producer_lease_id"]
    order["packet_id"] = packet["packet_id"]
    order["producer_result_id"] = result["result_id"]
    node_id = str(subject_packet["envelope"].get("route_node_id") or "")
    complete_flowguard_work_order(ledger, order_id, evidence_id=result["result_id"])
    order["proof_artifact"] = result["result_id"]
    order["confidence_boundary"] = "current_run_packet"
    if node_id and node_id in ledger.get("route_nodes", {}):
        ledger["route_nodes"][node_id].setdefault("flowguard_order_ids", []).append(order_id)
    return order_id


def _ensure_review_packet_for_task_result(ledger: dict[str, Any], subject_id: str) -> str:
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    target_result_id = str((subject_packet.get("result_ids") or [""])[-1])
    existing = _find_packet(ledger, packet_kind="review", subject_id=subject_id, target_result_id=target_result_id)
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "reviewer",
        f"Review result and FlowGuard evidence for {subject_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.review_packet.v1",
                "subject_packet_id": subject_id,
                "target_result_id": target_result_id,
                "instruction": "Review the subject result and matching FlowGuard evidence independently.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="",
        packet_kind="review",
        subject_id=subject_id,
        target_result_id=target_result_id,
        route_node_id=str(subject_packet["envelope"].get("route_node_id") or ""),
        route_scope=str(subject_packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(subject_packet["envelope"].get("acceptance_criteria") or []),
    )


def _record_review_from_packet_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    subject_id = str(packet["envelope"]["subject_id"])
    target_result_id = str(packet["envelope"]["target_result_id"])
    review_id = review_result(
        ledger,
        target_result_id,
        result["producer_lease_id"],
        decision="accept",
        checks_evidence=True,
        direct_evidence_ids=[result["result_id"]],
        pm_routing_decision="accept_result",
    )
    review = ledger["reviews"][review_id]
    review["review_packet_id"] = packet["packet_id"]
    review["review_packet_result_id"] = result["result_id"]
    review["subject_packet_id"] = subject_id
    node_id = str((ledger.get("packets", {}).get(subject_id, {}).get("envelope", {}) or {}).get("route_node_id") or "")
    if node_id and node_id in ledger.get("route_nodes", {}):
        ledger["route_nodes"][node_id].setdefault("review_ids", []).append(review_id)
        ledger["route_nodes"][node_id]["accepted_result_id"] = target_result_id
    return review_id


def _ensure_validation_packet_for_task(ledger: dict[str, Any], subject_id: str) -> str:
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    existing = _find_packet(ledger, packet_kind="validation", subject_id=subject_id)
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "validator",
        f"Record validation evidence for {subject_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.validation_packet.v1",
                "subject_packet_id": subject_id,
                "instruction": "Record current validation evidence for the accepted subject packet.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="",
        packet_kind="validation",
        subject_id=subject_id,
        route_node_id=str(subject_packet["envelope"].get("route_node_id") or ""),
        route_scope=str(subject_packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(subject_packet["envelope"].get("acceptance_criteria") or []),
    )


def _ensure_closure_packet_for_task(ledger: dict[str, Any], subject_id: str) -> str:
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    existing = _find_packet(ledger, packet_kind="closure", subject_id=subject_id)
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "closure_officer",
        f"Perform final backward closure for {subject_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.closure_packet.v1",
                "subject_packet_id": subject_id,
                "validation_evidence_id": ledger.get("latest_validation_evidence_id", ""),
                "instruction": "Confirm final backward chain and close only if all required packet evidence is current.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="",
        packet_kind="closure",
        subject_id=subject_id,
        route_node_id=str(subject_packet["envelope"].get("route_node_id") or ""),
        route_scope=str(subject_packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(subject_packet["envelope"].get("acceptance_criteria") or []),
    )


def _result_mechanical_blockers(
    ledger: Mapping[str, Any],
    *,
    lease: Mapping[str, Any],
    packet: Mapping[str, Any],
    output_type: str,
    evidence_generation: int,
    valid_shape: bool,
    packet_body_hash: str | None,
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
    if packet_body_hash is not None and packet_body_hash != packet["envelope"]["body_hash"]:
        blockers.append("body_hash_mismatch")
    if packet.get("accepted_result_id"):
        blockers.append("duplicate_after_packet_accepted")
    same_lease_results = [
        result
        for result in ledger.get("results", {}).values()
        if result.get("packet_id") == packet["packet_id"]
        and result.get("producer_lease_id") == lease["lease_id"]
        and result.get("status") == "mechanically_valid"
    ]
    if same_lease_results:
        blockers.append("duplicate_output_from_same_lease")
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
        "proof_artifact": "",
        "confidence_boundary": "scoped",
        "officer_lease_id": "",
        "pm_decision": "",
        "proof_stale": False,
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
    order["proof_artifact"] = evidence_id
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
    direct_evidence_ids: list[str] | None = None,
    waivers: list[str] | None = None,
    pm_routing_decision: str = "",
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
        "direct_evidence_ids": list(direct_evidence_ids or []),
        "waivers": list(waivers or []),
        "pm_routing_decision": pm_routing_decision,
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
    if recursive_route_required(ledger):
        build_final_route_wide_gate_ledger(ledger)
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
    if closure["decision"] == "complete" and recursive_route_required(ledger):
        frontier = dict(ledger.get("execution_frontier") or {})
        if frontier:
            frontier["status"] = "complete"
            frontier["active_node_id"] = ""
            frontier["updated_at"] = now_iso()
            ledger["execution_frontier"] = frontier
            _event(ledger, "execution_frontier_updated", status="complete", active_node_id="")
    _event(ledger, "final_closure_attempted", decision=closure["decision"], blockers=blockers)
    return closure


def record_resume_request(ledger: dict[str, Any], reason: str = "manual_resume") -> None:
    ledger["lifecycle"] = {"state": "resume_requested", "reason": reason}
    _event(ledger, "resume_requested", reason=reason)


def record_completion_claim(ledger: dict[str, Any], *, source: str, claim: str, evidence_id: str = "") -> None:
    ledger.setdefault("completion_claims", []).append(
        {"source": source, "claim": claim, "evidence_id": evidence_id, "created_at": now_iso()}
    )
    _event(ledger, "completion_claim_recorded", source=source, evidence_id=evidence_id)


def _closure_blockers(
    ledger: Mapping[str, Any],
    *,
    validation_evidence_id: str,
    required_flowguard_target: str,
) -> list[str]:
    blockers: list[str] = []
    if not ledger.get("goal"):
        blockers.append("missing_goal")
    if ledger.get("completion_claims") and not ledger.get("closure_confirmed_by_backward_replay"):
        blockers.append("completion_report_only_not_sufficient")
    if ledger.get("open_resources"):
        blockers.append("unresolved_resources")
    if ledger.get("residual_risks"):
        blockers.append("unresolved_residual_risks")
    if ledger.get("old_ui_evidence"):
        blockers.append("old_ui_evidence_unresolved")
    if recursive_route_required(ledger):
        route_wide = ledger.get("final_route_wide_gate_ledger")
        if not isinstance(route_wide, dict):
            blockers.append("missing_final_route_wide_gate_ledger")
        else:
            for item in route_wide.get("unresolved", []):
                blockers.append(str(item))
            if int(route_wide.get("unresolved_count", 0)) != 0:
                blockers.append("final_route_wide_gate_ledger_unresolved")
        frontier = ledger.get("execution_frontier") or {}
        if frontier.get("active_node_id"):
            blockers.append(f"frontier_has_active_node:{frontier.get('active_node_id')}")
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
        if packet["envelope"].get("packet_kind", "task") != "task":
            continue
        result = ledger["results"][packet["accepted_result_id"]]
        review = ledger["reviews"].get(result.get("review_id", ""))
        if not review or review.get("decision") != "accept":
            blockers.append(f"missing_independent_review:{packet['packet_id']}")
        packet_required_target = packet["envelope"].get("required_flowguard_target") or required_flowguard_target
        if packet_required_target and not _has_matching_flowguard_report(ledger, packet["packet_id"], packet_required_target):
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
        if not order.get("proof_artifact"):
            continue
        if order.get("proof_stale"):
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
        chain.append({"kind": "packet", "id": packet["packet_id"], "packet_kind": packet["envelope"].get("packet_kind", "task")})
        chain.append({"kind": "result", "id": result["result_id"]})
        if result.get("review_id"):
            chain.append({"kind": "review", "id": result["review_id"]})
        if packet["envelope"].get("packet_kind", "task") == "task":
            for order in ledger.get("flowguard_work_orders", {}).values():
                if order.get("subject_id") == packet["packet_id"] and order.get("decision") == "pass":
                    chain.append({"kind": "flowguard", "id": order["order_id"]})
    return chain


def router_next_action(ledger: Mapping[str, Any]) -> RuntimeAction:
    lifecycle = ledger.get("lifecycle") or {}
    if lifecycle.get("state") == "paused":
        return RuntimeAction("wait_for_resume", "run is paused by user")
    if lifecycle.get("state") == "resume_requested":
        return RuntimeAction("resume_reconcile", "resume request needs current-run reconciliation")
    if not ledger.get("contract_frozen"):
        return RuntimeAction("freeze_contract", "acceptance contract is not frozen")
    if ledger.get("active_route_version") is None:
        if not ledger.get("route_drafts"):
            return RuntimeAction("draft_route", "no active route exists")
        return RuntimeAction("activate_route", "route draft needs activation")

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
        if packet["status"] in {"assigned", "acknowledged"}:
            lease_id = packet.get("assigned_lease_id", "")
            lease = ledger.get("leases", {}).get(lease_id)
            if lease and lease.get("status") != "active":
                return RuntimeAction("replace_lease", "assigned lease is inactive", packet["packet_id"])
            if lease and not lease.get("ack_received"):
                return RuntimeAction("wait_for_ack", "assigned lease has not acknowledged", packet["packet_id"])
            if packet["status"] == "acknowledged":
                return RuntimeAction("wait_for_result", "ACK is liveness only", packet["packet_id"])

    for packet in active_packets:
        if packet["status"] in {"result_blocked", "review_blocked"}:
            return RuntimeAction("repair_packet", "packet result or review is blocked", packet["packet_id"])
        if packet["status"] == "result_submitted" and packet["envelope"].get("packet_kind", "task") == "task":
            required_target = packet["envelope"]["required_flowguard_target"]
            has_flowguard_packet = _find_packet(
                ledger,
                packet_kind="flowguard_check",
                subject_id=packet["packet_id"],
            )
            if not _has_matching_flowguard_report(ledger, packet["packet_id"], required_target) and not has_flowguard_packet:
                return RuntimeAction(
                    "issue_flowguard_packet",
                    "result needs a FlowGuard work packet",
                    packet["packet_id"],
                    "flowguard_operator",
                    required_target,
                )
            has_review_packet = _find_packet(
                ledger,
                packet_kind="review",
                subject_id=packet["packet_id"],
            )
            if _has_matching_flowguard_report(ledger, packet["packet_id"], required_target) and not has_review_packet:
                return RuntimeAction("issue_review_packet", "result needs a Reviewer work packet", packet["packet_id"], "reviewer")

    if recursive_route_required(ledger):
        frontier = ledger.get("execution_frontier") or {}
        node_id = str(frontier.get("active_node_id") or "")
        if not ledger.get("route_nodes"):
            return RuntimeAction("materialize_route_nodes", "PM planning chain must materialize route nodes before closure")
        if node_id:
            node = ledger.get("route_nodes", {}).get(node_id, {})
            if node.get("status") == "awaiting_pm_disposition":
                return RuntimeAction("issue_pm_disposition_packet", "node awaits PM disposition", node_id, "pm")
            if node.get("status") not in {"accepted", "superseded", "waived"}:
                return RuntimeAction("issue_node_task_packet", "frontier has an incomplete route node", node_id, node.get("responsibility", "worker"), node.get("modeled_target", ""))
        if frontier.get("status") == "ready_for_final_closure" and not (ledger.get("closure") or {}).get("decision") == "complete":
            return RuntimeAction("close_project", "all route nodes are resolved; final route-wide closure is required")

    closure = ledger.get("closure") or {}
    if closure.get("decision") == "complete":
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
                "packet_kind": envelope.get("packet_kind", "task"),
                "status": packet["status"],
                "route_version": envelope["route_version"],
                "responsibility": envelope["responsibility"],
                "objective": envelope["objective"],
                "subject_id": envelope.get("subject_id", ""),
                "target_result_id": envelope.get("target_result_id", ""),
                "route_node_id": envelope.get("route_node_id", ""),
                "route_scope": envelope.get("route_scope", ""),
                "body_hash": envelope["body_hash"],
                "sealed_body_hidden": True,
                "accepted_result_id": packet.get("accepted_result_id", ""),
            }
        )

    return {
        "project_id": ledger.get("project_id"),
        "goal": ledger.get("goal"),
        "lifecycle": _copy_jsonable(ledger.get("lifecycle") or {}),
        "route_stage": _route_stage(ledger),
        "active_route_version": ledger.get("active_route_version"),
        "source_generation": ledger.get("source_generation"),
        "next_action": router_next_action(ledger).to_json(),
        "sealed_bodies_visible": False,
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
        "validation_evidence": [
            {
                "evidence_id": evidence["evidence_id"],
                "status": evidence["status"],
                "source_generation": evidence["source_generation"],
            }
            for evidence in ledger.get("validation_evidence", {}).values()
        ],
        "host_evidence": list(ledger.get("host_evidence", {}).values()),
        "route_nodes": [
            {
                "node_id": node.get("node_id", ""),
                "route_version": node.get("route_version"),
                "title": node.get("title", ""),
                "status": node.get("status", ""),
                "responsibility": node.get("responsibility", ""),
                "modeled_target": node.get("modeled_target", ""),
                "packet_ids": list(node.get("packet_ids", [])),
                "pm_disposition_id": node.get("pm_disposition_id", ""),
                "sealed_bodies_visible": False,
            }
            for node in ledger.get("route_nodes", {}).values()
        ],
        "execution_frontier": _copy_jsonable(ledger.get("execution_frontier") or {}),
        "final_route_wide_gate_ledger": _copy_jsonable(ledger.get("final_route_wide_gate_ledger") or {"decision": "not_built"}),
        "cutover_gate": _copy_jsonable(ledger.get("cutover_gate") or {"decision": "not_evaluated"}),
        "display_surface": _copy_jsonable(ledger.get("display_surface") or {}),
        "closure": _copy_jsonable(ledger.get("closure") or {"decision": "not_attempted"}),
    }


def _route_stage(ledger: Mapping[str, Any]) -> str:
    if not ledger.get("startup_intake"):
        return "startup_intake"
    if not ledger.get("contract_frozen"):
        return "contract_freeze"
    if ledger.get("active_route_version") is None:
        return "route_planning"
    if recursive_route_required(ledger):
        frontier = ledger.get("execution_frontier") or {}
        if not ledger.get("route_nodes"):
            return "route_materialization"
        if frontier.get("active_node_id"):
            return "recursive_node_execution"
        if frontier.get("status") == "ready_for_final_closure":
            return "route_wide_closure"
    if any(packet.get("status") not in {"accepted", "quarantined_after_route_mutation"} for packet in ledger.get("packets", {}).values()):
        return "packet_execution"
    cutover_gate = ledger.get("cutover_gate") or {}
    if cutover_gate.get("decision") == "blocked":
        return "cutover_repair"
    if (ledger.get("closure") or {}).get("decision") == "complete":
        return "complete"
    return "closure"


def _require(mapping: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise BlackBoxRuntimeError(f"unknown {label}: {key}")
    return value
