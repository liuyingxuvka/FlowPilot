from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

from tests.flowpilot_current_authority_test_helpers import normalized_current_authority_references


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

runtime = importlib.import_module("flowpilot_core_runtime.runtime")


def _base_ledger() -> dict[str, object]:
    ledger = runtime.new_ledger("Goal", "Acceptance")
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "startup_answers": {runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True},
    }
    ledger["contract_frozen"] = True
    ledger["contract_hash"] = runtime.hash_text("Goal\nAcceptance")
    ledger["high_standard_control_flow_required"] = True
    ledger["recursive_route_execution_required"] = True
    ledger["active_route_version"] = 1
    ledger["routes"]["1"] = {
        "route_id": "route-v1",
        "route_version": 1,
        "summary": "Recursive route",
        "status": "active",
        "node_order": [],
        "created_at": runtime.now_iso(),
        "source_generation": ledger["source_generation"],
        "contract_hash": ledger["contract_hash"],
    }
    ledger["execution_frontier"] = {
        "active_route_version": 1,
        "active_node_id": "",
        "completed_nodes": [],
        "status": "node_execution",
        "pending_route_mutation": None,
        "blocked_reason": "",
        "updated_at": runtime.now_iso(),
    }
    _accept_preplanning_gates(ledger)
    return ledger


def _accept_preplanning_gates(ledger: dict[str, object]) -> None:
    ledger["high_standard_contract"] = {
        "status": "accepted",
        "source_result_id": "result-high-standard-contract",
        "requirements": [],
        "acceptance_item_registry": {"schema_version": runtime.ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION, "items": []},
    }
    ledger["preplanning_discovery"] = {"status": "accepted", "source_result_id": "result-discovery"}
    ledger["skill_standard_contract"] = {
        "status": "accepted",
        "source_result_id": "result-skill-standard",
        "selected_skills": [],
        "obligations": [],
    }


def _add_node(
    ledger: dict[str, object],
    node_id: str,
    *,
    status: str = "pending",
    node_kind: str = "leaf",
    parent_node_id: str = "",
    child_node_ids: list[str] | None = None,
    accepted_result_id: str = "",
) -> dict[str, object]:
    node = {
        "node_id": node_id,
        "route_version": ledger["active_route_version"],
        "title": node_id,
        "node_kind": node_kind,
        "parent_node_id": parent_node_id,
        "child_node_ids": list(child_node_ids or []),
        "responsibility": "worker",
        "modeled_target": "development_process",
        "acceptance_criteria": [f"{node_id} accepted"],
        "required_outputs": [],
        "deliverable_checks": [],
        "validation_checks": [],
        "status": status,
        "repair_generation": 0,
        "packet_ids": [],
        "accepted_result_id": accepted_result_id,
        "accepted_repair_generation": 0 if accepted_result_id else None,
        "flowguard_order_ids": [],
        "review_ids": [],
        "validation_evidence_ids": [],
        "closure_id": "",
        "pm_disposition_id": "",
        "node_acceptance_plan_id": "",
        "node_context_package_id": "",
        "node_context_package_repair_generation": None,
        "parent_backward_replay_id": "",
        "parent_backward_waiver": "",
        "high_standard_requirement_ids": [],
        "acceptance_item_ids": [],
        "skill_standard_obligation_ids": [],
        "supplemental_repair_contract_ids": [],
        "supplemental_repair_item_ids": [],
        "superseded_by": "",
        "stale_evidence": [],
        "created_at": runtime.now_iso(),
    }
    ledger["route_nodes"][node_id] = node
    route = ledger["routes"][str(ledger["active_route_version"])]
    route["node_order"] = [*route.get("node_order", []), node_id]
    return node


def _accept_entry_gate(ledger: dict[str, object], node_id: str) -> None:
    node = ledger["route_nodes"][node_id]
    generation = int(node.get("repair_generation", 0))
    plan_id = f"plan-{node_id}"
    context_id = f"context-{node_id}"
    source_packet_id = f"{context_id}-packet"
    source_result_id = f"{context_id}-result"
    ledger["node_acceptance_plans"][plan_id] = {
        "plan_id": plan_id,
        "status": "accepted",
        "node_id": node_id,
        "repair_generation": generation,
        "created_at": runtime.now_iso(),
    }
    ledger["node_context_packages"][context_id] = {
        "schema_version": "black_box_flowpilot.node_context_package.v2",
        "context_package_id": context_id,
        "status": "accepted",
        "node_id": node_id,
        "route_version": ledger.get("active_route_version"),
        "repair_generation": generation,
        "purpose": "Current node context.",
        "acceptance_criteria": list(node.get("acceptance_criteria") or []),
        "relevant_references": normalized_current_authority_references(
            ledger,
            node_id=node_id,
            source_packet_id=source_packet_id,
            source_result_id=source_result_id,
            include_repair=(
                str(node.get("node_kind") or "") == "repair"
                or generation > 0
            ),
            fixture_id=f"parent-entry-{node_id}",
        ),
        "known_risks": [],
        "acceptance_item_projection": [],
        "source_packet_id": source_packet_id,
        "source_result_id": source_result_id,
        "source_generation": int(ledger.get("source_generation", 0) or 0),
        "created_at": runtime.now_iso(),
    }
    node["node_acceptance_plan_id"] = plan_id
    node["node_context_package_id"] = context_id
    node["node_context_package_repair_generation"] = generation


def _accept_pm_disposition(ledger: dict[str, object], node_id: str) -> None:
    disposition_id = f"pm-disposition-{node_id}"
    ledger["pm_dispositions"][disposition_id] = {
        "disposition_id": disposition_id,
        "node_id": node_id,
        "result_id": str(ledger["route_nodes"][node_id].get("accepted_result_id") or ""),
        "decision": "accept",
        "reason": "Current node accepted.",
        "acceptance_item_disposition": [],
        "route_version": ledger["active_route_version"],
        "created_at": runtime.now_iso(),
    }
    ledger["route_nodes"][node_id]["pm_disposition_id"] = disposition_id


def _accept_parent_replay(ledger: dict[str, object], node_id: str) -> None:
    replay_id = f"parent-replay-{node_id}"
    ledger["parent_backward_replays"][replay_id] = {
        "replay_id": replay_id,
        "status": "accepted",
        "node_id": node_id,
        "source_review_packet_id": f"packet-parent-review-{node_id}",
        "source_review_result_id": f"result-parent-review-{node_id}",
        "reviewed_by_role": "human_like_reviewer",
        "passed": True,
        "blockers": [],
        "created_at": runtime.now_iso(),
    }
    ledger["route_nodes"][node_id]["parent_backward_replay_id"] = replay_id


def _add_current_worker_quality_evidence(ledger: dict[str, object], node_id: str) -> None:
    node = ledger["route_nodes"][node_id]
    packet_id = f"packet-node-{node_id}"
    result_id = str(node.get("accepted_result_id") or f"result-node-{node_id}")
    node["accepted_result_id"] = result_id
    ledger["packets"][packet_id] = {
        "packet_id": packet_id,
        "status": "accepted",
        "accepted_result_id": result_id,
        "result_ids": [result_id],
        "created_at": runtime.now_iso(),
        "envelope": {
            "packet_kind": "task",
            "route_scope": "node",
            "route_node_id": node_id,
            "route_version": ledger["active_route_version"],
            "responsibility": "worker",
            "required_flowguard_target": "development_process",
        },
    }
    ledger["results"][result_id] = {
        "result_id": result_id,
        "packet_id": packet_id,
        "status": "accepted",
        "accepted": True,
        "body": json.dumps({"decision": "pass"}),
        "envelope": {"body_hash": runtime.hash_text(json.dumps({"decision": "pass"}))},
        "created_at": runtime.now_iso(),
    }
    flowguard_id = f"flowguard-{node_id}"
    review_id = f"review-{node_id}"
    validation_id = f"validation-{node_id}"
    ledger["flowguard_work_orders"][flowguard_id] = {
        "order_id": flowguard_id,
        "status": "complete",
        "decision": "pass",
        "subject_id": packet_id,
        "proof_result_id": f"result-flowguard-{node_id}",
        "proof_artifact": f"evidence/{flowguard_id}.json",
        "source_generation": ledger["source_generation"],
        "progress_only": False,
        "skipped_checks": [],
        "proof_stale": False,
    }
    ledger["results"][f"result-review-{node_id}"] = {
        "result_id": f"result-review-{node_id}",
        "packet_id": f"packet-review-{node_id}",
        "status": "accepted",
        "body": json.dumps({"passed": True}),
        "envelope": {"body_hash": runtime.hash_text(json.dumps({"passed": True}))},
        "created_at": runtime.now_iso(),
    }
    ledger["reviews"][review_id] = {
        "review_id": review_id,
        "result_id": f"result-review-{node_id}",
        "subject_packet_id": packet_id,
        "decision": "accept",
        "blockers": [],
        "checks_evidence": True,
        "independent_from_producer": True,
        "direct_evidence_ids": [result_id],
    }
    ledger["validation_evidence"][validation_id] = {
        "evidence_id": validation_id,
        "status": "passed",
        "subject_packet_id": packet_id,
        "source_generation": ledger["source_generation"],
        "blockers": [],
    }
    node["flowguard_order_ids"] = [flowguard_id]
    node["review_ids"] = [review_id]
    node["validation_evidence_ids"] = [validation_id]


def _ready_for_final_closure(ledger: dict[str, object]) -> None:
    ledger["execution_frontier"] = {
        "active_route_version": ledger["active_route_version"],
        "active_node_id": "",
        "completed_nodes": list(ledger["route_nodes"].keys()),
        "status": "ready_for_final_closure",
        "pending_route_mutation": None,
        "blocked_reason": "",
        "updated_at": runtime.now_iso(),
    }


class FlowPilotParentEntryReturnPathTests(unittest.TestCase):
    def test_nonworker_scope_entry_opens_parent_plan_before_child_descent(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", parent_node_id="parent")
        ledger["execution_frontier"]["active_node_id"] = "parent"

        opened = runtime._enter_nonworker_route_scope(ledger, "parent", reason="test_parent_entry")

        self.assertTrue(opened)
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "parent")
        self.assertEqual(ledger["execution_frontier"]["status"], "node_execution")
        parent_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"].get("route_scope") == "node_acceptance_plan"
            and packet["envelope"].get("route_node_id") == "parent"
        ]
        child_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"].get("route_scope") == "node_acceptance_plan"
            and packet["envelope"].get("route_node_id") == "child"
        ]
        self.assertEqual(len(parent_packets), 1)
        self.assertEqual(child_packets, [])

    def test_frontier_enters_next_parent_plan_before_child_after_prior_node_acceptance(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "done", status="accepted", accepted_result_id="result-done")
        _add_node(ledger, "parent", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", parent_node_id="parent")

        runtime._advance_frontier_after_node_acceptance(ledger, "done")

        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "parent")
        self.assertEqual(ledger["execution_frontier"]["status"], "node_execution")
        self.assertTrue(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("route_scope") == "node_acceptance_plan"
                and packet["envelope"].get("route_node_id") == "parent"
            ]
        )
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("route_scope") == "node_acceptance_plan"
                and packet["envelope"].get("route_node_id") == "child"
            ]
        )

    def test_frontier_reclaims_awaiting_children_parent_missing_entry_before_child(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "done", status="accepted", accepted_result_id="result-done")
        _add_node(ledger, "parent", status="awaiting_children", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", parent_node_id="parent")

        runtime._advance_frontier_after_node_acceptance(ledger, "done")

        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "parent")
        self.assertEqual(ledger["execution_frontier"]["status"], "node_execution")
        self.assertTrue(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("route_scope") == "node_acceptance_plan"
                and packet["envelope"].get("route_node_id") == "parent"
            ]
        )
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("route_scope") == "node_acceptance_plan"
                and packet["envelope"].get("route_node_id") == "child"
            ]
        )

    def test_child_plan_cannot_satisfy_parent_entry_gate(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="awaiting_parent_backward_replay", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
        _accept_entry_gate(ledger, "child")

        with self.assertRaisesRegex(
            runtime.BlackBoxRuntimeError,
            "control_plane_hard_gate_escape:missing_node_acceptance_plan:parent",
        ):
            runtime.ensure_parent_backward_replay_packet(ledger, "parent")

    def test_parent_replay_closure_rejects_missing_parent_entry_gate(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="awaiting_parent_backward_replay", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")

        with self.assertRaisesRegex(
            runtime.BlackBoxRuntimeError,
            "control_plane_hard_gate_escape:missing_node_acceptance_plan:parent",
        ):
            runtime._record_parent_backward_replay_closure(ledger, "parent", {})

    def test_pm_disposition_rejects_missing_parent_entry_gate(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="accepted", node_kind="module", accepted_result_id="result-parent")
        ledger["results"]["result-parent"] = {
            "result_id": "result-parent",
            "packet_id": "packet-parent",
            "status": "accepted",
            "body": json.dumps({"decision": "pass"}),
            "created_at": runtime.now_iso(),
        }

        with self.assertRaisesRegex(
            runtime.BlackBoxRuntimeError,
            "control_plane_hard_gate_escape:missing_node_acceptance_plan:parent",
        ):
            runtime.record_pm_disposition(ledger, "parent", "result-parent")

    def test_final_hard_gate_escape_returns_to_parent_entry_gate_before_quality_review(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="accepted", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
        _accept_entry_gate(ledger, "child")
        _accept_pm_disposition(ledger, "parent")
        _accept_pm_disposition(ledger, "child")
        _add_current_worker_quality_evidence(ledger, "child")
        _accept_parent_replay(ledger, "parent")
        _ready_for_final_closure(ledger)

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_node_acceptance_plan_packet")
        self.assertEqual(action.subject_id, "parent")
        self.assertEqual(action.responsibility, "pm")
        self.assertEqual(action.reason, "control_plane_hard_gate_escape:missing_node_acceptance_plan:parent")

    def test_final_hard_gate_escape_returns_parent_replay_gate_after_entries_clean(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="accepted", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
        for node_id in ("parent", "child"):
            _accept_entry_gate(ledger, node_id)
            _accept_pm_disposition(ledger, node_id)
        _add_current_worker_quality_evidence(ledger, "child")
        _ready_for_final_closure(ledger)

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_parent_backward_replay_packet")
        self.assertEqual(action.subject_id, "parent")
        self.assertEqual(action.responsibility, "reviewer")
        self.assertEqual(action.reason, "control_plane_hard_gate_escape:missing_parent_backward_replay:parent")

    def test_final_hard_gate_escape_matrix_returns_each_runtime_gate_to_owner(self) -> None:
        cases = [
            (
                "missing_node_entry",
                lambda ledger: None,
                ("issue_node_acceptance_plan_packet", "parent", "pm", "missing_node_acceptance_plan"),
            ),
            (
                "missing_parent_replay",
                lambda ledger: (_accept_entry_gate(ledger, "parent"), _accept_entry_gate(ledger, "child")),
                ("issue_parent_backward_replay_packet", "parent", "reviewer", "missing_parent_backward_replay"),
            ),
            (
                "missing_pm_disposition",
                lambda ledger: (
                    _accept_entry_gate(ledger, "parent"),
                    _accept_entry_gate(ledger, "child"),
                    _accept_parent_replay(ledger, "parent"),
                    _accept_pm_disposition(ledger, "child"),
                ),
                ("issue_pm_disposition_packet", "parent", "pm", "missing_pm_disposition"),
            ),
            (
                "stale_node_evidence",
                lambda ledger: (
                    _accept_entry_gate(ledger, "parent"),
                    _accept_entry_gate(ledger, "child"),
                    _accept_parent_replay(ledger, "parent"),
                    _accept_pm_disposition(ledger, "parent"),
                    _accept_pm_disposition(ledger, "child"),
                    ledger["route_nodes"]["parent"].__setitem__("stale_evidence", ["stale-parent"]),
                ),
                ("issue_node_acceptance_plan_packet", "parent", "pm", "stale_current_evidence"),
            ),
            (
                "current_packet_unresolved",
                lambda ledger: (
                    _accept_entry_gate(ledger, "parent"),
                    _accept_entry_gate(ledger, "child"),
                    _accept_parent_replay(ledger, "parent"),
                    _accept_pm_disposition(ledger, "parent"),
                    _accept_pm_disposition(ledger, "child"),
                    ledger["packets"].__setitem__(
                        "packet-final-live",
                        {
                            "packet_id": "packet-final-live",
                            "status": "result_blocked",
                            "accepted_result_id": "",
                            "result_ids": [],
                            "created_at": runtime.now_iso(),
                            "envelope": {
                                "packet_kind": "task",
                                "route_scope": "final_runtime_gate",
                                "route_version": ledger["active_route_version"],
                                "responsibility": "pm",
                            },
                        },
                    ),
                ),
                ("repair_packet", "", "pm", "active_packet_unresolved"),
            ),
        ]
        for case_name, mutate, expected in cases:
            with self.subTest(case_name=case_name):
                ledger = _base_ledger()
                _add_node(ledger, "parent", status="accepted", node_kind="module", child_node_ids=["child"])
                _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
                _add_current_worker_quality_evidence(ledger, "child")
                mutate(ledger)
                _ready_for_final_closure(ledger)

                action = runtime.router_next_action(ledger)

                expected_action, expected_subject, expected_role, expected_reason = expected
                self.assertEqual(action.action_type, expected_action)
                if expected_subject:
                    self.assertEqual(action.subject_id, expected_subject)
                self.assertEqual(action.responsibility, expected_role)
                self.assertIn(f"control_plane_hard_gate_escape:{expected_reason}:", action.reason)

    def test_active_repair_chain_owns_blocked_packet_until_recheck_completes(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="accepted", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
        for node_id in ("parent", "child"):
            _accept_entry_gate(ledger, node_id)
            _accept_pm_disposition(ledger, node_id)
        _accept_parent_replay(ledger, "parent")
        _add_current_worker_quality_evidence(ledger, "child")
        ledger["packets"]["packet-blocked-review"] = {
            "packet_id": "packet-blocked-review",
            "status": "review_blocked",
            "accepted_result_id": "",
            "result_ids": ["result-blocked-review"],
            "active_blocker_id": "blocker-active",
            "created_at": runtime.now_iso(),
            "envelope": {
                "packet_kind": "review",
                "route_scope": "terminal_backward_replay",
                "route_version": ledger["active_route_version"],
                "responsibility": "reviewer",
                "subject_id": "validation-current",
            },
        }
        ledger["packets"]["packet-pm-repair"] = {
            "packet_id": "packet-pm-repair",
            "status": "accepted",
            "accepted_result_id": "result-pm-repair",
            "result_ids": ["result-pm-repair"],
            "repair_blocker_id": "blocker-active",
            "created_at": runtime.now_iso(),
            "envelope": {
                "packet_kind": "pm_repair_decision",
                "route_scope": "pm_repair_decision",
                "route_version": ledger["active_route_version"],
                "responsibility": "pm",
                "subject_id": "blocker-active",
                "repair_blocker_id": "blocker-active",
            },
        }
        ledger["packets"]["packet-repair-flowguard"] = {
            "packet_id": "packet-repair-flowguard",
            "status": "open",
            "accepted_result_id": "",
            "result_ids": [],
            "repair_blocker_id": "blocker-active",
            "created_at": runtime.now_iso(),
            "envelope": {
                "packet_kind": "flowguard_check",
                "route_scope": "pm_repair_decision",
                "route_version": ledger["active_route_version"],
                "responsibility": "flowguard_operator",
                "subject_id": "packet-pm-repair",
                "repair_blocker_id": "blocker-active",
            },
        }
        ledger["results"]["result-pm-repair"] = {
            "result_id": "result-pm-repair",
            "packet_id": "packet-pm-repair",
            "status": "accepted",
            "accepted": True,
            "body": json.dumps({"decision": "repair_current_scope"}),
            "envelope": {
                "body_hash": runtime.hash_text(
                    json.dumps({"decision": "repair_current_scope"})
                )
            },
            "created_at": runtime.now_iso(),
        }
        ledger["active_blockers"]["blocker-active"] = {
            "blocker_id": "blocker-active",
            "status": "awaiting_pm_decision_gate",
            "packet_id": "packet-blocked-review",
            "repair_target_packet_id": "packet-blocked-review",
            "pm_repair_packet_id": "packet-pm-repair",
            "subject_packet_id": "validation-current",
        }
        _ready_for_final_closure(ledger)

        action = runtime.router_next_action(ledger)

        self.assertTrue(runtime._packet_is_noncurrent_for_routing(ledger, ledger["packets"]["packet-blocked-review"]))
        self.assertEqual(action.action_type, "dispatch_current_role")
        self.assertEqual(action.subject_id, "packet-repair-flowguard")
        self.assertEqual(action.responsibility, "flowguard_operator")

    def test_final_quality_review_reachable_only_after_runtime_hard_gates_clean(self) -> None:
        ledger = _base_ledger()
        _add_node(ledger, "parent", status="accepted", node_kind="module", child_node_ids=["child"])
        _add_node(ledger, "child", status="accepted", parent_node_id="parent", accepted_result_id="result-child")
        for node_id in ("parent", "child"):
            _accept_entry_gate(ledger, node_id)
            _accept_pm_disposition(ledger, node_id)
        _accept_parent_replay(ledger, "parent")
        _add_current_worker_quality_evidence(ledger, "child")
        _ready_for_final_closure(ledger)

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_terminal_backward_replay_packet")
        self.assertEqual(action.responsibility, "reviewer")
        self.assertEqual(action.reason, "terminal backward replay is required before final closure")


if __name__ == "__main__":
    unittest.main()
