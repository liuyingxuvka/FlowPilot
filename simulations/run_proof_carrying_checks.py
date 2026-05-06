"""Run checks for the FlowPilot proof-carrying router-check model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import proof_carrying_checks_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "proof_carrying_checks_results.json"

HAZARD_EXPECTED_FAILURES = {
    "router_only_from_self_attested_claim": "router-only pass used evidence that was not recomputable or host-bound",
    "trusted_router_pass_without_audit_file": "reviewer gate was replaced without a router audit file",
    "live_fact_opened_without_reviewer": "live or judgement fact opened work without reviewer pass",
    "host_receipt_not_bound_to_current_run": "router-only pass used evidence that was not recomputable or host-bound",
    "reviewer_required_and_replaced": "self-attested AI claim replaced reviewer check",
}


def _state_id(state: model.State) -> str:
    return (
        f"step={state.step}|status={state.status}|fact={state.fact_kind}|"
        f"source={state.proof_source}|bound={state.proof_bound_to_current_run}|"
        f"verified={state.router_recomputed_or_verified}|audit={state.router_audit_file_written}|"
        f"reviewer_required={state.reviewer_required}|reviewer_passed={state.reviewer_passed}|"
        f"router_passed={state.router_only_passed}|replaced={state.reviewer_gate_replaced}|"
        f"ai_claim={state.ai_claim_used_as_proof}|opened={state.work_gate_opened}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int, str]]] = []
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
            edges[source_index].append((transition.label, index[transition.state], transition.gate_owner))

    return {
        "states": seen,
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
    router_proof_completions = [
        state for state in complete_states if state.router_only_passed and state.reviewer_gate_replaced
    ]
    reviewer_completions = [state for state in complete_states if state.reviewer_passed]
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and bool(router_proof_completions)
            and bool(reviewer_completions)
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": len(complete_states),
        "router_proof_completion_count": len(router_proof_completions),
        "reviewer_completion_count": len(reviewer_completions),
        "invariant_failures": graph["invariant_failures"],
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target, _owner in outgoing]
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
    result = {
        "ok": bool(safe_graph["ok"] and progress["ok"] and explorer["ok"] and hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "confidence_boundary": "abstract proof-source ownership model; pair with router runtime tests and card audits",
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
