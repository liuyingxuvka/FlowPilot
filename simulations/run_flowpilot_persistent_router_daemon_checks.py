"""Run checks for the FlowPilot persistent Router daemon model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_persistent_router_daemon_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_persistent_router_daemon_results.json"

REQUIRED_LABELS = (
    "formal_startup_starts_builtin_router_daemon",
    "controller_core_loaded_after_builtin_daemon_start",
    "router_issues_controller_action_to_ledger",
    "controller_executes_action_and_writes_receipt",
    "router_reconciles_controller_receipt_updates_router_fact_and_requires_rescan",
    "router_enters_ack_wait_owned_by_daemon",
    "daemon_wait_tick_keeps_checking_mailbox",
    "foreground_controller_standby_poll_tick_keeps_turn_open",
    "foreground_controller_bounded_timeout_reenters_standby",
    "role_writes_expected_mailbox_evidence",
    "daemon_consumes_mailbox_evidence_once",
    "daemon_continues_after_consumed_evidence",
    "heartbeat_wakes_and_finds_live_daemon",
    "user_requests_terminal_stop",
    "terminal_stop_reconciles_daemon_controller_roles",
)

HAZARD_EXPECTED_FAILURES = {
    "controller_core_loaded_after_skipped_daemon_start": "Controller core loaded before formal startup daemon was live",
    "formal_startup_continued_after_daemon_failure": "formal startup continued after Router daemon startup failure",
    "ack_wait_without_daemon": "ordinary wait exists without a live Router daemon",
    "duplicate_router_writers": "multiple Router daemon writers exist for one run",
    "duplicate_ack_consumption": "mailbox evidence was consumed more than once",
    "controller_done_without_receipt": "Controller action was marked done without a Controller receipt",
    "router_cleared_controller_receipt_without_internal_fact": "Router cleared Controller receipt without updating Router-owned internal action fact",
    "same_controller_action_reissued_after_done_receipt": "Router reissued the same Controller action after a done receipt because Router-owned fact stayed stale",
    "controller_used_router_next_as_metronome": "Controller used diagnostic Router next/run-until-wait as the normal runtime metronome",
    "controller_stopped_at_ordinary_wait": "Controller stopped at an ordinary daemon-owned wait",
    "foreground_controller_ended_during_live_daemon_wait": "Foreground Controller ended instead of staying in standby for a live daemon-owned role wait",
    "foreground_controller_ended_with_pending_controller_action": "Foreground Controller ended while an executable Controller action was pending",
    "foreground_controller_ended_while_daemon_active_no_action": "Foreground Controller ended while the Router daemon was live and no Controller action was ready",
    "heartbeat_started_second_live_daemon": "heartbeat started a second Router daemon while one was live",
    "terminal_left_runtime_active": "terminal lifecycle left daemon, Controller, roles, heartbeat, or route work active",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|formal={state.formal_startup_started},"
        f"startup_daemon={state.startup_daemon_step_completed},"
        f"startup_failed={state.startup_daemon_failed}|daemon={state.daemon_mode_enabled},"
        f"{state.daemon_alive},{state.daemon_lock_state},{state.daemon_writer_count},"
        f"tick={state.daemon_tick_seconds}|core={state.controller_core_loaded}|"
        f"controller={state.controller_attached},"
        f"metronome={state.controller_called_router_next_as_metronome},"
        f"finaled={state.controller_finaled_at_wait},"
        f"standby={state.foreground_standby_active},"
        f"poll_daemon={state.foreground_standby_polling_daemon_status},"
        f"poll_ledger={state.foreground_standby_polling_action_ledger},"
        f"standby_timeouts={state.foreground_standby_timeout_count},"
        f"ended_wait={state.foreground_controller_ended_turn_while_daemon_waiting},"
        f"ended_pending_action={state.foreground_controller_ended_while_controller_action_pending},"
        f"ended_no_action={state.foreground_controller_ended_while_daemon_active_no_action}|"
        f"roles={state.roles_live}|"
        f"heartbeat={state.heartbeat_active},{state.heartbeat_woke}|"
        f"wait={state.current_wait}|mail={state.mailbox_evidence_present},"
        f"{state.mailbox_evidence_valid},{state.mailbox_evidence_consumed},"
        f"wait_tick={state.mailbox_wait_tick_observed},"
        f"count={state.mailbox_consumption_count}|"
        f"action={state.controller_action_pending},{state.controller_action_ready},"
        f"done={state.controller_action_done},receipt={state.controller_receipt_present},"
        f"rescan={state.controller_rescanned_after_receipt},"
        f"router_fact={state.router_internal_action_fact_current},"
        f"router_fact_from_receipt={state.router_internal_fact_updated_from_receipt},"
        f"cleared_without_fact={state.router_cleared_pending_without_internal_fact},"
        f"same_action_reissues={state.same_controller_action_reissue_count}|"
        f"stop={state.stop_requested}|route={state.route_work_allowed}"
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
        "invariant_failures": graph["invariant_failures"][:10],
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
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
            "skipped_with_reason: this abstract daemon model validates the "
            "planned control contract before production code is changed"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = (
            "skipped_with_reason: no --json-out path was provided"
        )
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
