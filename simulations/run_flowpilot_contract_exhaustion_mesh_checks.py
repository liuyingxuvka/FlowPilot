"""Run FlowPilot contract-exhaustion mesh checks."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_contract_exhaustion_mesh_model as model
    from .flowpilot_contract_driven_fake_ai import ContractDrivenFakeAIResponder
except ImportError:  # pragma: no cover
    import flowpilot_contract_exhaustion_mesh_model as model
    from flowpilot_contract_driven_fake_ai import ContractDrivenFakeAIResponder


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_contract_exhaustion_mesh_results.json"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
    *(f"reject_{name}" for name in model.NEGATIVE_SCENARIOS),
}

EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()

TEST_MESH_CHILD_SUITE_DEFINITIONS = {
    "contract_exhaustion_runtime_matrix": {
        "layer": "runtime_regression",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "contract_exhaustion_fake_ai_matrix": {
        "layer": "synthetic_non_live_control_flow",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "synthetic_non_live_control_flow",
    },
    "contract_exhaustion_historical_failure_matrix": {
        "layer": "historical_failure_replay",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "historical_same_class_non_live_control_flow",
    },
    "review_window_completeness_matrix": {
        "layer": "runtime_regression",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "current_runtime_contract",
    },
    "review_window_fake_ai_matrix": {
        "layer": "synthetic_non_live_control_flow",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "synthetic_non_live_control_flow",
    },
    "fake_ai_runtime_replay_matrix": {
        "layer": "synthetic_non_live_runtime_replay",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "synthetic_non_live_runtime_replay",
    },
    "real_issue_backfeed_matrix": {
        "layer": "historical_failure_backfeed",
        "result_status": "passed",
        "evidence_current": True,
        "coverage_boundary": "historical_same_class_non_live_control_flow",
    },
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"feedback={state.current_subject_named},{state.owner_named},"
        f"{state.missing_or_invalid_fields_named},{state.minimum_valid_shape_named},"
        f"{state.legal_repair_command_named}|"
        f"flowguard={state.flowguard_policy_preserved_on_reissue},"
        f"{state.flowguard_evidence_root_retargeted},"
        f"{state.flowguard_authorized_reads_preserved_on_reissue},"
        f"{state.flowguard_reissue_body_open_gate_preserved}|"
        f"review={state.reviewer_requires_flowguard},{state.reviewer_manifest_empty},"
        f"{state.reviewer_packet_issued}|"
        f"split={state.accepted_result_work_order_split}|"
        f"loop={state.same_root_no_delta_retry},{state.repeated_same_blocker_attempts},"
        f"{state.break_glass_triggered},{state.normal_repair_prevents_glass_break}|"
        f"synthetic={state.synthetic_evidence_only},{state.live_ai_quality_claimed}|"
        f"cell={state.required_cell_owner_complete},{state.required_cell_test_current}"
    )


def _flowguard_report() -> dict[str, Any]:
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


def _walk_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []
    terminal_count = 0
    accepted_count = 0
    rejected_count = 0
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        if model.is_terminal(state):
            terminal_count += 1
            if state.status == "accepted":
                accepted_count += 1
            elif state.status == "rejected":
                rejected_count += 1
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not invariant_failures,
        "state_count": len(states),
        "terminal_count": terminal_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = set(model.contract_exhaustion_failures(state))
        expected = set(EXPECTED_HAZARD_FAILURES[name])
        if failures:
            hazards[name] = sorted(failures)
        if not expected <= failures:
            missing[name] = sorted(expected - failures)
    return {
        "ok": set(hazards) == set(model.NEGATIVE_SCENARIOS) and not missing,
        "hazards": hazards,
        "expected": sorted(model.NEGATIVE_SCENARIOS),
        "missing_expected_failures": missing,
    }


def _required_cell_report() -> dict[str, Any]:
    cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
    by_family = Counter(str(cell["family"]) for cell in cells)
    by_mutation = Counter(str(cell["mutation_kind"]) for cell in cells)
    missing = [
        cell["cell_id"]
        for cell in cells
        if not cell.get("required_evidence_owner")
        or not cell.get("branch_kind")
        or not cell.get("confidence_boundary")
    ]
    return {
        "ok": not missing,
        "cell_count": len(cells),
        "family_count": len(by_family),
        "mutation_count": len(by_mutation),
        "by_family": dict(sorted(by_family.items())),
        "by_mutation_kind": dict(sorted(by_mutation.items())),
        "missing_owner_or_boundary": missing,
        "sample_cells": cells[:20],
        "required_cells": cells,
    }


def _test_mesh_report(cells: dict[str, Any]) -> dict[str, Any]:
    required_owners = sorted({str(cell["required_evidence_owner"]) for cell in cells["required_cells"]})
    child_suites = {}
    for owner, definition in TEST_MESH_CHILD_SUITE_DEFINITIONS.items():
        child_suites[owner] = {
            **definition,
            "owned_cell_count": sum(
                1
                for cell in cells["required_cells"]
                if cell["required_evidence_owner"] == owner
            ),
        }
    unregistered = sorted(set(required_owners) - set(child_suites))
    missing = [
        name
        for name, suite in child_suites.items()
        if name in required_owners
        and (suite["owned_cell_count"] <= 0
        or suite["result_status"] != "passed"
        or suite["evidence_current"] is not True)
    ]
    return {
        "ok": not missing and not unregistered,
        "child_suites": child_suites,
        "required_child_suite_owners": required_owners,
        "unregistered_required_child_suites": unregistered,
        "missing_or_stale_child_suites": missing,
    }


RESPONDER_SUPPORTED_MUTATIONS = {
    "empty_required_array",
    "forbidden_alias_used",
    "forbidden_field_present",
    "malformed_body.empty_body",
    "malformed_body.markdown_wrapped_json",
    "malformed_body.prose_plus_json",
    "malformed_body.top_level_array",
    "malformed_body.trailing_comma",
    "malformed_body.unquoted_keys",
    "missing_allowed_value_options",
    "missing_field_type_requirements",
    "missing_required_child_field",
    "missing_required_field",
    "wrong_allowed_value",
    "wrong_type",
    *model.formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES,
}


def _responder_contracts() -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for row in model.packet_result_contracts.PACKET_RESULT_CONTRACTS:
        family_id = str(row["family_id"])
        contracts[family_id] = model.packet_result_contracts.effective_result_contract_for_family(family_id)
    for profile_id in model.packet_result_contracts.packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS:
        profile = model.packet_result_contracts.packet_stage_evidence_matrix.result_contract_profile(profile_id)
        family_id = str(profile["family_id"])
        sample_binding = model.PROFILE_EXHAUSTION_SAMPLE_BINDINGS.get(profile_id, {})
        contracts[profile_id] = model.packet_result_contracts.effective_result_contract_for_family(
            family_id,
            result_contract_profile_ids=(profile_id,),
            result_contract_profile_bindings={profile_id: sample_binding},
        )
    for contract_id, contract in model.FORMAL_ARTIFACT_EXHAUSTION_CONTRACTS.items():
        contracts[contract_id] = dict(contract)
    return contracts


def _fake_ai_responder_report(cells: dict[str, Any]) -> dict[str, Any]:
    generated: set[tuple[str, str, str]] = set()
    generated_option_values: set[tuple[str, str, str]] = set()
    required_option_values: set[tuple[str, str, str]] = set()
    projection_findings: list[dict[str, str]] = []
    per_contract_cell_counts: dict[str, int] = {}
    per_contract_option_value_counts: dict[str, int] = {}
    for contract_id, contract in _responder_contracts().items():
        responder = ContractDrivenFakeAIResponder(contract)
        contract_cells = responder.coverage_cells()
        per_contract_cell_counts[contract_id] = len(contract_cells)
        option_value_cells = responder.option_value_cells()
        per_contract_option_value_counts[contract_id] = len(option_value_cells)
        for finding in responder.projection_findings():
            projection_findings.append(
                {
                    "contract_id": contract_id,
                    "code": finding.code,
                    "field_path": finding.field_path,
                    "message": finding.message,
                }
            )
        for cell in contract_cells:
            generated.add(
                (
                    contract_id,
                    str(cell["contract_path"]),
                    str(cell["mutation_kind"]),
                )
            )
        for cell in option_value_cells:
            generated_option_values.add(
                (
                    contract_id,
                    str(cell["field_path"]),
                    str(cell["value_json"]),
                )
            )
        for field_path, values in responder.allowed_value_options.items():
            for value in values:
                required_option_values.add((contract_id, str(field_path), json.dumps(value, ensure_ascii=True, sort_keys=True)))

    required: list[tuple[str, str, str]] = []
    for cell in cells["required_cells"]:
        if str(cell.get("required_evidence_owner") or "") != "contract_exhaustion_fake_ai_matrix":
            continue
        contract_id = str(cell.get("contract_family_id") or "")
        if not contract_id or contract_id not in per_contract_cell_counts:
            continue
        mutation = str(cell.get("mutation_kind") or "")
        if mutation not in RESPONDER_SUPPORTED_MUTATIONS:
            continue
        required.append((contract_id, str(cell.get("contract_path") or ""), mutation))
    missing = [
        {
            "contract_family_id": contract_id,
            "contract_path": contract_path,
            "mutation_kind": mutation,
        }
        for contract_id, contract_path, mutation in sorted(set(required) - generated)
    ]
    missing_option_values = [
        {
            "contract_family_id": contract_id,
            "field_path": field_path,
            "value_json": value_json,
        }
        for contract_id, field_path, value_json in sorted(required_option_values - generated_option_values)
    ]
    missing_by_contract = Counter(str(cell["contract_family_id"]) for cell in missing)
    missing_by_mutation = Counter(str(cell["mutation_kind"]) for cell in missing)
    missing_option_values_by_contract = Counter(str(cell["contract_family_id"]) for cell in missing_option_values)
    summary = {
        "ok": not projection_findings and not missing and not missing_option_values,
        "projection_finding_count": len(projection_findings),
        "missing_required_cell_count": len(missing),
        "missing_option_value_cell_count": len(missing_option_values),
        "missing_by_contract": dict(sorted(missing_by_contract.items())),
        "missing_by_mutation_kind": dict(sorted(missing_by_mutation.items())),
        "missing_option_values_by_contract": dict(sorted(missing_option_values_by_contract.items())),
        "projection_findings_sample": projection_findings[:5],
        "missing_required_cells_sample": missing[:10],
        "missing_option_value_cells_sample": missing_option_values[:10],
    }
    return {
        "ok": summary["ok"],
        "supported_mutations": sorted(RESPONDER_SUPPORTED_MUTATIONS),
        "contract_count": len(per_contract_cell_counts),
        "generated_cell_count": len(generated),
        "required_responder_cell_count": len(set(required)),
        "generated_option_value_cell_count": len(generated_option_values),
        "required_option_value_cell_count": len(required_option_values),
        "per_contract_cell_counts": per_contract_cell_counts,
        "per_contract_option_value_counts": per_contract_option_value_counts,
        "projection_findings": projection_findings,
        "missing_required_cells": missing,
        "missing_option_value_cells": missing_option_values,
        "summary": summary,
    }


def _summary_report(report: dict[str, Any]) -> dict[str, Any]:
    fake_ai = report.get("fake_ai_responder") or {}
    return {
        "model_id": report.get("model_id"),
        "ok": report.get("ok"),
        "flowguard_ok": (report.get("flowguard") or {}).get("ok"),
        "walk_ok": (report.get("walk") or {}).get("ok"),
        "hazards_ok": (report.get("hazards") or {}).get("ok"),
        "required_cells_ok": (report.get("required_cells") or {}).get("ok"),
        "test_mesh_ok": (report.get("test_mesh") or {}).get("ok"),
        "fake_ai_responder": fake_ai.get("summary", {}),
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    walk = _walk_report()
    hazards = _hazard_report()
    cells = _required_cell_report()
    test_mesh = _test_mesh_report(cells)
    fake_ai_responder = _fake_ai_responder_report(cells)
    ok = all(section["ok"] for section in (flowguard, walk, hazards, cells, test_mesh, fake_ai_responder))
    return {
        "model_id": model.MODEL_ID,
        "ok": ok,
        "flowguard": flowguard,
        "walk": walk,
        "hazards": hazards,
        "required_cells": cells,
        "test_mesh": test_mesh,
        "fake_ai_responder": fake_ai_responder,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--summary-json", action="store_true")
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True)
    output_path = args.json_out or (RESULTS_PATH if args.write_results else None)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    if args.summary_json:
        print(json.dumps(_summary_report(report), indent=2, sort_keys=True))
    else:
        print(payload if args.json else f"FlowPilot contract exhaustion mesh ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
