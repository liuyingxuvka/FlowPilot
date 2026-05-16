"""Run checks for the FlowPilot route mutation activation/display model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_route_mutation_activation_model as model


REQUIRED_LABELS = (
    "reviewer_block_records_route_mutation_need",
    "pm_proposes_return_repair_candidate_route",
    "pm_proposes_supersede_replacement_candidate_route",
    "pm_proposes_branch_then_continue_candidate_route",
    "pm_proposes_sibling_branch_replacement_candidate_route",
    "controller_records_stale_evidence_before_route_recheck",
    "controller_supersedes_old_current_node_packet_for_route_mutation",
    "process_flowguard_officer_simulates_candidate_route",
    "product_flowguard_officer_checks_candidate_route",
    "human_like_reviewer_challenges_candidate_route",
    "pm_activates_checked_candidate_route",
    "execution_frontier_enters_activated_mutation_node",
    "reviewer_reruns_same_scope_replay_after_route_mutation",
    "route_sign_displays_activated_current_mutation_node",
    "route_mutation_activation_display_complete",
)


HAZARD_EXPECTED_FAILURES = {
    "active_flow_overwritten_before_activation": "candidate route overwrote active flow.json before checked PM activation",
    "frontier_entered_candidate_before_activation": "execution frontier entered candidate node before route activation",
    "candidate_route_displayed_before_activation": "candidate repair route was displayed as current before activation",
    "activation_without_process_recheck": "PM activated candidate route before process FlowGuard recheck",
    "activation_without_product_or_reviewer_recheck": "PM activated candidate route before product FlowGuard recheck",
    "missing_topology_strategy": "route mutation proposal lacks an explicit topology strategy",
    "supersede_original_forced_to_return": "supersede_original mutation was incorrectly forced to return to the old node",
    "return_repair_without_return_target": "return_to_original mutation lacks repair_return_to_node_id",
    "sibling_replacement_without_affected_siblings": "sibling_branch_replacement mutation lacks affected sibling nodes",
    "sibling_replacement_without_replay_scope": "sibling_branch_replacement mutation lacks replay scope",
    "old_sibling_evidence_reused_after_replacement": "old sibling evidence was reused as current proof after replacement",
    "route_recheck_before_old_packet_superseded": "route recheck started while the old current-node packet still blocked PM work",
    "final_scan_before_same_scope_replay_after_mutation": "final ledger started before same-scope replay after route mutation",
    "repair_rendered_as_final_mainline": "repair node was rendered as a final sequential mainline stage",
    "superseded_node_visible_as_pending": "superseded old node remained visible as a pending or active obligation",
    "stale_evidence_reused_before_activation": "PM activated candidate route before stale evidence was invalidated",
    "generated_files_only_display": "route sign display used generated files without user-visible receipt",
    "sealed_body_boundary_broken": "route mutation display weakened the sealed packet/result body boundary",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|block={state.reviewer_block_recorded}|"
        f"proposal={state.pm_mutation_proposed},{state.topology_strategy}|"
        f"fields=repair:{state.repair_node_id_declared},of:{state.repair_of_node_id_declared},"
        f"return:{state.return_target_declared},superseded:{state.superseded_nodes_declared},"
        f"continue:{state.continue_target_declared},affected_siblings:{state.affected_sibling_nodes_declared},"
        f"replay_scope:{state.replay_scope_declared}|early=active:{state.active_route_overwritten_before_activation},"
        f"frontier:{state.frontier_entered_candidate_before_activation},display:{state.candidate_route_displayed_as_current}|"
        f"checks=stale:{state.stale_evidence_invalidated},packet_superseded:{state.old_current_node_packet_superseded},"
        f"process:{state.process_recheck_passed},"
        f"product:{state.product_recheck_passed},review:{state.reviewer_recheck_passed},pm:{state.pm_activation_recorded}|"
        f"entry={state.candidate_node_entry_recorded},same_scope_replay:{state.same_scope_replay_rerun_after_mutation},"
        f"final_ledger:{state.final_ledger_started}|visible={state.route_visible_as_current},"
        f"receipt:{state.display_receipt_recorded},topology:{state.mermaid_topology_projected},"
        f"final_append:{state.repair_rendered_as_final_mainline},sup_pending:{state.superseded_node_shown_as_pending},"
        f"forced_return:{state.forced_return_for_supersede},old_sibling_evidence:{state.old_sibling_evidence_reused_as_current},"
        f"files_only:{state.generated_files_only_display},"
        f"sealed:{state.sealed_body_boundary_preserved}"
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
        "production_conformance_replay": (
            "skipped_with_reason: this runner validates the route-mutation "
            "activation/display model; production behavior is covered by router "
            "and user-flow-diagram tests"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
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
