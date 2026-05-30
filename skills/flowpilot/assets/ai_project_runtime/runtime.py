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

try:  # pragma: no cover - direct module test fallback.
    from . import control_surface
except ImportError:  # pragma: no cover
    import control_surface  # type: ignore


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
    "ui_qa",
}
PACKET_KINDS = {
    "task",
    "flowguard_check",
    "review",
    "pm_repair_decision",
    "pm_disposition",
}

PREPLANNING_GATE_SCOPES = {
    "high_standard_contract",
    "discovery",
    "skill_standard",
}

EVENT_FAMILY_BY_TYPE = {
    "project_started": "lifecycle",
    "lifecycle_guard_refreshed": "lifecycle",
    "startup_intake_recorded": "startup",
    "route_created": "route",
    "route_nodes_materialized": "route",
    "execution_frontier_updated": "route",
    "route_node_accepted": "route",
    "high_standard_contract_accepted": "planning",
    "discovery_record_accepted": "planning",
    "skill_standard_contract_accepted": "planning",
    "node_acceptance_plan_accepted": "route",
    "same_node_repair_prepared": "route",
    "parent_backward_replay_accepted": "route",
    "final_requirement_evidence_matrix_built": "closure",
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
    "resume_reconciled": "lifecycle",
    "run_stopped_by_user": "lifecycle",
    "run_cancelled_by_user": "lifecycle",
    "responsibility_lease_created": "lease",
    "role_memory_seed_recorded": "lease",
    "host_liveness_recorded": "lease",
    "orphan_evidence_detected": "validation",
    "task_packet_issued": "packet",
    "packet_assigned": "packet",
    "sealed_packet_body_opened": "packet",
    "lease_ack": "lease",
    "lease_progress": "lease",
    "accepted_packet_assignment_repaired": "packet",
    "result_submitted": "packet",
    "packet_outcome_recorded": "packet",
    "semantic_blocker_recorded": "repair",
    "semantic_blocker_cleared": "repair",
    "pm_repair_decision_recorded": "repair",
    "pm_repair_decision_blocked": "repair",
    "pm_decision_gate_staged": "repair",
    "pm_decision_gate_applied": "repair",
    "repair_reissue_packet_issued": "repair",
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

_GUARD_HISTORY_LIMIT = 50
_GUARD_STUCK_TRIGGERS = {"patrol", "resume"}
_FOREGROUND_DUTY_HISTORY_LIMIT = 50
_DEFAULT_WAIT_PATROL_SECONDS = 60
_WAIT_ACK_REMINDER_SECONDS = 180
_WAIT_ACK_BLOCKER_SECONDS = 600
_WAIT_RESULT_LIVENESS_SECONDS = 600
_WAIT_PROGRESS_GRACE_SECONDS = 600
_WAIT_PATROL_DECISIONS = {"wait_for_ack", "wait_for_result"}
_RECOVERY_DUTY_DECISIONS = {
    "reissue_or_replace_lease",
    "quarantine_stale_result",
    "recover_packet",
    "repair_assignment_race",
    "recover_orphan_evidence",
}
_WAIT_LIVENESS_FAILURE_STATUSES = {
    "missing",
    "cancelled",
    "not_found",
    "unknown",
    "unresponsive",
    "blocked",
    "lost",
    "timeout_unknown",
}
_WAIT_NO_OUTPUT_STATUSES = {
    "no_output",
    "alive_no_output",
    "not_working_no_output",
    "completed",
    "completed_without_result",
    "completed_without_expected_event",
}
_HOST_LIVENESS_STATUSES = (
    _WAIT_LIVENESS_FAILURE_STATUSES
    | _WAIT_NO_OUTPUT_STATUSES
    | {
        "active",
        "still_working",
        "working",
        "progressing",
        "acknowledged",
    }
)
TERMINAL_LIFECYCLE_STATUSES = {"stopped_by_user", "cancelled_by_user"}
_STALE_RESULT_BLOCKERS = {
    "closed_or_inactive_lease",
    "quarantined_packet",
    "stale_route_version",
    "stale_evidence",
    "wrong_lease_for_packet",
    "duplicate_after_packet_accepted",
}

ROUTER_INTERNAL_ACTION_TYPES = {
    "freeze_contract",
    "activate_route",
    "issue_task_packet",
    "issue_preplanning_gate_packet",
    "materialize_route_nodes",
    "issue_node_acceptance_plan_packet",
    "issue_node_task_packet",
    "issue_parent_backward_replay_packet",
    "issue_flowguard_packet",
    "issue_review_packet",
    "issue_pm_repair_decision_packet",
    "issue_pm_disposition_packet",
    "close_project",
}
ROLE_DISPATCH_ACTION_TYPES = {"lease_agent"}
ROLE_WAIT_ACTION_TYPES = {"wait_for_ack", "wait_for_result"}
RECOVERY_ACTION_TYPES = {"replace_lease", "repair_accepted_packet", "repair_packet"}
USER_REQUIRED_ACTION_TYPES = {"open_startup_intake", "wait_for_resume", "resume_reconcile", "repair_cutover_gate"}
TERMINAL_ACTION_TYPES = {"terminal_complete", "terminal_lifecycle"}
RUN_UNTIL_WAIT_MAX_STEPS = 50


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


def classify_runtime_action(action: RuntimeAction | Mapping[str, Any]) -> str:
    """Return the foreground boundary class for a runtime action."""

    if isinstance(action, RuntimeAction):
        action_type = action.action_type
    else:
        action_type = str(action.get("action_type") or "")
    if action_type in ROUTER_INTERNAL_ACTION_TYPES:
        return "router_internal"
    if action_type in ROLE_DISPATCH_ACTION_TYPES:
        return "role_dispatch"
    if action_type in ROLE_WAIT_ACTION_TYPES:
        return "role_wait"
    if action_type in RECOVERY_ACTION_TYPES:
        return "recovery"
    if action_type in USER_REQUIRED_ACTION_TYPES:
        return "user_required"
    if action_type in TERMINAL_ACTION_TYPES:
        return "terminal"
    return "controller_external"


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
        "lifecycle_guard": {
            "schema_version": "black_box_flowpilot.lifecycle_guard.v1",
            "decision": "not_refreshed",
            "controller_stop_allowed": False,
        },
        "lifecycle_guard_history": [],
        "lifecycle_guard_config": {
            "max_repeated_action_without_event": 3,
            "ack_reminder_seconds": _WAIT_ACK_REMINDER_SECONDS,
            "ack_blocker_seconds": _WAIT_ACK_BLOCKER_SECONDS,
            "result_liveness_seconds": _WAIT_RESULT_LIVENESS_SECONDS,
            "progress_grace_seconds": _WAIT_PROGRESS_GRACE_SECONDS,
        },
        "foreground_duty": {
            "schema_version": "black_box_flowpilot.foreground_duty.v1",
            "action": "not_refreshed",
            "final_return_preflight": {"allowed": False, "blockers": ["not_refreshed"]},
        },
        "foreground_duty_history": [],
        "foreground_duty_config": {"wait_patrol_seconds": _DEFAULT_WAIT_PATROL_SECONDS},
        "active_route_version": None,
        "route_mutations": [],
        "routes": {},
        "route_nodes": {},
        "execution_frontier": None,
        "high_standard_control_flow_required": False,
        "high_standard_contract": None,
        "preplanning_discovery": None,
        "skill_standard_contract": None,
        "node_acceptance_plans": {},
        "parent_backward_replays": {},
        "final_requirement_evidence_matrix": None,
        "pm_dispositions": {},
        "node_closures": {},
        "final_route_wide_gate_ledger": None,
        "recursive_route_execution_required": False,
        "leases": {},
        "packets": {},
        "results": {},
        "packet_outcomes": {},
        "active_blockers": {},
        "pm_repair_decisions": {},
        "pm_decision_gates": {},
        "repair_transactions": {},
        "reviews": {},
        "flowguard_work_orders": {},
        "validation_evidence": {},
        "system_closures": {},
        "host_driver_state": {},
        "host_evidence": {},
        "host_liveness_reports": {},
        "orphan_evidence": {},
        "terminal_lifecycle": None,
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


def terminal_lifecycle_status(ledger: Mapping[str, Any]) -> str:
    lifecycle = ledger.get("lifecycle") if isinstance(ledger.get("lifecycle"), Mapping) else {}
    status = str(lifecycle.get("status") or lifecycle.get("state") or "")
    if status in TERMINAL_LIFECYCLE_STATUSES:
        return status
    terminal = ledger.get("terminal_lifecycle") if isinstance(ledger.get("terminal_lifecycle"), Mapping) else {}
    status = str(terminal.get("status") or terminal.get("state") or "")
    return status if status in TERMINAL_LIFECYCLE_STATUSES else ""


def _is_terminal_lifecycle(ledger: Mapping[str, Any]) -> bool:
    return bool(terminal_lifecycle_status(ledger))


def _assert_not_terminal_lifecycle(ledger: Mapping[str, Any]) -> None:
    status = terminal_lifecycle_status(ledger)
    if status:
        raise BlackBoxRuntimeError(f"run is terminal ({status}); new work is not allowed")


def record_terminal_lifecycle(
    ledger: dict[str, Any],
    status: str,
    *,
    reason: str = "",
    actor: str = "controller",
) -> dict[str, Any]:
    if status not in TERMINAL_LIFECYCLE_STATUSES:
        raise BlackBoxRuntimeError(f"unsupported terminal lifecycle status: {status}")
    recorded_at = now_iso()
    record = {
        "schema_version": "black_box_flowpilot.terminal_lifecycle.v1",
        "state": status,
        "status": status,
        "terminal": True,
        "reason": reason,
        "actor": actor,
        "recorded_at": recorded_at,
        "controller_stop_allowed": True,
        "closure_required": False,
    }
    ledger["lifecycle"] = dict(record)
    ledger["terminal_lifecycle"] = dict(record)

    for lease_id, lease in list(ledger.get("leases", {}).items()):
        if isinstance(lease, Mapping) and lease.get("status") == "active":
            close_lease(ledger, str(lease_id), status)

    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, dict):
            continue
        if packet.get("accepted_result_id"):
            continue
        if packet.get("status") in {
            "open",
            "assigned",
            "acknowledged",
            "result_submitted",
            "result_blocked",
            "review_blocked",
            "system_validation_blocked",
            "flowguard_blocked",
        }:
            packet["status"] = status
            packet["terminal_lifecycle_status"] = status
            packet["terminal_lifecycle_reason"] = reason

    frontier = ledger.get("execution_frontier")
    if isinstance(frontier, dict):
        frontier["status"] = status
        frontier["terminal"] = True
        frontier["terminal_reason"] = reason
        frontier["updated_at"] = recorded_at

    event_type = "run_stopped_by_user" if status == "stopped_by_user" else "run_cancelled_by_user"
    _event(ledger, event_type, status=status, reason=reason, actor=actor)
    return record


def create_route(ledger: dict[str, Any], summary: str, steps: list[str]) -> str:
    _assert_not_terminal_lifecycle(ledger)
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


def high_standard_flow_required(ledger: Mapping[str, Any]) -> bool:
    return bool(ledger.get("high_standard_control_flow_required"))


def _gate_accepted(ledger: Mapping[str, Any], key: str) -> bool:
    record = ledger.get(key)
    return isinstance(record, dict) and record.get("status") == "accepted"


def preplanning_gates_accepted(ledger: Mapping[str, Any]) -> bool:
    if not high_standard_flow_required(ledger):
        return True
    return (
        _gate_accepted(ledger, "high_standard_contract")
        and _gate_accepted(ledger, "preplanning_discovery")
        and _gate_accepted(ledger, "skill_standard_contract")
    )


def _blocking_high_standard_requirements(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = ledger.get("high_standard_contract")
    if not isinstance(contract, dict):
        return []
    rows = contract.get("requirements")
    if not isinstance(rows, list):
        return []
    blocking = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("closure_blocking", True):
            blocking.append(row)
    return blocking


def _required_skill_obligations(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = ledger.get("skill_standard_contract")
    if not isinstance(contract, dict):
        return []
    rows = contract.get("obligations")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("closure_blocking", True)]


def _find_live_scope_packet(
    ledger: Mapping[str, Any],
    route_scope: str,
    *,
    route_node_id: str = "",
    packet_kind: str = "task",
) -> dict[str, Any] | None:
    for packet in ledger.get("packets", {}).values():
        envelope = packet.get("envelope", {})
        if envelope.get("packet_kind", "task") != packet_kind:
            continue
        if envelope.get("route_scope") != route_scope:
            continue
        if route_node_id and envelope.get("route_node_id") != route_node_id:
            continue
        if packet.get("status") not in {"accepted", "quarantined_after_route_mutation", "result_blocked", "review_blocked"}:
            return packet
    return None


def _accepted_task_packet_for_scope(
    ledger: Mapping[str, Any],
    route_scope: str,
    *,
    route_node_id: str = "",
) -> dict[str, Any] | None:
    for packet in ledger.get("packets", {}).values():
        envelope = packet.get("envelope", {})
        if envelope.get("packet_kind", "task") != "task":
            continue
        if envelope.get("route_scope") != route_scope:
            continue
        if route_node_id and envelope.get("route_node_id") != route_node_id:
            continue
        if packet.get("status") == "accepted" and packet.get("accepted_result_id"):
            return packet
    return None


def ensure_preplanning_gate_packet(ledger: dict[str, Any]) -> str:
    if not high_standard_flow_required(ledger):
        return ""
    if not _gate_accepted(ledger, "high_standard_contract"):
        return _ensure_high_standard_contract_packet(ledger)
    if not _gate_accepted(ledger, "preplanning_discovery"):
        return _ensure_discovery_packet(ledger)
    if not _gate_accepted(ledger, "skill_standard_contract"):
        return _ensure_skill_standard_packet(ledger)
    return _ensure_planning_packet(ledger)


def _ensure_high_standard_contract_packet(ledger: dict[str, Any]) -> str:
    existing = _find_live_scope_packet(ledger, "high_standard_contract")
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "pm",
        "Write PM high-standard completion contract",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.high_standard_contract_packet.v1",
                "instruction": (
                    "Turn the sealed startup request into the highest reasonable current-run completion "
                    "standard. Classify each row as hard_current, high_standard_current, optional_current, "
                    "future_suggestion, or rejected_expansion."
                ),
                "required_output": {
                    "requirements": [
                        {
                            "requirement_id": "hsr-001",
                            "classification": "hard_current",
                            "summary": "Current run must complete the user's actual requested outcome.",
                            "closure_blocking": True,
                        }
                    ]
                },
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="development_process",
        route_scope="high_standard_contract",
        acceptance_criteria=[
            "Hard/current requirements are explicit.",
            "Optional and future improvements do not silently become hard blockers.",
        ],
    )


def _ensure_discovery_packet(ledger: dict[str, Any]) -> str:
    existing = _find_live_scope_packet(ledger, "discovery")
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "pm",
        "Record current material and local skill discovery",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.discovery_packet.v1",
                "instruction": (
                    "Record current-run material discovery and local skill inventory before route planning. "
                    "Skill inventory is candidate-only; material summaries are navigation, not acceptance proof."
                ),
                "required_sections": [
                    "material_sources",
                    "material_sufficiency",
                    "local_skill_inventory",
                    "candidate_only_skill_policy",
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="development_process",
        route_scope="discovery",
        acceptance_criteria=[
            "Material sufficiency is stated from current-run sources.",
            "Local skill inventory is candidate-only and not route authority.",
        ],
    )


def _ensure_skill_standard_packet(ledger: dict[str, Any]) -> str:
    existing = _find_live_scope_packet(ledger, "skill_standard")
    if existing:
        return str(existing["packet_id"])
    return issue_task_packet(
        ledger,
        "pm",
        "Select skills and write skill standard obligations",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.skill_standard_packet.v1",
                "instruction": (
                    "Select only required or conditional child/process-support skills and convert each selected "
                    "skill into reviewer-checkable evidence obligations."
                ),
                "default_required_obligation": {
                    "obligation_id": "skill-std-001",
                    "skill": "flowguard-development-process-flow",
                    "role_use": "pm_or_flowguard_operator",
                    "use_context": "planning_validation_or_repair",
                    "evidence_required": "current-run FlowGuard work order/report evidence",
                    "closure_blocking": True,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="development_process",
        route_scope="skill_standard",
        acceptance_criteria=[
            "Selected skills have explicit evidence obligations.",
            "Rejected or deferred skills have reasons when material to the route.",
        ],
    )


def _ensure_planning_packet(ledger: dict[str, Any]) -> str:
    existing = _find_live_scope_packet(ledger, "planning")
    if existing:
        return str(existing["packet_id"])
    if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
        raise BlackBoxRuntimeError("PM planning packet requires accepted high-standard preplanning gates")
    body = json.dumps(
        {
            "schema_version": "black_box_flowpilot.pm_startup_packet.v1",
            "instruction": "Open the sealed startup body through the current-run packet boundary and plan the project route.",
            "startup_intake_ref": _startup_body_ref_from_ledger(ledger),
            "high_standard_contract_id": (ledger.get("high_standard_contract") or {}).get("contract_id", ""),
            "discovery_id": (ledger.get("preplanning_discovery") or {}).get("discovery_id", ""),
            "skill_standard_contract_id": (ledger.get("skill_standard_contract") or {}).get("contract_id", ""),
            "old_runtime_authority": "forbidden",
        },
        indent=2,
        sort_keys=True,
    )
    return issue_task_packet(
        ledger,
        "pm",
        "Plan and execute the sealed startup request with the new FlowPilot runtime",
        body,
        required_output_type="artifact",
        required_flowguard_target="development_process",
        route_scope="planning",
        acceptance_criteria=[
            "PM route plan uses the accepted high-standard contract and discovery records.",
            "PM route plan is reviewed and then materialized into route nodes.",
            "Project closure is blocked until every effective route node is accepted.",
        ],
    )


def _startup_body_ref_from_ledger(ledger: Mapping[str, Any]) -> dict[str, str]:
    intake = ledger.get("startup_intake") or {}
    run_paths = intake.get("run_paths") if isinstance(intake, dict) else {}
    return {
        "body_path": str((run_paths or {}).get("body", "")),
        "body_hash": str(intake.get("body_hash", "")) if isinstance(intake, dict) else "",
        "visibility": "sealed_pm_only",
    }


def materialize_route_from_planning_result(
    ledger: dict[str, Any],
    planning_result_id: str,
    *,
    nodes: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Create executable route nodes and initialize the frontier from a PM plan."""

    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot materialize route nodes without an active route")
    if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
        raise BlackBoxRuntimeError("cannot materialize route nodes before high-standard preplanning gates")
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
            "repair_generation": 0,
            "packet_ids": [],
            "accepted_result_id": "",
            "accepted_repair_generation": None,
            "flowguard_order_ids": [],
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "node_acceptance_plan_id": "",
            "parent_backward_replay_id": "",
            "parent_backward_waiver": "",
            "high_standard_requirement_ids": [],
            "skill_standard_obligation_ids": [],
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
    if high_standard_flow_required(ledger) and not _node_acceptance_plan_accepted(ledger, node_id):
        raise BlackBoxRuntimeError(f"route node requires accepted node acceptance plan before task packet: {node_id}")
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
                "node_acceptance_plan_id": node.get("node_acceptance_plan_id", ""),
                "repair_generation": int(node.get("repair_generation", 0)),
                "high_standard_requirement_ids": list(node.get("high_standard_requirement_ids") or []),
                "skill_standard_obligation_ids": list(node.get("skill_standard_obligation_ids") or []),
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


def _node_acceptance_plan_accepted(ledger: Mapping[str, Any], node_id: str) -> bool:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    plan_id = str(node.get("node_acceptance_plan_id") or "") if isinstance(node, dict) else ""
    if not plan_id:
        return False
    plan = ledger.get("node_acceptance_plans", {}).get(plan_id, {})
    return isinstance(plan, dict) and plan.get("status") == "accepted" and plan.get("node_id") == node_id


def ensure_node_acceptance_plan_packet(ledger: dict[str, Any], node_id: str) -> str:
    if _node_acceptance_plan_accepted(ledger, node_id):
        return ""
    existing = _find_live_scope_packet(ledger, "node_acceptance_plan", route_node_id=node_id)
    if existing:
        return str(existing["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    return issue_task_packet(
        ledger,
        "pm",
        f"Write node acceptance plan for {node_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.node_acceptance_plan_packet.v1",
                "route_node_id": node_id,
                "title": node.get("title", ""),
                "acceptance_criteria": list(node.get("acceptance_criteria") or []),
                "high_standard_requirement_ids": [
                    str(row.get("requirement_id", ""))
                    for row in _blocking_high_standard_requirements(ledger)
                    if row.get("requirement_id")
                ],
                "skill_standard_obligation_ids": [
                    str(row.get("obligation_id", ""))
                    for row in _required_skill_obligations(ledger)
                    if row.get("obligation_id")
                ],
                "instruction": (
                    "Define this node's proof obligations, low-quality-success risks, selected skill evidence, "
                    "and repair policy before any worker task packet is issued."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="development_process",
        route_scope="node_acceptance_plan",
        route_node_id=node_id,
        acceptance_criteria=[
            "Node proof obligations are explicit.",
            "Same-node repair is the default for ordinary quality, evidence, test, or skill-use gaps.",
        ],
    )


def _node_requires_parent_backward_replay(node: Mapping[str, Any]) -> bool:
    return bool(node.get("child_node_ids")) or str(node.get("node_kind") or "") in {"parent", "module"}


def _parent_backward_replay_accepted(ledger: Mapping[str, Any], node_id: str) -> bool:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    if isinstance(node, dict) and node.get("parent_backward_waiver"):
        return True
    replay_id = str(node.get("parent_backward_replay_id") or "") if isinstance(node, dict) else ""
    if not replay_id:
        return False
    replay = ledger.get("parent_backward_replays", {}).get(replay_id, {})
    return isinstance(replay, dict) and replay.get("status") == "accepted" and replay.get("node_id") == node_id


def ensure_parent_backward_replay_packet(ledger: dict[str, Any], node_id: str) -> str:
    if _parent_backward_replay_accepted(ledger, node_id):
        return ""
    existing = _find_live_scope_packet(ledger, "parent_backward_replay", route_node_id=node_id)
    if existing:
        return str(existing["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    return issue_task_packet(
        ledger,
        "reviewer",
        f"Replay parent/module node {node_id} backward from child outcomes",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.parent_backward_replay_packet.v1",
                "route_node_id": node_id,
                "child_node_ids": list(node.get("child_node_ids") or []),
                "instruction": (
                    "Check whether the accepted children compose into the parent goal. "
                    "Do not pass from child existence alone."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target="development_process",
        route_scope="parent_backward_replay",
        route_node_id=node_id,
        acceptance_criteria=[
            "Effective children compose into the parent/module goal.",
            "Missing child classes, stale evidence, or thin child outputs are reported.",
        ],
    )


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
        if high_standard_flow_required(ledger) and _node_requires_parent_backward_replay(node) and not _parent_backward_replay_accepted(ledger, node_id):
            node["status"] = "awaiting_parent_backward_replay"
            _frontier_update(ledger, node_id, "awaiting_parent_backward_replay", "parent_backward_replay_required")
            ensure_parent_backward_replay_packet(ledger, node_id)
            _event(ledger, "pm_disposition_recorded", node_id=node_id, disposition_id=disposition_id, decision=normalized)
            return disposition_id
        node["status"] = "accepted"
        _advance_frontier_after_node_acceptance(ledger, node_id)
        _event(ledger, "route_node_accepted", node_id=node_id, disposition_id=disposition_id)
    elif normalized == "mutate_route":
        _mutate_route_for_node(ledger, node_id, disposition_id=disposition_id, reason=reason or "pm_disposition_mutate_route")
    elif normalized == "repair":
        _prepare_same_node_repair(ledger, node_id, disposition_id=disposition_id, reason=reason or "pm_disposition_repair")
    else:
        node["status"] = "blocked" if normalized == "block" else "stopped"
        _frontier_update(ledger, node_id, node["status"], reason or f"pm_disposition_{normalized}")
    _event(ledger, "pm_disposition_recorded", node_id=node_id, disposition_id=disposition_id, decision=normalized)
    return disposition_id


def _prepare_same_node_repair(ledger: dict[str, Any], node_id: str, *, disposition_id: str, reason: str) -> None:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    previous_evidence = [
        str(item)
        for item in (
            list(node.get("packet_ids") or [])
            + list(node.get("flowguard_order_ids") or [])
            + list(node.get("review_ids") or [])
            + list(node.get("validation_evidence_ids") or [])
            + ([node.get("accepted_result_id")] if node.get("accepted_result_id") else [])
        )
        if item
    ]
    node["repair_generation"] = int(node.get("repair_generation", 0)) + 1
    node["status"] = "repair_required"
    node["accepted_result_id"] = ""
    node["accepted_repair_generation"] = None
    node["closure_id"] = ""
    node.setdefault("stale_evidence", []).extend([disposition_id, *previous_evidence])
    _frontier_update(ledger, node_id, "repair_required", reason)
    _event(
        ledger,
        "same_node_repair_prepared",
        node_id=node_id,
        repair_generation=node["repair_generation"],
        stale_evidence=previous_evidence,
    )
    ensure_next_node_task_packet(ledger)


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


def build_final_requirement_evidence_matrix(ledger: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []

    def add_row(row_id: str, kind: str, status: str, evidence_ids: list[str], summary: str) -> None:
        rows.append(
            {
                "row_id": row_id,
                "kind": kind,
                "status": status,
                "evidence_ids": evidence_ids,
                "summary": summary,
            }
        )
        if status != "covered":
            unresolved.append(f"{kind}:{row_id}:{status}")

    if high_standard_flow_required(ledger):
        contract = ledger.get("high_standard_contract")
        if not _gate_accepted(ledger, "high_standard_contract"):
            add_row("high-standard-contract", "preplanning_gate", "missing", [], "PM high-standard contract is required")
        else:
            add_row(
                "high-standard-contract",
                "preplanning_gate",
                "covered",
                [str(contract.get("source_result_id", ""))],
                "PM high-standard contract accepted",
            )
        discovery = ledger.get("preplanning_discovery")
        if not _gate_accepted(ledger, "preplanning_discovery"):
            add_row("preplanning-discovery", "preplanning_gate", "missing", [], "Material and skill discovery is required")
        else:
            add_row(
                "preplanning-discovery",
                "preplanning_gate",
                "covered",
                [str(discovery.get("source_result_id", ""))],
                "Material discovery and candidate-only skill inventory accepted",
            )
        skill_contract = ledger.get("skill_standard_contract")
        if not _gate_accepted(ledger, "skill_standard_contract"):
            add_row("skill-standard-contract", "preplanning_gate", "missing", [], "Skill standard contract is required")
        else:
            add_row(
                "skill-standard-contract",
                "preplanning_gate",
                "covered",
                [str(skill_contract.get("source_result_id", ""))],
                "Selected skill standards accepted",
            )
        for requirement in _blocking_high_standard_requirements(ledger):
            requirement_id = str(requirement.get("requirement_id") or "unknown")
            covered_nodes = [
                str(node.get("node_id", ""))
                for node in ledger.get("route_nodes", {}).values()
                if requirement_id in list(node.get("high_standard_requirement_ids") or [])
                and node.get("status") in {"accepted", "waived"}
            ]
            add_row(
                requirement_id,
                "high_standard_requirement",
                "covered" if covered_nodes else "missing",
                covered_nodes,
                str(requirement.get("summary") or requirement_id),
            )
        for obligation in _required_skill_obligations(ledger):
            obligation_id = str(obligation.get("obligation_id") or "unknown")
            covered_nodes = [
                str(node.get("node_id", ""))
                for node in ledger.get("route_nodes", {}).values()
                if obligation_id in list(node.get("skill_standard_obligation_ids") or [])
                and node.get("status") in {"accepted", "waived"}
            ]
            add_row(
                obligation_id,
                "skill_standard_obligation",
                "covered" if covered_nodes else "missing",
                covered_nodes,
                str(obligation.get("skill") or obligation_id),
            )

    for node in ledger.get("route_nodes", {}).values():
        if node.get("status") == "superseded":
            continue
        node_id = str(node.get("node_id", ""))
        add_row(
            f"{node_id}:node-status",
            "route_node",
            "covered" if node.get("status") in {"accepted", "waived"} else "missing",
            [str(node.get("accepted_result_id", ""))] if node.get("accepted_result_id") else [],
            f"Node {node_id} accepted or waived",
        )
        if high_standard_flow_required(ledger):
            plan_id = str(node.get("node_acceptance_plan_id") or "")
            add_row(
                f"{node_id}:acceptance-plan",
                "node_acceptance_plan",
                "covered" if plan_id and _node_acceptance_plan_accepted(ledger, node_id) else "missing",
                [plan_id] if plan_id else [],
                f"Node {node_id} has accepted acceptance plan",
            )
            if _node_requires_parent_backward_replay(node):
                replay_id = str(node.get("parent_backward_replay_id") or node.get("parent_backward_waiver") or "")
                add_row(
                    f"{node_id}:parent-replay",
                    "parent_backward_replay",
                    "covered" if _parent_backward_replay_accepted(ledger, node_id) else "missing",
                    [replay_id] if replay_id else [],
                    f"Parent/module node {node_id} has backward replay or waiver",
                )
        add_row(
            f"{node_id}:pm-disposition",
            "pm_disposition",
            "covered" if node.get("pm_disposition_id") else "missing",
            [str(node.get("pm_disposition_id", ""))] if node.get("pm_disposition_id") else [],
            f"Node {node_id} has PM disposition",
        )
        add_row(
            f"{node_id}:flowguard",
            "flowguard",
            "covered" if node.get("flowguard_order_ids") else "missing",
            [str(item) for item in node.get("flowguard_order_ids") or []],
            f"Node {node_id} has FlowGuard evidence",
        )
        add_row(
            f"{node_id}:review",
            "review",
            "covered" if node.get("review_ids") else "missing",
            [str(item) for item in node.get("review_ids") or []],
            f"Node {node_id} has independent review evidence",
        )
        add_row(
            f"{node_id}:validation",
            "validation",
            "covered" if node.get("validation_evidence_ids") else "missing",
            [str(item) for item in node.get("validation_evidence_ids") or []],
            f"Node {node_id} has validation evidence",
        )

    matrix = {
        "schema_version": "black_box_flowpilot.final_requirement_evidence_matrix.v1",
        "status": "clean" if not unresolved else "blocked",
        "route_version": ledger.get("active_route_version"),
        "row_count": len(rows),
        "rows": rows,
        "unresolved": sorted(set(unresolved)),
        "unresolved_count": len(set(unresolved)),
        "created_at": now_iso(),
    }
    ledger["final_requirement_evidence_matrix"] = matrix
    _event(ledger, "final_requirement_evidence_matrix_built", unresolved_count=matrix["unresolved_count"])
    return matrix


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
    if responsibility in RESPONSIBILITIES and responsibility not in {"planner", "flowguard_operator"}:
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
        required_flowguard_target=REQUIRED_FLOWGUARD_TARGET,
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


_PASSING_OUTCOME_DECISIONS = {"accept", "accepted", "pass", "passed", "complete", "completed", "success", "ok"}
_BLOCKING_OUTCOME_DECISIONS = {
    "block",
    "blocked",
    "fail",
    "failed",
    "failure",
    "reject",
    "rejected",
    "needs_pm",
    "needs_more_evidence",
    "more_evidence_required",
    "partial_with_blockers",
    "stop",
    "stopped",
}
_NONPASS_TEXT_RE = re.compile(
    r"\b(block|blocked|fail|failed|failure|reject|rejected|needs[_ -]?pm|needs[_ -]?more[_ -]?evidence|partial[_ -]?with[_ -]?blockers)\b",
    re.IGNORECASE,
)
_PM_REPAIR_DECISIONS = {
    "same_node_repair",
    "sender_reissue",
    "collect_more_evidence",
    "mutate_route",
    "quarantine_evidence",
    "waive_with_authority",
    "stop_for_user",
}
_HIGH_RISK_PM_REPAIR_DECISIONS = {"mutate_route", "waive_with_authority"}
_HIGH_RISK_PM_DISPOSITION_DECISIONS = {"mutate_route"}
_PM_REPAIR_ALIASES = {
    "repair": "same_node_repair",
    "local_repair": "same_node_repair",
    "repair_local": "same_node_repair",
    "reissue": "sender_reissue",
    "request_sender_reissue": "sender_reissue",
    "more_evidence": "collect_more_evidence",
    "collect_evidence": "collect_more_evidence",
    "route_mutation": "mutate_route",
    "quarantine": "quarantine_evidence",
    "waive": "waive_with_authority",
}
_PM_REPAIR_DECISION_FIELD_RE = re.compile(
    r"(?:^|[\n;])\s*(decision|repair_decision|recovery_option)\s*[:=]\s*([A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)


def _json_payload_from_body(body: str) -> dict[str, Any] | None:
    stripped = body.strip()
    candidates = [stripped]
    if ":" in stripped:
        candidates.append(stripped.split(":", 1)[1].strip())
    for candidate in candidates:
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _normalize_outcome_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _payload_outcome_token(payload: Mapping[str, Any], packet_kind: str) -> str:
    if isinstance(payload.get("passed"), bool):
        return "pass" if payload["passed"] else "block"
    challenge = payload.get("independent_challenge")
    if isinstance(challenge, Mapping):
        nested = _normalize_outcome_token(challenge.get("pass_or_block"))
        if nested:
            return nested
    for key in (
        "decision",
        "status",
        "outcome",
        "result",
        "pass_or_block",
        "validation_status",
        "flowguard_decision",
        "worker_status",
    ):
        token = _normalize_outcome_token(payload.get(key))
        if token:
            return token
    return ""


def _default_blocker_class(packet_kind: str, owner_role: str, token: str) -> str:
    if owner_role == "flowguard_operator" or packet_kind == "flowguard_check":
        return "flowguard_failure"
    if token in {"needs_more_evidence", "more_evidence_required"}:
        return "evidence_gap"
    if token in {"needs_pm", "stop", "stopped"}:
        return "needs_user"
    if token in {"reject", "rejected"}:
        return "protocol_error"
    return "local_artifact"


def _parse_packet_outcome(packet: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    owner_role = str(envelope.get("responsibility", ""))
    body = str(result.get("body", ""))
    payload = _json_payload_from_body(body)
    token = _payload_outcome_token(payload, packet_kind) if payload else ""
    if not token and payload and isinstance(payload.get("contract_self_check"), Mapping):
        token = "pass"
    match = None if packet_kind == "pm_repair_decision" else _NONPASS_TEXT_RE.search(body)
    if not token and match:
        token = _normalize_outcome_token(match.group(0))
    if token in _PASSING_OUTCOME_DECISIONS:
        decision = "pass"
    elif token in _BLOCKING_OUTCOME_DECISIONS:
        decision = "fail" if token in {"fail", "failed", "failure"} else "block"
    else:
        decision = "pass"
    blocking = decision != "pass"
    recommendation = ""
    evidence_refs: list[str] = []
    blocker_class = _default_blocker_class(packet_kind, owner_role, token)
    if payload:
        if "blocking" in payload:
            blocking = bool(payload.get("blocking"))
            if blocking and decision == "pass":
                decision = "block"
        blocker_class = str(payload.get("blocker_class") or payload.get("failure_class") or blocker_class)
        recommendation = str(
            payload.get("recommended_resolution")
            or payload.get("recommendation")
            or payload.get("pm_recommendation")
            or ""
        )
        refs = payload.get("evidence_refs") or payload.get("direct_evidence_paths_checked") or payload.get("evidence_ids") or []
        if isinstance(refs, list):
            evidence_refs = [str(item) for item in refs]
    reason = recommendation or (f"{owner_role or packet_kind} reported {decision}" if blocking else "")
    return {
        "decision": decision,
        "blocking": blocking,
        "blocker_class": blocker_class,
        "recommended_resolution": recommendation,
        "evidence_refs": evidence_refs,
        "reason": reason,
        "raw_token": token,
        "schema_version": str(payload.get("schema_version", "")) if payload else "",
    }


def _record_packet_outcome(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> str:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    subject_packet_id = str(envelope.get("subject_id") or packet.get("packet_id") or "")
    outcome_id = _next_id(ledger, "outcome")
    row = {
        "outcome_id": outcome_id,
        "packet_id": str(packet.get("packet_id") or ""),
        "packet_kind": packet_kind,
        "subject_packet_id": subject_packet_id,
        "target_result_id": str(envelope.get("target_result_id") or result.get("result_id") or ""),
        "result_id": str(result.get("result_id") or ""),
        "owner_role": str(envelope.get("responsibility") or ""),
        "decision": str(outcome.get("decision") or "pass"),
        "blocking": bool(outcome.get("blocking")),
        "blocker_class": str(outcome.get("blocker_class") or "unknown"),
        "recommended_resolution": str(outcome.get("recommended_resolution") or ""),
        "evidence_refs": list(outcome.get("evidence_refs") or []),
        "reason": str(outcome.get("reason") or ""),
        "route_version": envelope.get("route_version"),
        "route_node_id": str(envelope.get("route_node_id") or ""),
        "route_scope": str(envelope.get("route_scope") or ""),
        "created_at": now_iso(),
    }
    ledger.setdefault("packet_outcomes", {})[outcome_id] = row
    result["packet_outcome_id"] = outcome_id
    _event(
        ledger,
        "packet_outcome_recorded",
        outcome_id=outcome_id,
        packet_id=row["packet_id"],
        decision=row["decision"],
        blocking=row["blocking"],
    )
    return outcome_id


def _active_semantic_blockers(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        blocker
        for blocker in ledger.get("active_blockers", {}).values()
        if isinstance(blocker, Mapping) and blocker.get("status") in {"active", "repairing", "awaiting_recheck"}
    ]


def _stopped_semantic_blockers(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        blocker
        for blocker in ledger.get("active_blockers", {}).values()
        if isinstance(blocker, Mapping) and blocker.get("status") == "stopped"
    ]


def _required_recheck_role(packet_kind: str, owner_role: str) -> str:
    if packet_kind == "review":
        return "reviewer"
    if packet_kind == "flowguard_check":
        return "flowguard_operator"
    return owner_role or "pm"


def _packet_repair_blocker_id(ledger: Mapping[str, Any], packet_id: str) -> str:
    packet = ledger.get("packets", {}).get(packet_id)
    if not isinstance(packet, Mapping):
        return ""
    if packet.get("repair_blocker_id"):
        return str(packet.get("repair_blocker_id"))
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    subject_id = str(envelope.get("subject_id") or "")
    if subject_id:
        return _packet_repair_blocker_id(ledger, subject_id)
    return str(packet.get("active_blocker_id") or "")


def _record_semantic_blocker(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    outcome_id: str,
) -> str:
    outcome = _require(ledger.setdefault("packet_outcomes", {}), outcome_id, "packet outcome")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    blocker_id = _next_id(ledger, "blocker")
    repair_target_packet_id = str(outcome.get("subject_packet_id") or packet.get("packet_id") or "")
    subject_packet = ledger.get("packets", {}).get(repair_target_packet_id, {})
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet, Mapping) else {}
    route_node_id = str(outcome.get("route_node_id") or subject_envelope.get("route_node_id") or "")
    repair_generation = 0
    if route_node_id and route_node_id in ledger.get("route_nodes", {}):
        repair_generation = int(ledger["route_nodes"][route_node_id].get("repair_generation", 0))
    blocker = {
        "blocker_id": blocker_id,
        "status": "active",
        "outcome_id": outcome_id,
        "packet_id": str(packet.get("packet_id") or ""),
        "packet_kind": packet_kind,
        "subject_packet_id": str(outcome.get("subject_packet_id") or ""),
        "repair_target_packet_id": repair_target_packet_id,
        "target_result_id": str(outcome.get("target_result_id") or ""),
        "result_id": str(result.get("result_id") or ""),
        "owner_role": str(outcome.get("owner_role") or ""),
        "required_recheck_role": _required_recheck_role(packet_kind, str(outcome.get("owner_role") or "")),
        "gate_kind": packet_kind,
        "blocker_class": str(outcome.get("blocker_class") or "unknown"),
        "recommended_resolution": str(outcome.get("recommended_resolution") or outcome.get("reason") or ""),
        "route_version": outcome.get("route_version"),
        "route_node_id": route_node_id,
        "route_scope": str(outcome.get("route_scope") or subject_envelope.get("route_scope") or ""),
        "repair_generation": repair_generation,
        "stale_evidence_ids": [str(result.get("result_id") or ""), str(outcome.get("target_result_id") or "")],
        "created_at": now_iso(),
        "pm_repair_packet_id": "",
        "pm_repair_decision_id": "",
        "cleared_by_outcome_id": "",
    }
    ledger.setdefault("active_blockers", {})[blocker_id] = blocker
    if isinstance(subject_packet, dict):
        subject_packet["active_blocker_id"] = blocker_id
    _event(
        ledger,
        "semantic_blocker_recorded",
        blocker_id=blocker_id,
        packet_id=blocker["packet_id"],
        required_recheck_role=blocker["required_recheck_role"],
    )
    _ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    return blocker_id


def _clear_semantic_blockers_for_pass(
    ledger: dict[str, Any],
    *,
    subject_packet_id: str,
    gate_kind: str,
    recheck_role: str,
    outcome_id: str,
) -> None:
    repair_blocker_id = _packet_repair_blocker_id(ledger, subject_packet_id)
    for blocker in ledger.setdefault("active_blockers", {}).values():
        if blocker.get("status") not in {"active", "repairing", "awaiting_recheck"}:
            continue
        same_subject = blocker.get("subject_packet_id") == subject_packet_id
        same_repair_chain = repair_blocker_id and blocker.get("blocker_id") == repair_blocker_id
        if not (same_subject or same_repair_chain):
            continue
        if blocker.get("gate_kind") != gate_kind and not same_repair_chain:
            continue
        if blocker.get("required_recheck_role") not in {"", recheck_role}:
            continue
        blocker["status"] = "cleared"
        blocker["cleared_by_outcome_id"] = outcome_id
        blocker["cleared_at"] = now_iso()
        subject = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
        if isinstance(subject, dict) and subject.get("active_blocker_id") == blocker.get("blocker_id"):
            subject["active_blocker_id"] = ""
        _event(
            ledger,
            "semantic_blocker_cleared",
            blocker_id=str(blocker.get("blocker_id") or ""),
            outcome_id=outcome_id,
        )


def _ensure_pm_repair_decision_packet_for_blocker(ledger: dict[str, Any], blocker_id: str) -> str:
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if blocker.get("status") not in {"active", "repairing", "awaiting_recheck"}:
        raise BlackBoxRuntimeError(
            f"cannot issue PM repair decision packet for blocker {blocker_id} in status {blocker.get('status')}"
        )
    existing = _find_packet(ledger, packet_kind="pm_repair_decision", subject_id=blocker_id)
    if existing:
        blocker["pm_repair_packet_id"] = str(existing["packet_id"])
        return str(existing["packet_id"])
    packet_id = issue_task_packet(
        ledger,
        "pm",
        f"Choose repair strategy for semantic blocker {blocker_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_repair_decision_packet.v1",
                "blocker_id": blocker_id,
                "blocked_packet_id": blocker["packet_id"],
                "repair_target_packet_id": blocker["repair_target_packet_id"],
                "gate_kind": blocker["gate_kind"],
                "required_recheck_role": blocker["required_recheck_role"],
                "allowed_decisions": sorted(_PM_REPAIR_DECISIONS),
                "instruction": "Return a PM repair decision. PM chooses the repair route; PM does not impersonate the blocked reviewer, system validation check, or FlowGuard pass.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target=REQUIRED_FLOWGUARD_TARGET,
        packet_kind="pm_repair_decision",
        subject_id=blocker_id,
        target_result_id=str(blocker.get("outcome_id") or ""),
        route_node_id=str(blocker.get("route_node_id") or ""),
        route_scope="pm_repair_decision",
    )
    blocker["pm_repair_packet_id"] = packet_id
    return packet_id


def _parse_pm_repair_decision_body(body: str) -> tuple[str, str]:
    payload = _json_payload_from_body(body)
    if payload:
        raw = _normalize_outcome_token(payload.get("decision") or payload.get("repair_decision") or payload.get("recovery_option"))
        reason = str(payload.get("reason") or payload.get("summary") or payload.get("recommended_resolution") or "")
    else:
        match = _PM_REPAIR_DECISION_FIELD_RE.search(body)
        raw = _normalize_outcome_token(match.group(2)) if match else ""
        reason = body.strip()[:500]
    decision = _PM_REPAIR_ALIASES.get(raw, raw)
    if decision not in _PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("PM repair decision requires a structured allowed decision field")
    return decision, reason


def _record_pm_repair_decision_from_packet_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    decision: str | None = None,
    reason: str | None = None,
) -> str:
    blocker_id = str(packet["envelope"].get("subject_id") or "")
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if decision is None:
        decision, reason = _parse_pm_repair_decision_body(str(result.get("body", "")))
    decision = str(decision)
    reason = str(reason or "")
    decision_id = _next_id(ledger, "pm_repair_decision")
    row = {
        "decision_id": decision_id,
        "blocker_id": blocker_id,
        "packet_id": packet["packet_id"],
        "result_id": result["result_id"],
        "decision": decision,
        "reason": reason,
        "created_at": now_iso(),
    }
    ledger.setdefault("pm_repair_decisions", {})[decision_id] = row
    blocker["pm_repair_decision_id"] = decision_id
    if decision not in {"waive_with_authority", "stop_for_user"}:
        blocker["status"] = "repairing"
    _event(
        ledger,
        "pm_repair_decision_recorded",
        decision_id=decision_id,
        blocker_id=blocker_id,
        decision=decision,
    )
    if decision in _HIGH_RISK_PM_REPAIR_DECISIONS:
        blocker["status"] = "awaiting_pm_decision_gate"
        _stage_pm_decision_gate(
            ledger,
            gate_kind="pm_repair_decision",
            packet=packet,
            result=result,
            decision=decision,
            reason=reason,
            decision_id=decision_id,
            blocker_id=blocker_id,
            node_id=str(blocker.get("route_node_id") or ""),
        )
        return decision_id
    _apply_pm_repair_decision(ledger, blocker_id, decision_id)
    return decision_id


def _stage_pm_decision_gate(
    ledger: dict[str, Any],
    *,
    gate_kind: str,
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    decision: str,
    reason: str,
    decision_id: str = "",
    blocker_id: str = "",
    node_id: str = "",
) -> str:
    gate_id = _next_id(ledger, "pm_decision_gate")
    row = {
        "gate_id": gate_id,
        "gate_kind": gate_kind,
        "status": "awaiting_flowguard",
        "source_packet_id": str(packet.get("packet_id") or ""),
        "source_result_id": str(result.get("result_id") or ""),
        "decision_id": decision_id,
        "blocker_id": blocker_id,
        "node_id": node_id,
        "decision": decision,
        "reason": reason,
        "flowguard_order_id": "",
        "review_id": "",
        "validation_evidence_id": "",
        "system_closure_id": "",
        "created_at": now_iso(),
    }
    ledger.setdefault("pm_decision_gates", {})[gate_id] = row
    result["pm_decision_gate_id"] = gate_id
    _event(
        ledger,
        "pm_decision_gate_staged",
        gate_id=gate_id,
        gate_kind=gate_kind,
        decision=decision,
        source_packet_id=row["source_packet_id"],
    )
    _ensure_flowguard_packet_for_task_result(ledger, packet, result)
    return gate_id


def _pending_pm_decision_gate_for_subject(
    ledger: Mapping[str, Any],
    subject_packet_id: str,
) -> dict[str, Any] | None:
    terminal_statuses = {"applied", "rejected", "cancelled"}
    for gate in ledger.get("pm_decision_gates", {}).values():
        if not isinstance(gate, dict):
            continue
        if gate.get("source_packet_id") != subject_packet_id:
            continue
        if gate.get("status") in terminal_statuses:
            continue
        return gate
    return None


def _mark_pm_decision_gate_flowguard(
    ledger: dict[str, Any],
    subject_packet_id: str,
    order_id: str,
) -> None:
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if not gate:
        return
    gate["flowguard_order_id"] = order_id
    gate["status"] = "awaiting_review"
    gate["updated_at"] = now_iso()


def _mark_pm_decision_gate_review(
    ledger: dict[str, Any],
    subject_packet_id: str,
    review_id: str,
) -> None:
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if not gate:
        return
    gate["review_id"] = review_id
    gate["status"] = "awaiting_system_validation"
    gate["updated_at"] = now_iso()


def _mark_pm_decision_gate_validation(
    ledger: dict[str, Any],
    subject_packet_id: str,
    evidence_id: str,
) -> None:
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if not gate:
        return
    gate["validation_evidence_id"] = evidence_id
    gate["status"] = "awaiting_system_closure"
    gate["updated_at"] = now_iso()


def _apply_staged_pm_decision_gate(
    ledger: dict[str, Any],
    gate: dict[str, Any],
    *,
    system_closure_id: str,
) -> None:
    if gate.get("status") == "applied":
        return
    gate_kind = str(gate.get("gate_kind") or "")
    if gate_kind == "pm_repair_decision":
        _apply_pm_repair_decision(
            ledger,
            str(gate.get("blocker_id") or ""),
            str(gate.get("decision_id") or ""),
        )
    elif gate_kind == "pm_disposition":
        record_pm_disposition(
            ledger,
            str(gate.get("node_id") or ""),
            str(gate.get("source_result_id") or system_closure_id),
            decision=str(gate.get("decision") or "accept"),
            reason=str(gate.get("reason") or "pm_decision_gate_applied"),
        )
    else:
        raise BlackBoxRuntimeError(f"unknown PM decision gate kind: {gate_kind}")
    gate["status"] = "applied"
    gate["system_closure_id"] = system_closure_id
    gate["applied_at"] = now_iso()
    _event(
        ledger,
        "pm_decision_gate_applied",
        gate_id=str(gate.get("gate_id") or ""),
        gate_kind=gate_kind,
        decision=str(gate.get("decision") or ""),
    )


def _latest_open_packet_for_repair(ledger: Mapping[str, Any], *, route_node_id: str, before_ids: set[str]) -> str:
    for packet_id in reversed(list(ledger.get("packets", {}))):
        if packet_id in before_ids:
            continue
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, Mapping):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if packet.get("status") == "open" and envelope.get("route_node_id") == route_node_id:
            return str(packet_id)
    return ""


def _issue_sender_repair_packet(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
    *,
    responsibility: str = "",
    packet_kind: str = "task",
) -> str:
    target_packet_id = str(blocker.get("repair_target_packet_id") or blocker.get("subject_packet_id") or "")
    target_packet = _require(ledger["packets"], target_packet_id, "repair target packet")
    target_envelope = target_packet["envelope"]
    repair_role = responsibility or str(target_envelope.get("responsibility") or "worker")
    packet_id = issue_task_packet(
        ledger,
        repair_role,
        f"Repair and reissue work for blocker {blocker['blocker_id']}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.repair_reissue_packet.v1",
                "blocker_id": blocker["blocker_id"],
                "pm_repair_decision_id": decision_id,
                "original_packet_id": target_packet_id,
                "original_body_hash": target_envelope.get("body_hash", ""),
                "required_recheck_role": blocker.get("required_recheck_role", ""),
                "recommended_resolution": blocker.get("recommended_resolution", ""),
                "instruction": "Produce fresh repaired evidence. The prior blocked artifact is context only, not passing evidence.",
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target=str(target_envelope.get("required_flowguard_target") or ""),
        packet_kind=packet_kind,
        subject_id=target_packet_id if packet_kind != "task" else "",
        target_result_id=str(blocker.get("target_result_id") or ""),
        route_node_id=str(target_envelope.get("route_node_id") or ""),
        route_scope=str(target_envelope.get("route_scope") or ""),
        acceptance_criteria=list(target_envelope.get("acceptance_criteria") or []),
    )
    ledger["packets"][packet_id]["repair_blocker_id"] = str(blocker["blocker_id"])
    ledger.setdefault("repair_transactions", {})[decision_id] = {
        "transaction_id": decision_id,
        "blocker_id": blocker["blocker_id"],
        "decision": "sender_reissue",
        "fresh_packet_id": packet_id,
        "stale_evidence_ids": list(blocker.get("stale_evidence_ids") or []),
        "created_at": now_iso(),
    }
    _event(ledger, "repair_reissue_packet_issued", blocker_id=blocker["blocker_id"], packet_id=packet_id)
    return packet_id


def _apply_pm_repair_decision(ledger: dict[str, Any], blocker_id: str, decision_id: str) -> None:
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    decision = str(ledger["pm_repair_decisions"][decision_id]["decision"])
    reason = str(ledger["pm_repair_decisions"][decision_id].get("reason") or f"pm_repair_{decision}")
    route_node_id = str(blocker.get("route_node_id") or "")
    before_packets = set(ledger.get("packets", {}))
    if decision == "same_node_repair" and route_node_id and route_node_id in ledger.get("route_nodes", {}):
        _prepare_same_node_repair(ledger, route_node_id, disposition_id=decision_id, reason=reason)
        fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=route_node_id, before_ids=before_packets)
        if fresh_packet_id:
            ledger["packets"][fresh_packet_id]["repair_blocker_id"] = blocker_id
        ledger.setdefault("repair_transactions", {})[decision_id] = {
            "transaction_id": decision_id,
            "blocker_id": blocker_id,
            "decision": decision,
            "fresh_packet_id": fresh_packet_id,
            "stale_evidence_ids": list(blocker.get("stale_evidence_ids") or []),
            "created_at": now_iso(),
        }
        blocker["status"] = "awaiting_recheck"
        return
    if decision in {"same_node_repair", "sender_reissue", "collect_more_evidence"}:
        _issue_sender_repair_packet(ledger, blocker, decision_id)
        blocker["status"] = "awaiting_recheck"
        return
    if decision == "mutate_route" and route_node_id and route_node_id in ledger.get("route_nodes", {}):
        _mutate_route_for_node(ledger, route_node_id, disposition_id=decision_id, reason=reason)
        blocker["status"] = "awaiting_recheck"
        return
    if decision == "quarantine_evidence":
        blocker["status"] = "quarantined"
        blocker["quarantined_at"] = now_iso()
        return
    if decision == "waive_with_authority":
        blocker["status"] = "waived"
        blocker["waived_at"] = now_iso()
        blocker["cleared_by_outcome_id"] = str(blocker.get("outcome_id") or "")
        return
    if decision == "stop_for_user":
        blocker["status"] = "stopped"
        blocker["stopped_at"] = now_iso()
        target_packet = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
        if isinstance(target_packet, dict):
            target_packet["status"] = "pm_stopped"


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
        if high_standard_flow_required(ledger):
            ensure_node_acceptance_plan_packet(ledger, next_node)
        else:
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
        if packet.get("envelope", {}).get("route_node_id") != node_id:
            continue
        if packet.get("accepted_result_id"):
            packet["status"] = "accepted"
            continue
        if packet.get("status") != "accepted":
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
            "node_acceptance_plan_id": "",
            "parent_backward_replay_id": "",
            "parent_backward_waiver": "",
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
    if high_standard_flow_required(ledger):
        ensure_node_acceptance_plan_packet(ledger, replacement_id)
    else:
        ensure_next_node_task_packet(ledger)


def lease_agent(
    ledger: dict[str, Any],
    responsibility: str,
    *,
    agent_id: str | None = None,
    packet_id: str = "",
) -> str:
    _assert_not_terminal_lifecycle(ledger)
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
        "ack_received_at": "",
        "progress_count": 0,
        "last_progress_at": "",
        "last_liveness_status": "",
        "liveness_status": "",
        "liveness_checked_at": "",
        "host_liveness_history": [],
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
    _assert_not_terminal_lifecycle(ledger)
    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot issue a packet without an active route")
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    if packet_kind not in PACKET_KINDS:
        raise BlackBoxRuntimeError(f"unknown packet kind: {packet_kind}")
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
    envelope["output_contract"] = control_surface.build_packet_output_contract(
        packet_id=packet_id,
        responsibility=responsibility,
        packet_kind=packet_kind,
        route_version=int(ledger["active_route_version"]),
        source_generation=int(ledger["source_generation"]),
    )
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
    _assert_not_terminal_lifecycle(ledger)
    packet = _require(ledger["packets"], packet_id, "packet")
    lease = _require(ledger["leases"], lease_id, "lease")
    if packet.get("accepted_result_id"):
        raise BlackBoxRuntimeError("cannot assign accepted packet to a new lease")
    if lease["status"] != "active":
        raise BlackBoxRuntimeError("cannot assign packet to inactive lease")
    if lease["responsibility"] != packet["envelope"]["responsibility"]:
        raise BlackBoxRuntimeError("lease responsibility does not match packet")
    packet["assigned_lease_id"] = lease_id
    packet["status"] = "assigned"
    lease["packet_id"] = packet_id
    _event(ledger, "packet_assigned", packet_id=packet_id, lease_id=lease_id)


def ack_lease(ledger: dict[str, Any], lease_id: str, packet_id: str) -> None:
    _assert_not_terminal_lifecycle(ledger)
    lease = _require(ledger["leases"], lease_id, "lease")
    packet = _require(ledger["packets"], packet_id, "packet")
    if packet.get("accepted_result_id"):
        raise BlackBoxRuntimeError("cannot ACK an accepted packet")
    if lease["status"] != "active":
        raise BlackBoxRuntimeError("inactive lease cannot ACK")
    if packet["assigned_lease_id"] != lease_id:
        raise BlackBoxRuntimeError("lease is not assigned to packet")
    lease["ack_received"] = True
    lease["ack_received_at"] = now_iso()
    packet["status"] = "acknowledged"
    _event(ledger, "lease_ack", lease_id=lease_id, packet_id=packet_id)


def record_progress(ledger: dict[str, Any], lease_id: str, packet_id: str, status: str) -> None:
    _assert_not_terminal_lifecycle(ledger)
    lease = _require(ledger["leases"], lease_id, "lease")
    packet = _require(ledger["packets"], packet_id, "packet")
    if lease.get("status") != "active":
        raise BlackBoxRuntimeError("inactive lease cannot record progress")
    if lease.get("packet_id") != packet_id:
        raise BlackBoxRuntimeError("progress packet mismatch")
    if packet.get("accepted_result_id"):
        raise BlackBoxRuntimeError("accepted packet cannot record progress")
    lease["progress_count"] = int(lease.get("progress_count", 0)) + 1
    lease["last_progress_status"] = status
    lease["last_progress_at"] = now_iso()
    lease["last_liveness_status"] = status
    _event(ledger, "lease_progress", lease_id=lease_id, packet_id=packet_id, status=status)


def record_host_liveness(
    ledger: dict[str, Any],
    lease_id: str,
    packet_id: str,
    status: str,
    *,
    source: str = "host_report",
    detail: str = "",
) -> dict[str, Any]:
    _assert_not_terminal_lifecycle(ledger)
    normalized = status.strip()
    if normalized not in _HOST_LIVENESS_STATUSES:
        raise BlackBoxRuntimeError(f"unknown host liveness status: {status}")
    lease = _require(ledger["leases"], lease_id, "lease")
    packet = _require(ledger["packets"], packet_id, "packet")
    if lease.get("packet_id") != packet_id:
        raise BlackBoxRuntimeError("host liveness packet mismatch")
    if packet.get("accepted_result_id"):
        raise BlackBoxRuntimeError("accepted packet cannot record host liveness")
    checked_at = now_iso()
    report_id = _next_id(ledger, "host_liveness")
    report = {
        "schema_version": "black_box_flowpilot.host_liveness_report.v1",
        "report_id": report_id,
        "lease_id": lease_id,
        "packet_id": packet_id,
        "status": normalized,
        "source": source,
        "detail": detail,
        "checked_at": checked_at,
        "current_run_only": True,
    }
    ledger.setdefault("host_liveness_reports", {})[report_id] = report
    lease["liveness_status"] = normalized
    lease["last_liveness_status"] = normalized
    lease["liveness_checked_at"] = checked_at
    lease["liveness_source"] = source
    lease["liveness_detail"] = detail
    history = lease.setdefault("host_liveness_history", [])
    if isinstance(history, list):
        history.append(
            {
                "report_id": report_id,
                "status": normalized,
                "source": source,
                "checked_at": checked_at,
            }
        )
        del history[:-20]
    _event(
        ledger,
        "host_liveness_recorded",
        report_id=report_id,
        lease_id=lease_id,
        packet_id=packet_id,
        status=normalized,
        source=source,
    )
    return report


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
    _assert_not_terminal_lifecycle(ledger)
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
            "output_contract": control_surface.build_result_output_contract(packet["envelope"]),
            "ack_result_accepted_separate": True,
        },
        "body": body,
        "review_id": "",
        "accepted": False,
    }
    ledger["results"][result_id] = result
    result["quarantined"] = bool(set(blockers).intersection(_STALE_RESULT_BLOCKERS))
    packet["result_ids"].append(result_id)
    if not blockers:
        packet["status"] = "result_submitted"
    elif packet.get("status") == "quarantined_after_route_mutation" or "quarantined_packet" in blockers:
        packet["status"] = "quarantined_after_route_mutation"
        packet["latest_quarantined_result_id"] = result_id
    else:
        packet["status"] = "result_blocked"
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
    if packet_kind == "pm_repair_decision":
        try:
            repair_decision, repair_reason = _parse_pm_repair_decision_body(str(result.get("body", "")))
        except BlackBoxRuntimeError as exc:
            result["status"] = "pm_repair_decision_blocked"
            result["accepted"] = False
            result.setdefault("mechanical_blockers", []).append("pm_repair_decision_payload_contract")
            result["quarantine_reason"] = str(exc)
            packet["status"] = "result_blocked"
            close_lease(ledger, lease["lease_id"], "pm_repair_decision_payload_blocked")
            _event(
                ledger,
                "pm_repair_decision_blocked",
                packet_id=packet["packet_id"],
                result_id=result["result_id"],
                reason=str(exc),
            )
            return
        outcome = {
            "decision": "pass",
            "blocking": False,
            "blocker_class": "pm_repair_decision",
            "recommended_resolution": repair_decision,
            "evidence_refs": [],
            "reason": repair_reason,
            "raw_token": repair_decision,
            "schema_version": "",
        }
        outcome_id = _record_packet_outcome(ledger, packet, result, outcome)
        result["semantic_decision"] = "pass"
        result["packet_outcome_id"] = outcome_id
        _accept_packet_result(ledger, packet, result, lease, reason="pm_repair_decision_submitted")
        _record_pm_repair_decision_from_packet_result(
            ledger,
            packet,
            result,
            decision=repair_decision,
            reason=repair_reason,
        )
        return

    outcome = _parse_packet_outcome(packet, result)
    outcome_id = _record_packet_outcome(ledger, packet, result, outcome)
    result["semantic_decision"] = outcome["decision"]
    if outcome["blocking"]:
        if packet_kind == "task":
            result["status"] = "semantic_blocked"
            result["accepted"] = False
            packet["status"] = "result_blocked"
            close_lease(ledger, lease["lease_id"], "semantic_result_blocked")
            _record_semantic_blocker(ledger, packet, result, outcome_id)
            return
        if packet_kind == "flowguard_check":
            result["status"] = "flowguard_blocked"
            result["accepted"] = False
            packet["status"] = "flowguard_blocked"
            close_lease(ledger, lease["lease_id"], "flowguard_result_blocked")
            _record_flowguard_from_packet_result(ledger, packet, result, outcome=outcome)
            _record_semantic_blocker(ledger, packet, result, outcome_id)
            return
        if packet_kind == "review":
            _record_review_from_packet_result(ledger, packet, result, outcome=outcome, outcome_id=outcome_id)
            _accept_packet_result(ledger, packet, result, lease, reason="review_block_result_submitted")
            _record_semantic_blocker(ledger, packet, result, outcome_id)
            return
    if packet_kind == "task":
        close_lease(ledger, lease["lease_id"], "result_submitted")
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=packet["packet_id"],
            gate_kind="task",
            recheck_role=packet["envelope"]["responsibility"],
            outcome_id=outcome_id,
        )
        _ensure_flowguard_packet_for_task_result(ledger, packet, result)
        return
    if packet_kind == "flowguard_check":
        _accept_packet_result(ledger, packet, result, lease, reason="flowguard_result_submitted")
        _record_flowguard_from_packet_result(ledger, packet, result, outcome=outcome)
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=str(packet["envelope"]["subject_id"]),
            gate_kind="flowguard_check",
            recheck_role="flowguard_operator",
            outcome_id=outcome_id,
        )
        _ensure_review_packet_for_task_result(ledger, packet["envelope"]["subject_id"])
        return
    if packet_kind == "review":
        review_id = _record_review_from_packet_result(ledger, packet, result, outcome=outcome, outcome_id=outcome_id)
        _accept_packet_result(ledger, packet, result, lease, reason="review_result_submitted")
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=str(packet["envelope"]["subject_id"]),
            gate_kind="review",
            recheck_role="reviewer",
            outcome_id=outcome_id,
        )
        evidence_id = _record_system_validation_for_packet(
            ledger,
            str(packet["envelope"]["subject_id"]),
            source_packet_id=str(packet["packet_id"]),
            source_result_id=str(result["result_id"]),
            review_id=review_id,
        )
        if ledger["validation_evidence"][evidence_id]["status"] == "passed":
            _clear_system_validation_blockers_for_pass(
                ledger,
                subject_packet_id=str(packet["envelope"]["subject_id"]),
                validation_evidence_id=evidence_id,
            )
            _auto_close_packet_after_system_validation(
                ledger,
                str(packet["envelope"]["subject_id"]),
                validation_evidence_id=evidence_id,
                source_result_id=str(result["result_id"]),
            )
        else:
            _record_system_validation_blocker(
                ledger,
                str(packet["envelope"]["subject_id"]),
                validation_evidence_id=evidence_id,
                source_packet_id=str(packet["packet_id"]),
                source_result_id=str(result["result_id"]),
            )
        return
    if packet_kind == "pm_disposition":
        _accept_packet_result(ledger, packet, result, lease, reason="pm_disposition_submitted")
        node_id = str(packet["envelope"].get("route_node_id") or "")
        if not node_id:
            raise BlackBoxRuntimeError("PM disposition packet is missing route_node_id")
        decision, reason = _decision_from_pm_body(str(result.get("body", "")))
        if decision in _HIGH_RISK_PM_DISPOSITION_DECISIONS:
            _stage_pm_decision_gate(
                ledger,
                gate_kind="pm_disposition",
                packet=packet,
                result=result,
                decision=decision,
                reason=reason,
                node_id=node_id,
            )
            return
        record_pm_disposition(ledger, node_id, result["result_id"], decision=decision, reason=reason)
        return
    raise BlackBoxRuntimeError(f"unknown packet kind: {packet_kind}")


def _apply_closure_side_effect_for_subject(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    system_closure_id: str = "",
    validation_evidence_id: str = "",
    route_node_id_hint: str = "",
) -> None:
    subject_packet = ledger.get("packets", {}).get(subject_packet_id, {})
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet, dict) else {}
    route_scope = str(subject_envelope.get("route_scope") or "")
    node_id = str(subject_envelope.get("route_node_id") or route_node_id_hint or "")
    pm_gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if pm_gate:
        _apply_staged_pm_decision_gate(
            ledger,
            pm_gate,
            system_closure_id=system_closure_id,
        )
        return
    if high_standard_flow_required(ledger) and route_scope in PREPLANNING_GATE_SCOPES:
        _record_preplanning_gate_closure(ledger, route_scope, subject_packet)
        ensure_preplanning_gate_packet(ledger)
        return
    if high_standard_flow_required(ledger) and route_scope == "node_acceptance_plan" and node_id:
        _record_node_acceptance_plan_closure(ledger, node_id, subject_packet)
        ensure_next_node_task_packet(ledger)
        return
    if high_standard_flow_required(ledger) and route_scope == "parent_backward_replay" and node_id:
        _record_parent_backward_replay_closure(ledger, node_id, subject_packet)
        _ensure_pm_disposition_packet_for_node(ledger, node_id, str(subject_envelope.get("subject_id") or subject_packet_id))
        return
    if recursive_route_required(ledger) and route_scope == "planning":
        materialize_route_from_planning_result(
            ledger,
            str(subject_packet.get("accepted_result_id") or subject_envelope.get("target_result_id") or ""),
        )
        frontier = ledger.get("execution_frontier") or {}
        active_node = str(frontier.get("active_node_id") or "")
        if high_standard_flow_required(ledger) and active_node:
            ensure_node_acceptance_plan_packet(ledger, active_node)
        elif active_node:
            ensure_next_node_task_packet(ledger)
        return
    if recursive_route_required(ledger) and node_id:
        _record_node_closure(ledger, node_id, system_closure_id)
        node = ledger.get("route_nodes", {}).get(node_id, {})
        if high_standard_flow_required(ledger) and isinstance(node, dict) and _node_requires_parent_backward_replay(node) and not _parent_backward_replay_accepted(ledger, node_id):
            ensure_parent_backward_replay_packet(ledger, node_id)
            return
        _ensure_pm_disposition_packet_for_node(ledger, node_id, subject_packet_id)
        return
    evidence_id = str(validation_evidence_id or ledger.get("latest_validation_evidence_id") or f"validation-{system_closure_id}")
    attempt_final_closure(ledger, evidence_id)


def _record_system_closure(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    validation_evidence_id: str,
    source_result_id: str,
) -> str:
    for existing_id, existing in ledger.setdefault("system_closures", {}).items():
        if not isinstance(existing, Mapping):
            continue
        if existing.get("subject_packet_id") == subject_packet_id and existing.get("validation_evidence_id") == validation_evidence_id:
            return str(existing_id)
    subject_packet = _require(ledger["packets"], subject_packet_id, "packet")
    envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet.get("envelope"), Mapping) else {}
    closure_id = _next_id(ledger, "system_closure")
    row = {
        "closure_id": closure_id,
        "status": "closed",
        "subject_packet_id": subject_packet_id,
        "validation_evidence_id": validation_evidence_id,
        "source_result_id": source_result_id,
        "route_version": envelope.get("route_version"),
        "route_scope": str(envelope.get("route_scope") or ""),
        "route_node_id": str(envelope.get("route_node_id") or ""),
        "created_at": now_iso(),
    }
    ledger.setdefault("system_closures", {})[closure_id] = row
    ledger["latest_system_closure_id"] = closure_id
    _event(
        ledger,
        "system_closure_recorded",
        closure_id=closure_id,
        subject_packet_id=subject_packet_id,
        validation_evidence_id=validation_evidence_id,
    )
    return closure_id


def _auto_close_packet_after_system_validation(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    validation_evidence_id: str,
    source_result_id: str,
) -> str:
    evidence = _require(ledger.setdefault("validation_evidence", {}), validation_evidence_id, "validation evidence")
    if evidence.get("status") != "passed":
        raise BlackBoxRuntimeError("system closure requires passing validation evidence")
    closure_id = _record_system_closure(
        ledger,
        subject_packet_id,
        validation_evidence_id=validation_evidence_id,
        source_result_id=source_result_id,
    )
    _apply_closure_side_effect_for_subject(
        ledger,
        subject_packet_id,
        system_closure_id=closure_id,
        validation_evidence_id=validation_evidence_id,
    )
    return closure_id


def _record_preplanning_gate_closure(
    ledger: dict[str, Any],
    route_scope: str,
    subject_packet: Mapping[str, Any],
) -> None:
    result_id = str(subject_packet.get("accepted_result_id") or "")
    result = ledger.get("results", {}).get(result_id, {})
    body = str(result.get("body", ""))
    if route_scope == "high_standard_contract":
        requirements = _parse_high_standard_requirements(body)
        contract_id = _next_id(ledger, "high_standard_contract")
        ledger["high_standard_contract"] = {
            "contract_id": contract_id,
            "status": "accepted",
            "source_packet_id": subject_packet.get("packet_id", ""),
            "source_result_id": result_id,
            "requirements": requirements,
            "created_at": now_iso(),
        }
        _event(ledger, "high_standard_contract_accepted", contract_id=contract_id, requirement_count=len(requirements))
        return
    if route_scope == "discovery":
        discovery_id = _next_id(ledger, "discovery")
        ledger["preplanning_discovery"] = {
            "discovery_id": discovery_id,
            "status": "accepted",
            "source_packet_id": subject_packet.get("packet_id", ""),
            "source_result_id": result_id,
            "material_current": True,
            "skill_inventory_candidate_only": True,
            "created_at": now_iso(),
        }
        _event(ledger, "discovery_record_accepted", discovery_id=discovery_id)
        return
    if route_scope == "skill_standard":
        obligations = _parse_skill_obligations(body)
        contract_id = _next_id(ledger, "skill_standard")
        ledger["skill_standard_contract"] = {
            "contract_id": contract_id,
            "status": "accepted",
            "source_packet_id": subject_packet.get("packet_id", ""),
            "source_result_id": result_id,
            "obligations": obligations,
            "raw_inventory_authority": "candidate_only",
            "created_at": now_iso(),
        }
        _event(ledger, "skill_standard_contract_accepted", contract_id=contract_id, obligation_count=len(obligations))
        return
    raise BlackBoxRuntimeError(f"unknown preplanning gate scope: {route_scope}")


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_high_standard_requirements(body: str) -> list[dict[str, Any]]:
    payload = _parse_json_object(body)
    rows = payload.get("requirements")
    if not isinstance(rows, list) or not rows:
        rows = [
            {
                "requirement_id": "hsr-001",
                "classification": "hard_current",
                "summary": "Complete the user's requested outcome to the highest reasonable current-run standard.",
            }
        ]
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        classification = str(row.get("classification") or "hard_current")
        closure_blocking = classification in {"hard_current", "high_standard_current"} and not bool(row.get("waived", False))
        normalized.append(
            {
                "requirement_id": str(row.get("requirement_id") or f"hsr-{index:03d}"),
                "classification": classification,
                "summary": str(row.get("summary") or row.get("requirement") or f"High-standard requirement {index}"),
                "closure_blocking": bool(row.get("closure_blocking", closure_blocking)),
                "evidence_rule": str(row.get("evidence_rule") or "must be traced through route node evidence"),
            }
        )
    return normalized or [
        {
            "requirement_id": "hsr-001",
            "classification": "hard_current",
            "summary": "Complete the user's requested outcome to the highest reasonable current-run standard.",
            "closure_blocking": True,
            "evidence_rule": "must be traced through route node evidence",
        }
    ]


def _parse_skill_obligations(body: str) -> list[dict[str, Any]]:
    payload = _parse_json_object(body)
    rows = payload.get("obligations") or payload.get("selected_skills")
    if not isinstance(rows, list) or not rows:
        rows = [
            {
                "obligation_id": "skill-std-001",
                "skill": "flowguard-development-process-flow",
                "role_use": "pm_or_flowguard_operator",
                "use_context": "planning_validation_or_repair",
                "evidence_required": "current-run FlowGuard work order/report evidence",
                "closure_blocking": True,
            }
        ]
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        status = str(row.get("classification") or row.get("status") or "required")
        blocking = status in {"required", "conditional"} and not bool(row.get("waived", False))
        normalized.append(
            {
                "obligation_id": str(row.get("obligation_id") or row.get("skill_standard_id") or f"skill-std-{index:03d}"),
                "skill": str(row.get("skill") or row.get("name") or "unspecified-skill"),
                "classification": status,
                "role_use": str(row.get("role_use") or "worker_or_formal_role"),
                "use_context": str(row.get("use_context") or "execution_or_review"),
                "evidence_required": str(row.get("evidence_required") or "current-run role skill use evidence"),
                "closure_blocking": bool(row.get("closure_blocking", blocking)),
            }
        )
    return normalized


def _record_node_acceptance_plan_closure(
    ledger: dict[str, Any],
    node_id: str,
    subject_packet: Mapping[str, Any],
) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    result_id = str(subject_packet.get("accepted_result_id") or "")
    plan_id = _next_id(ledger, "node_plan")
    requirement_ids = [
        str(row.get("requirement_id", ""))
        for row in _blocking_high_standard_requirements(ledger)
        if row.get("requirement_id")
    ]
    obligation_ids = [
        str(row.get("obligation_id", ""))
        for row in _required_skill_obligations(ledger)
        if row.get("obligation_id")
    ]
    ledger.setdefault("node_acceptance_plans", {})[plan_id] = {
        "plan_id": plan_id,
        "status": "accepted",
        "node_id": node_id,
        "source_packet_id": subject_packet.get("packet_id", ""),
        "source_result_id": result_id,
        "repair_policy": "same_node_repair_default",
        "high_standard_requirement_ids": requirement_ids,
        "skill_standard_obligation_ids": obligation_ids,
        "created_at": now_iso(),
    }
    node["node_acceptance_plan_id"] = plan_id
    node["high_standard_requirement_ids"] = requirement_ids
    node["skill_standard_obligation_ids"] = obligation_ids
    _event(ledger, "node_acceptance_plan_accepted", node_id=node_id, plan_id=plan_id)
    return plan_id


def _record_parent_backward_replay_closure(
    ledger: dict[str, Any],
    node_id: str,
    subject_packet: Mapping[str, Any],
) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    result_id = str(subject_packet.get("accepted_result_id") or "")
    replay_id = _next_id(ledger, "parent_replay")
    ledger.setdefault("parent_backward_replays", {})[replay_id] = {
        "replay_id": replay_id,
        "status": "accepted",
        "node_id": node_id,
        "source_packet_id": subject_packet.get("packet_id", ""),
        "source_result_id": result_id,
        "child_node_ids": list(node.get("child_node_ids") or []),
        "created_at": now_iso(),
    }
    node["parent_backward_replay_id"] = replay_id
    node["status"] = "awaiting_pm_disposition"
    _event(ledger, "parent_backward_replay_accepted", node_id=node_id, replay_id=replay_id)
    return replay_id


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
    *,
    outcome: Mapping[str, Any] | None = None,
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
    semantic = outcome if isinstance(outcome, Mapping) else {}
    decision = "fail" if semantic.get("blocking") else "pass"
    complete_flowguard_work_order(ledger, order_id, decision=decision, evidence_id=result["result_id"])
    order["proof_artifact"] = result["result_id"]
    order["confidence_boundary"] = "current_run_packet"
    if node_id and node_id in ledger.get("route_nodes", {}):
        ledger["route_nodes"][node_id].setdefault("flowguard_order_ids", []).append(order_id)
    _mark_pm_decision_gate_flowguard(ledger, subject_id, order_id)
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
    *,
    outcome: Mapping[str, Any] | None = None,
    outcome_id: str = "",
) -> str:
    subject_id = str(packet["envelope"]["subject_id"])
    target_result_id = str(packet["envelope"]["target_result_id"])
    semantic = outcome if isinstance(outcome, Mapping) else {}
    accepted = not bool(semantic.get("blocking"))
    review_id = review_result(
        ledger,
        target_result_id,
        result["producer_lease_id"],
        decision="accept" if accepted else "block",
        checks_evidence=True,
        direct_evidence_ids=[result["result_id"]],
        pm_routing_decision="accept_result" if accepted else "pm_repair_decision_required",
    )
    review = ledger["reviews"][review_id]
    review["review_packet_id"] = packet["packet_id"]
    review["review_packet_result_id"] = result["result_id"]
    review["subject_packet_id"] = subject_id
    review["packet_outcome_id"] = outcome_id
    if not accepted:
        blocker_note = str(semantic.get("reason") or semantic.get("recommended_resolution") or "reviewer_blocked")
        review["blockers"] = sorted(set(list(review.get("blockers") or []) + [blocker_note]))
    subject_envelope = ledger.get("packets", {}).get(subject_id, {}).get("envelope", {}) or {}
    node_id = str(subject_envelope.get("route_node_id") or "")
    if node_id and node_id in ledger.get("route_nodes", {}):
        ledger["route_nodes"][node_id].setdefault("review_ids", []).append(review_id)
        if accepted and subject_envelope.get("route_scope") == "node":
            ledger["route_nodes"][node_id]["accepted_result_id"] = target_result_id
            ledger["route_nodes"][node_id]["accepted_repair_generation"] = int(
                ledger["route_nodes"][node_id].get("repair_generation", 0)
            )
    if accepted:
        _mark_pm_decision_gate_review(ledger, subject_id, review_id)
    return review_id


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
    if packet.get("status") == "quarantined_after_route_mutation":
        blockers.append("quarantined_packet")
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
    subject_packet_id: str = "",
    source_packet_id: str = "",
    source_result_id: str = "",
    evidence_kind: str = "system_validation",
    owner_role: str = "system",
    review_id: str = "",
    flowguard_order_ids: list[str] | None = None,
    gate_id: str = "",
    blockers: list[str] | None = None,
) -> None:
    ledger["validation_evidence"][evidence_id] = {
        "evidence_id": evidence_id,
        "status": status,
        "source_generation": generation if generation is not None else ledger["source_generation"],
        "subject_packet_id": subject_packet_id,
        "source_packet_id": source_packet_id,
        "source_result_id": source_result_id,
        "evidence_kind": evidence_kind,
        "owner_role": owner_role,
        "review_id": review_id,
        "flowguard_order_ids": list(flowguard_order_ids or []),
        "gate_id": gate_id,
        "blockers": list(blockers or []),
        "created_at": now_iso(),
    }
    _event(ledger, "validation_evidence_recorded", evidence_id=evidence_id, status=status)


def _matching_flowguard_order_ids(
    ledger: Mapping[str, Any],
    subject_packet_id: str,
    modeled_target: str,
) -> list[str]:
    rows: list[str] = []
    for order_id, order in ledger.get("flowguard_work_orders", {}).items():
        if order.get("subject_id") != subject_packet_id:
            continue
        if order.get("modeled_target") != modeled_target:
            continue
        if order.get("status") != "complete":
            continue
        if order.get("decision") != "pass":
            continue
        if order.get("progress_only") or order.get("skipped_checks") or order.get("proof_stale"):
            continue
        if not order.get("proof_artifact"):
            continue
        if order.get("source_generation") != ledger.get("source_generation"):
            continue
        rows.append(str(order_id))
    return rows


def _record_system_validation_for_packet(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    source_packet_id: str,
    source_result_id: str,
    review_id: str,
) -> str:
    subject_packet = _require(ledger["packets"], subject_packet_id, "packet")
    required_target = str(subject_packet["envelope"].get("required_flowguard_target") or "")
    flowguard_order_ids = _matching_flowguard_order_ids(ledger, subject_packet_id, required_target) if required_target else []
    blockers: list[str] = []
    subject_result_id = str(subject_packet.get("accepted_result_id") or subject_packet["envelope"].get("target_result_id") or "")
    subject_result = ledger.get("results", {}).get(subject_result_id, {})
    if not isinstance(subject_result, Mapping) or subject_result.get("review_id") != review_id:
        blockers.append("missing_accepted_review")
    if required_target and not flowguard_order_ids:
        blockers.append("missing_matching_flowguard_report")
    if _pending_pm_decision_gate_for_subject(ledger, subject_packet_id):
        gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
        if gate and not gate.get("review_id"):
            blockers.append("missing_pm_decision_gate_review")
    evidence_id = f"validation-{source_result_id}"
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    gate_id = str(gate.get("gate_id") or "") if gate else ""
    record_validation_evidence(
        ledger,
        evidence_id,
        status="failed" if blockers else "passed",
        subject_packet_id=subject_packet_id,
        source_packet_id=source_packet_id,
        source_result_id=source_result_id,
        evidence_kind="system_review_validation",
        owner_role="system",
        review_id=review_id,
        flowguard_order_ids=flowguard_order_ids,
        gate_id=gate_id,
        blockers=blockers,
    )
    ledger["latest_validation_evidence_id"] = evidence_id
    result = ledger.get("results", {}).get(source_result_id)
    if isinstance(result, dict):
        result["validation_evidence_id"] = evidence_id
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet, Mapping) else {}
    node_id = str(subject_envelope.get("route_node_id") or "")
    if (
        not blockers
        and node_id
        and node_id in ledger.get("route_nodes", {})
        and subject_envelope.get("route_scope") in {"node", "planning", "node_acceptance_plan", "parent_backward_replay"}
    ):
        ledger["route_nodes"][node_id].setdefault("validation_evidence_ids", []).append(evidence_id)
    if blockers:
        gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
        if gate:
            gate["validation_evidence_id"] = evidence_id
            gate["status"] = "system_validation_blocked"
            gate["updated_at"] = now_iso()
    else:
        _mark_pm_decision_gate_validation(ledger, subject_packet_id, evidence_id)
    return evidence_id


def _record_system_validation_blocker(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    validation_evidence_id: str,
    source_packet_id: str,
    source_result_id: str,
) -> str:
    for blocker_id, blocker in ledger.setdefault("active_blockers", {}).items():
        if not isinstance(blocker, Mapping):
            continue
        if blocker.get("gate_kind") != "system_validation":
            continue
        if blocker.get("subject_packet_id") != subject_packet_id:
            continue
        if blocker.get("status") in {"active", "repairing", "awaiting_recheck"}:
            return str(blocker_id)
    subject_packet = _require(ledger["packets"], subject_packet_id, "packet")
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet.get("envelope"), Mapping) else {}
    evidence = _require(ledger.setdefault("validation_evidence", {}), validation_evidence_id, "validation evidence")
    blockers = [str(item) for item in evidence.get("blockers") or ["system_validation_failed"]]
    blocker_id = _next_id(ledger, "blocker")
    route_node_id = str(subject_envelope.get("route_node_id") or "")
    repair_generation = 0
    if route_node_id and route_node_id in ledger.get("route_nodes", {}):
        repair_generation = int(ledger["route_nodes"][route_node_id].get("repair_generation", 0))
    row = {
        "blocker_id": blocker_id,
        "status": "active",
        "outcome_id": "",
        "packet_id": source_packet_id,
        "packet_kind": "system_validation",
        "subject_packet_id": subject_packet_id,
        "repair_target_packet_id": subject_packet_id,
        "target_result_id": str(subject_packet.get("accepted_result_id") or subject_envelope.get("target_result_id") or ""),
        "result_id": source_result_id,
        "owner_role": "system",
        "required_recheck_role": "system",
        "gate_kind": "system_validation",
        "blocker_class": "system_validation_failure",
        "recommended_resolution": "; ".join(blockers),
        "route_version": subject_envelope.get("route_version"),
        "route_node_id": route_node_id,
        "route_scope": str(subject_envelope.get("route_scope") or ""),
        "repair_generation": repair_generation,
        "stale_evidence_ids": [validation_evidence_id, source_result_id],
        "created_at": now_iso(),
        "pm_repair_packet_id": "",
        "pm_repair_decision_id": "",
        "cleared_by_outcome_id": "",
    }
    ledger.setdefault("active_blockers", {})[blocker_id] = row
    if isinstance(subject_packet, dict):
        subject_packet["active_blocker_id"] = blocker_id
        subject_packet["status"] = "system_validation_blocked"
    _event(
        ledger,
        "system_validation_blocker_recorded",
        blocker_id=blocker_id,
        subject_packet_id=subject_packet_id,
        validation_evidence_id=validation_evidence_id,
    )
    _ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    return blocker_id


def _clear_system_validation_blockers_for_pass(
    ledger: dict[str, Any],
    *,
    subject_packet_id: str,
    validation_evidence_id: str,
) -> None:
    repair_blocker_id = _packet_repair_blocker_id(ledger, subject_packet_id)
    for blocker in ledger.setdefault("active_blockers", {}).values():
        if not isinstance(blocker, dict):
            continue
        if blocker.get("status") not in {"active", "repairing", "awaiting_recheck"}:
            continue
        if blocker.get("gate_kind") != "system_validation":
            continue
        same_subject = blocker.get("subject_packet_id") == subject_packet_id
        same_repair_chain = repair_blocker_id and blocker.get("blocker_id") == repair_blocker_id
        if not (same_subject or same_repair_chain):
            continue
        blocker["status"] = "cleared"
        blocker["cleared_by_outcome_id"] = validation_evidence_id
        blocker["cleared_at"] = now_iso()
        subject = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
        if isinstance(subject, dict) and subject.get("active_blocker_id") == blocker.get("blocker_id"):
            subject["active_blocker_id"] = ""
        _event(
            ledger,
            "system_validation_blocker_cleared",
            blocker_id=str(blocker.get("blocker_id") or ""),
            validation_evidence_id=validation_evidence_id,
        )


def attempt_final_closure(
    ledger: dict[str, Any],
    validation_evidence_id: str,
    *,
    required_flowguard_target: str = REQUIRED_FLOWGUARD_TARGET,
) -> dict[str, Any]:
    if recursive_route_required(ledger):
        build_final_route_wide_gate_ledger(ledger)
    if high_standard_flow_required(ledger):
        build_final_requirement_evidence_matrix(ledger)
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


def reconcile_resume_request(ledger: dict[str, Any], *, resume_source: str = "manual_resume") -> dict[str, Any]:
    previous = dict(ledger.get("lifecycle") or {})
    ledger["lifecycle"] = {
        "state": "running",
        "resume_source": resume_source,
        "previous_state": previous.get("state", ""),
        "reason": previous.get("reason", ""),
        "reconciled_at": now_iso(),
    }
    _event(ledger, "resume_reconciled", resume_source=resume_source, previous_state=previous.get("state", ""))
    return refresh_lifecycle_guard(ledger, trigger="resume", resume_source=resume_source)


def record_completion_claim(ledger: dict[str, Any], *, source: str, claim: str, evidence_id: str = "") -> None:
    ledger.setdefault("completion_claims", []).append(
        {"source": source, "claim": claim, "evidence_id": evidence_id, "created_at": now_iso()}
    )
    _event(ledger, "completion_claim_recorded", source=source, evidence_id=evidence_id)


def _latest_route_draft(ledger: Mapping[str, Any]) -> Mapping[str, Any] | None:
    drafts = ledger.get("route_drafts")
    if not isinstance(drafts, Mapping):
        return None
    for draft in reversed(list(drafts.values())):
        if isinstance(draft, Mapping) and draft.get("status") == "draft":
            return draft
    return None


def _latest_accepted_planning_result_id(ledger: Mapping[str, Any]) -> str:
    for packet in reversed(list(ledger.get("packets", {}).values())):
        if not isinstance(packet, Mapping):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if envelope.get("packet_kind", "task") != "task" or envelope.get("route_scope") != "planning":
            continue
        result_id = str(packet.get("accepted_result_id") or "")
        if result_id:
            return result_id
    return ""


def _latest_node_subject_packet_id(ledger: Mapping[str, Any], node_id: str) -> str:
    node = ledger.get("route_nodes", {}).get(node_id)
    if not isinstance(node, Mapping):
        return ""
    for packet_id in reversed(list(node.get("packet_ids") or [])):
        packet = ledger.get("packets", {}).get(str(packet_id))
        if isinstance(packet, Mapping):
            return str(packet_id)
    return ""


def _apply_router_internal_action(ledger: dict[str, Any], action: RuntimeAction) -> dict[str, Any]:
    action_type = action.action_type
    if action_type not in ROUTER_INTERNAL_ACTION_TYPES:
        raise BlackBoxRuntimeError(f"action is not router-internal: {action_type}")
    result: dict[str, Any] = {"action_type": action_type, "subject_id": action.subject_id}
    if action_type == "freeze_contract":
        freeze_contract(ledger)
    elif action_type == "activate_route":
        draft = _latest_route_draft(ledger)
        if not draft:
            raise BlackBoxRuntimeError("activate_route requires a route draft")
        create_route(
            ledger,
            str(draft.get("summary") or "Activated FlowPilot route"),
            [str(step) for step in draft.get("steps") or []],
        )
        if isinstance(draft, dict):
            draft["status"] = "activated"
            draft["activated_at"] = now_iso()
    elif action_type == "issue_task_packet":
        result["packet_id"] = _ensure_planning_packet(ledger)
    elif action_type == "issue_preplanning_gate_packet":
        result["packet_id"] = ensure_preplanning_gate_packet(ledger)
    elif action_type == "materialize_route_nodes":
        planning_result_id = _latest_accepted_planning_result_id(ledger)
        if not planning_result_id:
            raise BlackBoxRuntimeError("materialize_route_nodes requires an accepted planning result")
        result["node_ids"] = materialize_route_from_planning_result(ledger, planning_result_id)
    elif action_type == "issue_node_acceptance_plan_packet":
        result["packet_id"] = ensure_node_acceptance_plan_packet(ledger, action.subject_id)
    elif action_type == "issue_node_task_packet":
        result["packet_id"] = ensure_next_node_task_packet(ledger)
    elif action_type == "issue_parent_backward_replay_packet":
        result["packet_id"] = ensure_parent_backward_replay_packet(ledger, action.subject_id)
    elif action_type == "issue_flowguard_packet":
        result["packet_id"] = _ensure_flowguard_packet_for_task_result(ledger, action.subject_id)
    elif action_type == "issue_review_packet":
        result["packet_id"] = _ensure_review_packet_for_task_result(ledger, action.subject_id)
    elif action_type == "issue_pm_repair_decision_packet":
        result["packet_id"] = _ensure_pm_repair_decision_packet_for_blocker(ledger, action.subject_id)
    elif action_type == "issue_pm_disposition_packet":
        subject_packet_id = _latest_node_subject_packet_id(ledger, action.subject_id)
        if not subject_packet_id:
            raise BlackBoxRuntimeError("PM disposition packet requires a node subject packet")
        result["packet_id"] = _ensure_pm_disposition_packet_for_node(ledger, action.subject_id, subject_packet_id)
    elif action_type == "close_project":
        evidence_id = str(ledger.get("latest_validation_evidence_id") or "")
        if not evidence_id:
            raise BlackBoxRuntimeError("close_project requires validation evidence")
        result["closure"] = attempt_final_closure(ledger, evidence_id)
    else:  # pragma: no cover - protected by allowlist above.
        raise BlackBoxRuntimeError(f"unsupported router-internal action: {action_type}")
    return result


def run_until_wait(ledger: dict[str, Any], *, max_steps: int = RUN_UNTIL_WAIT_MAX_STEPS) -> dict[str, Any]:
    """Fold safe internal mechanics until the next durable foreground boundary."""

    if max_steps < 1:
        raise BlackBoxRuntimeError("run_until_wait requires max_steps >= 1")
    folded: list[dict[str, Any]] = []
    for _ in range(max_steps):
        action = _guard_next_action(ledger)
        action_class = classify_runtime_action(action)
        if action_class != "router_internal":
            return {
                "ok": True,
                "command": "run-until-wait",
                "boundary_class": action_class,
                "next_action": action.to_json(),
                "folded_applied_count": len(folded),
                "folded_applied_actions": folded,
            }
        applied = _apply_router_internal_action(ledger, action)
        folded.append(applied)
    action = _guard_next_action(ledger)
    raise BlackBoxRuntimeError(
        "run_until_wait exceeded max_steps before a foreground boundary: "
        + json.dumps(
            {
                "max_steps": max_steps,
                "next_action": action.to_json(),
                "folded_applied_count": len(folded),
            },
            sort_keys=True,
        )
    )


def _guard_next_action(ledger: Mapping[str, Any]) -> RuntimeAction:
    status = terminal_lifecycle_status(ledger)
    if status:
        return RuntimeAction("terminal_lifecycle", f"run lifecycle is {status}", status)
    if not ledger.get("startup_intake"):
        return RuntimeAction("open_startup_intake", "startup intake has not been recorded")
    if (ledger.get("cutover_gate") or {}).get("decision") == "blocked":
        return RuntimeAction("repair_cutover_gate", "cutover gate has blockers")
    return router_next_action(ledger)


def _non_guard_event_count(ledger: Mapping[str, Any]) -> int:
    return sum(
        1
        for event in ledger.get("events", [])
        if isinstance(event, Mapping) and event.get("event_type") != "lifecycle_guard_refreshed"
    )


def _guard_action_key(action: RuntimeAction) -> str:
    return json.dumps(action.to_json(), sort_keys=True)


def _latest_result_for_packet(ledger: Mapping[str, Any], packet_id: str) -> Mapping[str, Any] | None:
    packet = ledger.get("packets", {}).get(packet_id)
    if not isinstance(packet, Mapping):
        return None
    for result_id in reversed(list(packet.get("result_ids") or [])):
        result = ledger.get("results", {}).get(result_id)
        if isinstance(result, Mapping):
            return result
    return None


def _stale_result_blockers_for_packet(ledger: Mapping[str, Any], packet_id: str) -> list[str]:
    packet = ledger.get("packets", {}).get(packet_id)
    blockers: set[str] = set()
    if isinstance(packet, Mapping) and packet.get("status") == "quarantined_after_route_mutation":
        blockers.add("quarantined_packet")
    latest = _latest_result_for_packet(ledger, packet_id)
    if isinstance(latest, Mapping):
        blockers.update(str(item) for item in latest.get("mechanical_blockers", []) if item in _STALE_RESULT_BLOCKERS)
    return sorted(blockers)


def _parse_utc_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _elapsed_seconds_since(raw: object) -> int | None:
    parsed = _parse_utc_timestamp(raw)
    if parsed is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def _runner_summary_candidate_paths(ledger: Mapping[str, Any], packet_id: str) -> list[Path]:
    raw_run_root = str(ledger.get("run_root") or "")
    if not raw_run_root:
        return []
    run_root = Path(raw_run_root)
    return [
        run_root / "evidence" / "flowguard" / packet_id / "runner_summary.json",
        run_root / "flowguard" / "evidence" / packet_id / "runner_summary.json",
        run_root / "evidence" / packet_id / "runner_summary.json",
    ]


def _walk_exit_codes(value: Any) -> list[int]:
    codes: list[int] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in {"exit_code", "returncode", "return_code"}:
                try:
                    codes.append(int(item))
                except (TypeError, ValueError):
                    pass
            else:
                codes.extend(_walk_exit_codes(item))
    elif isinstance(value, list):
        for item in value:
            codes.extend(_walk_exit_codes(item))
    return codes


def _walk_status_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in {"status", "state", "decision"} and isinstance(item, str):
                tokens.add(item.lower())
            else:
                tokens.update(_walk_status_tokens(item))
    elif isinstance(value, list):
        for item in value:
            tokens.update(_walk_status_tokens(item))
    return tokens


def _runner_summary_success(payload: Mapping[str, Any]) -> tuple[bool, list[int], set[str]]:
    exit_codes = _walk_exit_codes(payload)
    status_tokens = _walk_status_tokens(payload)
    if status_tokens.intersection({"running", "in_progress", "pending", "failed", "error", "cancelled"}):
        return False, exit_codes, status_tokens
    if exit_codes and all(code == 0 for code in exit_codes):
        return True, exit_codes, status_tokens
    if payload.get("ok") is True or payload.get("success") is True:
        return True, exit_codes, status_tokens
    return False, exit_codes, status_tokens


def _orphan_evidence_for_packet(ledger: Mapping[str, Any], packet_id: str) -> dict[str, Any] | None:
    packet = ledger.get("packets", {}).get(packet_id)
    if not isinstance(packet, Mapping) or packet.get("accepted_result_id"):
        return None
    for path in _runner_summary_candidate_paths(ledger, packet_id):
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, Mapping):
            continue
        ok, exit_codes, status_tokens = _runner_summary_success(payload)
        if not ok:
            continue
        return {
            "schema_version": "black_box_flowpilot.orphan_evidence.v1",
            "packet_id": packet_id,
            "path": str(path),
            "summary_hash": hash_text(text),
            "detected_at": now_iso(),
            "status": "completed_without_formal_result",
            "exit_codes": exit_codes,
            "status_tokens": sorted(status_tokens),
            "formal_result_present": bool(packet.get("result_ids")),
            "accepted_result_id": str(packet.get("accepted_result_id") or ""),
            "recovery_action": "recover_or_resubmit_formal_result",
        }
    return None


def _persist_orphan_evidence_from_guard(ledger: dict[str, Any], guard: Mapping[str, Any]) -> None:
    wait_recovery = guard.get("wait_recovery") if isinstance(guard.get("wait_recovery"), Mapping) else {}
    evidence = wait_recovery.get("orphan_evidence") if isinstance(wait_recovery, Mapping) else None
    if not isinstance(evidence, Mapping):
        return
    packet_id = str(evidence.get("packet_id") or "")
    summary_hash = str(evidence.get("summary_hash") or "")
    if not packet_id or not summary_hash:
        return
    records = ledger.setdefault("orphan_evidence", {})
    existing = records.get(packet_id) if isinstance(records, dict) else None
    if isinstance(existing, Mapping) and existing.get("summary_hash") == summary_hash:
        return
    record = dict(evidence)
    record["recorded_at"] = now_iso()
    records[packet_id] = record
    _event(
        ledger,
        "orphan_evidence_detected",
        packet_id=packet_id,
        path=str(record.get("path", "")),
        summary_hash=summary_hash,
    )


def _guard_config_int(ledger: Mapping[str, Any], key: str, default: int) -> int:
    config = ledger.get("lifecycle_guard_config") if isinstance(ledger.get("lifecycle_guard_config"), Mapping) else {}
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(0, value)


def _accepted_packet_repair_details(ledger: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    packet_id = str(packet.get("packet_id", ""))
    accepted_result_id = str(packet.get("accepted_result_id") or "")
    result = ledger.get("results", {}).get(accepted_result_id)
    result_map = result if isinstance(result, Mapping) else {}
    original_lease_id = str(result_map.get("producer_lease_id") or "")
    active_replacement_lease_ids = [
        str(lease_id)
        for lease_id, lease in ledger.get("leases", {}).items()
        if isinstance(lease, Mapping)
        and str(lease.get("packet_id") or "") == packet_id
        and str(lease.get("status") or "") == "active"
        and str(lease_id) != original_lease_id
    ]
    assigned_lease_id = str(packet.get("assigned_lease_id") or "")
    return {
        "packet_id": packet_id,
        "accepted_result_id": accepted_result_id,
        "original_lease_id": original_lease_id,
        "assigned_lease_id": assigned_lease_id,
        "active_replacement_lease_ids": active_replacement_lease_ids,
        "needs_repair": bool(
            accepted_result_id
            and (
                packet.get("status") != "accepted"
                or bool(active_replacement_lease_ids)
                or bool(original_lease_id and assigned_lease_id and assigned_lease_id != original_lease_id)
            )
        ),
    }


def _accepted_packet_repair_needed(ledger: Mapping[str, Any], packet: Mapping[str, Any]) -> bool:
    return bool(_accepted_packet_repair_details(ledger, packet).get("needs_repair"))


def repair_accepted_packet_assignment(
    ledger: dict[str, Any],
    packet_id: str,
    *,
    reason: str = "accepted_packet_assignment_race",
) -> dict[str, Any]:
    packet = _require(ledger["packets"], packet_id, "packet")
    details = _accepted_packet_repair_details(ledger, packet)
    accepted_result_id = str(details.get("accepted_result_id") or "")
    if not accepted_result_id:
        raise BlackBoxRuntimeError("accepted packet repair requires accepted_result_id")
    original_lease_id = str(details.get("original_lease_id") or "")
    closed_replacement_lease_ids: list[str] = []
    for lease_id in list(details.get("active_replacement_lease_ids") or []):
        close_lease(ledger, str(lease_id), reason)
        closed_replacement_lease_ids.append(str(lease_id))
    packet["status"] = "accepted"
    if original_lease_id and original_lease_id in ledger.get("leases", {}):
        packet["assigned_lease_id"] = original_lease_id
    _event(
        ledger,
        "accepted_packet_assignment_repaired",
        packet_id=packet_id,
        accepted_result_id=accepted_result_id,
        original_lease_id=original_lease_id,
        closed_replacement_lease_ids=closed_replacement_lease_ids,
        reason=reason,
    )
    return {
        "packet_id": packet_id,
        "accepted_result_id": accepted_result_id,
        "original_lease_id": original_lease_id,
        "closed_replacement_lease_ids": closed_replacement_lease_ids,
        "status": packet["status"],
        "assigned_lease_id": packet.get("assigned_lease_id", ""),
    }


def _guard_wait_recovery(
    ledger: Mapping[str, Any],
    action: RuntimeAction,
    *,
    trigger: str,
    repeated_count: int,
) -> dict[str, Any]:
    packet = ledger.get("packets", {}).get(action.subject_id)
    if not isinstance(packet, Mapping):
        return {"state": "not_applicable", "replacement_eligible": False}
    repair_details = _accepted_packet_repair_details(ledger, packet)
    if repair_details.get("needs_repair"):
        return {
            "state": "repair_assignment_race",
            "decision_override": "repair_assignment_race",
            "reason": "accepted packet has stale assignment or active replacement lease",
            "replacement_eligible": False,
            "repair": repair_details,
        }
    if action.action_type not in {"wait_for_ack", "wait_for_result"}:
        return {"state": "not_applicable", "replacement_eligible": False}

    lease_id = str(packet.get("assigned_lease_id") or "")
    lease = ledger.get("leases", {}).get(lease_id)
    lease_map = lease if isinstance(lease, Mapping) else {}
    if not lease_map:
        return {
            "state": "missing_lease",
            "decision_override": "reissue_or_replace_lease",
            "reason": "wait packet has no assigned lease record",
            "replacement_eligible": True,
            "lease_id": lease_id,
        }

    progress_count = int(lease_map.get("progress_count", 0) or 0)
    last_progress_status = str(lease_map.get("last_progress_status") or "")
    last_liveness_status = str(lease_map.get("liveness_status") or lease_map.get("last_liveness_status") or last_progress_status)
    last_progress_elapsed = _elapsed_seconds_since(lease_map.get("last_progress_at"))
    last_liveness_elapsed = _elapsed_seconds_since(lease_map.get("liveness_checked_at"))
    progress_grace_seconds = _guard_config_int(ledger, "progress_grace_seconds", _WAIT_PROGRESS_GRACE_SECONDS)
    positive_liveness_recent = bool(
        last_liveness_status
        and last_liveness_status not in _WAIT_LIVENESS_FAILURE_STATUSES
        and last_liveness_status not in _WAIT_NO_OUTPUT_STATUSES
        and (
            last_liveness_elapsed is not None
            and last_liveness_elapsed <= progress_grace_seconds
            or last_liveness_elapsed is None
            and last_progress_elapsed is not None
            and last_progress_elapsed <= progress_grace_seconds
        )
    )
    progress_recent = bool(
        (progress_count or lease_map.get("liveness_checked_at"))
        and positive_liveness_recent
    )
    base = {
        "state": "waiting",
        "replacement_eligible": False,
        "lease_id": lease_id,
        "lease_status": str(lease_map.get("status") or ""),
        "progress_count": progress_count,
        "last_progress_status": last_progress_status,
        "last_progress_elapsed_seconds": last_progress_elapsed,
        "last_liveness_status": last_liveness_status,
        "last_liveness_checked_at": str(lease_map.get("liveness_checked_at") or ""),
        "last_liveness_elapsed_seconds": last_liveness_elapsed,
        "progress_grace_seconds": progress_grace_seconds,
        "trigger": trigger,
        "repeated_count": repeated_count,
        "old_router_authority_used": False,
    }
    if lease_map.get("status") != "active":
        return {
            **base,
            "state": "inactive_lease",
            "decision_override": "reissue_or_replace_lease",
            "reason": "assigned lease is inactive",
            "replacement_eligible": True,
        }
    if action.action_type == "wait_for_result":
        orphan_evidence = _orphan_evidence_for_packet(ledger, action.subject_id)
        if orphan_evidence:
            return {
                **base,
                "state": "orphan_evidence",
                "decision_override": "recover_orphan_evidence",
                "reason": "completed runner evidence exists without a formal accepted result",
                "replacement_eligible": False,
                "orphan_evidence": orphan_evidence,
            }
    if last_liveness_status in _WAIT_LIVENESS_FAILURE_STATUSES or last_liveness_status in _WAIT_NO_OUTPUT_STATUSES:
        return {
            **base,
            "state": "current_liveness_failure",
            "decision_override": "reissue_or_replace_lease",
            "reason": f"current liveness status is {last_liveness_status}",
            "replacement_eligible": True,
        }
    if action.action_type == "wait_for_ack":
        elapsed = _elapsed_seconds_since(lease_map.get("created_at"))
        ack_reminder_seconds = _guard_config_int(ledger, "ack_reminder_seconds", _WAIT_ACK_REMINDER_SECONDS)
        ack_blocker_seconds = _guard_config_int(ledger, "ack_blocker_seconds", _WAIT_ACK_BLOCKER_SECONDS)
        if elapsed is not None and elapsed >= ack_blocker_seconds:
            return {
                **base,
                "state": "ack_blocker_due",
                "decision_override": "reissue_or_replace_lease",
                "reason": "ACK wait exceeded blocker threshold",
                "replacement_eligible": True,
                "elapsed_seconds": elapsed,
                "ack_reminder_seconds": ack_reminder_seconds,
                "ack_blocker_seconds": ack_blocker_seconds,
            }
        state = "wait_reminder_due" if elapsed is not None and elapsed >= ack_reminder_seconds else "wait_patrol"
        return {
            **base,
            "state": state,
            "reason": "assigned lease has not acknowledged",
            "elapsed_seconds": elapsed,
            "ack_reminder_seconds": ack_reminder_seconds,
            "ack_blocker_seconds": ack_blocker_seconds,
        }

    elapsed = _elapsed_seconds_since(lease_map.get("ack_received_at") or lease_map.get("created_at"))
    result_liveness_seconds = _guard_config_int(ledger, "result_liveness_seconds", _WAIT_RESULT_LIVENESS_SECONDS)
    if progress_recent:
        return {
            **base,
            "state": "grace_wait",
            "reason": "active lease recorded current-run progress",
            "elapsed_seconds": elapsed,
            "result_liveness_seconds": result_liveness_seconds,
        }
    state = "liveness_check_due" if elapsed is not None and elapsed >= result_liveness_seconds else "wait_patrol"
    reason = (
        "result wait reached liveness-check threshold; replacement still needs current failure evidence"
        if state == "liveness_check_due"
        else "ACK is liveness only and result is still required"
    )
    return {
        **base,
        "state": state,
        "reason": reason,
        "elapsed_seconds": elapsed,
        "result_liveness_seconds": result_liveness_seconds,
    }


def _guard_wait_subject(ledger: Mapping[str, Any], action: RuntimeAction) -> dict[str, Any]:
    packet = ledger.get("packets", {}).get(action.subject_id)
    if not isinstance(packet, Mapping):
        return {"packet_id": action.subject_id, "packet_found": False}
    lease_id = str(packet.get("assigned_lease_id") or "")
    lease = ledger.get("leases", {}).get(lease_id)
    lease_map = lease if isinstance(lease, Mapping) else {}
    return {
        "packet_id": action.subject_id,
        "packet_found": True,
        "packet_status": str(packet.get("status", "")),
        "packet_kind": str((packet.get("envelope") or {}).get("packet_kind", "task")),
        "route_version": (packet.get("envelope") or {}).get("route_version"),
        "source_generation": (packet.get("envelope") or {}).get("source_generation"),
        "lease_id": lease_id,
        "lease_found": bool(lease_map),
        "lease_status": str(lease_map.get("status", "")),
        "ack_received": bool(lease_map.get("ack_received")),
        "accepted_result_id": str(packet.get("accepted_result_id") or ""),
        "progress_count": int(lease_map.get("progress_count", 0) or 0),
        "last_progress_status": str(lease_map.get("last_progress_status", "")),
        "last_progress_at": str(lease_map.get("last_progress_at", "")),
        "last_liveness_status": str(
            lease_map.get("liveness_status") or lease_map.get("last_liveness_status") or lease_map.get("last_progress_status", "")
        ),
        "liveness_checked_at": str(lease_map.get("liveness_checked_at", "")),
        "liveness_source": str(lease_map.get("liveness_source", "")),
        "stale_result_blockers": _stale_result_blockers_for_packet(ledger, action.subject_id),
    }


def _guard_decision(
    ledger: Mapping[str, Any],
    action: RuntimeAction,
    *,
    trigger: str,
    repeated_count: int,
    wait_recovery: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    threshold = int((ledger.get("lifecycle_guard_config") or {}).get("max_repeated_action_without_event", 3))
    wait_recovery_map = wait_recovery if isinstance(wait_recovery, Mapping) else {}
    override = str(wait_recovery_map.get("decision_override") or "")
    if override:
        return override, str(wait_recovery_map.get("reason") or action.reason)
    if action.action_type == "terminal_complete":
        closure = ledger.get("closure") or {}
        if isinstance(closure, Mapping) and closure.get("decision") == "complete":
            return "terminal_return", "final closure is complete and Controller stop is allowed"
        return "control_plane_stuck", "terminal action appeared without complete closure evidence"
    if action.action_type == "terminal_lifecycle":
        status = terminal_lifecycle_status(ledger)
        if status:
            return "terminal_return", f"run lifecycle is {status}; Controller stop is allowed"
        return "control_plane_stuck", "terminal lifecycle action appeared without terminal lifecycle evidence"
    if action.action_type == "wait_for_ack":
        return "wait_for_ack", str(wait_recovery_map.get("reason") or "assigned lease has not acknowledged")
    if action.action_type == "wait_for_result":
        return "wait_for_result", str(wait_recovery_map.get("reason") or "ACK is liveness only and result is still required")
    if action.action_type == "replace_lease":
        return "reissue_or_replace_lease", "assigned lease is inactive"
    if action.action_type == "repair_accepted_packet":
        return "repair_assignment_race", "accepted packet has stale assignment or active replacement lease"
    if action.action_type == "repair_packet":
        stale = _stale_result_blockers_for_packet(ledger, action.subject_id)
        if stale:
            return "quarantine_stale_result", ",".join(stale)
        return "recover_packet", "packet result or review is blocked"
    if action.action_type in {"wait_for_resume", "resume_reconcile"}:
        return action.action_type, action.reason
    if (
        trigger in _GUARD_STUCK_TRIGGERS
        and repeated_count >= threshold
        and classify_runtime_action(action) != "router_internal"
    ):
        return "control_plane_stuck", "same nonterminal next action repeated without current-run progress"
    return "process_next_action", action.reason


def preview_lifecycle_guard(ledger: Mapping[str, Any], *, trigger: str = "status") -> dict[str, Any]:
    action = _guard_next_action(ledger)
    action_key = _guard_action_key(action)
    event_count = _non_guard_event_count(ledger)
    history = list(ledger.get("lifecycle_guard_history") or [])
    previous = history[-1] if history and isinstance(history[-1], Mapping) else {}
    if previous.get("action_key") == action_key and previous.get("observed_event_count") == event_count:
        repeated_count = int(previous.get("repeated_count", 1)) + 1
    else:
        repeated_count = 1
    wait_recovery = _guard_wait_recovery(ledger, action, trigger=trigger, repeated_count=repeated_count)
    decision, reason = _guard_decision(
        ledger,
        action,
        trigger=trigger,
        repeated_count=repeated_count,
        wait_recovery=wait_recovery,
    )
    controller_stop_allowed = decision == "terminal_return"
    wait_subject = _guard_wait_subject(ledger, action) if action.subject_id else {}
    return {
        "schema_version": "black_box_flowpilot.lifecycle_guard.v1",
        "trigger": trigger,
        "created_at": now_iso(),
        "run_id": str(ledger.get("run_id", ledger.get("project_id", ""))),
        "active_route_version": ledger.get("active_route_version"),
        "source_generation": ledger.get("source_generation"),
        "observed_event_count": event_count,
        "action_key": action_key,
        "next_action": action.to_json(),
        "next_action_class": classify_runtime_action(action),
        "decision": decision,
        "reason": reason,
        "controller_stop_allowed": controller_stop_allowed,
        "foreground_required_mode": "terminal_return" if controller_stop_allowed else "process_guard_action",
        "repeated_count": repeated_count,
        "wait_subject": wait_subject,
        "wait_recovery": wait_recovery,
        "sealed_bodies_visible": False,
    }


def final_return_preflight(
    ledger: Mapping[str, Any],
    *,
    guard: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return current-state evidence for whether foreground Controller may exit."""

    guard_map = guard if isinstance(guard, Mapping) else preview_lifecycle_guard(ledger, trigger="final_preflight_preview")
    next_action = guard_map.get("next_action") if isinstance(guard_map.get("next_action"), Mapping) else {}
    closure = ledger.get("closure") if isinstance(ledger.get("closure"), Mapping) else {}
    terminal_status = terminal_lifecycle_status(ledger)
    blockers: list[str] = []
    if guard_map.get("controller_stop_allowed") is not True:
        blockers.append("lifecycle_guard_disallows_stop")
    if guard_map.get("decision") != "terminal_return":
        blockers.append(f"guard_decision:{guard_map.get('decision', 'unknown')}")
    if terminal_status:
        if next_action.get("action_type") != "terminal_lifecycle":
            blockers.append(f"next_action:{next_action.get('action_type', 'unknown')}")
    else:
        if next_action.get("action_type") != "terminal_complete":
            blockers.append(f"next_action:{next_action.get('action_type', 'unknown')}")
        if closure.get("decision") != "complete":
            blockers.append(f"closure:{closure.get('decision', 'not_attempted')}")
    return {
        "schema_version": "black_box_flowpilot.final_return_preflight.v1",
        "checked_at": now_iso(),
        "allowed": not blockers,
        "blockers": sorted(set(blockers)),
        "controller_stop_allowed": bool(guard_map.get("controller_stop_allowed") is True),
        "guard_decision": str(guard_map.get("decision", "")),
        "next_action_type": str(next_action.get("action_type", "")),
        "closure_decision": str(closure.get("decision", "not_attempted")),
        "terminal_lifecycle_status": terminal_status,
        "sealed_bodies_visible": False,
    }


def _foreground_duty_action(guard: Mapping[str, Any]) -> str:
    decision = str(guard.get("decision", ""))
    if guard.get("controller_stop_allowed") is True and decision == "terminal_return":
        return "terminal_return"
    if decision in _WAIT_PATROL_DECISIONS:
        return "wait_patrol"
    if decision in _RECOVERY_DUTY_DECISIONS:
        return "recover_or_reissue"
    if decision == "control_plane_stuck":
        return "control_plane_blocker"
    return "process_next_action"


def _foreground_wait_patrol(
    ledger: Mapping[str, Any],
    guard: Mapping[str, Any],
) -> dict[str, Any]:
    config = ledger.get("foreground_duty_config") if isinstance(ledger.get("foreground_duty_config"), Mapping) else {}
    seconds = int(config.get("wait_patrol_seconds", _DEFAULT_WAIT_PATROL_SECONDS))
    wait_subject = guard.get("wait_subject") if isinstance(guard.get("wait_subject"), Mapping) else {}
    wait_recovery = guard.get("wait_recovery") if isinstance(guard.get("wait_recovery"), Mapping) else {}
    return {
        "active": True,
        "kind": "timed_patrol",
        "seconds": seconds,
        "subject_id": str((guard.get("next_action") or {}).get("subject_id", "")) if isinstance(guard.get("next_action"), Mapping) else "",
        "waiting_for": str(guard.get("decision", "")),
        "reason": str(guard.get("reason", "")),
        "packet_id": str(wait_subject.get("packet_id", "")),
        "wait_recovery": _copy_jsonable(wait_recovery),
        "after_wait": "refresh_lifecycle_guard_and_foreground_duty",
        "refresh_command": (
            "python skills\\flowpilot\\assets\\flowpilot_new.py "
            f"--root <project-root> --json patrol --sleep-seconds {seconds}"
        ),
    }


def preview_foreground_duty(
    ledger: Mapping[str, Any],
    *,
    guard: Mapping[str, Any] | None = None,
    trigger: str = "status",
) -> dict[str, Any]:
    guard_map = guard if isinstance(guard, Mapping) else preview_lifecycle_guard(ledger, trigger=trigger)
    next_action = guard_map.get("next_action") if isinstance(guard_map.get("next_action"), Mapping) else {}
    action = _foreground_duty_action(guard_map)
    preflight = final_return_preflight(ledger, guard=guard_map)
    duty = {
        "schema_version": "black_box_flowpilot.foreground_duty.v1",
        "trigger": trigger,
        "created_at": now_iso(),
        "run_id": str(ledger.get("run_id", ledger.get("project_id", ""))),
        "action": action,
        "reason": str(guard_map.get("reason", "")),
        "subject_id": str(next_action.get("subject_id", "")),
        "next_action": _copy_jsonable(next_action),
        "lifecycle_guard_decision": str(guard_map.get("decision", "")),
        "controller_stop_allowed": bool(guard_map.get("controller_stop_allowed") is True),
        "final_return_preflight": preflight,
        "legacy_monitor_required": False,
        "status_projection_stop_authority": False,
        "sealed_bodies_visible": False,
    }
    if action == "wait_patrol":
        duty["wait_patrol"] = _foreground_wait_patrol(ledger, guard_map)
    elif action == "recover_or_reissue":
        duty["recovery"] = {
            "required": True,
            "decision": str(guard_map.get("decision", "")),
            "reason": str(guard_map.get("reason", "")),
            "subject_id": str(next_action.get("subject_id", "")),
            "wait_recovery": _copy_jsonable(
                guard_map.get("wait_recovery") if isinstance(guard_map.get("wait_recovery"), Mapping) else {}
            ),
        }
    elif action == "control_plane_blocker":
        duty["blocker"] = {
            "required": True,
            "decision": str(guard_map.get("decision", "")),
            "reason": str(guard_map.get("reason", "")),
            "action_key": str(guard_map.get("action_key", "")),
            "repeated_count": int(guard_map.get("repeated_count", 0) or 0),
        }
    return duty


def refresh_foreground_duty(
    ledger: dict[str, Any],
    *,
    guard: Mapping[str, Any] | None = None,
    trigger: str = "save",
    record_history: bool = True,
) -> dict[str, Any]:
    duty = preview_foreground_duty(ledger, guard=guard, trigger=trigger)
    ledger["foreground_duty"] = duty
    if record_history:
        history = ledger.setdefault("foreground_duty_history", [])
        history.append(
            {
                "created_at": duty["created_at"],
                "trigger": trigger,
                "action": duty["action"],
                "subject_id": duty.get("subject_id", ""),
                "lifecycle_guard_decision": duty.get("lifecycle_guard_decision", ""),
                "final_return_allowed": duty.get("final_return_preflight", {}).get("allowed", False),
                "wait_seconds": duty.get("wait_patrol", {}).get("seconds", 0),
            }
        )
        del history[:-_FOREGROUND_DUTY_HISTORY_LIMIT]
        ledger["foreground_duty_history"] = history
    return duty


def refresh_lifecycle_guard(
    ledger: dict[str, Any],
    *,
    trigger: str = "save",
    resume_source: str = "",
    record_history: bool = True,
    record_event: bool = True,
) -> dict[str, Any]:
    snapshot = preview_lifecycle_guard(ledger, trigger=trigger)
    if resume_source:
        snapshot["resume_source"] = resume_source
    history = ledger.setdefault("lifecycle_guard_history", [])
    if record_history:
        history.append(
            {
                "created_at": snapshot["created_at"],
                "trigger": trigger,
                "decision": snapshot["decision"],
                "controller_stop_allowed": snapshot["controller_stop_allowed"],
                "action_key": snapshot["action_key"],
                "observed_event_count": snapshot["observed_event_count"],
                "repeated_count": snapshot["repeated_count"],
                "subject_id": snapshot["next_action"].get("subject_id", ""),
            }
        )
        del history[:-_GUARD_HISTORY_LIMIT]
        ledger["lifecycle_guard_history"] = history
    ledger["lifecycle_guard"] = snapshot
    _persist_orphan_evidence_from_guard(ledger, snapshot)
    refresh_foreground_duty(
        ledger,
        guard=snapshot,
        trigger=trigger,
        record_history=record_history,
    )
    if record_event:
        _event(
            ledger,
            "lifecycle_guard_refreshed",
            trigger=trigger,
            decision=snapshot["decision"],
            controller_stop_allowed=snapshot["controller_stop_allowed"],
            subject_id=snapshot["next_action"].get("subject_id", ""),
        )
    return snapshot


def assert_controller_stop_allowed(ledger: Mapping[str, Any]) -> None:
    preflight = final_return_preflight(ledger)
    if preflight.get("allowed") is not True:
        blockers = ", ".join(str(item) for item in preflight.get("blockers", []))
        raise BlackBoxRuntimeError(f"Controller cannot stop before final-return preflight passes: {blockers}")


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
    for blocker in _active_semantic_blockers(ledger):
        blockers.append(f"active_semantic_blocker:{blocker.get('blocker_id', '')}")
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
    if high_standard_flow_required(ledger):
        matrix = ledger.get("final_requirement_evidence_matrix")
        if not isinstance(matrix, dict):
            blockers.append("missing_final_requirement_evidence_matrix")
        else:
            for item in matrix.get("unresolved", []):
                blockers.append(str(item))
            if int(matrix.get("unresolved_count", 0)) != 0:
                blockers.append("final_requirement_evidence_matrix_unresolved")
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
    terminal_status = terminal_lifecycle_status(ledger)
    if terminal_status:
        return RuntimeAction("terminal_lifecycle", f"run lifecycle is {terminal_status}", terminal_status)
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

    stopped_blockers = _stopped_semantic_blockers(ledger)
    if stopped_blockers:
        blocker_id = str(stopped_blockers[0].get("blocker_id") or "")
        return RuntimeAction("wait_for_resume", "PM stopped a semantic blocker for user decision", blocker_id)

    active_route = ledger["active_route_version"]
    active_packets = [
        packet
        for packet in ledger.get("packets", {}).values()
        if packet["envelope"]["route_version"] == active_route
    ]
    if not active_packets:
        if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
            return RuntimeAction("issue_preplanning_gate_packet", "preplanning high-standard gates are required", responsibility="pm")
        return RuntimeAction("issue_task_packet", "active route has no task packets", responsibility="worker")

    for packet in active_packets:
        if packet.get("accepted_result_id") and _accepted_packet_repair_needed(ledger, packet):
            return RuntimeAction(
                "repair_accepted_packet",
                "accepted packet has stale assignment or active replacement lease",
                packet["packet_id"],
            )
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
        if packet["status"] in {"result_blocked", "review_blocked", "system_validation_blocked", "flowguard_blocked"}:
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

    if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
        return RuntimeAction("issue_preplanning_gate_packet", "preplanning high-standard gates are required", responsibility="pm")

    for blocker in _active_semantic_blockers(ledger):
        packet_id = str(blocker.get("pm_repair_packet_id") or "")
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, Mapping) or packet.get("status") in {"accepted", "quarantined_after_route_mutation"}:
            return RuntimeAction(
                "issue_pm_repair_decision_packet",
                "semantic blocker requires PM repair decision",
                str(blocker.get("blocker_id") or ""),
                "pm",
            )

    if recursive_route_required(ledger):
        frontier = ledger.get("execution_frontier") or {}
        node_id = str(frontier.get("active_node_id") or "")
        if not ledger.get("route_nodes"):
            return RuntimeAction("materialize_route_nodes", "PM planning chain must materialize route nodes before closure")
        if node_id:
            node = ledger.get("route_nodes", {}).get(node_id, {})
            if high_standard_flow_required(ledger) and not _node_acceptance_plan_accepted(ledger, node_id):
                return RuntimeAction(
                    "issue_node_acceptance_plan_packet",
                    "frontier node requires accepted node acceptance plan",
                    node_id,
                    "pm",
                    "development_process",
                )
            if high_standard_flow_required(ledger) and node.get("status") == "awaiting_parent_backward_replay":
                return RuntimeAction(
                    "issue_parent_backward_replay_packet",
                    "parent/module node requires backward replay before PM disposition",
                    node_id,
                    "reviewer",
                    "development_process",
                )
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
        "lifecycle_guard": _copy_jsonable(ledger.get("lifecycle_guard") or preview_lifecycle_guard(ledger, trigger="render")),
        "foreground_duty": _copy_jsonable(
            ledger.get("foreground_duty")
            or preview_foreground_duty(
                ledger,
                guard=ledger.get("lifecycle_guard") if isinstance(ledger.get("lifecycle_guard"), Mapping) else None,
                trigger="render",
            )
        ),
        "status_projection_authority": "display_only",
        "runtime_authority": "current_run_ledger_lifecycle_guard_foreground_duty",
        "legacy_monitor_required": False,
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
                "liveness_status": lease.get("liveness_status", ""),
                "liveness_checked_at": lease.get("liveness_checked_at", ""),
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
        "system_closures": [
            {
                "closure_id": closure.get("closure_id", ""),
                "status": closure.get("status", ""),
                "subject_packet_id": closure.get("subject_packet_id", ""),
                "validation_evidence_id": closure.get("validation_evidence_id", ""),
            }
            for closure in ledger.get("system_closures", {}).values()
        ],
        "packet_outcomes": [
            {
                "outcome_id": outcome["outcome_id"],
                "packet_id": outcome["packet_id"],
                "packet_kind": outcome["packet_kind"],
                "subject_packet_id": outcome["subject_packet_id"],
                "owner_role": outcome["owner_role"],
                "decision": outcome["decision"],
                "blocking": outcome["blocking"],
                "blocker_class": outcome["blocker_class"],
            }
            for outcome in ledger.get("packet_outcomes", {}).values()
        ],
        "active_blockers": [
            {
                "blocker_id": blocker["blocker_id"],
                "status": blocker["status"],
                "packet_id": blocker["packet_id"],
                "subject_packet_id": blocker["subject_packet_id"],
                "repair_target_packet_id": blocker["repair_target_packet_id"],
                "required_recheck_role": blocker["required_recheck_role"],
                "blocker_class": blocker["blocker_class"],
                "pm_repair_packet_id": blocker.get("pm_repair_packet_id", ""),
                "pm_repair_decision_id": blocker.get("pm_repair_decision_id", ""),
            }
            for blocker in ledger.get("active_blockers", {}).values()
            if blocker.get("status") in {"active", "repairing", "awaiting_recheck", "awaiting_pm_decision_gate"}
        ],
        "pm_decision_gates": [
            {
                "gate_id": gate.get("gate_id", ""),
                "gate_kind": gate.get("gate_kind", ""),
                "status": gate.get("status", ""),
                "source_packet_id": gate.get("source_packet_id", ""),
                "decision": gate.get("decision", ""),
                "flowguard_order_id": gate.get("flowguard_order_id", ""),
                "review_id": gate.get("review_id", ""),
                "validation_evidence_id": gate.get("validation_evidence_id", ""),
                "system_closure_id": gate.get("system_closure_id", ""),
            }
            for gate in ledger.get("pm_decision_gates", {}).values()
        ],
        "host_evidence": list(ledger.get("host_evidence", {}).values()),
        "host_liveness_reports": list(ledger.get("host_liveness_reports", {}).values()),
        "orphan_evidence": list(ledger.get("orphan_evidence", {}).values()),
        "route_nodes": [
            {
                "node_id": node.get("node_id", ""),
                "route_version": node.get("route_version"),
                "title": node.get("title", ""),
                "status": node.get("status", ""),
                "responsibility": node.get("responsibility", ""),
                "modeled_target": node.get("modeled_target", ""),
                "repair_generation": node.get("repair_generation", 0),
                "packet_ids": list(node.get("packet_ids", [])),
                "node_acceptance_plan_id": node.get("node_acceptance_plan_id", ""),
                "parent_backward_replay_id": node.get("parent_backward_replay_id", ""),
                "pm_disposition_id": node.get("pm_disposition_id", ""),
                "sealed_bodies_visible": False,
            }
            for node in ledger.get("route_nodes", {}).values()
        ],
        "high_standard_control_flow": {
            "required": high_standard_flow_required(ledger),
            "high_standard_contract_status": (ledger.get("high_standard_contract") or {}).get("status", "missing"),
            "discovery_status": (ledger.get("preplanning_discovery") or {}).get("status", "missing"),
            "skill_standard_status": (ledger.get("skill_standard_contract") or {}).get("status", "missing"),
            "node_acceptance_plan_count": len(ledger.get("node_acceptance_plans", {})),
            "parent_backward_replay_count": len(ledger.get("parent_backward_replays", {})),
        },
        "execution_frontier": _copy_jsonable(ledger.get("execution_frontier") or {}),
        "final_route_wide_gate_ledger": _copy_jsonable(ledger.get("final_route_wide_gate_ledger") or {"decision": "not_built"}),
        "final_requirement_evidence_matrix": _copy_jsonable(ledger.get("final_requirement_evidence_matrix") or {"decision": "not_built"}),
        "cutover_gate": _copy_jsonable(ledger.get("cutover_gate") or {"decision": "not_evaluated"}),
        "display_surface": _copy_jsonable(ledger.get("display_surface") or {}),
        "closure": _copy_jsonable(ledger.get("closure") or {"decision": "not_attempted"}),
    }


def _route_stage(ledger: Mapping[str, Any]) -> str:
    terminal_status = terminal_lifecycle_status(ledger)
    if terminal_status:
        return terminal_status
    if not ledger.get("startup_intake"):
        return "startup_intake"
    if not ledger.get("contract_frozen"):
        return "contract_freeze"
    if ledger.get("active_route_version") is None:
        return "route_planning"
    if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
        return "high_standard_preplanning"
    if _active_semantic_blockers(ledger):
        return "semantic_repair"
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
