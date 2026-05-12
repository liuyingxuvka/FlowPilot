"""Executable FlowGuard checks for the FlowPilot model mesh."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from flowguard import Explorer

import flowpilot_model_mesh_model as model


REQUIRED_LABELS = {
    "select_valid_live_can_continue",
    "accept_valid_live_can_continue",
    "select_valid_conformance_can_continue",
    "accept_valid_conformance_can_continue",
    "select_valid_blocked_current_state",
    "accept_valid_blocked_current_state",
    "select_valid_missing_conformance_boundary",
    "accept_valid_missing_conformance_boundary",
    "select_abstract_green_used_to_continue",
    "reject_abstract_green_used_to_continue",
    "select_skipped_live_audit_used_to_continue",
    "reject_skipped_live_audit_used_to_continue",
    "select_stale_run_result_used",
    "reject_stale_run_result_used",
    "select_unregistered_model_authoritative",
    "reject_unregistered_model_authoritative",
    "select_hidden_active_blocker",
    "reject_hidden_active_blocker",
    "select_current_authority_mismatch",
    "reject_current_authority_mismatch",
    "select_collapsed_repair_outcomes",
    "reject_collapsed_repair_outcomes",
    "select_parent_repair_leaf_event",
    "reject_parent_repair_leaf_event",
    "select_packet_role_origin_unchecked",
    "reject_packet_role_origin_unchecked",
    "select_known_hazard_without_live_projection",
    "reject_known_hazard_without_live_projection",
    "select_sealed_body_opened_by_mesh",
    "reject_sealed_body_opened_by_mesh",
    "select_coverage_parse_errors_ignored",
    "reject_coverage_parse_errors_ignored",
    "select_install_requires_safe_continue",
    "reject_install_requires_safe_continue",
    "select_installed_skill_stale_accepted",
    "reject_installed_skill_stale_accepted",
    "select_missing_conformance_claims_runtime",
    "reject_missing_conformance_claims_runtime",
    "select_control_transaction_registry_missing",
    "reject_control_transaction_registry_missing",
    "select_control_transaction_partial_commit_accepted",
    "reject_control_transaction_partial_commit_accepted",
    "select_parent_child_lifecycle_conformance_missed",
    "reject_parent_child_lifecycle_conformance_missed",
    "select_parent_child_lifecycle_replay_skipped",
    "reject_parent_child_lifecycle_replay_skipped",
    "select_legal_next_action_policy_missing",
    "reject_legal_next_action_policy_missing",
    "select_legal_next_action_projection_missing",
    "reject_legal_next_action_projection_missing",
    "select_legal_next_action_conformance_failed",
    "reject_legal_next_action_conformance_failed",
}

HAZARD_EXPECTED_FAILURES = {
    "abstract_green_used_to_continue": {
        "evidence_tier_below_required_runtime_confidence",
        "current_state_not_classified",
    },
    "skipped_live_audit_used_to_continue": {
        "live_required_but_audit_skipped",
        "current_state_not_classified",
    },
    "stale_run_result_used": {"stale_or_foreign_model_result_cannot_authorize_continue"},
    "unregistered_model_authoritative": {"unregistered_model_result_cannot_authorize_continue"},
    "hidden_active_blocker": {"active_blocker_cannot_be_safe_to_continue"},
    "current_authority_mismatch": {"current_authorities_disagree"},
    "collapsed_repair_outcomes": {"repair_outcome_events_collapsed"},
    "parent_repair_leaf_event": {"repair_event_not_compatible_with_active_node"},
    "packet_role_origin_unchecked": {"packet_authority_not_verified_before_acceptance"},
    "known_hazard_without_live_projection": {"known_hazard_lacks_live_projection"},
    "sealed_body_opened_by_mesh": {"mesh_must_not_open_sealed_bodies"},
    "coverage_parse_errors_ignored": {"coverage_parse_errors_must_block_green_result"},
    "install_requires_safe_continue": {"install_check_must_accept_classified_blocked_state"},
    "installed_skill_stale_accepted": {"installed_skill_not_synced_with_repo_model"},
    "missing_conformance_claims_runtime": {
        "evidence_tier_below_required_runtime_confidence",
        "missing_conformance_adapter_cannot_claim_runtime_conformance",
    },
    "control_transaction_registry_missing": {"control_transaction_registry_not_authoritative"},
    "control_transaction_partial_commit_accepted": {"control_transaction_commit_scope_incomplete"},
    "parent_child_lifecycle_conformance_missed": {"parent_child_lifecycle_conformance_failed"},
    "parent_child_lifecycle_replay_skipped": {"parent_child_lifecycle_conformance_replay_missing"},
    "legal_next_action_policy_missing": {
        "legal_next_action_policy_not_registered",
        "legal_next_action_projection_missing",
        "legal_next_action_conformance_failed",
    },
    "legal_next_action_projection_missing": {"legal_next_action_projection_missing"},
    "legal_next_action_conformance_failed": {"legal_next_action_conformance_failed"},
}


def _empty_report(ok: bool = True) -> Dict[str, Any]:
    return {
        "ok": ok,
        "labels_seen": [],
        "missing_labels": sorted(REQUIRED_LABELS),
        "violations": [],
    }


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|decision={state.decision}|"
        f"tier={state.evidence_tier}->{state.required_tier}|"
        f"live_skip={state.live_audit_skipped}|conformance_skip={state.conformance_skipped}|"
        f"blocker={state.active_blocker_present},{state.safe_to_continue_claimed}|"
        f"auth={state.current_authorities_agree}|repair={state.collapsed_repair_outcome_events},"
        f"{state.repair_event_node_compatible}|packet={state.role_origin_checked},"
        f"{state.completed_agent_id_belongs_to_role}|sealed={state.sealed_body_opened_by_mesh}|"
        f"parse={state.coverage_parse_errors_ignored}|install={state.install_requires_safe_to_continue}|"
        f"sync={state.installed_skill_matches_repo},{state.local_sync_required}|"
        f"ctr={state.control_transaction_registry_registered},{state.control_transaction_registry_valid},"
        f"{state.control_transaction_commit_scope_complete}|parent_child="
        f"{state.parent_child_lifecycle_conformant},{state.parent_child_lifecycle_replayed}|legal="
        f"{state.legal_next_action_policy_registered},{state.legal_next_action_projected},"
        f"{state.legal_next_action_conformant}"
    )


def _walk_graph() -> Dict[str, Any]:
    labels_seen = set()
    violations: List[Dict[str, Any]] = []
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: List[model.State] = [initial]
    index = {initial: 0}
    edges: List[List[tuple[str, int]]] = []

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

    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not violations,
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "violations": violations,
    }


def _progress_report(graph: Mapping[str, Any]) -> Dict[str, Any]:
    states: List[model.State] = graph["states"]
    edges: List[List[tuple[str, int]]] = graph["edges"]
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
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _flowguard_report() -> Dict[str, Any]:
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


def _graph_for_output(graph: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in graph.items()
        if key not in {"states", "edges"}
    } | {
        "terminal_state_count": sum(1 for state in graph["states"] if model.is_terminal(state)),
        "accepted_state_count": sum(1 for state in graph["states"] if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in graph["states"] if state.status == "rejected"),
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


def _contract_refinement_report() -> Dict[str, Any]:
    valid: List[str] = []
    rejected: List[str] = []
    bad_accepts: List[Dict[str, Any]] = []
    bad_rejects: List[Dict[str, Any]] = []

    for name, scenario in model.SCENARIOS.items():
        failures = model.mesh_failures(scenario)
        transition_state = _terminal_state_for(name)
        if transition_state.status == "accepted":
            valid.append(name)
            if failures:
                bad_accepts.append({"scenario": name, "failures": failures})
        else:
            rejected.append(name)
            if not failures:
                bad_rejects.append({"scenario": name})

    return {
        "ok": not bad_accepts and not bad_rejects,
        "accepted_scenarios": sorted(valid),
        "rejected_scenarios": sorted(rejected),
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _hazard_report() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    ok = True
    for name, state in model.hazard_states().items():
        failures = set(model.mesh_failures(state))
        expected = HAZARD_EXPECTED_FAILURES[name]
        missing = sorted(expected - failures)
        unexpected_empty = not failures
        if missing or unexpected_empty:
            ok = False
        rows.append(
            {
                "scenario": name,
                "expected_failures": sorted(expected),
                "observed_failures": sorted(failures),
                "missing_expected_failures": missing,
                "ok": not missing and not unexpected_empty,
            }
        )
    return {"ok": ok, "hazards": rows}


def _coverage_report() -> Dict[str, Any]:
    graph = _walk_graph()
    required_negative_count = len(model.NEGATIVE_SCENARIOS)
    reject_labels = [
        label
        for label in graph["labels_seen"]
        if label.startswith("reject_") and label.removeprefix("reject_") in model.NEGATIVE_SCENARIOS
    ]
    return {
        "ok": graph["ok"] and len(reject_labels) == required_negative_count,
        "graph": _graph_for_output(graph),
        "required_negative_count": required_negative_count,
        "negative_reject_labels_seen": sorted(reject_labels),
    }


def build_report(project_root: Path, run_id: str | None, include_live_audit: bool) -> Dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    contract = _contract_refinement_report()
    hazards = _hazard_report()
    coverage = _coverage_report()
    live_projection = None
    if include_live_audit:
        live_projection = model.project_live_run(project_root=project_root, run_id=run_id)

    sections = [graph, progress, flowguard, contract, hazards, coverage]
    if live_projection is not None:
        sections.append(live_projection)

    return {
        "schema_version": 1,
        "model": "flowpilot_model_mesh",
        "ok": all(section.get("ok", False) for section in sections),
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "contract_refinement": contract,
        "hazard_review": hazards,
        "coverage": coverage,
        "live_run_projection": live_projection,
    }


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Repository root for live run projection.")
    parser.add_argument("--run-id", default=None, help="FlowPilot run id to project; defaults to current run.")
    parser.add_argument("--json-out", default=None, help="Write a JSON report to this path.")
    parser.add_argument("--skip-live-audit", action="store_true", help="Skip metadata-only current run projection.")
    args = parser.parse_args(argv)

    report = build_report(
        project_root=Path(args.project_root),
        run_id=args.run_id,
        include_live_audit=not args.skip_live_audit,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        _write_json(Path(args.json_out), report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
