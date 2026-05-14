"""Run checks for the FlowPilot daemon durable reconciliation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_daemon_reconciliation_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_daemon_reconciliation_results.json"

REQUIRED_LABELS = (
    "daemon_tick_starts_durable_reconciliation_barrier",
    "role_output_submitted_while_router_waits",
    "heartbeat_opens_rehydrate_pending_action",
    "heartbeat_opens_rehydrate_pending_action_after_role_output",
    "role_output_submitted_while_rehydrate_pending",
    "controller_writes_complete_rehydrate_receipt",
    "controller_writes_incomplete_rehydrate_receipt",
    "controller_writes_blocked_rehydrate_receipt",
    "daemon_applies_complete_receipt_and_clears_pending",
    "daemon_converts_incomplete_receipt_to_control_blocker",
    "daemon_surfaces_blocked_receipt_as_control_blocker",
    "daemon_reconciles_role_output_to_router_event",
    "daemon_idempotently_ignores_already_recorded_role_output",
    "daemon_computes_next_action_after_reconciliation",
    "daemon_returns_control_blocker_after_reconciliation",
    "terminal_stop_after_reconciliation_contract_checked",
)

HAZARD_EXPECTED_FAILURES = {
    "completed_controller_action_repeated": "daemon repeated a completed or blocked Controller action instead of clearing or blocking",
    "done_receipt_without_stateful_postconditions": "stateful Controller receipt was marked done without applying Router postconditions",
    "incomplete_stateful_receipt_silently_done": "incomplete stateful Controller receipt was accepted without a control blocker",
    "submitted_role_output_left_in_ledger": "submitted expected role output was left only in durable storage",
    "canonical_artifact_flag_not_synced": "canonical role-output artifact existed without synced Router event flag",
    "stale_snapshot_overwrites_role_output_event": "daemon saved a stale router_state snapshot over newer durable role output",
    "computed_from_pending_before_reconciliation": "daemon computed next action from stale pending_action before durable reconciliation",
    "role_wait_not_cleared_after_event": "expected role wait remained current after Router recorded the role output",
    "duplicate_role_output_consumption": "role output durable evidence was consumed more than once",
    "blocked_receipt_repeated_instead_of_blocker": "daemon repeated a completed or blocked Controller action instead of clearing or blocking",
    "invalid_role_output_silently_accepted": "invalid or unauthorized role output was accepted as a Router event",
    "receipt_and_role_output_interleaving_starves_role_output": "submitted expected role output was left only in durable storage",
}


def _state_id(state: model.State) -> str:
    return (
        f"life={state.lifecycle}|daemon={state.daemon_alive}|"
        f"barrier={state.reconciliation_barrier_started}|"
        f"pending={state.pending_action_kind},{state.pending_action_status},"
        f"returned_again={state.pending_action_returned_again}|"
        f"compute={state.next_action_computed},before_reconcile={state.computed_before_reconciliation}|"
        f"receipt={state.controller_receipt_status},{state.controller_receipt_payload_quality},"
        f"reconciled={state.controller_receipt_reconciled},cleared={state.pending_cleared_after_receipt},"
        f"post={state.stateful_postconditions_applied},blocker={state.control_blocker_written}|"
        f"role_output={state.role_output_ledger_submitted},valid={state.role_output_envelope_valid},"
        f"expected={state.role_output_event_expected},artifact={state.canonical_artifact_exists},"
        f"reconciled={state.role_output_reconciled},event={state.router_event_recorded},"
        f"flag={state.router_event_flag_synced},scoped={state.scoped_event_recorded},"
        f"count={state.role_output_consumption_count},wait_cleared={state.role_wait_cleared_after_event}|"
        f"stale={state.stale_daemon_snapshot_loaded},{state.stale_snapshot_saved_after_external_event}|"
        f"invalid_accept={state.invalid_role_output_accepted}"
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
        "production_conformance_replay": (
            "skipped_with_reason: this model is a model-miss design check; "
            "production replay should be added with the Router fix"
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
