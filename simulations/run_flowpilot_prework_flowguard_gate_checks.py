"""Run FlowPilot current-node route-change gate checks."""

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
    "current_node_flow_started",
    "pm_self_checks_node_entry",
    "pm_passes_ordinary_node_plan",
    "pm_records_node_context_package",
    "runtime_issues_node_plan_reviewer",
    "reviewer_passes_node_plan",
    "runtime_issues_worker_packet_after_reviewer",
    "worker_submits_node_result",
    "runtime_issues_post_result_flowguard",
    "post_result_flowguard_passes",
    "runtime_issues_independent_reviewer_packet",
    "reviewer_passes_independently",
    "node_completed_after_reviewer",
    "current_node_flow_complete",
    "pm_stages_route_redesign_plan",
    "runtime_issues_route_redesign_flowguard",
    "flowguard_simulates_current_route_plan",
    "flowguard_route_redesign_passes",
    "flowguard_route_redesign_blocks",
    "pm_repairs_route_plan_after_flowguard_block",
    "runtime_issues_pm_flowguard_acceptance_packet",
    "pm_absorbs_flowguard_report",
    "pm_rewrites_route_from_flowguard_advice",
    "runtime_issues_route_redesign_reviewer_packet",
    "reviewer_passes_pm_absorption_package",
    "route_redesign_committed_after_review",
    "route_redesign_flow_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "pm_optional_flowguard": "PM made structural route FlowGuard optional",
    "flowguard_scope_missing": "FlowGuard did not bind the current route plan as simulation subject",
    "flowguard_validation_path_missing": "FlowGuard did not simulate work, validation, failure, and repair paths",
    "flowguard_operator_route_mutation": "FlowGuard operator mutated route instead of reporting to PM",
    "pm_accepts_blocked_flowguard": "PM accepted a blocked FlowGuard route result",
    "stale_flowguard_after_route_rewrite": "PM absorbed stale or missing FlowGuard result",
    "reviewer_before_pm_absorption": "Reviewer inspected route effect before PM absorbed FlowGuard result",
    "route_mutation_without_pm_absorption": "route mutation committed without PM FlowGuard absorption",
    "route_reviewer_before_pm_absorption": "Reviewer packet issued before current PM FlowGuard absorption",
    "route_commit_before_reviewer": "route mutation committed before Reviewer pass",
    "worker_before_node_plan_reviewer": "worker packet issued before ordinary node plan Reviewer pass",
    "worker_context_missing": "worker packet missing PM node context package",
    "worker_replans_broad_leaf": "Worker replanned a broad leaf instead of PM route deepening",
    "node_plan_reviewer_demands_worker_artifacts": "Node plan Reviewer required Worker artifacts before Worker dispatch",
    "node_plan_reviewer_treats_plan_as_result_proof": "Node plan Reviewer treated PM plan as Worker-result proof",
    "post_result_flowguard_skipped": "Reviewer packet issued before post-result FlowGuard pass",
    "reviewer_not_independent": "Reviewer pass was not independent",
    "final_reviewer_without_artifacts": "Worker result Reviewer passed without current Worker artifacts",
    "final_reviewer_accepts_without_worker_artifacts": "Worker result Reviewer accepted without current Worker artifacts",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|gen={state.route_plan_generation},"
        f"{state.flowguard_generation},{state.pm_absorption_generation}|"
        f"decision={state.node_plan_decision}|"
        f"ordinary={state.node_context_package_accepted},"
        f"{state.node_plan_reviewer_used_plan_stage_standard},"
        f"{state.node_plan_reviewer_passed},{state.worker_packet_issued},"
        f"{state.post_result_flowguard_passed},{state.final_reviewer_passed},"
        f"{state.final_reviewer_used_result_stage_standard},"
        f"{state.final_reviewer_inspected_worker_artifacts},{state.node_completed}|"
        f"route={state.route_plan_staged},"
        f"{state.route_redesign_flowguard_packet_issued},"
        f"{state.flowguard_current_subject_bound},"
        f"{state.flowguard_simulated_work_validation_failure_paths},"
        f"{state.flowguard_passed},{state.pm_absorbed_flowguard},"
        f"{state.route_reviewer_passed},{state.route_mutation_committed}"
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
    ordinary_target_failures = model.invariant_failures(model.ordinary_node_success_state())
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and not target_failures
            and not ordinary_target_failures
        ),
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "target_route_redesign_failures": target_failures,
        "target_ordinary_node_failures": ordinary_target_failures,
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
    model_text = (repo_root / "simulations" / "flowpilot_prework_flowguard_gate_model.py").read_text(encoding="utf-8")
    runtime_text = (repo_root / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py").read_text(encoding="utf-8")
    test_text = (repo_root / "tests" / "test_flowpilot_high_standard_control_flow.py").read_text(encoding="utf-8")
    core_test_text = (repo_root / "tests" / "test_flowpilot_core_runtime.py").read_text(encoding="utf-8")
    fake_text = (repo_root / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "fake_e2e.py").read_text(encoding="utf-8")
    prompt_text = (repo_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "flowguard_operator.md").read_text(encoding="utf-8").lower()
    reviewer_text = (repo_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "roles" / "human_like_reviewer.md").read_text(encoding="utf-8").lower()
    node_review_text = (repo_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "reviewer" / "node_acceptance_plan_review.md").read_text(encoding="utf-8").lower()
    obligations = {
        "node_plan_stage_model": "node_plan_reviewer_used_plan_stage_standard" in model_text,
        "result_stage_model": "final_reviewer_used_result_stage_standard" in model_text,
        "pm_flowguard_acceptance_packet": "pm_flowguard_acceptance" in runtime_text,
        "structural_gate_status": "awaiting_pm_flowguard_acceptance" in runtime_text,
        "ordinary_node_no_prework": "test_ordinary_node_acceptance_plan_releases_worker_without_prework_flowguard" in test_text,
        "node_plan_reviewer_stage_runtime_test": "test_node_acceptance_plan_review_packet_marks_plan_stage_boundary" in core_test_text,
        "worker_result_reviewer_stage_runtime_test": "test_worker_result_review_packet_marks_result_stage_boundary" in test_text,
        "flowguard_block_test": "test_node_acceptance_redesign_route_flowguard_block_prevents_route_mutation" in test_text,
        "pm_absorption_test": "test_node_acceptance_redesign_route_requires_pm_absorption_before_reviewer" in test_text,
        "pm_rewrite_test": "test_pm_flowguard_acceptance_rewrite_restarts_flowguard_cycle" in test_text,
        "optional_branch_rejection_test": "test_pm_flowguard_acceptance_rejects_optional_decisions" in test_text,
        "fake_ai_pm_acceptance": "pm_flowguard_acceptance.pm_flowguard_acceptance" in fake_text,
        "fake_ai_node_plan_stage_language": "plan-stage review" in fake_text,
        "reviewer_core_plan_stage_boundary": "plan-stage review" in reviewer_text,
        "reviewer_node_plan_no_worker_artifacts": "do not block solely because worker artifacts" in node_review_text,
        "flowguard_subject_prompt": "current subject simulation boundary" in prompt_text,
        "route_simulation_prompt": "work dispatch" in prompt_text and "validation/check path" in prompt_text,
        "unsupported_old_prework_rejection": "node_prework_flowguard is no longer a supported current FlowPilot path" in runtime_text,
        "old_worker_gate_removed": "_node_prework_flowguard_accepted" not in runtime_text,
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py",
            "skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md",
            "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
            "skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md",
            "tests/test_flowpilot_high_standard_control_flow.py",
            "tests/test_flowpilot_core_runtime.py",
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
    ordinary_state = model.ordinary_node_success_state()
    target_plan = {
        "ok": not model.invariant_failures(target_state) and not model.invariant_failures(ordinary_state),
        "route_redesign_state": target_state.__dict__,
        "ordinary_node_state": ordinary_state.__dict__,
        "route_redesign_failures": model.invariant_failures(target_state),
        "ordinary_node_failures": model.invariant_failures(ordinary_state),
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
        "target_current_node_route_gate_plan": target_plan,
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
