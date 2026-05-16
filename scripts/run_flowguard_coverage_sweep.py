"""Read-only FlowGuard coverage sweep and finding ledger.

The sweep intentionally does not pass --json-out to model runners and does not
refresh existing result files. Runners that still write results by default are
read from their last persisted JSON result instead of being executed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"

STRONG_COVERAGE = {
    "flowpilot_control_plane_friction",
    "flowpilot_gate_policy_audit",
    "protocol_contract_conformance",
    "flowpilot_router_loop",
    "flowpilot_startup_control",
    "flowpilot_packet_lifecycle",
    "flowpilot_repair_transaction",
    "flowpilot_control_transaction_registry",
    "flowpilot_legal_next_action",
    "flowpilot_event_capability_registry",
    "flowpilot_route_replanning_policy",
    "flowpilot_cross_plane_friction",
    "flowpilot_model_mesh",
    "flowpilot_model_hierarchy",
}
ABSTRACT_STRONG = {
    "meta",
    "capability",
    "flowpilot_resume",
    "output_contract",
    "flowpilot_gate_decision_contract",
}
SPECIALIZED = {
    "card_instruction_coverage",
    "defect_governance",
    "flowpilot_planning_quality",
    "flowpilot_reviewer_active_challenge",
    "release_tooling",
    "startup_pm_review",
    "user_flow_diagram",
}


def _runner_key(path: Path) -> str:
    name = path.stem
    if name.startswith("run_"):
        name = name[4:]
    if name.endswith("_checks"):
        name = name[:-7]
    return name


def _coverage_tier(key: str) -> str:
    if key in STRONG_COVERAGE:
        return "coverage_strong"
    if key in ABSTRACT_STRONG:
        return "abstract_strong_live_mapping_weaker"
    if key in SPECIALIZED:
        return "specialized_assertion_or_local_hazard"
    return "unclassified_or_supporting_model"


def _script_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _declared_result_path(path: Path, text: str) -> Path | None:
    key = _runner_key(path)
    if key == "meta":
        return path.parent / "meta_thin_parent_results.json"
    if key == "capability":
        return path.parent / "capability_thin_parent_results.json"
    match = re.search(r'RESULTS_PATH\s*=\s*ROOT\s*/\s*"([^"]+)"', text)
    if match:
        return path.parent / match.group(1)
    match = re.search(r'RESULTS_PATH\s*=\s*Path\(__file__\)\.with_name\(\s*"([^"]+)"\s*\)', text)
    if match:
        return path.parent / match.group(1)
    match = re.search(
        r'RESULTS_PATH\s*=\s*Path\(__file__\)\.resolve\(\)\.with_name\(\s*"([^"]+)"\s*\)',
        text,
    )
    if match:
        return path.parent / match.group(1)
    match = re.search(
        r'RESULTS_PATH\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*/\s*"([^"]+)"',
        text,
    )
    if match:
        return path.parent / match.group(1)
    return None


def _read_only_runnable(text: str) -> bool:
    if "write_text" not in text:
        return True
    if "--json-out" not in text:
        return False
    if "default=RESULTS_PATH" in text or "default=str(RESULTS_PATH)" in text:
        return False
    return "if args.json_out" in text


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


def _load_existing_result(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, "runner writes by default and has no declared result path"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"declared result file is missing: {path.relative_to(ROOT).as_posix()}"
    except json.JSONDecodeError as exc:
        return None, f"declared result file is invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "declared result JSON was not an object"
    return value, None


def _section_ok(section: Any) -> bool | None:
    if isinstance(section, dict) and isinstance(section.get("ok"), bool):
        return bool(section["ok"])
    return None


def _coverage_sections(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    abstract_keys = (
        "safe_graph",
        "flowguard_explorer",
        "graph",
        "checks",
        "scenario_metrics",
    )
    progress_keys = ("progress", "loop", "loop_review")
    hazard_keys = ("hazard_checks", "negative_scenarios", "scenario_review")
    live_keys = tuple(key for key in payload if "live" in key and isinstance(payload[key], dict))
    source_keys = tuple(key for key in payload if "source" in key and isinstance(payload[key], dict))

    def summarize(keys: tuple[str, ...]) -> dict[str, Any]:
        present = [key for key in keys if key in payload]
        oks = [_section_ok(payload[key]) for key in present]
        known = [value for value in oks if value is not None]
        return {
            "present": bool(present),
            "keys": present,
            "ok": all(known) if known else None,
        }

    return {
        "abstract": summarize(abstract_keys),
        "progress": summarize(progress_keys),
        "hazards": summarize(hazard_keys),
        "live": summarize(live_keys),
        "source": summarize(source_keys),
    }


def _collect_findings(
    value: Any,
    *,
    runner: str,
    section_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = section_path + (str(key),)
            if key == "findings" and isinstance(child, list):
                section = "live" if any("live" in part for part in section_path) else "source"
                if not any(("live" in part or "source" in part) for part in section_path):
                    section = "abstract"
                for item in child:
                    if isinstance(item, dict):
                        finding = dict(item)
                        finding["runner"] = runner
                        finding["section"] = section
                        finding["section_path"] = ".".join(section_path)
                        finding["classification"] = _classify_finding(finding)
                        findings.append(finding)
            else:
                findings.extend(_collect_findings(child, runner=runner, section_path=next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                _collect_findings(item, runner=runner, section_path=section_path + (str(index),))
            )
    return findings


def _classify_finding(finding: dict[str, Any]) -> str:
    section = str(finding.get("section") or "")
    severity = str(finding.get("severity") or "").lower()
    if section == "live":
        return "modeled_current_live_hit_fix_runtime_or_current_state"
    if section == "source":
        return "modeled_source_hit_fix_source_or_runtime"
    if severity in {"error", "fatal"}:
        return "abstract_or_runner_failure_review_check_flow"
    return "boundary_expected_or_informational"


def _run_runner(path: Path, text: str, timeout_seconds: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    command = [sys.executable, str(path.relative_to(ROOT))]
    if 'add_argument("--json"' in text:
        command.append("--json")
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        metadata = {
            "mode": "executed_read_only",
            "command": command,
            "exit_code": None,
            "parse_error": f"runner timed out after {timeout_seconds} seconds",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
        return None, metadata
    payload, parse_error = _parse_json_text(completed.stdout)
    metadata = {
        "mode": "executed_read_only",
        "command": command,
        "exit_code": completed.returncode,
        "parse_error": parse_error,
        "stderr_tail": completed.stderr[-2000:] if completed.stderr else "",
    }
    return payload, metadata


def _runner_record(path: Path, *, timeout_seconds: int) -> dict[str, Any]:
    key = _runner_key(path)
    text = _script_text(path)
    result_path = _declared_result_path(path, text)
    can_run = _read_only_runnable(text)
    if can_run:
        payload, metadata = _run_runner(path, text, timeout_seconds)
    else:
        payload, error = _load_existing_result(result_path)
        metadata = {
            "mode": "read_existing_result",
            "reason": "runner writes result files by default",
            "result_path": result_path.relative_to(ROOT).as_posix() if result_path else None,
            "parse_error": error,
            "exit_code": None,
        }

    parsed = payload is not None
    sections = _coverage_sections(payload or {})
    findings = _collect_findings(payload or {}, runner=key)
    skipped_checks = payload.get("skipped_checks", {}) if isinstance(payload, dict) else {}
    top_level_ok = payload.get("ok") if isinstance(payload, dict) and isinstance(payload.get("ok"), bool) else None
    if top_level_ok is None:
        ok = parsed and not metadata.get("parse_error") and metadata.get("exit_code") in (None, 0)
    else:
        ok = top_level_ok
    return {
        "runner": key,
        "script": path.relative_to(ROOT).as_posix(),
        "coverage_tier": _coverage_tier(key),
        "read_only_mode": metadata["mode"],
        "ok": ok,
        "parsed": parsed,
        "sections": sections,
        "finding_count": len(findings),
        "findings": findings,
        "skipped_checks": skipped_checks,
        "metadata": metadata,
    }


def _classification_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for finding in record["findings"]:
            key = str(finding.get("classification") or "unclassified")
            counts[key] = counts.get(key, 0) + 1
        if not record["parsed"]:
            counts["runner_unparsed_or_unavailable"] = counts.get("runner_unparsed_or_unavailable", 0) + 1
    return counts


def run_sweep(*, timeout_seconds: int) -> dict[str, Any]:
    runners = sorted(SIMULATIONS.glob("run_*_checks.py"))
    records = [_runner_record(path, timeout_seconds=timeout_seconds) for path in runners]
    finding_ledger = [
        finding
        for record in records
        for finding in record["findings"]
    ]
    tier_counts: dict[str, int] = {}
    for record in records:
        tier = str(record["coverage_tier"])
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    return {
        "schema_version": "flowguard.coverage_sweep.v1",
        "read_only": True,
        "runner_count": len(records),
        "read_only_execution_count": sum(
            1 for record in records if record["read_only_mode"] == "executed_read_only"
        ),
        "existing_result_read_count": sum(
            1 for record in records if record["read_only_mode"] == "read_existing_result"
        ),
        "ok": all(record["parsed"] for record in records),
        "finding_count": len(finding_ledger),
        "classification_counts": _classification_counts(records),
        "coverage_tier_counts": tier_counts,
        "finding_ledger": finding_ledger,
        "runners": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--fail-on-finding", action="store_true")
    args = parser.parse_args()

    result = run_sweep(timeout_seconds=args.timeout_seconds)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    if not result["ok"]:
        return 1
    if args.fail_on_finding and result["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
