"""Run checks for the FlowPilot route display projection model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_route_display_model as model


REQUIRED_LABELS = (
    "startup_no_route_displays_stage_mermaid_with_ledger",
    "pm_writes_route_draft_with_real_nodes_and_checklists",
    "router_refreshes_mermaid_from_canonical_route_source",
    "chat_fallback_displays_mermaid_route_sign_and_records_ledger",
    "cockpit_displays_same_canonical_graph_and_records_receipt",
    "pm_activates_reviewed_route_and_marks_display_dirty",
    "major_node_entry_marks_route_sign_dirty",
    "current_node_completion_moves_to_next_and_marks_display_dirty",
    "route_mutation_or_review_failure_return_marks_display_dirty",
    "route_display_projection_lifecycle_complete",
)


HAZARD_EXPECTED_FAILURES = {
    "controller_invents_route_nodes": "user-visible route map was not derived from canonical route/frontier/snapshot",
    "route_draft_keeps_startup_unknown_mermaid": "route draft or active route existed but user-visible Mermaid still showed route=unknown or node=unknown",
    "chat_fallback_bullet_list_after_route_draft": "chat fallback displayed bullet list instead of Mermaid route sign",
    "degraded_mermaid_without_reason": "chat fallback degraded without recording a Mermaid source reason",
    "cockpit_chat_source_drift": "Cockpit route map and chat fallback used different route sources",
    "route_checklists_simplified_away": "route display dropped real major nodes or node checklists",
    "route_statuses_collapsed": "completed, active, selected, blocked, or pending node states were conflated",
    "generated_files_without_visible_receipt": "generated route diagram files existed without a user-visible display receipt",
    "sealed_body_boundary_broken_by_display": "route display repair broke sealed packet/result body boundary",
    "internal_source_fields_visible_to_user": "user-visible route sign leaked internal source fields or evidence tables",
    "evidence_table_visible_to_user": "user-visible route sign leaked internal source fields or evidence tables",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|phase={state.route_phase}|startup={state.startup_displayed}|steps={state.steps}|"
        f"route={state.route_source_exists},{state.route_source_kind},canon={state.route_source_is_canonical},"
        f"nodes={state.route_nodes_real},checklist={state.route_checklists_preserved},"
        f"statuses={state.route_statuses_distinct}|aliases={state.route_node_aliases_supported},"
        f"{state.frontier_aliases_supported},draft={state.draft_route_fallback_supported},"
        f"snapshot={state.snapshot_fallback_supported}|gen={state.route_generation},"
        f"diagram={state.diagram_generation},visible={state.visible_generation}|"
        f"mermaid={state.mermaid_source_available},unknown={state.mermaid_route_unknown},"
        f"{state.mermaid_node_unknown},route_nodes={state.mermaid_uses_route_nodes},"
        f"source={state.mermaid_uses_canonical_source}|chat={state.chat_display_kind},"
        f"ledger={state.user_dialog_display_ledger_recorded}|cockpit={state.cockpit_available},"
        f"{state.cockpit_display_kind},{state.cockpit_receipt_recorded},"
        f"same={state.same_graph_source_for_chat_and_cockpit}|files_only={state.generated_files_only}|"
        f"boundary={state.sealed_body_boundary_preserved},source_leak={state.internal_source_fields_visible},"
        f"evidence={state.evidence_table_visible},invented={state.controller_invented_nodes}"
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
        "terminal_state_count": len(terminal),
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


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "canonical_route_sign_projection",
        "scenarios": list(model.SCENARIOS),
        "principles": [
            "display_plan.json remains a native visible-plan projection, not the only user-facing route map",
            "Mermaid/chat route sign and Cockpit route map share canonical route/frontier/snapshot semantics",
            "draft routes are valid display sources before flow.json activation",
            "route_state_snapshot.route.nodes is the stable fallback when route file aliases drift",
            "display receipt is required; generated files alone do not satisfy user visibility",
        ],
        "minimal_runtime_change_set": [
            "Teach flowpilot_user_flow_diagram.py route/frontier aliases and draft/snapshot fallback.",
            "Refresh user-flow-diagram.* during sync_display_plan and use its Mermaid markdown as chat fallback display_text when route data exists.",
            "Keep display_plan.json as host/native projection and record degraded reasons if Mermaid generation cannot use canonical route data.",
        ],
    }


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    skipped_checks = {
        "production_mutation": (
            "covered_elsewhere: this runner validates the display lifecycle model; "
            "runtime conformance is exercised by route-display unit tests and live-run projection checks"
        ),
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "current_implementation_failure_trace": model.current_implementation_failure_trace(),
        "architecture_candidate": _architecture_candidate(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing JSON result payload.")
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
