"""Run FlowPilot Cartesian control-plane exhaustion checks."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
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
    from . import flowpilot_cartesian_control_plane_exhaustion_model as model
except ImportError:  # pragma: no cover
    import flowpilot_cartesian_control_plane_exhaustion_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_cartesian_control_plane_exhaustion_results.json"
NATIVE_CONTRACT_SHARD_SUITE_ID = "cartesian_flowguard_native_combination_shard"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
    *(f"reject_{name}" for name in model.NEGATIVE_SCENARIOS),
}

EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()

TEST_MESH_CHILD_SUITE_DEFINITIONS = {
    "cartesian_runtime_matrix": {
        "layer": "runtime_router_current_contract",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "cartesian_pm_repair_matrix": {
        "layer": "pm_repair_current_contract",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "cartesian_reviewer_matrix": {
        "layer": "reviewer_gate_current_contract",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "cartesian_flowguard_handoff_matrix": {
        "layer": "flowguard_handoff_current_contract",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "cartesian_testmesh_consumption_matrix": {
        "layer": "testmesh_child_suite_consumption",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "model_test_alignment",
    },
    "cartesian_modelmesh_closure_matrix": {
        "layer": "modelmesh_closure_consumption",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "model_mesh_closure",
    },
    "cartesian_glassbreak_threshold_matrix": {
        "layer": "glassbreak_threshold_liveness_probe",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "threshold_probe_only",
    },
    NATIVE_CONTRACT_SHARD_SUITE_ID: {
        "layer": TEST_LAYER_CONTRACT_COMBINATION_SHARD,
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "flowguard_native_contract_exhaustion",
    },
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"product={state.product_count_recorded}|skip={state.skipped_cell_reason_named}|"
        f"oracle={state.applicable_cell_has_oracle}|"
        f"feedback={state.current_subject_named},{state.owner_named},{state.repair_command_named},"
        f"{state.evidence_owner_named}|testmesh={state.testmesh_owner_registered}|"
        f"glassbreak={state.normal_context_entered_glassbreak},"
        f"{state.glassbreak_threshold_has_loop_key},"
        f"{state.glassbreak_threshold_attempt_count}|"
        f"compat={state.unsupported_shape_translated}|delta={state.no_delta_retry_without_feedback}|"
        f"bridge={state.contract_bridge_consumed},{state.historical_bridge_consumed}"
    )


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
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
        failures = set(model.cartesian_failures(state))
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


def _matrix_report() -> dict[str, Any]:
    cells = list(model.REQUIRED_CARTESIAN_CELLS)
    skipped = list(model.SKIPPED_CARTESIAN_CELLS)
    by_boundary = Counter(str(cell["boundary_id"]) for cell in cells)
    by_mutation = Counter(str(cell["mutation_kind"]) for cell in cells)
    by_context = Counter(str(cell["context"]) for cell in cells)
    by_consumer = Counter(str(cell["consumer"]) for cell in cells)
    by_reaction = Counter(str(cell["expected_reaction"]) for cell in cells)
    by_coverage_shard = Counter(str(cell["coverage_shard_id"]) for cell in cells)
    skip_reasons = Counter(str(cell["skip_reason"]) for cell in skipped)
    missing = [
        str(cell["cell_id"])
        for cell in cells
        if not cell.get("current_subject")
        or not cell.get("mechanical_owner")
        or not cell.get("expected_reaction")
        or not cell.get("required_repair_command")
        or not cell.get("required_evidence_owner")
        or not cell.get("required_feedback_fields")
        or not cell.get("contract_combination_case_id")
        or not cell.get("coverage_shard_id")
        or not cell.get("coverage_receipt_id")
    ]
    normal_glassbreak = [
        str(cell["cell_id"])
        for cell in cells
        if cell.get("normal_repair_context") and cell.get("expected_reaction") == "glassbreak_alarm"
    ]
    threshold_without_key = [
        str(cell["cell_id"])
        for cell in cells
        if cell.get("expected_reaction") == "glassbreak_alarm"
        and not cell.get("repeated_blocker_key_required")
    ]
    retry_without_delta = [
        str(cell["cell_id"])
        for cell in cells
        if cell.get("requires_next_packet_delta")
        and "required_delta" not in set(cell.get("required_feedback_fields", ()))
    ]
    missing_dimensions = {
        "boundary_ids": sorted(set(model.BOUNDARY_IDS) - set(by_boundary)),
        "mutation_ids": sorted(set(model.MUTATION_IDS) - set(by_mutation)),
        "contexts": sorted(set(model.CONTEXTS) - set(by_context)),
        "consumers": sorted(set(model.CONSUMERS) - set(by_consumer)),
    }
    ok = (
        not missing
        and not normal_glassbreak
        and not threshold_without_key
        and not retry_without_delta
        and not any(missing_dimensions.values())
        and len(cells) + len(skipped) == model.CARTESIAN_MATRIX["full_product_count"]
        and not [cell for cell in skipped if not cell.get("skip_reason")]
    )
    return {
        "ok": ok,
        "full_product_count": model.CARTESIAN_MATRIX["full_product_count"],
        "applicable_count": len(cells),
        "skipped_count": len(skipped),
        "boundary_count": len(by_boundary),
        "mutation_count": len(by_mutation),
        "context_count": len(by_context),
        "consumer_count": len(by_consumer),
        "by_boundary": dict(sorted(by_boundary.items())),
        "by_mutation_kind": dict(sorted(by_mutation.items())),
        "by_context": dict(sorted(by_context.items())),
        "by_consumer": dict(sorted(by_consumer.items())),
        "by_expected_reaction": dict(sorted(by_reaction.items())),
        "by_coverage_shard": dict(sorted(by_coverage_shard.items())),
        "coverage_shard_count": len(by_coverage_shard),
        "required_coverage_shard_ids": sorted(by_coverage_shard),
        "required_coverage_receipt_ids": sorted(
            {str(cell["coverage_receipt_id"]) for cell in cells}
        ),
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "missing_oracle_or_feedback": missing,
        "normal_context_glassbreak_cells": normal_glassbreak,
        "threshold_cells_without_loop_key": threshold_without_key,
        "retry_cells_without_delta_feedback": retry_without_delta,
        "missing_dimensions": missing_dimensions,
        "sample_cells": cells[:20],
        "sample_skipped_cells": skipped[:20],
        "required_cells": cells,
    }


def _flowguard_native_contract_report(matrix: dict[str, Any]) -> dict[str, Any]:
    report = review_contract_exhaustion(model.build_flowguard_contract_exhaustion_plan())
    combination_case_ids = {case.case_id for case in report.combination_cases}
    required_shard_ids = tuple(contract_exhaustion_to_test_mesh_shard_ids(report))
    receipt_ids = tuple(contract_exhaustion_to_coverage_receipt_ids(report))
    missing_generated_cases = [
        str(cell["cell_id"])
        for cell in matrix["required_cells"]
        if str(cell["contract_combination_case_id"]) not in combination_case_ids
    ]
    model_shard_ids = {str(cell["coverage_shard_id"]) for cell in matrix["required_cells"]}
    missing_model_shards = sorted(model_shard_ids - set(required_shard_ids))
    missing_receipts = sorted(
        {str(cell["coverage_receipt_id"]) for cell in matrix["required_cells"]}
        - set(receipt_ids)
    )
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
            and not missing_generated_cases
            and not missing_model_shards
            and not missing_receipts
            and any(receipt["current"] for receipt in receipt_summaries)
        ),
        "decision": report.decision,
        "confidence": report.confidence,
        "finding_codes": sorted({finding.code for finding in report.findings}),
        "finding_count": len(report.findings),
        "combination_case_count": len(report.combination_cases),
        "expected_combination_case_count": matrix["full_product_count"],
        "coverage_shard_count": len(report.coverage_shards),
        "flowpilot_model_owned_shard_count": len(model_shard_ids),
        "required_coverage_shard_ids": sorted(required_shard_ids),
        "required_coverage_receipt_ids": sorted(receipt_ids),
        "required_model_obligation_count": len(contract_exhaustion_to_model_obligations(report)),
        "missing_generated_combination_cases": missing_generated_cases,
        "missing_model_owned_shards": missing_model_shards,
        "missing_coverage_receipts": missing_receipts,
        "coverage_receipts": receipt_summaries,
        "sample_combination_case_ids": sorted(combination_case_ids)[:20],
        "sample_coverage_shard_ids": sorted(required_shard_ids)[:20],
    }


def _test_mesh_report(matrix: dict[str, Any], native_contract: dict[str, Any]) -> dict[str, Any]:
    required_owners = sorted({str(cell["required_evidence_owner"]) for cell in matrix["required_cells"]})
    required_shard_ids = tuple(native_contract["required_coverage_shard_ids"])
    flowpilot_shard_ids = set(matrix["required_coverage_shard_ids"])
    native_only_shard_ids = sorted(set(required_shard_ids) - flowpilot_shard_ids)
    child_suites: dict[str, dict[str, Any]] = {}
    for owner, definition in TEST_MESH_CHILD_SUITE_DEFINITIONS.items():
        if owner == NATIVE_CONTRACT_SHARD_SUITE_ID:
            owned_shards = native_only_shard_ids
            owned_cell_count = 0
        else:
            owned_shards = sorted(
                {
                    str(cell["coverage_shard_id"])
                    for cell in matrix["required_cells"]
                    if cell["required_evidence_owner"] == owner
                }
            )
            owned_cell_count = sum(
                1 for cell in matrix["required_cells"] if cell["required_evidence_owner"] == owner
            )
        child_suites[owner] = {
            **definition,
            "owned_cell_count": owned_cell_count,
            "owned_coverage_shard_ids": owned_shards,
        }
    unregistered = sorted(set(required_owners) - set(child_suites))
    missing = [
        name
        for name, suite in child_suites.items()
        if name in required_owners
        and (
            suite["owned_cell_count"] <= 0
            or not suite["owned_coverage_shard_ids"]
            or suite["result_status"] != "passed"
            or suite["evidence_current"] is not True
        )
    ]
    partition_items = tuple(
        TestPartitionItem(
            item_id=f"cartesian_shards.{suite_id}",
            item_type="contract_coverage_shard",
            owner_suite_id=suite_id,
            ownership="child",
            description="Cartesian coverage shard ownership for FlowPilot control-plane exhaustion.",
            touched_paths=(
                "simulations/flowpilot_cartesian_control_plane_exhaustion_model.py",
                "tests/test_flowpilot_cartesian_control_plane_exhaustion.py",
            ),
        )
        for suite_id, suite in sorted(child_suites.items())
        if suite["owned_coverage_shard_ids"]
    )
    suite_evidence = tuple(
        TestSuiteEvidence(
            suite_id=suite_id,
            command="python -m pytest tests/test_flowpilot_cartesian_control_plane_exhaustion.py -q",
            layer=TEST_LAYER_CONTRACT_COMBINATION_SHARD,
            result_status=str(suite["result_status"]),
            evidence_tier="abstract_green",
            evidence_current=bool(suite["evidence_current"]),
            test_count=max(1, int(suite["owned_cell_count"])),
            selected_count=max(1, int(suite["owned_cell_count"])),
            skipped_count=0,
            result_path="simulations/flowpilot_cartesian_control_plane_exhaustion_results.json",
            owns_state=("coverage_shard_id", "coverage_receipt_id", "required_evidence_owner"),
            owns_side_effects=("result_artifact",),
            owned_coverage_shard_ids=tuple(suite["owned_coverage_shard_ids"]),
        )
        for suite_id, suite in sorted(child_suites.items())
        if suite["owned_coverage_shard_ids"]
    )
    test_mesh_plan = TestMeshPlan(
        parent_suite_id="flowpilot_cartesian_control_plane_exhaustion_parent",
        partition_items=partition_items,
        child_suites=suite_evidence,
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id=model.MODEL_ID,
            target_suite_ids=tuple(suite.suite_id for suite in suite_evidence),
            covered_partition_item_ids=tuple(item.item_id for item in partition_items),
            state_owner_fields=("coverage_shard_id", "coverage_receipt_id", "required_evidence_owner"),
            side_effect_owner_fields=("result_artifact",),
            source_model_path="simulations/flowpilot_cartesian_control_plane_exhaustion_model.py",
            rationale="FlowGuard 0.51 Cartesian shards must be consumed by child test evidence owners.",
        ),
        required_coverage_shard_ids=required_shard_ids,
        required_evidence_tier="abstract_green",
        decision_scope="routine",
        allowed_shared_state=("coverage_shard_id", "coverage_receipt_id", "required_evidence_owner"),
        allowed_shared_side_effects=("result_artifact",),
    )
    flowguard_test_mesh_report = review_test_mesh(test_mesh_plan)
    flowguard_test_mesh = {
        "ok": flowguard_test_mesh_report.ok,
        "decision": flowguard_test_mesh_report.decision,
        "finding_count": len(flowguard_test_mesh_report.findings),
        "finding_codes": sorted({finding.code for finding in flowguard_test_mesh_report.findings}),
    }
    unowned_shards = sorted(
        set(required_shard_ids)
        - {
            shard_id
            for suite in child_suites.values()
            for shard_id in suite["owned_coverage_shard_ids"]
        }
    )
    return {
        "ok": not unregistered and not missing and not unowned_shards and flowguard_test_mesh["ok"],
        "child_suites": child_suites,
        "required_child_suite_owners": required_owners,
        "required_coverage_shard_ids": sorted(required_shard_ids),
        "unowned_coverage_shard_ids": unowned_shards,
        "unregistered_required_child_suites": unregistered,
        "missing_or_stale_child_suites": missing,
        "flowguard_test_mesh": flowguard_test_mesh,
    }


def _bridge_missing_mutation_families(
    *row_groups: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[str]:
    return sorted(
        {
            str(row["source_mutation_kind"])
            for rows in row_groups
            for row in rows
            if not bool(row.get("source_mutation_known", str(row["source_mutation_kind"]) in model.MUTATION_BY_ID))
            or str(row["cartesian_mutation_kind"]) not in model.MUTATION_BY_ID
        }
    )


def _bridge_fallback_translations(
    *row_groups: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[str]:
    return sorted(
        str(row["bridge_id"])
        for rows in row_groups
        for row in rows
        if str(row["source_mutation_kind"]) != str(row["cartesian_mutation_kind"])
        and str(row.get("bridge_translation_kind") or "") != "canonical_current_control_plane"
    )


def _bridge_report() -> dict[str, Any]:
    contract_rows = list(model.CONTRACT_EXHAUSTION_BRIDGE_CELLS)
    historical_rows = list(model.HISTORICAL_FAILURE_BRIDGE_CELLS)
    contract_missing = [
        row["bridge_id"]
        for row in contract_rows
        if not row.get("cartesian_boundary_id")
        or not row.get("cartesian_mutation_kind")
        or not row.get("required_evidence_owner")
    ]
    historical_missing = [
        row["bridge_id"]
        for row in historical_rows
        if not row.get("cartesian_boundary_id")
        or not row.get("cartesian_mutation_kind")
        or row.get("glass_break_allowed_in_acceptance") is not False
    ]
    missing_mutation_families = _bridge_missing_mutation_families(contract_rows, historical_rows)
    fallback_translations = _bridge_fallback_translations(contract_rows, historical_rows)
    canonical_translations = [
        row["bridge_id"]
        for row in contract_rows
        if row.get("bridge_translation_kind") == "canonical_current_control_plane"
    ]
    return {
        "ok": (
            not contract_missing
            and not historical_missing
            and not missing_mutation_families
            and not fallback_translations
        ),
        "contract_exhaustion_bridge_count": len(contract_rows),
        "historical_failure_bridge_count": len(historical_rows),
        "contract_bridge_missing_consumption": contract_missing,
        "historical_bridge_missing_consumption": historical_missing,
        "missing_mutation_families": missing_mutation_families,
        "fallback_bridge_translations": fallback_translations,
        "canonical_bridge_translation_count": len(canonical_translations),
        "sample_canonical_bridge_translations": canonical_translations[:20],
        "sample_contract_bridge_cells": contract_rows[:20],
        "sample_historical_bridge_cells": historical_rows[:20],
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    walk = _walk_report()
    hazards = _hazard_report()
    matrix = _matrix_report()
    native_contract = _flowguard_native_contract_report(matrix)
    test_mesh = _test_mesh_report(matrix, native_contract)
    bridges = _bridge_report()
    ok = all(section["ok"] for section in (flowguard, walk, hazards, matrix, native_contract, test_mesh, bridges))
    return {
        "model_id": model.MODEL_ID,
        "ok": ok,
        "flowguard": flowguard,
        "walk": walk,
        "hazards": hazards,
        "matrix": matrix,
        "native_contract_exhaustion": native_contract,
        "test_mesh": test_mesh,
        "bridges": bridges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    report = run_checks()
    if not args.check_only:
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "model_id": report["model_id"]}, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
