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


def _pass_body(summary: str = "Current packet evidence passed.", **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
    }
    payload.update(fields)
    return json.dumps(payload)


def _flowguard_pass_body(summary: str = "FlowGuard accepted the current packet evidence.", **fields: object) -> str:
    fields.setdefault("selected_routes", ["flowguard-development-process-flow"])
    return _pass_body(summary, **fields)


def _review_pass_body(summary: str = "Reviewer accepted the current packet evidence.", **fields: object) -> str:
    return _pass_body(summary, **fields)


def _block_body(summary: str, *, blocker_class: str, recommended_resolution: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "block",
        "blocking": True,
        "blocker_class": blocker_class,
        "recommended_resolution": recommended_resolution,
        "pm_visible_summary": [summary],
    }
    payload.update(fields)
    return json.dumps(payload)


def _high_standard_contract_body() -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Complete the requested outcome.",
                    "closure_blocking": True,
                }
            ],
        }
    )


def _discovery_body() -> str:
    return json.dumps(
        {
            "decision": "pass",
            "material_sources": ["startup"],
            "material_sufficiency": "sufficient_for_route_planning",
            "local_skill_inventory": ["flowguard-development-process-flow"],
            "candidate_only_skill_policy": True,
        }
    )


def _skill_standard_body() -> str:
    return json.dumps(
        {
            "decision": "pass",
            "obligations": [
                {
                    "obligation_id": "skill-std-001",
                    "skill": "flowguard-development-process-flow",
                    "classification": "required",
                    "role_use": "flowguard_operator",
                    "use_context": "node_validation",
                    "evidence_required": "current-run FlowGuard work order",
                    "closure_blocking": True,
                }
            ],
        }
    )


def _ledger() -> dict:
    ledger = runtime.new_ledger("Build target", "Finish only with high-standard evidence.")
    ledger["startup_intake"] = {
        "sealed": True,
        "startup_answers": {
            runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
        },
    }
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


def _complete_open_packet(ledger: dict, packet_id: str, body: str | None = None) -> str:
    if body is None:
        body = _pass_body()
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
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    return host.submit_host_result(ledger, lease_id, packet_id, body)


def _complete_task_chain(ledger: dict, packet_id: str | None = None, body: str | None = None) -> None:
    if packet_id is None:
        raise AssertionError("packet_id is required for the current FlowPilot task chain")
    _complete_open_packet(ledger, packet_id, body)
    flowguard_packets = _open_packets(ledger, kind="flowguard_check")
    if flowguard_packets:
        _complete_open_packet(
            ledger,
            flowguard_packets[0],
            _flowguard_pass_body("FlowGuard checked the current packet evidence."),
        )
    review_packets = _open_packets(ledger, kind="review")
    if review_packets:
        _complete_open_packet(
            ledger,
            review_packets[0],
            _review_pass_body("Reviewer accepted the current packet evidence."),
        )


def _complete_preplanning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="high_standard_contract")[0],
        _high_standard_contract_body(),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="discovery")[0],
        _discovery_body(),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="skill_standard")[0],
        _skill_standard_body(),
    )


def _route_plan_body(nodes: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "decision": "pass",
            "pm_visible_summary": ["PM accepted the route plan."],
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


def _route_plan_obj(nodes: list[dict]) -> dict:
    return json.loads(_route_plan_body(nodes))


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
            "decision": "pass",
            "pm_visible_summary": ["PM accepted the node context package."],
            "repair_policy": "repair_scope_replacement_default",
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
        _flowguard_pass_body("Pre-work FlowGuard accepted the current node design."),
    )
    return packet_id


def _complete_active_node_packet_loop(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    if _open_packets(ledger, scope="node_prework_flowguard"):
        _complete_prework_flowguard(ledger)
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="node")[0],
        _pass_body("Worker completed the current node task.", node_id=node_id),
    )
    return node_id


class FlowPilotHighStandardControlFlowTests(unittest.TestCase):
    def test_reviewer_pass_auto_closes_without_closure_flowguard_operator_packet(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

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
        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())
        runtime._ensure_review_packet_for_task_result(ledger, packet_id)

        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

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

    def test_high_standard_contract_accepts_requirements_without_decision(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())

        self.assertEqual(ledger["packets"][packet_id]["status"], "result_submitted")
        result = ledger["results"][ledger["packets"][packet_id]["result_ids"][-1]]
        self.assertNotIn("decision", json.loads(result["body"]))
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

    def test_high_standard_contract_rejects_hidden_decision_wrapper(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            _pass_body(
                "PM accepted the high-standard contract.",
                requirements=[
                    {
                        "requirement_id": "hsr-001",
                        "classification": "hard_current",
                        "summary": "Complete the requested outcome.",
                    }
                ],
            ),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "task.high_standard_contract")
        self.assertIn("decision", result["forbidden_fields_seen"])
        self.assertIn("pm_visible_summary", result["forbidden_fields_seen"])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements"])
        self.assertIn("decision", reissue_body["forbidden_fields_seen"])

    def test_high_standard_contract_reissue_names_missing_requirements(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"overall_contract": "complete the work"}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["missing_required_fields"], ["requirements"])
        self.assertEqual(result["forbidden_fields_seen"], ["overall_contract"])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements"])
        self.assertEqual(reissue_body["missing_required_fields"], ["requirements"])
        self.assertEqual(reissue_body["forbidden_fields_seen"], ["overall_contract"])

    def test_high_standard_contract_requires_closure_blocking_field(self) -> None:
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
                            "summary": "Complete the requested outcome.",
                        }
                    ]
                }
            ),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertIn("requires boolean closure_blocking", result["quarantine_reason"])

    def test_discovery_reissue_names_missing_required_fields(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        packet_id = _open_packets(ledger, scope="discovery")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"decision": "pass", "material_sources": ["startup"]}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("material_sufficiency", result["quarantine_reason"])
        reissue_id = _open_packets(ledger, scope="discovery")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(
            reissue_body["required_result_body_fields"],
            [
                "decision",
                "material_sources",
                "material_sufficiency",
                "local_skill_inventory",
                "candidate_only_skill_policy",
            ],
        )

    def test_skill_standard_rejects_default_and_selected_skills_paths(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        _complete_task_chain(ledger, _open_packets(ledger, scope="discovery")[0], _discovery_body())
        packet_id = _open_packets(ledger, scope="skill_standard")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"decision": "pass"}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["missing_required_fields"], ["obligations"])
        reissue_id = _open_packets(ledger, scope="skill_standard")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["decision", "obligations"])
        self.assertEqual(reissue_body["missing_required_fields"], ["obligations"])

        _complete_open_packet(
            ledger,
            reissue_id,
            json.dumps(
                {
                    "decision": "pass",
                    "selected_skills": [
                        {
                            "skill": "flowguard-development-process-flow",
                            "classification": "required",
                        }
                    ],
                }
            ),
        )

        second_packet = ledger["packets"][reissue_id]
        self.assertEqual(second_packet["status"], "superseded_after_repair")
        second_result = ledger["results"][second_packet["superseded_by_result_id"]]
        self.assertEqual(second_result["missing_required_fields"], ["obligations"])
        self.assertEqual(second_result["forbidden_fields_seen"], ["selected_skills"])

    def test_skill_standard_reissue_names_missing_obligation_child_fields(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        _complete_task_chain(ledger, _open_packets(ledger, scope="discovery")[0], _discovery_body())
        packet_id = _open_packets(ledger, scope="skill_standard")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "obligations": [
                        {
                            "obligation_id": "skill-std-001",
                            "classification": "required",
                            "role_use": "flowguard_operator",
                            "use_context": "node_validation",
                            "evidence_required": "current-run FlowGuard work order",
                            "closure_blocking": True,
                        }
                    ],
                }
            ),
        )

        packet = ledger["packets"][packet_id]
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["missing_required_fields"], ["obligations[1].skill"])
        reissue_id = _open_packets(ledger, scope="skill_standard")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["missing_required_fields"], ["obligations[1].skill"])
        self.assertEqual(reissue_body["contract_family_id"], "task.skill_standard")

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
        result_id = _complete_open_packet(
            ledger,
            packet_id,
            _pass_body(
                "PM submitted a mechanically complete node plan without the required node context.",
                repair_policy="repair_scope_replacement_default",
            ),
        )

        node_id = ledger["execution_frontier"]["active_node_id"]
        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["results"][result_id]["missing_required_fields"], ["node_context_package"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertFalse(_open_packets(ledger, scope="node"))

    def test_node_acceptance_plan_reviewer_block_keeps_staged_effect_pending(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]

        result_id = _complete_open_packet(ledger, packet_id, _node_context_body(ledger))
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["status"], "pending")
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body("FlowGuard accepted the node acceptance plan."))

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="review")[0],
            _block_body(
                "Reviewer rejected the real node acceptance plan.",
                blocker_class="local_artifact",
                recommended_resolution="Reviewer rejected the real node acceptance plan.",
                schema_version="black_box_flowpilot.packet_outcome.v1",
            ),
        )

        self.assertEqual(ledger["results"][result_id]["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertTrue(ledger["packets"][packet_id]["active_blocker_id"])
        self.assertFalse(ledger["node_acceptance_plans"])
        self.assertFalse(ledger["node_context_packages"])
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertFalse(_open_packets(ledger, scope="node"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

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

        _complete_open_packet(
            ledger,
            worker_packet,
            _pass_body("Worker completed the current node task.", node_id=node_id),
        )
        post_flowguard = _open_packets(ledger, kind="flowguard_check")[0]
        post_body = json.loads(ledger["packets"][post_flowguard]["body"])
        self.assertEqual(ledger["packets"][post_flowguard]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(post_body["node_context_package_id"], context_id)

        _complete_open_packet(
            ledger,
            post_flowguard,
            _flowguard_pass_body("Post-result FlowGuard accepted the worker result."),
        )
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
                    "pm_visible_summary": ["Pre-work FlowGuard blocked the node design."],
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
            json.dumps(
                {
                    "decision": "repair_current_scope",
                    "reason": "replace current node from FlowGuard report",
                    "pm_visible_summary": ["PM repaired the node after the pre-work FlowGuard block."],
                }
            ),
        )

        replacement_id = ledger["execution_frontier"]["active_node_id"]
        self.assertNotEqual(replacement_id, node_id)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertFalse(runtime._node_prework_flowguard_accepted(ledger, replacement_id))
        self.assertFalse(runtime._node_context_package_current(ledger, replacement_id))
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(_open_packets(ledger, scope="node"))

        _complete_node_acceptance_plan(ledger)
        fresh_prework = _open_packets(ledger, scope="node_prework_flowguard")[0]
        self.assertNotEqual(fresh_prework, first_prework)
        _complete_prework_flowguard(ledger)

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "cleared")
        self.assertEqual(ledger["packets"][first_prework]["status"], "quarantined_after_route_mutation")
        self.assertTrue(runtime._node_prework_flowguard_accepted(ledger, replacement_id))
        self.assertTrue(_open_packets(ledger, scope="node"))

    def test_pm_disposition_repair_current_scope_creates_replacement_node(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pass_body(
                "PM chose current-node repair.",
                decision="repair_current_scope",
                reason="needs deeper evidence",
            ),
        )

        self.assertEqual(ledger["active_route_version"], 2)
        replacement_id = ledger["execution_frontier"]["active_node_id"]
        self.assertNotEqual(replacement_id, node_id)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(_open_packets(ledger, scope="node"))
        _complete_node_acceptance_plan(ledger)
        _complete_prework_flowguard(ledger)
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], replacement_id)

    def test_pm_disposition_summary_is_not_reason_fallback(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        _complete_active_node_packet_loop(ledger)
        packet_id = _open_packets(ledger, kind="pm_disposition")[0]

        result_id = _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "accept",
                    "summary": "legacy PM disposition summary must not be accepted as reason",
                }
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["pm_dispositions"])
        self.assertEqual(ledger["results"][result_id]["missing_required_fields"], ["reason"])
        self.assertEqual(ledger["results"][result_id]["forbidden_fields_seen"], ["summary"])

        fresh_packet_id = runtime._ensure_pm_disposition_packet_for_node(
            ledger,
            ledger["execution_frontier"]["active_node_id"],
            ledger["packets"][packet_id]["envelope"]["subject_id"],
        )

        self.assertNotEqual(fresh_packet_id, packet_id)
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertEqual(ledger["packets"][fresh_packet_id]["envelope"]["packet_kind"], "pm_disposition")
        fresh_body = json.loads(ledger["packets"][fresh_packet_id]["body"])
        self.assertEqual(fresh_body["missing_required_fields"], ["reason"])
        self.assertEqual(fresh_body["forbidden_fields_seen"], ["summary"])

    def test_pm_repair_parent_scope_replaces_parent_and_descendants(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="planning")[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-parent",
                        "title": "Parent module",
                        "node_kind": "parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Parent module composes."],
                        "child_node_ids": ["node-child"],
                    },
                    {
                        "node_id": "node-child",
                        "title": "Child module",
                        "parent_node_id": "node-parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Child module works."],
                    },
                ]
            ),
        )
        blocker_id = "blocker-parent-scope"
        decision_id = "pm_repair_decision-parent-scope"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-parent-scope",
            "packet_id": "",
            "packet_kind": "task",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "target_result_id": "",
            "result_id": "",
            "owner_role": "worker",
            "required_recheck_role": "reviewer",
            "gate_kind": "task",
            "blocker_class": "composition",
            "recommended_resolution": "bubble to parent",
            "route_version": ledger["active_route_version"],
            "route_node_id": "node-child",
            "route_scope": "node",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": decision_id,
            "cleared_by_outcome_id": "",
        }
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_parent_scope",
            "reason": "Parent composition is invalid.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)

        replacement_id = ledger["execution_frontier"]["active_node_id"]
        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        self.assertEqual(ledger["route_nodes"]["node-parent"]["status"], "superseded")
        self.assertEqual(ledger["route_nodes"]["node-child"]["status"], "superseded")
        self.assertEqual(ledger["route_nodes"]["node-parent"]["superseded_by"], replacement_id)
        self.assertEqual(ledger["route_nodes"]["node-child"]["superseded_by"], replacement_id)
        self.assertEqual(ledger["route_nodes"][replacement_id]["child_node_ids"], [])
        self.assertEqual(ledger["packets"][fresh_packet_id]["status"], "open")
        self.assertEqual(ledger["packets"][fresh_packet_id]["repair_blocker_id"], blocker_id)
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_reviewer_block_routes_to_pm_repair_and_requires_recheck(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            _high_standard_contract_body(),
        )
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())

        review_packet = _open_packets(ledger, kind="review")[0]
        _complete_open_packet(
            ledger,
            review_packet,
            _block_body(
                "Reviewer rejected the current high-standard contract.",
                blocker_class="local_artifact",
                recommended_resolution="PM must reissue a sharper high-standard contract.",
                schema_version="black_box_flowpilot.packet_outcome.v1",
            ),
        )

        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertTrue(ledger["packets"][packet_id]["active_blocker_id"])
        self.assertFalse(_open_packets(ledger, kind="validation"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")
        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]

        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pass_body("PM chose local current-scope repair.", decision="repair_current_scope", reason="local fix"),
        )
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == active[0]["blocker_id"] and packet["status"] == "open"
        ]
        self.assertEqual(len(repair_packets), 1)

        _complete_open_packet(ledger, repair_packets[0], _high_standard_contract_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

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

    def test_pm_repair_current_scope_for_packet_scope_remains_direct(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        _complete_prework_flowguard(ledger)
        packet_id = _open_packets(ledger, scope="node")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            _block_body(
                "Worker blocked on the current node.",
                blocker_class="local_artifact",
                recommended_resolution="sender fix",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            _pass_body("PM chose plain current-scope repair.", decision="repair_current_scope", reason="plain repair"),
        )

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "repair_packet_open")
        self.assertFalse(ledger["pm_decision_gates"])
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == blocker["blocker_id"] and packet["status"] == "open"
        ]
        self.assertEqual(len(repair_packets), 1)

    def test_pm_redesign_route_repair_is_gated_before_application(self) -> None:
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
            _block_body(
                "Worker blocked because this node needs a route change.",
                blocker_class="local_artifact",
                recommended_resolution="route change",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            _pass_body(
                "PM chose route redesign for the current blocker.",
                decision="redesign_route",
                reason="current route plan is wrong",
                route_plan=_route_plan_obj(
                    [
                        {
                            "node_id": "node-redesign-001",
                            "title": "Redesigned repair node",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
                            "acceptance_criteria": ["Redesigned route opens fresh repair work."],
                        }
                    ]
                ),
            ),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_pm_decision_gate")
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())
        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "repair_packet_open")
        self.assertFalse(_open_packets(ledger, kind="closure"))

    def test_pm_redesign_route_repair_reviewer_block_keeps_staged_effect_pending(self) -> None:
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
            _block_body(
                "Worker blocked because this node needs a route change.",
                blocker_class="local_artifact",
                recommended_resolution="route change",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_repair_decision")[0],
            _pass_body(
                "PM chose route redesign for the current blocker.",
                decision="redesign_route",
                reason="current route plan is wrong",
                route_plan=_route_plan_obj(
                    [
                        {
                            "node_id": "node-redesign-001",
                            "title": "Redesigned repair node",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
                            "acceptance_criteria": ["Redesigned route opens fresh repair work."],
                        }
                    ]
                ),
            ),
        )
        gate = next(iter(ledger["pm_decision_gates"].values()))
        source_result_id = gate["source_result_id"]

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="review")[0],
            _block_body(
                "Reviewer rejected the real route redesign decision.",
                blocker_class="local_artifact",
                recommended_resolution="Reviewer rejected the real route redesign decision.",
                schema_version="black_box_flowpilot.packet_outcome.v1",
            ),
        )

        self.assertEqual(gate["status"], "awaiting_review")
        self.assertEqual(gate["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["results"][source_result_id]["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertNotEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "retired_after_new_current_blocker")
        active_review_blocks = [
            row
            for row in ledger["active_blockers"].values()
            if row["status"] == "active" and row["gate_kind"] == "review"
        ]
        self.assertEqual(len(active_review_blocks), 1)
        self.assertEqual(active_review_blocks[0]["required_recheck_role"], "reviewer")

    def test_pm_redesign_route_disposition_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pass_body(
                "PM chose route redesign for the completed node.",
                decision="redesign_route",
                reason="node needs a different route",
            ),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["gate_kind"], "pm_disposition")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

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
                    "decision": "block",
                    "blocking": True,
                    "blocker_class": "needs_user",
                    "recommended_resolution": "PM must clarify the high-standard contract before evidence work.",
                }
            ),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "task.high_standard_contract")
        self.assertIn("requirements", result["missing_required_fields"])
        self.assertIn("decision", result["forbidden_fields_seen"])
        self.assertFalse(_open_packets(ledger, kind="flowguard_check"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(active, [])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["contract_family_id"], "task.high_standard_contract")
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements"])

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

        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="parent_backward_replay")[0],
            _review_pass_body("Reviewer accepted the parent backward replay."),
        )

        self.assertTrue(ledger["route_nodes"][node_id]["parent_backward_replay_id"])
        self.assertTrue(_open_packets(ledger, kind="pm_disposition"))


if __name__ == "__main__":
    unittest.main()
