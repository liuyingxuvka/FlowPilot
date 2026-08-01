from __future__ import annotations

import copy
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

runtime = importlib.import_module("flowpilot_core_runtime.runtime")
host = importlib.import_module("flowpilot_core_runtime.host")
packet_result_contracts = importlib.import_module("flowpilot_core_runtime.packet_result_contracts")


def _recursive_ledger() -> tuple[dict, str]:
    ledger = runtime.new_ledger("Build target", "Accept only after every route node is complete.")
    ledger["startup_intake"] = {
        "sealed": True,
        "startup_answers": {runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True},
    }
    ledger["recursive_route_execution_required"] = True
    runtime.create_route(ledger, "Recursive route", ["planning", "implementation", "validation"])
    packet_id = runtime.issue_task_packet(
        ledger,
        "pm",
        "Plan the route",
        "SEALED_PM_PLAN_PACKET",
        route_scope="planning",
        required_flowguard_target="development_process",
    )
    return ledger, packet_id


def _open_packets(ledger: dict, kind: str | None = None, scope: str | None = None) -> list[str]:
    rows: list[str] = []
    for packet_id, packet in ledger["packets"].items():
        if packet["status"] != "open":
            continue
        if kind and packet["envelope"].get("packet_kind", "task") != kind:
            continue
        if scope and packet["envelope"].get("route_scope") != scope:
            continue
        rows.append(packet_id)
    return rows


def _pass_body(summary: str, **extra: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-recursive-route-evidence"],
    }
    payload.update(extra)
    return json.dumps(payload)


def _flowguard_pass_body(summary: str, **extra: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("flowguard_check.post_result")
    payload["pm_visible_summary"] = [summary]
    payload.update(extra)
    return json.dumps(payload)


def _review_pass_body(summary: str, **extra: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("review.any_current_subject")
    payload["pm_visible_summary"] = [summary]
    payload.update(extra)
    return json.dumps(payload)


def _role_pass_body(kind: str, summary: str, **extra: object) -> str:
    if kind == "flowguard_check":
        return _flowguard_pass_body(summary, **extra)
    if kind == "review":
        return _review_pass_body(summary, **extra)
    return _pass_body(summary, **extra)


def _pm_disposition_body(decision: str, reason: str) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("pm_disposition.node_pm_disposition")
    payload["decision"] = decision
    payload["reason"] = reason
    if decision == "redesign_route":
        payload["route_plan"] = {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": [
                {
                    "node_id": "node-001-repair-v2",
                    "title": "Repair node-001 after PM redesign",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Replacement work is accepted with current evidence."],
                }
            ],
        }
    return json.dumps(payload)


def _milestone_pm_accept_body(
    ledger: dict,
    packet_id: str,
    *,
    remaining_route_plan: dict | None = None,
    reason: str = "Accept the current milestone after a fresh audit and complete remaining-plan rewrite.",
) -> str:
    packet = ledger["packets"][packet_id]
    handoff = packet["envelope"]["current_handoff_contract"]
    contract = handoff["required_report_contract"]
    payload = copy.deepcopy(contract["minimal_valid_shape"])
    packet_body = json.loads(packet["body"])
    if remaining_route_plan is None:
        remaining_route_plan = packet_body["prior_remaining_route_plan_context"]["plan"]
    canonical_plan = runtime._canonical_remaining_route_plan(remaining_route_plan)
    payload["decision"] = "accept"
    payload["reason"] = reason
    payload["remaining_route_plan"] = canonical_plan
    payload["milestone_audit"]["contract_hash"] = ledger.get("contract_hash", "")
    if canonical_plan["nodes"]:
        obligations = runtime._milestone_remaining_obligation_ids(
            ledger,
            node_id=str(packet_body.get("route_node_id") or ""),
            acceptance_item_disposition=payload.get(
                "acceptance_item_disposition", []
            ),
        )
        payload["milestone_audit"]["remaining"] = [
            {
                "obligation": "Complete every still-open part of the accepted final user goal.",
                "gap": "The freshly emitted remaining route has not executed yet.",
                "owner_node_ids": [str(node.get("node_id") or "") for node in canonical_plan["nodes"]],
                "obligation_ids": [
                    f"{field}:{item}"
                    for field, values in obligations.items()
                    for item in values
                ],
            }
        ]
    else:
        payload["milestone_audit"]["remaining"] = []
    return json.dumps(payload)


def _pm_flowguard_acceptance_body(
    ledger: dict,
    *,
    decision: str = "accept",
    route_plan: dict | None = None,
) -> str:
    gate = list(ledger["pm_decision_gates"].values())[-1]
    order = ledger["flowguard_work_orders"][gate["flowguard_order_id"]]
    payload = packet_result_contracts.minimal_valid_shape_for_family("pm_flowguard_acceptance.pm_flowguard_acceptance")
    payload.update(
        {
            "decision": decision,
            "reason": "PM absorbed the structural FlowGuard report.",
            "flowguard_absorption": "PM accepted the current FlowGuard report before Reviewer review.",
            "accepted_flowguard_result_id": order["proof_result_id"],
        }
    )
    if decision == "redesign_route":
        payload["route_plan"] = route_plan or {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": [
                {
                    "node_id": "unsafe-whole-route-replacement",
                    "title": "Unsafe whole-route replacement",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["This plan must not replace the accepted prefix."],
                }
            ],
        }
    return json.dumps(payload)


def _complete_open_packet(ledger: dict, packet_id: str, body: str | None = None) -> str:
    packet = ledger["packets"][packet_id]
    responsibility = packet["envelope"]["responsibility"]
    if body is None:
        body = _pass_body(f"{responsibility} completed {packet_id}.")
    if packet["envelope"].get("packet_kind") == "pm_disposition":
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        handoff = packet["envelope"].get("current_handoff_contract") or {}
        contract = handoff.get("required_report_contract") or {}
        minimal_valid_shape = contract.get("minimal_valid_shape")
        if isinstance(payload, dict) and isinstance(minimal_valid_shape, dict):
            if payload.get("acceptance_item_disposition") == packet_result_contracts.minimal_valid_shape_for_family(
                "pm_disposition.node_pm_disposition"
            ).get("acceptance_item_disposition"):
                payload["acceptance_item_disposition"] = minimal_valid_shape.get(
                    "acceptance_item_disposition",
                    payload.get("acceptance_item_disposition"),
                )
                body = json.dumps(payload)
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        host_kind="fake",
        agent_id=f"{responsibility}-{packet_id}",
        packet_id=packet_id,
        scope="recursive-route-test",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    if packet["envelope"].get("packet_kind") == "flowguard_check":
        _write_flowguard_evidence_artifact(ledger, packet, body or "")
    return host.submit_host_result(ledger, lease_id, packet_id, body)


def _write_flowguard_evidence_artifact(ledger: dict, packet: dict, body: str) -> None:
    packet_body = json.loads(packet.get("body") or "{}")
    evidence_policy = packet_body.get("evidence_output_policy")
    if isinstance(evidence_policy, dict):
        root = str(evidence_policy.get("run_local_evidence_root") or "")
        if "<" in root or ">" in root:
            run_root = str(ledger.get("run_root") or "")
            if run_root:
                root_path = Path(run_root) / "evidence" / "flowguard" / packet["packet_id"]
            else:
                root_path = ROOT / ".tmp_flowguard_evidence" / "recursive_route_execution_runtime" / packet["packet_id"]
            evidence_policy["run_local_evidence_root"] = str(root_path)
            packet["body"] = json.dumps(packet_body, sort_keys=True)
            packet["envelope"]["body_hash"] = runtime.hash_text(packet["body"])
    path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
    if path is None:
        return
    decision = "pass"
    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get("passed") is False:
        decision = "blocked"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": {
                    "decision": decision,
                    "failed_predicates": [] if decision == "pass" else ["recursive_route_test_block"],
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _route_plan_body(nodes: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "decision": "pass",
            "nodes": nodes
            or [
                {
                    "node_id": "node-001",
                    "title": "Plan architecture and contracts",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Architecture and contract work is accepted with current evidence."],
                },
                {
                    "node_id": "node-002",
                    "title": "Implement UI and runtime behavior",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Implementation work is accepted with current evidence."],
                },
                {
                    "node_id": "node-003",
                    "title": "Validate evidence and closure",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Validation and closure work is accepted with current evidence."],
                },
            ],
        }
    )


def _complete_foundation_planning_chain(ledger: dict, pm_packet: str) -> None:
    _complete_open_packet(ledger, pm_packet, _route_plan_body())
    for kind in ("flowguard_check", "review"):
        packet_id = _open_packets(ledger, kind)[0]
        _complete_open_packet(ledger, packet_id, _role_pass_body(kind, f"{kind} accepted foundation planning."))


def _advance_active_node_to_pm_disposition(ledger: dict) -> tuple[str, str]:
    runtime.run_until_wait(ledger)
    node_id = ledger["execution_frontier"]["active_node_id"]
    task_packet = _open_packets(ledger, "task", scope="node")[0]
    _complete_open_packet(ledger, task_packet, _pass_body(f"Worker completed {node_id}.", node_id=node_id))
    for kind in ("flowguard_check", "review"):
        packet_id = _open_packets(ledger, kind)[0]
        _complete_open_packet(ledger, packet_id, _role_pass_body(kind, f"{kind} accepted {node_id}."))
    pm_packet = _open_packets(ledger, "pm_disposition")[0]
    return node_id, pm_packet


def _complete_milestone_decision_gate(ledger: dict, node_id: str) -> None:
    flowguard_packets = _open_packets(ledger, "flowguard_check")
    if not flowguard_packets:
        # The final top-level node may enter terminal closure directly; there
        # is no remaining route to renew after an explicit empty-plan result.
        return
    flowguard_packet = flowguard_packets[0]
    _complete_open_packet(
        ledger,
        flowguard_packet,
        _flowguard_pass_body(f"Milestone renewal FlowGuard accepted {node_id}."),
    )
    pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]
    _complete_open_packet(ledger, pm_acceptance_packet, _pm_flowguard_acceptance_body(ledger))
    review_packet = _open_packets(ledger, "review")[0]
    _complete_open_packet(
        ledger,
        review_packet,
        _review_pass_body(f"Milestone renewal Reviewer accepted {node_id}."),
    )


def _complete_active_node(
    ledger: dict,
    *,
    remaining_route_plan: dict | None = None,
) -> str:
    node_id, pm_packet = _advance_active_node_to_pm_disposition(ledger)
    _complete_open_packet(
        ledger,
        pm_packet,
        _milestone_pm_accept_body(
            ledger,
            pm_packet,
            remaining_route_plan=remaining_route_plan,
        ),
    )
    _complete_milestone_decision_gate(ledger, node_id)
    return node_id


def _mark_node_ready_for_final_closure(ledger: dict, node_id: str) -> None:
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
    ledger["results"]["node-result"] = {
        "result_id": "node-result",
        "packet_id": packet_id,
        "status": "accepted",
        "accepted": True,
        "review_id": "review-1",
        "producer_lease_id": "",
    }
    ledger["reviews"]["review-1"] = {
        "review_id": "review-1",
        "decision": "accept",
        "blockers": [],
    }
    ledger["route_nodes"][node_id]["packet_ids"].append(packet_id)
    ledger["route_nodes"][node_id]["status"] = "accepted"
    ledger["route_nodes"][node_id]["accepted_result_id"] = "node-result"
    ledger["route_nodes"][node_id]["pm_disposition_id"] = "pm-disposition"
    ledger["route_nodes"][node_id]["flowguard_order_ids"] = ["flowguard-1"]
    ledger["route_nodes"][node_id]["review_ids"] = ["review-1"]
    ledger["route_nodes"][node_id]["validation_evidence_ids"] = ["runtime-validation"]
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


class FlowPilotRecursiveRouteExecutionRuntimeTests(unittest.TestCase):
    def test_pm_planning_chain_materializes_nodes_instead_of_terminal_completion(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        self.assertNotEqual((ledger.get("closure") or {}).get("decision"), "complete")
        self.assertEqual(len(ledger["route_nodes"]), 3)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001")
        action = runtime.router_next_action(ledger).to_json()
        self.assertEqual(action["action_type"], "dispatch_current_role")
        self.assertEqual(action["subject_id"], _open_packets(ledger, "task", scope="node")[0])

    def test_top_level_pm_packet_binds_milestone_renewal_profile(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        packet = ledger["packets"][disposition_packet_id]
        contract = packet["envelope"]["current_handoff_contract"]["required_report_contract"]
        packet_body = json.loads(packet["body"])

        self.assertEqual(node_id, "node-001")
        self.assertEqual(
            contract["result_contract_profile_ids"],
            [packet_result_contracts.MILESTONE_PLAN_RENEWAL_RESULT_CONTRACT_PROFILE_ID],
        )
        self.assertTrue(packet_body["milestone_plan_renewal_required"])
        self.assertEqual(packet_body["major_milestone_rule"], "top_level_route_node_parent_node_id_empty")
        self.assertIn("milestone_audit", contract["required_result_body_fields"])
        self.assertIn("remaining_route_plan", contract["required_result_body_fields"])

    def test_bare_unchanged_marker_is_rejected_without_frontier_advance(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        packet = ledger["packets"][disposition_packet_id]
        contract = packet["envelope"]["current_handoff_contract"]["required_report_contract"]
        payload = copy.deepcopy(contract["minimal_valid_shape"])
        payload["remaining_route_plan"] = json.loads(packet["body"])["prior_remaining_route_plan_context"]["plan"]
        payload["unchanged"] = True

        result_id = _complete_open_packet(ledger, disposition_packet_id, json.dumps(payload))

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertIn("freshly emit", ledger["results"][result_id]["blocked_reason"])
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(ledger["execution_frontier"]["status"], "awaiting_pm_disposition")
        self.assertEqual(ledger["pm_decision_gates"], {})

    def test_fresh_unchanged_remaining_plan_commits_without_route_version_bump(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        packet_body = json.loads(ledger["packets"][disposition_packet_id]["body"])
        prior_fingerprint = packet_body["prior_remaining_route_plan_context"]["fingerprint"]

        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )

        self.assertEqual(ledger["route_nodes"][node_id]["status"], "awaiting_milestone_plan_renewal")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        _complete_milestone_decision_gate(ledger, node_id)

        projection = runtime.render_compact_console(ledger)["latest_milestone_plan_renewal"]
        self.assertEqual(ledger["active_route_version"], 1)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-002")
        self.assertEqual(ledger["execution_frontier"]["blocked_reason"], "")
        self.assertFalse(projection["route_plan_changed"])
        self.assertEqual(projection["remaining_plan_fingerprint"], prior_fingerprint)
        self.assertEqual(projection["prior_remaining_plan_fingerprint"], prior_fingerprint)

    def test_nested_child_acceptance_stays_lightweight_and_does_not_open_global_gate(self) -> None:
        ledger = runtime.new_ledger("Nested goal", "Accept a nested child before its parent milestone.")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True},
        }
        ledger["recursive_route_execution_required"] = True
        runtime.create_route(ledger, "Nested route", ["child", "parent"])
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": _route_plan_body(
                [
                    {
                        "node_id": "child-001",
                        "title": "Nested implementation",
                        "node_kind": "leaf",
                        "parent_node_id": "parent-001",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["The nested implementation is accepted."],
                    },
                    {
                        "node_id": "parent-001",
                        "title": "Top-level milestone",
                        "node_kind": "module",
                        "child_node_ids": ["child-001"],
                        "responsibility": "pm",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["The parent milestone is accepted after its child."],
                    },
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, "planning-result")
        task_packet = runtime.ensure_next_node_task_packet(ledger)
        _complete_open_packet(ledger, task_packet, _pass_body("Nested child completed.", node_id="child-001"))
        for kind in ("flowguard_check", "review"):
            packet_id = _open_packets(ledger, kind)[0]
            _complete_open_packet(ledger, packet_id, _role_pass_body(kind, f"{kind} accepted child-001."))
        disposition_packet_id = _open_packets(ledger, "pm_disposition")[0]
        contract = ledger["packets"][disposition_packet_id]["envelope"]["current_handoff_contract"][
            "required_report_contract"
        ]

        self.assertEqual(contract["result_contract_profile_ids"], [])
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _pm_disposition_body("accept", "Accept the nested child locally."),
        )

        self.assertEqual(ledger["route_nodes"]["child-001"]["status"], "accepted")
        self.assertEqual(ledger["active_route_version"], 1)
        self.assertEqual(ledger["pm_decision_gates"], {})
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "parent-001")

    def test_reviewer_block_keeps_milestone_and_frontier_uncommitted(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )
        flowguard_packet = _open_packets(ledger, "flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_pass_body("FlowGuard accepted the renewal."))
        pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]
        _complete_open_packet(ledger, pm_acceptance_packet, _pm_flowguard_acceptance_body(ledger))
        review_packet = _open_packets(ledger, "review")[0]
        review_payload = json.loads(_review_pass_body("Reviewer blocked final-goal continuity."))
        review_payload["passed"] = False
        review_payload["blockers"] = ["remaining route is not connected to the accepted final goal"]

        _complete_open_packet(ledger, review_packet, json.dumps(review_payload))

        gate = list(ledger["pm_decision_gates"].values())[-1]
        self.assertEqual(gate["status"], "review_blocked")
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "awaiting_milestone_plan_renewal")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(ledger["active_route_version"], 1)
        self.assertEqual(ledger["execution_frontier"]["completed_nodes"], [])

    def test_milestone_flowguard_absorption_cannot_escape_into_whole_route_redesign(self) -> None:
        for decision in ("block", "redesign_route"):
            with self.subTest(decision=decision):
                ledger, pm_packet = _recursive_ledger()
                _complete_foundation_planning_chain(ledger, pm_packet)
                node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
                _complete_open_packet(
                    ledger,
                    disposition_packet_id,
                    _milestone_pm_accept_body(ledger, disposition_packet_id),
                )
                flowguard_packet = _open_packets(ledger, "flowguard_check")[0]
                _complete_open_packet(
                    ledger,
                    flowguard_packet,
                    _flowguard_pass_body("FlowGuard requires a revised milestone plan."),
                )
                pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]

                _complete_open_packet(
                    ledger,
                    pm_acceptance_packet,
                    _pm_flowguard_acceptance_body(
                        ledger,
                        decision=decision,
                    ),
                )

                old_gate = list(ledger["pm_decision_gates"].values())[-1]
                replacement_packet_id = old_gate["replacement_pm_disposition_packet_id"]
                self.assertEqual(old_gate["status"], "renewal_rewrite_required")
                self.assertEqual(ledger["active_route_version"], 1)
                self.assertEqual(ledger["route_nodes"][node_id]["status"], "awaiting_pm_disposition")
                self.assertNotEqual(
                    ledger["route_nodes"][node_id]["status"],
                    "superseded",
                )
                self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
                self.assertEqual(
                    ledger["packets"][replacement_packet_id]["envelope"]["packet_kind"],
                    "pm_disposition",
                )
                self.assertEqual(ledger["packets"][replacement_packet_id]["status"], "open")

    def test_milestone_flowguard_absorption_stop_is_durable_and_never_dispatches_worker(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )
        flowguard_packet = _open_packets(ledger, "flowguard_check")[0]
        _complete_open_packet(
            ledger,
            flowguard_packet,
            _flowguard_pass_body("FlowGuard found a substantive user decision."),
        )
        pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]

        _complete_open_packet(
            ledger,
            pm_acceptance_packet,
            _pm_flowguard_acceptance_body(
                ledger,
                decision="stop_for_user",
            ),
        )

        self.assertEqual(runtime.terminal_lifecycle_status(ledger), "stopped_by_user")
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "stopped")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_lifecycle")

    def test_pending_milestone_gate_recovers_missing_current_flowguard_owner_before_worker(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )
        missing_packet_id = _open_packets(ledger, "flowguard_check")[0]
        del ledger["packets"][missing_packet_id]

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_flowguard_packet")
        self.assertEqual(action.subject_id, disposition_packet_id)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(ledger["execution_frontier"]["status"], "awaiting_milestone_plan_renewal")

    def test_numbered_text_plan_is_rejected_without_route_fallback(self) -> None:
        ledger, _pm_packet = _recursive_ledger()
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": "1. Plan architecture\n2. Implement behavior\n3. Validate evidence",
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "strict route plan schema"):
            runtime.materialize_route_from_planning_result(ledger, "planning-result")

        self.assertEqual(ledger["route_nodes"], {})

    def test_route_nodes_compatibility_field_is_rejected(self) -> None:
        ledger, _pm_packet = _recursive_ledger()
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": json.dumps(
                {
                    "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                    "route_nodes": [{"node_id": "node-001", "title": "Implementation"}],
                }
            ),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "use nodes, not route_nodes"):
            runtime.materialize_route_from_planning_result(ledger, "planning-result")

        self.assertEqual(ledger["route_nodes"], {})

    def test_structured_route_plan_preserves_deliverable_metadata(self) -> None:
        ledger, _pm_packet = _recursive_ledger()
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implementation",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Implementation accepted."],
                        "required_outputs": [{"path": "data/product.json", "kind": "json"}],
                        "deliverable_checks": [
                            {"check_id": "product-json", "kind": "json_parse", "path": "data/product.json"}
                        ],
                        "validation_checks": [{"check_id": "pytest", "kind": "command_record"}],
                    }
                ]
            ),
        }

        node_ids = runtime.materialize_route_from_planning_result(ledger, "planning-result")

        self.assertEqual(node_ids, ["node-001"])
        node = ledger["route_nodes"]["node-001"]
        self.assertEqual(node["route_plan_schema_version"], runtime.ROUTE_PLAN_SCHEMA_VERSION)
        self.assertEqual(node["required_outputs"][0]["path"], "data/product.json")
        self.assertEqual(node["deliverable_checks"][0]["check_id"], "product-json")
        self.assertEqual(node["validation_checks"][0]["check_id"], "pytest")

    def test_all_nodes_accept_before_terminal_completion(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        accepted = []
        while ledger["execution_frontier"].get("active_node_id"):
            accepted.append(_complete_active_node(ledger))

        self.assertEqual(accepted, ["node-001", "node-002", "node-003"])
        self.assertEqual({node["status"] for node in ledger["route_nodes"].values()}, {"accepted"})
        self.assertEqual(ledger["final_route_wide_gate_ledger"]["unresolved_count"], 0)
        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")

    def test_missing_node_blocks_final_route_wide_closure(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        closure = runtime.attempt_final_closure(ledger, "validation-missing-node")

        self.assertEqual(closure["decision"], "blocked")
        self.assertIn("incomplete_node:node-001", closure["blockers"])
        self.assertIn("final_route_wide_gate_ledger_unresolved", closure["blockers"])

    def test_changed_milestone_plan_preserves_prefix_and_rewrites_unfinished_suffix(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        changed_plan = {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": [
                {
                    "node_id": "node-002-replanned",
                    "title": "Implement the audited runtime behavior",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["The audited runtime behavior is accepted with current evidence."],
                },
                {
                    "node_id": "node-003-replanned",
                    "title": "Validate the renewed route through final closure",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["The renewed route reaches validated final closure."],
                },
            ],
        }
        mutated = _complete_active_node(ledger, remaining_route_plan=changed_plan)

        self.assertEqual(mutated, "node-001")
        self.assertEqual(ledger["route_nodes"]["node-001"]["status"], "accepted")
        self.assertEqual(ledger["route_nodes"]["node-001"]["route_membership_versions"], [1, 2])
        self.assertEqual(ledger["route_nodes"]["node-002"]["status"], "superseded")
        self.assertEqual(ledger["route_nodes"]["node-003"]["status"], "superseded")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-002-replanned")
        self.assertEqual(ledger["active_route_version"], 2)
        self.assertTrue(ledger["route_mutations"][-1]["requires_replay_or_rebinding"])
        self.assertTrue(ledger["route_mutations"][-1]["completed_prefix_evidence_preserved"])
        prefix_packet_id = ledger["route_nodes"]["node-001"]["packet_ids"][0]
        self.assertIn(
            prefix_packet_id,
            {
                packet["packet_id"]
                for packet in runtime._accepted_result_packets_for_active_route(ledger)
            },
        )
        self.assertIn(
            prefix_packet_id,
            {
                row["id"]
                for row in runtime._backward_chain(ledger)
                if row["kind"] == "packet"
            },
        )

    def test_changed_milestone_plan_closes_active_leases_for_superseded_suffix(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        suffix_packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Speculative unfinished suffix work",
            "SEALED_SUFFIX_PACKET",
            route_node_id="node-002",
            route_scope="node",
        )
        ledger["route_nodes"]["node-002"]["packet_ids"].append(suffix_packet_id)
        suffix_lease_id = host.lease_responsibility(
            ledger,
            "worker",
            host_kind="fake",
            agent_id="worker-speculative-suffix",
            packet_id=suffix_packet_id,
            scope="recursive-route-test",
        )
        runtime.assign_packet(ledger, suffix_packet_id, suffix_lease_id)
        runtime.ack_lease(ledger, suffix_lease_id, suffix_packet_id)

        _complete_active_node(
            ledger,
            remaining_route_plan={
                "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                "nodes": [
                    {
                        "node_id": "node-002-replanned",
                        "title": "Execute the replanned suffix",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["The replanned suffix is accepted."],
                    }
                ],
            },
        )

        self.assertEqual(
            ledger["packets"][suffix_packet_id]["status"],
            "quarantined_after_route_mutation",
        )
        self.assertEqual(ledger["leases"][suffix_lease_id]["status"], "closed")
        self.assertEqual(
            ledger["leases"][suffix_lease_id]["close_reason"],
            "milestone_plan_renewal_superseded_unfinished_suffix",
        )

    def test_milestone_preflight_rejects_unbound_challenge_evidence_ids(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )
        flowguard_packet = _open_packets(ledger, "flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_pass_body("FlowGuard accepted the renewal."))
        pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]
        _complete_open_packet(ledger, pm_acceptance_packet, _pm_flowguard_acceptance_body(ledger))
        review_packet = _open_packets(ledger, "review")[0]
        with mock.patch.object(
            runtime,
            "_auto_close_packet_after_system_validation",
            return_value="",
        ):
            _complete_open_packet(
                ledger,
                review_packet,
                _review_pass_body("Reviewer accepted the renewal."),
            )
        gate = list(ledger["pm_decision_gates"].values())[-1]
        gate["flowguard_order_id"] = "flowguard-does-not-exist"

        with self.assertRaisesRegex(
            runtime.BlackBoxRuntimeError,
            "evidence is not current and exactly bound",
        ):
            runtime._preflight_milestone_plan_renewal_apply(ledger, gate)

        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(ledger["active_route_version"], 1)

    def test_failed_milestone_apply_does_not_leave_false_closed_system_closure(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        node_id, disposition_packet_id = _advance_active_node_to_pm_disposition(ledger)
        _complete_open_packet(
            ledger,
            disposition_packet_id,
            _milestone_pm_accept_body(ledger, disposition_packet_id),
        )
        flowguard_packet = _open_packets(ledger, "flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_pass_body("FlowGuard accepted the renewal."))
        pm_acceptance_packet = _open_packets(ledger, "pm_flowguard_acceptance")[0]
        _complete_open_packet(ledger, pm_acceptance_packet, _pm_flowguard_acceptance_body(ledger))
        review_packet = _open_packets(ledger, "review")[0]
        gate = list(ledger["pm_decision_gates"].values())[-1]
        gate_id = gate["gate_id"]
        gate["remaining_plan_fingerprint"] = "tampered-before-atomic-commit"

        with self.assertRaisesRegex(
            runtime.BlackBoxRuntimeError,
            "remaining-plan fingerprint changed",
        ):
            _complete_open_packet(
                ledger,
                review_packet,
                _review_pass_body("Reviewer accepted the renewal."),
            )

        live_gate = ledger["pm_decision_gates"][gate_id]
        self.assertEqual(live_gate["status"], "renewal_rewrite_required")
        self.assertTrue(live_gate.get("recovery_packet_id"))
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "awaiting_milestone_plan_renewal")
        self.assertFalse(
            [
                closure
                for closure in ledger["system_closures"].values()
                if closure.get("subject_packet_id") == pm_acceptance_packet
                and closure.get("status") == "closed"
            ]
        )

    def test_public_status_does_not_keep_consumed_route_mutation_as_current_blocker(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        _complete_active_node(
            ledger,
            remaining_route_plan={
                "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                "nodes": [
                    {
                        "node_id": "node-002-replanned",
                        "title": "Implement renewed behavior",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Renewed behavior is accepted."],
                    }
                ],
            },
        )
        while ledger["execution_frontier"].get("active_node_id"):
            _complete_active_node(ledger)

        projection = runtime.render_compact_console(ledger)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(projection["next_action"]["action_type"], "terminal_complete")
        self.assertNotIn("local_artifact", projection["blockers"])
        self.assertEqual(projection["blockers"], [])

    def test_public_status_projects_route_frontier_and_final_ledger_without_bodies(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        while ledger["execution_frontier"].get("active_node_id"):
            _complete_active_node(ledger)

        projection = runtime.render_console(ledger)

        self.assertFalse(projection["sealed_bodies_visible"])
        self.assertEqual(projection["execution_frontier"]["status"], "complete")
        self.assertEqual(projection["final_route_wide_gate_ledger"]["unresolved_count"], 0)
        self.assertEqual({node["status"] for node in projection["route_nodes"]}, {"accepted"})
        self.assertTrue(all(node["node_id"].startswith("node-") for node in projection["route_nodes"]))
        self.assertNotIn("SEALED_RESULT_BODY", json.dumps(projection, sort_keys=True))

    def test_final_ledger_uses_current_effective_packets(self) -> None:
        ledger = runtime.new_ledger("Build target", "Accept only current route work.")
        ledger["startup_intake"] = {"sealed": True}
        ledger["recursive_route_execution_required"] = True
        runtime.create_route(ledger, "Recursive route", ["implementation"])
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implementation",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Implementation accepted."],
                    }
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, "planning-result")
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Historical node packet",
            "SEALED_NODE_PACKET",
            route_node_id="node-001",
            route_scope="node",
        )
        ledger["route_nodes"]["node-001"]["packet_ids"].append(packet_id)
        ledger["route_nodes"]["node-001"]["status"] = "accepted"
        ledger["route_nodes"]["node-001"]["accepted_result_id"] = "result-current"
        ledger["execution_frontier"]["active_node_id"] = ""
        ledger["execution_frontier"]["status"] = "ready_for_final_closure"
        ledger["packets"][packet_id]["status"] = "result_blocked"
        ledger["packets"][packet_id]["active_blocker_id"] = "blocker-stale"
        ledger["active_blockers"]["blocker-stale"] = {
            "blocker_id": "blocker-stale",
            "status": "awaiting_recheck",
            "packet_id": packet_id,
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "route_node_id": "node-001",
            "blocker_class": "local_artifact",
        }

        final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
        projection = runtime.render_console(ledger)

        self.assertEqual(final_ledger["unresolved_count"], 0)
        self.assertEqual(projection["active_blockers"], [])
        self.assertEqual(projection["route_stage"], "route_wide_closure")

        ledger["route_nodes"]["node-001"]["status"] = "running"
        current_ledger = runtime.build_final_route_wide_gate_ledger(ledger)

        self.assertIn(f"packet_not_accepted:{packet_id}", current_ledger["unresolved"])

    def test_missing_route_deliverable_blocks_final_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = runtime.new_ledger("Build target", "Require concrete product output.")
            ledger["startup_intake"] = {"sealed": True}
            ledger["recursive_route_execution_required"] = True
            ledger["project_root"] = tmp
            runtime.create_route(ledger, "Recursive route", ["implementation"])
            ledger["results"]["planning-result"] = {
                "result_id": "planning-result",
                "body": _route_plan_body(
                    [
                        {
                            "node_id": "node-001",
                            "title": "Implementation",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
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

            self.assertEqual(closure["decision"], "blocked")
            self.assertIn("route_deliverable:node-001:product-json:failed", closure["blockers"])
            self.assertEqual(ledger["final_requirement_evidence_matrix"]["status"], "blocked")

    def test_blocked_final_closure_routes_to_repair_packet_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = runtime.new_ledger("Build target", "Require concrete product output.")
            ledger["startup_intake"] = {"sealed": True}
            ledger["recursive_route_execution_required"] = True
            ledger["project_root"] = tmp
            runtime.create_route(ledger, "Recursive route", ["implementation"])
            ledger["results"]["planning-result"] = {
                "result_id": "planning-result",
                "body": _route_plan_body(
                    [
                        {
                            "node_id": "node-001",
                            "title": "Implementation",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
                            "acceptance_criteria": ["Implementation accepted."],
                        }
                    ]
                ),
            }
            runtime.materialize_route_from_planning_result(ledger, "planning-result")
            _mark_node_ready_for_final_closure(ledger, "node-001")
            ledger["latest_validation_evidence_id"] = "runtime-validation"
            blocked_packet = runtime.issue_task_packet(
                ledger,
                "pm",
                "Repair stale closure blocker",
                "SEALED_REPAIR_PACKET",
                route_scope="repair",
            )
            ledger["packets"][blocked_packet]["status"] = "review_blocked"

            self.assertEqual(runtime.router_next_action(ledger).action_type, "repair_packet")

            boundary = runtime.run_until_wait(ledger, max_steps=3)

            self.assertEqual(boundary["boundary_class"], "recovery")
            self.assertEqual(boundary["next_action"]["action_type"], "repair_packet")
            self.assertEqual(boundary["next_action"]["subject_id"], blocked_packet)
            self.assertIsNone(ledger["closure"])

    def test_existing_route_deliverable_allows_final_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            product_path = Path(tmp) / "data" / "product.json"
            product_path.parent.mkdir(parents=True)
            product_path.write_text('{"ok": true}', encoding="utf-8")
            ledger = runtime.new_ledger("Build target", "Require concrete product output.")
            ledger["startup_intake"] = {"sealed": True}
            ledger["recursive_route_execution_required"] = True
            ledger["project_root"] = tmp
            runtime.create_route(ledger, "Recursive route", ["implementation"])
            ledger["results"]["planning-result"] = {
                "result_id": "planning-result",
                "body": _route_plan_body(
                    [
                        {
                            "node_id": "node-001",
                            "title": "Implementation",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
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

            final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)

            self.assertNotIn("route_deliverable:node-001:product-json:failed", final_ledger["unresolved"])
            self.assertEqual(final_ledger["deliverable_checks"][0]["status"], "passed")

if __name__ == "__main__":
    unittest.main()
