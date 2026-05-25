from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "scripts"))

import flowpilot_router as router  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402
from scripts.test_tier import background as test_tier_background  # noqa: E402
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json  # noqa: E402
from tests.synthetic_agent_trace_replay import SyntheticTracePackage, start_worker_trace  # noqa: E402


class FlowPilotHardGateRedTeamReplayTests(FlowPilotRouterRuntimeTestBase):
    def test_hard_gate_unauthorized_event_envelope_preserves_pending_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)
        self.assertEqual(envelope["event_name"], "reviewer_reports_startup_facts")
        flag = router.EXTERNAL_EVENTS["reviewer_reports_startup_facts"]["flag"]
        before = read_json(router.run_state_path(run_root))

        with self.assertRaisesRegex(router.RouterError, "not currently allowed"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
            )

        after = read_json(router.run_state_path(run_root))
        self.assertEqual(after.get("pending_action"), before.get("pending_action"))
        self.assertFalse(after["flags"][flag])
        self.assertNotEqual(after["status"], "closed")
        self.assertFalse(
            any(event.get("event") == "reviewer_reports_startup_facts" for event in after.get("events", []))
        )

    def test_hard_gate_role_output_authority_mismatch_writes_no_output(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-test")
        self.write_current_focus(root, run_root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = {
            "action_type": "await_role_decision",
            "to_role": "project_manager",
            "allowed_external_events": ["pm_registers_role_work_request"],
        }
        router.save_run_state(run_root, state)

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "not currently allowed"):
            role_output_runtime.validate_direct_router_submission_authority(
                root,
                output_type="officer_model_report",
                role="product_flowguard_officer",
                agent_id="agent-product-officer-hard-gate",
                run_id="run-test",
                event_name="product_officer_model_report",
            )

        self.assertFalse((run_root / "role_outputs").exists())
        self.assertFalse((run_root / "role_output_ledger.json").exists())

    def test_hard_gate_packet_wrong_holder_identity_preserves_ledger(self) -> None:
        replay = start_worker_trace(
            SyntheticTracePackage(name="hard_gate_packet_wrong_active_holder_identity")
        )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_submit_result(
                replay.root,
                lease_path=replay.lease["lease_path"],  # type: ignore[index]
                role=replay.package.role,
                agent_id="agent-worker-a-wrong",
                result_body_text="bad result\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient="project_manager",
                route_version=1,
                frontier_version=1,
            )

        record = replay.packet_record()
        self.assertIsNone(record.get("result_body_hash"))
        self.assertFalse(record.get("result_body_hash_verified"))
        self.assertFalse(replay.result_envelope_path.exists())

    def test_hard_gate_background_progress_only_proof_is_not_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-hard-gate-bg-") as tmp_name:
            root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(root, "hard_gate_progress_only")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("still running model exploration\n", encoding="utf-8")

            evidence = test_tier_background.classify_background_artifact(
                root,
                "hard_gate_progress_only",
            )

        self.assertEqual(evidence["status"], "progress_only")
        self.assertFalse(evidence["ok"])
        self.assertIn("missing_exit", evidence["reasons"])

    def test_hard_gate_peer_run_stop_preserves_current_run_authority(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="hard_gate_peer_stop", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(read_json(root / ".flowpilot" / "current.json")["current_run_id"], "run-b")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_hard_gate_terminal_closure_overclaim_preserves_nonclosed_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="hard-gate-terminal-node-packet")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])
        flag = router.EXTERNAL_EVENTS["pm_approves_terminal_closure"]["flag"]

        with self.assertRaisesRegex(router.RouterError, "PM suggestion ledger"):
            router.record_external_event(
                root,
                "pm_approves_terminal_closure",
                self.role_decision_envelope(
                    root,
                    "hard_gate/terminal_dirty_ledger_overclaim",
                    {
                        "approved_by_role": "project_manager",
                        "decision": "approve_terminal_closure",
                        **self.prior_path_context_review(
                            root,
                            "Terminal closure attempted while the PM suggestion ledger is dirty.",
                        ),
                        "final_report": {"status": "complete"},
                    },
                ),
            )

        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual(state["status"], "closed")
        self.assertFalse(state["flags"][flag])


if __name__ == "__main__":
    import unittest

    unittest.main()
