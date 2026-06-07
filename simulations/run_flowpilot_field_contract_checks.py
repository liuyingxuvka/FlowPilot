"""Run checks for the FlowPilot field-contract model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_field_contract_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_field_contract_results.json"
REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LABELS = (
    "select_success",
    "catalog_current_field_contracts",
    "catalog_field_status_lifecycle",
    "catalog_retired_and_forbidden_legacy_fields",
    "validate_startup_answer_fields",
    "filter_packet_startup_scope_fields",
    "bind_top_level_runtime_fields",
    "write_startup_mechanical_field_audit",
    "bind_packet_role_result_current_fields",
    "bind_runtime_leaf_mechanical_fields",
    "bind_pm_decision_fields",
    "bind_reviewer_quality_fields",
    "bind_flowguard_process_fields",
    "bind_current_background_agent_fields_after_route_allocation",
    "catalog_packet_result_family_contracts",
    "accept_field_contract",
    "block_unsupported_historical_field_accepted",
    "block_unsupported_historical_field_translated",
    "block_missing_background_ack_field",
    "block_provenance_promoted_to_controller_scope",
    "block_startup_fixed_role_binding_gate",
    "block_fixed_role_count_gate",
    "block_legacy_boot_action_accepted",
    "block_packet_result_contract_misaligned",
)

EXPECTED_HAZARD_FAILURES = {
    "unsupported_startup_field_accepted_accepted": "risk scenario was accepted: unsupported_startup_field_accepted",
    "unsupported_field_translated_accepted": "risk scenario was accepted: unsupported_field_translated",
    "missing_background_ack_advances_accepted": "risk scenario was accepted: missing_background_ack_advances",
    "provenance_promoted_to_scope_accepted": "risk scenario was accepted: provenance_promoted_to_scope",
    "startup_fixed_role_binding_gate_required_accepted": "risk scenario was accepted: startup_fixed_role_binding_gate_required",
    "fixed_role_count_gate_required_accepted": "risk scenario was accepted: fixed_role_count_gate_required",
    "legacy_boot_action_accepted_accepted": "risk scenario was accepted: legacy_boot_action_accepted",
    "packet_result_contract_misaligned_accepted": "risk scenario was accepted: packet_result_contract_misaligned",
    "success_overblocked": "current field contract was blocked",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"catalog={state.current_field_contracts_cataloged}/{model.REQUIRED_CURRENT_FIELD_CONTRACT_COUNT}|"
        f"statuses={state.field_statuses_cataloged}/{len(model.FIELD_STATUSES)}|"
        f"legacy_disposition={state.legacy_dispositions_cataloged}|"
        f"answers={state.startup_answers_validated}|"
        f"scope={state.packet_scope_filtered_to_current_options}|"
        f"top={state.top_level_runtime_fields_bound}|"
        f"audit={state.startup_mechanical_field_audit_written}|"
        f"packet_role={state.packet_role_runtime_fields_bound}|"
        f"leaf={state.runtime_leaf_mechanical_fields_bound}|"
        f"pm={state.pm_decision_fields_bound}|"
        f"reviewer_quality={state.reviewer_quality_fields_bound}|"
        f"flowguard={state.flowguard_process_fields_bound}|"
        f"background={state.current_background_agent_fields_bound}|"
        f"packet_results={state.packet_result_contracts_cataloged}/{model.REQUIRED_PACKET_RESULT_CONTRACT_COUNT}|"
        f"legacy={state.unsupported_historical_field_accepted},{state.unsupported_historical_field_translated}|"
        f"ack_missing={state.background_ack_missing}|"
        f"provenance_scope={state.provenance_leaked_to_controller_scope}|"
        f"fixed_startup={state.startup_fixed_role_binding_gate_required}|"
        f"fixed_count={state.fixed_role_count_gate_required}|"
        f"legacy_action={state.legacy_boot_action_accepted}|"
        f"packet_misaligned={state.packet_result_contract_misaligned}"
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
        failures = model.hard_check_failures(state)
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
        "invariant_failures": invariant_failures,
        "edge_count": sum(len(outgoing) for outgoing in edges),
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.hard_check_failures(state)
        expected = EXPECTED_HAZARD_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


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


def _source_alignment_report() -> dict[str, object]:
    runtime_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    core_test_path = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    high_standard_test_path = REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py"
    fake_e2e_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "fake_e2e.py"
    fake_cli_path = REPO_ROOT / "simulations" / "flowpilot_fake_project_rehearsal_cli.py"

    runtime_text = runtime_path.read_text(encoding="utf-8")
    test_text = (
        core_test_path.read_text(encoding="utf-8")
        + "\n"
        + high_standard_test_path.read_text(encoding="utf-8")
    )
    fake_text = fake_e2e_path.read_text(encoding="utf-8") + "\n" + fake_cli_path.read_text(encoding="utf-8")

    validators = sorted(
        {
            str(row["validator"])
            for row in model.PACKET_RESULT_CONTRACTS
            if str(row.get("validator") or "").startswith("_")
        }
    )
    missing_validators = [validator for validator in validators if f"def {validator}" not in runtime_text]
    forbidden_alias_hits = {
        "pm_repair_decision.authority_alias": 'payload.get("authority")' in runtime_text,
        "pm_disposition.summary_reason_alias": 'payload.get("reason") or payload.get("summary")' in runtime_text,
    }
    missing_negative_tests = [
        name
        for name in (
            "test_pm_repair_decision_rejects_authority_alias",
            "test_pm_disposition_summary_is_not_reason_fallback",
        )
        if name not in test_text
    ]
    missing_fake_contract_terms = [
        term
        for term in (
            '"requirements"',
            '"material_sources"',
            '"obligations"',
            '"node_context_package"',
            '"pm_visible_summary"',
        )
        if term not in fake_text
    ]
    return {
        "ok": not missing_validators and not any(forbidden_alias_hits.values()) and not missing_negative_tests and not missing_fake_contract_terms,
        "runtime_path": runtime_path.as_posix(),
        "test_paths": [core_test_path.as_posix(), high_standard_test_path.as_posix()],
        "fake_paths": [fake_e2e_path.as_posix(), fake_cli_path.as_posix()],
        "packet_result_contract_count": model.REQUIRED_PACKET_RESULT_CONTRACT_COUNT,
        "missing_validators": missing_validators,
        "forbidden_alias_hits": forbidden_alias_hits,
        "missing_negative_tests": missing_negative_tests,
        "missing_fake_contract_terms": missing_fake_contract_terms,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    progress = _progress_report(graph)
    hazards = _check_hazards()
    flowguard = _flowguard_report()
    source_alignment = _source_alignment_report()
    result = {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and bool(progress["ok"])
            and bool(hazards["ok"])
            and bool(flowguard["ok"])
            and bool(source_alignment["ok"])
        ),
        "model_id": model.MODEL_ID,
        "current_field_contracts": model.CURRENT_FIELD_CONTRACTS,
        "packet_result_contracts": model.PACKET_RESULT_CONTRACTS,
        "field_layers": model.FIELD_LAYERS,
        "field_statuses": model.FIELD_STATUSES,
        "retired_field_contracts": model.RETIRED_FIELD_CONTRACTS,
        "forbidden_legacy_field_contracts": model.FORBIDDEN_LEGACY_FIELD_CONTRACTS,
        "unsupported_historical_field_samples": sorted(model.UNSUPPORTED_HISTORICAL_FIELD_SAMPLES),
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "progress": progress,
        "hazard_checks": hazards,
        "flowguard": flowguard,
        "source_alignment": source_alignment,
        "scenario_matrix": model.scenario_matrix(),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
