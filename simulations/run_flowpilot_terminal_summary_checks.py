"""Run checks for the FlowPilot terminal-summary model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_terminal_summary_model as model


REQUIRED_LABELS = (
    "router_detects_terminal_mode_closed",
    "router_detects_terminal_mode_stopped_by_user",
    "router_detects_terminal_mode_cancelled_by_user",
    "router_detects_terminal_mode_blocked_handoff",
    "router_delivers_terminal_summary_card",
    "controller_reads_current_run_root_all_files",
    "controller_writes_and_displays_terminal_summary",
    "router_observes_terminal_lifecycle_after_summary",
)


HAZARD_EXPECTED_FAILURES = {
    "terminal_lifecycle_without_summary": "terminal lifecycle observed before final summary was saved and registered",
    "summary_card_before_terminal_mode": "terminal summary card delivered before Router knew terminal mode",
    "read_all_files_without_summary_card": "Controller read all run files before terminal summary authorization",
    "read_all_files_before_terminal": "terminal summary card delivered before Router knew terminal mode",
    "controller_reads_outside_run_root": "Controller read outside current run root during terminal summary",
    "summary_missing_flowpilot_attribution": "final summary markdown missing first-line FlowPilot GitHub attribution",
    "summary_not_registered_in_index": "terminal lifecycle observed before final summary was saved and registered",
    "summary_display_does_not_match_saved_content": "terminal lifecycle observed before final summary was saved and registered",
    "summary_requested_again_after_complete": "terminal summary requested again after summary was already complete",
    "controller_continues_route_work_after_summary": "Controller continued route work in terminal summary mode",
    "controller_approves_gate_after_summary": "Controller approved or reopened a gate in terminal summary mode",
    "controller_originates_project_evidence_after_summary": "Controller originated project evidence in terminal summary mode",
    "controller_writes_non_summary_file_after_summary": "Controller wrote non-summary files in terminal summary mode",
    "stopped_run_without_summary": "terminal lifecycle observed before final summary was saved and registered",
    "cancelled_run_without_summary": "terminal lifecycle observed before final summary was saved and registered",
    "blocked_handoff_without_summary": "terminal lifecycle observed before final summary was saved and registered",
}


def _state_id(state: model.State) -> str:
    return (
        f"mode={state.terminal_mode},known={state.router_terminal_mode_known}|"
        f"card={state.terminal_summary_card_delivered},"
        f"auth={state.terminal_read_all_run_files_authorized},"
        f"read_all={state.controller_read_current_run_root_all_files},"
        f"outside={state.controller_read_outside_current_run_root}|"
        f"display={state.summary_displayed_to_user},"
        f"md={state.summary_markdown_written},"
        f"json={state.summary_json_written},"
        f"link={state.summary_attribution_first_line},"
        f"index={state.summary_registered_in_index},"
        f"match={state.summary_display_matches_saved_content}|"
        f"observed={state.terminal_lifecycle_observed},"
        f"repeat={state.terminal_summary_requested_again}|"
        f"bad={state.controller_continued_route_work},"
        f"{state.controller_approved_or_reopened_gate},"
        f"{state.controller_originated_project_evidence},"
        f"{state.controller_wrote_non_summary_file}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(seen)
                seen.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    invariant_failures = graph["invariant_failures"]
    return {
        "ok": not invariant_failures
        and not missing_labels
        and any(model.is_success(state) for state in states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "success_state_count": sum(1 for state in states if model.is_success(state)),
        "invariant_failures": invariant_failures,
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, targets in enumerate(edges):
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in targets
            ):
                can_reach_terminal.add(source)
                changed = True
    stuck = [
        _state_id(states[idx])
        for idx, targets in enumerate(edges)
        if idx not in terminal and not targets
    ]
    cannot_reach_terminal = [
        _state_id(states[idx])
        for idx in range(len(states))
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_count": len(stuck),
        "stuck_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    results: dict[str, dict[str, object]] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        caught = any(expected in failure for failure in failures)
        results[name] = {"caught": caught, "expected": expected, "failures": failures}
        ok = ok and caught
    return {"ok": ok, "hazards": results}


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    hazards = _check_hazards()
    workflow = model.build_workflow()
    explorer = Explorer(
        workflow=workflow,
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    )
    report = explorer.explore()
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(hazards["ok"]) and bool(report.ok),
        "safe_graph": safe_graph,
        "progress": progress,
        "hazard_checks": hazards,
        "flowguard_explorer": {
            "ok": report.ok,
            "summary": report.summary,
            "violation_count": len(report.violations),
            "dead_branch_count": len(report.dead_branches),
            "exception_branch_count": len(report.exception_branches),
            "reachability_failure_count": len(report.reachability_failures),
            "reachability_failures": [
                failure.message for failure in report.reachability_failures
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    result = run_checks()
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
