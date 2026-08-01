"""Own the affected milestone-renewal models, tests, rehearsals, and budget.

The ordinary execution mode is the single producer.  ``--verify-results`` is
strictly read-only: it checks the current source fingerprint and every child
result hash without running or backfilling a missing check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_milestone_renewal_affected_results.json"

INPUT_PATHS = (
    "simulations/flowpilot_route_replanning_policy_model.py",
    "simulations/run_flowpilot_route_replanning_policy_checks.py",
    "simulations/flowpilot_planning_quality_model.py",
    "simulations/run_flowpilot_planning_quality_checks.py",
    "simulations/flowpilot_route_mutation_activation_model.py",
    "simulations/run_flowpilot_route_mutation_activation_checks.py",
    "simulations/flowpilot_fake_project_rehearsal_cli.py",
    "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
    "simulations/run_flowpilot_milestone_renewal_longitudinal_rehearsal.py",
    "simulations/run_flowpilot_milestone_renewal_budget_checks.py",
    "simulations/run_flowpilot_milestone_renewal_affected_checks.py",
    "simulations/flowpilot_model_test_alignment_family_plans.py",
    "simulations/flowpilot_acceptance_testmesh_model.py",
    "simulations/flowpilot_053_ppa_maintenance_model.py",
    "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
    "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
    "skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
    "skills/flowpilot/assets/flowpilot_core_runtime/review_window_contracts.py",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/pm_flowguard_acceptance_review.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md",
    "tests/test_flowpilot_milestone_plan_renewal_contracts.py",
    "tests/test_flowpilot_recursive_route_execution_runtime.py",
    "tests/test_flowpilot_parent_entry_return_path.py",
    "tests/test_flowpilot_high_standard_control_flow.py",
    "tests/test_flowpilot_milestone_renewal_budget.py",
    "docs/flowpilot_milestone_renewal_budget.md",
    "scripts/test_tier/fast_commands.py",
    "skills/flowpilot/.skillguard/contract-source.json",
    "simulations/flowpilot_skillguard_contract_model.py",
    "tests/test_flowpilot_skillguard_deep_contract.py",
    "tests/test_flowpilot_test_tiers.py",
)

RESULT_PATHS = (
    "simulations/flowpilot_route_replanning_policy_results.json",
    "simulations/flowpilot_planning_quality_results.json",
    "simulations/flowpilot_route_mutation_activation_results.json",
    "simulations/flowpilot_milestone_renewal_longitudinal_rehearsal_results.json",
    "simulations/flowpilot_milestone_renewal_budget_results.json",
)

COMMANDS = (
    (
        "route_replanning_policy_model",
        (
            "python",
            "simulations/run_flowpilot_route_replanning_policy_checks.py",
            "--json-out",
            "simulations/flowpilot_route_replanning_policy_results.json",
        ),
        120,
    ),
    (
        "planning_quality_model",
        (
            "python",
            "simulations/run_flowpilot_planning_quality_checks.py",
            "--json-out",
            "simulations/flowpilot_planning_quality_results.json",
        ),
        120,
    ),
    (
        "route_mutation_activation_model",
        (
            "python",
            "simulations/run_flowpilot_route_mutation_activation_checks.py",
            "--json-out",
            "simulations/flowpilot_route_mutation_activation_results.json",
        ),
        120,
    ),
    (
        "affected_runtime_contract_tests",
        (
            "python",
            "-m",
            "pytest",
            "tests/test_flowpilot_milestone_plan_renewal_contracts.py",
            "tests/test_flowpilot_recursive_route_execution_runtime.py",
            "tests/test_flowpilot_parent_entry_return_path.py",
            "tests/test_flowpilot_high_standard_control_flow.py",
            "tests/test_flowpilot_milestone_renewal_budget.py",
            "-q",
        ),
        240,
    ),
    (
        "public_cli_longitudinal_rehearsal",
        (
            "python",
            "simulations/run_flowpilot_milestone_renewal_longitudinal_rehearsal.py",
        ),
        180,
    ),
    (
        "lightweight_budget_10_50_100",
        (
            "python",
            "simulations/run_flowpilot_milestone_renewal_budget_checks.py",
        ),
        120,
    ),
)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _file_hash(relative: str) -> str:
    return _sha256_bytes((REPO_ROOT / relative).read_bytes())


def _input_fingerprint() -> str:
    digest = hashlib.sha256()
    for relative in sorted(INPUT_PATHS):
        path = REPO_ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _portable_to_native(command: tuple[str, ...]) -> list[str]:
    return [sys.executable, *command[1:]]


def _run_checks() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for check_id, command, timeout_seconds in COMMANDS:
        try:
            completed = subprocess.run(
                _portable_to_native(command),
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout_seconds,
            )
            output = completed.stdout + completed.stderr
            rows.append(
                {
                    "check_id": check_id,
                    "command": list(command),
                    "exit_code": completed.returncode,
                    "status": "passed" if completed.returncode == 0 else "failed",
                    "output_sha256": _sha256_bytes(output.encode("utf-8")),
                    "output_tail": output[-4000:],
                }
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            rows.append(
                {
                    "check_id": check_id,
                    "command": list(command),
                    "exit_code": None,
                    "status": "timed_out",
                    "output_sha256": _sha256_bytes(str(output).encode("utf-8")),
                    "output_tail": str(output)[-4000:],
                }
            )
            break
        if rows[-1]["status"] != "passed":
            break
    complete = len(rows) == len(COMMANDS) and all(
        row["status"] == "passed" for row in rows
    )
    missing_results = [
        relative for relative in RESULT_PATHS if not (REPO_ROOT / relative).is_file()
    ]
    result_hashes = {
        relative: _file_hash(relative)
        for relative in RESULT_PATHS
        if (REPO_ROOT / relative).is_file()
    }
    return {
        "schema_version": "flowpilot.milestone_renewal_affected.v1",
        "ok": complete and not missing_results,
        "evidence_role": "single_current_affected_check_producer",
        "input_fingerprint": _input_fingerprint(),
        "input_paths": list(INPUT_PATHS),
        "checks": rows,
        "result_hashes": result_hashes,
        "missing_results": missing_results,
        "claim_boundary": (
            "This receipt proves the current deterministic models, affected ordinary tests, "
            "scripted public-CLI conformance, and local budget only. It does not prove live-AI "
            "planning quality, provider latency, installation, publication, or future behavior."
        ),
    }


def _verify_results() -> dict[str, Any]:
    failures: list[str] = []
    try:
        receipt = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        receipt = {}
        failures.append("missing_or_invalid_affected_receipt")
    if receipt.get("schema_version") != "flowpilot.milestone_renewal_affected.v1":
        failures.append("affected_receipt_schema_mismatch")
    if receipt.get("ok") is not True:
        failures.append("affected_receipt_not_terminal_success")
    try:
        current_fingerprint = _input_fingerprint()
    except OSError:
        current_fingerprint = ""
        failures.append("affected_input_missing")
    if receipt.get("input_fingerprint") != current_fingerprint:
        failures.append("affected_receipt_source_stale")
    expected_hashes = receipt.get("result_hashes")
    if not isinstance(expected_hashes, dict):
        failures.append("affected_receipt_result_hashes_missing")
        expected_hashes = {}
    for relative in RESULT_PATHS:
        path = REPO_ROOT / relative
        if not path.is_file():
            failures.append(f"affected_child_result_missing:{relative}")
            continue
        if expected_hashes.get(relative) != _file_hash(relative):
            failures.append(f"affected_child_result_stale:{relative}")
    return {
        "schema_version": "flowpilot.milestone_renewal_affected_verification.v1",
        "ok": not failures,
        "mode": "read_only_receipt_verification",
        "input_fingerprint": current_fingerprint,
        "failures": failures,
        "claim_boundary": (
            "This command is read-only. It neither executes missing checks nor rewrites or "
            "backfills the affected-check receipt."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--verify-results", action="store_true")
    args = parser.parse_args()
    if args.verify_results:
        result = _verify_results()
    else:
        result = _run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.verify_results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        temp = args.json_out.with_name(args.json_out.name + ".tmp")
        temp.write_text(output, encoding="utf-8")
        temp.replace(args.json_out)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
