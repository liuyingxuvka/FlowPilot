"""Run checks for the FlowPilot record-event envelope transfer model."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_event_envelope_transfer_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_event_envelope_transfer_results.json"

REQUIRED_LABELS = (
    "select_valid_reviewer_full_payload",
    "select_valid_reviewer_envelope_ref",
    "select_valid_material_full_payload",
    "select_valid_material_envelope_ref",
    "select_manual_receipt_field_renamed",
    "select_manual_packets_nested_or_dropped",
    "select_duplicate_same_envelope",
    "select_missing_envelope_file",
    "select_envelope_hash_mismatch",
    "select_bad_envelope_schema",
    "select_event_name_mismatch",
    "select_from_role_mismatch",
    "select_bad_controller_visibility",
    "select_forbidden_body_field",
    "select_outside_allowed_event",
    "select_missing_runtime_receipt_ref",
    "router_accepts_full_payload_or_verified_envelope_ref",
    "router_returns_already_recorded_for_duplicate_same_envelope",
)

HAZARD_EXPECTED_FAILURES = {
    "accepted_without_hash_check": "accepted envelope without all hard checks",
    "accepted_outside_allowed_event": "accepted envelope without all hard checks",
    "accepted_wrong_role": "accepted envelope without all hard checks",
    "accepted_forbidden_body_field": "accepted envelope without all hard checks",
    "ref_controller_mutated_envelope": "envelope ref path let Controller mutate envelope fields",
    "manual_receipt_accepted": "manual reconstruction with renamed runtime receipt was accepted",
    "manual_packets_accepted": "manual reconstruction with hidden material packets was accepted",
    "duplicate_side_effect": "duplicate same envelope wrote a duplicate side effect",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|mode={state.input_mode}|"
        f"event={state.event}|role={state.from_role}->{state.expected_role}|"
        f"checks=path:{state.envelope_path_project_local},file:{state.envelope_file_exists},"
        f"hash:{state.envelope_hash_matches},schema:{state.schema_allowed},"
        f"event:{state.event_name_matches_cli},allowed:{state.event_currently_allowed},"
        f"role:{state.from_role_matches_contract},vis:{state.controller_visibility_allowed},"
        f"body:{state.forbidden_body_fields_absent}|"
        f"runtime_ref={state.runtime_receipt_ref_preserved}|packets={state.material_packets_preserved_top_level}|"
        f"duplicate={state.duplicate_submission}:{state.duplicate_side_effect_written}|reason={state.terminal_reason}"
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
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminals if state.status == "accepted"]
    rejected = [state for state in terminals if state.status == "rejected"]
    already_recorded = [state for state in terminals if state.status == "already_recorded"]
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == len(model.ACCEPTED_SCENARIOS)
        and len(rejected) == len(model.REJECTED_SCENARIOS)
        and len(already_recorded) == len(model.IDEMPOTENT_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
        "rejected_state_count": len(rejected),
        "already_recorded_state_count": len(already_recorded),
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
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
    cases: dict[str, dict[str, object]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        cases[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": _state_id(state),
        }
    return {"ok": ok, "hazards": cases}


def _scenario_report(graph: dict[str, Any]) -> dict[str, object]:
    terminal_by_scenario = {
        state.scenario: state
        for state in graph["states"]
        if isinstance(state, model.State) and model.is_terminal(state)
    }
    reviewer_full = terminal_by_scenario.get(model.VALID_REVIEWER_FULL)
    reviewer_ref = terminal_by_scenario.get(model.VALID_REVIEWER_REF)
    material_full = terminal_by_scenario.get(model.VALID_MATERIAL_FULL)
    material_ref = terminal_by_scenario.get(model.VALID_MATERIAL_REF)
    manual_receipt = terminal_by_scenario.get(model.MANUAL_RECEIPT_RENAMED)
    manual_packets = terminal_by_scenario.get(model.MANUAL_PACKETS_NESTED)
    duplicate = terminal_by_scenario.get(model.DUPLICATE_SAME_ENVELOPE)
    scenarios = {
        "reviewer_full_payload_and_ref_equivalent": {
            "ok": reviewer_full is not None
            and reviewer_ref is not None
            and reviewer_full.status == "accepted"
            and reviewer_ref.status == "accepted"
            and reviewer_ref.runtime_receipt_ref_preserved,
            "full": _state_id(reviewer_full) if reviewer_full else None,
            "ref": _state_id(reviewer_ref) if reviewer_ref else None,
        },
        "material_full_payload_and_ref_equivalent": {
            "ok": material_full is not None
            and material_ref is not None
            and material_full.status == "accepted"
            and material_ref.status == "accepted"
            and material_ref.material_packets_preserved_top_level,
            "full": _state_id(material_full) if material_full else None,
            "ref": _state_id(material_ref) if material_ref else None,
        },
        "known_manual_reconstruction_failures_rejected": {
            "ok": manual_receipt is not None
            and manual_packets is not None
            and manual_receipt.status == "rejected"
            and manual_packets.status == "rejected",
            "manual_receipt": _state_id(manual_receipt) if manual_receipt else None,
            "manual_packets": _state_id(manual_packets) if manual_packets else None,
        },
        "duplicate_same_envelope_idempotent": {
            "ok": duplicate is not None
            and duplicate.status == "already_recorded"
            and not duplicate.duplicate_side_effect_written,
            "duplicate": _state_id(duplicate) if duplicate else None,
        },
    }
    return {"ok": all(item["ok"] for item in scenarios.values()), "scenarios": scenarios}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    scenarios = _scenario_report(graph)
    return {
        "model": "flowpilot_event_envelope_transfer",
        "model_boundary": "record-event envelope transfer; semantic body review remains out of scope",
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_detection": hazards,
        "scenario_checks": scenarios,
        "ok": all(
            section["ok"]
            for section in (safe_graph, progress, flowguard, hazards, scenarios)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args(argv)
    report = run_checks()
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
