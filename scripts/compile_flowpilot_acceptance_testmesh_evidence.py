"""Compile current background-tier artifacts into FlowGuard TestMesh proof evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from simulations import flowpilot_acceptance_testmesh_model as model
from simulations.flowpilot_evidence_truth import (
    testmesh_final_receipt_fields,
    testmesh_receipt_obligation_ids,
)
from simulations.run_flowpilot_acceptance_testmesh_checks import BACKGROUND_CHILD_SUITES
from test_tier.checkpoint_manifest import (
    compile_owner_checkpoint_manifest as _compile_owner_checkpoint_manifest,
)
from test_tier.evidence_validation import validated_tier
from test_tier.source_fingerprint import source_fingerprint, source_snapshot


DEFAULT_OUT = ROOT / "simulations" / "flowpilot_acceptance_testmesh_evidence_manifest.json"
MANIFEST_SCHEMA_VERSION = "flowpilot.acceptance_testmesh_evidence_manifest.v5"


def _portable_path(path: Path) -> str:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{resolved.parent.name}/{resolved.name}"


def _portable_artifact_ref(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    portable = dict(value)
    path = portable.get("path")
    if isinstance(path, str) and path:
        portable["path"] = _portable_path(Path(path))
    return portable


def _portable_owner_row(value: dict[str, Any]) -> dict[str, Any]:
    portable = dict(value)
    for field_name in ("proof_ref", "reuse_ticket_ref"):
        if field_name in portable:
            portable[field_name] = _portable_artifact_ref(portable[field_name])
    return portable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprints(paths: Iterable[Path]) -> dict[str, str]:
    return {
        _portable_path(path): _sha256(path)
        for path in paths
        if path.is_file()
    }


def _proof(
    *,
    artifact_id: str,
    command: str,
    result_path: str,
    tier_reports: tuple[dict[str, Any], ...],
    covered_ids: tuple[str, ...],
    snapshot_fingerprint: str,
) -> dict[str, Any]:
    artifacts: list[Path] = []
    for report in tier_reports:
        artifacts.extend(
            (
                report["meta_path"],
                report["exit_path"],
                report["impact_plan_path"],
                report["owner_index_path"],
            )
        )
    started = min(str(report["meta"].get("start_time") or "") for report in tier_reports)
    finished = max(str(report["meta"].get("end_time") or "") for report in tier_reports)
    return {
        "artifact_id": artifact_id,
        "producer_route": "flowguard-test-mesh",
        "command": command,
        "result_path": result_path,
        "result_status": "passed",
        "exit_code": 0,
        "started_at": started,
        "finished_at": finished,
        "artifact_fingerprints": _fingerprints(artifacts),
        "covered_obligation_ids": list(covered_ids),
        "assertion_scope": "external_contract",
        "current": True,
        "route_evidence_current": True,
        "progress_only": False,
        "metadata": {
            "snapshot_fingerprint": snapshot_fingerprint,
            "impact_plan_ids": [
                report["impact_plan"]["plan_id"] for report in tier_reports
            ],
            "owner_proof_artifact_ids": sorted(
                str(row.get("proof_ref", {}).get("artifact_id") or "")
                for report in tier_reports
                for row in report["owners"].values()
                if isinstance(row, dict)
            ),
            "selected_child_command_count": sum(report["selected_count"] for report in tier_reports),
            "executed_child_command_count": sum(report["executed_count"] for report in tier_reports),
            "reused_child_command_count": sum(report["reused_count"] for report in tier_reports),
            "proof_backed_child_command_count": sum(
                report["executed_count"] + report["reused_count"]
                for report in tier_reports
            ),
            "count_unit": "background_child_commands",
            "tiers": [report["tier"] for report in tier_reports],
            "covered_tiers": [report["tier"] for report in tier_reports],
        },
    }


def compile_owner_checkpoint_manifest(*, all_root: Path) -> dict[str, Any]:
    """Public facade for the sole current checkpoint compiler owner."""

    return _compile_owner_checkpoint_manifest(
        all_root=all_root,
        schema_version=MANIFEST_SCHEMA_VERSION,
        portable_path=_portable_path,
        sha256=_sha256,
    )


def _suite_tier_report(
    all_report: dict[str, Any],
    *,
    suite_id: str,
    expected_names: tuple[str, ...],
) -> dict[str, Any]:
    owners = all_report["owners"]
    missing = [
        name
        for name in expected_names
        if name not in owners
    ]
    if missing:
        raise ValueError(
            f"{suite_id} is missing current all-tier child evidence: {missing}"
        )
    subset = dict(all_report)
    subset["owners"] = {name: owners[name] for name in expected_names}
    subset["child_meta_paths"] = [
        all_report["root"] / f"{name}.meta.json"
        for name in expected_names
        if (all_report["root"] / f"{name}.meta.json").is_file()
    ]
    subset["child_exit_paths"] = [
        all_report["root"] / f"{name}.exit.txt"
        for name in expected_names
        if (all_report["root"] / f"{name}.exit.txt").is_file()
    ]
    subset["selected_count"] = len(expected_names)
    subset["executed_count"] = sum(
        1 for name in expected_names if not owners[name].get("result_reused")
    )
    subset["reused_count"] = sum(
        1 for name in expected_names if owners[name].get("result_reused") is True
    )
    return subset


def _compile_routine_evidence(
    *,
    all_report: dict[str, Any],
    plan: Any,
    snapshot_fingerprint: str,
    artifact_prefix: str,
) -> dict[str, Any]:
    routine: dict[str, Any] = {}
    portable_all_root = _portable_path(all_report["root"])
    for suite in plan.child_suites:
        if suite.suite_id == "acceptance_router_release_tiers":
            continue
        proof_report = all_report
        child_config = BACKGROUND_CHILD_SUITES.get(suite.suite_id)
        if child_config is not None:
            proof_report = _suite_tier_report(
                all_report,
                suite_id=suite.suite_id,
                expected_names=tuple(child_config["expected"]),
            )
        covered_ids = testmesh_receipt_obligation_ids(plan, suite)
        proof = _proof(
            artifact_id=f"{artifact_prefix}.{suite.suite_id}",
            command="python scripts/run_test_tier.py --tier all --background",
            result_path=portable_all_root,
            tier_reports=(proof_report,),
            covered_ids=covered_ids,
            snapshot_fingerprint=snapshot_fingerprint,
        )
        routine[suite.suite_id] = {
            "result_status": "passed",
            "evidence_tier": "external_contract",
            "evidence_current": True,
            "test_count": int(proof["metadata"]["proof_backed_child_command_count"]),
            "selected_count": int(proof["metadata"]["selected_child_command_count"]),
            "skipped_count": 0,
            "skipped_visible": True,
            "exit_code": 0,
            "result_path": portable_all_root,
            "log_root": portable_all_root,
            "background": True,
            "has_exit_artifact": True,
            "has_result_artifact": True,
            "progress_only": False,
            "result_reused": False,
            "reuse_ticket": None,
            "owner_evidence_ids": sorted(proof_report["owners"]),
            "owner_ref_count": len(proof_report["owners"]),
            "reused_owner_ref_count": proof_report["reused_count"],
            "proof_artifact": proof,
            **testmesh_final_receipt_fields(
                proof,
                covered_obligation_ids=covered_ids,
            ),
        }
    return routine


def _compile_release_manifest(
    *,
    all_root: Path,
    adversarial_root: Path,
    release_root: Path,
    closure_root: Path | None,
    phase: str,
) -> dict[str, Any]:
    if phase not in {"preclosure", "final"}:
        raise ValueError(f"unsupported release manifest phase: {phase}")
    if (phase == "final") != (closure_root is not None):
        raise ValueError("final phase requires one evidence-closure root")
    snapshot = source_snapshot()
    snapshot_fingerprint = str(snapshot["fingerprint"])
    all_report = validated_tier(all_root, "all")
    release_report = validated_tier(release_root, "release")
    adversarial_report = validated_tier(
        adversarial_root,
        "formal-submit-adversarial",
    )
    closure_report = (
        validated_tier(closure_root, "evidence-closure")
        if closure_root is not None
        else None
    )
    tier_reports = tuple(
        report
        for report in (
            all_report,
            adversarial_report,
            release_report,
            closure_report,
        )
        if report is not None
    )
    portable_roots = tuple(
        _portable_path(report["root"])
        for report in tier_reports
    )
    combined_result_path = "; ".join(portable_roots)
    plan = model.build_testmesh_plan()
    routine = _compile_routine_evidence(
        all_report=all_report,
        plan=plan,
        snapshot_fingerprint=snapshot_fingerprint,
        artifact_prefix="proof",
    )
    release_proof = _proof(
        artifact_id="proof.acceptance_router_release_tiers",
        command=(
            "python scripts/run_test_tier.py --tier all --background; "
            "python scripts/run_test_tier.py --tier formal-submit-adversarial --background; "
            "python scripts/run_test_tier.py --tier release --background"
            + (
                "; python scripts/run_test_tier.py --tier evidence-closure --background"
                if closure_report is not None
                else ""
            )
        ),
        result_path=combined_result_path,
        tier_reports=tier_reports,
        covered_ids=tuple(model.RELEASE_EVIDENCE_CELLS),
        snapshot_fingerprint=snapshot_fingerprint,
    )
    owners: dict[str, Any] = {}
    for report in tier_reports:
        for owner_id, row in report["owners"].items():
            portable_row = _portable_owner_row(row)
            if owner_id in owners and owners[owner_id] != portable_row:
                raise ValueError(f"conflicting owner evidence row: {owner_id}")
            owners[owner_id] = portable_row
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "phase": phase,
        "claim_scope": "release",
        "snapshot": snapshot,
        "impact_plan_refs": [
            _portable_artifact_ref(report["meta"].get("impact_plan_ref") or {})
            for report in tier_reports
        ],
        "owners": owners,
        "routine": routine,
        "release": {
            "result_status": "passed",
            "evidence_current": True,
            "test_count": int(release_proof["metadata"]["proof_backed_child_command_count"]),
            "selected_count": int(release_proof["metadata"]["selected_child_command_count"]),
            "result_path": combined_result_path,
            "result_reused": False,
            "reuse_ticket": None,
            "owner_evidence_ids": sorted(owners),
            "owner_ref_count": len(owners),
            "reused_owner_ref_count": sum(
                1 for row in owners.values() if row.get("result_reused") is True
            ),
            "proof_artifact": release_proof,
            **testmesh_final_receipt_fields(
                release_proof,
                covered_obligation_ids=tuple(model.RELEASE_EVIDENCE_CELLS),
            ),
        },
    }


def compile_preclosure_manifest(
    *,
    all_root: Path,
    adversarial_root: Path,
    release_root: Path,
) -> dict[str, Any]:
    """Compile the exact prerequisite evidence consumed by closure owners."""

    return _compile_release_manifest(
        all_root=all_root,
        adversarial_root=adversarial_root,
        release_root=release_root,
        closure_root=None,
        phase="preclosure",
    )


def compile_manifest(
    *,
    all_root: Path,
    adversarial_root: Path,
    release_root: Path,
    closure_root: Path,
) -> dict[str, Any]:
    """Compile final evidence including every exact strict-parent owner."""

    return _compile_release_manifest(
        all_root=all_root,
        adversarial_root=adversarial_root,
        release_root=release_root,
        closure_root=closure_root,
        phase="final",
    )


def compile_bootstrap_manifest(*, all_root: Path, adversarial_root: Path) -> dict[str, Any]:
    """Compile Phase-A current routine proof without inventing release evidence."""

    snapshot = source_snapshot()
    snapshot_fingerprint = str(snapshot["fingerprint"])
    all_report = validated_tier(all_root, "all")
    adversarial_report = validated_tier(
        adversarial_root,
        "formal-submit-adversarial",
    )
    portable_adversarial_root = _portable_path(adversarial_root)
    plan = model.build_testmesh_plan()
    routine = _compile_routine_evidence(
        all_report=all_report,
        plan=plan,
        snapshot_fingerprint=snapshot_fingerprint,
        artifact_prefix="proof.bootstrap",
    )
    adversarial_proof = _proof(
        artifact_id="proof.bootstrap.formal_submit_adversarial",
        command="python scripts/run_test_tier.py --tier formal-submit-adversarial --background",
        result_path=portable_adversarial_root,
        tier_reports=(adversarial_report,),
        covered_ids=("formal-submit-adversarial",),
        snapshot_fingerprint=snapshot_fingerprint,
    )
    routine["formal_submit_adversarial"] = {
        "result_status": "passed",
        "evidence_current": True,
        "test_count": int(adversarial_proof["metadata"]["proof_backed_child_command_count"]),
        "selected_count": int(adversarial_proof["metadata"]["selected_child_command_count"]),
        "result_reused": False,
        "reuse_ticket": None,
        "owner_evidence_ids": sorted(adversarial_report["owners"]),
        "owner_ref_count": len(adversarial_report["owners"]),
        "reused_owner_ref_count": adversarial_report["reused_count"],
        "proof_artifact": adversarial_proof,
        **testmesh_final_receipt_fields(
            adversarial_proof,
            covered_obligation_ids=("formal-submit-adversarial",),
        ),
    }
    owners = {
        **{
            owner_id: _portable_owner_row(row)
            for owner_id, row in all_report["owners"].items()
        },
        **{
            owner_id: _portable_owner_row(row)
            for owner_id, row in adversarial_report["owners"].items()
        },
    }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "phase": "bootstrap",
        "claim_scope": "routine",
        "snapshot": snapshot,
        "impact_plan_refs": [
            _portable_artifact_ref(report["meta"].get("impact_plan_ref") or {})
            for report in (all_report, adversarial_report)
        ],
        "owners": owners,
        "routine": routine,
        "release": {
            "result_status": "not_run",
            "evidence_current": False,
            "test_count": 0,
            "selected_count": 0,
            "result_path": "",
            "proof_artifact": None,
            "not_run_reason": "release evidence is not an input to the bootstrap manifest",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("checkpoint", "bootstrap", "preclosure", "final"),
        default="final",
    )
    parser.add_argument("--all-root", type=Path, required=True)
    parser.add_argument("--adversarial-root", type=Path)
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--closure-root", type=Path)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.phase == "checkpoint":
        if (
            args.adversarial_root is not None
            or args.release_root is not None
            or args.closure_root is not None
        ):
            parser.error(
                "--adversarial-root, --release-root, and --closure-root "
                "are forbidden for --phase checkpoint"
            )
        manifest = compile_owner_checkpoint_manifest(
            all_root=args.all_root.resolve(),
        )
    elif args.phase == "bootstrap":
        if args.adversarial_root is None:
            parser.error("--adversarial-root is required for --phase bootstrap")
        manifest = compile_bootstrap_manifest(
            all_root=args.all_root.resolve(),
            adversarial_root=args.adversarial_root.resolve(),
        )
    elif args.phase == "preclosure":
        if args.adversarial_root is None or args.release_root is None:
            parser.error(
                "--adversarial-root and --release-root are required for --phase preclosure"
            )
        if args.closure_root is not None:
            parser.error("--closure-root is forbidden for --phase preclosure")
        manifest = compile_preclosure_manifest(
            all_root=args.all_root.resolve(),
            adversarial_root=args.adversarial_root.resolve(),
            release_root=args.release_root.resolve(),
        )
    else:
        if (
            args.adversarial_root is None
            or args.release_root is None
            or args.closure_root is None
        ):
            parser.error(
                "--adversarial-root, --release-root, and --closure-root "
                "are required for --phase final"
            )
        manifest = compile_manifest(
            all_root=args.all_root.resolve(),
            adversarial_root=args.adversarial_root.resolve(),
            release_root=args.release_root.resolve(),
            closure_root=args.closure_root.resolve(),
        )
    output = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
