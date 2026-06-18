"""Run FlowPilot fake-AI runtime replay matrix checks."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_fake_ai_runtime_replay_model as model
except ImportError:  # pragma: no cover
    import flowpilot_fake_ai_runtime_replay_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_fake_ai_runtime_replay_results.json"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.VALID_SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
}
EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()


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


def _walk_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []
    terminal_count = 0
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": str(state), "failures": failures})
        if model.is_terminal(state):
            terminal_count += 1
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not invariant_failures,
        "state_count": len(states),
        "terminal_count": terminal_count,
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = set(model.runtime_replay_failures(state))
        expected = set(EXPECTED_HAZARD_FAILURES[name])
        if failures:
            hazards[name] = sorted(failures)
        if not expected <= failures:
            missing[name] = sorted(expected - failures)
    return {
        "ok": set(hazards) == set(model.NEGATIVE_SCENARIOS) and not missing,
        "hazards": hazards,
        "expected": sorted(model.NEGATIVE_SCENARIOS),
        "missing_expected_failures": missing,
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    walk = _walk_report()
    hazards = _hazard_report()
    matrix = model.build_report()
    ok = all(section["ok"] for section in (flowguard, walk, hazards, matrix))
    return {
        "ok": ok,
        "model_id": model.MODEL_ID,
        "flowguard": flowguard,
        "walk": walk,
        "hazards": hazards,
        "matrix": matrix,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    report = run_checks()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"FlowPilot fake-AI runtime replay ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
