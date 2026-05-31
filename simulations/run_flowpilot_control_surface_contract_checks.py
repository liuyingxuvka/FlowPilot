"""Run checks for the FlowPilot control-surface contract model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_control_surface_contract_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_control_surface_contract_results.json"

REQUIRED_LABELS = (
    "select_success",
    "accept_control_surface_contract",
    "block_new_current_schema_ignored",
    "block_implicit_run_root_fallback",
    "block_unreadable_evidence_crash",
    "block_packet_contract_not_role_symmetric",
    "block_ack_result_acceptance_conflated",
    "block_accepted_packet_mutated",
    "block_old_generation_result_accepted",
    "block_unsupported_historical_current_fields",
)

EXPECTED_HAZARD_FAILURES = {
    "new_current_schema_ignored_accepted": "risk scenario was accepted: new_current_schema_ignored",
    "fallback_scans_project_root_accepted": "risk scenario was accepted: fallback_scans_project_root",
    "invalid_utf8_crashes_audit_accepted": "risk scenario was accepted: invalid_utf8_crashes_audit",
    "pm_only_packet_contract_accepted": "risk scenario was accepted: pm_only_packet_contract",
    "ack_treated_as_result_accepted": "risk scenario was accepted: ack_treated_as_result",
    "accepted_result_reassigned_accepted": "risk scenario was accepted: accepted_result_reassigned",
    "old_generation_result_accepted_accepted": "risk scenario was accepted: old_generation_result_accepted",
    "unsupported_historical_pointer_accepted_accepted": "risk scenario was accepted: unsupported_historical_pointer_accepted",
    "success_overblocked": "safe control surface was blocked",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"resolver_new={state.resolver_accepts_new_fields}|"
        f"explicit_root={state.resolver_uses_explicit_run_root}|"
        f"fallback_root={state.resolver_falls_back_to_project_root}|"
        f"safe_read={state.evidence_reader_returns_structured_error}|"
        f"decode_crash={state.evidence_reader_crashes_on_decode}|"
        f"roles={','.join(state.packet_contract_roles)}|"
        f"separate={state.ack_result_accepted_separate}|"
        f"accepted_mutated={state.accepted_packet_reassigned},{state.accepted_packet_ack_regressed}|"
        f"generation={state.result_generation}/{state.current_generation}|"
        f"quarantine={state.stale_generation_quarantined}"
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
        failures = model.hard_check_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_safe_states(state):
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
        "invariant_failures": invariant_failures,
        "edge_count": sum(len(outgoing) for outgoing in edges),
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
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
        failures = model.hard_check_failures(state)
        expected = EXPECTED_HAZARD_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


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
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    hazards = _check_hazards()
    explorer = _flowguard_report()
    skipped_checks: dict[str, object] = {}
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(hazards["ok"]) and bool(explorer["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "hazard_checks": hazards,
        "flowguard_explorer": explorer,
        "scenario_matrix": model.scenario_matrix(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
