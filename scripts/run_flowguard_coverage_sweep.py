"""Read-only FlowGuard coverage sweep and finding ledger.

The sweep intentionally does not pass --json-out to model runners and does not
refresh existing result files. Runners that still write results by default are
read from their last persisted JSON result instead of being executed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"

STRONG_COVERAGE = {
    "flowpilot_control_plane_friction",
    "flowpilot_complete_system_alignment",
    "flowpilot_complete_system_development",
    "flowpilot_complete_system_historical_replay",
    "flowpilot_complete_system_live_host_readiness",
    "flowpilot_complete_system_runtime",
    "flowpilot_complete_system_structure",
    "flowpilot_complete_system_testmesh",
    "flowpilot_complete_system_ui",
    "flowpilot_core_runtime",
    "flowpilot_final_confidence_gate",
    "flowpilot_gate_policy_audit",
    "flowpilot_information_flow_alignment",
    "flowpilot_lifecycle_guard",
    "flowpilot_new_control_plane_duty",
    "flowpilot_new_entrypoint",
    "protocol_contract_conformance",
    "flowpilot_router_loop",
    "flowpilot_startup_control",
    "flowpilot_packet_lifecycle",
    "flowpilot_repair_transaction",
    "flowpilot_unified_repair_integrity",
    "flowpilot_control_transaction_registry",
    "flowpilot_contract_exhaustion_mesh",
    "flowpilot_cartesian_control_plane_exhaustion",
    "flowpilot_current_contract_cartesian_matrix",
    "flowpilot_executable_matrix_coverage",
    "flowpilot_legal_next_action",
    "flowpilot_event_capability_registry",
    "flowpilot_route_replanning_policy",
    "flowpilot_cross_plane_friction",
    "flowpilot_fake_ai_runtime_replay",
    "flowpilot_persistent_router_daemon",
    "flowpilot_model_mesh",
    "flowpilot_rejection_liveness_matrix",
    "flowpilot_route_authority_singularity",
    "flowpilot_model_hierarchy",
    "flowpilot_packet_result_family_parity",
    "flowpilot_runtime_gateway_adoption",
    "flowpilot_singleton_identity",
    "flowpilot_structure_maintenance",
    "flowpilot_router_facade_split",
    "flowpilot_model_test_alignment",
    "flowpilot_terminal_flowguard_coverage",
    "prompt_isolation",
}
ABSTRACT_STRONG = {
    "meta",
    "capability",
    "flowpilot_resume",
    "output_contract",
    "flowpilot_gate_decision_contract",
    "flowpilot_protocol_kernel",
    "flowpilot_protocol_kernel_stress",
    "flowpilot_similarity_convergence",
}
SPECIALIZED = {
    "card_instruction_coverage",
    "defect_governance",
    "flowpilot_planning_quality",
    "flowpilot_reviewer_active_challenge",
    "release_tooling",
    "startup_pm_review",
    "user_flow_diagram",
}
SUPPORTING_COVERAGE = {
    "command_refinement",
    "flowpilot_blocker_repair_information_flow",
    "flowpilot_canonical_repair_scope_rotation",
    "flowpilot_card_envelope",
    "flowpilot_control_surface_contract",
    "flowpilot_control_plane_ledger_consolidation",
    "flowpilot_control_plane_state_consistency",
    "flowpilot_core_runtime_development",
    "flowpilot_controller_break_glass",
    "flowpilot_controller_patrol",
    "flowpilot_controller_process_aside",
    "flowpilot_controller_receipt_evidence_fold",
    "flowpilot_controller_wait_receipt_audit",
    "flowpilot_current_scope_pre_review_reconciliation",
    "flowpilot_daemon_controller_actions",
    "flowpilot_daemon_liveness",
    "flowpilot_daemon_microstep_lifecycle",
    "flowpilot_daemon_reconciliation",
    "flowpilot_daemon_startup_lock",
    "flowpilot_daemon_terminal_projection",
    "flowpilot_daemon_wait_liveness",
    "flowpilot_decision_liveness",
    "flowpilot_derived_view_prompt_boundary",
    "flowpilot_deterministic_startup_bootstrap",
    "flowpilot_dispatch_recipient_gate",
    "flowpilot_dynamic_return_path",
    "flowpilot_event_contract",
    "flowpilot_event_envelope_transfer",
    "flowpilot_event_idempotency",
    "flowpilot_fake_project_rehearsal",
    "flowpilot_acceptance_testmesh",
    "flowpilot_field_contract",
    "flowpilot_field_mesh",
    "flowpilot_handoff_artifact_protocol",
    "flowpilot_material_artifact_map",
    "flowpilot_model_driven_recursive_route",
    "flowpilot_model_maturation",
    "flowpilot_modeling_coverage",
    "flowpilot_optimization_proposal",
    "flowpilot_packet_open_authority",
    "flowpilot_parallel_packet_batch",
    "flowpilot_parallel_run_isolation",
    "flowpilot_parent_child_lifecycle",
    "flowpilot_pm_package_absorption",
    "flowpilot_pm_suggestion_disposition",
    "flowpilot_pm_visible_summary",
    "flowpilot_prework_flowguard_gate",
    "flowpilot_process_liveness",
    "flowpilot_project_control_information_flow",
    "flowpilot_prompt_boundary",
    "flowpilot_project_topology_orientation",
    "flowpilot_recursive_closure_reconciliation",
    "flowpilot_recursive_decomposition",
    "flowpilot_recursive_route_execution",
    "flowpilot_recovery_supervisor",
    "flowpilot_requirement_traceability",
    "flowpilot_reviewer_only_gate",
    "flowpilot_flowguard_work_order",
    "flowpilot_real_issue_backfeed",
    "flowpilot_role_packet_access",
    "flowpilot_role_output_runtime",
    "flowpilot_repair_dossier_testmesh",
    "flowpilot_role_recovery",
    "flowpilot_role_recovery_liveness",
    "flowpilot_route_display",
    "flowpilot_route_hard_gate",
    "flowpilot_route_mutation_activation",
    "flowpilot_router_error_recovery",
    "flowpilot_router_internal_mechanics",
    "flowpilot_router_reconciliation_branch_pruning",
    "flowpilot_runtime_closure",
    "flowpilot_semantic_gate_outcome",
    "flowpilot_sequential_parent_replay_review",
    "flowpilot_shared_maintenance_log",
    "flowpilot_slow_test_contract",
    "flowpilot_startup_intake_ui",
    "flowpilot_startup_optimization",
    "flowpilot_structural_refactor",
    "flowpilot_terminal_state_monotonicity",
    "flowpilot_terminal_supplemental_repair",
    "flowpilot_terminal_summary",
    "flowpilot_test_obligation_ownership",
    "flowpilot_test_tiering",
    "flowpilot_two_table_async_scheduler",
    "flowpilot_stop_host_orphan_recovery",
    "flowpilot_stopped_blocker_recheck",
    "flowpilot_symmetric_work_packet",
    "flowpilot_unsupported_transition_pruning",
    "flowpilot_validation_artifact_canonicalization",
    "flowpilot_validation_pm_gate",
    "flowpilot_workflow_step_contract",
    "long_check_observability",
    "new_only_runtime",
    "proof_carrying",
    "router_action_contract",
    "router_next_recipient",
}


def _runner_key(path: Path) -> str:
    name = path.stem
    if name.startswith("run_"):
        name = name[4:]
    if name.endswith("_checks"):
        name = name[:-7]
    return name


def _coverage_tier(key: str) -> str:
    if key in STRONG_COVERAGE:
        return "coverage_strong"
    if key in ABSTRACT_STRONG:
        return "abstract_strong_live_mapping_weaker"
    if key in SPECIALIZED:
        return "specialized_assertion_or_local_hazard"
    if key in SUPPORTING_COVERAGE:
        return "supporting_model_owned"
    return "unclassified_model_tier"


def _script_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _declared_result_path(path: Path, text: str) -> Path | None:
    key = _runner_key(path)
    if key == "meta":
        return path.parent / "meta_thin_parent_results.json"
    if key == "capability":
        return path.parent / "capability_thin_parent_results.json"
    if key == "flowpilot_final_confidence_gate":
        return path.parent / "flowpilot_final_confidence_gate_results.json"
    match = re.search(r'RESULTS_PATH\s*=\s*ROOT\s*/\s*"simulations"\s*/\s*"([^"]+)"', text)
    if match:
        return path.parent / match.group(1)
    match = re.search(r'RESULTS_PATH\s*=\s*ROOT\s*/\s*"([^"]+)"', text)
    if match:
        return path.parent / match.group(1)
    match = re.search(r'RESULTS_PATH\s*=\s*Path\(__file__\)\.with_name\(\s*"([^"]+)"\s*\)', text)
    if match:
        return path.parent / match.group(1)
    match = re.search(
        r'RESULTS_PATH\s*=\s*Path\(__file__\)\.resolve\(\)\.with_name\(\s*"([^"]+)"\s*\)',
        text,
    )
    if match:
        return path.parent / match.group(1)
    match = re.search(
        r'RESULTS_PATH\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*/\s*"([^"]+)"',
        text,
    )
    if match:
        return path.parent / match.group(1)
    return None


def _read_only_runnable(text: str) -> bool:
    if "write_text" not in text:
        return True
    if "--json-out" not in text:
        return False
    if "default=RESULTS_PATH" in text or "default=str(RESULTS_PATH)" in text:
        return False
    return "if args.json_out" in text


def _delegated_impl_text(path: Path, text: str) -> str:
    match = re.search(r"import\s+([A-Za-z0-9_]+_runner_impl)\s+as\s+_impl", text)
    if not match:
        return ""
    impl_path = path.with_name(match.group(1) + ".py")
    try:
        return impl_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _supports_argument(path: Path, text: str, argument: str) -> bool:
    quoted = re.escape(argument)
    direct = re.search(rf"add_argument\(\s*['\"]{quoted}['\"]", text)
    if direct:
        return True
    impl_text = _delegated_impl_text(path, text)
    if not impl_text:
        return False
    return bool(re.search(rf"add_argument\(\s*['\"]{quoted}['\"]", impl_text))


def _parse_json_text(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if not stripped:
        return None, "empty output"
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None, "output did not contain a JSON object"
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON output: {exc}"
    if not isinstance(value, dict):
        return None, "JSON output was not an object"
    return value, None


def _load_existing_result(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, "runner writes by default and has no declared result path"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"declared result file is missing: {path.relative_to(ROOT).as_posix()}"
    except json.JSONDecodeError as exc:
        return None, f"declared result file is invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "declared result JSON was not an object"
    return value, None


def _section_ok(section: Any) -> bool | None:
    if isinstance(section, dict) and isinstance(section.get("ok"), bool):
        return bool(section["ok"])
    return None


def _coverage_sections(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    abstract_keys = (
        "safe_graph",
        "flowguard_explorer",
        "graph",
        "checks",
        "scenario_metrics",
    )
    progress_keys = ("progress", "loop", "loop_review")
    hazard_keys = ("hazard_checks", "negative_scenarios", "scenario_review")
    live_keys = tuple(key for key in payload if "live" in key and isinstance(payload[key], dict))
    source_keys = tuple(key for key in payload if "source" in key and isinstance(payload[key], dict))

    def summarize(keys: tuple[str, ...]) -> dict[str, Any]:
        present = [key for key in keys if key in payload]
        oks = [_section_ok(payload[key]) for key in present]
        known = [value for value in oks if value is not None]
        return {
            "present": bool(present),
            "keys": present,
            "ok": all(known) if known else None,
        }

    return {
        "abstract": summarize(abstract_keys),
        "progress": summarize(progress_keys),
        "hazards": summarize(hazard_keys),
        "live": summarize(live_keys),
        "source": summarize(source_keys),
    }


def _collect_findings(
    value: Any,
    *,
    runner: str,
    section_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = section_path + (str(key),)
            if key == "findings" and isinstance(child, list):
                section = "live" if any("live" in part for part in section_path) else "source"
                if not any(("live" in part or "source" in part) for part in section_path):
                    section = "abstract"
                for item in child:
                    if isinstance(item, dict):
                        finding = dict(item)
                        finding["runner"] = runner
                        finding["section"] = section
                        finding["section_path"] = ".".join(section_path)
                        finding["classification"] = _classify_finding(finding)
                        findings.append(finding)
            else:
                findings.extend(_collect_findings(child, runner=runner, section_path=next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                _collect_findings(item, runner=runner, section_path=section_path + (str(index),))
            )
    return findings


def _classify_finding(finding: dict[str, Any]) -> str:
    section = str(finding.get("section") or "")
    section_path = str(finding.get("section_path") or "")
    severity = str(finding.get("severity") or "").lower()
    if "known_bad_sanity_checks" in section_path:
        return "boundary_expected_or_informational"
    if "current_run_projection" in section_path and (
        severity in {"blocking", "error", "fatal"}
        or finding.get("current_run_can_continue") is False
        or finding.get("decision") == "blocked_by_live_evidence"
    ):
        return "modeled_current_live_hit_fix_runtime_or_current_state"
    if section == "live":
        return "modeled_current_live_hit_fix_runtime_or_current_state"
    if section == "source":
        return "modeled_source_hit_fix_source_or_runtime"
    if severity in {"error", "fatal"}:
        return "abstract_or_runner_failure_review_check_flow"
    return "boundary_expected_or_informational"


def _run_runner(path: Path, text: str, timeout_seconds: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    command = [sys.executable, str(path.relative_to(ROOT))]
    if _runner_key(path) == "flowpilot_final_confidence_gate":
        command.extend(
            [
                "--run-checks",
                "--repository-confidence-only",
                "--json-out",
                str(SIMULATIONS / "flowpilot_final_confidence_gate_results.json"),
            ]
        )
    if _supports_argument(path, text, "--json"):
        command.append("--json")
    if _supports_argument(path, text, "--no-write-results"):
        command.append("--no-write-results")
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        metadata = {
            "mode": "executed_read_only",
            "command": command,
            "exit_code": None,
            "parse_error": f"runner timed out after {timeout_seconds} seconds",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
        return None, metadata
    payload, parse_error = _parse_json_text(completed.stdout)
    metadata = {
        "mode": "executed_read_only",
        "command": command,
        "exit_code": completed.returncode,
        "parse_error": parse_error,
        "stderr_tail": completed.stderr[-2000:] if completed.stderr else "",
    }
    return payload, metadata


def _runner_record(path: Path, *, timeout_seconds: int) -> dict[str, Any]:
    key = _runner_key(path)
    text = _script_text(path)
    result_path = _declared_result_path(path, text)
    can_run = _read_only_runnable(text)
    if can_run:
        payload, metadata = _run_runner(path, text, timeout_seconds)
    else:
        payload, error = _load_existing_result(result_path)
        metadata = {
            "mode": "read_existing_result",
            "reason": "runner writes result files by default",
            "result_path": result_path.relative_to(ROOT).as_posix() if result_path else None,
            "parse_error": error,
            "exit_code": None,
        }

    parsed = payload is not None
    sections = _coverage_sections(payload or {})
    findings = _collect_findings(payload or {}, runner=key)
    skipped_checks = payload.get("skipped_checks", {}) if isinstance(payload, dict) else {}
    top_level_ok = payload.get("ok") if isinstance(payload, dict) and isinstance(payload.get("ok"), bool) else None
    if top_level_ok is None:
        ok = parsed and not metadata.get("parse_error") and metadata.get("exit_code") in (None, 0)
    else:
        ok = top_level_ok
    return {
        "runner": key,
        "script": path.relative_to(ROOT).as_posix(),
        "coverage_tier": _coverage_tier(key),
        "read_only_mode": metadata["mode"],
        "ok": ok,
        "parsed": parsed,
        "sections": sections,
        "finding_count": len(findings),
        "findings": findings,
        "skipped_checks": skipped_checks,
        "metadata": metadata,
    }


def _classification_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for finding in record["findings"]:
            key = str(finding.get("classification") or "unclassified")
            counts[key] = counts.get(key, 0) + 1
        if not record["parsed"]:
            counts["runner_unparsed_or_unavailable"] = counts.get("runner_unparsed_or_unavailable", 0) + 1
    return counts


def run_sweep(*, timeout_seconds: int) -> dict[str, Any]:
    runners = sorted(SIMULATIONS.glob("run_*_checks.py"))
    records = [_runner_record(path, timeout_seconds=timeout_seconds) for path in runners]
    finding_ledger = [
        finding
        for record in records
        for finding in record["findings"]
    ]
    tier_counts: dict[str, int] = {}
    for record in records:
        tier = str(record["coverage_tier"])
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    return {
        "schema_version": "flowguard.coverage_sweep.v1",
        "read_only": True,
        "runner_count": len(records),
        "read_only_execution_count": sum(
            1 for record in records if record["read_only_mode"] == "executed_read_only"
        ),
        "existing_result_read_count": sum(
            1 for record in records if record["read_only_mode"] == "read_existing_result"
        ),
        "ok": all(record["parsed"] for record in records),
        "finding_count": len(finding_ledger),
        "classification_counts": _classification_counts(records),
        "coverage_tier_counts": tier_counts,
        "finding_ledger": finding_ledger,
        "runners": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--fail-on-finding", action="store_true")
    args = parser.parse_args()

    result = run_sweep(timeout_seconds=args.timeout_seconds)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    if not result["ok"]:
        return 1
    if args.fail_on_finding and result["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
