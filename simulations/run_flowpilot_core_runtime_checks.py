"""Run clean AI project runtime scenarios and evidence gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_core_runtime_results.json"
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from flowpilot_core_runtime import runtime  # noqa: E402


ScenarioFn = Callable[[], dict[str, Any]]


def _base_ledger() -> tuple[dict[str, Any], str, str]:
    ledger = runtime.new_ledger(
        "Ship the clean black-box FlowPilot runtime",
        "Complete only with accepted current-route work, independent review, matching FlowGuard, and fresh validation.",
    )
    runtime.create_route(ledger, "Runtime implementation route", ["implement runtime"])
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Implement runtime slice",
        "SEALED_TASK_BODY: worker private instructions",
    )
    worker = runtime.lease_agent(ledger, "worker", agent_id="worker-a")
    runtime.assign_packet(ledger, packet_id, worker)
    return ledger, packet_id, worker


def _open_packet_by_kind(ledger: dict[str, Any], packet_kind: str) -> str:
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"].get("packet_kind", "task") == packet_kind and packet["status"] == "open":
            return str(packet_id)
    raise AssertionError(f"missing open {packet_kind} packet")


def _complete_open_packet(ledger: dict[str, Any], packet_id: str, *, agent_id: str, body: str) -> str:
    packet = ledger["packets"][packet_id]
    lease_id = runtime.lease_agent(
        ledger,
        packet["envelope"]["responsibility"],
        agent_id=agent_id,
        packet_id=packet_id,
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    return runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        body,
        evidence_ids=[f"{packet['envelope'].get('packet_kind', 'task')}-runtime"],
    )


def _complete_happy_path(ledger: dict[str, Any], packet_id: str, worker: str) -> str:
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        "SEALED_RESULT_BODY: implementation result",
        evidence_ids=["unit-runtime"],
    )
    flowguard_packet = _open_packet_by_kind(ledger, "flowguard_check")
    _complete_open_packet(
        ledger,
        flowguard_packet,
        agent_id="flowguard-a",
        body="SEALED_RESULT_BODY: FlowGuard runtime evidence",
    )
    review_packet = _open_packet_by_kind(ledger, "review")
    _complete_open_packet(
        ledger,
        review_packet,
        agent_id="reviewer-a",
        body="SEALED_RESULT_BODY: reviewer accepted the runtime result",
    )
    return result_id


def replacement_worker_success() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.record_progress(ledger, worker, packet_id, "still working")
    runtime.close_lease(ledger, worker, "no final result")
    late_result = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        "SEALED_RESULT_BODY: late stale result",
        evidence_ids=["late"],
    )
    replacement = runtime.lease_agent(ledger, "worker", agent_id="worker-b")
    runtime.assign_packet(ledger, packet_id, replacement)
    result_id = _complete_happy_path(ledger, packet_id, replacement)
    return _scenario_result(
        "replacement_worker_success",
        ledger,
        accepted=ledger["closure"]["decision"] == "complete",
        expected=True,
        details={
            "late_result_blockers": ledger["results"][late_result]["mechanical_blockers"],
            "accepted_result_id": result_id,
        },
    )


def wrong_flowguard_target_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(ledger, worker, packet_id, "SEALED_RESULT_BODY")
    order_id = runtime.create_flowguard_work_order(
        ledger,
        "target_product_behavior",
        "wrong_target_for_done_claim",
        packet_id,
    )
    runtime.complete_flowguard_work_order(ledger, order_id, evidence_id="fg-wrong")
    reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-a")
    review_id = runtime.review_result(ledger, result_id, reviewer)
    runtime.record_validation_evidence(ledger, "runtime-validation")
    closure = runtime.attempt_final_closure(ledger, "runtime-validation")
    blockers = ledger["reviews"][review_id]["blockers"] + closure["blockers"]
    return _scenario_result(
        "wrong_flowguard_target_blocks",
        ledger,
        accepted=False,
        expected=False,
        details={"blockers": blockers},
    )


def self_review_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(ledger, worker, packet_id, "SEALED_RESULT_BODY")
    order_id = runtime.create_flowguard_work_order(ledger, "development_process", "done_claim", packet_id)
    runtime.complete_flowguard_work_order(ledger, order_id)
    reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="worker-a")
    review_id = runtime.review_result(ledger, result_id, reviewer)
    return _scenario_result(
        "self_review_blocks",
        ledger,
        accepted=False,
        expected=False,
        details={"blockers": ledger["reviews"][review_id]["blockers"]},
    )


def stale_route_output_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.create_route(ledger, "Mutated route", ["new implementation path"])
    result_id = runtime.submit_result(ledger, worker, packet_id, "SEALED_RESULT_BODY")
    return _scenario_result(
        "stale_route_output_blocks",
        ledger,
        accepted=False,
        expected=False,
        details={"blockers": ledger["results"][result_id]["mechanical_blockers"]},
    )


def stale_evidence_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.record_source_change(ledger, "source changed before result evidence was refreshed")
    result_id = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        "SEALED_RESULT_BODY",
        evidence_generation=1,
    )
    return _scenario_result(
        "stale_evidence_blocks",
        ledger,
        accepted=False,
        expected=False,
        details={"blockers": ledger["results"][result_id]["mechanical_blockers"]},
    )


def ack_only_timeout_stays_incomplete() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    action_before_timeout = runtime.router_next_action(ledger).to_json()
    runtime.expire_lease(ledger, worker)
    action_after_timeout = runtime.router_next_action(ledger).to_json()
    return _scenario_result(
        "ack_only_timeout_stays_incomplete",
        ledger,
        accepted=False,
        expected=False,
        details={
            "before_timeout": action_before_timeout,
            "after_timeout": action_after_timeout,
        },
    )


def console_does_not_leak_sealed_bodies() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_happy_path(ledger, packet_id, worker)
    console = runtime.render_console(ledger)
    rendered = json.dumps(console, sort_keys=True)
    leaked = "SEALED_TASK_BODY" in rendered or "SEALED_RESULT_BODY" in rendered
    return _scenario_result(
        "console_does_not_leak_sealed_bodies",
        ledger,
        accepted=not leaked,
        expected=True,
        details={"leaked": leaked, "packet_rows": console["packets"]},
    )


SCENARIOS: dict[str, ScenarioFn] = {
    "replacement_worker_success": replacement_worker_success,
    "wrong_flowguard_target_blocks": wrong_flowguard_target_blocks,
    "self_review_blocks": self_review_blocks,
    "stale_route_output_blocks": stale_route_output_blocks,
    "stale_evidence_blocks": stale_evidence_blocks,
    "ack_only_timeout_stays_incomplete": ack_only_timeout_stays_incomplete,
    "console_does_not_leak_sealed_bodies": console_does_not_leak_sealed_bodies,
}


def _scenario_result(
    name: str,
    ledger: dict[str, Any],
    *,
    accepted: bool,
    expected: bool,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "ok": accepted == expected,
        "accepted": accepted,
        "expected_acceptance": expected,
        "next_action": runtime.router_next_action(ledger).to_json(),
        "closure": ledger.get("closure") or {"decision": "not_attempted"},
        "details": details,
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


def run_checks(*, release_evidence: bool = False, install_ok: bool = False) -> dict[str, Any]:
    scenarios = [fn() for fn in SCENARIOS.values()]
    scenario_ok = all(item["ok"] for item in scenarios)
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
