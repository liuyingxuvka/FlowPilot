"""Run checks for the FlowPilot route mutation activation/display model."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_route_mutation_activation_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_route_mutation_activation_results.json"
RUNTIME_PATH = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
ROUTE_MUTATION_PATH = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_route.py"
PARENT_SEGMENT_PATH = (
    REPO_ROOT
    / "skills"
    / "flowpilot"
    / "assets"
    / "flowpilot_router_route_artifacts_nodes_parent.py"
)
RELEVANT_TEST_PATHS = (
    REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py",
    REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py",
    REPO_ROOT / "tests" / "router_runtime" / "route_mutation_sibling_replacement.py",
    REPO_ROOT / "tests" / "router_runtime" / "route_mutation_parent_backward.py",
    REPO_ROOT / "tests" / "test_flowpilot_user_flow_diagram.py",
    REPO_ROOT / "tests" / "test_flowpilot_unified_repair_runtime.py",
)


REQUIRED_LABELS = (
    "reviewer_block_records_route_mutation_need",
    "pm_proposes_return_repair_candidate_route",
    "pm_proposes_supersede_replacement_candidate_route",
    "pm_proposes_branch_then_continue_candidate_route",
    "pm_proposes_sibling_branch_replacement_candidate_route",
    "controller_records_stale_evidence_before_route_recheck",
    "controller_supersedes_old_current_node_packet_for_route_mutation",
    "flowguard_operator_route_scope_simulates_candidate_route",
    "flowguard_operator_product_scope_checks_candidate_route",
    "human_like_reviewer_challenges_candidate_route",
    "pm_activates_checked_candidate_route",
    "execution_frontier_enters_activated_mutation_node",
    "reviewer_reruns_same_scope_replay_after_route_mutation",
    "route_sign_displays_activated_current_mutation_node",
    "route_mutation_activation_display_complete",
)


HAZARD_EXPECTED_FAILURES = {
    "active_flow_overwritten_before_activation": "candidate route overwrote active flow.json before checked PM activation",
    "frontier_entered_candidate_before_activation": "execution frontier entered candidate node before route activation",
    "candidate_route_displayed_before_activation": "candidate repair route was displayed as current before activation",
    "parent_decision_self_invalidates_nested_route_mutation_authority": "route mutation revalidated route memory after its own parent-decision write",
    "activation_without_process_recheck": "PM activated candidate route before process FlowGuard recheck",
    "activation_without_product_or_reviewer_recheck": "PM activated candidate route before product FlowGuard recheck",
    "missing_topology_strategy": "route mutation proposal lacks an explicit topology strategy",
    "supersede_original_forced_to_return": "supersede_original mutation was incorrectly forced to return to the old node",
    "return_repair_without_return_target": "return_to_original mutation lacks repair_return_to_node_id",
    "sibling_replacement_without_affected_siblings": "sibling_branch_replacement mutation lacks affected sibling nodes",
    "sibling_replacement_without_replay_scope": "sibling_branch_replacement mutation lacks replay scope",
    "old_sibling_evidence_reused_after_replacement": "old sibling evidence was reused as current proof after replacement",
    "route_recheck_before_old_packet_superseded": "route recheck started while the old current-node packet still blocked PM work",
    "final_scan_before_same_scope_replay_after_mutation": "final ledger started before same-scope replay after route mutation",
    "repair_rendered_as_final_mainline": "repair node was rendered as a final sequential mainline stage",
    "superseded_node_visible_as_pending": "superseded old node remained visible as a pending or active obligation",
    "stale_evidence_reused_before_activation": "PM activated candidate route before stale evidence was invalidated",
    "generated_files_only_display": "route sign display used generated files without user-visible receipt",
    "sealed_body_boundary_broken": "route mutation display weakened the sealed packet/result body boundary",
    "replacement_drops_unaffected_sibling": "route replacement lost unaffected effective siblings",
    "unaffected_sibling_not_rebound": "unaffected siblings were not rebound into the activated route version",
    "activated_route_version_mismatch": "activated route version disagrees with the replacement route version",
    "final_ledger_effective_members_mismatch": "final ledger effective members disagree with activated effective route members",
    "terminal_targets_effective_members_mismatch": "terminal replay targets disagree with activated effective route members",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|block={state.reviewer_block_recorded}|"
        f"proposal={state.pm_mutation_proposed},{state.topology_strategy}|"
        f"authority=validated:{state.route_memory_authority_validated_before_event_write},"
        f"same:{state.route_mutation_consumed_same_authority},"
        f"revalidated_after_write:{state.route_memory_revalidated_after_parent_decision_write}|"
        f"fields=repair:{state.repair_node_id_declared},of:{state.repair_of_node_id_declared},"
        f"return:{state.return_target_declared},superseded:{state.superseded_nodes_declared},"
        f"continue:{state.continue_target_declared},affected_siblings:{state.affected_sibling_nodes_declared},"
        f"replay_scope:{state.replay_scope_declared}|members=before:{state.before_effective_member_ids},"
        f"superseded:{state.superseded_effective_member_ids},replacement:{state.replacement_effective_member_id},"
        f"after:{state.after_effective_member_ids},unaffected:{state.unaffected_sibling_node_ids},"
        f"rebound:{state.unaffected_siblings_rebound},versions:{state.active_route_version}/"
        f"{state.candidate_route_version}:{state.after_member_route_versions},"
        f"ledger:{state.final_ledger_effective_member_ids},terminal:{state.terminal_target_member_ids}|"
        f"early=active:{state.active_route_overwritten_before_activation},"
        f"frontier:{state.frontier_entered_candidate_before_activation},display:{state.candidate_route_displayed_as_current}|"
        f"checks=stale:{state.stale_evidence_invalidated},packet_superseded:{state.old_current_node_packet_superseded},"
        f"process:{state.process_recheck_passed},"
        f"product:{state.product_recheck_passed},review:{state.reviewer_recheck_passed},pm:{state.pm_activation_recorded}|"
        f"entry={state.candidate_node_entry_recorded},same_scope_replay:{state.same_scope_replay_rerun_after_mutation},"
        f"final_ledger:{state.final_ledger_started}|visible={state.route_visible_as_current},"
        f"receipt:{state.display_receipt_recorded},topology:{state.mermaid_topology_projected},"
        f"final_append:{state.repair_rendered_as_final_mainline},sup_pending:{state.superseded_node_shown_as_pending},"
        f"forced_return:{state.forced_return_for_supersede},old_sibling_evidence:{state.old_sibling_evidence_reused_as_current},"
        f"files_only:{state.generated_files_only_display},"
        f"sealed:{state.sealed_body_boundary_preserved}"
    )


def _build_graph() -> dict[str, object]:
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
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "terminal_state_count": len(terminal),
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


def _source_slice(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    end_index = text.find(end, start_index + len(start))
    return text[start_index:] if end_index < 0 else text[start_index:end_index]


def _production_conformance_report() -> dict[str, object]:
    runtime_text = RUNTIME_PATH.read_text(encoding="utf-8")
    test_texts = {str(path.relative_to(REPO_ROOT)).replace("\\", "/"): path.read_text(encoding="utf-8") for path in RELEVANT_TEST_PATHS}
    replacement_source = _source_slice(
        runtime_text,
        "def _replace_route_node_for_repair(",
        "def _role_continuity_table(",
    )
    core_tests = test_texts["tests/test_flowpilot_core_runtime.py"]
    high_standard_tests = test_texts["tests/test_flowpilot_high_standard_control_flow.py"]
    sibling_tests = test_texts["tests/router_runtime/route_mutation_sibling_replacement.py"]
    parent_tests = test_texts["tests/router_runtime/route_mutation_parent_backward.py"]
    unified_repair_tests = test_texts["tests/test_flowpilot_unified_repair_runtime.py"]
    route_mutation_text = ROUTE_MUTATION_PATH.read_text(encoding="utf-8")
    parent_segment_text = PARENT_SEGMENT_PATH.read_text(encoding="utf-8")
    obligations = {
        "parent_segment_validates_route_memory_before_event_local_write": (
            "_validate_route_mutation_authority(" in parent_segment_text
            and "validated_authority=mutation_authority" in parent_segment_text
            and "_ValidatedRouteMutationAuthority" in route_mutation_text
        ),
        "route_mutation_rejects_unvalidated_authority_dict_test": (
            "test_route_mutation_rejects_unvalidated_authority_dict" in parent_tests
        ),
        "parent_segment_same_authority_success_test": (
            "test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun" in parent_tests
        ),
        "runtime_rebinds_unaffected_members_to_new_route_version": any(
            marker in replacement_source
            for marker in (
                'ledger["route_nodes"][item_id]["route_version"] = new_version',
                'rebound_unaffected_node_ids',
                'unaffected_sibling_node_ids',
                'unaffected_rebound_ids',
            )
        ),
        "runtime_records_before_after_effective_member_inventory": (
            "before_effective_member_ids" in replacement_source
            and "after_effective_member_ids" in replacement_source
        ),
        "route_repair_unaffected_sibling_rebind_test": (
            "test_route_repair_rebinds_unaffected_siblings_into_new_effective_route" in core_tests
            or "test_route_repair_rebinds_unaffected_siblings_into_new_effective_route" in high_standard_tests
            or "test_route_repair_rebinds_unaffected_siblings_into_new_effective_route" in unified_repair_tests
        ),
        "final_ledger_and_terminal_targets_match_effective_members_test": (
            "test_route_repair_final_ledger_and_terminal_targets_match_effective_members" in core_tests
            or "test_route_repair_final_ledger_and_terminal_targets_match_effective_members" in high_standard_tests
            or "test_route_repair_final_ledger_and_terminal_targets_match_effective_members" in unified_repair_tests
        ),
        "existing_replacement_activation_baseline_tests_present": all(
            name in (core_tests + high_standard_tests + sibling_tests)
            for name in (
                "test_pm_disposition_repair_current_scope_creates_replacement_node",
                "test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
            )
        ),
        "runtime_uses_active_route_version_for_effective_member_selection": (
            "def _active_route_node_records(" in runtime_text
            and 'ledger.get("active_route_version")' in runtime_text
        ),
    }
    missing = [name for name, covered in obligations.items() if not covered]
    return {
        "ok": not missing,
        "status": "passed" if not missing else "failed",
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            for path in (
                RUNTIME_PATH,
                ROUTE_MUTATION_PATH,
                PARENT_SEGMENT_PATH,
                *RELEVANT_TEST_PATHS,
            )
        ],
        "claim_boundary": (
            "This is current source/test conformance, not a skipped replay. A route-version filter without "
            "retained-member rebinding and final-ledger/terminal-target regression evidence remains failed."
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprints() -> dict[str, str]:
    paths = (
        ROOT / "flowpilot_route_mutation_activation_model.py",
        Path(__file__).resolve(),
        RUNTIME_PATH,
        ROUTE_MUTATION_PATH,
        PARENT_SEGMENT_PATH,
        *RELEVANT_TEST_PATHS,
    )
    return {str(path.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(path) for path in paths}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    production_conformance = _production_conformance_report()
    model_ok = bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"])
    runtime_conformance_ok = bool(production_conformance["ok"])
    return {
        "result_type": "flowpilot_route_mutation_activation_checks",
        "ok": model_ok and runtime_conformance_ok,
        "model_ok": model_ok,
        "runtime_conformance_ok": runtime_conformance_ok,
        "decision": (
            "passed"
            if model_ok and runtime_conformance_ok
            else ("current_runtime_gap" if model_ok else "model_failed")
        ),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "production_conformance": production_conformance,
        "source_fingerprints": _source_fingerprints(),
        "claim_boundary": (
            "The refined model proves effective-member conservation, sibling rebinding, version agreement, "
            "and ledger/terminal target equality. Overall pass additionally requires current runtime/test "
            "conformance; no skipped production replay is counted as pass."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if not args.no_write_results:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
