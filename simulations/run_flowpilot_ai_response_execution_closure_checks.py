"""Run FlowGuard and execution-backed formal AI response closure checks."""

from __future__ import annotations

import argparse
import json
import platform
import time
from collections import deque
from pathlib import Path
from typing import Any, Sequence

from flowguard.explorer import Explorer

import flowpilot_ai_response_execution_closure_model as model


REQUIRED_LABELS = tuple(
    [f"select_{name}" for name in model.SCENARIOS]
    + ["accepted_valid_execution_closure"]
    + [f"rejected_{name}" for name in model.NEGATIVE_SCENARIOS]
)


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
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


def _graph_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial}
    labels: set[str] = set()
    accepted: list[model.State] = []
    rejected: list[model.State] = []
    invariant_failures: list[dict[str, Any]] = []
    while queue:
        state = queue.popleft()
        for invariant in model.INVARIANTS:
            result = invariant.predicate(state, ())
            if not result.ok:
                invariant_failures.append({"state": repr(state), "message": result.message})
        if state.status == "accepted":
            accepted.append(state)
        elif state.status == "rejected":
            rejected.append(state)
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in seen:
                seen.add(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    ok = (
        not invariant_failures
        and not missing_labels
        and {state.scenario for state in accepted} == model.VALID_SCENARIOS
        and {state.scenario for state in rejected} == model.NEGATIVE_SCENARIOS
    )
    return {
        "ok": ok,
        "state_count": len(seen),
        "accepted_scenarios": sorted(state.scenario for state in accepted),
        "rejected_scenarios": sorted(state.scenario for state in rejected),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    expected = model.expected_failures_by_hazard()
    cases: dict[str, Any] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        actual = model.state_failures(state)
        detected = bool(actual) and actual == expected[name]
        cases[name] = {
            "detected": detected,
            "expected_failures": expected[name],
            "actual_failures": actual,
        }
        if not detected:
            failures.append(f"{name}: expected={expected[name]!r} actual={actual!r}")
    return {"ok": not failures, "cases": cases, "failures": failures}


def run_checks(*, mode: str, budget_seconds: float | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    graph = _graph_report()
    explorer = _flowguard_report()
    hazards = _hazard_report()
    execution = model.run_execution_closure(mode=mode, budget_seconds=budget_seconds)
    result = {
        "model_id": model.MODEL_ID,
        "mode": mode,
        "graph": graph,
        "flowguard_explorer": explorer,
        "known_bad_hazards": hazards,
        "execution_closure": execution,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    result["ok"] = graph["ok"] and explorer["ok"] and hazards["ok"] and execution["ok"]
    result["duration_seconds"] = round(time.perf_counter() - started, 3)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fast", "adversarial"), default="fast")
    parser.add_argument("--budget-seconds", type=float, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run_checks(mode=args.mode, budget_seconds=args.budget_seconds)
    result["proof_artifact_ref"] = {
        "artifact_path": str(args.json_out) if args.json_out else "stdout_only",
        "final_status": "passed" if result["ok"] else "failed",
        "source_fingerprint": result["execution_closure"]["source_fingerprint"],
        "selected_case_count": result["execution_closure"]["execution_universe"]["selected_case_count"],
        "executed_case_count": result["execution_closure"]["execution_universe"]["executed_case_count"],
        "coverage_counts": result["execution_closure"]["coverage_summary"]["aggregate"],
        "coverage_count_fields": result["execution_closure"]["coverage_summary"]["count_fields"],
        "counts_are_independent": result["execution_closure"]["coverage_summary"]["counts_are_independent"],
        "exit_status_owner": "process_exit_code",
    }
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
