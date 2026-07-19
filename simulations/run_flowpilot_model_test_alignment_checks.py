"""Run FlowGuard Model-Test Alignment checks for major FlowPilot families.

This runner is intentionally read-only. It does not execute the referenced
tests or long parent FlowGuard checks; it reviews declared model obligations
against ordinary test evidence by using FlowGuard's Model-Test Alignment API.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
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

import flowpilot_model_test_alignment_common as alignment_common
from flowpilot_model_test_alignment_common import (
    FULL_DIAGNOSTIC_BOUNDARY,
    SOURCE_AUDIT_BOUNDARY,
)
from flowpilot_model_test_alignment_family_plans import (
    CURRENT_CARTESIAN_RISK_SHARD_OWNERS,
    MTA_RUNTIME_PATH_AUTHORITY,
    build_alignment_plan_entries,
)
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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.compile_flowpilot_acceptance_testmesh_evidence import source_fingerprint
from simulations.flowpilot_evidence_truth import load_manifest, proof_bundle_report

RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_model_test_alignment_results.json"


def _single_mta_evidence_owner_bundle(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Keep the dedicated MTA owner authoritative for each evidence subject."""

    owners = bundle.get("owners")
    if not isinstance(owners, dict):
        return bundle
    dedicated_by_evidence_id: dict[str, list[str]] = {}
    for owner_id, owner_row in owners.items():
        if not str(owner_id).startswith("mta_evidence_"):
            continue
        identity = (
            owner_row.get("identity")
            if isinstance(owner_row, dict)
            else None
        )
        evidence_ids = (
            identity.get("covered_evidence_ids")
            if isinstance(identity, dict)
            else None
        )
        if not isinstance(evidence_ids, list):
            continue
        for evidence_id in evidence_ids:
            dedicated_by_evidence_id.setdefault(str(evidence_id), []).append(
                str(owner_id)
            )
    singular = {
        evidence_id: owner_ids[0]
        for evidence_id, owner_ids in dedicated_by_evidence_id.items()
        if len(owner_ids) == 1
    }
    if not singular:
        return bundle
    normalized = copy.deepcopy(bundle)
    normalized_owners = normalized["owners"]
    for owner_id, owner_row in normalized_owners.items():
        identity = (
            owner_row.get("identity")
            if isinstance(owner_row, dict)
            else None
        )
        evidence_ids = (
            identity.get("covered_evidence_ids")
            if isinstance(identity, dict)
            else None
        )
        if not isinstance(evidence_ids, list):
            continue
        identity["covered_evidence_ids"] = [
            evidence_id
            for evidence_id in evidence_ids
            if singular.get(str(evidence_id), str(owner_id)) == str(owner_id)
        ]
    return normalized


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


def _declaration_report(entry: dict[str, Any]) -> dict[str, Any]:
    plan: ModelTestAlignmentPlan = entry["plan"]
    obligations = {item.obligation_id for item in plan.obligations}
    contract_ids = {item.code_contract_id for item in plan.code_contracts}
    evidence_ids = {item.evidence_id for item in plan.test_evidence}
    covered_by_contract = {
        obligation_id
        for contract in plan.code_contracts
        for obligation_id in contract.implements_obligations
    }
    covered_by_test = {
        obligation_id
        for evidence in plan.test_evidence
        for obligation_id in evidence.covered_obligations
    }
    missing_paths = sorted(
        {
            path
            for path in (
                *(contract.path for contract in plan.code_contracts),
                *(evidence.path for evidence in plan.test_evidence),
            )
            if path and not (REPO_ROOT / path).exists()
        }
    )
    failures = []
    if len(obligations) != len(plan.obligations):
        failures.append("duplicate_obligation_id")
    if len(contract_ids) != len(plan.code_contracts):
        failures.append("duplicate_code_contract_id")
    if len(evidence_ids) != len(plan.test_evidence):
        failures.append("duplicate_test_evidence_id")
    if obligations - covered_by_contract:
        failures.append("obligation_missing_code_contract_declaration")
    if obligations - covered_by_test:
        failures.append("obligation_missing_test_evidence_declaration")
    if missing_paths:
        failures.append("declared_source_path_missing")
    return {
        "ok": not failures,
        "family": entry["family"],
        "model_id": plan.model_id,
        "failures": failures,
        "missing_paths": missing_paths,
        "obligation_count": len(plan.obligations),
        "code_contract_count": len(plan.code_contracts),
        "test_evidence_count": len(plan.test_evidence),
        "evidence_status": "not_run",
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


def build_report(
    *,
    evidence_manifest: dict[str, Any] | None = None,
    declaration_only: bool = False,
    evidence_scope: str = "routine",
) -> dict[str, Any]:
    bundle = proof_bundle_report(
        evidence_manifest,
        expected_source_fingerprint=source_fingerprint(),
        required_scope=evidence_scope,
    ) if not declaration_only else {
        "ok": False,
        "selected_count": 0,
        "executed_count": 0,
        "test_count": 0,
        "failures": ["declaration_only_execution_not_run"],
    }
    if not declaration_only:
        bundle = _single_mta_evidence_owner_bundle(bundle)
    alignment_common.configure_execution_evidence(
        bundle,
        declaration_only=declaration_only,
        evidence_scope=evidence_scope,
    )
    entries = build_alignment_plan_entries()
    declaration_reports = [_declaration_report(entry) for entry in entries]
    per_plan = [_plan_report(entry) for entry in entries]
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
    declaration_ok = all(report["ok"] for report in declaration_reports)
    strict_ok = alignment_ok and bool(bundle.get("ok"))
    overall_ok = (
        declaration_ok
        if declaration_only
        else strict_ok and known_bad_ok and source_audit_ok and source_known_bad_ok and full_diagnostic_ok and packet_result_family_parity_ok and similarity_convergence_ok
    )
    return {
        "ok": overall_ok,
        "result_type": "flowpilot_model_test_alignment",
        "declaration_ok": declaration_ok,
        "declaration_reports": declaration_reports,
        "evidence_status": "not_run" if declaration_only else ("passed" if strict_ok else "not_run"),
        "claim_scope": "declaration_only" if declaration_only else evidence_scope,
        "execution_evidence": bundle,
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
    parser.add_argument("--evidence-manifest", type=Path, default=None)
    parser.add_argument("--evidence-scope", choices=("routine", "release", "done", "publish"), default="routine")
    parser.add_argument("--declaration-only", action="store_true")
    args = parser.parse_args(argv)

    evidence_manifest, manifest_error = load_manifest(args.evidence_manifest)
    report = build_report(
        evidence_manifest=evidence_manifest,
        declaration_only=args.declaration_only,
        evidence_scope=args.evidence_scope,
    )
    report["evidence_manifest_path"] = str(args.evidence_manifest or "")
    report["evidence_manifest_error"] = manifest_error
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        if args.declaration_only and args.json_out.resolve() == RESULTS_PATH.resolve():
            raise SystemExit("declaration-only evidence cannot overwrite the canonical strict result")
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
