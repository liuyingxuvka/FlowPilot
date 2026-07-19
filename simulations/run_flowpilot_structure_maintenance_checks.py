"""Executable StructureMesh/TestMesh checks for FlowPilot maintenance."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from flowguard import review_structure_mesh, review_test_mesh

import flowpilot_structure_maintenance_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_structure_maintenance_results.json"
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    return value


def _structure_review() -> dict[str, Any]:
    report = review_structure_mesh(model.router_structure_plan())
    hazards: list[dict[str, Any]] = []
    for name in model.STRUCTURE_HAZARDS:
        hazard_report = review_structure_mesh(model.router_structure_hazard_plan(name))
        hazards.append(
            {
                "name": name,
                "blocked": not hazard_report.ok,
                "decision": hazard_report.decision,
                "finding_codes": sorted({finding.code for finding in hazard_report.findings}),
                "blocker_count": hazard_report.blocker_count(),
            }
        )
    return {
        "ok": report.ok and all(hazard["blocked"] for hazard in hazards),
        "report": _jsonable(report),
        "hazards": hazards,
    }


def _model_structure_review() -> dict[str, Any]:
    report = review_structure_mesh(model.model_structure_plan())
    hazards: list[dict[str, Any]] = []
    for name in model.MODEL_STRUCTURE_HAZARDS:
        hazard_report = review_structure_mesh(model.model_structure_hazard_plan(name))
        hazards.append(
            {
                "name": name,
                "blocked": not hazard_report.ok,
                "decision": hazard_report.decision,
                "finding_codes": sorted({finding.code for finding in hazard_report.findings}),
                "blocker_count": hazard_report.blocker_count(),
            }
        )
    return {
        "ok": report.ok and all(hazard["blocked"] for hazard in hazards),
        "report": _jsonable(report),
        "hazards": hazards,
    }


def _resource_facade_structure_review() -> dict[str, Any]:
    report = review_structure_mesh(model.resource_facade_structure_plan())
    hazards: list[dict[str, Any]] = []
    for name in model.RESOURCE_STRUCTURE_HAZARDS:
        hazard_report = review_structure_mesh(
            model.resource_facade_structure_hazard_plan(name)
        )
        hazards.append(
            {
                "name": name,
                "blocked": not hazard_report.ok,
                "decision": hazard_report.decision,
                "finding_codes": sorted(
                    {finding.code for finding in hazard_report.findings}
                ),
                "blocker_count": hazard_report.blocker_count(),
            }
        )
    return {
        "ok": report.ok and all(hazard["blocked"] for hazard in hazards),
        "report": _jsonable(report),
        "hazards": hazards,
    }


def _test_tier_structure_review() -> dict[str, Any]:
    report = review_structure_mesh(model.test_tier_structure_plan())
    hazards: list[dict[str, Any]] = []
    for name in model.TEST_TIER_STRUCTURE_HAZARDS:
        hazard_report = review_structure_mesh(
            model.test_tier_structure_hazard_plan(name)
        )
        hazards.append(
            {
                "name": name,
                "blocked": not hazard_report.ok,
                "decision": hazard_report.decision,
                "finding_codes": sorted(
                    {finding.code for finding in hazard_report.findings}
                ),
                "blocker_count": hazard_report.blocker_count(),
            }
        )
    return {
        "ok": report.ok and all(hazard["blocked"] for hazard in hazards),
        "report": _jsonable(report),
        "hazards": hazards,
    }


def _testmesh_review() -> dict[str, Any]:
    report = review_test_mesh(model.router_testmesh_plan())
    hazards: list[dict[str, Any]] = []
    for name in model.TESTMESH_HAZARDS:
        hazard_report = review_test_mesh(model.router_testmesh_hazard_plan(name))
        hazards.append(
            {
                "name": name,
                "blocked": not hazard_report.ok,
                "decision": hazard_report.decision,
                "finding_codes": sorted({finding.code for finding in hazard_report.findings}),
                "blocker_count": hazard_report.blocker_count(),
            }
        )
    return {
        "ok": report.ok and all(hazard["blocked"] for hazard in hazards),
        "report": _jsonable(report),
        "hazards": hazards,
    }


def build_report() -> dict[str, Any]:
    structure = _structure_review()
    model_structure = _model_structure_review()
    resource_facade_structure = _resource_facade_structure_review()
    test_tier_structure = _test_tier_structure_review()
    testmesh = _testmesh_review()
    return {
        "model": "flowpilot_structure_maintenance",
        "ok": (
            structure["ok"]
            and model_structure["ok"]
            and resource_facade_structure["ok"]
            and test_tier_structure["ok"]
            and testmesh["ok"]
        ),
        "structure_mesh": structure,
        "model_structure_mesh": model_structure,
        "resource_facade_structure_mesh": resource_facade_structure,
        "test_tier_structure_mesh": test_tier_structure,
        "test_mesh": testmesh,
        "claim_boundary": (
            "StructureMesh parity is reviewed at release scope. The embedded "
            "router TestMesh is a routine declaration view: deferred release "
            "suites require current final receipts from the owning background "
            "test tier before broad completion or release confidence."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run FlowPilot StructureMesh/TestMesh maintenance checks."
    )
    parser.add_argument(
        "--json-out",
        default=str(RESULTS_PATH),
        help="Where to write the JSON report.",
    )
    args = parser.parse_args(argv)

    report = build_report()
    output_path = Path(args.json_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
