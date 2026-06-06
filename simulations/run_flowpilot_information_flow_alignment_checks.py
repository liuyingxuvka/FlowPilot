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
from typing import Any, Sequence

from flowguard import ModelTestAlignmentPlan, review_model_test_alignment

from flowpilot_information_flow_alignment_contracts import _code_contracts
from flowpilot_information_flow_alignment_evidence import _test_evidence
from flowpilot_information_flow_alignment_markers import _code_symbol_report, _marker_report
from flowpilot_information_flow_alignment_obligations import CHECK_COMMAND, MODEL_ID, _obligations
from flowpilot_model_test_alignment_common import _finding_counts

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


def build_report() -> dict[str, Any]:
    plan = build_alignment_plan()
    alignment_report = review_model_test_alignment(plan)
    alignment_findings = alignment_report.to_dict()["findings"]
    marker_report = _marker_report()
    code_symbol_report = _code_symbol_report(plan)
    model_reports = _model_reports()
    findings: list[dict[str, Any]] = []
    findings.extend({"layer": "model_test_alignment", **finding} for finding in alignment_findings)
    findings.extend({"layer": "source_marker", **finding} for finding in marker_report["findings"])
    findings.extend({"layer": "code_symbol", **finding} for finding in code_symbol_report["findings"])
    return {
        "ok": (
            alignment_report.ok
            and marker_report["ok"]
            and code_symbol_report["ok"]
            and model_reports["ok"]
        ),
        "result_type": "flowpilot_information_flow_alignment",
        "model_id": MODEL_ID,
        "command": CHECK_COMMAND,
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
    args = parser.parse_args(argv)

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
