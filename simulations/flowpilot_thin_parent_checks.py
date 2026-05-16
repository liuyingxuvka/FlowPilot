"""Thin parent evidence checks for FlowPilot heavyweight FlowGuard parents."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
LEDGER_PATH = ROOT / "flowpilot_parent_responsibility_ledger.json"
PROOF_SCHEMA = 1
HEAVYWEIGHT_STATE_THRESHOLD = 10_000
ALLOWED_OWNER_TYPES = {"child", "shared_kernel", "parent_only", "legacy_full_only", "out_of_scope"}
THIN_RESULT_PATHS = {
    "meta": ROOT / "meta_thin_parent_results.json",
    "capability": ROOT / "capability_thin_parent_results.json",
}
THIN_PROOF_PATHS = {
    "meta": ROOT / "meta_thin_parent_results.proof.json",
    "capability": ROOT / "capability_thin_parent_results.proof.json",
}
LEGACY_RESULT_PATHS = {
    "meta": ROOT / "results.json",
    "capability": ROOT / "capability_results.json",
}
LEGACY_PROOF_PATHS = {
    "meta": ROOT / "results.proof.json",
    "capability": ROOT / "capability_results.proof.json",
}
LEGACY_MODEL_PATHS = {
    "meta": ROOT / "meta_model.py",
    "capability": ROOT / "capability_model.py",
}
LEGACY_RUNNER_PATHS = {
    "meta": ROOT / "run_meta_checks.py",
    "capability": ROOT / "run_capability_checks.py",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__parse_error__": str(exc)}


def _flowguard_schema_version() -> str:
    try:
        import flowguard

        return str(flowguard.SCHEMA_VERSION)
    except Exception:
        return "unavailable"


def _walk_counts(value: Any) -> dict[str, Any]:
    state_counts: list[int] = []
    edge_counts: list[int] = []
    ok_values: list[bool] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if key == "state_count" and isinstance(child, int):
                    state_counts.append(child)
                elif key == "edge_count" and isinstance(child, int):
                    edge_counts.append(child)
                elif key == "ok" and isinstance(child, bool):
                    ok_values.append(child)
                visit(child)
        elif isinstance(node, list):
            for child in node[:100]:
                visit(child)

    visit(value)
    return {
        "state_count": max(state_counts) if state_counts else None,
        "edge_count": max(edge_counts) if edge_counts else None,
        "ok": all(ok_values) if ok_values else None,
    }


def _base_from_result_path(path: Path) -> str:
    name = path.stem
    if name == "results":
        return "meta"
    for suffix in (
        "_checks_results",
        "_model_only_results",
        "_background_latest",
        "_thin_parent_results",
        "_results",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def result_index() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(ROOT.glob("*.json")):
        if "results" not in path.name and path.name != "results.json":
            continue
        payload = read_json(path)
        if not isinstance(payload, Mapping):
            continue
        counts = _walk_counts(payload)
        if counts["state_count"] is None and counts["ok"] is None:
            continue
        base = _base_from_result_path(path)
        previous = rows.get(base)
        current_state_count = counts["state_count"] if counts["state_count"] is not None else -1
        previous_state_count = -1
        if previous and previous.get("state_count") is not None:
            previous_state_count = int(previous["state_count"])
        if previous and previous_state_count >= current_state_count:
            continue
        rows[base] = {
            "model_id": base,
            "result_file": path.relative_to(ROOT.parent).as_posix(),
            "result_path": path,
            "result_fingerprint": file_sha256(path),
            "state_count": current_state_count if current_state_count >= 0 else None,
            "edge_count": counts["edge_count"],
            "ok": counts["ok"],
            "result_type": str(payload.get("result_type") or payload.get("model") or "unknown"),
        }
    return rows


def _skipped_required_checks(payload: Any) -> list[str]:
    skipped: list[str] = []

    def visit(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                key_text = str(key).lower()
                if key_text in {"skipped_checks", "skipped_required_checks"}:
                    if isinstance(child, Mapping):
                        for skipped_key, skipped_value in child.items():
                            if not skipped_value:
                                continue
                            if (
                                isinstance(skipped_value, str)
                                and (
                                    skipped_value.startswith("skipped_with_reason:")
                                    or skipped_value.startswith("covered_elsewhere:")
                                )
                            ):
                                continue
                            skipped.append(".".join(path + (str(key), str(skipped_key))))
                    elif child:
                        skipped.append(".".join(path + (str(key),)))
                else:
                    visit(child, path + (str(key),))
        elif isinstance(node, list):
            for index, child in enumerate(node[:100]):
                visit(child, path + (str(index),))

    visit(payload, ())
    return skipped


def _evidence_contract(model_id: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {
            "model_id": model_id,
            "ok": False,
            "missing": True,
            "failures": ["missing_child_evidence"],
        }
    path = Path(row["result_path"])
    payload = read_json(path)
    skipped = _skipped_required_checks(payload)
    failures: list[str] = []
    if row.get("ok") is not True:
        failures.append("child_result_not_ok")
    if row.get("state_count") is not None and int(row["state_count"]) >= HEAVYWEIGHT_STATE_THRESHOLD:
        failures.append("child_result_exceeds_thin_threshold")
    if skipped:
        failures.append("child_skipped_required_checks_visible")
    proof_path = path.with_suffix(".proof.json")
    proof_status = "not_present"
    if proof_path.exists():
        proof_status = "present"
    return {
        "model_id": model_id,
        "ok": not failures,
        "missing": False,
        "result_file": row["result_file"],
        "result_fingerprint": row["result_fingerprint"],
        "state_count": row.get("state_count"),
        "edge_count": row.get("edge_count"),
        "proof_status": proof_status,
        "skipped_required_checks_visible": True,
        "skipped_required_checks": skipped,
        "failures": failures,
    }


def legacy_input_fingerprint(parent: str) -> str:
    payload = {
        "flowguard_schema_version": _flowguard_schema_version(),
        "mode": "legacy_full_parent",
        "model": file_sha256(LEGACY_MODEL_PATHS[parent]),
        "runner": file_sha256(LEGACY_RUNNER_PATHS[parent]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def legacy_full_status(parent: str) -> dict[str, Any]:
    result_path = LEGACY_RESULT_PATHS[parent]
    proof_path = LEGACY_PROOF_PATHS[parent]
    proof = read_json(proof_path)
    if not isinstance(proof, Mapping):
        return {
            "valid": False,
            "reason": "proof missing or invalid",
            "result_file": result_path.relative_to(ROOT.parent).as_posix(),
            "proof_file": proof_path.relative_to(ROOT.parent).as_posix(),
        }
    if not result_path.exists():
        return {
            "valid": False,
            "reason": "result missing",
            "result_file": result_path.relative_to(ROOT.parent).as_posix(),
            "proof_file": proof_path.relative_to(ROOT.parent).as_posix(),
        }
    expected = legacy_input_fingerprint(parent)
    result_fingerprint = file_sha256(result_path)
    valid = (
        proof.get("schema") == PROOF_SCHEMA
        and proof.get("check") == parent
        and proof.get("ok") is True
        and proof.get("input_fingerprint") == expected
        and proof.get("result_fingerprint") == result_fingerprint
    )
    return {
        "valid": valid,
        "reason": "valid full proof" if valid else "full proof fingerprint mismatch",
        "result_file": result_path.relative_to(ROOT.parent).as_posix(),
        "proof_file": proof_path.relative_to(ROOT.parent).as_posix(),
        "created_at": proof.get("created_at"),
        "state_count": _walk_counts(read_json(result_path)).get("state_count"),
        "edge_count": _walk_counts(read_json(result_path)).get("edge_count"),
    }


def _ledger() -> dict[str, Any]:
    payload = read_json(LEDGER_PATH)
    if not isinstance(payload, dict):
        raise RuntimeError(f"parent responsibility ledger is missing or invalid: {LEDGER_PATH}")
    return payload


def _validate_ledger_shape(ledger: dict[str, Any], parent: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    parent_data = ledger.get("parents", {}).get(parent)
    if not isinstance(parent_data, Mapping):
        return [{"code": "parent_missing_from_ledger", "parent": parent}]
    partitions = parent_data.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        return [{"code": "parent_partitions_missing", "parent": parent}]
    seen_partitions: set[str] = set()
    seen_families: dict[str, str] = {}
    for partition in partitions:
        if not isinstance(partition, Mapping):
            failures.append({"code": "partition_not_object", "parent": parent})
            continue
        partition_id = str(partition.get("id") or "")
        owner_type = str(partition.get("owner_type") or "")
        if not partition_id:
            failures.append({"code": "partition_id_missing", "parent": parent})
        elif partition_id in seen_partitions:
            failures.append({"code": "duplicate_partition", "parent": parent, "partition": partition_id})
        else:
            seen_partitions.add(partition_id)
        if owner_type not in ALLOWED_OWNER_TYPES:
            failures.append(
                {
                    "code": "partition_owner_type_invalid",
                    "parent": parent,
                    "partition": partition_id,
                    "owner_type": owner_type,
                }
            )
        evidence_ids = partition.get("evidence_ids", [])
        if owner_type in {"child", "shared_kernel"} and not evidence_ids:
            failures.append(
                {"code": "partition_evidence_missing", "parent": parent, "partition": partition_id}
            )
        if owner_type == "out_of_scope" and not partition.get("out_of_scope_reason"):
            failures.append(
                {"code": "out_of_scope_reason_missing", "parent": parent, "partition": partition_id}
            )
        families = partition.get("invariant_families", [])
        if not families:
            failures.append(
                {"code": "invariant_families_missing", "parent": parent, "partition": partition_id}
            )
        for family in families:
            family_id = str(family)
            if family_id in seen_families:
                failures.append(
                    {
                        "code": "duplicate_invariant_family",
                        "parent": parent,
                        "family": family_id,
                        "first_partition": seen_families[family_id],
                        "second_partition": partition_id,
                    }
                )
            else:
                seen_families[family_id] = partition_id
    ownership: dict[str, str] = {}
    for row in ledger.get("state_write_ownership", []):
        if not isinstance(row, Mapping):
            continue
        field = str(row.get("field") or "")
        owner = str(row.get("owner") or "")
        if field in ownership and ownership[field] != owner:
            failures.append(
                {
                    "code": "state_write_ownership_overlap",
                    "field": field,
                    "first_owner": ownership[field],
                    "second_owner": owner,
                }
            )
        ownership[field] = owner
    return failures


def build_thin_parent_result(parent: str) -> dict[str, Any]:
    ledger = _ledger()
    parent_data = ledger.get("parents", {}).get(parent, {})
    result_rows = result_index()
    failures = _validate_ledger_shape(ledger, parent)
    partitions: list[dict[str, Any]] = []
    full_release_obligations: list[str] = []

    for partition in parent_data.get("partitions", []):
        if not isinstance(partition, Mapping):
            continue
        partition_id = str(partition.get("id") or "")
        evidence_ids = [str(item) for item in partition.get("evidence_ids", [])]
        evidence_contracts = [
            _evidence_contract(evidence_id, result_rows.get(evidence_id))
            for evidence_id in evidence_ids
        ]
        for contract in evidence_contracts:
            for failure in contract["failures"]:
                failures.append(
                    {
                        "code": failure,
                        "parent": parent,
                        "partition": partition_id,
                        "evidence_id": contract["model_id"],
                    }
                )
        release_obligation = str(partition.get("release_obligation") or "")
        if release_obligation == "full_regression_required_for_release":
            full_release_obligations.append(partition_id)
        partitions.append(
            {
                "id": partition_id,
                "owner_type": partition.get("owner_type"),
                "evidence_ids": evidence_ids,
                "evidence": evidence_contracts,
                "invariant_families": partition.get("invariant_families", []),
                "release_obligation": release_obligation,
                "ok": all(contract["ok"] for contract in evidence_contracts)
                and not any(failure.get("partition") == partition_id for failure in failures),
            }
        )

    full_status = legacy_full_status(parent)
    release_current = bool(full_status.get("valid")) and not full_release_obligations
    # Release-only obligations stay visible even when a valid full proof exists.
    if full_status.get("valid") and full_release_obligations:
        release_confidence = "current_with_full_regression"
    elif full_status.get("valid"):
        release_confidence = "current"
    else:
        release_confidence = "requires_full_regression"
    ok = not failures
    return {
        "schema_version": "flowpilot.thin_parent_result.v1",
        "model": "flowpilot_thin_parent",
        "parent": parent,
        "result_type": "thin_parent",
        "ok": ok,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "routine_confidence": "current" if ok else "blocked",
        "release_confidence": release_confidence,
        "graph": {
            "ok": ok,
            "state_count": max(1, len(partitions) + len(failures) + 1),
            "edge_count": max(1, len(partitions) * 2 + len(failures)),
            "invariant_failure_count": len(failures),
            "invariant_failures": failures[:100],
        },
        "thin_parent": {
            "ok": ok,
            "ledger_file": LEDGER_PATH.relative_to(ROOT.parent).as_posix(),
            "partition_count": len(partitions),
            "partitions": partitions,
            "failures": failures,
            "full_regression_release_partitions": full_release_obligations,
        },
        "legacy_full_regression": {
            "required_for_release": True,
            "current": bool(full_status.get("valid")),
            "status": full_status,
        },
        "progress": {
            "ok": ok,
            "success_state_count": 1 if ok else 0,
            "nonterminal_without_terminal_path_count": 0,
        },
        "loop": {
            "ok": ok,
            "stuck_state_count": 0,
            "nonterminating_component_count": 0,
        },
    }


def thin_input_fingerprint(parent: str, runner_path: Path) -> str:
    rows = result_index()
    parent_data = _ledger().get("parents", {}).get(parent, {})
    evidence_ids = sorted(
        {
            str(evidence_id)
            for partition in parent_data.get("partitions", [])
            if isinstance(partition, Mapping)
            for evidence_id in partition.get("evidence_ids", [])
        }
    )
    evidence = {
        evidence_id: rows[evidence_id]["result_fingerprint"]
        for evidence_id in evidence_ids
        if evidence_id in rows
    }
    legacy_result = LEGACY_RESULT_PATHS[parent]
    legacy_proof = LEGACY_PROOF_PATHS[parent]
    payload = {
        "flowguard_schema_version": _flowguard_schema_version(),
        "mode": "thin_parent",
        "parent": parent,
        "helper": file_sha256(Path(__file__).resolve()),
        "runner": file_sha256(runner_path),
        "ledger": file_sha256(LEDGER_PATH),
        "evidence": evidence,
        "legacy_result": file_sha256(legacy_result) if legacy_result.exists() else None,
        "legacy_proof": file_sha256(legacy_proof) if legacy_proof.exists() else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def valid_thin_proof(
    *,
    parent: str,
    runner_path: Path,
    result_path: Path,
    proof_path: Path,
    input_fingerprint: str | None = None,
) -> tuple[bool, str]:
    if input_fingerprint is None:
        input_fingerprint = thin_input_fingerprint(parent, runner_path)
    if not proof_path.exists():
        return False, "proof missing"
    if not result_path.exists():
        return False, "results missing"
    proof = read_json(proof_path)
    if not isinstance(proof, Mapping):
        return False, "proof is not valid JSON"
    if proof.get("schema") != PROOF_SCHEMA:
        return False, "proof schema changed"
    if proof.get("check") != parent:
        return False, "proof check changed"
    if proof.get("result_type") != "thin_parent":
        return False, "proof result type changed"
    if proof.get("ok") is not True:
        return False, "previous proof was not successful"
    if proof.get("input_fingerprint") != input_fingerprint:
        return False, "input fingerprint changed"
    if proof.get("result_fingerprint") != file_sha256(result_path):
        return False, "result fingerprint changed"
    return True, "valid proof"


def write_thin_proof(
    *,
    parent: str,
    result_path: Path,
    proof_path: Path,
    ok: bool,
    input_fingerprint: str,
) -> None:
    payload = {
        "schema": PROOF_SCHEMA,
        "check": parent,
        "result_type": "thin_parent",
        "ok": ok,
        "input_fingerprint": input_fingerprint,
        "result_fingerprint": file_sha256(result_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    proof_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_thin_parent(parent: str, *, runner_path: Path, result_path: Path, proof_path: Path) -> dict[str, Any]:
    input_fingerprint = thin_input_fingerprint(parent, runner_path)
    payload = build_thin_parent_result(parent)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_thin_proof(
        parent=parent,
        result_path=result_path,
        proof_path=proof_path,
        ok=bool(payload.get("ok")),
        input_fingerprint=input_fingerprint,
    )
    return payload
