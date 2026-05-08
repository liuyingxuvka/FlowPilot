"""Run checks for the FlowPilot optimization proposal model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_optimization_proposal_model as model


REQUIRED_LABELS = (
    "select_baseline_full_strength_flow",
    "select_phase1_mechanical_receipt_fold",
    "select_phase2_parallel_gate_join",
    "select_phase3_guarded_artifact_and_clean_pass_fold",
    "proposal_profile_evaluation_completed",
)

HAZARD_EXPECTED_FAILURES = {
    "lazy_six_roles": "formal FlowPilot optimization used lazy roles, light mode, or fewer than six live roles",
    "small_task_light_mode": "formal FlowPilot optimization used lazy roles, light mode, or fewer than six live roles",
    "controller_reads_sealed_body": "Controller read sealed body or originated project evidence",
    "router_reset_missing_policy_hash": "router-owned controller receipt lacked core delivery, policy hash, role confirmation, or startup reviewer fact check",
    "router_reset_without_startup_fact_review": "router-owned controller receipt lacked core delivery, policy hash, role confirmation, or startup reviewer fact check",
    "card_bundle_cross_role": "system-card bundle lost same-role, manifest batch, per-card ledger, or hash/path evidence",
    "card_bundle_missing_per_card_ledger": "system-card bundle lost same-role, manifest batch, per-card ledger, or hash/path evidence",
    "ledger_relay_missing_result_open_receipt": "packet ledger relay transaction skipped ledger, delivery, open, result, role, or hash evidence",
    "ledger_relay_missing_hash": "packet ledger relay transaction skipped ledger, delivery, open, result, role, or hash evidence",
    "mechanical_proof_replaces_semantic_review": "router-owned proof was not trusted, file-backed, current-hash, mechanical-only, or non-self-attested",
    "mechanical_proof_self_attested": "router-owned proof was not trusted, file-backed, current-hash, mechanical-only, or non-self-attested",
    "parallel_gate_first_pass_advance": "parallel gate optimization advanced before every reviewer/officer pass joined",
    "parallel_gate_missing_product_officer": "parallel gate optimization advanced before every reviewer/officer pass joined",
    "artifact_merge_collapses_responsibility": "artifact merge collapsed responsibility, freeze points, required sections, node packet, evidence quality, or final ledger order",
    "artifact_merge_early_root_contract_freeze": "artifact merge collapsed responsibility, freeze points, required sections, node packet, evidence quality, or final ledger order",
    "artifact_merge_without_evidence_quality_review": "artifact merge collapsed responsibility, freeze points, required sections, node packet, evidence quality, or final ledger order",
    "auto_advance_without_pm_preauthorization": "clean-pass auto advance was used outside mechanical, preauthorized, all-pass, blocker-free state",
    "auto_advance_during_route_mutation": "clean-pass auto advance was used outside mechanical, preauthorized, all-pass, blocker-free state",
    "auto_advance_replaces_quality_judgement": "clean-pass auto advance was used outside mechanical, preauthorized, all-pass, blocker-free state",
    "terminal_lifecycle_before_pm_closure": "router-owned terminal lifecycle cleanup ran before PM closure, final replay, clean ledger, or closure ordering",
    "terminal_lifecycle_before_final_replay": "router-owned terminal lifecycle cleanup ran before PM closure, final replay, clean ledger, or closure ordering",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|profile={state.profile}|steps={state.handoff_steps}|"
        f"critical={state.critical_path_ticks}|roles={state.six_roles_live}|"
        f"light={state.light_mode_used}|lazy={state.lazy_spawn_used}|"
        f"router_receipt={state.router_owned_controller_receipt},{state.controller_policy_hash_recorded}|"
        f"bundle={state.same_role_card_bundle_used},{state.cross_role_bundle_used},"
        f"{state.manifest_batch_checked},{state.per_card_ledger_entries_kept}|"
        f"relay={state.packet_ledger_relay_transaction_used},{state.packet_ledger_check_receipt},"
        f"{state.reviewer_result_open_receipt_recorded},{state.body_hash_verified}|"
        f"proof={state.router_mechanical_proof_used},{state.reviewer_replacement_scope_mechanical_only},"
        f"semantic_replaced={state.proof_replaces_semantic_review}|"
        f"parallel={state.parallel_gate_checks_used},{state.pm_waited_for_all_parallel_passes},"
        f"first={state.advanced_after_first_parallel_pass}|"
        f"artifact={state.artifact_merge_used},{state.merged_artifact_responsibilities_separate},"
        f"freeze={state.root_contract_freeze_separate},evidence={state.evidence_quality_reviewer_passed}|"
        f"auto={state.clean_pass_auto_advance_used},{state.pm_clean_pass_preauthorized},"
        f"mutation={state.route_mutation_pending},quality={state.quality_judgement_pending}|"
        f"terminal={state.terminal_lifecycle_router_owned},{state.pm_closure_approved},"
        f"{state.terminal_backward_replay_passed}"
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


def _proposal_matrix() -> dict[str, object]:
    baseline = model.baseline_state()
    matrix: dict[str, object] = {}
    for name, item in model.proposal_catalog().items():
        state = item["profile"]
        assert isinstance(state, model.State)
        handoff_saved = baseline.handoff_steps - state.handoff_steps
        critical_saved = baseline.critical_path_ticks - state.critical_path_ticks
        handoff_reduction = round((handoff_saved / baseline.handoff_steps) * 100, 2)
        critical_reduction = round((critical_saved / baseline.critical_path_ticks) * 100, 2)
        failures = model.invariant_failures(state)
        matrix[name] = {
            "ok": not failures,
            "interpretation": item["interpretation"],
            "scope": item["scope"],
            "runtime_readiness": item["runtime_readiness"],
            "handoff_steps": state.handoff_steps,
            "handoff_steps_saved": handoff_saved,
            "handoff_reduction_percent": handoff_reduction,
            "critical_path_ticks": state.critical_path_ticks,
            "critical_path_ticks_saved": critical_saved,
            "critical_path_reduction_percent": critical_reduction,
            "failures": failures,
        }
    return matrix


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    proposal_matrix = _proposal_matrix()
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and all(bool(item["ok"]) for item in proposal_matrix.values()),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "proposal_matrix": proposal_matrix,
        "model_boundary": (
            "proposal-only model; no FlowPilot runtime, prompt card, route, "
            "or installer behavior is changed or proven by this check"
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
