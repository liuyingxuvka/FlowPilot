"""Final confidence aggregation for FlowPilot evidence gates.

This module does not replace existing FlowGuard checks. It consumes their
machine-readable outputs and fails closed when a broad confidence claim would
otherwise over-read local green subchecks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


DECISION_FULL = "full_confidence"
DECISION_BLOCKED = "blocked"

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RESULT_PATHS = {
    "control_plane": ROOT / "simulations" / "flowpilot_control_plane_friction_results.json",
    "event_idempotency": ROOT / "simulations" / "flowpilot_event_idempotency_results.json",
    "model_test_alignment": ROOT / "simulations" / "flowpilot_model_test_alignment_results.json",
    "known_friction": ROOT / "simulations" / "flowpilot_known_friction_regression_matrix_results.json",
}

SUBCHECK_COMMANDS = {
    "control_plane": (
        "simulations/run_flowpilot_control_plane_friction_checks.py",
        "flowpilot_control_plane_friction_results.json",
    ),
    "event_idempotency": (
        "simulations/run_flowpilot_event_idempotency_checks.py",
        "flowpilot_event_idempotency_results.json",
    ),
    "model_test_alignment": (
        "simulations/run_flowpilot_model_test_alignment_checks.py",
        "flowpilot_model_test_alignment_results.json",
    ),
    "known_friction": (
        "simulations/flowpilot_known_friction_regression_matrix.py",
        "flowpilot_known_friction_regression_matrix_results.json",
    ),
}


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing_evidence"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(data, dict):
        return None, "invalid_payload"
    return data, None


def _finding_codes(findings: object) -> list[str]:
    codes: list[str] = []
    if not isinstance(findings, list):
        return codes
    for finding in findings:
        if isinstance(finding, dict):
            code = finding.get("code")
            if isinstance(code, str) and code:
                codes.append(code)
    return codes


def _row(name: str, path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "path": str(path),
        "ok": False,
        "status": DECISION_BLOCKED,
        "blockers": [],
        "details": {},
    }


def evaluate_control_plane(path: Path, payload: Mapping[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    row = _row("control_plane", path)
    if load_error or payload is None:
        row["blockers"].append(load_error or "missing_evidence")
        return row

    live_audit = payload.get("live_run_audit")
    row["details"]["top_level_ok"] = bool(payload.get("ok"))
    if not isinstance(live_audit, dict):
        row["blockers"].append("live_run_audit_missing")
        return row

    row["details"]["live_run_audit_ok"] = bool(live_audit.get("ok"))
    row["details"]["live_run_audit_skipped"] = bool(live_audit.get("skipped"))
    row["details"]["live_run_id"] = live_audit.get("run_id")
    row["details"]["live_finding_codes"] = _finding_codes(live_audit.get("findings"))

    if live_audit.get("skipped"):
        row["blockers"].append("live_run_audit_skipped")
    if not live_audit.get("ok"):
        row["blockers"].append("live_run_audit_failed")
    if not payload.get("ok"):
        row["blockers"].append("control_plane_check_failed")

    row["ok"] = not row["blockers"]
    row["status"] = DECISION_FULL if row["ok"] else DECISION_BLOCKED
    return row


def evaluate_event_idempotency(path: Path, payload: Mapping[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    row = _row("event_idempotency", path)
    if load_error or payload is None:
        row["blockers"].append(load_error or "missing_evidence")
        return row

    required = {
        "top_level_ok": bool(payload.get("ok")),
        "flowguard_explorer_ok": bool((payload.get("flowguard_explorer") or {}).get("ok")),
        "safe_graph_ok": bool((payload.get("safe_graph") or {}).get("ok")),
        "progress_ok": bool((payload.get("progress") or {}).get("ok")),
        "hazard_detection_ok": bool((payload.get("hazard_detection") or {}).get("ok")),
    }
    row["details"].update(required)
    for key, ok in required.items():
        if not ok:
            row["blockers"].append(key.replace("_ok", "_failed"))

    row["ok"] = not row["blockers"]
    row["status"] = DECISION_FULL if row["ok"] else DECISION_BLOCKED
    return row


def evaluate_model_test_alignment(path: Path, payload: Mapping[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    row = _row("model_test_alignment", path)
    if load_error or payload is None:
        row["blockers"].append(load_error or "missing_evidence")
        return row

    full_diagnostic = payload.get("full_model_test_code_diagnostic")
    if not isinstance(full_diagnostic, dict):
        full_diagnostic = {}

    row["details"]["top_level_ok"] = bool(payload.get("ok"))
    row["details"]["alignment_ok"] = bool(payload.get("alignment_ok"))
    row["details"]["full_diagnostic_ok"] = bool(payload.get("full_diagnostic_ok"))
    row["details"]["full_coverage_ok"] = bool(payload.get("full_coverage_ok"))
    row["details"]["gap_counts"] = payload.get("gap_counts") or full_diagnostic.get("gap_counts") or {}
    row["details"]["gap_surface_count"] = full_diagnostic.get("gap_surface_count")

    for field in ("ok", "alignment_ok", "full_diagnostic_ok", "full_coverage_ok"):
        if not payload.get(field):
            row["blockers"].append(f"{field}_false")

    row["ok"] = not row["blockers"]
    row["status"] = DECISION_FULL if row["ok"] else DECISION_BLOCKED
    return row


def evaluate_known_friction(path: Path, payload: Mapping[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    row = _row("known_friction", path)
    if load_error or payload is None:
        row["blockers"].append(load_error or "missing_evidence")
        return row

    family = payload.get("defect_family_gate_report")
    if not isinstance(family, dict):
        row["blockers"].append("defect_family_gate_report_missing")
        return row
    gate_report = family.get("gate_report") if isinstance(family.get("gate_report"), dict) else {}
    ledger_report = family.get("risk_ledger_report") if isinstance(family.get("risk_ledger_report"), dict) else {}

    row["details"]["top_level_ok"] = bool(payload.get("ok"))
    row["details"]["defect_family_gate_ok"] = bool(payload.get("defect_family_gate_ok"))
    row["details"]["gate_decision"] = gate_report.get("decision")
    row["details"]["gate_confidence"] = gate_report.get("confidence")
    row["details"]["risk_ledger_decision"] = ledger_report.get("decision")
    row["details"]["risk_ledger_confidence"] = ledger_report.get("confidence")

    if not payload.get("ok"):
        row["blockers"].append("known_friction_check_failed")
    if not payload.get("defect_family_gate_ok"):
        row["blockers"].append("defect_family_gate_failed")
    if gate_report.get("confidence") != "full":
        row["blockers"].append("defect_family_confidence_not_full")
    if ledger_report.get("confidence") != "full":
        row["blockers"].append("risk_ledger_confidence_not_full")

    row["ok"] = not row["blockers"]
    row["status"] = DECISION_FULL if row["ok"] else DECISION_BLOCKED
    return row


EVALUATORS = {
    "control_plane": evaluate_control_plane,
    "event_idempotency": evaluate_event_idempotency,
    "model_test_alignment": evaluate_model_test_alignment,
    "known_friction": evaluate_known_friction,
}


def evaluate_final_confidence(result_paths: Mapping[str, Path]) -> dict[str, Any]:
    evidence_rows: list[dict[str, Any]] = []
    for name in ("control_plane", "event_idempotency", "model_test_alignment", "known_friction"):
        path = result_paths[name]
        payload, load_error = load_json(path)
        evidence_rows.append(EVALUATORS[name](path, payload, load_error))

    blockers = [
        {
            "evidence": row["name"],
            "path": row["path"],
            "codes": row["blockers"],
            "details": row["details"],
        }
        for row in evidence_rows
        if row["blockers"]
    ]
    ok = not blockers
    decision = DECISION_FULL if ok else DECISION_BLOCKED
    return {
        "ok": ok,
        "decision": decision,
        "summary": (
            "FULL: all required final-confidence evidence is current and passing"
            if ok
            else f"BLOCKED: {len(blockers)} required evidence source(s) are not full confidence"
        ),
        "evidence_rows": evidence_rows,
        "blockers": blockers,
    }


def result_paths_for_dir(results_dir: Path) -> dict[str, Path]:
    return {
        name: results_dir / filename
        for name, (_, filename) in SUBCHECK_COMMANDS.items()
    }


def run_required_subchecks(results_dir: Path) -> list[dict[str, Any]]:
    results_dir.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, Any]] = []
    for name, (script, filename) in SUBCHECK_COMMANDS.items():
        json_path = results_dir / filename
        out_path = results_dir / f"{name}.out.txt"
        err_path = results_dir / f"{name}.err.txt"
        command = [sys.executable, script, "--json-out", str(json_path)]
        with out_path.open("w", encoding="utf-8", errors="replace") as out_file, err_path.open(
            "w", encoding="utf-8", errors="replace"
        ) as err_file:
            completed = subprocess.run(command, cwd=ROOT, stdout=out_file, stderr=err_file, check=False)
        run_rows.append(
            {
                "name": name,
                "command": command,
                "exit_code": completed.returncode,
                "json_path": str(json_path),
                "stdout_path": str(out_path),
                "stderr_path": str(err_path),
            }
        )
    return run_rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "DECISION_BLOCKED",
    "DECISION_FULL",
    "DEFAULT_RESULT_PATHS",
    "evaluate_final_confidence",
    "result_paths_for_dir",
    "run_required_subchecks",
    "write_json",
]
