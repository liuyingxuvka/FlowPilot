"""Read-only FlowPilot retention reporting plus explicit frozen archive apply."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.flowpilot_runtime_retention_lib.common import (  # noqa: E402
    APPLY_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    ROOT,
    RUN_HEAVY_DIRECTORIES,
    RetentionPlanError,
    _project_relative,
    _read_json_result,
    _sha256_bytes,
    _sha256_file,
    _tree_fingerprint,
    _utc_now,
)
from scripts.flowpilot_runtime_retention_lib.scan import build_report  # noqa: E402


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def build_plan(
    project_root: Path = ROOT,
    *,
    max_runs: int = 30,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    report = build_report(root, max_runs=max_runs, max_age_days=max_age_days)
    candidates: list[dict[str, Any]] = []
    for record in report["stale_candidates"]:
        candidate = root / record["path"]
        snapshot = {
            key: record[key]
            for key in (
                "kind",
                "entry_id",
                "run_id",
                "path",
                "timestamp",
                "bytes",
                "file_count",
                "terminal_evidence_refs",
                "selection_reasons",
            )
        }
        snapshot["source_fingerprint"] = _tree_fingerprint(candidate)
        snapshot["heavy_paths"] = (
            [
                name
                for name in RUN_HEAVY_DIRECTORIES
                if (candidate / name).is_dir()
            ]
            if record["kind"] == "run"
            else ["."]
        )
        candidates.append(snapshot)
    index_path = root / ".flowpilot" / "index.json"
    body: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project_root": str(root),
        "policy": {
            "max_runs": max_runs,
            "max_age_days": max_age_days,
        },
        "index_path": _project_relative(root, index_path),
        "index_sha256": _sha256_file(index_path) if index_path.is_file() else None,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    body["plan_id"] = f"retention-{_sha256_bytes(_canonical_bytes(body))[:24]}"
    return body


def _atomic_write_bytes(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
            tmp_path = Path(handle.name)
        tmp_path.replace(path)
        if path.read_bytes() != body:
            raise RetentionPlanError(f"atomic write read-back mismatch: {path}")
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def write_plan(path: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    body = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    _atomic_write_bytes(path, body)
    return {
        "plan_path": str(path.resolve()),
        "plan_sha256": _sha256_bytes(body),
        "plan_id": plan["plan_id"],
        "candidate_count": plan["candidate_count"],
    }


def _candidate_path(root: Path, snapshot: Mapping[str, Any]) -> Path:
    raw = snapshot.get("path")
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise RetentionPlanError("retention plan candidate path must be project-relative")
    candidate = (root / raw).resolve()
    kind = str(snapshot.get("kind") or "")
    expected_parent = (
        root / ".flowpilot" / "runs"
        if kind == "run"
        else root / "tmp" / "test_background"
        if kind == "test_background"
        else None
    )
    if expected_parent is None or candidate.parent != expected_parent.resolve():
        raise RetentionPlanError(f"retention candidate escapes its exact owner root: {candidate}")
    if candidate.name != str(snapshot.get("entry_id") or ""):
        raise RetentionPlanError(f"retention candidate id/path mismatch: {candidate}")
    return candidate


def _archive_path(root: Path, snapshot: Mapping[str, Any]) -> Path:
    entry_id = str(snapshot["entry_id"])
    safe_id = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in entry_id)
    name = f"{safe_id}.zip" if snapshot["kind"] == "run" else f"test-background-{safe_id}.zip"
    return root / ".flowpilot" / "archives" / name


def _create_verified_archive(
    root: Path,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    source = _candidate_path(root, snapshot)
    if _tree_fingerprint(source) != snapshot.get("source_fingerprint"):
        raise RetentionPlanError(f"retention candidate changed after planning: {source}")
    archive_path = _archive_path(root, snapshot)
    if archive_path.exists():
        raise RetentionPlanError(f"archive target already exists: {archive_path}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = archive_path.with_name(f".{archive_path.name}.{os.getpid()}.tmp")
    expected: dict[str, str] = {}
    try:
        with zipfile.ZipFile(
            tmp_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            for child in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
                if child.is_symlink():
                    raise RetentionPlanError(f"retention candidate contains a symlink: {child}")
                if not child.is_file():
                    continue
                member = f"{source.name}/{child.relative_to(source).as_posix()}"
                expected[member] = _sha256_file(child)
                archive.write(child, member)
        with zipfile.ZipFile(tmp_path, "r") as archive:
            if archive.testzip() is not None:
                raise RetentionPlanError(f"archive read-back CRC failed: {tmp_path}")
            if set(archive.namelist()) != set(expected):
                raise RetentionPlanError(f"archive member inventory mismatch: {tmp_path}")
            for member, expected_hash in expected.items():
                digest = hashlib.sha256()
                with archive.open(member, "r") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != expected_hash:
                    raise RetentionPlanError(f"archive member hash mismatch: {member}")
        if _tree_fingerprint(source) != snapshot.get("source_fingerprint"):
            raise RetentionPlanError(f"retention candidate changed during archive creation: {source}")
        tmp_path.replace(archive_path)
        archive_sha256 = _sha256_file(archive_path)
        with zipfile.ZipFile(archive_path, "r") as archive:
            if archive.testzip() is not None:
                raise RetentionPlanError(f"committed archive read-back failed: {archive_path}")
        return {
            "kind": snapshot["kind"],
            "entry_id": snapshot["entry_id"],
            "source_path": snapshot["path"],
            "archive_path": _project_relative(root, archive_path),
            "archive_sha256": archive_sha256,
            "archive_bytes": archive_path.stat().st_size,
            "member_count": len(expected),
            "source_fingerprint": snapshot["source_fingerprint"],
            "heavy_paths": list(snapshot.get("heavy_paths") or []),
        }
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _updated_index(
    index: Mapping[str, Any],
    archives: list[dict[str, Any]],
    *,
    archived_at: str,
) -> dict[str, Any]:
    updated = json.loads(json.dumps(index, sort_keys=True))
    runs = updated.get("runs")
    if not isinstance(runs, list):
        raise RetentionPlanError("run index is missing its current runs array")
    by_run = {
        str(item.get("run_id") or ""): item
        for item in runs
        if isinstance(item, dict) and item.get("run_id")
    }
    validation_archives = updated.setdefault("validation_archives", [])
    if not isinstance(validation_archives, list):
        raise RetentionPlanError("run index validation_archives must be an array")
    existing_validation_ids = {
        str(item.get("entry_id") or "")
        for item in validation_archives
        if isinstance(item, dict)
    }
    for archive in archives:
        fields = {
            "archive_status": "verified",
            "archive_cleanup_status": "pending",
            "archive_path": archive["archive_path"],
            "archive_sha256": archive["archive_sha256"],
            "archived_at": archived_at,
            "archive_source_fingerprint": archive["source_fingerprint"],
        }
        if archive["kind"] == "run":
            row = by_run.get(str(archive["entry_id"]))
            if row is None:
                raise RetentionPlanError(f"run index lost candidate: {archive['entry_id']}")
            row.update(fields)
        else:
            if archive["entry_id"] in existing_validation_ids:
                raise RetentionPlanError(
                    f"validation archive identity already exists: {archive['entry_id']}"
                )
            validation_archives.append(
                {
                    "entry_id": archive["entry_id"],
                    "source_path": archive["source_path"],
                    **fields,
                }
            )
    return updated


def _mark_cleanup(
    index: Mapping[str, Any],
    archives: list[dict[str, Any]],
    *,
    cleanup_status: str,
    cleanup_errors: list[str],
) -> dict[str, Any]:
    updated = json.loads(json.dumps(index, sort_keys=True))
    run_rows = {
        str(item.get("run_id") or ""): item
        for item in updated.get("runs", [])
        if isinstance(item, dict)
    }
    validation_rows = {
        str(item.get("entry_id") or ""): item
        for item in updated.get("validation_archives", [])
        if isinstance(item, dict)
    }
    for archive in archives:
        row = (
            run_rows.get(str(archive["entry_id"]))
            if archive["kind"] == "run"
            else validation_rows.get(str(archive["entry_id"]))
        )
        if row is None:
            raise RetentionPlanError(f"archive cleanup index row is missing: {archive['entry_id']}")
        row["archive_cleanup_status"] = cleanup_status
        row["archive_cleanup_errors"] = cleanup_errors
    return updated


def _write_index(path: Path, payload: Mapping[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    _atomic_write_bytes(path, body)
    parsed, error = _read_json_result(path)
    if error or parsed != payload:
        raise RetentionPlanError(f"run index read-back mismatch: {path}")
    return body


def _remove_archived_heavy_paths(
    root: Path,
    snapshot: Mapping[str, Any],
) -> list[str]:
    source = _candidate_path(root, snapshot)
    removed: list[str] = []
    for raw in snapshot.get("heavy_paths") or []:
        if raw == ".":
            shutil.rmtree(source)
            removed.append(snapshot["path"])
            break
        target = (source / str(raw)).resolve()
        if target.parent != source or not target.is_dir():
            continue
        shutil.rmtree(target)
        removed.append(_project_relative(root, target))
    return removed


def apply_plan(
    project_root: Path,
    *,
    plan_path: Path,
    plan_sha256: str,
) -> dict[str, Any]:
    root = project_root.resolve()
    raw_plan = plan_path.read_bytes()
    actual_plan_sha256 = _sha256_bytes(raw_plan)
    if actual_plan_sha256 != plan_sha256:
        raise RetentionPlanError("retention plan SHA-256 does not match the supplied plan")
    try:
        plan = json.loads(raw_plan.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetentionPlanError("retention plan is not valid UTF-8 JSON") from exc
    if not isinstance(plan, dict) or plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise RetentionPlanError("retention plan does not use the current plan contract")
    if plan.get("project_root") != str(root):
        raise RetentionPlanError("retention plan project root does not match apply root")
    policy = plan.get("policy")
    if not isinstance(policy, dict):
        raise RetentionPlanError("retention plan policy is missing")
    max_runs = policy.get("max_runs")
    max_age_days = policy.get("max_age_days")
    if not isinstance(max_runs, int) or max_runs < 0:
        raise RetentionPlanError("retention plan max_runs is invalid")
    if max_age_days is not None and (not isinstance(max_age_days, int) or max_age_days < 0):
        raise RetentionPlanError("retention plan max_age_days is invalid")
    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or plan.get("candidate_count") != len(candidates):
        raise RetentionPlanError("retention plan candidate inventory is invalid")

    index_path = root / ".flowpilot" / "index.json"
    if not index_path.is_file() or _sha256_file(index_path) != plan.get("index_sha256"):
        raise RetentionPlanError("run index changed after retention planning")
    report = build_report(root, max_runs=max_runs, max_age_days=max_age_days)
    current = {
        (record["kind"], record["entry_id"]): record
        for record in report["records"]
    }
    for snapshot in candidates:
        if not isinstance(snapshot, dict):
            raise RetentionPlanError("retention plan candidate must be an object")
        record = current.get((snapshot.get("kind"), snapshot.get("entry_id")))
        if (
            record is None
            or record.get("path") != snapshot.get("path")
            or record.get("eligible") is not True
            or record.get("proposed_action") != "archive"
            or record.get("protected_reasons")
        ):
            raise RetentionPlanError(
                f"retention candidate is no longer eligible: {snapshot.get('entry_id')}"
            )
        source = _candidate_path(root, snapshot)
        if _tree_fingerprint(source) != snapshot.get("source_fingerprint"):
            raise RetentionPlanError(
                f"retention candidate changed after planning: {snapshot.get('entry_id')}"
            )

    original_index_bytes = index_path.read_bytes()
    original_index, index_error = _read_json_result(index_path)
    if index_error or original_index is None:
        raise RetentionPlanError("run index is not valid current authority")
    archives: list[dict[str, Any]] = []
    committed_paths: list[Path] = []
    try:
        for snapshot in candidates:
            archive = _create_verified_archive(root, snapshot)
            archives.append(archive)
            committed_paths.append(root / archive["archive_path"])
        archived_at = _utc_now()
        pending_index = _updated_index(original_index, archives, archived_at=archived_at)
        _write_index(index_path, pending_index)
    except Exception:
        if index_path.exists() and index_path.read_bytes() != original_index_bytes:
            _atomic_write_bytes(index_path, original_index_bytes)
        for archive_path in committed_paths:
            if archive_path.exists():
                archive_path.unlink()
        raise

    removed_paths: list[str] = []
    cleanup_errors: list[str] = []
    for snapshot in candidates:
        try:
            removed_paths.extend(_remove_archived_heavy_paths(root, snapshot))
        except OSError as exc:
            cleanup_errors.append(f"{snapshot.get('entry_id')}:{type(exc).__name__}:{exc}")
    cleanup_status = "complete" if not cleanup_errors else "incomplete"
    current_index, index_error = _read_json_result(index_path)
    if index_error or current_index is None:
        raise RetentionPlanError("run index became unreadable after archive commit")
    cleanup_index = _mark_cleanup(
        current_index,
        archives,
        cleanup_status=cleanup_status,
        cleanup_errors=cleanup_errors,
    )
    _write_index(index_path, cleanup_index)
    return {
        "schema_version": APPLY_SCHEMA_VERSION,
        "ok": not cleanup_errors,
        "plan_id": plan["plan_id"],
        "plan_path": str(plan_path.resolve()),
        "plan_sha256": plan_sha256,
        "archive_count": len(archives),
        "archives": archives,
        "removed_paths": removed_paths,
        "cleanup_status": cleanup_status,
        "cleanup_errors": cleanup_errors,
        "index_path": str(index_path),
    }


def _print_report(report: Mapping[str, Any]) -> None:
    print("FlowPilot runtime retention report: read-only")
    print(f"Runtime root: {report['flowpilot_root']}")
    print(f"Validation root: {report['validation_root']}")
    print(f"Current run: {report['current_run_id'] or '<none>'}")
    print(
        f"Run directories: {report['run_directory_count']} / "
        f"validation directories: {report['validation_directory_count']}"
    )
    print(f"Size: {report['total_bytes']} bytes in {report['total_files']} files")
    print(f"Eligible entries: {report['eligible_count']}")
    print(f"Archive candidates: {report['archive_candidate_count']}")
    print(f"Global protection reasons: {len(report['global_protection_reasons'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Accepted for clarity; report mode is always read-only.")
    parser.add_argument("--project-root", default=str(ROOT), help="Project root containing `.flowpilot`.")
    parser.add_argument("--max-runs", type=int, default=30, help="Maximum retained entries per owner root.")
    parser.add_argument("--max-age-days", type=int, default=None, help="Optionally select already eligible entries by age.")
    subparsers = parser.add_subparsers(dest="command")
    plan_parser = subparsers.add_parser("plan", help="Write one deterministic frozen retention plan.")
    plan_parser.add_argument("--out", type=Path, required=True)
    apply_parser = subparsers.add_parser("apply", help="Apply one exact frozen retention plan.")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args(argv)

    root = Path(args.project_root)
    try:
        if args.command == "plan":
            plan = build_plan(root, max_runs=args.max_runs, max_age_days=args.max_age_days)
            result = {
                "ok": True,
                "read_only": False,
                **write_plan(args.out, plan),
            }
        elif args.command == "apply":
            result = apply_plan(
                root,
                plan_path=args.plan,
                plan_sha256=args.plan_sha256,
            )
        else:
            result = build_report(root, max_runs=args.max_runs, max_age_days=args.max_age_days)
    except (OSError, ValueError, RetentionPlanError) as exc:
        result = {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "plan":
        print(f"Retention plan: {result.get('plan_path', '<failed>')}")
        print(f"Plan SHA-256: {result.get('plan_sha256', '<failed>')}")
        print(f"Candidates: {result.get('candidate_count', 0)}")
    elif args.command == "apply":
        print(f"Retention apply: {'complete' if result.get('ok') else 'failed'}")
        print(f"Archives: {result.get('archive_count', 0)}")
        print(f"Cleanup: {result.get('cleanup_status', 'not_run')}")
    else:
        _print_report(result)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
