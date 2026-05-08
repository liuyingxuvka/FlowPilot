"""Run checks for the FlowPilot packet lifecycle model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flowguard import Explorer

import flowpilot_packet_lifecycle_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_packet_lifecycle_results.json"

HAZARD_EXPECTED_FAILURES = {
    "stale_hash_after_body_repair": "dispatch passed without envelope/ledger packet body hash identity",
    "packet_body_alias_not_normalized": "dispatch passed without envelope/ledger packet body hash identity",
    "result_body_alias_not_normalized": "dispatch passed without envelope/ledger packet body hash identity",
    "packet_open_envelope_only": "result relay occurred before packet open receipts and result ledger absorption",
    "result_without_ledger_absorption": "result relay occurred before packet open receipts and result ledger absorption",
    "result_open_envelope_only": "reviewer pass occurred without complete packet/result receipts and agent role authority",
    "agent_id_role_string": "reviewer pass occurred without complete packet/result receipts and agent role authority",
    "worker_write_without_grant": "worker project write occurred before a current-node write grant",
    "pm_decision_clears_blocker_without_followup": "PM repair decision cleared blocker without corrected follow-up re-audit",
    "fatal_followup_without_pm_decision": "fatal protocol violation follow-up was accepted before PM repair decision",
    "pm_absorbs_without_packet_group_audit": "PM absorbed research before reviewer packet-group runtime audit passed",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|steps={state.steps}|"
        f"dispatch={state.dispatch_gate_checked},{state.packet_body_hash_identity_synced},"
        f"{state.packet_body_path_alias_normalized},{state.result_body_path_alias_normalized},"
        f"{state.reviewer_dispatch_passed}|packet={state.packet_relayed_by_controller},"
        f"{state.packet_open_envelope_receipt},{state.packet_open_ledger_receipt}|"
        f"grant={state.write_grant_issued}|"
        f"result={state.worker_result_written},{state.result_envelope_exists},"
        f"{state.worker_project_write_performed},"
        f"{state.result_ledger_absorbed},{state.result_relayed_by_controller},"
        f"{state.result_open_envelope_receipt},{state.result_open_ledger_receipt}|"
        f"agent={state.completed_agent_id_maps_to_role}|"
        f"review={state.reviewer_runtime_audit_passed}|"
        f"pm={state.pm_absorbed_reviewed_research},{state.pm_advanced_node}|"
        f"blocker={state.control_blocker_active},{state.control_blocker_lane},{state.pm_repair_decision_recorded},"
        f"{state.followup_event_already_recorded},{state.followup_reaudit_passed}"
    )


def _build_graph() -> dict[str, object]:
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


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    success = [state for state in terminals if model.is_success(state)]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(success),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminals),
        "success_state_count": len(success),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _run_flowguard_explorer() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_LABELS,
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


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    hazards = _check_hazards()
    explorer = _run_flowguard_explorer()
    ok = bool(safe_graph["ok"] and progress["ok"] and hazards["ok"] and explorer["ok"])
    return {
        "ok": ok,
        "model": "flowpilot_packet_lifecycle",
        "safe_graph": safe_graph,
        "progress": progress,
        "hazard_detection": hazards,
        "flowguard_explorer": explorer,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if not args.no_write:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
