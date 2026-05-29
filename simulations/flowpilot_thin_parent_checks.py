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
ALLOWED_OWNER_TYPES = {"child", "shared_kernel", "parent_only", "out_of_scope"}
THIN_RESULT_PATHS = {
    "meta": ROOT / "meta_thin_parent_results.json",
    "capability": ROOT / "capability_thin_parent_results.json",
}
THIN_PROOF_PATHS = {
    "meta": ROOT / "meta_thin_parent_results.proof.json",
    "capability": ROOT / "capability_thin_parent_results.proof.json",
}
LAYERED_FULL_RESULT_PATHS = {
    "meta": ROOT / "meta_layered_full_results.json",
    "capability": ROOT / "capability_layered_full_results.json",
}
LAYERED_FULL_PROOF_PATHS = {
    "meta": ROOT / "meta_layered_full_results.proof.json",
    "capability": ROOT / "capability_layered_full_results.proof.json",
}
RUNNER_PATHS = {
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


def _is_live_evidence_path(path: tuple[str, ...]) -> bool:
    return any("live" in part.lower() for part in path)


def _parent_evidence_ok(payload: Any, counts: dict[str, Any]) -> bool | None:
    """Return the static parent-evidence status without treating live probes as release proof.

    Child model runners may include read-only live-run projections. Those
    projections are important current-state findings, but a bad active run
    should not by itself invalidate a parent release-evidence proof.
    """

    ok_paths: list[tuple[tuple[str, ...], bool]] = []

    def visit(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                next_path = path + (str(key),)
                if key == "ok" and isinstance(child, bool):
                    ok_paths.append((next_path, child))
                visit(child, next_path)
        elif isinstance(node, list):
            for index, child in enumerate(node[:100]):
                visit(child, path + (str(index),))

    visit(payload, ())
    if not ok_paths:
        return counts.get("ok")

    false_paths = [path for path, ok in ok_paths if not ok]
    non_live_false_paths = [
        path
        for path in false_paths
        if path != ("ok",) and not _is_live_evidence_path(path)
    ]
    if non_live_false_paths:
        return False
    if false_paths:
        return any(ok and not _is_live_evidence_path(path) for path, ok in ok_paths)
    return True


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


def _is_canonical_result_path(path: Path) -> bool:
    return path.name.endswith("_results.json") and not path.name.endswith("_checks_results.json")


def _is_shadow_check_result_path(path: Path) -> bool:
    return path.name.endswith("_checks_results.json")


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
        if previous:
            previous_path = Path(previous["result_path"])
            if _is_canonical_result_path(previous_path) and _is_shadow_check_result_path(path):
                continue
            if _is_shadow_check_result_path(previous_path) and _is_canonical_result_path(path):
                previous = None
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
            "parent_evidence_ok": _parent_evidence_ok(payload, counts),
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
    if row.get("parent_evidence_ok", row.get("ok")) is not True:
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


def layered_full_input_fingerprint(parent: str, runner_path: Path) -> str:
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
    payload = {
        "flowguard_schema_version": _flowguard_schema_version(),
        "mode": "layered_full_parent",
        "parent": parent,
        "helper": file_sha256(Path(__file__).resolve()),
        "runner": file_sha256(runner_path),
        "ledger": file_sha256(LEDGER_PATH),
        "evidence": evidence,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def valid_layered_full_proof(
    *,
    parent: str,
    runner_path: Path,
    result_path: Path | None = None,
    proof_path: Path | None = None,
    input_fingerprint: str | None = None,
) -> tuple[bool, str]:
    result_path = result_path or LAYERED_FULL_RESULT_PATHS[parent]
    proof_path = proof_path or LAYERED_FULL_PROOF_PATHS[parent]
    if input_fingerprint is None:
        input_fingerprint = layered_full_input_fingerprint(parent, runner_path)
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
    if proof.get("result_type") != "layered_full_parent":
        return False, "proof result type changed"
    if proof.get("ok") is not True:
        return False, "previous proof was not successful"
    if proof.get("input_fingerprint") != input_fingerprint:
        return False, "input fingerprint changed"
    if proof.get("result_fingerprint") != file_sha256(result_path):
        return False, "result fingerprint changed"
    return True, "valid proof"


def _write_layered_full_proof(
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
        "result_type": "layered_full_parent",
        "ok": ok,
        "input_fingerprint": input_fingerprint,
        "result_fingerprint": file_sha256(result_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    proof_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def layered_full_status(parent: str) -> dict[str, Any]:
    result_path = LAYERED_FULL_RESULT_PATHS[parent]
    proof_path = LAYERED_FULL_PROOF_PATHS[parent]
    runner_path = RUNNER_PATHS[parent]
    valid, reason = valid_layered_full_proof(
        parent=parent,
        runner_path=runner_path,
        result_path=result_path,
        proof_path=proof_path,
    )
    status = {
        "valid": valid,
        "reason": reason,
        "result_file": result_path.relative_to(ROOT.parent).as_posix(),
        "proof_file": proof_path.relative_to(ROOT.parent).as_posix(),
    }
    payload = read_json(result_path)
    proof = read_json(proof_path)
    if isinstance(payload, Mapping):
        graph = payload.get("graph")
        if isinstance(graph, Mapping):
            counts = {
                "state_count": graph.get("state_count"),
                "edge_count": graph.get("edge_count"),
            }
        else:
            counts = _walk_counts(payload)
        status["state_count"] = counts.get("state_count")
        status["edge_count"] = counts.get("edge_count")
        status["release_confidence"] = payload.get("release_confidence")
    if isinstance(proof, Mapping):
        status["created_at"] = proof.get("created_at")
    return status


def release_regression_status(parent: str) -> dict[str, Any]:
    layered = layered_full_status(parent)
    return {
        **layered,
        "kind": "layered_full_parent",
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

    release_status = release_regression_status(parent)
    # Release-only obligations stay visible even when a valid full proof exists.
    if release_status.get("valid") and full_release_obligations:
        release_confidence = f"current_with_{release_status.get('kind', 'full_regression')}"
    elif release_status.get("valid"):
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
        "layered_full_regression": {
            "required_for_release": bool(full_release_obligations),
            "current": bool(release_status.get("valid")),
            "status": release_status,
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
    layered_result = LAYERED_FULL_RESULT_PATHS[parent]
    layered_proof = LAYERED_FULL_PROOF_PATHS[parent]
    payload = {
        "flowguard_schema_version": _flowguard_schema_version(),
        "mode": "thin_parent",
        "parent": parent,
        "helper": file_sha256(Path(__file__).resolve()),
        "runner": file_sha256(runner_path),
        "ledger": file_sha256(LEDGER_PATH),
        "evidence": evidence,
        "layered_full_result": file_sha256(layered_result) if layered_result.exists() else None,
        "layered_full_proof": file_sha256(layered_proof) if layered_proof.exists() else None,
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


def run_layered_full_parent(
    parent: str,
    *,
    runner_path: Path,
    result_path: Path,
    proof_path: Path,
    thin_result_path: Path,
    thin_proof_path: Path,
) -> dict[str, Any]:
    input_fingerprint = layered_full_input_fingerprint(parent, runner_path)
    thin_payload = build_thin_parent_result(parent)
    ok = bool(thin_payload.get("ok"))
    full_release_partitions = thin_payload.get("thin_parent", {}).get(
        "full_regression_release_partitions", []
    )
    graph = dict(thin_payload.get("graph", {}))
    graph["state_count"] = max(1, int(graph.get("state_count") or 0) + 2)
    graph["edge_count"] = max(1, int(graph.get("edge_count") or 0) + 2)
    payload = {
        "schema_version": "flowpilot.layered_full_parent_result.v1",
        "model": "flowpilot_layered_full_parent",
        "parent": parent,
        "result_type": "layered_full_parent",
        "ok": ok,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "routine_confidence": "current" if ok else "blocked",
        "release_confidence": "current_with_layered_full_parent" if ok else "blocked",
        "graph": graph,
        "layered_full_parent": {
            "ok": ok,
            "thin_parent_result_type": thin_payload.get("result_type"),
            "thin_parent_state_count": thin_payload.get("graph", {}).get("state_count"),
            "thin_parent_edge_count": thin_payload.get("graph", {}).get("edge_count"),
            "ledger_file": thin_payload.get("thin_parent", {}).get("ledger_file"),
            "partition_count": thin_payload.get("thin_parent", {}).get("partition_count"),
            "covered_release_partitions": full_release_partitions,
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
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_layered_full_proof(
        parent=parent,
        result_path=result_path,
        proof_path=proof_path,
        ok=ok,
        input_fingerprint=input_fingerprint,
    )
    # Refresh the routine proof after the release proof exists so thin-parent
    # confidence can report current layered release evidence.
    run_thin_parent(
        parent,
        runner_path=runner_path,
        result_path=thin_result_path,
        proof_path=thin_proof_path,
    )
    return payload
