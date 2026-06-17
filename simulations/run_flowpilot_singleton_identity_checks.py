"""Run FlowGuard singleton-identity authority checks for FlowPilot."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover - exercised by package import tests
    from . import flowpilot_singleton_identity_model as model
except ImportError:  # pragma: no cover - exercised by direct script execution
    import flowpilot_singleton_identity_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_singleton_identity_results.json"

REQUIRED_LABELS = (
    "select_legal_parallel_runs",
    "select_duplicate_daemon_writer",
    "select_active_packet_same_identity_replay",
    "select_active_packet_conflicting_holder",
    "select_pm_package_same_body_replay",
    "select_pm_package_different_body_conflict",
    "select_route_replacement_old_packet_disposed",
    "select_route_replacement_old_packet_undisposed",
    "select_material_reissue_stale_global_flag",
    "select_ack_only_output_closure",
    "select_final_progress_only_closure",
    "select_missing_ledger_evidence",
    "classify_intended_plurality_with_explicit_target",
    "classify_same_identity_replay_idempotent",
    "classify_duplicate_authority_without_disposition",
    "classify_same_identity_different_body_conflict",
    "classify_stale_evidence_current_authority_risk",
    "classify_ack_only_output_completion_risk",
    "classify_progress_only_completion_risk",
    "classify_missing_ledger_evidence",
)

HAZARD_EXPECTED_FAILURES = {
    "plurality_without_target_marked_safe": "intended plurality was marked safe without explicit operation target",
    "duplicate_daemon_writer_marked_safe": "duplicate singleton authority was marked safe",
    "package_conflict_marked_replay": "same singleton identity with different body hash was treated as replay",
    "replacement_without_disposition_marked_safe": "replacement or reissue was safe without old-object disposition",
    "stale_material_flag_marked_current": "replacement or reissue was safe without old-object disposition",
    "ack_only_output_marked_complete": "ACK settlement completed semantic output",
    "progress_only_final_marked_complete": "progress-only singleton evidence was consumed as completion",
    "missing_ledger_marked_safe": "missing singleton ledger evidence was treated as safe",
    "idempotent_replay_overblocked": "idempotent singleton replay was overblocked as risk",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|family={state.object_family}|"
        f"plural={state.intended_plurality}|target={state.explicit_target_required}|"
        f"dupes={state.duplicate_authority_count}|replay={state.same_identity_replay}|"
        f"body={state.same_body_hash}|repair={state.authorized_reissue_or_repair}|"
        f"disposed={state.old_object_disposed}|stale={state.stale_evidence_consumed_as_current}|"
        f"progress_only={state.progress_only_evidence_consumed_as_completion}|"
        f"ack={state.ack_settled}|output={state.output_completed}|ledger={state.required_ledger_present}|"
        f"classification={state.classification}"
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
    terminal_states = [state for state in states if model.is_terminal(state)]
    by_status: dict[str, list[str]] = {}
    for state in terminal_states:
        by_status.setdefault(state.status, []).append(state.scenario)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(by_status.get("safe", [])) == model.SAFE_SCENARIOS
        and set(by_status.get("risk", [])) == model.RISK_SCENARIOS
        and set(by_status.get("evidence_insufficient", [])) == model.EVIDENCE_INSUFFICIENT_SCENARIOS,
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "safe": sorted(by_status.get("safe", [])),
        "risk": sorted(by_status.get("risk", [])),
        "evidence_insufficient": sorted(by_status.get("evidence_insufficient", [])),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if idx not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
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
    ok = True
    hazards: dict[str, dict[str, object]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": _state_id(state),
        }
    return {"ok": ok, "hazards": hazards}


def run_checks(*, repo_root: Path = PROJECT_ROOT) -> dict[str, object]:
    graph = _build_graph()
    safe = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    matrix = model.matrix_rows_as_dicts()
    matrix_ok = all(
        row["singleton_scope"]
        and row["canonical_owner"]
        and row["identity_key"]
        and row["old_object_disposition"]
        for row in matrix
    )
    live_audit = model.build_live_singleton_audit(repo_root)
    live_risk_count = int(live_audit.get("risk_count", 0))
    live_gap_count = int(live_audit.get("evidence_insufficient_count", 0))
    model_ok = bool(safe["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]) and matrix_ok
    full_closure_ok = model_ok and live_risk_count == 0 and live_gap_count == 0
    return {
        "ok": model_ok,
        "result_type": "flowpilot_singleton_identity",
        "model": model.MODEL_ID,
        "claim_scope": "FlowPilot singleton-vs-plural authority for routine maintenance and local install confidence",
        "confidence": "full" if full_closure_ok else "scoped",
        "full_closure_ok": full_closure_ok,
        "safe_graph": safe,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_detection": hazards,
        "authority_matrix_ok": matrix_ok,
        "authority_matrix_count": len(matrix),
        "authority_matrix": matrix,
        "live_audit": live_audit,
        "recommended_actions": (
            []
            if full_closure_ok
            else [
                "inspect_live_singleton_audit_gaps",
                "refresh_or_attach_missing_singleton_evidence",
                "downgrade_broad_confidence_to_scoped_until_current",
            ]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    result = run_checks(repo_root=args.repo_root)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
