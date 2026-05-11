"""Run checks for the FlowPilot handoff/artifact protocol model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_handoff_artifact_protocol_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_handoff_artifact_protocol_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.MESSAGE_ONLY_WORK_PRODUCT: "substantive work product exists only in the handoff letter",
    model.ROUTER_TRUNCATES_ARTIFACT: "Router rebuilt or narrowed the role-authored official artifact",
    model.DOWNSTREAM_SKIPS_HANDOFF: "downstream role did not receive and read the handoff letter",
    model.HANDOFF_ARTIFACT_MISMATCH: "handoff claims do not match formal artifacts",
    model.STALE_HASH_ACCEPTED: "artifact refs were accepted without current path/hash validation",
    model.MISSING_PM_SUGGESTION_SECTION: "role output omitted PM Suggestion Items",
    model.SUGGESTION_IGNORED_BY_PM: "PM ignored a suggestion without final disposition or consultation",
    model.CONSULTATION_TREATED_AS_FINAL: "PM failed to issue final disposition after consultation",
    model.FORCED_CONSULTATION_FOR_MINOR: "consultation was forced for a minor suggestion",
    model.CONSULTATION_WITHOUT_PACKET: "PM consultation request lacks bounded formal packet",
    model.CONSULTATION_RESULT_NOT_READ: "PM did not read consultation result before final disposition",
    model.BLOCKER_ADVANCES_WHILE_CONSULTING: "blocking suggestion advanced while unresolved or consulting",
    model.ACK_TREATED_AS_COMPLETION: "ACK was treated as completion evidence",
    model.MAJOR_DIRECT_REJECT_WITHOUT_REASON: "major suggestion was directly rejected without PM reason",
    model.LEDGER_LEAKS_SEALED_BODY: "sealed body content leaked into handoff or ledger",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"artifact={state.formal_artifact_written},{state.router_preserves_role_artifact},"
        f"{state.role_authored_extra_fields_preserved}|"
        f"handoff={state.handoff_written},{state.downstream_reads_handoff},"
        f"{state.downstream_records_consistency_check}|"
        f"suggestion={state.suggestion_section_present},{state.suggestion_logged_for_pm},"
        f"{state.pm_final_disposition_recorded},{state.pm_final_disposition}|"
        f"consult={state.consultation_required_by_pm},{state.consultation_request_packet_written},"
        f"{state.consultation_result_read_by_pm},{state.pm_final_disposition_after_consultation}|"
        f"gate={state.gate_advances}|reason={state.terminal_reason}"
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
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    accepted_scenarios = sorted(state.scenario for state in accepted)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_state_count": len(rejected),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
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
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
                can_reach_terminal.add(source)
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
        "ok": not stuck and not cannot_reach_terminal,
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        protocol_failures = model.protocol_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in protocol_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": protocol_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
    }
    result["ok"] = all(
        section.get("ok", False) for section in (safe_graph, progress, explorer, hazards)
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
