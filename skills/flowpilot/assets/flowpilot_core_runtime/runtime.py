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
import os
from pathlib import Path
import re
import time
from typing import Any, Iterable, Mapping

try:  # pragma: no cover - direct module test harness path.
    from . import control_surface, packet_result_contracts, packet_stage_evidence_matrix, review_window_contracts
except ImportError:  # pragma: no cover
    import control_surface  # type: ignore
    import packet_result_contracts  # type: ignore
    import packet_stage_evidence_matrix  # type: ignore
    import review_window_contracts  # type: ignore


SCHEMA_VERSION = "black_box_flowpilot_runtime.v1"
ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION = "flowpilot.acceptance_item_registry.v1"
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
    "pm_flowguard_acceptance",
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
PM_FLOWGUARD_ACCEPTANCE_SCOPE = "pm_flowguard_acceptance"
TERMINAL_BACKWARD_REPLAY_SCOPE = "terminal_backward_replay"
TERMINAL_SUPPLEMENTAL_REPAIR_SCHEMA_VERSION = "black_box_flowpilot.terminal_supplemental_repair.v1"
SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION = "flowpilot.terminal_supplemental_repair_contract.v1"
PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION = "flowpilot.parent_repair_scope_contract.v1"
TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS = 3
ROUTE_NODE_KINDS = {"parent", "module", "leaf", "repair"}
NON_WORKER_DISPATCH_NODE_KINDS = {"parent", "module"}
ROUTE_DECOMPOSITION_REVIEW_CRITERIA = (
    "Each executable leaf has one small outcome, clear proof, clear dependency boundary, and clear failure boundary.",
    "Broad stage names such as research, design, implement, integrate, or validate are parent/module candidates when they hide multiple ordered work packages.",
    "Sibling leaves do not overlap scope or depend on a Worker choosing missing child ordering.",
    "Worker replanning, hidden subtasks, or worker-invented acceptance boundaries are route decomposition failures.",
    "Reviewer is the semantic decomposition quality gate and may block planning before route materialization.",
)
NODE_CONTEXT_PACKAGE_REQUIRED_LIST_FIELDS = {
    "acceptance_criteria",
    "relevant_references",
    "known_risks",
    "acceptance_item_projection",
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
    "pm_flowguard_acceptance_recorded": "flowguard",
    "repair_scope_replaced": "route",
    "parent_backward_replay_accepted": "route",
    "terminal_backward_replay_accepted": "closure",
    "terminal_supplemental_repair_contract_recorded": "repair",
    "terminal_supplemental_repair_exhausted": "repair",
    "final_requirement_evidence_matrix_built": "closure",
    "pm_disposition_recorded": "route",
    "semantic_blocker_superseded_by_route_mutation": "repair",
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
    "run_repair_rounds_exhausted": "lifecycle",
    "responsibility_lease_created": "lease",
    "role_memory_seed_recorded": "lease",
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
    "repair_loop_break_glass_required": "repair",
    "repair_loop_pm_repair_packets_superseded": "repair",
    "pm_repair_decision_recorded": "repair",
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
_REPAIR_LOOP_BREAK_GLASS_THRESHOLD = 5
_DEFAULT_WAIT_PATROL_SECONDS = 300
_WAIT_ACK_REMINDER_SECONDS = 300
_WAIT_ACK_REPLACE_SECONDS = 600
_WAIT_PROGRESS_REMINDER_SECONDS = 600
_WAIT_PROGRESS_REPLACE_SECONDS = 1800
_WAIT_PATROL_DECISIONS = {"wait_for_ack", "wait_for_result"}
_RECOVERY_DUTY_DECISIONS = {
    "reissue_or_replace_lease",
    "quarantine_stale_result",
    "recover_packet",
    "repair_assignment_race",
}
TERMINAL_LIFECYCLE_STATUSES = {"stopped_by_user", "cancelled_by_user", "repair_rounds_exhausted"}
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
    "issue_terminal_backward_replay_packet",
    "issue_flowguard_packet",
    "issue_review_packet",
    "issue_pm_repair_decision_packet",
    "issue_pm_disposition_packet",
    "issue_pm_flowguard_acceptance_packet",
    "close_project",
}
ROLE_DISPATCH_ACTION_TYPES = {"dispatch_current_role"}
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
            "ack_replace_seconds": _WAIT_ACK_REPLACE_SECONDS,
            "progress_reminder_seconds": _WAIT_PROGRESS_REMINDER_SECONDS,
            "progress_replace_seconds": _WAIT_PROGRESS_REPLACE_SECONDS,
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
        "acceptance_item_registry": None,
        "preplanning_discovery": None,
        "skill_standard_contract": None,
        "node_acceptance_plans": {},
        "node_context_packages": {},
        "parent_backward_replays": {},
        "terminal_backward_replays": {},
        "final_artifact_hygiene_reviews": {},
        "final_artifact_hygiene_findings": [],
        "terminal_supplemental_repair": {
            "schema_version": TERMINAL_SUPPLEMENTAL_REPAIR_SCHEMA_VERSION,
            "status": "inactive",
            "current_round": 0,
            "max_rounds": TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS,
            "active_contract_id": "",
            "exhausted_reason": "",
        },
        "supplemental_repair_contracts": {},
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


_LEDGER_READ_RETRY_ATTEMPTS = 5
_LEDGER_READ_RETRY_DELAY_SECONDS = 0.05


def save_ledger(ledger: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}-{datetime.now(timezone.utc).timestamp():.6f}")
    try:
        tmp_path.write_text(body, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def load_ledger(path: Path) -> dict[str, Any]:
    last_decode_error: json.JSONDecodeError | None = None
    for attempt in range(_LEDGER_READ_RETRY_ATTEMPTS):
        try:
            raw = path.read_text(encoding="utf-8")
            if not raw.strip():
                raise json.JSONDecodeError("empty runtime ledger", raw, 0)
            payload = json.loads(raw)
            break
        except json.JSONDecodeError as exc:
            last_decode_error = exc
            if attempt + 1 >= _LEDGER_READ_RETRY_ATTEMPTS:
                raise BlackBoxRuntimeError(f"invalid runtime ledger JSON at {path}: {exc}") from exc
            time.sleep(_LEDGER_READ_RETRY_DELAY_SECONDS)
    else:  # pragma: no cover - loop exits through break or exception.
        raise BlackBoxRuntimeError(f"invalid runtime ledger JSON at {path}: {last_decode_error}") from last_decode_error
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

    event_type_by_status = {
        "stopped_by_user": "run_stopped_by_user",
        "cancelled_by_user": "run_cancelled_by_user",
        "repair_rounds_exhausted": "run_repair_rounds_exhausted",
    }
    event_type = event_type_by_status[status]
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
    if old_version is not None:
        _supersede_repair_open_blockers_for_route_mutation(
            ledger,
            affected_packets=mutation["affected_packets"],
            mutation_id=str(mutation["mutation_id"]),
            disposition_id="",
            replacement_node_id="",
            new_route_version=new_version,
        )

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
        classification = str(row.get("classification") or "")
        if classification in {"hard_current", "high_standard_current"}:
            blocking.append(row)
    return blocking


def _acceptance_item_registry(ledger: Mapping[str, Any]) -> Mapping[str, Any]:
    registry = ledger.get("acceptance_item_registry")
    if isinstance(registry, Mapping):
        return registry
    contract = ledger.get("high_standard_contract")
    if isinstance(contract, Mapping) and isinstance(contract.get("acceptance_item_registry"), Mapping):
        return contract["acceptance_item_registry"]
    return {}


def _active_acceptance_items(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    registry = _acceptance_item_registry(ledger)
    rows = registry.get("items") if isinstance(registry, Mapping) else None
    if not isinstance(rows, list):
        return []
    active: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status") or "active")
        if status in {"active", "planned", "assigned"}:
            active.append(_copy_jsonable(row))
    return active


def _active_acceptance_item_ids(ledger: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("acceptance_item_id") or "")
        for item in _active_acceptance_items(ledger)
        if str(item.get("acceptance_item_id") or "")
    ]


def _node_acceptance_item_ids(node: Mapping[str, Any]) -> list[str]:
    return [str(item) for item in node.get("acceptance_item_ids") or [] if str(item)]


_TERMINAL_SUPPLEMENTAL_REPAIR_DECISIONS = {"repair_current_scope", "repair_parent_scope", "redesign_route"}
_SUPPLEMENTAL_REPAIR_GAP_KINDS = {
    "latent_high_standard_requirement",
    "missing_implementation",
    "missing_validation",
    "weak_evidence",
    "route_structure_gap",
    "terminal_replay_gap",
    "final_artifact_hygiene_gap",
}
_FINAL_ARTIFACT_HYGIENE_REQUIRED_CLASSIFICATIONS = {
    "current_goal_required_repair",
    "clean_delivery_required_repair",
}
_FINAL_ARTIFACT_HYGIENE_CLASSIFICATIONS = _FINAL_ARTIFACT_HYGIENE_REQUIRED_CLASSIFICATIONS | {
    "pm_decision_support",
    "future_contract_candidate",
}
_FINAL_ARTIFACT_HYGIENE_CATEGORIES = {
    "code_maintainability",
    "test_coverage",
    "model_coverage",
    "document_cleanup",
    "ui_polish",
    "artifact_lineage",
    "process_ledger_cleanup",
    "other",
}
_FINAL_ARTIFACT_HYGIENE_COVERED_DISPOSITIONS = {
    "clean",
    "repaired",
    "not_applicable",
    "waived_by_authority",
    "deferred_future_contract",
    "pm_suggestion_dispositioned",
}


def _string_list_field(value: Any, field_path: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise BlackBoxRuntimeError(f"{field_path} requires an explicit string list")
    rows = [str(item).strip() for item in value if str(item).strip()]
    if not allow_empty and not rows:
        raise BlackBoxRuntimeError(f"{field_path} requires a non-empty string list")
    if len(rows) != len(value):
        raise BlackBoxRuntimeError(f"{field_path} requires only non-empty strings")
    return rows


def _final_artifact_hygiene_required_findings(review: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    findings: list[Mapping[str, Any]] = []
    for field in ("current_goal_required_findings", "clean_delivery_required_findings"):
        values = review.get(field)
        if isinstance(values, list):
            findings.extend(item for item in values if isinstance(item, Mapping))
    return findings


def _final_artifact_hygiene_rows_from_review(
    review: Mapping[str, Any],
    *,
    source_result_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    field_to_classification = {
        "current_goal_required_findings": "current_goal_required_repair",
        "clean_delivery_required_findings": "clean_delivery_required_repair",
        "pm_decision_support_findings": "pm_decision_support",
        "future_contract_candidates": "future_contract_candidate",
    }
    for field, classification in field_to_classification.items():
        findings = review.get(field)
        if not isinstance(findings, list):
            continue
        for index, finding in enumerate(findings, start=1):
            if isinstance(finding, Mapping):
                finding_id = str(finding.get("finding_id") or f"{source_result_id}:{field}:{index}")
                artifact_family = str(finding.get("artifact_family") or finding.get("artifact_type") or "other")
                surface_path = str(finding.get("surface_path") or finding.get("path") or "")
                required_repair = str(finding.get("required_repair") or finding.get("finding") or "")
            else:
                finding_id = f"{source_result_id}:{field}:{index}"
                artifact_family = "other"
                surface_path = ""
                required_repair = str(finding)
            rows.append(
                {
                    "finding_id": finding_id,
                    "source_result_id": source_result_id,
                    "artifact_family": artifact_family,
                    "surface_path": surface_path,
                    "classification": classification,
                    "required_repair": required_repair,
                    "disposition": "",
                    "evidence_ids": [],
                    "owner_node_id": "",
                }
            )
    return rows


def _final_artifact_hygiene_finding_records(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings = ledger.get("final_artifact_hygiene_findings")
    if not isinstance(findings, list):
        return []
    return [dict(row) for row in findings if isinstance(row, Mapping)]


def _final_artifact_hygiene_closure_rows(ledger: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for finding in _final_artifact_hygiene_finding_records(ledger):
        finding_id = str(finding.get("finding_id") or "")
        if not finding_id:
            continue
        classification = str(finding.get("classification") or "")
        disposition = str(finding.get("disposition") or "")
        supplemental_contract_id = str(finding.get("supplemental_contract_id") or "")
        supplemental_repair_item_id = str(finding.get("supplemental_repair_item_id") or "")
        imported_into_repair = bool(supplemental_contract_id or supplemental_repair_item_id)
        unresolved_row = bool(finding.get("unresolved"))
        if classification in _FINAL_ARTIFACT_HYGIENE_REQUIRED_CLASSIFICATIONS:
            if disposition not in _FINAL_ARTIFACT_HYGIENE_COVERED_DISPOSITIONS:
                unresolved_row = True
            if disposition in {
                "deferred_future_contract",
                "pm_suggestion_dispositioned",
                "not_applicable",
            }:
                unresolved_row = True
        elif classification in {"pm_decision_support", "future_contract_candidate"}:
            if imported_into_repair and disposition not in _FINAL_ARTIFACT_HYGIENE_COVERED_DISPOSITIONS:
                unresolved_row = True
            if disposition == "blocked":
                unresolved_row = True
        if classification not in _FINAL_ARTIFACT_HYGIENE_CLASSIFICATIONS:
            unresolved_row = True
        if unresolved_row:
            unresolved.append(f"final_artifact_hygiene_unresolved:{finding_id}")
        seen.add(finding_id)
        rows.append(
            {
                "finding_id": finding_id,
                "artifact_family": str(finding.get("artifact_family") or "other"),
                "surface_path": str(finding.get("surface_path") or ""),
                "classification": classification,
                "owner_node_id": str(finding.get("owner_node_id") or ""),
                "supplemental_contract_id": supplemental_contract_id,
                "supplemental_repair_item_id": supplemental_repair_item_id,
                "evidence_ids": [str(item) for item in finding.get("evidence_ids") or []],
                "disposition": disposition,
                "unresolved": unresolved_row,
                "reason": str(finding.get("reason") or finding.get("required_repair") or ""),
            }
        )
    for repair_row, repair_unresolved in _supplemental_hygiene_repair_rows(ledger):
        finding_id = str(repair_row.get("finding_id") or "")
        if finding_id in seen:
            continue
        if repair_unresolved:
            unresolved.append(f"final_artifact_hygiene_unresolved:{finding_id}")
        rows.append(repair_row)
    return rows, unresolved


def _supplemental_hygiene_repair_rows(ledger: Mapping[str, Any]) -> list[tuple[dict[str, Any], bool]]:
    rows: list[tuple[dict[str, Any], bool]] = []
    supplemental_rows, _supplemental_unresolved = _supplemental_repair_closure_rows(ledger)
    for row in supplemental_rows:
        if str(row.get("gap_kind") or "") != "final_artifact_hygiene_gap":
            continue
        contract_id = str(row.get("contract_id") or "")
        repair_item_id = str(row.get("repair_item_id") or "")
        status = str(row.get("status") or "")
        finding_id = f"{contract_id}:{repair_item_id}"
        unresolved = status != "covered"
        rows.append(
            (
                {
                    "finding_id": finding_id,
                    "artifact_family": str(row.get("hygiene_category") or "other"),
                    "surface_path": "",
                    "classification": "clean_delivery_required_repair",
                    "owner_node_id": str(row.get("owner_repair_node_id") or ""),
                    "supplemental_contract_id": contract_id,
                    "supplemental_repair_item_id": repair_item_id,
                    "evidence_ids": [str(item) for item in row.get("evidence_ids") or []],
                    "disposition": "repaired" if status == "covered" else "blocked",
                    "unresolved": unresolved,
                    "reason": str(row.get("required_repair") or ""),
                },
                unresolved,
            )
        )
    return rows


def _terminal_supplemental_state(ledger: dict[str, Any]) -> dict[str, Any]:
    state = ledger.get("terminal_supplemental_repair")
    if state is None:
        state = {
            "schema_version": TERMINAL_SUPPLEMENTAL_REPAIR_SCHEMA_VERSION,
            "status": "inactive",
            "current_round": 0,
            "max_rounds": TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS,
            "active_contract_id": "",
            "exhausted_reason": "",
        }
        ledger["terminal_supplemental_repair"] = state
    if not isinstance(state, dict):
        raise BlackBoxRuntimeError("terminal_supplemental_repair must be a current structured object")
    if state.get("schema_version") != TERMINAL_SUPPLEMENTAL_REPAIR_SCHEMA_VERSION:
        raise BlackBoxRuntimeError("terminal_supplemental_repair has unsupported schema_version")
    if int(state.get("max_rounds", TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS)) != TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS:
        raise BlackBoxRuntimeError("terminal_supplemental_repair.max_rounds is runtime-owned and must be 3")
    return state


def _terminal_supplemental_state_view(ledger: Mapping[str, Any]) -> Mapping[str, Any]:
    state = ledger.get("terminal_supplemental_repair")
    return state if isinstance(state, Mapping) else {}


def _is_terminal_backward_replay_blocker(blocker: Mapping[str, Any]) -> bool:
    return str(blocker.get("route_scope") or "") == TERMINAL_BACKWARD_REPLAY_SCOPE


def _terminal_supplemental_repair_contract_minimal_shape(round_number: int = 1) -> dict[str, Any]:
    return {
        "schema_version": SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION,
        "contract_id": f"terminal-supplemental-repair-r{round_number}",
        "round_number": round_number,
        "original_contract_hash": "<current ledger contract_hash>",
        "terminal_blocker_id": "<terminal blocker id>",
        "terminal_gap_report_result_id": "<terminal reviewer result id>",
        "pm_reason": "Why this repair is required for the original user goal.",
        "repair_items": [
            {
                "repair_item_id": f"terminal-gap-r{round_number}-item-1",
                "gap_kind": "final_artifact_hygiene_gap",
                "hygiene_category": "artifact_lineage",
                "original_goal_link": "Which original user-goal obligation this item closes.",
                "reviewer_gap": "Concrete terminal Reviewer gap.",
                "required_repair": "Concrete repair work PM is adding.",
                "owner_repair_node_id": "repair-current-scope-leaf",
                "acceptance_item_ids": ["acc-001"],
                "required_evidence": ["fresh implementation evidence", "fresh validation evidence"],
                "status": "open",
            }
        ],
    }


def _terminal_supplemental_repair_contract_current_shape(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    *,
    round_number: int,
) -> dict[str, Any]:
    shape = _terminal_supplemental_repair_contract_minimal_shape(round_number)
    shape["original_contract_hash"] = str(ledger.get("contract_hash") or "")
    shape["terminal_blocker_id"] = str(blocker.get("blocker_id") or "")
    shape["terminal_gap_report_result_id"] = str(blocker.get("result_id") or "")
    shape["pm_reason"] = "Current terminal backward replay found a gap in the original user-goal closure."
    if shape.get("repair_items"):
        first_item = shape["repair_items"][0]
        if isinstance(first_item, dict):
            first_item["original_goal_link"] = "Current frozen acceptance contract."
            first_item["reviewer_gap"] = str(blocker.get("recommended_resolution") or "Terminal replay blocker.")
            first_item["required_repair"] = "Repair the delivered product and rerun terminal backward replay."
    return shape


def _project_supplemental_repair_ids_onto_route_plan(
    route_plan: Mapping[str, Any],
    supplemental_contract: Mapping[str, Any],
) -> dict[str, Any]:
    projected = _copy_jsonable(route_plan)
    contract_id = str(supplemental_contract.get("contract_id") or "")
    repair_items = supplemental_contract.get("repair_items")
    first_item = repair_items[0] if isinstance(repair_items, list) and repair_items else {}
    repair_item_id = str(first_item.get("repair_item_id") or "") if isinstance(first_item, Mapping) else ""
    owner_node_id = str(first_item.get("owner_repair_node_id") or "") if isinstance(first_item, Mapping) else ""
    nodes = projected.get("nodes") if isinstance(projected, dict) else None
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node["supplemental_repair_contract_ids"] = [contract_id] if contract_id else []
            if str(node.get("node_id") or "") == owner_node_id:
                node["supplemental_repair_item_ids"] = [repair_item_id] if repair_item_id else []
            else:
                node.setdefault("supplemental_repair_item_ids", [])
    return projected


def _terminal_supplemental_repair_required(
    ledger: Mapping[str, Any] | None,
    packet: Mapping[str, Any],
    decision: str,
) -> bool:
    if decision not in _TERMINAL_SUPPLEMENTAL_REPAIR_DECISIONS or ledger is None:
        return False
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    blocker_id = str(envelope.get("subject_id") or "")
    blocker = ledger.get("active_blockers", {}).get(blocker_id) if isinstance(ledger.get("active_blockers"), Mapping) else None
    return isinstance(blocker, Mapping) and _is_terminal_backward_replay_blocker(blocker)


def _parse_terminal_supplemental_repair_contract_payload(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    decision: str,
    route_plan: Mapping[str, Any] | None,
) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    blocker_id = str(envelope.get("subject_id") or "")
    blocker = ledger.get("active_blockers", {}).get(blocker_id) if isinstance(ledger.get("active_blockers"), Mapping) else None
    if not isinstance(blocker, Mapping) or not _is_terminal_backward_replay_blocker(blocker):
        raise BlackBoxRuntimeError("supplemental_repair_contract is only valid for terminal backward replay blockers")
    if decision not in _TERMINAL_SUPPLEMENTAL_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("terminal supplemental repair contract requires a repair decision")
    raw = payload.get("supplemental_repair_contract")
    if not isinstance(raw, Mapping):
        raise BlackBoxRuntimeError("terminal repair decision requires supplemental_repair_contract")
    forbidden = [
        field
        for field in ("supplemental_contract", "repair_contract", "terminal_repair_contract")
        if field in payload
    ]
    if forbidden:
        raise BlackBoxRuntimeError(
            "terminal repair decision uses unsupported supplemental contract alias field(s): "
            + ", ".join(forbidden)
        )
    if raw.get("schema_version") != SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION:
        raise BlackBoxRuntimeError(
            f"supplemental_repair_contract.schema_version must be {SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION}"
        )
    contract_id = str(raw.get("contract_id") or "").strip()
    if not contract_id:
        raise BlackBoxRuntimeError("supplemental_repair_contract requires contract_id")
    if contract_id in ledger.get("supplemental_repair_contracts", {}):
        raise BlackBoxRuntimeError(f"supplemental_repair_contract.contract_id already exists: {contract_id}")
    state = _terminal_supplemental_state_view(ledger)
    current_round = int(state.get("current_round", 0) or 0)
    max_rounds = int(state.get("max_rounds", TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS) or TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS)
    if current_round >= max_rounds:
        raise BlackBoxRuntimeError("terminal supplemental repair rounds are exhausted")
    round_number = raw.get("round_number")
    if not isinstance(round_number, int) or round_number != current_round + 1:
        raise BlackBoxRuntimeError("supplemental_repair_contract.round_number must be the next terminal repair round")
    if round_number > TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS:
        raise BlackBoxRuntimeError("supplemental_repair_contract.round_number exceeds runtime max_rounds=3")
    if str(raw.get("original_contract_hash") or "") != str(ledger.get("contract_hash") or ""):
        raise BlackBoxRuntimeError("supplemental_repair_contract.original_contract_hash must cite the frozen contract")
    if str(raw.get("terminal_blocker_id") or "") != blocker_id:
        raise BlackBoxRuntimeError("supplemental_repair_contract.terminal_blocker_id must match the current blocker")
    if str(raw.get("terminal_gap_report_result_id") or "") != str(blocker.get("result_id") or ""):
        raise BlackBoxRuntimeError("supplemental_repair_contract.terminal_gap_report_result_id must cite the Reviewer blocker result")
    if not str(raw.get("pm_reason") or "").strip():
        raise BlackBoxRuntimeError("supplemental_repair_contract requires pm_reason")
    repair_items = raw.get("repair_items")
    if not isinstance(repair_items, list) or not repair_items:
        raise BlackBoxRuntimeError("supplemental_repair_contract requires non-empty repair_items")
    route_plan_node_ids: set[str] = set()
    route_plan_nodes_by_id: dict[str, Mapping[str, Any]] = {}
    if decision == "redesign_route":
        if not isinstance(route_plan, Mapping):
            raise BlackBoxRuntimeError("terminal supplemental repair redesign_route requires route_plan")
        normalized_route_nodes = _normalize_strict_route_plan_nodes(route_plan)
        route_plan_node_ids = {str(node.get("node_id") or "") for node in normalized_route_nodes}
        route_plan_nodes_by_id = {str(node.get("node_id") or ""): node for node in normalized_route_nodes}
    existing_node_ids = set(str(node_id) for node_id in ledger.get("route_nodes", {}))
    active_acceptance_ids = set(_active_acceptance_item_ids(ledger))
    normalized_items: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    for index, item in enumerate(repair_items, start=1):
        if not isinstance(item, Mapping):
            raise BlackBoxRuntimeError(f"supplemental_repair_contract.repair_items[{index}] must be an object")
        item_id = str(item.get("repair_item_id") or "").strip()
        if not item_id:
            raise BlackBoxRuntimeError(f"supplemental_repair_contract.repair_items[{index}] requires repair_item_id")
        if item_id in seen_item_ids:
            raise BlackBoxRuntimeError(f"supplemental_repair_contract duplicate repair_item_id: {item_id}")
        seen_item_ids.add(item_id)
        gap_kind = str(item.get("gap_kind") or "").strip()
        if gap_kind not in _SUPPLEMENTAL_REPAIR_GAP_KINDS:
            raise BlackBoxRuntimeError(
                f"supplemental_repair_contract.repair_items[{index}].gap_kind must be one of "
                + ", ".join(sorted(_SUPPLEMENTAL_REPAIR_GAP_KINDS))
            )
        hygiene_category = str(item.get("hygiene_category") or "").strip()
        if gap_kind == "final_artifact_hygiene_gap":
            if hygiene_category not in _FINAL_ARTIFACT_HYGIENE_CATEGORIES:
                raise BlackBoxRuntimeError(
                    f"supplemental_repair_contract.repair_items[{index}].hygiene_category must be one of "
                    + ", ".join(sorted(_FINAL_ARTIFACT_HYGIENE_CATEGORIES))
                )
        elif hygiene_category and hygiene_category not in _FINAL_ARTIFACT_HYGIENE_CATEGORIES:
            raise BlackBoxRuntimeError(
                f"supplemental_repair_contract.repair_items[{index}].hygiene_category is unsupported"
            )
        owner_node_id = str(item.get("owner_repair_node_id") or "").strip()
        if not owner_node_id:
            raise BlackBoxRuntimeError(f"supplemental_repair_contract.repair_items[{index}] requires owner_repair_node_id")
        if decision == "redesign_route":
            if owner_node_id not in route_plan_node_ids:
                raise BlackBoxRuntimeError(
                    f"supplemental repair item {item_id} owner_repair_node_id is not present in route_plan"
                )
            node_spec = route_plan_nodes_by_id.get(owner_node_id, {})
            if contract_id not in [str(row) for row in node_spec.get("supplemental_repair_contract_ids") or []]:
                raise BlackBoxRuntimeError(
                    f"supplemental repair item {item_id} owner node must project supplemental_repair_contract_ids"
                )
            if item_id not in [str(row) for row in node_spec.get("supplemental_repair_item_ids") or []]:
                raise BlackBoxRuntimeError(
                    f"supplemental repair item {item_id} owner node must project supplemental_repair_item_ids"
                )
        elif owner_node_id not in existing_node_ids:
            raise BlackBoxRuntimeError(
                f"supplemental repair item {item_id} owner_repair_node_id must name a current route node"
            )
        acceptance_item_ids = _string_list_field(
            item.get("acceptance_item_ids"),
            f"supplemental_repair_contract.repair_items[{index}].acceptance_item_ids",
        )
        unknown_items = sorted(set(acceptance_item_ids) - active_acceptance_ids)
        if unknown_items:
            raise BlackBoxRuntimeError(
                f"supplemental repair item {item_id} references unknown acceptance item(s): "
                + ", ".join(unknown_items)
            )
        normalized_items.append(
            {
                "repair_item_id": item_id,
                "gap_kind": gap_kind,
                "hygiene_category": hygiene_category,
                "original_goal_link": str(item.get("original_goal_link") or "").strip(),
                "reviewer_gap": str(item.get("reviewer_gap") or "").strip(),
                "required_repair": str(item.get("required_repair") or "").strip(),
                "owner_repair_node_id": owner_node_id,
                "acceptance_item_ids": acceptance_item_ids,
                "required_evidence": _string_list_field(
                    item.get("required_evidence"),
                    f"supplemental_repair_contract.repair_items[{index}].required_evidence",
                ),
                "status": str(item.get("status") or "").strip(),
            }
        )
        for field in ("original_goal_link", "reviewer_gap", "required_repair", "status"):
            if not normalized_items[-1][field]:
                raise BlackBoxRuntimeError(f"supplemental_repair_contract.repair_items[{index}] requires {field}")
        if normalized_items[-1]["status"] != "open":
            raise BlackBoxRuntimeError(f"supplemental_repair_contract.repair_items[{index}].status must be open")
    return {
        "schema_version": SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION,
        "contract_id": contract_id,
        "status": "active",
        "round_number": round_number,
        "original_contract_hash": str(raw.get("original_contract_hash") or ""),
        "terminal_blocker_id": blocker_id,
        "terminal_gap_report_result_id": str(raw.get("terminal_gap_report_result_id") or ""),
        "pm_reason": str(raw.get("pm_reason") or "").strip(),
        "repair_items": normalized_items,
        "repair_node_ids": sorted({str(item["owner_repair_node_id"]) for item in normalized_items}),
        "created_at": now_iso(),
    }


def _record_terminal_supplemental_repair_contract(
    ledger: dict[str, Any],
    *,
    contract: Mapping[str, Any],
    decision_id: str,
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    state = _terminal_supplemental_state(ledger)
    round_number = int(contract.get("round_number", 0) or 0)
    contract_id = str(contract.get("contract_id") or "")
    record = _copy_jsonable(contract)
    record["pm_repair_decision_id"] = decision_id
    record["source_packet_id"] = str(packet.get("packet_id") or "")
    record["source_result_id"] = str(result.get("result_id") or "")
    ledger.setdefault("supplemental_repair_contracts", {})[contract_id] = record
    state["status"] = "active"
    state["current_round"] = round_number
    state["active_contract_id"] = contract_id
    state["exhausted_reason"] = ""
    ledger["terminal_backward_replay_id"] = ""
    ledger["closure_confirmed_by_backward_replay"] = False
    _event(
        ledger,
        "terminal_supplemental_repair_contract_recorded",
        contract_id=contract_id,
        round_number=round_number,
        decision_id=decision_id,
    )


def _terminal_supplemental_rounds_exhausted(ledger: Mapping[str, Any]) -> bool:
    state = _terminal_supplemental_state_view(ledger)
    if str(state.get("status") or "") == "repair_rounds_exhausted":
        return True
    return int(state.get("current_round", 0) or 0) >= int(
        state.get("max_rounds", TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS) or TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS
    )


def _record_terminal_supplemental_repair_exhausted(
    ledger: dict[str, Any],
    blocker: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    state = _terminal_supplemental_state(ledger)
    reason = (
        "terminal supplemental repair reached the three-round hard cap; "
        f"latest blocker {blocker.get('blocker_id', '')} still blocks closure"
    )
    state["status"] = "repair_rounds_exhausted"
    state["exhausted_reason"] = reason
    state["exhausted_blocker_id"] = str(blocker.get("blocker_id") or "")
    state["exhausted_result_id"] = str(result.get("result_id") or "")
    state["exhausted_at"] = now_iso()
    _event(
        ledger,
        "terminal_supplemental_repair_exhausted",
        blocker_id=str(blocker.get("blocker_id") or ""),
        current_round=int(state.get("current_round", 0) or 0),
        max_rounds=int(state.get("max_rounds", TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS) or TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS),
    )
    record_terminal_lifecycle(ledger, "repair_rounds_exhausted", reason=reason, actor="runtime")


def _required_skill_obligations(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = ledger.get("skill_standard_contract")
    if not isinstance(contract, dict):
        return []
    rows = contract.get("obligations")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("classification") or "") in {"required", "conditional_required"}
    ]


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
                    "future_suggestion, or rejected_expansion. Also compile acceptance_item_registry.items "
                    "from explicit user requirements, implicit user commitments, PM-added high standards, "
                    "low-quality-success risks, target-realization obligations, child-skill standards, and "
                    "FlowGuard obligations. The registry is the current-run acceptance table and this packet "
                    "defines its future closure policy. Do not claim Worker, target-product, route-node, or "
                    "final backward replay evidence already exists unless it is actually current. Every active "
                    "item must later be assigned to route nodes, checked by Reviewer/FlowGuard gates, and "
                    "closed by final backward replay."
                ),
                "required_output": {
                    "requirements": [
                        {
                            "requirement_id": "hsr-001",
                            "classification": "hard_current",
                            "summary": "Current run must complete the user's actual requested outcome.",
                            "source_user_intent": "sealed_startup_intake",
                            "closure_rule": (
                                "Future closure requires direct current evidence or explicit waiver; "
                                "this preplanning packet only defines the rule."
                            ),
                        }
                    ],
                    "acceptance_item_registry": {
                        "schema_version": ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION,
                        "items": [
                            {
                                "acceptance_item_id": "acc-user-001",
                                "source_type": "user_explicit",
                                "source_requirement_ids": ["hsr-001"],
                                "summary": "Current run must complete the user's actual requested outcome.",
                                "quality_floor": "high_quality_required",
                                "future_evidence_rule": (
                                    "Future closure requires direct current evidence or explicit waiver; "
                                    "not required in this preplanning contract-definition packet."
                                ),
                                "status": "active",
                            },
                            {
                                "acceptance_item_id": "acc-pm-001",
                                "source_type": "pm_high_standard",
                                "source_requirement_ids": ["hsr-001"],
                                "summary": "PM must hold the result to the highest reasonable current-run quality bar.",
                                "quality_floor": "high_quality_required",
                                "future_evidence_rule": "Proof of depth plus Reviewer/FlowGuard closure where applicable.",
                                "status": "active",
                            }
                        ]
                    }
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
                    "Record current-run material discovery and candidate skill inventory before route planning. "
                    "Skill inventory is planning input; material summaries are navigation, not acceptance proof."
                ),
                "required_output": {
                    "decision": "pass",
                    "material_sources": ["sealed_startup_intake"],
                    "material_sufficiency": "sufficient_for_route_planning",
                    "candidate_skill_inventory": ["flowguard-development-process-flow"],
                },
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
                "required_output": {
                    "decision": "pass",
                    "obligations": [
                        {
                            "obligation_id": "skill-std-001",
                            "skill": "flowguard-development-process-flow",
                            "classification": "required",
                            "role_use": "flowguard_operator",
                            "use_context": "node_validation",
                            "evidence_rule": "current-run FlowGuard work order/report evidence",
                        }
                    ],
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
            "instruction": (
                "Open the sealed startup body through the current-run packet boundary and plan the project route. "
                "Use one canonical executable route tree. Do not add broad per-node explanation fields just to satisfy the prompt; "
                "use the existing strict route fields plus acceptance criteria, outputs, and checks. The route will not materialize "
                "until FlowGuard Operator and Reviewer can see that every executable leaf is small, single-purpose, non-overlapping, "
                "and worker-ready without Worker replanning."
            ),
            "startup_intake_ref": _startup_body_ref_from_ledger(ledger),
            "high_standard_contract_id": (ledger.get("high_standard_contract") or {}).get("contract_id", ""),
            "discovery_id": (ledger.get("preplanning_discovery") or {}).get("discovery_id", ""),
            "skill_standard_contract_id": (ledger.get("skill_standard_contract") or {}).get("contract_id", ""),
            "route_decomposition_review_criteria": list(ROUTE_DECOMPOSITION_REVIEW_CRITERIA),
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
            "PM route plan is decomposed into small worker-ready leaves or parent/module nodes with ordered children.",
            "Reviewer may block planning before materialization if leaves are broad, overlapping, or require Worker replanning.",
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
    _validate_route_plan_acceptance_item_coverage(ledger, node_specs)

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
            "acceptance_item_ids": [str(item) for item in spec.get("acceptance_item_ids") or []],
            "skill_standard_obligation_ids": [str(item) for item in spec.get("skill_standard_obligation_ids") or []],
            "supplemental_repair_contract_ids": [str(item) for item in spec.get("supplemental_repair_contract_ids") or []],
            "supplemental_repair_item_ids": [str(item) for item in spec.get("supplemental_repair_item_ids") or []],
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
    blocker = _node_worker_dispatch_blocker(ledger, node_id, node)
    if blocker:
        raise BlackBoxRuntimeError(blocker)
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
                "acceptance_item_ids": _node_acceptance_item_ids(node),
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


def _optional_string_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _parent_repair_scope_contract_minimal_shape(source_parent_node_id: str = "") -> dict[str, Any]:
    parent_id = str(source_parent_node_id or "parent-node-id").strip()
    return {
        "schema_version": PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION,
        "source_parent_node_id": parent_id,
        "inherit_existing_children": True,
        "repair_child_specs": [
            {
                "node_id": f"{parent_id}-repair-child-001",
                "title": "Repair parent scope blocker",
                "purpose": "Repair the blocked parent-scope obligation with current evidence.",
                "required_evidence": ["current repair child result", "parent replay authorization proof"],
                "acceptance_criteria": ["Current repair child evidence closes the parent-scope blocker."],
            }
        ],
    }


def _parse_parent_repair_scope_contract_payload(
    payload: Mapping[str, Any],
    *,
    expected_parent_node_id: str = "",
) -> dict[str, Any]:
    raw_contract = payload.get("repair_parent_scope_contract")
    if not isinstance(raw_contract, Mapping):
        raise BlackBoxRuntimeError("repair_parent_scope requires repair_parent_scope_contract")
    source_parent_node_id = str(raw_contract.get("source_parent_node_id") or expected_parent_node_id).strip()
    if not source_parent_node_id:
        raise BlackBoxRuntimeError("repair_parent_scope_contract requires source_parent_node_id")
    if expected_parent_node_id and source_parent_node_id != expected_parent_node_id:
        raise BlackBoxRuntimeError("repair_parent_scope_contract source_parent_node_id must match the runtime parent node")
    if raw_contract.get("inherit_existing_children") is not True:
        raise BlackBoxRuntimeError("repair_parent_scope_contract requires inherit_existing_children=true")
    raw_specs = raw_contract.get("repair_child_specs")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise BlackBoxRuntimeError("repair_parent_scope_contract requires non-empty repair_child_specs")
    specs: list[dict[str, Any]] = []
    seen_child_ids: set[str] = set()
    for index, raw_spec in enumerate(raw_specs, start=1):
        if not isinstance(raw_spec, Mapping):
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs entries must be objects")
        child_id = str(raw_spec.get("node_id") or "").strip()
        if not child_id:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].node_id is required")
        if child_id in seen_child_ids:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].node_id must be unique")
        seen_child_ids.add(child_id)
        if child_id == source_parent_node_id:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair child cannot reuse the source parent node id")
        purpose = str(raw_spec.get("purpose") or "").strip()
        if not purpose:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].purpose is required")
        required_evidence = _optional_string_items(raw_spec.get("required_evidence"))
        if not required_evidence:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].required_evidence is required")
        node_kind = str(raw_spec.get("node_kind") or "repair").strip()
        if node_kind not in {"leaf", "repair"}:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].node_kind must be leaf or repair")
        if raw_spec.get("child_node_ids"):
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair child specs must not declare child_node_ids")
        title = str(raw_spec.get("title") or purpose or f"Repair parent scope child {index}").strip()
        acceptance_criteria = _optional_string_items(raw_spec.get("acceptance_criteria")) or [
            f"Current repair child proves: {purpose}"
        ]
        specs.append(
            {
                "node_id": child_id,
                "title": title,
                "node_kind": node_kind,
                "purpose": purpose,
                "required_evidence": required_evidence,
                "acceptance_criteria": acceptance_criteria,
                "responsibility": str(raw_spec.get("responsibility") or "worker").strip() or "worker",
                "modeled_target": str(raw_spec.get("modeled_target") or REQUIRED_FLOWGUARD_TARGET).strip()
                or REQUIRED_FLOWGUARD_TARGET,
                "acceptance_item_ids": _optional_string_items(raw_spec.get("acceptance_item_ids")),
                "high_standard_requirement_ids": _optional_string_items(raw_spec.get("high_standard_requirement_ids")),
                "skill_standard_obligation_ids": _optional_string_items(raw_spec.get("skill_standard_obligation_ids")),
            }
        )
    return {
        "schema_version": PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION,
        "source_parent_node_id": source_parent_node_id,
        "inherit_existing_children": True,
        "repair_child_specs": specs,
    }


def _parent_repair_scope_contract_for_decision(
    ledger: Mapping[str, Any],
    decision_row: Mapping[str, Any],
) -> dict[str, Any] | None:
    contract_id = str(decision_row.get("parent_repair_scope_contract_id") or "")
    contract = ledger.get("parent_repair_scope_contracts", {}).get(contract_id) if contract_id else None
    if isinstance(contract, Mapping):
        return _copy_jsonable(contract)
    embedded = decision_row.get("repair_parent_scope_contract")
    if isinstance(embedded, Mapping):
        return _copy_jsonable(embedded)
    return None


def _accepted_result_ids_for_route_nodes(ledger: Mapping[str, Any], node_ids: list[str]) -> list[str]:
    accepted: list[str] = []
    seen: set[str] = set()
    for node_id in node_ids:
        node = ledger.get("route_nodes", {}).get(node_id)
        result_id = str(node.get("accepted_result_id") or "") if isinstance(node, Mapping) else ""
        if result_id and result_id not in seen:
            accepted.append(result_id)
            seen.add(result_id)
        for packet in ledger.get("packets", {}).values():
            envelope = packet.get("envelope", {}) if isinstance(packet, Mapping) and isinstance(packet.get("envelope"), Mapping) else {}
            if str(envelope.get("route_node_id") or "") != node_id:
                continue
            result_id = str(packet.get("accepted_result_id") or "")
            if result_id and result_id not in seen:
                accepted.append(result_id)
                seen.add(result_id)
    return accepted


def _parent_repair_node_is_replacement(node: Mapping[str, Any]) -> bool:
    return bool(node.get("parent_repair_scope_contract_id") or node.get("repair_parent_scope_contract"))


def _parent_repair_node_current_child_violation(
    ledger: Mapping[str, Any],
    node_id: str,
    node: Mapping[str, Any],
    *,
    require_accepted_child_results: bool = False,
) -> str:
    if not _parent_repair_node_is_replacement(node):
        return ""
    child_ids = _route_node_child_ids(node)
    if not child_ids:
        return f"parent repair node {node_id} requires active repair child_node_ids; inherited children are history only"
    for child_id in child_ids:
        child = ledger.get("route_nodes", {}).get(child_id)
        if not isinstance(child, Mapping):
            return f"parent repair node {node_id} references missing active repair child {child_id}"
        if str(child.get("parent_node_id") or "") != node_id:
            return f"parent repair child {child_id} must point back to replacement parent {node_id}"
    if require_accepted_child_results:
        accepted_result_ids = _accepted_result_ids_for_route_nodes(ledger, child_ids)
        if not accepted_result_ids:
            return f"parent repair node {node_id} requires current repair child result before parent backward replay"
    return ""


def _parent_repair_subject_artifacts(
    ledger: Mapping[str, Any],
    node_id: str,
    *,
    subject_packet: Mapping[str, Any] | None = None,
    target_result: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    node = ledger.get("route_nodes", {}).get(node_id)
    if not isinstance(node, Mapping) or not _parent_repair_node_is_replacement(node):
        return []
    artifacts: list[dict[str, str]] = []
    contract_id = str(node.get("parent_repair_scope_contract_id") or "")
    if contract_id:
        artifacts.append(
            {
                "artifact_id": f"parent_repair_scope_contract:{contract_id}",
                "artifact_type": "parent_repair_scope_contract",
                "description": "PM parent repair contract with active repair_child_specs.",
            }
        )
    artifacts.append(
        {
            "artifact_id": f"replacement_route_node:{node_id}",
            "artifact_type": "replacement_route_node",
            "description": "Replacement parent route node; child_node_ids are current repair children.",
        }
    )
    for child_id in _route_node_child_ids(node):
        artifacts.append(
            {
                "artifact_id": f"active_repair_child_node:{child_id}",
                "artifact_type": "active_repair_child_node",
                "description": "Current repair child node that must produce fresh evidence.",
            }
        )
    for child_id in node.get("inherited_child_node_ids") or []:
        if str(child_id):
            artifacts.append(
                {
                    "artifact_id": f"inherited_child_node:{child_id}",
                    "artifact_type": "inherited_child_node_history",
                    "description": "Old child node inherited as history only, not current closure evidence.",
                }
            )
    for result_id in node.get("inherited_accepted_result_ids") or []:
        if str(result_id):
            artifacts.append(
                {
                    "artifact_id": f"inherited_accepted_result:{result_id}",
                    "artifact_type": "inherited_accepted_result_history",
                    "description": "Old accepted result inherited as history only, not current closure evidence.",
                }
            )
    plan_id = str(node.get("node_acceptance_plan_id") or "")
    if plan_id:
        artifacts.append(
            {
                "artifact_id": f"node_acceptance_plan:{plan_id}",
                "artifact_type": "node_acceptance_plan",
                "description": "Accepted node context package for the replacement parent.",
            }
        )
    replay_id = str(node.get("parent_backward_replay_id") or "")
    if replay_id:
        artifacts.append(
            {
                "artifact_id": f"parent_backward_replay:{replay_id}",
                "artifact_type": "parent_backward_replay",
                "description": "Parent backward replay for current repair children.",
            }
        )
    if subject_packet is not None:
        packet_id = str(subject_packet.get("packet_id") or "")
        if packet_id:
            artifacts.append(
                {
                    "artifact_id": f"subject_packet:{packet_id}",
                    "artifact_type": "subject_packet",
                    "description": "Current subject packet being checked.",
                }
            )
    if target_result is not None:
        result_id = str(target_result.get("result_id") or "")
        if result_id:
            artifacts.append(
                {
                    "artifact_id": f"target_result:{result_id}",
                    "artifact_type": "target_result",
                    "description": "Current subject result being checked.",
                }
            )
    return artifacts


def _flowguard_required_subject_artifact_ids(packet: Mapping[str, Any]) -> list[str]:
    binding = _packet_result_contract_profile_binding(
        packet,
        "flowguard.subject_artifacts_consumed_required",
    )
    raw_ids = binding.get("artifact_ids")
    if not isinstance(raw_ids, list):
        return []
    return [str(artifact_id) for artifact_id in raw_ids if str(artifact_id)]


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
    node_acceptance_item_ids = _node_acceptance_item_ids(node)
    raw_projection = raw_package.get("acceptance_item_projection")
    if node_acceptance_item_ids:
        if not isinstance(raw_projection, list) or not raw_projection:
            raise BlackBoxRuntimeError("node context package missing required field: acceptance_item_projection")
    normalized_projection: list[dict[str, Any]] = []
    if isinstance(raw_projection, list):
        for index, row in enumerate(raw_projection, start=1):
            if not isinstance(row, Mapping):
                raise BlackBoxRuntimeError(f"node context package acceptance_item_projection[{index}] must be an object")
            item_id = str(row.get("acceptance_item_id") or "").strip()
            if not item_id:
                raise BlackBoxRuntimeError(
                    f"node context package acceptance_item_projection[{index}] requires acceptance_item_id"
                )
            if item_id not in node_acceptance_item_ids:
                raise BlackBoxRuntimeError(
                    f"node context package acceptance_item_projection[{index}] references item outside node owner set: {item_id}"
                )
            for field in ("status_for_this_node", "future_evidence_rule"):
                if not str(row.get(field) or "").strip():
                    raise BlackBoxRuntimeError(
                        f"node context package acceptance_item_projection[{index}] requires {field}"
                    )
            normalized_projection.append(json.loads(json.dumps(dict(row), sort_keys=True)))
    missing_projected_items = sorted(set(node_acceptance_item_ids) - {row["acceptance_item_id"] for row in normalized_projection})
    if missing_projected_items:
        raise BlackBoxRuntimeError(
            "node context package acceptance_item_projection missing node-owned acceptance item(s): "
            + ", ".join(missing_projected_items)
        )
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
        "known_risks": _normalize_context_items(raw_package.get("known_risks"), "known_risks"),
        "acceptance_item_projection": normalized_projection,
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
        existing_blocker_id = str(existing.get("blocker_id") or "")
        incoming_blocker_id = str(blocker_id or "")
        if existing_blocker_id != incoming_blocker_id:
            raise BlackBoxRuntimeError("pending staged effect repair blocker identity mismatch")
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


def _route_node_kind(node: Mapping[str, Any]) -> str:
    return str(node.get("node_kind") or "leaf").strip()


def _route_node_child_ids(node: Mapping[str, Any]) -> list[str]:
    return [str(item).strip() for item in node.get("child_node_ids") or [] if str(item).strip()]


def _node_worker_dispatch_blocker(ledger: Mapping[str, Any], node_id: str, node: Mapping[str, Any]) -> str:
    kind = _route_node_kind(node)
    child_ids = _route_node_child_ids(node)
    if kind in {"leaf", "repair"} and child_ids:
        return f"route node shape conflict: {kind} node {node_id} has child_node_ids and cannot be a worker leaf"
    if kind in NON_WORKER_DISPATCH_NODE_KINDS:
        return f"route node {node_id} is a {kind} scope and cannot receive a worker task packet"
    if child_ids:
        return f"route node {node_id} has child_node_ids and cannot receive a worker task packet"
    return ""


def _route_node_all_children_resolved(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> bool:
    child_ids = _route_node_child_ids(node)
    if not child_ids:
        return False
    for child_id in child_ids:
        child = ledger.get("route_nodes", {}).get(child_id)
        if not isinstance(child, Mapping):
            return False
        if child.get("status") not in {"accepted", "waived", "superseded"}:
            return False
    return True


def _first_unresolved_child_node_id(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> str:
    for child_id in _route_node_child_ids(node):
        child = ledger.get("route_nodes", {}).get(child_id)
        if not isinstance(child, Mapping):
            raise BlackBoxRuntimeError(f"route node child reference is missing: {child_id}")
        if child.get("status") not in {"accepted", "waived", "superseded"}:
            return child_id
    return ""


def _enter_nonworker_route_scope(ledger: dict[str, Any], node_id: str, *, reason: str) -> bool:
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    blocker = _node_worker_dispatch_blocker(ledger, node_id, node)
    if not blocker:
        return False
    if _route_node_kind(node) in {"leaf", "repair"} and _route_node_child_ids(node):
        raise BlackBoxRuntimeError(blocker)
    child_id = _first_unresolved_child_node_id(ledger, node)
    if child_id:
        node["status"] = "awaiting_children"
        frontier = ledger.setdefault("execution_frontier", {})
        frontier["active_node_id"] = child_id
        frontier["status"] = "node_execution"
        frontier["blocked_reason"] = reason
        frontier["updated_at"] = now_iso()
        _event(ledger, "execution_frontier_updated", status="node_execution", active_node_id=child_id)
        if high_standard_flow_required(ledger):
            ensure_node_acceptance_plan_packet(ledger, child_id)
        else:
            ensure_next_node_task_packet(ledger)
        return True
    if _node_requires_parent_backward_replay(node) and not _parent_backward_replay_accepted(ledger, node_id):
        node["status"] = "awaiting_parent_backward_replay"
        _frontier_update(ledger, node_id, "awaiting_parent_backward_replay", reason)
        ensure_parent_backward_replay_packet(ledger, node_id)
        return True
    node["status"] = "awaiting_pm_disposition"
    _frontier_update(ledger, node_id, "awaiting_pm_disposition", reason)
    return True


def _flowguard_route_candidates() -> list[dict[str, str]]:
    return [
        {
            "modeled_target": modeled_target,
            "selected_skill": selected_skill,
        }
        for modeled_target, selected_skill in sorted(_DEFAULT_FLOWGUARD_ROUTES.items())
    ]


def ensure_node_prework_flowguard_packet(ledger: dict[str, Any], node_id: str) -> str:
    raise BlackBoxRuntimeError(
        "node_prework_flowguard is no longer a supported current FlowPilot path; "
        "ordinary accepted node plans go to Reviewer, and structural PM route changes use pm_flowguard_acceptance"
    )


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
                "node_kind": str(node.get("node_kind") or "leaf"),
                "parent_node_id": str(node.get("parent_node_id") or ""),
                "child_node_ids": list(node.get("child_node_ids") or []),
                "inherited_child_node_ids": list(node.get("inherited_child_node_ids") or []),
                "inherited_accepted_result_ids": list(node.get("inherited_accepted_result_ids") or []),
                "parent_repair_scope_contract_id": str(node.get("parent_repair_scope_contract_id") or ""),
                "repair_parent_scope_contract": _copy_jsonable(node.get("repair_parent_scope_contract") or {})
                if isinstance(node.get("repair_parent_scope_contract"), Mapping)
                else {},
                "acceptance_criteria": list(node.get("acceptance_criteria") or []),
                "high_standard_requirement_ids": [
                    str(row.get("requirement_id", ""))
                    for row in _blocking_high_standard_requirements(ledger)
                    if row.get("requirement_id")
                ],
                "acceptance_item_ids": _node_acceptance_item_ids(node),
                "skill_standard_obligation_ids": [
                    str(row.get("obligation_id", ""))
                    for row in _required_skill_obligations(ledger)
                    if row.get("obligation_id")
                ],
                "instruction": (
                    "First decide whether the current route/node structure is still right. If yes, return "
                    "decision=pass with a top-level node_context_package for Reviewer and Worker. If the node is "
                    "too coarse, too fine, or structurally wrong, return decision=redesign_route with a strict "
                    "route_plan. For node-entry redesign, the route_plan must start with a replacement "
                    "parent/module scope for the active node and put its decomposed child work in child_node_ids; "
                    "do not append those child work items as flat peer leaves. If this is a parent repair replacement, "
                    "child_node_ids are the only current repair children; inherited_child_node_ids and inherited_accepted_result_ids "
                    "are history/context only and cannot close the replacement parent. Do not request optional FlowGuard; runtime sends structural redesigns through "
                    "mandatory FlowGuard, PM absorption, Reviewer, and system validation."
                ),
                "required_node_context_package_fields": [
                    "purpose",
                    "acceptance_criteria",
                    "relevant_references",
                    "known_risks",
                    "acceptance_item_projection",
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


def _terminal_backward_replay_accepted(ledger: Mapping[str, Any]) -> bool:
    replay_id = str(ledger.get("terminal_backward_replay_id") or "")
    if not replay_id:
        return False
    replay = ledger.get("terminal_backward_replays", {}).get(replay_id, {})
    return (
        isinstance(replay, Mapping)
        and replay.get("status") == "accepted"
        and replay.get("source_generation") == ledger.get("source_generation")
    )


def _active_route_node_records(
    ledger: Mapping[str, Any],
    *,
    include_superseded: bool = False,
) -> list[Mapping[str, Any]]:
    active_route = ledger.get("active_route_version")
    nodes: list[Mapping[str, Any]] = []
    for node in ledger.get("route_nodes", {}).values():
        if not isinstance(node, Mapping):
            continue
        if active_route is not None and str(node.get("route_version", "")) != str(active_route):
            continue
        if not include_superseded and node.get("status") == "superseded":
            continue
        nodes.append(node)
    return nodes


def _packet_current_for_route_node(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    node_id: str = "",
) -> bool:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    active_route = ledger.get("active_route_version")
    if active_route is not None and envelope.get("route_version") != active_route:
        return False
    if node_id and str(envelope.get("route_node_id") or "") != node_id:
        return False
    return True


def _review_evidence_current_and_accepted(
    ledger: Mapping[str, Any],
    review_id: str,
    *,
    node_id: str = "",
) -> bool:
    review = ledger.get("reviews", {}).get(review_id)
    if not isinstance(review, Mapping):
        return False
    if review.get("decision") != "accept":
        return False
    if review.get("blockers"):
        return False
    if review.get("checks_evidence") is not True:
        return False
    if review.get("independent_from_producer") is not True:
        return False
    if not review.get("direct_evidence_ids"):
        return False
    result_id = str(review.get("result_id") or "")
    result = ledger.get("results", {}).get(result_id)
    if not isinstance(result, Mapping):
        return False
    if result.get("status") != "accepted":
        return False
    subject_packet_id = str(review.get("subject_packet_id") or result.get("packet_id") or "")
    packet = ledger.get("packets", {}).get(subject_packet_id)
    if not isinstance(packet, Mapping):
        return False
    return _packet_current_for_route_node(ledger, packet, node_id=node_id)


def _flowguard_order_current_and_passing(
    ledger: Mapping[str, Any],
    order_id: str,
    *,
    node_id: str = "",
) -> bool:
    order = ledger.get("flowguard_work_orders", {}).get(order_id)
    if not isinstance(order, Mapping):
        return False
    if order.get("status") != "complete" or order.get("decision") != "pass":
        return False
    if order.get("progress_only") or order.get("skipped_checks") or order.get("proof_stale"):
        return False
    if not order.get("proof_artifact"):
        return False
    if order.get("source_generation") != ledger.get("source_generation"):
        return False
    subject_packet_id = str(order.get("subject_id") or "")
    if subject_packet_id:
        packet = ledger.get("packets", {}).get(subject_packet_id)
        if not isinstance(packet, Mapping):
            return False
        if not _packet_current_for_route_node(ledger, packet, node_id=node_id):
            return False
    return True


def _validation_evidence_current_and_passing(
    ledger: Mapping[str, Any],
    evidence_id: str,
    *,
    node_id: str = "",
) -> bool:
    evidence = ledger.get("validation_evidence", {}).get(evidence_id)
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("status") != "passed":
        return False
    if evidence.get("source_generation") != ledger.get("source_generation"):
        return False
    if evidence.get("blockers"):
        return False
    subject_packet_id = str(evidence.get("subject_packet_id") or "")
    if subject_packet_id:
        packet = ledger.get("packets", {}).get(subject_packet_id)
        if not isinstance(packet, Mapping):
            return False
        if not _packet_current_for_route_node(ledger, packet, node_id=node_id):
            return False
    return True


def _valid_review_evidence_ids(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> list[str]:
    node_id = str(node.get("node_id") or "")
    return [
        str(review_id)
        for review_id in node.get("review_ids") or []
        if _review_evidence_current_and_accepted(ledger, str(review_id), node_id=node_id)
    ]


def _valid_flowguard_order_ids(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> list[str]:
    node_id = str(node.get("node_id") or "")
    return [
        str(order_id)
        for order_id in node.get("flowguard_order_ids") or []
        if _flowguard_order_current_and_passing(ledger, str(order_id), node_id=node_id)
    ]


def _valid_validation_evidence_ids(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> list[str]:
    node_id = str(node.get("node_id") or "")
    return [
        str(evidence_id)
        for evidence_id in node.get("validation_evidence_ids") or []
        if _validation_evidence_current_and_passing(ledger, str(evidence_id), node_id=node_id)
    ]


def _final_evidence_status(raw_ids: list[str], valid_ids: list[str]) -> str:
    if valid_ids:
        return "covered"
    if raw_ids:
        return "invalid"
    return "missing"


def _node_final_quality_evidence_valid(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> bool:
    node_id = str(node.get("node_id", ""))
    if _node_worker_dispatch_blocker(ledger, node_id, node):
        return True
    return (
        bool(_valid_flowguard_order_ids(ledger, node))
        and bool(_valid_review_evidence_ids(ledger, node))
        and bool(_valid_validation_evidence_ids(ledger, node))
    )


def _terminal_backward_replay_segment_targets(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = [
        {
            "segment_id": "delivered-product",
            "segment_kind": "delivered_product",
            "summary": "Inspect the delivered product or final artifact first.",
        },
        {
            "segment_id": "root-acceptance",
            "segment_kind": "root_acceptance",
            "summary": "Compare the delivered product against the frozen root acceptance contract.",
        },
        {
            "segment_id": "final-artifact-hygiene",
            "segment_kind": "final_artifact_hygiene",
            "summary": "Inspect final code, document, model, test, UI, artifact, and process hygiene before closure.",
        },
    ]
    for item in _active_acceptance_items(ledger):
        item_id = str(item.get("acceptance_item_id") or "")
        if not item_id:
            continue
        targets.append(
            {
                "segment_id": f"acceptance-item:{item_id}",
                "segment_kind": "acceptance_item",
                "summary": str(item.get("summary") or item_id),
                "quality_floor": str(item.get("quality_floor") or ""),
                "future_evidence_rule": str(item.get("future_evidence_rule") or ""),
            }
        )
    for contract in _supplemental_repair_contract_records(ledger):
        contract_id = str(contract.get("contract_id") or "")
        if not contract_id:
            continue
        targets.append(
            {
                "segment_id": f"supplemental-contract:{contract_id}",
                "segment_kind": "supplemental_repair_contract",
                "summary": str(contract.get("pm_reason") or contract_id),
                "round_number": int(contract.get("round_number", 0) or 0),
                "terminal_gap_report_result_id": str(contract.get("terminal_gap_report_result_id") or ""),
            }
        )
        for item in contract.get("repair_items") or []:
            if not isinstance(item, Mapping):
                continue
            item_id = str(item.get("repair_item_id") or "")
            if not item_id:
                continue
            targets.append(
                {
                    "segment_id": f"supplemental-repair-item:{contract_id}:{item_id}",
                    "segment_kind": "supplemental_repair_item",
                    "summary": str(item.get("required_repair") or item_id),
                    "gap_kind": str(item.get("gap_kind") or ""),
                    "owner_repair_node_id": str(item.get("owner_repair_node_id") or ""),
                    "acceptance_item_ids": [str(row) for row in item.get("acceptance_item_ids") or []],
                    "required_evidence": [str(row) for row in item.get("required_evidence") or []],
                }
            )
    for node in _active_route_node_records(ledger):
        node_id = str(node.get("node_id") or "")
        if not node_id:
            continue
        targets.append(
            {
                "segment_id": node_id,
                "segment_kind": "route_node",
                "summary": str(node.get("title") or node_id),
                "node_status": str(node.get("status") or ""),
                "node_acceptance_plan_id": str(node.get("node_acceptance_plan_id") or ""),
                "pm_disposition_id": str(node.get("pm_disposition_id") or ""),
            }
        )
    return targets


def _final_gate_ledgers_clean_for_terminal_replay(ledger: dict[str, Any]) -> bool:
    if recursive_route_required(ledger):
        build_final_route_wide_gate_ledger(ledger)
    if high_standard_flow_required(ledger) or recursive_route_required(ledger):
        build_final_requirement_evidence_matrix(ledger)
    route_wide = ledger.get("final_route_wide_gate_ledger")
    matrix = ledger.get("final_requirement_evidence_matrix")
    if recursive_route_required(ledger):
        if not isinstance(route_wide, Mapping) or int(route_wide.get("unresolved_count", 0)) != 0:
            return False
    if high_standard_flow_required(ledger) or recursive_route_required(ledger):
        if not isinstance(matrix, Mapping) or int(matrix.get("unresolved_count", 0)) != 0:
            return False
    return True


def _terminal_backward_replay_next_action(ledger: dict[str, Any]) -> RuntimeAction | None:
    if not recursive_route_required(ledger) or not ledger.get("route_nodes"):
        return None
    if not high_standard_flow_required(ledger) or _terminal_backward_replay_accepted(ledger):
        return None
    frontier = ledger.get("execution_frontier") or {}
    if frontier.get("active_node_id") or frontier.get("status") != "ready_for_final_closure":
        return None
    if not _final_gate_ledgers_clean_for_terminal_replay(ledger):
        return None
    return RuntimeAction(
        "issue_terminal_backward_replay_packet",
        "terminal backward replay is required before final closure",
        str(ledger.get("latest_validation_evidence_id") or ""),
        "reviewer",
    )


def ensure_terminal_backward_replay_packet(ledger: dict[str, Any], validation_evidence_id: str = "") -> str:
    if _terminal_backward_replay_accepted(ledger):
        return ""
    existing = _find_live_scope_packet(
        ledger,
        TERMINAL_BACKWARD_REPLAY_SCOPE,
        packet_kind="review",
    )
    if existing:
        return str(existing["packet_id"])
    if not _final_gate_ledgers_clean_for_terminal_replay(ledger):
        raise BlackBoxRuntimeError("terminal backward replay requires clean final route-wide and requirement ledgers")
    family_id = "review.terminal_backward_replay"
    return issue_task_packet(
        ledger,
        "reviewer",
        "Run terminal human backward replay before final closure",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.terminal_backward_replay_packet.v1",
                "route_version": ledger.get("active_route_version"),
                "validation_evidence_id": validation_evidence_id or str(ledger.get("latest_validation_evidence_id") or ""),
                "final_route_wide_gate_ledger_status": _copy_jsonable(ledger.get("final_route_wide_gate_ledger") or {}),
                "final_requirement_evidence_matrix_status": _copy_jsonable(ledger.get("final_requirement_evidence_matrix") or {}),
                "segment_targets": _terminal_backward_replay_segment_targets(ledger),
                "contract_family_id": family_id,
                "required_result_body_fields": list(packet_result_contracts.required_fields_for_family(family_id)),
                "required_child_fields": list(packet_result_contracts.required_child_fields_for_family(family_id)),
                "explicit_array_fields": list(packet_result_contracts.explicit_array_fields_for_family(family_id)),
                "non_empty_array_fields": list(packet_result_contracts.non_empty_array_fields_for_family(family_id)),
                "forbidden_fields": list(packet_result_contracts.forbidden_fields_for_family(family_id)),
                "minimal_valid_shape": packet_result_contracts.minimal_valid_shape_for_family(family_id),
                "instruction": (
                    "Start from the delivered product, then replay root acceptance and every effective route node. "
                    "Submit the terminal backward replay report with pm_visible_summary, reviewed_by_role, passed, "
                    "findings, blockers, pm_suggestion_items, final_artifact_refs, acceptance_item_closure, "
                    "route_segment_replay, waiver_records, final_blockers, and contract_self_check. "
                    "Do not pass from reports alone, accepted node ids alone, old UI evidence, or a completion summary."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        packet_kind="review",
        required_flowguard_target="",
        subject_id=str(ledger.get("latest_validation_evidence_id") or validation_evidence_id or "final-closure"),
        route_scope=TERMINAL_BACKWARD_REPLAY_SCOPE,
        acceptance_criteria=[
            "Terminal replay starts from the delivered product.",
            "Root acceptance and every effective node are checked backward.",
            "Every runtime-issued segment target appears exactly once in route_segment_replay.",
            "Any final blocker prevents terminal closure until PM chooses the matching current repair path.",
        ],
    )


def ensure_parent_backward_replay_packet(ledger: dict[str, Any], node_id: str) -> str:
    if _parent_backward_replay_accepted(ledger, node_id):
        return ""
    existing = _find_live_scope_packet(ledger, "parent_backward_replay", route_node_id=node_id)
    if existing:
        return str(existing["packet_id"])
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    parent_repair_violation = _parent_repair_node_current_child_violation(
        ledger,
        node_id,
        node,
        require_accepted_child_results=True,
    )
    if parent_repair_violation:
        raise BlackBoxRuntimeError(parent_repair_violation)
    active_child_node_ids = list(node.get("child_node_ids") or [])
    active_child_result_ids = _accepted_result_ids_for_route_nodes(ledger, [str(item) for item in active_child_node_ids])
    return issue_task_packet(
        ledger,
        "reviewer",
        f"Replay parent/module node {node_id} backward from child outcomes",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.parent_backward_replay_packet.v1",
                "route_node_id": node_id,
                "child_node_ids": active_child_node_ids,
                "current_repair_child_result_ids": active_child_result_ids,
                "inherited_child_node_ids": list(node.get("inherited_child_node_ids") or []),
                "inherited_accepted_result_ids": list(node.get("inherited_accepted_result_ids") or []),
                "parent_repair_scope_contract_id": str(node.get("parent_repair_scope_contract_id") or ""),
                "instruction": (
                    "Check whether the accepted children compose into the parent goal. "
                    "Do not pass from child existence alone. For parent repair replacements, inherited child nodes "
                    "and inherited accepted results are history only; pass requires current_repair_child_result_ids "
                    "from the active child_node_ids."
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
    if decision not in {"accept", "repair_current_scope", "redesign_route", "block", "stop"}:
        raise BlackBoxRuntimeError("PM disposition requires an explicit allowed decision")
    result = ledger.get("results", {}).get(result_id, {})
    payload = _parse_json_object(str(result.get("body", ""))) if isinstance(result, Mapping) else {}
    normalized = decision
    disposition_rows = payload.get("acceptance_item_disposition")
    normalized_disposition_rows = (
        json.loads(json.dumps(disposition_rows, sort_keys=True))
        if isinstance(disposition_rows, list)
        else []
    )
    ledger.setdefault("pm_dispositions", {})[disposition_id] = {
        "disposition_id": disposition_id,
        "node_id": node_id,
        "result_id": result_id,
        "decision": normalized,
        "reason": reason,
        "acceptance_item_disposition": normalized_disposition_rows,
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
        if not check_id or kind not in {
            "path_exists",
            "path_absent",
            "path_glob_exists",
            "path_glob_absent",
            "json_parse",
            "json_path_exists",
            "json_field_equals",
            "text_contains",
            "text_forbids",
            "fresh_after_event",
        }:
            result["reason"] = "invalid_deliverable_check_contract"
            result["summary"] = f"Node {node_id} deliverable check contract is invalid"
            results.append(result)
            continue
        if kind in {"path_glob_exists", "path_glob_absent"}:
            pattern = str(check.get("pattern") or check.get("path") or "").strip()
            matches, reason = _route_deliverable_glob_matches(ledger, pattern)
            if kind == "path_glob_absent":
                if matches:
                    result["reason"] = "forbidden_match"
                    result["summary"] = f"Node {node_id} forbidden deliverable glob matched {len(matches)} path(s)"
                    result["evidence"] = [f"path:{item}" for item in matches]
                else:
                    result["status"] = "passed"
                    result["reason"] = "absent"
                    result["summary"] = f"Node {node_id} forbidden deliverable glob is absent"
                result["pattern"] = pattern
                results.append(result)
                continue
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
        if kind == "path_absent":
            if resolved.exists():
                result["reason"] = "forbidden_path_exists"
                result["summary"] = f"Node {node_id} forbidden deliverable path exists"
            else:
                result["status"] = "passed"
                result["reason"] = "absent"
                result["summary"] = f"Node {node_id} forbidden deliverable path is absent"
        elif kind == "path_exists":
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
        elif kind in {"json_path_exists", "json_field_equals"}:
            json_path = str(check.get("json_path") or "").strip()
            if not json_path:
                result["reason"] = "missing_json_path"
                result["summary"] = f"Node {node_id} JSON deliverable check is missing json_path"
            elif not resolved.exists():
                result["reason"] = "missing"
                result["summary"] = f"Node {node_id} JSON deliverable path is missing"
            else:
                try:
                    parsed = json.loads(resolved.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    result["reason"] = "json_parse_failed"
                    result["summary"] = f"Node {node_id} JSON deliverable is not parseable"
                else:
                    exists, value = _json_path_lookup(parsed, json_path)
                    result["json_path"] = json_path
                    if kind == "json_path_exists":
                        if exists:
                            result["status"] = "passed"
                            result["reason"] = "json_path_exists"
                            result["summary"] = f"Node {node_id} JSON path exists"
                        else:
                            result["reason"] = "json_path_missing"
                            result["summary"] = f"Node {node_id} JSON path is missing"
                    else:
                        if "expected_value" not in check:
                            result["reason"] = "missing_expected_value"
                            result["summary"] = f"Node {node_id} JSON equality check is missing expected_value"
                        elif exists and value == check.get("expected_value"):
                            result["status"] = "passed"
                            result["reason"] = "json_field_equals"
                            result["summary"] = f"Node {node_id} JSON value matches"
                        else:
                            result["reason"] = "json_field_mismatch" if exists else "json_path_missing"
                            result["summary"] = f"Node {node_id} JSON value does not match"
                            result["evidence"].append(f"json_path:{json_path}")
        elif kind in {"text_contains", "text_forbids"}:
            text = str(check.get("text") or "")
            if not text:
                result["reason"] = "missing_text"
                result["summary"] = f"Node {node_id} text deliverable check is missing text"
            elif not resolved.exists():
                result["reason"] = "missing"
                result["summary"] = f"Node {node_id} text deliverable path is missing"
            else:
                try:
                    content = resolved.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    result["reason"] = "text_read_failed"
                    result["summary"] = f"Node {node_id} text deliverable is not readable"
                else:
                    found = text in content
                    if kind == "text_contains" and found:
                        result["status"] = "passed"
                        result["reason"] = "text_found"
                        result["summary"] = f"Node {node_id} required text is present"
                    elif kind == "text_forbids" and not found:
                        result["status"] = "passed"
                        result["reason"] = "text_absent"
                        result["summary"] = f"Node {node_id} forbidden text is absent"
                    else:
                        result["reason"] = "text_missing" if kind == "text_contains" else "forbidden_text_found"
                        result["summary"] = (
                            f"Node {node_id} required text is missing"
                            if kind == "text_contains"
                            else f"Node {node_id} forbidden text is present"
                        )
        elif kind == "fresh_after_event":
            event_type = str(check.get("event_type") or "").strip()
            event_at = _latest_event_created_at(ledger, event_type)
            if not event_type:
                result["reason"] = "missing_event_type"
                result["summary"] = f"Node {node_id} freshness check is missing event_type"
            elif not event_at:
                result["reason"] = "event_missing"
                result["summary"] = f"Node {node_id} freshness event is missing"
            elif not resolved.exists():
                result["reason"] = "missing"
                result["summary"] = f"Node {node_id} freshness deliverable path is missing"
            else:
                mtime = datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc)
                if mtime > event_at:
                    result["status"] = "passed"
                    result["reason"] = "fresh"
                    result["summary"] = f"Node {node_id} deliverable is fresh after event"
                    result["evidence"].append(f"event_type:{event_type}")
                else:
                    result["reason"] = "stale"
                    result["summary"] = f"Node {node_id} deliverable is stale before event"
                    result["evidence"].append(f"event_type:{event_type}")
        results.append(result)
    return results


def _json_path_lookup(value: Any, json_path: str) -> tuple[bool, Any]:
    current = value
    for raw_part in json_path.split("."):
        part = raw_part.strip()
        if not part:
            return False, None
        if "[" in part and part.endswith("]"):
            key, _, raw_index = part[:-1].partition("[")
            if key:
                if not isinstance(current, Mapping) or key not in current:
                    return False, None
                current = current[key]
            try:
                index = int(raw_index)
            except ValueError:
                return False, None
            if not isinstance(current, list) or index < 0 or index >= len(current):
                return False, None
            current = current[index]
            continue
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _latest_event_created_at(ledger: Mapping[str, Any], event_type: str) -> datetime | None:
    if not event_type:
        return None
    for event in reversed(list(ledger.get("events", []))):
        if not isinstance(event, Mapping) or event.get("event_type") != event_type:
            continue
        raw_created = str(event.get("created_at") or "")
        try:
            parsed = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


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


def _pm_disposition_for_node(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    disposition_id = str(node.get("pm_disposition_id") or "")
    disposition = ledger.get("pm_dispositions", {}).get(disposition_id, {}) if disposition_id else {}
    return disposition if isinstance(disposition, Mapping) else {}


def _acceptance_item_disposition_by_id(disposition: Mapping[str, Any]) -> dict[str, str]:
    rows = disposition.get("acceptance_item_disposition")
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        item_id = str(row.get("acceptance_item_id") or "").strip()
        item_disposition = str(row.get("disposition") or "").strip()
        if item_id and item_disposition:
            mapped[item_id] = item_disposition
    return mapped


def _node_has_passing_deliverable_evidence(ledger: Mapping[str, Any], node: Mapping[str, Any]) -> bool:
    checks = _evaluate_route_deliverable_checks(ledger, node)
    required = [check for check in checks if check.get("required") is not False]
    return bool(required) and all(check.get("status") == "passed" for check in required)


def _node_closes_high_standard_requirement(
    ledger: Mapping[str, Any],
    node: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> bool:
    requirement_id = str(requirement.get("requirement_id") or "")
    if not requirement_id:
        return False
    if requirement_id not in [str(item) for item in node.get("high_standard_requirement_ids") or []]:
        return False
    if node.get("status") != "accepted":
        return False
    if _node_worker_dispatch_blocker(ledger, str(node.get("node_id") or ""), node) and _parent_backward_replay_accepted(
        ledger,
        str(node.get("node_id") or ""),
    ):
        return True
    if _node_has_passing_deliverable_evidence(ledger, node):
        return True
    if node.get("validation_evidence_ids"):
        return True
    return False


def _node_closes_acceptance_item(
    ledger: Mapping[str, Any],
    node: Mapping[str, Any],
    item: Mapping[str, Any],
) -> bool:
    item_id = str(item.get("acceptance_item_id") or "")
    if not item_id:
        return False
    if item_id not in _node_acceptance_item_ids(node):
        return False
    disposition = _pm_disposition_for_node(ledger, node)
    item_disposition = _acceptance_item_disposition_by_id(disposition).get(item_id, "")
    if item_disposition in {"waived", "superseded"}:
        return bool(node.get("pm_disposition_id"))
    if node.get("status") != "accepted":
        return False
    if item_disposition != "accepted":
        return False
    return _node_final_quality_evidence_valid(ledger, node)


def _acceptance_item_closure_rows(ledger: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    effective_nodes = _active_route_node_records(ledger)
    for item in _active_acceptance_items(ledger):
        item_id = str(item.get("acceptance_item_id") or "")
        if not item_id:
            continue
        owner_nodes = [
            node
            for node in effective_nodes
            if item_id in _node_acceptance_item_ids(node)
        ]
        closed_nodes = [
            str(node.get("node_id") or "")
            for node in owner_nodes
            if _node_closes_acceptance_item(ledger, node, item)
        ]
        assigned_route_node_ids = [str(node.get("node_id") or "") for node in owner_nodes]
        if not owner_nodes:
            status = "orphan"
            unresolved.append(f"acceptance_item_orphan:{item_id}")
        elif closed_nodes:
            status = "covered"
        else:
            status = "missing"
            unresolved.append(f"acceptance_item_unresolved:{item_id}")
        rows.append(
            {
                "acceptance_item_id": item_id,
                "source_type": str(item.get("source_type") or ""),
                "summary": str(item.get("summary") or item_id),
                "quality_floor": str(item.get("quality_floor") or ""),
                "future_evidence_rule": str(item.get("future_evidence_rule") or ""),
                "assigned_route_node_ids": assigned_route_node_ids,
                "closed_by_node_ids": closed_nodes,
                "status": status,
            }
        )
    return rows, unresolved


def _supplemental_repair_contract_records(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    contracts = ledger.get("supplemental_repair_contracts")
    if not isinstance(contracts, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for contract in contracts.values():
        if isinstance(contract, Mapping):
            rows.append(_copy_jsonable(contract))
    rows.sort(key=lambda row: (int(row.get("round_number", 0) or 0), str(row.get("contract_id") or "")))
    return rows


def _supplemental_repair_closure_rows(ledger: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    nodes = {
        str(node.get("node_id") or ""): node
        for node in _active_route_node_records(ledger)
        if str(node.get("node_id") or "")
    }
    for contract in _supplemental_repair_contract_records(ledger):
        contract_id = str(contract.get("contract_id") or "")
        for item in contract.get("repair_items") or []:
            if not isinstance(item, Mapping):
                unresolved.append(f"supplemental_repair_item_invalid:{contract_id}")
                continue
            item_id = str(item.get("repair_item_id") or "")
            owner_node_id = str(item.get("owner_repair_node_id") or "")
            node = nodes.get(owner_node_id)
            evidence_ids: list[str] = []
            projection_ok = False
            node_status = ""
            if isinstance(node, Mapping):
                node_status = str(node.get("status") or "")
                evidence_ids = [
                    str(evidence_id)
                    for evidence_id in (
                        list(node.get("validation_evidence_ids") or [])
                        + list(node.get("review_ids") or [])
                        + list(node.get("flowguard_order_ids") or [])
                    )
                    if str(evidence_id)
                ]
                projection_ok = (
                    contract_id in [str(row) for row in node.get("supplemental_repair_contract_ids") or []]
                    and item_id in [str(row) for row in node.get("supplemental_repair_item_ids") or []]
                )
            if not node:
                status = "orphan"
                unresolved.append(f"supplemental_repair_item_orphan:{contract_id}:{item_id}")
            elif not projection_ok:
                status = "projection_missing"
                unresolved.append(f"supplemental_repair_item_projection_missing:{contract_id}:{item_id}")
            elif node_status != "accepted" or not _node_final_quality_evidence_valid(ledger, node):
                status = "missing"
                unresolved.append(f"supplemental_repair_item_unresolved:{contract_id}:{item_id}")
            else:
                status = "covered"
            rows.append(
                {
                    "contract_id": contract_id,
                    "round_number": int(contract.get("round_number", 0) or 0),
                    "repair_item_id": item_id,
                    "gap_kind": str(item.get("gap_kind") or ""),
                    "hygiene_category": str(item.get("hygiene_category") or ""),
                    "original_goal_link": str(item.get("original_goal_link") or ""),
                    "reviewer_gap": str(item.get("reviewer_gap") or ""),
                    "required_repair": str(item.get("required_repair") or ""),
                    "owner_repair_node_id": owner_node_id,
                    "acceptance_item_ids": [str(row) for row in item.get("acceptance_item_ids") or []],
                    "required_evidence": [str(row) for row in item.get("required_evidence") or []],
                    "evidence_ids": evidence_ids,
                    "status": status,
                }
            )
    return rows, unresolved


def build_final_route_wide_gate_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    nodes = _active_route_node_records(ledger, include_superseded=True)
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
        dispatch_blocker = _node_worker_dispatch_blocker(ledger, node_id, node)
        if dispatch_blocker and _route_node_kind(node) in {"leaf", "repair"}:
            unresolved.append(f"route_node_shape_conflict:{node_id}")
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
        if not dispatch_blocker:
            if node.get("flowguard_order_ids") and not _valid_flowguard_order_ids(ledger, node):
                unresolved.append(f"invalid_flowguard_evidence:{node_id}")
            if node.get("review_ids") and not _valid_review_evidence_ids(ledger, node):
                unresolved.append(f"invalid_review_evidence:{node_id}")
            if node.get("validation_evidence_ids") and not _valid_validation_evidence_ids(ledger, node):
                unresolved.append(f"invalid_validation_evidence:{node_id}")
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, Mapping) or not _packet_requires_current_acceptance(ledger, packet):
            continue
        if packet.get("status") not in _NONCURRENT_PACKET_STATUSES:
            unresolved.append(f"packet_not_accepted:{packet['packet_id']}")
    acceptance_item_rows, acceptance_item_unresolved = _acceptance_item_closure_rows(ledger)
    unresolved.extend(acceptance_item_unresolved)
    supplemental_repair_rows, supplemental_repair_unresolved = _supplemental_repair_closure_rows(ledger)
    unresolved.extend(supplemental_repair_unresolved)
    final_artifact_hygiene_rows, final_artifact_hygiene_unresolved = _final_artifact_hygiene_closure_rows(ledger)
    unresolved.extend(final_artifact_hygiene_unresolved)
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
        "acceptance_item_closure": acceptance_item_rows,
        "supplemental_repair_closure": supplemental_repair_rows,
        "final_artifact_hygiene_closure": final_artifact_hygiene_rows,
        "final_artifact_hygiene_finding_count": len(final_artifact_hygiene_rows),
        "resolved_final_artifact_hygiene_count": len(
            [row for row in final_artifact_hygiene_rows if not row.get("unresolved")]
        ),
        "unresolved_final_artifact_hygiene_count": len(
            [row for row in final_artifact_hygiene_rows if row.get("unresolved")]
        ),
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
                for node in _active_route_node_records(ledger)
                if _node_closes_high_standard_requirement(ledger, node, requirement)
                and _node_final_quality_evidence_valid(ledger, node)
            ]
            add_row(
                requirement_id,
                "high_standard_requirement",
                "covered" if covered_nodes else "missing",
                covered_nodes,
                (
                    str(requirement.get("summary") or requirement_id)
                    + " | closure_rule="
                    + str(requirement.get("closure_rule") or "")
                ),
            )
        acceptance_item_rows, _item_unresolved = _acceptance_item_closure_rows(ledger)
        for item_row in acceptance_item_rows:
            item_id = str(item_row.get("acceptance_item_id") or "unknown")
            add_row(
                item_id,
                "acceptance_item",
                "covered" if item_row.get("status") == "covered" else str(item_row.get("status") or "missing"),
                [str(item) for item in item_row.get("closed_by_node_ids") or []],
                (
                    str(item_row.get("summary") or item_id)
                    + " | quality_floor="
                    + str(item_row.get("quality_floor") or "")
                ),
            )
        for obligation in _required_skill_obligations(ledger):
            obligation_id = str(obligation.get("obligation_id") or "unknown")
            covered_nodes = [
                str(node.get("node_id", ""))
                for node in _active_route_node_records(ledger)
                if obligation_id in list(node.get("skill_standard_obligation_ids") or [])
                and node.get("status") in {"accepted", "waived"}
                and _node_final_quality_evidence_valid(ledger, node)
            ]
            add_row(
                obligation_id,
                "skill_standard_obligation",
                "covered" if covered_nodes else "missing",
                covered_nodes,
                str(obligation.get("skill") or obligation_id),
            )

    supplemental_repair_rows, _supplemental_unresolved = _supplemental_repair_closure_rows(ledger)
    for repair_row in supplemental_repair_rows:
        contract_id = str(repair_row.get("contract_id") or "unknown")
        item_id = str(repair_row.get("repair_item_id") or "unknown")
        add_row(
            f"{contract_id}:{item_id}",
            "terminal_supplemental_repair_item",
            "covered" if repair_row.get("status") == "covered" else str(repair_row.get("status") or "missing"),
            [str(item) for item in repair_row.get("evidence_ids") or []],
            (
                str(repair_row.get("required_repair") or item_id)
                + " | original_goal_link="
                + str(repair_row.get("original_goal_link") or "")
            ),
        )

    final_artifact_hygiene_rows, _hygiene_unresolved = _final_artifact_hygiene_closure_rows(ledger)
    for hygiene_row in final_artifact_hygiene_rows:
        finding_id = str(hygiene_row.get("finding_id") or "unknown")
        add_row(
            finding_id,
            "final_artifact_hygiene",
            "missing" if hygiene_row.get("unresolved") else "covered",
            [str(item) for item in hygiene_row.get("evidence_ids") or []],
            (
                str(hygiene_row.get("classification") or "")
                + " | "
                + str(hygiene_row.get("reason") or hygiene_row.get("artifact_family") or finding_id)
            ),
        )

    for node in _active_route_node_records(ledger):
        node_id = str(node.get("node_id", ""))
        dispatch_blocker = _node_worker_dispatch_blocker(ledger, node_id, node)
        worker_dispatch_node = not dispatch_blocker
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
        if dispatch_blocker and _route_node_kind(node) in {"leaf", "repair"}:
            add_row(
                f"{node_id}:route-shape",
                "route_shape",
                "missing",
                [],
                f"Node {node_id} is declared dispatchable but still has child_node_ids",
            )
        add_row(
            f"{node_id}:pm-disposition",
            "pm_disposition",
            "covered" if node.get("pm_disposition_id") else "missing",
            [str(node.get("pm_disposition_id", ""))] if node.get("pm_disposition_id") else [],
            f"Node {node_id} has PM disposition",
        )
        if worker_dispatch_node:
            raw_flowguard_ids = [str(item) for item in node.get("flowguard_order_ids") or []]
            valid_flowguard_ids = _valid_flowguard_order_ids(ledger, node)
            add_row(
                f"{node_id}:flowguard",
                "flowguard",
                _final_evidence_status(raw_flowguard_ids, valid_flowguard_ids),
                valid_flowguard_ids,
                f"Node {node_id} has FlowGuard evidence",
            )
            raw_review_ids = [str(item) for item in node.get("review_ids") or []]
            valid_review_ids = _valid_review_evidence_ids(ledger, node)
            add_row(
                f"{node_id}:review",
                "review",
                _final_evidence_status(raw_review_ids, valid_review_ids),
                valid_review_ids,
                f"Node {node_id} has independent review evidence",
            )
            raw_validation_ids = [str(item) for item in node.get("validation_evidence_ids") or []]
            valid_validation_ids = _valid_validation_evidence_ids(ledger, node)
            add_row(
                f"{node_id}:validation",
                "validation",
                _final_evidence_status(raw_validation_ids, valid_validation_ids),
                valid_validation_ids,
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
        node_kind = _strict_optional_string(raw_node, "node_kind", "leaf")
        if node_kind not in ROUTE_NODE_KINDS:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.node_kind must be one of {', '.join(sorted(ROUTE_NODE_KINDS))}"
            )
        normalized.append(
            {
                "node_id": node_id,
                "title": title,
                "node_kind": node_kind,
                "parent_node_id": _strict_optional_string(raw_node, "parent_node_id", ""),
                "child_node_ids": _strict_string_list(raw_node, "child_node_ids", node_id),
                "responsibility": _strict_optional_string(raw_node, "responsibility", ""),
                "modeled_target": _strict_optional_string(raw_node, "modeled_target", ""),
                "acceptance_criteria": _strict_string_list(raw_node, "acceptance_criteria", node_id),
                "required_outputs": _strict_json_list(raw_node, "required_outputs", node_id),
                "deliverable_checks": _strict_deliverable_checks(raw_node, node_id),
                "validation_checks": _strict_json_list(raw_node, "validation_checks", node_id),
                "high_standard_requirement_ids": _strict_string_list(raw_node, "high_standard_requirement_ids", node_id),
                "acceptance_item_ids": _strict_string_list(raw_node, "acceptance_item_ids", node_id),
                "skill_standard_obligation_ids": _strict_string_list(raw_node, "skill_standard_obligation_ids", node_id),
                "supplemental_repair_contract_ids": _strict_string_list(raw_node, "supplemental_repair_contract_ids", node_id),
                "supplemental_repair_item_ids": _strict_string_list(raw_node, "supplemental_repair_item_ids", node_id),
            }
        )
    known_ids = {str(node["node_id"]) for node in normalized}
    by_id = {str(node["node_id"]): node for node in normalized}
    for node in normalized:
        node_id = str(node["node_id"])
        parent_id = str(node.get("parent_node_id") or "")
        child_ids = [str(item) for item in node.get("child_node_ids") or []]
        kind = str(node.get("node_kind") or "leaf")
        if parent_id and parent_id not in known_ids:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: {node_id}.parent_node_id references unknown node {parent_id}")
        missing_children = [child_id for child_id in child_ids if child_id not in known_ids]
        if missing_children:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.child_node_ids reference unknown node(s): {', '.join(missing_children)}"
            )
        if kind in NON_WORKER_DISPATCH_NODE_KINDS and not child_ids:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: {kind} node {node_id} requires child_node_ids")
        if kind in {"leaf", "repair"} and child_ids:
            raise BlackBoxRuntimeError(f"strict route plan schema violation: {kind} node {node_id} must not have child_node_ids")
        for child_id in child_ids:
            child_parent = str(by_id[child_id].get("parent_node_id") or "")
            if child_parent and child_parent != node_id:
                raise BlackBoxRuntimeError(
                    f"strict route plan schema violation: child node {child_id} parent_node_id must match {node_id}"
                )
    return normalized


def _validate_route_plan_acceptance_item_coverage(
    ledger: Mapping[str, Any],
    node_specs: list[dict[str, Any]],
) -> None:
    if not high_standard_flow_required(ledger):
        return
    active_item_ids = set(_active_acceptance_item_ids(ledger))
    if not active_item_ids:
        return
    covered_item_ids = {
        str(item)
        for spec in node_specs
        for item in spec.get("acceptance_item_ids", [])
        if str(item)
    }
    missing_item_ids = sorted(active_item_ids - covered_item_ids)
    if missing_item_ids:
        raise BlackBoxRuntimeError(
            "strict route plan schema violation: active acceptance item(s) lack route node owner: "
            + ", ".join(missing_item_ids)
        )
    unknown_item_ids = sorted(covered_item_ids - active_item_ids)
    if unknown_item_ids:
        raise BlackBoxRuntimeError(
            "strict route plan schema violation: route node references unknown acceptance item(s): "
            + ", ".join(unknown_item_ids)
        )


def _validate_node_acceptance_redesign_route_nodes(
    node_specs: list[dict[str, Any]],
    *,
    target_node_id: str,
) -> None:
    del target_node_id
    if not node_specs:
        raise BlackBoxRuntimeError("strict route plan schema violation: node acceptance redesign_route nodes must be non-empty")
    first_node = node_specs[0]
    first_kind = str(first_node.get("node_kind") or "leaf")
    first_children = [str(item) for item in first_node.get("child_node_ids") or []]
    if first_kind not in NON_WORKER_DISPATCH_NODE_KINDS or not first_children:
        raise BlackBoxRuntimeError(
            "strict route plan schema violation: node acceptance redesign_route must start with a replacement "
            "parent/module scope using node_kind and child_node_ids; flat all-leaf peer route_plan nodes are not allowed"
        )
    if not any(str(node.get("node_kind") or "leaf") in {"leaf", "repair"} for node in node_specs):
        raise BlackBoxRuntimeError(
            "strict route plan schema violation: node acceptance redesign_route parent/module scope requires dispatchable leaf children"
        )


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
        if kind not in {
            "path_exists",
            "path_absent",
            "path_glob_exists",
            "path_glob_absent",
            "json_parse",
            "json_path_exists",
            "json_field_equals",
            "text_contains",
            "text_forbids",
            "fresh_after_event",
        }:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] has unsupported kind"
            )
        if kind in {
            "path_exists",
            "path_absent",
            "json_parse",
            "json_path_exists",
            "json_field_equals",
            "text_contains",
            "text_forbids",
            "fresh_after_event",
        } and not str(check.get("path") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing path"
            )
        if kind in {"path_glob_exists", "path_glob_absent"} and not str(check.get("pattern") or check.get("path") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing pattern"
            )
        if kind in {"json_path_exists", "json_field_equals"} and not str(check.get("json_path") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing json_path"
            )
        if kind == "json_field_equals" and "expected_value" not in check:
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing expected_value"
            )
        if kind in {"text_contains", "text_forbids"} and not str(check.get("text") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing text"
            )
        if kind == "fresh_after_event" and not str(check.get("event_type") or "").strip():
            raise BlackBoxRuntimeError(
                f"strict route plan schema violation: {node_id}.deliverable_checks[{check_id}] missing event_type"
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
    existing = _find_packet(
        ledger,
        packet_kind="pm_disposition",
        subject_id=subject_packet_id,
        reusable_statuses={"open", "assigned", "acknowledged", "result_submitted"},
    )
    if existing:
        return str(existing["packet_id"])
    stale_existing = _find_packet(ledger, packet_kind="pm_disposition", subject_id=subject_packet_id)
    if isinstance(stale_existing, dict) and stale_existing.get("status") in _CURRENT_PACKET_BLOCKING_STATUSES:
        stale_existing["status"] = "superseded_after_repair"
        stale_existing["superseded_reason"] = "blocked_pm_disposition_reissued"
        stale_existing["superseded_at"] = now_iso()
        _event(
            ledger,
            "blocked_pm_disposition_packet_superseded",
            packet_id=str(stale_existing.get("packet_id") or ""),
            node_id=node_id,
            subject_packet_id=subject_packet_id,
        )
    node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
    family_id = "pm_disposition.node_pm_disposition"
    minimal_valid_shape = packet_result_contracts.minimal_valid_shape_for_family(family_id)
    node_requirement_ids = [str(item) for item in node.get("high_standard_requirement_ids") or [] if str(item)]
    node_acceptance_item_ids = _node_acceptance_item_ids(node)
    minimal_valid_shape["acceptance_item_disposition"] = [
        {
            "acceptance_item_id": item_id,
            "disposition": "accepted",
            "basis": "Current node result, FlowGuard evidence, Reviewer report, and validation evidence support this item.",
        }
        for item_id in node_acceptance_item_ids
    ]
    node_validation_ids = [str(item) for item in node.get("validation_evidence_ids") or [] if str(item)]
    return issue_task_packet(
        ledger,
        "pm",
        f"Record PM disposition for route node {node_id}",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_disposition_packet.v1",
                "route_node_id": node_id,
                "subject_packet_id": subject_packet_id,
                "contract_family_id": family_id,
                "required_result_body_fields": list(packet_result_contracts.required_fields_for_family(family_id)),
                "explicit_array_fields": list(packet_result_contracts.explicit_array_fields_for_family(family_id)),
                "forbidden_fields": list(packet_result_contracts.forbidden_fields_for_family(family_id)),
                "node_high_standard_requirement_ids": node_requirement_ids,
                "node_acceptance_item_ids": node_acceptance_item_ids,
                "node_validation_evidence_ids": node_validation_ids,
                "minimal_valid_shape": minimal_valid_shape,
                "instruction": (
                    "Return exactly one structured JSON object for the PM disposition. "
                    "Default valid decision is accept; other valid decisions are repair_current_scope, redesign_route, block, or stop. "
                    "Use top-level reason; do not use summary or pm_disposition_summary. "
                    "Use acceptance_item_disposition as the only PM acceptance-item table. For each node-owned "
                    "acceptance item, write one row with acceptance_item_id, disposition, and basis. Do not use "
                    "old accepted/blocked/waived/superseded list fields."
                ),
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
    reason = str(payload.get("reason") or "")
    if not reason:
        raise BlackBoxRuntimeError("PM disposition requires a top-level reason")
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
_ACTIVE_SEMANTIC_BLOCKER_STATUSES = {"active", "repairing", "repair_packet_open", "awaiting_recheck"}
_CLEARABLE_SEMANTIC_BLOCKER_STATUSES = _ACTIVE_SEMANTIC_BLOCKER_STATUSES | {"repair_packet_open"}
_CURRENT_PACKET_BLOCKING_STATUSES = {"result_blocked", "review_blocked", "system_validation_blocked", "flowguard_blocked"}
_REPAIR_LOOP_COUNTED_BLOCKER_STATUSES = _CLEARABLE_SEMANTIC_BLOCKER_STATUSES | {"awaiting_pm_decision_gate"}
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
_GATED_PM_REPAIR_DECISIONS = {"repair_current_scope", "repair_parent_scope", "redesign_route"}
_HIGH_RISK_PM_DISPOSITION_DECISIONS = {"redesign_route"}
_PM_FLOWGUARD_ACCEPTANCE_DECISIONS = {"accept", "redesign_route", "block", "stop_for_user"}
_REMOVED_PM_FLOWGUARD_ACCEPTANCE_DECISIONS = {
    "maybe",
    "needs_flowguard",
    "optional_flowguard",
    "flowguard_optional",
    "uncertain",
}
def _strict_json_object_from_body(body: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_outcome_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _payload_outcome_token(payload: Mapping[str, Any], packet_kind: str) -> str:
    if packet_kind in {"flowguard_check", "review"} and isinstance(payload.get("passed"), bool):
        return "pass" if payload.get("passed") is True else "block"
    return _normalize_outcome_token(payload.get("decision"))


def _terminal_backward_replay_outcome_token(payload: Mapping[str, Any]) -> str:
    blockers = payload.get("final_blockers")
    if isinstance(blockers, list):
        return "block" if blockers else "pass"
    return _normalize_outcome_token(payload.get("decision"))

def _default_blocker_class(packet_kind: str, owner_role: str, token: str) -> str:
    if owner_role == "flowguard_operator" or packet_kind == "flowguard_check":
        return "flowguard_failure"
    if token in {"needs_more_evidence", "more_evidence_required"}:
        return "evidence_gap"
    if token in {"needs_pm", "stop", "stopped"}:
        return "needs_user"
    if token in {"reject", "rejected"}:
        return "local_artifact"
    return "local_artifact"


def _parse_packet_outcome(packet: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    route_scope = str(envelope.get("route_scope") or "")
    owner_role = str(envelope.get("responsibility", ""))
    body = str(result.get("body", ""))
    payload = _strict_json_object_from_body(body)
    if packet_kind == "task" and route_scope == "high_standard_contract" and isinstance(payload, Mapping) and isinstance(payload.get("requirements"), list):
        token = "pass"
    elif packet_kind == "review" and route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE and isinstance(payload, Mapping):
        token = _terminal_backward_replay_outcome_token(payload)
    elif packet_kind == "task" and route_scope == "parent_backward_replay" and isinstance(payload, Mapping):
        token = _normalize_outcome_token(payload.get("composition_decision"))
    else:
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
        current_blocker_rows = payload.get("final_blockers") if route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE else payload.get("blockers")
        first_current_blocker = None
        if isinstance(current_blocker_rows, list):
            first_current_blocker = next((row for row in current_blocker_rows if isinstance(row, Mapping)), None)
        blocker_class = str(payload.get("blocker_class") or payload.get("failure_class") or blocker_class)
        if isinstance(first_current_blocker, Mapping):
            blocker_class = str(
                first_current_blocker.get("blocker_class")
                or first_current_blocker.get("failure_class")
                or blocker_class
            )
        structured_repairs = _structured_required_repairs_from_payload(payload)
        pm_visible_summary = _pm_visible_summary_from_payload(payload)
        recommendation = str(
            ("; ".join(structured_repairs) if structured_repairs else "")
            or (
                first_current_blocker.get("recommended_resolution")
                if isinstance(first_current_blocker, Mapping)
                else ""
            )
            or (
                first_current_blocker.get("required_repair")
                if isinstance(first_current_blocker, Mapping)
                else ""
            )
            or (
                first_current_blocker.get("summary")
                if isinstance(first_current_blocker, Mapping)
                else ""
            )
            or payload.get("recommended_resolution")
            or payload.get("recommendation")
            or payload.get("pm_recommendation")
            or ("; ".join(pm_visible_summary) if blocking and pm_visible_summary else "")
            or ""
        )
        refs = payload.get("evidence_refs") or []
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


def _current_packets_for_routing(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        packet
        for packet in ledger.get("packets", {}).values()
        if isinstance(packet, Mapping) and not _packet_is_noncurrent_for_routing(ledger, packet)
    ]


def _accepted_result_packets_for_active_route(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    active_route = ledger.get("active_route_version")
    if active_route is None:
        return []
    accepted_result_packets: list[Mapping[str, Any]] = []
    for packet in ledger.get("packets", {}).values():
        if not isinstance(packet, Mapping):
            continue
        if packet.get("status") in {"quarantined_after_route_mutation", "superseded_after_repair"}:
            continue
        if not packet.get("accepted_result_id"):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if envelope.get("route_version") != active_route:
            continue
        route_node_id = _packet_route_node_id(packet)
        if route_node_id:
            node = ledger.get("route_nodes", {}).get(route_node_id)
            if not isinstance(node, Mapping) or node.get("status") not in {"accepted", "waived"}:
                continue
        accepted_result_packets.append(packet)
    return accepted_result_packets


def _accepted_packets_for_closure_evidence(ledger: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        packet
        for packet in _accepted_result_packets_for_active_route(ledger)
        if packet.get("status") == "accepted"
    ]


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


def _active_route_node_order_for_progress(ledger: Mapping[str, Any]) -> list[str]:
    active_route = ledger.get("active_route_version")
    if active_route is None:
        return []
    routes = ledger.get("routes", {})
    if not isinstance(routes, Mapping):
        return []
    route = routes.get(str(active_route))
    if not isinstance(route, Mapping):
        return []
    node_order = route.get("node_order")
    if not isinstance(node_order, (list, tuple)):
        return []
    return [node_id for item in node_order if (node_id := str(item or "").strip())]


def current_progress_fraction(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Return Controller-safe current expanded node progress."""

    route_nodes = ledger.get("route_nodes", {})
    if not isinstance(route_nodes, Mapping):
        route_nodes = {}
    active_route_node_ids = _active_route_node_order_for_progress(ledger)
    if active_route_node_ids:
        expanded_nodes = len(active_route_node_ids)
        ended_nodes = 0
        repair_generations = 0
        for node_id in active_route_node_ids:
            node = route_nodes.get(node_id)
            if not isinstance(node, Mapping):
                continue
            repair_generations += _coerce_nonnegative_int(node.get("repair_generation", 0))
            if str(node.get("status") or "") in _PROGRESS_ROUTE_NODE_ENDED_STATUSES:
                ended_nodes += 1
        source = "active_route_node_order"
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
        "includes_repair_generations": False,
        "repair_generations": repair_generations,
        "packet_projection_used": packet_projection_used,
        "controller_relay_only": True,
        "percent_provided": False,
        "active_subject": _progress_active_subject(ledger),
        "sealed_bodies_visible": False,
    }


def _blocker_current_effective(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> bool:
    status = str(blocker.get("status") or "")
    if status not in _ACTIVE_SEMANTIC_BLOCKER_STATUSES:
        return False
    if blocker.get("cleared_by_outcome_id"):
        return False
    if _route_node_is_noncurrent(ledger, str(blocker.get("route_node_id") or "")):
        return False
    if status == "repair_packet_open":
        repair_packet_id = str(blocker.get("repair_packet_id") or "")
        return bool(repair_packet_id) and not _packet_current_target_violation(ledger, repair_packet_id)
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
    if status == "result_blocked":
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


def _supersede_repair_open_blockers_for_route_mutation(
    ledger: dict[str, Any],
    *,
    affected_packets: list[str],
    mutation_id: str,
    disposition_id: str,
    replacement_node_id: str,
    new_route_version: Any,
) -> None:
    affected = {str(packet_id) for packet_id in affected_packets if packet_id}
    family_keys = {
        key
        for blocker in ledger.setdefault("active_blockers", {}).values()
        if isinstance(blocker, Mapping)
        and blocker.get("status") == "repair_packet_open"
        and str(blocker.get("repair_packet_id") or "") in affected
        for key in (_repair_open_blocker_family_key(blocker),)
        if any(key)
    }
    mutation_route_version = _route_version_int(new_route_version)
    for blocker in ledger.setdefault("active_blockers", {}).values():
        if not isinstance(blocker, dict):
            continue
        if blocker.get("status") != "repair_packet_open":
            continue
        repair_packet_id = str(blocker.get("repair_packet_id") or "")
        directly_affected = repair_packet_id in affected
        stale_prior_route = _repair_open_blocker_from_prior_route_version(
            blocker,
            mutation_route_version,
        )
        same_family_obsolete = (
            not directly_affected
            and not stale_prior_route
            and bool(family_keys)
            and _repair_open_blocker_family_key(blocker) in family_keys
            and _repair_open_blocker_obsolete_after_route_mutation(ledger, blocker)
        )
        if not (directly_affected or stale_prior_route or same_family_obsolete):
            continue
        _mark_repair_open_blocker_superseded_by_route_mutation(
            ledger,
            blocker,
            repair_packet_id=repair_packet_id,
            mutation_id=mutation_id,
            disposition_id=disposition_id,
            replacement_node_id=replacement_node_id,
        )


def _route_version_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _repair_open_blocker_from_prior_route_version(
    blocker: Mapping[str, Any],
    mutation_new_route_version: int | None,
) -> bool:
    if mutation_new_route_version is None:
        return False
    blocker_route_version = _route_version_int(blocker.get("route_version"))
    return blocker_route_version is not None and blocker_route_version < mutation_new_route_version


def _repair_open_blocker_family_key(blocker: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(blocker.get("blocker_class") or ""),
        str(blocker.get("route_scope") or ""),
        str(blocker.get("owner_role") or ""),
        str(blocker.get("required_recheck_role") or ""),
    )


def _repair_open_blocker_obsolete_after_route_mutation(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
) -> bool:
    repair_packet_id = str(blocker.get("repair_packet_id") or "")
    violation = _packet_current_target_violation(
        ledger,
        repair_packet_id,
        require_responsibility=False,
    )
    if violation.startswith(
        (
            "noncurrent_packet_status:",
            "stale_route_version:",
            "noncurrent_route_node:",
        )
    ):
        return True
    return _route_node_is_noncurrent(ledger, str(blocker.get("route_node_id") or ""))


def _mark_repair_open_blocker_superseded_by_route_mutation(
    ledger: dict[str, Any],
    blocker: dict[str, Any],
    *,
    repair_packet_id: str,
    mutation_id: str,
    disposition_id: str,
    replacement_node_id: str,
) -> None:
    blocker["status"] = "superseded_by_route_mutation"
    blocker["superseded_by_route_mutation_id"] = mutation_id
    blocker["superseded_by_route_mutation_disposition_id"] = disposition_id
    blocker["superseded_repair_packet_id"] = repair_packet_id
    blocker["superseded_replacement_node_id"] = replacement_node_id
    blocker["superseded_at"] = now_iso()
    packet = ledger.get("packets", {}).get(repair_packet_id)
    if isinstance(packet, dict) and packet.get("active_blocker_id") == blocker.get("blocker_id"):
        packet["active_blocker_id"] = ""
    _event(
        ledger,
        "semantic_blocker_superseded_by_route_mutation",
        blocker_id=str(blocker.get("blocker_id") or ""),
        repair_packet_id=repair_packet_id,
        mutation_id=mutation_id,
        disposition_id=disposition_id,
        replacement_node_id=replacement_node_id,
    )


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
    gate = _pending_pm_decision_gate_for_subject(ledger, blocker["subject_packet_id"])
    if gate:
        prior_blocker_id = str(gate.get("blocker_id") or "")
        prior_blocker = ledger.setdefault("active_blockers", {}).get(prior_blocker_id)
        if isinstance(prior_blocker, dict) and prior_blocker.get("status") == "awaiting_pm_decision_gate":
            prior_blocker["status"] = "retired_after_new_current_blocker"
            prior_blocker["retired_by_blocker_id"] = blocker_id
            prior_blocker["retired_at"] = now_iso()
    if isinstance(subject_packet, dict):
        subject_packet["active_blocker_id"] = blocker_id
    _event(
        ledger,
        "semantic_blocker_recorded",
        blocker_id=blocker_id,
        packet_id=blocker["packet_id"],
        required_recheck_role=blocker["required_recheck_role"],
    )
    if _is_terminal_backward_replay_blocker(blocker) and _terminal_supplemental_rounds_exhausted(ledger):
        _record_terminal_supplemental_repair_exhausted(ledger, blocker, result)
        return blocker_id
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


_REPAIR_OBLIGATION_CANNOT_BE_SATISFIED_BY = (
    "reason_text",
    "summary_text",
    "acceptance_registry_only",
    "historical_result_only",
)

_REPAIR_OBLIGATION_ALLOWED_RESOLUTIONS = (
    "fresh_repair_packet_required",
    "parent_scope_repair_required",
    "route_redesign_required",
    "waived_with_authority",
    "stop_for_user",
)

_REPAIR_OBLIGATION_DISPOSITION_BY_DECISION = {
    "repair_current_scope": "fresh_repair_packet_required",
    "repair_parent_scope": "parent_scope_repair_required",
    "redesign_route": "route_redesign_required",
    "waive_with_authority": "waived_with_authority",
    "stop_for_user": "stop_for_user",
}

_REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION = {
    "repair_current_scope": "flowguard_then_reviewer",
    "repair_parent_scope": "flowguard_then_reviewer",
    "redesign_route": "route_redesign_gate",
    "waive_with_authority": "authority_waiver_gate",
    "stop_for_user": "terminal_user_stop",
}


def _repair_obligation_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return token[:48] or "field"


def _repair_evidence_kind_for_source(source: str) -> str:
    lowered = source.lower()
    if "flowguard" in lowered:
        return "formal_flowguard_evidence"
    if "authorized_result_reads" in lowered or "authorized read" in lowered:
        return "authorized_result_read"
    if "direct" in lowered or "deliverable" in lowered or "actual outcome" in lowered:
        return "direct_deliverable_evidence"
    if "final replay" in lowered or "backward replay" in lowered or "replay" in lowered:
        return "final_replay_evidence"
    if "ordinary validation" in lowered or "validation" in lowered or "test proof" in lowered:
        return "ordinary_validation_evidence"
    if "route" in lowered or "node" in lowered or "context" in lowered:
        return "route_node_context"
    if "waiver" in lowered or "authority" in lowered:
        return "waiver_authority"
    return "current_blocker_evidence"


def _repair_evidence_obligations_for_blocker(blocker: Mapping[str, Any]) -> list[dict[str, Any]]:
    blocker_id = str(blocker.get("blocker_id") or "")
    target_result_id = str(blocker.get("target_result_id") or blocker.get("result_id") or "")
    required_recheck_role = str(blocker.get("required_recheck_role") or "")
    gate_kind = str(blocker.get("gate_kind") or "")
    blocker_class = str(blocker.get("blocker_class") or "")
    recommended_resolution = str(blocker.get("recommended_resolution") or blocker.get("reason") or "")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(source_field: str, evidence_kind: str, required_action: str, downstream_consumer: str) -> None:
        key = (source_field, evidence_kind)
        if key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "obligation_id": "",
                "source_blocker_id": blocker_id,
                "source_result_id": target_result_id,
                "source_field": source_field,
                "evidence_kind": evidence_kind,
                "required_action": required_action,
                "allowed_resolution": list(_REPAIR_OBLIGATION_ALLOWED_RESOLUTIONS),
                "downstream_consumer": downstream_consumer,
                "status": "open",
                "cannot_be_satisfied_by": list(_REPAIR_OBLIGATION_CANNOT_BE_SATISFIED_BY),
            }
        )

    for field in blocker.get("missing_required_fields") or []:
        field_name = str(field).strip()
        if not field_name:
            continue
        add(
            f"missing_required_fields.{field_name}",
            _repair_evidence_kind_for_source(field_name),
            f"produce current value for {field_name}",
            required_recheck_role or "runtime_router",
        )
    for evidence_id in blocker.get("stale_evidence_ids") or []:
        stale_id = str(evidence_id).strip()
        if not stale_id:
            continue
        add(
            f"stale_evidence_ids.{stale_id}",
            "fresh_current_evidence",
            f"replace stale evidence {stale_id} with current evidence",
            required_recheck_role or "runtime_router",
        )
    keyword_sources = (
        ("direct_deliverable_evidence", ("direct evidence", "deliverable evidence", "actual outcome", "current artifact")),
        ("final_replay_evidence", ("final replay", "backward replay", "replayable closure", "replay")),
        ("ordinary_validation_evidence", ("ordinary validation", "test proof", "validation proof", "validation")),
        ("formal_flowguard_evidence", ("flowguard", "model report", "process evidence")),
        ("reviewer_direct_evidence", ("reviewer", "human-like", "direct-source")),
        ("route_node_context", ("route/node", "route context", "node context")),
        ("waiver_authority", ("waiver", "authority")),
    )
    lowered_resolution = recommended_resolution.lower()
    for evidence_kind, keywords in keyword_sources:
        if any(keyword in lowered_resolution for keyword in keywords):
            add(
                f"recommended_resolution.{evidence_kind}",
                evidence_kind,
                f"resolve blocker recommendation for {evidence_kind}",
                required_recheck_role or "runtime_router",
            )
    if not rows and (recommended_resolution or blocker_class or gate_kind):
        add(
            "blocker.current_repair_requirement",
            _repair_evidence_kind_for_source(" ".join((recommended_resolution, blocker_class, gate_kind))),
            "produce a current repair path for the active blocker",
            required_recheck_role or "runtime_router",
        )
    for index, row in enumerate(rows, start=1):
        row["obligation_id"] = (
            f"{blocker_id or 'blocker'}.repair_obligation.{index:03d}."
            f"{_repair_obligation_token(str(row['evidence_kind']))}"
        )
    return rows


def _repair_evidence_obligations_from_packet(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    try:
        payload = _strict_json_object_from_body(str(packet.get("body", "")))
    except BlackBoxRuntimeError:
        return []
    rows = payload.get("repair_evidence_obligations")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping) and str(row.get("obligation_id") or "")]


def _repair_obligation_disposition_minimal_shape(
    obligations: list[Mapping[str, Any]],
    decision: str,
) -> list[dict[str, Any]]:
    disposition = _REPAIR_OBLIGATION_DISPOSITION_BY_DECISION.get(decision, "fresh_repair_packet_required")
    return_gate = _REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION.get(decision, "flowguard_then_reviewer")
    return [
        {
            "obligation_id": str(row.get("obligation_id") or ""),
            "evidence_kind": str(row.get("evidence_kind") or "current_blocker_evidence"),
            "disposition": disposition,
            "return_gate": return_gate,
        }
        for row in obligations
    ]


def _repair_obligation_context_for_decision(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    decision_id: str,
) -> dict[str, Any]:
    decision = ledger.get("pm_repair_decisions", {}).get(decision_id, {})
    obligations = (
        decision.get("repair_evidence_obligations")
        if isinstance(decision, Mapping) and isinstance(decision.get("repair_evidence_obligations"), list)
        else _repair_evidence_obligations_for_blocker(blocker)
    )
    disposition = (
        decision.get("repair_obligation_disposition")
        if isinstance(decision, Mapping) and isinstance(decision.get("repair_obligation_disposition"), list)
        else []
    )
    return {
        "schema_version": "black_box_flowpilot.repair_obligation_context.v1",
        "blocker_id": str(blocker.get("blocker_id") or ""),
        "pm_repair_decision_id": decision_id,
        "repair_evidence_obligations": _copy_jsonable(obligations),
        "repair_obligation_disposition": _copy_jsonable(disposition),
        "rule": (
            "These obligations came from the active blocker. Fresh repair, FlowGuard recheck, "
            "and Reviewer recheck must consume them; reason text or acceptance registry entries alone do not close them."
        ),
    }


def _attach_repair_obligation_context_to_packet(
    ledger: dict[str, Any],
    packet_id: str,
    blocker: Mapping[str, Any],
    decision_id: str,
) -> None:
    context = _repair_obligation_context_for_decision(ledger, blocker, decision_id)
    obligations = context.get("repair_evidence_obligations")
    if not obligations:
        return
    packet = _require(ledger["packets"], packet_id, "packet")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if not isinstance(envelope, dict):
        raise BlackBoxRuntimeError("packet envelope is missing")
    payload = _parse_json_object(str(packet.get("body", "")))
    payload["repair_obligation_context"] = context
    payload["repair_evidence_obligations"] = context["repair_evidence_obligations"]
    payload["repair_obligation_disposition"] = context["repair_obligation_disposition"]
    body = json.dumps(payload, indent=2, sort_keys=True)
    handoff_contract = _build_current_handoff_contract(
        ledger,
        envelope,
        _packet_authorized_result_reads(packet),
    )
    envelope["current_handoff_contract"] = handoff_contract
    body = _packet_body_with_current_handoff_contract(body, handoff_contract, replace_existing=True)
    packet["body"] = body
    envelope["body_hash"] = hash_text(body)


def _pm_repair_obligation_disposition_violation(
    packet: Mapping[str, Any],
    payload: Mapping[str, Any],
    decision: str,
) -> PacketResultContractCheck | None:
    obligations = _repair_evidence_obligations_from_packet(packet)
    if not obligations:
        return None
    expected_ids = [str(row.get("obligation_id") or "") for row in obligations]
    expected_set = set(expected_ids)
    rows = payload.get("repair_obligation_disposition")
    minimal_shape = {
        "decision": decision or "repair_current_scope",
        "reason": "Concrete PM repair reason.",
        "repair_obligation_disposition": _repair_obligation_disposition_minimal_shape(
            obligations,
            decision or "repair_current_scope",
        ),
    }
    if not isinstance(rows, list) or not rows:
        return _contract_block(
            packet,
            "PM repair decision must disposition every repair_evidence_obligations row",
            missing_required_fields=("repair_obligation_disposition",),
            required_result_body_fields=tuple(
                dict.fromkeys((*_packet_result_required_fields(packet), "repair_obligation_disposition"))
            ),
            failed_field_path="repair_obligation_disposition",
            branch_minimal_valid_shape=minimal_shape,
        )
    seen: set[str] = set()
    unknown: list[str] = []
    duplicates: list[str] = []
    missing_fields: list[str] = []
    stale_refs: list[str] = []
    unsupported: list[str] = []
    stale_evidence_ids = {
        str(item)
        for item in (_strict_json_object_from_body(str(packet.get("body", ""))).get("stale_evidence_ids") or [])
        if str(item)
    }
    expected_disposition = _REPAIR_OBLIGATION_DISPOSITION_BY_DECISION.get(decision, "")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            missing_fields.append(f"repair_obligation_disposition[{index}].obligation_id")
            continue
        obligation_id = str(row.get("obligation_id") or "")
        if not obligation_id:
            missing_fields.append(f"repair_obligation_disposition[{index}].obligation_id")
            continue
        if obligation_id in seen:
            duplicates.append(obligation_id)
        seen.add(obligation_id)
        if obligation_id not in expected_set:
            unknown.append(obligation_id)
        for field in ("disposition", "return_gate", "evidence_kind"):
            if not str(row.get(field) or ""):
                missing_fields.append(f"repair_obligation_disposition[{index}].{field}")
        disposition = _normalize_outcome_token(row.get("disposition"))
        if disposition in {
            "already_satisfied",
            "satisfied",
            "satisfied_by_reason",
            "reason_text",
            "summary_text",
            "acceptance_registry_only",
            "historical_result_only",
        }:
            unsupported.append(f"repair_obligation_disposition[{index}].disposition={disposition}")
        if expected_disposition and disposition != expected_disposition:
            unsupported.append(
                f"repair_obligation_disposition[{index}].disposition must be {expected_disposition} for decision={decision}"
            )
        for forbidden_field in ("reason", "summary", "acceptance_registry"):
            if forbidden_field in row:
                unsupported.append(f"repair_obligation_disposition[{index}].{forbidden_field}")
        refs = row.get("evidence_refs")
        if isinstance(refs, list):
            stale_refs.extend(str(ref) for ref in refs if str(ref) in stale_evidence_ids)
    missing_ids = sorted(expected_set - seen)
    if missing_ids or unknown or duplicates or missing_fields or stale_refs or unsupported:
        pieces: list[str] = []
        if missing_ids:
            pieces.append("missing obligation id(s): " + ", ".join(missing_ids))
        if unknown:
            pieces.append("unknown obligation id(s): " + ", ".join(sorted(set(unknown))))
        if duplicates:
            pieces.append("duplicate obligation id(s): " + ", ".join(sorted(set(duplicates))))
        if missing_fields:
            pieces.append("missing required field(s): " + ", ".join(dict.fromkeys(missing_fields)))
        if stale_refs:
            pieces.append("stale evidence ref(s): " + ", ".join(sorted(set(stale_refs))))
        if unsupported:
            pieces.append("unsupported obligation disposition(s): " + "; ".join(dict.fromkeys(unsupported)))
        return _contract_block(
            packet,
            "; ".join(pieces),
            missing_required_fields=tuple(
                dict.fromkeys(
                    [
                        "repair_obligation_disposition",
                        *missing_fields,
                        *(["repair_obligation_disposition[].obligation_id"] if missing_ids or unknown or duplicates else []),
                    ]
                )
            ),
            required_result_body_fields=tuple(
                dict.fromkeys((*_packet_result_required_fields(packet), "repair_obligation_disposition"))
            ),
            failed_field_path="repair_obligation_disposition",
            branch_minimal_valid_shape=minimal_shape,
        )
    return None


def _ensure_pm_repair_decision_packet_for_blocker(ledger: dict[str, Any], blocker_id: str) -> str:
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if blocker.get("status") not in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
        raise BlackBoxRuntimeError(
            f"cannot issue PM repair decision packet for blocker {blocker_id} in status {blocker.get('status')}"
        )
    repair_loop_review = _repair_loop_break_glass_review(ledger, blocker)
    if repair_loop_review.get("threshold_exceeded"):
        _supersede_same_family_pm_repair_packets_for_break_glass(ledger, repair_loop_review)
        blocker["pm_repair_packet_id"] = ""
        if not _repair_loop_break_glass_event_recorded(ledger, blocker_id):
            _event(
                ledger,
                "repair_loop_break_glass_required",
                blocker_id=blocker_id,
                family_key=str(repair_loop_review.get("family_key") or ""),
                attempt_count=int(repair_loop_review.get("attempt_count", 0) or 0),
                threshold=int(repair_loop_review.get("threshold", _REPAIR_LOOP_BREAK_GLASS_THRESHOLD) or 0),
            )
        return ""
    existing = _find_packet(
        ledger,
        packet_kind="pm_repair_decision",
        subject_id=blocker_id,
        reusable_statuses={"open", "assigned", "acknowledged", "result_submitted"},
    )
    if existing:
        if not _current_pm_repair_decision_packet_reusable(existing):
            existing = None
        else:
            existing_envelope = existing.get("envelope", {}) if isinstance(existing.get("envelope"), Mapping) else {}
            if (
                str(existing.get("repair_blocker_id") or "") != blocker_id
                or str(existing_envelope.get("repair_blocker_id") or "") != blocker_id
            ):
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
    repair_target_route_node_id = str(
        repair_target_envelope.get("route_node_id") or blocker.get("route_node_id") or ""
    )
    parent_repair_source_node_id = ""
    if repair_target_route_node_id and repair_target_route_node_id in ledger.get("route_nodes", {}):
        parent_repair_source_node_id = _nearest_parent_route_node_id(ledger, repair_target_route_node_id)
    repeat_context = _blocker_repeat_context(ledger, blocker)
    authorized_result_reads = _blocker_authorized_result_reads(
        ledger,
        blocker,
        allowed_roles=["pm"],
        purpose="blocking_report_for_pm_repair_decision",
        required_before_submit=True,
    )
    terminal_supplemental_required = _is_terminal_backward_replay_blocker(blocker)
    supplemental_state = _terminal_supplemental_state_view(ledger)
    next_supplemental_round = int(supplemental_state.get("current_round", 0) or 0) + 1
    repair_evidence_obligations = _repair_evidence_obligations_for_blocker(blocker)
    required_result_fields = ["decision", "reason", "target_blocker_id", "next_action"]
    minimal_valid_shape: dict[str, Any] = {
        "decision": "repair_current_scope",
        "reason": "Concrete PM repair reason.",
        "target_blocker_id": blocker_id,
        "next_action": "repair_current_scope",
    }
    conditional_required_fields: dict[str, list[str]] = {
        "repair_parent_scope": ["repair_parent_scope_contract"],
        "redesign_route": ["route_plan"],
        "waive_with_authority": ["authority_ref"],
    }
    if repair_evidence_obligations:
        required_result_fields.append("repair_obligation_disposition when repair_evidence_obligations exist")
        for branch in ("repair_current_scope", "repair_parent_scope", "redesign_route", "waive_with_authority", "stop_for_user"):
            conditional_required_fields.setdefault(branch, []).append("repair_obligation_disposition")
        minimal_valid_shape["repair_obligation_disposition"] = _repair_obligation_disposition_minimal_shape(
            repair_evidence_obligations,
            "repair_current_scope",
        )
    if terminal_supplemental_required:
        required_result_fields.append("supplemental_repair_contract when terminal repair continues")
        conditional_required_fields["repair_current_scope"] = ["supplemental_repair_contract"]
        conditional_required_fields["repair_parent_scope"] = [
            "repair_parent_scope_contract",
            "supplemental_repair_contract",
        ]
        conditional_required_fields["redesign_route"] = ["route_plan", "supplemental_repair_contract"]
        supplemental_contract_shape = _terminal_supplemental_repair_contract_current_shape(
            ledger,
            blocker,
            round_number=next_supplemental_round,
        )
        terminal_route_plan_shape = packet_result_contracts.strict_route_plan_minimal_shape()
        terminal_route_plan_shape = _project_supplemental_repair_ids_onto_route_plan(
            terminal_route_plan_shape,
            supplemental_contract_shape,
        )
        minimal_valid_shape = {
            "decision": "redesign_route",
            "reason": "Concrete PM terminal supplemental repair reason.",
            "target_blocker_id": blocker_id,
            "next_action": "redesign_route",
            "supplemental_repair_contract": supplemental_contract_shape,
            "route_plan": terminal_route_plan_shape,
        }
        if repair_evidence_obligations:
            minimal_valid_shape["repair_obligation_disposition"] = _repair_obligation_disposition_minimal_shape(
                repair_evidence_obligations,
                "redesign_route",
            )
            conditional_required_fields["repair_current_scope"] = [
                "supplemental_repair_contract",
                "repair_obligation_disposition",
            ]
            conditional_required_fields["repair_parent_scope"] = [
                "repair_parent_scope_contract",
                "supplemental_repair_contract",
                "repair_obligation_disposition",
            ]
            conditional_required_fields["redesign_route"] = [
                "route_plan",
                "supplemental_repair_contract",
                "repair_obligation_disposition",
            ]
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
                "repair_evidence_obligations": repair_evidence_obligations,
                "repair_target": {
                    "packet_id": str(blocker.get("repair_target_packet_id") or ""),
                    "objective": str(repair_target_envelope.get("objective") or ""),
                    "packet_kind": str(repair_target_envelope.get("packet_kind", "task")),
                    "responsibility": str(repair_target_envelope.get("responsibility") or ""),
                    "required_output_type": str(repair_target_envelope.get("required_output_type") or ""),
                    "output_contract": _copy_jsonable(repair_target_envelope.get("output_contract") or {}),
                    "acceptance_criteria": list(repair_target_envelope.get("acceptance_criteria") or []),
                    "route_node_id": repair_target_route_node_id,
                    "route_scope": str(repair_target_envelope.get("route_scope") or blocker.get("route_scope") or ""),
                },
                "repeat_context": repeat_context,
                "allowed_decisions": sorted(_PM_REPAIR_DECISIONS),
                "contract_family_id": "pm_repair_decision.pm_repair_decision",
                "required_result_body_fields": required_result_fields,
                "forbidden_fields": [
                    "authority",
                    "summary",
                    "repair_decision",
                    "pm_repair_decision",
                    "supplemental_contract",
                    "repair_contract",
                    "terminal_repair_contract",
                ],
                "conditional_required_fields": conditional_required_fields,
                "minimal_valid_shape": minimal_valid_shape,
                "repair_parent_scope_contract_shape": _parent_repair_scope_contract_minimal_shape(
                    parent_repair_source_node_id or repair_target_route_node_id or "parent-node-id"
                ),
                "repair_decision_contract": {
                    "pm_must_choose_allowed_decision": True,
                    "required_json_shape": "Use this packet's minimal_valid_shape as the current required JSON shape.",
                    "top_level_decision_only": True,
                    "nested_repair_decision_wrappers_forbidden": True,
                    "nonterminal_repairs_require_runtime_fresh_packet": True,
                    "redesign_route_requires_route_plan": True,
                    "repair_parent_scope_requires_repair_parent_scope_contract": True,
                    "repair_parent_scope_contract_requires_repair_child_specs": True,
                    "repair_parent_scope_inherited_children_are_history_only": True,
                    "waive_with_authority_requires_authority_ref": True,
                    "pm_must_account_for_recommended_resolution": bool(blocker.get("recommended_resolution")),
                    "pm_does_not_mark_blocked_gate_passed_by_text": True,
                    "repair_summary_alone_is_not_completion": True,
                    "pm_must_disposition_every_repair_evidence_obligation": bool(repair_evidence_obligations),
                    "reason_text_cannot_satisfy_repair_evidence_obligations": bool(repair_evidence_obligations),
                    "acceptance_registry_only_cannot_satisfy_repair_evidence_obligations": bool(
                        repair_evidence_obligations
                    ),
                    "repeat_context_is_advisory_not_terminal": True,
                    "terminal_supplemental_repair_required": terminal_supplemental_required,
                    "terminal_supplemental_repair_next_round": next_supplemental_round
                    if terminal_supplemental_required
                    else 0,
                    "terminal_supplemental_repair_max_rounds": TERMINAL_SUPPLEMENTAL_REPAIR_MAX_ROUNDS,
                },
                "instruction": (
                    "Return exactly one structured JSON object with top-level decision, reason, target_blocker_id, "
                    "and next_action. target_blocker_id must equal this packet's blocker_id; next_action must be "
                    "the selected current repair action. Use this "
                    "packet's minimal_valid_shape as the authoritative current example for the selected branch; "
                    "do not use a fixed decision/reason-only shape when the skeleton contains more fields. "
                    "Before deciding, use every required authorized input material delivered by open-packet as the "
                    "source of the concrete failure. "
                    "Use repair_parent_scope only when the explicit parent scope should be replaced, and include "
                    "repair_parent_scope_contract with source_parent_node_id, inherit_existing_children=true, and "
                    "non-empty repair_child_specs. The old child nodes become inherited history only; PM must define "
                    "new current repair child specs for the replacement parent. Use redesign_route only with a strict "
                    "route_plan object; complex redesigns must preserve parent/module grouping instead of returning "
                    "flat all-leaf peer nodes. Use waive_with_authority only with authority_ref. "
                    "Do not wrap the decision inside repair_decision, pm_repair_decision, prose, or any legacy shape. "
                    "PM chooses the repair route using the blocker recommendation and target contract. PM does not "
                    "impersonate the blocked reviewer, system validation check, FlowGuard pass, or worker deliverable. "
                    "When repair_evidence_obligations is non-empty, include repair_obligation_disposition with one "
                    "row for every obligation_id; do not satisfy any row with reason text, summary text, old evidence, "
                    "or acceptance-registry-only claims. "
                    "For terminal backward replay blockers, continuing repair decisions must include exactly one "
                    "supplemental_repair_contract that cites the frozen contract hash and current Reviewer gap report."
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
        repair_blocker_id=blocker_id,
        authorized_result_reads=authorized_result_reads,
    )
    blocker["pm_repair_packet_id"] = packet_id
    return packet_id


def _parse_pm_repair_decision_body(
    body: str,
) -> tuple[str, str, str, dict[str, Any] | None, dict[str, Any] | None]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BlackBoxRuntimeError("PM repair decision requires a structured JSON object") from exc
    if not isinstance(payload, dict):
        raise BlackBoxRuntimeError("PM repair decision requires a structured JSON object")
    decision = _normalize_outcome_token(payload.get("decision"))
    reason = str(payload.get("reason") or "")
    target_blocker_id = str(payload.get("target_blocker_id") or "").strip()
    next_action = _normalize_outcome_token(payload.get("next_action"))
    if decision in _REMOVED_PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("PM repair decision uses a removed decision; request a current five-choice decision")
    if decision not in _PM_REPAIR_DECISIONS:
        raise BlackBoxRuntimeError("PM repair decision requires an explicit allowed decision")
    if not reason:
        raise BlackBoxRuntimeError("PM repair decision requires a top-level reason")
    if not target_blocker_id:
        raise BlackBoxRuntimeError("PM repair decision requires target_blocker_id")
    if next_action != decision:
        raise BlackBoxRuntimeError("PM repair decision next_action must match decision")
    authority_ref = str(payload.get("authority_ref") or "")
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
    parent_repair_contract: dict[str, Any] | None = None
    if decision == "repair_parent_scope":
        parent_repair_contract = _parse_parent_repair_scope_contract_payload(payload)
    return decision, reason, authority_ref, route_plan, parent_repair_contract


def _parse_pm_flowguard_acceptance_body(body: str) -> tuple[str, str, str, str, dict[str, Any] | None]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires a structured JSON object") from exc
    if not isinstance(payload, dict):
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires a structured JSON object")
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision in _REMOVED_PM_FLOWGUARD_ACCEPTANCE_DECISIONS:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance does not support optional or uncertain FlowGuard decisions")
    if decision not in _PM_FLOWGUARD_ACCEPTANCE_DECISIONS:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires an explicit allowed decision")
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires a top-level reason")
    absorption = str(payload.get("flowguard_absorption") or "").strip()
    if not absorption:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires concrete flowguard_absorption")
    accepted_flowguard_result_id = str(payload.get("accepted_flowguard_result_id") or "").strip()
    if not accepted_flowguard_result_id:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires accepted_flowguard_result_id")
    route_plan: dict[str, Any] | None = None
    if decision == "redesign_route":
        raw_route_plan = payload.get("route_plan")
        if not isinstance(raw_route_plan, dict):
            raise BlackBoxRuntimeError("PM FlowGuard acceptance redesign_route requires a strict route_plan object")
        route_plan = _parse_strict_route_plan(json.dumps(raw_route_plan, sort_keys=True))
        _normalize_strict_route_plan_nodes(route_plan)
        route_plan = _copy_jsonable(route_plan)
    return decision, reason, absorption, accepted_flowguard_result_id, route_plan


def _record_pm_repair_decision_from_packet_result(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    decision: str | None = None,
    reason: str | None = None,
    authority_ref: str = "",
    route_plan: dict[str, Any] | None = None,
    parent_repair_contract: dict[str, Any] | None = None,
) -> str:
    blocker_id = str(packet["envelope"].get("subject_id") or "")
    blocker = _require(ledger.setdefault("active_blockers", {}), blocker_id, "semantic blocker")
    if decision is None:
        decision, reason, authority_ref, route_plan, parent_repair_contract = _parse_pm_repair_decision_body(
            str(result.get("body", ""))
        )
    decision = str(decision)
    reason = str(reason or "")
    payload = _parse_json_object(str(result.get("body", "")))
    repair_evidence_obligations = _repair_evidence_obligations_from_packet(packet)
    repair_obligation_disposition = (
        payload.get("repair_obligation_disposition")
        if isinstance(payload.get("repair_obligation_disposition"), list)
        else []
    )
    supplemental_contract: dict[str, Any] | None = None
    if _terminal_supplemental_repair_required(ledger, packet, decision):
        supplemental_contract = _parse_terminal_supplemental_repair_contract_payload(
            ledger,
            packet,
            payload,
            decision=decision,
            route_plan=route_plan,
        )
    decision_id = _next_id(ledger, "pm_repair_decision")
    parent_repair_contract_id = ""
    if parent_repair_contract is not None:
        parent_repair_contract_id = _next_id(ledger, "parent_repair_contract")
        parent_repair_contract = _copy_jsonable(parent_repair_contract)
        parent_repair_contract.update(
            {
                "contract_id": parent_repair_contract_id,
                "decision_id": decision_id,
                "blocker_id": blocker_id,
                "packet_id": packet["packet_id"],
                "result_id": result["result_id"],
                "status": "active",
                "created_at": now_iso(),
            }
        )
    row = {
        "decision_id": decision_id,
        "blocker_id": blocker_id,
        "packet_id": packet["packet_id"],
        "result_id": result["result_id"],
        "decision": decision,
        "reason": reason,
        "authority_ref": authority_ref,
        "repair_evidence_obligations": _copy_jsonable(repair_evidence_obligations),
        "repair_obligation_disposition": _copy_jsonable(repair_obligation_disposition),
        "route_plan": route_plan,
        "parent_repair_scope_contract_id": parent_repair_contract_id,
        "repair_parent_scope_contract": _copy_jsonable(parent_repair_contract) if parent_repair_contract else None,
        "supplemental_repair_contract_id": str(supplemental_contract.get("contract_id") or "")
        if isinstance(supplemental_contract, Mapping)
        else "",
        "created_at": now_iso(),
    }
    ledger.setdefault("pm_repair_decisions", {})[decision_id] = row
    if parent_repair_contract is not None:
        ledger.setdefault("parent_repair_scope_contracts", {})[parent_repair_contract_id] = parent_repair_contract
    if supplemental_contract is not None:
        _record_terminal_supplemental_repair_contract(
            ledger,
            contract=supplemental_contract,
            decision_id=decision_id,
            packet=packet,
            result=result,
        )
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
    if decision in _GATED_PM_REPAIR_DECISIONS:
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
            route_plan=route_plan,
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
    route_plan: Mapping[str, Any] | None = None,
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
        "route_plan": _copy_jsonable(route_plan) if isinstance(route_plan, Mapping) else None,
        "flowguard_order_id": "",
        "pm_flowguard_acceptance_packet_id": "",
        "pm_flowguard_acceptance_result_id": "",
        "review_subject_packet_id": "",
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
    terminal_statuses = {"applied", "rejected", "cancelled", "flowguard_blocked", "pm_blocked", "pm_stopped", "replaced_by_pm_flowguard_acceptance"}
    for gate in ledger.get("pm_decision_gates", {}).values():
        if not isinstance(gate, dict):
            continue
        if gate.get("source_packet_id") != subject_packet_id and gate.get("review_subject_packet_id") != subject_packet_id:
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
    gate["status"] = "awaiting_pm_flowguard_acceptance"
    gate["updated_at"] = now_iso()
    _ensure_pm_flowguard_acceptance_packet_for_gate(ledger, gate)


def _mark_pm_decision_gate_flowguard_blocked(
    ledger: dict[str, Any],
    subject_packet_id: str,
    result_id: str,
) -> None:
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if not gate:
        return
    gate["flowguard_block_result_id"] = result_id
    for order_id, order in ledger.get("flowguard_work_orders", {}).items():
        if not isinstance(order, Mapping):
            continue
        if str(order.get("subject_id") or "") == subject_packet_id and str(order.get("proof_result_id") or "") == result_id:
            gate["flowguard_order_id"] = str(order_id)
            break
    gate["status"] = "flowguard_blocked"
    gate["updated_at"] = now_iso()


def _mark_pm_decision_gate_pm_absorbed(
    ledger: dict[str, Any],
    gate: dict[str, Any],
    packet_id: str,
    result_id: str,
) -> None:
    gate["pm_flowguard_acceptance_packet_id"] = packet_id
    gate["pm_flowguard_acceptance_result_id"] = result_id
    gate["review_subject_packet_id"] = packet_id
    gate["status"] = "awaiting_review"
    gate["updated_at"] = now_iso()
    _event(
        ledger,
        "pm_flowguard_acceptance_recorded",
        gate_id=str(gate.get("gate_id") or ""),
        packet_id=packet_id,
        result_id=result_id,
    )


def _flowguard_result_id_for_gate(ledger: Mapping[str, Any], gate: Mapping[str, Any]) -> str:
    order_id = str(gate.get("flowguard_order_id") or "")
    order = ledger.get("flowguard_work_orders", {}).get(order_id)
    if not isinstance(order, Mapping):
        return ""
    return str(order.get("proof_result_id") or order.get("producer_result_id") or "")


def _ensure_pm_flowguard_acceptance_packet_for_gate(
    ledger: dict[str, Any],
    gate: Mapping[str, Any],
) -> str:
    gate_id = str(gate.get("gate_id") or "")
    if not gate_id:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires gate_id")
    existing = _find_packet(
        ledger,
        packet_kind="pm_flowguard_acceptance",
        subject_id=gate_id,
    )
    if existing:
        return str(existing["packet_id"])
    source_packet_id = str(gate.get("source_packet_id") or "")
    source_result_id = str(gate.get("source_result_id") or "")
    flowguard_result_id = _flowguard_result_id_for_gate(ledger, gate)
    if not source_packet_id or not source_result_id or not flowguard_result_id:
        raise BlackBoxRuntimeError("PM FlowGuard acceptance requires source and FlowGuard result evidence")
    source_packet = _require(ledger["packets"], source_packet_id, "PM decision source packet")
    source_envelope = source_packet.get("envelope", {}) if isinstance(source_packet.get("envelope"), Mapping) else {}
    reads = [
        _authorized_read_for_result(
            ledger,
            source_result_id,
            allowed_roles=["pm"],
            purpose="structural_pm_decision_for_flowguard_absorption",
            required_before_submit=True,
        ),
        _authorized_read_for_result(
            ledger,
            flowguard_result_id,
            allowed_roles=["pm"],
            purpose="flowguard_report_for_pm_absorption",
            required_before_submit=True,
        ),
    ]
    body_payload = {
        "schema_version": "black_box_flowpilot.pm_flowguard_acceptance_packet.v1",
        "gate_id": gate_id,
        "gate_kind": str(gate.get("gate_kind") or ""),
        "source_packet_id": source_packet_id,
        "source_result_id": source_result_id,
        "flowguard_order_id": str(gate.get("flowguard_order_id") or ""),
        "flowguard_result_id": flowguard_result_id,
        **_staged_effect_public_reference(gate),
        "allowed_decisions": ["accept", "redesign_route", "block", "stop_for_user"],
        "instruction": (
            "Read the current staged structural decision and the current FlowGuard report. "
            "Return one strict JSON result. Use decision=accept only after absorbing the FlowGuard findings; "
            "use decision=redesign_route with a strict route_plan when the report changes the route; "
            "do not replace a hierarchical route with a complex flat all-leaf route_plan, and keep node-entry "
            "splits under a replacement parent/module scope; "
            "use decision=block or stop_for_user when the structural change cannot proceed. "
            "There is no optional or uncertain FlowGuard branch."
        ),
    }
    return issue_task_packet(
        ledger,
        "pm",
        f"Absorb FlowGuard report for structural decision {gate_id}",
        json.dumps(body_payload, indent=2, sort_keys=True),
        required_flowguard_target=str(source_envelope.get("required_flowguard_target") or REQUIRED_FLOWGUARD_TARGET),
        packet_kind="pm_flowguard_acceptance",
        subject_id=gate_id,
        target_result_id=flowguard_result_id,
        route_node_id=str(gate.get("node_id") or source_envelope.get("route_node_id") or ""),
        route_scope=PM_FLOWGUARD_ACCEPTANCE_SCOPE,
        acceptance_criteria=[
            "PM absorbed the current FlowGuard report before Reviewer review.",
            "PM did not treat FlowGuard as route authority or worker release.",
            "Any rewritten route plan uses the strict current route_plan shape.",
        ],
        authorized_result_reads=reads,
    )


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
        route_plan = gate.get("route_plan")
        decision_id = str(gate.get("decision_id") or "")
        if isinstance(route_plan, Mapping) and decision_id in ledger.get("pm_repair_decisions", {}):
            ledger["pm_repair_decisions"][decision_id]["route_plan"] = _copy_jsonable(route_plan)
        _apply_pm_repair_decision(
            ledger,
            str(gate.get("blocker_id") or ""),
            decision_id,
        )
    elif gate_kind == "route_redesign":
        route_plan = gate.get("route_plan")
        if not isinstance(route_plan, Mapping):
            raise BlackBoxRuntimeError("route_redesign PM decision gate requires route_plan")
        blocker_id = str(gate.get("blocker_id") or "")
        blocker = ledger.get("active_blockers", {}).get(blocker_id)
        _materialize_route_redesign(
            ledger,
            route_plan=route_plan,
            source_result_id=str(gate.get("source_result_id") or ""),
            disposition_id=str(gate.get("gate_id") or ""),
            reason=str(gate.get("reason") or "pm_route_redesign_gate_applied"),
            blocker=blocker if isinstance(blocker, Mapping) else None,
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
    repair_obligation_context = _repair_obligation_context_for_decision(ledger, blocker, decision_id)
    body_payload: dict[str, Any] = {
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
            "must_satisfy_repair_evidence_obligations": bool(
                repair_obligation_context.get("repair_evidence_obligations")
            ),
            "may_return_new_blocker_if_repair_is_not_possible": True,
            "required_recheck_role": blocker.get("required_recheck_role", ""),
        },
        "instruction": (
            "Produce fresh repaired evidence for this current replacement packet. "
            "The source artifact is context only, not passing evidence. Submit the corrected deliverable "
            "or a new structured blocker. If authorized Reviewer materials include a Quality score "
            "line, quantitative required/delivered/gap finding, or target: 9/10 guidance, read that "
            "context and repair toward the 9/10 target inside this packet boundary without expanding "
            "scope beyond the packet."
        ),
    }
    if repair_obligation_context.get("repair_evidence_obligations"):
        body_payload["repair_obligation_context"] = repair_obligation_context
        body_payload["repair_evidence_obligations"] = _copy_jsonable(
            repair_obligation_context["repair_evidence_obligations"]
        )
        body_payload["repair_obligation_disposition"] = _copy_jsonable(
            repair_obligation_context["repair_obligation_disposition"]
        )
    route_scope = str(target_envelope.get("route_scope") or "")
    if packet_kind == "review" and route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE:
        family_id = "review.terminal_backward_replay"
        body_payload.update(
            {
                "schema_version": "black_box_flowpilot.terminal_backward_replay_repair_packet.v1",
                "route_version": target_envelope.get("route_version") or ledger.get("active_route_version"),
                "validation_evidence_id": str(
                    ledger.get("latest_validation_evidence_id") or target_envelope.get("subject_id") or ""
                ),
                "final_route_wide_gate_ledger_status": _copy_jsonable(ledger.get("final_route_wide_gate_ledger") or {}),
                "final_requirement_evidence_matrix_status": _copy_jsonable(
                    ledger.get("final_requirement_evidence_matrix") or {}
                ),
                "segment_targets": _terminal_backward_replay_segment_targets(ledger),
                "contract_family_id": family_id,
                "required_result_body_fields": list(packet_result_contracts.required_fields_for_family(family_id)),
                "required_child_fields": list(packet_result_contracts.required_child_fields_for_family(family_id)),
                "explicit_array_fields": list(packet_result_contracts.explicit_array_fields_for_family(family_id)),
                "non_empty_array_fields": list(packet_result_contracts.non_empty_array_fields_for_family(family_id)),
                "forbidden_fields": list(packet_result_contracts.forbidden_fields_for_family(family_id)),
                "minimal_valid_shape": packet_result_contracts.minimal_valid_shape_for_family(family_id),
                "repair_completion_contract": {
                    **body_payload["repair_completion_contract"],
                    "must_submit_terminal_backward_replay_result": True,
                    "must_cover_runtime_issued_segment_targets": True,
                    "passing_replay_required_before_final_closure": True,
                },
                "instruction": (
                    "Repair the current terminal backward replay blocker, then rerun terminal backward replay from "
                    "the delivered product against every runtime-issued segment target. Submit a current terminal "
                    "backward replay result. Do not close from the source artifact, PM summary, or previous blocked "
                    "review."
                ),
            }
        )
    packet_id = issue_task_packet(
        ledger,
        repair_role,
        f"Repair current packet scope for blocker {blocker['blocker_id']}",
        json.dumps(body_payload, indent=2, sort_keys=True),
        required_flowguard_target=str(target_envelope.get("required_flowguard_target") or ""),
        packet_kind=packet_kind,
        subject_id=target_packet_id if packet_kind != "task" else "",
        target_result_id=str(blocker.get("target_result_id") or ""),
        route_node_id=str(target_envelope.get("route_node_id") or ""),
        route_scope=route_scope,
        acceptance_criteria=list(target_envelope.get("acceptance_criteria") or []),
        node_context_package_id=str(target_envelope.get("node_context_package_id") or ""),
        repair_blocker_id=str(blocker["blocker_id"]),
        authorized_result_reads=_blocker_authorized_result_reads(
            ledger,
            blocker,
            allowed_roles=[repair_role],
            purpose="blocking_report_for_repair_work",
            required_before_submit=True,
        ),
    )
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
    parent_repair_contract: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    before_packets = set(ledger.get("packets", {}))
    replacement_id = _replace_route_node_for_repair(
        ledger,
        source_node_id,
        disposition_id=decision_id,
        reason=reason,
        supersede_descendants=supersede_descendants,
        parent_repair_contract=parent_repair_contract,
    )
    fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=replacement_id, before_ids=before_packets)
    if not fresh_packet_id:
        replacement_node = ledger.get("route_nodes", {}).get(replacement_id, {})
        if isinstance(replacement_node, Mapping):
            for child_id in _route_node_child_ids(replacement_node):
                fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=child_id, before_ids=before_packets)
                if fresh_packet_id:
                    break
    if not fresh_packet_id:
        raise BlackBoxRuntimeError("repair scope replacement did not create a fresh executable packet")
    _bind_packet_repair_blocker_identity(ledger, fresh_packet_id, str(blocker["blocker_id"]))
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
    _attach_repair_obligation_context_to_packet(ledger, fresh_packet_id, blocker, decision_id)
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


def _materialize_route_redesign(
    ledger: dict[str, Any],
    *,
    route_plan: Mapping[str, Any],
    source_result_id: str,
    disposition_id: str,
    reason: str,
    blocker: Mapping[str, Any] | None = None,
) -> tuple[list[str], str]:
    parsed_route_plan = _parse_strict_route_plan(json.dumps(route_plan, sort_keys=True))
    node_specs = _normalize_strict_route_plan_nodes(parsed_route_plan)
    _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    old_node_ids = [
        str(node_id)
        for node_id, node in ledger.get("route_nodes", {}).items()
        if isinstance(node, Mapping) and int(node.get("route_version") or 0) == old_version
    ]
    affected_packets: list[str] = []
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
        affected_packets.append(str(packet.get("packet_id") or ""))
    for node_id in old_node_ids:
        node = ledger.get("route_nodes", {}).get(node_id)
        if isinstance(node, dict):
            node["status"] = "superseded"
            node["superseded_by"] = f"route-v{new_version}"
            node.setdefault("stale_evidence", []).append(disposition_id)
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
            "acceptance_item_ids": [str(item) for item in spec.get("acceptance_item_ids") or []],
            "skill_standard_obligation_ids": [str(item) for item in spec.get("skill_standard_obligation_ids") or []],
            "supplemental_repair_contract_ids": [str(item) for item in spec.get("supplemental_repair_contract_ids") or []],
            "supplemental_repair_item_ids": [str(item) for item in spec.get("supplemental_repair_item_ids") or []],
            "superseded_by": "",
            "stale_evidence": [],
            "created_from_result_id": source_result_id,
            "route_plan_schema_version": parsed_route_plan.get("schema_version", ""),
            "created_at": now_iso(),
        }
        materialized_ids.append(node_id)

    ledger.setdefault("routes", {})[str(new_version)] = {
        "route_version": new_version,
        "route_id": f"route-v{new_version}",
        "title": "Redesigned route",
        "status": "active",
        "nodes": [str(spec["title"]) for spec in node_specs],
        "node_order": materialized_ids,
        "created_at": now_iso(),
        "redesigned_from_route_version": old_version,
        "redesign_decision_id": disposition_id,
        "redesign_reason": reason,
    }
    ledger["active_route_version"] = new_version
    first_node_id = materialized_ids[0] if materialized_ids else ""
    mutation = {
        "mutation_id": _next_id(ledger, "mutation"),
        "old_route_version": old_version,
        "new_route_version": new_version,
        "reason": reason,
        "disposition_id": disposition_id,
        "superseded_node_ids": old_node_ids,
        "replacement_node_id": first_node_id,
        "affected_packets": affected_packets,
        "requires_replay_or_rebinding": True,
        "created_at": now_iso(),
    }
    ledger["execution_frontier"] = {
        "active_route_version": new_version,
        "active_node_id": first_node_id,
        "completed_nodes": [],
        "status": "node_execution" if first_node_id else "blocked",
        "pending_route_mutation": mutation,
        "blocked_reason": "" if first_node_id else "route_redesign_empty",
        "updated_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(mutation)
    _supersede_repair_open_blockers_for_route_mutation(
        ledger,
        affected_packets=affected_packets,
        mutation_id=str(mutation["mutation_id"]),
        disposition_id=disposition_id,
        replacement_node_id=first_node_id,
        new_route_version=new_version,
    )
    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    _event(ledger, "execution_frontier_updated", status=ledger["execution_frontier"]["status"], active_node_id=first_node_id)
    if not first_node_id:
        return materialized_ids, ""

    before_packets = set(ledger.get("packets", {}))
    opened_node_id = first_node_id
    if high_standard_flow_required(ledger):
        ensure_node_acceptance_plan_packet(ledger, first_node_id)
    else:
        if _enter_nonworker_route_scope(ledger, first_node_id, reason="nonworker_route_scope_after_route_redesign"):
            opened_node_id = str((ledger.get("execution_frontier") or {}).get("active_node_id") or first_node_id)
        else:
            ensure_next_node_task_packet(ledger)
    fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=opened_node_id, before_ids=before_packets)
    if not fresh_packet_id:
        raise BlackBoxRuntimeError("redesign_route did not create a fresh executable packet")
    if blocker is not None:
        blocker_id = str(blocker.get("blocker_id") or "")
        if blocker_id:
            _bind_packet_repair_blocker_identity(ledger, fresh_packet_id, blocker_id)
            _attach_repair_obligation_context_to_packet(ledger, fresh_packet_id, blocker, disposition_id)
            _record_repair_transaction(
                ledger,
                blocker,
                disposition_id,
                source_id=f"route-v{old_version}",
                fresh_packet_id=fresh_packet_id,
            )
            _mark_repair_target_noncurrent_after_current_reissue(ledger, blocker, disposition_id)
    return materialized_ids, fresh_packet_id


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
    _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    old_node_ids = [
        str(node_id)
        for node_id, node in ledger.get("route_nodes", {}).items()
        if isinstance(node, Mapping) and int(node.get("route_version") or 0) == old_version
    ]
    affected_packets: list[str] = []
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
        affected_packets.append(str(packet.get("packet_id") or ""))
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
            "acceptance_item_ids": [str(item) for item in spec.get("acceptance_item_ids") or []],
            "skill_standard_obligation_ids": [str(item) for item in spec.get("skill_standard_obligation_ids") or []],
            "supplemental_repair_contract_ids": [str(item) for item in spec.get("supplemental_repair_contract_ids") or []],
            "supplemental_repair_item_ids": [str(item) for item in spec.get("supplemental_repair_item_ids") or []],
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
            "affected_packets": affected_packets,
            "requires_replay_or_rebinding": True,
            "created_at": now_iso(),
        },
        "blocked_reason": "" if first_node_id else "route_redesign_empty",
        "updated_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(ledger["execution_frontier"]["pending_route_mutation"])
    _supersede_repair_open_blockers_for_route_mutation(
        ledger,
        affected_packets=affected_packets,
        mutation_id=str(ledger["execution_frontier"]["pending_route_mutation"]["mutation_id"]),
        disposition_id=decision_id,
        replacement_node_id=first_node_id,
        new_route_version=new_version,
    )
    _event(ledger, "route_created", route_version=new_version, old_route_version=old_version)
    _event(ledger, "execution_frontier_updated", status=ledger["execution_frontier"]["status"], active_node_id=first_node_id)
    if first_node_id:
        before_packets = set(ledger.get("packets", {}))
        opened_node_id = first_node_id
        if high_standard_flow_required(ledger):
            ensure_node_acceptance_plan_packet(ledger, first_node_id)
        else:
            if _enter_nonworker_route_scope(ledger, first_node_id, reason="nonworker_route_scope_after_route_redesign"):
                opened_node_id = str((ledger.get("execution_frontier") or {}).get("active_node_id") or first_node_id)
            else:
                ensure_next_node_task_packet(ledger)
        fresh_packet_id = _latest_open_packet_for_repair(ledger, route_node_id=opened_node_id, before_ids=before_packets)
        if not fresh_packet_id:
            raise BlackBoxRuntimeError("redesign_route did not create a fresh executable packet")
        _bind_packet_repair_blocker_identity(ledger, fresh_packet_id, str(blocker["blocker_id"]))
        _attach_repair_obligation_context_to_packet(ledger, fresh_packet_id, blocker, decision_id)
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
        parent_repair_contract = _parent_repair_scope_contract_for_decision(
            ledger,
            ledger["pm_repair_decisions"][decision_id],
        )
        if parent_repair_contract is None:
            raise BlackBoxRuntimeError("repair_parent_scope requires repair_parent_scope_contract")
        _replacement_id, fresh_packet_id = _replace_scope_and_open_repair_packet(
            ledger,
            blocker,
            decision_id,
            source_node_id=parent_node_id,
            reason=reason,
            supersede_descendants=True,
            parent_repair_contract=parent_repair_contract,
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
        if node.get("status") == "awaiting_children" and not _route_node_all_children_resolved(ledger, node):
            continue
        if node.get("status") not in {"accepted", "superseded", "waived"}:
            next_node = candidate
            break
    frontier["active_node_id"] = next_node
    frontier["status"] = "node_execution" if next_node else "ready_for_final_closure"
    _retire_pending_route_mutation_after_frontier_commit(ledger, frontier, node_id)
    frontier["updated_at"] = now_iso()
    ledger["execution_frontier"] = frontier
    _event(ledger, "execution_frontier_updated", status=frontier["status"], active_node_id=next_node)
    if next_node:
        if _enter_nonworker_route_scope(ledger, next_node, reason="nonworker_route_scope_after_child_acceptance"):
            return
        if high_standard_flow_required(ledger):
            ensure_node_acceptance_plan_packet(ledger, next_node)
        else:
            ensure_next_node_task_packet(ledger)
    else:
        build_final_route_wide_gate_ledger(ledger)
        attempt_final_closure(ledger, str(ledger.get("latest_validation_evidence_id") or "route-wide-validation"))


def _retire_pending_route_mutation_after_frontier_commit(
    ledger: dict[str, Any],
    frontier: dict[str, Any],
    committed_node_id: str,
) -> None:
    pending = frontier.get("pending_route_mutation")
    if not isinstance(pending, dict):
        return
    replacement_node_id = str(pending.get("replacement_node_id") or pending.get("candidate_node_id") or "")
    if replacement_node_id and replacement_node_id != committed_node_id:
        return
    mutation_id = str(pending.get("mutation_id") or "")
    terminal = {
        **pending,
        "status": "committed",
        "committed_node_id": committed_node_id,
        "committed_at": now_iso(),
    }
    for row in ledger.get("route_mutations", []):
        if isinstance(row, dict) and str(row.get("mutation_id") or "") == mutation_id:
            row.update(terminal)
            break
    frontier["pending_route_mutation"] = None


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


def _materialize_parent_repair_child_nodes(
    ledger: dict[str, Any],
    *,
    replacement_id: str,
    source_parent: Mapping[str, Any],
    contract: Mapping[str, Any],
    route_version: int,
) -> list[str]:
    child_ids: list[str] = []
    for raw_spec in contract.get("repair_child_specs") or []:
        if not isinstance(raw_spec, Mapping):
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs entries must be objects")
        child_id = str(raw_spec.get("node_id") or "").strip()
        if not child_id:
            raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].node_id is required")
        if child_id in ledger.get("route_nodes", {}):
            raise BlackBoxRuntimeError(f"parent repair child node id already exists: {child_id}")
        if child_id == replacement_id:
            raise BlackBoxRuntimeError("parent repair child node id must not match the replacement parent")
        child_ids.append(child_id)
        acceptance_item_ids = _optional_string_items(raw_spec.get("acceptance_item_ids")) or _optional_string_items(
            source_parent.get("acceptance_item_ids")
        )
        high_standard_requirement_ids = _optional_string_items(
            raw_spec.get("high_standard_requirement_ids")
        ) or _optional_string_items(source_parent.get("high_standard_requirement_ids"))
        skill_standard_obligation_ids = _optional_string_items(
            raw_spec.get("skill_standard_obligation_ids")
        ) or _optional_string_items(source_parent.get("skill_standard_obligation_ids"))
        child_node = {
            "node_id": child_id,
            "route_version": route_version,
            "title": str(raw_spec.get("title") or raw_spec.get("purpose") or f"Repair {source_parent.get('title', replacement_id)}"),
            "node_kind": str(raw_spec.get("node_kind") or "repair"),
            "parent_node_id": replacement_id,
            "child_node_ids": [],
            "responsibility": _normalize_node_responsibility(str(raw_spec.get("responsibility") or "worker")),
            "modeled_target": _normalize_modeled_target(
                str(raw_spec.get("modeled_target") or source_parent.get("modeled_target") or REQUIRED_FLOWGUARD_TARGET),
                str(raw_spec.get("title") or raw_spec.get("purpose") or child_id),
            ),
            "acceptance_criteria": _optional_string_items(raw_spec.get("acceptance_criteria")) or [
                f"Current repair child proves: {raw_spec.get('purpose')}"
            ],
            "acceptance_item_ids": acceptance_item_ids,
            "high_standard_requirement_ids": high_standard_requirement_ids,
            "skill_standard_obligation_ids": skill_standard_obligation_ids,
            "parent_repair_purpose": str(raw_spec.get("purpose") or ""),
            "parent_repair_required_evidence": _optional_string_items(raw_spec.get("required_evidence")),
            "parent_repair_scope_contract_id": str(contract.get("contract_id") or ""),
            "parent_repair_source_parent_node_id": str(contract.get("source_parent_node_id") or ""),
            "status": "pending",
            "packet_ids": [],
            "accepted_result_id": "",
            "flowguard_order_ids": [],
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
            "repair_generation": int(source_parent.get("repair_generation", 0) or 0) + 1,
            "created_at": now_iso(),
        }
        ledger.setdefault("route_nodes", {})[child_id] = child_node
    if len(child_ids) != len(set(child_ids)):
        raise BlackBoxRuntimeError("repair_parent_scope_contract repair_child_specs[].node_id must be unique")
    return child_ids


def _replace_route_node_for_repair(
    ledger: dict[str, Any],
    node_id: str,
    *,
    disposition_id: str,
    reason: str,
    supersede_descendants: bool = False,
    parent_repair_contract: Mapping[str, Any] | None = None,
) -> str:
    old_version = int(ledger.get("active_route_version") or 0)
    new_version = old_version + 1
    replacement_id = f"{node_id}-repair-v{new_version}"
    superseded_node_ids = [node_id]
    if supersede_descendants:
        superseded_node_ids.extend(_descendant_route_node_ids(ledger, node_id))
        if parent_repair_contract is None:
            raise BlackBoxRuntimeError("repair_parent_scope requires a structured parent repair contract")
        parent_repair_contract = _parse_parent_repair_scope_contract_payload(
            {"repair_parent_scope_contract": parent_repair_contract},
            expected_parent_node_id=node_id,
        )
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
    inherited_child_node_ids: list[str] = []
    inherited_accepted_result_ids: list[str] = []
    child_node_ids = list(node.get("child_node_ids") or [])
    if supersede_descendants:
        inherited_child_node_ids = [item for item in superseded_node_ids if item != node_id]
        inherited_accepted_result_ids = _accepted_result_ids_for_route_nodes(ledger, inherited_child_node_ids)
        child_node_ids = _materialize_parent_repair_child_nodes(
            ledger,
            replacement_id=replacement_id,
            source_parent=node,
            contract=parent_repair_contract,
            route_version=new_version,
        )
        if not child_node_ids:
            raise BlackBoxRuntimeError("repair_parent_scope replacement parent requires active repair child nodes")
    replacement.update(
        {
            "node_id": replacement_id,
            "route_version": new_version,
            "title": f"Repair {node['title']}",
            "status": "pending",
            "child_node_ids": child_node_ids,
            "inherited_child_node_ids": inherited_child_node_ids,
            "inherited_accepted_result_ids": inherited_accepted_result_ids,
            "parent_repair_scope_contract_id": str(parent_repair_contract.get("contract_id") or "")
            if isinstance(parent_repair_contract, Mapping)
            else "",
            "repair_parent_scope_contract": _copy_jsonable(parent_repair_contract)
            if isinstance(parent_repair_contract, Mapping)
            else None,
            "parent_repair_source_node_id": node_id if supersede_descendants else "",
            "packet_ids": [],
            "accepted_result_id": "",
            "flowguard_order_ids": [],
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
    node_order: list[str] = []
    for item in route.get("node_order", []):
        item_id = str(item)
        if item_id == node_id:
            node_order.append(replacement_id)
            node_order.extend(child_node_ids)
            continue
        if item_id not in superseded_node_ids:
            node_order.append(item_id)
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
        "active_repair_child_node_ids": list(child_node_ids),
        "inherited_child_node_ids": list(inherited_child_node_ids),
        "inherited_accepted_result_ids": list(inherited_accepted_result_ids),
        "parent_repair_scope_contract_id": str(parent_repair_contract.get("contract_id") or "")
        if isinstance(parent_repair_contract, Mapping)
        else "",
        "affected_packets": affected_packets,
        "requires_replay_or_rebinding": True,
        "created_at": now_iso(),
    }
    ledger.setdefault("route_mutations", []).append(mutation)
    _supersede_repair_open_blockers_for_route_mutation(
        ledger,
        affected_packets=affected_packets,
        mutation_id=str(mutation["mutation_id"]),
        disposition_id=disposition_id,
        replacement_node_id=replacement_id,
        new_route_version=new_version,
    )
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
        if _enter_nonworker_route_scope(ledger, replacement_id, reason="nonworker_route_scope_after_route_repair"):
            return replacement_id
        ensure_next_node_task_packet(ledger)
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


def _latest_liveness_evidence(lease: Mapping[str, Any]) -> dict[str, Any]:
    candidates: list[tuple[str, str, datetime]] = []
    if lease.get("ack_received"):
        ack_at = str(lease.get("ack_received_at") or "")
        parsed_ack = _parse_utc_timestamp(ack_at)
        if parsed_ack is not None:
            candidates.append(("ack", ack_at, parsed_ack))
    progress_at = str(lease.get("last_progress_at") or "")
    parsed_progress = _parse_utc_timestamp(progress_at)
    if parsed_progress is not None:
        candidates.append(("progress", progress_at, parsed_progress))
    if not candidates:
        return {"kind": "none", "at": "", "elapsed_seconds": None}
    kind, raw_at, parsed_at = max(candidates, key=lambda item: item[2])
    return {
        "kind": kind,
        "at": raw_at,
        "elapsed_seconds": max(0, int((datetime.now(timezone.utc) - parsed_at).total_seconds())),
    }


def _lease_replacement_due_from_evidence_age(ledger: Mapping[str, Any], lease: Mapping[str, Any]) -> bool:
    if str(lease.get("status") or "") != "active":
        return False
    packet_id = str(lease.get("packet_id") or "")
    packet = ledger.get("packets", {}).get(packet_id)
    if isinstance(packet, Mapping) and packet.get("accepted_result_id"):
        return False
    if not lease.get("ack_received"):
        elapsed = _elapsed_seconds_since(lease.get("created_at"))
        ack_replace_seconds = _guard_config_int(ledger, "ack_replace_seconds", _WAIT_ACK_REPLACE_SECONDS)
        return elapsed is not None and elapsed >= ack_replace_seconds
    evidence = _latest_liveness_evidence(lease)
    elapsed = evidence.get("elapsed_seconds")
    progress_replace_seconds = _guard_config_int(
        ledger,
        "progress_replace_seconds",
        _WAIT_PROGRESS_REPLACE_SECONDS,
    )
    return isinstance(elapsed, int) and elapsed >= progress_replace_seconds


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
        if _lease_replacement_due_from_evidence_age(ledger, lease):
            return False
    return True


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


def _lease_reusable_for_role_slot(ledger: Mapping[str, Any], lease: Mapping[str, Any]) -> bool:
    agent_id = str(lease.get("agent_id") or "").strip()
    if not agent_id:
        return False
    if str(lease.get("status") or "") in {"expired", "superseded", "cancelled"}:
        return False
    return not _lease_replacement_due_from_evidence_age(ledger, lease)


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
        if not _lease_reusable_for_role_slot(ledger, lease):
            continue
        roles = _role_continuity_table(ledger)
        slot = {
            "schema_version": "black_box_flowpilot.role_slot.v1",
            "role": role,
            "agent_id": str(lease.get("agent_id") or ""),
            "latest_lease_id": str(lease.get("lease_id") or ""),
            "latest_packet_id": str(lease.get("packet_id") or ""),
            "reuse_state": "reusable",
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


_REPAIR_NODE_SUFFIX_RE = re.compile(r"(?:-repair-v\d+)+$")
_ROUTE_NODE_VERSION_RE = re.compile(r"-v\d+(?=-|$)")


def _normalize_repair_loop_route_node_id(route_node_id: str) -> str:
    node_id = str(route_node_id or "").strip()
    previous = None
    while node_id and previous != node_id:
        previous = node_id
        node_id = _REPAIR_NODE_SUFFIX_RE.sub("", node_id)
    return _ROUTE_NODE_VERSION_RE.sub("-v#", node_id)


def _blocker_repair_loop_target_id(blocker: Mapping[str, Any]) -> str:
    return str(blocker.get("repair_target_packet_id") or blocker.get("subject_packet_id") or blocker.get("packet_id") or "")


def _blocker_repair_loop_route_node_id(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> str:
    explicit = str(blocker.get("route_node_id") or "")
    if explicit:
        return explicit
    for field in ("repair_target_packet_id", "subject_packet_id", "packet_id", "pm_repair_packet_id", "repair_packet_id"):
        packet_id = str(blocker.get(field) or "")
        packet = ledger.get("packets", {}).get(packet_id)
        envelope = packet.get("envelope", {}) if isinstance(packet, Mapping) and isinstance(packet.get("envelope"), Mapping) else {}
        route_node_id = str(envelope.get("route_node_id") or "")
        if route_node_id:
            return route_node_id
    return ""


def _repair_loop_family_parts(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, str]:
    normalized_node_id = _normalize_repair_loop_route_node_id(_blocker_repair_loop_route_node_id(ledger, blocker))
    packet_subject_id = _blocker_repair_loop_target_id(blocker)
    return {
        "family_subject": normalized_node_id or packet_subject_id,
        "normalized_route_node_id": normalized_node_id,
        "packet_subject_id": "" if normalized_node_id else packet_subject_id,
        "blocker_class": str(blocker.get("blocker_class") or "unknown"),
        "gate_kind": str(blocker.get("gate_kind") or "unknown"),
        "required_recheck_role": str(blocker.get("required_recheck_role") or "unknown"),
    }


def _repair_loop_family_key(parts: Mapping[str, str]) -> str:
    return "|".join(
        f"{field}={str(parts.get(field) or '')}"
        for field in ("family_subject", "blocker_class", "gate_kind", "required_recheck_role")
    )


def _flowguard_missing_evidence_root_cause_key(
    *,
    subject_packet_id: str,
    target_result_id: str = "",
    repair_blocker_id: str = "",
) -> str:
    return "|".join(
        (
            "flowguard_missing_matching_report",
            f"subject_packet_id={subject_packet_id}",
            f"target_result_id={target_result_id}",
            f"repair_blocker_id={repair_blocker_id}",
        )
    )


def _blocker_counts_for_repair_loop(ledger: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if candidate.get("cleared_by_outcome_id"):
        return False
    status = str(candidate.get("status") or "")
    return status in _REPAIR_LOOP_COUNTED_BLOCKER_STATUSES or status.startswith("retired_after_")


def _repair_loop_same_family_rows(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    family = _repair_loop_family_parts(ledger, blocker)
    family_key = _repair_loop_family_key(family)
    root_cause_key = str(blocker.get("root_cause_loop_key") or "")
    rows: list[dict[str, str]] = []
    target_blocker_id = str(blocker.get("blocker_id") or "")
    for candidate in ledger.get("active_blockers", {}).values():
        if not isinstance(candidate, Mapping):
            continue
        candidate_family = _repair_loop_family_parts(ledger, candidate)
        candidate_key = _repair_loop_family_key(candidate_family)
        candidate_counts = _blocker_counts_for_repair_loop(ledger, candidate)
        candidate_root_key = str(candidate.get("root_cause_loop_key") or "")
        if root_cause_key:
            same_problem = candidate_root_key == root_cause_key
        else:
            same_problem = candidate_key == family_key
        if same_problem:
            if candidate_counts:
                rows.append(
                    {
                        "blocker_id": str(candidate.get("blocker_id") or ""),
                        "status": str(candidate.get("status") or ""),
                        "route_node_id": str(candidate.get("route_node_id") or ""),
                        "normalized_route_node_id": str(candidate_family.get("normalized_route_node_id") or ""),
                        "pm_repair_decision_id": str(candidate.get("pm_repair_decision_id") or ""),
                        "pm_repair_packet_id": str(candidate.get("pm_repair_packet_id") or ""),
                        "repair_packet_id": str(candidate.get("repair_packet_id") or ""),
                        "root_cause_loop_key": candidate_root_key,
                    }
                )
            else:
                rows = []
        elif candidate_counts:
            rows = []
        if target_blocker_id and str(candidate.get("blocker_id") or "") == target_blocker_id:
            break
    return family, rows


def _repair_loop_break_glass_review(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, Any]:
    family, rows = _repair_loop_same_family_rows(ledger, blocker)
    attempt_count = len(rows)
    threshold_exceeded = attempt_count >= _REPAIR_LOOP_BREAK_GLASS_THRESHOLD
    root_cause_key = str(blocker.get("root_cause_loop_key") or "")
    return {
        "schema_version": "black_box_flowpilot.repair_loop_break_glass_review.v1",
        "family_key": root_cause_key or _repair_loop_family_key(family),
        "family": family,
        "root_cause_loop_key": root_cause_key,
        "attempt_count": attempt_count,
        "threshold": _REPAIR_LOOP_BREAK_GLASS_THRESHOLD,
        "threshold_exceeded": threshold_exceeded,
        "blocker_ids": [row["blocker_id"] for row in rows if row["blocker_id"]],
        "same_family_blockers": rows,
        "required_action": "controller_break_glass_diagnosis" if threshold_exceeded else "ordinary_pm_repair_allowed",
        "consecutive_scope": "same_repair_lineage_problem_identity",
        "reason": (
            "same repair lineage repeated the same blocker problem five or more consecutive times"
            if threshold_exceeded
            else "same repair lineage problem remains within ordinary PM repair threshold"
        ),
        "sealed_bodies_visible": False,
    }


def _repair_loop_break_glass_event_recorded(ledger: Mapping[str, Any], blocker_id: str) -> bool:
    for event in ledger.get("events", []):
        if not isinstance(event, Mapping) or event.get("event_type") != "repair_loop_break_glass_required":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        if str(payload.get("blocker_id") or "") == blocker_id:
            return True
    return False


def _supersede_same_family_pm_repair_packets_for_break_glass(
    ledger: dict[str, Any],
    review: Mapping[str, Any],
) -> list[str]:
    superseded: list[str] = []
    for row in review.get("same_family_blockers") or []:
        if not isinstance(row, Mapping):
            continue
        packet_id = str(row.get("pm_repair_packet_id") or "")
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, dict):
            continue
        envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
        if envelope.get("packet_kind") != "pm_repair_decision":
            continue
        if packet.get("status") in _NONCURRENT_PACKET_STATUSES:
            continue
        packet["status"] = "superseded_after_repair"
        packet["superseded_reason"] = "repair_loop_break_glass_required"
        packet["superseded_at"] = now_iso()
        packet["active_blocker_id"] = ""
        superseded.append(packet_id)
    if superseded:
        _event(
            ledger,
            "repair_loop_pm_repair_packets_superseded",
            packet_ids=superseded,
            family_key=str(review.get("family_key") or ""),
            attempt_count=int(review.get("attempt_count", 0) or 0),
        )
    return superseded


def _blocker_repeat_context(ledger: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, Any]:
    family, same_family = _repair_loop_same_family_rows(ledger, blocker)
    repeat_count = len(same_family)
    return {
        "family_key": _repair_loop_family_key(family),
        "family": family,
        "repeat_count": repeat_count,
        "previous_blocker_ids": [row["blocker_id"] for row in same_family if row["blocker_id"] != blocker.get("blocker_id")],
        "same_family_blockers": same_family,
        "threshold": _REPAIR_LOOP_BREAK_GLASS_THRESHOLD,
        "threshold_exceeded": repeat_count >= _REPAIR_LOOP_BREAK_GLASS_THRESHOLD,
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
    raw_findings_sources: list[Any] = [payload.get("blocking_findings")]
    for raw_findings in raw_findings_sources:
        if not isinstance(raw_findings, list):
            continue
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


def _packet_body_with_current_handoff_contract(
    body: str,
    contract: Mapping[str, Any],
    *,
    replace_existing: bool = False,
) -> str:
    payload = _strict_json_object_from_body(body)
    if payload is None:
        return body
    if not replace_existing and "current_handoff_contract" in payload:
        raise BlackBoxRuntimeError("current_handoff_contract must be issued by the runtime envelope")
    payload["current_handoff_contract"] = _copy_jsonable(contract)
    return json.dumps(payload, indent=2, sort_keys=True)


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
    envelope["authorized_result_reads"] = merged
    handoff_contract = _build_current_handoff_contract(ledger, envelope, merged)
    envelope["current_handoff_contract"] = handoff_contract
    body = _packet_body_with_current_handoff_contract(body, handoff_contract, replace_existing=True)
    body_hash = hash_text(body)
    packet["body"] = body
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


def _blocker_related_result_reads(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    *,
    primary_purpose: str,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(result_id: str, purpose: str) -> None:
        result_id = str(result_id or "")
        if not result_id or result_id in seen:
            return
        if not isinstance(ledger.get("results", {}).get(result_id), Mapping):
            return
        seen.add(result_id)
        rows.append((result_id, purpose))

    primary_result_id = str(blocker.get("result_id") or "")
    add(primary_result_id, primary_purpose)
    target_result_id = str(blocker.get("target_result_id") or "")
    if target_result_id != primary_result_id:
        add(target_result_id, "blocked_target_result_body_for_repair")

    index = 0
    while index < len(rows):
        result_id, _purpose = rows[index]
        index += 1
        result = ledger.get("results", {}).get(result_id)
        if not isinstance(result, Mapping):
            continue
        source_packet_id = str(result.get("packet_id") or "")
        source_packet = ledger.get("packets", {}).get(source_packet_id)
        if not isinstance(source_packet, Mapping):
            continue
        for read in _packet_authorized_result_reads(source_packet):
            upstream_result_id = str(read.get("result_id") or "")
            upstream_purpose = str(read.get("purpose") or "authorized_result_read")
            add(upstream_result_id, f"upstream_context_for_blocker:{upstream_purpose}")

    return rows


def _blocker_authorized_result_reads(
    ledger: Mapping[str, Any],
    blocker: Mapping[str, Any],
    *,
    allowed_roles: list[str],
    purpose: str,
    required_before_submit: bool = True,
) -> list[dict[str, Any]]:
    return [
        _authorized_read_for_result(
            ledger,
            result_id,
            allowed_roles=allowed_roles,
            purpose=read_purpose,
            required_before_submit=required_before_submit,
        )
        for result_id, read_purpose in _blocker_related_result_reads(
            ledger,
            blocker,
            primary_purpose=purpose,
        )
    ]


def _packet_handoff_missing_information_response(
    *,
    family_id: str,
    required_fields: tuple[str, ...],
) -> dict[str, Any]:
    if "decision" in required_fields:
        return {
            "if_required_information_is_missing": (
                "Submit a current JSON result for this packet family with decision=block, "
                "blocker_class=missing_required_information, recommended_resolution naming the missing input, "
                "and pm_visible_summary when that field is required."
            ),
            "old_shapes_forbidden": True,
            "runtime_reissue_on_mechanical_contract_failure": True,
        }
    return {
        "if_required_information_is_missing": (
            "Do not guess or switch result shape. Submit only the contract-defined current-family fields; "
            "if those fields cannot be produced, the runtime mechanical contract gate reissues the current packet."
        ),
        "contract_family_id": family_id,
        "old_shapes_forbidden": True,
        "runtime_reissue_on_mechanical_contract_failure": True,
    }


def _dedupe_contract_fields(*groups: Iterable[Any]) -> list[str]:
    fields: list[str] = []
    for group in groups:
        for item in group:
            value = str(item)
            if value and value not in fields:
                fields.append(value)
    return fields


def _planning_owner_coverage_minimal_shape(active_item_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "decision": "pass",
        "nodes": [
            {
                "node_id": "node-cover-active-acceptance-items",
                "title": "Execute current acceptance items",
                "node_kind": "leaf",
                "parent_node_id": "",
                "child_node_ids": [],
                "responsibility": "worker",
                "acceptance_criteria": ["Current node owns and closes every active acceptance item assigned here."],
                "acceptance_item_ids": list(active_item_ids),
                "supplemental_repair_contract_ids": [],
                "supplemental_repair_item_ids": [],
            }
        ],
    }


def _node_acceptance_projection_rows(item_ids: list[str]) -> list[dict[str, str]]:
    return [
        {
            "acceptance_item_id": item_id,
            "status_for_this_node": "planned_for_current_node",
            "future_evidence_rule": "Current node evidence, FlowGuard, Reviewer, PM disposition, and terminal replay must close or explicitly defer this item.",
        }
        for item_id in item_ids
    ]


def _project_current_pm_repair_blocker_id(value: Any, blocker_id: str) -> Any:
    if not blocker_id:
        return _copy_jsonable(value)
    if isinstance(value, Mapping):
        projected: dict[str, Any] = {}
        for key, item in value.items():
            if str(key) == "target_blocker_id":
                projected[str(key)] = blocker_id
            else:
                projected[str(key)] = _project_current_pm_repair_blocker_id(item, blocker_id)
        return projected
    if isinstance(value, list):
        return [_project_current_pm_repair_blocker_id(item, blocker_id) for item in value]
    return _copy_jsonable(value)


def _dynamic_effective_result_contract_for_envelope(
    ledger: Mapping[str, Any],
    envelope: Mapping[str, Any],
    effective_contract: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _copy_jsonable(dict(effective_contract))
    family_id = str(contract.get("family_id") or packet_result_contracts.packet_result_family_id(envelope))
    allowed_options = dict(contract.get("allowed_value_options") or {})
    field_types = dict(contract.get("field_type_requirements") or {})
    required_child_fields = list(contract.get("required_child_fields") or [])

    if family_id == "task.planning" and high_standard_flow_required(ledger):
        active_item_ids = _active_acceptance_item_ids(ledger)
        if active_item_ids:
            contract["required_acceptance_item_ids"] = active_item_ids
            contract["ownership_coverage_rule"] = {
                "field_path": "nodes[].acceptance_item_ids",
                "required_ids": active_item_ids,
                "rule": "Every current active acceptance item id must appear in at least one route node acceptance_item_ids owner list.",
                "unknown_ids_forbidden": True,
                "minimal_repair_shape": {"nodes[].acceptance_item_ids": active_item_ids},
            }
            allowed_options["nodes[].acceptance_item_ids[]"] = active_item_ids
            field_types["nodes[].acceptance_item_ids"] = "array:string"
            contract["minimal_valid_shape"] = _planning_owner_coverage_minimal_shape(active_item_ids)

    if family_id == "task.node_acceptance_plan":
        node_id = str(envelope.get("route_node_id") or "")
        node = ledger.get("route_nodes", {}).get(node_id, {}) if node_id else {}
        node_item_ids = _node_acceptance_item_ids(node) if isinstance(node, Mapping) else []
        if node_item_ids:
            required_child_fields = _dedupe_contract_fields(
                required_child_fields,
                (
                    "node_context_package.acceptance_item_projection[].acceptance_item_id",
                    "node_context_package.acceptance_item_projection[].status_for_this_node",
                    "node_context_package.acceptance_item_projection[].future_evidence_rule",
                ),
            )
            contract["required_node_acceptance_item_ids"] = node_item_ids
            contract["node_acceptance_projection_rule"] = {
                "field_path": "node_context_package.acceptance_item_projection",
                "required_ids": node_item_ids,
                "row_required_fields": [
                    "acceptance_item_id",
                    "status_for_this_node",
                    "future_evidence_rule",
                ],
                "rule": "When decision=pass, every node-owned acceptance item id must have one projection row.",
                "unknown_ids_forbidden": True,
                "minimal_repair_rows": _node_acceptance_projection_rows(node_item_ids),
            }
            allowed_options["node_context_package.acceptance_item_projection[].acceptance_item_id"] = node_item_ids
            field_types["node_context_package.acceptance_item_projection"] = "array:object"
            minimal_shape = _copy_jsonable(contract.get("minimal_valid_shape") or {})
            package = minimal_shape.get("node_context_package")
            if isinstance(package, dict):
                package["acceptance_item_projection"] = _node_acceptance_projection_rows(node_item_ids)
            branch_shapes = _copy_jsonable(contract.get("branch_valid_shapes") or {})
            pass_shape = branch_shapes.get("decision=pass")
            if isinstance(pass_shape, dict):
                pass_package = pass_shape.get("node_context_package")
                if isinstance(pass_package, dict):
                    pass_package["acceptance_item_projection"] = _node_acceptance_projection_rows(node_item_ids)
            contract["minimal_valid_shape"] = minimal_shape
            contract["branch_valid_shapes"] = branch_shapes

    if family_id == "pm_repair_decision.pm_repair_decision":
        blocker_id = str(envelope.get("repair_blocker_id") or envelope.get("subject_id") or "")
        if blocker_id:
            contract["minimal_valid_shape"] = _project_current_pm_repair_blocker_id(
                contract.get("minimal_valid_shape") or {},
                blocker_id,
            )
            contract["branch_valid_shapes"] = _project_current_pm_repair_blocker_id(
                contract.get("branch_valid_shapes") or {},
                blocker_id,
            )

    contract["required_child_fields"] = _dedupe_contract_fields(required_child_fields)
    contract["allowed_value_options"] = _copy_jsonable(allowed_options)
    contract["field_type_requirements"] = _copy_jsonable(field_types)
    return contract


def _review_window_for_handoff(
    ledger: Mapping[str, Any],
    envelope: Mapping[str, Any],
    authorized_result_reads: list[Mapping[str, Any]],
    stage_evidence_matrix: Mapping[str, Any],
) -> dict[str, Any]:
    if str(envelope.get("packet_kind") or "task") != "review":
        return {}
    subject_id = str(envelope.get("subject_id") or "")
    subject_packet = ledger.get("packets", {}).get(subject_id) if subject_id else None
    subject_envelope = (
        subject_packet.get("envelope", {})
        if isinstance(subject_packet, Mapping) and isinstance(subject_packet.get("envelope"), Mapping)
        else {}
    )
    review_family_id = packet_result_contracts.packet_result_family_id(envelope)
    subject_family_id = (
        packet_result_contracts.packet_result_family_id(subject_envelope)
        if isinstance(subject_envelope, Mapping) and subject_envelope
        else ""
    )
    if not subject_family_id and review_family_id == "review.terminal_backward_replay":
        subject_family_id = review_family_id
    subject_stage_evidence = (
        packet_result_contracts.role_visible_stage_evidence_row_json_for_family(subject_family_id)
        if subject_family_id
        else stage_evidence_matrix
    )
    required_read_ids = [
        str(row.get("result_id") or "")
        for row in authorized_result_reads
        if isinstance(row, Mapping) and row.get("required_before_submit") is True and str(row.get("result_id") or "")
    ]
    stage = str(subject_stage_evidence.get("lifecycle_stage") or "")
    completeness = review_window_contracts.review_window_contract_for_context(
        review_result_family_id=review_family_id,
        subject_family_id=subject_family_id,
        subject_lifecycle_stage=stage,
    )
    forbidden_future_stage_demands = [
        "Do not require Worker/result-stage artifacts for a plan-stage subject unless the subject claims they already exist.",
        "Do not require terminal replay evidence before the terminal replay packet.",
        "Do not treat PM navigation summaries as reviewed evidence bodies.",
    ]
    return {
        "schema_version": review_window_contracts.REVIEW_WINDOW_SCHEMA_VERSION,
        "review_flow_id": str(completeness.get("review_flow_id") or ""),
        "review_window_coverage_status": str(completeness.get("coverage_status") or "unknown"),
        "review_result_family_id": review_family_id,
        "subject_packet_id": subject_id,
        "target_result_id": str(envelope.get("target_result_id") or ""),
        "subject_result_family_id": subject_family_id,
        "subject_lifecycle_stage": stage,
        "required_window_paths": list(completeness.get("required_window_paths") or ()),
        "required_material_classes": list(completeness.get("required_material_classes") or ()),
        "required_authorized_read_purposes_before_submit": list(
            completeness.get("required_read_purposes") or ()
        ),
        "authorized_result_read_purposes": [
            str(row.get("purpose") or "")
            for row in authorized_result_reads
            if isinstance(row, Mapping) and str(row.get("purpose") or "")
        ],
        "forbidden_future_stage_classes": list(
            completeness.get("forbidden_future_stage_classes") or ()
        ),
        "required_current_fields": list(subject_stage_evidence.get("current_required_fields") or []),
        "allowed_blocker_classes": list(subject_stage_evidence.get("allowed_blocker_classes") or []),
        "blocker_next_actions": _copy_jsonable(subject_stage_evidence.get("blocker_next_actions") or {}),
        "authorized_result_read_ids": [
            str(row.get("result_id") or "")
            for row in authorized_result_reads
            if isinstance(row, Mapping) and str(row.get("result_id") or "")
        ],
        "required_authorized_result_read_ids_before_submit": required_read_ids,
        "sealed_body_access": "authorized_result_reads_only",
        "review_depth_rule": (
            "Reviewer must independently challenge the current subject using the subject stage, "
            "authorized reads, node context, FlowGuard manifest, and current-stage evidence; the package checklist is a floor, not the boundary."
        ),
        "forbidden_future_stage_demands": forbidden_future_stage_demands,
        "pm_repair_return_rule": "Reviewer hard blockers return to PM repair work and then to Reviewer recheck; PM text alone does not bypass Reviewer.",
    }


def _build_current_handoff_contract(
    ledger: Mapping[str, Any],
    envelope: Mapping[str, Any],
    authorized_result_reads: list[Mapping[str, Any]],
) -> dict[str, Any]:
    family_id = packet_result_contracts.packet_result_family_id(envelope)
    family_row = packet_result_contracts.contract_for_family(family_id) or {}
    effective_contract = _dynamic_effective_result_contract_for_envelope(
        ledger,
        envelope,
        packet_result_contracts.effective_result_contract_from_envelope(envelope),
    )
    stage_evidence_matrix = packet_result_contracts.role_visible_stage_evidence_row_json_for_family(family_id)
    required_fields = tuple(str(field) for field in effective_contract.get("required_fields") or ())
    handoff = {
        "schema_version": "black_box_flowpilot.current_handoff_contract.v1",
        "contract_id": "black_box_flowpilot.current_handoff_contract.v1",
        "packet_id": str(envelope.get("packet_id") or ""),
        "packet_kind": str(envelope.get("packet_kind") or "task"),
        "route_scope": str(envelope.get("route_scope") or ""),
        "recipient_responsibility": str(envelope.get("responsibility") or ""),
        "contract_family_id": family_id,
        "result_contract_profile_ids": list(effective_contract.get("result_contract_profile_ids") or []),
        "result_contract_profile_bindings": _copy_jsonable(
            effective_contract.get("result_contract_profile_bindings") or {}
        ),
        "stage_evidence_matrix": stage_evidence_matrix,
        "current_run_only": True,
        "input_material_manifest": {
            "subject_id": str(envelope.get("subject_id") or ""),
            "target_result_id": str(envelope.get("target_result_id") or ""),
            "route_node_id": str(envelope.get("route_node_id") or ""),
            "blocker_id": str(envelope.get("repair_blocker_id") or ""),
            "node_context_package_id": str(envelope.get("node_context_package_id") or ""),
            "authorized_result_reads": _copy_jsonable(authorized_result_reads),
            "authorized_result_read_ids": [
                str(row.get("result_id") or "")
                for row in authorized_result_reads
                if isinstance(row, Mapping) and str(row.get("result_id") or "")
            ],
            "required_authorized_reads_before_submit": [
                str(row.get("result_id") or "")
                for row in authorized_result_reads
                if isinstance(row, Mapping) and row.get("required_before_submit") is True
            ],
            "required_authorized_read_count": len(
                [
                    row
                    for row in authorized_result_reads
                    if isinstance(row, Mapping) and row.get("required_before_submit") is True
                ]
            ),
            "all_required_authorized_result_bodies_must_be_opened_before_submit": True,
            "packet_body_hash_authority": "envelope.body_hash",
            "packet_body_opened_by_assigned_role_via_open_packet": True,
            "sealed_body_visibility": str(envelope.get("body_visibility") or "sealed"),
        },
        "required_report_contract": {
            "output_contract": _copy_jsonable(envelope.get("output_contract") or {}),
            "result_contract_profile_ids": list(effective_contract.get("result_contract_profile_ids") or []),
            "result_contract_profile_bindings": _copy_jsonable(
                effective_contract.get("result_contract_profile_bindings") or {}
            ),
            "required_result_body_fields": list(effective_contract.get("required_fields") or []),
            "required_child_fields": list(effective_contract.get("required_child_fields") or []),
            "explicit_array_fields": list(effective_contract.get("explicit_array_fields") or []),
            "non_empty_array_fields": list(effective_contract.get("non_empty_array_fields") or []),
            "allowed_value_options": _copy_jsonable(effective_contract.get("allowed_value_options") or {}),
            "field_type_requirements": _copy_jsonable(effective_contract.get("field_type_requirements") or {}),
            "minimal_valid_shape": _copy_jsonable(effective_contract.get("minimal_valid_shape") or {}),
            "branch_valid_shapes": _copy_jsonable(effective_contract.get("branch_valid_shapes") or {}),
            "stage_evidence_matrix": stage_evidence_matrix,
            "validator": str(effective_contract.get("validator") or ""),
        },
        "missing_information_response": _packet_handoff_missing_information_response(
            family_id=family_id,
            required_fields=required_fields,
        ),
        "downstream_consumer": {
            "unlocks": str(family_row.get("unlocks") or ""),
            "next_consumer_authority": "runtime_router",
            "accepted_by_role_text_alone": False,
        },
        "status_projection_requirements": {
            "repair_chain_visible_when_current": True,
            "sealed_bodies_visible": False,
            "controller_projection_is_display_only": True,
        },
        "unsupported_paths_forbidden": {
            "legacy_aliases": True,
            "wrapper_shapes": True,
            "missing_field_defaults": True,
            "historical_artifact_promotion": True,
            "old_router_path": True,
        },
        "source_generation": int(ledger.get("source_generation", 0) or 0),
        "route_version": envelope.get("route_version"),
    }
    for key in (
        "required_acceptance_item_ids",
        "ownership_coverage_rule",
        "required_node_acceptance_item_ids",
        "node_acceptance_projection_rule",
    ):
        if key in effective_contract:
            handoff["required_report_contract"][key] = _copy_jsonable(effective_contract[key])
    review_window = _review_window_for_handoff(
        ledger,
        envelope,
        authorized_result_reads,
        stage_evidence_matrix,
    )
    if review_window:
        handoff["review_window"] = review_window
    return handoff


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
    return _result_body_open_receipt(
        packet,
        lease_id=lease_id,
        responsibility=responsibility,
        result_id=result_id,
        body_hash=body_hash,
    ) is not None


def _result_body_open_receipt(
    packet: Mapping[str, Any],
    *,
    lease_id: str,
    responsibility: str,
    result_id: str,
    body_hash: str,
) -> Mapping[str, Any] | None:
    receipts = packet.get("authorized_result_read_receipts", [])
    if not isinstance(receipts, list):
        return None
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        if (
            receipt.get("lease_id") == lease_id
            and receipt.get("responsibility") == responsibility
            and receipt.get("result_id") == result_id
            and receipt.get("body_hash") == body_hash
        ):
            return receipt
    return None


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
    repair_blocker_id: str = "",
    result_contract_profile_ids: list[str] | tuple[str, ...] | None = None,
    result_contract_profile_bindings: Mapping[str, Any] | None = None,
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
        "repair_blocker_id": repair_blocker_id,
        "node_context_package_id": node_context_package_id,
        "acceptance_criteria": _default_packet_acceptance_criteria(acceptance_criteria),
        "body_hash": "",
        "body_visibility": "sealed",
        "source_generation": ledger["source_generation"],
    }
    normalized_profile_ids = packet_result_contracts.normalize_result_contract_profile_ids(
        result_contract_profile_ids or ()
    )
    if normalized_profile_ids:
        envelope["result_contract_profile_ids"] = list(normalized_profile_ids)
        envelope["result_contract_profile_bindings"] = _copy_jsonable(result_contract_profile_bindings or {})
    if normalized_result_reads:
        envelope["authorized_result_reads"] = normalized_result_reads
    envelope["output_contract"] = control_surface.build_packet_output_contract(
        packet_id=packet_id,
        responsibility=responsibility,
        packet_kind=packet_kind,
        route_version=int(ledger["active_route_version"]),
        source_generation=int(ledger["source_generation"]),
    )
    family_id = packet_result_contracts.packet_result_family_id(envelope)
    effective_contract = packet_result_contracts.effective_result_contract_from_envelope(envelope)
    output_contract = dict(envelope["output_contract"])
    output_contract["contract_family_id"] = family_id
    output_contract["result_contract_profile_ids"] = list(effective_contract.get("result_contract_profile_ids") or [])
    output_contract["result_contract_profile_bindings"] = _copy_jsonable(
        effective_contract.get("result_contract_profile_bindings") or {}
    )
    output_contract["allowed_value_options"] = _copy_jsonable(effective_contract.get("allowed_value_options") or {})
    output_contract["field_type_requirements"] = _copy_jsonable(
        effective_contract.get("field_type_requirements") or {}
    )
    output_contract["forbidden_fields"] = list(effective_contract.get("forbidden_fields") or [])
    envelope["output_contract"] = output_contract
    if _role_result_requires_pm_visible_summary(responsibility=responsibility, packet_kind=packet_kind):
        output_contract = dict(envelope["output_contract"])
        output_contract["pm_visible_summary_required"] = True
        output_contract["pm_visible_summary_shape"] = "non_empty_string_list"
        output_contract["runner_may_synthesize_pm_visible_summary"] = False
        envelope["output_contract"] = output_contract
    current_handoff_contract = _build_current_handoff_contract(ledger, envelope, normalized_result_reads)
    envelope["current_handoff_contract"] = current_handoff_contract
    if isinstance(current_handoff_contract.get("review_window"), Mapping):
        envelope["review_window"] = _copy_jsonable(current_handoff_contract["review_window"])
    body = _packet_body_with_current_handoff_contract(body, current_handoff_contract)
    envelope["body_hash"] = hash_text(body)
    ledger["packets"][packet_id] = {
        "packet_id": packet_id,
        "status": "open",
        "envelope": envelope,
        "body": body,
        "assigned_lease_id": "",
        "result_ids": [],
        "accepted_result_id": "",
        "old_route_disposition": "",
        "repair_blocker_id": repair_blocker_id,
    }
    _event(ledger, "task_packet_issued", packet_id=packet_id, responsibility=responsibility, packet_kind=packet_kind)
    return packet_id


def _bind_packet_repair_blocker_identity(
    ledger: dict[str, Any],
    packet_id: str,
    repair_blocker_id: str,
) -> None:
    if not repair_blocker_id:
        return
    packet = _require(ledger["packets"], packet_id, "packet")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if not isinstance(envelope, dict):
        raise BlackBoxRuntimeError("packet envelope is missing")
    existing_packet_id = str(packet.get("repair_blocker_id") or "")
    existing_envelope_id = str(envelope.get("repair_blocker_id") or "")
    if existing_packet_id and existing_packet_id != repair_blocker_id:
        raise BlackBoxRuntimeError("packet repair blocker identity already bound to a different blocker")
    if existing_envelope_id and existing_envelope_id != repair_blocker_id:
        raise BlackBoxRuntimeError("packet envelope repair blocker identity already bound to a different blocker")
    packet["repair_blocker_id"] = repair_blocker_id
    envelope["repair_blocker_id"] = repair_blocker_id
    handoff_contract = _build_current_handoff_contract(
        ledger,
        envelope,
        _packet_authorized_result_reads(packet),
    )
    envelope["current_handoff_contract"] = handoff_contract
    if isinstance(handoff_contract.get("review_window"), Mapping):
        envelope["review_window"] = _copy_jsonable(handoff_contract["review_window"])
    body = _packet_body_with_current_handoff_contract(str(packet.get("body", "")), handoff_contract, replace_existing=True)
    packet["body"] = body
    envelope["body_hash"] = hash_text(body)


def _formal_repair_identity_blockers(packet: Mapping[str, Any]) -> list[str]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_repair_blocker_id = str(packet.get("repair_blocker_id") or "")
    envelope_repair_blocker_id = str(envelope.get("repair_blocker_id") or "") if isinstance(envelope, Mapping) else ""
    blockers: list[str] = []
    if packet_repair_blocker_id != envelope_repair_blocker_id:
        blockers.append("repair_blocker_id_packet_envelope_mismatch")
    formal_id = packet_repair_blocker_id or envelope_repair_blocker_id
    declared_ids: list[tuple[str, str]] = []
    envelope_handoff = envelope.get("current_handoff_contract") if isinstance(envelope, Mapping) else None
    if isinstance(envelope_handoff, Mapping):
        manifest = envelope_handoff.get("input_material_manifest")
        if isinstance(manifest, Mapping):
            declared_ids.append(
                (
                    "envelope.current_handoff_contract.input_material_manifest.blocker_id",
                    str(manifest.get("blocker_id") or ""),
                )
            )
    payload = _strict_json_object_from_body(str(packet.get("body", "")))
    if payload is not None:
        for field in ("blocker_id", "recheck_for_blocker_id"):
            if payload.get(field):
                declared_ids.append((field, str(payload.get(field) or "")))
        handoff = payload.get("current_handoff_contract")
        if isinstance(handoff, Mapping):
            manifest = handoff.get("input_material_manifest")
            if isinstance(manifest, Mapping):
                declared_ids.append(
                    (
                        "body.current_handoff_contract.input_material_manifest.blocker_id",
                        str(manifest.get("blocker_id") or ""),
                    )
                )
        for section_name in ("generator_inputs", "subject_context"):
            section = payload.get(section_name)
            if isinstance(section, Mapping) and section.get("blocker_id"):
                declared_ids.append((f"{section_name}.blocker_id", str(section.get("blocker_id") or "")))
        manifest = payload.get("flowguard_evidence_manifest")
        if isinstance(manifest, Mapping):
            for index, entry in enumerate(manifest.get("entries") or []):
                if isinstance(entry, Mapping) and entry.get("blocker_id"):
                    declared_ids.append(
                        (
                            f"flowguard_evidence_manifest.entries[{index}].blocker_id",
                            str(entry.get("blocker_id") or ""),
                        )
                    )
    for label, declared_id in declared_ids:
        if declared_id and not formal_id:
            blockers.append(f"repair_blocker_id_missing_formal_field:{label}")
        if formal_id and declared_id != formal_id:
            blockers.append(f"repair_blocker_id_mismatch:{label}")
    return sorted(set(blockers))


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
    if packet.get("accepted_result_id") or _packet_is_noncurrent_for_routing(ledger, packet):
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


def open_authorized_input_materials_for_role(
    ledger: dict[str, Any],
    packet_id: str,
    lease_id: str,
) -> list[dict[str, Any]]:
    """Deliver the packet's authorized result inputs as part of packet open.

    The role still opens one current packet. Runtime delivers the authorized
    result bodies named by that packet and records receipts so submit-result can
    verify the inputs were current and role-scoped without requiring a separate
    micro-step for each material.
    """

    packet = _require(ledger["packets"], packet_id, "packet")
    lease = _require(ledger["leases"], lease_id, "lease")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if packet.get("assigned_lease_id") != lease_id:
        raise BlackBoxRuntimeError("lease cannot open this packet's authorized input materials")
    if lease.get("status") != "active":
        raise BlackBoxRuntimeError("inactive lease cannot open authorized input materials")
    if lease.get("packet_id") != packet_id:
        raise BlackBoxRuntimeError("lease packet mismatch")
    if lease.get("responsibility") != envelope.get("responsibility"):
        raise BlackBoxRuntimeError("lease responsibility does not match packet")
    if not lease.get("ack_received"):
        raise BlackBoxRuntimeError("lease must ACK before opening authorized input materials")
    if packet.get("accepted_result_id") or _packet_is_noncurrent_for_routing(ledger, packet):
        raise BlackBoxRuntimeError("accepted or stale packet cannot open authorized input materials")
    responsibility = str(lease.get("responsibility") or "")
    materials: list[dict[str, Any]] = []
    for row in _packet_authorized_result_reads(packet):
        result_id = str(row.get("result_id") or "")
        body_hash = str(row.get("body_hash") or "")
        if not result_id:
            continue
        result = _require(ledger["results"], result_id, "result")
        receipt = _result_body_open_receipt(
            packet,
            lease_id=lease_id,
            responsibility=responsibility,
            result_id=result_id,
            body_hash=body_hash,
        )
        if receipt is None:
            opened = open_result_body_for_role(ledger, packet_id, lease_id, result_id)
            body = str(opened["body"])
            receipt = opened["receipt"]
        else:
            body = str(result.get("body", ""))
        materials.append(
            {
                "schema_version": "black_box_flowpilot.authorized_input_material.v1",
                "result_id": result_id,
                "source_packet_id": str(result.get("packet_id") or ""),
                "purpose": str(row.get("purpose") or "authorized_result_read"),
                "required_before_submit": row.get("required_before_submit") is True,
                "body_hash": body_hash,
                "sealed_result_body": body,
                "sealed_body_visibility": "assigned_role_only",
                "open_receipt": dict(receipt),
            }
        )
    return materials


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
    packet_status = str(packet.get("status") or "")
    if packet_status in _NONCURRENT_PACKET_STATUSES:
        if packet_status == "quarantined_after_route_mutation" or "quarantined_packet" in blockers:
            packet["latest_quarantined_result_id"] = result_id
    elif not blockers:
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


@dataclass(frozen=True)
class PacketResultContractCheck:
    ok: bool
    contract_family_id: str
    blocked_reason: str = ""
    missing_required_fields: tuple[str, ...] = ()
    forbidden_fields_seen: tuple[str, ...] = ()
    required_result_body_fields: tuple[str, ...] = ()
    minimal_valid_shape: Mapping[str, Any] | None = None
    failed_branch: str = ""
    failed_field_path: str = ""
    branch_minimal_valid_shape: Mapping[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "contract_family_id": self.contract_family_id,
            "blocked_reason": self.blocked_reason,
            "missing_required_fields": list(self.missing_required_fields),
            "forbidden_fields_seen": list(self.forbidden_fields_seen),
            "required_result_body_fields": list(self.required_result_body_fields),
            "minimal_valid_shape": _copy_jsonable(self.minimal_valid_shape or {}),
            "failed_branch": self.failed_branch,
            "failed_field_path": self.failed_field_path,
            "branch_minimal_valid_shape": _copy_jsonable(self.branch_minimal_valid_shape or {}),
        }


def _packet_result_family_id(packet: Mapping[str, Any]) -> str:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    return packet_result_contracts.packet_result_family_id(envelope)


def _packet_stage_evidence_row(packet: Mapping[str, Any]) -> dict[str, Any]:
    return packet_stage_evidence_matrix.role_visible_stage_evidence_row_json(_packet_result_family_id(packet))


def _packet_effective_result_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    base = packet_result_contracts.effective_result_contract_from_envelope(envelope)
    handoff = envelope.get("current_handoff_contract") if isinstance(envelope, Mapping) else None
    report_contract = (
        handoff.get("required_report_contract")
        if isinstance(handoff, Mapping) and isinstance(handoff.get("required_report_contract"), Mapping)
        else None
    )
    if not isinstance(report_contract, Mapping):
        return base
    dynamic = _copy_jsonable(base)
    key_map = {
        "required_result_body_fields": "required_fields",
        "required_child_fields": "required_child_fields",
        "explicit_array_fields": "explicit_array_fields",
        "non_empty_array_fields": "non_empty_array_fields",
        "allowed_value_options": "allowed_value_options",
        "field_type_requirements": "field_type_requirements",
        "minimal_valid_shape": "minimal_valid_shape",
        "branch_valid_shapes": "branch_valid_shapes",
        "result_contract_profile_ids": "result_contract_profile_ids",
        "result_contract_profile_bindings": "result_contract_profile_bindings",
    }
    for source_key, target_key in key_map.items():
        if source_key in report_contract:
            dynamic[target_key] = _copy_jsonable(report_contract[source_key])
    for same_key in (
        "required_acceptance_item_ids",
        "ownership_coverage_rule",
        "required_node_acceptance_item_ids",
        "node_acceptance_projection_rule",
    ):
        if same_key in report_contract:
            dynamic[same_key] = _copy_jsonable(report_contract[same_key])
    if "validator" in report_contract:
        dynamic["validator"] = str(report_contract.get("validator") or "")
    return dynamic


_SKILL_STANDARD_REQUIRED_CHILD_FIELDS = (
    "obligation_id",
    "skill",
    "classification",
    "role_use",
    "use_context",
    "evidence_rule",
)


def _packet_result_required_fields(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in _packet_effective_result_contract(packet).get("required_fields", ()))


def _packet_result_required_child_fields(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in _packet_effective_result_contract(packet).get("required_child_fields", ()))


def _packet_result_explicit_array_fields(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in _packet_effective_result_contract(packet).get("explicit_array_fields", ()))


def _packet_result_non_empty_array_fields(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in _packet_effective_result_contract(packet).get("non_empty_array_fields", ()))


def _packet_result_forbidden_fields(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in _packet_effective_result_contract(packet).get("forbidden_fields", ()))


def _packet_result_minimal_valid_shape(packet: Mapping[str, Any]) -> dict[str, Any]:
    shape = _packet_effective_result_contract(packet).get("minimal_valid_shape")
    return _copy_jsonable(shape if isinstance(shape, Mapping) else {})


def _packet_result_branch_valid_shapes(packet: Mapping[str, Any]) -> dict[str, Any]:
    shapes = _packet_effective_result_contract(packet).get("branch_valid_shapes")
    return _copy_jsonable(shapes if isinstance(shapes, Mapping) else {})


def _contract_pass(packet: Mapping[str, Any]) -> PacketResultContractCheck:
    return PacketResultContractCheck(
        ok=True,
        contract_family_id=_packet_result_family_id(packet),
        required_result_body_fields=_packet_result_required_fields(packet),
        minimal_valid_shape=_packet_result_minimal_valid_shape(packet),
    )


def _contract_block(
    packet: Mapping[str, Any],
    reason: str,
    *,
    missing_required_fields: tuple[str, ...] | list[str] = (),
    forbidden_fields_seen: tuple[str, ...] | list[str] = (),
    required_result_body_fields: tuple[str, ...] | list[str] | None = None,
    failed_branch: str = "",
    failed_field_path: str = "",
    branch_minimal_valid_shape: Mapping[str, Any] | None = None,
) -> PacketResultContractCheck:
    return PacketResultContractCheck(
        ok=False,
        contract_family_id=_packet_result_family_id(packet),
        blocked_reason=reason,
        missing_required_fields=tuple(dict.fromkeys(str(field) for field in missing_required_fields if str(field))),
        forbidden_fields_seen=tuple(dict.fromkeys(str(field) for field in forbidden_fields_seen if str(field))),
        required_result_body_fields=tuple(required_result_body_fields or _packet_result_required_fields(packet)),
        minimal_valid_shape=_packet_result_minimal_valid_shape(packet),
        failed_branch=failed_branch,
        failed_field_path=failed_field_path,
        branch_minimal_valid_shape=branch_minimal_valid_shape,
    )


def _top_level_missing_fields(payload: Mapping[str, Any], required_fields: tuple[str, ...]) -> tuple[str, ...]:
    missing: list[str] = []
    for field in required_fields:
        value = payload.get(field)
        if value is None or value == "":
            missing.append(field)
    return tuple(missing)


def _top_level_forbidden_fields(payload: Mapping[str, Any], forbidden_fields: tuple[str, ...]) -> tuple[str, ...]:
    present: list[str] = []
    for field in forbidden_fields:
        if "[]" in field:
            exists, _values = _payload_path_values(payload, field)
            if exists:
                present.append(field)
            continue
        if "." in field:
            exists, _value = _payload_path_value(payload, field)
            if exists:
                present.append(field)
            continue
        if field in payload:
            present.append(field)
    return tuple(present)


def _payload_path_value(payload: Mapping[str, Any], field_path: str) -> tuple[bool, Any]:
    current: Any = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _payload_path_values(payload: Mapping[str, Any], field_path: str) -> tuple[bool, list[Any]]:
    parts = field_path.split(".")

    def visit(current: Any, index: int) -> list[Any] | None:
        if index >= len(parts):
            return [current]
        part = parts[index]
        if part.endswith("[]"):
            key = part[:-2]
            if not isinstance(current, Mapping) or key not in current:
                return None
            value = current[key]
            if not isinstance(value, list) or not value:
                return None
            values: list[Any] = []
            for item in value:
                nested = visit(item, index + 1)
                if nested is None:
                    return None
                values.extend(nested)
            return values
        if not isinstance(current, Mapping) or part not in current:
            return None
        return visit(current[part], index + 1)

    values = visit(payload, 0)
    if values is None:
        return False, []
    return True, values


def _payload_path_missing(payload: Any, field_path: str) -> bool:
    parts = field_path.split(".")

    def visit(current: Any, index: int) -> bool:
        if index >= len(parts):
            return current is None or current == ""
        part = parts[index]
        if part.endswith("[]"):
            key = part[:-2]
            if not isinstance(current, Mapping) or key not in current:
                return True
            value = current[key]
            if not isinstance(value, list) or not value:
                return True
            return any(visit(item, index + 1) for item in value)
        if not isinstance(current, Mapping) or part not in current:
            return True
        return visit(current[part], index + 1)

    return visit(payload, 0)


def _missing_child_fields(payload: Mapping[str, Any], required_child_fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(field for field in required_child_fields if _payload_path_missing(payload, field))


def _missing_or_wrong_explicit_array_fields(
    payload: Mapping[str, Any],
    explicit_array_fields: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing: list[str] = []
    wrong_type: list[str] = []
    for field in explicit_array_fields:
        if "[]" in field:
            exists, values = _payload_path_values(payload, field)
            if not exists:
                missing.append(field)
                continue
            if any(not isinstance(value, list) for value in values):
                wrong_type.append(field)
            continue
        exists, value = _payload_path_value(payload, field)
        if not exists:
            missing.append(field)
            continue
        if not isinstance(value, list):
            wrong_type.append(field)
    return tuple(missing), tuple(wrong_type)


def _missing_or_wrong_non_empty_array_fields(
    payload: Mapping[str, Any],
    non_empty_array_fields: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing_or_empty: list[str] = []
    wrong_type: list[str] = []
    for field in non_empty_array_fields:
        if "[]" in field:
            exists, values = _payload_path_values(payload, field)
            if not exists:
                missing_or_empty.append(field)
                continue
            if any(not isinstance(value, list) for value in values):
                wrong_type.append(field)
                continue
            if any(not value for value in values):
                missing_or_empty.append(field)
            continue
        exists, value = _payload_path_value(payload, field)
        if not exists:
            missing_or_empty.append(field)
            continue
        if not isinstance(value, list):
            wrong_type.append(field)
            continue
        if not value:
            missing_or_empty.append(field)
    return tuple(missing_or_empty), tuple(wrong_type)


def _allowed_value_option_violations_for_payload(
    packet: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[str, ...]:
    violations: list[str] = []
    allowed_options = _packet_effective_result_contract(packet).get("allowed_value_options") or {}
    for raw_field_path, allowed_values in allowed_options.items():
        if not isinstance(allowed_values, list):
            continue
        field_path = str(raw_field_path).split(" when ", 1)[0]
        if "[]" in field_path:
            exists, values = _payload_path_values(payload, field_path)
        else:
            exists, value = _payload_path_value(payload, field_path)
            values = [value] if exists else []
        if not exists:
            continue
        allowed = tuple(allowed_values)
        for value in values:
            candidate = value.strip() if isinstance(value, str) else value
            if candidate not in allowed:
                violations.append(field_path)
                break
    return tuple(dict.fromkeys(violations))


def _value_matches_field_type_requirement(value: Any, requirement: str) -> bool:
    if requirement == "object":
        return isinstance(value, Mapping)
    if requirement == "string":
        return isinstance(value, str)
    if requirement == "boolean:true":
        return value is True
    if requirement.startswith("string:"):
        return isinstance(value, str) and value == requirement.split(":", 1)[1]
    if requirement == "array:string":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if requirement == "array:object":
        return isinstance(value, list) and all(isinstance(item, Mapping) for item in value)
    return True


def _field_type_requirement_violations_for_payload(
    packet: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[str, ...]:
    requirements = _packet_effective_result_contract(packet).get("field_type_requirements") or {}
    violations: list[str] = []
    for raw_field_path, raw_requirement in requirements.items():
        field_path = str(raw_field_path)
        requirement = str(raw_requirement)
        if "[]" in field_path:
            exists, values = _payload_path_values(payload, field_path)
            if not exists:
                continue
            if any(not _value_matches_field_type_requirement(value, requirement) for value in values):
                violations.append(field_path)
            continue
        exists, value = _payload_path_value(payload, field_path)
        if not exists:
            continue
        if not _value_matches_field_type_requirement(value, requirement):
            violations.append(field_path)
    return tuple(dict.fromkeys(violations))


def _json_payload_contract_check(packet: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[dict[str, Any] | None, PacketResultContractCheck | None]:
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return None, _contract_block(
            packet,
            f"{_packet_result_family_id(packet)} result requires a current strict JSON object",
            missing_required_fields=_packet_result_required_fields(packet),
        )
    forbidden = _top_level_forbidden_fields(payload, _packet_result_forbidden_fields(packet))
    missing = _top_level_missing_fields(payload, _packet_result_required_fields(packet))
    missing_child = _missing_child_fields(payload, _packet_result_required_child_fields(packet))
    missing_arrays, wrong_array_types = _missing_or_wrong_explicit_array_fields(
        payload,
        _packet_result_explicit_array_fields(packet),
    )
    missing_non_empty_arrays, wrong_non_empty_array_types = _missing_or_wrong_non_empty_array_fields(
        payload,
        _packet_result_non_empty_array_fields(packet),
    )
    all_missing = tuple(dict.fromkeys((*missing, *missing_child, *missing_arrays, *missing_non_empty_arrays)))
    all_wrong_array_types = tuple(dict.fromkeys((*wrong_array_types, *wrong_non_empty_array_types)))
    if forbidden or all_missing or all_wrong_array_types:
        pieces: list[str] = []
        if all_missing:
            pieces.append("missing required field(s): " + ", ".join(all_missing))
        if all_wrong_array_types:
            pieces.append("explicit array field(s) must be arrays: " + ", ".join(all_wrong_array_types))
        if forbidden:
            pieces.append("forbidden field(s): " + ", ".join(forbidden))
        return payload, _contract_block(
            packet,
            "; ".join(pieces),
            missing_required_fields=(*all_missing, *all_wrong_array_types),
            forbidden_fields_seen=forbidden,
        )
    field_type_violations = _field_type_requirement_violations_for_payload(packet, payload)
    if field_type_violations:
        type_requirements = _packet_effective_result_contract(packet).get("field_type_requirements") or {}
        return payload, _contract_block(
            packet,
            "field type(s) must match field_type_requirements: "
            + ", ".join(
                f"{field}={type_requirements.get(field)}"
                for field in field_type_violations
            ),
            missing_required_fields=field_type_violations,
        )
    allowed_value_violations = _allowed_value_option_violations_for_payload(packet, payload)
    if allowed_value_violations:
        return payload, _contract_block(
            packet,
            "field value(s) must be selected from allowed_value_options: "
            + ", ".join(allowed_value_violations),
            missing_required_fields=allowed_value_violations,
        )
    return payload, None


def _strict_packet_outcome_contract_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    if not payload:
        return _contract_block(packet, "packet result requires a current strict JSON object")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    if packet_kind in {"flowguard_check", "review"}:
        if not isinstance(payload.get("passed"), bool):
            return _contract_block(
                packet,
                "formal review/FlowGuard report requires boolean passed",
                missing_required_fields=("passed",),
            )
        return _contract_pass(packet)
    if "decision" not in payload:
        alias_keys = sorted(key for key in _OUTCOME_ALIAS_KEYS if key in payload)
        if alias_keys:
            return _contract_block(
                packet,
                "packet result uses unsupported outcome alias field(s): " + ",".join(alias_keys),
                forbidden_fields_seen=alias_keys,
                missing_required_fields=("decision",),
            )
        return _contract_block(packet, "packet result requires top-level decision", missing_required_fields=("decision",))
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision not in (_PASSING_OUTCOME_DECISIONS | _BLOCKING_OUTCOME_DECISIONS):
        return _contract_block(packet, "packet result decision must be an explicit allowed pass/block decision")
    return _contract_pass(packet)


def _parent_backward_replay_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    decision = _normalize_outcome_token(payload.get("composition_decision"))
    if decision not in {"pass", "block"}:
        return _contract_block(
            packet,
            "parent backward replay composition_decision must be one of: pass, block",
            missing_required_fields=("composition_decision",),
        )
    parent_node_id = str(payload.get("parent_node_id") or "").strip()
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    expected_node_id = str(envelope.get("route_node_id") or "").strip()
    if expected_node_id and parent_node_id != expected_node_id:
        return _contract_block(
            packet,
            "parent backward replay parent_node_id must match the packet route_node_id",
            missing_required_fields=("parent_node_id",),
        )
    blockers = payload.get("blockers")
    assert isinstance(blockers, list)
    if decision == "pass" and blockers:
        return _contract_block(
            packet,
            "parent backward replay composition_decision=pass cannot carry blockers",
            missing_required_fields=("blockers",),
        )
    if decision == "block" and not blockers:
        return _contract_block(
            packet,
            "parent backward replay composition_decision=block requires at least one blocker",
            missing_required_fields=("blockers",),
        )
    allowed_blocker_classes = set(packet_stage_evidence_matrix.allowed_blocker_classes_for_family("task.parent_backward_replay"))
    for index, blocker in enumerate(blockers, start=1):
        if not isinstance(blocker, Mapping):
            return _contract_block(packet, f"parent backward replay blockers[{index}] must be an object")
        missing = [
            f"blockers[{index}].{field}"
            for field in ("blocker_id", "blocker_class", "recommended_resolution")
            if not str(blocker.get(field) or "").strip()
        ]
        blocker_class = str(blocker.get("blocker_class") or "")
        if blocker_class and blocker_class not in allowed_blocker_classes:
            missing.append(f"blockers[{index}].blocker_class")
        if missing:
            return _contract_block(
                packet,
                "parent backward replay blocker is missing current fields or allowed blocker_class: "
                + ", ".join(missing),
                missing_required_fields=tuple(dict.fromkeys(missing)),
            )
    return _contract_pass(packet)


_FLOWGUARD_SELF_CHECK_TRUE_FIELDS = (
    "all_required_fields_present",
    "exact_field_names_used",
    "empty_required_arrays_explicit",
    "runtime_mechanical_validation_passed",
)
_FLOWGUARD_HARD_EVIDENCE_PASS_DECISIONS = {"pass", "passed", "ok", "clear", "clean"}
_FLOWGUARD_HARD_EVIDENCE_BLOCK_DECISIONS = {
    "block",
    "blocked",
    "fail",
    "failed",
    "failure",
    "missing_code_contract",
    "revalidation_required",
    "not_ok",
    "stale",
}


def _flowguard_current_report_violation(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    if payload.get("reviewed_by_role") != "flowguard_operator":
        return _contract_block(
            packet,
            "FlowGuard result must be reviewed_by_role=flowguard_operator",
            missing_required_fields=("reviewed_by_role",),
        )
    contract_self_check = payload.get("contract_self_check")
    if not isinstance(contract_self_check, Mapping):
        return _contract_block(
            packet,
            "FlowGuard result requires object contract_self_check",
            missing_required_fields=("contract_self_check",),
        )
    failed_self_check_fields = tuple(
        f"contract_self_check.{field}"
        for field in _FLOWGUARD_SELF_CHECK_TRUE_FIELDS
        if contract_self_check.get(field) is not True
    )
    if failed_self_check_fields:
        return _contract_block(
            packet,
            "FlowGuard result self-check failed; mechanical report fields must be repaired before acceptance",
            missing_required_fields=failed_self_check_fields,
        )

    packet_body = _flowguard_packet_body_payload(packet)
    evidence_policy = packet_body.get("evidence_output_policy")
    if not isinstance(evidence_policy, Mapping):
        return _contract_block(
            packet,
            "FlowGuard check packet requires evidence_output_policy so formal evidence has one current owner",
            missing_required_fields=("evidence_output_policy",),
        )
    if evidence_policy.get("required_for_formal_run") is not True:
        return _contract_block(
            packet,
            "FlowGuard check packet evidence_output_policy.required_for_formal_run must be true",
            missing_required_fields=("evidence_output_policy.required_for_formal_run",),
        )
    evidence_root = str(evidence_policy.get("run_local_evidence_root") or "")
    if not evidence_root:
        return _contract_block(
            packet,
            "FlowGuard check packet requires evidence_output_policy.run_local_evidence_root",
            missing_required_fields=("evidence_output_policy.run_local_evidence_root",),
        )

    top_level_passed = payload.get("passed") is True
    blockers = payload.get("blockers")
    if top_level_passed and isinstance(blockers, list) and blockers:
        return _contract_block(
            packet,
            "FlowGuard passed=true cannot carry blockers",
            missing_required_fields=("blockers",),
        )
    semantic_violation = _flowguard_semantic_recheck_contract_violation(packet, payload)
    if semantic_violation is not None:
        return semantic_violation
    required_subject_artifact_ids = _flowguard_required_subject_artifact_ids(packet)
    if top_level_passed and required_subject_artifact_ids:
        consumed_artifacts = payload.get("subject_artifacts_consumed")
        if not isinstance(consumed_artifacts, list):
            return _contract_block(
                packet,
                "FlowGuard parent repair pass requires subject_artifacts_consumed for every required subject artifact",
                missing_required_fields=("subject_artifacts_consumed",),
            )
        consumed_ids: set[str] = set()
        for item in consumed_artifacts:
            if isinstance(item, Mapping):
                artifact_id = str(item.get("artifact_id") or item.get("id") or "").strip()
            else:
                artifact_id = str(item or "").strip()
            if artifact_id:
                consumed_ids.add(artifact_id)
        missing_artifacts = [
            artifact_id for artifact_id in required_subject_artifact_ids if artifact_id not in consumed_ids
        ]
        if missing_artifacts:
            return _contract_block(
                packet,
                "FlowGuard parent repair pass did not consume required subject artifact(s): "
                + ", ".join(missing_artifacts),
                missing_required_fields=("subject_artifacts_consumed",),
            )
    artifact_decision = _flowguard_packet_artifact_hard_decision(ledger, packet)
    if artifact_decision.get("required") and artifact_decision.get("missing"):
        return _contract_block(
            packet,
            "FlowGuard formal evidence artifact is required but missing from the packet-owned run-local evidence root",
            missing_required_fields=("flowguard_evidence.json",),
        )
    if artifact_decision.get("invalid"):
        return _contract_block(
            packet,
            "FlowGuard formal evidence artifact is not readable as current JSON evidence",
            missing_required_fields=("flowguard_evidence.json",),
        )
    artifact_hard_decision = _normalize_outcome_token(artifact_decision.get("decision"))
    if top_level_passed and artifact_hard_decision in _FLOWGUARD_HARD_EVIDENCE_BLOCK_DECISIONS:
        return _contract_block(
            packet,
            "FlowGuard result cannot pass while packet-owned hard evidence artifact reports blocked evidence",
            missing_required_fields=("flowguard_evidence.json.model_test_alignment_report.decision",),
        )
    if top_level_passed and artifact_hard_decision and artifact_hard_decision not in _FLOWGUARD_HARD_EVIDENCE_PASS_DECISIONS:
        return _contract_block(
            packet,
            "FlowGuard passed=true requires packet-owned hard evidence artifact decision=pass",
            missing_required_fields=("flowguard_evidence.json.model_test_alignment_report.decision",),
        )
    return _contract_pass(packet)


def _flowguard_packet_body_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = _strict_json_object_from_body(str(packet.get("body", "")))
    except BlackBoxRuntimeError:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _flowguard_reissue_inherited_authorized_result_reads(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    reads = _packet_authorized_result_reads(packet)
    if not reads:
        return []
    normalized = _normalize_authorized_result_reads(ledger, list(reads))
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    handoff = envelope.get("current_handoff_contract")
    manifest = (
        handoff.get("input_material_manifest", {})
        if isinstance(handoff, Mapping) and isinstance(handoff.get("input_material_manifest"), Mapping)
        else {}
    )
    required_ids = [
        str(row.get("result_id") or "")
        for row in normalized
        if row.get("required_before_submit") is True and str(row.get("result_id") or "")
    ]
    manifest_required_ids = manifest.get("required_authorized_reads_before_submit")
    if isinstance(manifest_required_ids, list) and manifest_required_ids:
        if sorted(str(item) for item in manifest_required_ids) != sorted(required_ids):
            raise BlackBoxRuntimeError(
                "source FlowGuard packet authorized_result_reads disagree with current_handoff_contract"
            )
    return normalized


_FLOWGUARD_REISSUE_INHERITED_BODY_FIELDS = (
    "required_subject_artifacts",
    "subject_bound_report_contract",
    "recheck_for_blocker_id",
    "generator_inputs",
    "subject_context",
    "semantic_recheck_contract",
    "recheck_reason",
    "route_process_focus",
    "structural_route_simulation_focus",
)


def _flowguard_reissue_inherited_body_payload(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    fresh_packet_id: str,
) -> dict[str, Any]:
    body_payload = _flowguard_packet_body_payload(packet)
    inherited: dict[str, Any] = {}
    evidence_policy = body_payload.get("evidence_output_policy")
    if isinstance(evidence_policy, Mapping):
        fresh_policy = _copy_jsonable(evidence_policy)
        if isinstance(fresh_policy, dict):
            fresh_policy["run_local_evidence_root"] = _flowguard_packet_evidence_root(ledger, fresh_packet_id)
            fresh_policy["required_for_formal_run"] = True
            inherited["evidence_output_policy"] = fresh_policy
    for field in _FLOWGUARD_REISSUE_INHERITED_BODY_FIELDS:
        if field in body_payload:
            inherited[field] = _copy_jsonable(body_payload[field])
    inherited["reissue_inherited_contract"] = {
        "schema_version": "black_box_flowpilot.flowguard_reissue_inherited_contract.v1",
        "source_packet_id": str(packet.get("packet_id") or ""),
        "fresh_packet_id": fresh_packet_id,
        "evidence_output_policy_retargeted": isinstance(inherited.get("evidence_output_policy"), Mapping),
        "rule": (
            "A mechanical reissue of a FlowGuard check remains the same current contract. "
            "It must preserve blocker identity, subject-bound recheck requirements, required subject artifacts, "
            "authorized result-body read requirements, and formal evidence policy while retargeting "
            "the evidence root to the fresh packet id."
        ),
    }
    return inherited


def _flowguard_packet_evidence_artifact_path(ledger: Mapping[str, Any], packet: Mapping[str, Any]) -> Path | None:
    packet_id = str(packet.get("packet_id") or "")
    run_root = str(ledger.get("run_root") or "")
    if run_root and packet_id:
        return Path(run_root) / "evidence" / "flowguard" / packet_id / "flowguard_evidence.json"
    body_payload = _flowguard_packet_body_payload(packet)
    evidence_policy = body_payload.get("evidence_output_policy")
    root_value = ""
    if isinstance(evidence_policy, Mapping):
        root_value = str(evidence_policy.get("run_local_evidence_root") or "")
    if root_value:
        root = Path(root_value)
        if root.is_absolute():
            return root / "flowguard_evidence.json"
    return None


def _flowguard_artifact_decision_from_payload(payload: Mapping[str, Any]) -> str:
    report = payload.get("model_test_alignment_report")
    if isinstance(report, Mapping):
        decision = _normalize_outcome_token(report.get("decision"))
        if decision:
            return decision
    for field in ("hard_evidence_decision", "decision"):
        decision = _normalize_outcome_token(payload.get(field))
        if decision:
            return decision
    ok_value = payload.get("ok")
    if ok_value is True:
        return "pass"
    if ok_value is False:
        return "blocked"
    return ""


def _flowguard_packet_artifact_hard_decision(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    body_payload = _flowguard_packet_body_payload(packet)
    evidence_policy = body_payload.get("evidence_output_policy")
    formal_required = bool(
        isinstance(evidence_policy, Mapping)
        and evidence_policy.get("required_for_formal_run") is True
    )
    path = _flowguard_packet_evidence_artifact_path(ledger, packet)
    if path is None:
        return {
            "required": False,
            "missing": False,
            "invalid": False,
            "decision": "",
            "path": "",
        }
    if not path.exists():
        return {
            "required": formal_required,
            "missing": True,
            "invalid": False,
            "decision": "",
            "path": path.as_posix(),
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {
            "required": formal_required,
            "missing": False,
            "invalid": True,
            "decision": "",
            "path": path.as_posix(),
        }
    if not isinstance(payload, Mapping):
        return {
            "required": formal_required,
            "missing": False,
            "invalid": True,
            "decision": "",
            "path": path.as_posix(),
        }
    return {
        "required": formal_required,
        "missing": False,
        "invalid": False,
        "decision": _flowguard_artifact_decision_from_payload(payload),
        "path": path.as_posix(),
    }


def _packet_result_contract_profile_binding(packet: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    profile_ids = set(packet_result_contracts.result_contract_profile_ids_from_envelope(envelope))
    if profile_id not in profile_ids:
        return {}
    bindings = packet_result_contracts.result_contract_profile_bindings_from_envelope(envelope)
    binding = bindings.get(profile_id)
    return binding if isinstance(binding, Mapping) else {}


def _flowguard_semantic_recheck_contract_violation(
    packet: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> PacketResultContractCheck | None:
    binding = _packet_result_contract_profile_binding(packet, "flowguard.semantic_recheck_required")
    if not binding:
        return None
    packet_body = _flowguard_packet_body_payload(packet)
    contract = packet_body.get("semantic_recheck_contract")
    if not isinstance(contract, Mapping):
        contract = {}
    semantic = payload.get("semantic_recheck")
    if not isinstance(semantic, Mapping):
        return _contract_block(
            packet,
            "FlowGuard blocker-bound semantic recheck requires object semantic_recheck",
            missing_required_fields=("semantic_recheck",),
        )
    blocker_id = str(binding.get("blocker_id") or "")
    if blocker_id and str(semantic.get("blocker_id") or "") != blocker_id:
        return _contract_block(
            packet,
            "FlowGuard semantic_recheck.blocker_id must match the active repair blocker",
            missing_required_fields=("semantic_recheck.blocker_id",),
        )
    required_true_fields = (
        "subject_result_consumed",
        "subject_bound_semantic_coverage",
    )
    missing = tuple(
        f"semantic_recheck.{field}"
        for field in required_true_fields
        if semantic.get(field) is not True
    )
    if missing:
        return _contract_block(
            packet,
            "FlowGuard blocker-bound semantic recheck must prove subject-bound coverage",
            missing_required_fields=missing,
        )
    coverage_boundary = _normalize_outcome_token(semantic.get("coverage_boundary"))
    forbidden = {
        _normalize_outcome_token(item)
        for item in contract.get("forbidden_pass_boundaries", [])
        if _normalize_outcome_token(item)
    }
    if coverage_boundary and coverage_boundary in forbidden:
        return _contract_block(
            packet,
            "FlowGuard semantic recheck cannot pass with a shape-only or current-contract-only coverage boundary",
            missing_required_fields=("semantic_recheck.coverage_boundary",),
        )
    consumed_read_ids = semantic.get("consumed_authorized_result_read_ids")
    if not isinstance(consumed_read_ids, list) or not consumed_read_ids:
        return _contract_block(
            packet,
            "FlowGuard semantic recheck must list consumed authorized subject result read ids",
            missing_required_fields=("semantic_recheck.consumed_authorized_result_read_ids",),
        )
    required_read_ids = [
        str(item)
        for item in binding.get("authorized_result_read_ids", [])
        if str(item)
    ] if isinstance(binding.get("authorized_result_read_ids"), list) else []
    if required_read_ids:
        consumed_read_id_values = [str(item) for item in consumed_read_ids if str(item)]
        missing_read_ids = sorted(set(required_read_ids) - set(consumed_read_id_values))
        unknown_read_ids = sorted(set(consumed_read_id_values) - set(required_read_ids))
        if missing_read_ids or unknown_read_ids:
            return _contract_block(
                packet,
                "FlowGuard semantic recheck must consume exactly the authorized result read ids from the packet profile",
                missing_required_fields=("semantic_recheck.consumed_authorized_result_read_ids",),
            )
    required_obligation_ids = [
        str(item)
        for item in binding.get("repair_obligation_ids", [])
        if str(item)
    ] if isinstance(binding.get("repair_obligation_ids"), list) else []
    if required_obligation_ids:
        consumed_obligation_ids = (
            [str(item) for item in semantic.get("consumed_repair_obligation_ids", []) if str(item)]
            if isinstance(semantic.get("consumed_repair_obligation_ids"), list)
            else []
        )
        missing_obligation_ids = sorted(set(required_obligation_ids) - set(consumed_obligation_ids))
        unknown_obligation_ids = sorted(set(consumed_obligation_ids) - set(required_obligation_ids))
        if missing_obligation_ids or unknown_obligation_ids:
            return _contract_block(
                packet,
                "FlowGuard semantic recheck must consume every repair evidence obligation exactly within the blocker contract",
                missing_required_fields=("semantic_recheck.consumed_repair_obligation_ids",),
            )
    return None


def _terminal_backward_replay_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    packet_payload = _strict_json_object_from_body(str(packet.get("body", "")))
    segment_targets = packet_payload.get("segment_targets") if isinstance(packet_payload, Mapping) else None
    if not isinstance(segment_targets, list) or not segment_targets:
        return _contract_block(
            packet,
            "terminal backward replay packet is missing runtime-issued segment_targets",
            missing_required_fields=("segment_targets",),
        )
    target_ids: list[str] = []
    for index, target in enumerate(segment_targets, start=1):
        if not isinstance(target, Mapping) or not str(target.get("segment_id") or "").strip():
            return _contract_block(
                packet,
                f"terminal backward replay segment_targets[{index}] is missing segment_id",
                missing_required_fields=(f"segment_targets[{index}].segment_id",),
            )
        target_ids.append(str(target.get("segment_id")))
    route_segment_replay = payload.get("route_segment_replay")
    if not isinstance(route_segment_replay, list) or not route_segment_replay:
        return _contract_block(
            packet,
            "terminal backward replay requires non-empty route_segment_replay",
            missing_required_fields=("route_segment_replay",),
        )
    seen_segment_ids: list[str] = []
    for index, segment in enumerate(route_segment_replay, start=1):
        if not isinstance(segment, Mapping):
            return _contract_block(packet, f"terminal backward replay route_segment_replay[{index}] must be an object")
        missing: list[str] = []
        for field in ("segment_id", "segment_kind", "status", "basis"):
            if not str(segment.get(field) or "").strip():
                missing.append(f"route_segment_replay[{index}].{field}")
        if str(segment.get("status") or "") not in {"closed", "blocked", "waived", "superseded"}:
            missing.append(f"route_segment_replay[{index}].status")
        if missing:
            return _contract_block(
                packet,
                "terminal backward replay segment is missing required current fields: " + ", ".join(missing),
                missing_required_fields=tuple(dict.fromkeys(missing)),
            )
        seen_segment_ids.append(str(segment.get("segment_id")))
    duplicate_ids = sorted({segment_id for segment_id in seen_segment_ids if seen_segment_ids.count(segment_id) > 1})
    missing_ids = sorted(set(target_ids) - set(seen_segment_ids))
    unexpected_ids = sorted(set(seen_segment_ids) - set(target_ids))
    if duplicate_ids or missing_ids or unexpected_ids:
        details: list[str] = []
        if missing_ids:
            details.append("missing segment id(s): " + ", ".join(missing_ids))
        if unexpected_ids:
            details.append("unexpected segment id(s): " + ", ".join(unexpected_ids))
        if duplicate_ids:
            details.append("duplicate segment id(s): " + ", ".join(duplicate_ids))
        return _contract_block(
            packet,
            "terminal backward replay segment ids must match runtime-issued targets exactly; " + "; ".join(details),
            missing_required_fields=("route_segment_replay.segment_id",),
        )
    for field_name in ("final_artifact_refs", "acceptance_item_closure"):
        rows = payload.get(field_name)
        assert isinstance(rows, list)
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                return _contract_block(packet, f"terminal backward replay {field_name}[{index}] must be an object")
            missing = [
                f"{field_name}[{index}].{field}"
                for field in ("id", "status", "basis")
                if not str(row.get(field) or "").strip()
            ]
            if missing:
                return _contract_block(
                    packet,
                    "terminal backward replay row is missing required current fields: " + ", ".join(missing),
                    missing_required_fields=tuple(missing),
                )
    final_blockers = payload.get("final_blockers")
    assert isinstance(final_blockers, list)
    blockers = payload.get("blockers")
    assert isinstance(blockers, list)
    if bool(final_blockers) != bool(blockers):
        return _contract_block(
            packet,
            "terminal backward replay common blockers must mirror final_blockers presence for PM routing",
            missing_required_fields=("blockers", "final_blockers"),
        )
    expected_passed = not bool(final_blockers)
    if payload.get("passed") is not expected_passed:
        return _contract_block(
            packet,
            f"terminal backward replay passed must be {str(expected_passed).lower()} for the current final_blockers state",
            missing_required_fields=("passed",),
        )
    blocked_segment_ids = [
        str(segment.get("segment_id") or "")
        for segment in route_segment_replay
        if isinstance(segment, Mapping) and str(segment.get("status") or "") == "blocked"
    ]
    if blocked_segment_ids and not final_blockers:
        return _contract_block(
            packet,
            "terminal backward replay blocked segments require final_blockers for PM repair routing",
            missing_required_fields=("final_blockers",),
        )
    for index, blocker in enumerate(final_blockers, start=1):
        if not isinstance(blocker, Mapping):
            return _contract_block(packet, f"terminal backward replay final_blockers[{index}] must be an object")
        missing = [
            f"final_blockers[{index}].{field}"
            for field in ("blocker_id", "blocker_class", "recommended_resolution")
            if not str(blocker.get(field) or "").strip()
        ]
        if missing:
            return _contract_block(
                packet,
                "terminal backward replay blocker is missing required current fields: " + ", ".join(missing),
                missing_required_fields=tuple(missing),
            )
    return _contract_pass(packet)


def _high_standard_contract_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    rows = payload.get("requirements")
    if not isinstance(rows, list) or not rows:
        return _contract_block(
            packet,
            "high_standard_contract result requires top-level requirements list",
            missing_required_fields=("requirements",),
        )
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            return _contract_block(packet, f"high_standard_contract requirements[{index}] must be an object")
        if not str(row.get("requirement_id") or "").strip():
            return _contract_block(
                packet,
                f"high_standard_contract requirements[{index}] requires requirement_id",
                missing_required_fields=(f"requirements[{index}].requirement_id",),
            )
        if not str(row.get("classification") or "").strip():
            return _contract_block(
                packet,
                f"high_standard_contract requirements[{index}] requires classification",
                missing_required_fields=(f"requirements[{index}].classification",),
            )
        if not str(row.get("summary") or "").strip():
            return _contract_block(
                packet,
                f"high_standard_contract requirements[{index}] requires summary",
                missing_required_fields=(f"requirements[{index}].summary",),
            )
        if not str(row.get("source_user_intent") or "").strip():
            return _contract_block(
                packet,
                f"high_standard_contract requirements[{index}] requires source_user_intent",
                missing_required_fields=(f"requirements[{index}].source_user_intent",),
            )
        if not str(row.get("closure_rule") or "").strip():
            return _contract_block(
                packet,
                f"high_standard_contract requirements[{index}] requires closure_rule",
                missing_required_fields=(f"requirements[{index}].closure_rule",),
            )
    registry = payload.get("acceptance_item_registry")
    if not isinstance(registry, Mapping):
        return _contract_block(
            packet,
            "high_standard_contract result requires acceptance_item_registry",
            missing_required_fields=("acceptance_item_registry",),
        )
    item_rows = registry.get("items")
    if not isinstance(item_rows, list) or not item_rows:
        return _contract_block(
            packet,
            "acceptance_item_registry requires non-empty items list",
            missing_required_fields=("acceptance_item_registry.items",),
        )
    requirement_ids = {str(row.get("requirement_id") or "") for row in rows if isinstance(row, Mapping)}
    blocking_requirement_ids = {
        str(row.get("requirement_id") or "")
        for row in rows
        if isinstance(row, Mapping)
        and str(row.get("classification") or "") in {"hard_current", "high_standard_current"}
    }
    seen_item_ids: set[str] = set()
    item_requirement_refs: set[str] = set()
    source_types: set[str] = set()
    for index, item in enumerate(item_rows, start=1):
        if not isinstance(item, Mapping):
            return _contract_block(packet, f"acceptance_item_registry.items[{index}] must be an object")
        missing: list[str] = []
        for field in (
            "acceptance_item_id",
            "source_type",
            "summary",
            "quality_floor",
            "future_evidence_rule",
            "status",
        ):
            if not str(item.get(field) or "").strip():
                missing.append(f"acceptance_item_registry.items[{index}].{field}")
        for field in ("source_requirement_ids",):
            if field in item and not isinstance(item.get(field), list):
                missing.append(f"acceptance_item_registry.items[{index}].{field}")
        if missing:
            return _contract_block(
                packet,
                "acceptance item is missing required current fields: " + ", ".join(missing),
                missing_required_fields=tuple(missing),
            )
        item_id = str(item.get("acceptance_item_id") or "").strip()
        if item_id in seen_item_ids:
            return _contract_block(
                packet,
                f"duplicate acceptance_item_id {item_id}",
                missing_required_fields=(f"acceptance_item_registry.items[{index}].acceptance_item_id",),
            )
        seen_item_ids.add(item_id)
        source_type = str(item.get("source_type") or "")
        source_types.add(source_type)
        refs = [str(ref) for ref in item.get("source_requirement_ids") or [] if str(ref)]
        unknown_refs = sorted(set(refs) - requirement_ids)
        if unknown_refs:
            return _contract_block(
                packet,
                f"acceptance item {item_id} references unknown requirement id(s): {', '.join(unknown_refs)}",
                missing_required_fields=(f"acceptance_item_registry.items[{index}].source_requirement_ids",),
            )
        item_requirement_refs.update(refs)
    if not (source_types & {"user_explicit", "user_implicit"}):
        return _contract_block(
            packet,
            "acceptance_item_registry requires at least one user-explicit or user-implicit item",
            missing_required_fields=("acceptance_item_registry.items[].source_type",),
        )
    if "pm_high_standard" not in source_types:
        return _contract_block(
            packet,
            "acceptance_item_registry requires at least one PM high-standard item",
            missing_required_fields=("acceptance_item_registry.items[].source_type",),
        )
    missing_requirement_refs = sorted(blocking_requirement_ids - item_requirement_refs)
    if missing_requirement_refs:
        return _contract_block(
            packet,
            "acceptance_item_registry does not cover blocking requirement id(s): "
            + ", ".join(missing_requirement_refs),
            missing_required_fields=("acceptance_item_registry.items[].source_requirement_ids",),
        )
    return _contract_pass(packet)


def _discovery_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision in _BLOCKING_OUTCOME_DECISIONS:
        return _contract_pass(packet)
    if not isinstance(payload.get("material_sources"), list) or not payload.get("material_sources"):
        return _contract_block(packet, "discovery result requires non-empty material_sources list", missing_required_fields=("material_sources",))
    if not str(payload.get("material_sufficiency") or "").strip():
        return _contract_block(packet, "discovery result requires material_sufficiency", missing_required_fields=("material_sufficiency",))
    if not isinstance(payload.get("candidate_skill_inventory"), list):
        return _contract_block(packet, "discovery result requires candidate_skill_inventory list", missing_required_fields=("candidate_skill_inventory",))
    return _contract_pass(packet)


def _skill_standard_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision in _BLOCKING_OUTCOME_DECISIONS:
        return _contract_pass(packet)
    rows = payload.get("obligations")
    if not isinstance(rows, list) or not rows:
        return _contract_block(
            packet,
            "skill_standard result requires top-level obligations list",
            missing_required_fields=("obligations",),
        )
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            return _contract_block(packet, f"skill_standard obligations[{index}] must be an object")
        missing: list[str] = []
        for field in _SKILL_STANDARD_REQUIRED_CHILD_FIELDS:
            value = row.get(field)
            if not str(value or "").strip():
                missing.append(f"obligations[{index}].{field}")
        if missing:
            return _contract_block(
                packet,
                "skill_standard result obligation row is missing required field(s): " + ", ".join(missing),
                missing_required_fields=tuple(missing),
            )
    return _contract_pass(packet)


def _pm_visible_summary_contract_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    if not _packet_requires_pm_visible_summary(packet):
        return _contract_pass(packet)
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return _contract_block(packet, "packet result requires a current strict JSON object")
    if not _pm_visible_summary_from_payload(payload):
        return _contract_block(
            packet,
            "formal role result requires role-authored pm_visible_summary as a non-empty list of non-empty strings",
            missing_required_fields=("pm_visible_summary",),
        )
    return _contract_pass(packet)


def _pm_repair_decision_branch_shape(decision: str) -> Mapping[str, Any]:
    return _packet_result_branch_valid_shapes(
        {
            "envelope": {
                "packet_kind": "pm_repair_decision",
                "route_scope": "pm_repair_decision",
            }
        }
    ).get(f"decision={decision}", {})


def _pm_flowguard_acceptance_branch_shape(decision: str) -> Mapping[str, Any]:
    return _packet_result_branch_valid_shapes(
        {
            "envelope": {
                "packet_kind": "pm_flowguard_acceptance",
                "route_scope": PM_FLOWGUARD_ACCEPTANCE_SCOPE,
            }
        }
    ).get(f"decision={decision}", {})


def _terminal_supplemental_repair_decision_branch_shape(
    ledger: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    decision: str,
    payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    blocker_id = str(envelope.get("subject_id") or "")
    blocker = ledger.get("active_blockers", {}).get(blocker_id) if isinstance(ledger.get("active_blockers"), Mapping) else None
    state = _terminal_supplemental_state_view(ledger)
    next_round = int(state.get("current_round", 0) or 0) + 1
    if isinstance(blocker, Mapping):
        supplemental_contract = _terminal_supplemental_repair_contract_current_shape(
            ledger,
            blocker,
            round_number=next_round,
        )
    else:
        supplemental_contract = _terminal_supplemental_repair_contract_minimal_shape(next_round)
    branch: dict[str, Any] = {
        "decision": decision,
        "reason": "Concrete PM terminal supplemental repair reason.",
        "supplemental_repair_contract": supplemental_contract,
    }
    if decision == "redesign_route":
        route_plan = payload.get("route_plan") if isinstance(payload, Mapping) else None
        if not isinstance(route_plan, Mapping):
            supplemental_branch = _packet_result_branch_valid_shapes(
                {
                    "envelope": {
                        "packet_kind": "pm_repair_decision",
                        "route_scope": "pm_repair_decision",
                    }
                }
            ).get("decision=redesign_route_terminal_supplemental", {})
            route_plan = supplemental_branch.get("route_plan") if isinstance(supplemental_branch, Mapping) else None
        if not isinstance(route_plan, Mapping):
            redesign_branch = _pm_repair_decision_branch_shape("redesign_route")
            route_plan = redesign_branch.get("route_plan") if isinstance(redesign_branch, Mapping) else None
        if isinstance(route_plan, Mapping):
            branch["route_plan"] = _project_supplemental_repair_ids_onto_route_plan(route_plan, supplemental_contract)
    return branch


def _route_plan_failure_field_path(error: str) -> str:
    lowered = error.lower()
    if "acceptance item" in lowered:
        return "route_plan.nodes[].acceptance_item_ids"
    if "schema_version" in lowered:
        return "route_plan.schema_version"
    if "node_kind" in lowered:
        return "route_plan.nodes[].node_kind"
    if "parent_node_id" in lowered:
        return "route_plan.nodes[].parent_node_id"
    if "child_node_ids" in lowered:
        return "route_plan.nodes[].child_node_ids"
    if "nodes" in lowered:
        if "node_id" in lowered:
            return "route_plan.nodes[].node_id"
        if "title" in lowered:
            return "route_plan.nodes[].title"
        return "route_plan.nodes"
    if "node_id" in lowered:
        return "route_plan.nodes[].node_id"
    if "title" in lowered:
        return "route_plan.nodes[].title"
    return "route_plan"


def _planning_result_failure_field_path(error: str) -> str:
    path = _route_plan_failure_field_path(error)
    return path.removeprefix("route_plan.")


def _pm_repair_decision_result_violation(
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    ledger: Mapping[str, Any] | None = None,
) -> PacketResultContractCheck:
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return _contract_block(
            packet,
            "pm_repair_decision.pm_repair_decision result requires a current strict JSON object",
            missing_required_fields=_packet_result_required_fields(packet),
        )
    forbidden = list(_top_level_forbidden_fields(payload, _packet_result_forbidden_fields(packet)))
    missing = list(_top_level_missing_fields(payload, _packet_result_required_fields(packet)))
    decision = _normalize_outcome_token(payload.get("decision"))
    failed_branch = ""
    failed_field_path = ""
    branch_shape: Mapping[str, Any] | None = None
    if decision == "waive_with_authority" and not str(payload.get("authority_ref") or ""):
        missing.append("authority_ref")
        failed_branch = "decision=waive_with_authority"
        failed_field_path = "authority_ref"
        branch_shape = _pm_repair_decision_branch_shape("waive_with_authority")
    if decision == "redesign_route" and not isinstance(payload.get("route_plan"), Mapping):
        missing.append("route_plan")
        failed_branch = "decision=redesign_route"
        failed_field_path = "route_plan"
        branch_shape = (
            _terminal_supplemental_repair_decision_branch_shape(
                ledger,
                packet,
                decision=decision,
                payload=payload,
            )
            if _terminal_supplemental_repair_required(ledger, packet, decision)
            else _pm_repair_decision_branch_shape("redesign_route")
        )
    if decision == "repair_parent_scope" and not isinstance(payload.get("repair_parent_scope_contract"), Mapping):
        missing.append("repair_parent_scope_contract")
        failed_branch = "decision=repair_parent_scope"
        failed_field_path = "repair_parent_scope_contract"
        branch_shape = {
            "decision": "repair_parent_scope",
            "reason": "Concrete PM parent-scope repair reason.",
            "repair_parent_scope_contract": _parent_repair_scope_contract_minimal_shape(),
        }
    if forbidden or missing:
        pieces: list[str] = []
        if missing:
            pieces.append("missing required field(s): " + ", ".join(dict.fromkeys(missing)))
        if forbidden:
            pieces.append("forbidden field(s): " + ", ".join(dict.fromkeys(forbidden)))
        required = list(_packet_result_required_fields(packet))
        for field in missing:
            if field not in required:
                required.append(field)
        return _contract_block(
            packet,
            "; ".join(pieces),
            missing_required_fields=tuple(missing),
            forbidden_fields_seen=tuple(forbidden),
            required_result_body_fields=tuple(required),
            failed_branch=failed_branch,
            failed_field_path=failed_field_path,
            branch_minimal_valid_shape=branch_shape,
        )
    allowed_value_violations = _allowed_value_option_violations_for_payload(packet, payload)
    if allowed_value_violations:
        return _contract_block(
            packet,
            "PM repair decision field value(s) must be selected from allowed_value_options: "
            + ", ".join(allowed_value_violations),
            missing_required_fields=allowed_value_violations,
        )
    if decision in _REMOVED_PM_REPAIR_DECISIONS:
        return _contract_block(packet, "PM repair decision uses a removed decision; request a current five-choice decision")
    if decision not in _PM_REPAIR_DECISIONS:
        return _contract_block(packet, "PM repair decision requires an explicit allowed decision")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    blocker_id = str(envelope.get("subject_id") or "")
    target_blocker_id = str(payload.get("target_blocker_id") or "").strip()
    if blocker_id and target_blocker_id != blocker_id:
        return _contract_block(
            packet,
            "PM repair decision target_blocker_id must match the current blocker",
            missing_required_fields=("target_blocker_id",),
        )
    next_action = _normalize_outcome_token(payload.get("next_action"))
    if next_action not in _PM_REPAIR_DECISIONS:
        return _contract_block(packet, "PM repair decision next_action must be one current PM repair action")
    if next_action != decision:
        return _contract_block(
            packet,
            "PM repair decision next_action must match decision",
            missing_required_fields=("next_action",),
        )
    if decision == "repair_parent_scope":
        try:
            _parse_parent_repair_scope_contract_payload(payload)
        except BlackBoxRuntimeError as exc:
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=("repair_parent_scope_contract",),
                required_result_body_fields=tuple(
                    dict.fromkeys((*_packet_result_required_fields(packet), "repair_parent_scope_contract"))
                ),
                failed_branch="decision=repair_parent_scope",
                failed_field_path="repair_parent_scope_contract",
                branch_minimal_valid_shape={
                    "decision": "repair_parent_scope",
                    "reason": "Concrete PM parent-scope repair reason.",
                    "repair_parent_scope_contract": _parent_repair_scope_contract_minimal_shape(),
                },
            )
    if decision == "redesign_route":
        try:
            route_plan = _parse_strict_route_plan(json.dumps(payload.get("route_plan"), sort_keys=True))
            node_specs = _normalize_strict_route_plan_nodes(route_plan)
            if ledger is not None:
                _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
        except BlackBoxRuntimeError as exc:
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=(_route_plan_failure_field_path(str(exc)),),
                required_result_body_fields=tuple(dict.fromkeys((*_packet_result_required_fields(packet), "route_plan"))),
                failed_branch="decision=redesign_route",
                failed_field_path=_route_plan_failure_field_path(str(exc)),
                branch_minimal_valid_shape=_pm_repair_decision_branch_shape("redesign_route"),
            )
    if _terminal_supplemental_repair_required(ledger, packet, decision):
        try:
            parsed_route_plan = None
            if decision == "redesign_route":
                parsed_route_plan = _parse_strict_route_plan(json.dumps(payload.get("route_plan"), sort_keys=True))
            assert ledger is not None
            _parse_terminal_supplemental_repair_contract_payload(
                ledger,
                packet,
                payload,
                decision=decision,
                route_plan=parsed_route_plan,
            )
        except BlackBoxRuntimeError as exc:
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=("supplemental_repair_contract",),
                required_result_body_fields=tuple(
                    dict.fromkeys((*_packet_result_required_fields(packet), "supplemental_repair_contract"))
                ),
                failed_branch=f"decision={decision}",
                failed_field_path="supplemental_repair_contract",
                branch_minimal_valid_shape=_terminal_supplemental_repair_decision_branch_shape(
                    ledger,
                    packet,
                    decision=decision,
                    payload=payload,
                ),
            )
    obligation_violation = _pm_repair_obligation_disposition_violation(packet, payload, decision)
    if obligation_violation is not None:
        return obligation_violation
    return _contract_pass(packet)


def _pm_disposition_result_violation(packet: Mapping[str, Any], result: Mapping[str, Any]) -> PacketResultContractCheck:
    payload, contract_error = _json_payload_contract_check(packet, result)
    if contract_error:
        return contract_error
    assert payload is not None
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision not in {"accept", "repair_current_scope", "redesign_route", "block", "stop"}:
        return _contract_block(packet, "PM disposition requires an explicit allowed decision")
    packet_body = _strict_json_object_from_body(str(packet.get("body", "")))
    node_acceptance_item_ids = [
        str(item)
        for item in packet_body.get("node_acceptance_item_ids") or []
        if str(item)
    ] if isinstance(packet_body.get("node_acceptance_item_ids"), list) else []
    disposition_rows = payload.get("acceptance_item_disposition")
    if not isinstance(disposition_rows, list):
        return _contract_block(
            packet,
            "PM disposition requires acceptance_item_disposition list",
            missing_required_fields=("acceptance_item_disposition",),
        )
    allowed_dispositions = {"accepted", "blocked", "waived", "superseded"}
    disposition_by_item: dict[str, str] = {}
    for index, row in enumerate(disposition_rows, start=1):
        if not isinstance(row, Mapping):
            return _contract_block(packet, f"acceptance_item_disposition[{index}] must be an object")
        item_id = str(row.get("acceptance_item_id") or "").strip()
        disposition = str(row.get("disposition") or "").strip()
        basis = str(row.get("basis") or "").strip()
        missing_row: list[str] = []
        if not item_id:
            missing_row.append(f"acceptance_item_disposition[{index}].acceptance_item_id")
        if disposition not in allowed_dispositions:
            missing_row.append(f"acceptance_item_disposition[{index}].disposition")
        if not basis:
            missing_row.append(f"acceptance_item_disposition[{index}].basis")
        if missing_row:
            return _contract_block(
                packet,
                "PM disposition row is missing required current field(s): " + ", ".join(missing_row),
                missing_required_fields=tuple(missing_row),
            )
        if item_id in disposition_by_item:
            return _contract_block(
                packet,
                f"PM disposition duplicates acceptance item: {item_id}",
                missing_required_fields=(f"acceptance_item_disposition[{index}].acceptance_item_id",),
            )
        disposition_by_item[item_id] = disposition
    dispositioned_item_ids = set(disposition_by_item)
    missing_item_ids = sorted(set(node_acceptance_item_ids) - dispositioned_item_ids)
    unknown_item_ids = sorted(dispositioned_item_ids - set(node_acceptance_item_ids))
    if missing_item_ids:
        return _contract_block(
            packet,
            "PM disposition missing acceptance item closure for: " + ", ".join(missing_item_ids),
            missing_required_fields=("acceptance_item_disposition",),
        )
    if unknown_item_ids:
        return _contract_block(
            packet,
            "PM disposition references acceptance item(s) outside this node: " + ", ".join(unknown_item_ids),
            missing_required_fields=("acceptance_item_disposition",),
        )
    if decision == "accept" and any(value == "blocked" for value in disposition_by_item.values()):
        return _contract_block(
            packet,
            "PM disposition decision=accept cannot carry blocked acceptance items",
            missing_required_fields=("acceptance_item_disposition",),
        )
    if decision == "accept" and not set(node_acceptance_item_ids).issubset(
        item_id
        for item_id, item_disposition in disposition_by_item.items()
        if item_disposition in {"accepted", "waived", "superseded"}
    ):
        return _contract_block(
            packet,
            "PM disposition decision=accept requires every node acceptance item to be accepted, waived, or superseded",
            missing_required_fields=("acceptance_item_disposition",),
        )
    return _contract_pass(packet)


def _pm_flowguard_acceptance_result_violation(
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
    ledger: Mapping[str, Any] | None = None,
) -> PacketResultContractCheck:
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return _contract_block(
            packet,
            "pm_flowguard_acceptance.pm_flowguard_acceptance result requires a current strict JSON object",
            missing_required_fields=_packet_result_required_fields(packet),
        )
    forbidden = list(_top_level_forbidden_fields(payload, _packet_result_forbidden_fields(packet)))
    missing = list(_top_level_missing_fields(payload, _packet_result_required_fields(packet)))
    decision = _normalize_outcome_token(payload.get("decision"))
    failed_branch = ""
    failed_field_path = ""
    branch_shape: Mapping[str, Any] | None = None
    if decision == "redesign_route" and not isinstance(payload.get("route_plan"), Mapping):
        missing.append("route_plan")
        failed_branch = "decision=redesign_route"
        failed_field_path = "route_plan"
        branch_shape = _pm_flowguard_acceptance_branch_shape("redesign_route")
    if forbidden or missing:
        pieces: list[str] = []
        if missing:
            pieces.append("missing required field(s): " + ", ".join(dict.fromkeys(missing)))
        if forbidden:
            pieces.append("forbidden field(s): " + ", ".join(dict.fromkeys(forbidden)))
        required = list(_packet_result_required_fields(packet))
        for field in missing:
            if field not in required:
                required.append(field)
        return _contract_block(
            packet,
            "; ".join(pieces),
            missing_required_fields=tuple(missing),
            forbidden_fields_seen=tuple(forbidden),
            required_result_body_fields=tuple(required),
            failed_branch=failed_branch,
            failed_field_path=failed_field_path,
            branch_minimal_valid_shape=branch_shape,
        )
    if decision in _REMOVED_PM_FLOWGUARD_ACCEPTANCE_DECISIONS:
        return _contract_block(packet, "PM FlowGuard acceptance does not support optional or uncertain FlowGuard decisions")
    if decision not in _PM_FLOWGUARD_ACCEPTANCE_DECISIONS:
        return _contract_block(packet, "PM FlowGuard acceptance requires an explicit allowed decision")
    allowed_value_violations = _allowed_value_option_violations_for_payload(packet, payload)
    if allowed_value_violations:
        return _contract_block(
            packet,
            "PM FlowGuard acceptance field value(s) must be selected from allowed_value_options: "
            + ", ".join(allowed_value_violations),
            missing_required_fields=allowed_value_violations,
        )
    if decision == "redesign_route":
        try:
            route_plan = _parse_strict_route_plan(json.dumps(payload.get("route_plan"), sort_keys=True))
            node_specs = _normalize_strict_route_plan_nodes(route_plan)
            if ledger is not None:
                _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
        except BlackBoxRuntimeError as exc:
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=(_route_plan_failure_field_path(str(exc)),),
                required_result_body_fields=tuple(dict.fromkeys((*_packet_result_required_fields(packet), "route_plan"))),
                failed_branch="decision=redesign_route",
                failed_field_path=_route_plan_failure_field_path(str(exc)),
                branch_minimal_valid_shape=_pm_flowguard_acceptance_branch_shape("redesign_route"),
            )
    return _contract_pass(packet)


def _node_acceptance_plan_result_violation(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> PacketResultContractCheck:
    payload = _strict_json_object_from_body(str(result.get("body", "")))
    if not payload:
        return _contract_block(packet, "node acceptance plan result requires a current strict JSON object")
    summary_violation = _pm_visible_summary_contract_violation(packet, result)
    if not summary_violation.ok:
        return summary_violation
    forbidden = _top_level_forbidden_fields(
        payload,
        (
            "optional_flowguard",
            "needs_flowguard",
            "maybe_flowguard",
            "flowguard_optional",
            "node_acceptance_plan",
            *_packet_result_forbidden_fields(packet),
        ),
    )
    if forbidden:
        return _contract_block(
            packet,
            "node acceptance plan result uses unsupported field(s): " + ", ".join(forbidden),
            forbidden_fields_seen=forbidden,
        )
    allowed_value_violations = _allowed_value_option_violations_for_payload(packet, payload)
    if allowed_value_violations:
        return _contract_block(
            packet,
            "node acceptance plan field value(s) must be selected from allowed_value_options: "
            + ", ".join(allowed_value_violations),
            missing_required_fields=allowed_value_violations,
        )
    decision = _normalize_outcome_token(payload.get("decision"))
    if decision in _BLOCKING_OUTCOME_DECISIONS:
        return _contract_pass(packet)
    if decision == "redesign_route":
        raw_route_plan = payload.get("route_plan")
        if not isinstance(raw_route_plan, Mapping):
            return _contract_block(
                packet,
                "node acceptance plan redesign_route requires a strict route_plan object",
                missing_required_fields=("route_plan",),
                required_result_body_fields=("decision", "route_plan"),
                failed_branch="decision=redesign_route",
                failed_field_path="route_plan",
                branch_minimal_valid_shape={"decision": "redesign_route", "route_plan": packet_result_contracts.strict_route_plan_minimal_shape()},
            )
        try:
            route_plan = _parse_strict_route_plan(json.dumps(raw_route_plan, sort_keys=True))
            node_specs = _normalize_strict_route_plan_nodes(route_plan)
            _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
            _validate_node_acceptance_redesign_route_nodes(
                node_specs,
                target_node_id=str(packet.get("envelope", {}).get("route_node_id") or ""),
            )
        except BlackBoxRuntimeError as exc:
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=(_route_plan_failure_field_path(str(exc)),),
                required_result_body_fields=("decision", "route_plan"),
                failed_branch="decision=redesign_route",
                failed_field_path=_route_plan_failure_field_path(str(exc)),
                branch_minimal_valid_shape={"decision": "redesign_route", "route_plan": packet_result_contracts.strict_route_plan_minimal_shape()},
            )
        _attach_staged_effect(
            result,  # type: ignore[arg-type]
            effect_kind="commit_route_redesign",
            source_packet_id=str(packet.get("packet_id") or ""),
            source_result_id=str(result.get("result_id") or ""),
            target_node_id=str(packet.get("envelope", {}).get("route_node_id") or ""),
            route_scope=str(packet.get("envelope", {}).get("route_scope") or ""),
        )
        return _contract_pass(packet)
    if decision not in _PASSING_OUTCOME_DECISIONS:
        return _contract_block(packet, "node acceptance plan decision must be pass, block, or redesign_route")
    node_id = str((packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}).get("route_node_id") or "")
    try:
        node = _require(ledger.setdefault("route_nodes", {}), node_id, "route node")
        parent_repair_violation = _parent_repair_node_current_child_violation(ledger, node_id, node)
        if parent_repair_violation:
            return _contract_block(
                packet,
                parent_repair_violation,
                missing_required_fields=("route_node.child_node_ids", "repair_parent_scope_contract.repair_child_specs"),
            )
        _node_context_package_from_pm_result(
            ledger,
            node,
            packet,
            str(result.get("result_id") or ""),
            context_package_id="staged",
            status="staged",
        )
    except BlackBoxRuntimeError as exc:
        missing: list[str] = []
        text = str(exc)
        if "node_context_package" in text:
            missing.append("node_context_package")
        for field in NODE_CONTEXT_PACKAGE_REQUIRED_LIST_FIELDS | {"purpose"}:
            if field in text:
                missing.append(f"node_context_package.{field}")
        if "acceptance_item_projection" in text:
            missing.append("node_context_package.acceptance_item_projection")
        return _contract_block(packet, text, missing_required_fields=tuple(missing))
    _attach_staged_effect(
        result,  # type: ignore[arg-type]
        effect_kind="commit_node_acceptance_plan",
        source_packet_id=str(packet.get("packet_id") or ""),
        source_result_id=str(result.get("result_id") or ""),
        target_node_id=node_id,
        route_scope=str((packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}).get("route_scope") or ""),
    )
    return _contract_pass(packet)


def _current_result_submission_contract_violation(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> PacketResultContractCheck:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    route_scope = str(envelope.get("route_scope") or "")
    body = str(result.get("body", ""))
    if packet_kind == "task" and route_scope == "high_standard_contract":
        return _high_standard_contract_result_violation(packet, result)
    if packet_kind == "pm_repair_decision":
        return _pm_repair_decision_result_violation(packet, result, ledger)
    if packet_kind == "pm_disposition":
        return _pm_disposition_result_violation(packet, result)
    if packet_kind == "pm_flowguard_acceptance":
        return _pm_flowguard_acceptance_result_violation(packet, result, ledger)
    if packet_kind == "review" and route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE:
        return _terminal_backward_replay_result_violation(packet, result)
    if packet_kind == "flowguard_check" and route_scope == NODE_PREWORK_FLOWGUARD_SCOPE:
        return _contract_block(packet, "node_prework_flowguard is no longer a supported current FlowPilot packet family")
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        return _node_acceptance_plan_result_violation(ledger, packet, result)
    if packet_kind == "task" and route_scope == "parent_backward_replay":
        return _parent_backward_replay_result_violation(packet, result)
    outcome_violation = _strict_packet_outcome_contract_violation(packet, result)
    if not outcome_violation.ok:
        return outcome_violation
    summary_violation = _pm_visible_summary_contract_violation(packet, result)
    if not summary_violation.ok:
        return summary_violation
    if packet_kind == "flowguard_check":
        flowguard_report_violation = _flowguard_current_report_violation(ledger, packet, result)
        if not flowguard_report_violation.ok:
            return flowguard_report_violation
    if packet_kind == "task" and route_scope == "discovery":
        return _discovery_result_violation(packet, result)
    if packet_kind == "task" and route_scope == "skill_standard":
        return _skill_standard_result_violation(packet, result)
    if packet_kind == "task" and route_scope == "planning":
        try:
            route_plan = _parse_strict_route_plan(body)
            node_specs = _normalize_strict_route_plan_nodes(route_plan)
            _validate_route_plan_acceptance_item_coverage(ledger, node_specs)
        except BlackBoxRuntimeError as exc:
            missing = (_planning_result_failure_field_path(str(exc)),)
            return _contract_block(
                packet,
                str(exc),
                missing_required_fields=missing,
                failed_field_path=missing[0],
            )
    if packet_kind == "flowguard_check":
        lowered_body = body.lower()
        if "api_fallback_manual_block_eval" in lowered_body or "fallback_manual_block_eval" in lowered_body:
            return _contract_block(
                packet,
                "FlowGuard fallback evidence is forbidden; submit real FlowGuard evidence or a toolchain blocker",
                forbidden_fields_seen=(
                    "api_fallback_manual_block_eval"
                    if "api_fallback_manual_block_eval" in lowered_body
                    else "fallback_manual_block_eval",
                ),
            )
    return _contract_pass(packet)


def _block_result_and_reissue_current_packet_family(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: Mapping[str, Any],
    *,
    contract_check: PacketResultContractCheck,
) -> str:
    blocker_name = "current_result_contract_violation"
    result["status"] = "mechanical_contract_blocked"
    result["accepted"] = False
    result["non_authoritative"] = True
    result.setdefault("mechanical_blockers", []).append(blocker_name)
    result["blocked_reason"] = contract_check.blocked_reason
    result["quarantine_reason"] = contract_check.blocked_reason
    result["mechanical_contract_failure"] = contract_check.to_json()
    result["missing_required_fields"] = list(contract_check.missing_required_fields)
    result["forbidden_fields_seen"] = list(contract_check.forbidden_fields_seen)
    result["contract_family_id"] = contract_check.contract_family_id
    old_packet_id = str(packet.get("packet_id") or "")
    packet["status"] = "superseded_after_repair"
    packet["superseded_by_result_id"] = str(result.get("result_id") or "")
    packet["superseded_reason"] = blocker_name
    packet["superseded_at"] = now_iso()
    close_lease(ledger, str(lease["lease_id"]), "current_result_contract_blocked")
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    packet_kind = str(envelope.get("packet_kind", "task"))
    route_scope = str(envelope.get("route_scope") or "")
    effective_contract = _packet_effective_result_contract(packet)
    reissue_payload: dict[str, Any] = {
        "schema_version": "black_box_flowpilot.current_contract_reissue_packet.v1",
        "blocked_packet_id": old_packet_id,
        "blocked_result_id": str(result.get("result_id") or ""),
        "blocked_reason": contract_check.blocked_reason,
        "contract_family_id": contract_check.contract_family_id,
        "mechanical_contract_failure": contract_check.to_json(),
        "missing_required_fields": list(contract_check.missing_required_fields),
        "forbidden_fields_seen": list(contract_check.forbidden_fields_seen),
        "failed_branch": contract_check.failed_branch,
        "failed_field_path": contract_check.failed_field_path,
        "original_packet_kind": packet_kind,
        "route_scope": route_scope,
        "route_node_id": str(envelope.get("route_node_id") or ""),
        "acceptance_criteria": list(envelope.get("acceptance_criteria") or []),
        "contract": _copy_jsonable(envelope.get("output_contract") or {}),
        "required_result_body_fields": list(contract_check.required_result_body_fields),
        "required_child_fields": list(effective_contract.get("required_child_fields") or []),
        "explicit_array_fields": list(effective_contract.get("explicit_array_fields") or []),
        "non_empty_array_fields": list(effective_contract.get("non_empty_array_fields") or []),
        "minimal_valid_shape": _copy_jsonable(contract_check.minimal_valid_shape or {}),
        "branch_minimal_valid_shape": _copy_jsonable(contract_check.branch_minimal_valid_shape or {}),
        "allowed_value_options": _copy_jsonable(effective_contract.get("allowed_value_options") or {}),
        "field_type_requirements": _copy_jsonable(effective_contract.get("field_type_requirements") or {}),
        "required_acceptance_item_ids": list(effective_contract.get("required_acceptance_item_ids") or []),
        "ownership_coverage_rule": _copy_jsonable(effective_contract.get("ownership_coverage_rule") or {}),
        "required_node_acceptance_item_ids": list(effective_contract.get("required_node_acceptance_item_ids") or []),
        "node_acceptance_projection_rule": _copy_jsonable(effective_contract.get("node_acceptance_projection_rule") or {}),
        "result_contract_profile_ids": list(effective_contract.get("result_contract_profile_ids") or []),
        "result_contract_profile_bindings": _copy_jsonable(
            effective_contract.get("result_contract_profile_bindings") or {}
        ),
        "instruction": (
            "Submit a fresh current-contract result for the same packet family. "
            "Use the current minimal shape, exact field names, finite options, and type requirements. "
            "When pm_visible_summary is required, the producing role must write it directly; runtime cannot synthesize it. "
            "Use missing_required_fields, forbidden_fields_seen, allowed_value_options, field_type_requirements, "
            "failed_branch, failed_field_path, and branch_minimal_valid_shape as the authoritative "
            "mechanical correction list."
        ),
    }
    if packet_kind == "review" and route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE:
        reissue_payload.update(
            {
                "schema_version": "black_box_flowpilot.terminal_backward_replay_reissue_packet.v1",
                "route_version": envelope.get("route_version"),
                "validation_evidence_id": str(ledger.get("latest_validation_evidence_id") or envelope.get("subject_id") or ""),
                "final_route_wide_gate_ledger_status": _copy_jsonable(ledger.get("final_route_wide_gate_ledger") or {}),
                "final_requirement_evidence_matrix_status": _copy_jsonable(ledger.get("final_requirement_evidence_matrix") or {}),
                "segment_targets": _terminal_backward_replay_segment_targets(ledger),
            }
        )
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        node_id = str(envelope.get("route_node_id") or "")
        node = ledger.setdefault("route_nodes", {}).get(node_id, {})
        if isinstance(node, Mapping):
            reissue_payload.update(
                {
                    "schema_version": "black_box_flowpilot.node_acceptance_plan_reissue_packet.v1",
                    "title": str(node.get("title") or ""),
                    "node_kind": str(node.get("node_kind") or "leaf"),
                    "parent_node_id": str(node.get("parent_node_id") or ""),
                    "child_node_ids": list(node.get("child_node_ids") or []),
                    "inherited_child_node_ids": list(node.get("inherited_child_node_ids") or []),
                    "inherited_accepted_result_ids": list(node.get("inherited_accepted_result_ids") or []),
                    "parent_repair_scope_contract_id": str(node.get("parent_repair_scope_contract_id") or ""),
                    "repair_parent_scope_contract": _copy_jsonable(node.get("repair_parent_scope_contract") or {})
                    if isinstance(node.get("repair_parent_scope_contract"), Mapping)
                    else {},
                    "high_standard_requirement_ids": [
                        str(row.get("requirement_id", ""))
                        for row in _blocking_high_standard_requirements(ledger)
                        if row.get("requirement_id")
                    ],
                    "acceptance_item_ids": _node_acceptance_item_ids(node),
                    "skill_standard_obligation_ids": [
                        str(row.get("obligation_id", ""))
                        for row in _required_skill_obligations(ledger)
                        if row.get("obligation_id")
                    ],
                    "required_node_context_package_fields": [
                        "purpose",
                        "acceptance_criteria",
                        "relevant_references",
                        "known_risks",
                        "acceptance_item_projection",
                    ],
                }
            )
    if packet_kind == "pm_disposition" and route_scope == "node_pm_disposition":
        node_id = str(envelope.get("route_node_id") or "")
        node = ledger.setdefault("route_nodes", {}).get(node_id, {})
        if isinstance(node, Mapping):
            node_requirement_ids = [str(item) for item in node.get("high_standard_requirement_ids") or [] if str(item)]
            node_acceptance_item_ids = _node_acceptance_item_ids(node)
            node_validation_ids = [str(item) for item in node.get("validation_evidence_ids") or [] if str(item)]
            pm_minimal_valid_shape = _copy_jsonable(
                packet_result_contracts.minimal_valid_shape_for_family("pm_disposition.node_pm_disposition")
            )
            if isinstance(pm_minimal_valid_shape, dict):
                pm_minimal_valid_shape["acceptance_item_disposition"] = [
                    {
                        "acceptance_item_id": item_id,
                        "disposition": "accepted",
                        "basis": "Current node result, FlowGuard evidence, Reviewer report, and validation evidence support this item.",
                    }
                    for item_id in node_acceptance_item_ids
                ]
            reissue_payload.update(
                {
                    "schema_version": "black_box_flowpilot.pm_disposition_reissue_packet.v1",
                    "node_high_standard_requirement_ids": node_requirement_ids,
                    "node_acceptance_item_ids": node_acceptance_item_ids,
                    "node_validation_evidence_ids": node_validation_ids,
                    "minimal_valid_shape": pm_minimal_valid_shape,
                }
            )
    if packet_kind == "pm_repair_decision":
        current_blocker_id = str(
            packet.get("active_blocker_id")
            or packet.get("repair_blocker_id")
            or envelope.get("repair_blocker_id")
            or envelope.get("subject_id")
            or ""
        )
        if current_blocker_id:
            reissue_payload["minimal_valid_shape"] = _project_current_pm_repair_blocker_id(
                reissue_payload.get("minimal_valid_shape") or {},
                current_blocker_id,
            )
            reissue_payload["branch_minimal_valid_shape"] = _project_current_pm_repair_blocker_id(
                reissue_payload.get("branch_minimal_valid_shape") or {},
                current_blocker_id,
            )
    preassigned_packet_id = ""
    reissue_authorized_result_reads: list[dict[str, Any]] = []
    if packet_kind == "flowguard_check":
        preassigned_packet_id = _next_id(ledger, "packet")
        reissue_authorized_result_reads = _flowguard_reissue_inherited_authorized_result_reads(ledger, packet)
        reissue_payload.update(
            {
                "schema_version": "black_box_flowpilot.flowguard_check_reissue_packet.v1",
                "fresh_packet_id": preassigned_packet_id,
                **_flowguard_reissue_inherited_body_payload(ledger, packet, preassigned_packet_id),
            }
        )
    fresh_packet_id = issue_task_packet(
        ledger,
        str(envelope.get("responsibility") or "pm"),
        f"Reissue current-contract result for {old_packet_id}",
        json.dumps(reissue_payload, indent=2, sort_keys=True),
        required_flowguard_target=str(envelope.get("required_flowguard_target") or ""),
        packet_kind=packet_kind,
        subject_id=str(envelope.get("subject_id") or "") if packet_kind != "task" else "",
        target_result_id=str(envelope.get("target_result_id") or ""),
        preassigned_packet_id=preassigned_packet_id,
        route_node_id=str(envelope.get("route_node_id") or ""),
        route_scope=route_scope,
        acceptance_criteria=list(envelope.get("acceptance_criteria") or []),
        node_context_package_id=str(envelope.get("node_context_package_id") or ""),
        authorized_result_reads=reissue_authorized_result_reads,
        repair_blocker_id=str(
            packet.get("active_blocker_id")
            or packet.get("repair_blocker_id")
            or envelope.get("repair_blocker_id")
            or ""
        ),
        result_contract_profile_ids=list(effective_contract.get("result_contract_profile_ids") or []),
        result_contract_profile_bindings=_copy_jsonable(
            effective_contract.get("result_contract_profile_bindings") or {}
        ),
    )
    if packet_kind == "pm_repair_decision":
        blocker_id = str(envelope.get("subject_id") or "")
        blocker = ledger.setdefault("active_blockers", {}).get(blocker_id)
        if isinstance(blocker, dict):
            blocker["pm_repair_packet_id"] = fresh_packet_id
    _event(
        ledger,
        "result_mechanical_contract_blocked",
        packet_id=old_packet_id,
        result_id=str(result.get("result_id") or ""),
        reason=contract_check.blocked_reason,
        contract_family_id=contract_check.contract_family_id,
    )
    _event(
        ledger,
        "current_contract_reissue_packet_issued",
        blocked_packet_id=old_packet_id,
        fresh_packet_id=fresh_packet_id,
        packet_kind=packet_kind,
        route_scope=str(envelope.get("route_scope") or ""),
        inherited_authorized_result_read_ids=[
            str(row.get("result_id") or "")
            for row in reissue_authorized_result_reads
            if str(row.get("result_id") or "")
        ],
    )
    return fresh_packet_id


def _apply_valid_packet_result(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
    lease: dict[str, Any],
) -> None:
    packet_kind = packet["envelope"].get("packet_kind", "task")
    route_scope = str(packet["envelope"].get("route_scope") or "")
    contract_check = _current_result_submission_contract_violation(ledger, packet, result)
    if not contract_check.ok:
        _block_result_and_reissue_current_packet_family(
            ledger,
            packet,
            result,
            lease,
            contract_check=contract_check,
        )
        return
    if packet_kind == "pm_repair_decision":
        repair_decision, repair_reason, authority_ref, route_plan, parent_repair_contract = (
            _parse_pm_repair_decision_body(str(result.get("body", "")))
        )
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
            parent_repair_contract=parent_repair_contract,
        )
        return
    if packet_kind == "pm_flowguard_acceptance":
        decision, reason, absorption, accepted_flowguard_result_id, route_plan = _parse_pm_flowguard_acceptance_body(
            str(result.get("body", ""))
        )
        gate_id = str(packet["envelope"].get("subject_id") or "")
        gate = _require(ledger.setdefault("pm_decision_gates", {}), gate_id, "PM decision gate")
        expected_flowguard_result_id = _flowguard_result_id_for_gate(ledger, gate)
        if accepted_flowguard_result_id != expected_flowguard_result_id:
            raise BlackBoxRuntimeError("PM FlowGuard acceptance result_id does not match the current gate FlowGuard report")
        outcome = {
            "decision": "pass" if decision in {"accept", "redesign_route"} else "block",
            "blocking": decision not in {"accept", "redesign_route"},
            "blocker_class": "pm_flowguard_acceptance",
            "recommended_resolution": decision,
            "evidence_refs": [accepted_flowguard_result_id],
            "reason": reason,
            "raw_token": decision,
            "schema_version": "",
        }
        outcome_id = _record_packet_outcome(ledger, packet, result, outcome)
        result["semantic_decision"] = outcome["decision"]
        result["packet_outcome_id"] = outcome_id
        result["flowguard_absorption"] = absorption
        _accept_packet_result(ledger, packet, result, lease, reason="pm_flowguard_acceptance_submitted")
        if decision == "accept":
            _mark_pm_decision_gate_pm_absorbed(ledger, gate, packet["packet_id"], result["result_id"])
            _ensure_review_packet_for_task_result(ledger, packet["packet_id"])
            return
        if decision == "redesign_route":
            gate["status"] = "replaced_by_pm_flowguard_acceptance"
            gate["replacement_result_id"] = result["result_id"]
            gate["updated_at"] = now_iso()
            _stage_pm_decision_gate(
                ledger,
                gate_kind="route_redesign",
                packet=packet,
                result=result,
                decision=decision,
                reason=reason,
                blocker_id=str(gate.get("blocker_id") or ""),
                node_id=str(gate.get("node_id") or packet["envelope"].get("route_node_id") or ""),
                route_plan=route_plan,
            )
            return
        gate["status"] = "pm_stopped" if decision == "stop_for_user" else "pm_blocked"
        gate["pm_flowguard_acceptance_packet_id"] = packet["packet_id"]
        gate["pm_flowguard_acceptance_result_id"] = result["result_id"]
        gate["updated_at"] = now_iso()
        blocker_id = str(gate.get("blocker_id") or "")
        blocker = ledger.get("active_blockers", {}).get(blocker_id)
        if isinstance(blocker, dict):
            blocker["status"] = "stopped" if decision == "stop_for_user" else "active"
            blocker["recommended_resolution"] = reason or blocker.get("recommended_resolution", "")
        return
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        payload = _strict_json_object_from_body(str(result.get("body", ""))) or {}
        decision = _normalize_outcome_token(payload.get("decision"))
        passing_decision = decision in (_PASSING_OUTCOME_DECISIONS | {"redesign_route"})
        outcome = {
            "decision": "pass" if passing_decision else "block",
            "blocking": not passing_decision,
            "blocker_class": "node_acceptance_plan",
            "recommended_resolution": str(payload.get("recommended_resolution") or payload.get("reason") or decision),
            "evidence_refs": [],
            "reason": str(payload.get("reason") or ""),
            "raw_token": decision,
            "schema_version": "",
        }
        outcome_id = _record_packet_outcome(ledger, packet, result, outcome)
        result["semantic_decision"] = outcome["decision"]
        result["packet_outcome_id"] = outcome_id
        if outcome["blocking"]:
            result["status"] = "semantic_blocked"
            result["accepted"] = False
            packet["status"] = "result_blocked"
            close_lease(ledger, lease["lease_id"], "semantic_result_blocked")
            _record_semantic_blocker(ledger, packet, result, outcome_id)
            return
        close_lease(ledger, lease["lease_id"], "result_submitted")
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=packet["packet_id"],
            gate_kind="task",
            recheck_role=packet["envelope"]["responsibility"],
            outcome_id=outcome_id,
        )
        if decision == "redesign_route":
            route_plan = payload.get("route_plan")
            if not isinstance(route_plan, Mapping):
                raise BlackBoxRuntimeError("node acceptance redesign_route requires route_plan after contract validation")
            _stage_pm_decision_gate(
                ledger,
                gate_kind="route_redesign",
                packet=packet,
                result=result,
                decision=decision,
                reason=str(payload.get("reason") or "pm_node_acceptance_route_redesign"),
                node_id=str(packet["envelope"].get("route_node_id") or ""),
                route_plan=route_plan,
            )
            return
        _ensure_review_packet_for_task_result(ledger, packet["packet_id"])
        return

    outcome = _parse_packet_outcome(packet, result)
    outcome_id = _record_packet_outcome(ledger, packet, result, outcome)
    result["semantic_decision"] = outcome["decision"]
    if packet_kind == "review" and route_scope == TERMINAL_BACKWARD_REPLAY_SCOPE:
        if outcome["blocking"]:
            result["status"] = "review_blocked"
            result["accepted"] = False
            packet["status"] = "review_blocked"
            close_lease(ledger, lease["lease_id"], "terminal_backward_replay_blocked")
            _record_semantic_blocker(ledger, packet, result, outcome_id)
            return
        _accept_packet_result(ledger, packet, result, lease, reason="terminal_backward_replay_submitted")
        _clear_semantic_blockers_for_pass(
            ledger,
            subject_packet_id=str(packet["packet_id"]),
            gate_kind="review",
            recheck_role="reviewer",
            outcome_id=outcome_id,
        )
        _record_terminal_backward_replay_closure(ledger, packet, result)
        evidence_id = str(ledger.get("latest_validation_evidence_id") or packet["envelope"].get("subject_id") or "")
        if evidence_id:
            attempt_final_closure(ledger, evidence_id)
        return
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
            _mark_pm_decision_gate_flowguard_blocked(
                ledger,
                str(packet["envelope"]["subject_id"]),
                str(result["result_id"]),
            )
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
        gate = _pending_pm_decision_gate_for_subject(ledger, str(packet["envelope"]["subject_id"]))
        if gate and gate.get("status") == "awaiting_pm_flowguard_acceptance":
            return
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
        node_id = str(packet["envelope"].get("route_node_id") or "")
        if not node_id:
            raise BlackBoxRuntimeError("PM disposition packet is missing route_node_id")
        decision, reason = _decision_from_pm_body(str(result.get("body", "")))
        _accept_packet_result(ledger, packet, result, lease, reason="pm_disposition_submitted")
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
        if _enter_nonworker_route_scope(ledger, node_id, reason="nonworker_route_scope_after_node_acceptance_plan"):
            return
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
            if _enter_nonworker_route_scope(ledger, active_node, reason="nonworker_route_scope_after_planning"):
                return
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
        acceptance_item_registry = _parse_acceptance_item_registry(body, requirements)
        contract_id = _next_id(ledger, "high_standard_contract")
        ledger["high_standard_contract"] = {
            "contract_id": contract_id,
            "status": "accepted",
            "source_packet_id": subject_packet.get("packet_id", ""),
            "source_result_id": result_id,
            "requirements": requirements,
            "acceptance_item_registry": acceptance_item_registry,
            "created_at": now_iso(),
        }
        ledger["acceptance_item_registry"] = acceptance_item_registry
        _event(
            ledger,
            "high_standard_contract_accepted",
            contract_id=contract_id,
            requirement_count=len(requirements),
            acceptance_item_count=len(acceptance_item_registry["items"]),
        )
        return
    if route_scope == "discovery":
        discovery = _parse_discovery_result(body)
        discovery_id = _next_id(ledger, "discovery")
        ledger["preplanning_discovery"] = {
            "discovery_id": discovery_id,
            "status": "accepted",
            "source_packet_id": subject_packet.get("packet_id", ""),
            "source_result_id": result_id,
            "material_sources": discovery["material_sources"],
            "material_sufficiency": discovery["material_sufficiency"],
            "candidate_skill_inventory": discovery["candidate_skill_inventory"],
            "material_current": discovery["material_current"],
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
        raise BlackBoxRuntimeError("high_standard_contract result requires top-level requirements list")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] must be an object")
        requirement_id = str(row.get("requirement_id") or "").strip()
        classification = str(row.get("classification") or "").strip()
        summary = str(row.get("summary") or "").strip()
        source_user_intent = str(row.get("source_user_intent") or "").strip()
        closure_rule = str(row.get("closure_rule") or "").strip()
        if not requirement_id:
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] requires requirement_id")
        if not classification:
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] requires classification")
        if not summary:
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] requires summary")
        if not source_user_intent:
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] requires source_user_intent")
        if not closure_rule:
            raise BlackBoxRuntimeError(f"high_standard_contract requirements[{index}] requires closure_rule")
        normalized.append(
            {
                "requirement_id": requirement_id,
                "classification": classification,
                "summary": summary,
                "source_user_intent": source_user_intent,
                "closure_rule": closure_rule,
                "forbidden_scope": str(row.get("forbidden_scope") or ""),
                "done_signal": str(row.get("done_signal") or ""),
                "quality_floor": str(row.get("quality_floor") or ""),
                "waiver_policy": str(row.get("waiver_policy") or ""),
            }
        )
    return normalized


def _parse_acceptance_item_registry(body: str, requirements: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _parse_json_object(body)
    registry = payload.get("acceptance_item_registry")
    if not isinstance(registry, Mapping):
        raise BlackBoxRuntimeError("high_standard_contract result requires acceptance_item_registry")
    rows = registry.get("items")
    if not isinstance(rows, list) or not rows:
        raise BlackBoxRuntimeError("acceptance_item_registry requires non-empty items list")
    requirement_ids = {str(row.get("requirement_id") or "") for row in requirements}
    blocking_requirement_ids = {
        str(row.get("requirement_id") or "")
        for row in requirements
        if str(row.get("classification") or "") in {"hard_current", "high_standard_current"}
    }
    normalized: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    source_types: set[str] = set()
    item_requirement_refs: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] must be an object")
        item_id = str(row.get("acceptance_item_id") or "").strip()
        source_type = str(row.get("source_type") or "").strip()
        summary = str(row.get("summary") or "").strip()
        quality_floor = str(row.get("quality_floor") or "").strip()
        future_evidence_rule = str(row.get("future_evidence_rule") or "").strip()
        status = str(row.get("status") or "").strip()
        if not item_id:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires acceptance_item_id")
        if item_id in seen_item_ids:
            raise BlackBoxRuntimeError(f"duplicate acceptance_item_id {item_id}")
        if not source_type:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires source_type")
        if not summary:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires summary")
        if not quality_floor:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires quality_floor")
        if not future_evidence_rule:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires future_evidence_rule")
        if not status:
            raise BlackBoxRuntimeError(f"acceptance_item_registry.items[{index}] requires status")
        source_requirement_ids = _optional_string_items(row.get("source_requirement_ids"))
        unknown_refs = sorted(set(source_requirement_ids) - requirement_ids)
        if unknown_refs:
            raise BlackBoxRuntimeError(
                f"acceptance item {item_id} references unknown requirement id(s): {', '.join(unknown_refs)}"
            )
        seen_item_ids.add(item_id)
        source_types.add(source_type)
        item_requirement_refs.update(source_requirement_ids)
        normalized.append(
            {
                "acceptance_item_id": item_id,
                "source_type": source_type,
                "source_requirement_ids": source_requirement_ids,
                "summary": summary,
                "quality_floor": quality_floor,
                "future_evidence_rule": future_evidence_rule,
                "status": status,
                "waiver_authority_ref": str(row.get("waiver_authority_ref") or ""),
                "superseded_by_acceptance_item_ids": _optional_string_items(row.get("superseded_by_acceptance_item_ids")),
            }
        )
    if not (source_types & {"user_explicit", "user_implicit"}):
        raise BlackBoxRuntimeError("acceptance_item_registry requires at least one user-explicit or user-implicit item")
    if "pm_high_standard" not in source_types:
        raise BlackBoxRuntimeError("acceptance_item_registry requires at least one PM high-standard item")
    missing_requirement_refs = sorted(blocking_requirement_ids - item_requirement_refs)
    if missing_requirement_refs:
        raise BlackBoxRuntimeError(
            "acceptance_item_registry does not cover blocking requirement id(s): "
            + ", ".join(missing_requirement_refs)
        )
    return {
        "schema_version": ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION,
        "status": "accepted",
        "items": normalized,
        "active_item_ids": [
            item["acceptance_item_id"]
            for item in normalized
            if item.get("status") in {"active", "planned", "assigned"}
        ],
        "created_at": now_iso(),
    }


def _parse_discovery_result(body: str) -> dict[str, Any]:
    payload = _parse_json_object(body)
    sources = payload.get("material_sources")
    if not isinstance(sources, list) or not sources:
        raise BlackBoxRuntimeError("discovery result requires non-empty material_sources list")
    source_texts = [str(item).strip() for item in sources if str(item).strip()]
    if not source_texts:
        raise BlackBoxRuntimeError("discovery result requires non-empty material_sources list")
    material_sufficiency = str(payload.get("material_sufficiency") or "").strip()
    if not material_sufficiency:
        raise BlackBoxRuntimeError("discovery result requires material_sufficiency")
    inventory = payload.get("candidate_skill_inventory")
    if not isinstance(inventory, list):
        raise BlackBoxRuntimeError("discovery result requires candidate_skill_inventory list")
    skill_texts = [str(item).strip() for item in inventory if str(item).strip()]
    return {
        "material_sources": source_texts,
        "material_sufficiency": material_sufficiency,
        "candidate_skill_inventory": skill_texts,
        "material_current": True,
    }


def _parse_skill_obligations(body: str) -> list[dict[str, Any]]:
    payload = _parse_json_object(body)
    if "selected_skills" in payload:
        raise BlackBoxRuntimeError("skill_standard result must use obligations; selected_skills is unsupported")
    rows = payload.get("obligations")
    if not isinstance(rows, list) or not rows:
        raise BlackBoxRuntimeError("skill_standard result requires top-level obligations list")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] must be an object")
        obligation_id = str(row.get("obligation_id") or "").strip()
        skill = str(row.get("skill") or "").strip()
        classification = str(row.get("classification") or "").strip()
        role_use = str(row.get("role_use") or "").strip()
        use_context = str(row.get("use_context") or "").strip()
        evidence_rule = str(row.get("evidence_rule") or "").strip()
        if not obligation_id:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires obligation_id")
        if not skill:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires skill")
        if not classification:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires classification")
        if not role_use:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires role_use")
        if not use_context:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires use_context")
        if not evidence_rule:
            raise BlackBoxRuntimeError(f"skill_standard obligations[{index}] requires evidence_rule")
        normalized.append(
            {
                "obligation_id": obligation_id,
                "skill": skill,
                "classification": classification,
                "role_use": role_use,
                "use_context": use_context,
                "evidence_rule": evidence_rule,
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
    acceptance_item_ids = _node_acceptance_item_ids(node)
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
        "acceptance_item_ids": acceptance_item_ids,
        "skill_standard_obligation_ids": obligation_ids,
        "created_at": now_iso(),
    }
    ledger.setdefault("node_context_packages", {})[context_package["context_package_id"]] = context_package
    node["node_acceptance_plan_id"] = plan_id
    node["node_context_package_id"] = context_package["context_package_id"]
    node["node_context_package_repair_generation"] = int(node.get("repair_generation", 0))
    node["high_standard_requirement_ids"] = requirement_ids
    node["acceptance_item_ids"] = acceptance_item_ids
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
    parent_repair_violation = _parent_repair_node_current_child_violation(
        ledger,
        node_id,
        node,
        require_accepted_child_results=True,
    )
    if parent_repair_violation:
        raise BlackBoxRuntimeError(parent_repair_violation)
    result_id = str(subject_packet.get("accepted_result_id") or "")
    child_node_ids = list(node.get("child_node_ids") or [])
    replay_id = _next_id(ledger, "parent_replay")
    ledger.setdefault("parent_backward_replays", {})[replay_id] = {
        "replay_id": replay_id,
        "status": "accepted",
        "node_id": node_id,
        "source_packet_id": subject_packet.get("packet_id", ""),
        "source_result_id": result_id,
        "child_node_ids": child_node_ids,
        "current_repair_child_result_ids": _accepted_result_ids_for_route_nodes(
            ledger,
            [str(item) for item in child_node_ids],
        ),
        "inherited_child_node_ids": list(node.get("inherited_child_node_ids") or []),
        "inherited_accepted_result_ids": list(node.get("inherited_accepted_result_ids") or []),
        "parent_repair_scope_contract_id": str(node.get("parent_repair_scope_contract_id") or ""),
        "created_at": now_iso(),
    }
    node["parent_backward_replay_id"] = replay_id
    node["status"] = "awaiting_pm_disposition"
    _event(ledger, "parent_backward_replay_accepted", node_id=node_id, replay_id=replay_id)
    return replay_id


def _record_terminal_backward_replay_closure(
    ledger: dict[str, Any],
    packet: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    payload = _parse_json_object(str(result.get("body", "")))
    replay_id = _next_id(ledger, "terminal_replay")
    route_segment_replay = payload.get("route_segment_replay") if isinstance(payload.get("route_segment_replay"), list) else []
    ledger.setdefault("terminal_backward_replays", {})[replay_id] = {
        "replay_id": replay_id,
        "status": "accepted",
        "source_packet_id": str(packet.get("packet_id") or ""),
        "source_result_id": str(result.get("result_id") or ""),
        "route_version": ledger.get("active_route_version"),
        "source_generation": ledger.get("source_generation"),
        "segment_count": len(route_segment_replay),
        "segment_ids": [str(row.get("segment_id") or "") for row in route_segment_replay if isinstance(row, Mapping)],
        "final_artifact_refs": _copy_jsonable(payload.get("final_artifact_refs") or []),
        "acceptance_item_closure": _copy_jsonable(payload.get("acceptance_item_closure") or []),
        "route_segment_replay": _copy_jsonable(route_segment_replay),
        "waiver_records": _copy_jsonable(payload.get("waiver_records") or []),
        "final_blockers": _copy_jsonable(payload.get("final_blockers") or []),
        "created_at": now_iso(),
    }
    ledger["terminal_backward_replay_id"] = replay_id
    ledger["closure_confirmed_by_backward_replay"] = True
    supplemental_contracts = ledger.get("supplemental_repair_contracts")
    if isinstance(supplemental_contracts, dict) and supplemental_contracts:
        _supplemental_rows, supplemental_unresolved = _supplemental_repair_closure_rows(ledger)
        if not supplemental_unresolved:
            state = _terminal_supplemental_state(ledger)
            state["status"] = "clean"
            state["active_contract_id"] = ""
            for contract in supplemental_contracts.values():
                if isinstance(contract, dict):
                    contract["status"] = "closed"
                    contract["closed_by_terminal_replay_id"] = replay_id
                    contract["closed_at"] = now_iso()
    _event(
        ledger,
        "terminal_backward_replay_accepted",
        replay_id=replay_id,
        source_packet_id=str(packet.get("packet_id") or ""),
        source_result_id=str(result.get("result_id") or ""),
    )
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
        if _packet_is_noncurrent_for_routing(ledger, packet):
            continue
        if reusable_statuses is not None and packet.get("status") not in reusable_statuses:
            continue
        return packet
    return None


_STAGE_FIELD_SIMULATION_TARGET_LABELS = {
    "requirements": "requirements list defines current hard/high-standard obligations",
    "acceptance_item_registry": "acceptance_item_registry.items records active acceptance items",
    "candidate_skill_inventory": "candidate_skill_inventory records candidate skills as planning input only",
    "obligations": "skill obligations define only selected skill evidence duties",
    "node_context_package": "node_context_package carries the node's five-field starting context",
    "current_evidence_refs": "current_evidence_refs point to the worker's current evidence",
    "modeled_boundary": "modeled_boundary states the exact current packet/result boundary",
    "blockers": "blockers use only the stage-approved blocker classes",
    "acceptance_item_disposition": "acceptance_item_disposition maps each node item to a current PM decision",
    "route_segment_replay": "route_segment_replay accounts the terminal route segments",
    "final_blockers": "final_blockers route any terminal replay gap to PM repair",
}


def _required_simulation_targets_for_stage_evidence(stage_evidence: Mapping[str, Any]) -> list[str]:
    targets: list[str] = []
    for field in stage_evidence.get("current_required_fields") or []:
        field_name = str(field)
        targets.append(_STAGE_FIELD_SIMULATION_TARGET_LABELS.get(field_name, f"current field due now: {field_name}"))
    return targets


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
    if not repair_blocker_id:
        repair_blocker_id = _packet_repair_blocker_id(ledger, subject_id)
    if repair_blocker_id and not recheck_reason:
        recheck_reason = "repair_blocker_semantic_recheck"
    existing = None
    if not force_new and not repair_blocker_id:
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
    staged_effect_reference = _staged_effect_public_reference(result)
    subject_family_id = _packet_result_family_id(packet)
    subject_stage_evidence = _packet_stage_evidence_row(packet)
    required_simulation_targets = _required_simulation_targets_for_stage_evidence(subject_stage_evidence)
    if str(packet["envelope"].get("route_scope") or "") == "planning":
        required_simulation_targets.extend(
            [
                "first executable leaf can progress without Worker-owned replanning",
                "route validation and failure/repair paths are represented at the right level",
            ]
        )
    if staged_effect_reference:
        required_simulation_targets.extend(
            [
                "current staged route or node effect can commit only after required PM/FlowGuard/Reviewer gates",
                "stale evidence invalidation and repair path for the staged effect",
            ]
        )
    required_subject_artifacts = (
        _parent_repair_subject_artifacts(ledger, node_id, subject_packet=packet, target_result=result) if node_id else []
    )
    result_contract_profile_ids: list[str] = []
    result_contract_profile_bindings: dict[str, Any] = {}
    body_payload = {
        "schema_version": "black_box_flowpilot.flowguard_packet.v1",
        "subject_packet_id": subject_id,
        "target_result_id": result["result_id"],
        "subject_result_family_id": subject_family_id,
        "subject_stage_evidence_matrix": subject_stage_evidence,
        "modeled_target": packet["envelope"]["required_flowguard_target"],
        **node_context,
        **staged_effect_reference,
        "modeled_subject_policy": {
            "boundary": (
                "Model the current subject packet result only. Use subject_stage_evidence_matrix to decide "
                "which current fields, blocker classes, and repair routes are in scope. When a staged route or "
                "node structure decision is present, simulate that proposed route/node topology, its work path, "
                "validation path, failure/repair path, stale-evidence effects, and closure path."
            ),
            "subject_lifecycle_stage": subject_stage_evidence["lifecycle_stage"],
            "required_evidence_owner": subject_stage_evidence["required_evidence_owner"],
            "required_simulation_targets": required_simulation_targets,
            "current_required_fields": list(subject_stage_evidence.get("current_required_fields") or []),
            "allowed_blocker_classes": list(subject_stage_evidence.get("allowed_blocker_classes") or []),
            "blocker_next_actions": _copy_jsonable(subject_stage_evidence.get("blocker_next_actions") or {}),
            "forbidden_authority": [
                "do not mutate routes",
                "do not approve gates",
                "do not release workers",
                "do not replace PM or Reviewer decisions",
                "do not invent a different modeling subject outside this packet",
            ],
        },
        "instruction": (
            "Produce current-run FlowGuard evidence for the subject packet result. Start from the authorized "
            "source result, node_context_package, or staged_effect when present. First read "
            "subject_stage_evidence_matrix. Require only the current-stage evidence listed there. If a small "
            "model/test gap is inside FlowGuard's own work, record it in FlowGuard evidence and report PM-visible "
            "suggestion items; do not turn it into a PM missing-field blocker. Simulate the current route, node, "
            "work, validation, failure, repair, and closure lines contained in that subject; do not choose an "
            "unrelated modeling target or mutate the route. Report pass or block with PM-visible repair guidance "
            "using only allowed blocker classes."
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
    if required_subject_artifacts:
        subject_artifact_ids = [
            str(artifact.get("artifact_id") or "")
            for artifact in required_subject_artifacts
            if isinstance(artifact, Mapping) and str(artifact.get("artifact_id") or "")
        ]
        result_contract_profile_ids.append("flowguard.subject_artifacts_consumed_required")
        result_contract_profile_bindings["flowguard.subject_artifacts_consumed_required"] = {
            "artifact_ids": subject_artifact_ids,
        }
        body_payload["required_subject_artifacts"] = required_subject_artifacts
        body_payload["subject_bound_report_contract"] = {
            "subject_artifacts_consumed_required": True,
            "result_field": "subject_artifacts_consumed",
            "rule": (
                "A parent repair FlowGuard pass is invalid unless subject_artifacts_consumed covers every "
                "required_subject_artifacts artifact_id. Format-only checks of passed/current-contract/result-shape "
                "are insufficient."
            ),
        }
    if str(packet["envelope"].get("route_scope") or "") == "planning":
        body_payload["route_process_focus"] = {
            "worker_decision_leakage_check_required": True,
            "route_decomposition_review_criteria": list(ROUTE_DECOMPOSITION_REVIEW_CRITERIA),
            "instruction": (
                "For this planning result, check whether the proposed route can traverse from first executable leaf "
                "to closure without letting a Worker invent subtasks, child order, dependency boundaries, or acceptance boundaries."
            ),
        }
    staged_effect = staged_effect_reference.get("staged_effect")
    if isinstance(staged_effect, Mapping) and staged_effect.get("effect_kind") == "commit_route_redesign":
        body_payload["structural_route_simulation_focus"] = {
            "pm_absorption_required_after_pass": True,
            "reviewer_required_after_pm_absorption": True,
            "route_mutation_authority": "PM writes the route plan; FlowGuard reports; Reviewer reviews; runtime commits only after system validation.",
            "must_check": [
                "candidate route has enough depth for worker-ready leaves",
                "candidate route is not over-fragmented into unnecessary handoffs",
                "node ordering and dependencies can progress without loops",
                "validation/check nodes and evidence obligations are represented at the right level",
                "blocker repair and PM rewrite paths cannot reuse stale route evidence",
            ],
        }
    if repair_blocker_id:
        blocker = ledger.get("active_blockers", {}).get(repair_blocker_id, {})
        blocker_reason = ""
        blocker_class = ""
        gate_kind = ""
        required_recheck_role = ""
        if isinstance(blocker, Mapping):
            blocker_reason = str(blocker.get("reason") or blocker.get("recommended_resolution") or "")
            blocker_class = str(blocker.get("blocker_class") or "")
            gate_kind = str(blocker.get("gate_kind") or "")
            required_recheck_role = str(blocker.get("required_recheck_role") or "")
        repair_evidence_obligations = (
            _repair_evidence_obligations_for_blocker(blocker) if isinstance(blocker, Mapping) else []
        )
        body_payload["recheck_for_blocker_id"] = repair_blocker_id
        body_payload["generator_inputs"] = {
            "blocker_id": repair_blocker_id,
            "subject_packet_id": subject_id,
            "target_result_id": str(result["result_id"]),
        }
        body_payload["subject_context"] = {
            "blocker_id": repair_blocker_id,
            "subject_packet_id": subject_id,
            "target_result_id": str(result["result_id"]),
        }
        body_payload["semantic_recheck_contract"] = {
            "schema_version": "black_box_flowpilot.semantic_flowguard_recheck_contract.v1",
            "blocker_id": repair_blocker_id,
            "subject_packet_id": subject_id,
            "target_result_id": str(result["result_id"]),
            "subject_bound_required": True,
            "must_consume_authorized_result_read_purposes": [
                "subject_result_for_flowguard_check",
            ],
            "required_focus": [
                "consume the authorized subject result body",
                "answer the active reviewer blocker instead of checking only result shape",
                "decide whether the subject result satisfies the blocker-bound semantic requirement",
            ],
            "forbidden_pass_boundaries": [
                "shape_only",
                "field_shape_only",
                "current_contract_only",
                "result_shape_only",
                "role_boundary_only",
            ],
            "blocker_context": {
                "blocker_class": blocker_class,
                "gate_kind": gate_kind,
                "required_recheck_role": required_recheck_role,
                "reason": blocker_reason,
            },
        }
        if repair_evidence_obligations:
            obligation_ids = [
                str(row.get("obligation_id") or "")
                for row in repair_evidence_obligations
                if str(row.get("obligation_id") or "")
            ]
            body_payload["repair_evidence_obligations"] = _copy_jsonable(repair_evidence_obligations)
            semantic_contract = body_payload["semantic_recheck_contract"]
            semantic_contract["repair_evidence_obligation_ids"] = obligation_ids
            semantic_contract["must_consume_repair_obligation_ids"] = obligation_ids
            semantic_contract["required_focus"].append(
                "account for every repair_evidence_obligations row produced by the active blocker"
            )
        else:
            obligation_ids = []
        result_contract_profile_ids.append("flowguard.semantic_recheck_required")
        result_contract_profile_bindings["flowguard.semantic_recheck_required"] = {
            "blocker_id": repair_blocker_id,
            "coverage_boundary": "subject_bound_semantic",
            "authorized_result_read_ids": [str(result["result_id"])],
            "repair_obligation_ids": obligation_ids,
        }
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
        repair_blocker_id=repair_blocker_id,
        authorized_result_reads=[
            _authorized_read_for_result(
                ledger,
                str(result["result_id"]),
                allowed_roles=["flowguard_operator"],
                purpose="subject_result_for_flowguard_check",
                required_before_submit=True,
            )
        ],
        result_contract_profile_ids=result_contract_profile_ids,
        result_contract_profile_bindings=result_contract_profile_bindings,
    )
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
    repair_blocker_id = str(packet.get("repair_blocker_id") or envelope.get("repair_blocker_id") or "")
    if repair_blocker_id:
        result["blocker_id"] = repair_blocker_id
    subject_id = str(packet["envelope"]["subject_id"])
    subject_packet = _require(ledger["packets"], subject_id, "packet")
    modeled_target = subject_packet["envelope"]["required_flowguard_target"]
    order_id = create_flowguard_work_order(ledger, modeled_target, "done_claim", subject_id)
    order = ledger["flowguard_work_orders"][order_id]
    order["flowguard_operator_lease_id"] = result["producer_lease_id"]
    order["packet_id"] = packet["packet_id"]
    order["producer_result_id"] = result["result_id"]
    order["proof_result_id"] = result["result_id"]
    order["proof_artifact_kind"] = "flowguard_packet_result"
    order["reviewer_authorized_read_required"] = True
    order["blocker_id"] = repair_blocker_id
    node_id = str(subject_packet["envelope"].get("route_node_id") or "")
    semantic = outcome if isinstance(outcome, Mapping) else {}
    artifact_decision = _flowguard_packet_artifact_hard_decision(ledger, packet)
    artifact_hard_decision = _normalize_outcome_token(artifact_decision.get("decision"))
    hard_decision = artifact_hard_decision or ("blocked" if semantic.get("blocking") else "pass")
    order["hard_evidence_decision"] = hard_decision
    order["hard_evidence_source_path"] = str(artifact_decision.get("path") or "")
    hard_evidence_blocks = (
        artifact_decision.get("missing")
        or artifact_decision.get("invalid")
        or hard_decision in _FLOWGUARD_HARD_EVIDENCE_BLOCK_DECISIONS
        or (hard_decision and hard_decision not in _FLOWGUARD_HARD_EVIDENCE_PASS_DECISIONS)
    )
    decision = "fail" if semantic.get("blocking") or hard_evidence_blocks else "pass"
    complete_flowguard_work_order(ledger, order_id, decision=decision, evidence_id=result["result_id"])
    order["proof_artifact"] = result["result_id"]
    order["confidence_boundary"] = "current_run_packet"
    if node_id and node_id in ledger.get("route_nodes", {}):
        ledger["route_nodes"][node_id].setdefault("flowguard_order_ids", []).append(order_id)
    if decision == "pass":
        _mark_pm_decision_gate_flowguard(ledger, subject_id, order_id)
    return order_id


def _flowguard_evidence_reads_for_review(
    ledger: Mapping[str, Any],
    subject_id: str,
    *,
    repair_blocker_id: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subject_packet = ledger.get("packets", {}).get(subject_id)
    if not isinstance(subject_packet, Mapping):
        return [], []
    subject_envelope = (
        subject_packet.get("envelope", {})
        if isinstance(subject_packet.get("envelope"), Mapping)
        else {}
    )
    modeled_target = str(subject_envelope.get("required_flowguard_target") or "")
    reads: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for order in ledger.get("flowguard_work_orders", {}).values():
        if not isinstance(order, Mapping):
            continue
        if str(order.get("subject_id") or "") != subject_id:
            continue
        if modeled_target and str(order.get("modeled_target") or "") != modeled_target:
            continue
        if order.get("status") != "complete" or order.get("decision") != "pass":
            continue
        if order.get("progress_only") or order.get("skipped_checks") or order.get("proof_stale"):
            continue
        if order.get("source_generation") != ledger.get("source_generation"):
            continue
        hard_evidence_decision = _normalize_outcome_token(order.get("hard_evidence_decision"))
        if hard_evidence_decision and hard_evidence_decision not in _FLOWGUARD_HARD_EVIDENCE_PASS_DECISIONS:
            continue
        if repair_blocker_id and str(order.get("blocker_id") or "") != repair_blocker_id:
            continue
        result_id = str(order.get("proof_result_id") or order.get("producer_result_id") or "")
        if not result_id or not isinstance(ledger.get("results", {}).get(result_id), Mapping):
            continue
        reads.append(
            _authorized_read_for_result(
                ledger,
                result_id,
                allowed_roles=["reviewer"],
                purpose="matching_flowguard_result_for_review",
                required_before_submit=True,
            )
        )
        manifest.append(
            {
                "order_id": str(order.get("order_id") or ""),
                "modeled_target": str(order.get("modeled_target") or ""),
                "flowguard_packet_id": str(order.get("packet_id") or ""),
                "flowguard_result_id": result_id,
                "blocker_id": str(order.get("blocker_id") or ""),
                "proof_artifact_kind": str(order.get("proof_artifact_kind") or "flowguard_packet_result"),
                "hard_evidence_decision": hard_evidence_decision or "pass",
                "hard_evidence_source_path": str(order.get("hard_evidence_source_path") or ""),
                "required_before_review_submit": True,
            }
        )
    return reads, manifest


def _record_missing_matching_flowguard_review_handoff_blocker(
    ledger: dict[str, Any],
    subject_packet_id: str,
    *,
    target_result_id: str,
    repair_blocker_id: str = "",
) -> str:
    root_cause_key = _flowguard_missing_evidence_root_cause_key(
        subject_packet_id=subject_packet_id,
        target_result_id=target_result_id,
        repair_blocker_id=repair_blocker_id,
    )
    for blocker_id, blocker in ledger.setdefault("active_blockers", {}).items():
        if not isinstance(blocker, Mapping):
            continue
        if blocker.get("root_cause_loop_key") != root_cause_key:
            continue
        if blocker.get("status") in _CLEARABLE_SEMANTIC_BLOCKER_STATUSES:
            return str(blocker_id)
    subject_packet = _require(ledger["packets"], subject_packet_id, "packet")
    subject_envelope = subject_packet.get("envelope", {}) if isinstance(subject_packet.get("envelope"), Mapping) else {}
    blocker_id = _next_id(ledger, "blocker")
    route_node_id = str(subject_envelope.get("route_node_id") or "")
    repair_generation = 0
    if route_node_id and route_node_id in ledger.get("route_nodes", {}):
        repair_generation = int(ledger["route_nodes"][route_node_id].get("repair_generation", 0))
    row = {
        "blocker_id": blocker_id,
        "status": "active",
        "outcome_id": "",
        "packet_id": subject_packet_id,
        "packet_kind": "review_handoff",
        "subject_packet_id": subject_packet_id,
        "repair_target_packet_id": subject_packet_id,
        "target_result_id": target_result_id,
        "result_id": target_result_id,
        "owner_role": "runtime",
        "required_recheck_role": "flowguard_operator",
        "gate_kind": "flowguard_review_handoff",
        "blocker_class": "missing_matching_flowguard_report",
        "recommended_resolution": (
            "missing_matching_flowguard_report: run or repair the current FlowGuard check for "
            f"subject_packet_id={subject_packet_id} and target_result_id={target_result_id}; "
            "the reviewer packet cannot be issued until flowguard_evidence_manifest.entries includes "
            "a matching current FlowGuard result and authorized_result_reads includes "
            "matching_flowguard_result_for_review."
        ),
        "missing_required_fields": [
            "flowguard_evidence_manifest.entries[].flowguard_result_id",
            "authorized_result_reads[matching_flowguard_result_for_review]",
        ],
        "route_version": subject_envelope.get("route_version"),
        "route_node_id": route_node_id,
        "route_scope": str(subject_envelope.get("route_scope") or ""),
        "repair_generation": repair_generation,
        "stale_evidence_ids": [target_result_id] if target_result_id else [],
        "root_cause_loop_key": root_cause_key,
        "created_at": now_iso(),
        "pm_repair_packet_id": "",
        "pm_repair_decision_id": "",
        "cleared_by_outcome_id": "",
    }
    ledger.setdefault("active_blockers", {})[blocker_id] = row
    if isinstance(subject_packet, dict):
        subject_packet["active_blocker_id"] = blocker_id
        subject_packet["flowguard_review_handoff_blocker_id"] = blocker_id
    _event(
        ledger,
        "flowguard_review_handoff_blocker_recorded",
        blocker_id=blocker_id,
        subject_packet_id=subject_packet_id,
        target_result_id=target_result_id,
        root_cause_loop_key=root_cause_key,
    )
    _ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    return blocker_id


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
    target_result = ledger.get("results", {}).get(target_result_id, {})
    subject_stage_evidence = _packet_stage_evidence_row(subject_packet)
    flowguard_required = _flowguard_required_for_subject_result(subject_packet, target_result)
    flowguard_reads, flowguard_manifest = _flowguard_evidence_reads_for_review(
        ledger,
        subject_id,
        repair_blocker_id=repair_blocker_id,
    )
    if flowguard_required and not flowguard_manifest:
        _record_missing_matching_flowguard_review_handoff_blocker(
            ledger,
            subject_id,
            target_result_id=target_result_id,
            repair_blocker_id=repair_blocker_id,
        )
        return ""
    staged_effect_kind = _staged_effect_kind_from_result(target_result)
    is_node_plan_review = (
        str(subject_packet["envelope"].get("packet_kind") or "") == "task"
        and str(subject_packet["envelope"].get("route_scope") or "") == "node_acceptance_plan"
        and staged_effect_kind == "commit_node_acceptance_plan"
    )
    if is_node_plan_review:
        review_instruction = (
            "Perform a plan-stage review of the PM node acceptance plan before Worker dispatch. "
            "Use subject_stage_evidence_matrix to identify current plan fields and the allowed blocker route. "
            "Review decomposition depth, node context, acceptance criteria, projected evidence, route fit, "
            "and whether the staged commit_node_acceptance_plan effect is safe to commit. Do not block solely "
            "because Worker artifacts, per-output artifact payloads, post-result FlowGuard evidence, or fresh "
            "Worker-result checker output do not exist yet; those are result-stage requirements unless PM "
            "claims them as already produced. Start from node_context_package as the minimum checklist and "
            "actively inspect current route, node, and plan evidence inside the authorized scope."
        )
    else:
        review_instruction = (
            "Review the subject result independently. Start by reading subject_stage_evidence_matrix: require "
            "the current-stage fields it lists and reject fields outside the current contract. Do not block for "
            "future-stage evidence unless the subject claims that evidence already exists. When matching "
            "FlowGuard evidence is required, inspect it before pass. Start from node_context_package as the "
            "minimum checklist, then actively inspect relevant files, UI/screenshots, logs, commands, model "
            "artifacts, and evidence paths inside the authorized scope. Do not treat the package as the review "
            "boundary."
        )
    body_payload = {
        "schema_version": "black_box_flowpilot.review_packet.v1",
        "subject_packet_id": subject_id,
        "target_result_id": target_result_id,
        "subject_result_family_id": _packet_result_family_id(subject_packet),
        "subject_stage_evidence_matrix": subject_stage_evidence,
        **node_context,
        **_staged_effect_public_reference(target_result),
        "flowguard_evidence_manifest": {
            "subject_packet_id": subject_id,
            "matching_flowguard_result_reads_required": flowguard_required,
            "entries": flowguard_manifest,
        },
        "instruction": review_instruction,
    }
    if str(subject_packet["envelope"].get("route_scope") or "") == "planning":
        body_payload["route_decomposition_quality_gate"] = {
            "reviewer_is_semantic_gate": True,
            "route_decomposition_review_criteria": list(ROUTE_DECOMPOSITION_REVIEW_CRITERIA),
            "block_if": [
                "a proposed executable leaf is a broad stage rather than one bounded worker outcome",
                "sibling leaves overlap or leave unclear ownership",
                "the Worker would need to create subtasks, order child work, or define acceptance boundaries",
                "a parent/module route scope can reach Worker dispatch directly",
            ],
            "recommended_resolution_rule": (
                "If blocking, return one concrete PM-actionable split recommendation. Reviewer may suggest child nodes, "
                "but PM owns the revised route plan."
            ),
        }
    if repair_blocker_id:
        body_payload["recheck_for_blocker_id"] = repair_blocker_id
        body_payload["subject_context"] = {
            "blocker_id": repair_blocker_id,
            "subject_packet_id": subject_id,
            "target_result_id": target_result_id,
        }
    if recheck_reason:
        body_payload["recheck_reason"] = recheck_reason
    extra_authorized_reads: list[dict[str, Any]] = []
    if str(subject_packet["envelope"].get("packet_kind") or "") == "pm_flowguard_acceptance":
        gate_id = str(subject_packet["envelope"].get("subject_id") or "")
        gate = ledger.get("pm_decision_gates", {}).get(gate_id)
        if isinstance(gate, Mapping):
            source_result_id = str(gate.get("source_result_id") or "")
            flowguard_result_id = _flowguard_result_id_for_gate(ledger, gate)
            if source_result_id:
                extra_authorized_reads.append(
                    _authorized_read_for_result(
                        ledger,
                        source_result_id,
                        allowed_roles=["reviewer"],
                        purpose="structural_pm_decision_under_review",
                        required_before_submit=True,
                    )
                )
            if flowguard_result_id:
                extra_authorized_reads.append(
                    _authorized_read_for_result(
                        ledger,
                        flowguard_result_id,
                        allowed_roles=["reviewer"],
                        purpose="flowguard_report_absorbed_by_pm",
                        required_before_submit=True,
                    )
                )
            body_payload["structural_pm_flowguard_acceptance_gate"] = {
                "gate_id": gate_id,
                "source_packet_id": str(gate.get("source_packet_id") or ""),
                "source_result_id": source_result_id,
                "flowguard_result_id": flowguard_result_id,
                "pm_flowguard_acceptance_required": True,
                "reviewer_reviews_pm_absorbed_plan_not_raw_flowguard_report": True,
            }
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
        repair_blocker_id=repair_blocker_id,
        authorized_result_reads=[
            _authorized_read_for_result(
                ledger,
                target_result_id,
                allowed_roles=["reviewer"],
                purpose="subject_result_for_review",
                required_before_submit=True,
            )
        ] + flowguard_reads + extra_authorized_reads
        if target_result_id
        else None,
    )
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
    elif packet.get("status") in _NONCURRENT_PACKET_STATUSES:
        blockers.append("noncurrent_packet")
    if packet["envelope"]["route_version"] != ledger.get("active_route_version"):
        blockers.append("stale_route_version")
    if output_type != packet["envelope"]["required_output_type"] or not valid_shape:
        blockers.append("wrong_result_shape")
    if evidence_generation < int(ledger.get("source_generation", 1)):
        blockers.append("stale_evidence")
    if packet_body_hash is not None and packet_body_hash != packet["envelope"]["body_hash"]:
        blockers.append("body_hash_mismatch")
    blockers.extend(_required_authorized_result_read_blockers(ledger, lease=lease, packet=packet))
    blockers.extend(_formal_repair_identity_blockers(packet))
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


def _staged_effect_kind_from_result(result: Mapping[str, Any]) -> str:
    effect = result.get("staged_effect")
    if not isinstance(effect, Mapping):
        return ""
    return str(effect.get("effect_kind") or "")


def _flowguard_required_for_subject_result(packet: Mapping[str, Any], result: Mapping[str, Any] | Any) -> bool:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), Mapping) else {}
    if envelope.get("packet_kind") == "pm_flowguard_acceptance":
        return False
    if (
        envelope.get("packet_kind", "task") == "task"
        and envelope.get("route_scope") == "node_acceptance_plan"
        and isinstance(result, Mapping)
        and _staged_effect_kind_from_result(result) == "commit_node_acceptance_plan"
    ):
        return False
    return bool(str(envelope.get("required_flowguard_target") or ""))


def _current_gate_flowguard_order_ids_for_subject(ledger: Mapping[str, Any], subject_packet_id: str) -> list[str]:
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if not gate:
        return []
    gate_order_id = str(gate.get("flowguard_order_id") or "")
    gate_order = ledger.get("flowguard_work_orders", {}).get(gate_order_id)
    if not isinstance(gate_order, Mapping):
        return []
    if (
        gate_order.get("status") == "complete"
        and gate_order.get("decision") == "pass"
        and not gate_order.get("progress_only")
        and not gate_order.get("skipped_checks")
        and not gate_order.get("proof_stale")
        and gate_order.get("source_generation") == ledger.get("source_generation")
    ):
        return [gate_order_id]
    return []


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
    flowguard_required = _flowguard_required_for_subject_result(packet, result)
    has_direct_flowguard = _has_matching_flowguard_report(
        ledger,
        packet["packet_id"],
        packet["envelope"]["required_flowguard_target"],
    )
    has_gate_flowguard = bool(_current_gate_flowguard_order_ids_for_subject(ledger, str(packet["packet_id"])))
    if flowguard_required and not has_direct_flowguard and not has_gate_flowguard:
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
    blockers: list[str] = []
    result_ids = [str(item) for item in subject_packet.get("result_ids") or [] if item]
    subject_result_id = str(
        subject_packet.get("accepted_result_id")
        or subject_packet["envelope"].get("target_result_id")
        or (result_ids[-1] if result_ids else "")
        or ""
    )
    subject_result = ledger.get("results", {}).get(subject_result_id, {})
    flowguard_required = _flowguard_required_for_subject_result(subject_packet, subject_result)
    flowguard_order_ids = _matching_flowguard_order_ids(ledger, subject_packet_id, required_target) if flowguard_required and required_target else []
    gate = _pending_pm_decision_gate_for_subject(ledger, subject_packet_id)
    if flowguard_required and not flowguard_order_ids and gate:
        flowguard_order_ids = _current_gate_flowguard_order_ids_for_subject(ledger, subject_packet_id)
    if not isinstance(subject_result, Mapping) or subject_result.get("review_id") != review_id:
        blockers.append("missing_accepted_review")
    if flowguard_required and required_target and not flowguard_order_ids:
        blockers.append("missing_matching_flowguard_report")
    if gate:
        if not gate.get("review_id"):
            blockers.append("missing_pm_decision_gate_review")
    evidence_id = f"validation-{source_result_id}"
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
    missing_flowguard_report = "missing_matching_flowguard_report" in blockers
    root_cause_loop_key = (
        _flowguard_missing_evidence_root_cause_key(
            subject_packet_id=subject_packet_id,
            target_result_id=str(subject_packet.get("accepted_result_id") or subject_envelope.get("target_result_id") or ""),
            repair_blocker_id=str(subject_packet.get("repair_blocker_id") or subject_envelope.get("repair_blocker_id") or ""),
        )
        if missing_flowguard_report
        else ""
    )
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
        "recommended_resolution": (
            "missing_matching_flowguard_report: system validation cannot pass until a matching current FlowGuard "
            "report is present in the review evidence manifest and authorized reads"
            if missing_flowguard_report
            else "; ".join(blockers)
        ),
        "missing_required_fields": [
            "flowguard_evidence_manifest.entries[].flowguard_result_id",
            "authorized_result_reads[matching_flowguard_result_for_review]",
        ]
        if missing_flowguard_report
        else [],
        "root_cause_loop_key": root_cause_loop_key,
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
    elif action_type == "issue_node_task_packet":
        result["packet_id"] = ensure_next_node_task_packet(ledger)
    elif action_type == "issue_parent_backward_replay_packet":
        result["packet_id"] = ensure_parent_backward_replay_packet(ledger, action.subject_id)
    elif action_type == "issue_terminal_backward_replay_packet":
        result["packet_id"] = ensure_terminal_backward_replay_packet(ledger, action.subject_id)
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
    elif action_type == "issue_pm_flowguard_acceptance_packet":
        gate = _require(ledger.setdefault("pm_decision_gates", {}), action.subject_id, "PM decision gate")
        result["packet_id"] = _ensure_pm_flowguard_acceptance_packet_for_gate(ledger, gate)
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


def _repair_loop_break_glass_review_for_action(
    ledger: Mapping[str, Any],
    action: RuntimeAction,
) -> dict[str, Any]:
    if action.action_type != "control_plane_blocker":
        return {}
    blocker = ledger.get("active_blockers", {}).get(action.subject_id)
    if not isinstance(blocker, Mapping):
        return {}
    review = _repair_loop_break_glass_review(ledger, blocker)
    return review if review.get("threshold_exceeded") else {}


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
    for packet in _accepted_result_packets_for_active_route(ledger):
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
    last_progress_elapsed = _elapsed_seconds_since(lease_map.get("last_progress_at"))
    liveness_evidence = _latest_liveness_evidence(lease_map)
    evidence_elapsed = liveness_evidence.get("elapsed_seconds")
    ack_reminder_seconds = _guard_config_int(ledger, "ack_reminder_seconds", _WAIT_ACK_REMINDER_SECONDS)
    ack_replace_seconds = _guard_config_int(ledger, "ack_replace_seconds", _WAIT_ACK_REPLACE_SECONDS)
    progress_reminder_seconds = _guard_config_int(
        ledger,
        "progress_reminder_seconds",
        _WAIT_PROGRESS_REMINDER_SECONDS,
    )
    progress_replace_seconds = _guard_config_int(
        ledger,
        "progress_replace_seconds",
        _WAIT_PROGRESS_REPLACE_SECONDS,
    )
    base = {
        "state": "waiting",
        "replacement_eligible": False,
        "lease_id": lease_id,
        "lease_status": str(lease_map.get("status") or ""),
        "progress_count": progress_count,
        "last_progress_status": last_progress_status,
        "last_progress_elapsed_seconds": last_progress_elapsed,
        "last_liveness_evidence_kind": str(liveness_evidence.get("kind") or "none"),
        "last_liveness_evidence_at": str(liveness_evidence.get("at") or ""),
        "liveness_evidence_elapsed_seconds": evidence_elapsed,
        "ack_reminder_seconds": ack_reminder_seconds,
        "ack_replace_seconds": ack_replace_seconds,
        "progress_reminder_seconds": progress_reminder_seconds,
        "progress_replace_seconds": progress_replace_seconds,
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
    if action.action_type == "wait_for_ack":
        elapsed = _elapsed_seconds_since(lease_map.get("created_at"))
        if elapsed is not None and elapsed >= ack_replace_seconds:
            return {
                **base,
                "state": "ack_replacement_due",
                "decision_override": "reissue_or_replace_lease",
                "reason": "ACK wait exceeded replacement threshold",
                "replacement_eligible": True,
                "elapsed_seconds": elapsed,
                "reminder_kind": "ack",
            }
        state = "ack_reminder_due" if elapsed is not None and elapsed >= ack_reminder_seconds else "wait_patrol"
        reason = (
            "assigned lease has not acknowledged; send ACK reminder"
            if state == "ack_reminder_due"
            else "assigned lease has not acknowledged"
        )
        return {
            **base,
            "state": state,
            "reason": reason,
            "elapsed_seconds": elapsed,
            "reminder_kind": "ack" if state == "ack_reminder_due" else "",
        }

    elapsed = _elapsed_seconds_since(lease_map.get("ack_received_at") or lease_map.get("created_at"))
    if isinstance(evidence_elapsed, int) and evidence_elapsed < progress_reminder_seconds:
        return {
            **base,
            "state": "grace_wait",
            "reason": "active lease has fresh ACK/progress evidence",
            "elapsed_seconds": elapsed,
        }
    if isinstance(evidence_elapsed, int) and evidence_elapsed >= progress_replace_seconds:
        return {
            **base,
            "state": "progress_replacement_due",
            "decision_override": "reissue_or_replace_lease",
            "reason": "result wait exceeded progress evidence replacement threshold",
            "replacement_eligible": True,
            "elapsed_seconds": elapsed,
            "reminder_kind": "progress",
        }
    state = "progress_reminder_due" if isinstance(evidence_elapsed, int) else "wait_patrol"
    reason = (
        "result wait needs strong progress reminder"
        if state == "progress_reminder_due"
        else "ACK is liveness only and result is still required"
    )
    return {
        **base,
        "state": state,
        "reason": reason,
        "elapsed_seconds": elapsed,
        "reminder_kind": "progress" if state == "progress_reminder_due" else "",
    }


def _guard_wait_subject(ledger: Mapping[str, Any], action: RuntimeAction) -> dict[str, Any]:
    packet = ledger.get("packets", {}).get(action.subject_id)
    if not isinstance(packet, Mapping):
        return {"packet_id": action.subject_id, "packet_found": False}
    lease_id = str(packet.get("assigned_lease_id") or "")
    lease = ledger.get("leases", {}).get(lease_id)
    lease_map = lease if isinstance(lease, Mapping) else {}
    liveness_evidence = _latest_liveness_evidence(lease_map)
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
        "last_liveness_evidence_kind": str(liveness_evidence.get("kind") or "none"),
        "last_liveness_evidence_at": str(liveness_evidence.get("at") or ""),
        "liveness_evidence_elapsed_seconds": liveness_evidence.get("elapsed_seconds"),
        "stale_result_blockers": _stale_result_blockers_for_packet(ledger, action.subject_id),
    }


def _guard_decision(
    ledger: Mapping[str, Any],
    action: RuntimeAction,
    *,
    trigger: str,
    repeated_count: int,
    prior_stuck_absorbed: bool,
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
    if action.action_type == "control_plane_blocker":
        return "control_plane_stuck", action.reason
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
    if prior_stuck_absorbed:
        return "control_plane_stuck", "previous stuck decision for the same nonterminal action remains unresolved"
    if classify_runtime_action(action) == "role_dispatch":
        return "process_next_action", action.reason
    if (
        trigger in _GUARD_STUCK_TRIGGERS
        and repeated_count >= threshold
        and classify_runtime_action(action) != "router_internal"
    ):
        return "control_plane_stuck", "same nonterminal next action repeated without current-run progress"
    return "process_next_action", action.reason


def _guard_prior_stuck_absorbed(
    history: list[Any],
    *,
    action_key: str,
    observed_event_count: int,
) -> bool:
    for item in reversed(history):
        if not isinstance(item, Mapping):
            continue
        if item.get("action_key") != action_key:
            continue
        if item.get("observed_event_count") != observed_event_count:
            continue
        if item.get("decision") == "control_plane_stuck":
            return True
    return False


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
    prior_stuck_absorbed = _guard_prior_stuck_absorbed(
        history,
        action_key=action_key,
        observed_event_count=event_count,
    )
    wait_recovery = _guard_wait_recovery(ledger, action, trigger=trigger, repeated_count=repeated_count)
    decision, reason = _guard_decision(
        ledger,
        action,
        trigger=trigger,
        repeated_count=repeated_count,
        prior_stuck_absorbed=prior_stuck_absorbed,
        wait_recovery=wait_recovery,
    )
    controller_stop_allowed = decision == "terminal_return"
    wait_subject = _guard_wait_subject(ledger, action) if action.subject_id else {}
    repair_loop_review = _repair_loop_break_glass_review_for_action(ledger, action)
    result = {
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
        "stuck_absorbed_from_history": prior_stuck_absorbed,
        "wait_subject": wait_subject,
        "wait_recovery": wait_recovery,
        "sealed_bodies_visible": False,
    }
    if repair_loop_review:
        result["repair_loop_break_glass_review"] = repair_loop_review
    return result


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
        status = str(blocker.get("status") or "")
        if status != "awaiting_pm_decision_gate" and not _blocker_current_effective(ledger, blocker):
            continue
        if status == "repair_packet_open":
            target_fields = ("repair_packet_id",)
        elif status == "awaiting_pm_decision_gate":
            target_fields = ()
        else:
            target_fields = (
                "packet_id",
                "subject_packet_id",
                "repair_target_packet_id",
            )
        for field in target_fields:
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
            packet = ledger.get("packets", {}).get(packet_id)
            if not isinstance(packet, Mapping):
                blockers.append(f"pm_gate_missing_source_packet:{gate_id}:{field}:{packet_id}")
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
    reminder_kind = str(wait_recovery.get("reminder_kind") or "")
    reminder_text = ""
    if reminder_kind == "ack":
        reminder_text = (
            "You have not ACKed the current packet. ACK it now through the current runtime path, "
            "or submit the supported blocker if you cannot receive this packet."
        )
    elif reminder_kind == "progress":
        reminder_text = (
            "You have not submitted the final result. If complete, submit the final result now. "
            "If still working, immediately record progress +1 for this lease and packet, then continue. "
            "After that, record progress +1 whenever work starts, resumes, reaches a small milestone, "
            "starts or finishes a long command, or receives another runtime reminder. If unable to continue, "
            "submit the supported blocker."
        )
    return {
        "active": True,
        "kind": "timed_patrol",
        "seconds": seconds,
        "subject_id": str((guard.get("next_action") or {}).get("subject_id", "")) if isinstance(guard.get("next_action"), Mapping) else "",
        "waiting_for": str(guard.get("decision", "")),
        "reason": str(guard.get("reason", "")),
        "packet_id": str(wait_subject.get("packet_id", "")),
        "wait_recovery": _copy_jsonable(wait_recovery),
        "reminder": {
            "due": bool(reminder_text),
            "kind": reminder_kind,
            "text": reminder_text,
            "controller_must_use_runtime_authored_text": bool(reminder_text),
        },
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
        command = "dispatch-current-role"
        args = {
            "packet_id": packet_id,
            "responsibility": responsibility,
            "host_kind": "live",
        }
        cli_args = [
            "dispatch-current-role",
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
        "cleanup_action": "dispatch_current_role",
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
        repair_loop_review = guard_map.get("repair_loop_break_glass_review")
        if isinstance(repair_loop_review, Mapping):
            duty["blocker"]["repair_loop_break_glass_review"] = _copy_jsonable(repair_loop_review)
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
                "stuck_absorbed_from_history": bool(snapshot.get("stuck_absorbed_from_history")),
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
    if ledger.get("completion_claims") and not _terminal_backward_replay_accepted(ledger):
        blockers.append("completion_report_only_not_sufficient")
    if high_standard_flow_required(ledger) and not _terminal_backward_replay_accepted(ledger):
        blockers.append("missing_terminal_backward_replay")
    if ledger.get("open_resources"):
        blockers.append("unresolved_resources")
    if ledger.get("residual_risks"):
        blockers.append("unresolved_residual_risks")
    if ledger.get("old_ui_evidence"):
        blockers.append("old_ui_evidence_unresolved")
    supplemental_state = _terminal_supplemental_state_view(ledger)
    if str(supplemental_state.get("status") or "") == "repair_rounds_exhausted":
        blockers.append("terminal_supplemental_repair_rounds_exhausted")
    _supplemental_rows, supplemental_unresolved = _supplemental_repair_closure_rows(ledger)
    blockers.extend(supplemental_unresolved)
    _hygiene_rows, hygiene_unresolved = _final_artifact_hygiene_closure_rows(ledger)
    blockers.extend(hygiene_unresolved)
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

    active_packets = [] if active_route is None else _current_packets_for_routing(ledger)
    accepted_packets = _accepted_packets_for_closure_evidence(ledger)
    if not accepted_packets:
        blockers.append("missing_accepted_packet_result")
    for packet in active_packets:
        if _packet_requires_current_acceptance(ledger, packet) and packet["status"] not in _NONCURRENT_PACKET_STATUSES:
            blockers.append(f"packet_not_accepted:{packet['packet_id']}")
    for packet in accepted_packets:
        if packet["envelope"].get("packet_kind", "task") != "task":
            continue
        result = ledger["results"][packet["accepted_result_id"]]
        node_id = str(packet["envelope"].get("route_node_id") or "")
        review_id = str(result.get("review_id") or "")
        if not _review_evidence_current_and_accepted(ledger, review_id, node_id=node_id):
            blockers.append(f"missing_independent_review:{packet['packet_id']}")
        packet_required_target = packet["envelope"].get("required_flowguard_target") or required_flowguard_target
        flowguard_required = _flowguard_required_for_subject_result(packet, result)
        if flowguard_required and packet_required_target:
            flowguard_order_ids = _matching_flowguard_order_ids(ledger, packet["packet_id"], packet_required_target)
            if not flowguard_order_ids:
                flowguard_order_ids = _current_gate_flowguard_order_ids_for_subject(ledger, packet["packet_id"])
            if not flowguard_order_ids:
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


def _repair_loop_break_glass_action(ledger: Mapping[str, Any]) -> RuntimeAction | None:
    for blocker in _active_semantic_blockers(ledger):
        review = _repair_loop_break_glass_review(ledger, blocker)
        if not review.get("threshold_exceeded"):
            continue
        blocker_id = str(blocker.get("blocker_id") or "")
        return RuntimeAction(
            "control_plane_blocker",
            "same current route node repeated the same blocker problem five or more consecutive times; Controller break-glass diagnosis is required",
            blocker_id,
            "controller",
        )
    return None


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
    active_packets = _current_packets_for_routing(ledger)
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
    terminal_replay_action = _terminal_backward_replay_next_action(ledger)
    if terminal_replay_action is not None:
        return terminal_replay_action
    repair_loop_action = _repair_loop_break_glass_action(ledger)
    if repair_loop_action is not None:
        return repair_loop_action
    if not active_packets and recursive_route_required(ledger) and ledger.get("route_nodes"):
        frontier = ledger.get("execution_frontier") or {}
        if (
            not frontier.get("active_node_id")
            and frontier.get("status") == "ready_for_final_closure"
            and closure.get("decision") != "blocked"
        ):
            if high_standard_flow_required(ledger) and not _terminal_backward_replay_accepted(ledger):
                if _final_gate_ledgers_clean_for_terminal_replay(ledger):
                    return RuntimeAction(
                        "issue_terminal_backward_replay_packet",
                        "terminal backward replay is required before final closure",
                        str(ledger.get("latest_validation_evidence_id") or ""),
                        "reviewer",
                    )
            return RuntimeAction("close_project", "all route nodes are resolved; final route-wide closure is required")
    if not active_packets:
        if recursive_route_required(ledger) and ledger.get("route_nodes"):
            frontier = ledger.get("execution_frontier") or {}
            if not frontier.get("active_node_id") and frontier.get("status") == "ready_for_final_closure":
                if high_standard_flow_required(ledger) and not _terminal_backward_replay_accepted(ledger):
                    if _final_gate_ledgers_clean_for_terminal_replay(ledger):
                        return RuntimeAction(
                            "issue_terminal_backward_replay_packet",
                            "terminal backward replay is required before final closure",
                            str(ledger.get("latest_validation_evidence_id") or ""),
                            "reviewer",
                        )
                if closure.get("decision") == "blocked":
                    return RuntimeAction(
                        "repair_packet",
                        "final closure blockers require current-route repair before new work",
                        "final_closure",
                    )
                return RuntimeAction("close_project", "all route nodes are resolved; final route-wide closure is required")
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
                "dispatch_current_role",
                "packet role must be dispatched through the current runtime",
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
            route_scope = str(packet["envelope"].get("route_scope") or "")
            if route_scope == "node_acceptance_plan":
                accepted_result = ledger.get("results", {}).get(str(packet.get("accepted_result_id") or ""))
                if not isinstance(accepted_result, Mapping):
                    result_ids = [str(item) for item in packet.get("result_ids") or [] if item]
                    accepted_result = ledger.get("results", {}).get(result_ids[-1]) if result_ids else None
                staged_effect = accepted_result.get("staged_effect") if isinstance(accepted_result, Mapping) else {}
                if isinstance(staged_effect, Mapping) and staged_effect.get("effect_kind") == "commit_node_acceptance_plan":
                    has_review_packet = _find_packet(
                        ledger,
                        packet_kind="review",
                        subject_id=packet["packet_id"],
                    )
                    if not has_review_packet:
                        return RuntimeAction("issue_review_packet", "node acceptance plan needs Reviewer review", packet["packet_id"], "reviewer")
                    continue
                if isinstance(staged_effect, Mapping) and staged_effect.get("effect_kind") == "commit_route_redesign":
                    continue
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

    for gate in ledger.get("pm_decision_gates", {}).values():
        if not isinstance(gate, Mapping):
            continue
        if gate.get("status") != "awaiting_pm_flowguard_acceptance":
            continue
        existing = _find_packet(
            ledger,
            packet_kind="pm_flowguard_acceptance",
            subject_id=str(gate.get("gate_id") or ""),
        )
        if not existing:
            return RuntimeAction(
                "issue_pm_flowguard_acceptance_packet",
                "structural PM decision requires PM absorption of FlowGuard before Reviewer",
                str(gate.get("gate_id") or ""),
                "pm",
            )

    for blocker in _active_semantic_blockers(ledger):
        packet_id = str(blocker.get("pm_repair_packet_id") or "")
        packet = ledger.get("packets", {}).get(packet_id)
        if not isinstance(packet, Mapping) or _packet_is_noncurrent_for_routing(ledger, packet):
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
            blocker = _node_worker_dispatch_blocker(ledger, node_id, node) if isinstance(node, Mapping) else ""
            if blocker:
                child_id = _first_unresolved_child_node_id(ledger, node) if isinstance(node, Mapping) else ""
                if child_id:
                    return RuntimeAction(
                        "issue_node_acceptance_plan_packet",
                        "parent/module route scope must enter child before worker execution",
                        child_id,
                        "pm",
                        "development_process",
                    )
                if high_standard_flow_required(ledger) and _node_requires_parent_backward_replay(node) and not _parent_backward_replay_accepted(ledger, node_id):
                    return RuntimeAction(
                        "issue_parent_backward_replay_packet",
                        "parent/module node requires backward replay before PM disposition",
                        node_id,
                        "reviewer",
                        "development_process",
                    )
                if node.get("status") == "awaiting_pm_disposition":
                    return RuntimeAction("issue_pm_disposition_packet", "node awaits PM disposition", node_id, "pm")
            if node.get("status") == "awaiting_pm_disposition":
                return RuntimeAction("issue_pm_disposition_packet", "node awaits PM disposition", node_id, "pm")
            if node.get("status") not in {"accepted", "superseded", "waived"}:
                return RuntimeAction("issue_node_task_packet", "frontier has an incomplete route node", node_id, node.get("responsibility", "worker"), node.get("modeled_target", ""))
        if (
            frontier.get("status") == "ready_for_final_closure"
            and not (ledger.get("closure") or {}).get("decision") == "complete"
            and (ledger.get("closure") or {}).get("decision") != "blocked"
        ):
            if high_standard_flow_required(ledger) and not _terminal_backward_replay_accepted(ledger):
                if _final_gate_ledgers_clean_for_terminal_replay(ledger):
                    return RuntimeAction(
                        "issue_terminal_backward_replay_packet",
                        "terminal backward replay is required before final closure",
                        str(ledger.get("latest_validation_evidence_id") or ""),
                        "reviewer",
                    )
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
    outcome_id = str(outcome.get("outcome_id") or outcome_id)
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
    matching_blockers = [
        blocker
        for blocker in ledger.get("active_blockers", {}).values()
        if isinstance(blocker, Mapping) and str(blocker.get("outcome_id") or "") == outcome_id
    ]
    if matching_blockers:
        return any(
            blocker.get("status") == "awaiting_pm_decision_gate" or _blocker_current_effective(ledger, blocker)
            for blocker in matching_blockers
        )
    packet_id = str(outcome.get("packet_id") or "")
    packet = ledger.get("packets", {}).get(packet_id) if packet_id else None
    if isinstance(packet, Mapping) and _packet_is_noncurrent_for_routing(ledger, packet):
        return False
    if _route_node_is_noncurrent(ledger, str(outcome.get("route_node_id") or "")):
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
                "progress_count": int(lease.get("progress_count", 0) or 0),
                "last_progress_at": lease.get("last_progress_at", ""),
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
    active_packet_ids = {
        str(packet.get("packet_id") or "")
        for packet in _current_packets_for_routing(ledger)
    }
    active_packets = [
        packet
        for packet in packets
        if isinstance(packet, Mapping) and str(packet.get("packet_id") or "") in active_packet_ids
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
