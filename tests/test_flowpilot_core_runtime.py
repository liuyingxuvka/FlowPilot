from __future__ import annotations

import importlib.util
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import packets, role_handoff, run_shell  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_module("flowpilot_core_runtime_under_test", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_core_runtime_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)
development_runner = load_module(
    "flowpilot_core_runtime_development_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_development_checks.py",
)
control_plane_duty_runner = load_module(
    "flowpilot_new_control_plane_duty_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_new_control_plane_duty_checks.py",
)
control_plane_audit = load_module(
    "flowpilot_control_plane_friction_model_audit_under_test",
    ROOT / "simulations" / "flowpilot_control_plane_friction_model_audit.py",
)
control_surface = runtime.control_surface


class FlowPilotCoreRuntimeTests(unittest.TestCase):
    def test_runtime_assets_exist_and_document_boundaries(self) -> None:
        runtime_files = {path.name for path in RUNTIME_ROOT.iterdir() if path.is_file()}
        for required_file in {
            "__init__.py",
            "README.md",
            "runtime.py",
            "cli.py",
            "run_shell.py",
            "host.py",
            "router.py",
            "packets.py",
            "flowguard_orders.py",
            "review_closure.py",
            "cockpit.py",
            "migration.py",
            "role_handoff.py",
        }:
            with self.subTest(required_file=required_file):
                self.assertIn(required_file, runtime_files)
        readme = (RUNTIME_ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "The ledger is the truth",
            "ACK and progress are liveness only",
            "FlowGuard work orders must name the modeled target",
            "Non-authoritative inputs include prior runtime state",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_replacement_worker_can_finish_but_closed_worker_late_output_is_blocked(self) -> None:
        report = runtime_runner.replacement_worker_success()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["accepted"])
        self.assertIn("closed_or_inactive_lease", report["details"]["late_result_blockers"])

    def test_wrong_flowguard_target_self_review_stale_route_and_stale_evidence_block(self) -> None:
        for scenario_name in (
            "wrong_flowguard_target_blocks",
            "self_review_blocks",
            "stale_route_output_blocks",
            "stale_evidence_blocks",
        ):
            with self.subTest(scenario=scenario_name):
                report = runtime_runner.SCENARIOS[scenario_name]()
                self.assertTrue(report["ok"], report)
                self.assertFalse(report["accepted"])

    def test_ack_and_progress_do_not_complete_packet(self) -> None:
        report = runtime_runner.ack_only_timeout_stays_incomplete()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["details"]["before_timeout"]["action_type"], "wait_for_result")
        self.assertEqual(report["details"]["after_timeout"]["action_type"], "replace_lease")

    def test_public_console_hides_sealed_bodies(self) -> None:
        report = runtime_runner.console_does_not_leak_sealed_bodies()
        self.assertTrue(report["ok"], report)
        self.assertFalse(report["details"]["leaked"])
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)

    def test_current_progress_fraction_is_zero_before_work_expands(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")

        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "0/0")
        self.assertEqual(progress["ended_nodes"], 0)
        self.assertEqual(progress["expanded_nodes"], 0)
        self.assertFalse(progress["percent_provided"])
        self.assertTrue(progress["controller_relay_only"])
        self.assertFalse(progress["sealed_bodies_visible"])

    def test_current_progress_fraction_packet_projection_ignores_control_plane_mechanics(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")

        self.assertEqual(runtime.current_progress_fraction(ledger)["display"], "0/1")

        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.record_progress(ledger, lease_id, packet_id, "still_working")
        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "0/1")
        self.assertEqual(progress["source"], "packets")
        self.assertTrue(progress["packet_projection_used"])

    def test_current_progress_fraction_counts_route_nodes_and_repairs_equally(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["route_nodes"] = {
            "node-1": {"node_id": "node-1", "status": "running", "repair_generation": 0},
            "node-2": {"node_id": "node-2", "status": "accepted", "repair_generation": 0},
            "node-3": {"node_id": "node-3", "status": "repair_required", "repair_generation": 1},
            "node-4": {"node_id": "node-4", "status": "superseded", "repair_generation": 0},
        }

        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "3/5")
        self.assertEqual(progress["ended_nodes"], 3)
        self.assertEqual(progress["expanded_nodes"], 5)
        self.assertEqual(progress["repair_generations"], 1)
        self.assertEqual(progress["source"], "route_nodes")
        self.assertFalse(progress["packet_projection_used"])

    def test_public_console_exposes_progress_fraction_without_completion_authority(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["route_nodes"] = {
            "node-1": {"node_id": "node-1", "status": "accepted", "repair_generation": 0},
            "node-2": {"node_id": "node-2", "status": "running", "repair_generation": 0},
        }

        full = runtime.render_console(ledger)
        compact = runtime.render_compact_console(ledger)

        self.assertEqual(full["progress_fraction"]["display"], "1/2")
        self.assertEqual(compact["progress_fraction"]["display"], "1/2")
        self.assertFalse(compact["progress_fraction"]["percent_provided"])
        self.assertEqual(compact["counts"]["progress_ended_nodes"], 1)
        self.assertEqual(compact["counts"]["progress_expanded_nodes"], 2)
        self.assertEqual(compact["status_projection_authority"], "display_only")

    def test_reassignment_supersedes_older_active_packet_lease(self) -> None:
        ledger, packet_id, first_lease = runtime_runner._base_ledger()
        assignment = runtime.resolve_role_assignment(ledger, "worker", packet_id=packet_id, host_kind="fake")
        second_lease = runtime.lease_agent(
            ledger,
            "worker",
            packet_id=packet_id,
            assignment_id=assignment["assignment_id"],
        )

        runtime.assign_packet(ledger, packet_id, second_lease)

        self.assertEqual(ledger["packets"][packet_id]["assigned_lease_id"], second_lease)
        self.assertEqual(ledger["leases"][first_lease]["status"], "superseded")
        self.assertEqual(ledger["leases"][first_lease]["superseded_by"], second_lease)
        self.assertEqual(ledger["leases"][second_lease]["status"], "active")
        self.assertEqual(ledger["leases"][second_lease]["packet_id"], packet_id)

    def test_final_preflight_blocks_stale_active_accepted_packet_lease(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)
        stale_lease = runtime._next_id(ledger, "lease")
        ledger["leases"][stale_lease] = {
            **ledger["leases"][worker],
            "lease_id": stale_lease,
            "agent_id": "stale-worker",
            "status": "active",
            "packet_id": packet_id,
            "ack_received": True,
        }

        health = runtime.accepted_packet_lease_health(ledger)
        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(health["ok"])
        self.assertEqual(health["findings"][0]["active_lease_ids"], [stale_lease])
        self.assertFalse(preflight["allowed"])
        self.assertIn(f"accepted_packet_lease_health:{packet_id}", preflight["blockers"])
        self.assertEqual(runtime.router_next_action(ledger).action_type, "repair_accepted_packet")

    def test_compact_status_projection_hides_sealed_bodies(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        compact = runtime.render_compact_console(ledger)
        rendered = json.dumps(compact, sort_keys=True)

        self.assertEqual(compact["projection"], "compact_controller_status")
        self.assertFalse(compact["sealed_bodies_visible"])
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)
        self.assertIn("body_free", compact["body_policy"])

    def test_recover_or_reissue_payload_names_concrete_command(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        ledger["leases"][worker]["liveness_status"] = "not_found"
        ledger["leases"][worker]["liveness_checked_at"] = runtime.now_iso()

        guard = runtime.preview_lifecycle_guard(ledger, trigger="patrol")
        duty = runtime.preview_foreground_duty(ledger, guard=guard, trigger="patrol")
        command = duty["recovery"]["recommended_command"]

        self.assertEqual(duty["action"], "recover_or_reissue")
        self.assertEqual(command["command"], "resolve-role-assignment")
        self.assertEqual(command["packet_id"], packet_id)
        self.assertEqual(command["responsibility"], "worker")
        self.assertEqual(command["host_kind"], "live")
        self.assertNotIn("--agent-id", command["cli"])
        self.assertNotIn("<new-agent-id>", command["cli"])
        self.assertIn(worker, command["stale_lease_ids"])
        self.assertFalse(command["sealed_bodies_visible"])

    def test_nested_node_context_package_is_rejected(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        node = {"node_id": "node-1", "title": "Node One", "repair_generation": 0}
        ledger["route_nodes"]["node-1"] = node
        package = {
            "node_id": "node-1",
            "purpose": "Give every role enough starting context without granting command authority.",
            "acceptance_criteria": ["criterion"],
            "relevant_references": ["reference"],
            "evidence_targets": ["evidence"],
            "inspection_targets": ["inspection"],
            "known_risks": ["risk"],
            "flowguard_targets": ["development_process"],
            "reviewer_starting_points": ["start here"],
        }
        ledger["results"]["result-node"] = {
            "result_id": "result-node",
            "body": json.dumps({"node_acceptance_plan": {"node_context_package": package}}),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "top-level node_context_package"):
            runtime._node_context_package_from_pm_result(
                ledger,
                node,
                {"packet_id": "packet-node", "accepted_result_id": "result-node"},
                "result-node",
            )
        self.assertFalse(
            [event for event in ledger["events"] if event["event_type"] == "node_context_package_accepted"]
        )

    def test_planning_result_old_route_nodes_shape_reissues_current_planning_packet(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Planning route", ["Plan"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "pm",
            "Write current route plan",
            "PLANNING_PACKET",
            route_scope="planning",
        )
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-plan", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(
                {
                    "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                    "route_nodes": [{"node_id": "node-1", "title": "Old alias"}],
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("current_result_contract_violation", result["mechanical_blockers"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        reissues = [
            packet
            for packet in ledger["packets"].values()
            if packet["packet_id"] != packet_id
            and packet["envelope"]["route_scope"] == "planning"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        self.assertEqual(reissues[0]["envelope"]["responsibility"], "pm")
        self.assertEqual(reissues[0]["envelope"]["packet_kind"], "task")

    def test_node_acceptance_plan_result_stages_effect_before_closure(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "pending",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        package = {
            "node_id": "node-1",
            "purpose": "Provide current starting context.",
            "acceptance_criteria": ["criterion"],
            "relevant_references": ["reference"],
            "evidence_targets": ["evidence"],
            "inspection_targets": ["inspection"],
            "known_risks": ["risk"],
            "flowguard_targets": ["development_process"],
            "reviewer_starting_points": ["review start"],
        }

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"node_context_package": package, "decision": "pass"}),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")
        self.assertEqual(result["staged_effect"]["status"], "pending")
        self.assertFalse(ledger["node_acceptance_plans"])
        self.assertFalse(ledger["node_context_packages"])
        flowguard_packets = [
            packet for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        self.assertEqual(len(flowguard_packets), 1)
        self.assertEqual(json.loads(flowguard_packets[0]["body"])["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")

    def test_staged_effect_same_family_reuses_pending_effect(self) -> None:
        record: dict[str, object] = {}

        first = runtime._attach_staged_effect(
            record,
            effect_kind="commit_route_redesign",
            source_packet_id="packet-1",
            source_result_id="result-1",
            target_node_id="node-1",
            blocker_id="blocker-1",
            gate_id="gate-1",
            route_scope="node",
        )
        second = runtime._attach_staged_effect(
            record,
            effect_kind="commit_route_redesign",
            source_packet_id="packet-2",
            source_result_id="result-2",
            target_node_id="node-2",
            blocker_id="blocker-2",
            gate_id="gate-2",
            route_scope="node",
        )

        self.assertIs(second, first)
        self.assertEqual(record["staged_effect"], first)
        self.assertEqual(first["source_packet_id"], "packet-1")
        self.assertEqual(first["gate_id"], "gate-1")

    def test_redesign_route_pm_decision_stages_route_effect_until_gate_applies(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "running",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do node work",
            "NODE_PACKET",
            route_node_id="node-1",
            route_scope="node",
        )
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-node", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "redesign route"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-route", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        active_route_version = ledger["active_route_version"]

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "Current route cannot complete cleanly.",
                    "route_plan": {
                        "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                        "decision": "pass",
                        "nodes": [
                            {
                                "node_id": "node-redesign-001",
                                "title": "Repair redesigned node",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["Repair route has fresh executable work."],
                            }
                        ],
                    },
                }
            ),
        )

        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertEqual(gate["staged_effect"]["effect_kind"], "commit_route_redesign")
        self.assertEqual(gate["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["effect_kind"], "commit_route_redesign")
        self.assertEqual(ledger["active_route_version"], active_route_version)

    def test_repair_current_scope_preserves_pm_repair_decision_packet_kind(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Do work"])
        target_blocker_id = "blocker-target"
        ledger["active_blockers"][target_blocker_id] = {
            "blocker_id": target_blocker_id,
            "status": "active",
            "outcome_id": "outcome-target",
            "packet_id": "packet-target",
            "packet_kind": "task",
            "subject_packet_id": "packet-target",
            "repair_target_packet_id": "packet-target",
            "target_result_id": "",
            "result_id": "result-target",
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        pm_repair_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, target_blocker_id)
        reissue_blocker_id = "blocker-reissue"
        decision_id = "pm_repair_decision-reissue"
        ledger["active_blockers"][reissue_blocker_id] = {
            **ledger["active_blockers"][target_blocker_id],
            "blocker_id": reissue_blocker_id,
            "repair_target_packet_id": pm_repair_packet,
            "subject_packet_id": pm_repair_packet,
            "packet_id": pm_repair_packet,
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": decision_id,
        }
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": reissue_blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Replace PM decision in same current scope.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, reissue_blocker_id, decision_id)

        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        fresh = ledger["packets"][fresh_packet_id]
        self.assertEqual(fresh["envelope"]["packet_kind"], "pm_repair_decision")
        self.assertEqual(fresh["envelope"]["route_scope"], "pm_repair_decision")
        self.assertEqual(fresh["envelope"]["subject_id"], pm_repair_packet)

    def test_flowguard_fallback_evidence_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, json.dumps({"decision": "pass"}))
        flowguard_packet = next(
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        )
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg",
            packet_id=flowguard_packet["packet_id"],
        )
        runtime.assign_packet(ledger, flowguard_packet["packet_id"], flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet["packet_id"])

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet["packet_id"],
            json.dumps({"decision": "pass", "evidence_mode": "api_fallback_manual_block_eval"}),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][flowguard_packet["packet_id"]]["status"], "superseded_after_repair")
        reissues = [
            packet for packet in ledger["packets"].values()
            if packet["packet_id"] != flowguard_packet["packet_id"]
            and packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)

    def test_result_submitted_repair_target_is_superseded_after_reissue(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, json.dumps({"decision": "pass"}))
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_submitted")

        blocker_id = "blocker-result-submitted"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-result-submitted",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "reissue current work",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        decision_id = "pm_repair_decision-result-submitted"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Replace a submitted but unaccepted packet.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)

        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        self.assertEqual(ledger["packets"][fresh_packet_id]["status"], "open")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_final_preflight_blocks_active_blocker_pointing_at_result_submitted_target(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, json.dumps({"decision": "pass"}))
        blocker_id = "blocker-stale-submitted"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-stale-submitted",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }

        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(preflight["allowed"])
        self.assertTrue(
            any(
                blocker.startswith(f"active_blocker_result_submitted_target:{blocker_id}:")
                for blocker in preflight["blockers"]
            ),
            preflight["blockers"],
        )

    def test_final_preflight_does_not_block_on_repair_packet_open_history(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, json.dumps({"decision": "pass"}))
        blocker_id = "blocker-repair-open"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-repair-open",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        decision_id = "pm_repair_decision-repair-open"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Open a fresh repair packet.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)
        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(preflight["allowed"])
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")
        self.assertFalse(
            [
                blocker
                for blocker in preflight["blockers"]
                if blocker.startswith(f"active_blocker_current_target:{blocker_id}:")
                or blocker.startswith(f"active_blocker_result_submitted_target:{blocker_id}:")
            ],
            preflight["blockers"],
        )

    def test_foreground_recovery_missing_packet_responsibility_hard_blocks(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")
        ledger["packets"][packet_id]["envelope"]["responsibility"] = ""
        guard = {
            "decision": "replace_lease",
            "next_action": {
                "action_type": "replace_lease",
                "subject_id": packet_id,
                "responsibility": "worker",
            },
            "wait_subject": {"packet_id": packet_id},
            "wait_recovery": {"lease_id": "lease-stale"},
        }

        command = runtime._foreground_recovery_command(ledger, guard)

        self.assertEqual(command["command"], "control-plane-blocker")
        self.assertEqual(command["packet_id"], packet_id)
        self.assertEqual(command["responsibility"], "")
        self.assertEqual(command["cli"], "")
        self.assertEqual(command["cleanup_action"], "hard_block_until_current_packet_responsibility_exists")

    def test_evidence_summary_finalizer_excludes_self_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("A", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "b.txt").write_text("B", encoding="utf-8")
            (root / "evidence_summary.md").write_text("summary", encoding="utf-8")
            (root / "evidence_summary.json").write_text("old", encoding="utf-8")

            manifest = runtime.finalize_evidence_summary_manifest(root)
            second_manifest = runtime.finalize_evidence_summary_manifest(root)

            paths = [item["path"] for item in manifest["evidence_files"]]
            self.assertEqual(paths, ["a.txt", "nested/b.txt"])
            self.assertEqual(second_manifest["evidence_files"], manifest["evidence_files"])
            self.assertEqual(json.loads((root / "evidence_summary.json").read_text(encoding="utf-8"))["file_count"], 2)

    def test_terminal_current_pointer_status_uses_final_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Goal", "Acceptance", run_id="run-terminal")
            ledger, packet_id, worker = runtime_runner._base_ledger()
            runtime_runner._complete_happy_path(ledger, packet_id, worker)

            run_shell.save_run_ledger(shell, ledger, guard_trigger="final_preflight")
            current = json.loads((root / ".flowpilot" / "current.json").read_text(encoding="utf-8"))

            self.assertEqual(current["lifecycle_state"], "terminal_complete")
            self.assertEqual(current["ledger_lifecycle_state"], "contract_frozen")
            self.assertTrue(current["final_return_allowed"])
            self.assertEqual(current["closure_decision"], "complete")

    def test_router_closes_only_after_backward_chain_and_validation(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")
        chain = ledger["closure"]["backward_chain"]
        self.assertEqual([item["packet_kind"] for item in chain if item["kind"] == "packet"], [
            "task",
            "flowguard_check",
            "review",
        ])
        self.assertTrue(ledger["system_closures"])
        self.assertFalse([lease for lease in ledger["leases"].values() if lease["status"] == "active"])

    def test_runtime_testmesh_does_not_overclaim_release_evidence(self) -> None:
        report = runtime_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["test_mesh"]["parent_gates"]["routine_runtime_gate"]["ok"])
        self.assertFalse(report["test_mesh"]["parent_gates"]["release_runtime_gate"]["ok"])
        rows = {row["id"]: row for row in report["test_mesh"]["rows"]}
        self.assertEqual(rows["background_meta_capability"]["status"], "not_run")
        self.assertEqual(rows["install_surface_parity"]["status"], "not_run")

    def test_flowguard_development_model_accepts_order_and_rejects_hazards(self) -> None:
        report = development_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["target_plan"]["ok"])
        self.assertTrue(report["hazard_detection"]["ok"])
        self.assertIn("fixed_role_topology_reintroduced", report["hazard_detection"]["hazards"])

    def test_flowguard_control_plane_duty_model_matches_runtime_repairs(self) -> None:
        report = control_plane_duty_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["source_contract"]["ok"])
        self.assertIn("status_mutates_ledger", report["hazard_detection"]["hazards"])

    def test_current_run_resolver_accepts_new_schema_and_rejects_project_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / ".flowpilot" / "runs" / "run-new"
            run_root.mkdir(parents=True)
            ledger_path = run_root / "ledger.json"
            ledger_path.write_text("{}\n", encoding="utf-8")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_text(
                json.dumps(
                    {
                        "schema_version": "black_box_flowpilot_run_shell.v1",
                        "authority": "current_run_ledger",
                        "run_id": "run-new",
                        "run_root": str(run_root),
                        "ledger_path": str(ledger_path),
                    }
                ),
                encoding="utf-8",
            )

            resolution = control_surface.resolve_current_run(root)

            self.assertTrue(resolution.ok, resolution)
            self.assertEqual(resolution.run_id, "run-new")
            self.assertEqual(resolution.run_root, run_root.resolve())
            self.assertEqual(resolution.source_fields, ("run_id", "run_root"))

            current_path.write_text(
                json.dumps({"run_id": "run-new", "run_root": "."}),
                encoding="utf-8",
            )
            invalid = control_surface.resolve_current_run(root)

            self.assertFalse(invalid.ok)
            self.assertEqual(invalid.error_code, "invalid_run_root")

            current_path.write_text(
                json.dumps({"current_run_id": "run-new", "current_run_root": str(run_root)}),
                encoding="utf-8",
            )
            legacy = control_surface.resolve_current_run(root)

            self.assertFalse(legacy.ok)
            self.assertEqual(legacy.error_code, "unsupported_run_pointer_fields")

    def test_current_run_resolver_missing_pointer_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = control_surface.resolve_current_run(root)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "missing_file")
            finding = result.finding()
            self.assertEqual(finding["code"], "current_run_resolution_failed")
            self.assertIn("current.json", finding["evidence"]["pointer_path"])

    def test_safe_json_read_and_live_audit_report_invalid_utf8_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_utf8 = root / "bad.json"
            bad_utf8.write_bytes(b"\xff\xfe")
            bad_json = root / "bad-syntax.json"
            bad_json.write_text("{", encoding="utf-8")

            utf8_result = control_surface.safe_read_json(bad_utf8)
            json_result = control_surface.safe_read_json(bad_json)

            self.assertFalse(utf8_result.ok)
            self.assertEqual(utf8_result.error_code, "invalid_utf8")
            self.assertFalse(json_result.ok)
            self.assertEqual(json_result.error_code, "invalid_json")

            run_root = root / ".flowpilot" / "runs" / "run-bad"
            run_root.mkdir(parents=True)
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps({"run_id": "run-bad", "run_root": str(run_root)}),
                encoding="utf-8",
            )
            (run_root / "router_state.json").write_bytes(b"\xff\xfe")
            (run_root / "ledger.json").write_text(
                json.dumps(runtime.new_ledger("Goal", "Contract")),
                encoding="utf-8",
            )

            audit = control_plane_audit.audit_live_run(root)

            self.assertFalse(audit["ok"])
            codes = {finding["code"] for finding in audit["findings"]}
            self.assertIn("control_surface_evidence_unreadable", codes)

    def test_packet_control_surface_contracts_are_role_symmetric(self) -> None:
        required_roles = {
            "pm",
            "worker",
            "flowguard_operator",
            "reviewer",
        }
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        for role in sorted(required_roles):
            packet_id = runtime.issue_task_packet(
                ledger,
                role,
                f"{role} objective",
                json.dumps({"role": role}),
                packet_kind="flowguard_check" if role == "flowguard_operator" else "task",
            )
            envelope = ledger["packets"][packet_id]["envelope"]
            self.assertEqual(envelope["output_contract"]["recipient_responsibility"], role)

        findings = control_surface.audit_packet_contracts(
            ledger,
            required_responsibilities=required_roles,
        )

        self.assertEqual(findings, [])

        bad_ledger = json.loads(json.dumps(ledger))
        reviewer_packet = next(
            packet
            for packet in bad_ledger["packets"].values()
            if packet["envelope"]["responsibility"] == "reviewer"
        )
        reviewer_packet["envelope"].pop("output_contract")
        bad_findings = control_surface.audit_packet_contracts(
            bad_ledger,
            required_responsibilities=required_roles,
        )

        self.assertIn("packet_contract_fields_missing", {finding["code"] for finding in bad_findings})

    def test_packet_result_contract_separates_ack_result_and_acceptance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "body")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")

        result_id = runtime.submit_result(ledger, lease_id, packet_id, json.dumps({"decision": "pass"}))

        packet = ledger["packets"][packet_id]
        result = ledger["results"][result_id]
        self.assertEqual(packet["status"], "result_submitted")
        self.assertEqual(packet["accepted_result_id"], "")
        self.assertTrue(result["envelope"]["ack_result_accepted_separate"])
        self.assertEqual(result["envelope"]["output_contract"]["packet_id"], packet_id)
        flowguard_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        self.assertEqual(len(flowguard_packets), 1)
        self.assertEqual(runtime.router_next_action(ledger).subject_id, flowguard_packets[0]["packet_id"])
        self.assertEqual(control_surface.audit_packet_contracts(ledger), [])

    def test_generated_role_handoff_and_packet_open_are_role_symmetric(self) -> None:
        for role in sorted(runtime.RESPONSIBILITIES):
            with self.subTest(role=role):
                ledger = runtime.new_ledger("Goal", "Contract")
                runtime.create_route(ledger, "Route", ["Do work"])
                body = f"SEALED_BODY_FOR_{role}"
                packet_id = runtime.issue_task_packet(
                    ledger,
                    role,
                    f"{role} objective",
                    body,
                    packet_kind="flowguard_check" if role == "flowguard_operator" else "task",
                )
                lease_id = runtime.lease_agent(ledger, role, agent_id=f"{role}-agent", packet_id=packet_id)
                runtime.assign_packet(ledger, packet_id, lease_id)

                handoff = role_handoff.render_current_packet_handoff(
                    ledger,
                    root=ROOT,
                    script_path=ASSETS_ROOT / "flowpilot_new.py",
                    run_id="run-test",
                    packet_id=packet_id,
                    lease_id=lease_id,
                )

                rendered = json.dumps(handoff, sort_keys=True)
                self.assertTrue(handoff["controller_may_read"])
                self.assertFalse(handoff["controller_may_read_packet_body"])
                self.assertFalse(handoff["sealed_body_text_included"])
                self.assertIn("flowpilot_new.py", handoff["commands"]["ack"])
                self.assertIn("open-packet", handoff["commands"]["open_packet"])
                self.assertIn("submit-result", handoff["commands"]["submit_result"])
                self.assertNotIn(body, rendered)

                with self.assertRaises(Exception):
                    packets.open_sealed_body_for_role(ledger, packet_id, lease_id)

                runtime.ack_lease(ledger, lease_id, packet_id)
                opened = packets.open_sealed_body_for_role(ledger, packet_id, lease_id)

                self.assertEqual(opened, body)
                open_events = [
                    event
                    for event in ledger["events"]
                    if event["event_type"] == "sealed_packet_body_opened"
                    and event["payload"]["packet_id"] == packet_id
                    and event["payload"]["lease_id"] == lease_id
                ]
                self.assertEqual(len(open_events), 1)

    def test_packet_open_rejects_wrong_stale_or_tampered_authority(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "sealed")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        wrong_lease = runtime.lease_agent(ledger, "worker", agent_id="worker-2", packet_id=packet_id)
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(ledger, packet_id, wrong_lease)

        wrong_role = copy.deepcopy(ledger)
        wrong_role_lease = runtime.lease_agent(wrong_role, "pm", agent_id="pm-1")
        wrong_role["packets"][packet_id]["assigned_lease_id"] = wrong_role_lease
        wrong_role["leases"][wrong_role_lease]["ack_received"] = True
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(wrong_role, packet_id, wrong_role_lease)

        accepted = copy.deepcopy(ledger)
        accepted["packets"][packet_id]["status"] = "accepted"
        accepted["packets"][packet_id]["accepted_result_id"] = "result-accepted"
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(accepted, packet_id, lease_id)

        tampered = copy.deepcopy(ledger)
        tampered["packets"][packet_id]["body"] = "changed after envelope hash"
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(tampered, packet_id, lease_id)

    def test_prose_status_pass_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "\n".join(
                [
                    "Status: PASS",
                    "The old topology check failed before this repair.",
                    "The report includes function-block rows and blocker history.",
                ]
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertIn("current_result_contract_violation", ledger["results"][result_id]["mechanical_blockers"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        reissues = [
            row
            for row in ledger["packets"].values()
            if row["packet_id"] != packet_id and row["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)

    def test_declared_block_line_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "Decision: block\nReason: current evidence is not sufficient.",
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["active_blockers"])
        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "resolve_role_assignment")
        self.assertEqual(action.responsibility, "worker")

    def test_structured_verdict_alias_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"verdict": "blocked", "recommended_resolution": "fresh FlowGuard evidence required"}),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["active_blockers"])

    def test_nested_flowguard_report_not_ok_routes_to_semantic_repair(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "flowguard_report": {
                        "ok": False,
                        "findings": ["missing_validation_evidence"],
                    },
                    "recommended_resolution": "rerun with current-run evidence",
                }
            ),
        )

        self.assertEqual(ledger["results"][result_id]["semantic_decision"], "block")
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_blocked")
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)

    def test_run_until_wait_folds_internal_action_to_role_boundary(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["startup_intake"] = {"sealed": True}
        runtime.create_route(ledger, "Route", ["Do work"])

        boundary = runtime.run_until_wait(ledger)

        self.assertEqual(boundary["boundary_class"], "role_dispatch")
        self.assertEqual(boundary["next_action"]["action_type"], "resolve_role_assignment")
        self.assertEqual(boundary["folded_applied_count"], 1)
        self.assertEqual(boundary["folded_applied_actions"][0]["action_type"], "issue_task_packet")

    def test_pm_repair_decision_ignores_hostile_prose_when_json_decision_is_present(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs repair"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-a", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)

        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "repair_current_scope",
                    "reason": "This prose mentions stop_for_user and block, but they are not the decision.",
                }
            ),
        )

        decision = next(iter(ledger["pm_repair_decisions"].values()))
        self.assertEqual(decision["decision"], "repair_current_scope")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_removed_pm_repair_decisions_are_rejected(self) -> None:
        for removed in (
            "same_node_repair",
            "sender_reissue",
            "collect_more_evidence",
            "mutate_route",
            "quarantine_evidence",
        ):
            with self.subTest(removed=removed):
                ledger, packet_id, worker = runtime_runner._base_ledger()
                runtime.ack_lease(ledger, worker, packet_id)
                runtime.submit_result(
                    ledger,
                    worker,
                    packet_id,
                    json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
                )
                blocker_id = next(iter(ledger["active_blockers"]))
                pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
                pm_lease = runtime.lease_agent(ledger, "pm", agent_id=f"pm-{removed}", packet_id=pm_packet)
                runtime.assign_packet(ledger, pm_packet, pm_lease)
                runtime.ack_lease(ledger, pm_lease, pm_packet)

                bad_result = runtime.submit_result(
                    ledger,
                    pm_lease,
                    pm_packet,
                    json.dumps({"decision": removed, "reason": "old menu value"}),
                )

                self.assertEqual(ledger["results"][bad_result]["status"], "pm_repair_decision_blocked")
                self.assertFalse(ledger["pm_repair_decisions"])
                self.assertIn("removed decision", ledger["results"][bad_result]["quarantine_reason"])

    def test_waive_with_authority_requires_authority_ref_and_opens_no_repair_packet(self) -> None:
        for body, expected_status in (
            ({"decision": "waive_with_authority", "reason": "authorized exception"}, "pm_repair_decision_blocked"),
            (
                {
                    "decision": "waive_with_authority",
                    "reason": "authorized exception",
                    "authority_ref": "AUTH-20260604-001",
                },
                "waived",
            ),
        ):
            with self.subTest(expected_status=expected_status):
                ledger, packet_id, worker = runtime_runner._base_ledger()
                runtime.ack_lease(ledger, worker, packet_id)
                runtime.submit_result(
                    ledger,
                    worker,
                    packet_id,
                    json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
                )
                blocker_id = next(iter(ledger["active_blockers"]))
                blocker = ledger["active_blockers"][blocker_id]
                pm_packet = blocker["pm_repair_packet_id"]
                pm_lease = runtime.lease_agent(ledger, "pm", agent_id=f"pm-{expected_status}", packet_id=pm_packet)
                runtime.assign_packet(ledger, pm_packet, pm_lease)
                runtime.ack_lease(ledger, pm_lease, pm_packet)

                result_id = runtime.submit_result(ledger, pm_lease, pm_packet, json.dumps(body))

                if expected_status == "pm_repair_decision_blocked":
                    self.assertEqual(ledger["results"][result_id]["status"], expected_status)
                    self.assertFalse(ledger["pm_repair_decisions"])
                    self.assertIn("authority_ref", ledger["results"][result_id]["quarantine_reason"])
                else:
                    self.assertEqual(ledger["active_blockers"][blocker_id]["status"], expected_status)
                    self.assertEqual(ledger["active_blockers"][blocker_id]["authority_ref"], "AUTH-20260604-001")
                    self.assertNotIn("repair_packet_id", ledger["active_blockers"][blocker_id])

    def test_june3_same_node_empty_fresh_packet_regression_is_rejected(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs repair"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        decision_id = "pm_repair_decision-june3"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": blocker["pm_repair_packet_id"],
            "result_id": result_id,
            "decision": "repair_current_scope",
            "reason": "Regression guard for empty fresh packet.",
            "created_at": runtime.now_iso(),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "fresh repair packet id"):
            runtime._mark_blocker_repair_packet_open(
                ledger,
                blocker,
                decision_id=decision_id,
                fresh_packet_id="",
            )

        self.assertNotEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_pm_repair_decision_requires_structured_field_and_stop_pauses_route(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        bad_pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-bad", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, bad_pm_lease)
        runtime.ack_lease(ledger, bad_pm_lease, pm_packet)

        bad_result = runtime.submit_result(
            ledger,
            bad_pm_lease,
            pm_packet,
            "This body says block and stop_for_user, but it has no structured decision field.",
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "pm_repair_decision_blocked")
        self.assertEqual(ledger["packets"][pm_packet]["status"], "result_blocked")
        self.assertFalse(ledger["pm_repair_decisions"])
        self.assertEqual(runtime.router_next_action(ledger).action_type, "issue_pm_repair_decision_packet")

        fresh_pm_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
        self.assertNotEqual(fresh_pm_packet, pm_packet)
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")

        good_pm_lease = runtime.lease_agent(ledger, "pm", packet_id=fresh_pm_packet)
        runtime.assign_packet(ledger, fresh_pm_packet, good_pm_lease)
        runtime.ack_lease(ledger, good_pm_lease, fresh_pm_packet)
        runtime.submit_result(
            ledger,
            good_pm_lease,
            fresh_pm_packet,
            json.dumps({"decision": "stop_for_user", "reason": "PM needs the user to decide."}),
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "wait_for_resume")
        runtime.record_resume_request(ledger, "plain_resume")
        runtime.reconcile_resume_request(ledger, resume_source="plain_resume")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")

        recovery = runtime.resolve_stopped_blocker(
            ledger,
            blocker_id,
            resolution="reissue_pm_repair_decision",
            reason="user chose to continue current repair",
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "active")
        self.assertNotEqual(recovery["fresh_packet_id"], fresh_pm_packet)
        self.assertEqual(ledger["packets"][recovery["fresh_packet_id"]]["envelope"]["packet_kind"], "pm_repair_decision")

    def test_nested_pm_repair_decision_wrapper_is_rejected_and_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-wrapper", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)

        bad_result = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps({"repair_decision": {"decision": "same_node_repair", "reason": "legacy wrapper"}}),
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "pm_repair_decision_blocked")
        self.assertFalse(ledger["pm_repair_decisions"])
        fresh_pm_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)

        self.assertNotEqual(fresh_pm_packet, pm_packet)
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")
        body = json.loads(ledger["packets"][fresh_pm_packet]["body"])
        self.assertTrue(body["repair_decision_contract"]["top_level_decision_only"])
        self.assertTrue(body["repair_decision_contract"]["nested_repair_decision_wrappers_forbidden"])

    def test_pm_repair_decision_summary_is_not_reason_fallback(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-summary", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)

        bad_result = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "repair_current_scope",
                    "summary": "legacy reason fallback must not be accepted",
                    "recommended_resolution": "same node repair",
                }
            ),
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "pm_repair_decision_blocked")
        self.assertIn("top-level reason", ledger["results"][bad_result]["quarantine_reason"])
        self.assertFalse(ledger["pm_repair_decisions"])


if __name__ == "__main__":
    unittest.main()
