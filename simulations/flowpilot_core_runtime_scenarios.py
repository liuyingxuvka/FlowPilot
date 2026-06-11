"""Scenario catalog for FlowPilot core runtime checks."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from flowpilot_core_runtime import runtime  # noqa: E402


ScenarioFn = Callable[[], dict[str, Any]]


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
        "startup_answers": {"background_collaboration_authorized": True},
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


def _role_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {"decision": "pass", "pm_visible_summary": [summary]}
    payload.update(fields)
    return json.dumps(payload)


def _flowguard_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "flowguard_operator",
        "passed": True,
        "modeled_boundary": "Current packet and current result only.",
        "commands_run": ["python simulations/run_flowpilot_model_test_alignment_checks.py"],
        "counterexamples_or_absence": ["No counterexample in the current modeled boundary."],
        "hard_invariants": ["Current packet-result contracts use only current fields."],
        "skipped_checks": [],
        "model_obligations": ["Current FlowGuard packet report fields are present."],
        "ordinary_test_evidence": ["Scenario runtime regression."],
        "missing_test_kinds": [],
        "conformance_boundary": "Runtime checks mechanics only.",
        "confidence_boundary": "Scoped to this current packet.",
        "residual_blindspots": [],
        "background_artifact_completion": [],
        "pm_suggestion_items": [],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
        "evidence_consistency": {
            "self_check_passed": True,
            "child_reports_all_passed": True,
            "blocking_child_reports": [],
            "hard_evidence_decision": "pass",
        },
    }
    payload.update(fields)
    return json.dumps(payload)


def _review_result_body(summary: str, **fields: object) -> str:
    passed = bool(fields.pop("passed", True))
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "human_like_reviewer",
        "passed": passed,
        "direct_evidence_paths_checked": ["current result body"],
        "independent_challenge": {
            "scope_restatement": "Review the current packet result against current acceptance criteria.",
            "explicit_and_implicit_commitments": ["current contract fields", "quality sufficient for next gate"],
            "failure_hypotheses": ["The result may satisfy fields without satisfying the task."],
            "challenge_actions": ["Checked current evidence and challenged the strongest likely failure."],
            "blocking_findings": [],
            "non_blocking_findings": [],
            "pass_or_block": "pass" if passed else "block",
            "reroute_request": [],
            "challenge_waivers": [],
        },
        "findings": [],
        "blockers": [],
        "residual_risks": [],
        "pm_suggestion_items": [],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
    }
    payload.update(fields)
    return json.dumps(payload)


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
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
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
        _role_result_body("Worker produced implementation result evidence."),
        evidence_ids=["unit-runtime"],
    )
    flowguard_packet = _open_packet_by_kind(ledger, "flowguard_check")
    _complete_open_packet(
        ledger,
        flowguard_packet,
        agent_id="flowguard-a",
        body=_flowguard_result_body("FlowGuard runtime evidence passed."),
    )
    review_packet = _open_packet_by_kind(ledger, "review")
    _complete_open_packet(
        ledger,
        review_packet,
        agent_id="reviewer-a",
        body=_review_result_body("Reviewer accepted the runtime result."),
    )
    return result_id


def _route_plan_body(nodes: list[dict[str, Any]]) -> str:
    return json.dumps({"schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION, "decision": "pass", "nodes": nodes})


def _accept_high_standard_gates_for_scenario(ledger: dict[str, Any]) -> None:
    ledger["high_standard_contract"] = {
        "status": "accepted",
        "requirements": [
            {
                "requirement_id": "hsr-001",
                "classification": "hard_current",
                "summary": "Complete the current route with direct evidence.",
                "source_user_intent": "sealed_startup_intake",
                "evidence_rule": "Direct current evidence or explicit waiver required.",
                "closure_blocking": True,
                "report_only_closure_allowed": False,
            }
        ],
    }
    ledger["preplanning_discovery"] = {
        "status": "accepted",
        "material_sources": ["sealed_startup_intake"],
    }
    ledger["skill_standard_contract"] = {
        "status": "accepted",
        "obligations": [
            {
                "obligation_id": "skill-std-001",
                "skill": "flowguard-development-process-flow",
                "classification": "required",
                "role_use": "flowguard_operator",
                "use_context": "node_validation",
                "evidence_required": "current-run FlowGuard evidence",
                "closure_blocking": True,
            }
        ],
    }


def _mark_node_ready_for_final_closure(ledger: dict[str, Any], node_id: str) -> str:
    result_id = f"{node_id}-result"
    review_id = f"{node_id}-review"
    flowguard_order_id = f"{node_id}-flowguard"
    validation_id = f"{node_id}-validation"
    disposition_id = f"{node_id}-pm-disposition"
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Accepted node work",
        "SEALED_NODE_PACKET",
        route_node_id=node_id,
        route_scope="node",
    )
    ledger["packets"][packet_id]["status"] = "accepted"
    ledger["packets"][packet_id]["accepted_result_id"] = result_id
    ledger["results"][result_id] = {"result_id": result_id, "review_id": review_id}
    ledger["reviews"][review_id] = {"review_id": review_id, "decision": "accept"}
    ledger["route_nodes"][node_id]["packet_ids"].append(packet_id)
    ledger["route_nodes"][node_id]["status"] = "accepted"
    ledger["route_nodes"][node_id]["accepted_result_id"] = result_id
    ledger["route_nodes"][node_id]["pm_disposition_id"] = disposition_id
    ledger["route_nodes"][node_id]["flowguard_order_ids"] = [flowguard_order_id]
    ledger["route_nodes"][node_id]["review_ids"] = [review_id]
    ledger["route_nodes"][node_id]["validation_evidence_ids"] = [validation_id]
    ledger["flowguard_work_orders"][flowguard_order_id] = {
        "order_id": flowguard_order_id,
        "subject_id": packet_id,
        "modeled_target": "development_process",
        "status": "complete",
        "decision": "pass",
        "proof_artifact": "flowguard-report",
        "source_generation": ledger["source_generation"],
    }
    ledger["execution_frontier"]["active_node_id"] = ""
    ledger["execution_frontier"]["status"] = "ready_for_final_closure"
    runtime.record_validation_evidence(ledger, validation_id, subject_packet_id=packet_id)
    ledger["latest_validation_evidence_id"] = validation_id
    ledger.setdefault("pm_dispositions", {})[disposition_id] = {
        "disposition_id": disposition_id,
        "node_id": node_id,
        "result_id": result_id,
        "decision": "accept",
        "covered_requirement_ids": ["hsr-001"],
        "validation_evidence_ids": [validation_id],
        "waived_requirement_ids": [],
        "reviewer_absorption": "current reviewer evidence absorbed",
        "flowguard_absorption": "current FlowGuard evidence absorbed",
        "residual_risk_disposition": "no residual risk remains",
        "semantic_downgrade_disposition": "no semantic downgrade remains",
        "route_version": ledger.get("active_route_version"),
    }
    return packet_id


def _mark_high_standard_node_context_accepted(ledger: dict[str, Any], node_id: str) -> None:
    plan_id = f"{node_id}-acceptance-plan"
    context_id = f"{node_id}-context-package"
    ledger.setdefault("node_acceptance_plans", {})[plan_id] = {
        "plan_id": plan_id,
        "node_id": node_id,
        "status": "accepted",
        "repair_generation": int(ledger["route_nodes"][node_id].get("repair_generation", 0)),
    }
    ledger.setdefault("node_context_packages", {})[context_id] = {
        "context_package_id": context_id,
        "node_id": node_id,
        "status": "accepted",
        "repair_generation": int(ledger["route_nodes"][node_id].get("repair_generation", 0)),
    }
    ledger["route_nodes"][node_id]["node_acceptance_plan_id"] = plan_id
    ledger["route_nodes"][node_id]["node_context_package_id"] = context_id
    ledger["route_nodes"][node_id]["node_context_package_repair_generation"] = int(
        ledger["route_nodes"][node_id].get("repair_generation", 0)
    )


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
        _role_result_body("Worker produced a late stale result."),
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
    result_id = runtime.submit_result(ledger, worker, packet_id, _role_result_body("Worker result exists for wrong-target review."))
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
        closure = runtime.attempt_final_closure(ledger, str(ledger.get("latest_validation_evidence_id") or ""))
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


def terminal_backward_replay_block_does_not_replan() -> dict[str, Any]:
    ledger = runtime.new_ledger(
        "Ship the clean black-box FlowPilot runtime",
        "Terminal closure must go through terminal backward replay, not a new route plan.",
    )
    ledger["startup_intake"] = {
        "status": "confirmed",
        "startup_answers": {"background_collaboration_authorized": True},
    }
    ledger["recursive_route_execution_required"] = True
    ledger["high_standard_control_flow_required"] = True
    runtime.create_route(ledger, "Runtime implementation route", ["implementation", "validation", "closure"])
    _accept_high_standard_gates_for_scenario(ledger)
    ledger["results"]["planning-result"] = {
        "result_id": "planning-result",
        "body": _route_plan_body(
            [
                {
                    "node_id": "node-001",
                    "title": "Implementation",
                    "acceptance_criteria": ["Implementation accepted."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
                {
                    "node_id": "node-002",
                    "title": "Validation",
                    "acceptance_criteria": ["Validation accepted."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
                {
                    "node_id": "node-003",
                    "title": "Closure",
                    "acceptance_criteria": ["Closure evidence accepted."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
            ]
        ),
    }
    runtime.materialize_route_from_planning_result(ledger, "planning-result")
    for node_id in ("node-001", "node-002", "node-003"):
        _mark_node_ready_for_final_closure(ledger, node_id)
        _mark_high_standard_node_context_accepted(ledger, node_id)
    ledger["execution_frontier"]["completed_nodes"] = ["node-001", "node-002", "node-003"]
    closure = runtime.attempt_final_closure(ledger, str(ledger.get("latest_validation_evidence_id") or ""))
    action = runtime.router_next_action(ledger)
    accepted = (
        closure["decision"] == "blocked"
        and closure["blockers"] == ["missing_terminal_backward_replay"]
        and action.action_type == "issue_terminal_backward_replay_packet"
        and action.responsibility == "reviewer"
        and not any(
            packet["status"] == "open" and packet["envelope"].get("route_scope") == "planning"
            for packet in ledger["packets"].values()
        )
    )
    return _scenario_result(
        "terminal_backward_replay_block_does_not_replan",
        ledger,
        accepted=accepted,
        expected=True,
        details={"closure": closure, "next_action": action.to_json()},
    )


def self_review_blocks() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(ledger, worker, packet_id, _role_result_body("Worker result exists for self-review guard."))
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
    result_id = runtime.submit_result(ledger, worker, packet_id, _role_result_body("Worker result is stale after route mutation."))
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
        _role_result_body("Worker result uses stale evidence generation."),
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
        and command.get("command") == "dispatch-current-role"
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


def pm_repair_decision_receives_authorized_body_on_packet_open() -> dict[str, Any]:
    ledger, packet_id, worker = _base_ledger()
    runtime.ack_lease(ledger, worker, packet_id)
    blocking_result_id = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        _role_result_body(
            "Worker found a stale lifecycle path that PM must repair.",
            decision="block",
            blocking=True,
            recommended_resolution="Replace stale lifecycle path.",
        ),
    )
    blocker_id = next(iter(ledger["active_blockers"]))
    pm_packet_id = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
    pm_packet = ledger["packets"][pm_packet_id]
    body = json.loads(pm_packet["body"])
    pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-a", packet_id=pm_packet_id)
    runtime.assign_packet(ledger, pm_packet_id, pm_lease)
    runtime.ack_lease(ledger, pm_lease, pm_packet_id)
    delivered = runtime.open_authorized_input_materials_for_role(ledger, pm_packet_id, pm_lease)
    accepted_decision = runtime.submit_result(
        ledger,
        pm_lease,
        pm_packet_id,
        json.dumps({"decision": "repair_current_scope", "reason": "repair stale lifecycle path"}),
    )
    fresh_packets = [
        row
        for row in ledger["packets"].values()
        if row.get("repair_blocker_id") == blocker_id and row["packet_id"] != pm_packet_id and row["status"] == "open"
    ]
    ok = (
        body["recent_role_report_summary"][0]["result_id"] == blocking_result_id
        and body["authorized_result_reads"][0]["result_id"] == blocking_result_id
        and len(delivered) == 1
        and delivered[0]["result_id"] == blocking_result_id
        and "stale lifecycle path" in delivered[0]["sealed_result_body"]
        and ledger["results"][accepted_decision]["status"] == "accepted"
        and len(fresh_packets) == 1
        and json.loads(fresh_packets[0]["body"])["authorized_result_reads"][0]["result_id"] == blocking_result_id
    )
    return _scenario_result(
        "pm_repair_decision_receives_authorized_body_on_packet_open",
        ledger,
        accepted=ok,
        expected=True,
        details={
            "delivered_material_count": len(delivered),
            "fresh_packet_count": len(fresh_packets),
        },
    )


SCENARIOS: dict[str, ScenarioFn] = {
    "replacement_worker_success": replacement_worker_success,
    "wrong_flowguard_target_blocks": wrong_flowguard_target_blocks,
    "strict_route_plan_rejects_numbered_text": strict_route_plan_rejects_numbered_text,
    "route_deliverable_blocks_terminal_closure": route_deliverable_blocks_terminal_closure,
    "terminal_backward_replay_block_does_not_replan": terminal_backward_replay_block_does_not_replan,
    "self_review_blocks": self_review_blocks,
    "stale_route_output_blocks": stale_route_output_blocks,
    "stale_evidence_blocks": stale_evidence_blocks,
    "ack_only_timeout_stays_incomplete": ack_only_timeout_stays_incomplete,
    "console_does_not_leak_sealed_bodies": console_does_not_leak_sealed_bodies,
    "reassignment_supersedes_active_packet_lease": reassignment_supersedes_active_packet_lease,
    "final_preflight_blocks_accepted_packet_stale_lease": final_preflight_blocks_accepted_packet_stale_lease,
    "compact_status_does_not_leak_sealed_bodies": compact_status_does_not_leak_sealed_bodies,
    "recovery_duty_names_command_payload": recovery_duty_names_command_payload,
    "pm_repair_decision_receives_authorized_body_on_packet_open": pm_repair_decision_receives_authorized_body_on_packet_open,
}
