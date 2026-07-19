"""Build the unified-repair evidence manifest from two native owner results.

This builder is read-only with respect to owner execution: it never imports
the product runtime, runs pytest, or invokes either owner command. It validates
their frozen terminal machine artifacts and projects exact immutable receipts
for the unified model runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - package execution
    from . import run_flowpilot_unified_repair_integrity_checks as unified
    from .run_flowpilot_unified_repair_exact_native_test_owner import (
        RESULT_SCHEMA as OWNER_RESULT_SCHEMA,
    )
except ImportError:  # pragma: no cover - direct script execution
    import run_flowpilot_unified_repair_integrity_checks as unified
    from run_flowpilot_unified_repair_exact_native_test_owner import (
        RESULT_SCHEMA as OWNER_RESULT_SCHEMA,
    )


RUNTIME_CHECK_ID = "native_runtime_conformance"
TEST_CHECK_ID = "exact_native_test_conformance"


def _artifact_path(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
        resolved.relative_to(unified.REPO_ROOT.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _load_owner_result(
    path: Path,
    *,
    check_id: str,
    expected_fingerprints: Mapping[str, str],
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    resolved = _artifact_path(path)
    if resolved is None or not resolved.is_file():
        return {}, [f"{check_id}:owner_result_missing_or_external"]
    try:
        loaded = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [f"{check_id}:owner_result_unreadable:{exc}"]
    if not isinstance(loaded, dict):
        return {}, [f"{check_id}:owner_result_not_object"]

    requirement = unified.REQUIRED_NATIVE_RECEIPTS[check_id]
    checks = (
        (
            "schema_mismatch",
            loaded.get("schema_version") != OWNER_RESULT_SCHEMA,
        ),
        ("check_id_mismatch", loaded.get("check_id") != check_id),
        (
            "execution_owner_mismatch",
            loaded.get("execution_owner")
            != requirement["execution_owner"],
        ),
        ("result_not_passed", loaded.get("result_status") != "passed"),
        ("exit_code_not_zero", loaded.get("exit_code") != 0),
        ("not_terminal", loaded.get("terminal") is not True),
        ("not_current", loaded.get("current") is not True),
        ("not_immutable", loaded.get("immutable") is not True),
        ("command_missing", not str(loaded.get("command") or "")),
        (
            "source_changed_during_execution",
            loaded.get("source_stable_during_execution") is not True,
        ),
        (
            "input_fingerprints_mismatch",
            loaded.get("input_fingerprints")
            != dict(expected_fingerprints),
        ),
        (
            "covered_obligation_ids_incomplete",
            not set(unified.UNIFIED_REPAIR_OBLIGATION_IDS).issubset(
                set(
                    unified._string_sequence(
                        loaded.get("covered_obligation_ids")
                    )
                )
            ),
        ),
    )
    failures.extend(
        f"{check_id}:{code}" for code, active in checks if active
    )
    return loaded, failures


def build_manifest(
    *,
    runtime_owner_result_path: Path,
    exact_test_owner_result_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    source_fingerprints = unified._source_fingerprints()
    failures: list[str] = []
    owner_inputs = {
        RUNTIME_CHECK_ID: runtime_owner_result_path,
        TEST_CHECK_ID: exact_test_owner_result_path,
    }
    owner_rows: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []

    for check_id, result_path in owner_inputs.items():
        requirement = unified.REQUIRED_NATIVE_RECEIPTS[check_id]
        expected_inputs = unified._flatten_fingerprint_groups(
            source_fingerprints,
            requirement["required_input_groups"],
        )
        owner_row, row_failures = _load_owner_result(
            result_path,
            check_id=check_id,
            expected_fingerprints=expected_inputs,
        )
        failures.extend(row_failures)
        owner_rows[check_id] = owner_row
        resolved = _artifact_path(result_path)
        if row_failures or resolved is None:
            continue
        receipt: dict[str, Any] = {
            "receipt_id": requirement["receipt_id"],
            "check_id": check_id,
            "execution_owner": requirement["execution_owner"],
            "terminal_status": "passed",
            "exit_code": 0,
            "current": True,
            "immutable": True,
            "command": str(owner_row["command"]),
            "input_fingerprints": expected_inputs,
            "covered_obligation_ids": list(
                unified.UNIFIED_REPAIR_OBLIGATION_IDS
            ),
            "result_path": resolved.relative_to(
                unified.REPO_ROOT.resolve()
            ).as_posix(),
            "result_sha256": hashlib.sha256(
                resolved.read_bytes()
            ).hexdigest(),
        }
        receipt["request_identity"] = (
            unified.native_receipt_request_identity(receipt)
        )
        receipts.append(receipt)

    runtime_typed = owner_rows.get(RUNTIME_CHECK_ID, {}).get(
        "typed_runtime_evidence"
    )
    typed_runtime_evidence = (
        [
            dict(row)
            for row in runtime_typed
            if isinstance(row, Mapping)
        ]
        if isinstance(runtime_typed, list)
        else []
    )
    if len(typed_runtime_evidence) != 1:
        failures.append(
            "native_runtime_conformance:"
            "typed_runtime_evidence_not_singular"
        )

    manifest = {
        "schema_version": unified.NATIVE_EVIDENCE_MANIFEST_SCHEMA,
        "model_id": unified.model.MODEL_ID,
        "receipts": receipts,
        "typed_runtime_evidence": typed_runtime_evidence,
        "builder": {
            "execution_mode": "read_only_owner_result_consumer",
            "owner_result_paths": {
                check_id: str(path)
                for check_id, path in owner_inputs.items()
            },
            "failures": sorted(set(failures)),
            "claim_boundary": (
                "The builder validates and hashes native owner results. It "
                "does not run either owner or create native evidence."
            ),
        },
    }
    if not failures:
        validation = unified._native_evidence_report(
            manifest,
            source_fingerprints,
        )
        if validation.get("ok") is not True:
            failures.extend(
                str(value)
                for value in validation.get("failures", [])
            )
            manifest["builder"]["failures"] = sorted(set(failures))
    return manifest, sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-owner-result",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--exact-test-owner-result",
        type=Path,
        required=True,
    )
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    manifest, failures = build_manifest(
        runtime_owner_result_path=args.runtime_owner_result,
        exact_test_owner_result_path=args.exact_test_owner_result,
    )
    output = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if failures:
        return 1
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
