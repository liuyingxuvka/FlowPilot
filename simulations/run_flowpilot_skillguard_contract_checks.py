"""Run the focused FlowPilot current-SkillGuard-contract FlowGuard checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # pragma: no cover - direct-script fallback below.
    from . import flowpilot_skillguard_contract_model as model
except ImportError:  # pragma: no cover
    import flowpilot_skillguard_contract_model as model


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_skillguard_current_contract_results.json"
)
CONTRACT_SOURCE_PATH = (
    ROOT / "skills" / "flowpilot" / ".skillguard" / "contract-source.json"
)

EXPECTED_BLOCKERS = {
    "missing_opt_in": "explicit_opt_in_missing",
    "ordinary_small_task": "complex_long_project_boundary_missing",
    "missing_native_route_bindings": "native_route_bindings_missing",
    "missing_native_check_bindings": "native_check_bindings_missing",
    "parallel_skillguard_route": "parallel_skillguard_route_forbidden",
    "former_contract_authority": "former_contract_authority_forbidden",
    "missing_skill_inventory": "local_skill_inventory_missing",
    "missing_numbered_plan": "numbered_role_plan_missing",
    "unintegrated_delegation": "delegated_outputs_not_integrated",
    "missing_independent_flowguard": "independent_flowguard_missing",
    "stale_final_receipts": "final_parent_receipts_missing",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _scenario_report() -> dict[str, Any]:
    good, positive_blocker = model._run(model.ContractInput())
    cases = {
        "missing_opt_in": model.ContractInput(explicit_opt_in=False),
        "ordinary_small_task": model.ContractInput(complex_long_project=False),
        "missing_native_route_bindings": model.ContractInput(
            native_route_bindings_current=False
        ),
        "missing_native_check_bindings": model.ContractInput(
            native_check_bindings_current=False
        ),
        "parallel_skillguard_route": model.ContractInput(
            parallel_skillguard_route=True
        ),
        "former_contract_authority": model.ContractInput(
            former_contract_authority_present=True
        ),
        "missing_skill_inventory": model.ContractInput(
            local_skill_inventory_current=False
        ),
        "missing_numbered_plan": model.ContractInput(
            numbered_role_plan_current=False
        ),
        "unintegrated_delegation": model.ContractInput(
            delegated_outputs_integrated=False
        ),
        "missing_independent_flowguard": model.ContractInput(
            independent_flowguard_current=False
        ),
        "stale_final_receipts": model.ContractInput(
            final_parent_receipts_current=False
        ),
    }
    observed = {name: model._run(case)[1] for name, case in cases.items()}
    mismatches = {
        name: {"expected": expected, "observed": observed.get(name, "")}
        for name, expected in EXPECTED_BLOCKERS.items()
        if observed.get(name) != expected
    }
    return {
        "ok": good.closure_bound and not positive_blocker and not mismatches,
        "positive_closure_bound": good.closure_bound,
        "positive_blocker": positive_blocker,
        "known_bad_count": len(cases),
        "known_bad_blockers": observed,
        "mismatches": mismatches,
    }


def _progress_report() -> dict[str, Any]:
    input_obj = model.ContractInput()
    state = model.ContractState()
    trace: list[dict[str, Any]] = []
    monotonic = True
    previous = state
    for block in model.BLOCKS:
        result = next(iter(block.apply(input_obj, state)))
        state = result.new_state
        monotonic = monotonic and all(
            not getattr(previous, field_name) or getattr(state, field_name)
            for field_name in (
                "activation_bound",
                "route_plan_bound",
                "workstream_bound",
                "closure_bound",
            )
        )
        invariant_failures = []
        for name, check in (
            ("singular_native_authority", model.singular_native_authority),
            ("monotonic_closure", model.monotonic_closure),
        ):
            outcome = check(state, None)
            if not outcome.ok:
                invariant_failures.append(name)
        trace.append(
            {
                "block": block.name,
                "label": result.label,
                "state": {
                    "activation_bound": state.activation_bound,
                    "route_plan_bound": state.route_plan_bound,
                    "workstream_bound": state.workstream_bound,
                    "closure_bound": state.closure_bound,
                },
                "invariant_failures": invariant_failures,
            }
        )
        monotonic = monotonic and not invariant_failures
        previous = state
    labels = [str(row["label"]) for row in trace]
    return {
        "ok": monotonic and state.closure_bound and len(labels) == len(set(labels)),
        "monotonic": monotonic,
        "terminal_closure_reached": state.closure_bound,
        "loop_or_duplicate_label": len(labels) != len(set(labels)),
        "trace": trace,
    }


def _conformance_report(exported: Mapping[str, Any]) -> dict[str, Any]:
    routes = [row for row in exported.get("routes", []) if isinstance(row, Mapping)]
    steps = [row for row in exported.get("steps", []) if isinstance(row, Mapping)]
    obligations = [
        row for row in exported.get("obligations", []) if isinstance(row, Mapping)
    ]
    route_ids = [str(row.get("route_id") or "") for row in routes]
    step_ids = [str(row.get("step_id") or "") for row in steps]
    obligation_ids = [str(row.get("obligation_id") or "") for row in obligations]
    owners = {str(row.get("owner_id") or "") for row in routes}
    invariant_ids = set(exported.get("invariant_ids") or ())
    findings: list[str] = []
    if len(route_ids) != 4 or len(route_ids) != len(set(route_ids)):
        findings.append("route_identity_not_exactly_four_unique")
    if len(step_ids) != len(set(step_ids)):
        findings.append("duplicate_step_identity")
    if len(obligation_ids) != 10 or len(obligation_ids) != len(set(obligation_ids)):
        findings.append("obligation_identity_not_exactly_ten_unique")
    if owners != {"flowpilot_runtime_router"}:
        findings.append("native_owner_not_singular")
    known_steps = set(step_ids)
    for route in routes:
        declared = set(route.get("step_ids") or ())
        required = {
            str(route.get("start_step_id") or ""),
            str(route.get("success_terminal_step_id") or ""),
            str(route.get("blocked_terminal_step_id") or ""),
        }
        if not required <= declared or not declared <= known_steps:
            findings.append(f"route_step_refinement_failed:{route.get('route_id')}")
    for obligation in obligations:
        if not set(obligation.get("owner_step_ids") or ()) <= known_steps:
            findings.append(
                f"obligation_owner_missing:{obligation.get('obligation_id')}"
            )
        if str(obligation.get("invariant_id") or "") not in invariant_ids:
            findings.append(
                f"obligation_invariant_missing:{obligation.get('obligation_id')}"
            )
    return {
        "ok": not findings,
        "route_count": len(routes),
        "step_count": len(steps),
        "obligation_count": len(obligations),
        "owners": sorted(owners),
        "findings": findings,
    }


def _contract_refinement_report(exported: Mapping[str, Any]) -> dict[str, Any]:
    source = _read_json(CONTRACT_SOURCE_PATH)
    declared_obligations = {
        str(obligation_id)
        for profile in source.get("closure_profiles", [])
        if isinstance(profile, Mapping)
        for obligation_id in profile.get("required_obligation_ids", [])
        if obligation_id
    }
    exported_obligations = {
        str(row.get("obligation_id") or "")
        for row in exported.get("obligations", [])
        if isinstance(row, Mapping) and row.get("required") is True
    }
    covered_obligations = {
        str(obligation_id)
        for check in source.get("checks", [])
        if isinstance(check, Mapping)
        for obligation_id in check.get("covers_obligation_ids", [])
    }
    final_check = next(
        (
            row
            for row in source.get("checks", [])
            if isinstance(row, Mapping)
            and row.get("check_id") == "check:flowpilot-final-receipt"
        ),
        {},
    )
    final_args = [str(value) for value in final_check.get("args", [])]
    evaluator_hash = hashlib.sha256(
        model.__file__ and Path(model.__file__).read_bytes()
    ).hexdigest().upper()
    findings: list[str] = []
    if source.get("integration_mode") != "native-integrated":
        findings.append("integration_mode_not_native_integrated")
    if source.get("native_route_owner") != "flowpilot_runtime_router":
        findings.append("native_route_owner_not_flowpilot")
    native_route_ids = {
        str(row.get("native_route_id") or "")
        for row in source.get("native_route_bindings", [])
        if isinstance(row, Mapping)
    }
    exported_route_ids = {
        str(row.get("route_id") or "")
        for row in exported.get("routes", [])
        if isinstance(row, Mapping)
    }
    if native_route_ids != exported_route_ids:
        findings.append("native_route_bindings_not_exact")
    declared_check_ids = {
        str(row.get("check_id") or "")
        for row in source.get("checks", [])
        if isinstance(row, Mapping)
    }
    native_check_ids = {
        str(row.get("native_check_id") or "")
        for row in source.get("native_check_bindings", [])
        if isinstance(row, Mapping)
    }
    if native_check_ids != declared_check_ids:
        findings.append("native_check_bindings_not_exact")
    for binding in source.get("native_route_bindings", []):
        if not isinstance(binding, Mapping) or not (ROOT / str(binding.get("source") or "")).is_file():
            findings.append(
                f"native_route_source_missing:{binding.get('native_route_id') if isinstance(binding, Mapping) else 'invalid'}"
            )
    for binding in source.get("native_check_bindings", []):
        if not isinstance(binding, Mapping) or not (ROOT / str(binding.get("evidence_source") or "")).is_file():
            findings.append(
                f"native_check_source_missing:{binding.get('native_check_id') if isinstance(binding, Mapping) else 'invalid'}"
            )
    if source.get("may_define_parallel_execution_route") is not False:
        findings.append("parallel_execution_route_not_forbidden")
    if source.get("may_define_skillguard_runtime_route") is not False:
        findings.append("skillguard_runtime_route_not_forbidden")
    if declared_obligations != exported_obligations:
        findings.append("contract_and_model_obligations_diverge")
    if not declared_obligations <= covered_obligations:
        findings.append("required_obligation_without_declared_check")
    if "--background" in final_args or "--resume" in final_args:
        findings.append("final_receipt_consumer_can_execute_owner")
    if "--verify-background" not in final_args or not any(
        value.replace("\\", "/").endswith("/v0.12.0-final")
        for value in final_args
    ):
        findings.append("final_receipt_identity_not_v0_12_0_read_only")
    depth_profile = source.get("depth_profile") or {}
    if depth_profile.get("enforcement_level") != "enforced":
        findings.append("declared_check_supervision_not_enforced")
    if depth_profile.get("required_closure_profiles") != ["enforced"]:
        findings.append("declared_check_closure_not_singular")
    provider_runtime = depth_profile.get("provider_runtime") or {}
    if provider_runtime.get("required_enrollment_status") != "enrolled":
        findings.append("provider_runtime_not_enrolled")
    readiness_check_ids = {
        str(check_id)
        for check_id in provider_runtime.get("readiness_check_ids", [])
        if check_id
    }
    if not readiness_check_ids or not readiness_check_ids <= declared_check_ids:
        findings.append("provider_runtime_readiness_not_target_owned")
    return {
        "ok": not findings,
        "declared_obligation_count": len(declared_obligations),
        "covered_obligation_count": len(declared_obligations & covered_obligations),
        "native_route_binding_count": len(native_route_ids),
        "native_check_binding_count": len(native_check_ids),
        "native_evaluator_hash": evaluator_hash,
        "findings": findings,
    }


def run_checks() -> dict[str, Any]:
    exported = model.export_contract_model()
    scenarios = _scenario_report()
    progress = _progress_report()
    conformance = _conformance_report(exported)
    refinement = _contract_refinement_report(exported)
    return {
        "schema_version": "flowpilot.skillguard_contract_checks.v1",
        "model_id": "flowpilot_skillguard_current_contract",
        "ok": all(
            section["ok"]
            for section in (scenarios, progress, conformance, refinement)
        ),
        "scenario_review": scenarios,
        "progress_and_loop_review": progress,
        "contract_conformance": conformance,
        "contract_refinement": refinement,
        "claim_boundary": (
            "These checks prove the finite current FlowPilot-to-SkillGuard contract projection, "
            "its single native owner, declared negative cases, and read-only final receipt binding. "
            "They do not execute FlowPilot work or license SkillGuard execution-depth claims."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    report = run_checks()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
