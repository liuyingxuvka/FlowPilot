"""Run black-box fake-project rehearsal checks for the new FlowPilot entrypoint."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_fake_project_rehearsal_model as model
    from . import flowpilot_fake_project_rehearsal_scenarios as rehearsal_scenarios
    from . import flowpilot_recursive_route_execution_model as recursive_route_model
except ImportError:  # pragma: no cover
    import flowpilot_fake_project_rehearsal_model as model
    import flowpilot_fake_project_rehearsal_scenarios as rehearsal_scenarios
    import flowpilot_recursive_route_execution_model as recursive_route_model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ENTRYPOINT = rehearsal_scenarios.ENTRYPOINT
RESULTS_PATH = ROOT / "flowpilot_fake_project_rehearsal_results.json"
DEFAULT_WORK_ROOT = REPO_ROOT / "tmp" / "flowpilot_fake_project_rehearsal"
RECURSIVE_ROUTE_BAD_CASES = (
    "missing_node_terminal_complete",
    "wrong_flowguard_target_accepted",
    "stale_node_evidence_accepted",
    "dead_lease_advances_node",
    "mutation_without_frontier_rewrite",
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
        "evidence_role": "blackbox_fake_project_target_plan_not_live_user_proof",
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


def _recursive_route_hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in recursive_route_model.hazard_states().items():
        failures = recursive_route_model.invariant_failures(state)
        if failures:
            hazards[name] = failures
    covered = [name for name in RECURSIVE_ROUTE_BAD_CASES if name in hazards]
    return {
        "ok": set(covered) == set(RECURSIVE_ROUTE_BAD_CASES),
        "hazards": hazards,
        "expected": list(RECURSIVE_ROUTE_BAD_CASES),
        "covered": covered,
        "model_id": recursive_route_model.MODEL_ID,
    }


def _row(row_id: str, ok: bool, evidence: list[str], *, scope: str = "routine") -> dict[str, Any]:
    return {
        "id": row_id,
        "status": "passed" if ok else "failed",
        "freshness": "current",
        "scope": scope,
        "evidence": evidence,
    }


def _run_checks_in_root(work_root: Path, *, scenario_names: set[str] | None = None) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    recursive_hazards = _recursive_route_hazard_report()
    if scenario_names is None:
        scenarios = rehearsal_scenarios.run_all_scenarios(work_root)
    else:
        scenario_map = dict(rehearsal_scenarios.SCENARIOS)
        missing = sorted(scenario_names - set(scenario_map))
        if missing:
            raise ValueError(f"unknown fake project scenario(s): {missing}")
        scenarios = [
            rehearsal_scenarios.run_scenario(name, scenario_map[name], work_root)
            for name in [name for name, _fn in rehearsal_scenarios.SCENARIOS if name in scenario_names]
        ]
    scenario_by_name = {scenario["name"]: scenario for scenario in scenarios}
    recursive_bad_case_rows = [
        _row(f"fake_project_recursive_bad_case_{name}", name in recursive_hazards["covered"], ["simulations/flowpilot_recursive_route_execution_model.py"])
        for name in RECURSIVE_ROUTE_BAD_CASES
    ]
    rows = [
        _row("fake_project_flowguard_model", flowguard["ok"], ["simulations/flowpilot_fake_project_rehearsal_model.py"]),
        _row("fake_project_hazard_replay", hazards["ok"], ["simulations/flowpilot_fake_project_rehearsal_model.py"]),
        _row("fake_project_recursive_route_bad_case_replay", recursive_hazards["ok"], ["simulations/flowpilot_recursive_route_execution_model.py"]),
        *recursive_bad_case_rows,
    ]
    scenario_rows = {
        "normal_full_path": ("fake_project_blackbox_cli_normal", "skills/flowpilot/assets/flowpilot_new.py"),
        "planning_chain_does_not_terminal": ("fake_project_blackbox_cli_planning_chain_guard", "skills/flowpilot/assets/flowpilot_new.py"),
        "route_mutation_recovery": ("fake_project_blackbox_cli_route_mutation_recovery", "skills/flowpilot/assets/flowpilot_new.py"),
        "terminal_supplemental_repair": ("fake_project_blackbox_cli_terminal_supplemental_repair", "skills/flowpilot/assets/flowpilot_new.py"),
        "slow_reviewer_progress_preserved": ("fake_project_blackbox_cli_slow_reviewer_progress", "skills/flowpilot/assets/flowpilot_new.py"),
        "missing_current_result_fields_reissue": ("fake_project_blackbox_cli_missing_current_result_fields_reissue", "skills/flowpilot/assets/flowpilot_new.py"),
        "accepted_packet_reassignment_rejected": ("fake_project_blackbox_cli_accepted_packet_reassignment", "skills/flowpilot/assets/flowpilot_new.py"),
        "stop_terminal_fence": ("fake_project_blackbox_cli_stop_terminal_fence", "skills/flowpilot/assets/flowpilot_new.py"),
        "progress_evidence_replacement": ("fake_project_blackbox_cli_progress_evidence_replacement", "skills/flowpilot/assets/flowpilot_new.py"),
        "orphan_runner_summary_recovery": ("fake_project_blackbox_cli_orphan_runner_summary", "skills/flowpilot/assets/flowpilot_new.py"),
    }
    for scenario_name, (row_id, evidence_path) in scenario_rows.items():
        if scenario_name in scenario_by_name:
            rows.append(_row(row_id, scenario_by_name[scenario_name]["ok"], [evidence_path]))
    if len(scenarios) > 1:
        rows.append(
            _row(
                "fake_project_blackbox_cli_selected_flows",
                all(scenario["ok"] for scenario in scenarios),
                ["skills/flowpilot/assets/flowpilot_new.py"],
            )
        )
    return {
        "result_type": "flowpilot_fake_project_rehearsal_checks",
        "model_id": model.MODEL_ID,
        "ok": (
            flowguard["ok"]
            and target_plan["ok"]
            and hazards["ok"]
            and recursive_hazards["ok"]
            and all(scenario["ok"] for scenario in scenarios)
        ),
        "entrypoint": str(ENTRYPOINT),
        "work_root": str(work_root),
        "black_box_contract": {
            "uses_public_cli_subprocesses": True,
            "uses_startup_ui_script": True,
            "uses_internal_e2e_helper": False,
            "fake_ai_result_bodies_redacted_from_report": True,
        },
        "flowguard": flowguard,
        "target_plan": target_plan,
        "hazard_detection": hazards,
        "recursive_route_hazard_detection": recursive_hazards,
        "scenarios": scenarios,
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": all(row["status"] == "passed" for row in rows)},
        },
    }


def run_checks(work_root: Path | None = None, *, scenario_names: set[str] | None = None) -> dict[str, Any]:
    if work_root is None:
        with tempfile.TemporaryDirectory(prefix="flowpilot_fake_project_rehearsal_") as tmp:
            return _run_checks_in_root(Path(tmp), scenario_names=scenario_names)
    return _run_checks_in_root(work_root, scenario_names=scenario_names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--scenario", action="append", choices=[name for name, _fn in rehearsal_scenarios.SCENARIOS])
    args = parser.parse_args()

    result = run_checks(args.work_root, scenario_names=set(args.scenario) if args.scenario else None)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = args.json_out.with_name(f"{args.json_out.name}.tmp")
        tmp_path.write_text(output, encoding="utf-8")
        tmp_path.replace(args.json_out)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
