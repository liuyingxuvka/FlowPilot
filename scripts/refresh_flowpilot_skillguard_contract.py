"""Compile and check FlowPilot's one current SkillGuard contract authority.

The maintained source is ``skills/flowpilot/.skillguard/contract-source.json``.
SkillGuard's official compiler owns ``compiled-contract.json`` and
``check-manifest.json``.  This helper never reconstructs a former work
contract and never creates a parallel FlowPilot execution route.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "skills" / "flowpilot"


def _skillguard_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return (codex_home / "skills" / "skillguard").resolve()


def _run_json(command: list[str]) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {
            "decision": "fail",
            "failures": ["tool_output_not_json"],
            "stdout": stdout,
        }
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    payload["exit_code"] = completed.returncode
    return completed.returncode, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skillguard-root", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check generated parity and current authority without writing.",
    )
    args = parser.parse_args()

    skillguard_root = _skillguard_root(args.skillguard_root)
    compiler = skillguard_root / "scripts" / "skillguard_compile.py"
    cli = skillguard_root / "scripts" / "skillguard.py"
    missing = [str(path) for path in (compiler, cli) if not path.is_file()]
    if missing:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "blocked",
                    "failures": ["skillguard_current_toolchain_missing"],
                    "missing": missing,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    target_arg = TARGET.relative_to(ROOT).as_posix()
    results: dict[str, Any] = {}
    ok = True

    if not args.check:
        compile_command = [
            sys.executable,
            str(compiler),
            target_arg,
            "--repository-root",
            str(ROOT),
        ]
        exit_code, payload = _run_json(compile_command)
        results["compile"] = payload
        ok = ok and exit_code == 0 and payload.get("ok") is True

    contract_command = [
        sys.executable,
        str(cli),
        "check-contract",
        "--target",
        target_arg,
        "--repository-root",
        str(ROOT),
    ]
    contract_exit, contract_payload = _run_json(contract_command)
    results["contract"] = contract_payload
    ok = ok and contract_exit == 0 and contract_payload.get("decision") == "pass"

    depth_command = [
        sys.executable,
        str(cli),
        "check-depth",
        "--target",
        target_arg,
        "--target-root",
        str(ROOT),
    ]
    depth_exit, depth_payload = _run_json(depth_command)
    results["depth"] = depth_payload
    ok = ok and depth_exit == 0 and depth_payload.get("decision") == "pass"

    contract_hash = str(
        contract_payload.get("contract_hash")
        or depth_payload.get("contract_hash")
        or ""
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "status": "current" if ok else "blocked",
                "mode": "check" if args.check else "compile",
                "target": target_arg,
                "contract_hash": contract_hash,
                "results": results,
                "claim_boundary": (
                    "This helper proves current source/compiled/manifest parity and "
                    "contract-depth mapping only. It does not execute FlowPilot, prove "
                    "execution depth, reuse stale parent evidence, or replace native closure."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
