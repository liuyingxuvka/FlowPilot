from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "scripts"))

import flowpilot_router as router  # noqa: E402
import packet_runtime  # noqa: E402
from scripts.test_tier import background as test_tier_background  # noqa: E402
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json  # noqa: E402


class FlowPilotEndToEndSyntheticChaosReplayTests(FlowPilotRouterRuntimeTestBase):
    def close_run_after_terminal_replay(self, root: Path, *, name: str) -> Path:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.closure")
        result = router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                f"e2e/{name}/pm_terminal_closure_decision",
                self.pm_terminal_closure_body(
                    root,
                    "Terminal closure considered the clean full-flow replay evidence.",
                ),
            ),
        )
        self.assertTrue(result["ok"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.apply_terminal_summary(root, action, run_root, note=f"E2E chaos replay {name} closed.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        terminal = router.apply_action(root, "run_lifecycle_terminal")
        self.assertTrue(terminal["terminal"])
        return run_root

    def prepare_active_node_packet(self, root: Path, *, packet_id: str) -> str:
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker",
            node_id="node-001",
            body_text=f"synthetic current node work for {packet_id}",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": packet_id, "packet_envelope_path": packet_path},
        )
        self.apply_until_action(root, "relay_current_node_packet")
        return packet_path

    def complete_current_node_after_packet_result(
        self,
        root: Path,
        *,
        packet_id: str,
        result_path: str,
        agent_id: str,
    ) -> None:
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": packet_id, "result_envelope_path": result_path},
        )
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                f"e2e/{packet_id}/current_node_result_review",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker"},
                },
            ),
        )
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

    def prepare_terminal_ready_run(self, root: Path, *, packet_id: str) -> Path:
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id=packet_id)
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        return run_root

    def test_e2e_golden_fake_ai_run_reaches_clean_terminal_lifecycle(self) -> None:
        root = self.make_project()
        run_root = self.prepare_terminal_ready_run(root, packet_id="e2e-golden-node-packet")

        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        self.assertEqual(lock["status"], "active")
        self.assertTrue(read_json(router.run_state_path(run_root))["daemon_mode_enabled"])

        self.close_run_after_terminal_replay(root, name="golden")

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")
        self.assertTrue(state["flags"]["terminal_closure_approved"])
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")
        self.assertTrue((run_root / "final_summary.md").exists())

    def test_e2e_worker_bad_package_then_repair_continues_to_terminal(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        packet_id = "e2e-worker-bad-then-repair"
        self.prepare_active_node_packet(root, packet_id=packet_id)

        lease = self.active_holder_lease_for_packet(root, packet_id)
        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_submit_result(
                root,
                lease_path=lease["lease_path"],
                role=lease["holder_role"],
                agent_id="agent-worker-1-wrong",
                result_body_text="bad result\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient="project_manager",
                route_version=lease["route_version"],
                frontier_version=lease["frontier_version"],
            )

        ledger = read_json(run_root / "packet_ledger.json")
        packet_record = next(item for item in ledger["packets"] if item["packet_id"] == packet_id)
        self.assertIsNone(packet_record.get("result_body_hash"))
        self.assertFalse(packet_record.get("result_body_hash_verified"))

        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id=packet_id,
            result_body_text="repaired result after wrong-agent rejection",
        )
        self.complete_current_node_after_packet_result(
            root,
            packet_id=packet_id,
            result_path=result_path,
            agent_id=agent_id,
        )
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.close_run_after_terminal_replay(root, name="worker_bad_then_repair")

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")

    def test_e2e_pm_repair_bad_package_then_corrected_repair_restores_legal_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="e2e_synthetic_chaos",
            error_message="fake PM package repairs route draft handoff",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/e2e-route-draft.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "rerun_target must name a registered external event"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "e2e/pm_repair/invalid_target",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="router_selects_next_legal_action_after_pm_repair",
                    ),
                ),
            )
        saved_blocker = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", saved_blocker)

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "e2e/pm_repair/registered_target",
                self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
            ),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_route_draft", action["allowed_external_events"])
        active = read_json(state_path).get("active_control_blocker")
        self.assertIsInstance(active, dict)
        self.assertEqual(active["pm_repair_decision_status"], "recorded")
        self.assertEqual(active["pm_repair_rerun_target"], "pm_writes_route_draft")

    def test_e2e_background_progress_only_then_final_artifacts_controls_proof_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-e2e-chaos-bg-") as tmp_name:
            root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(root, "e2e_background_proof")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("still running model regression\n", encoding="utf-8")

            progress = test_tier_background.classify_background_artifact(root, "e2e_background_proof")
            self.assertEqual(progress["status"], "progress_only")
            self.assertFalse(progress["ok"])
            self.assertIn("missing_exit", progress["reasons"])

            paths["out"].write_text("model regression passed\n", encoding="utf-8")
            paths["err"].write_text("", encoding="utf-8")
            paths["combined"].write_text("model regression passed\n", encoding="utf-8")
            paths["exit"].write_text("0\n", encoding="utf-8")
            paths["meta"].write_text(
                json.dumps(
                    {
                        "name": "e2e_background_proof",
                        "status": "passed",
                        "exit_code": 0,
                        "proof_reused": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            final = test_tier_background.classify_background_artifact(root, "e2e_background_proof")
            self.assertEqual(final["status"], "passed")
            self.assertTrue(final["ok"])
            self.assertEqual(final["exit_code"], 0)

    def test_e2e_parallel_run_peer_stop_does_not_mutate_current_run(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="e2e_peer_stop", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(read_json(root / ".flowpilot" / "current.json")["run_id"], "run-b")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_e2e_terminal_overclaim_then_clean_retry_closes_run(self) -> None:
        root = self.make_project()
        run_root = self.prepare_terminal_ready_run(root, packet_id="e2e-terminal-overclaim")
        self.deliver_expected_card(root, "pm.closure")
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])
        flag = router.EXTERNAL_EVENTS["pm_approves_terminal_closure"]["flag"]

        with self.assertRaisesRegex(router.RouterError, "PM suggestion ledger"):
            router.record_external_event(
                root,
                "pm_approves_terminal_closure",
                self.role_decision_envelope(
                    root,
                    "e2e/terminal/dirty_closure_overclaim",
                    self.pm_terminal_closure_body(
                        root,
                        "Terminal closure attempted while a PM suggestion ledger is dirty.",
                    ),
                ),
            )
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual(state["status"], "closed")
        self.assertFalse(state["flags"][flag])

        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=True)])
        self.close_run_after_terminal_replay(root, name="terminal_overclaim_clean_retry")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")
        self.assertTrue(state["flags"][flag])


if __name__ == "__main__":
    import unittest

    unittest.main()
