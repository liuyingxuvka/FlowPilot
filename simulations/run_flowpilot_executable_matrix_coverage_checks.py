"""Run executable FlowPilot matrix coverage checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_executable_matrix_coverage_model as model
except ImportError:  # pragma: no cover
    import flowpilot_executable_matrix_coverage_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_executable_matrix_coverage_results.json"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
}


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.State(),),
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


def _known_bad_report() -> dict[str, Any]:
    cases: dict[str, Any] = {}
    missing_expected: dict[str, list[str]] = {}
    for case in model.known_bad_cases():
        findings = model.validate_bridge_rows(case["rows"])
        codes = {str(finding["code"]) for finding in findings}
        expected = set(case["expected_codes"])
        if not expected <= codes:
            missing_expected[str(case["name"])] = sorted(expected - codes)
        cases[str(case["name"])] = {
            "expected_codes": sorted(expected),
            "actual_codes": sorted(codes),
        }
    return {
        "ok": not missing_expected,
        "cases": cases,
        "missing_expected_codes": missing_expected,
    }


def run_checks() -> dict[str, Any]:
    bridge = model.build_report()
    flowguard = _flowguard_report()
    known_bad = _known_bad_report()
    ok = bridge["ok"] and flowguard["ok"] and known_bad["ok"]
    return {
        "ok": ok,
        "model_id": model.MODEL_ID,
        "bridge": bridge,
        "flowguard": flowguard,
        "known_bad": known_bad,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output_path = args.json_out or (RESULTS_PATH if args.write_results else None)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    print(payload if args.json else f"FlowPilot executable matrix coverage ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
