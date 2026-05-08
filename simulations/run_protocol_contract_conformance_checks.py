"""Run checks for the FlowPilot concrete protocol/contract model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_protocol_contract_conformance_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "protocol_contract_conformance_results.json"

REQUIRED_LABELS = (
    "select_valid_fixed_protocol",
    "select_startup_fact_jsonpath_mismatch",
    "select_control_blocker_ambiguous_event",
    "select_control_blocker_weak_decision_contract",
    "select_pm_resume_decision_weak_contract",
    "select_startup_fact_hash_alias",
    "select_cockpit_missing_host_receipt",
    "select_display_fallback_after_pm_activation",
    "select_startup_repair_dedupes_new_report",
    "select_role_output_envelope_ambiguity",
    "select_material_scan_inline_body_only",
    "select_material_dispatch_unknown_block_event",
    "select_material_dispatch_frontier_phase_mismatch",
    "router_accepts_conformant_protocol",
    "router_rejects_startup_fact_jsonpath_mismatch",
    "router_rejects_control_blocker_ambiguous_event",
    "router_rejects_control_blocker_weak_decision_contract",
    "router_rejects_pm_resume_decision_weak_contract",
    "router_rejects_startup_fact_hash_alias",
    "router_rejects_cockpit_missing_host_receipt",
    "router_rejects_display_fallback_after_pm_activation",
    "router_rejects_startup_repair_dedupes_new_report",
    "router_rejects_role_output_envelope_ambiguity",
    "router_rejects_material_scan_inline_body_only",
    "router_rejects_material_dispatch_unknown_block_event",
    "router_rejects_material_dispatch_frontier_phase_mismatch",
)

HAZARD_EXPECTED_FAILURES = {
    "startup_fact_jsonpath_mismatch": "reviewer_checked_requirement_ids",
    "control_blocker_ambiguous_event": "PM control-blocker lane",
    "control_blocker_weak_decision_contract": "PM control-blocker output contract",
    "pm_resume_decision_weak_contract": "PM resume decision output contract",
    "startup_fact_hash_alias": "startup fact role submission can alias",
    "cockpit_missing_host_receipt": "cockpit requested without host receipt",
    "display_fallback_after_pm_activation": "display fallback receipt is unavailable before startup reviewer fact review",
    "startup_repair_dedupes_new_report": "startup repair event is deduped by a one-shot flag",
    "role_output_envelope_ambiguity": "role output guidance omits exact path/hash pairs",
    "material_scan_inline_body_only": "PM material scan guidance does not require file-backed packet body paths and hashes",
    "material_dispatch_unknown_block_event": "material dispatch reviewer block event is not registered",
    "material_dispatch_frontier_phase_mismatch": "material dispatch review can run while execution_frontier still reports startup_intake",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"router={state.router_decision}:{state.router_rejection_reason}"
    )


def _build_reachable_graph() -> dict[str, Any]:
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


def _check_safe_graph(graph: dict[str, Any]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminal_states = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal_states if state.status == "accepted"]
    rejected = [state for state in terminal_states if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == 1
        and accepted[0].scenario == model.VALID_FIXED_PROTOCOL
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
        "rejected_state_count": len(rejected),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _check_progress(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}

    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
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


def _run_flowguard_explorer() -> dict[str, object]:
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


def _check_hazards() -> dict[str, object]:
    results: dict[str, str] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        invariant_failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in invariant_failures)
        results[name] = "detected" if detected else "missed"
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "results": results, "failures": failures}


def _check_current_source() -> dict[str, object]:
    state = model.collect_source_state(PROJECT_ROOT)
    failures = model.protocol_failures(state)
    return {
        "ok": not failures,
        "failures": failures,
        "facts": {
            "startup_contract_paths": sorted(state.startup_contract_paths),
            "startup_card_example_paths": sorted(state.startup_card_example_paths),
            "startup_card_prose_paths": sorted(state.startup_card_prose_paths),
            "startup_router_validator_paths": sorted(state.startup_router_validator_paths),
            "pm_control_blocker_allowed_events": sorted(state.pm_control_blocker_allowed_events),
            "pm_control_blocker_card_events": sorted(state.pm_control_blocker_card_events),
            "pm_control_blocker_contract_fields": sorted(state.pm_control_blocker_contract_fields),
            "pm_control_blocker_router_fields": sorted(state.pm_control_blocker_router_fields),
            "pm_control_blocker_card_fields": sorted(state.pm_control_blocker_card_fields),
            "pm_resume_contract_fields": sorted(state.pm_resume_contract_fields),
            "pm_resume_router_fields": sorted(state.pm_resume_router_fields),
            "pm_resume_card_fields": sorted(state.pm_resume_card_fields),
            "pm_resume_action_contract_fields": sorted(state.pm_resume_action_contract_fields),
            "router_rewrites_startup_fact_canonical": state.router_rewrites_startup_fact_canonical,
            "startup_role_may_submit_to_canonical_path": state.startup_role_may_submit_to_canonical_path,
            "router_blocks_startup_fact_canonical_alias": state.router_blocks_startup_fact_canonical_alias,
            "display_status_available_before_startup_fact_review": state.display_status_available_before_startup_fact_review,
            "startup_repair_request_repeatable_for_new_blocking_report": state.startup_repair_request_repeatable_for_new_blocking_report,
            "startup_repair_request_tracks_cycle_identity": state.startup_repair_request_tracks_cycle_identity,
            "startup_repair_exact_duplicate_rejected": state.startup_repair_exact_duplicate_rejected,
            "role_output_contract_path_hash_pairs": sorted(state.role_output_contract_path_hash_pairs),
            "role_output_router_path_hash_pairs": sorted(state.role_output_router_path_hash_pairs),
            "role_output_card_path_hash_pairs": sorted(state.role_output_card_path_hash_pairs),
            "role_output_cards_require_top_level_keys": state.role_output_cards_require_top_level_keys,
            "role_output_cards_forbid_sha256_aliases": state.role_output_cards_forbid_sha256_aliases,
            "role_output_router_rejects_sha256_aliases": state.role_output_router_rejects_sha256_aliases,
            "role_output_router_rejects_nested_envelope": state.role_output_router_rejects_nested_envelope,
            "material_scan_card_requires_file_backed_packet_bodies": state.material_scan_card_requires_file_backed_packet_bodies,
            "material_scan_router_accepts_file_backed_packet_specs": state.material_scan_router_accepts_file_backed_packet_specs,
            "material_scan_router_requires_inline_body_text_only": state.material_scan_router_requires_inline_body_text_only,
            "material_scan_index_forbids_controller_body_reads": state.material_scan_index_forbids_controller_body_reads,
            "material_dispatch_block_event_registered": state.material_dispatch_block_event_registered,
            "material_dispatch_block_report_writer": state.material_dispatch_block_report_writer,
            "material_dispatch_pm_block_cards_reachable": state.material_dispatch_pm_block_cards_reachable,
            "material_dispatch_route_memory_tracks_block": state.material_dispatch_route_memory_tracks_block,
            "material_dispatch_relay_requires_allow_without_block": state.material_dispatch_relay_requires_allow_without_block,
            "material_dispatch_frontier_phase_synchronized": state.material_dispatch_frontier_phase_synchronized,
            "material_dispatch_card_has_pre_route_material_exception": state.material_dispatch_card_has_pre_route_material_exception,
            "material_scan_packets_mark_pre_route_not_current_node": state.material_scan_packets_mark_pre_route_not_current_node,
        },
    }


def _pass_fail(ok: bool) -> str:
    return "pass" if ok else "fail"


def run_checks(*, include_source: bool = True) -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _check_safe_graph(graph)
    progress = _check_progress(graph)
    hazards = _check_hazards()
    explorer = _run_flowguard_explorer()
    current_source = _check_current_source() if include_source else {
        "ok": True,
        "skipped": "model-only mode skips current source scan",
    }

    ok = all(
        bool(check["ok"])
        for check in (safe_graph, progress, hazards, explorer, current_source)
    )

    result: dict[str, object] = {
        "ok": ok,
        "checks": {
            "safe_graph": _pass_fail(bool(safe_graph["ok"])),
            "progress": _pass_fail(bool(progress["ok"])),
            "hazard_invariants": _pass_fail(bool(hazards["ok"])),
            "flowguard_explorer": _pass_fail(bool(explorer["ok"])),
            "current_source_conformance": _pass_fail(bool(current_source["ok"])),
        },
        "counts": {
            "states": safe_graph["state_count"],
            "edges": safe_graph["edge_count"],
            "accepted": safe_graph["accepted_state_count"],
            "rejected": safe_graph["rejected_state_count"],
        },
        "hazards": hazards["results"],
        "current_source": current_source,
        "skipped_checks": {
            "production_replay": (
                "skipped_with_reason: this check scans source facts and explores "
                "a protocol model; it is not a full runtime transcript replay"
            )
        },
    }

    if not ok:
        result["failure_details"] = {
            "safe_graph": safe_graph,
            "progress": progress,
            "hazard_invariants": hazards,
            "flowguard_explorer": explorer,
            "current_source": current_source,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-only",
        action="store_true",
        help="Verify the abstract model and known hazards without scanning current source files.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=RESULTS_PATH,
        help="Path for writing the JSON result payload.",
    )
    args = parser.parse_args()

    result = run_checks(include_source=not args.model_only)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
