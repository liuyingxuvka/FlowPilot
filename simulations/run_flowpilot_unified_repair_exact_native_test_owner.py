"""Execute the one frozen exact native-test owner for unified repair.

This command is the sole execution owner for the eight-file pytest inventory.
The unified model runner and manifest builder only consume its terminal
machine result; they never invoke or relabel these tests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

try:  # pragma: no cover - package execution
    from . import run_flowpilot_unified_repair_integrity_checks as unified
except ImportError:  # pragma: no cover - direct script execution
    import run_flowpilot_unified_repair_integrity_checks as unified


RESULT_SCHEMA = "flowpilot.unified_repair_native_owner_result.v1"
CHECK_ID = "exact_native_test_conformance"
EXECUTION_OWNER = "native.unified_repair.exact_runtime_tests"
DEFAULT_RESULT_PATH = (
    unified.REPO_ROOT
    / "tmp"
    / "flowguard_background"
    / "unified_repair_exact_native_tests.json"
)
LOG_ROOT = unified.REPO_ROOT / "tmp" / "flowguard_background"


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(
            unified.REPO_ROOT.resolve()
        ).as_posix()
    except ValueError:
        return str(path.resolve())


def _command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        *(_relative(path) for path in unified.EXACT_RELEVANT_TEST_PATHS),
        "-q",
    ]


def _portable_command() -> list[str]:
    return [
        "python",
        "-m",
        "pytest",
        *(_relative(path) for path in unified.EXACT_RELEVANT_TEST_PATHS),
        "-q",
    ]


def run_owner(*, result_path: Path) -> dict[str, Any]:
    before = unified._source_fingerprints()
    missing = [
        str(row.get("path") or "")
        for value in before.values()
        for row in (
            value
            if isinstance(value, list)
            else [value]
        )
        if isinstance(row, dict) and row.get("exists") is not True
    ]
    command = _command()
    result_path = result_path.resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_ROOT / f"{result_path.stem}.out.txt"
    stderr_path = LOG_ROOT / f"{result_path.stem}.err.txt"

    if missing:
        completed_exit_code = 2
        stdout = ""
        stderr = (
            "missing exact unified-repair native test inputs: "
            + ", ".join(sorted(missing))
            + "\n"
        )
    else:
        completed = subprocess.run(
            command,
            cwd=unified.REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        completed_exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr

    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    after = unified._source_fingerprints()
    source_stable = before == after
    input_fingerprints = unified._flatten_fingerprint_groups(
        after,
        (
            "unified_runtime_sources",
            "exact_relevant_tests",
            "exact_native_test_owner",
        ),
    )
    ok = (
        completed_exit_code == 0
        and source_stable
        and not missing
    )
    return {
        "schema_version": RESULT_SCHEMA,
        "check_id": CHECK_ID,
        "execution_owner": EXECUTION_OWNER,
        "result_status": "passed" if ok else "failed",
        "exit_code": 0 if ok else completed_exit_code or 1,
        "terminal": True,
        "current": ok,
        "immutable": True,
        "command": " ".join(_portable_command()),
        "input_fingerprints": input_fingerprints,
        "source_fingerprints": after,
        "source_stable_during_execution": source_stable,
        "covered_obligation_ids": list(
            unified.UNIFIED_REPAIR_OBLIGATION_IDS
        ),
        "selected_test_paths": [
            _relative(path)
            for path in unified.EXACT_RELEVANT_TEST_PATHS
        ],
        "missing_input_paths": sorted(missing),
        "stdout_path": _relative(stdout_path),
        "stderr_path": _relative(stderr_path),
        "claim_boundary": (
            "This artifact proves the one frozen eight-file pytest owner "
            "completed against an unchanged input snapshot. It does not "
            "replace the separate direct runtime-conformance owner."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_RESULT_PATH,
    )
    args = parser.parse_args()
    result = run_owner(result_path=args.json_out)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["result_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
