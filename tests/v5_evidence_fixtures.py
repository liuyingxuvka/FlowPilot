"""Small, real V5 owner-proof fixtures shared by evidence consumer tests."""

from __future__ import annotations

import atexit
import hashlib
import json
import shutil
import sys
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from flowguard import ProofArtifactRef
from scripts.test_tier import evidence_v5, impact_resolution
from scripts.test_tier.source_fingerprint import file_fingerprint, source_snapshot


ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_ROOT = Path(tempfile.mkdtemp(prefix="flowpilot-v5-evidence-fixtures-"))
atexit.register(shutil.rmtree, _FIXTURE_ROOT, True)


@lru_cache(maxsize=1)
def _current_snapshot() -> dict[str, object]:
    return source_snapshot()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def current_v5_manifest(
    owner_ids: Iterable[str],
    *,
    source_path: Path,
    selected_count: int | None = None,
    release: bool = False,
    reused_without_ticket: bool = False,
    suite_id: str = "all",
    aggregate_artifact_id: str = "proof.fixture.current-v5",
    aggregate_obligation_ids: Sequence[str] = ("current-tests",),
    owner_identities: Mapping[str, Mapping[str, Any]] | None = None,
    owner_commands: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, object]:
    """Build compact owner refs backed by real plan, stream, index, and meta files."""

    normalized_owner_ids = sorted({str(value) for value in owner_ids if str(value)})
    if not normalized_owner_ids:
        raise ValueError("a V5 evidence fixture requires at least one owner")
    selected = len(normalized_owner_ids) if selected_count is None else selected_count
    relative_input = source_path.resolve().relative_to(ROOT).as_posix()
    input_fingerprint = file_fingerprint(source_path.resolve())
    fixture_root = _FIXTURE_ROOT / uuid.uuid4().hex
    fixture_root.mkdir(parents=True)
    plan_path = fixture_root / "impact-plan.json"
    plan_id = f"fixture-plan-{uuid.uuid4().hex}"

    identities: dict[str, dict[str, Any]] = {}
    decisions: list[dict[str, Any]] = []
    for owner_id in normalized_owner_ids:
        supplied_identity = (
            owner_identities.get(owner_id)
            if owner_identities is not None
            else None
        )
        identity = (
            dict(supplied_identity)
            if isinstance(supplied_identity, Mapping)
            else {
                "command_fingerprint": _sha256_text(
                    f"fixture-command:{owner_id}"
                ),
                "test_source_fingerprint": input_fingerprint,
                "tested_artifact_fingerprint": input_fingerprint,
                "dependency_fingerprints": {"fixture": input_fingerprint},
                "environment_fingerprint": _sha256_text(
                    f"{sys.executable}:{sys.version_info[:3]}"
                ),
                "covered_input_fingerprint": input_fingerprint,
                "covered_input_fingerprints": {
                    relative_input: input_fingerprint,
                },
                "covered_obligation_ids": [f"owner:{owner_id}"],
                "covered_evidence_ids": [],
            }
        )
        identities[owner_id] = identity
        decisions.append(
            {
                "owner_id": owner_id,
                "action": "execute",
                "reason_codes": ["fixture_current_execution"],
                "identity": identity,
                "previous_proof_artifact_id": "",
                "previous_proof_ref": None,
                "reuse_ticket": None,
                "reuse_ticket_identity": "",
            }
        )
    plan = {
        "schema_version": impact_resolution.IMPACT_PLAN_SCHEMA_VERSION,
        "plan_id": plan_id,
        "requested_scope": "release" if release else "all",
        "snapshot": _current_snapshot(),
        "previous_manifest": {"path": "", "sha256": ""},
        "seed_baseline": True,
        "contracts": [],
        "decisions": decisions,
        "blockers": [],
        "execute_owner_ids": normalized_owner_ids,
        "reuse_owner_ids": [],
    }
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    plan_ref = {
        **evidence_v5.path_reference(plan_path, root=ROOT),
        "plan_id": plan_id,
    }

    owners: dict[str, object] = {}
    for owner_id in normalized_owner_ids:
        owner_root = fixture_root / owner_id.replace("/", "_").replace("\\", "_")
        owner_root.mkdir()
        out_path = owner_root / "owner.out.txt"
        err_path = owner_root / "owner.err.txt"
        combined_path = owner_root / "owner.combined.txt"
        meta_path = owner_root / "owner.meta.json"
        out_path.write_text(f"current V5 proof for {owner_id}\n", encoding="utf-8")
        err_path.write_text("", encoding="utf-8")
        stdout = evidence_v5.stream_descriptor(
            out_path,
            path_value=str(out_path.resolve()),
        )
        stderr = evidence_v5.stream_descriptor(
            err_path,
            path_value=str(err_path.resolve()),
        )
        result_fingerprint = evidence_v5.background_result_fingerprint_v2(
            stdout=stdout,
            stderr=stderr,
            exit_code=0,
            status="passed",
            descendant_zero_confirmed=True,
            cleanup_reason="fixture_no_process",
        )
        combined_path.write_bytes(
            evidence_v5.terminal_stream_index_bytes(
                name=owner_id,
                status="passed",
                exit_code=0,
                start_time="2026-07-24T00:00:00+00:00",
                end_time="2026-07-24T00:00:01+00:00",
                stdout=stdout,
                stderr=stderr,
                descendant_zero_confirmed=True,
                cleanup_reason="fixture_no_process",
                result_fingerprint=result_fingerprint,
            )
        )
        meta = {
            "schema_version": evidence_v5.BACKGROUND_CHILD_META_SCHEMA_VERSION,
            "name": owner_id,
            "owner_id": owner_id,
            "command": list(
                owner_commands.get(owner_id)
                if owner_commands is not None
                and owner_commands.get(owner_id) is not None
                else [sys.executable, "-m", "pytest", relative_input, "-q"]
            ),
            "status": "passed",
            "start_time": "2026-07-24T00:00:00+00:00",
            "end_time": "2026-07-24T00:00:01+00:00",
            "exit_code": 0,
            "impact_plan_ref": {
                **plan_ref,
                "owner_id": owner_id,
            },
            "owner_identity_sha256": evidence_v5.sha256_json(
                identities[owner_id]
            ),
            "inputs_current": True,
            "descendant_zero_confirmed": True,
            "cleanup_proof": {
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "reason": "fixture_no_process",
            },
            "stream_artifacts": {
                "stdout": stdout,
                "stderr": stderr,
            },
            "combined_artifact": {
                **evidence_v5.path_reference(combined_path, root=ROOT),
                "kind": "terminal_stream_index",
                "max_bytes": evidence_v5.COMBINED_INDEX_MAX_BYTES,
            },
            "combined_kind": "terminal_stream_index",
            "result_fingerprint_schema_version": (
                evidence_v5.BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION
            ),
            "result_fingerprint": result_fingerprint,
        }
        meta_path.write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        owner_ref = impact_resolution.owner_reference_from_child_meta(
            owner_id=owner_id,
            meta_path=meta_path,
            meta=meta,
        )
        if reused_without_ticket:
            owner_ref["action"] = "reuse"
            owner_ref["result_reused"] = True
            owner_ref["reuse_ticket_ref"] = None
        owners[owner_id] = owner_ref

    aggregate = ProofArtifactRef(
        artifact_id=aggregate_artifact_id,
        producer_route="flowguard-test-mesh",
        command="python scripts/run_test_tier.py --tier release --background"
        if release
        else "python scripts/run_test_tier.py --tier all --background",
        result_path=str(fixture_root.resolve()),
        result_status="passed",
        exit_code=0,
        artifact_fingerprints={
            "owner-set": _sha256_text("\n".join(normalized_owner_ids)),
            "impact-plan": str(plan_ref["sha256"]),
        },
        covered_obligation_ids=tuple(aggregate_obligation_ids),
        assertion_scope="external_contract",
        current=True,
        route_evidence_current=True,
        progress_only=False,
        metadata={
            "selected_child_command_count": selected,
            "executed_child_command_count": (
                0 if reused_without_ticket else selected
            ),
            "reused_child_command_count": (
                selected if reused_without_ticket else 0
            ),
            "proof_backed_child_command_count": selected,
        },
    )
    suite_row = {
        "result_status": "passed",
        "result_reused": reused_without_ticket,
        "reuse_ticket": None,
        "selected_count": selected,
        "test_count": selected,
        "owner_evidence_ids": normalized_owner_ids,
        "owner_ref_count": len(normalized_owner_ids),
        "proof_artifact": aggregate.to_dict(),
    }
    manifest: dict[str, object] = {
        "schema_version": impact_resolution.EVIDENCE_MANIFEST_SCHEMA_VERSION,
        "snapshot": _current_snapshot(),
        "impact_plan_refs": [plan_ref],
        "owners": owners,
        "routine": {},
    }
    if release:
        manifest["release"] = suite_row
    else:
        manifest["routine"] = {suite_id: suite_row}
    return manifest


def set_owner_covered_obligations(
    manifest: Mapping[str, Any],
    owner_id: str,
    covered_obligation_ids: Iterable[str],
) -> None:
    """Rewrite one fixture plan identity and refresh its exact child/meta refs."""

    owners = manifest.get("owners")
    if not isinstance(owners, Mapping):
        raise ValueError("fixture owners missing")
    row = owners.get(owner_id)
    if not isinstance(row, dict):
        raise ValueError(f"fixture owner missing: {owner_id}")
    proof_ref = row.get("proof_ref")
    if not isinstance(proof_ref, dict):
        raise ValueError(f"fixture owner proof ref missing: {owner_id}")
    meta_path = evidence_v5.resolve_artifact_path(
        ROOT,
        str(proof_ref.get("path") or ""),
    )
    meta = evidence_v5.load_json_object(meta_path)
    impact_ref = meta.get("impact_plan_ref")
    if not isinstance(impact_ref, dict):
        raise ValueError(f"fixture impact ref missing: {owner_id}")
    plan_path = evidence_v5.resolve_artifact_path(
        ROOT,
        str(impact_ref.get("path") or ""),
    )
    plan = evidence_v5.load_json_object(plan_path)
    decisions = [
        decision
        for decision in plan.get("decisions") or ()
        if isinstance(decision, dict)
        and decision.get("owner_id") == owner_id
    ]
    if len(decisions) != 1 or not isinstance(decisions[0].get("identity"), dict):
        raise ValueError(f"fixture owner decision missing: {owner_id}")
    identity = decisions[0]["identity"]
    identity["covered_obligation_ids"] = list(covered_obligation_ids)
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    base_plan_ref = {
        **evidence_v5.path_reference(plan_path, root=ROOT),
        "plan_id": plan["plan_id"],
    }
    manifest_plan_refs = manifest.get("impact_plan_refs")
    if isinstance(manifest_plan_refs, list):
        for index, manifest_ref in enumerate(manifest_plan_refs):
            if (
                isinstance(manifest_ref, Mapping)
                and manifest_ref.get("path") == impact_ref.get("path")
            ):
                manifest_plan_refs[index] = dict(base_plan_ref)
    for current_owner_id, current_row in owners.items():
        if not isinstance(current_row, dict):
            continue
        current_proof_ref = current_row.get("proof_ref")
        if not isinstance(current_proof_ref, dict):
            continue
        current_meta_path = evidence_v5.resolve_artifact_path(
            ROOT,
            str(current_proof_ref.get("path") or ""),
        )
        current_meta = evidence_v5.load_json_object(current_meta_path)
        current_impact_ref = current_meta.get("impact_plan_ref")
        if (
            not isinstance(current_impact_ref, Mapping)
            or current_impact_ref.get("path") != impact_ref.get("path")
        ):
            continue
        current_meta["impact_plan_ref"] = {
            **base_plan_ref,
            "owner_id": current_owner_id,
        }
        if current_owner_id == owner_id:
            current_meta["owner_identity_sha256"] = evidence_v5.sha256_json(
                identity
            )
            current_row["identity_sha256"] = current_meta[
                "owner_identity_sha256"
            ]
        current_meta_path.write_text(
            json.dumps(current_meta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        current_row["proof_ref"] = {
            **evidence_v5.path_reference(current_meta_path, root=ROOT),
            "artifact_id": current_proof_ref["artifact_id"],
            "result_fingerprint": current_proof_ref["result_fingerprint"],
            "result_fingerprint_schema_version": current_proof_ref[
                "result_fingerprint_schema_version"
            ],
            "result_status": current_proof_ref["result_status"],
        }
