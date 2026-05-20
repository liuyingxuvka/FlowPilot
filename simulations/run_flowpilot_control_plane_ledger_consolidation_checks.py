"""Run checks for the FlowPilot control-plane ledger consolidation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_control_plane_ledger_consolidation_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_control_plane_ledger_consolidation_results.json"

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    "foreground_receipt_writes_scheduler_during_daemon": "foreground receipt path mutated Router scheduler ledger while daemon owned folding",
    "readback_permission_kills_daemon": "transient ledger access denial released daemon lock as error",
    "pending_action_overrides_controller_ledger": "legacy pending_action overrode Controller action ledger authority",
    "worker_event_collapses_batch_to_worker_a": "batch wait projection did not derive missing roles from member state",
    "stale_passive_wait_left_open": "stale passive wait remained unresolved after prerequisite resolved",
    "signed_envelope_mutated_for_projection": "signed packet or result envelope was mutated after relay",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|daemon={state.daemon_mode},"
        f"{state.daemon_live}|receipt={state.controller_receipt_persisted},"
        f"owner={state.scheduler_fold_owner},fg_write={state.foreground_mutated_scheduler},"
        f"folded={state.scheduler_row_folded_from_receipt},"
        f"action_meta={state.action_local_receipt_metadata_written}|"
        f"json_denied={state.daemon_critical_json_access_denied},"
        f"fresh_write={state.fresh_runtime_write_activity},"
        f"deferred={state.daemon_deferred_tick},"
        f"lock_error={state.daemon_lock_released_error}|"
        f"ledger_auth={state.controller_action_ledger_authority},"
        f"pending={state.legacy_pending_action_present},"
        f"pending_apply={state.legacy_pending_apply_required},"
        f"action_apply={state.controller_action_apply_required},"
        f"mode={state.controller_action_wait_mode},"
        f"decision_ledger={state.decision_used_controller_ledger},"
        f"projection={state.pending_action_labeled_projection}|"
        f"batch={state.batch_member_roles},returned={state.batch_returned_roles},"
        f"inferred={state.event_inferred_role},missing={state.projected_missing_roles}|"
        f"passive={state.passive_wait_open},resolved={state.passive_wait_prerequisite_resolved},"
        f"superseded={state.passive_wait_superseded_or_reconciled},"
        f"open_rows={state.passive_wait_in_open_rows}|"
        f"signed={state.signed_envelope_relayed},mutated={state.signed_envelope_mutated},"
        f"sidecar={state.sidecar_projection_written}"
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
    terminal = [state for state in graph["states"] if model.is_terminal(state)]
    accepted = sorted(state.scenario for state in terminal if state.status == "accepted")
    rejected = sorted(state.scenario for state in terminal if state.status == "rejected")
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted) == set(model.VALID_SCENARIOS)
        and set(rejected) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted,
        "rejected_scenarios": rejected,
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
        scenario_failures = model.consolidation_failures(state)
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
            "focused control-plane ledger consolidation model; runtime tests "
            "and install sync remain required for production confidence"
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
