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
from scripts.test_tier.evidence_v5 import (  # noqa: E402
    BACKGROUND_CHILD_META_SCHEMA_VERSION,
    load_json_object,
    resolve_artifact_path,
    sha256_file,
    sha256_json,
)
from scripts.test_tier.impact_resolution import (  # noqa: E402
    IMPACT_PLAN_SCHEMA_VERSION,
    build_owner_contracts,
    owner_identity,
)
from scripts.test_tier.source_fingerprint import source_snapshot  # noqa: E402


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
        name=name,
        command=tuple(command),
        description="Stable FlowGuard background-log owner.",
    )
    contract = build_owner_contracts((owner,))[0]
    return owner_identity(contract).to_dict()


def _write_current_impact_plan(
    *,
    name: str,
    command: Sequence[str],
    log_root: Path,
) -> tuple[Path, str]:
    identity = _current_owner_identity(name=name, command=command)
    owner_id = name
    plan_id = (
        f"flowguard-background:{name}:"
        f"{identity['command_fingerprint']}"
    )
    plan = {
        "schema_version": IMPACT_PLAN_SCHEMA_VERSION,
        "plan_id": plan_id,
        "requested_scope": "flowguard-background",
        "snapshot": source_snapshot(),
        "previous_manifest": {"path": "", "sha256": ""},
        "seed_baseline": True,
        "contracts": [],
        "decisions": [
            {
                "owner_id": owner_id,
                "action": "execute",
                "reason_codes": ["explicit_background_execution"],
                "identity": identity,
                "previous_proof_artifact_id": "",
                "previous_proof_ref": None,
                "reuse_ticket": None,
                "reuse_ticket_identity": "",
            }
        ],
        "blockers": [],
        "execute_owner_ids": [owner_id],
        "reuse_owner_ids": [],
    }
    plan_path = log_root / f"{name}.impact-plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return plan_path, sha256_file(plan_path)


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
    if meta.get("schema_version") != BACKGROUND_CHILD_META_SCHEMA_VERSION:
        failures.append("child_meta_not_current")
    if meta.get("owner_id") != name:
        failures.append("owner_id_mismatch")
    if meta.get("owner_identity_sha256") != sha256_json(expected_identity):
        failures.append("owner_identity_stale")
    if (
        meta.get("covered_input_fingerprint_end")
        != expected_identity["covered_input_fingerprint"]
    ):
        failures.append("covered_owner_inputs_stale")
    plan_ref = meta.get("impact_plan_ref")
    plan_path = log_root / f"{name}.impact-plan.json"
    if not isinstance(plan_ref, dict):
        failures.append("impact_plan_ref_missing")
    else:
        resolved_plan = resolve_artifact_path(
            ROOT,
            str(plan_ref.get("path") or ""),
        )
        if resolved_plan != plan_path.resolve():
            failures.append("impact_plan_path_mismatch")
        elif (
            not plan_path.is_file()
            or str(plan_ref.get("sha256") or "") != sha256_file(plan_path)
        ):
            failures.append("impact_plan_sha256_mismatch")
        else:
            plan = load_json_object(plan_path)
            decisions = [
                row
                for row in plan.get("decisions") or ()
                if isinstance(row, dict) and row.get("owner_id") == name
            ]
            if (
                len(decisions) != 1
                or decisions[0].get("action") != "execute"
                or decisions[0].get("identity") != expected_identity
            ):
                failures.append("impact_plan_owner_identity_stale")
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
    plan_path, plan_sha256 = _write_current_impact_plan(
        name=args.name,
        command=command,
        log_root=log_root,
    )
    return run_background_child(
        args.name,
        command,
        log_root=log_root,
        impact_plan_path=plan_path,
        impact_plan_sha256=plan_sha256,
        owner_id=args.name,
        timeout_seconds=max(0, args.timeout_seconds),
    )


if __name__ == "__main__":
    raise SystemExit(main())
