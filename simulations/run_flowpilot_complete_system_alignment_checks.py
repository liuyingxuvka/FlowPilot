"""Run FlowGuard model-test alignment checks for the complete FlowPilot system."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from flowguard import review_model_test_alignment

try:  # pragma: no cover
    from . import flowpilot_complete_system_evidence_model as model
except ImportError:  # pragma: no cover
    import flowpilot_complete_system_evidence_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_alignment_results.json"


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


def run_checks(*, implementation_evidence: bool = False) -> dict[str, Any]:
    plan = model.build_alignment_plan(implementation_evidence=implementation_evidence)
    report = review_model_test_alignment(plan)
    pending_evidence = [
        evidence.evidence_id
        for evidence in plan.test_evidence
        if evidence.result_status != "passed" or not evidence.evidence_current
    ]
    if not implementation_evidence:
        pending_evidence.append("test_complete_runtime_future")
    rows = [
        {
            "id": "complete_model_test_alignment",
            "status": "passed" if report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_evidence_model.py"],
        },
        {
            "id": "complete_implementation_evidence",
            "status": "passed" if not pending_evidence else "not_run",
            "freshness": "current" if not pending_evidence else "not_run",
            "scope": "implementation",
            "evidence": pending_evidence,
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_alignment_checks",
        "model_id": model.ALIGNMENT_ID,
        "ok": report.ok,
        "mode": "implementation" if implementation_evidence else "planning",
        "report": _to_jsonable(report),
        "pending_evidence": pending_evidence,
        "test_mesh": {"rows": rows, "routine_gate": {"ok": report.ok}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--implementation-evidence", action="store_true")
    args = parser.parse_args()

    result = run_checks(implementation_evidence=args.implementation_evidence)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
