"""Run checks for the FlowPilot requirement traceability model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_requirement_traceability_model as model


REQUIRED_LABELS = (
    "add_product_requirement_trace_spine",
    "bind_root_contract_to_requirement_deltas",
    "bind_route_nodes_to_requirements",
    "bind_node_acceptance_to_direct_evidence",
    "add_mutation_impact_and_stale_evidence_guards",
    "add_final_ledger_and_router_trace_closure",
    "requirement_traceability_upgrade_completed",
)

HAZARD_EXPECTED_FAILURES = {
    "product_missing_stable_ids": "product architecture phase lacked stable requirement trace ids across tasks, capabilities, and acceptance",
    "product_capability_unmapped": "product architecture phase lacked stable requirement trace ids across tasks, capabilities, and acceptance",
    "root_missing_change_status": "root contract phase lacked source ids, change status, supersession policy, or proof-matrix trace",
    "root_missing_supersession_policy": "root contract phase lacked source ids, change status, supersession policy, or proof-matrix trace",
    "route_node_unknown_requirement": "route phase lacked valid requirement coverage, scenario/capability links, or node rationale",
    "route_node_without_rationale": "route phase lacked valid requirement coverage, scenario/capability links, or node rationale",
    "node_plan_missing_direct_evidence": "node acceptance phase lacked requirement evidence mapping, standard scenarios, direct evidence, or child-skill trace",
    "node_child_skill_trace_dropped": "node acceptance phase lacked requirement evidence mapping, standard scenarios, direct evidence, or child-skill trace",
    "mutation_keeps_stale_evidence": "mutation phase failed to list impacted requirements/nodes, invalidate stale evidence, require reruns, or block old superseded evidence",
    "superseded_requirement_closed_by_old_evidence": "mutation phase failed to list impacted requirements/nodes, invalidate stale evidence, require reruns, or block old superseded evidence",
    "final_ledger_unresolved_requirement": "final ledger completed without complete requirement closure, direct evidence, waiver authority, and stale-status checks",
    "final_ledger_existence_only": "final ledger completed without complete requirement closure, direct evidence, waiver authority, and stale-status checks",
    "external_spec_as_authority": "external OpenSpec-like output became route authority without FlowPilot PM import approval",
    "light_profile_allowed": "formal FlowPilot run allowed a light/simple profile instead of the full protocol",
    "simple_profile_waiver_allowed": "formal FlowPilot run allowed a light/simple profile instead of the full protocol",
    "router_trace_event_not_authorized": "traceability completion lacked router validation and router-authorized trace events",
    "router_trace_validation_missing": "traceability completion lacked router validation and router-authorized trace events",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|stage={state.stage}|standalone={state.flowpilot_standalone}|"
        f"external_authority={state.external_spec_authority_used}|full={state.full_protocol_required}|"
        f"light={state.light_profile_allowed}|simple={state.simple_profile_waiver_allowed}|"
        f"product={state.requirement_registry_exists},{state.stable_requirement_ids},"
        f"{state.product_tasks_trace_ids},{state.product_capabilities_trace_ids},"
        f"{state.product_acceptance_trace_ids}|root={state.root_requirements_source_ids},"
        f"{state.root_requirements_change_status},{state.root_requirements_supersession_policy},"
        f"{state.root_proof_matrix_trace_ids}|route={state.route_nodes_cover_requirement_ids},"
        f"{state.route_nodes_reference_known_requirements},{state.route_nodes_have_rationale},"
        f"{state.route_nodes_merge_split_review}|node={state.node_inherits_route_requirements},"
        f"{state.node_acceptance_direct_evidence_required},{state.child_skill_requirement_trace_kept}|"
        f"mutation={state.mutation_stale_evidence_invalidated},"
        f"{state.superseded_requirements_block_old_evidence}|final="
        f"{state.final_ledger_requirement_trace_closure},"
        f"{state.final_ledger_all_effective_requirements_resolved},"
        f"{state.final_ledger_direct_evidence_required}|router="
        f"{state.router_validation_enforces_trace_fields},"
        f"{state.router_authorized_trace_events},{state.router_rejects_invented_trace_events}"
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
    return {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
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
        "ok": bool(success) and not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "success_state_count": len(success),
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


def _intended_upgrade_matrix() -> dict[str, object]:
    matrix: dict[str, object] = {}
    for name, item in model.intended_upgrade_catalog().items():
        state = item["profile"]
        assert isinstance(state, model.State)
        failures = model.invariant_failures(state)
        matrix[name] = {
            "ok": not failures,
            "interpretation": item["interpretation"],
            "scope": item["scope"],
            "runtime_readiness": item["runtime_readiness"],
            "failures": failures,
        }
    return matrix


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    intended_upgrade = _intended_upgrade_matrix()
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and all(bool(item["ok"]) for item in intended_upgrade.values()),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "intended_upgrade_matrix": intended_upgrade,
        "model_boundary": (
            "traceability-design model; production templates, cards, router "
            "validation, and local install sync still require separate checks"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing the JSON result payload.")
    args = parser.parse_args()

    result = run_checks()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
