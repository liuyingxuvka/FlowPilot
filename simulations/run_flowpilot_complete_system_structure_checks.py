"""Run FlowGuard code-structure checks for the complete FlowPilot system."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from flowguard import review_code_structure_recommendation

try:  # pragma: no cover
    from . import flowpilot_complete_system_structure_model as model
except ImportError:  # pragma: no cover
    import flowpilot_complete_system_structure_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_structure_results.json"


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def run_checks() -> dict[str, Any]:
    recommendation = model.build_recommendation()
    report = review_code_structure_recommendation(recommendation)
    hazards: dict[str, Any] = {}
    for hazard_id, bad_recommendation in model.known_bad_recommendations().items():
        bad_report = review_code_structure_recommendation(bad_recommendation)
        if not bad_report.ok:
            hazards[hazard_id] = _to_jsonable(bad_report)
    rows = [
        {
            "id": "complete_structure_recommendation",
            "status": "passed" if report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_structure_model.py"],
        },
        {
            "id": "complete_structure_known_bad_replay",
            "status": "passed" if set(hazards) == set(model.known_bad_recommendations()) else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_structure_model.py"],
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_structure_checks",
        "model_id": model.MODEL_ID,
        "ok": report.ok and all(row["status"] == "passed" for row in rows),
        "report": _to_jsonable(report),
        "known_bad": hazards,
        "target_modules": [module.module_id for module in recommendation.target_modules],
        "function_blocks": list(model.FUNCTION_BLOCKS),
        "test_mesh": {"rows": rows, "routine_gate": {"ok": all(row["status"] == "passed" for row in rows)}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
