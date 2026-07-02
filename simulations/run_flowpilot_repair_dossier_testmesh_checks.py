"""Run the FlowPilot repair-dossier Cartesian TestMesh checks."""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_PATH = ASSETS_ROOT / "flowpilot_core_runtime" / "runtime.py"
RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_repair_dossier_testmesh_results.json")


def _load_runtime():
    if str(ASSETS_ROOT) not in sys.path:
        sys.path.insert(0, str(ASSETS_ROOT))
    if str(RUNTIME_PATH.parent) not in sys.path:
        sys.path.insert(0, str(RUNTIME_PATH.parent))
    spec = importlib.util.spec_from_file_location("flowpilot_runtime_repair_dossier_mesh", RUNTIME_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runtime = _load_runtime()


def _seed_ledger(*, repair_depth: int, blocker_class: str) -> tuple[dict[str, Any], str]:
    ledger = runtime.new_ledger("Goal", "Acceptance")
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    ledger["contract_frozen"] = True
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
        "title": "Mesh node",
        "node_kind": "leaf",
        "parent_node_id": "",
        "child_node_ids": [],
        "responsibility": "worker",
        "modeled_target": "development_process",
        "acceptance_criteria": ["Current evidence"],
        "status": "pending",
        "repair_generation": repair_depth,
        "packet_ids": [],
        "accepted_result_id": "",
        "flowguard_order_ids": [],
        "review_ids": [],
        "validation_evidence_ids": [],
        "node_context_package_id": "",
        "node_context_package_repair_generation": None,
        "stale_evidence": [],
    }
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Mesh subject packet",
        json.dumps({"schema_version": "mesh.subject.v1"}, sort_keys=True),
        route_node_id=node_id,
        route_scope="node",
        required_flowguard_target="development_process",
    )
    result_body = json.dumps({"decision": "pass", "pm_visible_summary": ["context"]}, sort_keys=True)
    result_id = "result-subject"
    ledger["results"][result_id] = {
        "result_id": result_id,
        "packet_id": packet_id,
        "status": "review_blocked",
        "body": result_body,
        "envelope": {"body_hash": runtime.hash_text(result_body)},
    }
    ledger["packets"][packet_id]["result_ids"].append(result_id)
    blocker_id = "blocker-current"
    ledger["active_blockers"][blocker_id] = {
        "blocker_id": blocker_id,
        "status": "active",
        "packet_id": packet_id,
        "subject_packet_id": packet_id,
        "repair_target_packet_id": packet_id,
        "target_result_id": result_id,
        "result_id": result_id,
        "required_recheck_role": "reviewer",
        "gate_kind": "review",
        "blocker_class": blocker_class,
        "recommended_resolution": "Repair current gap.",
        "route_node_id": node_id,
        "route_scope": "node",
        "repair_generation": repair_depth,
        "pm_repair_packet_id": "",
        "pm_repair_decision_id": "",
        "repair_packet_id": "",
    }
    return ledger, blocker_id


def _stage_precedence_subject_cases() -> tuple[dict[str, str], ...]:
    return (
        {
            "subject_case": "pm_plan_stage_no_completion_claim",
            "subject_family": "task.node_acceptance_plan",
            "lifecycle_stage": "node_plan_definition",
            "evidence_state": "pm_plan_only",
            "subject_completion_claim_state": "no_completion_claim",
            "expected_outcome": "allow_plan_stage_review",
        },
        {
            "subject_case": "pm_plan_stage_claims_worker_evidence",
            "subject_family": "task.node_acceptance_plan",
            "lifecycle_stage": "node_plan_definition",
            "evidence_state": "pm_plan_only",
            "subject_completion_claim_state": "claims_worker_evidence_complete",
            "expected_outcome": "block_missing_claimed_current_evidence",
        },
        {
            "subject_case": "worker_result_stage_plan_only",
            "subject_family": "task.node",
            "lifecycle_stage": "node_result_execution",
            "evidence_state": "pm_plan_only",
            "subject_completion_claim_state": "result_stage_subject",
            "expected_outcome": "block_missing_current_worker_evidence",
        },
        {
            "subject_case": "worker_result_stage_current_worker_evidence",
            "subject_family": "task.node",
            "lifecycle_stage": "node_result_execution",
            "evidence_state": "current_worker_evidence",
            "subject_completion_claim_state": "result_stage_subject",
            "expected_outcome": "allow_worker_result_review",
        },
    )


def _stage_precedence_outcome(case: dict[str, str]) -> str:
    subject_family = case["subject_family"]
    lifecycle_stage = case["lifecycle_stage"]
    evidence_state = case["evidence_state"]
    claim_state = case["subject_completion_claim_state"]
    stage_row = runtime.packet_result_contracts.role_visible_stage_evidence_row_json_for_family(subject_family)
    review_window = runtime.review_window_contracts.review_window_contract_for_context(
        review_result_family_id="review.any_current_subject",
        subject_family_id=subject_family,
        subject_lifecycle_stage=lifecycle_stage,
    )
    if stage_row.get("lifecycle_stage") != lifecycle_stage:
        return "block_stage_mismatch"
    required_fields = {str(field) for field in stage_row.get("current_required_fields") or []}
    forbidden_future = {str(item) for item in review_window.get("forbidden_future_stage_classes") or []}
    if subject_family == "task.node_acceptance_plan" and claim_state == "no_completion_claim":
        if "current_evidence_refs" in required_fields:
            return "block_missing_current_worker_evidence"
        if "worker_result_artifacts" in forbidden_future:
            return "allow_plan_stage_review"
    if evidence_state == "pm_plan_only" and claim_state == "claims_worker_evidence_complete":
        return "block_missing_claimed_current_evidence"
    if subject_family == "task.node" and evidence_state == "pm_plan_only":
        return "block_missing_current_worker_evidence"
    if subject_family == "task.node" and evidence_state == "current_worker_evidence":
        return "allow_worker_result_review"
    return "block_uncovered_stage_precedence_case"


def run_checks() -> dict[str, Any]:
    roles = {
        "pm": "pm_repair_decision",
        "worker": "task",
        "reviewer": "review",
        "flowguard_operator": "flowguard_check",
    }
    blocker_classes = [
        "evidence_gap",
        "flowguard_failure",
        "route_decomposition",
        "missing_required_information",
        "missing_matching_flowguard_report",
    ]
    depths = [0, 1, 2, 4, 5, 6]
    failures: list[str] = []
    cells = []
    for role, blocker_class, depth in itertools.product(roles, blocker_classes, depths):
        ledger, blocker_id = _seed_ledger(repair_depth=depth, blocker_class=blocker_class)
        blocker = ledger["active_blockers"][blocker_id]
        next_action = runtime._blocker_required_next_action(blocker_class)
        review = runtime._repair_loop_break_glass_review(ledger, blocker)
        cells.append(
            {
                "role": role,
                "packet_kind": roles[role],
                "blocker_class": blocker_class,
                "repair_depth": depth,
                "hard_next_action": next_action,
                "glassbreak": bool(review["threshold_exceeded"]),
            }
        )
        if depth >= 5 and not review["threshold_exceeded"]:
            failures.append(f"missing_glassbreak:{role}:{blocker_class}:{depth}")
        if depth < 5 and review["threshold_exceeded"]:
            failures.append(f"early_glassbreak:{role}:{blocker_class}:{depth}")
        if blocker_class == "missing_required_information" and next_action != "same_packet_block_or_stop_for_user":
            failures.append("missing_required_information_wrong_next_action")
        if blocker_class == "missing_matching_flowguard_report" and next_action != "issue_matching_flowguard_packet":
            failures.append("missing_matching_flowguard_wrong_next_action")
        if blocker_class not in {"missing_required_information", "missing_matching_flowguard_report"}:
            packet_id = runtime.issue_task_packet(
                ledger,
                role,
                "Mesh repair packet",
                json.dumps({"schema_version": "mesh.repair.v1"}, sort_keys=True),
                packet_kind=roles[role],
                subject_id=blocker_id if roles[role] == "pm_repair_decision" else blocker["subject_packet_id"],
                target_result_id=blocker["target_result_id"],
                route_node_id=blocker["route_node_id"],
                route_scope="pm_repair_decision" if roles[role] == "pm_repair_decision" else "node",
                repair_blocker_id=blocker_id,
            )
            packet = ledger["packets"][packet_id]
            body = json.loads(packet["body"])
            if body.get("repair_dossier_context", {}).get("repair_depth") != depth:
                failures.append(f"missing_dossier_depth:{role}:{blocker_class}:{depth}")
            reads = packet["envelope"].get("authorized_result_reads") or []
            if not reads or any(role not in row.get("allowed_roles", []) for row in reads):
                failures.append(f"bad_role_scoped_reads:{role}:{blocker_class}:{depth}")
    for blocker_class, depth, case in itertools.product(blocker_classes, depths, _stage_precedence_subject_cases()):
        outcome = _stage_precedence_outcome(case)
        cells.append(
            {
                "dimension_family": "stage_precedence",
                "role": "reviewer",
                "packet_kind": "review",
                "blocker_class": blocker_class,
                "repair_depth": depth,
                "subject_case": case["subject_case"],
                "subject_family": case["subject_family"],
                "lifecycle_stage": case["lifecycle_stage"],
                "evidence_state": case["evidence_state"],
                "subject_completion_claim_state": case["subject_completion_claim_state"],
                "expected_outcome": case["expected_outcome"],
                "actual_outcome": outcome,
            }
        )
        if outcome != case["expected_outcome"]:
            failures.append(
                "stage_precedence_mismatch:"
                f"{blocker_class}:{depth}:{case['subject_case']}:{outcome}"
            )
    return {
        "ok": not failures,
        "cell_count": len(cells),
        "stage_precedence_cell_count": len(
            [cell for cell in cells if cell.get("dimension_family") == "stage_precedence"]
        ),
        "failures": failures,
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    if args.write:
        RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    text = json.dumps(report, indent=2, sort_keys=True) if args.json else ("ok" if report["ok"] else "failed")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
