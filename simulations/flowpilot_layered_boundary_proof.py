"""Review FlowPilot coverage with FlowGuard layered boundary proof.

This check consumes the full model coverage inventory and model-test alignment
diagnostic. It does not execute FlowPilot routes or mutate runtime state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from flowguard import (
    ChildProofContract,
    ChildReattachmentProof,
    LeafBoundaryMatrix,
    LeafBoundaryMatrixCell,
    LayeredBoundaryProofPlan,
    ParentCoverageItem,
    review_layered_boundary_proof,
)

import run_flowpilot_full_model_coverage_inventory as coverage_inventory
import flowpilot_contract_exhaustion_mesh_model as contract_exhaustion_model
import run_flowpilot_contract_exhaustion_mesh_checks as contract_exhaustion_runner
import flowpilot_cartesian_control_plane_exhaustion_model as cartesian_exhaustion_model
import run_flowpilot_cartesian_control_plane_exhaustion_checks as cartesian_exhaustion_runner


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY_PATH = ROOT / "simulations" / "flowpilot_full_model_coverage_inventory_results.json"
DEFAULT_ALIGNMENT_PATH = ROOT / "simulations" / "flowpilot_model_test_alignment_results.json"
DEFAULT_CONTRACT_EXHAUSTION_PATH = ROOT / "simulations" / "flowpilot_contract_exhaustion_mesh_results.json"
DEFAULT_CARTESIAN_EXHAUSTION_PATH = ROOT / "simulations" / "flowpilot_cartesian_control_plane_exhaustion_results.json"
DEFAULT_JSON_OUT = ROOT / "simulations" / "flowpilot_layered_boundary_proof_results.json"

CURRENTLY_CONSUMABLE = "currently_consumable_inventory_evidence"
GAP_CLASS_STRATEGY = {
    "runner_unparsed_or_unavailable": "failure-sentinel",
    "runner_not_ok": "failure-sentinel",
    "live_runtime_or_state_findings": "failure-sentinel",
    "source_or_code_findings": "result-contract",
    "missing_or_scoped_replay_adapter": "scoped-boundary",
    "skipped_or_scoped_evidence": "scoped-boundary",
    "abstract_without_detected_ordinary_test_reference": "runner-exec",
    "unclassified_model_tier": "result-contract",
    CURRENTLY_CONSUMABLE: "result-contract",
}
REQUIREMENT_BLOCKING_GAP_CLASSES = (
    "runner_unparsed_or_unavailable",
    "runner_not_ok",
    "live_runtime_or_state_findings",
    "source_or_code_findings",
    "missing_or_scoped_replay_adapter",
    "skipped_or_scoped_evidence",
    "abstract_without_detected_ordinary_test_reference",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value


def _stable_evidence_id(label: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{label}:{hashlib.sha256(encoded).hexdigest()[:16]}"


def _report_dict(report: Any) -> dict[str, Any]:
    return report.to_dict() if hasattr(report, "to_dict") else dict(report)


def _alignment_diagnostic(alignment: dict[str, Any]) -> dict[str, Any]:
    value = alignment.get("full_model_test_code_diagnostic")
    return value if isinstance(value, dict) else {}


def _deferred_structure_findings(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostic = _alignment_diagnostic(alignment)
    findings = [
        item
        for item in diagnostic.get("actionable_findings") or []
        if isinstance(item, dict) and item.get("code") == "needs_structure_split"
    ]
    return sorted(findings, key=lambda item: str(item.get("surface_id") or item.get("path") or ""))


def _gap_counts(inventory: dict[str, Any]) -> dict[str, int]:
    raw = inventory.get("gap_class_counts") or {}
    return {str(key): int(value) for key, value in raw.items()}


def _unknown_gap_classes(inventory: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(set(_gap_counts(inventory)) - set(GAP_CLASS_STRATEGY)))


def _coverage_inventory_passes(inventory: dict[str, Any]) -> bool:
    counts = _gap_counts(inventory)
    hard_failures = {
        "runner_unparsed_or_unavailable",
        "runner_not_ok",
    }
    return (
        bool(inventory.get("sweep_ok"))
        and bool(inventory.get("alignment_ok"))
        and bool(inventory.get("source_audit_ok"))
        and not _unknown_gap_classes(inventory)
        and not (hard_failures & set(counts))
    )


def _test_gap_closure_passes(inventory: dict[str, Any]) -> bool:
    counts = _gap_counts(inventory)
    return (
        not _unknown_gap_classes(inventory)
        and "abstract_without_detected_ordinary_test_reference" not in counts
    )


def _alignment_accounting_passes(alignment: dict[str, Any]) -> bool:
    return (
        bool(alignment.get("alignment_ok") or alignment.get("ok"))
        and bool(alignment.get("source_audit_ok"))
        and bool(alignment.get("release_convergence_ok"))
        and bool(alignment.get("full_diagnostic_ok"))
    )


def _gap_class_cells(inventory: dict[str, Any]) -> tuple[LeafBoundaryMatrixCell, ...]:
    counts = _gap_counts(inventory)
    present_consumable = any(
        CURRENTLY_CONSUMABLE in (record.get("gap_classes") or [])
        for record in inventory.get("records") or []
        if isinstance(record, dict)
    )
    cells: list[LeafBoundaryMatrixCell] = []
    for gap_class, strategy in sorted(GAP_CLASS_STRATEGY.items()):
        if gap_class == CURRENTLY_CONSUMABLE:
            state = "present" if present_consumable else "absent"
            count = sum(
                1
                for record in inventory.get("records") or []
                if isinstance(record, dict) and CURRENTLY_CONSUMABLE in (record.get("gap_classes") or [])
            )
        else:
            count = counts.get(gap_class, 0)
            state = "present" if count else "absent"
        cells.append(
            LeafBoundaryMatrixCell(
                cell_id=f"gap_class:{gap_class}",
                input_case=f"gap_class={gap_class}",
                state_case="current_inventory",
                expected_outputs=(f"strategy:{strategy}", f"presence:{state}"),
                observed_outputs=(f"strategy:{strategy}", f"presence:{state}"),
                expected_next_states=("classified",),
                observed_next_states=("classified",),
                evidence_ids=("tests/test_flowpilot_full_model_test_gap_closure.py",),
                metadata={"count": count, "strategy": strategy},
            )
        )
    return tuple(cells)


def _alignment_cells(alignment: dict[str, Any]) -> tuple[LeafBoundaryMatrixCell, ...]:
    diagnostic = _alignment_diagnostic(alignment)
    checks = (
        ("alignment_ok", bool(alignment.get("alignment_ok") or alignment.get("ok"))),
        ("source_audit_ok", bool(alignment.get("source_audit_ok"))),
        ("full_diagnostic_ok", bool(alignment.get("full_diagnostic_ok"))),
        ("release_convergence_ok", bool(alignment.get("release_convergence_ok"))),
        ("unresolved_non_deferred_gap_count_zero", int(diagnostic.get("unresolved_non_deferred_gap_count") or 0) == 0),
    )
    cells: list[LeafBoundaryMatrixCell] = []
    for name, passed in checks:
        state = "passed" if passed else "failed"
        cells.append(
            LeafBoundaryMatrixCell(
                cell_id=f"alignment:{name}",
                input_case=f"alignment_check={name}",
                state_case="current_alignment_result",
                expected_outputs=(state,),
                observed_outputs=(state,),
                expected_next_states=("consumable",),
                observed_next_states=("consumable",),
                evidence_ids=("simulations/flowpilot_model_test_alignment_results.json",),
                evidence_status="passed" if passed else "failed",
                metadata={"check": name},
            )
        )
    return tuple(cells)


def _contract_exhaustion_result() -> dict[str, Any]:
    if DEFAULT_CONTRACT_EXHAUSTION_PATH.exists():
        return _read_json(DEFAULT_CONTRACT_EXHAUSTION_PATH)
    return contract_exhaustion_runner.run_checks()


def _contract_exhaustion_cells(report: dict[str, Any]) -> tuple[LeafBoundaryMatrixCell, ...]:
    passed = bool(report.get("ok"))
    required = report.get("required_cells") if isinstance(report.get("required_cells"), dict) else {}
    cells_payload = required.get("required_cells") if isinstance(required, dict) else []
    cells: list[LeafBoundaryMatrixCell] = []
    for cell in cells_payload:
        if not isinstance(cell, dict):
            continue
        cell_id = str(cell.get("cell_id") or "")
        family = str(cell.get("family") or "")
        mutation = str(cell.get("mutation_kind") or "")
        owner = str(cell.get("required_evidence_owner") or "")
        boundary = str(cell.get("confidence_boundary") or "")
        cells.append(
            LeafBoundaryMatrixCell(
                cell_id=f"contract_exhaustion:{cell_id}",
                input_case=f"family={family};mutation={mutation}",
                state_case=str(cell.get("contract_path") or family),
                expected_outputs=(f"owner:{owner}", f"boundary:{boundary}"),
                observed_outputs=(f"owner:{owner}", f"boundary:{boundary}"),
                expected_next_states=("owned",),
                observed_next_states=("owned",),
                evidence_ids=("simulations/flowpilot_contract_exhaustion_mesh_results.json",),
                evidence_status="passed" if passed else "failed",
                metadata={
                    "contract_family_id": str(cell.get("contract_family_id") or ""),
                    "contract_path": str(cell.get("contract_path") or ""),
                    "branch_kind": str(cell.get("branch_kind") or ""),
                },
            )
        )
    return tuple(cells)


def _cartesian_exhaustion_result() -> dict[str, Any]:
    if DEFAULT_CARTESIAN_EXHAUSTION_PATH.exists():
        return _read_json(DEFAULT_CARTESIAN_EXHAUSTION_PATH)
    return cartesian_exhaustion_runner.run_checks()


def _cartesian_exhaustion_cells(report: dict[str, Any]) -> tuple[LeafBoundaryMatrixCell, ...]:
    passed = bool(report.get("ok"))
    matrix = report.get("matrix") if isinstance(report.get("matrix"), dict) else {}
    cells_payload = matrix.get("required_cells") if isinstance(matrix, dict) else []
    cells: list[LeafBoundaryMatrixCell] = []
    for cell in cells_payload:
        if not isinstance(cell, dict):
            continue
        cell_id = str(cell.get("cell_id") or "")
        boundary = str(cell.get("boundary_id") or "")
        mutation = str(cell.get("mutation_kind") or "")
        context = str(cell.get("context") or "")
        consumer = str(cell.get("consumer") or "")
        reaction = str(cell.get("expected_reaction") or "")
        owner = str(cell.get("required_evidence_owner") or "")
        cells.append(
            LeafBoundaryMatrixCell(
                cell_id=f"cartesian_exhaustion:{cell_id}",
                input_case=f"boundary={boundary};mutation={mutation};context={context};consumer={consumer}",
                state_case=reaction,
                expected_outputs=(f"owner:{owner}", f"reaction:{reaction}"),
                observed_outputs=(f"owner:{owner}", f"reaction:{reaction}"),
                expected_next_states=("owned",),
                observed_next_states=("owned",),
                evidence_ids=("simulations/flowpilot_cartesian_control_plane_exhaustion_results.json",),
                evidence_status="passed" if passed else "failed",
                metadata={
                    "normal_repair_context": bool(cell.get("normal_repair_context")),
                    "glass_break_allowed": bool(cell.get("glass_break_allowed")),
                    "required_repair_command": str(cell.get("required_repair_command") or ""),
                },
            )
        )
    return tuple(cells)


def build_accounting_plan(inventory: dict[str, Any], alignment: dict[str, Any]) -> LayeredBoundaryProofPlan:
    """Build the green proof for the current coverage-accounting boundary."""

    contract_exhaustion = _contract_exhaustion_result()
    cartesian_exhaustion = _cartesian_exhaustion_result()
    inventory_evidence = _stable_evidence_id(
        "inventory",
        {
            "runner_count": inventory.get("runner_count"),
            "gap_class_counts": inventory.get("gap_class_counts"),
            "sweep_ok": inventory.get("sweep_ok"),
            "alignment_ok": inventory.get("alignment_ok"),
        },
    )
    closure_evidence = _stable_evidence_id(
        "test-gap-closure",
        {"gap_classes": sorted(_gap_counts(inventory)), "unknown": _unknown_gap_classes(inventory)},
    )
    alignment_evidence = _stable_evidence_id(
        "model-test-alignment",
        {
            "alignment_ok": alignment.get("alignment_ok") or alignment.get("ok"),
            "source_audit_ok": alignment.get("source_audit_ok"),
            "full_diagnostic_ok": alignment.get("full_diagnostic_ok"),
            "release_convergence_ok": alignment.get("release_convergence_ok"),
        },
    )
    contract_exhaustion_evidence = _stable_evidence_id(
        "contract-exhaustion",
        {
            "ok": contract_exhaustion.get("ok"),
            "cell_count": (contract_exhaustion.get("required_cells") or {}).get("cell_count")
            if isinstance(contract_exhaustion.get("required_cells"), dict)
            else None,
            "mutation_count": (contract_exhaustion.get("required_cells") or {}).get("mutation_count")
            if isinstance(contract_exhaustion.get("required_cells"), dict)
            else None,
        },
    )
    cartesian_exhaustion_evidence = _stable_evidence_id(
        "cartesian-control-plane-exhaustion",
        {
            "ok": cartesian_exhaustion.get("ok"),
            "full_product_count": (cartesian_exhaustion.get("matrix") or {}).get("full_product_count")
            if isinstance(cartesian_exhaustion.get("matrix"), dict)
            else None,
            "applicable_count": (cartesian_exhaustion.get("matrix") or {}).get("applicable_count")
            if isinstance(cartesian_exhaustion.get("matrix"), dict)
            else None,
        },
    )
    leaf_evidence = _stable_evidence_id(
        "leaf-boundary-accounting",
        {"gap_cells": [cell.cell_id for cell in _gap_class_cells(inventory)]},
    )

    return LayeredBoundaryProofPlan(
        proof_id="flowpilot-layered-boundary-accounting",
        parent_model_id="flowpilot-full-flowguard-coverage",
        claim_scope="coverage_accounting",
        rationale=(
            "This proof checks that FlowPilot coverage evidence is owned, classified, "
            "reattached to parent coverage, and leaf-matrixed for the inventory "
            "boundary. It does not claim production replay adapters or large runtime "
            "surfaces have finished finite semantic proof."
        ),
        parent_items=(
            ParentCoverageItem("enumerate_model_check_runners", owner_model_id="coverage_inventory"),
            ParentCoverageItem("classify_gap_classes", owner_model_id="coverage_inventory"),
            ParentCoverageItem("own_ordinary_test_strategy", owner_model_id="test_gap_closure"),
            ParentCoverageItem("keep_scoped_evidence_visible", owner_model_id="test_gap_closure"),
            ParentCoverageItem("consume_source_contract_alignment", owner_model_id="model_test_alignment"),
            ParentCoverageItem("release_convergence_accounting", owner_model_id="model_test_alignment"),
            ParentCoverageItem("consume_contract_exhaustion_mesh", owner_model_id="contract_exhaustion_mesh"),
            ParentCoverageItem("consume_cartesian_control_plane_exhaustion", owner_model_id="cartesian_control_plane_exhaustion"),
            ParentCoverageItem("prove_inventory_boundary_matrix", owner_model_id="leaf_boundary_accounting"),
            ParentCoverageItem("prove_contract_exhaustion_leaf_matrix", owner_model_id="contract_exhaustion_mesh"),
            ParentCoverageItem("prove_cartesian_control_plane_leaf_matrix", owner_model_id="cartesian_control_plane_exhaustion"),
            ParentCoverageItem(
                "production_replay_adapter_completion",
                owner_kind="out_of_scope",
                rationale="Tracked as scoped replay gap classes until production replay adapters exist.",
            ),
            ParentCoverageItem(
                "structuremesh_runtime_surface_split_completion",
                owner_kind="out_of_scope",
                rationale="Tracked by full diagnostic needs_structure_split findings until those surfaces are split.",
            ),
        ),
        child_contracts=(
            ChildProofContract(
                "coverage_inventory",
                evidence_id=inventory_evidence,
                evidence_status="passed" if _coverage_inventory_passes(inventory) else "failed",
                responsibilities=("enumerate_model_check_runners", "classify_gap_classes"),
                functions_owned=("run_flowpilot_full_model_coverage_inventory.build_inventory",),
                inputs_accepted=("coverage_sweep_result", "model_test_alignment_result", "test_corpus"),
                outputs_emitted=("runner_records", "gap_class_counts", "claim_boundary"),
                state_owned=("coverage_inventory_json",),
                contracts_out=("full_model_coverage_inventory",),
            ),
            ChildProofContract(
                "test_gap_closure",
                evidence_id=closure_evidence,
                evidence_status="passed" if _test_gap_closure_passes(inventory) else "failed",
                responsibilities=("own_ordinary_test_strategy", "keep_scoped_evidence_visible"),
                functions_owned=("tests/test_flowpilot_full_model_test_gap_closure.py",),
                inputs_accepted=("gap_class_counts", "runner_records"),
                outputs_emitted=("closure_strategy", "scoped_boundary_visible"),
                contracts_out=("ordinary_test_gap_closure",),
            ),
            ChildProofContract(
                "model_test_alignment",
                evidence_id=alignment_evidence,
                evidence_status="passed" if _alignment_accounting_passes(alignment) else "failed",
                responsibilities=("consume_source_contract_alignment", "release_convergence_accounting"),
                functions_owned=("run_flowpilot_model_test_alignment_checks",),
                inputs_accepted=("model_obligations", "source_contracts", "ordinary_tests"),
                outputs_emitted=("alignment_ok", "source_audit_ok", "release_convergence_ok"),
                contracts_out=("model_test_alignment",),
            ),
            ChildProofContract(
                "contract_exhaustion_mesh",
                evidence_id=contract_exhaustion_evidence,
                evidence_status="passed" if contract_exhaustion.get("ok") else "failed",
                responsibilities=("consume_contract_exhaustion_mesh", "prove_contract_exhaustion_leaf_matrix"),
                functions_owned=("run_flowpilot_contract_exhaustion_mesh_checks.run_checks",),
                inputs_accepted=(
                    "packet_result_contracts",
                    "control_plane_required_paths",
                    "synthetic_mutation_kinds",
                    "historical_failure_families",
                ),
                outputs_emitted=(
                    "required_contract_exhaustion_cells",
                    "hazard_findings",
                    "required_child_suite_owners",
                    "test_mesh_owner_status",
                ),
                state_owned=("flowpilot_contract_exhaustion_mesh_results",),
                contracts_out=("contract_exhaustion_mesh",),
                is_leaf=True,
                leaf_matrix_id="flowpilot-contract-exhaustion-matrix",
            ),
            ChildProofContract(
                "cartesian_control_plane_exhaustion",
                evidence_id=cartesian_exhaustion_evidence,
                evidence_status="passed" if cartesian_exhaustion.get("ok") else "failed",
                responsibilities=(
                    "consume_cartesian_control_plane_exhaustion",
                    "prove_cartesian_control_plane_leaf_matrix",
                ),
                functions_owned=("run_flowpilot_cartesian_control_plane_exhaustion_checks.run_checks",),
                inputs_accepted=(
                    "control_plane_boundaries",
                    "mutation_alphabet",
                    "handoff_contexts",
                    "downstream_consumers",
                    "contract_exhaustion_bridge_cells",
                    "historical_failure_bridge_cells",
                ),
                outputs_emitted=(
                    "full_product_count",
                    "required_cartesian_cells",
                    "skipped_cartesian_cells",
                    "required_child_suite_owners",
                    "test_mesh_owner_status",
                ),
                state_owned=("flowpilot_cartesian_control_plane_exhaustion_results",),
                contracts_out=("cartesian_control_plane_exhaustion",),
                is_leaf=True,
                leaf_matrix_id="flowpilot-cartesian-control-plane-matrix",
            ),
            ChildProofContract(
                "leaf_boundary_accounting",
                evidence_id=leaf_evidence,
                responsibilities=("prove_inventory_boundary_matrix",),
                functions_owned=("flowpilot_layered_boundary_proof.build_accounting_plan",),
                inputs_accepted=("gap_class", "alignment_check"),
                outputs_emitted=("strategy", "presence", "consumable"),
                state_owned=("current_inventory", "current_alignment_result"),
                contracts_out=("layered_boundary_accounting",),
                is_leaf=True,
                leaf_matrix_id="flowpilot-inventory-boundary-matrix",
            ),
        ),
        reattachment_proofs=(
            ChildReattachmentProof(
                "coverage_inventory",
                consumed_evidence_id=inventory_evidence,
                expected_inputs=("coverage_sweep_result", "model_test_alignment_result", "test_corpus"),
                expected_outputs=("runner_records", "gap_class_counts", "claim_boundary"),
                expected_state_owned=("coverage_inventory_json",),
                expected_contracts_out=("full_model_coverage_inventory",),
            ),
            ChildReattachmentProof(
                "test_gap_closure",
                consumed_evidence_id=closure_evidence,
                expected_inputs=("gap_class_counts", "runner_records"),
                expected_outputs=("closure_strategy", "scoped_boundary_visible"),
                expected_contracts_out=("ordinary_test_gap_closure",),
            ),
            ChildReattachmentProof(
                "model_test_alignment",
                consumed_evidence_id=alignment_evidence,
                expected_inputs=("model_obligations", "source_contracts", "ordinary_tests"),
                expected_outputs=("alignment_ok", "source_audit_ok", "release_convergence_ok"),
                expected_contracts_out=("model_test_alignment",),
            ),
            ChildReattachmentProof(
                "contract_exhaustion_mesh",
                consumed_evidence_id=contract_exhaustion_evidence,
                expected_inputs=(
                    "packet_result_contracts",
                    "control_plane_required_paths",
                    "synthetic_mutation_kinds",
                    "historical_failure_families",
                ),
                expected_outputs=(
                    "required_contract_exhaustion_cells",
                    "hazard_findings",
                    "required_child_suite_owners",
                    "test_mesh_owner_status",
                ),
                expected_state_owned=("flowpilot_contract_exhaustion_mesh_results",),
                expected_contracts_out=("contract_exhaustion_mesh",),
            ),
            ChildReattachmentProof(
                "cartesian_control_plane_exhaustion",
                consumed_evidence_id=cartesian_exhaustion_evidence,
                expected_inputs=(
                    "control_plane_boundaries",
                    "mutation_alphabet",
                    "handoff_contexts",
                    "downstream_consumers",
                    "contract_exhaustion_bridge_cells",
                    "historical_failure_bridge_cells",
                ),
                expected_outputs=(
                    "full_product_count",
                    "required_cartesian_cells",
                    "skipped_cartesian_cells",
                    "required_child_suite_owners",
                    "test_mesh_owner_status",
                ),
                expected_state_owned=("flowpilot_cartesian_control_plane_exhaustion_results",),
                expected_contracts_out=("cartesian_control_plane_exhaustion",),
            ),
            ChildReattachmentProof(
                "leaf_boundary_accounting",
                consumed_evidence_id=leaf_evidence,
                expected_inputs=("gap_class", "alignment_check"),
                expected_outputs=("strategy", "presence", "consumable"),
                expected_state_owned=("current_inventory", "current_alignment_result"),
                expected_contracts_out=("layered_boundary_accounting",),
            ),
        ),
        leaf_matrices=(
            LeafBoundaryMatrix(
                "leaf_boundary_accounting",
                matrix_id="flowpilot-inventory-boundary-matrix",
                expected_cell_ids=tuple(
                    [f"gap_class:{gap_class}" for gap_class in sorted(GAP_CLASS_STRATEGY)]
                    + [
                        "alignment:alignment_ok",
                        "alignment:source_audit_ok",
                        "alignment:full_diagnostic_ok",
                        "alignment:release_convergence_ok",
                        "alignment:unresolved_non_deferred_gap_count_zero",
                    ]
                ),
                cells=_gap_class_cells(inventory) + _alignment_cells(alignment),
                rationale=(
                    "The leaf here is the coverage-accounting adapter. Every possible "
                    "inventory gap class and alignment gate has an explicit current cell."
                ),
            ),
            LeafBoundaryMatrix(
                "contract_exhaustion_mesh",
                matrix_id="flowpilot-contract-exhaustion-matrix",
                expected_cell_ids=tuple(
                    f"contract_exhaustion:{cell['cell_id']}"
                    for cell in contract_exhaustion_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
                ),
                cells=_contract_exhaustion_cells(contract_exhaustion),
                rationale=(
                    "Every current packet/result/control-plane contract-exhaustion cell "
                    "generated from the live contract tables must have an explicit owner, "
                    "boundary, and current evidence path."
                ),
            ),
            LeafBoundaryMatrix(
                "cartesian_control_plane_exhaustion",
                matrix_id="flowpilot-cartesian-control-plane-matrix",
                expected_cell_ids=tuple(
                    f"cartesian_exhaustion:{cell['cell_id']}"
                    for cell in cartesian_exhaustion_model.REQUIRED_CARTESIAN_CELLS
                ),
                cells=_cartesian_exhaustion_cells(cartesian_exhaustion),
                rationale=(
                    "Every applicable declared control-plane boundary, mutation, "
                    "context, and consumer cell must have an explicit owner, "
                    "repair oracle, and current evidence path."
                ),
            ),
        ),
    )


def _requirement_blockers(inventory: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    counts = _gap_counts(inventory)
    deferred = _deferred_structure_findings(alignment)
    return {
        "blocking_gap_counts": {
            key: counts[key]
            for key in REQUIREMENT_BLOCKING_GAP_CLASSES
            if counts.get(key, 0) > 0
        },
        "deferred_structure_split_count": len(deferred),
        "deferred_structure_split_surfaces": [
            {
                "surface_id": str(item.get("surface_id") or ""),
                "path": str(item.get("path") or ""),
                "message": str(item.get("message") or ""),
            }
            for item in deferred
        ],
        "alignment_full_coverage_ok": bool(alignment.get("full_coverage_ok")),
    }


def _requirement_outputs(blockers: dict[str, Any]) -> tuple[str, ...]:
    outputs = []
    if blockers["blocking_gap_counts"]:
        outputs.append("inventory_blocking_gaps_present")
    if blockers["deferred_structure_split_count"]:
        outputs.append("structure_split_backlog_present")
    if not blockers["alignment_full_coverage_ok"]:
        outputs.append("alignment_full_coverage_false")
    if not outputs:
        outputs.append("full_leaf_cartesian_ready")
    else:
        outputs.append("full_leaf_cartesian_blocked")
    return tuple(sorted(outputs))


def _requirement_leaf_cells(inventory: dict[str, Any], alignment: dict[str, Any]) -> tuple[LeafBoundaryMatrixCell, ...]:
    blockers = _requirement_blockers(inventory, alignment)
    cells: list[LeafBoundaryMatrixCell] = []
    for gap_class in REQUIREMENT_BLOCKING_GAP_CLASSES:
        count = blockers["blocking_gap_counts"].get(gap_class, 0)
        ok = count == 0
        observed = "absent" if ok else "present"
        cells.append(
            LeafBoundaryMatrixCell(
                cell_id=f"requirement:no_{gap_class}",
                input_case=f"runtime_gap_class={gap_class}",
                state_case="current_inventory",
                expected_outputs=("absent",),
                observed_outputs=(observed,),
                expected_next_states=("full_leaf_candidate",),
                observed_next_states=("full_leaf_candidate" if ok else "must_split_or_repair",),
                evidence_ids=("simulations/flowpilot_full_model_coverage_inventory_results.json",),
                evidence_status="passed" if ok else "failed",
                metadata={"count": count},
            )
        )
    structure_ok = blockers["deferred_structure_split_count"] == 0
    cells.append(
        LeafBoundaryMatrixCell(
            cell_id="requirement:no_deferred_structure_split",
            input_case="runtime_contract_surface=all",
            state_case="full_diagnostic",
            expected_outputs=("absent",),
            observed_outputs=("absent" if structure_ok else "present",),
            expected_next_states=("full_leaf_candidate",),
            observed_next_states=("full_leaf_candidate" if structure_ok else "must_split_or_repair",),
            evidence_ids=("simulations/flowpilot_model_test_alignment_results.json",),
            evidence_status="passed" if structure_ok else "failed",
            metadata={"count": blockers["deferred_structure_split_count"]},
        )
    )
    full_coverage_ok = blockers["alignment_full_coverage_ok"]
    cells.append(
        LeafBoundaryMatrixCell(
            cell_id="requirement:alignment_full_coverage_ok",
            input_case="alignment_full_coverage",
            state_case="current_alignment_result",
            expected_outputs=("true",),
            observed_outputs=("true" if full_coverage_ok else "false",),
            expected_next_states=("full_leaf_candidate",),
            observed_next_states=("full_leaf_candidate" if full_coverage_ok else "must_split_or_repair",),
            evidence_ids=("simulations/flowpilot_model_test_alignment_results.json",),
            evidence_status="passed" if full_coverage_ok else "failed",
        )
    )
    return tuple(cells)


def build_requirement_plan(inventory: dict[str, Any], alignment: dict[str, Any]) -> LayeredBoundaryProofPlan:
    """Build the stricter plan for full leaf Cartesian readiness."""

    blockers = _requirement_blockers(inventory, alignment)
    outputs = _requirement_outputs(blockers)
    ready = outputs == ("full_leaf_cartesian_ready",)
    evidence_id = _stable_evidence_id("full-leaf-requirement", blockers)
    return LayeredBoundaryProofPlan(
        proof_id="flowpilot-full-leaf-cartesian-requirement",
        parent_model_id="flowpilot-full-flowguard-coverage",
        claim_scope="full_leaf_cartesian",
        parent_items=(
            ParentCoverageItem(
                "full_leaf_cartesian_for_all_runtime_contracts",
                owner_model_id="full_leaf_cartesian_requirement",
            ),
        ),
        child_contracts=(
            ChildProofContract(
                "full_leaf_cartesian_requirement",
                evidence_id=evidence_id,
                evidence_status="passed" if ready else "failed",
                responsibilities=("full_leaf_cartesian_for_all_runtime_contracts",),
                functions_owned=("flowpilot_layered_boundary_proof.build_requirement_plan",),
                inputs_accepted=("runtime_gap_class", "runtime_contract_surface", "alignment_full_coverage"),
                outputs_emitted=outputs,
                state_owned=("current_inventory", "full_diagnostic"),
                contracts_out=("full_leaf_cartesian_requirement",),
                is_leaf=True,
                leaf_matrix_id="flowpilot-full-leaf-cartesian-requirement-matrix",
                rationale=(
                    "This stricter child is green only when no scoped replay/skipped "
                    "evidence, no hard model gaps, no deferred StructureMesh split, "
                    "and alignment full_coverage_ok is true."
                ),
            ),
        ),
        reattachment_proofs=(
            ChildReattachmentProof(
                "full_leaf_cartesian_requirement",
                consumed_evidence_id=evidence_id,
                expected_inputs=("runtime_gap_class", "runtime_contract_surface", "alignment_full_coverage"),
                expected_outputs=outputs,
                expected_state_owned=("current_inventory", "full_diagnostic"),
                expected_contracts_out=("full_leaf_cartesian_requirement",),
            ),
        ),
        leaf_matrices=(
            LeafBoundaryMatrix(
                "full_leaf_cartesian_requirement",
                matrix_id="flowpilot-full-leaf-cartesian-requirement-matrix",
                expected_cell_ids=tuple(cell.cell_id for cell in _requirement_leaf_cells(inventory, alignment)),
                cells=_requirement_leaf_cells(inventory, alignment),
                complete=True,
                finite=True,
                split_required=not ready,
                scoped_exemption="" if ready else "remaining gaps must be repaired or split before full leaf proof",
                rationale=(
                    "Each cell states whether a blocker class is absent. Any present "
                    "blocker prevents claiming whole-system full leaf Cartesian proof."
                ),
            ),
        ),
    )


def build_report(inventory: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    accounting_plan = build_accounting_plan(inventory, alignment)
    requirement_plan = build_requirement_plan(inventory, alignment)
    accounting_report = review_layered_boundary_proof(accounting_plan)
    requirement_report = review_layered_boundary_proof(requirement_plan)
    blockers = _requirement_blockers(inventory, alignment)
    return {
        "schema_version": "flowpilot.layered_boundary_proof.v1",
        "result_type": "flowpilot_layered_boundary_proof",
        "ok": accounting_report.ok,
        "layered_accounting_ok": accounting_report.ok,
        "full_leaf_cartesian_ok": requirement_report.ok,
        "requirement_blockers": blockers,
        "accounting_decision": accounting_report.decision,
        "requirement_decision": requirement_report.decision,
        "accounting_report": _report_dict(accounting_report),
        "requirement_report": _report_dict(requirement_report),
        "claim_boundary": (
            "layered_accounting_ok means FlowPilot has current parent/child coverage "
            "accounting and leaf matrix proof for the inventory boundary. "
            "full_leaf_cartesian_ok is stricter and remains false while scoped replay, "
            "skipped evidence, hard runner findings, deferred StructureMesh split, or "
            "alignment full_coverage_ok=false remain."
        ),
    }


def load_inputs(inventory_path: Path, alignment_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if inventory_path.exists():
        inventory = _read_json(inventory_path)
    else:
        inventory = coverage_inventory.build_inventory()
    alignment = _read_json(alignment_path)
    return inventory, alignment


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-json", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--alignment-json", type=Path, default=DEFAULT_ALIGNMENT_PATH)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args(list(argv) if argv is not None else None)

    inventory, alignment = load_inputs(args.inventory_json, args.alignment_json)
    report = build_report(inventory, alignment)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["layered_accounting_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
