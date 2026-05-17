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


@dataclass(frozen=True, slots=True)
class TierCommand:
    name: str
    command: tuple[str, ...]
    description: str
    long_running: bool = False
    release_only: bool = False
    background_recommended: bool = False


def _py(*args: str) -> tuple[str, ...]:
    return (sys.executable, *args)


def _pytest(name: str, *paths: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "pytest", *paths, "-q"), description=description)


def _unittest(name: str, *modules: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "unittest", "-v", *modules), description=description)


FAST_COMMANDS = (
    TierCommand(
        name="flowguard_test_tiering",
        command=_py(
            "simulations/run_flowpilot_test_tiering_checks.py",
            "--json-out",
            "simulations/flowpilot_test_tiering_results.json",
        ),
        description="FlowGuard TestMesh-style checks for test tier ownership and evidence.",
    ),
    TierCommand(
        name="flowguard_slow_test_contracts",
        command=_py(
            "simulations/run_flowpilot_slow_test_contract_checks.py",
            "--json-out",
            "simulations/flowpilot_slow_test_contract_results.json",
        ),
        description="FlowGuard TestMesh contract checks for semantic parent/child slow-test splits.",
    ),
    TierCommand(
        name="flowguard_model_test_alignment",
        command=_py(
            "simulations/run_flowpilot_model_test_alignment_checks.py",
            "--json-out",
            "simulations/flowpilot_model_test_alignment_results.json",
        ),
        description="FlowGuard Model-Test Alignment checks for model obligations and ordinary test evidence.",
    ),
    TierCommand(
        name="flowguard_controller_break_glass",
        command=_py(
            "simulations/run_flowpilot_controller_break_glass_checks.py",
            "--json-out",
            "simulations/flowpilot_controller_break_glass_results.json",
        ),
        description="FlowGuard checks for Controller emergency break-glass eligibility and forbidden powers.",
    ),
    _pytest(
        "test_tier_runner",
        "tests/test_flowpilot_test_tiers.py",
        description="Focused tests for tier command planning and background artifact contracts.",
    ),
    _pytest(
        "model_test_alignment_tests",
        "tests/test_flowpilot_model_test_alignment.py",
        description="Focused tests for FlowGuard Model-Test Alignment evidence and known-bad cases.",
    ),
    _pytest(
        "controller_break_glass_tests",
        "tests/test_flowpilot_controller_break_glass.py",
        description="Focused tests for Controller break-glass prompt, records, and runtime reminders.",
    ),
    _pytest(
        "flowguard_proof_tests",
        "tests/test_flowguard_result_proof.py",
        description="Proof reuse checks for slow Meta/Capability parents.",
    ),
    _pytest(
        "thin_parent_tests",
        "tests/test_flowpilot_thin_parent_checks.py",
        description="Thin-parent proof and hierarchy helper tests.",
    ),
    _pytest(
        "maintenance_tool_tests",
        "tests/test_flowpilot_maintenance_tools.py",
        description="Small maintenance-tool regression tests.",
    ),
)

ROUTER_STARTUP_COMMANDS = (
    _unittest(
        "router_startup_runtime",
        "tests.test_flowpilot_router_startup_runtime",
        "tests.router_runtime.bootstrap_cli",
        "tests.router_runtime.startup_bootstrap",
        "tests.router_runtime.startup_daemon",
        description="Startup bootstrap, CLI, and daemon router slices.",
    ),
)

ROUTER_FOREGROUND_COMMANDS = (
    _unittest(
        "router_foreground_controller",
        "tests.router_runtime.foreground",
        "tests.router_runtime.controller",
        "tests.router_runtime.foreground_controller",
        "tests.router_runtime.dispatch_gate",
        description="Foreground controller and dispatch-gate router slices.",
    ),
)

ROUTER_PACKET_COMMANDS = (
    _unittest(
        "router_packet_runtime",
        "tests.test_flowpilot_packet_runtime",
        description="Packet runtime contract tests.",
    ),
    _unittest(
        "router_packets",
        "tests.router_runtime.packets",
        description="Router packet ledger and envelope slice.",
    ),
    _unittest(
        "router_cards",
        "tests.router_runtime.cards",
        description="Router runtime card slice.",
    ),
    _unittest(
        "router_ack_return",
        "tests.router_runtime.ack_return",
        description="ACK and return-event router slice.",
    ),
)

ROUTER_ROUTE_COMMANDS = (
    _unittest(
        "router_boundaries",
        "tests.test_flowpilot_router_boundaries",
        description="Router public boundary and import-contract slice.",
    ),
    _unittest(
        "router_route_mutation_core",
        "tests.router_runtime.route_mutation",
        description="Runtime route-mutation router slice.",
    ),
    _unittest(
        "router_route_mutation_contracts",
        "tests.test_flowpilot_router_runtime_route_mutation",
        description="Route-mutation contract tests.",
    ),
    _unittest(
        "router_user_flow_diagram",
        "tests.test_flowpilot_user_flow_diagram",
        description="User-flow diagram route display tests.",
    ),
)

ROUTER_TERMINAL_COMMANDS = (
    _unittest(
        "router_terminal",
        "tests.router_runtime.terminal",
        description="Terminal lifecycle router slice.",
    ),
    _unittest(
        "router_closure",
        "tests.router_runtime.closure",
        description="Terminal closure ledger router slice.",
    ),
    _unittest(
        "router_resume",
        "tests.router_runtime.resume",
        description="Resume and role-recovery router slice.",
    ),
    _unittest(
        "router_control_blockers",
        "tests.router_runtime.control_blockers",
        description="Control-blocker repair router slice.",
    ),
    _unittest(
        "router_pm_role_work",
        "tests.router_runtime.pm_role_work",
        description="PM role-work router slice.",
    ),
    _unittest(
        "router_quality_gates",
        "tests.router_runtime.quality_gates",
        description="Quality gate router slice.",
    ),
    _unittest(
        "router_material_modeling",
        "tests.router_runtime.material_modeling",
        description="Material intake and modeling router slice.",
    ),
)

INTEGRATION_COMMANDS = (
    TierCommand(
        name="check_install",
        command=_py("scripts/check_install.py", "--json"),
        description="Repository install contract check.",
    ),
    TierCommand(
        name="audit_local_install_sync",
        command=_py("scripts/audit_local_install_sync.py", "--json"),
        description="Local installed-skill freshness and source sync audit.",
    ),
    TierCommand(
        name="smoke_autopilot_fast",
        command=_py("scripts/smoke_autopilot.py", "--fast"),
        description="Smoke checks with reusable thin-parent slow-model proofs.",
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_coverage_sweep",
        command=_py("scripts/run_flowguard_coverage_sweep.py", "--timeout-seconds", "30"),
        description="Read-only FlowGuard coverage sweep.",
        long_running=True,
        background_recommended=True,
    ),
)

RELEASE_COMMANDS = (
    TierCommand(
        name="release_tooling",
        command=_py("simulations/run_release_tooling_checks.py"),
        description="Release-tooling FlowGuard checks.",
    ),
    TierCommand(
        name="public_release_check",
        command=_py("scripts/check_public_release.py", "--json", "--skip-url-check"),
        description="Public release boundary validation without URL probing.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="meta_full",
        command=_py("simulations/run_meta_checks.py", "--full"),
        description="Layered full Meta parent regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="capability_full",
        command=_py("simulations/run_capability_checks.py", "--full"),
        description="Layered full Capability parent regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
)

LEGACY_FULL_COMMANDS = (
    TierCommand(
        name="meta_legacy_full",
        command=_py("simulations/run_meta_checks.py", "--legacy-full"),
        description="Legacy full Meta graph regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="capability_legacy_full",
        command=_py("simulations/run_capability_checks.py", "--legacy-full"),
        description="Legacy full Capability graph regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
)


def commands_for_tier(tier: str) -> tuple[TierCommand, ...]:
    mapping: dict[str, tuple[TierCommand, ...]] = {
        "collect": (
            TierCommand(
                name="pytest_collect_tests",
                command=_py("-m", "pytest", "tests", "--collect-only", "-q"),
                description="Collect only from the real tests/ tree.",
            ),
        ),
        "fast": FAST_COMMANDS,
        "router-startup": ROUTER_STARTUP_COMMANDS,
        "router-foreground": ROUTER_FOREGROUND_COMMANDS,
        "router-packets": ROUTER_PACKET_COMMANDS,
        "router-route": ROUTER_ROUTE_COMMANDS,
        "router-terminal": ROUTER_TERMINAL_COMMANDS,
        "integration": INTEGRATION_COMMANDS,
        "release": RELEASE_COMMANDS,
        "legacy-full": LEGACY_FULL_COMMANDS,
    }
    if tier == "router":
        return (
            *ROUTER_STARTUP_COMMANDS,
            *ROUTER_FOREGROUND_COMMANDS,
            *ROUTER_PACKET_COMMANDS,
            *ROUTER_ROUTE_COMMANDS,
            *ROUTER_TERMINAL_COMMANDS,
        )
    if tier == "all":
        return (
            *mapping["collect"],
            *FAST_COMMANDS,
            *commands_for_tier("router"),
            *INTEGRATION_COMMANDS,
        )
    return mapping[tier]


def tier_names() -> tuple[str, ...]:
    return (
        "collect",
        "fast",
        "router-startup",
        "router-foreground",
        "router-packets",
        "router-route",
        "router-terminal",
        "router",
        "integration",
        "release",
        "legacy-full",
        "all",
    )


def _safe_base(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return safe or "test_tier_command"


def artifact_paths(log_root: Path, name: str) -> dict[str, Path]:
    base = _safe_base(name)
    return {suffix: log_root / f"{base}.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"} | {
        "meta": log_root / f"{base}.meta.json"
    }


def background_supervisor_name(tier: str) -> str:
    return f"{tier}_background_supervisor"


def should_use_background_supervisor(command_count: int, max_parallel: int) -> bool:
    return max_parallel > 0 and command_count > max_parallel


def _artifact_paths_for_json(log_root: Path, name: str) -> dict[str, str]:
    return {
        key: str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
        for key, path in artifact_paths(log_root, name).items()
    }


def command_to_json(command: TierCommand, *, background_dir: Path) -> dict[str, Any]:
    return {
        "name": command.name,
        "command": list(command.command),
        "description": command.description,
        "long_running": command.long_running,
        "release_only": command.release_only,
        "background_recommended": command.background_recommended,
        "background_artifacts": _artifact_paths_for_json(background_dir, command.name),
    }


def plan_for_tier(tier: str, *, background_dir: Path) -> dict[str, Any]:
    commands = commands_for_tier(tier)
    return {
        "tier": tier,
        "command_count": len(commands),
        "commands": [command_to_json(command, background_dir=background_dir) for command in commands],
        "background_dir": str(
            background_dir.relative_to(ROOT) if background_dir.is_relative_to(ROOT) else background_dir
        ),
        "background_contract": [f"<name>.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"]
        + ["<name>.meta.json"],
        "release_obligation_visible": tier not in {"release", "legacy-full"},
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


MappingLike = dict[str, Any]


def _windows_hidden_process_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def _windows_hidden_startupinfo() -> Any | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo


def _hidden_process_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    return {
        "creationflags": _windows_hidden_process_flags(),
        "startupinfo": _windows_hidden_startupinfo(),
    }


def _launch_background(command: TierCommand, *, log_root: Path) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(log_root, command.name)
    meta = {
        "name": command.name,
        "command": list(command.command),
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    child_args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--background-child",
        "--name",
        command.name,
        "--command-json",
        json.dumps(list(command.command)),
        "--background-dir",
        str(log_root),
    ]
    proc = subprocess.Popen(
        child_args,
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
        "name": command.name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def launch_background(commands: Iterable[TierCommand], *, log_root: Path) -> list[dict[str, Any]]:
    return [_launch_background(command, log_root=log_root) for command in commands]


def _read_exit_code(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return 1


def _launch_background_supervisor(tier: str, *, log_root: Path, max_parallel: int) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
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
) -> int:
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
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
        "command_count": len(commands),
        "running": [],
        "completed": [],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)

    pending = list(commands)
    running: list[TierCommand] = []
    completed: list[dict[str, Any]] = []

    with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths["err"].open(
        "w", encoding="utf-8", errors="replace"
    ) as err_file, paths["combined"].open("w", encoding="utf-8", errors="replace") as combined_file:
        while pending or running:
            while pending and len(running) < max_parallel:
                command = pending.pop(0)
                launched = _launch_background(command, log_root=log_root)
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
                result = {"name": command.name, "exit_code": exit_code, "ok": exit_code == 0}
                completed.append(result)
                line = f"completed {command.name} exit={exit_code}\n"
                out_file.write(line)
                out_file.flush()
                combined_file.write(f"[supervisor] {line}")
                combined_file.flush()
                if exit_code != 0:
                    err_file.write(line)
                    err_file.flush()
            running = still_running

            meta["running"] = [command.name for command in running]
            meta["completed"] = completed
            _write_json(paths["meta"], meta)
            if pending or running:
                time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)

    ok = all(item["ok"] for item in completed) and len(completed) == len(commands)
    exit_code = 0 if ok else 1
    paths["exit"].write_text(f"{exit_code}\n", encoding="utf-8")
    meta["status"] = "passed" if ok else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = exit_code
    meta["completed"] = completed
    meta["running"] = []
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


def run_background_child(name: str, command: Sequence[str], *, log_root: Path) -> int:
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": name,
        "command": list(command),
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
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
            returncode = process.wait()
            out_thread.join()
            err_thread.join()
    except Exception as exc:  # pragma: no cover - defensive background reporting
        paths["err"].write_text(f"background child failed before command exit: {exc}\n", encoding="utf-8")
        paths["combined"].write_text(
            f"[runner] background child failed before command exit: {exc}\n",
            encoding="utf-8",
        )
        returncode = 1

    paths["exit"].write_text(f"{returncode}\n", encoding="utf-8")
    meta["status"] = "passed" if returncode == 0 else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = returncode
    meta["proof_reused"] = flags["proof_reused"]
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
    parser.add_argument("--background-dir", type=Path, default=DEFAULT_BACKGROUND_DIR)
    parser.add_argument(
        "--background-max-parallel",
        type=int,
        default=DEFAULT_BACKGROUND_MAX_PARALLEL,
        help="Maximum command runners started concurrently by the background supervisor.",
    )
    parser.add_argument("--list-tiers", action="store_true")
    parser.add_argument("--background-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--background-supervisor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--name", default="", help=argparse.SUPPRESS)
    parser.add_argument("--command-json", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.background_child:
        command = json.loads(args.command_json)
        if not isinstance(command, list) or not args.name:
            raise SystemExit("background child requires --name and command list")
        return run_background_child(args.name, [str(part) for part in command], log_root=args.background_dir)

    if args.background_supervisor:
        commands = commands_for_tier(args.tier)
        max_parallel = max(1, args.background_max_parallel)
        return run_background_supervisor(
            args.tier,
            commands,
            log_root=args.background_dir,
            max_parallel=max_parallel,
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
    if args.dry_run:
        if args.json:
            print(json.dumps(plan, indent=2, sort_keys=True))
        else:
            for command in plan["commands"]:
                print(" ".join(command["command"]))
        return 0

    if args.background:
        max_parallel = max(1, args.background_max_parallel)
        if should_use_background_supervisor(len(commands), max_parallel):
            launched = [_launch_background_supervisor(args.tier, log_root=args.background_dir, max_parallel=max_parallel)]
            supervisor = launched[0]
        else:
            launched = launch_background(commands, log_root=args.background_dir)
            supervisor = None
        payload = {
            "ok": True,
            "tier": args.tier,
            "background_max_parallel": max_parallel,
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
