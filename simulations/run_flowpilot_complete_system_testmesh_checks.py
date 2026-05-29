"""Run FlowGuard TestMesh checks for the complete FlowPilot system."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from flowguard import review_test_mesh

try:  # pragma: no cover
    from . import flowpilot_complete_system_evidence_model as model
except ImportError:  # pragma: no cover
    import flowpilot_complete_system_evidence_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_testmesh_results.json"


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


def run_checks(*, release_evidence: bool = False, live_host_evidence: bool = False) -> dict[str, Any]:
    plan = model.build_testmesh_plan(release_evidence=release_evidence, live_host_evidence=live_host_evidence)
    report = review_test_mesh(plan)
    release_rows = [suite for suite in plan.child_suites if suite.release_required]
    release_gate_ok = all(suite.result_status == "passed" and suite.evidence_current for suite in release_rows)
    rows = [
        {
            "id": "complete_testmesh_plan",
            "status": "passed" if report.ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_complete_system_evidence_model.py"],
        },
        {
            "id": "complete_release_evidence_boundary",
            "status": "passed" if release_gate_ok else "not_run",
            "freshness": "current" if release_gate_ok else "not_run",
            "scope": "release",
            "evidence": [suite.result_path or suite.not_run_reason for suite in release_rows],
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_testmesh_checks",
        "model_id": model.TESTMESH_ID,
        "ok": report.ok,
        "mode": "release" if release_gate_ok else "routine",
        "report": _to_jsonable(report),
        "release_gate": {"ok": release_gate_ok, "required_suites": [suite.suite_id for suite in release_rows]},
        "test_mesh": {"rows": rows, "routine_gate": {"ok": report.ok}, "release_gate": {"ok": release_gate_ok}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--release-evidence", action="store_true")
    parser.add_argument("--live-host-evidence", action="store_true")
    args = parser.parse_args()

    result = run_checks(release_evidence=args.release_evidence, live_host_evidence=args.live_host_evidence)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
