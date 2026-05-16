"""Run checks for the FlowPilot daemon heartbeat liveness model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_daemon_liveness_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_daemon_liveness_results.json"

REQUIRED_LABELS = (
    "monitor_reports_ok_inside_five_second_window",
    "monitor_reports_check_liveness_after_five_second_window",
    "monitor_reports_check_liveness_for_dead_daemon_after_window",
    "controller_attaches_after_liveness_check_finds_alive_daemon",
    "controller_recovers_after_liveness_check_finds_dead_daemon",
    "terminal_after_safe_liveness_decision",
)

HAZARD_EXPECTED_FAILURES = {
    "delayed_heartbeat_reported_ok": "monitor reported ok after the five-second heartbeat window",
    "monitor_decides_restart_from_timestamp": "monitor decided recovery before Controller liveness check",
    "controller_skips_liveness_check": "Controller continued after delayed heartbeat without liveness check",
    "dead_daemon_left_dead_after_check": "Controller found dead daemon without recovering current run daemon",
    "recovery_starts_second_writer": "Controller recovery started a second live Router writer",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|process={state.daemon_process}|"
        f"age={state.heartbeat_age_seconds}|monitor={state.monitor_status}|"
        f"checked={state.controller_liveness_checked}|decision={state.controller_decision}|"
        f"second_writer={state.second_writer_started}|next={state.next_action_allowed}"
    )


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    labels = set(graph["labels"])
    terminal_states = [state for state in states if model.is_terminal(state)]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(terminal_states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if idx not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
    }


def _flowguard_report() -> dict[str, object]:
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
        "reachability_failures": [
            {"label": item.label, "reason": item.reason}
            for item in report.reachability_failures
        ],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.HAZARD_STATES.items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = expected in failures
        ok = ok and detected
        hazards[name] = {"detected": detected, "expected": expected, "failures": failures}
    return {"ok": ok, "hazards": hazards}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "ok": bool(safe["ok"]) and bool(progress["ok"]) and bool(flowguard["ok"]) and bool(hazards["ok"]),
        "heartbeat_check_seconds": model.HEARTBEAT_CHECK_SECONDS,
        "safe_graph": safe,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    result = run_checks()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
