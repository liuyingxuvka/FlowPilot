"""Run FlowGuard checks for the symmetric new FlowPilot packet lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_symmetric_work_packet_model as model
except ImportError:  # pragma: no cover
    import flowpilot_symmetric_work_packet_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_symmetric_work_packet_results.json"


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_SAFE_LABELS,
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


def _target_plan_report() -> dict[str, Any]:
    state = model.target_state()
    failures = model.invariant_failures(state)
    return {
        "ok": not failures and model.is_success(state),
        "evidence_role": "symmetric_packet_target_path_not_live_user_proof",
        "failures": failures,
        "state": model.state_summary(state),
        "labels": list(model.REQUIRED_SAFE_LABELS),
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        if failures:
            hazards[name] = failures
    return {
        "ok": set(hazards) == set(model.hazard_states()),
        "hazards": hazards,
        "expected": sorted(model.hazard_states()),
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    rows = [
        {
            "id": "symmetric_packet_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_symmetric_work_packet_model.py"],
        },
        {
            "id": "symmetric_packet_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/unify-new-flowpilot-work-packet-lifecycle/tasks.md"],
        },
        {
            "id": "symmetric_packet_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_symmetric_work_packet_model.py"],
        },
    ]
    return {
        "result_type": "flowpilot_symmetric_work_packet_checks",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and target_plan["ok"] and hazards["ok"],
        "flowguard": flowguard,
        "target_plan": target_plan,
        "hazard_detection": hazards,
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": all(row["status"] == "passed" for row in rows)},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
