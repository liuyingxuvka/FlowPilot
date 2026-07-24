"""Run FlowGuard 0.53 PPA/BCL maintenance checks for FlowPilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable

from flowguard import (
    review_behavior_commitment_ledger,
    review_field_lifecycle,
    review_primary_path_authority,
    review_risk_evidence_ledger,
)

try:  # pragma: no cover
    from . import flowpilot_053_ppa_maintenance_model as model
    from . import flowpilot_ai_response_execution_closure_model as formal_ai_model
    from . import run_flowpilot_pm_visible_summary_checks
except ImportError:  # pragma: no cover
    import flowpilot_053_ppa_maintenance_model as model
    import flowpilot_ai_response_execution_closure_model as formal_ai_model
    import run_flowpilot_pm_visible_summary_checks

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_tier.source_fingerprint import source_fingerprint


RESULTS_PATH = ROOT / "flowpilot_053_ppa_maintenance_results.json"
FORMAL_AI_RESULTS_PATH = (
    REPO_ROOT / "tmp" / "test_results" / "formal_ai_submit_adversarial.json"
)
MODEL_TEST_ALIGNMENT_RESULTS_PATH = ROOT / "flowpilot_model_test_alignment_results.json"


def _portable_repo_path(path: Path) -> str:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    try:
        return candidate.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _formal_ai_execution_evidence_report(
    path: Path = FORMAL_AI_RESULTS_PATH,
) -> dict[str, Any]:
    payload = _json_object(path)
    closure = payload.get("execution_closure")
    closure = closure if isinstance(closure, dict) else {}
    aggregate = closure.get("coverage_summary", {}).get("aggregate", {})
    aggregate = aggregate if isinstance(aggregate, dict) else {}
    proof = payload.get("proof_artifact_ref")
    proof = proof if isinstance(proof, dict) else {}
    current_fingerprint = formal_ai_model.source_fingerprint()
    checks = {
        "result_ok": payload.get("ok") is True,
        "adversarial_mode": payload.get("mode") == "adversarial",
        "source_current": closure.get("source_fingerprint") == current_fingerprint,
        "proof_current": proof.get("source_fingerprint") == current_fingerprint,
        "proof_final_passed": proof.get("final_status") == "passed",
        "executed_nonzero": int(aggregate.get("executed") or 0) > 0,
        "executed_equals_passed": aggregate.get("executed") == aggregate.get("passed"),
        "failed_zero": aggregate.get("failed") == 0,
        "stale_zero": aggregate.get("stale") == 0,
        "proof_backed_equals_passed": aggregate.get("proof_backed") == aggregate.get("passed"),
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "path": _portable_repo_path(path),
        "checks": checks,
        "summary": (
            f"Formal adversarial AI execution is current and proof-backed "
            f"({int(aggregate.get('passed') or 0)} passed)."
            if ok
            else "Formal adversarial AI execution result is missing, stale, or non-passing."
        ),
    }


def _model_test_alignment_evidence_report(
    path: Path = MODEL_TEST_ALIGNMENT_RESULTS_PATH,
) -> dict[str, Any]:
    payload = _json_object(path)
    execution = payload.get("execution_evidence")
    execution = execution if isinstance(execution, dict) else {}
    current_fingerprint = source_fingerprint()
    checks = {
        "result_ok": payload.get("ok") is True,
        "done_or_stronger_scope": payload.get("claim_scope") in {"done", "release", "publish"},
        "evidence_passed": payload.get("evidence_status") == "passed",
        "execution_bundle_ok": execution.get("ok") is True,
        "snapshot_fingerprint_matches": execution.get("snapshot_fingerprint_matches")
        is True,
        "manifest_matches_current": execution.get("manifest_snapshot_fingerprint")
        == current_fingerprint,
        "expected_matches_current": execution.get("expected_source_fingerprint") == current_fingerprint,
        "no_execution_failures": not execution.get("failures"),
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "path": _portable_repo_path(path),
        "checks": checks,
        "summary": (
            "Strict model-test alignment consumes a current done-scope execution manifest."
            if ok
            else "Strict model-test alignment result is missing, stale, declaration-only, or non-passing."
        ),
    }


def _report_dict(report: Any) -> dict[str, Any]:
    if hasattr(report, "to_dict"):
        return report.to_dict()
    return dict(report)


def _finding_codes(report: Any) -> set[str]:
    return {finding.code for finding in getattr(report, "findings", ())}


def _negative_case(
    *,
    name: str,
    reviewer: Callable[[Any], Any],
    payload: Any,
    expected_codes: set[str],
) -> dict[str, Any]:
    report = reviewer(payload)
    codes = _finding_codes(report)
    return {
        "name": name,
        "ok": (not report.ok) and expected_codes.issubset(codes),
        "expected_codes": sorted(expected_codes),
        "finding_codes": sorted(codes),
        "report": _report_dict(report),
    }


def _source_guard_report() -> dict[str, Any]:
    runtime_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    contracts_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_core_runtime"
        / "packet_result_contracts.py"
    )
    prompt_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "runtime_kit"
        / "prompts"
        / "packets"
        / "output_contract_section.md"
    )
    runtime_text = runtime_path.read_text(encoding="utf-8")
    contracts_text = contracts_path.read_text(encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    checks = {
        "summary_is_required_by_contract": "pm_visible_summary" in contracts_text
        and "FLOWGUARD_REPORT_NON_EMPTY_ARRAY_FIELDS" in contracts_text,
        "runtime_uses_missing_summary_as_mechanical_failure": "formal role result requires role-authored pm_visible_summary"
        in runtime_text,
        "runtime_carries_recent_summary": "recent_role_report_summary" in runtime_text,
        "prompt_says_runtime_does_not_synthesize": "runtime relays it to PM and does not synthesize it" in prompt_text,
        "prompt_says_summaries_not_substitutes": "summaries are navigation aids, not substitutes" in prompt_text,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
            "skills/flowpilot/assets/runtime_kit/prompts/packets/output_contract_section.md",
        ],
    }


def build_report(
    *,
    formal_ai_evidence: dict[str, Any] | None = None,
    model_test_alignment_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ppa_plan = model.build_primary_path_plan()
    ppa_report = review_primary_path_authority(ppa_plan)
    bcl_ledger = model.build_behavior_commitment_ledger(ppa_report)
    bcl_report = review_behavior_commitment_ledger(bcl_ledger)
    field_plan = model.build_field_lifecycle_plan()
    field_report = review_field_lifecycle(field_plan)
    formal_ai_evidence = formal_ai_evidence or _formal_ai_execution_evidence_report()
    model_test_alignment_evidence = (
        model_test_alignment_evidence or _model_test_alignment_evidence_report()
    )
    risk_plan = model.build_risk_evidence_ledger_plan(
        ppa_report,
        bcl_report,
        field_report,
        formal_ai_evidence=formal_ai_evidence,
        model_test_alignment_evidence=model_test_alignment_evidence,
    )
    risk_report = review_risk_evidence_ledger(risk_plan)
    pm_visible_summary = run_flowpilot_pm_visible_summary_checks.run_checks()
    source_guard = _source_guard_report()

    negative_cases = [
        _negative_case(
            name="old_field_fallback_masks_primary_failure",
            reviewer=review_primary_path_authority,
            payload=model.build_broken_old_field_fallback_plan(),
            expected_codes={"primary_failure_masked_by_fallback_success", "old_field_or_backup_cache_masks_primary_failure"},
        ),
        _negative_case(
            name="duplicate_primary_authority",
            reviewer=review_primary_path_authority,
            payload=model.build_broken_duplicate_primary_authority_plan(),
            expected_codes={"duplicate_primary_runtime_authority"},
        ),
        _negative_case(
            name="broad_claim_missing_coverage",
            reviewer=review_primary_path_authority,
            payload=model.build_broken_missing_coverage_plan(),
            expected_codes={
                "primary_path_cartesian_coverage_missing",
                "primary_path_coverage_shards_missing",
                "primary_path_risk_gate_missing",
            },
        ),
        _negative_case(
            name="path_sensitive_commitment_missing_ppa",
            reviewer=review_behavior_commitment_ledger,
            payload=model.build_broken_missing_ppa_ledger(),
            expected_codes={"commitment_missing_primary_path_authority"},
        ),
        _negative_case(
            name="ppa_binding_missing_primary_path_id",
            reviewer=review_behavior_commitment_ledger,
            payload=model.build_broken_ppa_missing_primary_path_ids_ledger(),
            expected_codes={"commitment_primary_path_id_missing"},
        ),
        _negative_case(
            name="commitment_stale_evidence",
            reviewer=review_behavior_commitment_ledger,
            payload=model.build_broken_stale_evidence_ledger(),
            expected_codes={"commitment_current_evidence_missing"},
        ),
        _negative_case(
            name="field_lifecycle_missing_projection",
            reviewer=review_field_lifecycle,
            payload=model.build_broken_missing_field_projection_plan(),
            expected_codes={"behavior_field_projection_missing"},
        ),
    ]

    gates = {
        "ppa": ppa_report.ok,
        "behavior_commitments": bcl_report.ok,
        "field_lifecycle": field_report.ok,
        "risk_evidence": risk_report.ok,
        "pm_visible_summary_existing_runner": pm_visible_summary["ok"],
        "source_guard": source_guard["ok"],
        "formal_ai_execution_evidence": formal_ai_evidence["ok"],
        "model_test_alignment_evidence": model_test_alignment_evidence["ok"],
        "negative_cases": all(case["ok"] for case in negative_cases),
    }
    return {
        "result_type": "flowpilot_053_ppa_maintenance",
        "ok": all(gates.values()),
        "model_id": model.MODEL_ID,
        "gates": gates,
        "primary_path_authority": {
            "plan": ppa_plan.to_dict(),
            "report": ppa_report.to_dict(),
        },
        "behavior_commitment_ledger": {
            "ledger": bcl_ledger.to_dict(),
            "report": bcl_report.to_dict(),
        },
        "field_lifecycle": {
            "plan": field_plan.to_dict(),
            "report": field_report.to_dict(),
        },
        "risk_evidence_ledger": {
            "plan": risk_plan.to_dict(),
            "report": risk_report.to_dict(),
        },
        "pm_visible_summary": pm_visible_summary,
        "source_guard": source_guard,
        "formal_ai_execution_evidence": formal_ai_evidence,
        "model_test_alignment_evidence": model_test_alignment_evidence,
        "negative_cases": negative_cases,
        "coverage": {
            "primary_path_intents": list(model.PRIMARY_PATH_INTENTS),
            "commitment_ids": list(model.COMMITMENT_IDS),
            "field_ids": list(model.FIELD_IDS),
            "coverage_case_ids": list(model.COVERAGE_CASE_IDS),
            "coverage_shard_ids": list(model.COVERAGE_SHARD_IDS),
            "coverage_receipt_ids": list(model.COVERAGE_RECEIPT_IDS),
            "risk_gate_ids": list(model.PPA_RISK_GATES + model.BCL_RISK_GATES),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
