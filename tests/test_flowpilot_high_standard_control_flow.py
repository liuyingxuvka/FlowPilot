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

runtime = importlib.import_module("ai_project_runtime.runtime")
host = importlib.import_module("ai_project_runtime.host")


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
    for kind in ("flowguard_check", "review", "closure"):
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


def _complete_planning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="planning")[0],
        "1. Plan architecture\n2. Implement behavior\n3. Validate evidence",
    )


def _complete_node_acceptance_plan(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="node_acceptance_plan")[0],
        json.dumps({"repair_policy": "same_node_repair_default"}),
    )


def _complete_active_node_packet_loop(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    _complete_task_chain(ledger, _open_packets(ledger, scope="node")[0], f"SEALED_RESULT_BODY: {node_id}")
    return node_id


class FlowPilotHighStandardControlFlowTests(unittest.TestCase):
    def test_reviewer_pass_records_system_validation_without_validator_packet(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, json.dumps({"requirements": []}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], json.dumps({"passed": True}))

        self.assertFalse(_open_packets(ledger, kind="validation"))
        evidence = list(ledger["validation_evidence"].values())
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["status"], "passed")
        self.assertEqual(evidence[0]["owner_role"], "system")
        self.assertEqual(evidence[0]["evidence_kind"], "system_review_validation")
        self.assertEqual(evidence[0]["subject_packet_id"], packet_id)
        self.assertTrue(evidence[0]["flowguard_order_ids"])
        self.assertTrue(_open_packets(ledger, kind="closure"))

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

        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], node_id)
        self.assertTrue(ledger["route_nodes"][node_id]["node_acceptance_plan_id"])

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
        self.assertTrue(_open_packets(ledger, kind="closure"))

    def test_legacy_validator_fail_records_failed_evidence_and_routes_pm_repair(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, json.dumps({"requirements": []}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))

        runtime._ensure_validation_packet_for_task(ledger, packet_id)
        validation_packet = _open_packets(ledger, kind="validation")[0]
        _complete_open_packet(
            ledger,
            validation_packet,
            json.dumps(
                {
                    "schema_version": "black_box_flowpilot.packet_outcome.v1",
                    "status": "failed",
                    "blocker_class": "validation_failure",
                    "recommended_resolution": "Rerun validation after repaired evidence.",
                }
            ),
        )

        self.assertEqual(ledger["packets"][packet_id]["status"], "validation_blocked")
        self.assertFalse(_open_packets(ledger, kind="closure"))
        failed = [row for row in ledger["validation_evidence"].values() if row["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "validator")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_pm_rerun_validation_requires_fresh_validator_pass(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, json.dumps({"requirements": []}))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], json.dumps({"decision": "pass"}))

        runtime._ensure_validation_packet_for_task(ledger, packet_id)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="validation")[0],
            json.dumps({"status": "failed", "blocker_class": "validation_failure"}),
        )

        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        self.assertEqual(ledger["packets"][packet_id]["status"], "validation_blocked")
        self.assertFalse(_open_packets(ledger, kind="closure"))

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            json.dumps({"decision": "rerun_validation", "reason": "validator must recheck repaired evidence"}),
        )

        validation_rechecks = [
            recheck_packet_id
            for recheck_packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == blocker["blocker_id"]
            and packet["status"] == "open"
            and packet["envelope"].get("packet_kind") == "validation"
        ]
        self.assertEqual(len(validation_rechecks), 1)
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_recheck")
        self.assertFalse(_open_packets(ledger, kind="closure"))

        _complete_open_packet(ledger, validation_rechecks[0], json.dumps({"passed": True}))

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "cleared")
        self.assertEqual([row["status"] for row in ledger["validation_evidence"].values()], ["failed", "passed"])
        self.assertTrue(_open_packets(ledger, kind="closure"))

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
        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertEqual(gate["status"], "awaiting_closure")

        _complete_open_packet(ledger, _open_packets(ledger, kind="closure")[0], json.dumps({"passed": True}))

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_recheck")

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
        self.assertEqual(ledger["active_route_version"], old_route_version)
        _complete_open_packet(ledger, _open_packets(ledger, kind="closure")[0], json.dumps({"passed": True}))

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")

    def test_worker_blocked_result_routes_pm_repair_without_flowguard_pass(self) -> None:
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
            "body": "1. Implement behavior",
        }
        runtime.materialize_route_from_planning_result(ledger, planning_result)
        node_id = ledger["execution_frontier"]["active_node_id"]
        ledger["route_nodes"][node_id]["status"] = "accepted"
        ledger["route_nodes"][node_id]["pm_disposition_id"] = "pm-disposition"
        ledger["route_nodes"][node_id]["accepted_result_id"] = "node-result"
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
        ledger["results"][planning_result] = {"result_id": planning_result, "body": "parent plan"}
        runtime.materialize_route_from_planning_result(
            ledger,
            planning_result,
            nodes=[
                {
                    "node_id": "parent-001",
                    "title": "Parent feature",
                    "node_kind": "parent",
                    "child_node_ids": ["node-001"],
                    "acceptance_criteria": ["Parent composes child evidence"],
                }
            ],
        )
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
