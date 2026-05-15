"""Run checks for the FlowPilot Controller patrol timer model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_controller_patrol_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_controller_patrol_results.json"

REQUIRED_LABELS = (
    "controller_enters_continuous_standby",
    "controller_runs_named_patrol_timer_command",
    "patrol_timer_waits_requested_interval",
    "patrol_reads_existing_router_monitor",
    "patrol_returns_continue_with_anti_exit_rerun_and_wait",
    "controller_reruns_patrol_timer_and_waits_for_next_output",
    "new_controller_work_arrives_while_timer_waits",
    "patrol_returns_new_controller_work",
    "controller_processes_ready_action_ledger",
    "terminal_state_exposed_before_patrol",
)

HAZARD_EXPECTED_FAILURES = {
    "quiet_monitor_foreground_exit": "quiet monitor allowed Controller foreground exit",
    "command_start_marked_complete": "patrol command start or restart was treated as standby completion",
    "command_restart_marked_complete": "patrol command start or restart was treated as standby completion",
    "continue_patrol_without_anti_exit": "continue_patrol lacked anti-exit reminder",
    "continue_patrol_without_next_command": "continue_patrol did not name the next patrol command",
    "continue_patrol_without_rerun": "continue_patrol did not instruct Controller to rerun the patrol command",
    "continue_patrol_without_wait_next_output": "continue_patrol did not instruct Controller to wait for the next output",
    "continue_patrol_completes_standby": "continuous standby completed before terminal stop allowance",
    "rerun_without_waiting": "Controller reran patrol command without waiting for next output",
    "separate_monitor_used": "patrol timer used a separate monitor instead of the existing daemon monitor",
    "router_next_used_as_metronome": "Controller used router next/apply/run-until-wait as the patrol metronome",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|daemon={state.daemon_live}|mode={state.foreground_required_mode}|"
        f"standby={state.continuous_standby_visible},{state.continuous_standby_status}|"
        f"work={state.ordinary_controller_work_ready},processed={state.controller_action_ledger_processed}|"
        f"monitor={state.existing_monitor_read},separate={state.separate_monitor_used}|"
        f"command={state.patrol_command_named_in_prompt},{state.patrol_command_started},"
        f"elapsed={state.patrol_timer_elapsed}|result={state.patrol_result}|"
        f"reminder={state.anti_exit_reminder},next={state.next_command_named},"
        f"rerun={state.rerun_instruction},wait={state.wait_next_output_instruction}|"
        f"complete_start={state.command_start_marked_complete},"
        f"complete_restart={state.command_restart_marked_complete}|"
        f"rerun_started={state.next_command_rerun_started},"
        f"waiting={state.waiting_for_next_output}|closed={state.foreground_closed}|"
        f"stop_allowed={state.controller_stop_allowed}|next_metronome={state.router_next_used_as_metronome}"
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
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and any(model.is_success(state) for state in states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
        "success_state_count": sum(1 for state in states if model.is_success(state)),
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if idx not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(idx)
                changed = True
            if idx not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(idx)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
    return {"ok": ok, "hazards": hazards}


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    safe = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _run_flowguard_explorer()
    hazards = _hazard_report()
    skipped_checks: dict[str, str] = {
        "conformance_replay": (
            "skipped_with_reason: this is a preimplementation abstract model; "
            "runtime pytest checks cover the concrete patrol command"
        ),
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"]),
        "safe_graph": safe,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
