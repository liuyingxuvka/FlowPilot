"""Source-contract FlowPilot model-test alignment plans and audits."""

from __future__ import annotations

from typing import Any

from flowguard import (
    audit_python_code_contracts,
    audit_python_test_assertions,
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

def build_source_contract_alignment_plan() -> ModelTestAlignmentPlan:
    """Build the AST-audited model/code/test contract subset."""

    return ModelTestAlignmentPlan(
        model_id="model_test_code_source_contracts",
        obligations=source_obligations(),
        code_contracts=source_code_contracts(),
        test_evidence=source_test_evidence(),
        require_code_contracts=True,
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
    findings = [
        {"layer": "model_code_test_alignment", **finding}
        for finding in alignment_report.to_dict()["findings"]
    ]
    findings.extend(
        {"layer": "python_source_contract_audit", **finding}
        for finding in source_report.to_dict()["findings"]
    )
    return {
        "ok": alignment_report.ok and source_report.ok,
        "model_id": plan.model_id,
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "finding_count": len(findings),
        "finding_counts": _finding_counts(findings),
        "findings": findings,
        "plan": plan.to_dict(),
        "alignment_report": alignment_report.to_dict(),
        "source_audit_report": source_report.to_dict(),
    }
