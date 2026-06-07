from __future__ import annotations

import importlib
import hashlib
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
run_shell = importlib.import_module("flowpilot_core_runtime.run_shell")
host = importlib.import_module("flowpilot_core_runtime.host")
packets = importlib.import_module("flowpilot_core_runtime.packets")
flowguard_orders = importlib.import_module("flowpilot_core_runtime.flowguard_orders")
review_closure = importlib.import_module("flowpilot_core_runtime.review_closure")
cockpit = importlib.import_module("flowpilot_core_runtime.cockpit")
migration = importlib.import_module("flowpilot_core_runtime.migration")
complete_development_runner = importlib.import_module("simulations.run_flowpilot_complete_system_development_checks")
complete_structure_runner = importlib.import_module("simulations.run_flowpilot_complete_system_structure_checks")
complete_ui_runner = importlib.import_module("simulations.run_flowpilot_complete_system_ui_checks")
complete_testmesh_runner = importlib.import_module("simulations.run_flowpilot_complete_system_testmesh_checks")
complete_alignment_runner = importlib.import_module("simulations.run_flowpilot_complete_system_alignment_checks")
complete_runtime_runner = importlib.import_module("simulations.run_flowpilot_complete_system_runtime_checks")


def role_result_body(*, decision: str = "pass", summary: str = "role result", **extra: object) -> str:
    body = {
        "decision": decision,
        "pm_visible_summary": [summary],
    }
    body.update(extra)
    return json.dumps(body)


def open_required_result_reads(ledger: dict[str, object], packet_id: str, lease_id: str) -> None:
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)


def authorize_background_collaboration(ledger: dict[str, object]) -> None:
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }


class FlowPilotCompleteSystemRuntimeTests(unittest.TestCase):
    def test_run_shell_creates_current_run_authority_without_old_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shell = run_shell.create_run_shell(Path(tmp), "Build target", "Accept only with full evidence", run_id="run-test")
            self.assertTrue(shell.ledger_path.is_file())
            self.assertTrue(shell.events_path.is_file())
            current = json.loads((Path(tmp) / ".flowpilot" / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(current["authority"], "current_run_ledger")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["run_id"], "run-test")
            self.assertEqual(ledger["project_id"], "run-test")
            self.assertEqual(ledger["events"][0]["event_family"], "lifecycle")
            self.assertTrue((shell.run_root / "console" / "status.json").is_file())

    def test_startup_intake_result_is_copied_as_current_run_sealed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Build target", "Accept only with full evidence", run_id="run-test")
            source_dir = root / ".flowpilot" / "bootstrap" / "startup_intake" / "sample"
            source_dir.mkdir(parents=True)
            body = source_dir / "startup_intake_body.md"
            body.write_text("sealed user request", encoding="utf-8")
            body_hash = hashlib.sha256(body.read_bytes()).hexdigest()
            receipt = source_dir / "startup_intake_receipt.json"
            receipt.write_text(json.dumps({"status": "confirmed"}) + "\n", encoding="utf-8")
            envelope = source_dir / "startup_intake_envelope.json"
            envelope.write_text(json.dumps({"body_hash": body_hash}) + "\n", encoding="utf-8")
            result = source_dir / "startup_intake_result.json"
            result.write_text(
                json.dumps(
                    {
                        "status": "confirmed",
                        "source": "headless_startup_intake",
                        "startup_answers": {"background_collaboration_authorized": True, "display_surface": "cockpit"},
                        "body_path": str(body.relative_to(root)),
                        "body_hash": body_hash,
                        "receipt_path": str(receipt.relative_to(root)),
                        "envelope_path": str(envelope.relative_to(root)),
                        "body_text_included": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            record = run_shell.record_startup_intake_result(shell, result)
            ledger = run_shell.load_run_ledger(shell)

            self.assertTrue(record["current_run_authority"])
            self.assertFalse(record["controller_may_read_body"])
            self.assertEqual(ledger["startup_intake"]["body_hash"], body_hash)
            self.assertTrue((shell.run_root / "startup_intake" / "startup_intake_body.md").is_file())
            self.assertIn("startup", {event["event_family"] for event in ledger["events"]})

    def test_events_append_only_and_role_memory_is_file_backed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shell = run_shell.create_run_shell(Path(tmp), "Goal", "Contract", run_id="run-events")
            ledger = run_shell.load_run_ledger(shell)
            authorize_background_collaboration(ledger)
            initial_events = shell.events_path.read_text(encoding="utf-8").splitlines()
            lease_id = host.lease_responsibility(ledger, "project_manager", host_kind="fake", scope="startup")
            host.record_role_memory_seed(ledger, lease_id, memory_packet_id="memory-001", prior_agent_id="old-pm")
            run_shell.save_run_ledger(shell, ledger)
            after_first_save = shell.events_path.read_text(encoding="utf-8").splitlines()
            run_shell.save_run_ledger(shell, ledger)
            after_second_save = shell.events_path.read_text(encoding="utf-8").splitlines()

            self.assertGreater(len(after_first_save), len(initial_events))
            self.assertEqual(after_first_save, after_second_save)
            self.assertTrue((shell.run_root / "role_memory" / f"{lease_id}.json").is_file())
            role_assignment_id = ledger["leases"][lease_id]["role_assignment_id"]
            self.assertTrue((shell.run_root / "role_assignments" / f"{role_assignment_id}.json").is_file())

    def test_dynamic_host_lease_is_scoped_until_real_live_evidence_exists(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        lease_id = host.lease_responsibility(ledger, "project_manager", host_kind="fake", scope="startup")
        boundary = host.host_confidence_boundary(ledger)
        self.assertFalse(boundary["has_live_host_evidence"])
        self.assertEqual(boundary["confidence"], "scoped")
        self.assertEqual(ledger["leases"][lease_id]["responsibility"], "pm")
        live_lease_id = host.lease_responsibility(ledger, "worker", host_kind="live", scope="node")
        self.assertTrue(ledger["host_evidence"][live_lease_id]["live_confidence"])
        self.assertEqual(host.host_confidence_boundary(ledger)["confidence"], "live")

    def test_same_responsibility_leases_reuse_current_run_agent_for_all_roles(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])

        for role in ("pm", "reviewer", "flowguard_operator", "worker", "research_worker", "ui_qa", "planner"):
            with self.subTest(role=role):
                first = host.lease_responsibility(ledger, role, agent_id=f"{role}-agent-1", host_kind="fake")
                runtime.close_lease(ledger, first, "test_role_available")
                second = host.lease_responsibility(ledger, role, agent_id=f"{role}-agent-2", host_kind="fake")

                self.assertEqual(ledger["leases"][second]["agent_id"], f"{role}-agent-1")
                self.assertTrue(ledger["leases"][second]["role_continuity"]["reused"])
                assignment_id = ledger["leases"][second]["role_assignment_id"]
                self.assertEqual(ledger["role_assignments"][assignment_id]["disposition"], "reuse_existing_role")
                self.assertEqual(ledger["role_assignments"][assignment_id]["status"], "consumed")
                slot = ledger["role_continuity"]["roles"][role]
                self.assertEqual(slot["agent_id"], f"{role}-agent-1")
                self.assertEqual(slot["rejected_replacement_candidate_ids"], [])

    def test_role_assignment_resolution_reuses_without_fresh_candidate(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "reviewer", "Review", "SEALED_REVIEW")
        first = host.lease_responsibility(ledger, "reviewer", agent_id="reviewer-agent-1", host_kind="fake")
        runtime.close_lease(ledger, first, "available")

        assignment = runtime.resolve_role_assignment(ledger, "reviewer", packet_id=packet_id, host_kind="fake")
        self.assertEqual(assignment["disposition"], "reuse_existing_role")
        self.assertFalse(assignment["role_surface_required"])
        self.assertEqual(assignment["effective_agent_id"], "reviewer-agent-1")

        lease_id = host.lease_responsibility(
            ledger,
            "reviewer",
            host_kind="fake",
            packet_id=packet_id,
            assignment_id=assignment["assignment_id"],
        )

        self.assertEqual(ledger["leases"][lease_id]["agent_id"], "reviewer-agent-1")
        self.assertEqual(ledger["leases"][lease_id]["role_assignment_id"], assignment["assignment_id"])
        self.assertEqual(ledger["role_assignments"][assignment["assignment_id"]]["status"], "consumed")
        self.assertEqual(ledger["role_continuity"]["roles"]["reviewer"]["rejected_replacement_candidate_ids"], [])

    def test_missing_role_slot_hydrates_from_current_run_same_role_history(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Review work"])
        packet_id = packets.issue_packet(ledger, "reviewer", "Review", "SEALED_REVIEW")
        first = host.lease_responsibility(ledger, "reviewer", agent_id="reviewer-agent-1", host_kind="fake", packet_id=packet_id)
        runtime.close_lease(ledger, first, "available")
        del ledger["role_continuity"]["roles"]["reviewer"]

        next_packet = packets.issue_packet(ledger, "reviewer", "Review next", "SEALED_REVIEW_NEXT")
        assignment = runtime.resolve_role_assignment(ledger, "reviewer", packet_id=next_packet, host_kind="fake")

        self.assertEqual(assignment["disposition"], "reuse_existing_role")
        self.assertEqual(assignment["hydration_reason"], "hydrated_from_current_run_history")
        self.assertEqual(assignment["effective_agent_id"], "reviewer-agent-1")
        self.assertEqual(
            ledger["role_continuity"]["roles"]["reviewer"]["hydrated_from_current_run_lease"],
            first,
        )

    def test_missing_role_slot_with_unusable_history_blocks_assignment(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Review work"])
        packet_id = packets.issue_packet(ledger, "reviewer", "Review", "SEALED_REVIEW")
        first = host.lease_responsibility(ledger, "reviewer", agent_id="reviewer-agent-1", host_kind="fake", packet_id=packet_id)
        runtime.record_host_liveness(ledger, first, packet_id, "lost")
        del ledger["role_continuity"]["roles"]["reviewer"]

        next_packet = packets.issue_packet(ledger, "reviewer", "Review next", "SEALED_REVIEW_NEXT")
        assignment = runtime.resolve_role_assignment(ledger, "reviewer", packet_id=next_packet, host_kind="fake")

        self.assertEqual(assignment["disposition"], "blocked")
        self.assertEqual(assignment["status"], "blocked")
        self.assertEqual(assignment["blocker_reason"], "role_continuity_slot_missing_and_history_not_reusable")
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "history_not_reusable"):
            host.lease_responsibility(
                ledger,
                "reviewer",
                agent_id="reviewer-agent-2",
                host_kind="fake",
                packet_id=next_packet,
                assignment_id=assignment["assignment_id"],
            )

    def test_replacement_lease_requires_same_responsibility_memory_seed(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Review work"])
        packet_id = packets.issue_packet(ledger, "reviewer", "Review work", "SEALED_REVIEW")
        first = host.lease_responsibility(ledger, "reviewer", agent_id="reviewer-agent-1", host_kind="fake", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, first)
        runtime.record_host_liveness(ledger, first, packet_id, "lost")

        replacement_packet = packets.issue_packet(ledger, "reviewer", "Review replacement work", "SEALED_REVIEW_2")
        replacement = host.lease_responsibility(
            ledger,
            "reviewer",
            agent_id="reviewer-agent-2",
            host_kind="fake",
            packet_id=replacement_packet,
        )
        memory = runtime.role_memory_seed_for_lease(ledger, replacement, replacement_packet)

        self.assertEqual(ledger["leases"][replacement]["agent_id"], "reviewer-agent-2")
        self.assertEqual(ledger["leases"][replacement]["prior_agent_id"], "reviewer-agent-1")
        self.assertTrue(ledger["leases"][replacement]["role_memory_seed_required"])
        self.assertIsNotNone(memory)
        assert memory is not None
        self.assertEqual(memory["role"], "reviewer")
        self.assertFalse(memory["sealed_packet_body_text_included"])
        self.assertFalse(memory["sealed_result_body_text_included"])
        self.assertNotIn("SEALED_REVIEW", json.dumps(memory, sort_keys=True))

    def test_pm_repair_packets_include_recommendation_and_fresh_deliverable_contract(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")
        worker = host.lease_responsibility(ledger, "worker", agent_id="worker-agent-1", host_kind="fake", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, worker)
        runtime.ack_lease(ledger, worker, packet_id)
        host.submit_host_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                decision="block",
                summary="Deliverable gap blocks this worker packet.",
                blocker_class="deliverable_gap",
                recommended_resolution="Create the missing concrete deliverable, not another repair summary.",
            ),
        )

        blocker = next(iter(ledger["active_blockers"].values()))
        pm_packet_id = blocker["pm_repair_packet_id"]
        pm_body = json.loads(ledger["packets"][pm_packet_id]["body"])
        self.assertEqual(pm_body["recommended_resolution"], "Create the missing concrete deliverable, not another repair summary.")
        self.assertEqual(pm_body["repair_target_packet_id"], packet_id)
        self.assertEqual(pm_body["repair_target"]["output_contract"]["packet_id"], packet_id)
        self.assertTrue(pm_body["repair_decision_contract"]["repair_summary_alone_is_not_completion"])

        pm_lease = host.lease_responsibility(ledger, "pm", agent_id="pm-agent-1", host_kind="fake", packet_id=pm_packet_id)
        runtime.assign_packet(ledger, pm_packet_id, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet_id)
        open_required_result_reads(ledger, pm_packet_id, pm_lease)
        host.submit_host_result(
            ledger,
            pm_lease,
            pm_packet_id,
            json.dumps({"decision": "repair_current_scope", "reason": "open a fresh current-scope repair packet"}),
        )

        repair_packet = next(
            packet
            for packet in ledger["packets"].values()
            if packet.get("repair_blocker_id") == blocker["blocker_id"]
        )
        repair_body = json.loads(repair_packet["body"])
        self.assertEqual(repair_body["source_packet_id"], packet_id)
        self.assertEqual(repair_body["source_output_contract"]["packet_id"], packet_id)
        self.assertEqual(repair_body["recommended_resolution"], "Create the missing concrete deliverable, not another repair summary.")
        self.assertTrue(repair_body["repair_completion_contract"]["must_submit_current_packet_result"])
        self.assertTrue(repair_body["repair_completion_contract"]["must_satisfy_source_output_contract"])
        self.assertTrue(repair_body["repair_completion_contract"]["source_artifact_is_context_not_passing_evidence"])
        self.assertTrue(repair_body["repair_completion_contract"]["repair_summary_alone_is_not_completion"])

    def test_repair_packet_open_blocker_stays_visible_in_status_projection(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")
        worker = host.lease_responsibility(ledger, "worker", agent_id="worker-agent-1", host_kind="fake", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, worker)
        runtime.ack_lease(ledger, worker, packet_id)
        host.submit_host_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                decision="block",
                summary="Deliverable gap blocks this worker packet.",
                blocker_class="deliverable_gap",
                recommended_resolution="Create the missing concrete deliverable.",
            ),
        )
        blocker = next(iter(ledger["active_blockers"].values()))
        pm_packet_id = blocker["pm_repair_packet_id"]
        pm_lease = host.lease_responsibility(ledger, "pm", agent_id="pm-agent-1", host_kind="fake", packet_id=pm_packet_id)
        runtime.assign_packet(ledger, pm_packet_id, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet_id)
        open_required_result_reads(ledger, pm_packet_id, pm_lease)
        host.submit_host_result(
            ledger,
            pm_lease,
            pm_packet_id,
            json.dumps({"decision": "repair_current_scope", "reason": "open a fresh current-scope repair packet"}),
        )

        compact = runtime.render_compact_console(ledger)
        projected = compact["active_blockers"]

        self.assertEqual(blocker["status"], "repair_packet_open")
        self.assertEqual(compact["counts"]["active_blockers"], 1)
        self.assertEqual(projected[0]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(projected[0]["status"], "repair_packet_open")

    def test_repeated_blocker_family_is_visible_as_advisory_context(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")

        for index in (1, 2):
            lease = host.lease_responsibility(
                ledger,
                "worker",
                agent_id=f"worker-agent-{index}",
                host_kind="fake",
                packet_id=packet_id,
            )
            runtime.assign_packet(ledger, packet_id, lease)
            runtime.ack_lease(ledger, lease, packet_id)
            host.submit_host_result(
                ledger,
                lease,
                packet_id,
                role_result_body(
                    decision="block",
                    summary="Same deliverable gap blocks this worker packet.",
                    blocker_class="same_gap",
                    recommended_resolution="Fix the same missing output.",
                ),
            )

        latest_blocker = list(ledger["active_blockers"].values())[-1]
        pm_packet = ledger["packets"][latest_blocker["pm_repair_packet_id"]]
        pm_body = json.loads(pm_packet["body"])

        self.assertEqual(pm_body["repeat_context"]["repeat_count"], 2)
        self.assertTrue(pm_body["repeat_context"]["advisory_only"])
        self.assertIn(list(ledger["active_blockers"].values())[0]["blocker_id"], pm_body["repeat_context"]["previous_blocker_ids"])

    def test_complete_packet_flow_rejects_cockpit_direct_state_write_and_old_authority(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")
        lease_id = host.lease_responsibility(ledger, "worker", host_kind="fake")
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        result_id = host.submit_host_result(ledger, lease_id, packet_id, role_result_body(summary="Worker result passed."))
        order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", packet_id)
        flowguard_orders.complete_work_order(ledger, order_id, proof_artifact="simulations/result.json")
        reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
        review_id = review_closure.review_result(
            ledger,
            result_id,
            reviewer,
            scope_restatement="Check packet evidence",
            failure_hypotheses=["stale output", "wrong target"],
        )
        runtime.record_validation_evidence(ledger, "unit-validation")
        migration.import_old_artifact(ledger, Path("old/.flowpilot/state.json"), disposition="imported_read_only", reason="historical context")
        gate = migration.evaluate_cutover_gate(
            ledger,
            openspec_ok=True,
            flowguard_ok=True,
            tests_ok=True,
            install_ok=True,
            live_host_ok=False,
            git_ok=True,
        )
        closure = review_closure.attempt_final_closure(ledger, "unit-validation")
        projection = cockpit.render_status(ledger)
        event = cockpit.submit_cockpit_event(ledger, "pause", {"routes": {"bad": "direct-write"}})

        self.assertEqual(ledger["reviews"][review_id]["scope_restatement"], "Check packet evidence")
        self.assertEqual(gate["decision"], "blocked")
        self.assertIn("live_host_not_current", gate["blockers"])
        self.assertEqual(closure["decision"], "blocked")
        self.assertIn("cutover_gate_blocked", closure["blockers"])
        self.assertFalse(ledger["imported_evidence"]["import-0001"]["current_authority"])
        self.assertTrue(projection["projection_only"])
        self.assertFalse(projection["sealed_bodies_visible"])
        self.assertFalse(event["accepted"])
        self.assertEqual(event["blocked_direct_keys"], ["routes"])
        rendered = json.dumps(projection, sort_keys=True)
        self.assertNotIn("SEALED_TASK", rendered)
        self.assertNotIn("SEALED_RESULT", rendered)

    def test_route_mutation_duplicate_body_hash_and_completion_claim_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route v1", ["Do work"])
        old_packet = packets.issue_packet(ledger, "worker", "Old work", "OLD_BODY")
        old_lease = host.lease_responsibility(ledger, "worker", host_kind="fake")
        runtime.assign_packet(ledger, old_packet, old_lease)
        runtime.ack_lease(ledger, old_lease, old_packet)
        runtime.create_route(ledger, "Route v2", ["New work"])
        new_packet = packets.issue_packet(ledger, "worker", "New work", "NEW_BODY")
        new_lease = host.lease_responsibility(ledger, "worker", host_kind="fake")
        runtime.assign_packet(ledger, new_packet, new_lease)
        runtime.ack_lease(ledger, new_lease, new_packet)
        bad_hash_result = host.submit_host_result(
            ledger,
            new_lease,
            new_packet,
            role_result_body(summary="Bad hash result."),
            packet_body_hash="not-the-packet-hash",
        )
        good_result = host.submit_host_result(ledger, new_lease, new_packet, role_result_body(summary="Good worker result."))
        duplicate_result = host.submit_host_result(ledger, new_lease, new_packet, role_result_body(summary="Duplicate worker result."))
        order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", new_packet)
        flowguard_orders.complete_work_order(ledger, order_id, proof_artifact="simulations/result.json")
        reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
        review_closure.review_result(
            ledger,
            good_result,
            reviewer,
            direct_evidence_ids=["unit-validation"],
            pm_routing_decision="accept_result",
        )
        runtime.record_validation_evidence(ledger, "unit-validation")
        runtime.record_completion_claim(ledger, source="chat", claim="done")
        ledger["open_resources"].append("runtime-role-slot")
        ledger["residual_risks"].append("live-host missing")
        ledger["old_ui_evidence"].append("old screenshot")
        closure = runtime.attempt_final_closure(ledger, "unit-validation")

        self.assertEqual(ledger["packets"][old_packet]["status"], "quarantined_after_route_mutation")
        self.assertTrue(ledger["route_mutations"][0]["requires_replay_or_rebinding"])
        self.assertIn("body_hash_mismatch", ledger["results"][bad_hash_result]["mechanical_blockers"])
        self.assertIn("duplicate_output_from_same_lease", ledger["results"][duplicate_result]["mechanical_blockers"])
        self.assertIn("completion_report_only_not_sufficient", closure["blockers"])
        self.assertIn("unresolved_resources", closure["blockers"])
        self.assertIn("unresolved_residual_risks", closure["blockers"])
        self.assertIn("old_ui_evidence_unresolved", closure["blockers"])

    def test_superseded_lease_output_and_missing_or_report_only_flowguard_do_not_satisfy_gate(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")
        first = host.lease_responsibility(ledger, "worker", host_kind="fake")
        replacement = host.lease_responsibility(ledger, "worker", host_kind="fake")
        runtime.supersede_lease(ledger, first, replacement)
        runtime.assign_packet(ledger, packet_id, replacement)
        runtime.ack_lease(ledger, replacement, packet_id)
        late = host.submit_host_result(ledger, first, packet_id, role_result_body(summary="Late worker result."))
        result_id = host.submit_host_result(ledger, replacement, packet_id, role_result_body(summary="Replacement worker result."))
        with self.assertRaises(runtime.BlackBoxRuntimeError):
            flowguard_orders.create_work_order(ledger, "", "done_claim", packet_id)
        order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", packet_id)
        flowguard_orders.complete_work_order(ledger, order_id, proof_artifact="", progress_only=True)
        reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
        review_id = review_closure.review_result(ledger, result_id, reviewer)

        self.assertIn("closed_or_inactive_lease", ledger["results"][late]["mechanical_blockers"])
        self.assertEqual(ledger["reviews"][review_id]["decision"], "block")
        self.assertIn("missing_matching_flowguard_report", ledger["reviews"][review_id]["blockers"])

    def test_cockpit_disconnect_records_display_surface_blocker(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        blocked = cockpit.record_display_surface_blocker(ledger, "cockpit_unavailable")
        projection = cockpit.render_status(ledger)

        self.assertTrue(blocked["blocker"]["repair_required"])
        self.assertEqual(projection["display_surface"]["active"], "blocked")
        self.assertEqual(ledger["user_events"][-1]["cockpit_event_type"], "display_blocked")

    def test_current_run_save_materializes_sealed_envelopes_orders_reviews_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shell = run_shell.create_run_shell(Path(tmp), "Goal", "Contract", run_id="run-materialize")
            ledger = run_shell.load_run_ledger(shell)
            authorize_background_collaboration(ledger)
            runtime.create_route(ledger, "Route", ["Do work"])
            packet_id = packets.issue_packet(ledger, "worker", "Do work", "SEALED_TASK")
            lease_id = host.lease_responsibility(ledger, "worker", host_kind="fake")
            runtime.assign_packet(ledger, packet_id, lease_id)
            runtime.ack_lease(ledger, lease_id, packet_id)
            result_id = host.submit_host_result(ledger, lease_id, packet_id, role_result_body(summary="Persisted worker result."))
            order_id = flowguard_orders.create_work_order(ledger, "development_process", "done_claim", packet_id)
            flowguard_orders.complete_work_order(ledger, order_id, proof_artifact="simulations/result.json")
            reviewer = host.lease_responsibility(ledger, "reviewer", host_kind="fake")
            review_id = review_closure.review_result(ledger, result_id, reviewer, scope_restatement="Check")
            runtime.record_validation_evidence(ledger, "unit-validation")
            run_shell.save_run_ledger(shell, ledger)

            self.assertTrue((shell.run_root / "routes" / "route-v1.json").is_file())
            self.assertTrue((shell.run_root / "packets" / "envelopes" / f"{packet_id}.json").is_file())
            self.assertTrue((shell.run_root / "packets" / "bodies" / f"{packet_id}.md").is_file())
            self.assertTrue((shell.run_root / "results" / "envelopes" / f"{result_id}.json").is_file())
            self.assertTrue((shell.run_root / "flowguard" / "work_orders" / f"{order_id}.json").is_file())
            self.assertTrue((shell.run_root / "flowguard" / "work_orders" / "envelopes" / f"{order_id}.json").is_file())
            self.assertTrue((shell.run_root / "flowguard" / "work_orders" / "reports" / f"{order_id}.json").is_file())
            self.assertTrue((shell.run_root / "reviews" / f"{review_id}.json").is_file())
            status = json.loads((shell.run_root / "console" / "status.json").read_text(encoding="utf-8"))
            self.assertNotIn("SEALED_TASK", json.dumps(status, sort_keys=True))
            self.assertNotIn("SEALED_RESULT", json.dumps(status, sort_keys=True))

    def test_complete_system_models_are_green_but_release_gate_stays_scoped(self) -> None:
        for runner in (
            complete_development_runner,
            complete_structure_runner,
            complete_ui_runner,
            complete_alignment_runner,
            complete_runtime_runner,
        ):
            with self.subTest(runner=runner.__name__):
                self.assertTrue(runner.run_checks()["ok"])

        testmesh = complete_testmesh_runner.run_checks()
        self.assertTrue(testmesh["ok"], testmesh)
        self.assertFalse(testmesh["release_gate"]["ok"])
        self.assertIn("live_host", testmesh["release_gate"]["required_suites"])

    def test_complete_system_runner_uses_current_contract_for_all_packets(self) -> None:
        ledger, packet_id, lease_id = complete_runtime_runner._base_ledger()
        result_id = complete_runtime_runner._complete_packet(ledger, packet_id, lease_id)

        self.assertTrue(runtime.background_collaboration_authorized(ledger))
        worker_payload = json.loads(ledger["results"][result_id]["body"])
        self.assertIn("decision", worker_payload)
        self.assertIn("pm_visible_summary", worker_payload)
        for packet in ledger["packets"].values():
            contract = packet["envelope"].get("current_handoff_contract")
            self.assertIsInstance(contract, dict)
            self.assertEqual(contract["packet_id"], packet["packet_id"])
            required_reads = contract["input_material_manifest"]["required_authorized_reads_before_submit"]
            receipts = packet.get("authorized_result_read_receipts", [])
            for required_result_id in required_reads:
                self.assertIn(required_result_id, {receipt["result_id"] for receipt in receipts})
        for result in ledger["results"].values():
            blockers = ",".join(result.get("mechanical_blockers", []))
            self.assertNotIn("required_result_body_not_opened", blockers)


if __name__ == "__main__":
    unittest.main()
