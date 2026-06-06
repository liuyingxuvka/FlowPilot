"""Clean FlowPilot core runtime for dynamic execution.

The runtime is deliberately small and serializable. It implements the current
protocol rules needed for a project ledger, dynamic agent leases, sealed
packets, FlowGuard work orders, independent review, safe console projection,
and final backward closure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - direct module test fallback.
    from . import control_surface
except ImportError:  # pragma: no cover
    import control_surface  # type: ignore


SCHEMA_VERSION = "black_box_flowpilot_runtime.v1"
ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
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
PM_VISIBLE_SUMMARY_REQUIRED_PACKET_KINDS = {
    "task",
    "flowguard_check",
    "review",
}
PM_VISIBLE_SUMMARY_EXEMPT_RESPONSIBILITIES = {
    "pm",
    "planner",
}
PM_VISIBLE_SUMMARY_MAX_ENTRIES = 8
REPLAYABLE_ARTIFACT_ACCEPTANCE_CRITERION = (
    "Scripts, checkers, and evidence generators must be replayable; do not make execution depend on a "
    "specific FlowPilot packet id, current active packet, or one-time phase."
)

PREPLANNING_GATE_SCOPES = {
    "high_standard_contract",
    "discovery",
    "skill_standard",
}
NODE_PREWORK_FLOWGUARD_SCOPE = "node_prework_flowguard"
NODE_CONTEXT_PACKAGE_REQUIRED_LIST_FIELDS = {
    "acceptance_criteria",
    "relevant_references",
    "evidence_targets",
    "inspection_targets",
    "known_risks",
    "flowguard_targets",
    "reviewer_starting_points",
}
STAGED_EFFECT_SCHEMA_VERSION = "black_box_flowpilot.staged_effect.v1"
STAGED_EFFECT_KINDS = {
    "commit_node_acceptance_plan",
    "commit_route_redesign",
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
    "node_context_package_accepted": "route",
    "node_prework_flowguard_accepted": "flowguard",
    "repair_scope_replaced": "route",
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
    "role_continuity_reused": "lease",
    "role_continuity_replaced": "lease",
    "role_continuity_initialized": "lease",
    "role_continuity_hydrated": "lease",
    "role_assignment_resolved": "lease",
    "role_assignment_committed": "lease",
    "role_assignment_blocked": "lease",
    "role_memory_seed_attached": "lease",
    "role_memory_seed_missing": "lease",
    "orphan_evidence_detected": "validation",
    "task_packet_issued": "packet",
    "packet_assigned": "packet",
    "sealed_packet_body_opened": "packet",
    "sealed_result_body_opened": "packet",
    "lease_ack": "lease",
    "lease_progress": "lease",
    "accepted_packet_assignment_repaired": "packet",
    "result_submitted": "packet",
    "result_mechanical_contract_blocked": "packet",
    "current_contract_reissue_packet_issued": "packet",
    "packet_outcome_recorded": "packet",
    "semantic_blocker_recorded": "repair",
    "semantic_blocker_cleared": "repair",
    "pm_repair_decision_recorded": "repair",
    "pm_repair_decision_blocked": "repair",
    "pm_decision_gate_staged": "repair",
    "pm_decision_gate_applied": "repair",
    "staged_effect_committed": "repair",
    "stopped_blocker_resolved": "repair",
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
_ROLE_NONREUSABLE_LIVENESS_STATUSES = _WAIT_LIVENESS_FAILURE_STATUSES | _WAIT_NO_OUTPUT_STATUSES
TERMINAL_LIFECYCLE_STATUSES = {"stopped_by_user", "cancelled_by_user"}
_STALE_RESULT_BLOCKERS = {
    "closed_or_inactive_lease",
    "quarantined_packet",
    "stale_route_version",
    "stale_evidence",
    "wrong_lease_for_packet",
    "duplicate_after_packet_accepted",
}
BACKGROUND_COLLABORATION_ACK_FIELD = "background_collaboration_authorized"
BACKGROUND_COLLABORATION_REQUIRED_MESSAGE = "background_collaboration_authorized=true required"

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
ROLE_DISPATCH_ACTION_TYPES = {"resolve_role_assignment"}
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
        / "flowpilot_protocol_kernel"
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
        "node_context_packages": {},
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
        "role_continuity": {
            "schema_version": "black_box_flowpilot.role_continuity.v1",
            "roles": {},
        },
        "role_assignments": {},
        "role_memory": {},
        "orphan_evidence": {},
        "terminal_lifecycle": None,
        "imported_evidence": {},
        "cutover_gate": None,
        "user_events": [],
        "status_projection": None,
        "display_surface": {"preferred": "cockpit", "active": "unknown", "block_reason": ""},
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize_evidence_summary_manifest(evidence_root: str | Path) -> dict[str, Any]:
    root = Path(evidence_root)
    if not root.exists() or not root.is_dir():
        raise BlackBoxRuntimeError(f"evidence root not found: {root}")
    skipped_names = {"evidence_summary.json", "evidence_summary.md"}
    evidence_files = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file() or path.name in skipped_names:
            continue
        evidence_files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "black_box_flowpilot.evidence_summary_manifest.v1",
        "evidence_root": str(root),
        "generated_at": now_iso(),
        "file_count": len(evidence_files),
        "evidence_files": evidence_files,
        "excluded_summary_artifacts": sorted(skipped_names),
        "sealed_bodies_visible": False,
    }
    (root / "evidence_summary.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


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


def background_collaboration_authorized(ledger: Mapping[str, Any]) -> bool:
    intake = ledger.get("startup_intake") if isinstance(ledger.get("startup_intake"), Mapping) else {}
    answers = intake.get("startup_answers") if isinstance(intake.get("startup_answers"), Mapping) else {}
    return answers.get(BACKGROUND_COLLABORATION_ACK_FIELD) is True


def background_collaboration_blocker(ledger: Mapping[str, Any]) -> str:
    if background_collaboration_authorized(ledger):
        return ""
    intake = ledger.get("startup_intake") if isinstance(ledger.get("startup_intake"), Mapping) else None
    if intake is None:
        return "background_collaboration_startup_intake_missing"
    if str(intake.get("status") or "") == "blocked":
        return "background_collaboration_required"
    answers = intake.get("startup_answers") if isinstance(intake.get("startup_answers"), Mapping) else None
    if answers is None or BACKGROUND_COLLABORATION_ACK_FIELD not in answers:
        return "background_collaboration_authorized_missing"
    return "background_collaboration_authorized_disabled"


def _require_background_collaboration_authorized(ledger: Mapping[str, Any]) -> None:
    blocker = background_collaboration_blocker(ledger)
    if blocker:
        raise BlackBoxRuntimeError(f"{BACKGROUND_COLLABORATION_REQUIRED_MESSAGE}: {blocker}")


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
        if _packet_is_noncurrent_for_routing(ledger, packet):
            continue
        if packet.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES:
            continue
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
) -> list[str]:
    """Create executable route nodes and initialize the frontier from a PM plan."""

    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot materialize route nodes without an active route")
    if high_standard_flow_required(ledger) and not preplanning_gates_accepted(ledger):
        raise BlackBoxRuntimeError("cannot materialize route nodes before high-standard preplanning gates")
    route_version = int(ledger["active_route_version"])
    plan_result = ledger.get("results", {}).get(planning_result_id, {})
    if not isinstance(plan_result, Mapping):
        raise BlackBoxRuntimeError("strict route plan schema violation: planning result is missing")
    plan_text = str(plan_result.get("body", ""))
    route_plan = _parse_strict_route_plan(plan_text)
    node_specs = _normalize_strict_route_plan_nodes(route_plan)

    route_nodes: dict[str, Any] = ledger.setdefault("route_nodes", {})
    materialized_ids: list[str] = []
    for index, spec in enumerate(node_specs, start=1):
        node_id = str(spec["node_id"])
        title = str(spec["title"])
        criteria = spec.get("acceptance_criteria")
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
            "required_outputs": list(spec.get("required_outputs") or []),
            "deliverable_checks": list(spec.get("deliverable_checks") or []),
            "validation_checks": list(spec.get("validation_checks") or []),
            "status": "pending",
            "repair_generation": 0,
            "packet_ids": [],
            "accepted_result_id": "",
            "accepted_repair_generation": None,
            "flowguard_order_ids": [],
            "prework_flowguard_order_ids": [],
            "prework_flowguard_packet_id": "",
            "prework_flowguard_order_id": "",
            "prework_flowguard_result_id": "",
            "prework_flowguard_repair_generation": None,
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "node_acceptance_plan_id": "",
            "node_context_package_id": "",
            "node_context_package_repair_generation": None,
            "parent_backward_replay_id": "",
            "parent_backward_waiver": "",
            "high_standard_requirement_ids": [str(item) for item in spec.get("high_standard_requirement_ids") or []],
            "skill_standard_obligation_ids": [str(item) for item in spec.get("skill_standard_obligation_ids") or []],
            "superseded_by": "",
            "stale_evidence": [],
            "created_from_result_id": planning_result_id,
            "route_plan_schema_version": route_plan.get("schema_version", ""),
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
    if not _node_prework_flowguard_accepted(ledger, node_id):
        raise BlackBoxRuntimeError(f"route node requires accepted pre-work FlowGuard gate before task packet: {node_id}")
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
                **_optional_node_context_reference(ledger, node_id),
                "instruction": (
                    "Complete this bounded route node from node_context_package and return concrete current-run evidence. "
                    "The context package is the minimum baseline; preserve the listed evidence and inspection targets."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        required_output_type="artifact",
        required_flowguard_target=str(node["modeled_target"]),
        route_node_id=node_id,
        route_scope="node",
        acceptance_criteria=list(node["acceptance_criteria"]),
        node_context_package_id=str(node.get("node_context_package_id") or ""),
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
    return (
        isinstance(plan, dict)
        and plan.get("status") == "accepted"
        and plan.get("node_id") == node_id
        and int(plan.get("repair_generation", -1)) == int(node.get("repair_generation", 0))
        and _node_context_package_current(ledger, node_id)
    )


def _node_context_package_current(ledger: Mapping[str, Any], node_id: str) -> bool:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    if not isinstance(node, Mapping):
        return False
    package_id = str(node.get("node_context_package_id") or "")
    if not package_id:
        return False
    if int(node.get("node_context_package_repair_generation", -1)) != int(node.get("repair_generation", 0)):
        return False
    package = ledger.get("node_context_packages", {}).get(package_id, {})
    return (
        isinstance(package, Mapping)
        and package.get("status") == "accepted"
        and package.get("node_id") == node_id
        and int(package.get("repair_generation", -1)) == int(node.get("repair_generation", 0))
    )


def _current_node_context_package(ledger: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    if not _node_context_package_current(ledger, node_id):
        raise BlackBoxRuntimeError(f"route node requires current PM node context package: {node_id}")
    node = _require(ledger.get("route_nodes", {}), node_id, "route node")
    package_id = str(node.get("node_context_package_id") or "")
    package = ledger.get("node_context_packages", {}).get(package_id, {})
    if not isinstance(package, Mapping):
        raise BlackBoxRuntimeError(f"node context package is missing: {package_id}")
    return _copy_jsonable(package)


def _node_context_reference(ledger: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    package = _current_node_context_package(ledger, node_id)
    return {
        "node_context_package_id": str(package.get("context_package_id") or ""),
        "node_context_package": package,
        "minimum_starting_context_not_boundary": True,
    }


def _optional_node_context_reference(ledger: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    if not node_id or not _node_context_package_current(ledger, node_id):
        return {}
    return _node_context_reference(ledger, node_id)


def _normalize_context_items(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise BlackBoxRuntimeError(f"node context package missing required list field: {field_name}")
    normalized: list[Any] = []
    for item in value:
        if isinstance(item, Mapping):
            normalized.append(_copy_jsonable(item))
        elif isinstance(item, (str, int, float, bool)):
            normalized.append(str(item))
        else:
            raise BlackBoxRuntimeError(f"node context package field has unsupported item: {field_name}")
    if not normalized:
        raise BlackBoxRuntimeError(f"node context package missing required list field: {field_name}")
    return normalized


def _node_context_package_from_pm_result(
    ledger: dict[str, Any],
    node: Mapping[str, Any],
    subject_packet: Mapping[str, Any],
    result_id: str,
    *,
    context_package_id: str = "",
    status: str = "accepted",
) -> dict[str, Any]:
    result = ledger.get("results", {}).get(result_id, {})
    payload = _parse_json_object(str(result.get("body", "")))
    raw_package = payload.get("node_context_package")
    if not isinstance(raw_package, Mapping):
        raise BlackBoxRuntimeError("node acceptance plan result missing top-level node_context_package")

    missing = [
        field
        for field in sorted(NODE_CONTEXT_PACKAGE_REQUIRED_LIST_FIELDS)
        if field not in raw_package
    ]
    purpose = str(raw_package.get("purpose") or "").strip()
    if not purpose:
        missing.append("purpose")
    if missing:
        raise BlackBoxRuntimeError(f"node context package missing required fields: {', '.join(sorted(missing))}")

    node_id = str(node.get("node_id") or "")
    package_id = context_package_id or _next_id(ledger, "node_context")
    normalized = {
        "schema_version": "black_box_flowpilot.node_context_package.v1",
        "context_package_id": package_id,
        "status": status,
        "node_id": node_id,
        "route_version": ledger.get("active_route_version"),
        "repair_generation": int(node.get("repair_generation", 0)),
        "node_title": str(node.get("title") or ""),
        "purpose": purpose,
        "acceptance_criteria": _normalize_context_items(raw_package.get("acceptance_criteria"), "acceptance_criteria"),
        "relevant_references": _normalize_context_items(raw_package.get("relevant_references"), "relevant_references"),
        "evidence_targets": _normalize_context_items(raw_package.get("evidence_targets"), "evidence_targets"),
        "inspection_targets": _normalize_context_items(raw_package.get("inspection_targets"), "inspection_targets"),
        "known_risks": _normalize_context_items(raw_package.get("known_risks"), "known_risks"),
        "flowguard_targets": _normalize_context_items(raw_package.get("flowguard_targets"), "flowguard_targets"),
        "reviewer_starting_points": _normalize_context_items(raw_package.get("reviewer_starting_points"), "reviewer_starting_points"),
        "source_packet_id": str(subject_packet.get("packet_id") or ""),
        "source_result_id": result_id,
        "source_package_path": "node_context_package",
        "sealed_body_boundary": "references_only_authorized_runtime_open_required",
        "minimum_starting_context_not_boundary": True,
        "created_at": now_iso(),
    }
    if str(raw_package.get("node_id") or node_id) != node_id:
        raise BlackBoxRuntimeError("node context package node_id does not match route node")
    return normalized


def _attach_staged_effect(
    record: dict[str, Any],
    *,
    effect_kind: str,
    source_packet_id: str,
    source_result_id: str,
    target_node_id: str = "",
    blocker_id: str = "",
    gate_id: str = "",
    route_scope: str = "",
) -> dict[str, Any]:
    if effect_kind not in STAGED_EFFECT_KINDS:
        raise BlackBoxRuntimeError(f"unknown staged effect kind: {effect_kind}")
    existing = record.get("staged_effect")
    if isinstance(existing, dict) and existing.get("effect_kind") == effect_kind and existing.get("status") == "pending":
        return existing
    effect = {
        "schema_version": STAGED_EFFECT_SCHEMA_VERSION,
        "effect_kind": effect_kind,
        "status": "pending",
        "source_packet_id": source_packet_id,
        "source_result_id": source_result_id,
        "target_node_id": target_node_id,
        "blocker_id": blocker_id,
        "gate_id": gate_id,
        "route_scope": route_scope,
        "created_at": now_iso(),
        "committed_at": "",
        "system_closure_id": "",
    }
    record["staged_effect"] = effect
    return effect


def _staged_effect_public_reference(record: Mapping[str, Any]) -> dict[str, Any]:
    effect = record.get("staged_effect") if isinstance(record, Mapping) else None
    if not isinstance(effect, Mapping):
        return {}
    return {
        "staged_effect": {
            "schema_version": str(effect.get("schema_version") or STAGED_EFFECT_SCHEMA_VERSION),
            "effect_kind": str(effect.get("effect_kind") or ""),
            "status": str(effect.get("status") or ""),
            "source_packet_id": str(effect.get("source_packet_id") or ""),
            "source_result_id": str(effect.get("source_result_id") or ""),
            "target_node_id": str(effect.get("target_node_id") or ""),
            "blocker_id": str(effect.get("blocker_id") or ""),
            "gate_id": str(effect.get("gate_id") or ""),
            "route_scope": str(effect.get("route_scope") or ""),
            "sealed_body_copied": False,
        }
    }


def _mark_staged_effect_committed(record: dict[str, Any], *, system_closure_id: str = "") -> None:
    effect = record.get("staged_effect")
    if not isinstance(effect, dict):
        return
    if effect.get("status") == "committed":
        return
    effect["status"] = "committed"
    effect["committed_at"] = now_iso()
    effect["system_closure_id"] = system_closure_id


def _node_prework_flowguard_accepted(ledger: Mapping[str, Any], node_id: str) -> bool:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    if not isinstance(node, Mapping):
        return False
    order_id = str(node.get("prework_flowguard_order_id") or "")
    if not order_id:
        return False
    if int(node.get("prework_flowguard_repair_generation", -1)) != int(node.get("repair_generation", 0)):
        return False
    order = ledger.get("flowguard_work_orders", {}).get(order_id, {})
    return isinstance(order, Mapping) and order.get("status") == "complete" and order.get("decision") == "pass"


def _open_or_live_node_prework_flowguard_packet(ledger: Mapping[str, Any], node_id: str) -> dict[str, Any] | None:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    repair_generation = int(node.get("repair_generation", 0)) if isinstance(node, Mapping) else 0
    for packet in reversed(list(ledger.get("packets", {}).values())):
        if not isinstance(packet, Mapping):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if envelope.get("packet_kind") != "flowguard_check":
            continue
        if envelope.get("route_scope") != NODE_PREWORK_FLOWGUARD_SCOPE:
            continue
        if envelope.get("route_node_id") != node_id:
            continue
        if int(packet.get("prework_repair_generation", -1)) != repair_generation:
            continue
        if _packet_is_noncurrent_for_routing(ledger, packet):
            continue
        if packet.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES:
            continue
        return dict(packet)
    return None


def _flowguard_route_candidates() -> list[dict[str, str]]:
    return [
        {
            "modeled_target": modeled_target,
            "selected_skill": selected_skill,
        }
        for modeled_target, selected_skill in sorted(_DEFAULT_FLOWGUARD_ROUTES.items())
    ]


def ensure_node_prework_flowguard_packet(ledger: dict[str, Any], node_id: str) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    if node.get("status") in {"accepted", "superseded", "waived"}:
        raise BlackBoxRuntimeError(f"route node is not executable: {node_id}")
    if high_standard_flow_required(ledger) and not _node_acceptance_plan_accepted(ledger, node_id):
        raise BlackBoxRuntimeError(f"route node requires accepted node acceptance plan before pre-work FlowGuard: {node_id}")
    if _node_prework_flowguard_accepted(ledger, node_id):
        return ""
    existing = _open_or_live_node_prework_flowguard_packet(ledger, node_id)
    if existing:
        return str(existing["packet_id"])

    plan_id = str(node.get("node_acceptance_plan_id") or "")
    plan = ledger.get("node_acceptance_plans", {}).get(plan_id, {}) if plan_id else {}
    subject_packet_id = str(plan.get("source_packet_id") or "")
    target_result_id = str(plan.get("source_result_id") or "")
    if not subject_packet_id:
        subject_packet_id = node_id

    packet_id = _next_id(ledger, "packet")
    evidence_root = _flowguard_packet_evidence_root(ledger, packet_id)
    modeled_target = str(node.get("modeled_target") or REQUIRED_FLOWGUARD_TARGET)
    route_candidates = _flowguard_route_candidates()
    node_context = _optional_node_context_reference(ledger, node_id)
    body = json.dumps(
        {
            "schema_version": "black_box_flowpilot.node_prework_flowguard_packet.v1",
            "route_node_id": node_id,
            "title": node.get("title", ""),
            "responsibility_after_pass": node.get("responsibility", ""),
            "modeled_target": modeled_target,
            "repair_generation": int(node.get("repair_generation", 0)),
            "node_acceptance_plan_id": plan_id,
            "node_acceptance_plan_source_packet_id": str(plan.get("source_packet_id") or ""),
            "node_acceptance_plan_source_result_id": str(plan.get("source_result_id") or ""),
            "acceptance_criteria": list(node.get("acceptance_criteria") or []),
            **node_context,
            "route_selection_policy": {
                "default_rule": "Choose FlowGuard route(s) by the thing being modeled, not by PM preference.",
                "scheduler_path": "skills/flowpilot/assets/flowpilot_protocol_kernel/flowguard_route_scheduler.json",
                "candidate_routes": route_candidates,
                "primary_modeled_target": modeled_target,
                "required_output_fields": [
                    "selected_routes",
                    "model_boundary",
                    "risks_found",
                    "skipped_checks",
                    "confidence_boundary",
                    "pm_repair_guidance",
                ],
                "multiple_routes_allowed": True,
                "pm_skip_decision_allowed": False,
            },
            "pm_visibility_policy": {
                "pm_can_read_model_artifacts": True,
                "pm_can_read_flowguard_report": True,
                "run_local_evidence_root": evidence_root,
                "required_for_repair": True,
            },
            "evidence_output_policy": {
                "run_local_evidence_root": evidence_root,
                "required_for_formal_run": True,
                "tracked_baseline_paths_forbidden_unless_explicit_baseline_update": [
                    "simulations/meta_thin_parent_results.json",
                    "simulations/meta_layered_full_results.json",
                    "simulations/capability_thin_parent_results.json",
                    "simulations/capability_layered_full_results.json",
                ],
            },
            "instruction": (
                "Mandatory pre-work FlowGuard gate. Inspect the PM node design before any worker task starts. "
                "Start from node_context_package, then independently select one or more FlowGuard routes, record "
                "PM-visible artifacts, declare pass only when the node design is safe to execute, and declare block "
                "with concrete PM repair guidance when it is not. The package is a minimum starting context, not a boundary."
            ),
        },
        indent=2,
        sort_keys=True,
    )
    issued_id = issue_task_packet(
        ledger,
        "flowguard_operator",
        f"Run pre-work FlowGuard for route node {node_id}",
        body,
        required_flowguard_target=modeled_target,
        packet_kind="flowguard_check",
        subject_id=subject_packet_id,
        target_result_id=target_result_id,
        preassigned_packet_id=packet_id,
        route_node_id=node_id,
        route_scope=NODE_PREWORK_FLOWGUARD_SCOPE,
        acceptance_criteria=list(node.get("acceptance_criteria") or []),
        node_context_package_id=str(node_context.get("node_context_package_id") or ""),
        authorized_result_reads=[
            _authorized_read_for_result(
                ledger,
                target_result_id,
                allowed_roles=["flowguard_operator"],
                purpose="node_acceptance_plan_result_for_prework_flowguard",
                required_before_submit=True,
            )
        ]
        if target_result_id
        else None,
    )
    ledger["packets"][issued_id]["prework_repair_generation"] = int(node.get("repair_generation", 0))
    node["prework_flowguard_packet_id"] = issued_id
    node["prework_flowguard_repair_generation"] = None
    return issued_id


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
                    "repair policy, and a node_context_package before any FlowGuard or worker task packet is issued. "
                    "The node_context_package must be the minimum starting context for FlowGuard, worker, and Reviewer."
                ),
                "required_node_context_package_fields": [
                    "purpose",
                    "acceptance_criteria",
                    "relevant_references",
                    "evidence_targets",
                    "inspection_targets",
                    "known_risks",
                    "flowguard_targets",
                    "reviewer_starting_points",
                ],
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
    normalized = decision if decision in {"accept", "repair_current_scope", "redesign_route", "block", "stop"} else "accept"
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
    elif normalized == "redesign_route":
        _replace_route_node_for_repair(ledger, node_id, disposition_id=disposition_id, reason=reason or "pm_disposition_redesign_route")
    elif normalized == "repair_current_scope":
        _replace_route_node_for_repair(ledger, node_id, disposition_id=disposition_id, reason=reason or "pm_disposition_repair_current_scope")
    else:
        node["status"] = "blocked" if normalized == "block" else "stopped"
        _frontier_update(ledger, node_id, node["status"], reason or f"pm_disposition_{normalized}")
    _event(ledger, "pm_disposition_recorded", node_id=node_id, disposition_id=disposition_id, decision=normalized)
    return disposition_id


def _evaluate_route_deliverable_checks(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> list[dict[str, Any]]:
    node_id = str(node.get("node_id") or "")
    results: list[dict[str, Any]] = []
    for raw_check in node.get("deliverable_checks") or []:
        if not isinstance(raw_check, Mapping):
            results.append(
                {
                    "node_id": node_id,
                    "check_id": "<invalid>",
                    "kind": "invalid",
                    "required": True,
                    "status": "failed",
                    "reason": "deliverable check is not an object",
                    "summary": f"Node {node_id} has an invalid route deliverable check",
                    "evidence": [],
                }
            )
            continue
        check = dict(raw_check)
        check_id = str(check.get("check_id") or "").strip()
        kind = str(check.get("kind") or "").strip()
        required = check.get("required", True) is not False
        result = {
            "node_id": node_id,
            "check_id": check_id,
            "kind": kind,
            "required": required,
            "path": str(check.get("path") or ""),
            "pattern": str(check.get("pattern") or ""),
            "status": "failed",
            "reason": "",
            "summary": "",
            "evidence": [],
        }
        if not check_id or kind not in {"path_exists", "path_glob_exists", "json_parse"}:
            result["reason"] = "invalid_deliverable_check_contract"
            result["summary"] = f"Node {node_id} deliverable check contract is invalid"
            results.append(result)
            continue
        if kind == "path_glob_exists":
            pattern = str(check.get("pattern") or check.get("path") or "").strip()
            matches, reason = _route_deliverable_glob_matches(ledger, pattern)
            if matches:
                result["status"] = "passed"
                result["reason"] = "matched"
                result["summary"] = f"Node {node_id} deliverable glob matched {len(matches)} path(s)"
                result["evidence"] = [f"path:{item}" for item in matches]
            else:
                result["reason"] = reason or "missing"
                result["summary"] = f"Node {node_id} deliverable glob did not match"
            result["pattern"] = pattern
            results.append(result)
            continue
        resolved, reason = _resolve_route_deliverable_path(ledger, str(check.get("path") or ""))
        if resolved is None:
            result["reason"] = reason
            result["summary"] = f"Node {node_id} deliverable path is not valid"
            results.append(result)
            continue
        result["path"] = resolved.as_posix()
        result["evidence"] = [f"path:{resolved.as_posix()}"]
        if kind == "path_exists":
            if resolved.exists():
                result["status"] = "passed"
                result["reason"] = "exists"
                result["summary"] = f"Node {node_id} deliverable path exists"
            else:
                result["reason"] = "missing"
                result["summary"] = f"Node {node_id} deliverable path is missing"
        elif kind == "json_parse":
            if not resolved.exists():
                result["reason"] = "missing"
                result["summary"] = f"Node {node_id} JSON deliverable path is missing"
            else:
                try:
                    json.loads(resolved.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    result["reason"] = "json_parse_failed"
                    result["summary"] = f"Node {node_id} JSON deliverable is not parseable"
                else:
                    result["status"] = "passed"
                    result["reason"] = "json_parse_passed"
                    result["summary"] = f"Node {node_id} JSON deliverable is parseable"
        results.append(result)
    return results


def _route_deliverable_project_root(ledger: Mapping[str, Any]) -> Path:
    for field in ("project_root", "workspace_root", "root"):
        raw_root = str(ledger.get(field) or "").strip()
        if raw_root:
            return Path(raw_root).resolve()
    raw_run_root = str(ledger.get("run_root") or "").strip()
    if raw_run_root:
        run_root = Path(raw_run_root).resolve()
        if run_root.parent.name == "runs" and run_root.parent.parent.name == ".flowpilot":
            return run_root.parent.parent.parent.resolve()
        return run_root
    return Path.cwd().resolve()


def _resolve_route_deliverable_path(ledger: Mapping[str, Any], raw_path: str) -> tuple[Path | None, str]:
    if not raw_path.strip():
        return None, "missing_path"
    root = _route_deliverable_project_root(ledger)
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not _path_is_within_root(resolved, root):
        return None, "outside_project_root"
    return resolved, ""


def _route_deliverable_glob_matches(ledger: Mapping[str, Any], pattern: str) -> tuple[list[str], str]:
    if not pattern.strip():
        return [], "missing_pattern"
    pattern_path = Path(pattern)
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        return [], "outside_project_root"
    root = _route_deliverable_project_root(ledger)
    try:
        matches = sorted(path.resolve().as_posix() for path in root.glob(pattern) if _path_is_within_root(path.resolve(), root))
    except (OSError, ValueError):
        return [], "invalid_pattern"
    return matches, "missing"


def _path_is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def build_final_route_wide_gate_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    nodes = list(ledger.get("route_nodes", {}).values())
    effective_nodes = [node for node in nodes if node.get("status") != "superseded"]
    unresolved: list[str] = []
    stale: list[str] = []
    deliverable_results: list[dict[str, Any]] = []
    for node in effective_nodes:
        node_id = str(node.get("node_id", ""))
        if node.get("status") not in {"accepted", "waived"}:
            unresolved.append(f"incomplete_node:{node_id}")
        if high_standard_flow_required(ledger) and not _node_context_package_current(ledger, node_id):
            unresolved.append(f"node_context_package_missing:{node_id}")
        if not _node_prework_flowguard_accepted(ledger, node_id):
            unresolved.append(f"node_prework_flowguard_missing:{node_id}")
        if node.get("stale_evidence"):
            stale.append(node_id)
        if node.get("required_outputs") and not node.get("deliverable_checks"):
            unresolved.append(f"route_deliverable_checks_missing:{node_id}")
        for check_result in _evaluate_route_deliverable_checks(ledger, node):
            deliverable_results.append(check_result)
            if check_result.get("required") and check_result.get("status") != "passed":
                unresolved.append(
                    "route_deliverable:"
                    f"{node_id}:{check_result.get('check_id', '')}:{check_result.get('status', 'failed')}"
                )
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, Mapping) or not _packet_requires_current_acceptance(ledger, packet):
            continue
        if packet.get("status") not in _NONCURRENT_PACKET_STATUSES:
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
        "deliverable_checks": deliverable_results,
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
            context_id = str(node.get("node_context_package_id") or "")
            add_row(
                f"{node_id}:context-package",
                "node_context_package",
                "covered" if _node_context_package_current(ledger, node_id) else "missing",
                [context_id] if context_id else [],
                f"Node {node_id} has current PM node context package",
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
            f"{node_id}:prework-flowguard",
            "prework_flowguard",
            "covered" if _node_prework_flowguard_accepted(ledger, node_id) else "missing",
            [str(node.get("prework_flowguard_order_id", ""))] if node.get("prework_flowguard_order_id") else [],
            f"Node {node_id} has accepted pre-work FlowGuard gate",
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
        if node.get("required_outputs") and not node.get("deliverable_checks"):
            add_row(
                f"{node_id}:deliverable-checks",
                "route_deliverable",
                "missing",
                [],
                f"Node {node_id} declares required outputs but no system deliverable checks",
            )
        for check_result in _evaluate_route_deliverable_checks(ledger, node):
            row_status = "covered" if check_result.get("status") == "passed" else str(check_result.get("status") or "failed")
            evidence_ids = [str(item) for item in check_result.get("evidence", [])]
            add_row(
                f"{node_id}:{check_result.get('check_id', '')}",
                "route_deliverable",
                row_status,
                evidence_ids,
                str(check_result.get("summary") or check_result.get("reason") or "Route deliverable check"),
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


def _parse_strict_route_plan(plan_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(plan_text)
    except json.JSONDecodeError as exc:
        raise BlackBoxRuntimeError(
            f"strict route plan schema violation: PM planning result must be JSON with schema_version {ROUTE_PLAN_SCHEMA_VERSION}"
        ) from exc
    if not isinstance(payload, dict):
        raise BlackBoxRuntimeError("strict route plan schema violation: PM route plan body must be a JSON object")
    if payload.get("schema_version") != ROUTE_PLAN_SCHEMA_VERSION:
        raise BlackBoxRuntimeError(
            f"strict route plan schema violation: schema_version must be {ROUTE_PLAN_SCHEMA_VERSION}"
        )
    if "route_nodes" in payload:
        raise BlackBoxRuntimeError("strict route plan schema violation: use nodes, not route_nodes")
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BlackBoxRuntimeError("strict route plan schema violation: nodes must be a non-empty list")
    return payload


def _normalize_strict_route_plan_nodes(route_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes = route_plan.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BlackBoxRuntimeError("strict route plan schema violation: nodes must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_node in enumerate(nodes, start=1):
        if not isinstance(raw_node, Mapping):
            raise BlackBoxRuntimeError(f"strict route plan schema violation: node {index} must be an object")
        node_id = str(raw_node.get("node_id") or "").strip()
        title = str(raw_node.get("title") or "").strip()
        if not node_id:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: node {index} missing node_id")
        if not title:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: node {node_id} missing title")
        if node_id in seen_ids:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: duplicate node_id {node_id}")
        seen_ids.add(node_id)
        normalized.append(
            {
                "node_id": node_id,
                "title": title,
                "node_kind": _strict_optional_string(raw_node, "node_kind", "leaf"),
                "parent_node_id": _strict_optional_string(raw_node, "parent_node_id", ""),
                "child_node_ids": _strict_string_list(raw_node, "child_node_ids", node_id),
                "responsibility": _strict_optional_string(raw_node, "responsibility", ""),
                "modeled_target": _strict_optional_string(raw_node, "modeled_target", ""),
                "acceptance_criteria": _strict_string_list(raw_node, "acceptance_criteria", node_id),
                "required_outputs": _strict_json_list(raw_node, "required_outputs", node_id),
                "deliverable_checks": _strict_deliverable_checks(raw_node, node_id),
                "validation_checks": _strict_json_list(raw_node, "validation_checks", node_id),
                "high_standard_requirement_ids": _strict_string_list(raw_node, "high_standard_requirement_ids", node_id),
                "skill_standard_obligation_ids": _strict_string_list(raw_node, "skill_standard_obligation_ids", node_id),
            }
        )
    return normalized


def _strict_optional_string(raw_node: Mapping[str, Any], field: str, default: str) -> str:
    if field not in raw_node or raw_node.get(field) is None:
        return default
    value = raw_node.get(field)
    if not isinstance(value, str):
        node_id = str(raw_node.get("node_id") or "<unknown>")
        raise BlackBoxRuntimeError(f"strict route plan schema violation: {node_id}.{field} must be a string")
    return value.strip()


def _strict_string_list(raw_node: Mapping[str, Any], field: str, node_id: str) -> list[str]:
    if field not in raw_node or raw_node.get(field) is None:
        return []
    value = raw_node.get(field)
    if not isinstance(value, list):
        raise BlackBoxRuntimeError(f"strict route plan schema violation: {node_id}.{field} must be a list")
    rows: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.{field}[{index}] must be a non-empty string"
            )
        rows.append(item.strip())
    return rows


def _strict_json_list(raw_node: Mapping[str, Any], field: str, node_id: str) -> list[Any]:
    if field not in raw_node or raw_node.get(field) is None:
        return []
    value = raw_node.get(field)
    if not isinstance(value, list):
        raise BlackBoxRuntimeError(f"strict route plan schema violation: {node_id}.{field} must be a list")
    return json.loads(json.dumps(value, sort_keys=True))


def _strict_deliverable_checks(raw_node: Mapping[str, Any], node_id: str) -> list[dict[str, Any]]:
    checks = _strict_json_list(raw_node, "deliverable_checks", node_id)
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, Mapping):
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{index}] must be an object"
            )
        check_id = str(check.get("check_id") or "").strip()
        kind = str(check.get("kind") or "").strip()
        if not check_id:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{index}] missing check_id"
            )
        if kind not in {"path_exists", "path_glob_exists", "json_parse"}:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] has unsupported kind"
            )
        if kind in {"path_exists", "json_parse"} and not str(check.get("path") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing path"
            )
        if kind == "path_glob_exists" and not str(check.get("pattern") or check.get("path") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing pattern"
            )
        normalized.append(json.loads(json.dumps(check, sort_keys=True)))
    return normalized


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
    if responsibility in RESPONSIBILITIES and responsibility not in {
        "planner",
        "flowguard_operator",
    }:
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
        if _packet_is_noncurrent_for_routing(ledger, packet):
            continue
        if packet.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES:
            continue
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
                "instruction": "Return a PM disposition. Default valid decision is accept; other valid decisions are repair_current_scope, redesign_route, block, or stop.",
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
    except json.JSONDecodeError as exc:
        raise BlackBoxRuntimeError("PM disposition requires a structured JSON object") from exc
    if not isinstance(payload, dict):
        raise BlackBoxRuntimeError("PM disposition requires a structured JSON object")
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision not in {"accept", "repair_current_scope", "redesign_route", "block", "stop"}:
        raise BlackBoxRuntimeError("PM disposition requires an explicit allowed decision")
    reason = str(payload.get("reason") or payload.get("summary") or "")
    return decision, reason


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
_ACTIVE_SEMANTIC_BLOCKER_STATUSES = {"active", "repairing", "awaiting_recheck"}
_CLEARABLE_SEMANTIC_BLOCKER_STATUSES = _ACTIVE_SEMANTIC_BLOCKER_STATUSES | {"repair_packet_open"}
_CURRENT_PACKET_BLOCKING_STATUSES = {"result_blocked", "review_blocked", "system_validation_blocked", "flowguard_blocked"}
_REPAIR_REPLACED_PACKET_STATUSES = _CURRENT_PACKET_BLOCKING_STATUSES | {"result_submitted"}
_NONCURRENT_PACKET_STATUSES = {"accepted", "quarantined_after_route_mutation", "superseded_after_repair"}
_NONCURRENT_ROUTE_NODE_STATUSES = {"accepted", "waived", "superseded"}
_PROGRESS_ROUTE_NODE_ENDED_STATUSES = {"accepted", "waived", "superseded", "blocked", "stopped"}
_PROGRESS_PACKET_ENDED_STATUSES = {
    "accepted",
    "result_blocked",
    "review_blocked",
    "system_validation_blocked",
    "flowguard_blocked",
    "quarantined_after_route_mutation",
    "superseded_after_repair",
}
_PM_REPAIR_DECISIONS = {
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
    "waive_with_authority",
    "stop_for_user",
}
_REMOVED_PM_REPAIR_DECISIONS = {
    "same_node_repair",
    "sender_reissue",
    "collect_more_evidence",
    "mutate_route",
    "quarantine_evidence",
}
_HIGH_RISK_PM_REPAIR_DECISIONS = {"redesign_route"}
_HIGH_RISK_PM_DISPOSITION_DECISIONS = {"redesign_route"}
def _strict_json_object_from_body(body: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_outcome_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _payload_outcome_token(payload: Mapping[str, Any], packet_kind: str) -> str:
    flowguard_report = payload.get("flowguard_report")
    if isinstance(flowguard_report, Mapping) and flowguard_report.get("ok") is False:
        return "block"
    return _normalize_outcome_token(payload.get("decision"))

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
    payload = _strict_json_object_from_body(body)
    token = _payload_outcome_token(payload, packet_kind) if payload else ""
    if token in _PASSING_OUTCOME_DECISIONS:
        decision = "pass"
    elif token in _BLOCKING_OUTCOME_DECISIONS:
        decision = "fail" if token in {"fail", "failed", "failure"} else "block"
    else:
        decision = "block"
    blocking = decision != "pass"
    recommendation = ""
    evidence_refs: list[str] = []
    blocker_class = _default_blocker_class(packet_kind, owner_role, token)
    if payload:
        if "blocking" in payload:
            payload_blocking = bool(payload.get("blocking"))
            if payload_blocking and decision == "pass":
                decision = "block"
                blocking = True
            elif decision != "pass":
                blocking = True
            else:
                blocking = False
        blocker_class = str(payload.get("blocker_class") or payload.get("failure_class") or blocker_class)
        structured_repairs = _structured_required_repairs_from_payload(payload)
        pm_visible_summary = _pm_visible_summary_from_payload(payload)
        recommendation = str(
            ("; ".join(structured_repairs) if structured_repairs else "")
            or payload.get("recommended_resolution")
            or payload.get("recommendation")
            or payload.get("pm_recommendation")
            or ("; ".join(pm_visible_summary) if blocking and pm_visible_summary else "")
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


def _route_node_is_noncurrent(ledger: Mapping[str, Any], route_node_id: str) -> bool:
    if not route_node_id:
        return False
    node = ledger.get("route_nodes", {}).get(route_node_id)
    return isinstance(node, Mapping) and node.get("status") in _NONCURRENT_ROUTE_NODE_STATUSES


def _packet_route_node_id(packet: Mapping[str, Any]) -> str:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    return str(envelope.get("route_node_id") or "")


def _packet_is_noncurrent_for_routing(ledger: Mapping[str, Any], packet: Mapping[str, Any]) -> bool:
    if packet.get("status") in _NONCURRENT_PACKET_STATUSES:
        return True
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    active_route = ledger.get("active_route_version")
    if active_route is not None and envelope.get("route_version") != active_route:
        return True
    return _route_node_is_noncurrent(ledger, _packet_route_node_id(packet))


def _packet_requires_current_acceptance(ledger: Mapping[str, Any], packet: Mapping[str, Any]) -> bool:
    if _packet_is_noncurrent_for_routing(ledger, packet):
        return False
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    active_route = ledger.get("active_route_version")
    if active_route is not None and envelope.get("route_version") != active_route:
        return False
    return True


def _coerce_nonnegative_int(value: Any) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return 0
    return max(coerced, 0)


def _progress_active_subject(ledger: Mapping[str, Any]) -> dict[str, Any]:
    try:
        action = router_next_action(ledger).to_json()
    except BlackBoxRuntimeError:
        return {}
    subject_id = str(action.get("subject_id") or "")
    packet = ledger.get("packets", {}).get(subject_id) if subject_id else None
    node_id = ""
    if isinstance(packet, Mapping):
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        node_id = str(envelope.get("route_node_id") or "")
    return {
        "action_type": str(action.get("action_type") or ""),
        "subject_id": subject_id,
        "route_node_id": node_id,
    }


def _progress_packets(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    active_route = ledger.get("active_route_version")
    packets: list[Mapping[str, Any]] = []
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, Mapping):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        packet_kind = str(envelope.get("packet_kind") or "task")
        if packet_kind not in PACKET_KINDS:
            continue
        if active_route is not None and envelope.get("route_version") != active_route:
            continue
        packets.append(packet)
    return packets


def current_progress_fraction(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Return Controller-safe current expanded node progress."""

    route_nodes = [
        node
        for node in ledger.get("route_nodes", {}).values()
        if isinstance(node, Mapping)
    ]
    if route_nodes:
        expanded_nodes = 0
        ended_nodes = 0
        repair_generations = 0
        for node in route_nodes:
            repairs = _coerce_nonnegative_int(node.get("repair_generation", 0))
            repair_generations += repairs
            expanded_nodes += 1 + repairs
            ended_nodes += repairs
            if str(node.get("status") or "") in _PROGRESS_ROUTE_NODE_ENDED_STATUSES:
                ended_nodes += 1
        source = "route_nodes"
        packet_projection_used = False
    else:
        packets = _progress_packets(ledger)
        expanded_nodes = len(packets)
        ended_nodes = sum(
            1
            for packet in packets
            if str(packet.get("status") or "") in _PROGRESS_PACKET_ENDED_STATUSES
        )
        repair_generations = 0
        source = "packets"
        packet_projection_used = True

    ended_nodes = min(ended_nodes, expanded_nodes)
    return {
        "schema_version": "black_box_flowpilot.progress_fraction.v1",
        "display": f"{ended_nodes}/{expanded_nodes}",
        "ended_nodes": ended_nodes,
        "expanded_nodes": expanded_nodes,
        "source": source,
        "equal_weight_nodes": True,
        "includes_repair_generations": True,
        "repair_generations": repair_generations,
        "packet_projection_used": packet_projection_used,
        "controller_relay_only": True,
        "percent_provided": False,
        "active_subject": _progress_active_subject(ledger),
        "sealed_bodies_visible": False,
    }


def _blocker_current_effective(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> bool:
    if blocker.get("status") not in _ACTIVE_SEMANTIC_BLOCKER_STATUSES:
        return False
    if blocker.get("cleared_by_outcome_id"):
        return False
    if _route_node_is_noncurrent(ledger, str(blocker.get("route_node_id") or "")):
        return False
    target_packet_ids = [
        str(blocker.get("repair_target_packet_id") or ""),
        str(blocker.get("subject_packet_id") or ""),
    ]
    if not any(target_packet_ids):
        target_packet_ids.append(str(blocker.get("packet_id") or ""))
    for packet_id in target_packet_ids:
        packet = ledger.get("packets", {}).get(packet_id)
        if isinstance(packet, Mapping) and _packet_is_noncurrent_for_routing(ledger, packet):
            return False
    return True


def _packet_current_target_violation(
    ledger: Mapping[str, Any],
    packet_id: str,
    *,
    require_responsibility: bool = True,
) -> str:
    if not packet_id:
        return "missing_packet_id"
    packet = ledger.get("packets", {}).get(packet_id)
    if not isinstance(packet, Mapping):
        return "missing_packet"
    status = str(packet.get("status") or "")
    if status in _NONCURRENT_PACKET_STATUSES:
        return f"noncurrent_packet_status:{status}"
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    active_route = ledger.get("active_route_version")
    if active_route is not None and envelope.get("route_version") != active_route:
        return f"stale_route_version:{envelope.get('route_version')}"
    route_node_id = str(envelope.get("route_node_id") or "")
    if _route_node_is_noncurrent(ledger, route_node_id):
        return f"noncurrent_route_node:{route_node_id}"
    if require_responsibility and not str(envelope.get("responsibility") or ""):
        return "missing_packet_responsibility"
    if status == "result_submitted" and packet.get("accepted_result_id"):
        return "result_submitted_with_accepted_result"
    return ""


def _packet_is_current_repair_target(ledger: Mapping[str, Any], packet_id: str) -> bool:
    return not _packet_current_target_violation(ledger, packet_id)


def _current_pm_repair_decision_packet_reusable(packet: Mapping[str, Any]) -> bool:
    status = str(packet.get("status") or "")
    if status in _NONCURRENT_PACKET_STATUSES or status in _CURRENT_PACKET_BLOCKING_STATUSES:
        return False
    if status in {"pm_repair_decision_blocked", "result_blocked"}:
        return False
    return status in {"open", "assigned", "acknowledged", "result_submitted"}


def _active_semantic_blockers(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        blocker
        for blocker in ledger.get("active_blockers", {}).values()
        if isinstance(blocker, Mapping) and _blocker_current_effective(ledger, blocker)
    ]


def _stopped_semantic_blockers(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        blocker
        for blocker in ledger.get("active_blockers", {}).values()
        if isinstance(blocker, Mapping)
        and blocker.get("status") == "stopped"
        and not _route_node_is_noncurrent(ledger, str(blocker.get("route_node_id") or ""))
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


def _mark_blocked_packet_noncurrent_after_repair(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    outcome_id: str,
) -> None:
    for packet_id in {
        str(blocker.get("packet_id") or ""),
        str(blocker.get("repair_target_packet_id") or ""),
        str(blocker.get("subject_packet_id") or ""),
    }:
        if not packet_id:
            continue
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, dict):
            continue
        if packet.get("status") not in _REPAIR_REPLACED_PACKET_STATUSES:
            continue
        if packet.get("status") == "result_submitted" and packet.get("accepted_result_id"):
            continue
        packet["status"] = "superseded_after_repair"
        packet["superseded_by_outcome_id"] = outcome_id
        packet["superseded_at"] = now_iso()
        packet["active_blocker_id"] = ""
        _event(
            ledger,
            "blocked_packet_superseded_after_repair",
            packet_id=packet_id,
            blocker_id=str(blocker.get("blocker_id") or ""),
            outcome_id=outcome_id,
        )


def _mark_repair_target_noncurrent_after_current_reissue(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    outcome_id: str,
) -> None:
    """Retire old repair-chain packet targets once a fresh current packet exists."""

    _mark_blocked_packet_noncurrent_after_repair(ledger, blocker, outcome_id)


def _resolve_current_repair_target_packet_id(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> str:
    candidate = str(outcome.get("subject_packet_id") or "")
    if candidate and _packet_is_current_repair_target(ledger, candidate):
        return candidate
    packet_id = str(packet.get("packet_id") or "")
    if packet_id and _packet_is_current_repair_target(ledger, packet_id):
        return packet_id
    return candidate or packet_id


def _blocker_family_ids(blocker: Mapping[str, Any]) -> set[str]:
    return {
        str(blocker.get(field) or "")
        for field in (
            "packet_id",
            "subject_packet_id",
            "repair_target_packet_id",
            "target_result_id",
            "result_id",
            "pm_repair_packet_id",
        )
        if blocker.get(field)
    }


def _same_family_blocker(existing: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    existing_id = str(existing.get("blocker_id") or "")
    current_id = str(current.get("blocker_id") or "")
    if not existing_id or existing_id == current_id:
        return False
    if _blocker_family_ids(existing).intersection(_blocker_family_ids(current)):
        return True
    return (
        str(existing.get("route_node_id") or "") == str(current.get("route_node_id") or "")
        and str(existing.get("gate_kind") or "") == str(current.get("gate_kind") or "")
        and str(existing.get("blocker_class") or "") == str(current.get("blocker_class") or "")
        and str(existing.get("required_recheck_role") or "") == str(current.get("required_recheck_role") or "")
        and str(existing.get("route_version") or "") == str(current.get("route_version") or "")
    )


def _retire_older_same_family_blockers(
    ledger: dict[str, Any],
    current: Mapping[str, Any],
    *,
    status: str = "retired_after_new_current_blocker",
) -> None:
    current_id = str(current.get("blocker_id") or "")
    for blocker in ledger.setdefault("active_blockers", {}).values():
        if not isinstance(blocker, dict):
            continue
        if blocker.get("status") not in (_CLEARABLE_SEMANTIC_BLOCKER_STATUSES | {"awaiting_pm_decision_gate"}):
            continue
        if not _same_family_blocker(blocker, current):
            continue
        blocker["status"] = status
        blocker["retired_by_blocker_id"] = current_id
        blocker["retired_at"] = now_iso()
        subject = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
        if isinstance(subject, dict) and subject.get("active_blocker_id") == blocker.get("blocker_id"):
            subject["active_blocker_id"] = ""
        _event(
            ledger,
            "same_family_blocker_retired",
            blocker_id=str(blocker.get("blocker_id") or ""),
            retired_by_blocker_id=current_id,
            status=status,
        )


def _mark_blocker_repair_packet_open(
    ledger: dict[str, Any],
    blocker: dict[str, Any],
    *,
    decision_id: str,
    fresh_packet_id: str,
) -> None:
    if not fresh_packet_id:
        raise BlackBoxRuntimeError("repair_packet_open requires a fresh repair packet id")
    packet = ledger.get("packets", {}).get(fresh_packet_id)
    if not isinstance(packet, Mapping):
        raise BlackBoxRuntimeError(f"fresh repair packet does not exist: {fresh_packet_id}")
    if packet.get("status") != "open":
        raise BlackBoxRuntimeError(f"fresh repair packet is not open: {fresh_packet_id}")
    target_violation = _packet_current_target_violation(ledger, fresh_packet_id)
    if target_violation:
        raise BlackBoxRuntimeError(f"fresh repair packet is not current: {target_violation}")
    blocker["status"] = "repair_packet_open"
    blocker["repair_packet_id"] = fresh_packet_id
    blocker["repair_packet_opened_by_decision_id"] = decision_id
    blocker["repair_packet_opened_at"] = now_iso()
    _retire_older_same_family_blockers(ledger, blocker)


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
    repair_target_packet_id = _resolve_current_repair_target_packet_id(ledger, packet, outcome)
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
    _retire_older_same_family_blockers(ledger, blocker)
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
    outcome = ledger.get("packet_outcomes", {}).get(outcome_id, {})
    outcome_route_node_id = str(outcome.get("route_node_id") or "") if isinstance(outcome, Mapping) else ""
    for blocker in ledger.setdefault("active_blockers", {}).values():
        if blocker.get("status") not in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
            continue
        same_subject = blocker.get("subject_packet_id") == subject_packet_id
        same_repair_chain = repair_blocker_id and blocker.get("blocker_id") == repair_blocker_id
        same_route_gate = (
            outcome_route_node_id
            and blocker.get("route_node_id") == outcome_route_node_id
            and blocker.get("gate_kind") == gate_kind
            and blocker.get("required_recheck_role") in {"", recheck_role}
        )
        if not (same_subject or same_repair_chain or same_route_gate):
            continue
        if blocker.get("gate_kind") != gate_kind and not same_repair_chain:
            continue
        if blocker.get("required_recheck_role") not in {"", recheck_role}:
            continue
        blocker["status"] = "cleared"
        blocker["cleared_by_outcome_id"] = outcome_id
        blocker["cleared_at"] = now_iso()
        _mark_blocked_packet_noncurrent_after_repair(ledger, blocker, outcome_id)
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
    if blocker.get("status") not in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
        raise BlackBoxRuntimeError(
            f"cannot issue PM repair decision packet for blocker {blocker_id} in status {blocker.get('status')}"
        )
    existing = _find_packet(
        ledger,
        packet_kind="pm_repair_decision",
        subject_id=blocker_id,
        reusable_statuses={"open", "assigned", "acknowledged", "result_submitted"},
    )
    if existing:
        if not _current_pm_repair_decision_packet_reusable(existing):
            existing = None
    if existing:
        blocker["pm_repair_packet_id"] = str(existing["packet_id"])
        return str(existing["packet_id"])
    stale_existing = _find_packet(ledger, packet_kind="pm_repair_decision", subject_id=blocker_id)
    if isinstance(stale_existing, dict) and stale_existing.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES:
        stale_existing["status"] = "superseded_after_repair"
        stale_existing["superseded_by_outcome_id"] = str(blocker.get("outcome_id") or "")
        stale_existing["superseded_reason"] = "blocked_pm_repair_decision_reissued"
        stale_existing["superseded_at"] = now_iso()
        stale_existing["active_blocker_id"] = ""
        _event(
            ledger,
            "blocked_pm_repair_decision_packet_superseded",
            packet_id=str(stale_existing.get("packet_id") or ""),
            blocker_id=blocker_id,
        )
    repair_target_packet = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
    repair_target_envelope = (
        repair_target_packet.get("envelope", {})
        if isinstance(repair_target_packet, Mapping) and isinstance(repair_target_packet.get("envelope"), Mapping)
        else {}
    )
    repeat_context = _blocker_repeat_context(ledger, blocker)
    authorized_result_reads = _blocker_authorized_result_reads(
        ledger,
        blocker,
        allowed_roles=["pm"],
        purpose="blocking_report_for_pm_repair_decision",
        required_before_submit=True,
    )
    packet_id = issue_task_packet(
        ledger,
        "pm",
        f"Choose repair strategy for semantic blocker {blocker_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_repair_decision_packet.v1",
                "blocker_id": blocker_id,
                "blocked_packet_id": blocker["packet_id"],
                "subject_packet_id": blocker.get("subject_packet_id", ""),
                "repair_target_packet_id": blocker["repair_target_packet_id"],
                "target_result_id": blocker.get("target_result_id", ""),
                "gate_kind": blocker["gate_kind"],
                "blocker_class": blocker.get("blocker_class", ""),
                "blocker_status": blocker.get("status", ""),
                "recommended_resolution": blocker.get("recommended_resolution", ""),
                "stale_evidence_ids": list(blocker.get("stale_evidence_ids") or []),
                "required_recheck_role": blocker["required_recheck_role"],
                "repair_target": {
                    "packet_id": str(blocker.get("repair_target_packet_id") or ""),
                    "objective": str(repair_target_envelope.get("objective") or ""),
                    "packet_kind": str(repair_target_envelope.get("packet_kind", "task")),
                    "responsibility": str(repair_target_envelope.get("responsibility") or ""),
                    "required_output_type": str(repair_target_envelope.get("required_output_type") or ""),
                    "output_contract": _copy_jsonable(repair_target_envelope.get("output_contract") or {}),
                    "acceptance_criteria": list(repair_target_envelope.get("acceptance_criteria") or []),
                    "route_node_id": str(repair_target_envelope.get("route_node_id") or blocker.get("route_node_id") or ""),
                    "route_scope": str(repair_target_envelope.get("route_scope") or blocker.get("route_scope") or ""),
                },
                "repeat_context": repeat_context,
                "allowed_decisions": sorted(_PM_REPAIR_DECISIONS),
                "repair_decision_contract": {
                    "pm_must_choose_allowed_decision": True,
                    "required_json_shape": {"decision": "<allowed_decision>", "reason": "<brief reason>"},
                    "top_level_decision_only": True,
                    "nested_repair_decision_wrappers_forbidden": True,
                    "nonterminal_repairs_require_runtime_fresh_packet": True,
                    "redesign_route_requires_route_plan": True,
                    "waive_with_authority_requires_authority_ref": True,
                    "pm_must_account_for_recommended_resolution": bool(blocker.get("recommended_resolution")),
                    "pm_does_not_mark_blocked_gate_passed_by_text": True,
                    "repair_summary_alone_is_not_completion": True,
                    "repeat_context_is_advisory_not_terminal": True,
                },
                "instruction": (
                    "Return exactly one structured JSON object with a top-level allowed decision, for example "
                    "{\"decision\":\"repair_current_scope\",\"reason\":\"current node needs replacement repair\"}. "
                    "Before deciding, open every required authorized_result_reads entry and use the opened report "
                    "body as the source of the concrete failure. "
                    "Use repair_parent_scope only when the explicit parent scope should be replaced. Use redesign_route "
                    "only with a strict route_plan object. Use waive_with_authority only with authority_ref. "
                    "Do not wrap the decision inside repair_decision, pm_repair_decision, prose, or any legacy shape. "
                    "PM chooses the repair route using the blocker recommendation and target contract. PM does not "
                    "impersonate the blocked reviewer, system validation check, FlowGuard pass, or worker deliverable."
                ),
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
        authorized_result_reads=authorized_result_reads,
    )
    blocker["pm_repair_packet_id"] = packet_id
    return packet_id


def _parse_pm_repair_decision_body(body: str) -> tuple[str, str, str, dict[str, Any] | None]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BlackBoxRuntimeError("PM repair decision requires a structured JSON object") from exc
    if not isinstance(payload, dict):
        raise BlackBoxRuntimeError("PM repair decision requires a structured JSON object")
    decision = _normalize_outcome_token(payload.get("decision"))
    reason = str(payload.get("reason") or "")
    if decision in _REMOVED_PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("PM repair decision uses a removed decision; request a current five-choice decision")
    if decision not in _PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("PM repair decision requires an explicit allowed decision")
    if not reason:
        raise BlackBoxRuntimeError("PM repair decision requires a top-level reason")
    authority_ref = str(payload.get("authority_ref") or payload.get("authority") or "")
    if decision == "waive_with_authority" and not authority_ref:
        raise BlackBoxRuntimeError("PM repair decision waive_with_authority requires authority_ref")
    route_plan: dict[str, Any] | None = None
    if decision == "redesign_route":
        raw_route_plan = payload.get("route_plan")
        if not isinstance(raw_route_plan, dict):
            raise BlackBoxRuntimeError("PM repair decision redesign_route requires a strict route_plan object")
        route_plan = _parse_strict_route_plan(json.dumps(raw_route_plan, sort_keys=True))
        _normalize_strict_route_plan_nodes(route_plan)
        route_plan = _copy_jsonable(route_plan)
    return decision, reason, authority_ref, route_plan


def _record_pm_repair_decision_from_packet_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    decision: str | None = None,
    reason: str | None = None,
    authority_ref: str = "",
    route_plan: dict[str, Any] | None = None,
) -> str:
    blocker_id = str(packet["envelope"].get("subject_id") or "")
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if decision is None:
        decision, reason, authority_ref, route_plan = _parse_pm_repair_decision_body(str(result.get("body", "")))
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
        "authority_ref": authority_ref,
        "route_plan": route_plan,
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
    if decision == "redesign_route":
        _attach_staged_effect(
            row,
            effect_kind="commit_route_redesign",
            source_packet_id=row["source_packet_id"],
            source_result_id=row["source_result_id"],
            target_node_id=node_id,
            blocker_id=blocker_id,
            gate_id=gate_id,
            route_scope=str(packet.get("envelope", {}).get("route_scope") or ""),
        )
        if isinstance(result, dict):
            _attach_staged_effect(
                result,
                effect_kind="commit_route_redesign",
                source_packet_id=row["source_packet_id"],
                source_result_id=row["source_result_id"],
                target_node_id=node_id,
                blocker_id=blocker_id,
                gate_id=gate_id,
                route_scope=str(packet.get("envelope", {}).get("route_scope") or ""),
            )
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
    _mark_staged_effect_committed(gate, system_closure_id=system_closure_id)
    source_result = ledger.get("results", {}).get(str(gate.get("source_result_id") or ""))
    if isinstance(source_result, dict):
        _mark_staged_effect_committed(source_result, system_closure_id=system_closure_id)
    staged_effect = gate.get("staged_effect") if isinstance(gate.get("staged_effect"), Mapping) else {}
    _event(
        ledger,
        "staged_effect_committed",
        effect_kind=str(staged_effect.get("effect_kind") or ""),
        source_packet_id=str(gate.get("source_packet_id") or ""),
        source_result_id=str(gate.get("source_result_id") or ""),
        system_closure_id=system_closure_id,
    )
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


def _record_repair_transaction(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
    *,
    source_id: str,
    fresh_packet_id: str,
) -> None:
    decision_label = str(ledger.get("pm_repair_decisions", {}).get(decision_id, {}).get("decision") or "")
    ledger.setdefault("repair_transactions", {})[decision_id] = {
        "transaction_id": decision_id,
        "source_id": source_id,
        "blocker_id": blocker["blocker_id"],
        "decision": decision_label,
        "fresh_packet_id": fresh_packet_id,
        "stale_evidence_ids": list(blocker.get("stale_evidence_ids") or []),
        "created_at": now_iso(),
    }


def _issue_current_scope_repair_packet(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
) -> str:
    target_packet_id = str(blocker.get("repair_target_packet_id") or blocker.get("subject_packet_id") or "")
    target_packet = _require(ledger["packets"], target_packet_id, "repair target packet")
    target_envelope = target_packet["envelope"]
    repair_role = str(target_envelope.get("responsibility") or "")
    if not repair_role:
        raise BlackBoxRuntimeError("repair_current_scope requires current packet responsibility")
    packet_kind = str(target_envelope.get("packet_kind") or "task")
    repeat_context = _blocker_repeat_context(ledger, blocker)
    packet_id = issue_task_packet(
        ledger,
        repair_role,
        f"Repair current packet scope for blocker {blocker['blocker_id']}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.current_scope_repair_packet.v1",
                "blocker_id": blocker["blocker_id"],
                "pm_repair_decision_id": decision_id,
                "source_packet_id": target_packet_id,
                "source_body_hash": target_envelope.get("body_hash", ""),
                "source_objective": target_envelope.get("objective", ""),
                "source_packet_kind": packet_kind,
                "source_required_output_type": target_envelope.get("required_output_type", ""),
                "source_output_contract": _copy_jsonable(target_envelope.get("output_contract") or {}),
                "source_acceptance_criteria": list(target_envelope.get("acceptance_criteria") or []),
                "target_result_id": blocker.get("target_result_id", ""),
                "stale_evidence_ids": list(blocker.get("stale_evidence_ids") or []),
                "blocker_class": blocker.get("blocker_class", ""),
                "required_recheck_role": blocker.get("required_recheck_role", ""),
                "recommended_resolution": blocker.get("recommended_resolution", ""),
                "repeat_context": repeat_context,
                "repair_completion_contract": {
                    "must_submit_current_packet_result": True,
                    "source_artifact_is_context_not_passing_evidence": True,
                    "repair_summary_alone_is_not_completion": True,
                    "must_satisfy_source_output_contract": True,
                    "may_return_new_blocker_if_repair_is_not_possible": True,
                    "required_recheck_role": blocker.get("required_recheck_role", ""),
                },
                "instruction": (
                    "Produce fresh repaired evidence for this current replacement packet. "
                    "The source artifact is context only, not passing evidence. Submit the corrected deliverable "
                    "or a new structured blocker."
                ),
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
        node_context_package_id=str(target_envelope.get("node_context_package_id") or ""),
        authorized_result_reads=_blocker_authorized_result_reads(
            ledger,
            blocker,
            allowed_roles=[repair_role],
            purpose="blocking_report_for_repair_work",
            required_before_submit=True,
        ),
    )
    ledger["packets"][packet_id]["repair_blocker_id"] = str(blocker["blocker_id"])
    _record_repair_transaction(
        ledger,
        blocker,
        decision_id,
        source_id=target_packet_id,
        fresh_packet_id=packet_id,
    )
    _mark_repair_target_noncurrent_after_current_reissue(ledger, blocker, decision_id)
    _event(ledger, "repair_scope_replaced", blocker_id=blocker["blocker_id"], source_id=target_packet_id, fresh_packet_id=packet_id)
    return packet_id


def _replace_scope_and_open_repair_packet(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
    *,
    source_node_id: str,
    reason: str,
    supersede_descendants: bool = False,
) -> tuple[str, str]:
    before_packets = set(ledger.get("packets", {}))
    replacement_id = _replace_route_node_for_repair(
        ledger,
        source_node_id,
        disposition_id=decision_id,
        reason=reason,
        supersede_descendants=supersede_descendants,
    )
    fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=replacement_id, before_ids=before_packets)
    if not fresh_packet_id:
        raise BlackBoxRuntimeError("repair scope replacement did not create a fresh executable packet")
    ledger["packets"][fresh_packet_id]["repair_blocker_id"] = str(blocker["blocker_id"])
    fresh_envelope = ledger["packets"][fresh_packet_id].get("envelope", {})
    fresh_role = str(fresh_envelope.get("responsibility") or "") if isinstance(fresh_envelope, Mapping) else ""
    if fresh_role:
        _attach_authorized_result_reads_to_packet(
            ledger,
            fresh_packet_id,
            _blocker_authorized_result_reads(
                ledger,
                blocker,
                allowed_roles=[fresh_role],
                purpose="blocking_report_for_repair_work",
                required_before_submit=True,
            ),
        )
    _record_repair_transaction(
        ledger,
        blocker,
        decision_id,
        source_id=source_node_id,
        fresh_packet_id=fresh_packet_id,
    )
    _mark_repair_target_noncurrent_after_current_reissue(ledger, blocker, decision_id)
    _event(
        ledger,
        "repair_scope_replaced",
        blocker_id=str(blocker["blocker_id"]),
        source_id=source_node_id,
        replacement_node_id=replacement_id,
        fresh_packet_id=fresh_packet_id,
    )
    return replacement_id, fresh_packet_id


def _redesign_route_from_pm_decision(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
    *,
    reason: str,
) -> tuple[list[str], str]:
    row = ledger.get("pm_repair_decisions", {}).get(decision_id, {})
    route_plan = row.get("route_plan") if isinstance(row, Mapping) else None
    if not isinstance(route_plan, Mapping):
        raise BlackBoxRuntimeError("redesign_route requires a strict route_plan")
    route_plan = _parse_strict_route_plan(json.dumps(route_plan, sort_keys=True))
    node_specs = _normalize_strict_route_plan_nodes(route_plan)
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    old_node_ids = [
        str(node_id)
        for node_id, node in ledger.get("route_nodes", {}).items()
        if isinstance(node, Mapping) and int(node.get("route_version") or 0) == old_version
    ]
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, dict):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if envelope.get("route_version") != old_version:
            continue
        if packet.get("status") == "accepted":
            continue
        packet["status"] = "quarantined_after_route_mutation"
        packet["old_route_disposition"] = "quarantined"
    for node_id in old_node_ids:
        node = ledger.get("route_nodes", {}).get(node_id)
        if isinstance(node, dict):
            node["status"] = "superseded"
            node["superseded_by"] = f"route-v{new_version}"
            node.setdefault("stale_evidence", []).append(decision_id)
    if str(old_version) in ledger.get("routes", {}):
        ledger["routes"][str(old_version)]["status"] = "superseded"
        ledger["routes"][str(old_version)]["superseded_by_route_version"] = new_version

    materialized_ids: list[str] = []
    route_nodes = ledger.setdefault("route_nodes", {})
    for spec in node_specs:
        node_id = str(spec["node_id"])
        if node_id in route_nodes:
            raise BlackBoxRuntimeError(f"redesign_route node_id already exists: {node_id}")
        criteria = spec.get("acceptance_criteria")
        route_nodes[node_id] = {
            "node_id": node_id,
            "route_version": new_version,
            "title": str(spec["title"]),
            "node_kind": str(spec.get("node_kind") or "leaf"),
            "parent_node_id": str(spec.get("parent_node_id") or ""),
            "child_node_ids": list(spec.get("child_node_ids") or []),
            "responsibility": _normalize_node_responsibility(str(spec.get("responsibility") or "")),
            "modeled_target": _normalize_modeled_target(str(spec.get("modeled_target") or ""), str(spec["title"])),
            "acceptance_criteria": [str(item) for item in criteria],
            "required_outputs": list(spec.get("required_outputs") or []),
            "deliverable_checks": list(spec.get("deliverable_checks") or []),
            "validation_checks": list(spec.get("validation_checks") or []),
            "status": "pending",
            "repair_generation": 0,
            "packet_ids": [],
            "accepted_result_id": "",
            "accepted_repair_generation": None,
            "flowguard_order_ids": [],
            "prework_flowguard_order_ids": [],
            "prework_flowguard_packet_id": "",
            "prework_flowguard_order_id": "",
            "prework_flowguard_result_id": "",
            "prework_flowguard_repair_generation": None,
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "node_acceptance_plan_id": "",
            "node_context_package_id": "",
            "node_context_package_repair_generation": None,
            "parent_backward_replay_id": "",
            "parent_backward_waiver": "",
            "high_standard_requirement_ids": [str(item) for item in spec.get("high_standard_requirement_ids") or []],
            "skill_standard_obligation_ids": [str(item) for item in spec.get("skill_standard_obligation_ids") or []],
            "superseded_by": "",
            "stale_evidence": [],
            "created_from_result_id": str(row.get("result_id") or ""),
            "route_plan_schema_version": route_plan.get("schema_version", ""),
            "created_at": now_iso(),
        }
        materialized_ids.append(node_id)

    ledger.setdefault("routes", {})[str(new_version)] = {
        "route_version": new_version,
        "route_id": f"route-v{new_version}",
        "title": "Redesigned repair route",
        "status": "active",
        "nodes": [str(spec["title"]) for spec in node_specs],
        "node_order": materialized_ids,
        "created_at": now_iso(),
        "redesigned_from_route_version": old_version,
        "redesign_decision_id": decision_id,
        "redesign_reason": reason,
    }
    ledger["active_route_version"] = new_version
    first_node_id = materialized_ids[0] if materialized_ids else ""
    ledger["execution_frontier"] = {
        "active_route_version": new_version,
        "active_node_id": first_node_id,
        "completed_nodes": [],
        "status": "node_execution" if first_node_id else "blocked",
        "pending_route_mutation": {
            "mutation_id": _next_id(ledger, "mutation"),
            "old_route_version": old_version,
            "new_route_version": new_version,
            "reason": reason,
            "disposition_id": decision_id,
            "superseded_node_ids": old_node_ids,
            "replacement_node_id": first_node_id,
            "affected_packets": [],
            "requires_replay_or_rebinding": True,
            "created_at": now_iso(),
        },
        "blocked_reason": "" if first_node_id else "route_redesign_empty",
        "updated_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(ledger["execution_frontier"]["pending_route_mutation"])
    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    _event(ledger, "execution_frontier_updated", status=ledger["execution_frontier"]["status"], active_node_id=first_node_id)
    if first_node_id:
        before_packets = set(ledger.get("packets", {}))
        if high_standard_flow_required(ledger):
            ensure_node_acceptance_plan_packet(ledger, first_node_id)
        else:
            ensure_node_prework_flowguard_packet(ledger, first_node_id)
        fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=first_node_id, before_ids=before_packets)
        if not fresh_packet_id:
            raise BlackBoxRuntimeError("redesign_route did not create a fresh executable packet")
        ledger["packets"][fresh_packet_id]["repair_blocker_id"] = str(blocker["blocker_id"])
        _record_repair_transaction(
            ledger,
            blocker,
            decision_id,
            source_id=f"route-v{old_version}",
            fresh_packet_id=fresh_packet_id,
        )
        _mark_repair_target_noncurrent_after_current_reissue(ledger, blocker, decision_id)
        return materialized_ids, fresh_packet_id
    return materialized_ids, ""


def _apply_pm_repair_decision(ledger: dict[str, Any], blocker_id: str, decision_id: str) -> None:
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    decision = str(ledger["pm_repair_decisions"][decision_id]["decision"])
    reason = str(ledger["pm_repair_decisions"][decision_id].get("reason") or f"pm_repair_{decision}")
    route_node_id = str(blocker.get("route_node_id") or "")
    if decision in _REMOVED_PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("removed PM repair decision cannot be applied")
    if decision == "repair_current_scope":
        if route_node_id and route_node_id in ledger.get("route_nodes", {}):
            _replacement_id, fresh_packet_id = _replace_scope_and_open_repair_packet(
                ledger,
                blocker,
                decision_id,
                source_node_id=route_node_id,
                reason=reason,
            )
        else:
            fresh_packet_id = _issue_current_scope_repair_packet(ledger, blocker, decision_id)
        _mark_blocker_repair_packet_open(
            ledger,
            blocker,
            decision_id=decision_id,
            fresh_packet_id=fresh_packet_id,
        )
        return
    if decision == "repair_parent_scope":
        if not route_node_id or route_node_id not in ledger.get("route_nodes", {}):
            raise BlackBoxRuntimeError("repair_parent_scope requires a current route node")
        parent_node_id = _nearest_parent_route_node_id(ledger, route_node_id)
        if not parent_node_id or parent_node_id not in ledger.get("route_nodes", {}):
            raise BlackBoxRuntimeError("repair_parent_scope requires an explicit parent route node")
        _replacement_id, fresh_packet_id = _replace_scope_and_open_repair_packet(
            ledger,
            blocker,
            decision_id,
            source_node_id=parent_node_id,
            reason=reason,
            supersede_descendants=True,
        )
        _mark_blocker_repair_packet_open(
            ledger,
            blocker,
            decision_id=decision_id,
            fresh_packet_id=fresh_packet_id,
        )
        return
    if decision == "redesign_route":
        _node_ids, fresh_packet_id = _redesign_route_from_pm_decision(
            ledger,
            blocker,
            decision_id,
            reason=reason,
        )
        _mark_blocker_repair_packet_open(
            ledger,
            blocker,
            decision_id=decision_id,
            fresh_packet_id=fresh_packet_id,
        )
        return
    if decision == "waive_with_authority":
        authority_ref = str(ledger["pm_repair_decisions"][decision_id].get("authority_ref") or "")
        if not authority_ref:
            raise BlackBoxRuntimeError("waive_with_authority requires authority_ref")
        blocker["status"] = "waived"
        blocker["waived_at"] = now_iso()
        blocker["authority_ref"] = authority_ref
        blocker["cleared_by_outcome_id"] = str(blocker.get("outcome_id") or "")
        return
    if decision == "stop_for_user":
        blocker["status"] = "stopped"
        blocker["stopped_at"] = now_iso()
        target_packet = ledger.get("packets", {}).get(str(blocker.get("repair_target_packet_id") or ""))
        if isinstance(target_packet, dict):
            if target_packet.get("status") != "pm_stopped" and not target_packet.get("pm_stop_previous_status"):
                target_packet["pm_stop_previous_status"] = str(target_packet.get("status") or "")
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
            ensure_node_prework_flowguard_packet(ledger, next_node)
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


def _descendant_route_node_ids(ledger: Mapping[str, Any], node_id: str) -> list[str]:
    route_nodes = ledger.get("route_nodes", {})
    descendants: list[str] = []
    queue = [str(item) for item in (route_nodes.get(node_id, {}) or {}).get("child_node_ids", [])]
    while queue:
        candidate = queue.pop(0)
        if candidate in descendants:
            continue
        descendants.append(candidate)
        node = route_nodes.get(candidate, {})
        if isinstance(node, Mapping):
            queue.extend(str(item) for item in node.get("child_node_ids", []) if item)
    return descendants


def _nearest_parent_route_node_id(ledger: Mapping[str, Any], node_id: str) -> str:
    node = ledger.get("route_nodes", {}).get(node_id, {})
    if isinstance(node, Mapping):
        direct_parent = str(node.get("parent_node_id") or "")
        if direct_parent:
            return direct_parent
    for candidate_id, candidate in ledger.get("route_nodes", {}).items():
        if not isinstance(candidate, Mapping):
            continue
        if node_id in [str(item) for item in candidate.get("child_node_ids", [])]:
            return str(candidate_id)
    return ""


def _replace_route_node_for_repair(
    ledger: dict[str, Any],
    node_id: str,
    *,
    disposition_id: str,
    reason: str,
    supersede_descendants: bool = False,
) -> str:
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    replacement_id = f"{node_id}-repair-v{new_version}"
    superseded_node_ids = [node_id]
    if supersede_descendants:
        superseded_node_ids.extend(_descendant_route_node_ids(ledger, node_id))
    affected_packets: list[str] = []
    for packet in ledger.get("packets", {}).values():
        if packet.get("envelope", {}).get("route_node_id") not in superseded_node_ids:
            continue
        if packet.get("accepted_result_id"):
            packet["status"] = "accepted"
            continue
        if packet.get("status") != "accepted":
            packet["status"] = "quarantined_after_route_mutation"
            packet["old_route_disposition"] = "quarantined"
            affected_packets.append(packet["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    for superseded_id in superseded_node_ids:
        superseded_node = _require(ledger.setdefault("route_nodes", {}), superseded_id, "route node")
        superseded_node["status"] = "superseded"
        superseded_node["superseded_by"] = replacement_id
        superseded_node.setdefault("stale_evidence", []).append(disposition_id)
    replacement = dict(node)
    child_node_ids = [] if supersede_descendants else list(node.get("child_node_ids") or [])
    replacement.update(
        {
            "node_id": replacement_id,
            "route_version": new_version,
            "title": f"Repair {node['title']}",
            "status": "pending",
            "child_node_ids": child_node_ids,
            "packet_ids": [],
            "accepted_result_id": "",
            "flowguard_order_ids": [],
            "prework_flowguard_order_ids": [],
            "prework_flowguard_packet_id": "",
            "prework_flowguard_order_id": "",
            "prework_flowguard_result_id": "",
            "prework_flowguard_repair_generation": None,
            "review_ids": [],
            "validation_evidence_ids": [],
            "closure_id": "",
            "pm_disposition_id": "",
            "node_acceptance_plan_id": "",
            "node_context_package_id": "",
            "node_context_package_repair_generation": None,
            "parent_backward_replay_id": "",
            "parent_backward_waiver": "",
            "superseded_by": "",
            "stale_evidence": [],
            "created_at": now_iso(),
        }
    )
    ledger["route_nodes"][replacement_id] = replacement
    if str(old_version) in ledger.get("routes", {}):
        ledger["routes"][str(old_version)]["status"] = "superseded"
        ledger["routes"][str(old_version)]["superseded_by_route_version"] = new_version
    route = dict(ledger.get("routes", {}).get(str(old_version), {}))
    node_order = [
        replacement_id if item == node_id else item
        for item in route.get("node_order", [])
        if item == node_id or item not in superseded_node_ids
    ]
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
        "superseded_node_ids": superseded_node_ids,
        "replacement_node_id": replacement_id,
        "affected_packets": affected_packets,
        "requires_replay_or_rebinding": True,
        "created_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(mutation)
    ledger["execution_frontier"] = {
        "active_route_version": new_version,
        "active_node_id": replacement_id,
        "completed_nodes": [
            item
            for item in (ledger.get("execution_frontier") or {}).get("completed_nodes", [])
            if item not in superseded_node_ids
        ],
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
        ensure_node_prework_flowguard_packet(ledger, replacement_id)
    return replacement_id


def _role_continuity_table(ledger: dict[str, Any]) -> dict[str, Any]:
    continuity = ledger.setdefault(
        "role_continuity",
        {
            "schema_version": "black_box_flowpilot.role_continuity.v1",
            "roles": {},
        },
    )
    if not isinstance(continuity, dict):
        continuity = {"schema_version": "black_box_flowpilot.role_continuity.v1", "roles": {}}
        ledger["role_continuity"] = continuity
    roles = continuity.setdefault("roles", {})
    if not isinstance(roles, dict):
        roles = {}
        continuity["roles"] = roles
    return roles


def _role_slot_reusable(ledger: Mapping[str, Any], role: str, slot: Mapping[str, Any] | None) -> bool:
    if not isinstance(slot, Mapping):
        return False
    agent_id = str(slot.get("agent_id") or "").strip()
    lease_id = str(slot.get("latest_lease_id") or "").strip()
    if not agent_id:
        return False
    if str(slot.get("reuse_state") or "reusable") != "reusable":
        return False
    lease = ledger.get("leases", {}).get(lease_id)
    if isinstance(lease, Mapping):
        if lease.get("responsibility") != role:
            return False
        if lease.get("status") in {"expired", "superseded", "cancelled"}:
            return False
        liveness = str(lease.get("liveness_status") or lease.get("last_liveness_status") or "")
        if liveness in _ROLE_NONREUSABLE_LIVENESS_STATUSES:
            return False
    liveness = str(slot.get("last_liveness_status") or "")
    return liveness not in _ROLE_NONREUSABLE_LIVENESS_STATUSES


def _role_assignment_reuse_forbidden_reason(
    ledger: Mapping[str, Any],
    responsibility: str,
    *,
    packet_id: str,
    prior_agent_id: str,
) -> str:
    if responsibility != "reviewer" or not packet_id or not prior_agent_id:
        return ""
    packet = ledger.get("packets", {}).get(packet_id)
    if not isinstance(packet, Mapping):
        return ""
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if envelope.get("packet_kind") != "review":
        return ""
    target_result = ledger.get("results", {}).get(str(envelope.get("target_result_id") or ""))
    if isinstance(target_result, Mapping) and str(target_result.get("producer_agent_id") or "") == prior_agent_id:
        return "reviewer_self_review_forbidden"
    return ""


def _role_assignment_table(ledger: dict[str, Any]) -> dict[str, Any]:
    assignments = ledger.setdefault("role_assignments", {})
    if not isinstance(assignments, dict):
        assignments = {}
        ledger["role_assignments"] = assignments
    return assignments


def _lease_reusable_for_role_slot(lease: Mapping[str, Any]) -> bool:
    agent_id = str(lease.get("agent_id") or "").strip()
    if not agent_id:
        return False
    if str(lease.get("status") or "") in {"expired", "superseded", "cancelled"}:
        return False
    liveness = str(lease.get("liveness_status") or lease.get("last_liveness_status") or lease.get("last_progress_status") or "")
    return liveness not in _ROLE_NONREUSABLE_LIVENESS_STATUSES


def _same_responsibility_lease_history(ledger: Mapping[str, Any], role: str) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for lease in ledger.get("leases", {}).values():
        if not isinstance(lease, Mapping):
            continue
        if str(lease.get("responsibility") or "") == role:
            rows.append(lease)
    return rows


def _hydrate_role_slot_from_current_run_history(
    ledger: dict[str, Any],
    role: str,
) -> tuple[dict[str, Any] | None, str]:
    history = _same_responsibility_lease_history(ledger, role)
    if not history:
        return None, "no_same_responsibility_history"
    for lease in reversed(history):
        if not _lease_reusable_for_role_slot(lease):
            continue
        roles = _role_continuity_table(ledger)
        slot = {
            "schema_version": "black_box_flowpilot.role_slot.v1",
            "role": role,
            "agent_id": str(lease.get("agent_id") or ""),
            "latest_lease_id": str(lease.get("lease_id") or ""),
            "latest_packet_id": str(lease.get("packet_id") or ""),
            "reuse_state": "reusable",
            "last_liveness_status": str(
                lease.get("liveness_status") or lease.get("last_liveness_status") or lease.get("last_progress_status") or ""
            ),
            "last_continuity_action": "hydrated",
            "prior_agent_id": "",
            "replacement_reason": "",
            "rejected_replacement_candidate_ids": [],
            "hydrated_from_current_run_lease": str(lease.get("lease_id") or ""),
            "updated_at": now_iso(),
        }
        roles[role] = slot
        _event(
            ledger,
            "role_continuity_hydrated",
            role=role,
            agent_id=slot["agent_id"],
            source_lease_id=slot["latest_lease_id"],
            source_packet_id=slot["latest_packet_id"],
        )
        return slot, "hydrated_from_current_run_history"
    return None, "same_responsibility_history_not_reusable"


def resolve_role_assignment(
    ledger: dict[str, Any],
    responsibility: str,
    *,
    packet_id: str = "",
    host_kind: str = "live",
) -> dict[str, Any]:
    """Resolve role reuse/create/block before any new role surface is opened."""

    _assert_not_terminal_lifecycle(ledger)
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    if packet_id:
        packet = _require(ledger["packets"], packet_id, "packet")
        if packet.get("accepted_result_id"):
            raise BlackBoxRuntimeError("cannot assign accepted packet")
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if str(envelope.get("responsibility") or "") != responsibility:
            raise BlackBoxRuntimeError("assignment responsibility does not match packet")
    assignments = _role_assignment_table(ledger)
    background_blocker = background_collaboration_blocker(ledger)
    if background_blocker:
        assignment_id = _next_id(ledger, "role_assignment")
        assignment = {
            "schema_version": "black_box_flowpilot.role_assignment.v1",
            "assignment_id": assignment_id,
            "packet_id": packet_id,
            "responsibility": responsibility,
            "host_kind": host_kind,
            "disposition": "blocked",
            "status": "blocked",
            "effective_agent_id": "",
            "prior_agent_id": "",
            "replacement_reason": "",
            "role_surface_required": False,
            "role_memory_seed_required": False,
            "hydration_reason": "",
            "blocker_reason": f"{BACKGROUND_COLLABORATION_REQUIRED_MESSAGE}: {background_blocker}",
            "background_collaboration_required": True,
            "created_at": now_iso(),
            "sealed_bodies_visible": False,
        }
        assignments[assignment_id] = assignment
        _event(
            ledger,
            "role_assignment_blocked",
            assignment_id=assignment_id,
            role=responsibility,
            packet_id=packet_id,
            disposition="blocked",
            effective_agent_id="",
            blocker_reason=assignment["blocker_reason"],
        )
        return _copy_jsonable(assignment)
    roles = _role_continuity_table(ledger)
    slot = roles.get(responsibility) if isinstance(roles.get(responsibility), Mapping) else None
    hydration_reason = ""
    if slot is None:
        slot, hydration_reason = _hydrate_role_slot_from_current_run_history(ledger, responsibility)
    for existing in reversed(list(assignments.values())):
        if not isinstance(existing, Mapping):
            continue
        if str(existing.get("status") or "") != "resolved":
            continue
        if str(existing.get("responsibility") or "") != responsibility:
            continue
        if str(existing.get("packet_id") or "") != packet_id:
            continue
        if str(existing.get("host_kind") or "") != host_kind:
            continue
        return _copy_jsonable(existing)
    prior_agent_id = str(slot.get("agent_id") or "") if isinstance(slot, Mapping) else ""
    reusable = _role_slot_reusable(ledger, responsibility, slot)
    reuse_forbidden_reason = _role_assignment_reuse_forbidden_reason(
        ledger,
        responsibility,
        packet_id=packet_id,
        prior_agent_id=prior_agent_id,
    )
    if reuse_forbidden_reason:
        reusable = False
    assignment_id = _next_id(ledger, "role_assignment")
    disposition = "create_new_role"
    status = "resolved"
    effective_agent_id = ""
    replacement_reason = ""
    role_surface_required = True
    blocker_reason = ""
    memory_seed_required = False
    if reusable and prior_agent_id:
        disposition = "reuse_existing_role"
        effective_agent_id = prior_agent_id
        role_surface_required = False
    elif reuse_forbidden_reason and prior_agent_id:
        disposition = "create_new_role"
        replacement_reason = reuse_forbidden_reason
        memory_seed_required = True
    elif slot is None and hydration_reason == "same_responsibility_history_not_reusable":
        disposition = "blocked"
        status = "blocked"
        blocker_reason = "role_continuity_slot_missing_and_history_not_reusable"
        role_surface_required = False
    elif prior_agent_id:
        disposition = "create_new_role"
        replacement_reason = "prior_role_slot_not_reusable"
        memory_seed_required = True
    assignment = {
        "schema_version": "black_box_flowpilot.role_assignment.v1",
        "assignment_id": assignment_id,
        "packet_id": packet_id,
        "responsibility": responsibility,
        "host_kind": host_kind,
        "disposition": disposition,
        "status": status,
        "effective_agent_id": effective_agent_id,
        "prior_agent_id": prior_agent_id,
        "replacement_reason": replacement_reason,
        "role_surface_required": role_surface_required,
        "role_memory_seed_required": memory_seed_required,
        "hydration_reason": hydration_reason,
        "blocker_reason": blocker_reason,
        "created_at": now_iso(),
        "sealed_bodies_visible": False,
    }
    assignments[assignment_id] = assignment
    event = "role_assignment_blocked" if disposition == "blocked" else "role_assignment_resolved"
    _event(
        ledger,
        event,
        assignment_id=assignment_id,
        role=responsibility,
        packet_id=packet_id,
        disposition=disposition,
        effective_agent_id=effective_agent_id,
        blocker_reason=blocker_reason,
    )
    return _copy_jsonable(assignment)


def _public_packet_memory_row(ledger: Mapping[str, Any], packet_id: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    result_rows: list[dict[str, Any]] = []
    for result_id in list(packet.get("result_ids") or [])[-3:]:
        result = ledger.get("results", {}).get(str(result_id))
        if not isinstance(result, Mapping):
            continue
        result_rows.append(
            {
                "result_id": str(result.get("result_id") or result_id),
                "status": str(result.get("status") or ""),
                "accepted": bool(result.get("accepted") is True),
                "semantic_decision": str(result.get("semantic_decision") or ""),
                "packet_outcome_id": str(result.get("packet_outcome_id") or ""),
                "review_id": str(result.get("review_id") or ""),
                "validation_evidence_id": str(result.get("validation_evidence_id") or ""),
            }
        )
    return {
        "packet_id": str(packet_id),
        "packet_kind": str(envelope.get("packet_kind", "task")),
        "status": str(packet.get("status") or ""),
        "responsibility": str(envelope.get("responsibility") or ""),
        "objective": str(envelope.get("objective") or ""),
        "route_version": envelope.get("route_version"),
        "route_node_id": str(envelope.get("route_node_id") or ""),
        "route_scope": str(envelope.get("route_scope") or ""),
        "subject_id": str(envelope.get("subject_id") or ""),
        "target_result_id": str(envelope.get("target_result_id") or ""),
        "accepted_result_id": str(packet.get("accepted_result_id") or ""),
        "active_blocker_id": str(packet.get("active_blocker_id") or packet.get("repair_blocker_id") or ""),
        "result_summaries": result_rows,
    }


def _blocker_repeat_context(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, Any]:
    target = str(blocker.get("repair_target_packet_id") or blocker.get("subject_packet_id") or blocker.get("packet_id") or "")
    blocker_class = str(blocker.get("blocker_class") or "")
    same_family: list[dict[str, str]] = []
    for candidate in ledger.get("active_blockers", {}).values():
        if not isinstance(candidate, Mapping):
            continue
        candidate_target = str(
            candidate.get("repair_target_packet_id") or candidate.get("subject_packet_id") or candidate.get("packet_id") or ""
        )
        if candidate_target != target or str(candidate.get("blocker_class") or "") != blocker_class:
            continue
        same_family.append(
            {
                "blocker_id": str(candidate.get("blocker_id") or ""),
                "status": str(candidate.get("status") or ""),
                "pm_repair_decision_id": str(candidate.get("pm_repair_decision_id") or ""),
                "pm_repair_packet_id": str(candidate.get("pm_repair_packet_id") or ""),
            }
        )
    return {
        "family_key": f"{target}:{blocker_class}",
        "repeat_count": len(same_family),
        "previous_blocker_ids": [row["blocker_id"] for row in same_family if row["blocker_id"] != blocker.get("blocker_id")],
        "same_family_blockers": same_family,
        "advisory_only": True,
    }


def _public_blocker_memory_row(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "blocker_id": str(blocker.get("blocker_id") or ""),
        "status": str(blocker.get("status") or ""),
        "packet_id": str(blocker.get("packet_id") or ""),
        "subject_packet_id": str(blocker.get("subject_packet_id") or ""),
        "repair_target_packet_id": str(blocker.get("repair_target_packet_id") or ""),
        "target_result_id": str(blocker.get("target_result_id") or ""),
        "required_recheck_role": str(blocker.get("required_recheck_role") or ""),
        "gate_kind": str(blocker.get("gate_kind") or ""),
        "blocker_class": str(blocker.get("blocker_class") or ""),
        "recommended_resolution": str(blocker.get("recommended_resolution") or ""),
        "stale_evidence_ids": [str(item) for item in blocker.get("stale_evidence_ids") or []],
        "pm_repair_packet_id": str(blocker.get("pm_repair_packet_id") or ""),
        "pm_repair_decision_id": str(blocker.get("pm_repair_decision_id") or ""),
        "repeat_context": _blocker_repeat_context(ledger, blocker),
    }


def _build_role_memory_seed(
    ledger: Mapping[str, Any],
    role: str,
    *,
    prior_agent_id: str = "",
    replacement_reason: str = "",
) -> dict[str, Any]:
    packet_rows: list[dict[str, Any]] = []
    for packet_id, packet in reversed(list(ledger.get("packets", {}).items())):
        if not isinstance(packet, Mapping):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        packet_role = str(envelope.get("responsibility") or "")
        packet_kind = str(envelope.get("packet_kind", "task"))
        visible_to_role = packet_role == role or (
            role == "pm" and packet_kind in {"pm_repair_decision", "pm_disposition"}
        )
        if not visible_to_role:
            continue
        packet_rows.append(_public_packet_memory_row(ledger, str(packet_id), packet))
        if len(packet_rows) >= 8:
            break

    blocker_rows: list[dict[str, Any]] = []
    for blocker in reversed(list(ledger.get("active_blockers", {}).values())):
        if not isinstance(blocker, Mapping):
            continue
        if role != "pm" and role not in {
            str(blocker.get("required_recheck_role") or ""),
            str(blocker.get("owner_role") or ""),
        }:
            continue
        blocker_rows.append(_public_blocker_memory_row(ledger, blocker))
        if len(blocker_rows) >= 8:
            break

    pm_decisions: list[dict[str, Any]] = []
    if role == "pm":
        for decision in reversed(list(ledger.get("pm_repair_decisions", {}).values())):
            if not isinstance(decision, Mapping):
                continue
            pm_decisions.append(
                {
                    "decision_id": str(decision.get("decision_id") or ""),
                    "blocker_id": str(decision.get("blocker_id") or ""),
                    "packet_id": str(decision.get("packet_id") or ""),
                    "result_id": str(decision.get("result_id") or ""),
                    "decision": str(decision.get("decision") or ""),
                    "reason": str(decision.get("reason") or ""),
                    "created_at": str(decision.get("created_at") or ""),
                }
            )
            if len(pm_decisions) >= 8:
                break

    return {
        "schema_version": "black_box_flowpilot.role_memory_seed.v1",
        "role": role,
        "prior_agent_id": prior_agent_id,
        "replacement_reason": replacement_reason,
        "current_run_only": True,
        "body_text_included": False,
        "sealed_packet_body_text_included": False,
        "sealed_result_body_text_included": False,
        "packet_summaries": packet_rows,
        "active_blockers": blocker_rows,
        "pm_repair_decisions": pm_decisions,
        "recent_role_report_summary": _recent_role_report_summary(ledger) if role == "pm" else [],
        "created_at": now_iso(),
    }


def _attach_role_memory_seed(
    ledger: dict[str, Any],
    lease: dict[str, Any],
    *,
    memory: Mapping[str, Any],
    prior_agent_id: str = "",
    required: bool = False,
) -> str:
    memory_seed_id = _next_id(ledger, "role_memory_seed")
    row = _copy_jsonable(memory)
    row["memory_seed_id"] = memory_seed_id
    row["lease_id"] = str(lease.get("lease_id") or "")
    row["required_before_open"] = bool(required)
    row["prior_agent_id"] = prior_agent_id or str(row.get("prior_agent_id") or "")
    ledger.setdefault("role_memory", {})[memory_seed_id] = row
    lease["role_memory_seed_id"] = memory_seed_id
    lease["role_memory_seed_required"] = bool(required)
    lease["role_memory_present"] = True
    if prior_agent_id:
        lease["prior_agent_id"] = prior_agent_id
        lease["prior_agent_authority"] = "audit_only"
    _event(
        ledger,
        "role_memory_seed_attached",
        lease_id=str(lease.get("lease_id") or ""),
        role=str(lease.get("responsibility") or ""),
        memory_seed_id=memory_seed_id,
        required=bool(required),
    )
    return memory_seed_id


def _update_role_slot_liveness(ledger: dict[str, Any], lease: Mapping[str, Any], status: str) -> None:
    role = str(lease.get("responsibility") or "")
    lease_id = str(lease.get("lease_id") or "")
    if not role or not lease_id:
        return
    roles = _role_continuity_table(ledger)
    slot = roles.get(role)
    if not isinstance(slot, dict) or str(slot.get("latest_lease_id") or "") != lease_id:
        return
    slot["last_liveness_status"] = status
    slot["last_liveness_checked_at"] = now_iso()
    if status in _ROLE_NONREUSABLE_LIVENESS_STATUSES:
        slot["reuse_state"] = "not_reusable"
        slot["not_reusable_reason"] = f"liveness:{status}"
    slot["updated_at"] = now_iso()


def role_memory_seed_for_lease(
    ledger: dict[str, Any],
    lease_id: str,
    packet_id: str = "",
) -> dict[str, Any] | None:
    lease = _require(ledger["leases"], lease_id, "lease")
    if packet_id and str(lease.get("packet_id") or "") not in {"", packet_id}:
        raise BlackBoxRuntimeError("role memory lease packet mismatch")
    memory_seed_id = str(lease.get("role_memory_seed_id") or "")
    if not memory_seed_id:
        if lease.get("role_memory_seed_required"):
            _event(ledger, "role_memory_seed_missing", lease_id=lease_id, packet_id=packet_id)
            raise BlackBoxRuntimeError("replacement lease requires role memory before packet open")
        return None
    memory = ledger.setdefault("role_memory", {}).get(memory_seed_id)
    if not isinstance(memory, Mapping):
        if lease.get("role_memory_seed_required"):
            _event(ledger, "role_memory_seed_missing", lease_id=lease_id, packet_id=packet_id)
            raise BlackBoxRuntimeError("replacement lease role memory seed is missing")
        return None
    return _copy_jsonable(memory)


def _mark_role_slot_after_lease(
    ledger: dict[str, Any],
    role: str,
    lease: dict[str, Any],
    *,
    reused: bool,
    requested_agent_id: str,
    prior_agent_id: str = "",
    replacement_reason: str = "",
) -> None:
    roles = _role_continuity_table(ledger)
    previous = roles.get(role) if isinstance(roles.get(role), Mapping) else {}
    slot = {
        "schema_version": "black_box_flowpilot.role_slot.v1",
        "role": role,
        "agent_id": str(lease.get("agent_id") or ""),
        "latest_lease_id": str(lease.get("lease_id") or ""),
        "latest_packet_id": str(lease.get("packet_id") or ""),
        "reuse_state": "reusable",
        "last_liveness_status": str(lease.get("liveness_status") or lease.get("last_liveness_status") or ""),
        "last_continuity_action": "reused" if reused else ("replaced" if prior_agent_id else "initialized"),
        "prior_agent_id": prior_agent_id,
        "replacement_reason": replacement_reason,
        "updated_at": now_iso(),
    }
    rejected: list[str] = []
    if reused and requested_agent_id and requested_agent_id != slot["agent_id"]:
        rejected = [requested_agent_id]
    if isinstance(previous, Mapping):
        rejected.extend(str(item) for item in previous.get("rejected_replacement_candidate_ids") or [])
    slot["rejected_replacement_candidate_ids"] = sorted(set(item for item in rejected if item))
    roles[role] = slot
    lease["role_continuity"] = {
        "role": role,
        "reused": reused,
        "replaced": bool(prior_agent_id and not reused),
        "requested_agent_id": requested_agent_id,
        "effective_agent_id": slot["agent_id"],
        "prior_agent_id": prior_agent_id,
        "replacement_reason": replacement_reason,
    }
    if reused:
        event = "role_continuity_reused"
    elif prior_agent_id:
        event = "role_continuity_replaced"
    else:
        event = "role_continuity_initialized"
    _event(
        ledger,
        event,
        role=role,
        lease_id=slot["latest_lease_id"],
        effective_agent_id=slot["agent_id"],
        requested_agent_id=requested_agent_id,
        prior_agent_id=prior_agent_id,
        replacement_reason=replacement_reason,
    )


def lease_agent(
    ledger: dict[str, Any],
    responsibility: str,
    *,
    agent_id: str | None = None,
    packet_id: str = "",
    assignment_id: str = "",
) -> str:
    _assert_not_terminal_lifecycle(ledger)
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    _require_background_collaboration_authorized(ledger)
    assignments = _role_assignment_table(ledger)
    assignment: dict[str, Any]
    if assignment_id:
        raw_assignment = _require(assignments, assignment_id, "role assignment")
        if not isinstance(raw_assignment, dict):
            raise BlackBoxRuntimeError("role assignment record is invalid")
        assignment = raw_assignment
        if assignment.get("status") != "resolved":
            raise BlackBoxRuntimeError("role assignment is not available for lease commit")
        if str(assignment.get("responsibility") or "") != responsibility:
            raise BlackBoxRuntimeError("role assignment responsibility mismatch")
        if packet_id and str(assignment.get("packet_id") or "") not in {"", packet_id}:
            raise BlackBoxRuntimeError("role assignment packet mismatch")
        if str(assignment.get("disposition") or "") == "blocked":
            raise BlackBoxRuntimeError("blocked role assignment cannot be committed")
    else:
        assignment = resolve_role_assignment(ledger, responsibility, packet_id=packet_id, host_kind="live")
        assignment_id = str(assignment.get("assignment_id") or "")
    disposition = str(assignment.get("disposition") or "")
    if disposition not in {"reuse_existing_role", "create_new_role"}:
        raise BlackBoxRuntimeError(f"unsupported role assignment disposition: {disposition}")
    requested_agent_id = ""
    prior_agent_id = str(assignment.get("prior_agent_id") or "")
    effective_agent_id = str(assignment.get("effective_agent_id") or "")
    replacement_reason = ""
    reused = disposition == "reuse_existing_role"
    memory_seed: dict[str, Any] | None = None
    memory_required = False
    if reused:
        if agent_id and str(agent_id).strip() and str(agent_id).strip() != effective_agent_id:
            raise BlackBoxRuntimeError("reuse assignment does not accept a fresh agent id")
    else:
        requested_agent_id = str(agent_id or "").strip()
        effective_agent_id = requested_agent_id
        replacement_reason = str(assignment.get("replacement_reason") or "")
    if prior_agent_id and not reused:
        memory_seed = _build_role_memory_seed(
            ledger,
            responsibility,
            prior_agent_id=prior_agent_id,
            replacement_reason=replacement_reason,
        )
        memory_required = True
    lease_id = _next_id(ledger, "lease")
    if not effective_agent_id:
        if disposition == "create_new_role":
            effective_agent_id = f"{responsibility}-{assignment_id}"
            requested_agent_id = effective_agent_id
        else:
            raise BlackBoxRuntimeError("reuse assignment is missing effective agent id")
    lease = {
        "lease_id": lease_id,
        "agent_id": effective_agent_id,
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
        "role_assignment_id": assignment_id,
    }
    ledger["leases"][lease_id] = lease
    if memory_seed is not None:
        _attach_role_memory_seed(
            ledger,
            lease,
            memory=memory_seed,
            prior_agent_id=prior_agent_id,
            required=memory_required,
        )
    _mark_role_slot_after_lease(
        ledger,
        responsibility,
        lease,
        reused=reused,
        requested_agent_id=requested_agent_id,
        prior_agent_id="" if reused else prior_agent_id,
        replacement_reason=replacement_reason,
    )
    if isinstance(assignment, dict):
        assignment["status"] = "consumed"
        assignment["consumed_lease_id"] = lease_id
        assignment["consumed_at"] = now_iso()
        assignment["effective_agent_id"] = effective_agent_id
    _event(
        ledger,
        "role_assignment_committed",
        assignment_id=assignment_id,
        lease_id=lease_id,
        role=responsibility,
        packet_id=packet_id,
        disposition=disposition,
        effective_agent_id=effective_agent_id,
    )
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


def _active_packet_lease_ids(ledger: Mapping[str, Any], packet_id: str) -> list[str]:
    return [
        str(lease_id)
        for lease_id, lease in ledger.get("leases", {}).items()
        if isinstance(lease, Mapping)
        and str(lease.get("packet_id") or "") == packet_id
        and str(lease.get("status") or "") == "active"
    ]


def _supersede_older_active_packet_leases(
    ledger: dict[str, Any],
    packet_id: str,
    replacement_lease_id: str,
    *,
    reason: str,
) -> list[str]:
    replacement = _require(ledger["leases"], replacement_lease_id, "lease")
    superseded: list[str] = []
    closed: list[str] = []
    for lease_id in list(_active_packet_lease_ids(ledger, packet_id)):
        if lease_id == replacement_lease_id:
            continue
        lease = _require(ledger["leases"], lease_id, "lease")
        if lease.get("responsibility") == replacement.get("responsibility"):
            supersede_lease(ledger, lease_id, replacement_lease_id, reason)
            superseded.append(lease_id)
        else:
            close_lease(ledger, lease_id, f"{reason}:wrong_responsibility")
            closed.append(lease_id)
    return superseded + closed


def _default_packet_acceptance_criteria(acceptance_criteria: list[str] | None) -> list[str]:
    criteria = list(acceptance_criteria or [])
    if REPLAYABLE_ARTIFACT_ACCEPTANCE_CRITERION not in criteria:
        criteria.append(REPLAYABLE_ARTIFACT_ACCEPTANCE_CRITERION)
    return criteria


def _role_result_requires_pm_visible_summary(*, responsibility: str, packet_kind: str) -> bool:
    return (
        packet_kind in PM_VISIBLE_SUMMARY_REQUIRED_PACKET_KINDS
        and responsibility not in PM_VISIBLE_SUMMARY_EXEMPT_RESPONSIBILITIES
    )


def _packet_requires_pm_visible_summary(packet: Mapping[str, Any]) -> bool:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    return _role_result_requires_pm_visible_summary(
        responsibility=str(envelope.get("responsibility") or ""),
        packet_kind=str(envelope.get("packet_kind", "task")),
    )


def _pm_visible_summary_from_payload(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("pm_visible_summary")
    if not isinstance(raw, list):
        return []
    summaries: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            return []
        text = item.strip()
        if not text:
            return []
        summaries.append(text)
    return summaries


def _pm_visible_summary_from_body(body: str) -> list[str]:
    payload = _strict_json_object_from_body(body)
    if not payload:
        return []
    return _pm_visible_summary_from_payload(payload)


def _structured_required_repairs_from_payload(payload: Mapping[str, Any]) -> list[str]:
    repairs: list[str] = []
    raw_findings = payload.get("blocking_findings")
    if isinstance(raw_findings, list):
        for finding in raw_findings:
            if not isinstance(finding, Mapping):
                continue
            repair = finding.get("required_repair")
            if isinstance(repair, str) and repair.strip():
                repairs.append(repair.strip())
    direct = payload.get("required_repair")
    if isinstance(direct, str) and direct.strip():
        repairs.append(direct.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for repair in repairs:
        if repair in seen:
            continue
        seen.add(repair)
        deduped.append(repair)
    return deduped


def _recent_role_report_summary(ledger: Mapping[str, Any], *, limit: int = PM_VISIBLE_SUMMARY_MAX_ENTRIES) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in reversed(list(ledger.get("results", {}).values())):
        if not isinstance(result, Mapping):
            continue
        packet_id = str(result.get("packet_id") or "")
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, Mapping) or not _packet_requires_pm_visible_summary(packet):
            continue
        summary = _pm_visible_summary_from_body(str(result.get("body", "")))
        if not summary:
            continue
        status = str(result.get("status") or "")
        semantic_decision = str(result.get("semantic_decision") or "")
        if not (
            result.get("accepted") is True
            or status in {"semantic_blocked", "flowguard_blocked"}
            or semantic_decision in {"block", "fail"}
        ):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        rows.append(
            {
                "role": str(envelope.get("responsibility") or ""),
                "packet_id": packet_id,
                "result_id": str(result.get("result_id") or ""),
                "packet_kind": str(envelope.get("packet_kind", "task")),
                "summary": summary,
                "summary_is_navigation_only": True,
                "formal_judgement_requires_authorized_body_read": True,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _pm_packet_body_with_recent_role_reports(ledger: Mapping[str, Any], responsibility: str, body: str) -> str:
    if responsibility != "pm":
        return body
    payload = _strict_json_object_from_body(body)
    if payload is None:
        return body
    if "recent_role_report_summary" not in payload:
        payload["recent_role_report_summary"] = _recent_role_report_summary(ledger)
    payload.setdefault(
        "recent_role_report_summary_policy",
        {
            "role_authored_summary_only": True,
            "summary_is_navigation_only": True,
            "required_body_reads_still_apply": True,
            "runtime_may_synthesize_missing_summary": False,
        },
    )
    return json.dumps(payload, indent=2, sort_keys=True)


def _normalize_authorized_result_read_ref(
    ledger: Mapping[str, Any],
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    result_id = str(raw.get("result_id") or "")
    if not result_id:
        raise BlackBoxRuntimeError("authorized_result_reads[] requires result_id")
    result = _require(ledger.get("results", {}), result_id, "authorized result")
    result_envelope = result.get("envelope", {}) if isinstance(result.get("envelope"), Mapping) else {}
    body_hash = str(result_envelope.get("body_hash") or "")
    body = str(result.get("body", ""))
    if not body_hash or hash_text(body) != body_hash:
        raise BlackBoxRuntimeError(f"authorized result body hash mismatch: {result_id}")
    source_packet_id = str(result.get("packet_id") or raw.get("source_packet_id") or "")
    source_packet = ledger.get("packets", {}).get(source_packet_id) if source_packet_id else None
    source_envelope = (
        source_packet.get("envelope", {})
        if isinstance(source_packet, Mapping) and isinstance(source_packet.get("envelope"), Mapping)
        else {}
    )
    allowed_roles_raw = raw.get("allowed_roles")
    if not isinstance(allowed_roles_raw, list) or not allowed_roles_raw:
        raise BlackBoxRuntimeError(f"authorized_result_reads[] requires explicit allowed_roles for {result_id}")
    allowed_roles = sorted({str(role) for role in allowed_roles_raw if str(role) in RESPONSIBILITIES})
    if len(allowed_roles) != len({str(role) for role in allowed_roles_raw}):
        raise BlackBoxRuntimeError(f"authorized_result_reads[] has unknown allowed role for {result_id}")
    return {
        "result_id": result_id,
        "source_packet_id": source_packet_id,
        "source_packet_kind": str(source_envelope.get("packet_kind", "task")),
        "source_role": str(source_envelope.get("responsibility") or raw.get("source_role") or ""),
        "purpose": str(raw.get("purpose") or "authorized_result_read"),
        "allowed_roles": allowed_roles,
        "required_before_submit": bool(raw.get("required_before_submit") is True),
        "body_hash": body_hash,
        "body_visibility": "sealed",
        "runtime_verifies_body_hash": True,
    }


def _normalize_authorized_result_reads(
    ledger: Mapping[str, Any],
    reads: list[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for raw in reads or []:
        if not isinstance(raw, Mapping):
            raise BlackBoxRuntimeError("authorized_result_reads[] entries must be objects")
        row = _normalize_authorized_result_read_ref(ledger, raw)
        key = (row["result_id"], row["purpose"], tuple(row["allowed_roles"]))
        if key in seen:
            continue
        seen.add(key)
        normalized.append(row)
    return normalized


def _packet_body_with_authorized_result_reads(body: str, reads: list[dict[str, Any]]) -> str:
    payload = _strict_json_object_from_body(body)
    if reads:
        if payload is None:
            raise BlackBoxRuntimeError("authorized_result_reads requires a strict JSON packet body")
        payload["authorized_result_reads"] = json.loads(json.dumps(reads, sort_keys=True))
        return json.dumps(payload, indent=2, sort_keys=True)
    if payload is not None and "authorized_result_reads" in payload:
        raise BlackBoxRuntimeError("authorized_result_reads must be issued by the runtime envelope")
    return body


def _merge_authorized_result_reads(
    existing: list[Mapping[str, Any]],
    additions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for row in list(existing) + list(additions):
        if not isinstance(row, Mapping):
            continue
        allowed = tuple(sorted(str(role) for role in row.get("allowed_roles", []) if str(role)))
        key = (str(row.get("result_id") or ""), str(row.get("purpose") or ""), allowed)
        if not key[0] or not allowed:
            continue
        merged[key] = json.loads(json.dumps(dict(row), sort_keys=True))
    return list(merged.values())


def _attach_authorized_result_reads_to_packet(
    ledger: dict[str, Any],
    packet_id: str,
    reads: list[Mapping[str, Any]],
) -> None:
    if not reads:
        return
    packet = _require(ledger["packets"], packet_id, "packet")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if not isinstance(envelope, dict):
        raise BlackBoxRuntimeError("packet envelope is missing")
    existing = envelope.get("authorized_result_reads", [])
    if not isinstance(existing, list):
        raise BlackBoxRuntimeError("packet authorized_result_reads must be a list")
    normalized = _normalize_authorized_result_reads(ledger, list(reads))
    merged = _merge_authorized_result_reads(existing, normalized)
    body = _packet_body_with_authorized_result_reads(str(packet.get("body", "")), merged)
    body_hash = hash_text(body)
    packet["body"] = body
    envelope["authorized_result_reads"] = merged
    envelope["body_hash"] = body_hash


def _authorized_read_for_result(
    ledger: Mapping[str, Any],
    result_id: str,
    *,
    allowed_roles: list[str],
    purpose: str,
    required_before_submit: bool = True,
) -> dict[str, Any]:
    return _normalize_authorized_result_read_ref(
        ledger,
        {
            "result_id": result_id,
            "allowed_roles": allowed_roles,
            "purpose": purpose,
            "required_before_submit": required_before_submit,
        },
    )


def _blocker_authorized_result_reads(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    *,
    allowed_roles: list[str],
    purpose: str,
    required_before_submit: bool = True,
) -> list[dict[str, Any]]:
    result_id = str(blocker.get("result_id") or "")
    if not result_id:
        return []
    if not isinstance(ledger.get("results", {}).get(result_id), Mapping):
        return []
    return [
        _authorized_read_for_result(
            ledger,
            result_id,
            allowed_roles=allowed_roles,
            purpose=purpose,
            required_before_submit=required_before_submit,
        )
    ]


def _packet_authorized_result_reads(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    raw = envelope.get("authorized_result_reads", [])
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _has_result_body_open_receipt(
    packet: Mapping[str, Any],
    *,
    lease_id: str,
    responsibility: str,
    result_id: str,
    body_hash: str,
) -> bool:
    receipts = packet.get("authorized_result_read_receipts", [])
    if not isinstance(receipts, list):
        return False
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        if (
            receipt.get("lease_id") == lease_id
            and receipt.get("responsibility") == responsibility
            and receipt.get("result_id") == result_id
            and receipt.get("body_hash") == body_hash
        ):
            return True
    return False


def _required_authorized_result_read_blockers(
    ledger: Mapping[str, Any],
    *,
    lease: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    responsibility = str(lease.get("responsibility") or "")
    for row in _packet_authorized_result_reads(packet):
        if row.get("required_before_submit") is not True:
            continue
        result_id = str(row.get("result_id") or "")
        body_hash = str(row.get("body_hash") or "")
        allowed_roles = row.get("allowed_roles")
        if not isinstance(allowed_roles, list) or responsibility not in {str(role) for role in allowed_roles}:
            blockers.append(f"required_result_body_not_authorized:{result_id}")
            continue
        result = ledger.get("results", {}).get(result_id)
        result_envelope = result.get("envelope", {}) if isinstance(result, Mapping) and isinstance(result.get("envelope"), Mapping) else {}
        if not isinstance(result, Mapping) or hash_text(str(result.get("body", ""))) != body_hash or result_envelope.get("body_hash") != body_hash:
            blockers.append(f"required_result_body_hash_mismatch:{result_id}")
            continue
        if not _has_result_body_open_receipt(
            packet,
            lease_id=str(lease.get("lease_id") or ""),
            responsibility=responsibility,
            result_id=result_id,
            body_hash=body_hash,
        ):
            blockers.append(f"required_result_body_not_opened:{result_id}")
    return blockers


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
    node_context_package_id: str = "",
    authorized_result_reads: list[Mapping[str, Any]] | None = None,
) -> str:
    _assert_not_terminal_lifecycle(ledger)
    if ledger.get("active_route_version") is None:
        raise BlackBoxRuntimeError("cannot issue a packet without an active route")
    if responsibility not in RESPONSIBILITIES:
        raise BlackBoxRuntimeError(f"unknown responsibility: {responsibility}")
    if packet_kind not in PACKET_KINDS:
        raise BlackBoxRuntimeError(f"unknown packet kind: {packet_kind}")
    packet_id = preassigned_packet_id or _next_id(ledger, "packet")
    normalized_result_reads = _normalize_authorized_result_reads(ledger, authorized_result_reads)
    body = _pm_packet_body_with_recent_role_reports(ledger, responsibility, body)
    body = _packet_body_with_authorized_result_reads(body, normalized_result_reads)
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
        "node_context_package_id": node_context_package_id,
        "acceptance_criteria": _default_packet_acceptance_criteria(acceptance_criteria),
        "body_hash": body_hash,
        "body_visibility": "sealed",
        "source_generation": ledger["source_generation"],
    }
    if normalized_result_reads:
        envelope["authorized_result_reads"] = normalized_result_reads
    envelope["output_contract"] = control_surface.build_packet_output_contract(
        packet_id=packet_id,
        responsibility=responsibility,
        packet_kind=packet_kind,
        route_version=int(ledger["active_route_version"]),
        source_generation=int(ledger["source_generation"]),
    )
    if _role_result_requires_pm_visible_summary(responsibility=responsibility, packet_kind=packet_kind):
        output_contract = dict(envelope["output_contract"])
        output_contract["pm_visible_summary_required"] = True
        output_contract["pm_visible_summary_shape"] = "non_empty_string_list"
        output_contract["runner_may_synthesize_pm_visible_summary"] = False
        envelope["output_contract"] = output_contract
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
    superseded_lease_ids = _supersede_older_active_packet_leases(
        ledger,
        packet_id,
        lease_id,
        reason="packet_reassigned",
    )
    packet["assigned_lease_id"] = lease_id
    packet["status"] = "assigned"
    lease["packet_id"] = packet_id
    _event(
        ledger,
        "packet_assigned",
        packet_id=packet_id,
        lease_id=lease_id,
        superseded_active_lease_ids=superseded_lease_ids,
    )


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


def open_result_body_for_role(
    ledger: dict[str, Any],
    packet_id: str,
    lease_id: str,
    result_id: str,
) -> dict[str, Any]:
    _assert_not_terminal_lifecycle(ledger)
    packet = _require(ledger["packets"], packet_id, "packet")
    lease = _require(ledger["leases"], lease_id, "lease")
    result = _require(ledger["results"], result_id, "result")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if packet.get("assigned_lease_id") != lease_id:
        raise BlackBoxRuntimeError("lease cannot open this sealed result body")
    if lease.get("status") != "active":
        raise BlackBoxRuntimeError("inactive lease cannot open sealed result body")
    if lease.get("packet_id") != packet_id:
        raise BlackBoxRuntimeError("lease packet mismatch")
    if lease.get("responsibility") != envelope.get("responsibility"):
        raise BlackBoxRuntimeError("lease responsibility does not match packet")
    if not lease.get("ack_received"):
        raise BlackBoxRuntimeError("lease must ACK before opening sealed result body")
    if packet.get("accepted_result_id") or packet.get("status") in {"accepted", "quarantined_after_route_mutation"}:
        raise BlackBoxRuntimeError("accepted or stale packet cannot open result body")
    authorized = None
    responsibility = str(lease.get("responsibility") or "")
    for row in _packet_authorized_result_reads(packet):
        if str(row.get("result_id") or "") != result_id:
            continue
        allowed_roles = row.get("allowed_roles")
        if isinstance(allowed_roles, list) and responsibility in {str(role) for role in allowed_roles}:
            authorized = row
            break
    if authorized is None:
        raise BlackBoxRuntimeError("result body is not authorized for this role packet")
    result_envelope = result.get("envelope", {}) if isinstance(result.get("envelope"), Mapping) else {}
    body = str(result.get("body", ""))
    body_hash = str(result_envelope.get("body_hash") or "")
    expected_hash = str(authorized.get("body_hash") or "")
    if not body_hash or body_hash != expected_hash or hash_text(body) != expected_hash:
        raise BlackBoxRuntimeError("authorized result body hash mismatch")
    receipt_id = _next_id(ledger, "result_read")
    receipt = {
        "schema_version": "black_box_flowpilot.result_body_open_receipt.v1",
        "receipt_id": receipt_id,
        "packet_id": packet_id,
        "lease_id": lease_id,
        "responsibility": responsibility,
        "result_id": result_id,
        "source_packet_id": str(result.get("packet_id") or ""),
        "purpose": str(authorized.get("purpose") or "authorized_result_read"),
        "body_hash": body_hash,
        "opened_at": now_iso(),
        "current_run_only": True,
    }
    packet.setdefault("authorized_result_read_receipts", []).append(receipt)
    result.setdefault("body_open_receipts", []).append(receipt)
    _event(
        ledger,
        "sealed_result_body_opened",
        packet_id=packet_id,
        lease_id=lease_id,
        responsibility=responsibility,
        result_id=result_id,
        body_hash=body_hash,
        receipt_id=receipt_id,
    )
    return {"body": body, "receipt": receipt}


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
    _update_role_slot_liveness(ledger, lease, normalized)
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


_OUTCOME_ALIAS_KEYS = {
    "verdict",
    "status",
    "outcome",
    "result",
    "pass_or_block",
    "validation_status",
    "flowguard_decision",
    "worker_status",
    "passed",
}


def _strict_packet_outcome_contract_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> str:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    if packet_kind in {"pm_repair_decision", "pm_disposition"}:
        return ""
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return "packet result requires a current strict JSON object"
    if "decision" not in payload:
        alias_keys = sorted(key for key in _OUTCOME_ALIAS_KEYS if key in payload)
        if alias_keys:
            return "packet result uses unsupported outcome alias field(s): " + ",".join(alias_keys)
        return "packet result requires top-level decision"
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision not in (_PASSING_OUTCOME_DECISIONS | _BLOCKING_OUTCOME_DECISIONS):
        return "packet result decision must be an explicit allowed pass/block decision"
    return ""


def _pm_visible_summary_contract_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> str:
    if not _packet_requires_pm_visible_summary(packet):
        return ""
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return "packet result requires a current strict JSON object"
    if not _pm_visible_summary_from_payload(payload):
        return "formal role result requires role-authored pm_visible_summary as a non-empty list of non-empty strings"
    return ""


def _current_result_submission_contract_violation(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    route_scope = str(envelope.get("route_scope") or "")
    body = str(result.get("body", ""))
    outcome_violation = _strict_packet_outcome_contract_violation(packet, result)
    if outcome_violation:
        return outcome_violation
    summary_violation = _pm_visible_summary_contract_violation(packet, result)
    if summary_violation:
        return summary_violation
    if packet_kind == "task" and route_scope == "planning":
        try:
            route_plan = _parse_strict_route_plan(body)
            _normalize_strict_route_plan_nodes(route_plan)
        except BlackBoxRuntimeError as exc:
            return str(exc)
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        node_id = str(envelope.get("route_node_id") or "")
        try:
            node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
            _node_context_package_from_pm_result(
                ledger,
                node,
                packet,
                str(result.get("result_id") or ""),
                context_package_id="staged",
                status="staged",
            )
        except BlackBoxRuntimeError as exc:
            return str(exc)
        _attach_staged_effect(
            result,  # type: ignore[arg-type]
            effect_kind="commit_node_acceptance_plan",
            source_packet_id=str(packet.get("packet_id") or ""),
            source_result_id=str(result.get("result_id") or ""),
            target_node_id=node_id,
            route_scope=route_scope,
        )
    if packet_kind == "flowguard_check":
        lowered_body = body.lower()
        if "api_fallback_manual_block_eval" in lowered_body or "fallback_manual_block_eval" in lowered_body:
            return "FlowGuard fallback evidence is forbidden; submit real FlowGuard evidence or a toolchain blocker"
    return ""


def _block_result_and_reissue_current_packet_family(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: Mapping[str, Any],
    *,
    reason: str,
) -> str:
    blocker_name = "current_result_contract_violation"
    result["status"] = "mechanical_contract_blocked"
    result["accepted"] = False
    result["non_authoritative"] = True
    result.setdefault("mechanical_blockers", []).append(blocker_name)
    result["quarantine_reason"] = reason
    old_packet_id = str(packet.get("packet_id") or "")
    packet["status"] = "superseded_after_repair"
    packet["superseded_by_result_id"] = str(result.get("result_id") or "")
    packet["superseded_reason"] = blocker_name
    packet["superseded_at"] = now_iso()
    close_lease(ledger, str(lease["lease_id"]), "current_result_contract_blocked")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    fresh_packet_id = issue_task_packet(
        ledger,
        str(envelope.get("responsibility") or "pm"),
        f"Reissue current-contract result for {old_packet_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.current_contract_reissue_packet.v1",
                "blocked_packet_id": old_packet_id,
                "blocked_result_id": str(result.get("result_id") or ""),
                "blocked_reason": reason,
                "original_packet_kind": packet_kind,
                "route_scope": str(envelope.get("route_scope") or ""),
                "route_node_id": str(envelope.get("route_node_id") or ""),
                "acceptance_criteria": list(envelope.get("acceptance_criteria") or []),
                "contract": _copy_jsonable(envelope.get("output_contract") or {}),
                "required_result_body_fields": ["decision", "pm_visible_summary"]
                if _packet_requires_pm_visible_summary(packet)
                else ["decision"],
                "instruction": (
                    "Submit a fresh current-contract result for the same packet family. "
                    "Do not reuse obsolete field names, wrapper shapes, fallback evidence, or prior blocked text as passing evidence. "
                    "When pm_visible_summary is required, the producing role must write it directly; runtime cannot synthesize it."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        required_flowguard_target=str(envelope.get("required_flowguard_target") or ""),
        packet_kind=packet_kind,
        subject_id=str(envelope.get("subject_id") or "") if packet_kind != "task" else "",
        target_result_id=str(envelope.get("target_result_id") or ""),
        route_node_id=str(envelope.get("route_node_id") or ""),
        route_scope=str(envelope.get("route_scope") or ""),
        acceptance_criteria=list(envelope.get("acceptance_criteria") or []),
        node_context_package_id=str(envelope.get("node_context_package_id") or ""),
    )
    ledger["packets"][fresh_packet_id]["repair_blocker_id"] = str(packet.get("active_blocker_id") or "")
    _event(
        ledger,
        "result_mechanical_contract_blocked",
        packet_id=old_packet_id,
        result_id=str(result.get("result_id") or ""),
        reason=reason,
    )
    _event(
        ledger,
        "current_contract_reissue_packet_issued",
        blocked_packet_id=old_packet_id,
        fresh_packet_id=fresh_packet_id,
        packet_kind=packet_kind,
        route_scope=str(envelope.get("route_scope") or ""),
    )
    return fresh_packet_id


def _apply_valid_packet_result(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: dict[str, Any],
) -> None:
    packet_kind = packet["envelope"].get("packet_kind", "task")
    contract_violation = _current_result_submission_contract_violation(ledger, packet, result)
    if contract_violation:
        _block_result_and_reissue_current_packet_family(
            ledger,
            packet,
            result,
            lease,
            reason=contract_violation,
        )
        return
    if packet_kind == "pm_repair_decision":
        try:
            repair_decision, repair_reason, authority_ref, route_plan = _parse_pm_repair_decision_body(str(result.get("body", "")))
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
            authority_ref=authority_ref,
            route_plan=route_plan,
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
        if packet["envelope"].get("route_scope") == NODE_PREWORK_FLOWGUARD_SCOPE:
            _clear_semantic_blockers_for_pass(
                ledger,
                subject_packet_id=str(packet["envelope"]["subject_id"]),
                gate_kind="flowguard_check",
                recheck_role=str(packet["envelope"]["responsibility"]),
                outcome_id=outcome_id,
            )
            ensure_next_node_task_packet(ledger)
            return
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=str(packet["envelope"]["subject_id"]),
            gate_kind="flowguard_check",
            recheck_role="flowguard_operator",
            outcome_id=outcome_id,
        )
        repair_blocker_id = str(packet.get("repair_blocker_id") or "")
        _ensure_review_packet_for_task_result(
            ledger,
            packet["envelope"]["subject_id"],
            force_new=bool(repair_blocker_id),
            repair_blocker_id=repair_blocker_id,
            recheck_reason="recheck_after_reattached_stopped_blocker" if repair_blocker_id else "",
        )
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
        _record_node_acceptance_plan_closure(
            ledger,
            node_id,
            subject_packet,
            system_closure_id=system_closure_id,
        )
        ensure_node_prework_flowguard_packet(ledger, node_id)
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
            ensure_node_prework_flowguard_packet(ledger, active_node)
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
    *,
    system_closure_id: str = "",
) -> str:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    result_id = str(subject_packet.get("accepted_result_id") or "")
    result = _require(ledger.setdefault("results", {}), result_id, "result")
    effect = result.get("staged_effect") if isinstance(result.get("staged_effect"), Mapping) else {}
    if (
        effect.get("effect_kind") != "commit_node_acceptance_plan"
        or effect.get("status") not in {"pending", "committed"}
        or str(effect.get("target_node_id") or "") != node_id
    ):
        raise BlackBoxRuntimeError("node acceptance plan closure requires a pending staged effect")
    context_package = _node_context_package_from_pm_result(ledger, node, subject_packet, result_id)
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
        "repair_generation": int(node.get("repair_generation", 0)),
        "node_context_package_id": context_package["context_package_id"],
        "repair_policy": "repair_scope_replacement_default",
        "high_standard_requirement_ids": requirement_ids,
        "skill_standard_obligation_ids": obligation_ids,
        "created_at": now_iso(),
    }
    ledger.setdefault("node_context_packages", {})[context_package["context_package_id"]] = context_package
    node["node_acceptance_plan_id"] = plan_id
    node["node_context_package_id"] = context_package["context_package_id"]
    node["node_context_package_repair_generation"] = int(node.get("repair_generation", 0))
    node["prework_flowguard_packet_id"] = ""
    node["prework_flowguard_order_id"] = ""
    node["prework_flowguard_result_id"] = ""
    node["prework_flowguard_repair_generation"] = None
    node["high_standard_requirement_ids"] = requirement_ids
    node["skill_standard_obligation_ids"] = obligation_ids
    _mark_staged_effect_committed(result, system_closure_id=system_closure_id)
    _event(
        ledger,
        "node_context_package_accepted",
        node_id=node_id,
        context_package_id=context_package["context_package_id"],
        repair_generation=int(node.get("repair_generation", 0)),
    )
    _event(ledger, "node_acceptance_plan_accepted", node_id=node_id, plan_id=plan_id)
    _event(
        ledger,
        "staged_effect_committed",
        effect_kind="commit_node_acceptance_plan",
        source_packet_id=str(subject_packet.get("packet_id") or ""),
        source_result_id=result_id,
        system_closure_id=system_closure_id,
    )
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
    _supersede_older_active_packet_leases(
        ledger,
        str(packet.get("packet_id") or ""),
        str(lease.get("lease_id") or ""),
        reason="accepted_result_superseded_stale_lease",
    )
    packet["assigned_lease_id"] = lease["lease_id"]
    close_lease(ledger, lease["lease_id"], reason)


def _find_packet(
    ledger: Mapping[str, Any],
    *,
    packet_kind: str,
    subject_id: str,
    target_result_id: str = "",
    reusable_statuses: set[str] | None = None,
) -> dict[str, Any] | None:
    for packet in ledger.get("packets", {}).values():
        envelope = packet.get("envelope", {})
        if envelope.get("packet_kind", "task") != packet_kind:
            continue
        if envelope.get("subject_id", "") != subject_id:
            continue
        if target_result_id and envelope.get("target_result_id", "") != target_result_id:
            continue
        if packet.get("status") in {"quarantined_after_route_mutation", "superseded_after_repair"}:
            continue
        if reusable_statuses is not None and packet.get("status") not in reusable_statuses:
            continue
        return packet
    return None


def _ensure_flowguard_packet_for_task_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    force_new: bool = False,
    repair_blocker_id: str = "",
    recheck_reason: str = "",
) -> str:
    subject_id = str(packet["packet_id"])
    existing = None
    if not force_new:
        existing = _find_packet(
            ledger,
            packet_kind="flowguard_check",
            subject_id=subject_id,
            target_result_id=str(result["result_id"]),
        )
    if existing:
        return str(existing["packet_id"])
    flowguard_packet_id = _next_id(ledger, "packet")
    evidence_root = _flowguard_packet_evidence_root(ledger, flowguard_packet_id)
    node_id = str(packet["envelope"].get("route_node_id") or "")
    node_context = _optional_node_context_reference(ledger, node_id) if node_id else {}
    body_payload = {
        "schema_version": "black_box_flowpilot.flowguard_packet.v1",
        "subject_packet_id": subject_id,
        "target_result_id": result["result_id"],
        "modeled_target": packet["envelope"]["required_flowguard_target"],
        **node_context,
        **_staged_effect_public_reference(result),
        "instruction": (
            "Produce current-run FlowGuard evidence for the subject packet result. Start from node_context_package "
            "or staged_effect when present, then independently select or create suitable FlowGuard evidence for "
            "the result, skipped checks, and residual risks."
        ),
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
    }
    if repair_blocker_id:
        body_payload["recheck_for_blocker_id"] = repair_blocker_id
    if recheck_reason:
        body_payload["recheck_reason"] = recheck_reason
    packet_id = issue_task_packet(
        ledger,
        "flowguard_operator",
        f"Run FlowGuard evidence for {subject_id}",
        json.dumps(body_payload, indent=2, sort_keys=True),
        required_flowguard_target="",
        packet_kind="flowguard_check",
        subject_id=subject_id,
        target_result_id=str(result["result_id"]),
        preassigned_packet_id=flowguard_packet_id,
        route_node_id=str(packet["envelope"].get("route_node_id") or ""),
        route_scope=str(packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(packet["envelope"].get("acceptance_criteria") or []),
        node_context_package_id=str(node_context.get("node_context_package_id") or ""),
        authorized_result_reads=[
            _authorized_read_for_result(
                ledger,
                str(result["result_id"]),
                allowed_roles=["flowguard_operator"],
                purpose="subject_result_for_flowguard_check",
                required_before_submit=True,
            )
        ],
    )
    if repair_blocker_id:
        ledger["packets"][packet_id]["repair_blocker_id"] = repair_blocker_id
    return packet_id


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
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if envelope.get("route_scope") == NODE_PREWORK_FLOWGUARD_SCOPE:
        node_id = str(envelope.get("route_node_id") or "")
        node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
        modeled_target = str(node.get("modeled_target") or envelope.get("required_flowguard_target") or REQUIRED_FLOWGUARD_TARGET)
        order_id = create_flowguard_work_order(ledger, modeled_target, "prework_node_design", node_id)
        order = ledger["flowguard_work_orders"][order_id]
        order["flowguard_operator_lease_id"] = result["producer_lease_id"]
        order["packet_id"] = packet["packet_id"]
        order["producer_result_id"] = result["result_id"]
        order["flowguard_phase"] = "prework_node_gate"
        order["pm_visible_artifacts_required"] = True
        semantic = outcome if isinstance(outcome, Mapping) else {}
        decision = "fail" if semantic.get("blocking") else "pass"
        complete_flowguard_work_order(ledger, order_id, decision=decision, evidence_id=result["result_id"])
        order["proof_artifact"] = result["result_id"]
        order["confidence_boundary"] = "current_run_node_prework"
        node.setdefault("prework_flowguard_order_ids", []).append(order_id)
        if decision == "pass":
            node["prework_flowguard_order_id"] = order_id
            node["prework_flowguard_packet_id"] = str(packet["packet_id"])
            node["prework_flowguard_result_id"] = str(result["result_id"])
            node["prework_flowguard_repair_generation"] = int(node.get("repair_generation", 0))
            _event(
                ledger,
                "node_prework_flowguard_accepted",
                node_id=node_id,
                order_id=order_id,
                packet_id=str(packet["packet_id"]),
                repair_generation=int(node.get("repair_generation", 0)),
            )
        return order_id

    subject_id = str(packet["envelope"]["subject_id"])
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    modeled_target = subject_packet["envelope"]["required_flowguard_target"]
    order_id = create_flowguard_work_order(ledger, modeled_target, "done_claim", subject_id)
    order = ledger["flowguard_work_orders"][order_id]
    order["flowguard_operator_lease_id"] = result["producer_lease_id"]
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


def _ensure_review_packet_for_task_result(
    ledger: dict[str, Any],
    subject_id: str,
    *,
    force_new: bool = False,
    repair_blocker_id: str = "",
    recheck_reason: str = "",
) -> str:
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    result_ids = [str(item) for item in (subject_packet.get("result_ids") or []) if item]
    target_result_id = str(
        (result_ids[-1] if result_ids else "")
        or subject_packet.get("accepted_result_id")
        or subject_packet["envelope"].get("target_result_id")
        or ""
    )
    existing = None
    if not force_new:
        existing = _find_packet(ledger, packet_kind="review", subject_id=subject_id, target_result_id=target_result_id)
    if existing:
        return str(existing["packet_id"])
    node_id = str(subject_packet["envelope"].get("route_node_id") or "")
    node_context = _optional_node_context_reference(ledger, node_id) if node_id else {}
    body_payload = {
        "schema_version": "black_box_flowpilot.review_packet.v1",
        "subject_packet_id": subject_id,
        "target_result_id": target_result_id,
        **node_context,
        "instruction": (
            "Review the subject result and matching FlowGuard evidence independently. Start from "
            "node_context_package as the minimum checklist, then actively inspect relevant files, UI/screenshots, "
            "logs, commands, model artifacts, and evidence paths inside the authorized scope. Do not treat the "
            "package as the review boundary."
        ),
    }
    if repair_blocker_id:
        body_payload["recheck_for_blocker_id"] = repair_blocker_id
    if recheck_reason:
        body_payload["recheck_reason"] = recheck_reason
    packet_id = issue_task_packet(
        ledger,
        "reviewer",
        f"Review result and FlowGuard evidence for {subject_id}",
        json.dumps(body_payload, indent=2, sort_keys=True),
        required_flowguard_target="",
        packet_kind="review",
        subject_id=subject_id,
        target_result_id=target_result_id,
        route_node_id=str(subject_packet["envelope"].get("route_node_id") or ""),
        route_scope=str(subject_packet["envelope"].get("route_scope") or ""),
        acceptance_criteria=list(subject_packet["envelope"].get("acceptance_criteria") or []),
        node_context_package_id=str(node_context.get("node_context_package_id") or ""),
        authorized_result_reads=[
            _authorized_read_for_result(
                ledger,
                target_result_id,
                allowed_roles=["reviewer"],
                purpose="subject_result_for_review",
                required_before_submit=True,
            )
        ]
        if target_result_id
        else None,
    )
    if repair_blocker_id:
        ledger["packets"][packet_id]["repair_blocker_id"] = repair_blocker_id
    return packet_id


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
    background_blocker = background_collaboration_blocker(ledger)
    if background_blocker:
        blockers.append(background_blocker)
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
    blockers.extend(_required_authorized_result_read_blockers(ledger, lease=lease, packet=packet))
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
        "flowguard_operator_lease_id": "",
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
        if blocker.get("status") in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
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
        if blocker.get("status") not in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
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
        _mark_blocked_packet_noncurrent_after_repair(ledger, blocker, validation_evidence_id)
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
    if high_standard_flow_required(ledger) or recursive_route_required(ledger):
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


def _supersede_stopped_blocker_pm_packet(ledger: dict[str, Any], blocker: Mapping[str, Any]) -> None:
    old_packet_id = str(blocker.get("pm_repair_packet_id") or "")
    old_packet = ledger.get("packets", {}).get(old_packet_id)
    if isinstance(old_packet, dict):
        old_packet["status"] = "superseded_after_repair"
        old_packet["superseded_reason"] = "stopped_blocker_recovery"
        old_packet["superseded_at"] = now_iso()


def _restore_pm_stopped_repair_target(ledger: dict[str, Any], blocker: Mapping[str, Any]) -> str:
    target_packet_id = str(blocker.get("repair_target_packet_id") or blocker.get("subject_packet_id") or "")
    if not target_packet_id:
        raise BlackBoxRuntimeError("reattach_required_recheck requires a stopped blocker repair target")
    target_packet = ledger.get("packets", {}).get(target_packet_id)
    if not isinstance(target_packet, dict):
        raise BlackBoxRuntimeError(f"reattach_required_recheck target packet does not exist: {target_packet_id}")
    if target_packet.get("status") != "pm_stopped":
        return str(target_packet.get("status") or "")
    previous_status = str(target_packet.get("pm_stop_previous_status") or "")
    if not previous_status:
        has_result = bool(
            target_packet.get("result_ids")
            or target_packet.get("accepted_result_id")
            or blocker.get("target_result_id")
        )
        if not has_result:
            raise BlackBoxRuntimeError("PM-stopped target is missing previous status and result evidence")
        previous_status = "result_submitted"
    target_packet["status"] = previous_status
    target_packet["pm_stop_restored_at"] = now_iso()
    _event(
        ledger,
        "pm_stopped_target_restored",
        blocker_id=str(blocker.get("blocker_id") or ""),
        packet_id=target_packet_id,
        restored_status=previous_status,
    )
    return previous_status


def _stopped_blocker_recheck_subject_packet_id(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> str:
    for field in ("repair_target_packet_id", "subject_packet_id"):
        packet_id = str(blocker.get(field) or "")
        packet = ledger.get("packets", {}).get(packet_id)
        if isinstance(packet, Mapping):
            return packet_id
    packet_id = str(blocker.get("packet_id") or "")
    packet = ledger.get("packets", {}).get(packet_id)
    envelope = packet.get("envelope", {}) if isinstance(packet, Mapping) else {}
    subject_id = str(envelope.get("subject_id") or "")
    if subject_id and isinstance(ledger.get("packets", {}).get(subject_id), Mapping):
        return subject_id
    if isinstance(packet, Mapping):
        return packet_id
    raise BlackBoxRuntimeError("reattach_required_recheck could not identify a subject packet")


def _stopped_blocker_target_result(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    subject_packet: Mapping[str, Any],
) -> Mapping[str, Any]:
    envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet.get("envelope"), Mapping) else {}
    result_ids = [str(item) for item in (subject_packet.get("result_ids") or []) if item]
    candidates = [
        str(blocker.get("target_result_id") or ""),
        str(subject_packet.get("accepted_result_id") or ""),
        result_ids[-1] if result_ids else "",
        str(envelope.get("target_result_id") or ""),
    ]
    for result_id in candidates:
        if result_id and isinstance(ledger.get("results", {}).get(result_id), Mapping):
            return ledger["results"][result_id]
    raise BlackBoxRuntimeError("reattach_required_recheck requires an existing target result")


def _stopped_blocker_recheck_kind(blocker: Mapping[str, Any]) -> str:
    blocker_class = str(blocker.get("blocker_class") or "")
    gate_kind = str(blocker.get("gate_kind") or "")
    recheck_role = str(blocker.get("required_recheck_role") or "")
    if blocker_class == "flowguard_failure" or gate_kind == "flowguard_check" or recheck_role == "flowguard_operator":
        return "flowguard_check"
    if gate_kind == "review" or recheck_role == "reviewer":
        return "review"
    raise BlackBoxRuntimeError("reattach_required_recheck supports FlowGuard or Reviewer semantic blockers only")


def _issue_required_recheck_packet_for_stopped_blocker(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    *,
    reason: str,
) -> tuple[str, str]:
    subject_packet_id = _stopped_blocker_recheck_subject_packet_id(ledger, blocker)
    subject_packet = _require(ledger["packets"], subject_packet_id, "subject packet")
    recheck_kind = _stopped_blocker_recheck_kind(blocker)
    repair_blocker_id = str(blocker.get("blocker_id") or "")
    recheck_reason = reason or "reattach_required_recheck"
    if recheck_kind == "flowguard_check":
        result = _stopped_blocker_target_result(ledger, blocker, subject_packet)
        fresh_packet_id = _ensure_flowguard_packet_for_task_result(
            ledger,
            subject_packet,
            result,
            force_new=True,
            repair_blocker_id=repair_blocker_id,
            recheck_reason=recheck_reason,
        )
        return fresh_packet_id, recheck_kind
    fresh_packet_id = _ensure_review_packet_for_task_result(
        ledger,
        subject_packet_id,
        force_new=True,
        repair_blocker_id=repair_blocker_id,
        recheck_reason=recheck_reason,
    )
    return fresh_packet_id, recheck_kind


def resolve_stopped_blocker(
    ledger: dict[str, Any],
    blocker_id: str,
    *,
    resolution: str,
    reason: str = "",
    user_requested: bool = False,
) -> dict[str, Any]:
    _assert_not_terminal_lifecycle(ledger)
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if blocker.get("status") != "stopped":
        raise BlackBoxRuntimeError("stopped-blocker recovery requires a stopped semantic blocker")
    if resolution == "reissue_pm_repair_decision":
        if not user_requested:
            raise BlackBoxRuntimeError("reissue_pm_repair_decision requires explicit user request")
        _supersede_stopped_blocker_pm_packet(ledger, blocker)
        blocker["status"] = "active"
        blocker["recovered_from_stop_at"] = now_iso()
        blocker["stopped_recovery_reason"] = reason
        blocker["stopped_recovery_user_requested"] = True
        blocker["pm_repair_packet_id"] = ""
        blocker["pm_repair_decision_id"] = ""
        fresh_packet_id = _ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
        _event(
            ledger,
            "stopped_blocker_resolved",
            blocker_id=blocker_id,
            resolution=resolution,
            fresh_packet_id=fresh_packet_id,
            user_requested=True,
        )
        return {
            "blocker_id": blocker_id,
            "resolution": resolution,
            "fresh_packet_id": fresh_packet_id,
            "status": blocker["status"],
            "user_requested": True,
        }
    if resolution == "reattach_required_recheck":
        if not user_requested:
            raise BlackBoxRuntimeError("reattach_required_recheck requires explicit user request")
        _supersede_stopped_blocker_pm_packet(ledger, blocker)
        restored_status = _restore_pm_stopped_repair_target(ledger, blocker)
        blocker["status"] = "awaiting_recheck"
        blocker["recovered_from_stop_at"] = now_iso()
        blocker["stopped_recovery_reason"] = reason
        blocker["stopped_recovery_user_requested"] = True
        blocker["pm_repair_packet_id"] = ""
        blocker["pm_repair_decision_id"] = ""
        blocker["reattached_required_recheck_at"] = now_iso()
        fresh_packet_id, recheck_kind = _issue_required_recheck_packet_for_stopped_blocker(
            ledger,
            blocker,
            reason=reason or "reattach_required_recheck",
        )
        _event(
            ledger,
            "stopped_blocker_resolved",
            blocker_id=blocker_id,
            resolution=resolution,
            fresh_packet_id=fresh_packet_id,
            recheck_kind=recheck_kind,
            restored_target_status=restored_status,
            user_requested=True,
        )
        return {
            "blocker_id": blocker_id,
            "resolution": resolution,
            "fresh_packet_id": fresh_packet_id,
            "recheck_kind": recheck_kind,
            "restored_target_status": restored_status,
            "status": blocker["status"],
            "user_requested": True,
        }
    if resolution in {"stop_run", "cancel_run"}:
        terminal_status = "stopped_by_user" if resolution == "stop_run" else "cancelled_by_user"
        terminal = record_terminal_lifecycle(
            ledger,
            terminal_status,
            reason=reason or f"stopped_blocker_{resolution}",
            actor="controller",
        )
        _event(
            ledger,
            "stopped_blocker_resolved",
            blocker_id=blocker_id,
            resolution=resolution,
            fresh_packet_id="",
        )
        return {
            "blocker_id": blocker_id,
            "resolution": resolution,
            "terminal_lifecycle": terminal,
            "status": str(blocker.get("status") or ""),
        }
    raise BlackBoxRuntimeError("unknown stopped-blocker recovery resolution")


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
    elif action_type == "issue_node_prework_flowguard_packet":
        result["packet_id"] = ensure_node_prework_flowguard_packet(ledger, action.subject_id)
    elif action_type == "issue_node_task_packet":
        result["packet_id"] = ensure_next_node_task_packet(ledger)
    elif action_type == "issue_parent_backward_replay_packet":
        result["packet_id"] = ensure_parent_backward_replay_packet(ledger, action.subject_id)
    elif action_type == "issue_flowguard_packet":
        subject_packet = _require(ledger["packets"], action.subject_id, "packet")
        result_ids = subject_packet.get("result_ids") or []
        if not result_ids:
            raise BlackBoxRuntimeError("issue_flowguard_packet requires a submitted packet result")
        subject_result = _require(ledger["results"], str(result_ids[-1]), "result")
        result["packet_id"] = _ensure_flowguard_packet_for_task_result(ledger, subject_packet, subject_result)
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
        next_action = _guard_next_action(ledger)
        if _guard_action_key(next_action) == _guard_action_key(action):
            return {
                "ok": True,
                "command": "run-until-wait",
                "boundary_class": "router_internal_blocked",
                "next_action": next_action.to_json(),
                "folded_applied_count": len(folded),
                "folded_applied_actions": folded,
                "blocked_reason": "router internal action repeated after application",
            }
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


def accepted_packet_lease_health(ledger: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, Mapping) or not packet.get("accepted_result_id"):
            continue
        if packet.get("status") in {"quarantined_after_route_mutation", "superseded_after_repair"}:
            continue
        details = _accepted_packet_repair_details(ledger, packet)
        active_lease_ids = _active_packet_lease_ids(ledger, str(packet.get("packet_id") or ""))
        original_lease_id = str(details.get("original_lease_id") or "")
        assigned_lease_id = str(details.get("assigned_lease_id") or "")
        stale_assigned = bool(original_lease_id and assigned_lease_id and assigned_lease_id != original_lease_id)
        if active_lease_ids or stale_assigned or packet.get("status") != "accepted":
            findings.append(
                {
                    "packet_id": str(packet.get("packet_id") or ""),
                    "accepted_result_id": str(packet.get("accepted_result_id") or ""),
                    "original_lease_id": original_lease_id,
                    "assigned_lease_id": assigned_lease_id,
                    "active_lease_ids": active_lease_ids,
                    "active_replacement_lease_ids": list(details.get("active_replacement_lease_ids") or []),
                    "stale_assigned_lease": stale_assigned,
                    "packet_status": str(packet.get("status") or ""),
                }
            )
    return {
        "schema_version": "black_box_flowpilot.accepted_packet_lease_health.v1",
        "ok": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "sealed_bodies_visible": False,
    }


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
                "decision_override": "reissue_or_replace_lease",
                "reason": "completed runner evidence is audit-only; formal current result must be reissued",
                "replacement_eligible": True,
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
    if action.action_type == "close_project":
        closure = ledger.get("closure") if isinstance(ledger.get("closure"), Mapping) else {}
        if closure.get("decision") == "blocked":
            return "control_plane_stuck", "final closure is blocked and requires explicit repair before another closure attempt"
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
    if classify_runtime_action(action) == "role_dispatch":
        return "process_next_action", action.reason
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
    accepted_health = accepted_packet_lease_health(ledger)
    blockers: list[str] = []
    for finding in accepted_health.get("findings", []):
        if not isinstance(finding, Mapping):
            continue
        blockers.append(f"accepted_packet_lease_health:{finding.get('packet_id', 'unknown')}")
    blockers.extend(_current_target_preflight_blockers(ledger, next_action))
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
        "accepted_packet_lease_health": accepted_health,
        "sealed_bodies_visible": False,
    }


def _current_target_preflight_blockers(
    ledger: Mapping[str, Any],
    next_action: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    subject_id = str(next_action.get("subject_id") or "")
    if subject_id and subject_id in ledger.get("packets", {}):
        violation = _packet_current_target_violation(ledger, subject_id)
        if violation:
            blockers.append(f"next_action_current_target:{subject_id}:{violation}")
        packet = ledger.get("packets", {}).get(subject_id)
        envelope = packet.get("envelope", {}) if isinstance(packet, Mapping) and isinstance(packet.get("envelope"), Mapping) else {}
        if (
            isinstance(packet, Mapping)
            and envelope.get("packet_kind", "task") == "pm_repair_decision"
            and packet.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES
        ):
            blockers.append(f"next_action_blocked_pm_repair_decision:{subject_id}")
    for blocker in ledger.get("active_blockers", {}).values():
        if not isinstance(blocker, Mapping):
            continue
        if blocker.get("status") not in (_ACTIVE_SEMANTIC_BLOCKER_STATUSES | {"awaiting_pm_decision_gate"}):
            continue
        blocker_id = str(blocker.get("blocker_id") or "")
        for field in ("packet_id", "subject_packet_id", "repair_target_packet_id"):
            packet_id = str(blocker.get(field) or "")
            if not packet_id:
                continue
            packet = ledger.get("packets", {}).get(packet_id)
            if not isinstance(packet, Mapping):
                continue
            violation = _packet_current_target_violation(ledger, packet_id, require_responsibility=False)
            if violation:
                blockers.append(f"active_blocker_current_target:{blocker_id}:{field}:{packet_id}:{violation}")
            if packet.get("status") == "result_submitted" and not packet.get("accepted_result_id"):
                blockers.append(f"active_blocker_result_submitted_target:{blocker_id}:{field}:{packet_id}")
    for gate in ledger.get("pm_decision_gates", {}).values():
        if not isinstance(gate, Mapping):
            continue
        if gate.get("status") not in {"awaiting_flowguard", "awaiting_review", "awaiting_system_closure", "pending"}:
            continue
        gate_id = str(gate.get("gate_id") or "")
        for field in ("source_packet_id",):
            packet_id = str(gate.get(field) or "")
            if not packet_id:
                continue
            violation = _packet_current_target_violation(ledger, packet_id, require_responsibility=False)
            if violation:
                blockers.append(f"pm_gate_current_target:{gate_id}:{field}:{packet_id}:{violation}")
    return blockers


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


def _packet_recovery_responsibility(ledger: Mapping[str, Any], packet_id: str) -> str:
    packet = ledger.get("packets", {}).get(packet_id)
    if isinstance(packet, Mapping):
        envelope = packet.get("envelope") if isinstance(packet.get("envelope"), Mapping) else {}
        responsibility = str(envelope.get("responsibility") or "")
        if responsibility:
            return responsibility
    return ""


def _foreground_recovery_command(
    ledger: Mapping[str, Any],
    guard: Mapping[str, Any],
) -> dict[str, Any]:
    next_action = guard.get("next_action") if isinstance(guard.get("next_action"), Mapping) else {}
    wait_subject = guard.get("wait_subject") if isinstance(guard.get("wait_subject"), Mapping) else {}
    wait_recovery = guard.get("wait_recovery") if isinstance(guard.get("wait_recovery"), Mapping) else {}
    decision = str(guard.get("decision") or "")
    packet_id = str(wait_subject.get("packet_id") or next_action.get("subject_id") or "")
    responsibility = str(next_action.get("responsibility") or "")
    if packet_id:
        responsibility = _packet_recovery_responsibility(ledger, packet_id)
    stale_lease_ids: list[str] = []
    repair = wait_recovery.get("repair") if isinstance(wait_recovery.get("repair"), Mapping) else {}
    if isinstance(repair, Mapping):
        stale_lease_ids.extend(str(item) for item in repair.get("active_replacement_lease_ids", []) if item)
    lease_id = str(wait_recovery.get("lease_id") or wait_subject.get("lease_id") or "")
    if lease_id and lease_id not in stale_lease_ids:
        stale_lease_ids.append(lease_id)

    if decision == "repair_assignment_race":
        command = "repair-accepted-packet"
        args = {"packet_id": packet_id}
        cli_args = ["repair-accepted-packet", "--packet-id", packet_id]
    elif packet_id and not responsibility:
        return {
            "schema_version": "black_box_flowpilot.recovery_command.v1",
            "command": "control-plane-blocker",
            "args": {"packet_id": packet_id, "reason": "missing current packet responsibility"},
            "cli": "",
            "packet_id": packet_id,
            "responsibility": "",
            "host_kind": "",
            "stale_lease_ids": stale_lease_ids,
            "cleanup_action": "hard_block_until_current_packet_responsibility_exists",
            "reason": "missing current packet responsibility",
            "sealed_bodies_visible": False,
        }
    else:
        command = "resolve-role-assignment"
        args = {
            "packet_id": packet_id,
            "responsibility": responsibility,
            "host_kind": "live",
        }
        cli_args = [
            "resolve-role-assignment",
            "--packet-id",
            packet_id,
            "--responsibility",
            responsibility,
            "--host-kind",
            "live",
        ]
    return {
        "schema_version": "black_box_flowpilot.recovery_command.v1",
        "command": command,
        "args": args,
        "cli": "python skills\\flowpilot\\assets\\flowpilot_new.py --root <project-root> --json " + " ".join(cli_args),
        "packet_id": packet_id,
        "responsibility": responsibility,
        "host_kind": str(args.get("host_kind", "")),
        "stale_lease_ids": stale_lease_ids,
        "cleanup_action": "resolve_assignment_then_commit_authorized_lease",
        "reason": str(guard.get("reason", "")),
        "sealed_bodies_visible": False,
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
        "unsupported_historical_monitor_required": False,
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
            "recommended_command": _foreground_recovery_command(ledger, guard_map),
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
    if high_standard_flow_required(ledger) or recursive_route_required(ledger):
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
        and packet.get("status") not in {"quarantined_after_route_mutation", "superseded_after_repair"}
    ]
    accepted_packets = [packet for packet in active_packets if packet.get("accepted_result_id")]
    if not accepted_packets:
        blockers.append("missing_accepted_packet_result")
    for packet in active_packets:
        if _packet_requires_current_acceptance(ledger, packet) and packet["status"] not in _NONCURRENT_PACKET_STATUSES:
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
        if packet["envelope"]["route_version"] == active_route and not _packet_is_noncurrent_for_routing(ledger, packet)
    ]
    for finding in accepted_packet_lease_health(ledger).get("findings", []):
        if isinstance(finding, Mapping) and finding.get("packet_id"):
            return RuntimeAction(
                "repair_accepted_packet",
                "accepted packet has stale assignment or active replacement lease",
                str(finding.get("packet_id")),
            )
    closure = ledger.get("closure") or {}
    if closure.get("decision") == "complete":
        return RuntimeAction("terminal_complete", "final backward chain is complete")
    if recursive_route_required(ledger) and ledger.get("route_nodes"):
        frontier = ledger.get("execution_frontier") or {}
        if (
            not frontier.get("active_node_id")
            and frontier.get("status") == "ready_for_final_closure"
            and closure.get("decision") != "blocked"
        ):
            return RuntimeAction("close_project", "all route nodes are resolved; final route-wide closure is required")
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
                "resolve_role_assignment",
                "packet role assignment must resolve before lease commit",
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
        if (
            packet["status"] in _CURRENT_PACKET_BLOCKING_STATUSES
            and packet["envelope"].get("packet_kind", "task") == "pm_repair_decision"
        ):
            blocker_id = str(packet["envelope"].get("subject_id") or packet.get("repair_blocker_id") or "")
            return RuntimeAction(
                "issue_pm_repair_decision_packet",
                "blocked PM repair decision packet is noncurrent and must be reissued",
                blocker_id,
                "pm",
            )

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
            if not _node_prework_flowguard_accepted(ledger, node_id):
                return RuntimeAction(
                    "issue_node_prework_flowguard_packet",
                    "frontier node requires pre-work FlowGuard before worker execution",
                    node_id,
                    "flowguard_operator",
                    node.get("modeled_target", REQUIRED_FLOWGUARD_TARGET),
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
        if (
            frontier.get("status") == "ready_for_final_closure"
            and not (ledger.get("closure") or {}).get("decision") == "complete"
            and (ledger.get("closure") or {}).get("decision") != "blocked"
        ):
            return RuntimeAction("close_project", "all route nodes are resolved; final route-wide closure is required")

    closure = ledger.get("closure") or {}
    if closure.get("decision") == "complete":
        return RuntimeAction("terminal_complete", "final backward chain is complete")
    return RuntimeAction("close_project", "all active packets are accepted")


def _packet_outcome_is_current_blocker(ledger: Mapping[str, Any], outcome: Mapping[str, Any]) -> bool:
    if outcome.get("blocking") is not True:
        return False
    outcome_id = str(outcome.get("outcome_id") or "")
    source_outcome = ledger.get("packet_outcomes", {}).get(outcome_id) if outcome_id else None
    if isinstance(source_outcome, Mapping):
        outcome = source_outcome
    result_id = str(outcome.get("result_id") or "")
    if result_id:
        for gate in ledger.get("pm_decision_gates", {}).values():
            if not isinstance(gate, Mapping):
                continue
            staged = gate.get("staged_effect") if isinstance(gate.get("staged_effect"), Mapping) else {}
            if (
                gate.get("status") == "applied"
                and str(gate.get("source_result_id") or "") == result_id
                and staged.get("status") == "committed"
            ):
                return False
    return True


def render_console(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Return public status without sealed task or result bodies."""

    progress_fraction = current_progress_fraction(ledger)
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
                "node_context_package_id": envelope.get("node_context_package_id", ""),
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
        "progress_fraction": progress_fraction,
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
        "unsupported_historical_monitor_required": False,
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
                "order_id": order.get("order_id", ""),
                "modeled_target": order.get("modeled_target", ""),
                "selected_skill": order.get("selected_skill", ""),
                "subject_id": order.get("subject_id", ""),
                "status": order.get("status", ""),
                "decision": order.get("decision", ""),
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
            if _blocker_current_effective(ledger, blocker) or blocker.get("status") == "awaiting_pm_decision_gate"
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
                "required_outputs": list(node.get("required_outputs", [])),
                "deliverable_check_count": len(node.get("deliverable_checks", []) or []),
                "repair_generation": node.get("repair_generation", 0),
                "packet_ids": list(node.get("packet_ids", [])),
                "node_acceptance_plan_id": node.get("node_acceptance_plan_id", ""),
                "node_context_package_id": node.get("node_context_package_id", ""),
                "node_context_package_current": _node_context_package_current(ledger, str(node.get("node_id", ""))),
                "prework_flowguard_order_id": node.get("prework_flowguard_order_id", ""),
                "prework_flowguard_packet_id": node.get("prework_flowguard_packet_id", ""),
                "prework_flowguard_current": _node_prework_flowguard_accepted(ledger, str(node.get("node_id", ""))),
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


def render_redacted_ledger_projection(ledger: Mapping[str, Any]) -> dict[str, Any]:
    projection = render_console(ledger)
    projection["projection"] = "redacted_ledger"
    projection["sealed_bodies_visible"] = False
    return projection


def render_compact_console(ledger: Mapping[str, Any]) -> dict[str, Any]:
    full = render_console(ledger)
    packets = list(full.get("packets", []))
    leases = list(full.get("leases", []))
    active_leases = [lease for lease in leases if isinstance(lease, Mapping) and lease.get("status") == "active"]
    active_packets = [
        packet
        for packet in packets
        if isinstance(packet, Mapping) and packet.get("status") not in {"accepted", "quarantined_after_route_mutation", "superseded_after_repair"}
    ]
    foreground = full.get("foreground_duty") if isinstance(full.get("foreground_duty"), Mapping) else {}
    compact_foreground = {
        "action": str(foreground.get("action", "")),
        "reason": str(foreground.get("reason", "")),
        "subject_id": str(foreground.get("subject_id", "")),
        "lifecycle_guard_decision": str(foreground.get("lifecycle_guard_decision", "")),
        "controller_stop_allowed": bool(foreground.get("controller_stop_allowed") is True),
        "final_return_preflight": _copy_jsonable(
            foreground.get("final_return_preflight") if isinstance(foreground.get("final_return_preflight"), Mapping) else {}
        ),
        "sealed_bodies_visible": False,
    }
    if isinstance(foreground.get("recovery"), Mapping):
        recovery = foreground["recovery"]
        compact_foreground["recovery"] = {
            "required": bool(recovery.get("required") is True),
            "decision": str(recovery.get("decision", "")),
            "reason": str(recovery.get("reason", "")),
            "recommended_command": _copy_jsonable(
                recovery.get("recommended_command") if isinstance(recovery.get("recommended_command"), Mapping) else {}
            ),
            "sealed_bodies_visible": False,
        }
    if isinstance(foreground.get("wait_patrol"), Mapping):
        compact_foreground["wait_patrol"] = _copy_jsonable(foreground["wait_patrol"])
    return {
        "schema_version": "black_box_flowpilot.compact_status.v1",
        "projection": "compact_controller_status",
        "project_id": full.get("project_id"),
        "goal": full.get("goal"),
        "lifecycle": full.get("lifecycle", {}),
        "route_stage": full.get("route_stage", ""),
        "active_route_version": full.get("active_route_version"),
        "source_generation": full.get("source_generation"),
        "next_action": full.get("next_action", {}),
        "lifecycle_guard": {
            "decision": str((full.get("lifecycle_guard") or {}).get("decision", "")),
            "controller_stop_allowed": bool((full.get("lifecycle_guard") or {}).get("controller_stop_allowed") is True),
            "reason": str((full.get("lifecycle_guard") or {}).get("reason", "")),
            "sealed_bodies_visible": False,
        },
        "foreground_duty": compact_foreground,
        "final_return_preflight": full.get("foreground_duty", {}).get("final_return_preflight", {}),
        "progress_fraction": full.get("progress_fraction", current_progress_fraction(ledger)),
        "counts": {
            "packets": len(packets),
            "active_packets": len(active_packets),
            "leases": len(leases),
            "active_leases": len(active_leases),
            "flowguard_orders": len(full.get("flowguard", [])),
            "active_blockers": len(full.get("active_blockers", [])),
            "progress_ended_nodes": int((full.get("progress_fraction") or {}).get("ended_nodes", 0) or 0),
            "progress_expanded_nodes": int((full.get("progress_fraction") or {}).get("expanded_nodes", 0) or 0),
        },
        "packets": packets,
        "leases": leases,
        "active_packets": active_packets,
        "active_leases": active_leases,
        "flowguard": full.get("flowguard", []),
        "validation_evidence": full.get("validation_evidence", []),
        "system_closures": full.get("system_closures", []),
        "packet_outcomes": full.get("packet_outcomes", []),
        "active_blockers": full.get("active_blockers", []),
        "blockers": sorted(
            {
                str(blocker.get("blocker_class") or blocker.get("blocker_id") or "")
                for blocker in full.get("active_blockers", [])
                if isinstance(blocker, Mapping)
            }
            | {
                str(outcome.get("blocker_class") or outcome.get("outcome_id") or "")
                for outcome in full.get("packet_outcomes", [])
                if isinstance(outcome, Mapping) and _packet_outcome_is_current_blocker(ledger, outcome)
            }
            | {
                str(blocker)
                for result in ledger.get("results", {}).values()
                if isinstance(result, Mapping) and str(result.get("status") or "") == "blocked"
                for blocker in result.get("mechanical_blockers", [])
            }
        ),
        "pm_decision_gates": full.get("pm_decision_gates", []),
        "orphan_evidence": full.get("orphan_evidence", []),
        "route_nodes": full.get("route_nodes", []),
        "high_standard_control_flow": full.get("high_standard_control_flow", {}),
        "execution_frontier": full.get("execution_frontier", {}),
        "final_route_wide_gate_ledger": full.get("final_route_wide_gate_ledger", {"decision": "not_built"}),
        "final_requirement_evidence_matrix": full.get("final_requirement_evidence_matrix", {"decision": "not_built"}),
        "closure": full.get("closure", {"decision": "not_attempted"}),
        "status_projection_authority": "display_only",
        "runtime_authority": full.get("runtime_authority", "current_run_ledger_lifecycle_guard_foreground_duty"),
        "sealed_bodies_visible": False,
        "body_policy": "default_status_is_body_free; authorized PM/reviewer body-open is a soft reading boundary",
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
    if any(
        isinstance(packet, Mapping)
        and _packet_requires_current_acceptance(ledger, packet)
        and packet.get("status") not in _NONCURRENT_PACKET_STATUSES
        for packet in ledger.get("packets", {}).values()
    ):
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
