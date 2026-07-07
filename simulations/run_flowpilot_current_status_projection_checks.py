"""Run FlowPilot current status projection convergence checks."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_current_status_projection_model as model
except ImportError:  # pragma: no cover
    import flowpilot_current_status_projection_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_current_status_projection_results.json")


def _state_id(state: model.State) -> str:
    return f"status={state.status}|cell_id={state.cell_id}|reason={state.terminal_reason}"


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=(),
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
    states: list[model.State] = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, object]] = []
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    accepted = [state.cell_id for state in states if state.status == "accepted"]
    rejected = [state.cell_id for state in states if state.status == "rejected"]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels_seen)
    return {
        "ok": (
            not missing_labels
            and not invariant_failures
            and set(accepted) == set(model.VALID_CELL_IDS)
            and set(rejected) == set(model.NEGATIVE_CELL_IDS)
        ),
        "state_count": len(states),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "missing_labels": missing_labels[:20],
        "missing_label_count": len(missing_labels),
        "invariant_failures": invariant_failures[:20],
    }


def _hazard_report() -> dict[str, Any]:
    missed: dict[str, list[str]] = {}
    by_failure: dict[str, int] = {}
    for cell_id, state in model.hazard_states().items():
        cell = model.CELL_BY_ID[cell_id]
        expected = list(model.projection_failures(cell))
        if not expected:
            missed[cell_id] = ["negative cell has no expected projection failure"]
        for failure in expected:
            by_failure[failure] = by_failure.get(failure, 0) + 1
        terminal = list(model.next_safe_states(state))
        if not terminal or not terminal[0].label.startswith("reject_"):
            missed[cell_id] = [*missed.get(cell_id, []), "negative cell did not reject"]
    return {
        "ok": not missed,
        "negative_cell_count": len(model.NEGATIVE_CELL_IDS),
        "missed_negative_cells": missed,
        "by_failure": dict(sorted(by_failure.items())),
    }


def run_checks() -> dict[str, Any]:
    matrix = model.matrix_report()
    walk = _walk_report()
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "model_id": model.MODEL_ID,
        "ok": matrix["ok"] and walk["ok"] and flowguard["ok"] and hazards["ok"],
        "matrix": matrix,
        "walk": walk,
        "flowguard": flowguard,
        "hazards": hazards,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "flowpilot current status projection checks: "
            f"ok={report['ok']} matrix={report['matrix']['ok']} "
            f"walk={report['walk']['ok']} flowguard={report['flowguard']['ok']} "
            f"hazards={report['hazards']['ok']}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
