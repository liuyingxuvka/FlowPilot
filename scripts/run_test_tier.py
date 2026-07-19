"""Run layered FlowPilot test tiers.

The runner keeps routine validation small, lets router domains run as child
suites, and launches long integration/release regressions with stable
background artifacts when requested.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKGROUND_DIR = ROOT / "tmp" / "test_background"
DEFAULT_BACKGROUND_MAX_PARALLEL = 4


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
        _process_descendant_identities,
        _process_identity,
        _process_identity_is_live,
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
        _process_descendant_identities,
        _process_identity,
        _process_identity_is_live,
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
    from .test_tier.background_child import run_background_child as _run_background_child_impl
    from .test_tier.background_supervisor import (
        launch_background_supervisor as _launch_background_supervisor,
        next_background_launch_index,
        run_background_supervisor as _run_background_supervisor_impl,
    )
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.background_child import run_background_child as _run_background_child_impl
    from test_tier.background_supervisor import (
        launch_background_supervisor as _launch_background_supervisor,
        next_background_launch_index,
        run_background_supervisor as _run_background_supervisor_impl,
    )

try:
    from .test_tier.verification import verify_background_tier
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_tier.verification import verify_background_tier

def run_background_supervisor(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
    max_parallel: int,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> int:
    return _run_background_supervisor_impl(
        tier,
        commands,
        log_root=log_root,
        max_parallel=max_parallel,
        timeout_seconds=timeout_seconds,
        launch_fn=_launch_background,
        fingerprint_fn=source_fingerprint,
    )


def run_background_child(
    name: str,
    command: Sequence[str],
    *,
    log_root: Path,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    source_fingerprint_value: str | None = None,
) -> int:
    return _run_background_child_impl(
        name,
        command,
        log_root=log_root,
        timeout_seconds=timeout_seconds,
        source_fingerprint_value=source_fingerprint_value,
        fingerprint_fn=source_fingerprint,
    )


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
