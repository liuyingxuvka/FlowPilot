"""Run one FlowGuard command with the repository's stable background-log contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_test_tier import (  # noqa: E402
    DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    artifact_paths,
    classify_background_artifact,
    clear_artifacts,
    run_background_child,
)
from scripts.test_tier.command_builders import TierCommand  # noqa: E402
from scripts.test_tier.impact_resolution import (  # noqa: E402
    build_owner_contracts,
    owner_identity,
)


DEFAULT_LOG_ROOT = ROOT / "tmp" / "flowguard_background"


def _command_from_remainder(values: Sequence[str]) -> tuple[str, ...]:
    command = list(values)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise ValueError("a command is required after --")
    if command[0] == "python":
        command[0] = sys.executable
    return tuple(command)


def _current_owner_identity(
    *,
    name: str,
    command: Sequence[str],
) -> dict[str, object]:
    owner = TierCommand(
        name=f"flowguard_background_{name}",
        command=tuple(command),
        description="Stable FlowGuard background-log owner.",
    )
    contract = build_owner_contracts((owner,))[0]
    return owner_identity(contract).to_dict()


def verify_existing_background_command(
    *,
    name: str,
    command: Sequence[str],
    log_root: Path,
) -> dict[str, object]:
    expected_identity = _current_owner_identity(name=name, command=command)
    paths = artifact_paths(log_root, name)
    failures: list[str] = []
    missing = [key for key, path in paths.items() if not path.is_file()]
    if missing:
        failures.append("missing_artifacts:" + ",".join(sorted(missing)))
    meta: dict[str, object] = {}
    if paths["meta"].is_file():
        try:
            value = json.loads(paths["meta"].read_text(encoding="utf-8-sig"))
            if isinstance(value, dict):
                meta = value
            else:
                failures.append("invalid_meta:not_object")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"invalid_meta:{type(exc).__name__}")
    if list(meta.get("command") or []) != list(command):
        failures.append("command_mismatch")
    if meta.get("owner_identity") != expected_identity:
        failures.append("owner_identity_stale")
    if (
        meta.get("covered_input_fingerprints_end")
        != expected_identity["covered_input_fingerprints"]
    ):
        failures.append("covered_owner_inputs_stale")
    if meta.get("inputs_current") is not True:
        failures.append("owner_inputs_not_current")
    evidence = classify_background_artifact(log_root, name)
    if evidence.get("status") != "passed" or not evidence.get("ok"):
        failures.append(f"evidence_not_passed:{evidence.get('status')}")
    return {
        "ok": not failures,
        "name": name,
        "command": list(command),
        "log_root": str(log_root),
        "owner_input_fingerprint": expected_identity[
            "covered_input_fingerprint"
        ],
        "status": evidence.get("status"),
        "failures": sorted(set(failures)),
        "artifacts": evidence.get("artifacts"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Stable artifact base name.")
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing final artifacts without launching or rewriting the command.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        help="Maximum command runtime; zero disables the timeout.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    try:
        command = _command_from_remainder(args.command)
    except ValueError as exc:
        parser.error(str(exc))

    log_root = args.log_root
    if not log_root.is_absolute():
        log_root = ROOT / log_root
    if args.verify:
        report = verify_existing_background_command(
            name=args.name,
            command=command,
            log_root=log_root,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1
    paths = artifact_paths(log_root, args.name)
    clear_artifacts(paths)
    identity = _current_owner_identity(name=args.name, command=command)
    return run_background_child(
        args.name,
        command,
        log_root=log_root,
        impact_plan_id=(
            f"flowguard-background:{args.name}:"
            f"{identity['command_fingerprint']}"
        ),
        owner_identity_value=identity,
        timeout_seconds=max(0, args.timeout_seconds),
    )


if __name__ == "__main__":
    raise SystemExit(main())
