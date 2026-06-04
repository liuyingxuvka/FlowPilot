from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

runtime = importlib.import_module("flowpilot_core_runtime.runtime")
host = importlib.import_module("flowpilot_core_runtime.host")


def _ledger() -> dict:
    ledger = runtime.new_ledger("Build target", "Finish only with high-standard evidence.")
    ledger["startup_intake"] = {"sealed": True}
    ledger["recursive_route_execution_required"] = True
    ledger["high_standard_control_flow_required"] = True
    runtime.create_route(ledger, "High-standard route", ["planning", "implementation", "validation"])
    runtime.ensure_preplanning_gate_packet(ledger)
    return ledger


def _open_packets(ledger: dict, *, kind: str | None = None, scope: str | None = None) -> list[str]:
    rows: list[str] = []
    for packet_id, packet in ledger["packets"].items():
        envelope = packet["envelope"]
        if packet["status"] != "open":
            continue
        if kind and envelope.get("packet_kind", "task") != kind:
            continue
        if scope and envelope.get("route_scope") != scope:
            continue
        rows.append(packet_id)
    return rows


def _complete_open_packet(ledger: dict, packet_id: str, body: str = "SEALED_RESULT_BODY") -> str:
    packet = ledger["packets"][packet_id]
    responsibility = packet["envelope"]["responsibility"]
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        host_kind="fake",
        agent_id=f"{responsibility}-{packet_id}",
        packet_id=packet_id,
        scope="high-standard-test",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    return host.submit_host_result(ledger, lease_id, packet_id, body)


def _complete_task_chain(ledger: dict, packet_id: str, body: str = "SEALED_RESULT_BODY") -> None:
    _complete_open_packet(ledger, packet_id, body)
    for kind in ("flowguard_check", "review"):
        _complete_open_packet(ledger, _open_packets(ledger, kind=kind)[0], f"SEALED_RESULT_BODY: {kind}")


def _complete_preplanning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="high_standard_contract")[0],
        json.dumps(
            {
                "requirements": [
                    {
                        "requirement_id": "hsr-001",
                        "classification": "hard_current",
                        "summary": "Complete the requested outcome.",
                    }
                ]
            }
        ),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="discovery")[0],
        json.dumps({"material_sources": ["startup"], "local_skill_inventory": ["flowguard-development-process-flow"]}),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="skill_standard")[0],
        json.dumps(
            {
                "obligations": [
                    {
                        "obligation_id": "skill-std-001",
                        "skill": "flowguard-development-process-flow",
                        "classification": "required",
                    }
                ]
            }
        ),
    )


def _route_plan_body(nodes: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": nodes
            or [
                {
                    "node_id": "node-001",
                    "title": "Plan architecture",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Architecture plan is accepted with high-standard evidence."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
                {
                    "node_id": "node-002",
                    "title": "Implement behavior",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Behavior implementation is accepted with high-standard evidence."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
                {
                    "node_id": "node-003",
                    "title": "Validate evidence",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["Validation evidence is accepted with high-standard evidence."],
                    "high_standard_requirement_ids": ["hsr-001"],
                    "skill_standard_obligation_ids": ["skill-std-001"],
                },
            ],
        }
    )


def _complete_planning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="planning")[0],
        _route_plan_body(),
    )


def _node_context_body(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    node = ledger["route_nodes"][node_id]
    return json.dumps(
        {
            "repair_policy": "same_node_repair_default",
            "node_context_package": {
                "node_id": node_id,
                "purpose": f"Execute and verify {node['title']}",
                "acceptance_criteria": list(node.get("acceptance_criteria") or []),
                "relevant_references": [
                    {"kind": "route_node", "id": node_id},
                    {"kind": "node_acceptance_plan_packet", "id": _open_packets(ledger, scope="node_acceptance_plan")[0]},
                ],
                "evidence_targets": ["current-run result evidence", "fresh validation output"],
                "inspection_targets": ["changed files or product surface", "test and FlowGuard evidence"],
                "known_risks": ["thin evidence", "wrong FlowGuard target", "stale repair-generation evidence"],
                "flowguard_targets": [str(node.get("modeled_target") or "development_process")],
                "reviewer_starting_points": ["subject result", "post-result FlowGuard report", "node acceptance criteria"],
            },
        }
    )


def _complete_node_acceptance_plan(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="node_acceptance_plan")[0],
        _node_context_body(ledger),
    )


def _complete_prework_flowguard(ledger: dict) -> str:
    packet_id = _open_packets(ledger, scope="node_prework_flowguard")[0]
    _complete_open_packet(
        ledger,
        packet_id,
        json.dumps({"decision": "pass", "selected_routes": ["flowguard-development-process-flow"]}),
    )
    return packet_id


def _complete_active_node_packet_loop(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    if _open_packets(ledger, scope="node_prework_flowguard"):
        _complete_prework_flowguard(ledger)
    _complete_task_chain(ledger, _open_packets(ledger, scope="node")[0], f"SEALED_RESULT_BODY: {node_id}")
    return node_id


class FlowPilotHighStandardControlFlowTests(unittest.TestCase):
    def test_reviewer_pass_auto_closes_without_closure_flowguard_operator_packet(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, json.dumps({"requirements": []}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))

        self.assertFalse(_open_packets(ledger, kind="validation"))
        self.assertFalse(_open_packets(ledger, kind="closure"))
        evidence = list(ledger["validation_evidence"].values())
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["status"], "passed")
        self.assertEqual(evidence[0]["owner_role"], "system")
        self.assertEqual(evidence[0]["evidence_kind"], "system_review_validation")
        self.assertEqual(evidence[0]["subject_packet_id"], packet_id)
        self.assertTrue(evidence[0]["flowguard_order_ids"])
        closures = list(ledger["system_closures"].values())
        self.assertEqual(len(closures), 1)
        self.assertEqual(closures[0]["subject_packet_id"], packet_id)
        self.assertEqual(closures[0]["validation_evidence_id"], evidence[0]["evidence_id"])
        self.assertEqual((ledger.get("high_standard_contract") or {}).get("status"), "accepted")

    def test_system_validation_failure_routes_to_pm_repair(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, json.dumps({"requirements": []}))
        runtime._ensure_review_packet_for_task_result(ledger, packet_id)

        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))

        self.assertFalse(_open_packets(ledger, kind="closure"))
        self.assertFalse(ledger["system_closures"])
        failed = [row for row in ledger["validation_evidence"].values() if row["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertIn("missing_matching_flowguard_report", failed[0]["blockers"])
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["gate_kind"], "system_validation")
        self.assertEqual(active[0]["required_recheck_role"], "system")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_preplanning_gates_run_before_pm_planning(self) -> None:
        ledger = _ledger()

        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="high_standard_contract")[0]]["envelope"]["route_scope"], "high_standard_contract")
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "before high-standard preplanning gates"):
            runtime.materialize_route_from_planning_result(ledger, "missing-result")

        _complete_preplanning(ledger)

        self.assertTrue(runtime.preplanning_gates_accepted(ledger))
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="planning")[0]]["envelope"]["route_scope"], "planning")

    def test_node_task_requires_accepted_node_acceptance_plan(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        self.assertEqual(_open_packets(ledger, scope="node_acceptance_plan"), [ledger["packets"][_open_packets(ledger, scope="node_acceptance_plan")[0]]["packet_id"]])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "requires accepted node acceptance plan"):
            runtime.ensure_next_node_task_packet(ledger)

        _complete_node_acceptance_plan(ledger)

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "requires accepted pre-work FlowGuard"):
            runtime.ensure_next_node_task_packet(ledger)
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node_prework_flowguard")[0]]["envelope"]["route_node_id"], node_id)
        _complete_prework_flowguard(ledger)

        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], node_id)
        self.assertTrue(ledger["route_nodes"][node_id]["node_acceptance_plan_id"])

    def test_node_task_requires_prework_flowguard_gate(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        context_id = ledger["route_nodes"][node_id]["node_context_package_id"]
        self.assertTrue(context_id)
        self.assertTrue(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node"))
        prework_packet = _open_packets(ledger, scope="node_prework_flowguard")[0]
        body = json.loads(ledger["packets"][prework_packet]["body"])

        self.assertEqual(body["route_node_id"], node_id)
        self.assertEqual(body["node_context_package_id"], context_id)
        self.assertEqual(ledger["packets"][prework_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertTrue(body["minimum_starting_context_not_boundary"])
        self.assertTrue(body["route_selection_policy"]["multiple_routes_allowed"])
        self.assertFalse(body["route_selection_policy"]["pm_skip_decision_allowed"])
        self.assertIn("selected_routes", body["route_selection_policy"]["required_output_fields"])
        self.assertTrue(body["pm_visibility_policy"]["pm_can_read_model_artifacts"])
        self.assertIn(f"/evidence/flowguard/{prework_packet}", body["pm_visibility_policy"]["run_local_evidence_root"])

        _complete_prework_flowguard(ledger)

        node = ledger["route_nodes"][node_id]
        self.assertTrue(runtime._node_prework_flowguard_accepted(ledger, node_id))
        self.assertEqual(node["prework_flowguard_packet_id"], prework_packet)
        self.assertEqual(node["prework_flowguard_repair_generation"], node["repair_generation"])
        self.assertEqual(_open_packets(ledger, scope="node"), [_open_packets(ledger, scope="node")[0]])

    def test_node_acceptance_plan_requires_node_context_package(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]
        result_id = _complete_open_packet(ledger, packet_id, json.dumps({"repair_policy": "same_node_repair_default"}))

        node_id = ledger["execution_frontier"]["active_node_id"]
        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertIn("top-level node_context_package", ledger["results"][result_id]["quarantine_reason"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertFalse(_open_packets(ledger, scope="node"))

    def test_node_context_package_follows_flowguard_worker_and_reviewer_packets(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        context_id = ledger["route_nodes"][node_id]["node_context_package_id"]
        prework_packet = _open_packets(ledger, scope="node_prework_flowguard")[0]
        self.assertEqual(ledger["packets"][prework_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(json.loads(ledger["packets"][prework_packet]["body"])["node_context_package_id"], context_id)

        _complete_prework_flowguard(ledger)
        worker_packet = _open_packets(ledger, scope="node")[0]
        worker_body = json.loads(ledger["packets"][worker_packet]["body"])
        self.assertEqual(ledger["packets"][worker_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(worker_body["node_context_package_id"], context_id)
        self.assertIn("minimum baseline", worker_body["instruction"])

        _complete_open_packet(ledger, worker_packet, f"SEALED_RESULT_BODY: completed {node_id}")
        post_flowguard = _open_packets(ledger, kind="flowguard_check")[0]
        post_body = json.loads(ledger["packets"][post_flowguard]["body"])
        self.assertEqual(ledger["packets"][post_flowguard]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(post_body["node_context_package_id"], context_id)

        _complete_open_packet(ledger, post_flowguard, json.dumps({"decision": "pass"}))
        review_packet = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertEqual(ledger["packets"][review_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(review_body["node_context_package_id"], context_id)
        self.assertIn("as the review boundary", review_body["instruction"])

    def test_prework_flowguard_block_returns_to_pm_and_requires_fresh_prework(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        first_prework = _open_packets(ledger, scope="node_prework_flowguard")[0]

        _complete_open_packet(
            ledger,
            first_prework,
            json.dumps(
                {
                    "decision": "block",
                    "blocker_class": "node_design_risk",
                    "recommended_resolution": "PM must tighten node acceptance before worker execution.",
                }
            ),
        )

        self.assertEqual(ledger["packets"][first_prework]["status"], "flowguard_blocked")
        self.assertFalse(_open_packets(ledger, scope="node"))
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        self.assertEqual(blocker["required_recheck_role"], "flowguard_operator")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            json.dumps({"decision": "same_node_repair", "reason": "repair node design from FlowGuard report"}),
        )

        self.assertEqual(ledger["route_nodes"][node_id]["repair_generation"], 1)
        self.assertFalse(runtime._node_prework_flowguard_accepted(ledger, node_id))
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(_open_packets(ledger, scope="node"))

        _complete_node_acceptance_plan(ledger)
        fresh_prework = _open_packets(ledger, scope="node_prework_flowguard")[0]
        self.assertNotEqual(fresh_prework, first_prework)
        _complete_prework_flowguard(ledger)

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "cleared")
        self.assertEqual(ledger["packets"][first_prework]["status"], "superseded_after_repair")
        self.assertTrue(runtime._node_prework_flowguard_accepted(ledger, node_id))
        self.assertTrue(_open_packets(ledger, scope="node"))

    def test_pm_repair_reuses_same_node_and_repair_generation(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        _complete_open_packet(ledger, _open_packets(ledger, kind="pm_disposition")[0], json.dumps({"decision": "repair", "reason": "needs deeper evidence"}))

        self.assertEqual(ledger["active_route_version"], 1)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], node_id)
        self.assertEqual(ledger["route_nodes"][node_id]["repair_generation"], 1)
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(_open_packets(ledger, scope="node"))
        _complete_node_acceptance_plan(ledger)
        _complete_prework_flowguard(ledger)
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], node_id)

    def test_reviewer_block_routes_to_pm_repair_and_requires_recheck(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "requirements": [
                        {
                            "requirement_id": "hsr-001",
                            "classification": "hard_current",
                            "summary": "Initial contract draft.",
                        }
                    ]
                }
            ),
        )
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))

        review_packet = _open_packets(ledger, kind="review")[0]
        _complete_open_packet(
            ledger,
            review_packet,
            json.dumps(
                {
                    "schema_version": "black_box_flowpilot.packet_outcome.v1",
                    "passed": False,
                    "blocker_class": "local_artifact",
                    "recommended_resolution": "PM must reissue a sharper high-standard contract.",
                }
            ),
        )

        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertFalse(_open_packets(ledger, kind="validation"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")
        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]

        _complete_open_packet(ledger, pm_repair_packet, json.dumps({"decision": "sender_reissue", "reason": "local fix"}))
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == active[0]["blocker_id"] and packet["status"] == "open"
        ]
        self.assertEqual(len(repair_packets), 1)

        _complete_open_packet(ledger, repair_packets[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))

        self.assertEqual(ledger["active_blockers"][active[0]["blocker_id"]]["status"], "cleared")
        self.assertFalse(_open_packets(ledger, kind="validation"))
        self.assertFalse(_open_packets(ledger, kind="closure"))
        self.assertTrue(ledger["system_closures"])

    def test_validator_and_closure_flowguard_operator_are_not_runtime_roles(self) -> None:
        ledger = _ledger()
        for responsibility in ("validator", "closure_flowguard_operator"):
            with self.subTest(responsibility=responsibility):
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown responsibility"):
                    runtime.issue_task_packet(
                        ledger,
                        responsibility,
                        "Forbidden old role",
                        "SEALED_OLD_ROLE_BODY",
                    )

    def test_validation_and_closure_packet_kinds_are_rejected(self) -> None:
        ledger = _ledger()
        for packet_kind in ("validation", "closure"):
            with self.subTest(packet_kind=packet_kind):
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown packet kind"):
                    runtime.issue_task_packet(
                        ledger,
                        "worker",
                        "Forbidden old packet kind",
                        "SEALED_OLD_PACKET_KIND_BODY",
                        packet_kind=packet_kind,
                    )

    def test_pm_sender_reissue_repair_remains_direct(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps({"status": "blocked", "blocker_class": "local_artifact", "recommended_resolution": "sender fix"}),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            json.dumps({"decision": "sender_reissue", "reason": "plain repair"}),
        )

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_recheck")
        self.assertFalse(ledger["pm_decision_gates"])
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == blocker["blocker_id"] and packet["status"] == "open"
        ]
        self.assertEqual(len(repair_packets), 1)

    def test_pm_mutate_route_repair_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        _complete_prework_flowguard(ledger)
        node_packet = _open_packets(ledger, scope="node")[0]
        _complete_open_packet(
            ledger,
            node_packet,
            json.dumps({"status": "blocked", "blocker_class": "local_artifact", "recommended_resolution": "route change"}),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            json.dumps({"decision": "mutate_route", "reason": "current node plan is wrong"}),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_pm_decision_gate")
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))
        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_recheck")
        self.assertFalse(_open_packets(ledger, kind="closure"))

    def test_pm_mutate_route_disposition_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            json.dumps({"decision": "mutate_route", "reason": "node needs a different route"}),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["gate_kind"], "pm_disposition")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertFalse(_open_packets(ledger, kind="closure"))

    def test_workerlocked_result_routes_pm_repair_without_flowguard_pass(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "schema_version": "black_box_flowpilot.packet_outcome.v1",
                    "status": "blocked",
                    "blocker_class": "needs_user",
                    "recommended_resolution": "PM must clarify the high-standard contract before evidence work.",
                }
            ),
        )

        self.assertEqual(ledger["packets"][packet_id]["status"], "result_blocked")
        self.assertFalse(_open_packets(ledger, kind="flowguard_check"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["owner_role"], "pm")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_final_matrix_blocks_missing_node_acceptance_plan(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        planning_result = "planning-result"
        ledger["results"][planning_result] = {
            "result_id": planning_result,
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implement behavior",
                        "acceptance_criteria": ["Behavior implementation accepted."],
                        "high_standard_requirement_ids": ["hsr-001"],
                        "skill_standard_obligation_ids": ["skill-std-001"],
                    }
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, planning_result)
        node_id = ledger["execution_frontier"]["active_node_id"]
        ledger["route_nodes"][node_id]["status"] = "accepted"
        ledger["route_nodes"][node_id]["pm_disposition_id"] = "pm-disposition"
        ledger["route_nodes"][node_id]["accepted_result_id"] = "node-result"
        ledger["route_nodes"][node_id]["prework_flowguard_order_id"] = "prework-flowguard-1"
        ledger["route_nodes"][node_id]["prework_flowguard_repair_generation"] = 0
        ledger["flowguard_work_orders"]["prework-flowguard-1"] = {
            "order_id": "prework-flowguard-1",
            "status": "complete",
            "decision": "pass",
        }
        ledger["route_nodes"][node_id]["flowguard_order_ids"] = ["flowguard-1"]
        ledger["route_nodes"][node_id]["review_ids"] = ["review-1"]
        ledger["route_nodes"][node_id]["validation_evidence_ids"] = ["validation-1"]

        closure = runtime.attempt_final_closure(ledger, "validation-missing-plan")

        self.assertEqual(closure["decision"], "blocked")
        self.assertIn("node_acceptance_plan", json.dumps(closure["blockers"]))
        self.assertEqual(ledger["final_requirement_evidence_matrix"]["status"], "blocked")

    def test_parent_node_requires_backward_replay_before_pm_disposition(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        planning_result = "planning-result"
        ledger["results"][planning_result] = {
            "result_id": planning_result,
            "body": _route_plan_body(
                [
                    {
                        "node_id": "parent-001",
                        "title": "Parent feature",
                        "node_kind": "parent",
                        "child_node_ids": ["node-001"],
                        "acceptance_criteria": ["Parent composes child evidence"],
                        "high_standard_requirement_ids": ["hsr-001"],
                        "skill_standard_obligation_ids": ["skill-std-001"],
                    }
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, planning_result)
        runtime.ensure_node_acceptance_plan_packet(ledger, "parent-001")
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)

        self.assertEqual(node_id, "parent-001")
        self.assertEqual(_open_packets(ledger, scope="parent_backward_replay"), [_open_packets(ledger, scope="parent_backward_replay")[0]])
        self.assertFalse(_open_packets(ledger, kind="pm_disposition"))

        _complete_task_chain(ledger, _open_packets(ledger, scope="parent_backward_replay")[0], json.dumps({"decision": "pass"}))

        self.assertTrue(ledger["route_nodes"][node_id]["parent_backward_replay_id"])
        self.assertTrue(_open_packets(ledger, kind="pm_disposition"))


if __name__ == "__main__":
    unittest.main()
