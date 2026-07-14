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
from test_tier.source_fingerprint import source_fingerprint


DEFAULT_OUT = ROOT / "simulations" / "flowpilot_acceptance_testmesh_evidence_manifest.json"
MANIFEST_SCHEMA_VERSION = "flowpilot.acceptance_testmesh_evidence_manifest.v3"


def _portable_path(path: Path) -> str:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{resolved.parent.name}/{resolved.name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _supervisor_paths(root: Path, tier: str) -> tuple[Path, Path]:
    base = root / f"{tier}_background_supervisor"
    return base.with_suffix(".meta.json"), base.with_suffix(".exit.txt")


def _validated_tier(
    root: Path,
    tier: str,
    *,
    expected_source_fingerprint: str,
) -> dict[str, Any]:
    meta_path, exit_path = _supervisor_paths(root, tier)
    if not meta_path.is_file() or not exit_path.is_file():
        raise ValueError(f"{tier} background supervisor artifacts are incomplete under {root}")
    meta = _json(meta_path)
    try:
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise ValueError(f"invalid exit artifact: {exit_path}") from exc
    if meta.get("status") != "passed" or exit_code != 0 or meta.get("timed_out") is True:
        raise ValueError(f"{tier} background tier is not a current pass: {meta}")
    source_start = str(meta.get("covered_source_fingerprint_start") or "")
    source_end = str(meta.get("covered_source_fingerprint_end") or "")
    if (
        not source_start
        or source_start != source_end
        or source_end != expected_source_fingerprint
        or meta.get("source_fingerprint_current") is not True
    ):
        raise ValueError(
            f"{tier} background tier source fingerprint is missing or stale: "
            f"start={source_start!r} end={source_end!r} "
            f"expected={expected_source_fingerprint!r}"
        )
    child_meta_paths = sorted(
        path
        for path in root.glob("*.meta.json")
        if path != meta_path and "background_supervisor" not in path.name
    )
    child_exit_paths = sorted(
        path
        for path in root.glob("*.exit.txt")
        if path != exit_path and "background_supervisor" not in path.name
    )
    child_rows = [_json(path) for path in child_meta_paths]
    failed = [
        row.get("name")
        for row in child_rows
        if row.get("status") != "passed"
        or row.get("exit_code") != 0
        or str(row.get("covered_source_fingerprint") or "") != source_start
    ]
    if failed:
        raise ValueError(f"{tier} contains non-passing child artifacts: {failed}")
    if len(child_meta_paths) != len(child_exit_paths):
        raise ValueError(f"{tier} child meta/exit cardinality mismatch")
    return {
        "tier": tier,
        "root": root,
        "meta": meta,
        "meta_path": meta_path,
        "exit_path": exit_path,
        "child_meta_paths": child_meta_paths,
        "child_exit_paths": child_exit_paths,
        "selected_count": len(child_meta_paths),
        "executed_count": len(child_rows),
        "covered_source_fingerprint_start": source_start,
        "covered_source_fingerprint_end": source_end,
    }


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
    source_digest: str,
) -> dict[str, Any]:
    artifacts: list[Path] = []
    for report in tier_reports:
        artifacts.extend((report["meta_path"], report["exit_path"]))
        artifacts.extend(report["child_meta_paths"])
        artifacts.extend(report["child_exit_paths"])
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
            "source_fingerprint": source_digest,
            "tier_source_fingerprint_starts": [
                report["covered_source_fingerprint_start"] for report in tier_reports
            ],
            "tier_source_fingerprint_ends": [
                report["covered_source_fingerprint_end"] for report in tier_reports
            ],
            "selected_child_command_count": sum(report["selected_count"] for report in tier_reports),
            "executed_child_command_count": sum(report["executed_count"] for report in tier_reports),
            "count_unit": "background_child_commands",
            "tiers": [report["tier"] for report in tier_reports],
            "covered_tiers": [report["tier"] for report in tier_reports],
        },
    }


def _suite_tier_report(
    all_report: dict[str, Any],
    *,
    suite_id: str,
    expected_names: tuple[str, ...],
) -> dict[str, Any]:
    meta_by_name: dict[str, Path] = {}
    for meta_path in all_report["child_meta_paths"]:
        name = str(_json(meta_path).get("name") or "")
        if not name:
            raise ValueError(f"all-tier child metadata has no command name: {meta_path}")
        if name in meta_by_name:
            raise ValueError(f"all-tier child command name is duplicated: {name}")
        meta_by_name[name] = meta_path
    exit_by_name = {
        path.name[: -len(".exit.txt")]: path
        for path in all_report["child_exit_paths"]
        if path.name.endswith(".exit.txt")
    }
    missing = [
        name
        for name in expected_names
        if name not in meta_by_name or name not in exit_by_name
    ]
    if missing:
        raise ValueError(
            f"{suite_id} is missing current all-tier child evidence: {missing}"
        )
    nonzero = [
        name
        for name in expected_names
        if int(exit_by_name[name].read_text(encoding="utf-8").strip()) != 0
    ]
    if nonzero:
        raise ValueError(f"{suite_id} contains non-passing exit artifacts: {nonzero}")
    subset = dict(all_report)
    subset["child_meta_paths"] = [meta_by_name[name] for name in expected_names]
    subset["child_exit_paths"] = [exit_by_name[name] for name in expected_names]
    subset["selected_count"] = len(expected_names)
    subset["executed_count"] = len(expected_names)
    return subset


def _compile_routine_evidence(
    *,
    all_report: dict[str, Any],
    plan: Any,
    source_digest: str,
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
            source_digest=source_digest,
        )
        routine[suite.suite_id] = {
            "result_status": "passed",
            "evidence_tier": "external_contract",
            "evidence_current": True,
            "test_count": int(proof["metadata"]["executed_child_command_count"]),
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
            "proof_artifact": proof,
            **testmesh_final_receipt_fields(
                proof,
                covered_obligation_ids=covered_ids,
            ),
        }
    return routine


def compile_manifest(
    *,
    all_root: Path,
    adversarial_root: Path,
    release_root: Path,
) -> dict[str, Any]:
    source_digest = source_fingerprint()
    all_report = _validated_tier(
        all_root,
        "all",
        expected_source_fingerprint=source_digest,
    )
    release_report = _validated_tier(
        release_root,
        "release",
        expected_source_fingerprint=source_digest,
    )
    adversarial_report = _validated_tier(
        adversarial_root,
        "formal-submit-adversarial",
        expected_source_fingerprint=source_digest,
    )
    portable_roots = (
        _portable_path(all_root),
        _portable_path(adversarial_root),
        _portable_path(release_root),
    )
    combined_result_path = "; ".join(portable_roots)
    plan = model.build_testmesh_plan()
    routine = _compile_routine_evidence(
        all_report=all_report,
        plan=plan,
        source_digest=source_digest,
        artifact_prefix="proof",
    )
    release_proof = _proof(
        artifact_id="proof.acceptance_router_release_tiers",
        command=(
            "python scripts/run_test_tier.py --tier all --background; "
            "python scripts/run_test_tier.py --tier formal-submit-adversarial --background; "
            "python scripts/run_test_tier.py --tier release --background"
        ),
        result_path=combined_result_path,
        tier_reports=(all_report, adversarial_report, release_report),
        covered_ids=tuple(model.RELEASE_EVIDENCE_CELLS),
        source_digest=source_digest,
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "phase": "final",
        "claim_scope": "release",
        "source_fingerprint": source_digest,
        "routine": routine,
        "release": {
            "result_status": "passed",
            "evidence_current": True,
            "test_count": int(release_proof["metadata"]["executed_child_command_count"]),
            "selected_count": int(release_proof["metadata"]["selected_child_command_count"]),
            "result_path": combined_result_path,
            "proof_artifact": release_proof,
            **testmesh_final_receipt_fields(
                release_proof,
                covered_obligation_ids=tuple(model.RELEASE_EVIDENCE_CELLS),
            ),
        },
    }


def compile_bootstrap_manifest(*, all_root: Path, adversarial_root: Path) -> dict[str, Any]:
    """Compile Phase-A current routine proof without inventing release evidence."""

    source_digest = source_fingerprint()
    all_report = _validated_tier(
        all_root,
        "all",
        expected_source_fingerprint=source_digest,
    )
    adversarial_report = _validated_tier(
        adversarial_root,
        "formal-submit-adversarial",
        expected_source_fingerprint=source_digest,
    )
    portable_adversarial_root = _portable_path(adversarial_root)
    plan = model.build_testmesh_plan()
    routine = _compile_routine_evidence(
        all_report=all_report,
        plan=plan,
        source_digest=source_digest,
        artifact_prefix="proof.bootstrap",
    )
    adversarial_proof = _proof(
        artifact_id="proof.bootstrap.formal_submit_adversarial",
        command="python scripts/run_test_tier.py --tier formal-submit-adversarial --background",
        result_path=portable_adversarial_root,
        tier_reports=(adversarial_report,),
        covered_ids=("formal-submit-adversarial",),
        source_digest=source_digest,
    )
    routine["formal_submit_adversarial"] = {
        "result_status": "passed",
        "evidence_current": True,
        "test_count": int(adversarial_proof["metadata"]["executed_child_command_count"]),
        "selected_count": int(adversarial_proof["metadata"]["selected_child_command_count"]),
        "result_reused": False,
        "proof_artifact": adversarial_proof,
        **testmesh_final_receipt_fields(
            adversarial_proof,
            covered_obligation_ids=("formal-submit-adversarial",),
        ),
    }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "phase": "bootstrap",
        "claim_scope": "routine",
        "source_fingerprint": source_digest,
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
    parser.add_argument("--phase", choices=("bootstrap", "final"), default="final")
    parser.add_argument("--all-root", type=Path, required=True)
    parser.add_argument("--adversarial-root", type=Path)
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.phase == "bootstrap":
        if args.adversarial_root is None:
            parser.error("--adversarial-root is required for --phase bootstrap")
        manifest = compile_bootstrap_manifest(
            all_root=args.all_root.resolve(),
            adversarial_root=args.adversarial_root.resolve(),
        )
    else:
        if args.adversarial_root is None or args.release_root is None:
            parser.error("--adversarial-root and --release-root are required for --phase final")
        manifest = compile_manifest(
            all_root=args.all_root.resolve(),
            adversarial_root=args.adversarial_root.resolve(),
            release_root=args.release_root.resolve(),
        )
    output = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
