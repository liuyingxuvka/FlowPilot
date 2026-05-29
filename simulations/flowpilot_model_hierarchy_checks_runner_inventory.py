"""Inventory and proof helpers for the FlowPilot model hierarchy checks runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import flowpilot_model_hierarchy_model as model
from flowpilot_thin_parent_checks import (
    LEDGER_PATH,
    THIN_PROOF_PATHS,
    THIN_RESULT_PATHS,
    release_regression_status,
    read_json,
    thin_input_fingerprint,
    valid_thin_proof,
)


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
HEAVYWEIGHT_STATE_THRESHOLD = model.HEAVYWEIGHT_STATE_THRESHOLD


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__parse_error__": str(exc)}


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
        "_results",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _is_canonical_result_path(path: Path) -> bool:
    return path.name.endswith("_results.json") and not path.name.endswith("_checks_results.json")


def _is_shadow_check_result_path(path: Path) -> bool:
    return path.name.endswith("_checks_results.json")


def _result_index() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(SIMULATIONS.glob("*.json")):
        if "results" not in path.name and path.name != "results.json":
            continue
        payload = _read_json(path)
        if not isinstance(payload, Mapping):
            continue
        counts = _walk_counts(payload)
        if counts["state_count"] is None and counts["ok"] is None:
            continue
        base = _base_from_result_path(path)
        previous = rows.get(base)
        if previous:
            previous_path = SIMULATIONS.parent / str(previous["result_file"])
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
            "result_file": path.relative_to(ROOT).as_posix(),
            "state_count": current_state_count if current_state_count >= 0 else None,
            "edge_count": counts["edge_count"],
            "ok": counts["ok"],
            "tier": _size_tier(counts["state_count"]),
        }
    return rows


def _result_row_from_path(path: Path, model_id: str) -> dict[str, Any] | None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        return None
    graph_payload = payload.get("graph") if payload.get("result_type") == "thin_parent" else None
    if isinstance(graph_payload, Mapping):
        counts = {
            "state_count": graph_payload.get("state_count"),
            "edge_count": graph_payload.get("edge_count"),
            "ok": graph_payload.get("ok"),
        }
    else:
        counts = _walk_counts(payload)
    if counts["state_count"] is None and counts["ok"] is None:
        return None
    return {
        "model_id": model_id,
        "result_file": path.relative_to(ROOT).as_posix(),
        "state_count": counts["state_count"],
        "edge_count": counts["edge_count"],
        "ok": counts["ok"],
        "tier": _size_tier(counts["state_count"]),
        "result_type": str(payload.get("result_type") or payload.get("model") or "unknown"),
        "release_confidence": payload.get("release_confidence"),
        "routine_confidence": payload.get("routine_confidence"),
    }


def _size_tier(state_count: int | None) -> str:
    if state_count is None:
        return "unknown"
    if state_count >= 100_000:
        return "huge"
    if state_count >= HEAVYWEIGHT_STATE_THRESHOLD:
        return "large"
    if state_count >= 1_000:
        return "medium"
    return "small"


def _thin_proof_status(parent: str) -> dict[str, Any]:
    if parent == "meta":
        runner_path = SIMULATIONS / "run_meta_checks.py"
    elif parent == "capability":
        runner_path = SIMULATIONS / "run_capability_checks.py"
    else:
        return {"valid": False, "reason": "unknown parent"}
    result_path = THIN_RESULT_PATHS[parent]
    proof_path = THIN_PROOF_PATHS[parent]
    proof = _read_json(proof_path)
    try:
        input_fingerprint = thin_input_fingerprint(parent, runner_path)
        valid, reason = valid_thin_proof(
            parent=parent,
            runner_path=runner_path,
            result_path=result_path,
            proof_path=proof_path,
            input_fingerprint=input_fingerprint,
        )
    except Exception as exc:
        valid = False
        reason = f"thin proof check failed: {exc}"
    row = {
        "valid": valid,
        "reason": reason,
        "proof_file": proof_path.relative_to(ROOT).as_posix(),
        "result_file": result_path.relative_to(ROOT).as_posix(),
    }
    if isinstance(proof, Mapping):
        row["created_at"] = proof.get("created_at")
        row["result_type"] = proof.get("result_type")
    return row


def _owner_label(parent: str, owner_type: str) -> str:
    if owner_type == "child":
        return parent
    return owner_type


def _partition_contracts_from_ledger() -> dict[str, Any]:
    ledger = read_json(LEDGER_PATH)
    if not isinstance(ledger, Mapping):
        return {
            "ok": False,
            "ledger_file": LEDGER_PATH.relative_to(ROOT).as_posix(),
            "parents": {},
            "by_partition": {},
            "state_write_ownership": [],
            "failures": ["ledger_missing_or_invalid"],
        }

    failures: list[str] = []
    parents: dict[str, dict[str, Any]] = {}
    by_partition: dict[str, dict[str, Any]] = {}
    ledger_parents = ledger.get("parents", {})
    if not isinstance(ledger_parents, Mapping):
        failures.append("ledger_parents_missing")
        ledger_parents = {}

    for parent in model.PARENT_MODELS:
        parent_data = ledger_parents.get(parent)
        if not isinstance(parent_data, Mapping):
            failures.append(f"{parent}:parent_missing")
            continue
        partitions = parent_data.get("partitions")
        if not isinstance(partitions, list):
            failures.append(f"{parent}:partitions_missing")
            continue
        parent_rows: dict[str, Any] = {}
        for partition in partitions:
            if not isinstance(partition, Mapping):
                failures.append(f"{parent}:partition_not_object")
                continue
            partition_id = str(partition.get("id") or "")
            if not partition_id:
                failures.append(f"{parent}:partition_id_missing")
                continue
            evidence_ids = [str(item) for item in partition.get("evidence_ids", [])]
            owner_type = str(partition.get("owner_type") or "")
            release_obligation = str(partition.get("release_obligation") or "")
            invariant_families = [str(item) for item in partition.get("invariant_families", [])]
            row = {
                "parent": parent,
                "owner_type": owner_type,
                "owner": _owner_label(parent, owner_type),
                "children": evidence_ids,
                "invariant_families": invariant_families,
                "release_obligation": release_obligation,
            }
            parent_rows[partition_id] = row

            aggregate = by_partition.setdefault(
                partition_id,
                {
                    "parents": [],
                    "owners": [],
                    "children": [],
                    "invariant_families": [],
                    "release_obligations": [],
                },
            )
            aggregate["parents"].append(parent)
            aggregate["owners"].append(row["owner"])
            aggregate["children"] = sorted(set(aggregate["children"]) | set(evidence_ids))
            aggregate["invariant_families"] = sorted(
                set(aggregate["invariant_families"]) | set(invariant_families)
            )
            if release_obligation:
                aggregate["release_obligations"] = sorted(
                    set(aggregate["release_obligations"]) | {release_obligation}
                )
        parents[parent] = parent_rows

    expected_partitions = set(model.PARTITION_ITEMS)
    actual_partitions = set(by_partition)
    missing = sorted(expected_partitions - actual_partitions)
    extra = sorted(actual_partitions - expected_partitions)
    if missing:
        failures.extend(f"partition_missing:{item}" for item in missing)
    if extra:
        failures.extend(f"partition_unknown:{item}" for item in extra)

    return {
        "ok": not failures,
        "ledger_file": LEDGER_PATH.relative_to(ROOT).as_posix(),
        "parents": parents,
        "by_partition": by_partition,
        "state_write_ownership": ledger.get("state_write_ownership", []),
        "missing_partition_items": missing,
        "unknown_partition_items": extra,
        "failures": failures,
    }


def build_inventory_report() -> dict[str, Any]:
    partition_contracts = _partition_contracts_from_ledger()
    results = _result_index()
    parent_rows: list[dict[str, Any]] = []
    for parent in model.PARENT_MODELS:
        thin_row = _result_row_from_path(THIN_RESULT_PATHS[parent], parent)
        release_status = release_regression_status(parent)
        thin_proof = _thin_proof_status(parent)
        row = dict(thin_row or results.get(parent, {"model_id": parent, "tier": "unknown"}))
        row["role"] = "thin_parent" if thin_row else "heavyweight_parent"
        row["thin_parent"] = {
            "result": thin_row,
            "proof": thin_proof,
        }
        row["layered_full_regression"] = {
            "proof": release_status,
            "current": bool(release_status.get("valid")),
        }
        row["split_review_required"] = (
            row.get("role") == "thin_parent"
        )
        row["proof"] = release_status
        row["release_confidence"] = (
            row.get("release_confidence")
            or ("current" if release_status.get("valid") else "requires_background_or_valid_proof")
        )
        row["routine_validation_command"] = f"python simulations/run_{parent}_checks.py --fast"
        row["release_validation_command"] = f"python simulations/run_{parent}_checks.py --full"
        parent_rows.append(row)

    child_ids = sorted(
        {
            child
            for parent_map in partition_contracts.get("parents", {}).values()
            for item in parent_map.values()
            for child in item["children"]
        }
    )
    child_rows = []
    for child in child_ids:
        row = dict(results.get(child, {"model_id": child, "tier": "unknown"}))
        row["role"] = "child_evidence"
        row["registered_in_partition"] = True
        child_rows.append(row)

    missing_children = sorted(child["model_id"] for child in child_rows if not child.get("result_file"))
    large_children = sorted(
        child["model_id"]
        for child in child_rows
        if child.get("state_count") is not None
        and child["state_count"] >= HEAVYWEIGHT_STATE_THRESHOLD
    )
    heavy_parent_obligations = [
        parent["model_id"]
        for parent in parent_rows
        if not parent.get("layered_full_regression", {}).get("current")
    ]
    thin_parent_obligations = [
        parent["model_id"]
        for parent in parent_rows
        if not parent.get("thin_parent", {}).get("proof", {}).get("valid")
    ]
    tier_counts: dict[str, int] = {}
    for child in child_rows:
        tier = str(child.get("tier") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    routine_ok = (
        partition_contracts.get("ok") is True
        and not large_children
        and not missing_children
        and not thin_parent_obligations
    )
    return {
        "ok": routine_ok,
        "evidence_contract_version": "flowpilot.parent_evidence_layers.v1",
        "heavyweight_threshold": HEAVYWEIGHT_STATE_THRESHOLD,
        "routine_confidence": "current" if routine_ok else "blocked",
        "routine_validation_commands": {
            "meta": "python simulations/run_meta_checks.py --fast",
            "capability": "python simulations/run_capability_checks.py --fast",
            "hierarchy": (
                "python simulations/run_flowpilot_model_hierarchy_checks.py "
                "--json-out simulations/flowpilot_model_hierarchy_results.json"
            ),
        },
        "release_validation_commands": {
            "meta": "python simulations/run_meta_checks.py --full",
            "capability": "python simulations/run_capability_checks.py --full",
        },
        "parents": parent_rows,
        "registered_child_count": len(child_rows),
        "registered_children": child_rows,
        "child_evidence_tier_counts": tier_counts,
        "missing_child_results": missing_children,
        "large_child_models": large_children,
        "thin_parent_obligations": thin_parent_obligations,
        "partition_contracts": partition_contracts,
        "partition_map": partition_contracts.get("by_partition", {}),
        "partition_items": list(model.PARTITION_ITEMS),
        "heavy_parent_full_regression_obligations": heavy_parent_obligations,
        "release_confidence": "current" if not heavy_parent_obligations else "requires_background_or_valid_proof",
    }
