"""Run checks for the current FlowPilot startup path model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard.explorer import Explorer

import flowpilot_startup_optimization_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_startup_optimization_results.json"


HAZARD_EXPECTED_FAILURES = {
    "background_not_authorized": "background collaboration was not authorized",
    "startup_background_agents_preleased": "startup pre-leased background agents",
    "fixed_role_count_gate_required": "startup required a fixed role-count gate",
    "heartbeat_or_manual_resume_binding_required": "startup required heartbeat or manual resume binding liveness",
    "controller_loaded_before_run": "Controller loaded before current run shell existed",
    "controller_reads_sealed_body": "Controller read sealed startup or role body",
    "self_attested_proof": "self-attested startup claim was used as runtime proof",
    "mechanical_audit_without_current_intake": "startup mechanical audit was written without current sealed intake",
    "display_status_without_runtime_ready": "startup display status was written without current audit",
    "user_intake_before_runtime_ready": "user_intake mail was exposed before startup runtime mechanics were ready",
    "legacy_human_startup_review_gate_used": "legacy human startup review gate was used",
    "quality_reviewer_reproves_router_mechanics": "quality Reviewer was required to re-prove router-owned startup mechanics",
    "legacy_pm_startup_release_gate_used": "legacy PM startup release gate was used",
    "pm_intake_ack_bypasses_common_ledger": "PM startup intake ACK bypassed user_intake mail or common card ledger",
    "pm_route_planning_before_pm_intake": "PM route planning started before PM startup intake ACK",
    "role_work_before_pm_route_planning": "role work was allocated before PM route planning",
    "route_work_without_current_role_agent": "route work started without a current role-agent binding",
    "role_agent_failure_continues": "FlowPilot continued after required current role-agent opening failed",
    "foreground_only_fallback_used": "FlowPilot used foreground-only fallback work after role-agent failure",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|answers={state.startup_answers_recorded}|"
        f"run={state.run_shell_created},{state.current_pointer_written},{state.run_index_updated}|"
        f"controller={state.controller_loaded},{state.controller_boundary_confirmed}|"
        f"intake={state.startup_intake_record_current},{state.startup_intake_body_sealed}|"
        f"audit={state.mechanical_audit_written},{state.router_owned_mechanical_proof_current}|"
        f"display={state.display_status_written},{state.display_receipt_current}|"
        f"pm={state.user_intake_mail_exposed},{state.pm_startup_intake_ack_recorded},"
        f"{state.pm_startup_intake_ack_via_common_ledger},{state.pm_route_planning_started}|"
        f"role={state.first_role_work_allocated},{state.current_role_agent_open_attempted},"
        f"{state.current_role_agent_bound},{state.current_role_agent_failed}|"
        f"legacy={state.startup_background_agents_preleased},{state.fixed_role_count_gate_required},"
        f"{state.heartbeat_or_manual_resume_binding_required},{state.legacy_human_startup_review_gate_used},"
        f"{state.legacy_pm_startup_release_gate_used}|work={state.route_work_started}"
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
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
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
        for source, outgoing in enumerate(edges):
            if source not in can_reach_success and any(target in can_reach_success for _label, target in outgoing):
                can_reach_success.add(source)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": bool(success) and not stuck and 0 in can_reach_success,
        "success_state_count": len(success),
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
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


def _hazard_report() -> dict[str, object]:
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
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    optimized_failures = model.invariant_failures(model.optimized_plan_state())
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and not optimized_failures,
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "optimized_plan": {
            "ok": not optimized_failures,
            "failures": optimized_failures,
            "state": model.optimized_plan_state().__dict__,
        },
        "model_boundary": "current startup path model; runtime tests remain required",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    result = run_checks()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
