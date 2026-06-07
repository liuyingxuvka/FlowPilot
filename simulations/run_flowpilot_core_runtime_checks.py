"""Run clean AI project runtime scenarios and evidence gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowpilot_core_runtime_scenarios import (
    SCENARIOS,
    _base_ledger,
    _complete_happy_path,
    _complete_open_packet,
    _mark_node_ready_for_final_closure,
    _open_packet_by_kind,
    _role_result_body,
    _route_plan_body,
    ack_only_timeout_stays_incomplete,
    compact_status_does_not_leak_sealed_bodies,
    console_does_not_leak_sealed_bodies,
    final_preflight_blocks_accepted_packet_stale_lease,
    pm_repair_decision_receives_authorized_body_on_packet_open,
    reassignment_supersedes_active_packet_lease,
    recovery_duty_names_command_payload,
    replacement_worker_success,
    route_deliverable_blocks_terminal_closure,
    self_review_blocks,
    stale_evidence_blocks,
    stale_route_output_blocks,
    strict_route_plan_rejects_numbered_text,
    wrong_flowguard_target_blocks,
)


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_core_runtime_results.json"


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


def run_checks(*, release_evidence: bool = False, install_ok: bool = False) -> dict[str, Any]:
    scenarios = [fn() for fn in SCENARIOS.values()]
    scenario_ok = all(item["ok"] for item in scenarios)
    health_family_names = {
        "reassignment_supersedes_active_packet_lease",
        "final_preflight_blocks_accepted_packet_stale_lease",
        "compact_status_does_not_leak_sealed_bodies",
        "recovery_duty_names_command_payload",
    }
    health_family_ok = all(
        item["ok"]
        for item in scenarios
        if item["name"] in health_family_names
    )
    rows = [
        _row(
            "runtime_scenarios",
            "passed" if scenario_ok else "failed",
            "current",
            "routine",
            ["simulations/run_flowpilot_core_runtime_checks.py"],
            {"case_count": len(scenarios)},
        ),
        _row(
            "runtime_console_isolation",
            "passed" if next(item for item in scenarios if item["name"] == "console_does_not_leak_sealed_bodies")["ok"] else "failed",
            "current",
            "routine",
            ["skills/flowpilot/assets/flowpilot_core_runtime/runtime.py"],
        ),
        _row(
            "run_20260531_210441_health_family",
            "passed" if health_family_ok else "failed",
            "current",
            "routine",
            ["tests/test_flowpilot_core_runtime.py", "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py"],
            {
                "covered_sources": sorted(health_family_names),
                "body_policy": "reviewer_body_reading_is_soft; controller_projection_leakage_and_cross_role_execution_are_hard",
            },
        ),
        _row(
            "background_meta_capability",
            "passed" if release_evidence else "not_run",
            "current" if release_evidence else "not_run",
            "release",
            ["tmp/flowguard_background/run_meta_checks.*", "tmp/flowguard_background/run_capability_checks.*"],
        ),
        _row(
            "install_surface_parity",
            "passed" if release_evidence and install_ok else "not_run",
            "current" if release_evidence and install_ok else "not_run",
            "release",
            ["scripts/install_flowpilot.py", "scripts/audit_local_install_sync.py", "scripts/check_install.py"],
        ),
    ]
    routine_rows = [row for row in rows if row["scope"] == "routine"]
    release_rows = rows
    return {
        "result_type": "flowpilot_core_runtime_checks",
        "ok": scenario_ok,
        "mode": "release" if release_evidence and install_ok else "routine",
        "scenarios": scenarios,
        "test_mesh": {
            "rows": rows,
            "parent_gates": {
                "routine_runtime_gate": {
                    "ok": all(row["status"] == "passed" and row["freshness"] == "current" for row in routine_rows),
                    "required_rows": [row["id"] for row in routine_rows],
                },
                "release_runtime_gate": {
                    "ok": all(row["status"] == "passed" and row["freshness"] == "current" for row in release_rows),
                    "required_rows": [row["id"] for row in release_rows],
                },
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument("--release-evidence", action="store_true")
    parser.add_argument("--install-ok", action="store_true")
    args = parser.parse_args()

    result = run_checks(release_evidence=args.release_evidence, install_ok=args.install_ok)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
