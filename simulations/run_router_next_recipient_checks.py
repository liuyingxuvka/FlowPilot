"""Run checks for the FlowPilot explicit next-recipient model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import router_next_recipient_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "router_next_recipient_results.json"

HAZARD_EXPECTED_FAILURES = {
    "controller_unknown_next": "Controller lacks explicit next recipient/action",
    "direct_role_pass_without_dispatch": "role pass event was accepted without router-dispatched work package",
    "dummy_route_activation": "route activated from dummy route instead of reviewed draft",
    "controller_content_decision": "Controller made a content decision",
    "double_worker_owner": "same worker packet assigned to more than one owner",
    "reissue_wrong_role": "control-plane reissue was routed to the wrong role",
    "resume_without_ledger_next": "resume continued without deriving next recipient from ledger",
    "parent_repair_without_pm_segment_decision": "parent replay repair proceeded without PM segment decision",
    "frontier_rewrite_without_stale_mark": "frontier rewritten without marking affected evidence stale",
    "ui_uses_stale_running_index_entry": "UI snapshot used stale index running entry as active task",
    "completion_missing_legacy_obligation": "completion recorded before all legacy obligations were preserved",
}


def _state_id(state: model.State) -> str:
    return (
        f"step={state.step}|status={state.status}|obligations={state.obligations}|"
        f"last={state.last_action}->{state.last_recipient}|"
        f"explicit={state.controller_has_explicit_next}|"
        f"direct_pass={state.direct_external_pass_event_used}|"
        f"route_source={state.route_activation_source}|"
        f"owner={state.packet_owner},double={state.second_packet_owner_assigned}|"
        f"dispatch={state.reviewer_dispatch_allowed}|"
        f"lane={state.rejection_lane},target={state.reissue_target},"
        f"target_ok={state.reissue_target_matches_owner}|"
        f"resume={state.resume_next_derived_from_ledger}|"
        f"parent_pm={state.parent_segment_pm_decision_recorded}|"
        f"repair={state.stale_evidence_marked},{state.frontier_rewritten_after_repair}|"
        f"ui={state.ui_active_run_resolved},{state.ui_snapshot_from_canonical},"
        f"stale_index={state.ui_used_stale_index_running_entry}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int, str]]] = []
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
            edges[source_index].append((transition.label, index[transition.state], transition.recipient))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    complete_states = [state for state in states if model.is_success(state)]
    missing_obligations: list[str] = []
    if complete_states:
        complete = complete_states[0]
        missing_obligations = [
            obligation
            for obligation, bit in model.OBLIGATION_BITS.items()
            if not complete.obligations & bit
        ]
    missing_recipients = [
        {"source": source, "label": label, "target": target}
        for source, outgoing in enumerate(edges)
        for label, target, recipient in outgoing
        if recipient in {"", "none", "unknown"}
    ]
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and bool(complete_states)
            and not missing_obligations
            and not missing_recipients
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": len(complete_states),
        "blocked_state_count": sum(1 for state in states if state.status == "blocked"),
        "missing_obligations_at_completion": missing_obligations,
        "missing_recipient_edges": missing_recipients,
        "legacy_obligation_count": len(model.LEGACY_OBLIGATIONS),
        "invariant_failures": graph["invariant_failures"],
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target, _recipient in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(source)
                changed = True
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True

    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": not stuck and 0 in can_reach_success and 0 in can_reach_terminal,
        "initial_can_reach_success": 0 in can_reach_success,
        "initial_can_reach_terminal": 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
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


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    result = {
        "ok": bool(safe_graph["ok"] and progress["ok"] and explorer["ok"] and hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "confidence_boundary": "abstract next-recipient model; pair with router runtime tests",
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
