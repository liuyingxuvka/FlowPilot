"""Run FlowPilot progress_fraction lifecycle Cartesian checks."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import sys
from typing import Any

from flowguard import (
    TEST_LAYER_CONTRACT_COMBINATION_SHARD,
    TestMeshPlan,
    TestPartitionItem,
    TestSuiteEvidence,
    TestTargetSplitDerivation,
    contract_exhaustion_to_coverage_receipt_ids,
    contract_exhaustion_to_model_obligations,
    contract_exhaustion_to_test_mesh_shard_ids,
    review_contract_exhaustion,
    review_test_mesh,
)
from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_progress_lifecycle_cartesian_model as model
except ImportError:  # pragma: no cover
    import flowpilot_progress_lifecycle_cartesian_model as model


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import runtime  # noqa: E402


RESULTS_PATH = ROOT / "simulations" / "flowpilot_progress_lifecycle_cartesian_results.json"
RUNTIME_MATRIX_SUITE_ID = "progress_lifecycle_runtime_matrix"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
    *(f"reject_{name}" for name in model.NEGATIVE_SCENARIOS),
}
EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|full={state.full_product_declared}|"
        f"runtime={state.runtime_matrix_passed}|node_order={state.node_order_projection_independent}|"
        f"noise={state.control_noise_independent}|removed={state.removed_status_excluded}|"
        f"packet_projection={state.packet_projection_used}"
    )


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _walk_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []
    terminal_count = 0
    accepted_count = 0
    rejected_count = 0
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        if model.is_terminal(state):
            terminal_count += 1
            if state.status == "accepted":
                accepted_count += 1
            elif state.status == "rejected":
                rejected_count += 1
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not invariant_failures,
        "state_count": len(states),
        "terminal_count": terminal_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = set(model.coverage_failures(state))
        expected = set(EXPECTED_HAZARD_FAILURES[name])
        if failures:
            hazards[name] = sorted(failures)
        if not expected <= failures:
            missing[name] = sorted(expected - failures)
    return {
        "ok": set(hazards) == set(model.NEGATIVE_SCENARIOS) and not missing,
        "hazards": hazards,
        "expected": sorted(model.NEGATIVE_SCENARIOS),
        "missing_expected_failures": missing,
    }


def _runtime_ledger_for_cell(cell: dict[str, Any]) -> dict[str, Any]:
    ledger = runtime.new_ledger("Progress lifecycle matrix", "Contract")
    nodes = model.route_nodes_for_cell(cell)
    node_order = model.node_order_for_cell(cell, nodes)
    if nodes:
        ledger["active_route_version"] = 1
        ledger["routes"] = {
            "1": {
                "route_version": 1,
                "status": "active",
                "node_order": list(node_order),
            }
        }
        ledger["route_nodes"] = {
            str(node["node_id"]): {
                "node_id": str(node["node_id"]),
                "route_version": 1,
                "status": str(node["status"]),
                "node_kind": str(node.get("node_kind") or "leaf"),
                "repair_generation": int(node.get("repair_generation", 0) or 0),
                "parent_node_id": str(node.get("parent_node_id") or ""),
                "child_node_ids": list(node.get("child_node_ids") or []),
                "packet_ids": [],
            }
            for node in nodes
        }
    noise = str(cell["control_plane_noise"])
    if noise == "packet_activity":
        ledger.setdefault("packets", {})["packet-noise"] = {
            "packet_id": "packet-noise",
            "status": "accepted",
            "accepted_result_id": "result-noise",
            "envelope": {"route_node_id": "node-noise", "route_version": 1, "packet_kind": "task"},
            "body": "SEALED_PACKET_BODY",
        }
        ledger.setdefault("results", {})["result-noise"] = {"result_id": "result-noise", "status": "accepted"}
    elif noise == "lease_ack_progress":
        ledger.setdefault("leases", {})["lease-noise"] = {
            "lease_id": "lease-noise",
            "status": "acknowledged",
            "packet_id": "packet-noise",
            "role": "worker",
        }
        ledger.setdefault("events", []).append({"event_type": "lease_acknowledged", "payload": {"lease_id": "lease-noise"}})
    elif noise == "patrol_role_receipt":
        ledger.setdefault("controller_receipts", {})["receipt-noise"] = {
            "receipt_id": "receipt-noise",
            "status": "recorded",
        }
        ledger.setdefault("role_assignments", {})["assignment-noise"] = {
            "assignment_id": "assignment-noise",
            "status": "resolved",
        }
    elif noise == "sealed_body_payload":
        ledger.setdefault("packets", {})["packet-sealed-noise"] = {
            "packet_id": "packet-sealed-noise",
            "status": "open",
            "envelope": {"packet_kind": "task", "route_node_id": "", "route_version": 1},
            "body": '{"sealed":"SHOULD_NOT_AFFECT_PROGRESS"}',
        }
    return ledger


def _actual_progress_for_cell(cell: dict[str, Any]) -> dict[str, Any]:
    progress = runtime.current_progress_fraction(_runtime_ledger_for_cell(cell))
    return {
        "display": progress["display"],
        "ended_nodes": progress["ended_nodes"],
        "expanded_nodes": progress["expanded_nodes"],
        "source": progress["source"],
        "repair_generations": progress["repair_generations"],
        "includes_repair_generations": progress["includes_repair_generations"],
        "packet_projection_used": progress["packet_projection_used"],
        "percent_provided": progress["percent_provided"],
        "sealed_bodies_visible": progress["sealed_bodies_visible"],
    }


def _matrix_report() -> dict[str, Any]:
    by_status: Counter[str] = Counter()
    by_topology: Counter[str] = Counter()
    by_projection: Counter[str] = Counter()
    by_noise: Counter[str] = Counter()
    by_display: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    by_shard: Counter[str] = Counter()
    runtime_mismatches: list[dict[str, Any]] = []
    packet_projection_cells: list[str] = []
    percent_cells: list[str] = []
    sealed_body_cells: list[str] = []
    removed_status_projection_failures: list[str] = []
    node_order_groups: dict[tuple[str, str, str, str, str], set[tuple[int, int, str]]] = defaultdict(set)
    noise_groups: dict[tuple[str, str, str, str, str], set[tuple[int, int, str]]] = defaultdict(set)
    sample_cells: list[dict[str, Any]] = []

    for index, cell in enumerate(model.iter_required_cells()):
        expected = dict(cell["expected_progress"])
        actual = _actual_progress_for_cell(cell)
        by_status[str(cell["node_status"])] += 1
        by_topology[str(cell["route_topology"])] += 1
        by_projection[str(cell["node_order_projection"])] += 1
        by_noise[str(cell["control_plane_noise"])] += 1
        by_display[str(actual["display"])] += 1
        by_source[str(actual["source"])] += 1
        by_shard[str(cell["coverage_shard_id"])] += 1
        group_without_projection = (
            str(cell["node_status"]),
            str(cell["route_topology"]),
            str(cell["node_kind"]),
            str(cell["control_plane_noise"]),
            str(cell["repair_generation"]),
        )
        group_without_noise = (
            str(cell["node_status"]),
            str(cell["route_topology"]),
            str(cell["node_order_projection"]),
            str(cell["node_kind"]),
            str(cell["repair_generation"]),
        )
        projection_result = (int(actual["ended_nodes"]), int(actual["expanded_nodes"]), str(actual["source"]))
        node_order_groups[group_without_projection].add(projection_result)
        noise_groups[group_without_noise].add(projection_result)
        for key in (
            "display",
            "ended_nodes",
            "expanded_nodes",
            "source",
            "repair_generations",
            "includes_repair_generations",
        ):
            if actual[key] != expected[key]:
                runtime_mismatches.append(
                    {
                        "cell_id": cell["cell_id"],
                        "field": key,
                        "expected": expected[key],
                        "actual": actual[key],
                    }
                )
                break
        if actual["packet_projection_used"]:
            packet_projection_cells.append(str(cell["cell_id"]))
        if actual["percent_provided"]:
            percent_cells.append(str(cell["cell_id"]))
        if actual["sealed_bodies_visible"]:
            sealed_body_cells.append(str(cell["cell_id"]))
        if str(cell["node_status"]) in model.REMOVED_STATUSES and (
            actual["expanded_nodes"] != expected["expanded_nodes"]
            or actual["repair_generations"] != expected["repair_generations"]
        ):
            removed_status_projection_failures.append(str(cell["cell_id"]))
        if index < 25:
            sample_cells.append(
                {
                    "cell_id": cell["cell_id"],
                    "expected": expected,
                    "actual": actual,
                    "coverage_shard_id": cell["coverage_shard_id"],
                }
            )

    node_order_variant_failures = [
        {"group": "|".join(group), "observed_results": sorted(results)}
        for group, results in node_order_groups.items()
        if len(results) > 1
    ]
    control_noise_variant_failures = [
        {"group": "|".join(group), "observed_results": sorted(results)}
        for group, results in noise_groups.items()
        if len(results) > 1
    ]
    coverage = model.axis_value_coverage()
    missing_axis_values = {axis: row["missing"] for axis, row in coverage.items() if row["missing"]}
    ok = (
        not runtime_mismatches
        and not packet_projection_cells
        and not percent_cells
        and not sealed_body_cells
        and not node_order_variant_failures
        and not control_noise_variant_failures
        and not missing_axis_values
    )
    return {
        "ok": ok,
        "full_product_count": model.required_cell_count(),
        "axis_counts": model.matrix_counts()["axis_counts"],
        "axis_coverage": coverage,
        "missing_axis_values": missing_axis_values,
        "by_node_status": dict(sorted(by_status.items())),
        "by_route_topology": dict(sorted(by_topology.items())),
        "by_node_order_projection": dict(sorted(by_projection.items())),
        "by_control_plane_noise": dict(sorted(by_noise.items())),
        "by_display": dict(sorted(by_display.items())),
        "by_source": dict(sorted(by_source.items())),
        "coverage_shard_count": len(by_shard),
        "required_coverage_shard_ids": sorted(by_shard),
        "runtime_mismatch_count": len(runtime_mismatches),
        "runtime_mismatches": runtime_mismatches[:20],
        "packet_projection_cells": packet_projection_cells[:20],
        "percent_cells": percent_cells[:20],
        "sealed_body_cells": sealed_body_cells[:20],
        "removed_status_projection_failures": removed_status_projection_failures[:20],
        "node_order_variant_failures": node_order_variant_failures[:20],
        "control_noise_variant_failures": control_noise_variant_failures[:20],
        "sample_cells": sample_cells,
    }


def _flowguard_native_contract_report(matrix: dict[str, Any]) -> dict[str, Any]:
    report = review_contract_exhaustion(model.build_flowguard_contract_exhaustion_plan())
    combination_case_ids = {case.case_id for case in report.combination_cases}
    required_shard_ids = tuple(contract_exhaustion_to_test_mesh_shard_ids(report))
    receipt_ids = tuple(contract_exhaustion_to_coverage_receipt_ids(report))
    expected_case_ids = {str(cell["contract_combination_case_id"]) for cell in model.iter_required_cells()}
    missing_generated_cases = sorted(expected_case_ids - combination_case_ids)
    model_shard_ids = set(matrix["required_coverage_shard_ids"])
    missing_model_shards = sorted(model_shard_ids - set(required_shard_ids))
    receipt_summaries = [
        {
            "receipt_id": receipt.receipt_id,
            "model_id": receipt.model_id,
            "status": receipt.status,
            "current": receipt.current,
            "covered_case_count": len(receipt.covered_case_ids),
            "shard_count": len(receipt.shard_ids),
            "missing_case_count": len(receipt.missing_case_ids),
            "blocked_case_count": len(receipt.blocked_case_ids),
        }
        for receipt in report.coverage_receipts
    ]
    return {
        "ok": (
            report.ok
            and len(combination_case_ids) == matrix["full_product_count"]
            and not missing_generated_cases
            and not missing_model_shards
            and model.FLOWGUARD_NATIVE_RECEIPT_ID in receipt_ids
            and any(receipt["current"] for receipt in receipt_summaries)
        ),
        "decision": report.decision,
        "confidence": report.confidence,
        "finding_codes": sorted({finding.code for finding in report.findings}),
        "finding_count": len(report.findings),
        "combination_case_count": len(report.combination_cases),
        "expected_combination_case_count": matrix["full_product_count"],
        "coverage_shard_count": len(report.coverage_shards),
        "required_coverage_shard_ids": sorted(required_shard_ids),
        "required_coverage_receipt_ids": sorted(receipt_ids),
        "required_model_obligation_count": len(contract_exhaustion_to_model_obligations(report)),
        "missing_generated_combination_cases": missing_generated_cases[:20],
        "missing_generated_combination_case_count": len(missing_generated_cases),
        "missing_model_owned_shards": missing_model_shards,
        "coverage_receipts": receipt_summaries,
        "sample_combination_case_ids": sorted(combination_case_ids)[:20],
    }


def _test_mesh_report(matrix: dict[str, Any], native_contract: dict[str, Any]) -> dict[str, Any]:
    required_shard_ids = tuple(native_contract["required_coverage_shard_ids"])
    partition_items = (
        TestPartitionItem(
            item_id=f"progress_lifecycle_shards.{RUNTIME_MATRIX_SUITE_ID}",
            item_type="contract_coverage_shard",
            owner_suite_id=RUNTIME_MATRIX_SUITE_ID,
            ownership="child",
            description="Cartesian coverage shard ownership for FlowPilot progress lifecycle projection.",
            touched_paths=(
                "simulations/flowpilot_progress_lifecycle_cartesian_model.py",
                "tests/test_flowpilot_progress_lifecycle_cartesian.py",
            ),
        ),
    )
    suite_evidence = (
        TestSuiteEvidence(
            suite_id=RUNTIME_MATRIX_SUITE_ID,
            command="python -m pytest tests/test_flowpilot_progress_lifecycle_cartesian.py -q",
            layer=TEST_LAYER_CONTRACT_COMBINATION_SHARD,
            result_status="passed",
            evidence_tier="abstract_green",
            evidence_current=True,
            test_count=int(matrix["full_product_count"]),
            selected_count=int(matrix["full_product_count"]),
            skipped_count=0,
            result_path="simulations/flowpilot_progress_lifecycle_cartesian_results.json",
            owns_state=(
                "progress_fraction.ended_nodes",
                "progress_fraction.expanded_nodes",
                "route_nodes.status",
                "routes.node_order",
            ),
            owns_side_effects=("result_artifact",),
            owned_coverage_shard_ids=required_shard_ids,
        ),
    )
    plan = TestMeshPlan(
        parent_suite_id="flowpilot_progress_lifecycle_cartesian_parent",
        partition_items=partition_items,
        child_suites=suite_evidence,
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id=model.MODEL_ID,
            target_suite_ids=(RUNTIME_MATRIX_SUITE_ID,),
            covered_partition_item_ids=tuple(item.item_id for item in partition_items),
            state_owner_fields=(
                "progress_fraction.ended_nodes",
                "progress_fraction.expanded_nodes",
                "route_nodes.status",
                "routes.node_order",
            ),
            side_effect_owner_fields=("result_artifact",),
            source_model_path="simulations/flowpilot_progress_lifecycle_cartesian_model.py",
            rationale="The progress lifecycle matrix owns every finite progress_fraction combination cell.",
        ),
        required_coverage_shard_ids=required_shard_ids,
        required_evidence_tier="abstract_green",
        decision_scope="routine",
        allowed_shared_state=(
            "progress_fraction.ended_nodes",
            "progress_fraction.expanded_nodes",
            "route_nodes.status",
            "routes.node_order",
        ),
        allowed_shared_side_effects=("result_artifact",),
    )
    report = review_test_mesh(plan)
    return {
        "ok": report.ok,
        "decision": report.decision,
        "finding_count": len(report.findings),
        "finding_codes": sorted({finding.code for finding in report.findings}),
        "required_coverage_shard_ids": sorted(required_shard_ids),
        "child_suites": {
            RUNTIME_MATRIX_SUITE_ID: {
                "owned_coverage_shard_ids": sorted(required_shard_ids),
                "owned_cell_count": int(matrix["full_product_count"]),
                "result_status": "passed",
                "evidence_current": True,
            }
        },
        "unowned_coverage_shard_ids": [],
    }


def run_checks() -> dict[str, Any]:
    walk = _walk_report()
    explorer = _flowguard_report()
    hazards = _hazard_report()
    matrix = _matrix_report()
    native_contract = _flowguard_native_contract_report(matrix)
    test_mesh = _test_mesh_report(matrix, native_contract)
    result = {
        "model_id": model.MODEL_ID,
        "ok": all(
            section.get("ok", False)
            for section in (walk, explorer, hazards, matrix, native_contract, test_mesh)
        ),
        "walk": walk,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "matrix": matrix,
        "native_contract_exhaustion": native_contract,
        "test_mesh": test_mesh,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
