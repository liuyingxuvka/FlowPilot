"""Run FlowPilot pre-work FlowGuard node-gate checks."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Sequence

from flowguard import Explorer

import flowpilot_prework_flowguard_gate_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_prework_flowguard_gate_results.json"
)

REQUIRED_LABELS = (
    "node_prework_flow_started",
    "pm_accepts_node_design",
    "pm_records_node_context_package",
    "runtime_issues_prework_flowguard_packet",
    "flowguard_operator_selects_route_mix",
    "flowguard_operator_records_pm_visible_artifacts",
    "flowguard_prework_passes_current_generation",
    "flowguard_prework_blocks_node_design",
    "pm_repairs_node_design_after_prework_block",
    "runtime_issues_worker_packet_after_prework",
    "worker_submits_node_result",
    "runtime_issues_post_result_flowguard",
    "post_result_flowguard_passes",
    "runtime_issues_independent_reviewer_packet",
    "reviewer_passes_independently",
    "node_completed_after_reviewer",
    "node_prework_flow_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "pm_optional_prework": "PM made mandatory pre-work FlowGuard optional",
    "context_before_node_design": "PM context package recorded before node design",
    "stale_context_after_repair": "PM context package is stale for repair generation",
    "prework_context_missing": "pre-work FlowGuard packet missing PM node context package",
    "prework_before_node_design": "pre-work FlowGuard issued before PM node design",
    "route_mix_missing": "PM-visible artifacts recorded before FlowGuard route selection",
    "pm_visible_artifacts_missing": "pre-work FlowGuard passed before PM-visible artifacts",
    "stale_prework_after_repair": "worker packet issued before current-generation pre-work FlowGuard pass",
    "worker_before_prework": "worker packet issued before current-generation pre-work FlowGuard pass",
    "worker_context_missing": "worker packet issued without current PM node context package",
    "prework_block_without_pm_repair": "worker released after pre-work block without PM repair",
    "flowguard_operator_route_mutation": "FlowGuard operator mutated route instead of reporting to PM",
    "post_result_context_missing": "post-result FlowGuard packet missing PM node context package",
    "post_result_flowguard_skipped": "Reviewer packet issued before post-result FlowGuard pass",
    "reviewer_before_post_result_flowguard": "Reviewer packet issued before post-result FlowGuard pass",
    "reviewer_context_missing": "Reviewer packet missing PM node context package",
    "reviewer_not_independent": "Reviewer pass was not independent",
    "reviewer_pm_scoped_only": "Reviewer was scoped only by PM rather than independent node contract review",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|repair={state.repair_generation}|"
        f"context={state.pm_context_package_accepted},{state.context_package_generation}|"
        f"prework={state.prework_packet_issued},{state.prework_routes_selected},"
        f"{state.prework_artifacts_pm_visible},{state.prework_passed},"
        f"{state.prework_pass_generation},{state.prework_blocked}|"
        f"pm={state.pm_node_design_accepted},{state.pm_repair_decision_recorded}|"
        f"worker={state.worker_packet_issued},{state.worker_context_attached},{state.worker_result_submitted}|"
        f"post_fg={state.post_result_flowguard_issued},{state.post_result_context_attached},{state.post_result_flowguard_passed}|"
        f"review={state.reviewer_packet_issued},{state.reviewer_context_attached},{state.reviewer_independent},{state.reviewer_passed}|"
        f"node={state.node_completed}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = [[]]
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                edges.append([])
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
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    target_failures = model.invariant_failures(model.target_success_state())
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and not target_failures,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "target_plan_failures": target_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_success and any(target in can_reach_success for _label, target in outgoing):
                can_reach_success.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": bool(success) and not stuck and 0 in can_reach_success,
        "success_state_count": len(success),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "initial_can_reach_success": 0 in can_reach_success,
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


def _model_test_alignment_report() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    runtime_text = (repo_root / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py").read_text(encoding="utf-8")
    test_text = (repo_root / "tests" / "test_flowpilot_high_standard_control_flow.py").read_text(encoding="utf-8")
    obligations = {
        "prework_scope": "node_prework_flowguard" in runtime_text,
        "prework_packet_function": "ensure_node_prework_flowguard_packet" in runtime_text,
        "worker_gate_function": "_node_prework_flowguard_accepted" in runtime_text,
        "node_context_package": "node_context_package" in runtime_text,
        "context_current_function": "_node_context_package_current" in runtime_text,
        "route_selection_policy": "route_selection_policy" in runtime_text,
        "pm_visible_artifacts": "pm_visibility_policy" in runtime_text,
        "prework_runtime_tests": "test_node_task_requires_prework_flowguard_gate" in test_text,
        "context_attachment_tests": "test_node_context_package_follows_flowguard_worker_and_reviewer_packets" in test_text,
        "prework_repair_tests": "test_prework_flowguard_block_returns_to_pm_and_requires_fresh_prework" in test_text,
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "tests/test_flowpilot_high_standard_control_flow.py",
        ],
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    alignment = _model_test_alignment_report()
    target_state = model.target_success_state()
    target_plan = {
        "ok": not model.invariant_failures(target_state),
        "state": target_state.__dict__,
        "failures": model.invariant_failures(target_state),
    }
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(alignment["ok"])
        and bool(target_plan["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "model_test_alignment": alignment,
        "target_prework_flowguard_plan": target_plan,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    result = run_checks()
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
