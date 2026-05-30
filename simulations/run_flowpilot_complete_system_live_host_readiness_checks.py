"""Check live-host evidence boundary for the complete FlowPilot system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_live_host_results.json"
DEFAULT_EVIDENCE_PATH = ROOT / "flowpilot_complete_system_live_host_evidence.json"


def _load_live_evidence(path: Path | None) -> tuple[bool, dict[str, Any], list[str]]:
    if path is None or not path.exists():
        return False, {}, ["missing_live_host_evidence_file"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, {}, [f"invalid_live_host_evidence_json:{type(exc).__name__}"]
    agents = payload.get("agents")
    blockers: list[str] = []
    if payload.get("schema_version") != "flowpilot.complete_system.live_host_evidence.v1":
        blockers.append("unsupported_live_host_evidence_schema")
    if payload.get("host_surface") not in {"multi_agent_v1", "codex_runtime_role_assistance"}:
        blockers.append("unsupported_live_host_surface")
    if not isinstance(agents, list) or not agents:
        blockers.append("missing_completed_live_agents")
    else:
        completed = [
            agent
            for agent in agents
            if isinstance(agent, dict)
            and agent.get("agent_id")
            and agent.get("status") == "completed"
            and agent.get("task_scope")
        ]
        if not completed:
            blockers.append("no_completed_live_agent_rows")
    return not blockers, payload if isinstance(payload, dict) else {}, blockers


def run_checks(
    *,
    live_host_evidence: bool = False,
    live_host_evidence_file: Path | None = None,
) -> dict[str, Any]:
    evidence_path = live_host_evidence_file or DEFAULT_EVIDENCE_PATH
    evidence_ok, evidence_payload, evidence_blockers = _load_live_evidence(evidence_path) if live_host_evidence else (False, {}, [])
    live_confidence = bool(live_host_evidence and evidence_ok)
    rows = [
        {
            "id": "host_driver_interface",
            "status": "passed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["skills/flowpilot/assets/flowpilot_core_runtime/host.py"],
        },
        {
            "id": "real_live_host_project_run",
            "status": "passed" if live_confidence else "not_run",
            "freshness": "current" if live_confidence else "not_run",
            "scope": "live",
            "evidence": [str(evidence_path)] if live_confidence else (evidence_blockers or ["not available in this run"]),
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_live_host_readiness_checks",
        "ok": not live_host_evidence or evidence_ok,
        "live_confidence": live_confidence,
        "claim_boundary": "live" if live_confidence else "scoped_no_live_host",
        "evidence_file": str(evidence_path) if live_host_evidence else "",
        "evidence_blockers": evidence_blockers,
        "evidence_summary": {
            "host_surface": evidence_payload.get("host_surface", ""),
            "agent_count": len(evidence_payload.get("agents", [])) if isinstance(evidence_payload.get("agents"), list) else 0,
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--live-host-evidence", action="store_true")
    parser.add_argument("--live-host-evidence-file", type=Path, default=DEFAULT_EVIDENCE_PATH)
    args = parser.parse_args()

    result = run_checks(
        live_host_evidence=args.live_host_evidence,
        live_host_evidence_file=args.live_host_evidence_file,
    )
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
