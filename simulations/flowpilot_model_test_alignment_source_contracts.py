"""Source-contract FlowPilot model-test alignment plans and audits."""

from __future__ import annotations

from typing import Any

from flowguard import (
    audit_python_code_contracts,
    audit_python_test_assertions,
    review_code_boundary_conformance,
    review_model_test_alignment,
    review_python_contract_source_audit,
)

from flowpilot_model_test_alignment_common import *

from flowpilot_model_test_alignment_source_code_contracts import source_code_contracts
from flowpilot_model_test_alignment_source_obligations import (
    _source_obligation,
    source_obligations,
)
from flowpilot_model_test_alignment_source_test_evidence import source_test_evidence


def source_boundary_contracts() -> tuple[CodeBoundaryContract, ...]:
    """Return runtime-observed code boundaries for finite FlowPilot surfaces."""

    return (
        CodeBoundaryContract(
            boundary_id="controller_aside.metadata_only_runtime_boundary",
            code_contract_id="controller_aside.build",
            model_obligation_id="controller_aside.metadata_only_boundary",
            allowed_inputs=("valid_status_text",),
            rejected_inputs=("blank_text", "too_many_lines", "too_long_text"),
            allowed_outputs=("metadata_only_controller_aside", "none"),
            allowed_error_paths=(
                "ValueError: non-empty lines or fewer",
                "ValueError: characters or fewer",
            ),
            exact=True,
            input_gate_required=True,
            required_observation_ids=(
                "boundary.controller_aside.valid_status",
                "boundary.controller_aside.blank_text",
                "boundary.controller_aside.too_many_lines",
                "boundary.controller_aside.too_long_text",
            ),
        ),
        CodeBoundaryContract(
            boundary_id="material_artifact_map.index_only_runtime_boundary",
            code_contract_id="material_artifact_map.navigation_status",
            model_obligation_id="material_artifact_map.index_only_boundary",
            allowed_inputs=(
                "ordinary_project_artifacts_with_existing_map",
                "no_existing_map",
                "existing_noncurrent_or_unsafe_map",
            ),
            allowed_outputs=(
                "index_only_material_artifact_map",
                "map_absent_nonblocking",
                "map_noncurrent_or_unsafe_omitted",
            ),
            exact=True,
            input_gate_required=False,
            required_observation_ids=(
                "boundary.material_artifact_map.index_only",
                "boundary.material_artifact_map.absent_nonblocking",
                "boundary.material_artifact_map.noncurrent_omitted",
            ),
        ),
    )


def source_boundary_observations() -> tuple[CodeBoundaryObservation, ...]:
    """Return runtime observations produced by ordinary boundary tests."""

    return (
        CodeBoundaryObservation(
            observation_id="boundary.controller_aside.valid_status",
            boundary_id="controller_aside.metadata_only_runtime_boundary",
            input_case="valid_status_text",
            accepted=True,
            observed_output="metadata_only_controller_aside",
            evidence_id="source.controller_aside.boundary",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.controller_aside.blank_text",
            boundary_id="controller_aside.metadata_only_runtime_boundary",
            input_case="blank_text",
            accepted=False,
            observed_output="none",
            evidence_id="source.controller_aside.boundary",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.controller_aside.too_many_lines",
            boundary_id="controller_aside.metadata_only_runtime_boundary",
            input_case="too_many_lines",
            accepted=False,
            observed_error_path="ValueError: non-empty lines or fewer",
            evidence_id="source.controller_aside.boundary",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.controller_aside.too_long_text",
            boundary_id="controller_aside.metadata_only_runtime_boundary",
            input_case="too_long_text",
            accepted=False,
            observed_error_path="ValueError: characters or fewer",
            evidence_id="source.controller_aside.boundary",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.material_artifact_map.index_only",
            boundary_id="material_artifact_map.index_only_runtime_boundary",
            input_case="ordinary_project_artifacts_with_existing_map",
            accepted=True,
            observed_output="index_only_material_artifact_map",
            evidence_id="source.material_artifact_map.boundary",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.material_artifact_map.absent_nonblocking",
            boundary_id="material_artifact_map.index_only_runtime_boundary",
            input_case="no_existing_map",
            accepted=True,
            observed_output="map_absent_nonblocking",
            evidence_id="source.material_artifact_map.absence",
        ),
        CodeBoundaryObservation(
            observation_id="boundary.material_artifact_map.noncurrent_omitted",
            boundary_id="material_artifact_map.index_only_runtime_boundary",
            input_case="existing_noncurrent_or_unsafe_map",
            accepted=True,
            observed_output="map_noncurrent_or_unsafe_omitted",
            evidence_id="source.material_artifact_map.noncurrent_navigation_omitted",
        ),
    )


def build_source_contract_alignment_plan() -> ModelTestAlignmentPlan:
    """Build the AST-audited model/code/test contract subset."""

    return ModelTestAlignmentPlan(
        model_id="model_test_code_source_contracts",
        obligations=source_obligations(),
        code_contracts=source_code_contracts(),
        boundary_contracts=source_boundary_contracts(),
        boundary_observations=source_boundary_observations(),
        test_evidence=source_test_evidence(),
    )


def _read_sources_for_plan(plan: ModelTestAlignmentPlan) -> dict[str, str]:
    paths = {contract.path for contract in plan.code_contracts}
    paths.update(evidence.path for evidence in plan.test_evidence)
    return {path: (ROOT / path).read_text(encoding="utf-8") for path in sorted(paths)}


def _source_contract_plan_report() -> dict[str, Any]:
    plan = build_source_contract_alignment_plan()
    alignment_report = review_model_test_alignment(plan)
    source_by_path = _read_sources_for_plan(plan)
    code_evidence = audit_python_code_contracts(plan.code_contracts, source_by_path)
    test_assertions = audit_python_test_assertions(plan.test_evidence, plan.code_contracts, source_by_path)
    source_report = review_python_contract_source_audit(
        plan.code_contracts,
        plan.test_evidence,
        code_evidence,
        test_assertions,
    )
    boundary_report = review_code_boundary_conformance(
        plan.boundary_contracts,
        plan.boundary_observations,
        plan.code_contracts,
    )
    findings = [
        {"layer": "model_code_test_alignment", **finding}
        for finding in alignment_report.to_dict()["findings"]
    ]
    findings.extend(
        {"layer": "python_source_contract_audit", **finding}
        for finding in source_report.to_dict()["findings"]
    )
    findings.extend(
        {"layer": "code_boundary_conformance", **finding}
        for finding in boundary_report.to_dict()["findings"]
    )
    return {
        "ok": alignment_report.ok and source_report.ok and boundary_report.ok,
        "model_id": plan.model_id,
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "finding_count": len(findings),
        "finding_counts": _finding_counts(findings),
        "findings": findings,
        "plan": plan.to_dict(),
        "alignment_report": alignment_report.to_dict(),
        "source_audit_report": source_report.to_dict(),
        "boundary_report": boundary_report.to_dict(),
    }
