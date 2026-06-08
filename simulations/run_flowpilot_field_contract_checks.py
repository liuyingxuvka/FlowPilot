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
    "catalog_field_lifecycle_chains",
    "catalog_retired_and_forbidden_legacy_fields",
    "validate_startup_answer_fields",
    "filter_packet_startup_scope_fields",
    "bind_top_level_runtime_fields",
    "write_startup_mechanical_field_audit",
    "bind_packet_role_result_current_fields",
    "bind_runtime_leaf_mechanical_fields",
    "bind_formal_repair_identity_chain",
    "bind_runtime_repair_identity_mechanical_gate",
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
    "block_repair_identity_prose_only",
    "block_repair_identity_chain_misaligned",
    "block_repair_identity_reviewer_owned",
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
    "repair_identity_prose_only_accepted": "risk scenario was accepted: repair_identity_prose_only",
    "repair_identity_chain_misaligned_accepted": "risk scenario was accepted: repair_identity_chain_misaligned",
    "repair_identity_reviewer_owned_accepted": "risk scenario was accepted: repair_identity_reviewer_owned",
    "success_overblocked": "current field contract was blocked",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"catalog={state.current_field_contracts_cataloged}/{model.REQUIRED_CURRENT_FIELD_CONTRACT_COUNT}|"
        f"statuses={state.field_statuses_cataloged}/{len(model.FIELD_STATUSES)}|"
        f"chains={state.field_lifecycle_chains_cataloged}/{model.REQUIRED_FIELD_LIFECYCLE_CHAIN_COUNT}|"
        f"legacy_disposition={state.legacy_dispositions_cataloged}|"
        f"answers={state.startup_answers_validated}|"
        f"scope={state.packet_scope_filtered_to_current_options}|"
        f"top={state.top_level_runtime_fields_bound}|"
        f"audit={state.startup_mechanical_field_audit_written}|"
        f"packet_role={state.packet_role_runtime_fields_bound}|"
        f"leaf={state.runtime_leaf_mechanical_fields_bound}|"
        f"repair_chain={state.formal_repair_identity_chain_bound}|"
        f"repair_gate={state.formal_repair_identity_mechanical_gate_bound}|"
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
        f"packet_misaligned={state.packet_result_contract_misaligned}|"
        f"repair_prose={state.repair_identity_prose_only}|"
        f"repair_misaligned={state.repair_identity_chain_misaligned}|"
        f"repair_reviewer_owned={state.repair_identity_reviewer_owned}"
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
    contract_module_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_core_runtime"
        / "packet_result_contracts.py"
    )
    core_test_path = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    high_standard_test_path = REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py"
    fake_project_test_path = REPO_ROOT / "tests" / "test_flowpilot_fake_project_rehearsal.py"
    new_entrypoint_test_path = REPO_ROOT / "tests" / "test_flowpilot_new_entrypoint.py"
    fake_e2e_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "fake_e2e.py"
    fake_cli_path = REPO_ROOT / "simulations" / "flowpilot_fake_project_rehearsal_cli.py"
    contract_index_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "runtime_kit"
        / "contracts"
        / "contract_index.json"
    )

    runtime_text = runtime_path.read_text(encoding="utf-8")
    contract_module_text = contract_module_path.read_text(encoding="utf-8")
    contract_index_text = contract_index_path.read_text(encoding="utf-8")
    test_text = (
        core_test_path.read_text(encoding="utf-8")
        + "\n"
        + high_standard_test_path.read_text(encoding="utf-8")
        + "\n"
        + fake_project_test_path.read_text(encoding="utf-8")
        + "\n"
        + new_entrypoint_test_path.read_text(encoding="utf-8")
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
    private_runtime_contract_tables = [
        token
        for token in (
            "_PACKET_RESULT_REQUIRED_FIELDS",
            "_PACKET_RESULT_FORBIDDEN_FIELDS",
        )
        if token in runtime_text
    ]
    shared_contract_source_ok = (
        "import packet_result_contracts" in runtime_text
        and "PACKET_RESULT_CONTRACTS" in contract_module_text
        and "PACKET_RESULT_CONTRACTS = packet_result_contracts.PACKET_RESULT_CONTRACTS" in (
            REPO_ROOT / "simulations" / "flowpilot_field_contract_model.py"
        ).read_text(encoding="utf-8")
    )
    missing_negative_tests = [
        name
        for name in (
            "test_pm_repair_decision_rejects_authority_alias",
            "test_pm_disposition_summary_is_not_reason_fallback",
            "test_fake_e2e_success_bodies_use_declared_contract_fields",
            "test_fake_project_success_bodies_use_declared_contract_fields",
            "test_packet_handoff_contract_is_visible_in_envelope_body_and_role_handoff",
            "test_review_packet_authorizes_matching_flowguard_result_read",
            "test_pm_repair_handoff_contract_includes_branch_shapes",
            "test_pm_repair_redesign_route_reissue_names_branch_field_path",
            "test_repair_packet_handoff_contract_carries_formal_blocker_identity",
            "test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker",
            "test_staged_effect_same_family_rejects_different_formal_blocker_identity",
            "test_flowguard_packet_rejects_generic_decision_summary_result",
            "test_review_packet_rejects_generic_decision_summary_result",
        )
        if name not in test_text
    ]
    current_handoff_source_ok = (
        "_build_current_handoff_contract" in runtime_text
        and '"current_handoff_contract"' in runtime_text
        and "branch_valid_shapes_for_family" in runtime_text
        and "branch_minimal_valid_shape" in runtime_text
        and "matching_flowguard_result_for_review" in runtime_text
        and "current_handoff_contract" in test_text
    )
    missing_repair_identity_markers = [
        label
        for label, token, source in (
            ("issue_task_packet_accepts_repair_blocker_id", "repair_blocker_id: str = \"\"", runtime_text),
            ("envelope_carries_repair_blocker_id", '"repair_blocker_id": repair_blocker_id', runtime_text),
            (
                "handoff_manifest_projects_repair_blocker_id",
                '"blocker_id": str(envelope.get("repair_blocker_id") or "")',
                runtime_text,
            ),
            ("runtime_formal_repair_identity_gate", "def _formal_repair_identity_blockers", runtime_text),
            (
                "result_gate_calls_formal_repair_identity_gate",
                "blockers.extend(_formal_repair_identity_blockers(packet))",
                runtime_text,
            ),
            ("flowguard_generator_inputs_bind_blocker_id", 'body_payload["generator_inputs"] = {', runtime_text),
            ("flowguard_subject_context_binds_blocker_id", 'body_payload["subject_context"] = {', runtime_text),
            (
                "flowguard_result_records_blocker_id",
                'result["blocker_id"] = repair_blocker_id',
                runtime_text,
            ),
            (
                "review_manifest_carries_blocker_id",
                '"blocker_id": str(order.get("blocker_id") or "")',
                runtime_text,
            ),
            (
                "runtime_negative_test_for_formal_identity_mismatch",
                "test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker",
                test_text,
            ),
            (
                "runtime_replay_test_for_formal_identity_chain",
                "test_repair_packet_handoff_contract_carries_formal_blocker_identity",
                test_text,
            ),
            (
                "staged_effect_negative_test_for_identity_mismatch",
                "test_staged_effect_same_family_rejects_different_formal_blocker_identity",
                test_text,
            ),
        )
        if token not in source
    ]
    formal_repair_identity_source_ok = not missing_repair_identity_markers
    role_report_contract_alignment_ok = all(
        token in source
        for token, source in (
            ("REVIEW_REPORT_REQUIRED_FIELDS", contract_module_text),
            ("FLOWGUARD_REPORT_REQUIRED_FIELDS", contract_module_text),
            ("explicit_array_fields_for_family", contract_module_text),
            ('"decision", "outcome", "status"', contract_module_text),
            ("_payload_path_missing", runtime_text),
            ("_missing_or_wrong_explicit_array_fields", runtime_text),
            ('packet_kind in {"flowguard_check", "review"}', runtime_text),
            ('"pm_visible_summary"', contract_index_text),
            ('"independent_challenge"', contract_index_text),
            ('"missing_test_kinds"', contract_index_text),
            ("flowguard_result_body", test_text),
            ("review_result_body", test_text),
        )
    )
    missing_fake_contract_terms = [
        term
        for term in (
            '"requirements"',
            '"material_sources"',
            '"obligations"',
            '"node_context_package"',
            '"pm_visible_summary"',
            '"modeled_boundary"',
            '"independent_challenge"',
            '"missing_test_kinds"',
        )
        if term not in fake_text
    ]
    return {
        "ok": (
            not missing_validators
            and not any(forbidden_alias_hits.values())
            and not private_runtime_contract_tables
            and shared_contract_source_ok
            and current_handoff_source_ok
            and formal_repair_identity_source_ok
            and role_report_contract_alignment_ok
            and not missing_negative_tests
            and not missing_fake_contract_terms
        ),
        "runtime_path": runtime_path.as_posix(),
        "contract_module_path": contract_module_path.as_posix(),
        "test_paths": [core_test_path.as_posix(), high_standard_test_path.as_posix()],
        "fake_paths": [fake_e2e_path.as_posix(), fake_cli_path.as_posix()],
        "packet_result_contract_count": model.REQUIRED_PACKET_RESULT_CONTRACT_COUNT,
        "missing_validators": missing_validators,
        "forbidden_alias_hits": forbidden_alias_hits,
        "private_runtime_contract_tables": private_runtime_contract_tables,
        "shared_contract_source_ok": shared_contract_source_ok,
        "current_handoff_source_ok": current_handoff_source_ok,
        "formal_repair_identity_source_ok": formal_repair_identity_source_ok,
        "role_report_contract_alignment_ok": role_report_contract_alignment_ok,
        "missing_repair_identity_markers": missing_repair_identity_markers,
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
        "field_lifecycle_chains": model.FIELD_LIFECYCLE_CHAINS,
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
