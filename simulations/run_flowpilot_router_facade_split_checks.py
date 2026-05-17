"""Run FlowGuard checks for the router facade and PromptStore split."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from flowguard import review_structure_mesh, review_test_mesh

import flowpilot_router_facade_split_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_router_facade_split_results.json")


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


def build_report() -> dict[str, Any]:
    structure = review_structure_mesh(model.router_facade_structure_plan())
    testmesh = review_test_mesh(model.router_facade_testmesh_plan())
    split = model.review_split_evidence(model.valid_split_evidence())
    hazards: list[dict[str, Any]] = []
    for name in model.SPLIT_HAZARDS:
        report = model.review_split_evidence(model.split_hazard_evidence(name))
        hazards.append(
            {
                "name": name,
                "blocked": not report["ok"],
                "finding_codes": sorted({item["code"] for item in report["findings"]}),
                "finding_count": len(report["findings"]),
            }
        )
    return {
        "model": "flowpilot_router_facade_split",
        "ok": structure.ok and testmesh.ok and split["ok"] and all(item["blocked"] for item in hazards),
        "structure_mesh": _jsonable(structure),
        "test_mesh": _jsonable(testmesh),
        "prompt_split": split,
        "known_bad_hazards": hazards,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
