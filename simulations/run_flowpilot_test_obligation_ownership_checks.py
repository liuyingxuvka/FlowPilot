"""Run FlowGuard checks for FlowPilot test-obligation ownership."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path

from flowguard import Explorer

import flowpilot_test_obligation_ownership_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_test_obligation_ownership_results.json"

HAZARD_EXPECTED_FAILURES = {
    "controller_decides_tests": "Controller decided test obligation disposition",
    "flowguard_operator_writes_ordinary_tests": "FlowGuard operator maintained ordinary test code by default",
    "background_progress_counted": "background progress was counted as passing test evidence",
    "missing_tests_left_as_prose": "missing test kinds were left as residual prose",
    "stale_test_evidence_used": "stale ordinary test evidence was used for closure",
    "post_matrix_before_worker_result": "post-worker test matrix was written before required inputs",
    "worker_packet_no_coverage_rows": "worker test packet completed without test obligation coverage rows",
    "ordinary_gap_without_worker_or_waiver": "ordinary missing test kind was closed without worker coverage or waiver",
    "broad_gap_without_testmesh": "broad validation gap was closed without TestMesh evidence or waiver",
    "alignment_gap_without_alignment": "model/test mismatch was closed without Model-Test Alignment evidence or waiver",
    "reviewer_before_disposition": "reviewer checked package before PM dispositioned test obligations",
    "node_completion_before_reviewer": "node completion approved before reviewer checked test dispositions",
    "final_ledger_before_evidence_package": "final ledger carried test rows before evidence quality package",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|pre={state.pre_worker_matrix_written}|"
        f"FlowGuard operator={state.flowguard_operator_report_absorbed}|worker={state.worker_result_absorbed}|"
        f"post={state.post_worker_matrix_written}|gap={state.gap_kind}|"
        f"worker_test={state.worker_test_packet_completed},{state.worker_test_coverage_rows_returned}|"
        f"testmesh={state.testmesh_completed}|mta={state.model_test_alignment_completed}|"
        f"waiver={state.waived_with_authority}|disposition={state.all_test_obligations_dispositioned}|"
        f"reviewer={state.reviewer_checked_matrix}|node={state.node_completion_approved}|"
        f"evidence={state.evidence_quality_package_carries_rows}|final={state.final_ledger_carries_rows}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
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
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    complete_states = [state for state in states if model.is_success(state)]
    complete_gaps = sorted({state.gap_kind for state in complete_states})
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and complete_gaps == sorted(model.GAP_KINDS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "complete_state_count": len(complete_states),
        "complete_gap_kinds": complete_gaps,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True

    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": not stuck and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
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
            "state": asdict(state),
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
