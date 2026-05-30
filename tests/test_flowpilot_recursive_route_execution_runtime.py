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


def _recursive_ledger() -> tuple[dict, str]:
    ledger = runtime.new_ledger("Build target", "Accept only after every route node is complete.")
    ledger["startup_intake"] = {"sealed": True}
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


def _open_packets(ledger: dict, kind: str | None = None) -> list[str]:
    rows: list[str] = []
    for packet_id, packet in ledger["packets"].items():
        if packet["status"] != "open":
            continue
        if kind and packet["envelope"].get("packet_kind", "task") != kind:
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
        scope="recursive-route-test",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    return host.submit_host_result(ledger, lease_id, packet_id, body)


def _complete_foundation_planning_chain(ledger: dict, pm_packet: str) -> None:
    _complete_open_packet(
        ledger,
        pm_packet,
        "\n".join(
            [
                "1. Plan architecture and contracts",
                "2. Implement UI and runtime behavior",
                "3. Validate evidence and closure",
            ]
        ),
    )
    for kind in ("flowguard_check", "review"):
        packet_id = _open_packets(ledger, kind)[0]
        _complete_open_packet(ledger, packet_id, f"SEALED_RESULT_BODY: {kind}")


def _complete_active_node(ledger: dict, disposition: str = "accept") -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    task_packet = _open_packets(ledger, "task")[0]
    _complete_open_packet(ledger, task_packet, f"SEALED_RESULT_BODY: completed {node_id}")
    for kind in ("flowguard_check", "review"):
        packet_id = _open_packets(ledger, kind)[0]
        _complete_open_packet(ledger, packet_id, f"SEALED_RESULT_BODY: {kind} for {node_id}")
    pm_packet = _open_packets(ledger, "pm_disposition")[0]
    _complete_open_packet(ledger, pm_packet, json.dumps({"decision": disposition, "reason": f"{disposition} {node_id}"}))
    if disposition == "mutate_route":
        for kind in ("flowguard_check", "review"):
            packet_id = _open_packets(ledger, kind)[0]
            _complete_open_packet(ledger, packet_id, f"SEALED_RESULT_BODY: PM disposition gate {kind} for {node_id}")
    return node_id


class FlowPilotRecursiveRouteExecutionRuntimeTests(unittest.TestCase):
    def test_pm_planning_chain_materializes_nodes_instead_of_terminal_completion(self) -> None:
        ledger, pm_packet = _recursive_ledger()
        _complete_foundation_planning_chain(ledger, pm_packet)

        self.assertNotEqual((ledger.get("closure") or {}).get("decision"), "complete")
        self.assertEqual(len(ledger["route_nodes"]), 3)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001")
        action = runtime.router_next_action(ledger).to_json()
        self.assertEqual(action["action_type"], "lease_agent")
        self.assertEqual(action["subject_id"], _open_packets(ledger, "task")[0])

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

        mutated = _complete_active_node(ledger, "mutate_route")

        self.assertEqual(mutated, "node-001")
        self.assertEqual(ledger["route_nodes"]["node-001"]["status"], "superseded")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001-repair-v2")
        self.assertEqual(ledger["active_route_version"], 2)
        self.assertTrue(ledger["route_mutations"][-1]["requires_replay_or_rebinding"])

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


if __name__ == "__main__":
    unittest.main()
