"""Run checks for the FlowPilot terminal supplemental repair model."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_terminal_supplemental_repair_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_terminal_supplemental_repair_results.json"
RUNTIME_PATH = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
RELEVANT_TEST_PATHS = (
    REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py",
    REPO_ROOT / "tests" / "test_flowpilot_fake_project_rehearsal.py",
    REPO_ROOT / "tests" / "test_flowpilot_new_entrypoint.py",
    REPO_ROOT / "simulations" / "run_flowpilot_unified_repair_native_runtime_conformance.py",
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.MISSING_SUPPLEMENTAL_CONTRACT: "terminal gap repair requires PM supplemental contract",
    model.ORIGINAL_CONTRACT_MUTATED: "terminal supplemental repair must not mutate frozen original contract",
    model.MISSING_REPAIR_ITEM_OWNER: "supplemental repair items require owner repair nodes",
    model.MISSING_ROUTE_NODE_PROJECTION: "repair route nodes must project supplemental contract and item ids",
    model.REPAIR_BYPASSES_EXISTING_GATES: "supplemental repair nodes must reuse existing FlowPilot gates",
    model.FINAL_LEDGER_OMITS_SUPPLEMENTAL: "final ledgers must include supplemental repair closure rows",
    model.TERMINAL_REPLAY_OMITS_SUPPLEMENTAL: "terminal backward replay must include supplemental repair segments",
    model.FOURTH_ROUND_PM_PACKET_OPENED: "runtime must stop instead of opening a fourth supplemental repair round",
    model.HYGIENE_GAP_NOT_CONTRACTUALIZED: "required final artifact hygiene gap requires PM supplemental repair contract",
    model.HYGIENE_CATEGORY_MISSING: "final artifact hygiene repair items require hygiene_category",
    model.FINAL_LEDGER_OMITS_HYGIENE: "final ledgers must include final artifact hygiene closure rows",
    model.TERMINAL_REPLAY_OMITS_HYGIENE_SEGMENT: "terminal backward replay must include final artifact hygiene segment",
    model.OPTIONAL_HYGIENE_NOTE_BLOCKS: "optional hygiene notes must not block closure unless PM imports them",
    model.REVIEWER_ONLY_SUBSTANTIVE_REPAIR: "terminal substantive repair requires a Worker task packet, not a Reviewer repair packet",
    model.MISSING_WORKER_REPAIR_PACKET: "terminal substantive repair requires a Worker task packet, not a Reviewer repair packet",
    model.MISSING_WORKER_REPAIR_RESULT: "terminal substantive repair requires a fresh Worker-owned result after the repair packet",
    model.WORKER_SELF_REVIEWS_REPAIR: "terminal repair result requires a distinct Reviewer after Worker execution",
    model.PRE_CONTRACT_REPAIR_EVIDENCE: "repair evidence must be created after supplemental contract generation",
    model.MISMATCHED_REPAIR_EVIDENCE: "repair evidence must match the supplemental contract, item, and owner repair node",
    model.WRONG_TERMINAL_GATE: "terminal repair must return through the same terminal backward-replay gate",
    model.MISSING_SHARED_ENGINE_RECEIPT: "terminal repair requires a current shared-engine receipt after Worker evidence",
    model.MISMATCHED_SHARED_ENGINE_HANDOFF: "Reviewer handoff must consume the matching current shared-engine receipt",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|round={state.current_round}|"
        f"lifecycle={state.terminal_lifecycle_status}"
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


def _source_slice(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    end_index = text.find(end, start_index + len(start))
    return text[start_index:] if end_index < 0 else text[start_index:end_index]


def _production_conformance_report() -> dict[str, object]:
    runtime_text = RUNTIME_PATH.read_text(encoding="utf-8")
    test_texts = {path.name: path.read_text(encoding="utf-8") for path in RELEVANT_TEST_PATHS}
    replacement_repair = _source_slice(
        runtime_text,
        "def _replace_scope_and_open_repair_packet(",
        "def _materialize_route_redesign(",
    )
    route_replacement = _source_slice(
        runtime_text,
        "def _replace_route_node_for_repair(",
        "def _role_continuity_table(",
    )
    causal_identity = _source_slice(
        runtime_text,
        "def _repair_chain_identity_blockers(",
        "def _record_repair_transaction(",
    )
    core_tests = test_texts["test_flowpilot_core_runtime.py"]
    native_owner = test_texts[
        "run_flowpilot_unified_repair_native_runtime_conformance.py"
    ]
    obligations = {
        "terminal_repair_dispatches_explicit_worker_task": (
            "_replace_route_node_for_repair(" in replacement_repair
            and "ensure_next_node_task_packet(ledger)" in route_replacement
            and 'worker_packet["envelope"]["responsibility"] == "worker"' in native_owner
        ),
        "terminal_repair_worker_then_distinct_reviewer_test": (
            "test_terminal_replay_repair_current_scope_preserves_targets_and_closes"
            in core_tests
            and "_scenario_terminal_worker_chain" in native_owner
            and "terminal Reviewer recheck was not accepted" in native_owner
        ),
        "supplemental_contract_precedes_bound_repair_evidence": (
            "supplemental_contract_not_active" in causal_identity
            and "repair_packet_not_after_contract_and_effect_commit" in causal_identity
            and "supplemental_contract_repair_generation_mismatch" in causal_identity
            and "supplemental_contract_source_generation_mismatch" in causal_identity
        ),
        "precontract_and_mismatched_evidence_negative_test": (
            "test_terminal_repair_evidence_rejects_wrong_or_early_contract_generation_identity"
            in core_tests
        ),
        "ordinary_shared_engine_receipt_handoff_surface_exists": (
            "proof_result_id" in runtime_text
            and "flowguard_evidence_manifest" in runtime_text
            and "matching_flowguard_result_for_review" in runtime_text
        ),
        "terminal_repair_reuses_terminal_gate_and_shared_handoff_test": (
            "test_terminal_replay_repair_current_scope_preserves_targets_and_closes"
            in core_tests
            and "unified_repair.terminal_shared_engine" in native_owner
            and "terminal backward replay did not accept current repair evidence"
            in native_owner
        ),
        "existing_terminal_supplemental_baseline_tests_present": all(
            name in core_tests
            for name in (
                "test_terminal_pm_repair_for_terminal_gap_requires_supplemental_contract",
                "test_terminal_replay_repair_current_scope_preserves_targets_and_closes",
                "test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet",
            )
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
            for path in (RUNTIME_PATH, *RELEVANT_TEST_PATHS)
        ],
        "claim_boundary": (
            "This is current source/test conformance, not a skipped check. Missing Worker dispatch, "
            "generation binding, or terminal shared-engine/gate regression evidence keeps the runner red."
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
        ROOT / "flowpilot_terminal_supplemental_repair_model.py",
        Path(__file__).resolve(),
        RUNTIME_PATH,
        *RELEVANT_TEST_PATHS,
    )
    return {str(path.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(path) for path in paths}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    flowguard = _flowguard_report()
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    hazard_failures = {
        scenario: model.repair_failures(model._scenario_state(scenario))
        for scenario in model.NEGATIVE_SCENARIOS
    }
    missing_expected_hazards = [
        scenario
        for scenario, expected in HAZARD_EXPECTED_FAILURES.items()
        if expected not in hazard_failures.get(scenario, [])
    ]
    model_ok = (
        not graph["invariant_failures"]
        and not missing_labels
        and not missing_expected_hazards
        and accepted_scenarios == sorted(model.VALID_SCENARIOS)
        and rejected_scenarios == sorted(model.NEGATIVE_SCENARIOS)
        and bool(flowguard["ok"])
    )
    production_conformance = _production_conformance_report()
    runtime_conformance_ok = bool(production_conformance["ok"])
    report: dict[str, object] = {
        "result_type": "flowpilot_terminal_supplemental_repair_checks",
        "ok": model_ok and runtime_conformance_ok,
        "model_ok": model_ok,
        "runtime_conformance_ok": runtime_conformance_ok,
        "decision": (
            "passed"
            if model_ok and runtime_conformance_ok
            else ("current_runtime_gap" if model_ok else "model_failed")
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "missing_expected_hazards": missing_expected_hazards,
        "hazard_failures": hazard_failures,
        "invariant_failures": graph["invariant_failures"],
        "flowguard_explorer": flowguard,
        "production_conformance": production_conformance,
        "source_fingerprints": _source_fingerprints(),
        "claim_boundary": (
            "The refined model closes the Worker/Reviewer, causality, terminal-gate, and shared-engine "
            "behavior class. Overall pass additionally requires current production/test conformance; no "
            "skipped production check is counted as pass."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if not args.no_write_results:
        args.json_out.write_text(payload, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
