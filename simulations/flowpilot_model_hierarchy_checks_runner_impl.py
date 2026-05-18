"""Executable FlowGuard checks for the FlowPilot model hierarchy."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from flowguard import Explorer

import flowpilot_model_hierarchy_model as model
from flowpilot_model_hierarchy_checks_runner_inventory import (
    _base_from_result_path,
    _file_sha256,
    _flowguard_schema_version,
    _owner_label,
    _partition_contracts_from_ledger,
    _proof_status,
    _read_json,
    _result_index,
    _result_row_from_path,
    _size_tier,
    _thin_proof_status,
    _walk_counts,
    build_inventory_report,
)

ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_model_hierarchy_results.json")
HEAVYWEIGHT_STATE_THRESHOLD = model.HEAVYWEIGHT_STATE_THRESHOLD

REQUIRED_LABELS = {
    "select_valid_hierarchy_with_background_obligation",
    "accept_valid_hierarchy_with_background_obligation",
    "select_valid_release_hierarchy_with_current_heavy_proof",
    "accept_valid_release_hierarchy_with_current_heavy_proof",
    "reject_heavy_parent_without_split_review",
    "reject_parent_partition_gap",
    "reject_sibling_ownership_overlap",
    "reject_stale_child_evidence_used",
    "reject_hidden_child_skipped_checks",
    "reject_release_green_without_heavy_parent_proof",
    "reject_release_obligation_hidden",
    "reject_routine_thin_parent_blocked_by_full_regression",
    "reject_background_progress_only_claimed_pass",
    "reject_child_model_inlines_parent_graph",
    "reject_authority_mesh_confused_with_partition",
    "reject_missing_child_inventory",
}

EXPECTED_HAZARD_FAILURES = {
    "heavy_parent_without_split_review": {"heavy_parent_split_review_missing"},
    "parent_partition_gap": {"parent_partition_coverage_gap"},
    "sibling_ownership_overlap": {
        "sibling_overlap_requires_explicit_shared_kernel_or_refactor",
    },
    "stale_child_evidence_used": {"child_evidence_stale_or_foreign"},
    "hidden_child_skipped_checks": {"child_skipped_required_checks_hidden"},
    "release_green_without_heavy_parent_proof": {
        "release_claim_requires_current_heavy_parent_regression",
    },
    "release_obligation_hidden": {
        "release_full_regression_obligation_hidden",
    },
    "routine_thin_parent_blocked_by_full_regression": {
        "full_regression_must_not_block_routine_thin_parent",
    },
    "background_progress_only_claimed_pass": {
        "background_progress_is_not_completion_evidence",
    },
    "child_model_inlines_parent_graph": {
        "child_model_must_not_inline_parent_state_graph",
    },
    "authority_mesh_confused_with_partition": {
        "authority_mesh_cannot_substitute_for_partition_map",
    },
    "missing_child_inventory": {"child_model_inventory_incomplete"},
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|decision={state.decision}|"
        f"parent={state.heavyweight_parent_registered},{state.parent_exceeds_threshold},"
        f"{state.split_review_required}|partition={state.partition_map_written},"
        f"{state.partition_coverage_complete},{state.sibling_ownership_overlap}|"
        f"child={state.child_inventory_complete},{state.child_evidence_registered},"
        f"{state.child_evidence_current},{state.child_expands_parent_graph}|"
        f"layer={state.release_obligation_visible},{state.full_regression_used_as_routine_gate}|"
        f"release={state.hierarchy_claims_release_green},{state.heavy_full_regression_current}|"
        f"background={state.background_run_has_exit_artifact},"
        f"{state.background_run_has_valid_result_or_proof},{state.background_progress_claimed_as_pass}"
    )


def _walk_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels_seen: set[str] = set()
    violations: list[dict[str, Any]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            violations.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "ok": not violations and not (REQUIRED_LABELS - labels_seen),
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "terminal_state_count": sum(1 for state in states if model.is_terminal(state)),
        "accepted_state_count": sum(1 for state in states if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in states if state.status == "rejected"),
        "labels_seen": sorted(labels_seen),
        "missing_labels": sorted(REQUIRED_LABELS - labels_seen),
        "violations": violations,
    }


def _graph_for_output(graph: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in graph.items() if key not in {"states", "edges"}}


def _progress_report(graph: Mapping[str, Any]) -> dict[str, Any]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {index for index, state in enumerate(states) if model.is_terminal(state)}
    stuck = [
        _state_id(state)
        for index, state in enumerate(states)
        if index not in terminal and not edges[index]
    ]
    return {
        "ok": not stuck,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": 0,
        "cannot_reach_terminal_samples": [],
    }


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "violations": [str(item) for item in report.violations[:10]],
        "exception_branch_count": len(report.exception_branches),
        "dead_branch_count": len(report.dead_branches),
        "reachability_failure_count": len(report.reachability_failures),
    }


def _terminal_state_for(name: str) -> model.State:
    selected = None
    for transition in model.next_safe_states(model.initial_state()):
        if transition.label == f"select_{name}":
            selected = transition.state
            break
    if selected is None:
        raise KeyError(name)
    terminals = list(model.next_safe_states(selected))
    if len(terminals) != 1:
        raise AssertionError(f"expected one terminal for {name}")
    return terminals[0].state


def _contract_refinement_report() -> dict[str, Any]:
    bad_accepts: list[dict[str, Any]] = []
    bad_rejects: list[dict[str, Any]] = []
    for name in sorted(model.SCENARIOS):
        terminal = _terminal_state_for(name)
        should_accept = name in model.VALID_SCENARIOS
        accepted = terminal.status == "accepted"
        if accepted and not should_accept:
            bad_accepts.append({"scenario": name, "failures": model.hierarchy_failures(model.SCENARIOS[name])})
        if should_accept and not accepted:
            bad_rejects.append({"scenario": name, "failures": model.hierarchy_failures(model.SCENARIOS[name])})
    return {
        "ok": not bad_accepts and not bad_rejects,
        "accepted_scenarios": sorted(model.VALID_SCENARIOS),
        "rejected_scenarios": sorted(model.NEGATIVE_SCENARIOS),
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _hazard_report() -> dict[str, Any]:
    rows = []
    ok = True
    for name, state in model.hazard_states().items():
        observed = set(model.hierarchy_failures(state))
        expected = EXPECTED_HAZARD_FAILURES.get(name, set())
        missing = sorted(expected - observed)
        row_ok = not missing and bool(observed)
        if not row_ok:
            ok = False
        rows.append(
            {
                "scenario": name,
                "ok": row_ok,
                "expected_failures": sorted(expected),
                "observed_failures": sorted(observed),
                "missing_expected_failures": missing,
            }
        )
    return {"ok": ok, "hazards": rows}


def build_report() -> dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    contract = _contract_refinement_report()
    hazards = _hazard_report()
    inventory = build_inventory_report()
    sections = [graph, progress, flowguard, contract, hazards, inventory]
    return {
        "schema_version": 1,
        "model": "flowpilot_model_hierarchy",
        "ok": all(section.get("ok", False) for section in sections),
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "contract_refinement": contract,
        "hazard_review": hazards,
        "inventory": inventory,
    }


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        default=str(RESULTS_PATH),
        help="Write a JSON report to this path; defaults to the persisted hierarchy result.",
    )
    args = parser.parse_args(argv)

    report = build_report()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        _write_json(Path(args.json_out), report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
