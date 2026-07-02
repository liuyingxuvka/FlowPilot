from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ASSETS_ROOT / "flowpilot_core_runtime"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))


def load_runtime_module():
    name = "flowpilot_core_runtime_repair_tests"
    spec = importlib.util.spec_from_file_location(name, RUNTIME_ROOT / "runtime.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(RUNTIME_ROOT))
    sys.path.insert(0, str(ASSETS_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_runtime_module()


def authorize_background_collaboration(ledger: dict[str, object]) -> None:
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }


def strict_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload, sort_keys=True)


def seeded_ledger(*, repair_depth: int = 0, blocker_class: str = "evidence_gap") -> tuple[dict[str, object], str]:
    ledger = runtime.new_ledger("Goal", "Acceptance")
    authorize_background_collaboration(ledger)
    ledger["contract_frozen"] = True
    ledger["contract_hash"] = runtime.hash_text("Goal\nAcceptance")
    node_id = "node-root" + "".join(f"-repair-v{index}" for index in range(1, repair_depth + 1))
    ledger["active_route_version"] = 1
    ledger["routes"]["1"] = {
        "route_version": 1,
        "route_id": "route-v1",
        "status": "active",
        "node_order": [node_id],
    }
    ledger["route_nodes"][node_id] = {
        "node_id": node_id,
        "route_version": 1,
        "title": "Current node",
        "node_kind": "leaf",
        "parent_node_id": "",
        "child_node_ids": [],
        "responsibility": "worker",
        "modeled_target": "development_process",
        "acceptance_criteria": ["Produce current evidence."],
        "status": "pending",
        "repair_generation": repair_depth,
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
        "stale_evidence": [],
    }
    ledger["execution_frontier"] = {
        "active_route_version": 1,
        "active_node_id": node_id,
        "completed_nodes": [],
        "status": "node_execution",
        "pending_route_mutation": None,
        "blocked_reason": "",
        "updated_at": runtime.now_iso(),
    }
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Do current work",
        json.dumps({"schema_version": "test.task.v1", "instruction": "work"}, sort_keys=True),
        route_node_id=node_id,
        route_scope="node",
        required_flowguard_target="development_process",
    )
    result_body = strict_result_body("Blocked worker evidence.")
    result_id = "result-worker-blocked"
    ledger["results"][result_id] = {
        "result_id": result_id,
        "packet_id": packet_id,
        "status": "review_blocked",
        "body": result_body,
        "envelope": {"body_hash": runtime.hash_text(result_body)},
        "created_at": runtime.now_iso(),
    }
    ledger["packets"][packet_id]["result_ids"].append(result_id)
    ledger["packets"][packet_id]["status"] = "review_blocked"
    review_body = strict_result_body("Reviewer blocked current evidence.")
    review_result_id = "result-review-blocker"
    ledger["results"][review_result_id] = {
        "result_id": review_result_id,
        "packet_id": "packet-review-blocker",
        "status": "accepted",
        "body": review_body,
        "envelope": {"body_hash": runtime.hash_text(review_body)},
        "created_at": runtime.now_iso(),
    }
    blocker_id = "blocker-current"
    ledger["active_blockers"][blocker_id] = {
        "blocker_id": blocker_id,
        "status": "active",
        "outcome_id": "",
        "packet_id": "packet-review-blocker",
        "packet_kind": "review",
        "subject_packet_id": packet_id,
        "repair_target_packet_id": packet_id,
        "target_result_id": result_id,
        "result_id": review_result_id,
        "owner_role": "reviewer",
        "required_recheck_role": "reviewer",
        "gate_kind": "review",
        "blocker_class": blocker_class,
        "recommended_resolution": "Repair the current evidence gap.",
        "route_version": 1,
        "route_node_id": node_id,
        "route_scope": "node",
        "repair_generation": repair_depth,
        "stale_evidence_ids": [result_id],
        "created_at": runtime.now_iso(),
        "pm_repair_packet_id": "",
        "pm_repair_decision_id": "",
        "repair_packet_id": "",
        "cleared_by_outcome_id": "",
    }
    return ledger, blocker_id
