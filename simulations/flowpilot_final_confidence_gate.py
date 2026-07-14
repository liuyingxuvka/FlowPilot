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
DECISION_RELEASE_CONVERGED = "release_convergence_with_deferred_structure_splits"
DECISION_REPOSITORY_ONLY = "repository_confidence_only"
DECISION_BLOCKED = "blocked"

ROOT = Path(__file__).resolve().parents[1]


def portable_evidence_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


DEFAULT_RESULT_PATHS = {
    "control_plane": ROOT / "simulations" / "flowpilot_control_plane_friction_results.json",
    "event_idempotency": ROOT / "simulations" / "flowpilot_event_idempotency_results.json",
    "model_test_alignment": ROOT / "simulations" / "flowpilot_model_test_alignment_results.json",
    "known_friction": ROOT / "simulations" / "flowpilot_known_friction_regression_matrix_results.json",
    "terminal_return": ROOT / "simulations" / "flowpilot_terminal_return_preflight_results.json",
}
DEFAULT_EVIDENCE_MANIFEST_PATH = (
    ROOT / "simulations" / "flowpilot_acceptance_testmesh_evidence_manifest.json"
)

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
TERMINAL_RETURN_RESULT_FILENAME = "flowpilot_terminal_return_preflight_results.json"


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
        "path": portable_evidence_path(path),
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
    full_coverage_ok = bool(payload.get("full_coverage_ok"))
    release_convergence_ok = bool(payload.get("release_convergence_ok")) or (
        full_coverage_ok and "release_convergence_ok" not in payload
    )
    gap_counts = payload.get("gap_counts") or full_diagnostic.get("gap_counts") or {}
    gap_surface_count = int(full_diagnostic.get("gap_surface_count") or 0)
    unresolved_non_deferred_gap_count = int(
        full_diagnostic.get("unresolved_non_deferred_gap_count") or 0
    )
    deferred_structure_split_count = int(
        full_diagnostic.get("deferred_structure_split_count") or 0
    )
    deferred_structure_only = (
        not full_coverage_ok
        and release_convergence_ok
        and unresolved_non_deferred_gap_count == 0
        and deferred_structure_split_count > 0
        and gap_surface_count == deferred_structure_split_count
        and set(gap_counts) <= {"needs_structure_split"}
    )
    claim_scope = str(payload.get("claim_scope") or "")
    evidence_status = str(payload.get("evidence_status") or "")
    execution_evidence = payload.get("execution_evidence")
    execution_evidence_ok = bool(
        isinstance(execution_evidence, Mapping) and execution_evidence.get("ok") is True
    )

    row["details"]["top_level_ok"] = bool(payload.get("ok"))
    row["details"]["alignment_ok"] = bool(payload.get("alignment_ok"))
    row["details"]["full_diagnostic_ok"] = bool(payload.get("full_diagnostic_ok"))
    row["details"]["full_coverage_ok"] = full_coverage_ok
    row["details"]["release_convergence_ok"] = release_convergence_ok
    row["details"]["gap_counts"] = gap_counts
    row["details"]["gap_surface_count"] = gap_surface_count
    row["details"]["unresolved_non_deferred_gap_count"] = unresolved_non_deferred_gap_count
    row["details"]["deferred_structure_split_count"] = deferred_structure_split_count
    row["details"]["claim_scope"] = claim_scope
    row["details"]["evidence_status"] = evidence_status
    row["details"]["execution_evidence_ok"] = execution_evidence_ok
    row["details"]["coverage_claim"] = (
        "full_coverage" if full_coverage_ok else "release_convergence_deferred_structure_only"
        if deferred_structure_only
        else "blocked"
    )

    for field in ("ok", "alignment_ok", "full_diagnostic_ok"):
        if not payload.get(field):
            row["blockers"].append(f"{field}_false")
    if claim_scope not in {"done", "publish"}:
        row["blockers"].append("model_test_alignment_scope_not_done")
    if evidence_status != "passed":
        row["blockers"].append("model_test_alignment_evidence_not_passed")
    if not execution_evidence_ok:
        row["blockers"].append("model_test_alignment_execution_evidence_not_current")
    if not full_coverage_ok and not deferred_structure_only:
        row["blockers"].append("full_coverage_ok_false")
    if not full_coverage_ok and not release_convergence_ok:
        row["blockers"].append("release_convergence_ok_false")

    row["ok"] = not row["blockers"]
    row["status"] = (
        DECISION_FULL
        if row["ok"] and full_coverage_ok
        else DECISION_RELEASE_CONVERGED
        if row["ok"]
        else DECISION_BLOCKED
    )
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


def evaluate_terminal_return(path: Path, payload: Mapping[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    row = _row("terminal_return", path)
    if load_error or payload is None:
        row["blockers"].append(load_error or "missing_evidence")
        return row

    preflight = payload.get("final_return_preflight")
    foreground = payload.get("foreground_duty")
    next_action = payload.get("next_action")
    if not isinstance(preflight, Mapping):
        row["blockers"].append("final_return_preflight_missing")
        return row
    if not isinstance(foreground, Mapping):
        foreground = {}
    if not isinstance(next_action, Mapping):
        next_action = {}

    runtime_blockers = [
        str(item)
        for item in preflight.get("blockers", [])
        if isinstance(item, str) and item
    ]
    allowed = preflight.get("allowed") is True
    foreground_action = foreground.get("action")
    controller_stop_allowed = (
        foreground.get("controller_stop_allowed") is True
        and preflight.get("controller_stop_allowed") is True
    )
    next_action_type = preflight.get("next_action_type") or next_action.get("action_type")

    row["details"].update(
        {
            "top_level_ok": bool(payload.get("ok")),
            "allowed": allowed,
            "foreground_action": foreground_action,
            "controller_stop_allowed": controller_stop_allowed,
            "preflight_controller_stop_allowed": preflight.get("controller_stop_allowed"),
            "foreground_controller_stop_allowed": foreground.get("controller_stop_allowed"),
            "next_action_type": next_action_type,
            "runtime_blockers": runtime_blockers,
            "closure_decision": preflight.get("closure_decision"),
            "guard_decision": preflight.get("guard_decision"),
            "run_id": foreground.get("run_id"),
        }
    )

    row["blockers"].extend(runtime_blockers)
    if not allowed:
        row["blockers"].append("terminal_return_not_allowed")
    if foreground_action != "terminal_return":
        row["blockers"].append("foreground_duty_not_terminal_return")
    if not controller_stop_allowed:
        row["blockers"].append("controller_stop_not_allowed")
    if next_action_type:
        row["blockers"].append(f"next_action:{next_action_type}")

    row["ok"] = not row["blockers"]
    row["status"] = DECISION_FULL if row["ok"] else DECISION_BLOCKED
    return row


def terminal_return_scoped_out_row() -> dict[str, Any]:
    row = _row("terminal_return", ROOT / "simulations" / TERMINAL_RETURN_RESULT_FILENAME)
    row["ok"] = True
    row["status"] = DECISION_REPOSITORY_ONLY
    row["details"].update(
        {
            "scoped_out": True,
            "reason": "repository_confidence_only: terminal-return authority was explicitly scoped out",
            "formal_exit_authority": False,
        }
    )
    return row


EVALUATORS = {
    "control_plane": evaluate_control_plane,
    "event_idempotency": evaluate_event_idempotency,
    "model_test_alignment": evaluate_model_test_alignment,
    "known_friction": evaluate_known_friction,
    "terminal_return": evaluate_terminal_return,
}


def evaluate_final_confidence(
    result_paths: Mapping[str, Path],
    *,
    subcheck_runs: Sequence[Mapping[str, Any]] = (),
    terminal_return_required: bool = True,
) -> dict[str, Any]:
    run_by_name = {str(run.get("name")): run for run in subcheck_runs if isinstance(run, Mapping)}
    evidence_rows: list[dict[str, Any]] = []
    required_names = ["control_plane", "event_idempotency", "model_test_alignment", "known_friction"]
    if terminal_return_required:
        required_names.append("terminal_return")
    for name in required_names:
        path = result_paths[name]
        payload, load_error = load_json(path)
        row = EVALUATORS[name](path, payload, load_error)
        run = run_by_name.get(name)
        if run is not None:
            exit_code = int(run.get("exit_code") or 0)
            row["details"]["subcheck_exit_code"] = exit_code
            row["details"]["subcheck_stdout_path"] = run.get("stdout_path")
            row["details"]["subcheck_stderr_path"] = run.get("stderr_path")
            if exit_code != 0:
                row["blockers"].append(
                    "terminal_return_preflight_command_nonzero"
                    if name == "terminal_return"
                    else "subcheck_failed"
                )
                row["ok"] = False
                row["status"] = DECISION_BLOCKED
        evidence_rows.append(row)
    if not terminal_return_required:
        evidence_rows.append(terminal_return_scoped_out_row())

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
    release_converged = ok and any(row["status"] == DECISION_RELEASE_CONVERGED for row in evidence_rows)
    repository_only = ok and not terminal_return_required
    decision = (
        DECISION_BLOCKED
        if not ok
        else DECISION_REPOSITORY_ONLY
        if repository_only
        else DECISION_RELEASE_CONVERGED
        if release_converged
        else DECISION_FULL
    )
    terminal_row = next((row for row in evidence_rows if row["name"] == "terminal_return"), {})
    formal_exit_authority = bool(
        terminal_return_required
        and ok
        and terminal_row.get("ok")
        and terminal_row.get("status") == DECISION_FULL
    )
    return {
        "ok": ok,
        "decision": decision,
        "claim_scope": "formal_exit" if terminal_return_required else "repository_only",
        "formal_exit_authority": formal_exit_authority,
        "summary": (
            "FULL: all required final-confidence and terminal-return evidence is current and passing"
            if decision == DECISION_FULL
            else "RELEASE_CONVERGED: required evidence passes with explicitly deferred structure split debt"
            if decision == DECISION_RELEASE_CONVERGED
            else "REPOSITORY_ONLY: repository evidence is current; terminal-return authority was scoped out"
            if decision == DECISION_REPOSITORY_ONLY
            else f"BLOCKED: {len(blockers)} required evidence source(s) are not full confidence"
        ),
        "evidence_rows": evidence_rows,
        "blockers": blockers,
    }


def result_paths_for_dir(results_dir: Path) -> dict[str, Path]:
    paths = {
        name: results_dir / filename
        for name, (_, filename) in SUBCHECK_COMMANDS.items()
    }
    paths["terminal_return"] = results_dir / TERMINAL_RETURN_RESULT_FILENAME
    return paths


def _display_command(
    command: Sequence[str],
    *,
    live_root: Path | None = None,
    source_root: Path | None = None,
) -> list[str]:
    display: list[str] = []
    live_root_text = str(live_root) if live_root is not None else None
    source_root_text = str(source_root) if source_root is not None else None
    for index, arg in enumerate(command):
        if index == 0:
            display.append("<python>")
        elif live_root_text is not None and arg == live_root_text:
            display.append("<external-live-root>")
        elif source_root_text is not None and arg == source_root_text:
            display.append("<flowpilot-source-root>")
        elif Path(arg).is_absolute():
            display.append(portable_evidence_path(Path(arg)))
        else:
            display.append(arg)
    return display


def run_required_subchecks(
    results_dir: Path,
    *,
    live_root: Path | None = None,
    source_root: Path | None = None,
    terminal_return_required: bool = True,
    evidence_manifest: Path = DEFAULT_EVIDENCE_MANIFEST_PATH,
) -> list[dict[str, Any]]:
    results_dir.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, Any]] = []
    for name, (script, filename) in SUBCHECK_COMMANDS.items():
        json_path = results_dir / filename
        out_path = results_dir / f"{name}.out.txt"
        err_path = results_dir / f"{name}.err.txt"
        json_path.unlink(missing_ok=True)
        command = [sys.executable, script, "--json-out", str(json_path)]
        if name == "control_plane":
            if live_root is not None:
                command.extend(["--live-root", str(live_root)])
            if source_root is not None:
                command.extend(["--source-root", str(source_root)])
        elif name == "model_test_alignment":
            command.extend(
                [
                    "--evidence-manifest",
                    str(evidence_manifest),
                    "--evidence-scope",
                    "done",
                ]
            )
        with out_path.open("w", encoding="utf-8", errors="replace") as out_file, err_path.open(
            "w", encoding="utf-8", errors="replace"
        ) as err_file:
            completed = subprocess.run(command, cwd=ROOT, stdout=out_file, stderr=err_file, check=False)
        run_rows.append(
            {
                "name": name,
                "command": _display_command(
                    command,
                    live_root=live_root,
                    source_root=source_root,
                ),
                "exit_code": completed.returncode,
                "json_path": portable_evidence_path(json_path),
                "stdout_path": portable_evidence_path(out_path),
                "stderr_path": portable_evidence_path(err_path),
            }
        )
    if terminal_return_required:
        run_rows.append(run_terminal_return_preflight(results_dir, live_root=live_root))
    return run_rows


def _parse_json_text(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if not stripped:
        return None, "empty output"
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None, "output did not contain a JSON object"
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON output: {exc}"
    if not isinstance(value, dict):
        return None, "JSON output was not an object"
    return value, None


def run_terminal_return_preflight(
    results_dir: Path,
    *,
    live_root: Path | None = None,
) -> dict[str, Any]:
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / TERMINAL_RETURN_RESULT_FILENAME
    out_path = results_dir / "terminal_return.out.txt"
    err_path = results_dir / "terminal_return.err.txt"
    json_path.unlink(missing_ok=True)
    root_arg = live_root if live_root is not None else ROOT
    command = [
        sys.executable,
        "skills/flowpilot/assets/flowpilot_new.py",
        "--root",
        str(root_arg),
        "--json",
        "final-preflight",
    ]
    with out_path.open("w", encoding="utf-8", errors="replace") as out_file, err_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as err_file:
        completed = subprocess.run(command, cwd=ROOT, stdout=out_file, stderr=err_file, check=False)
    payload, parse_error = _parse_json_text(out_path.read_text(encoding="utf-8", errors="replace"))
    if payload is None:
        payload = {
            "ok": False,
            "parse_error": parse_error,
        }
    payload["terminal_return_preflight_command"] = _display_command(
        command,
        live_root=live_root,
    )
    payload["terminal_return_preflight_exit_code"] = completed.returncode
    write_json(json_path, payload)
    return {
        "name": "terminal_return",
        "command": _display_command(command, live_root=live_root),
        "exit_code": completed.returncode,
        "json_path": portable_evidence_path(json_path),
        "stdout_path": portable_evidence_path(out_path),
        "stderr_path": portable_evidence_path(err_path),
        "parse_error": parse_error,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "DECISION_BLOCKED",
    "DECISION_FULL",
    "DECISION_RELEASE_CONVERGED",
    "DECISION_REPOSITORY_ONLY",
    "DEFAULT_EVIDENCE_MANIFEST_PATH",
    "DEFAULT_RESULT_PATHS",
    "evaluate_final_confidence",
    "result_paths_for_dir",
    "run_required_subchecks",
    "run_terminal_return_preflight",
    "write_json",
]
