"""Run FlowGuard TestMesh checks for FlowPilot acceptance-item registry coverage."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

from flowguard import review_test_mesh

try:  # pragma: no cover
    from . import flowpilot_acceptance_testmesh_model as model
    from .flowpilot_evidence_truth import (
        testmesh_final_receipt_fields,
        testmesh_receipt_obligation_ids,
    )
except ImportError:  # pragma: no cover
    import flowpilot_acceptance_testmesh_model as model
    from flowpilot_evidence_truth import (
        testmesh_final_receipt_fields,
        testmesh_receipt_obligation_ids,
    )


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_acceptance_testmesh_results.json")
ROOT = Path(__file__).resolve().parents[1]


def _portable_path(path: Path) -> str:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{resolved.parent.name}/{resolved.name}"

BACKGROUND_CHILD_SUITES = {
    "acceptance_router_quality_gate_children": {
        "tier": "router-quality-gates",
        "expected": (
            "router_quality_gates_background_manifest",
            "router_quality_gates_decisions",
            "router_quality_gates_evidence_package",
            "router_quality_gates_route_check_reports",
            "router_quality_gates_route_check_delivery",
            "router_quality_gates_router_owned_proof",
            "router_quality_gates_artifact_validation",
            "router_quality_gates_model_miss_sync",
            "router_quality_gates_node_acceptance_plan",
            "router_quality_gates_route_repair_reopens_draft",
            "router_quality_gates_root_contract",
            "router_quality_gates_route_draft_product_model",
            "router_quality_gates_node_contracts",
        ),
    },
    "acceptance_router_packet_tier": {
        "tier": "router-packets",
        "expected": (
            "router_packet_runtime",
            "router_packets_generic_ack_mail",
            "router_packets_current_node_direct",
            "router_packets_current_node_dispatch_relay",
            "router_packets_current_node_dispatch_worker_binding",
            "router_packets_current_node_dispatch_unready_leaf",
            "router_packets_result_audit_completion",
            "router_packets_result_audit_reviewer_map",
            "router_packets_result_audit_rejection",
            "router_packets_result_decision_review_card",
            "router_packets_result_decision_relay",
            "router_packets_result_decision_pm_repair",
            "router_packets_grant_result_requires_write",
            "router_packets_grant_unresolved_node_entry",
            "router_cards",
            "router_ack_return",
        ),
    },
    "acceptance_router_route_tier": {
        "tier": "router-route",
        "expected": (
            "router_boundaries",
            "router_route_mutation_draft_policy",
            "router_route_mutation_draft_activation_reviewed",
            "router_route_mutation_draft_missing_active_node",
            "router_route_mutation_model_miss_refs",
            "router_route_mutation_model_miss_unlocks",
            "router_route_mutation_model_miss_non_authorizing",
            "router_route_mutation_model_miss_out_of_scope",
            "router_route_mutation_model_miss_role_work",
            "router_route_mutation_model_miss_closed_triage",
            "router_route_mutation_model_miss_delivery",
            "router_route_mutation_model_miss_stale_wait",
            "router_route_mutation_acceptance_revise",
            "router_route_mutation_acceptance_model_miss",
            "router_route_mutation_preconditions_final_ledger",
            "router_route_mutation_preconditions_topology_reset",
            "router_route_mutation_preconditions_root_gap",
            "router_route_mutation_transactions",
            "router_route_mutation_topology",
            "router_route_mutation_sibling_replacement",
            "router_route_mutation_parent_backward",
            "router_route_mutation_contracts",
            "router_user_flow_diagram",
        ),
    },
    "acceptance_router_terminal_tier": {
        "tier": "router-terminal",
        "expected": (
            "router_terminal_final_ledger",
            "router_terminal_replay_summary",
            "router_terminal_node_stop",
            "router_closure_dirty_ledgers",
            "router_closure_pm_role_work",
            "router_resume_reentry",
            "router_resume_rehydration",
            "router_resume_role_recovery",
            "router_resume_liveness_faults",
            "router_control_blockers_recorded_events",
            "router_control_blockers_reissue_retry",
            "router_control_blockers_pm_repair_decisions",
            "router_control_blockers_protocol_transactions",
            "router_control_blockers_followup_fatal",
        ),
    },
}

TIER_OVERRIDE_FIELDS = {
    "result_status",
    "evidence_tier",
    "evidence_current",
    "test_count",
    "selected_count",
    "skipped_count",
    "skipped_visible",
    "exit_code",
    "result_path",
    "log_root",
    "background",
    "has_exit_artifact",
    "has_result_artifact",
    "progress_only",
    "duration_seconds",
    "timeout_seconds",
    "stale_reasons",
    "proof_artifact",
    "result_reused",
    "run_id",
    "terminal_status",
    "result_fingerprint",
    "covered_obligation_ids",
    "artifact_version",
    "verifier_version",
    "not_run_reason",
}


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _suite_nonpass_reasons(suite: Any) -> list[str]:
    reasons: list[str] = []
    if suite.result_status != "passed":
        reasons.append(str(suite.result_status))
    if not suite.evidence_current:
        reasons.append("not_current")
    if suite.exit_code not in (0, None):
        reasons.append(f"exit_code:{suite.exit_code}")
    if suite.has_exit_artifact is False:
        reasons.append("missing_exit_artifact")
    if suite.has_result_artifact is False:
        reasons.append("missing_result_artifact")
    if suite.progress_only:
        reasons.append("progress_only")
    if suite.timeout_seconds is not None and suite.result_status != "passed":
        reasons.append("timeout")
    for stale_reason in suite.stale_reasons:
        reasons.append(f"stale:{stale_reason}")
    return list(dict.fromkeys(reasons))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _background_suite_override(
    suite_id: str,
    background_dir: Path | None,
    *,
    covered_obligation_ids: tuple[str, ...] = (),
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if background_dir is None:
        return None, None
    config = BACKGROUND_CHILD_SUITES[suite_id]
    root = Path(background_dir)
    expected = tuple(config["expected"])
    child_rows: list[dict[str, Any]] = []
    missing: list[str] = []
    running: list[str] = []
    failed: list[str] = []
    passed: list[str] = []
    durations: list[float] = []

    for name in expected:
        exit_path = root / f"{name}.exit.txt"
        meta_path = root / f"{name}.meta.json"
        combined_path = root / f"{name}.combined.txt"
        has_any_artifact = exit_path.exists() or meta_path.exists() or combined_path.exists()
        row: dict[str, Any] = {
            "name": name,
            "exit_artifact": _portable_path(exit_path),
            "meta_artifact": _portable_path(meta_path),
            "combined_artifact": _portable_path(combined_path),
            "has_exit_artifact": exit_path.exists(),
            "has_result_artifact": combined_path.exists(),
        }
        if exit_path.exists():
            exit_text = _read_text(exit_path).strip()
            try:
                exit_code = int(exit_text)
            except ValueError:
                exit_code = -1
            row["exit_code"] = exit_code
            row["status"] = "passed" if exit_code == 0 else "failed"
            if exit_code == 0:
                passed.append(name)
            else:
                failed.append(name)
        elif has_any_artifact:
            row["status"] = "progress_only"
            row["exit_code"] = None
            running.append(name)
        else:
            row["status"] = "not_run"
            row["exit_code"] = None
            missing.append(name)
        if meta_path.exists():
            try:
                meta = json.loads(_read_text(meta_path))
            except json.JSONDecodeError:
                meta = {}
            row["meta_status"] = meta.get("status")
            duration = meta.get("duration_seconds")
            if isinstance(duration, (int, float)):
                durations.append(float(duration))
        child_rows.append(row)

    if failed:
        status = "failed"
        evidence_current = True
        exit_code = 1
        reason = f"{config['tier']} child failures: {', '.join(failed)}"
    elif running:
        status = "progress_only"
        evidence_current = False
        exit_code = None
        reason = f"{config['tier']} background children still running or missing exit artifacts: {', '.join(running)}"
    elif missing:
        status = "not_run"
        evidence_current = False
        exit_code = None
        reason = f"{config['tier']} background children missing artifacts: {', '.join(missing)}"
    else:
        status = "passed"
        evidence_current = True
        exit_code = 0
        reason = ""

    portable_root = _portable_path(root)
    override = {
        "result_status": status,
        "evidence_tier": "external_contract" if status == "passed" else "candidate_only",
        "evidence_current": evidence_current,
        "test_count": len(passed),
        "exit_code": exit_code,
        "result_path": portable_root,
        "background": True,
        "has_exit_artifact": not (running or missing),
        "has_result_artifact": root.exists(),
        "progress_only": bool(running),
        "duration_seconds": sum(durations) if durations else None,
        "not_run_reason": reason or f"{config['tier']} artifacts passed",
    }
    proof_paths = [
        root / f"{name}.{suffix}"
        for name in expected
        for suffix in ("meta.json", "exit.txt", "combined.txt")
        if (root / f"{name}.{suffix}").is_file()
    ]
    override["proof_artifact"] = {
        "artifact_id": f"proof.{suite_id}",
        "producer_route": "flowguard-test-mesh",
        "command": f"python scripts/run_test_tier.py --tier {config['tier']} --background",
        "result_path": portable_root,
        "result_status": status,
        "exit_code": exit_code,
        "artifact_fingerprints": {_portable_path(path): _sha256(path) for path in proof_paths},
        "covered_obligation_ids": list(covered_obligation_ids),
        "assertion_scope": "external_contract",
        "current": evidence_current,
        "route_evidence_current": evidence_current,
        "progress_only": bool(running),
        "stale_reasons": [] if evidence_current else [reason],
        "metadata": {
            "selected_child_count": len(expected),
            "executed_child_count": len(passed) + len(failed),
            "passed_child_count": len(passed),
            "failed_child_count": len(failed),
        },
    }
    override.update(
        testmesh_final_receipt_fields(
            override["proof_artifact"],
            covered_obligation_ids=covered_obligation_ids,
        )
    )
    tier_detail = {
        "suite_id": suite_id,
        "tier": config["tier"],
        "background_dir": portable_root,
        "status": status,
        "passed_children": passed,
        "failed_children": failed,
        "running_children": running,
        "missing_children": missing,
        "children": child_rows,
    }
    return override, tier_detail


def _collect_router_tier_overrides(background_dirs: dict[str, Path | None]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    overrides: dict[str, dict[str, Any]] = {}
    details: list[dict[str, Any]] = []
    declared_plan = model.build_testmesh_plan()
    declared_suites = {suite.suite_id: suite for suite in declared_plan.child_suites}
    for suite_id, background_dir in background_dirs.items():
        declared_suite = declared_suites[suite_id]
        override, detail = _background_suite_override(
            suite_id,
            background_dir,
            covered_obligation_ids=testmesh_receipt_obligation_ids(
                declared_plan,
                declared_suite,
            ),
        )
        if override is not None:
            overrides[suite_id] = override
        if detail is not None:
            details.append(detail)
    return overrides, details


def run_checks(
    *,
    release_evidence: bool = False,
    release_result_status: str | None = None,
    release_evidence_current: bool | None = None,
    release_progress_only: bool = False,
    release_background: bool = False,
    release_has_exit_artifact: bool = True,
    release_has_result_artifact: bool = True,
    release_timeout_seconds: float | None = None,
    release_duration_seconds: float | None = None,
    release_stale_reasons: tuple[str, ...] = (),
    release_result_path: str = "tmp/test_background acceptance tier artifacts",
    router_quality_background_dir: Path | None = None,
    router_packets_background_dir: Path | None = None,
    router_route_background_dir: Path | None = None,
    router_terminal_background_dir: Path | None = None,
    routine_evidence_overrides: dict[str, dict[str, Any]] | None = None,
    release_proof_artifact: dict[str, Any] | None = None,
    release_test_count: int | None = None,
    release_selected_count: int | None = None,
) -> dict[str, Any]:
    router_tier_overrides, router_tier_background_details = _collect_router_tier_overrides(
        {
            "acceptance_router_quality_gate_children": router_quality_background_dir,
            "acceptance_router_packet_tier": router_packets_background_dir,
            "acceptance_router_route_tier": router_route_background_dir,
            "acceptance_router_terminal_tier": router_terminal_background_dir,
        }
    )
    evidence_overrides = dict(routine_evidence_overrides or {})
    for suite_id in BACKGROUND_CHILD_SUITES:
        manifest_override = evidence_overrides.get(suite_id)
        if manifest_override is not None and suite_id not in router_tier_overrides:
            router_tier_overrides[suite_id] = {
                key: value
                for key, value in manifest_override.items()
                if key in TIER_OVERRIDE_FIELDS
            }
    plan = model.build_testmesh_plan(
        release_evidence=release_evidence,
        release_result_status=release_result_status,
        release_evidence_current=release_evidence_current,
        release_progress_only=release_progress_only,
        release_background=release_background,
        release_has_exit_artifact=release_has_exit_artifact,
        release_has_result_artifact=release_has_result_artifact,
        release_timeout_seconds=release_timeout_seconds,
        release_duration_seconds=release_duration_seconds,
        release_stale_reasons=release_stale_reasons,
        release_result_path=release_result_path,
        router_tier_overrides=router_tier_overrides,
        routine_evidence_overrides=evidence_overrides,
        release_proof_artifact=release_proof_artifact,
        release_test_count=release_test_count,
        release_selected_count=release_selected_count,
    )
    report = review_test_mesh(plan)
    release_rows = [suite for suite in plan.child_suites if suite.release_required]
    routine_router_rows = [
        suite
        for suite in plan.child_suites
        if suite.suite_id
        in {
            "acceptance_router_quality_gate_children",
            "acceptance_router_packet_tier",
            "acceptance_router_route_tier",
            "acceptance_router_terminal_tier",
        }
    ]
    release_gate_ok = all(
        suite.result_status == "passed"
        and suite.evidence_current
        and suite.exit_code == 0
        and suite.has_exit_artifact
        and suite.has_result_artifact
        and not suite.progress_only
        for suite in release_rows
    )
    routine_router_gate_ok = all(
        suite.result_status == "passed"
        and suite.evidence_current
        and suite.exit_code == 0
        and suite.has_exit_artifact
        and suite.has_result_artifact
        and not suite.progress_only
        for suite in routine_router_rows
    )
    owners = model.payload_cell_owners(plan)
    release_evidence_owners = model.release_evidence_cell_owners(plan)
    missing_cells = [cell_id for cell_id, suite_ids in owners.items() if not suite_ids]
    rows = [
        {
            "id": suite.suite_id,
            "status": suite.result_status,
            "freshness": "current" if suite.evidence_current else "not_current",
            "scope": "release" if suite.release_required else "routine",
            "evidence": [suite.result_path or suite.not_run_reason],
            "owned_leaf_cell_ids": list(suite.owned_leaf_cell_ids),
            "background": suite.background,
            "progress_only": suite.progress_only,
            "has_exit_artifact": suite.has_exit_artifact,
            "has_result_artifact": suite.has_result_artifact,
            "timeout_seconds": suite.timeout_seconds,
            "duration_seconds": suite.duration_seconds,
            "stale_reasons": list(suite.stale_reasons),
            "nonpass_reasons": _suite_nonpass_reasons(suite),
            "test_count": suite.test_count,
            "selected_count": suite.selected_count,
            "proof_artifact": suite.proof_artifact.to_dict() if suite.proof_artifact else None,
        }
        for suite in plan.child_suites
    ]
    return {
        "result_type": "flowpilot_acceptance_testmesh_checks",
        "model_id": model.TESTMESH_ID,
        "ok": report.ok and not missing_cells and routine_router_gate_ok,
        "mode": "release" if release_gate_ok else "routine",
        "report": _to_jsonable(report),
        "required_payload_cells": list(model.PAYLOAD_CELLS),
        "payload_cell_owners": {cell_id: list(suite_ids) for cell_id, suite_ids in owners.items()},
        "release_evidence_cells": list(model.RELEASE_EVIDENCE_CELLS),
        "release_evidence_cell_owners": {
            cell_id: list(suite_ids) for cell_id, suite_ids in release_evidence_owners.items()
        },
        "missing_payload_cells": missing_cells,
        "router_tier_mappings": list(model.ROUTER_TIER_MAPPINGS),
        "router_tier_background_details": router_tier_background_details,
        "routine_router_gate": {
            "ok": routine_router_gate_ok,
            "required_suites": [suite.suite_id for suite in routine_router_rows],
            "nonpassing_suites": [
                {
                    "suite_id": suite.suite_id,
                    "status": suite.result_status,
                    "nonpass_reasons": _suite_nonpass_reasons(suite),
                    "background": suite.background,
                    "progress_only": suite.progress_only,
                    "has_exit_artifact": suite.has_exit_artifact,
                    "has_result_artifact": suite.has_result_artifact,
                    "result_path": suite.result_path or suite.not_run_reason,
                }
                for suite in routine_router_rows
                if suite.result_status != "passed"
                or not suite.evidence_current
                or suite.exit_code != 0
                or suite.progress_only
                or not suite.has_exit_artifact
                or not suite.has_result_artifact
            ],
        },
        "release_gate": {
            "ok": release_gate_ok,
            "release_evidence_requested": release_evidence,
            "required_suites": [suite.suite_id for suite in release_rows],
            "deferred_suites": [
                {
                    "suite_id": suite.suite_id,
                    "status": suite.result_status,
                    "reason": suite.not_run_reason,
                    "nonpass_reasons": _suite_nonpass_reasons(suite),
                    "background": suite.background,
                    "progress_only": suite.progress_only,
                    "has_exit_artifact": suite.has_exit_artifact,
                    "has_result_artifact": suite.has_result_artifact,
                    "stale_reasons": list(suite.stale_reasons),
                }
                for suite in release_rows
                if suite.result_status != "passed" or not suite.evidence_current
                or suite.progress_only
                or not suite.has_exit_artifact
                or not suite.has_result_artifact
            ],
        },
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": report.ok and not missing_cells and routine_router_gate_ok},
            "release_gate": {"ok": release_gate_ok},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--release-evidence", action="store_true")
    parser.add_argument("--release-result-status", choices=("passed", "failed", "timeout", "progress_only", "not_run"))
    parser.add_argument("--release-progress-only", action="store_true")
    parser.add_argument("--release-background", action="store_true")
    parser.add_argument("--release-missing-exit-artifact", action="store_true")
    parser.add_argument("--release-missing-result-artifact", action="store_true")
    parser.add_argument("--release-timeout-seconds", type=float)
    parser.add_argument("--release-stale-reason", action="append", default=[])
    parser.add_argument("--release-result-path", default="tmp/test_background acceptance tier artifacts")
    parser.add_argument("--router-quality-background-dir", type=Path)
    parser.add_argument("--router-packets-background-dir", type=Path)
    parser.add_argument("--router-route-background-dir", type=Path)
    parser.add_argument("--router-terminal-background-dir", type=Path)
    parser.add_argument("--evidence-manifest", type=Path)
    args = parser.parse_args()

    evidence_manifest: dict[str, Any] = {}
    if args.evidence_manifest:
        evidence_manifest = json.loads(args.evidence_manifest.read_text(encoding="utf-8"))

    release_manifest_row = evidence_manifest.get("release") or {}
    result = run_checks(
        release_evidence=args.release_evidence,
        release_result_status=args.release_result_status,
        release_evidence_current=False if args.release_stale_reason else None,
        release_progress_only=args.release_progress_only,
        release_background=args.release_background,
        release_has_exit_artifact=not args.release_missing_exit_artifact,
        release_has_result_artifact=not args.release_missing_result_artifact,
        release_timeout_seconds=args.release_timeout_seconds,
        release_stale_reasons=tuple(args.release_stale_reason),
        release_result_path=args.release_result_path,
        router_quality_background_dir=args.router_quality_background_dir,
        router_packets_background_dir=args.router_packets_background_dir,
        router_route_background_dir=args.router_route_background_dir,
        router_terminal_background_dir=args.router_terminal_background_dir,
        routine_evidence_overrides=dict(evidence_manifest.get("routine") or {}),
        release_proof_artifact=release_manifest_row.get("proof_artifact"),
        release_test_count=release_manifest_row.get("test_count"),
        release_selected_count=release_manifest_row.get("selected_count"),
    )
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
