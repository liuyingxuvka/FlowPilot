"""Run FlowGuard Model-Test Alignment checks for major FlowPilot families.

This runner is intentionally read-only. It does not execute the referenced
tests or long parent FlowGuard checks; it reviews declared model obligations
against ordinary test evidence by using FlowGuard's Model-Test Alignment API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from flowguard import (
    CodeContract,
    ModelTestAlignmentPlan,
    TestEvidence,
    audit_python_code_contracts,
    audit_python_test_assertions,
    review_python_contract_source_audit,
    review_model_test_alignment,
)

from flowpilot_model_test_alignment_common import (
    FULL_DIAGNOSTIC_BOUNDARY,
    SOURCE_AUDIT_BOUNDARY,
)
from flowpilot_model_test_alignment_family_plans import build_alignment_plan_entries
from flowpilot_model_test_alignment_source_contracts import (
    build_source_contract_alignment_plan,
    _source_contract_plan_report,
)
from flowpilot_model_test_alignment_known_bad import (
    _known_bad_cases,
    _source_known_bad_cases,
)
from flowpilot_model_test_alignment_diagnostics import (
    build_full_model_test_code_diagnostic,
    _finding_counts,
)
from flowpilot_packet_result_family_parity_model import build_report as build_packet_result_family_parity_report
from flowpilot_similarity_convergence_model import build_report as build_similarity_convergence_report

def _plan_report(entry: dict[str, Any]) -> dict[str, Any]:
    plan: ModelTestAlignmentPlan = entry["plan"]
    report = review_model_test_alignment(plan)
    findings = report.to_dict()["findings"]
    progress_lines: list[str] = []
    for run in plan.runtime_path_runs:
        progress_lines.extend(run.format_progress_lines().splitlines())
    return {
        "family": entry["family"],
        "model_id": plan.model_id,
        "ok": report.ok,
        "decision": report.decision,
        "finding_count": len(report.findings),
        "finding_counts": _finding_counts(findings),
        "model_checks": entry["model_checks"],
        "coverage_boundary": entry["coverage_boundary"],
        "runtime_path_summary": {
            "required": plan.require_runtime_path_evidence,
            "runtime_node_contract_count": len(plan.runtime_node_contracts),
            "runtime_path_run_count": len(plan.runtime_path_runs),
            "runtime_observation_count": len(plan.runtime_node_observations)
            + sum(len(run.observations) for run in plan.runtime_path_runs),
            "progress_line_count": len(progress_lines),
            "progress_lines": progress_lines,
        },
        "plan": plan.to_dict(),
        "report": report.to_dict(),
    }


def _known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    plan: ModelTestAlignmentPlan = case["plan"]
    report = review_model_test_alignment(plan)
    finding_codes = sorted({finding.code for finding in report.findings})
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": (not report.ok) and expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "plan": plan.to_dict(),
        "report": report.to_dict(),
    }


def _source_known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    code_contracts: Sequence[CodeContract] = case["code_contracts"]
    test_evidence: Sequence[TestEvidence] = case["test_evidence"]
    code_evidence = audit_python_code_contracts(code_contracts, case["source_by_path"])
    test_assertions = audit_python_test_assertions(
        test_evidence,
        code_contracts,
        case["source_by_path"],
    )
    report = review_python_contract_source_audit(
        code_contracts,
        test_evidence,
        code_evidence,
        test_assertions,
    )
    finding_codes = sorted({finding.code for finding in report.findings})
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": (not report.ok) and expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "code_contracts": [contract.to_dict() for contract in code_contracts],
        "test_evidence": [evidence.to_dict() for evidence in test_evidence],
        "report": report.to_dict(),
    }


def build_report() -> dict[str, Any]:
    per_plan = [_plan_report(entry) for entry in build_alignment_plan_entries()]
    known_bad = [_known_bad_report(case) for case in _known_bad_cases()]
    source_contract_plan = _source_contract_plan_report()
    source_known_bad = [
        _source_known_bad_report(case) for case in _source_known_bad_cases()
    ]
    full_diagnostic = build_full_model_test_code_diagnostic()
    packet_result_family_parity = build_packet_result_family_parity_report()
    similarity_convergence = build_similarity_convergence_report()
    findings: list[dict[str, Any]] = []
    for plan in per_plan:
        for finding in plan["report"]["findings"]:
            findings.append(
                {
                    "family": plan["family"],
                    "model_id": plan["model_id"],
                    **finding,
                }
            )
    findings.extend(source_contract_plan["findings"])
    alignment_ok = all(plan["ok"] for plan in per_plan)
    known_bad_ok = all(case["ok"] for case in known_bad)
    source_audit_ok = source_contract_plan["ok"]
    source_known_bad_ok = all(case["ok"] for case in source_known_bad)
    full_diagnostic_ok = full_diagnostic["ok"]
    packet_result_family_parity_ok = packet_result_family_parity["ok"]
    similarity_convergence_ok = similarity_convergence["ok"]
    return {
        "ok": alignment_ok and known_bad_ok and source_audit_ok and source_known_bad_ok and full_diagnostic_ok and packet_result_family_parity_ok and similarity_convergence_ok,
        "result_type": "flowpilot_model_test_alignment",
        "alignment_ok": alignment_ok,
        "known_bad_ok": known_bad_ok,
        "source_audit_ok": source_audit_ok,
        "source_known_bad_ok": source_known_bad_ok,
        "full_diagnostic_ok": full_diagnostic_ok,
        "packet_result_family_parity_ok": packet_result_family_parity_ok,
        "similarity_convergence_ok": similarity_convergence_ok,
        "full_coverage_ok": full_diagnostic["full_coverage_ok"],
        "release_convergence_ok": full_diagnostic["release_convergence_ok"],
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "full_diagnostic_boundary": FULL_DIAGNOSTIC_BOUNDARY,
        "plan_count": len(per_plan),
        "families": [plan["family"] for plan in per_plan],
        "findings": findings,
        "finding_counts": _finding_counts(findings),
        "per_plan": per_plan,
        "source_contract_plan": source_contract_plan,
        "packet_result_family_parity": packet_result_family_parity,
        "similarity_convergence": similarity_convergence,
        "full_model_test_code_diagnostic": full_diagnostic,
        "known_bad_sanity_checks": known_bad,
        "source_known_bad_sanity_checks": source_known_bad,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for writing the JSON result payload.",
    )
    args = parser.parse_args(argv)

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
