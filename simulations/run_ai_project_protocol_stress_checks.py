"""Run stress checks for the clean AI project protocol kernel."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import ai_project_protocol_stress_model as model
    from . import run_ai_project_protocol_checks as kernel_runner
except ImportError:  # pragma: no cover
    import ai_project_protocol_stress_model as model
    import run_ai_project_protocol_checks as kernel_runner


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "ai_project_protocol_stress_results.json"
BACKGROUND_CHECKS = ("run_meta_checks", "run_capability_checks")
FINAL_STATUSES = {"pass", "passed", "complete", "completed", "success", "succeeded", "ok"}


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=tuple(f"select_{scenario.name}" for scenario in model.SCRIPTED_SCENARIOS),
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model.hard_check_failures(state)
        if failures:
            hazards[name] = failures
    expected = set(model.hazard_states())
    return {
        "ok": set(hazards) == expected,
        "hazards": hazards,
        "expected": sorted(expected),
    }


def _matrix_report() -> dict[str, Any]:
    matrix = model.scenario_matrix()
    expected = {
        scenario.name: scenario.expected_classification
        for scenario in model.SCRIPTED_SCENARIOS
    }
    mismatches = {
        scenario: {"expected": expected_label, "actual": matrix.get(scenario)}
        for scenario, expected_label in expected.items()
        if matrix.get(scenario) != expected_label
    }
    return {"ok": not mismatches, "matrix": matrix, "mismatches": mismatches}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _artifact_paths(background_dir: Path, name: str) -> dict[str, str]:
    return {
        "stdout": str(background_dir / f"{name}.out.txt"),
        "stderr": str(background_dir / f"{name}.err.txt"),
        "combined": str(background_dir / f"{name}.combined.txt"),
        "exit": str(background_dir / f"{name}.exit.txt"),
        "meta": str(background_dir / f"{name}.meta.json"),
    }


def inspect_background_artifacts(background_dir: Path | None) -> dict[str, Any]:
    if background_dir is None:
        return {
            "ok": False,
            "status": "not_run",
            "checks": [],
            "missing": list(BACKGROUND_CHECKS),
        }

    checks: list[dict[str, Any]] = []
    for name in BACKGROUND_CHECKS:
        paths = {key: Path(value) for key, value in _artifact_paths(background_dir, name).items()}
        exists = {key: path.exists() for key, path in paths.items()}
        exit_code = _read_exit_code(paths["exit"])
        meta = _load_json(paths["meta"])
        meta_status = str(meta.get("status", "")).lower()
        proof_status = (
            meta.get("proof_status")
            or meta.get("proofStatus")
            or meta.get("proof_reuse_status")
            or "not_present"
        )
        final_status = meta_status in FINAL_STATUSES or bool(meta.get("ended_at") or meta.get("end_time"))
        ok = all(exists.values()) and exit_code == 0 and final_status
        checks.append(
            {
                "name": name,
                "ok": ok,
                "exists": exists,
                "exit_code": exit_code,
                "meta_status": meta.get("status"),
                "latest_update": meta.get("ended_at") or meta.get("end_time") or meta.get("updated_at"),
                "proof_status": proof_status,
                "paths": {key: str(path) for key, path in paths.items()},
            }
        )

    return {
        "ok": all(check["ok"] for check in checks),
        "status": "passed" if all(check["ok"] for check in checks) else "failed",
        "checks": checks,
        "missing": [check["name"] for check in checks if not check["ok"]],
    }


def _row(
    row_id: str,
    status: str,
    freshness: str,
    scope: str,
    evidence: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "status": status,
        "freshness": freshness,
        "scope": scope,
        "evidence": evidence,
        "details": details or {},
    }


def _row_passes(row: dict[str, Any]) -> bool:
    return row["status"] == "passed" and row["freshness"] == "current"


def _build_test_mesh(
    *,
    kernel: dict[str, Any],
    scripted: dict[str, Any],
    random_runs: dict[str, Any],
    historical: dict[str, Any],
    flowguard: dict[str, Any],
    hazards: dict[str, Any],
    matrix: dict[str, Any],
    release_evidence: bool,
    background: dict[str, Any],
    install_ok: bool,
) -> dict[str, Any]:
    rows = [
        _row(
            "focused_kernel_compatibility",
            "passed" if kernel["ok"] else "failed",
            "current",
            "routine",
            ["simulations/run_ai_project_protocol_checks.py", "simulations/ai_project_protocol_results.json"],
            {"result_type": kernel.get("result_type"), "model_id": kernel.get("model_id")},
        ),
        _row(
            "deterministic_multiround_scenarios",
            "passed" if scripted["ok"] and matrix["ok"] else "failed",
            "current",
            "routine",
            ["simulations/ai_project_protocol_stress_model.py"],
            {"case_count": scripted["case_count"], "accepted_cases": scripted["accepted_cases"]},
        ),
        _row(
            "seeded_random_long_run",
            "passed" if random_runs["ok"] else "failed",
            "current",
            "routine",
            ["simulations/ai_project_protocol_stress_model.py"],
            {
                "seed_count": random_runs["seed_count"],
                "steps_per_seed": random_runs["steps_per_seed"],
                "violation_count": len(random_runs["violations"]),
            },
        ),
        _row(
            "historical_bad_case_replay",
            "passed" if historical["ok"] else "failed",
            "current",
            "routine",
            ["simulations/ai_project_protocol_stress_model.py"],
            {"case_count": historical["case_count"]},
        ),
        _row(
            "flowguard_stress_explorer",
            "passed" if flowguard["ok"] and hazards["ok"] else "failed",
            "current",
            "routine",
            ["simulations/run_ai_project_protocol_stress_checks.py"],
            {
                "violation_count": flowguard["violation_count"],
                "hazard_count": len(hazards["hazards"]),
            },
        ),
    ]

    background_status = "passed" if release_evidence and background["ok"] else "not_run"
    background_freshness = "current" if background_status == "passed" else "not_run"
    rows.append(
        _row(
            "background_project_regressions",
            background_status,
            background_freshness,
            "release",
            [
                "tmp/flowguard_background/run_meta_checks.*",
                "tmp/flowguard_background/run_capability_checks.*",
            ],
            background,
        )
    )

    install_status = "passed" if release_evidence and install_ok else "not_run"
    install_freshness = "current" if install_status == "passed" else "not_run"
    rows.append(
        _row(
            "install_surface_parity",
            install_status,
            install_freshness,
            "release",
            [
                "scripts/install_flowpilot.py --sync-repo-owned",
                "scripts/audit_local_install_sync.py",
                "scripts/install_flowpilot.py --check",
                "scripts/check_install.py",
            ],
            {"install_ok_flag": install_ok},
        )
    )

    routine_rows = [row for row in rows if row["scope"] == "routine"]
    release_rows = rows
    routine_ok = all(_row_passes(row) for row in routine_rows)
    release_ok = all(_row_passes(row) for row in release_rows)
    return {
        "rows": rows,
        "parent_gates": {
            "routine_stress_gate": {
                "ok": routine_ok,
                "required_rows": [row["id"] for row in routine_rows],
            },
            "release_stress_gate": {
                "ok": release_ok,
                "required_rows": [row["id"] for row in release_rows],
            },
        },
        "ok": release_ok if release_evidence else routine_ok,
        "mode": "release" if release_evidence else "routine",
    }


def run_checks(
    *,
    release_evidence: bool = False,
    background_dir: Path | None = None,
    install_ok: bool = False,
) -> dict[str, Any]:
    kernel = kernel_runner.run_checks()
    scripted = model.run_scripted_scenarios()
    random_runs = model.run_seeded_random_long_runs()
    historical = model.run_historical_replay()
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    matrix = _matrix_report()
    background = inspect_background_artifacts(background_dir)
    test_mesh = _build_test_mesh(
        kernel=kernel,
        scripted=scripted,
        random_runs=random_runs,
        historical=historical,
        flowguard=flowguard,
        hazards=hazards,
        matrix=matrix,
        release_evidence=release_evidence,
        background=background,
        install_ok=install_ok,
    )
    report = {
        "result_type": "ai_project_protocol_stress",
        "model_id": model.MODEL_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "release" if release_evidence else "routine",
        "kernel_compatibility": {
            "ok": kernel["ok"],
            "result_type": kernel.get("result_type"),
            "model_id": kernel.get("model_id"),
        },
        "scripted_scenarios": scripted,
        "seeded_random_long_run": random_runs,
        "historical_replay": historical,
        "flowguard": flowguard,
        "hazard_detection": hazards,
        "scenario_matrix": matrix,
        "test_mesh": test_mesh,
        "ok": bool(
            kernel["ok"]
            and scripted["ok"]
            and random_runs["ok"]
            and historical["ok"]
            and flowguard["ok"]
            and hazards["ok"]
            and matrix["ok"]
            and test_mesh["ok"]
        ),
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--release-evidence", action="store_true")
    parser.add_argument("--background-dir", type=Path)
    parser.add_argument("--install-ok", action="store_true")
    args = parser.parse_args(argv)
    report = run_checks(
        release_evidence=args.release_evidence,
        background_dir=args.background_dir,
        install_ok=args.install_ok,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"[ai-project-protocol-stress] ok={report['ok']} mode={report['mode']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
