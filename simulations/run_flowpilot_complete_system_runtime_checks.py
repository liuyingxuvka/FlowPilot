"""Run complete black-box FlowPilot runtime and fake-agent chaos checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_runtime_results.json"
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from flowpilot_core_runtime import (  # noqa: E402
    cockpit,
    flowguard_orders,
    host,
    migration,
    packet_result_contracts,
    packets,
    review_closure,
    runtime,
)


ScenarioFn = Callable[[], dict[str, Any]]


def _base_ledger() -> tuple[dict[str, Any], str, str]:
    ledger = runtime.new_ledger(
        "Complete black-box FlowPilot system",
        "Accept only with current ledger, dynamic lease, FlowGuard, review, validation, and cutover evidence.",
    )
    ledger["startup_intake"] = {
        "status": "confirmed",
        "sealed": True,
        "source": "test",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    runtime.create_route(ledger, "Complete-system route", ["execute packet"])
    packet_id = packets.issue_packet(ledger, "worker", "Execute packet", "SEALED_TASK_BODY: complete-system work")
    lease_id = host.lease_responsibility(ledger, "worker", host_kind="fake", scope="node")
    runtime.assign_packet(ledger, packet_id, lease_id)
    return ledger, packet_id, lease_id


def _open_packet_by_kind(ledger: dict[str, Any], packet_kind: str) -> str:
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"].get("packet_kind", "task") == packet_kind and packet["status"] == "open":
            return str(packet_id)
    raise AssertionError(f"missing open {packet_kind} packet")


def _current_contract_body(ledger: dict[str, Any], packet_id: str, **updates: Any) -> str:
    packet = ledger["packets"][packet_id]
    family_id = packet_result_contracts.packet_result_family_id(packet["envelope"])
    payload = dict(packet_result_contracts.minimal_valid_shape_for_family(family_id))
    payload.update(updates)
    return json.dumps(payload)


def _complete_open_packet(ledger: dict[str, Any], packet_id: str, *, agent_id: str, body: str = "") -> str:
    packet = ledger["packets"][packet_id]
    lease_id = host.lease_responsibility(
        ledger,
        packet["envelope"]["responsibility"],
        host_kind="fake",
        agent_id=agent_id,
        packet_id=packet_id,
        scope="complete-system",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    return host.submit_host_result(
        ledger,
        lease_id,
        packet_id,
        body or _current_contract_body(ledger, packet_id),
        evidence_ids=[f"{packet['envelope'].get('packet_kind', 'task')}-complete-system"],
    )


def _latest_validation_evidence_id(ledger: dict[str, Any]) -> str:
    evidence_id = str(ledger.get("latest_validation_evidence_id", ""))
    if evidence_id:
        return evidence_id
    if ledger.get("validation_evidence"):
        return next(reversed(ledger["validation_evidence"]))
    return "runtime-validation"


def _complete_packet(ledger: dict[str, Any], packet_id: str, lease_id: str) -> str:
    runtime.ack_lease(ledger, lease_id, packet_id)
    result_id = host.submit_host_result(
        ledger,
        lease_id,
        packet_id,
        _current_contract_body(ledger, packet_id),
        evidence_ids=["runtime-unit"],
    )
    flowguard_packet = _open_packet_by_kind(ledger, "flowguard_check")
    _complete_open_packet(
        ledger,
        flowguard_packet,
        agent_id="flowguard-complete-system",
    )
    review_packet = _open_packet_by_kind(ledger, "review")
    _complete_open_packet(
        ledger,
        review_packet,
        agent_id="reviewer-complete-system",
    )
    return result_id


def dead_worker_replaced() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.record_progress(ledger, worker, packet_id, "working")
    runtime.expire_lease(ledger, worker)
    late = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    replacement = host.lease_responsibility(ledger, "worker", host_kind="fake", scope="replacement")
    runtime.assign_packet(ledger, packet_id, replacement)
    _complete_packet(ledger, packet_id, replacement)
    closure = ledger["closure"]
    return _scenario_result(
        "dead_worker_replaced",
        closure["decision"] == "complete" and "closed_or_inactive_lease" in ledger["results"][late]["mechanical_blockers"],
        ledger,
        {"late_blockers": ledger["results"][late]["mechanical_blockers"]},
    )


def cockpit_direct_write_rejected() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_packet(ledger, packet_id, worker)
    event = cockpit.submit_cockpit_event(ledger, "pause", {"packets": {"packet-0001": "mutate"}})
    projection = cockpit.render_status(ledger)
    rendered = json.dumps(projection, sort_keys=True)
    return _scenario_result(
        "cockpit_direct_write_rejected",
        not event["accepted"] and "SEALED_TASK_BODY" not in rendered and "SEALED_RESULT_BODY" not in rendered,
        ledger,
        {"event": event},
    )


def imported_old_artifact_is_read_only() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_packet(ledger, packet_id, worker)
    import_id = migration.import_old_artifact(
        ledger,
        Path("old/.flowpilot/state.json"),
        disposition="imported_read_only",
        reason="historical context only",
    )
    record = ledger["imported_evidence"][import_id]
    return _scenario_result(
        "imported_old_artifact_is_read_only",
        record["current_authority"] is False,
        ledger,
        {"import": record},
    )


def cutover_requires_live_host() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_packet(ledger, packet_id, worker)
    gate = migration.evaluate_cutover_gate(
        ledger,
        openspec_ok=True,
        flowguard_ok=True,
        tests_ok=True,
        install_ok=True,
        live_host_ok=False,
        git_ok=True,
    )
    closure = review_closure.attempt_final_closure(ledger, _latest_validation_evidence_id(ledger))
    return _scenario_result(
        "cutover_requires_live_host",
        gate["decision"] == "blocked" and closure["decision"] == "blocked",
        ledger,
        {"gate": gate, "closure": closure},
    )


def wrong_flowguard_target_blocks_complete_system() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    order_id = flowguard_orders.create_work_order(ledger, "target_product_behavior", "wrong_target", packet_id)
    flowguard_orders.complete_work_order(ledger, order_id)
    reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
    review_id = review_closure.review_result(ledger, result_id, reviewer)
    return _scenario_result(
        "wrong_flowguard_target_blocks_complete_system",
        ledger["reviews"][review_id]["decision"] == "block"
        and "missing_matching_flowguard_report" in ledger["reviews"][review_id]["blockers"],
        ledger,
        {"review": ledger["reviews"][review_id]},
    )


def route_mutation_quarantines_old_packet() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    runtime.create_route(ledger, "Mutated complete-system route", ["execute replacement packet"])
    mutation = ledger["route_mutations"][-1]
    return _scenario_result(
        "route_mutation_quarantines_old_packet",
        ledger["packets"][packet_id]["status"] == "quarantined_after_route_mutation"
        and packet_id in mutation["affected_packets"]
        and mutation["requires_replay_or_rebinding"],
        ledger,
        {"mutation": mutation, "old_packet": ledger["packets"][packet_id]},
    )


def body_hash_mismatch_blocks_result() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = host.submit_host_result(
        ledger,
        worker,
        packet_id,
        _current_contract_body(ledger, packet_id),
        packet_body_hash="wrong-body-hash",
    )
    return _scenario_result(
        "body_hash_mismatch_blocks_result",
        "body_hash_mismatch" in ledger["results"][result_id]["mechanical_blockers"],
        ledger,
        {"result": ledger["results"][result_id]},
    )


def duplicate_output_blocks_second_result() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    first = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    second = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    return _scenario_result(
        "duplicate_output_blocks_second_result",
        ledger["results"][first]["status"] == "mechanically_valid"
        and "duplicate_output_from_same_lease" in ledger["results"][second]["mechanical_blockers"],
        ledger,
        {"first": ledger["results"][first], "second": ledger["results"][second]},
    )


def missing_target_and_report_only_flowguard_block_review() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    missing_target_blocked = False
    try:
        flowguard_orders.create_work_order(ledger, "", "done_claim", packet_id)
    except runtime.BlackBoxRuntimeError:
        missing_target_blocked = True
    order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", packet_id)
    flowguard_orders.complete_work_order(ledger, order_id, progress_only=True)
    reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
    review_id = review_closure.review_result(ledger, result_id, reviewer)
    return _scenario_result(
        "missing_target_and_report_only_flowguard_block_review",
        missing_target_blocked
        and ledger["reviews"][review_id]["decision"] == "block"
        and "missing_matching_flowguard_report" in ledger["reviews"][review_id]["blockers"],
        ledger,
        {"review": ledger["reviews"][review_id]},
    )


def stale_proof_artifact_blocks_review() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = host.submit_host_result(ledger, worker, packet_id, _current_contract_body(ledger, packet_id))
    order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", packet_id)
    flowguard_orders.complete_work_order(ledger, order_id, proof_artifact="simulations/stale.json")
    ledger["flowguard_work_orders"][order_id]["proof_stale"] = True
    reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
    review_id = review_closure.review_result(ledger, result_id, reviewer)
    return _scenario_result(
        "stale_proof_artifact_blocks_review",
        ledger["reviews"][review_id]["decision"] == "block"
        and "missing_matching_flowguard_report" in ledger["reviews"][review_id]["blockers"],
        ledger,
        {"order": ledger["flowguard_work_orders"][order_id], "review": ledger["reviews"][review_id]},
    )


def completion_claim_resources_risks_and_old_ui_block_closure() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    _complete_packet(ledger, packet_id, worker)
    runtime.record_completion_claim(ledger, source="chat", claim="done")
    ledger["open_resources"].append("runtime-role-slot")
    ledger["residual_risks"].append("live host missing")
    ledger["old_ui_evidence"].append("old screenshot")
    closure = runtime.attempt_final_closure(ledger, _latest_validation_evidence_id(ledger))
    expected = {
        "completion_report_only_not_sufficient",
        "unresolved_resources",
        "unresolved_residual_risks",
        "old_ui_evidence_unresolved",
    }
    return _scenario_result(
        "completion_claim_resources_risks_and_old_ui_block_closure",
        expected.issubset(set(closure["blockers"])),
        ledger,
        {"closure": closure},
    )


def cockpit_disconnect_records_display_surface_blocker() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    blocked = cockpit.record_display_surface_blocker(ledger, "cockpit_unavailable")
    projection = cockpit.render_status(ledger)
    return _scenario_result(
        "cockpit_disconnect_records_display_surface_blocker",
        blocked["blocker"]["repair_required"]
        and projection["display_surface"]["active"] == "blocked",
        ledger,
        {"blocker": blocked["blocker"]},
    )


SCENARIOS: dict[str, ScenarioFn] = {
    "dead_worker_replaced": dead_worker_replaced,
    "cockpit_direct_write_rejected": cockpit_direct_write_rejected,
    "imported_old_artifact_is_read_only": imported_old_artifact_is_read_only,
    "cutover_requires_live_host": cutover_requires_live_host,
    "wrong_flowguard_target_blocks_complete_system": wrong_flowguard_target_blocks_complete_system,
    "route_mutation_quarantines_old_packet": route_mutation_quarantines_old_packet,
    "body_hash_mismatch_blocks_result": body_hash_mismatch_blocks_result,
    "duplicate_output_blocks_second_result": duplicate_output_blocks_second_result,
    "missing_target_and_report_only_flowguard_block_review": missing_target_and_report_only_flowguard_block_review,
    "stale_proof_artifact_blocks_review": stale_proof_artifact_blocks_review,
    "completion_claim_resources_risks_and_old_ui_block_closure": completion_claim_resources_risks_and_old_ui_block_closure,
    "cockpit_disconnect_records_display_surface_blocker": cockpit_disconnect_records_display_surface_blocker,
}


def _scenario_result(name: str, ok: bool, ledger: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "next_action": runtime.router_next_action(ledger).to_json(),
        "closure": ledger.get("closure") or {"decision": "not_attempted"},
        "details": details,
    }


def run_checks(*, release_evidence: bool = False, live_host_evidence: bool = False) -> dict[str, Any]:
    scenarios = [scenario() for scenario in SCENARIOS.values()]
    scenario_ok = all(item["ok"] for item in scenarios)
    rows = [
        {
            "id": "complete_runtime_scenarios",
            "status": "passed" if scenario_ok else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/run_flowpilot_complete_system_runtime_checks.py"],
            "details": {"case_count": len(scenarios)},
        },
        {
            "id": "complete_runtime_release_boundary",
            "status": "passed" if release_evidence and live_host_evidence else "not_run",
            "freshness": "current" if release_evidence and live_host_evidence else "not_run",
            "scope": "release",
            "evidence": ["live-host evidence required"] if not live_host_evidence else ["live-host evidence supplied"],
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_runtime_checks",
        "ok": scenario_ok,
        "mode": "release" if release_evidence and live_host_evidence else "routine",
        "scenarios": scenarios,
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": rows[0]["status"] == "passed"},
            "release_gate": {"ok": all(row["status"] == "passed" for row in rows)},
        },
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
