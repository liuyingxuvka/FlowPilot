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
import sys
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import flowguard as flowguard_module
from flowguard import (
    ProofArtifactRef,
    TestResultReuseTicket,
    proof_artifact_gap_codes,
    test_result_reuse_gap_codes,
)
from scripts.test_tier.evidence_v5 import sha256_json
from scripts.test_tier.impact_resolution import (
    _current_reuse_ticket,
    validate_owner_reference,
)
TESTMESH_FINAL_RECEIPT_ARTIFACT_VERSION = "flowpilot.testmesh.final_receipt.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_source_file_fingerprint(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix in {".py", ".md", ".json"}:
        text = data.decode("utf-8-sig")
        data = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


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
            "snapshot_fingerprint_matches": False,
            "owners": {},
            "owner_failures": {},
            "proof_artifacts": [],
            "proof_artifact_ids": [],
            "selected_count": 0,
            "executed_count": 0,
            "test_count": 0,
            "count_unit": "background_child_commands",
            "failures": ["execution_evidence_manifest_missing"],
        }

    if manifest.get("schema_version") != "flowpilot.acceptance_testmesh_evidence_manifest.v5":
        failure = (
            "execution_evidence_manifest_v4_rejected"
            if manifest.get("schema_version")
            == "flowpilot.acceptance_testmesh_evidence_manifest.v4"
            else "execution_evidence_manifest_not_current_v5"
        )
        return {
            "ok": False,
            "snapshot_fingerprint_matches": False,
            "owners": {},
            "owner_failures": {},
            "proof_artifacts": [],
            "proof_artifact_ids": [],
            "selected_count": 0,
            "executed_count": 0,
            "reused_count": 0,
            "test_count": 0,
            "count_unit": "background_child_commands",
            "failures": [failure],
        }
    snapshot = manifest.get("snapshot")
    manifest_snapshot = (
        str(snapshot.get("fingerprint") or "")
        if isinstance(snapshot, Mapping)
        else ""
    )
    snapshot_matches = (
        bool(manifest_snapshot)
        and manifest_snapshot == expected_source_fingerprint
    )
    owners = manifest.get("owners")
    if not isinstance(owners, Mapping):
        owners = {}
    owner_failures: dict[str, list[str]] = {}
    resolved_owners: dict[str, dict[str, Any]] = {}
    for owner_id, owner_row in owners.items():
        row_failures: list[str] = []
        if not isinstance(owner_row, Mapping):
            owner_failures[str(owner_id)] = ["owner_row_invalid"]
            continue
        try:
            resolved = validate_owner_reference(
                owner_row,
                expected_owner_id=str(owner_id),
            )
        except (TypeError, ValueError) as exc:
            owner_failures[str(owner_id)] = [str(exc)]
            continue
        identity = resolved.identity
        covered_inputs = (
            identity.get("covered_input_fingerprints")
            if isinstance(identity, Mapping)
            else None
        )
        if not isinstance(covered_inputs, Mapping) or not covered_inputs:
            row_failures.append("owner_covered_inputs_missing")
        else:
            for relative, expected in covered_inputs.items():
                path = REPO_ROOT / str(relative)
                if (
                    not path.is_file()
                    or canonical_source_file_fingerprint(path) != str(expected)
                ):
                    row_failures.append(f"owner_input_stale:{relative}")
        proof = resolved.proof
        proof_gaps = proof_artifact_gap_codes(
            proof,
            declared_status=str(owner_row.get("result_status") or ""),
            require_result_path=True,
            require_fingerprints=True,
            require_external_scope=True,
        )
        row_failures.extend(code for code, _ in proof_gaps)
        ticket = None
        if owner_row.get("result_reused") is True:
            from scripts.test_tier.impact_resolution import OwnerIdentity

            try:
                current_identity = OwnerIdentity(
                    command_fingerprint=str(identity["command_fingerprint"]),
                    test_source_fingerprint=str(
                        identity["test_source_fingerprint"]
                    ),
                    tested_artifact_fingerprint=str(
                        identity["tested_artifact_fingerprint"]
                    ),
                    dependency_fingerprints=dict(
                        identity["dependency_fingerprints"]
                    ),
                    environment_fingerprint=str(
                        identity["environment_fingerprint"]
                    ),
                    covered_input_fingerprint=str(
                        identity["covered_input_fingerprint"]
                    ),
                    covered_input_fingerprints=dict(
                        identity["covered_input_fingerprints"]
                    ),
                    covered_obligation_ids=tuple(
                        identity.get("covered_obligation_ids") or ()
                    ),
                    covered_evidence_ids=tuple(
                        identity.get("covered_evidence_ids") or ()
                    ),
                )
            except (KeyError, TypeError, ValueError):
                current_identity = None
                row_failures.append("owner_identity_invalid")
            ticket = (
                _current_reuse_ticket(
                    str(owner_id),
                    resolved,
                    current_identity,
                )
                if current_identity is not None
                else None
            )
            row_failures.extend(
                code
                for code, _ in test_result_reuse_gap_codes(
                    ticket,
                    expected_evidence_id=str(owner_id),
                    required_obligation_ids=(
                        proof.covered_obligation_ids if proof is not None else ()
                    ),
                )
            )
            ticket_ref = owner_row.get("reuse_ticket_ref")
            if not isinstance(ticket_ref, Mapping):
                row_failures.append("reuse_ticket_ref_missing")
            elif ticket is not None and ticket_ref.get("identity") != sha256_json(
                ticket.to_dict()
            ):
                row_failures.append("reuse_ticket_ref_stale")
        resolved_owners[str(owner_id)] = {
            "owner_id": str(owner_id),
            "result_status": proof.result_status,
            "result_reused": owner_row.get("result_reused") is True,
            "identity": dict(identity),
            "result_fingerprint": resolved.result_fingerprint,
            "proof_artifact": proof.to_dict(),
            "reuse_ticket": ticket.to_dict() if ticket is not None else None,
        }
        if row_failures:
            owner_failures[str(owner_id)] = sorted(set(row_failures))
    rows = _proof_rows(manifest)
    if required_scope in {"release", "done", "publish"}:
        rows = [(suite_id, row) for suite_id, row in rows if suite_id == "release"]

    failures: list[str] = []
    proofs: list[ProofArtifactRef] = []
    selected_count = 0
    executed_count = 0
    reused_count = 0
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
        if row.get("result_reused") is True:
            reuse_ticket = _coerce_reuse_ticket(row.get("reuse_ticket"))
            failures.extend(
                f"{suite_id}:{code}"
                for code, _message in test_result_reuse_gap_codes(
                    reuse_ticket,
                    expected_evidence_id=suite_id,
                    required_obligation_ids=(
                        proof.covered_obligation_ids if proof is not None else ()
                    ),
                )
            )
        row_selected = row.get("selected_count")
        if not isinstance(row_selected, int) and proof is not None:
            row_selected = proof.metadata.get("selected_child_command_count")
        row_proof_backed = row.get("test_count")
        if not isinstance(row_proof_backed, int) and proof is not None:
            row_proof_backed = proof.metadata.get("proof_backed_child_command_count")
        if not isinstance(row_selected, int) or row_selected < 0:
            failures.append(f"{suite_id}:selected_count_missing")
            row_selected = 0
        if not isinstance(row_proof_backed, int) or row_proof_backed < 0:
            failures.append(f"{suite_id}:proof_backed_count_missing")
            row_proof_backed = 0
        if row_proof_backed > row_selected:
            failures.append(f"{suite_id}:proof_backed_count_exceeds_selected")
        if proof is not None:
            owner_ids = row.get("owner_evidence_ids")
            if not isinstance(owner_ids, list) or not owner_ids:
                failures.append(f"{suite_id}:owner_evidence_ids_missing")
                owner_ids = []
            for owner_id in owner_ids:
                if str(owner_id) not in resolved_owners:
                    failures.append(f"{suite_id}:owner_proof_missing:{owner_id}")
                for code in owner_failures.get(str(owner_id), ()):
                    failures.append(f"{suite_id}:{owner_id}:{code}")
            proofs.append(proof)
        row_reused = 0
        if proof is not None:
            row_reused = int(proof.metadata.get("reused_child_command_count") or 0)
        selected_count += row_selected
        executed_count += row_proof_backed
        reused_count += row_reused

    if not rows:
        failures.append(f"{required_scope}:required_proof_scope_missing")
    if selected_count <= 0 or executed_count + reused_count <= 0:
        failures.append("current_owner_evidence_count_missing")

    return {
        "ok": not failures,
        "snapshot_fingerprint_matches": snapshot_matches,
        "expected_source_fingerprint": expected_source_fingerprint,
        "manifest_snapshot_fingerprint": manifest_snapshot,
        "owners": resolved_owners,
        "owner_failures": owner_failures,
        "proof_artifacts": [proof.to_dict() for proof in proofs],
        "proof_artifact_ids": [proof.artifact_id for proof in proofs],
        "selected_count": selected_count,
        "executed_count": executed_count,
        "current_execution_count": sum(
            int(
                proof.get("metadata", {}).get("executed_child_command_count") or 0
            )
            for proof in [
                row.get("proof_artifact")
                for _suite_id, row in rows
                if isinstance(row, Mapping)
            ]
            if isinstance(proof, Mapping)
        ),
        "reused_count": reused_count,
        "test_count": executed_count,
        "count_unit": "background_child_commands",
        "failures": sorted(set(failures)),
    }


def derived_owner_proof(
    bundle: Mapping[str, Any],
    *,
    owner_id: str,
    covered_obligation_ids: Sequence[str],
    projected_evidence_id: str = "",
) -> tuple[ProofArtifactRef | None, TestResultReuseTicket | None, tuple[str, ...]]:
    """Return one exact current owner proof; aggregate fallback is forbidden."""

    failures = tuple(str(item) for item in bundle.get("failures", ()))
    owners = bundle.get("owners")
    owner_failures = bundle.get("owner_failures")
    if failures or not isinstance(owners, Mapping):
        return None, None, failures or ("owner_proof_bundle_missing",)
    owner_row = owners.get(owner_id)
    if not isinstance(owner_row, Mapping):
        return None, None, ("owner_proof_missing",)
    exact_failures = (
        tuple(str(value) for value in owner_failures.get(owner_id, ()))
        if isinstance(owner_failures, Mapping)
        else ()
    )
    if exact_failures:
        return None, None, exact_failures
    proof = _coerce_proof(owner_row.get("proof_artifact"))
    if proof is None:
        return None, None, ("owner_proof_missing",)
    obligations = tuple(str(value) for value in covered_obligation_ids if str(value))
    identity = owner_row.get("identity")
    if not isinstance(identity, Mapping):
        return None, None, ("owner_identity_missing",)
    result_fingerprint = str(owner_row.get("result_fingerprint") or "")
    source_ticket = _coerce_reuse_ticket(owner_row.get("reuse_ticket"))
    target_evidence_id = projected_evidence_id or owner_id
    ticket = TestResultReuseTicket(
        evidence_id=target_evidence_id,
        previous_evidence_id=proof.artifact_id,
        reason="current exact owner proof is projected to one declared evidence subject",
        same_output_proof_id=proof.artifact_id,
        command_fingerprint=str(identity.get("command_fingerprint") or ""),
        test_source_fingerprint=str(identity.get("test_source_fingerprint") or ""),
        tested_artifact_fingerprint=str(identity.get("tested_artifact_fingerprint") or ""),
        dependency_fingerprints=dict(identity.get("dependency_fingerprints") or {}),
        environment_fingerprint=str(identity.get("environment_fingerprint") or ""),
        result_fingerprint=result_fingerprint,
        covered_obligation_ids=obligations,
        metadata={
            "source_owner_id": owner_id,
            "source_proof_artifact_id": proof.artifact_id,
            "source_reuse_ticket_evidence_id": (
                source_ticket.evidence_id if source_ticket is not None else ""
            ),
        },
    )
    gaps = test_result_reuse_gap_codes(
        ticket,
        expected_evidence_id=target_evidence_id,
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
