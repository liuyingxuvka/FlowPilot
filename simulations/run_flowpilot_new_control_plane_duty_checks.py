"""Run FlowGuard checks for the new FlowPilot control-plane duty repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_new_control_plane_duty_model as model
except ImportError:  # pragma: no cover
    import flowpilot_new_control_plane_duty_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_new_control_plane_duty_results.json"


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


def _source_contract_report() -> dict[str, Any]:
    runtime_text = (REPO_ROOT / "skills/flowpilot/assets/ai_project_runtime/runtime.py").read_text(encoding="utf-8")
    entrypoint_text = (REPO_ROOT / "skills/flowpilot/assets/flowpilot_new.py").read_text(encoding="utf-8")
    fake_text = (REPO_ROOT / "skills/flowpilot/assets/ai_project_runtime/fake_e2e.py").read_text(encoding="utf-8")
    runtime_tests = (REPO_ROOT / "tests/test_ai_project_runtime.py").read_text(encoding="utf-8")
    entrypoint_tests = (REPO_ROOT / "tests/test_flowpilot_new_entrypoint.py").read_text(encoding="utf-8")
    checks = {
        "action_classifier_present": "def classify_runtime_action" in runtime_text,
        "run_until_wait_present": "def run_until_wait(" in runtime_text and "def run_until_wait(root:" in entrypoint_text,
        "router_internal_whitelist_present": "ROUTER_INTERNAL_ACTION_TYPES" in runtime_text,
        "status_read_only": 'guard_trigger="status"' not in entrypoint_text,
        "structured_pm_parser_present": "_PM_REPAIR_DECISION_FIELD_RE" in runtime_text,
        "hostile_aliases_removed": '"stop": "stop_for_user"' not in runtime_text and '"block": "stop_for_user"' not in runtime_text,
        "pm_stop_blocks_route": "_stopped_semantic_blockers" in runtime_text and "PM stopped a semantic blocker" in runtime_text,
        "fake_e2e_public_fold": "runtime.run_until_wait(ledger)" in fake_text,
        "runtime_tests_cover_parser_and_fold": "test_pm_repair_decision_ignores_hostile_prose" in runtime_tests
        and "test_run_until_wait_folds_internal_action_to_role_boundary" in runtime_tests,
        "entrypoint_tests_cover_status": "test_status_is_read_only_but_patrol_refreshes_current_run_duty" in entrypoint_tests,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "failed": sorted(key for key, passed in checks.items() if not passed),
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    source = _source_contract_report()
    target_failures = model.invariant_failures(model.target_state())
    target = {
        "ok": not target_failures and model.is_success(model.target_state()),
        "failures": target_failures,
        "state": model.state_summary(model.target_state()),
    }
    return {
        "result_type": "flowpilot_new_control_plane_duty_checks",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and hazards["ok"] and source["ok"] and target["ok"],
        "flowguard": flowguard,
        "hazard_detection": hazards,
        "source_contract": source,
        "target": target,
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
