"""Run FlowGuard role-recovery liveness proof checks for FlowPilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_role_recovery_liveness_model as model
except ImportError:  # pragma: no cover
    import flowpilot_role_recovery_liveness_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_role_recovery_liveness_results.json"

REQUIRED_LABELS = (
    "select_valid_current_report",
    "select_stale_report_reclaim",
    "select_unknown_liveness",
    "select_replacement_intent_only",
    "select_daemon_error_with_diagnostics",
    "select_daemon_error_without_diagnostics",
    "classify_current_recovery_liveness_proven",
    "classify_stale_recovery_report_risk",
    "classify_missing_host_liveness_risk",
    "classify_daemon_error_diagnostics_complete",
    "classify_daemon_error_diagnostics_missing",
)


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
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


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model._hard_check_failures(state)  # noqa: SLF001 - test/check helper
        if failures:
            hazards[name] = failures
    expected = {
        "stale_report_marked_safe",
        "unknown_liveness_marked_safe",
        "replacement_intent_only_marked_safe",
        "daemon_error_without_diagnostics_marked_safe",
        "current_report_overblocked",
    }
    return {"ok": set(hazards) == expected, "hazards": hazards}


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    report = {
        "result_type": "flowpilot_role_recovery_liveness",
        "model_id": model.MODEL_ID,
        "flowguard": flowguard,
        "hazard_detection": hazards,
        "safe_scenarios": sorted(model.SAFE_SCENARIOS),
        "risk_scenarios": sorted(model.RISK_SCENARIOS),
        "ok": bool(flowguard["ok"] and hazards["ok"]),
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_checks()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"[flowpilot-role-recovery-liveness] ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
