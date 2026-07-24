"""Bounded background-tier supervisor for the public test-tier facade."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Callable, Sequence

try:
    from .background import (
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _launch_background,
        _read_background_meta,
        _read_exit_code,
        _utc_now,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
    )
    from .definitions import TierCommand, commands_for_tier
    from .evidence_v5 import (
        BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION,
        BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION,
        BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION,
        COMBINED_INDEX_MAX_BYTES,
        RECENT_PROGRESS_OWNER_LIMIT,
        background_result_fingerprint_v2,
        canonical_json_bytes,
        path_reference,
        sha256_json,
        stream_descriptor,
        terminal_stream_index_bytes,
    )
    from .impact_resolution import (
        build_owner_contracts,
        load_previous_manifest,
        owner_reference_from_child_meta,
        owner_reference_from_reuse_decision,
        owner_identity,
        resolve_impact,
    )
    from .source_fingerprint import source_snapshot
except ImportError:  # pragma: no cover - direct script import path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from background import (
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _launch_background,
        _read_background_meta,
        _read_exit_code,
        _utc_now,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
    )
    from definitions import TierCommand, commands_for_tier
    from evidence_v5 import (
        BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION,
        BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION,
        BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION,
        COMBINED_INDEX_MAX_BYTES,
        RECENT_PROGRESS_OWNER_LIMIT,
        background_result_fingerprint_v2,
        canonical_json_bytes,
        path_reference,
        sha256_json,
        stream_descriptor,
        terminal_stream_index_bytes,
    )
    from impact_resolution import (
        build_owner_contracts,
        load_previous_manifest,
        owner_reference_from_child_meta,
        owner_reference_from_reuse_decision,
        owner_identity,
        resolve_impact,
    )
    from source_fingerprint import source_snapshot


ROOT = Path(__file__).resolve().parents[2]
BACKGROUND_CHILD_ENTRYPOINT = ROOT / "scripts" / "run_test_tier.py"
BACKGROUND_SUPERVISOR_POLL_SECONDS = 2.0
SUPERVISOR_PROGRESS_MAX_BYTES = 32 * 1024


def _publish_exit(path: Path, content: bytes) -> None:
    staging = path.with_name(path.name + ".tmp")
    staging.write_bytes(content)
    staging.replace(path)


def _publish_bytes(path: Path, content: bytes) -> None:
    staging = path.with_name(path.name + ".tmp")
    staging.write_bytes(content)
    staging.replace(path)


def supervisor_control_paths(log_root: Path, tier: str) -> dict[str, Path]:
    base = background_supervisor_name(tier)
    return {
        "impact_plan": log_root / f"{base}.impact-plan.json",
        "progress": log_root / f"{base}.progress.json",
        "owner_index": log_root / f"{base}.owner-index.json",
    }


def _write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"immutable artifact already exists: {path}")
    _write_json(path, payload)


def _write_progress(
    path: Path,
    *,
    tier: str,
    impact_plan_id: str,
    owner_count: int,
    execute_count: int,
    reuse_count: int,
    pending_owner_ids: Sequence[str],
    running_owner_ids: Sequence[str],
    recent_terminal: Sequence[dict[str, Any]],
    status: str,
) -> None:
    payload = {
        "schema_version": BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION,
        "tier": tier,
        "impact_plan_id": impact_plan_id,
        "status": status,
        "updated_at": _utc_now(),
        "counts": {
            "owner": owner_count,
            "execute": execute_count,
            "reuse": reuse_count,
            "pending": len(pending_owner_ids),
            "running": len(running_owner_ids),
            "terminal": owner_count
            - len(pending_owner_ids)
            - len(running_owner_ids),
        },
        "pending_owner_count": len(pending_owner_ids),
        "running_owner_ids": list(running_owner_ids),
        "recent_terminal": list(recent_terminal)[-RECENT_PROGRESS_OWNER_LIMIT:],
    }
    encoded = canonical_json_bytes(payload)
    if len(encoded) > SUPERVISOR_PROGRESS_MAX_BYTES:
        raise ValueError("supervisor progress exceeds bounded current contract")
    _write_json(path, payload)


def _finalize_stream_index(
    paths: dict[str, Path],
    meta: dict[str, Any],
    *,
    exit_code: int,
) -> None:
    for key in ("out", "err"):
        if not paths[key].exists():
            paths[key].write_text("", encoding="utf-8")
    stdout = stream_descriptor(paths["out"], path_value=str(paths["out"].resolve()))
    stderr = stream_descriptor(paths["err"], path_value=str(paths["err"].resolve()))
    cleanup_reason = "supervisor_no_descendant_ownership"
    result_fingerprint = background_result_fingerprint_v2(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        status=str(meta.get("status") or ""),
        descendant_zero_confirmed=True,
        cleanup_reason=cleanup_reason,
    )
    combined = terminal_stream_index_bytes(
        name=str(meta.get("name") or ""),
        status=str(meta.get("status") or ""),
        exit_code=exit_code,
        start_time=str(meta.get("start_time") or ""),
        end_time=str(meta.get("end_time") or ""),
        stdout=stdout,
        stderr=stderr,
        descendant_zero_confirmed=True,
        cleanup_reason=cleanup_reason,
        result_fingerprint=result_fingerprint,
    )
    _publish_bytes(paths["combined"], combined)
    meta["stream_artifacts"] = {"stdout": stdout, "stderr": stderr}
    meta["combined_artifact"] = {
        **path_reference(paths["combined"], root=ROOT),
        "kind": "terminal_stream_index",
        "max_bytes": COMBINED_INDEX_MAX_BYTES,
    }
    meta["combined_kind"] = "terminal_stream_index"
    meta["result_fingerprint_schema_version"] = (
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION
    )
    meta["result_fingerprint"] = result_fingerprint


def _finalize_supervisor(
    paths: dict[str, Path],
    meta: dict[str, Any],
    *,
    exit_code: int,
) -> None:
    """Publish one terminal receipt before making its exit marker observable."""

    _finalize_stream_index(paths, meta, exit_code=exit_code)
    _write_json(paths["meta"], meta)
    _publish_exit(paths["exit"], f"{exit_code}\n".encode("utf-8"))


def _global_owner_contracts():
    """Return the sole cross-tier owner graph used for impact mapping."""

    return build_owner_contracts(commands_for_tier("all"))


def next_background_launch_index(
    pending: Sequence[TierCommand],
    running: Sequence[TierCommand],
) -> int | None:
    if not pending:
        return None
    if running:
        active_stage = min(command.background_stage for command in running)
    else:
        active_stage = min(command.background_stage for command in pending)
    active_resources = {
        command.background_exclusive_resource
        for command in running
        if command.background_exclusive_resource
    }
    for index, command in enumerate(pending):
        if (
            command.background_stage == active_stage
            and command.background_exclusive_resource not in active_resources
        ):
            return index
    return None


def launch_background_supervisor(
    tier: str,
    *,
    log_root: Path,
    max_parallel: int,
    seed_baseline: bool,
    previous_manifest: Path | None,
    previous_manifest_sha256: str,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if log_root.exists() and any(log_root.iterdir()):
        raise ValueError(f"background run root must be new and empty: {log_root}")
    log_root.mkdir(parents=True, exist_ok=True)
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    clear_artifacts(paths)
    command = [
        sys.executable,
        str(BACKGROUND_CHILD_ENTRYPOINT),
        "--background-supervisor",
        "--tier",
        tier,
        "--background-dir",
        str(log_root),
        "--background-max-parallel",
        str(max_parallel),
        "--background-child-timeout-seconds",
        str(timeout_seconds),
    ]
    if seed_baseline:
        command.append("--seed-baseline")
    else:
        if previous_manifest is None or not previous_manifest_sha256:
            raise ValueError("previous manifest path and sha256 are required")
        command.extend(
            (
                "--previous-manifest",
                str(previous_manifest),
                "--previous-manifest-sha256",
                previous_manifest_sha256,
            )
        )
    meta = {
        "name": name,
        "tier": tier,
        "command": command,
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "max_parallel": max_parallel,
        "timeout_seconds": timeout_seconds,
        "seed_baseline": seed_baseline,
        "previous_manifest": str(previous_manifest or ""),
        "previous_manifest_sha256": previous_manifest_sha256,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_hidden_process_kwargs(),
    )
    meta["status"] = "running"
    meta["launcher_pid"] = os.getpid()
    meta["child_pid"] = proc.pid
    _write_json(paths["meta"], meta)
    return {
        "name": name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def run_background_supervisor(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
    max_parallel: int,
    seed_baseline: bool,
    previous_manifest_path: Path | None,
    previous_manifest_sha256: str,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    launch_fn: Callable[..., dict[str, Any]] = _launch_background,
) -> int:
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    control_paths = supervisor_control_paths(log_root, tier)
    log_root.mkdir(parents=True, exist_ok=True)
    previous_manifest, actual_previous_sha256, manifest_blockers = load_previous_manifest(
        previous_manifest_path,
        expected_sha256=previous_manifest_sha256,
        seed_baseline=seed_baseline,
    )
    all_owner_contracts = _global_owner_contracts()
    plan = resolve_impact(
        requested_scope=tier,
        tier_commands=commands,
        all_owner_contracts=all_owner_contracts,
        previous_manifest=previous_manifest,
        previous_manifest_path=str(previous_manifest_path or ""),
        previous_manifest_sha256=actual_previous_sha256 or previous_manifest_sha256,
        seed_baseline=seed_baseline,
        preexisting_blockers=manifest_blockers,
    )
    impact_plan_payload = plan.to_dict()
    _write_immutable_json(control_paths["impact_plan"], impact_plan_payload)
    impact_plan_ref = {
        **path_reference(control_paths["impact_plan"], root=ROOT),
        "plan_id": plan.plan_id,
    }
    meta: dict[str, Any] = {
        "schema_version": BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION,
        "name": name,
        "tier": tier,
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "max_parallel": max_parallel,
        "timeout_seconds": timeout_seconds,
        "command_count": len(commands),
        "execute_count": len(plan.executable_owner_ids),
        "reuse_count": len(plan.reused_owner_ids),
        "impact_plan_ref": impact_plan_ref,
        "progress_ref": {
            "path": str(control_paths["progress"].resolve()),
        },
        "owner_index_ref": None,
        "snapshot_start_fingerprint": plan.snapshot.get("fingerprint"),
        "snapshot_end_fingerprint": None,
        "terminal_owner_count": 0,
        "running_owner_count": 0,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    _write_progress(
        control_paths["progress"],
        tier=tier,
        impact_plan_id=plan.plan_id,
        owner_count=len(commands),
        execute_count=len(plan.executable_owner_ids),
        reuse_count=len(plan.reused_owner_ids),
        pending_owner_ids=plan.executable_owner_ids,
        running_owner_ids=(),
        recent_terminal=(
            {
                "owner_id": owner_id,
                "state": "reused",
                "at": _utc_now(),
            }
            for owner_id in plan.reused_owner_ids
        ),
        status="blocked" if plan.blockers else "running",
    )
    if plan.blockers:
        paths["out"].write_text("", encoding="utf-8")
        paths["err"].write_text(
            "\n".join(plan.blockers) + "\n",
            encoding="utf-8",
        )
        owner_index = {
            "schema_version": BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
            "tier": tier,
            "impact_plan_id": plan.plan_id,
            "impact_plan_sha256": impact_plan_ref["sha256"],
            "status": "blocked",
            "expected_owner_ids": [command.name for command in commands],
            "owners": [],
            "blockers": list(plan.blockers),
        }
        _write_immutable_json(control_paths["owner_index"], owner_index)
        meta.update(
            status="blocked",
            end_time=_utc_now(),
            exit_code=1,
            blockers=list(plan.blockers),
            owner_index_ref=path_reference(
                control_paths["owner_index"],
                root=ROOT,
            ),
            progress_ref=path_reference(control_paths["progress"], root=ROOT),
        )
        _finalize_supervisor(paths, meta, exit_code=1)
        return 1

    command_by_name = {command.name: command for command in commands}
    decision_by_name = {decision.owner_id: decision for decision in plan.decisions}
    contract_by_name = {contract.owner_id: contract for contract in plan.contracts}
    pending = [
        command_by_name[owner_id] for owner_id in plan.executable_owner_ids
    ]
    running: list[TierCommand] = []
    completed: list[dict[str, Any]] = [
        {
            "name": decision.owner_id,
            "exit_code": 0,
            "ok": True,
            "evidence_status": "reused",
            "proof_scope": "exact_owner_reuse_ticket",
            "reasons": list(decision.reason_codes),
        }
        for decision in plan.decisions
        if decision.action == "reuse"
    ]
    owners: dict[str, Any] = {}
    for decision in plan.decisions:
        if decision.action != "reuse":
            continue
        owners[decision.owner_id] = owner_reference_from_reuse_decision(
            decision
        )
    recent_terminal = [
        {
            "owner_id": item["name"],
            "state": item["evidence_status"],
            "at": _utc_now(),
        }
        for item in completed
    ]
    try:
        with paths["out"].open(
            "w", encoding="utf-8", errors="replace"
        ) as out_file, paths["err"].open(
            "w", encoding="utf-8", errors="replace"
        ) as err_file:
            while pending or running:
                while pending and len(running) < max_parallel:
                    launch_index = next_background_launch_index(pending, running)
                    if launch_index is None:
                        break
                    command = pending.pop(launch_index)
                    launched = launch_fn(
                        command,
                        log_root=log_root,
                        impact_plan_path=control_paths["impact_plan"],
                        impact_plan_sha256=str(impact_plan_ref["sha256"]),
                        timeout_seconds=timeout_seconds,
                    )
                    running.append(command)
                    line = f"launched {command.name} pid={launched['child_pid']}\n"
                    out_file.write(line)
                    out_file.flush()
                still_running: list[TierCommand] = []
                for command in running:
                    exit_code = _read_exit_code(artifact_paths(log_root, command.name)["exit"])
                    if exit_code is None:
                        still_running.append(command)
                        continue
                    evidence = classify_background_artifact(
                        log_root,
                        command.name,
                        command=command,
                        tier=tier,
                    )
                    result = {
                        "name": command.name,
                        "exit_code": exit_code,
                        "ok": bool(evidence["ok"]),
                        "evidence_status": evidence["status"],
                        "proof_scope": evidence["proof_scope"],
                        "reasons": evidence["reasons"],
                    }
                    completed.append(result)
                    child_paths = artifact_paths(log_root, command.name)
                    child_meta, child_meta_error = _read_background_meta(
                        child_paths["meta"]
                    )
                    if child_meta_error or child_meta is None:
                        result["ok"] = False
                        result["reasons"] = [
                            *result["reasons"],
                            child_meta_error or "missing_meta",
                        ]
                    else:
                        try:
                            owners[command.name] = owner_reference_from_child_meta(
                                owner_id=command.name,
                                meta_path=child_paths["meta"],
                                meta=child_meta,
                            )
                        except ValueError as exc:
                            result["ok"] = False
                            result["reasons"] = [*result["reasons"], str(exc)]
                    line = f"completed {command.name} exit={exit_code} evidence={evidence['status']}\n"
                    out_file.write(line)
                    out_file.flush()
                    if not result["ok"]:
                        err_file.write(line)
                        err_file.flush()
                    recent_terminal.append(
                        {
                            "owner_id": command.name,
                            "state": evidence["status"],
                            "at": _utc_now(),
                        }
                    )
                running = still_running
                _write_progress(
                    control_paths["progress"],
                    tier=tier,
                    impact_plan_id=plan.plan_id,
                    owner_count=len(commands),
                    execute_count=len(plan.executable_owner_ids),
                    reuse_count=len(plan.reused_owner_ids),
                    pending_owner_ids=[command.name for command in pending],
                    running_owner_ids=[command.name for command in running],
                    recent_terminal=recent_terminal,
                    status="running",
                )
                if pending or running:
                    time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)
    except Exception as exc:
        details = traceback.format_exc()
        with paths["err"].open(
            "a", encoding="utf-8", errors="replace"
        ) as err_file:
            err_file.write(details)
        if not paths["out"].exists():
            paths["out"].write_text("", encoding="utf-8")
        owner_index = {
            "schema_version": BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
            "tier": tier,
            "impact_plan_id": plan.plan_id,
            "impact_plan_sha256": impact_plan_ref["sha256"],
            "status": "failed",
            "expected_owner_ids": [command.name for command in commands],
            "owners": [owners[key] for key in sorted(owners)],
            "error": str(exc),
        }
        _write_immutable_json(control_paths["owner_index"], owner_index)
        _write_progress(
            control_paths["progress"],
            tier=tier,
            impact_plan_id=plan.plan_id,
            owner_count=len(commands),
            execute_count=len(plan.executable_owner_ids),
            reuse_count=len(plan.reused_owner_ids),
            pending_owner_ids=[command.name for command in pending],
            running_owner_ids=[command.name for command in running],
            recent_terminal=recent_terminal,
            status="failed",
        )
        meta.update(
            status="failed",
            end_time=_utc_now(),
            exit_code=1,
            error=str(exc),
            running_owner_count=len(running),
            terminal_owner_count=len(owners),
            owner_index_ref=path_reference(
                control_paths["owner_index"],
                root=ROOT,
            ),
            progress_ref=path_reference(control_paths["progress"], root=ROOT),
        )
        _finalize_supervisor(paths, meta, exit_code=1)
        return 1
    snapshot_end = source_snapshot()
    start_files = plan.snapshot.get("files")
    end_files = snapshot_end.get("files")
    changed_during_run = {
        path
        for path in set(start_files or {}) | set(end_files or {})
        if (start_files or {}).get(path) != (end_files or {}).get(path)
    }
    globally_mapped = {
        path
        for contract in all_owner_contracts
        for path in contract.covered_inputs
    }
    final_failures: list[str] = []
    final_failures.extend(
        f"impact_mapping_missing:{path}"
        for path in sorted(changed_during_run)
        if path not in globally_mapped
    )
    fingerprint_cache: dict[str, str] = {}
    for decision in plan.decisions:
        current_identity = owner_identity(
            contract_by_name[decision.owner_id],
            fingerprint_cache=fingerprint_cache,
        )
        if current_identity.to_dict() != decision.identity.to_dict():
            final_failures.append(
                f"{decision.owner_id}:owner_inputs_changed_after_plan"
            )
    if final_failures:
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write("\n".join(final_failures) + "\n")
    ok = (
        all(item["ok"] for item in completed)
        and len(completed) == len(commands)
        and len(owners) == len(commands)
        and not final_failures
    )
    exit_code = 0 if ok else 1
    meta.update(
        status="passed" if ok else "failed",
        end_time=_utc_now(),
        exit_code=exit_code,
        terminal_owner_count=len(owners),
        running_owner_count=0,
        snapshot_end_fingerprint=snapshot_end.get("fingerprint"),
        final_impact_failures=final_failures,
    )
    if final_failures:
        meta["failure_reason"] = "impact_plan_stale_or_unmapped"
    owner_index = {
        "schema_version": BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
        "tier": tier,
        "impact_plan_id": plan.plan_id,
        "impact_plan_sha256": impact_plan_ref["sha256"],
        "status": meta["status"],
        "expected_owner_ids": [command.name for command in commands],
        "owner_count": len(owners),
        "execute_count": len(plan.executable_owner_ids),
        "reuse_count": len(plan.reused_owner_ids),
        "owners": [owners[key] for key in sorted(owners)],
        "snapshot_end_fingerprint": snapshot_end.get("fingerprint"),
        "final_impact_failures": final_failures,
    }
    _write_immutable_json(control_paths["owner_index"], owner_index)
    _write_progress(
        control_paths["progress"],
        tier=tier,
        impact_plan_id=plan.plan_id,
        owner_count=len(commands),
        execute_count=len(plan.executable_owner_ids),
        reuse_count=len(plan.reused_owner_ids),
        pending_owner_ids=(),
        running_owner_ids=(),
        recent_terminal=recent_terminal,
        status=str(meta["status"]),
    )
    meta["owner_index_ref"] = path_reference(
        control_paths["owner_index"],
        root=ROOT,
    )
    meta["progress_ref"] = path_reference(control_paths["progress"], root=ROOT)
    _finalize_supervisor(paths, meta, exit_code=exit_code)
    return exit_code
