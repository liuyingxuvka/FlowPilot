"""Run checks for the FlowPilot packet-open authority model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_packet_open_authority_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_packet_open_authority_results.json"

REQUIRED_LABELS = (
    "pm_startup_packet_open_verified_and_authorized",
    "pm_control_blocker_packet_open_verified_and_authorized",
    "ordinary_role_packet_open_verified_and_authorized",
    "pm_completes_opened_packet_work",
    "pm_requests_existing_startup_repair",
    "pm_declares_existing_startup_protocol_dead_end",
    "pm_records_existing_control_blocker_repair_decision",
    "ordinary_role_submits_packet_result",
    "ordinary_role_submits_existing_formal_blocker",
)

HAZARD_EXPECTED_FAILURES = {
    "verified_open_without_authority": "verified open did not record work authority",
    "pm_waits_for_extra_relay_after_verified_open": "verified open waited for additional relay",
    "pm_self_blocker_loop": "PM routed a blocker back to PM",
    "pm_custom_repair_flow": "PM invented a custom recovery flow",
    "ordinary_role_silent_terminal_wait": "ordinary role ended without result or formal blocker",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|role={state.role_kind}|pm_context={state.pm_context}|"
        f"open_verified={state.open_verified}|authority={state.authority_recorded}|"
        f"exit={state.formal_exit}"
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
