"""Strict current execution-evidence helpers for FlowPilot model runners.

Model cells, source files, and JSON result files are declarations or artifacts;
none of them is passing execution evidence by itself.  This module consumes
FlowGuard ``ProofArtifactRef`` and ``TestResultReuseTicket`` rows emitted by the
background TestMesh compiler and keeps the proof boundary identical across the
Cartesian, ContractExhaustion, MTA, ModelMesh, and DevelopmentProcessFlow
consumers.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as importlib_metadata
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import flowguard as flowguard_module
from flowguard import (
    ProofArtifactRef,
    TestResultReuseTicket,
    proof_artifact_gap_codes,
    test_result_reuse_gap_codes,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTMESH_FINAL_RECEIPT_ARTIFACT_VERSION = "flowpilot.testmesh.final_receipt.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def read_json_object(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        return {}, "result artifact is missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, str(exc)
    if not isinstance(value, dict):
        return {}, "result artifact is not a JSON object"
    return value, ""


def _proof_rows(manifest: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    rows: list[tuple[str, Mapping[str, Any]]] = []
    routine = manifest.get("routine")
    if isinstance(routine, Mapping):
        for suite_id, row in sorted(routine.items(), key=lambda item: str(item[0])):
            if isinstance(row, Mapping):
                rows.append((str(suite_id), row))
    release = manifest.get("release")
    if isinstance(release, Mapping):
        rows.append(("release", release))
    return rows


def _coerce_reuse_ticket(value: Any) -> TestResultReuseTicket | None:
    if isinstance(value, TestResultReuseTicket):
        return value
    if isinstance(value, Mapping):
        return TestResultReuseTicket(**dict(value))
    return None


def _coerce_proof(value: Any) -> ProofArtifactRef | None:
    if isinstance(value, ProofArtifactRef):
        return value
    if isinstance(value, Mapping):
        return ProofArtifactRef(**dict(value))
    return None


def testmesh_receipt_obligation_ids(plan: Any, suite: Any) -> tuple[str, ...]:
    """Return the exact final-receipt coverage set used by FlowGuard TestMesh."""

    direct = (
        tuple(suite.owned_inventory_item_ids)
        or tuple(suite.owned_leaf_cell_ids)
        or tuple(suite.owned_coverage_shard_ids)
    )
    if direct:
        return tuple(dict.fromkeys(str(value) for value in direct if str(value)))
    return tuple(
        dict.fromkeys(
            str(item.item_id)
            for item in plan.partition_items
            if item.owner_suite_id == suite.suite_id and str(item.item_id)
        )
    )


def testmesh_final_receipt_fields(
    proof_artifact: ProofArtifactRef | Mapping[str, Any],
    *,
    covered_obligation_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Derive stable FlowGuard 0.55 final-receipt fields from concrete proof bytes."""

    proof = _coerce_proof(proof_artifact)
    if proof is None:
        raise ValueError("a proof artifact is required for a final receipt")
    covered = tuple(
        dict.fromkeys(
            str(value)
            for value in (covered_obligation_ids or proof.covered_obligation_ids)
            if str(value)
        )
    )
    fingerprint_payload = {
        "artifact_id": proof.artifact_id,
        "artifact_fingerprints": dict(sorted(proof.artifact_fingerprints.items())),
        "covered_obligation_ids": list(covered),
        "finished_at": proof.finished_at,
        "result_path": proof.result_path,
        "result_status": proof.result_status,
        "started_at": proof.started_at,
    }
    result_fingerprint = sha256_text(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"))
    )
    try:
        package_version = importlib_metadata.version("flowguard")
    except importlib_metadata.PackageNotFoundError:
        package_version = "unknown"
    schema_version = str(getattr(flowguard_module, "SCHEMA_VERSION", "unknown"))
    return {
        "run_id": f"{proof.artifact_id}:{result_fingerprint[:24]}",
        "terminal_status": proof.result_status,
        "result_fingerprint": result_fingerprint,
        "covered_obligation_ids": list(covered),
        "artifact_version": TESTMESH_FINAL_RECEIPT_ARTIFACT_VERSION,
        "verifier_version": f"flowguard-testmesh/{package_version}/schema-{schema_version}",
    }


def proof_bundle_report(
    manifest: Mapping[str, Any] | None,
    *,
    expected_source_fingerprint: str,
    required_scope: str = "routine",
) -> dict[str, Any]:
    """Validate current TestMesh proof rows without inventing execution counts."""

    if not isinstance(manifest, Mapping):
        return {
            "ok": False,
            "source_fingerprint_current": False,
            "proof_artifacts": [],
            "proof_artifact_ids": [],
            "selected_count": 0,
            "executed_count": 0,
            "test_count": 0,
            "count_unit": "background_child_commands",
            "failures": ["execution_evidence_manifest_missing"],
        }

    manifest_source = str(manifest.get("source_fingerprint") or "")
    source_current = bool(manifest_source) and manifest_source == expected_source_fingerprint
    rows = _proof_rows(manifest)
    if required_scope in {"release", "done", "publish"}:
        rows = [(suite_id, row) for suite_id, row in rows if suite_id == "release"]

    failures: list[str] = []
    proofs: list[ProofArtifactRef] = []
    selected_count = 0
    executed_count = 0
    for suite_id, row in rows:
        proof = _coerce_proof(row.get("proof_artifact"))
        declared_status = str(row.get("result_status") or "not_run")
        gaps = proof_artifact_gap_codes(
            proof,
            declared_status=declared_status,
            require_result_path=True,
            require_fingerprints=True,
            require_external_scope=True,
        )
        failures.extend(f"{suite_id}:{code}" for code, _message in gaps)
        row_selected = row.get("selected_count")
        if not isinstance(row_selected, int) and proof is not None:
            row_selected = proof.metadata.get("selected_child_command_count")
        row_executed = row.get("test_count")
        if not isinstance(row_executed, int) and proof is not None:
            row_executed = proof.metadata.get("executed_child_command_count")
        if not isinstance(row_selected, int) or row_selected < 0:
            failures.append(f"{suite_id}:selected_count_missing")
            row_selected = 0
        if not isinstance(row_executed, int) or row_executed < 0:
            failures.append(f"{suite_id}:executed_count_missing")
            row_executed = 0
        if row_executed > row_selected:
            failures.append(f"{suite_id}:executed_count_exceeds_selected")
        if proof is not None:
            result_reused = bool(row.get("result_reused")) or bool(proof.metadata.get("proof_reused"))
            ticket = _coerce_reuse_ticket(row.get("reuse_ticket"))
            if result_reused or ticket is not None:
                reuse_gaps = test_result_reuse_gap_codes(
                    ticket,
                    expected_evidence_id=proof.artifact_id,
                    required_obligation_ids=proof.covered_obligation_ids,
                )
                failures.extend(f"{suite_id}:{code}" for code, _message in reuse_gaps)
            proofs.append(proof)
        selected_count += row_selected
        executed_count += row_executed

    if not rows:
        failures.append(f"{required_scope}:required_proof_scope_missing")
    if not source_current:
        failures.append("source_fingerprint_stale")
    if selected_count <= 0 or executed_count <= 0:
        failures.append("current_command_execution_count_missing")

    return {
        "ok": not failures,
        "source_fingerprint_current": source_current,
        "expected_source_fingerprint": expected_source_fingerprint,
        "manifest_source_fingerprint": manifest_source,
        "proof_artifacts": [proof.to_dict() for proof in proofs],
        "proof_artifact_ids": [proof.artifact_id for proof in proofs],
        "selected_count": selected_count,
        "executed_count": executed_count,
        "test_count": executed_count,
        "count_unit": "background_child_commands",
        "failures": sorted(set(failures)),
    }


def derived_owner_proof(
    bundle: Mapping[str, Any],
    *,
    owner_id: str,
    covered_obligation_ids: Sequence[str],
) -> tuple[ProofArtifactRef | None, TestResultReuseTicket | None, tuple[str, ...]]:
    """Bind one owner to a current aggregate run through an explicit reuse ticket."""

    failures = tuple(str(item) for item in bundle.get("failures", ()))
    artifacts = bundle.get("proof_artifacts")
    if failures or not isinstance(artifacts, list) or not artifacts:
        return None, None, failures or ("proof_bundle_missing",)
    source_proofs = [ProofArtifactRef(**dict(row)) for row in artifacts if isinstance(row, Mapping)]
    if not source_proofs:
        return None, None, ("proof_bundle_missing",)
    source_fingerprints: dict[str, str] = {}
    for source in source_proofs:
        source_fingerprints.update(source.artifact_fingerprints)
    source_ids = tuple(source.artifact_id for source in source_proofs)
    obligations = tuple(str(value) for value in covered_obligation_ids if str(value))
    result_fingerprint = sha256_text("\n".join(sorted(source_fingerprints.values())))
    fingerprints = {
        "aggregate_proof_set_sha256": result_fingerprint,
        "source_tree_sha256": str(bundle.get("manifest_source_fingerprint") or ""),
    }
    command = " && ".join(source.command for source in source_proofs if source.command)
    result_path = "; ".join(source.result_path for source in source_proofs if source.result_path)
    proof = ProofArtifactRef(
        artifact_id=f"proof.owner.{owner_id}",
        producer_route="flowguard-test-mesh",
        command=command,
        result_path=result_path,
        result_status="passed",
        exit_code=0,
        started_at=min((source.started_at for source in source_proofs if source.started_at), default=""),
        finished_at=max((source.finished_at for source in source_proofs if source.finished_at), default=""),
        artifact_fingerprints=fingerprints,
        covered_obligation_ids=obligations,
        assertion_scope="external_contract",
        current=True,
        route_evidence_current=True,
        progress_only=False,
        metadata={
            "source_proof_artifact_ids": list(source_ids),
            "selected_count": int(bundle.get("selected_count") or 0),
            "executed_count": int(bundle.get("executed_count") or 0),
            "count_unit": str(bundle.get("count_unit") or "background_child_commands"),
        },
    )
    ticket = TestResultReuseTicket(
        evidence_id=owner_id,
        previous_evidence_id=source_ids[0],
        reason="current aggregate tier result is reused only for this declared owner scope",
        same_output_proof_id=source_ids[0],
        command_fingerprint=sha256_text(command),
        test_source_fingerprint=str(bundle.get("manifest_source_fingerprint") or ""),
        tested_artifact_fingerprint=str(bundle.get("expected_source_fingerprint") or ""),
        dependency_fingerprints={"aggregate_proof_set_sha256": result_fingerprint},
        environment_fingerprint=sha256_text("\n".join(source_ids)),
        result_fingerprint=result_fingerprint,
        covered_obligation_ids=obligations,
        metadata={"source_proof_artifact_ids": list(source_ids)},
    )
    gaps = test_result_reuse_gap_codes(
        ticket,
        expected_evidence_id=owner_id,
        required_obligation_ids=obligations,
    )
    return proof, ticket, tuple(code for code, _message in gaps)


def load_manifest(path: Path | None) -> tuple[dict[str, Any] | None, str]:
    if path is None:
        return None, "execution evidence manifest path was not provided"
    payload, error = read_json_object(path)
    return (payload if not error else None), error


__all__ = [
    "TESTMESH_FINAL_RECEIPT_ARTIFACT_VERSION",
    "derived_owner_proof",
    "load_manifest",
    "proof_bundle_report",
    "read_json_object",
    "sha256_file",
    "sha256_text",
    "testmesh_final_receipt_fields",
    "testmesh_receipt_obligation_ids",
]
