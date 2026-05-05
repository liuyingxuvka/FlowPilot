"""Run checks for the FlowPilot barrier-bundle equivalence model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import barrier_equivalence_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "barrier_equivalence_results.json"
REQUIRED_LABELS = (
    "barrier_bundle_run_started",
    "startup_barrier_bundle_passed",
    "material_barrier_bundle_passed",
    "product_architecture_barrier_bundle_passed",
    "root_contract_barrier_bundle_passed",
    "child_skill_manifest_barrier_bundle_passed",
    "route_skeleton_barrier_bundle_passed",
    "current_node_barrier_bundle_passed",
    "parent_backward_barrier_bundle_passed",
    "final_closure_barrier_bundle_passed",
    "completion_recorded_after_all_equivalent_obligations",
)

HAZARD_EXPECTED_FAILURES = {
    "ai_discretion_bypass": "AI discretion was used to downgrade or skip a barrier",
    "controller_reads_sealed_body": "Controller read a sealed packet/result body",
    "controller_originates_evidence": "Controller originated project evidence",
    "controller_summarizes_body": "Controller summarized sealed body content",
    "wrong_role_approval": "wrong role approval was used for a bundled gate",
    "missing_required_role_slice": "barrier bundle missing a required role slice",
    "missing_required_obligation": "barrier bundle missing a required legacy obligation",
    "missing_reviewer_gate": "reviewer gate missing from bundled evidence",
    "missing_officer_gate": "FlowGuard officer gate missing from bundled evidence",
    "cache_reuse_after_input_change": "cache reuse claimed after input hash changed",
    "cache_reuse_after_source_change": "cache reuse claimed after source hash changed",
    "cache_reuse_with_bad_evidence_hash": "cache reuse claimed with invalid evidence hash",
    "stale_evidence_used": "stale evidence was used by a barrier",
    "route_mutation_without_stale_mark": "route mutation did not mark affected evidence stale",
    "route_mutation_without_frontier_rewrite": "route mutation did not rewrite the frontier",
    "final_closure_without_all_obligations": "final closure passed before all legacy obligations were covered",
    "final_closure_without_clean_ledger": "final closure passed without clean final ledger",
    "final_closure_without_terminal_replay": "final closure passed without terminal backward replay",
    "completion_without_all_barriers": "completion recorded before every barrier bundle passed",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|next={state.next_barrier_index}|"
        f"barriers={state.passed_barrier_mask}|obligations={state.obligation_mask}|"
        f"ctrl={state.controller_read_sealed_body},"
        f"{state.controller_originated_evidence},{state.controller_summarized_body}|"
        f"disc={state.ai_discretion_used}|wrong_role={state.wrong_role_approval_used}|"
        f"missing={state.missing_required_role_slice},{state.missing_required_obligation}|"
        f"reviewer={state.reviewer_gate_missing}|officer={state.officer_gate_missing}|"
        f"cache={state.cache_reuse_claimed},{state.input_hash_same},"
        f"{state.source_hash_same},{state.evidence_hash_valid}|"
        f"stale={state.stale_evidence_used}|mutation={state.route_mutation_recorded},"
        f"{state.stale_evidence_marked},{state.frontier_rewritten_after_mutation}|"
        f"final={state.final_ledger_clean},{state.terminal_backward_replay_passed}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
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
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    invariant_failures = graph["invariant_failures"]
    complete_states = [state for state in states if model.is_success(state)]
    missing_obligations = []
    if complete_states:
        complete = complete_states[0]
        missing_obligations = [
            obligation
            for obligation, bit in model.OBLIGATION_BITS.items()
            if not complete.obligation_mask & bit
        ]
    return {
        "ok": (
            not invariant_failures
            and not missing_labels
            and bool(complete_states)
            and not missing_obligations
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": len(complete_states),
        "blocked_state_count": sum(1 for state in states if state.status == "blocked"),
        "missing_obligations_at_completion": missing_obligations,
        "legacy_obligation_count": len(model.LEGACY_OBLIGATIONS),
        "barrier_count": len(model.BARRIER_ORDER),
        "invariant_failures": invariant_failures,
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
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


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    control_overhead_comparison = {
        "schema_version": "flowpilot.barrier_control_overhead_comparison.v1",
        "baseline_active_run_prompt_deliveries_before_route": 26,
        "new_pre_route_barriers_before_route": 6,
        "control_transition_reduction_ratio": 0.769,
        "semantics": "control checks are bundled; role packets, approvals, hashes, stale markers, and final replay are not removed",
    }
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "control_overhead_comparison": control_overhead_comparison,
    }


def main() -> int:
    result = run_checks()
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
