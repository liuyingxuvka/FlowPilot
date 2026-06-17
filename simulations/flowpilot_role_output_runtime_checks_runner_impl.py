"""Run checks for the FlowPilot role-output runtime model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_role_output_runtime_model as model

from flowpilot_role_output_runtime_checks_runner_source import (
    REQUIRED_OUTPUT_TYPES,
    REQUIRED_CONTRACT_IDS,
    REGISTRY_BINDING_REQUIRED_FIELDS,
    ROUTER_EVENT_MODES,
    ROLE_CARDS,
    _contract_ids,
    _registry_contracts,
    _runtime_binding_contracts,
    _runtime_specs,
    _router_events,
    _binding_source_report,
    _source_report,
)


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_role_output_runtime_results.json"

REQUIRED_LABELS = (
    "select_valid_pm_resume_decision",
    "select_valid_gate_decision",
    "select_valid_reviewer_report",
    "select_valid_controller_boundary_confirmation",
    "select_valid_pm_package_result_disposition",
    "select_forbidden_legacy_startup_activation_approval",
    "select_missing_registry_runtime_binding",
    "select_registry_contract_id_mismatch",
    "select_registry_allowed_role_mismatch",
    "select_registry_router_event_missing",
    "select_unregistered_runtime_output_type",
    "select_missing_runtime_receipt",
    "select_missing_required_field",
    "select_missing_explicit_empty_array",
    "select_wrong_role",
    "select_stale_body_hash",
    "select_inline_body_leak",
    "select_controller_reads_body",
    "select_controller_intermediates_output",
    "select_semantic_auto_approval",
    "select_missing_quality_pack_check",
    "select_pack_specific_runtime_judgment",
    "runtime_prepares_contract_skeleton",
    "role_authors_body_inside_runtime_skeleton",
    "runtime_validates_writes_receipt_and_envelope",
    "runtime_submits_role_output_directly_to_router",
    "router_accepts_runtime_checked_role_output",
    "router_rejects_forbidden_legacy_output_type",
    "router_rejects_missing_registry_runtime_binding",
    "router_rejects_registry_contract_id_mismatch",
    "router_rejects_registry_allowed_role_mismatch",
    "router_rejects_registry_router_event_missing",
    "router_rejects_unregistered_runtime_output_type",
    "router_rejects_missing_runtime_receipt",
    "router_rejects_missing_required_field",
    "router_rejects_missing_explicit_empty_array",
    "router_rejects_wrong_role",
    "router_rejects_stale_body_hash",
    "router_rejects_inline_body_leak",
    "router_rejects_controller_read_body",
    "router_rejects_controller_intermediated_output",
    "router_rejects_runtime_attempted_semantic_approval",
    "router_rejects_missing_quality_pack_check",
    "router_rejects_runtime_attempted_pack_specific_judgment",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_registry_runtime_binding": "without registry runtime binding",
    "registry_contract_id_mismatch": "registry/runtime contract id mismatch",
    "registry_allowed_role_mismatch": "registry/runtime allowed role mismatch",
    "registry_router_event_missing": "missing Router event binding",
    "unregistered_runtime_output_type": "not declared by registry",
    "missing_runtime_receipt": "without runtime receipt",
    "missing_required_field": "missing required field",
    "missing_explicit_empty_array": "missing explicit empty array",
    "wrong_role": "wrong role",
    "stale_body_hash": "stale body hash",
    "inline_body_leak": "leaked body content",
    "controller_reads_body": "Controller body read",
    "controller_intermediates_output": "routed through Controller",
    "missing_direct_router_submission": "without direct Router submission",
    "missing_router_receipt": "was not received by Router",
    "controller_waits_role_instead_of_router": "left Controller waiting on a role instead of Router",
    "router_ready_next_action_waited_on_role": "Router-ready evidence unconsumed before foreground wait",
    "semantic_auto_approval": "replaced semantic gate approval",
    "missing_default_progress_status": "without default progress status",
    "missing_progress_prompt": "without shared progress prompt",
    "progress_status_grants_output_dir": "progress visibility was wider than status metadata",
    "progress_status_leaks_body": "progress status leaked sealed body content",
    "progress_update_manual_write": "progress update bypassed runtime",
    "progress_value_nonnumeric": "progress value was not nonnegative numeric",
    "progress_used_as_semantic_decision": "progress was used as semantic decision evidence",
    "missing_quality_pack_check": "omitted declared quality-pack checks",
    "pack_specific_runtime_judgment": "judged quality-pack semantics",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|output={state.output_type}|"
        f"role={state.submitting_role}->{state.allowed_role}|"
        f"registry={state.registry_runtime_binding_present},"
        f"{state.registry_contract_id_matches_runtime},"
        f"{state.registry_allowed_roles_match_runtime},"
        f"{state.registry_router_event_exists},"
        f"{state.runtime_output_type_declared_by_registry}|"
        f"runtime={state.runtime_receipt_written}|hash={state.body_hash_verified}|"
        f"direct_router={state.direct_router_submission},{state.router_receives_role_output_envelope},"
        f"{state.controller_waits_router_status}|router_ready="
        f"{state.router_ready_evidence_available},"
        f"{state.controller_reentered_router_before_foreground_wait},"
        f"{state.controller_foreground_waits_role_after_router_ready}|"
        f"progress={state.runtime_progress_status_initialized},{state.progress_prompt_included},"
        f"{state.progress_visibility_grant},{state.progress_updates_runtime_written},"
        f"{state.progress_value_numeric},{state.progress_message_metadata_only}|"
        f"router={state.router_decision}:{state.router_rejection_reason}|lane={state.repair_lane}"
    )


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
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
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminals if state.status == "accepted"]
    rejected = [state for state in terminals if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == len(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
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
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _hazard_report() -> dict[str, object]:
    ok = True
    cases: dict[str, str] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        invariant_failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in invariant_failures)
        cases[name] = "detected" if detected else "missed"
        if not detected:
            ok = False
            failures.append(f"{name}: expected invariant failure containing {expected!r}")
    return {"ok": ok, "cases": cases, "failures": failures}


def _pass_fail(ok: bool) -> str:
    return "pass" if ok else "fail"


def run_checks(*, include_source: bool = True) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    hazards = _hazard_report()
    explorer = _flowguard_report()
    source = _source_report(PROJECT_ROOT) if include_source else {
        "ok": True,
        "skipped": "model-only mode skips current source scan",
    }
    ok = all(bool(check["ok"]) for check in (safe_graph, progress, hazards, explorer, source))
    result: dict[str, object] = {
        "ok": ok,
        "checks": {
            "safe_graph": _pass_fail(bool(safe_graph["ok"])),
            "progress": _pass_fail(bool(progress["ok"])),
            "hazard_invariants": _pass_fail(bool(hazards["ok"])),
            "flowguard_explorer": _pass_fail(bool(explorer["ok"])),
            "current_source": _pass_fail(bool(source["ok"])),
        },
        "counts": {
            "states": safe_graph["state_count"],
            "edges": safe_graph["edge_count"],
            "accepted": safe_graph["accepted_state_count"],
            "rejected": safe_graph["rejected_state_count"],
        },
        "source": source,
        "skipped_checks": {
            "semantic_sufficiency": (
                "skipped_with_reason: role_output_runtime is a mechanical "
                "submission runtime; PM/reviewer/FlowGuard operator gates own semantics"
            )
        },
    }
    if not ok:
        result["failure_details"] = {
            "safe_graph": safe_graph,
            "progress": progress,
            "hazards": hazards,
            "flowguard_explorer": explorer,
            "source": source,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks(include_source=not args.model_only)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
