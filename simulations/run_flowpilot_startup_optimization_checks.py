"""Run checks for the FlowPilot startup optimization model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_startup_optimization_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_startup_optimization_results.json"


HAZARD_EXPECTED_FAILURES = {
    "roles_ready_without_core_receipts": "roles became ready without six current-run role slots, core prompt hashes, and role I/O receipts",
    "later_core_injection_required": "optimized startup still required a delayed role-core injection gate",
    "fewer_than_six_roles": "roles became ready without six current-run role slots, core prompt hashes, and role I/O receipts",
    "heartbeat_before_run_or_roles": "heartbeat was created before current run and role ledger existed",
    "heartbeat_after_reviewer_dispatch": "reviewer startup fact card was dispatched before early heartbeat binding",
    "heartbeat_wrong_cadence": "heartbeat lacked current-run one-minute verified host proof",
    "heartbeat_missing_host_proof": "heartbeat lacked current-run one-minute verified host proof",
    "controller_loaded_before_roles": "Controller loaded before run shell and six-role startup receipts existed",
    "controller_reads_sealed_body": "Controller read sealed role body during startup optimization",
    "self_attested_proof": "self-attested startup claim was used as proof",
    "reviewer_without_mechanical_proof": "reviewer startup fact card lacked current mechanical proof or display evidence",
    "reviewer_without_display_receipt": "reviewer startup fact card lacked current mechanical proof or display evidence",
    "reviewer_reproves_router_facts": "reviewer was required to re-prove router-owned mechanical facts",
    "pm_prep_before_reviewer": "PM startup prep started before reviewer startup fact card dispatch",
    "pm_prep_no_join_policy": "PM prep lacked independence and join policy while reviewer report was pending",
    "pm_prep_blocks_reviewer": "PM prep blocked reviewer startup fact progress",
    "startup_join_without_reviewer": "startup join was marked clean before reviewer report and PM prep completion",
    "pm_activation_before_join": "PM startup activation occurred before reviewer and PM prep joined",
    "work_before_pm_activation": "work beyond startup was allowed before PM startup activation",
    "route_work_before_startup_open": "route or material work started before startup activation opened",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|answers={state.startup_answers_recorded}|"
        f"run={state.run_shell_created},{state.current_pointer_written},{state.run_index_updated}|"
        f"roles={state.six_roles_started},{state.role_core_prompts_delivered_at_spawn},"
        f"{state.role_core_prompt_hashes_recorded},{state.role_io_protocol_receipts_current},"
        f"later_core={state.later_core_injection_required},few={state.fewer_than_six_roles_used}|"
        f"heartbeat={state.scheduled_continuation_requested},{state.heartbeat_created},"
        f"{state.heartbeat_bound_to_current_run},{state.heartbeat_interval_minutes},"
        f"{state.heartbeat_host_proof_verified}|"
        f"controller={state.controller_loaded},{state.controller_boundary_confirmed},"
        f"body={state.controller_read_sealed_body},selfproof={state.self_attested_claim_used_as_proof}|"
        f"audit={state.mechanical_audit_written},{state.router_owned_mechanical_proof_current},"
        f"display={state.display_receipt_written},{state.display_receipt_visible_to_reviewer}|"
        f"reviewer={state.reviewer_fact_card_dispatched},"
        f"first={state.reviewer_fact_card_dispatched_before_pm_prep},"
        f"reprove={state.reviewer_required_to_reprove_router_facts},"
        f"report={state.reviewer_report_returned},{state.reviewer_external_facts_checked}|"
        f"pm={state.pm_prep_started},{state.pm_prep_independent_after_reviewer_dispatch},"
        f"{state.pm_prep_join_policy_recorded},{state.pm_prep_completed},"
        f"blocks={state.pm_prep_blocked_reviewer}|"
        f"join={state.startup_join_clean}|activation={state.pm_activation_approved},"
        f"open={state.work_beyond_startup_allowed}|work={state.route_or_material_work_started}"
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
        "model_boundary": "startup control-plane optimization model; runtime tests remain required",
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
