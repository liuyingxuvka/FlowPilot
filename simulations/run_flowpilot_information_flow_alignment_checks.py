"""Check FlowPilot information-flow model obligations against code and tests.

This runner is read-only. It answers whether the blocker/repair/resume/
break-glass/route-mutation information-flow models have concrete receiving
surfaces in runtime code, role cards, and tests. A green result is scoped
alignment evidence, not a full runtime replay.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from flowguard import ModelTestAlignmentPlan, review_model_test_alignment

from flowpilot_information_flow_alignment_contracts import _code_contracts
from flowpilot_information_flow_alignment_evidence import _test_evidence
from flowpilot_information_flow_alignment_markers import _code_symbol_report, _marker_report
from flowpilot_information_flow_alignment_obligations import CHECK_COMMAND, MODEL_ID, _obligations
from flowpilot_model_test_alignment_common import (
    _finding_counts,
    configure_execution_evidence,
)
from flowpilot_evidence_truth import load_manifest, proof_bundle_report

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.compile_flowpilot_acceptance_testmesh_evidence import source_fingerprint

try:  # pragma: no cover
    from . import run_flowpilot_blocker_repair_information_flow_checks as blocker_checks
    from . import run_flowpilot_project_control_information_flow_checks as project_checks
except ImportError:  # pragma: no cover
    import run_flowpilot_blocker_repair_information_flow_checks as blocker_checks
    import run_flowpilot_project_control_information_flow_checks as project_checks


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_information_flow_alignment_results.json"
)


def build_alignment_plan() -> ModelTestAlignmentPlan:
    return ModelTestAlignmentPlan(
        model_id=MODEL_ID,
        obligations=_obligations(),
        code_contracts=_code_contracts(),
        test_evidence=_test_evidence(),
    )


def _model_reports() -> dict[str, Any]:
    blocker = blocker_checks.run_checks()
    project = project_checks.run_checks()
    return {
        "ok": bool(blocker["ok"] and project["ok"]),
        "blocker_repair_information_flow": {
            "ok": blocker["ok"],
            "model_id": blocker["model_id"],
            "accepted": blocker["safe_graph"]["accepted_scenarios"],
            "rejected": blocker["safe_graph"]["rejected_scenarios"],
            "hazard_failure_count": len(blocker["hazard_detection"]["failures"]),
        },
        "project_control_information_flow": {
            "ok": project["ok"],
            "model_id": project["model_id"],
            "accepted": project["safe_graph"]["accepted_scenarios"],
            "rejected": project["safe_graph"]["rejected_scenarios"],
            "hazard_failure_count": len(project["hazard_detection"]["failures"]),
        },
    }


def _declaration_report(plan: ModelTestAlignmentPlan) -> dict[str, Any]:
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
    failures: list[str] = []
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
    return {"ok": not failures, "failures": failures, "evidence_status": "not_run"}


def build_report(
    *,
    evidence_manifest: dict[str, Any] | None = None,
    declaration_only: bool = False,
    evidence_scope: str = "routine",
) -> dict[str, Any]:
    bundle = (
        proof_bundle_report(
            evidence_manifest,
            expected_source_fingerprint=source_fingerprint(),
            required_scope=evidence_scope,
        )
        if not declaration_only
        else {
            "ok": False,
            "selected_count": 0,
            "executed_count": 0,
            "test_count": 0,
            "failures": ["declaration_only_execution_not_run"],
        }
    )
    configure_execution_evidence(bundle, declaration_only=declaration_only)
    plan = build_alignment_plan()
    declaration_report = _declaration_report(plan)
    alignment_report = review_model_test_alignment(plan)
    alignment_findings = alignment_report.to_dict()["findings"]
    marker_report = _marker_report()
    code_symbol_report = _code_symbol_report(plan)
    model_reports = _model_reports()
    findings: list[dict[str, Any]] = []
    findings.extend({"layer": "model_test_alignment", **finding} for finding in alignment_findings)
    findings.extend({"layer": "source_marker", **finding} for finding in marker_report["findings"])
    findings.extend({"layer": "code_symbol", **finding} for finding in code_symbol_report["findings"])
    strict_ok = alignment_report.ok and bool(bundle.get("ok"))
    return {
        "ok": (
            (declaration_report["ok"] if declaration_only else strict_ok)
            and marker_report["ok"]
            and code_symbol_report["ok"]
            and model_reports["ok"]
        ),
        "result_type": "flowpilot_information_flow_alignment",
        "model_id": MODEL_ID,
        "command": CHECK_COMMAND,
        "claim_scope": "declaration_only" if declaration_only else evidence_scope,
        "evidence_status": "not_run" if declaration_only else ("passed" if strict_ok else "not_run"),
        "execution_evidence": bundle,
        "declaration_ok": declaration_report["ok"],
        "declaration_report": declaration_report,
        "alignment_ok": alignment_report.ok,
        "marker_ok": marker_report["ok"],
        "code_symbol_ok": code_symbol_report["ok"],
        "underlying_model_ok": model_reports["ok"],
        "obligation_count": len(plan.obligations),
        "code_contract_count": len(plan.code_contracts),
        "test_evidence_count": len(plan.test_evidence),
        "finding_count": len(findings),
        "finding_counts": _finding_counts(findings),
        "findings": findings,
        "plan": plan.to_dict(),
        "alignment_report": alignment_report.to_dict(),
        "source_marker_report": marker_report,
        "code_symbol_report": code_symbol_report,
        "underlying_model_reports": model_reports,
        "claim_boundary": {
            "covers": [
                "model obligations for blocker repair and project-control information sufficiency",
                "declared runtime code owners for each obligation",
                "existence of targeted tests/cards/markers for required information fields",
                "source-symbol existence for declared code contracts",
            ],
            "does_not_cover": [
                "executing every referenced test command in this runner",
                "full release/install synchronization",
                "semantic proof that every private helper branch is correct",
            ],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=RESULTS_PATH,
        help="Optional path for writing the JSON result payload.",
    )
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--evidence-manifest", type=Path, default=None)
    parser.add_argument(
        "--evidence-scope",
        choices=("routine", "release", "done", "publish"),
        default="routine",
    )
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
    print(output, end="")
    if not args.no_write_results:
        if args.declaration_only and args.json_out.resolve() == RESULTS_PATH.resolve():
            raise SystemExit("declaration-only evidence cannot overwrite the canonical strict result")
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
