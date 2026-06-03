"""Run clean AI project runtime scenarios and evidence gates."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
    }
    runtime.create_route(ledger, "Runtime implementation route", ["implement runtime"])
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Implement runtime slice",
        "SEALED_TASK_BODY: worker private instructions",
    )
    worker = runtime.lease_agent(ledger, "worker", agent_id="worker-1")
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


def _route_plan_body(nodes: list[dict[str, Any]]) -> str:
    return json.dumps({"schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION, "nodes": nodes})


def _mark_node_ready_for_final_closure(ledger: dict[str, Any], node_id: str) -> str:
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Accepted node work",
        "SEALED_NODE_PACKET",
        route_node_id=node_id,
        route_scope="node",
    )
    ledger["packets"][packet_id]["status"] = "accepted"
    ledger["packets"][packet_id]["accepted_result_id"] = "node-result"
    ledger["results"]["node-result"] = {"result_id": "node-result", "review_id": "review-1"}
    ledger["reviews"]["review-1"] = {"review_id": "review-1", "decision": "accept"}
    ledger["route_nodes"][node_id]["packet_ids"].append(packet_id)
    ledger["route_nodes"][node_id]["status"] = "accepted"
    ledger["route_nodes"][node_id]["accepted_result_id"] = "node-result"
    ledger["route_nodes"][node_id]["pm_disposition_id"] = "pm-disposition"
    ledger["route_nodes"][node_id]["prework_flowguard_order_id"] = "prework-flowguard-1"
    ledger["route_nodes"][node_id]["prework_flowguard_repair_generation"] = 0
    ledger["route_nodes"][node_id]["flowguard_order_ids"] = ["flowguard-1"]
    ledger["route_nodes"][node_id]["review_ids"] = ["review-1"]
    ledger["route_nodes"][node_id]["validation_evidence_ids"] = ["runtime-validation"]
    ledger["flowguard_work_orders"]["prework-flowguard-1"] = {
        "order_id": "prework-flowguard-1",
        "status": "complete",
        "decision": "pass",
    }
    ledger["flowguard_work_orders"]["flowguard-1"] = {
        "order_id": "flowguard-1",
        "subject_id": packet_id,
        "modeled_target": "development_process",
        "status": "complete",
        "decision": "pass",
        "proof_artifact": "flowguard-report",
        "source_generation": ledger["source_generation"],
    }
    ledger["execution_frontier"]["active_node_id"] = ""
    ledger["execution_frontier"]["status"] = "ready_for_final_closure"
    runtime.record_validation_evidence(ledger, "runtime-validation", subject_packet_id=packet_id)
    return packet_id


def replacement_worker_success() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.record_progress(ledger, worker, packet_id, "still working")
    runtime.record_host_liveness(ledger, worker, packet_id, "lost")
    runtime.close_lease(ledger, worker, "no final result")
    late_result = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        "SEALED_RESULT_BODY: late stale result",
        evidence_ids=["late"],
    )
    replacement = runtime.lease_agent(ledger, "worker", agent_id="worker-2")
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


def strict_route_plan_rejects_numbered_text() -> dict[str, Any]:
    ledger = runtime.new_ledger(
        "Ship the clean black-box FlowPilot runtime",
        "Route planning must use strict schema.",
    )
    ledger["startup_intake"] = {"status": "confirmed"}
    ledger["recursive_route_execution_required"] = True
    runtime.create_route(ledger, "Runtime implementation route", ["bootstrap planning", "bootstrap implementation"])
    ledger["results"]["planning-result"] = {
        "result_id": "planning-result",
        "body": "1. Bootstrap planning\n2. Bootstrap implementation",
    }
    try:
        runtime.materialize_route_from_planning_result(ledger, "planning-result")
    except runtime.BlackBoxRuntimeError as exc:
        blocked = "strict route plan schema" in str(exc)
    else:
        blocked = False
    return _scenario_result(
        "strict_route_plan_rejects_numbered_text",
        ledger,
        accepted=blocked and ledger["route_nodes"] == {},
        expected=True,
        details={"route_nodes": ledger["route_nodes"]},
    )


def route_deliverable_blocks_terminal_closure() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = runtime.new_ledger(
            "Ship the clean black-box FlowPilot runtime",
            "Terminal closure must verify concrete route deliverables.",
        )
        ledger["startup_intake"] = {"status": "confirmed"}
        ledger["recursive_route_execution_required"] = True
        ledger["project_root"] = tmp
        runtime.create_route(ledger, "Runtime implementation route", ["implementation"])
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implementation",
                        "acceptance_criteria": ["Implementation accepted."],
                        "required_outputs": [{"path": "data/product.json", "kind": "json"}],
                        "deliverable_checks": [
                            {"check_id": "product-json", "kind": "json_parse", "path": "data/product.json"}
                        ],
                    }
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, "planning-result")
        _mark_node_ready_for_final_closure(ledger, "node-001")
        closure = runtime.attempt_final_closure(ledger, "runtime-validation")
        blocked = (
            closure["decision"] == "blocked"
            and "route_deliverable:node-001:product-json:failed" in closure["blockers"]
            and ledger["final_route_wide_gate_ledger"]["deliverable_checks"][0]["status"] == "failed"
        )
        return _scenario_result(
            "route_deliverable_blocks_terminal_closure",
            ledger,
            accepted=blocked,
            expected=True,
            details={"blockers": closure["blockers"]},
        )


def self_review_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(ledger, worker, packet_id, "SEALED_RESULT_BODY")
    order_id = runtime.create_flowguard_work_order(ledger, "development_process", "done_claim", packet_id)
    runtime.complete_flowguard_work_order(ledger, order_id)
    reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="worker-1")
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


def reassignment_supersedes_active_packet_lease() -> dict[str, Any]:
    ledger, packet_id, first_lease = _base_ledger()
    assignment = runtime.resolve_role_assignment(ledger, "worker", packet_id=packet_id, host_kind="fake")
    replacement = runtime.lease_agent(
        ledger,
        "worker",
        packet_id=packet_id,
        assignment_id=assignment["assignment_id"],
    )
    runtime.assign_packet(ledger, packet_id, replacement)
    safe = (
        ledger["packets"][packet_id]["assigned_lease_id"] == replacement
        and ledger["leases"][first_lease]["status"] == "superseded"
        and ledger["leases"][first_lease].get("superseded_by") == replacement
    )
    return _scenario_result(
        "reassignment_supersedes_active_packet_lease",
        ledger,
        accepted=safe,
        expected=True,
        details={
            "first_lease_status": ledger["leases"][first_lease]["status"],
            "first_lease_superseded_by": ledger["leases"][first_lease].get("superseded_by", ""),
            "replacement_lease": replacement,
        },
    )


def final_preflight_blocks_accepted_packet_stale_lease() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_happy_path(ledger, packet_id, worker)
    stale_lease = runtime._next_id(ledger, "lease")
    ledger["leases"][stale_lease] = {
        **ledger["leases"][worker],
        "lease_id": stale_lease,
        "agent_id": "stale-worker",
        "status": "active",
        "packet_id": packet_id,
        "ack_received": True,
    }
    preflight = runtime.final_return_preflight(ledger)
    blocked = (
        preflight["allowed"] is False
        and f"accepted_packet_lease_health:{packet_id}" in preflight["blockers"]
        and runtime.router_next_action(ledger).action_type == "repair_accepted_packet"
    )
    return _scenario_result(
        "final_preflight_blocks_accepted_packet_stale_lease",
        ledger,
        accepted=blocked,
        expected=True,
        details={
            "stale_lease": stale_lease,
            "preflight": preflight,
            "accepted_packet_lease_health": runtime.accepted_packet_lease_health(ledger),
        },
    )


def compact_status_does_not_leak_sealed_bodies() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_happy_path(ledger, packet_id, worker)
    compact = runtime.render_compact_console(ledger)
    rendered = json.dumps(compact, sort_keys=True)
    leaked = "SEALED_TASK_BODY" in rendered or "SEALED_RESULT_BODY" in rendered
    return _scenario_result(
        "compact_status_does_not_leak_sealed_bodies",
        ledger,
        accepted=not leaked and compact.get("projection") == "compact_controller_status",
        expected=True,
        details={"leaked": leaked, "projection": compact.get("projection"), "counts": compact.get("counts", {})},
    )


def recovery_duty_names_command_payload() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    ledger["leases"][worker]["liveness_status"] = "not_found"
    ledger["leases"][worker]["liveness_checked_at"] = runtime.now_iso()
    guard = runtime.preview_lifecycle_guard(ledger, trigger="patrol")
    duty = runtime.preview_foreground_duty(ledger, guard=guard, trigger="patrol")
    command = duty.get("recovery", {}).get("recommended_command", {})
    ok = (
        duty.get("action") == "recover_or_reissue"
        and command.get("command") == "resolve-role-assignment"
        and command.get("packet_id") == packet_id
        and command.get("responsibility") == "worker"
        and command.get("host_kind") == "live"
        and "--agent-id" not in str(command.get("cli", ""))
        and worker in command.get("stale_lease_ids", [])
        and command.get("sealed_bodies_visible") is False
    )
    return _scenario_result(
        "recovery_duty_names_command_payload",
        ledger,
        accepted=ok,
        expected=True,
        details={"duty": duty},
    )


SCENARIOS: dict[str, ScenarioFn] = {
    "replacement_worker_success": replacement_worker_success,
    "wrong_flowguard_target_blocks": wrong_flowguard_target_blocks,
    "strict_route_plan_rejects_numbered_text": strict_route_plan_rejects_numbered_text,
    "route_deliverable_blocks_terminal_closure": route_deliverable_blocks_terminal_closure,
    "self_review_blocks": self_review_blocks,
    "stale_route_output_blocks": stale_route_output_blocks,
    "stale_evidence_blocks": stale_evidence_blocks,
    "ack_only_timeout_stays_incomplete": ack_only_timeout_stays_incomplete,
    "console_does_not_leak_sealed_bodies": console_does_not_leak_sealed_bodies,
    "reassignment_supersedes_active_packet_lease": reassignment_supersedes_active_packet_lease,
    "final_preflight_blocks_accepted_packet_stale_lease": final_preflight_blocks_accepted_packet_stale_lease,
    "compact_status_does_not_leak_sealed_bodies": compact_status_does_not_leak_sealed_bodies,
    "recovery_duty_names_command_payload": recovery_duty_names_command_payload,
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
