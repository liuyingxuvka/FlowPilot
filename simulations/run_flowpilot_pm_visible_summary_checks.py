"""Run FlowGuard checks for PM-visible role-authored summary handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_pm_visible_summary_model as model
except ImportError:  # pragma: no cover
    import flowpilot_pm_visible_summary_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_pm_visible_summary_results.json"


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
    rows: dict[str, Any] = {}
    failures: list[str] = []
    for path in ("missing_summary", "passing_summary", "blocking_summary"):
        state = model.target_state_for_path(path)
        path_failures = model.invariant_failures(state)
        rows[path] = {
            "ok": not path_failures and model.is_success(state),
            "failures": path_failures,
            "state": model.state_summary(state),
        }
        if path_failures or not model.is_success(state):
            failures.append(path)
    return {
        "ok": not failures,
        "paths": rows,
        "failures": failures,
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


def _model_test_alignment_report() -> dict[str, Any]:
    runtime_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    test_path = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    worker_card = REPO_ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "worker.md"
    reviewer_card = (
        REPO_ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "human_like_reviewer.md"
    )
    flowguard_card = (
        REPO_ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "flowguard_operator.md"
    )
    pm_card = REPO_ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "project_manager.md"
    runtime_text = runtime_path.read_text(encoding="utf-8")
    test_text = test_path.read_text(encoding="utf-8")
    card_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (worker_card, reviewer_card, flowguard_card, pm_card)
    )
    obligations = {
        "runtime_requires_pm_visible_summary": "pm_visible_summary_required" in runtime_text,
        "runtime_rejects_missing_summary": "formal role result requires role-authored pm_visible_summary" in runtime_text,
        "runtime_carries_recent_summary": "recent_role_report_summary" in runtime_text,
        "runtime_prefers_required_repair": "blocking_findings" in runtime_text and "required_repair" in runtime_text,
        "missing_summary_negative_test": "test_missing_pm_visible_summary_is_mechanically_reissued" in test_text,
        "pm_summary_propagation_test": "test_pm_repair_packet_includes_recent_role_report_summary" in test_text,
        "required_repair_to_pm_test": "test_reviewer_required_repair_reaches_pm_repair_packet" in test_text,
        "role_cards_require_summary": card_text.count("pm_visible_summary") >= 3,
        "pm_card_consumes_recent_summary": "recent_role_report_summary" in card_text,
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "tests/test_flowpilot_core_runtime.py",
            "skills/flowpilot/assets/runtime_kit/cards/roles/worker.md",
            "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
            "skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md",
            "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
        ],
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    alignment = _model_test_alignment_report()
    rows = [
        {
            "id": "pm_visible_summary_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_pm_visible_summary_model.py"],
        },
        {
            "id": "pm_visible_summary_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/enforce-pm-visible-role-summaries/tasks.md"],
        },
        {
            "id": "pm_visible_summary_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_pm_visible_summary_model.py"],
        },
        {
            "id": "pm_visible_summary_model_test_alignment",
            "status": "passed" if alignment["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": alignment["evidence"],
        },
    ]
    return {
        "result_type": "flowpilot_pm_visible_summary_checks",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and target_plan["ok"] and hazards["ok"] and alignment["ok"],
        "flowguard": flowguard,
        "target_plan": target_plan,
        "hazard_detection": hazards,
        "model_test_alignment": alignment,
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
