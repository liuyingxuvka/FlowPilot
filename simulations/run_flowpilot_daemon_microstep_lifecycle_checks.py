"""Run checks for the FlowPilot daemon lifecycle microstep model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_daemon_microstep_lifecycle_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_daemon_microstep_lifecycle_results.json"

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.COMPUTE_NEXT_BEFORE_REQUIRED_READS: "daemon computed or reported progress before reading required control tables",
    model.STARTUP_RECEIPT_LEAVES_PENDING: "done Controller receipt did not reconcile all authority, Router, Controller, and pending state",
    model.ROUTE_RECEIPT_LEAVES_ROUTER_FACT_STALE: "daemon cleared pending or wait before syncing authority state",
    model.ROLE_OUTPUT_LEFT_DURABLE_ONLY: "role output stayed in durable storage without authority sync and wait closure",
    model.EXTERNAL_EVENT_WAIT_NOT_ROUTER_CLOSED: "external event did not close the Router-owned wait row",
    model.REPAIR_BLOCKER_BEFORE_RECEIPT_READ: "daemon computed or reported progress before reading required control tables",
    model.TERMINAL_STATUS_BEFORE_CLEANUP: "terminal daemon status was written before runtime cleanup completed",
    model.PENDING_CLEARED_BEFORE_AUTHORITY_SYNC: "daemon cleared pending or wait before syncing authority state",
    model.CONTROLLER_WRITES_ROUTER_TABLE: "Controller wrote Router-owned scheduler state",
    model.DAEMON_STATUS_FROM_STALE_SUMMARY: "daemon computed or reported progress before reading required control tables",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|phase={state.phase}|"
        f"reads=daemon:{state.read_daemon_status},auth:{state.read_authority_state},"
        f"router:{state.read_router_scheduler},controller:{state.read_controller_ledger},"
        f"receipts:{state.read_receipts},events:{state.read_events},terminal:{state.read_terminal_records}|"
        f"evidence=receipt:{state.controller_receipt_done},role:{state.role_output_present},"
        f"event:{state.external_event_present},repair:{state.repair_receipt_present}|"
        f"sync=auth:{state.authority_state_synced},router_row:{state.router_row_reconciled},"
        f"controller_row:{state.controller_row_reconciled},clear:{state.pending_or_wait_cleared},"
        f"next_or_barrier:{state.next_scheduled_or_barrier_recorded}|"
        f"writes=router:{state.write_router_table_done},controller:{state.write_controller_table_done},"
        f"daemon_status:{state.write_daemon_status_done},terminal_cleanup:{state.terminal_cleanup_done}|"
        f"writers=router_table:{state.router_table_writer},controller_table:{state.controller_table_writer}|"
        f"bad=compute_before_reads:{state.computed_next_before_required_reads},"
        f"clear_before_sync:{state.pending_cleared_before_authority_sync},"
        f"reissue:{state.same_action_reissued_after_done},stale_status:{state.daemon_status_from_stale_summary},"
        f"terminal_before_cleanup:{state.terminal_status_written_before_cleanup},"
        f"repair_before_receipt:{state.repair_blocker_before_receipt_read}"
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
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, object]:
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.microstep_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(flowguard["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
        "model_boundary": (
            "full lifecycle control-plane microstep model; validates daemon "
            "read/reconcile/sync/clear/schedule/write order, not business content bodies"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
