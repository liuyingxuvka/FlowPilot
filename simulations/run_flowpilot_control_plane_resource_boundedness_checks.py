"""Run FlowGuard checks for control-plane resource boundedness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard.explorer import Explorer

import flowpilot_control_plane_resource_boundedness_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_control_plane_resource_boundedness_results.json"


def _scenario_report() -> dict[str, object]:
    workflow = model.build_workflow()
    rows: dict[str, object] = {}
    labels: set[str] = set()
    ok = True
    for scenario in model.SCENARIOS:
        run = workflow.execute(model.initial_state(), model.Tick(scenario))
        completed = list(run.completed_paths)
        terminal = completed[0].state if len(completed) == 1 else None
        trace_labels = (
            [step.label for step in completed[0].trace.steps] if completed else []
        )
        labels.update(trace_labels)
        expected = "accepted" if scenario in model.VALID_SCENARIOS else "rejected"
        row_ok = (
            terminal is not None
            and terminal.status == expected
            and not run.dead_branches
            and not run.exception_branches
        )
        ok = ok and row_ok
        rows[scenario] = {
            "ok": row_ok,
            "expected_status": expected,
            "actual_status": terminal.status if terminal else "missing",
            "labels": trace_labels,
            "contract_failures": list(terminal.rejection_reasons) if terminal else [],
        }
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    return {"ok": ok and not missing_labels, "missing_labels": missing_labels, "rows": rows}


def _explorer_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
    }


def _known_bad_report() -> dict[str, object]:
    rows: dict[str, object] = {}
    ok = True
    for name, state in model.known_bad_states().items():
        failures = model.contract_failures(state)
        detected = bool(failures)
        ok = ok and detected
        rows[name] = {"detected": detected, "failures": failures}
    return {"ok": ok, "rows": rows}


def run_checks() -> dict[str, object]:
    checks = {
        "scenario_matrix": _scenario_report(),
        "flowguard_explorer": _explorer_report(),
        "known_bad": _known_bad_report(),
    }
    return {
        "ok": all(check["ok"] for check in checks.values()),
        "model": model.MODEL_ID,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args()
    report = run_checks()
    output = Path(args.json_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
