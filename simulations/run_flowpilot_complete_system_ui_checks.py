"""Run FlowGuard UI-flow checks for complete FlowPilot startup and Cockpit status."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from flowguard import (
    review_ui_interaction_model,
    review_ui_journey_coverage,
    review_ui_structure_derivation,
)

try:  # pragma: no cover
    from . import flowpilot_complete_system_ui_model as model
except ImportError:  # pragma: no cover
    import flowpilot_complete_system_ui_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_ui_results.json"


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
    interaction_model = model.build_interaction_model()
    journey = model.build_journey_coverage()
    structure = model.build_structure_derivation()
    interaction_report = review_ui_interaction_model(interaction_model)
    journey_report = review_ui_journey_coverage(journey, interaction_model=interaction_model)
    structure_report = review_ui_structure_derivation(structure, interaction_model=interaction_model)
    rows = [
        {
            "id": "complete_ui_interaction_model",
            "status": "passed" if interaction_report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_ui_model.py"],
        },
        {
            "id": "complete_ui_journey_coverage",
            "status": "passed" if journey_report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_ui_model.py"],
        },
        {
            "id": "complete_ui_structure_derivation",
            "status": "passed" if structure_report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_ui_model.py"],
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_ui_checks",
        "model_id": model.MODEL_ID,
        "ok": all(row["status"] == "passed" for row in rows),
        "interaction_report": _to_jsonable(interaction_report),
        "journey_report": _to_jsonable(journey_report),
        "structure_report": _to_jsonable(structure_report),
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
