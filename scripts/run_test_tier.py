"""Run layered FlowPilot test tiers.

The runner keeps routine validation small, lets router domains run as child
suites, and launches long integration/release regressions with stable
background artifacts when requested.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKGROUND_DIR = ROOT / "tmp" / "test_background"
DEFAULT_BACKGROUND_MAX_PARALLEL = 4
BACKGROUND_SUPERVISOR_POLL_SECONDS = 2.0
ARTIFACT_SUFFIXES = ("out", "err", "combined", "exit", "meta")


try:
    from .test_tier.definitions import TierCommand, commands_for_tier, tier_names
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.definitions import TierCommand, commands_for_tier, tier_names

try:
    from .test_tier.background import (
        ARTIFACT_SUFFIXES,
        BACKGROUND_CHILD_TIMEOUT_EXIT_CODE,
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        MappingLike,
        _artifact_has_progress,
        _artifact_paths_for_json,
        _coerce_timeout_seconds,
        _hidden_process_kwargs,
        _launch_background,
        _read_background_meta,
        _read_exit_code,
        _release_local_only_proof,
        _safe_base,
        _terminate_process_tree,
        _utc_now,
        _windows_hidden_process_flags,
        _windows_hidden_startupinfo,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
        command_to_json,
        launch_background,
        plan_for_tier,
        should_use_background_supervisor,
    )

except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.background import (
        ARTIFACT_SUFFIXES,
        BACKGROUND_CHILD_TIMEOUT_EXIT_CODE,
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        MappingLike,
        _artifact_has_progress,
        _artifact_paths_for_json,
        _coerce_timeout_seconds,
        _hidden_process_kwargs,
        _launch_background,
        _read_background_meta,
        _read_exit_code,
        _release_local_only_proof,
        _safe_base,
        _terminate_process_tree,
        _utc_now,
        _windows_hidden_process_flags,
        _windows_hidden_startupinfo,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
        command_to_json,
        launch_background,
        plan_for_tier,
        should_use_background_supervisor,
    )

try:
    from .test_tier.source_fingerprint import source_fingerprint
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.source_fingerprint import source_fingerprint

try:
    from .test_tier.verification import verify_background_tier
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.verification import verify_background_tier

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
    for index, command in enumerate(pending):
        if command.background_stage == active_stage:
            return index
    return None


def _launch_background_supervisor(
    tier: str,
    *,
    log_root: Path,
    max_parallel: int,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    clear_artifacts(paths)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
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
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> int:
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    source_fingerprint_start = source_fingerprint()
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
        "covered_source_fingerprint_start": source_fingerprint_start,
        "covered_source_fingerprint_end": None,
        "source_fingerprint_current": None,
        "running": [],
        "completed": [],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)

    pending = list(commands)
    running: list[TierCommand] = []
    completed: list[dict[str, Any]] = []

    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths["err"].open(
            "w", encoding="utf-8", errors="replace"
        ) as err_file, paths["combined"].open("w", encoding="utf-8", errors="replace") as combined_file:
            while pending or running:
                while pending and len(running) < max_parallel:
                    launch_index = next_background_launch_index(pending, running)
                    if launch_index is None:
                        break
                    command = pending.pop(launch_index)
                    launched = _launch_background(
                        command,
                        log_root=log_root,
                        timeout_seconds=timeout_seconds,
                        source_fingerprint_value=source_fingerprint_start,
                    )
                    running.append(command)
                    line = f"launched {command.name} pid={launched['child_pid']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()

                still_running: list[TierCommand] = []
                for command in running:
                    exit_path = artifact_paths(log_root, command.name)["exit"]
                    exit_code = _read_exit_code(exit_path)
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
                _write_json(paths["meta"], meta)
                if pending or running:
                    time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)
    except Exception as exc:
        details = traceback.format_exc()
        paths["err"].write_text(details, encoding="utf-8", errors="replace")
        paths["combined"].write_text(f"[supervisor-error] {details}", encoding="utf-8", errors="replace")
        paths["exit"].write_text("1\n", encoding="utf-8")
        meta["status"] = "failed"
        meta["end_time"] = _utc_now()
        meta["exit_code"] = 1
        meta["error"] = str(exc)
        meta["running"] = [command.name for command in running]
        meta["completed"] = completed
        _write_json(paths["meta"], meta)
        return 1

    source_fingerprint_end = source_fingerprint()
    source_fingerprint_current = source_fingerprint_start == source_fingerprint_end
    if not source_fingerprint_current:
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write("covered source changed while the background tier was running\n")
    ok = (
        all(item["ok"] for item in completed)
        and len(completed) == len(commands)
        and source_fingerprint_current
    )
    exit_code = 0 if ok else 1
    paths["exit"].write_text(f"{exit_code}\n", encoding="utf-8")
    meta["status"] = "passed" if ok else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = exit_code
    meta["completed"] = completed
    meta["running"] = []
    meta["covered_source_fingerprint_end"] = source_fingerprint_end
    meta["source_fingerprint_current"] = source_fingerprint_current
    if not source_fingerprint_current:
        meta["failure_reason"] = "covered_source_changed_during_tier"
    _write_json(paths["meta"], meta)
    return exit_code


def _stream_pipe(
    pipe: Any,
    stream_name: str,
    target: Any,
    combined: Any,
    lock: threading.Lock,
    flags: dict[str, bool],
) -> None:
    for line in iter(pipe.readline, ""):
        target.write(line)
        target.flush()
        if "proof_reused" in line or "proof reused" in line.lower():
            flags["proof_reused"] = True
        with lock:
            combined.write(f"[{stream_name}] {line}")
            combined.flush()
    pipe.close()


def run_background_child(
    name: str,
    command: Sequence[str],
    *,
    log_root: Path,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    source_fingerprint_value: str | None = None,
) -> int:
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    covered_source = source_fingerprint_value or source_fingerprint()
    meta = {
        "name": name,
        "command": list(command),
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "timeout_seconds": timeout_seconds,
        "timed_out": False,
        "covered_source_fingerprint": covered_source,
        "covered_source_fingerprint_start": covered_source,
        "covered_source_fingerprint_end": None,
        "source_fingerprint_current": None,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    flags = {"proof_reused": False}
    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths[
            "err"
        ].open("w", encoding="utf-8", errors="replace") as err_file, paths["combined"].open(
            "w", encoding="utf-8", errors="replace"
        ) as combined_file:
            process = subprocess.Popen(
                list(command),
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                **_hidden_process_kwargs(),
            )
            assert process.stdout is not None
            assert process.stderr is not None
            lock = threading.Lock()
            out_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stdout, "stdout", out_file, combined_file, lock, flags),
                daemon=True,
            )
            err_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stderr, "stderr", err_file, combined_file, lock, flags),
                daemon=True,
            )
            out_thread.start()
            err_thread.start()
            try:
                returncode = process.wait(timeout=timeout_seconds or None)
            except subprocess.TimeoutExpired:
                meta["timed_out"] = True
                combined_file.write(
                    f"[runner] timed out after {timeout_seconds} seconds; terminating process tree\n"
                )
                combined_file.flush()
                err_file.write(f"background child timed out after {timeout_seconds} seconds\n")
                err_file.flush()
                _terminate_process_tree(process.pid)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                returncode = BACKGROUND_CHILD_TIMEOUT_EXIT_CODE
            out_thread.join(timeout=5)
            err_thread.join(timeout=5)
    except Exception as exc:  # pragma: no cover - defensive background reporting
        paths["err"].write_text(f"background child failed before command exit: {exc}\n", encoding="utf-8")
        paths["combined"].write_text(
            f"[runner] background child failed before command exit: {exc}\n",
            encoding="utf-8",
        )
        returncode = 1

    covered_source_end = source_fingerprint()
    source_current = covered_source == covered_source_end
    if returncode == 0 and not source_current:
        returncode = 1
        message = "covered source changed while the background child was running\n"
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write(message)
        with paths["combined"].open("a", encoding="utf-8", errors="replace") as combined_file:
            combined_file.write(f"[runner] {message}")
    paths["exit"].write_text(f"{returncode}\n", encoding="utf-8")
    meta["status"] = "passed" if returncode == 0 else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = returncode
    meta["proof_reused"] = flags["proof_reused"]
    meta["covered_source_fingerprint_end"] = covered_source_end
    meta["source_fingerprint_current"] = source_current
    if meta["timed_out"]:
        meta["failure_reason"] = "background_child_timeout"
    elif not source_current:
        meta["failure_reason"] = "covered_source_changed_during_command"
    _write_json(paths["meta"], meta)
    return returncode


def run_foreground(commands: Iterable[TierCommand]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            list(command.command),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_hidden_process_kwargs(),
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        results.append(
            {
                "name": command.name,
                "command": list(command.command),
                "returncode": completed.returncode,
                "ok": completed.returncode == 0,
            }
        )
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tier_names(), default="fast")
    parser.add_argument("--dry-run", action="store_true", help="Plan commands without executing.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--background", action="store_true", help="Launch commands as detached jobs.")
    parser.add_argument(
        "--verify-background",
        action="store_true",
        help="Verify existing final background artifacts without launching commands.",
    )
    parser.add_argument("--background-dir", type=Path, default=DEFAULT_BACKGROUND_DIR)
    parser.add_argument(
        "--background-max-parallel",
        type=int,
        default=DEFAULT_BACKGROUND_MAX_PARALLEL,
        help="Maximum command runners started concurrently by the background supervisor.",
    )
    parser.add_argument(
        "--background-child-timeout-seconds",
        type=int,
        default=DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        help="Maximum wall-clock seconds for each background child command; 0 disables this guard.",
    )
    parser.add_argument("--list-tiers", action="store_true")
    parser.add_argument("--background-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--background-supervisor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--name", default="", help=argparse.SUPPRESS)
    parser.add_argument("--command-json", default="", help=argparse.SUPPRESS)
    parser.add_argument("--covered-source-fingerprint", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.background_child:
        command = json.loads(args.command_json)
        if not isinstance(command, list) or not args.name:
            raise SystemExit("background child requires --name and command list")
        return run_background_child(
            args.name,
            [str(part) for part in command],
            log_root=args.background_dir,
            timeout_seconds=_coerce_timeout_seconds(args.background_child_timeout_seconds),
            source_fingerprint_value=args.covered_source_fingerprint or None,
        )

    if args.background_supervisor:
        commands = commands_for_tier(args.tier)
        max_parallel = max(1, args.background_max_parallel)
        return run_background_supervisor(
            args.tier,
            commands,
            log_root=args.background_dir,
            max_parallel=max_parallel,
            timeout_seconds=_coerce_timeout_seconds(args.background_child_timeout_seconds),
        )

    if args.list_tiers:
        payload = {"tiers": list(tier_names())}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for tier in tier_names():
                print(tier)
        return 0

    commands = commands_for_tier(args.tier)
    plan = plan_for_tier(args.tier, background_dir=args.background_dir)
    if args.verify_background:
        report = verify_background_tier(
            args.tier,
            commands,
            log_root=args.background_dir,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        elif report["ok"]:
            print(
                f"Verified {report['verified_count']} background test command(s) "
                f"under {args.background_dir}"
            )
        else:
            print("Background tier verification failed: " + "; ".join(report["failures"]))
        return 0 if report["ok"] else 1
    if args.dry_run:
        if args.json:
            print(json.dumps(plan, indent=2, sort_keys=True))
        else:
            for command in plan["commands"]:
                print(" ".join(command["command"]))
        return 0

    if args.background:
        max_parallel = max(1, args.background_max_parallel)
        timeout_seconds = _coerce_timeout_seconds(args.background_child_timeout_seconds)
        if should_use_background_supervisor(len(commands), max_parallel):
            launched = [
                _launch_background_supervisor(
                    args.tier,
                    log_root=args.background_dir,
                    max_parallel=max_parallel,
                    timeout_seconds=timeout_seconds,
                )
            ]
            supervisor = launched[0]
        else:
            launched = launch_background(
                commands,
                log_root=args.background_dir,
                timeout_seconds=timeout_seconds,
            )
            supervisor = None
        payload = {
            "ok": True,
            "tier": args.tier,
            "background_max_parallel": max_parallel,
            "background_child_timeout_seconds": timeout_seconds,
            "launched": launched,
            "plan": plan,
            "supervisor": supervisor,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Launched {len(launched)} background test command(s) under {args.background_dir}")
            for item in launched:
                print(f"- {item['name']}: pid={item['child_pid']}")
        return 0

    results = run_foreground(commands)
    ok = all(item["ok"] for item in results)
    payload = {"ok": ok, "tier": args.tier, "results": results, "plan": plan}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
