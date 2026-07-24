"""Executable FlowGuard checks for FlowPilot tiered test validation."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from flowguard.explorer import Explorer

import flowpilot_test_tiering_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_test_tiering_results.json")

REQUIRED_LABELS = {
    "select_valid_fast_tier",
    "accept_valid_fast_tier",
    "select_valid_router_child_tier",
    "accept_valid_router_child_tier",
    "select_valid_background_integration_tier",
    "accept_valid_background_integration_tier",
    "select_valid_release_background_tier",
    "accept_valid_release_background_tier",
    "reject_root_pytest_scans_backup_tests",
    "reject_foreground_full_regression",
    "reject_public_release_in_fast_tier",
    "reject_coverage_sweep_blocks_fast_tier",
    "reject_missing_child_owner",
    "reject_duplicate_child_owner",
    "reject_hidden_skipped_tests",
    "reject_stale_child_evidence_used",
    "reject_router_slice_import_broken_counted_green",
    "reject_router_child_tier_keeps_slow_aggregate",
    "reject_router_child_tier_duplicates_k_shards",
    "reject_router_child_tier_stale_k_pattern",
    "reject_background_progress_only_claimed_pass",
    "reject_background_missing_artifact_set",
    "reject_background_exit_precedes_terminal_meta",
    "reject_background_running_without_timeout_guard",
    "reject_background_inner_interpreter_follows_external_upgrade",
    "reject_background_windows_venv_shim_exits_before_process_owner",
    "reject_background_shared_runtime_resource_race",
    "reject_background_descendant_settlement_missing",
    "reject_background_predating_process_misclassified_as_descendant",
    "reject_background_sibling_misclassified_through_reused_parent_pid",
    "reject_background_surviving_descendant_promoted",
    "reject_json_write_readback_can_hang_control_gate",
    "reject_release_obligation_hidden",
    "reject_release_claim_without_release_suite",
    "reject_release_public_check_races_model_proofs",
    "reject_release_embeds_final_confidence_consumer",
    "reject_testmesh_mta_final_confidence_dependency_cycle",
    "reject_shared_input_selects_every_owner",
    "reject_mta_supplement_runs_before_upstream_owner",
    "reject_install_check_races_topology_writers",
    "reject_install_sync_skipped_after_tool_change",
}

EXPECTED_HAZARD_FAILURES = {
    "root_pytest_scans_backup_tests": {"pytest_collection_not_scoped"},
    "foreground_full_regression": {"fast_tier_not_foreground_safe"},
    "public_release_in_fast_tier": {"public_release_check_in_fast_tier"},
    "coverage_sweep_blocks_fast_tier": {"coverage_sweep_blocks_fast_tier"},
    "missing_child_owner": {"child_owner_missing"},
    "duplicate_child_owner": {"duplicate_child_owner"},
    "hidden_skipped_tests": {"hidden_skipped_tests"},
    "stale_child_evidence_used": {"child_evidence_stale"},
    "line_ending_transport_forces_execution": {
        "controlled_text_not_canonicalized"
    },
    "global_snapshot_mismatch_stales_every_owner": {
        "global_snapshot_used_as_blanket_invalidation_authority"
    },
    "shared_input_selects_every_owner": {
        "shared_input_selected_blanket_tier_execution"
    },
    "unmapped_change_falls_back_to_run_all": {
        "impact_mapping_missing_not_blocked",
        "blocked_impact_falls_back_to_run_all",
    },
    "reused_owner_has_no_current_ticket": {
        "reused_owner_missing_current_ticket"
    },
    "receipt_consumer_relaunches_heavy_owner": {
        "receipt_consumer_relaunches_heavy_owner"
    },
    "mta_supplement_runs_before_upstream_owner": {
        "mta_supplement_precedes_upstream_owner"
    },
    "router_slice_import_broken_counted_green": {
        "router_slice_import_failure_counted_green",
    },
    "router_child_tier_keeps_slow_aggregate": {
        "router_child_commands_not_granular",
    },
    "router_child_tier_duplicates_k_shards": {
        "router_child_shards_duplicate_test_selection",
    },
    "router_child_tier_stale_k_pattern": {
        "router_child_shard_pattern_stale_or_empty",
    },
    "background_progress_only_claimed_pass": {
        "background_progress_is_not_completion_evidence",
    },
    "background_missing_artifact_set": {"background_artifact_set_missing"},
    "background_exit_precedes_terminal_meta": {
        "background_exit_precedes_terminal_meta"
    },
    "background_running_without_timeout_guard": {
        "background_progress_is_not_completion_evidence",
        "background_timeout_not_enforced",
    },
    "background_inner_interpreter_follows_external_upgrade": {
        "background_interpreter_not_bound_to_execution_owner",
    },
    "background_windows_venv_shim_exits_before_process_owner": {
        "background_interpreter_shim_not_direct_process_owner",
    },
    "background_shared_runtime_resource_race": {
        "background_shared_runtime_resource_not_serialized",
    },
    "background_descendant_settlement_missing": {
        "background_descendant_settlement_not_bounded",
    },
    "background_predating_process_misclassified_as_descendant": {
        "background_descendant_lineage_not_ordered",
    },
    "background_sibling_misclassified_through_reused_parent_pid": {
        "background_sibling_isolation_not_preserved",
    },
    "background_surviving_descendant_promoted": {
        "background_surviving_descendants_not_fail_closed",
    },
    "json_write_readback_can_hang_control_gate": {
        "json_write_readback_not_bounded",
    },
    "release_obligation_hidden": {"release_obligation_hidden"},
    "release_claim_without_release_suite": {"release_scope_missing_release_suite"},
    "release_public_check_races_model_proofs": {"release_public_check_races_model_proofs"},
    "release_embeds_final_confidence_consumer": {"release_tier_embeds_terminal_consumer"},
    "testmesh_mta_final_confidence_dependency_cycle": {
        "testmesh_mta_final_confidence_dependency_cycle"
    },
    "install_check_races_topology_writers": {
        "install_check_races_topology_writers"
    },
    "install_sync_skipped_after_tool_change": {"install_sync_not_planned"},
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|scope={state.tier_scope}|"
        f"parent={state.parent_tier_declared}|child={state.child_suites_declared},"
        f"{state.child_owner_registered},{state.duplicate_child_owner}|"
        f"collection={state.pytest_scoped_to_tests},{state.backup_tmp_excluded}|"
        f"fast={state.fast_tier_foreground_safe},{state.long_regression_in_fast_tier},"
        f"{state.public_release_in_fast_tier},{state.coverage_sweep_blocks_fast_tier}|"
        f"router={state.router_slice_import_ok},{state.router_slice_counted_green}|"
        f"router_granular={state.router_child_commands_granular},"
        f"{state.router_k_shards_disjoint},{state.router_k_patterns_current},"
        f"{state.slow_router_aggregate_command_present}|"
        f"background={state.background_requested},{state.background_artifacts_declared},"
        f"{state.background_exit_artifact_present},{state.background_exit_inspected},"
        f"{state.background_progress_claimed_as_pass},{state.background_timeout_enforced},"
        f"{state.background_interpreter_bound_to_owner},"
        f"{state.background_interpreter_is_direct_process_owner},"
        f"{state.shared_runtime_resources_serialized},"
        f"{state.background_descendant_settlement_bounded},"
        f"{state.background_descendant_lineage_ordered},"
        f"{state.background_sibling_isolation_preserved},"
        f"{state.background_surviving_descendants_fail_closed},"
        f"{state.json_write_readback_bounded}|"
        f"release={state.release_required},{state.release_obligation_visible},"
        f"{state.release_suite_run_or_backgrounded},"
        f"{state.release_public_check_after_model_proofs}|"
        f"install_order={state.install_check_after_topology_writers}|"
        f"sync={state.install_sync_required},{state.install_sync_planned}"
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


def _progress_report(graph: Mapping[str, Any]) -> dict[str, Any]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _flowguard_report() -> dict[str, Any]:
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


def _terminal_state_for(name: str) -> model.State:
    selected = None
    for transition in model.next_safe_states(model.initial_state()):
        if transition.label == f"select_{name}":
            selected = transition.state
            break
    if selected is None:
        raise AssertionError(f"scenario was not selectable: {name}")
    terminals = list(model.next_safe_states(selected))
    if len(terminals) != 1:
        raise AssertionError(f"scenario did not have exactly one terminal transition: {name}")
    return terminals[0].state


def _scenario_review() -> dict[str, Any]:
    valid: list[str] = []
    rejected: list[str] = []
    bad_accepts: list[dict[str, Any]] = []
    bad_rejects: list[dict[str, Any]] = []

    for name in sorted(model.VALID_SCENARIOS):
        terminal = _terminal_state_for(name)
        if terminal.status == "accepted":
            valid.append(name)
        else:
            bad_rejects.append(
                {
                    "scenario": name,
                    "status": terminal.status,
                    "failures": model.test_tier_failures(terminal),
                }
            )

    for name in sorted(model.NEGATIVE_SCENARIOS):
        terminal = _terminal_state_for(name)
        failures = set(model.test_tier_failures(terminal))
        expected = EXPECTED_HAZARD_FAILURES[name]
        if terminal.status == "rejected" and expected <= failures:
            rejected.append(name)
        else:
            bad_accepts.append(
                {
                    "scenario": name,
                    "status": terminal.status,
                    "expected": sorted(expected),
                    "actual": sorted(failures),
                }
            )

    return {
        "ok": not bad_accepts and not bad_rejects,
        "valid_scenarios_accepted": valid,
        "hazard_scenarios_rejected": rejected,
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _graph_for_output(graph: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in graph.items()
        if key not in {"states", "edges"}
    }


def build_report() -> dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    scenarios = _scenario_review()
    ok = graph["ok"] and progress["ok"] and flowguard["ok"] and scenarios["ok"]
    return {
        "ok": ok,
        "model": "flowpilot_test_tiering",
        "result_type": "test_mesh",
        "background_artifact_contract": list(model.BACKGROUND_ARTIFACTS),
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "scenario_review": scenarios,
        "expected_hazard_failures": {
            key: sorted(value) for key, value in sorted(EXPECTED_HAZARD_FAILURES.items())
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = build_report()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output_path = args.json_out
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
