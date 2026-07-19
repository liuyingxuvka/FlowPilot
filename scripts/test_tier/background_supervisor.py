"""Bounded background-tier supervisor for the public test-tier facade."""

from __future__ import annotations

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
    from .impact_resolution import (
        build_owner_contracts,
        load_previous_manifest,
        owner_identity,
        proof_row_from_child_meta,
        resolve_impact,
        sha256_file,
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
    from impact_resolution import (
        build_owner_contracts,
        load_previous_manifest,
        owner_identity,
        proof_row_from_child_meta,
        resolve_impact,
        sha256_file,
    )
    from source_fingerprint import source_snapshot


ROOT = Path(__file__).resolve().parents[2]
BACKGROUND_CHILD_ENTRYPOINT = ROOT / "scripts" / "run_test_tier.py"
BACKGROUND_SUPERVISOR_POLL_SECONDS = 2.0


def _publish_exit(path: Path, content: bytes) -> None:
    staging = path.with_name(path.name + ".tmp")
    staging.write_bytes(content)
    staging.replace(path)


def _finalize_supervisor(
    paths: dict[str, Path],
    meta: dict[str, Any],
    *,
    exit_code: int,
) -> None:
    """Publish one terminal receipt before making its exit marker observable."""

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
    meta: dict[str, Any] = {
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
        "impact_plan": plan.to_dict(),
        "snapshot_start": dict(plan.snapshot),
        "snapshot_end": None,
        "running": [],
        "completed": [],
        "owners": {},
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    if plan.blockers:
        paths["out"].write_text("", encoding="utf-8")
        paths["err"].write_text(
            "\n".join(plan.blockers) + "\n",
            encoding="utf-8",
        )
        paths["combined"].write_text(
            "\n".join(f"[supervisor] blocked {item}" for item in plan.blockers) + "\n",
            encoding="utf-8",
        )
        meta.update(
            status="blocked",
            end_time=_utc_now(),
            exit_code=1,
            blockers=list(plan.blockers),
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
    previous_owners = (
        previous_manifest.get("owners")
        if isinstance(previous_manifest, dict)
        and isinstance(previous_manifest.get("owners"), dict)
        else {}
    )
    owners: dict[str, Any] = {}
    for decision in plan.decisions:
        if decision.action != "reuse":
            continue
        previous_row = previous_owners.get(decision.owner_id)
        assert isinstance(previous_row, dict)
        owners[decision.owner_id] = {
            **previous_row,
            "identity": decision.identity.to_dict(),
            "result_reused": True,
            "reuse_ticket": decision.reuse_ticket.to_dict()
            if decision.reuse_ticket is not None
            else None,
        }
    meta["completed"] = completed
    meta["owners"] = owners
    _write_json(paths["meta"], meta)
    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths[
            "err"
        ].open("w", encoding="utf-8", errors="replace") as err_file, paths["combined"].open(
            "w", encoding="utf-8", errors="replace"
        ) as combined_file:
            while pending or running:
                while pending and len(running) < max_parallel:
                    launch_index = next_background_launch_index(pending, running)
                    if launch_index is None:
                        break
                    command = pending.pop(launch_index)
                    launched = launch_fn(
                        command,
                        log_root=log_root,
                        impact_plan_id=plan.plan_id,
                        owner_identity_value=decision_by_name[
                            command.name
                        ].identity.to_dict(),
                        timeout_seconds=timeout_seconds,
                    )
                    running.append(command)
                    line = f"launched {command.name} pid={launched['child_pid']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()
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
                        proof_fingerprints = {
                            key: sha256_file(child_paths[key])
                            for key in ("out", "err", "combined", "exit")
                            if child_paths[key].is_file()
                        }
                        try:
                            owners[command.name] = proof_row_from_child_meta(
                                owner_id=command.name,
                                meta=child_meta,
                                artifact_fingerprints=proof_fingerprints,
                            )
                        except ValueError as exc:
                            result["ok"] = False
                            result["reasons"] = [*result["reasons"], str(exc)]
                    line = f"completed {command.name} exit={exit_code} evidence={evidence['status']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()
                    if not result["ok"]:
                        err_file.write(line)
                        err_file.flush()
                running = still_running
                meta["running"] = [command.name for command in running]
                meta["completed"] = completed
                meta["owners"] = owners
                _write_json(paths["meta"], meta)
                if pending or running:
                    time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)
    except Exception as exc:
        details = traceback.format_exc()
        paths["err"].write_text(details, encoding="utf-8", errors="replace")
        paths["combined"].write_text(f"[supervisor-error] {details}", encoding="utf-8", errors="replace")
        meta.update(
            status="failed",
            end_time=_utc_now(),
            exit_code=1,
            error=str(exc),
            running=[command.name for command in running],
            completed=completed,
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
    for decision in plan.decisions:
        current_identity = owner_identity(contract_by_name[decision.owner_id])
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
        completed=completed,
        owners=owners,
        running=[],
        snapshot_end=snapshot_end,
        final_impact_failures=final_failures,
    )
    if final_failures:
        meta["failure_reason"] = "impact_plan_stale_or_unmapped"
    _finalize_supervisor(paths, meta, exit_code=exit_code)
    return exit_code
