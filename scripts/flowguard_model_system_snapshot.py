"""Build the canonical FlowPilot observed/candidate FlowGuard model snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from flowguard.model_authority import (
    LIFECYCLE_ACTIVE,
    SUBJECT_OBSERVED_IMPLEMENTATION,
    AuthorityEndpointRef,
    CoverageDimension,
    CoverageUniverse,
    ModelRelation,
    ModelSystemSnapshot,
    build_model_instance_ref,
    canonical_fingerprint,
    file_fingerprint,
)


TOPOLOGY_PATH = Path("docs/flowguard_project_topology.json")
LEDGER_PATH = Path(".flowguard/behavior_commitment_ledger/ledger.json")
LOGICAL_MODEL_ID_OVERRIDES = {
    "flowpilot_material_artifact_map": "flowpilot_optional_material_artifact_map",
}


def _load_object(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _stable_id(prefix: str, value: Any) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9._:/-]+",
        "-",
        str(value).strip(),
    ).strip("-")
    if not normalized:
        normalized = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{normalized}"


def _values(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(
        value,
        (str, bytes, Mapping),
    ):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _logical_model_id(row: Mapping[str, Any]) -> str:
    runner_key = str(row.get("runner_key", "")).strip()
    if not runner_key:
        raise ValueError("topology model row has no runner_key")
    return LOGICAL_MODEL_ID_OVERRIDES.get(runner_key, runner_key)


def _source_paths(row: Mapping[str, Any]) -> tuple[str, str]:
    runner_path = str(row.get("runner_path", "")).strip()
    model_path = str(row.get("model_path", "")).strip() or runner_path
    if not model_path or not runner_path:
        raise ValueError(
            f"topology model row lacks source paths: {_logical_model_id(row)}"
        )
    return model_path, runner_path


def build_snapshot(
    root: Path,
    *,
    snapshot_id: str,
    subject_lane: str = SUBJECT_OBSERVED_IMPLEMENTATION,
    lifecycle: str = LIFECYCLE_ACTIVE,
) -> ModelSystemSnapshot:
    root = root.resolve()
    topology_path = root / TOPOLOGY_PATH
    ledger_path = root / LEDGER_PATH
    topology = _load_object(topology_path)
    ledger_document = _load_object(ledger_path)
    ledger = ledger_document.get("ledger")
    if not isinstance(ledger, Mapping):
        raise ValueError("behavior commitment document has no ledger object")
    models = topology.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("project topology has no model inventory")

    source_inventory: dict[str, str] = {}
    for row in models:
        if not isinstance(row, Mapping):
            raise ValueError("topology model inventory contains a non-object")
        for relative in _source_paths(row):
            source = root / relative
            if not source.is_file():
                raise ValueError(f"missing topology model source: {relative}")
            source_inventory[relative] = file_fingerprint(source)
    subject_revision = "source-inventory:" + canonical_fingerprint(
        [
            {"path": path, "sha256": source_inventory[path]}
            for path in sorted(source_inventory)
        ]
    ).split(":", 1)[1]

    instances = []
    by_id = {}
    for row in models:
        logical_model_id = _logical_model_id(row)
        if logical_model_id in by_id:
            raise ValueError(f"duplicate logical model id: {logical_model_id}")
        model_path, runner_path = _source_paths(row)
        evidence = row.get("evidence")
        known_bad = (
            _values(evidence.get("known_bad"))
            if isinstance(evidence, Mapping)
            else ()
        )
        purpose_fingerprint = canonical_fingerprint(
            {
                "schema": "flowpilot.model_purpose_projection.v1",
                "logical_model_id": logical_model_id,
                "model_path": model_path,
                "runner_path": runner_path,
                "known_bad_case_ids": known_bad,
                "guarded_purpose": (
                    "Preserve the declared good/bad oracle boundary of "
                    f"{logical_model_id} under its native runner."
                ),
                "claim_boundary": (
                    "This projection identifies the current native model and "
                    "runner boundary; executable checks remain separate evidence."
                ),
            }
        )
        instance = build_model_instance_ref(
            root,
            logical_model_id=logical_model_id,
            model_kind=f"flowpilot_{str(row.get('area') or 'model')}",
            model_path=model_path,
            runner_path=runner_path,
            purpose_closure_fingerprint=purpose_fingerprint,
            subject_revision=subject_revision,
            input_paths=(model_path, runner_path),
        )
        instances.append(instance)
        by_id[logical_model_id] = instance

    root_instance = by_id.get("flowpilot_model_mesh")
    if root_instance is None:
        raise ValueError("project topology has no flowpilot_model_mesh root")

    def model_endpoint(logical_model_id: str) -> AuthorityEndpointRef:
        instance = by_id[logical_model_id]
        return AuthorityEndpointRef(
            endpoint_kind="model_instance",
            endpoint_id=f"model:{logical_model_id}",
            fingerprint=instance.fingerprint,
            owner_route="model_mesh_maintenance",
        )

    topology_owner = AuthorityEndpointRef(
        endpoint_kind="parent_closure",
        endpoint_id="flowpilot:project-topology",
        fingerprint=file_fingerprint(topology_path),
        owner_route="model_mesh_maintenance",
    )
    ledger_owner = AuthorityEndpointRef(
        endpoint_kind="parent_closure",
        endpoint_id="flowpilot:behavior-ledger-root",
        fingerprint=file_fingerprint(ledger_path),
        owner_route="behavior_commitment_ledger",
    )
    owners = {
        (topology_owner.endpoint_kind, topology_owner.endpoint_id): topology_owner,
        (ledger_owner.endpoint_kind, ledger_owner.endpoint_id): ledger_owner,
    }
    relations: list[ModelRelation] = []
    relation_ids: set[str] = set()

    def add_owner(endpoint: AuthorityEndpointRef) -> None:
        owners[(endpoint.endpoint_kind, endpoint.endpoint_id)] = endpoint

    def add_relation(
        relation_id: str,
        kind: str,
        source: AuthorityEndpointRef,
        target: AuthorityEndpointRef,
        evidence_fingerprints: tuple[str, ...] = (),
    ) -> None:
        if relation_id in relation_ids:
            return
        relation_ids.add(relation_id)
        relations.append(
            ModelRelation(
                relation_id=relation_id,
                kind=kind,
                source=source,
                target=target,
                evidence_fingerprints=evidence_fingerprints,
            )
        )

    for logical_model_id in sorted(by_id):
        add_relation(
            _stable_id("relation:topology-contains-model", logical_model_id),
            "contains",
            topology_owner,
            model_endpoint(logical_model_id),
            (topology_owner.fingerprint,),
        )

    raw_surfaces = ledger.get("source_surfaces", ())
    surfaces = {
        str(row.get("surface_id", "")): row
        for row in raw_surfaces
        if isinstance(row, Mapping) and str(row.get("surface_id", "")).strip()
    }
    commitments = tuple(
        row
        for row in ledger.get("commitments", ())
        if isinstance(row, Mapping)
        and str(row.get("commitment_id", "")).strip()
    )
    covered_commitments: set[str] = set()
    covered_surfaces: set[str] = set()
    field_ids: set[str] = set()
    contract_ids: set[str] = set()
    test_ids: set[str] = set()

    for commitment in commitments:
        commitment_id = str(commitment["commitment_id"])
        commitment_endpoint = AuthorityEndpointRef(
            endpoint_kind="behavior_commitment",
            endpoint_id=commitment_id,
            fingerprint=canonical_fingerprint(dict(commitment)),
            owner_route="behavior_commitment_ledger",
        )
        add_owner(commitment_endpoint)
        owner_id = str(commitment.get("primary_owner_model_id", "")).strip()
        owner_model = model_endpoint(owner_id) if owner_id in by_id else None
        if owner_model is not None:
            covered_commitments.add(commitment_id)
            add_relation(
                _stable_id(
                    "relation:model-realizes-commitment",
                    commitment_id,
                ),
                "realizes",
                owner_model,
                commitment_endpoint,
                (ledger_owner.fingerprint, commitment_endpoint.fingerprint),
            )
        for surface_id in _values(commitment.get("source_surface_ids")):
            surface = surfaces.get(surface_id)
            if surface is None:
                continue
            surface_endpoint = AuthorityEndpointRef(
                endpoint_kind="external_surface",
                endpoint_id=surface_id,
                fingerprint=canonical_fingerprint(dict(surface)),
                owner_route="behavior_commitment_ledger",
            )
            add_owner(surface_endpoint)
            add_relation(
                _stable_id(
                    "relation:surface-produces-for",
                    f"{surface_id}->{commitment_id}",
                ),
                "produces_for",
                surface_endpoint,
                commitment_endpoint,
                (ledger_owner.fingerprint,),
            )
            if owner_model is not None:
                covered_surfaces.add(surface_id)
        for endpoint_kind, values in (
            ("field_inventory", _values(commitment.get("state_writes"))),
            ("side_effect_inventory", _values(commitment.get("side_effects"))),
        ):
            for value in values:
                endpoint_id = _stable_id("field-or-effect", value)
                field_ids.add(endpoint_id)
                endpoint = AuthorityEndpointRef(
                    endpoint_kind=endpoint_kind,
                    endpoint_id=endpoint_id,
                    fingerprint=canonical_fingerprint(
                        {"kind": endpoint_kind, "value": value}
                    ),
                    owner_route="field_lifecycle_mesh",
                )
                add_owner(endpoint)
                if owner_model is not None:
                    add_relation(
                        _stable_id(
                            f"relation:model-realizes-{endpoint_kind}",
                            f"{owner_id}->{endpoint_id}",
                        ),
                        "realizes",
                        owner_model,
                        endpoint,
                        (commitment_endpoint.fingerprint,),
                    )
        evidence = commitment.get("evidence")
        if not isinstance(evidence, Mapping):
            evidence = {}
        for value in _values(evidence.get("code_contract_ids")):
            endpoint_id = _stable_id("contract", value)
            contract_ids.add(endpoint_id)
            endpoint = AuthorityEndpointRef(
                endpoint_kind="code_contract",
                endpoint_id=endpoint_id,
                fingerprint=canonical_fingerprint(
                    {"kind": "code_contract", "value": value}
                ),
                owner_route="model_test_alignment",
            )
            add_owner(endpoint)
            if owner_model is not None:
                add_relation(
                    _stable_id(
                        "relation:model-realizes-contract",
                        f"{owner_id}->{endpoint_id}",
                    ),
                    "realizes",
                    owner_model,
                    endpoint,
                    (commitment_endpoint.fingerprint,),
                )
        for value in _values(evidence.get("test_evidence_ids")):
            endpoint_id = _stable_id("test", value)
            test_ids.add(endpoint_id)
            endpoint = AuthorityEndpointRef(
                endpoint_kind="test_evidence",
                endpoint_id=endpoint_id,
                fingerprint=canonical_fingerprint(
                    {"kind": "test_evidence", "value": value}
                ),
                owner_route="test_mesh_maintenance",
            )
            add_owner(endpoint)
            if owner_model is not None:
                add_relation(
                    _stable_id(
                        "relation:test-validates-model",
                        f"{endpoint_id}->{owner_id}",
                    ),
                    "validates",
                    endpoint,
                    owner_model,
                    (commitment_endpoint.fingerprint,),
                )

    surface_ids = tuple(sorted(surfaces))
    commitment_ids = tuple(
        sorted(str(row["commitment_id"]) for row in commitments)
    )
    model_ids = tuple(sorted(by_id))
    all_commitments_covered = len(covered_commitments) == len(commitment_ids)
    dimensions = (
        CoverageDimension(
            "external_surfaces",
            surface_ids,
            tuple(sorted(covered_surfaces)),
        ),
        CoverageDimension(
            "behavior_commitments",
            commitment_ids,
            tuple(sorted(covered_commitments)),
        ),
        CoverageDimension("model_instances", model_ids, model_ids),
        CoverageDimension(
            "fields_state_side_effects",
            tuple(sorted(field_ids)),
            tuple(sorted(field_ids)) if all_commitments_covered else (),
        ),
        CoverageDimension(
            "code_contracts",
            tuple(sorted(contract_ids)),
            tuple(sorted(contract_ids)) if all_commitments_covered else (),
        ),
        CoverageDimension(
            "tests_evidence",
            tuple(sorted(test_ids)),
            tuple(sorted(test_ids)) if all_commitments_covered else (),
        ),
    )
    coverage = CoverageUniverse(
        boundary_id="flowpilot:topology-ledger-observed-boundary",
        source_inventory_fingerprint=canonical_fingerprint(
            {
                "topology": topology_owner.fingerprint,
                "ledger": ledger_owner.fingerprint,
                "subject_revision": subject_revision,
                "model_ids": model_ids,
            }
        ),
        dimensions=dimensions,
        claim_boundary=(
            "Coverage is exhaustive only for the checked-in FlowPilot project "
            "topology, its resolved native model and runner pairs, and the "
            "current behavior commitment ledger references."
        ),
    )
    unresolved_gap_ids = tuple(
        sorted(
            _stable_id(f"gap:{dimension.dimension_id}", value)
            for dimension in dimensions
            for value in (*dimension.missing_ids, *dimension.unresolved_ids)
        )
    )
    return ModelSystemSnapshot(
        snapshot_id=snapshot_id,
        system_id="flowpilot",
        subject_lane=subject_lane,
        lifecycle=lifecycle,
        subject_revision=subject_revision,
        root_instance_fingerprints=(root_instance.fingerprint,),
        model_instances=tuple(instances),
        relations=tuple(relations),
        coverage=coverage,
        owner_artifact_refs=tuple(owners.values()),
        unresolved_gap_ids=unresolved_gap_ids,
        claim_boundary=(
            "This FlowPilot model-system snapshot is assembled from the "
            "checked-in topology, native model files, native runners, and "
            "behavior ledger. It does not claim that current regressions ran."
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--snapshot-id",
        default="snapshot:flowpilot-observed",
    )
    parser.add_argument(
        "--subject-lane",
        default=SUBJECT_OBSERVED_IMPLEMENTATION,
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    snapshot = build_snapshot(
        root,
        snapshot_id=args.snapshot_id,
        subject_lane=args.subject_lane,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            snapshot.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "pass",
                "snapshot_path": str(output),
                "snapshot_fingerprint": snapshot.fingerprint,
                "subject_revision": snapshot.subject_revision,
                "model_count": len(snapshot.model_instances),
                "relation_count": len(snapshot.relations),
                "coverage_status": snapshot.coverage_status,
                "unresolved_gap_ids": list(snapshot.unresolved_gap_ids),
                "bootstrap_evidence_fingerprint": canonical_fingerprint(
                    {
                        "topology": file_fingerprint(root / TOPOLOGY_PATH),
                        "ledger": file_fingerprint(root / LEDGER_PATH),
                        "flowguard_version": "0.61.0",
                    }
                ),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
