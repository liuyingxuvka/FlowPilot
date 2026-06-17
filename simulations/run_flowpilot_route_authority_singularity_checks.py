"""Run checks for the FlowPilot route-authority singularity model."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_route_authority_singularity_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_route_authority_singularity_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.OWNER_MISSING: "current owner missing from route authority snapshot",
    model.OWNER_CONFLICT: "route authority owner conflict",
    model.LEGAL_ACTIONS_MISSING: "legal action ids missing from route authority snapshot",
    model.PM_WRONG_PATH_PARENT_CLOSURE: "wrong route path was not rejected",
    model.WRONG_ROLE_ROUTE_ACTION: "submitted role does not match current route authority owner",
    model.STALE_AUTHORITY_SNAPSHOT: "stale route authority snapshot used",
    model.OLD_ALIAS_TRANSLATED: "unsupported old route-action alias was translated",
    model.FALLBACK_PROSE_TRANSLATED: "fallback or prose route-action payload was translated",
    model.REJECTION_FEEDBACK_MISSING: "route authority rejection feedback missing repair fields",
    model.REPEATED_NO_DELTA_ACCEPTED: "repeated no-delta wrong-path submission was accepted",
    model.MESH_GREEN_WITHOUT_AUTHORITY_EVIDENCE: "mesh green claim lacked route authority projection",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|owner={state.current_owner},"
        f"{state.current_owner_present},{state.current_owner_unique}|"
        f"legal={state.legal_actions_computed},{state.legal_actions_current},"
        f"{state.legal_action_ids_present}|submitted={state.submitted_role},"
        f"{state.submitted_action_id},{state.submitted_action_in_legal_set},"
        f"{state.submitted_role_matches_owner}|alias={state.old_alias_used},"
        f"{state.old_alias_translated_to_current_action}|fallback={state.fallback_or_prose_payload},"
        f"{state.fallback_or_prose_translated_to_current_action}|reject={state.wrong_path_rejected},"
        f"{state.rejection_feedback_owner_present},{state.rejection_feedback_legal_actions_present},"
        f"{state.rejection_feedback_forbidden_actions_present},"
        f"{state.rejection_feedback_repair_command_present}|repeat={state.repeated_submission_same_as_rejected},"
        f"{state.repeated_submission_blocked_as_same_family}|corrected={state.corrected_retry_after_rejection},"
        f"{state.corrected_retry_uses_required_command},{state.corrected_retry_action_in_legal_set}|"
        f"mesh={state.mesh_authority_projection_available},{state.mesh_green_claimed}|reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
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
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "terminal_state_count": len(terminal),
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        authority_failures = model.route_authority_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in authority_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": authority_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _intended_report() -> dict[str, object]:
    failures: dict[str, list[str]] = {}
    for scenario, state in model.intended_plan_states().items():
        authority_failures = model.route_authority_failures(state)
        if authority_failures:
            failures[scenario] = authority_failures
    return {"ok": not failures, "failures": failures, "accepted_plan": sorted(model.VALID_SCENARIOS)}


def _candidate_fix_plan() -> dict[str, object]:
    return {
        "name": "flowpilot_route_authority_singularity",
        "minimum_runtime_change_set": [
            "Treat the route action policy registry as the single authority for owner, legal actions, and repair command.",
            "Reject wrong-path submissions by materializing a route-authority control blocker.",
            "Reject unsupported old event aliases and fallback/prose payload shapes instead of translating them.",
            "Project route-authority rejection feedback into active control blocker summaries.",
            "Require model-mesh and synthetic coverage evidence before broad continuation claims.",
        ],
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    reports = {
        "safe_graph": _safe_graph_report(graph),
        "progress": _progress_report(graph),
        "flowguard": _flowguard_report(),
        "hazards": _hazard_report(),
        "intended": _intended_report(),
    }
    ok = all(report.get("ok") for report in reports.values())
    return {
        "ok": ok,
        "model": "flowpilot_route_authority_singularity",
        "covered_risks": sorted(model.NEGATIVE_SCENARIOS),
        "candidate_fix_plan": _candidate_fix_plan(),
        **reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ok={result['ok']} results={args.json_out}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
