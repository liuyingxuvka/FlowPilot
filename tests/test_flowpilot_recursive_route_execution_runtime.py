from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


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
    payload: dict[str, object] = {"decision": "pass", "pm_visible_summary": [summary]}
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
    return json.dumps(payload)


def _complete_open_packet(ledger: dict, packet_id: str, body: str | None = None) -> str:
    packet = ledger["packets"][packet_id]
    responsibility = packet["envelope"]["responsibility"]
    if body is None:
        body = _pass_body(f"{responsibility} completed {packet_id}.")
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
    return host.submit_host_result(ledger, lease_id, packet_id, body)


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


def _complete_active_node(ledger: dict, disposition: str = "accept") -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    if _open_packets(ledger, "flowguard_check", scope="node_prework_flowguard"):
        prework_packet = _open_packets(ledger, "flowguard_check", scope="node_prework_flowguard")[0]
        _complete_open_packet(
            ledger,
            prework_packet,
            _flowguard_pass_body(
                f"Prework FlowGuard accepted {node_id}.",
                selected_routes=["flowguard-development-process-flow"],
            ),
        )
    task_packet = _open_packets(ledger, "task", scope="node")[0]
    _complete_open_packet(ledger, task_packet, _pass_body(f"Worker completed {node_id}.", node_id=node_id))
    for kind in ("flowguard_check", "review"):
        packet_id = _open_packets(ledger, kind)[0]
        _complete_open_packet(ledger, packet_id, _role_pass_body(kind, f"{kind} accepted {node_id}."))
    pm_packet = _open_packets(ledger, "pm_disposition")[0]
    _complete_open_packet(ledger, pm_packet, _pm_disposition_body(disposition, f"{disposition} {node_id}"))
    if disposition == "redesign_route":
        for kind in ("flowguard_check", "review"):
            packet_id = _open_packets(ledger, kind)[0]
            _complete_open_packet(
                ledger,
                packet_id,
                _role_pass_body(kind, f"PM disposition gate {kind} accepted {node_id}."),
            )
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


class FlowPilotRecursiveRouteExecutionRuntimeTests(unittest.TestCase):
    def test_pm_planning_chain_materializes_nodes_instead_of_terminal_completion(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        self.assertNotEqual((ledger.get("closure") or {}).get("decision"), "complete")
        self.assertEqual(len(ledger["route_nodes"]), 3)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001")
        action = runtime.router_next_action(ledger).to_json()
        self.assertEqual(action["action_type"], "dispatch_current_role")
        self.assertEqual(action["subject_id"], _open_packets(ledger, "flowguard_check", scope="node_prework_flowguard")[0])

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
            accepted.append(_complete_active_node(ledger, "accept"))

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

    def test_pm_mutation_supersedes_node_and_rewrites_frontier(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        mutated = _complete_active_node(ledger, "redesign_route")

        self.assertEqual(mutated, "node-001")
        self.assertEqual(ledger["route_nodes"]["node-001"]["status"], "superseded")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001-repair-v2")
        self.assertEqual(ledger["active_route_version"], 2)
        self.assertTrue(ledger["route_mutations"][-1]["requires_replay_or_rebinding"])

    def test_public_status_does_not_keep_consumed_route_mutation_as_current_blocker(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        _complete_active_node(ledger, "redesign_route")
        while ledger["execution_frontier"].get("active_node_id"):
            _complete_active_node(ledger, "accept")

        projection = runtime.render_compact_console(ledger)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(projection["next_action"]["action_type"], "terminal_complete")
        self.assertNotIn("local_artifact", projection["blockers"])
        self.assertEqual(projection["blockers"], [])

    def test_public_status_projects_route_frontier_and_final_ledger_without_bodies(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)
        while ledger["execution_frontier"].get("active_node_id"):
            _complete_active_node(ledger, "accept")

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
                [{"node_id": "node-001", "title": "Implementation", "acceptance_criteria": ["Implementation accepted."]}]
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
        ledger["route_nodes"]["node-001"]["prework_flowguard_order_id"] = "prework-flowguard-1"
        ledger["route_nodes"]["node-001"]["prework_flowguard_repair_generation"] = 0
        ledger["flowguard_work_orders"]["prework-flowguard-1"] = {
            "order_id": "prework-flowguard-1",
            "status": "complete",
            "decision": "pass",
        }
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

            self.assertEqual(runtime.router_next_action(ledger).action_type, "close_project")

            boundary = runtime.run_until_wait(ledger, max_steps=3)

            self.assertEqual(boundary["folded_applied_actions"][0]["action_type"], "close_project")
            self.assertEqual(boundary["boundary_class"], "recovery")
            self.assertEqual(boundary["next_action"]["action_type"], "repair_packet")
            self.assertEqual(boundary["next_action"]["subject_id"], blocked_packet)
            self.assertEqual(ledger["closure"]["decision"], "blocked")

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
