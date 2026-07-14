from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, STARTUP_ANSWERS, USER_REQUEST, read_json
from scripts.test_tier import background as test_tier_background


class FlowPilotRealRouterDryRunRehearsalTests(FlowPilotRouterRuntimeTestBase):
    def cli_json(self, root: Path, args: list[str]) -> dict:
        stdout = io.StringIO()
        argv = ["--root", str(root), *args]
        if "--json" not in argv:
            argv.append("--json")
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(argv)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0, payload)
        self.assertIsInstance(payload, dict)
        return payload

    def cli_apply_action(self, root: Path, action: dict, payload: dict | None = None) -> dict:
        action_type = str(action["action_type"])
        if payload is not None:
            applied_payload = self.payload_for_action(action, payload)
        elif action_type == "open_startup_intake_ui":
            applied_payload = self.startup_intake_payload(root, startup_answers=STARTUP_ANSWERS)
        elif action_type == "record_user_request" and action.get("requires_payload") == "user_request":
            applied_payload = {"user_request": USER_REQUEST}
        elif action_type in {"bind_background_role_agents", "start_role_slots", "create_heartbeat_automation"}:
            self.fail(f"legacy FlowPilot action reached dry-run rehearsal: {action_type}")
        else:
            applied_payload = self.payload_for_action(action)
        args = ["apply", "--action-type", action_type]
        if applied_payload:
            args.extend(["--payload-json", json.dumps(applied_payload, sort_keys=True)])
        return self.cli_json(root, args)

    def cli_boot_to_controller(self, root: Path) -> Path:
        while True:
            action = self.cli_json(root, ["next"])
            action_type = str(action["action_type"])
            self.cli_apply_action(root, action)
            if action_type == "load_controller_core":
                self.complete_startup_async_controller_rows(root, startup_answers=STARTUP_ANSWERS)
                return self.run_root_for(root)

    def close_run_after_terminal_replay(self, root: Path, *, name: str) -> Path:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.closure")
        result = router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                f"real_router_dry_run/{name}/pm_terminal_closure_decision",
                self.pm_terminal_closure_body(
                    root,
                    "Real Router dry-run rehearsal considered the clean fake AI package evidence.",
                ),
            ),
        )
        self.assertTrue(result["ok"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.apply_terminal_summary(root, action, run_root, note=f"Real Router dry-run rehearsal {name} closed.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        terminal = router.apply_action(root, "run_lifecycle_terminal")
        self.assertTrue(terminal["terminal"])
        return run_root

    def assert_rehearsal_runtime_receipts(self, root: Path, run_root: Path, packet_id: str) -> None:
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")
        self.assertIsNone(state.get("active_control_blocker"))
        self.assertGreaterEqual(len(state.get("delivered_cards", [])), 8)

        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertTrue(return_ledger["completed_returns"])
        self.assertFalse(
            [
                item
                for item in return_ledger["pending_returns"]
                if isinstance(item, dict) and item.get("status") not in {"returned", "resolved"}
            ]
        )

        packet_ledger = read_json(run_root / "packet_ledger.json")
        packet_record = next(item for item in packet_ledger["packets"] if item["packet_id"] == packet_id)
        self.assertTrue(packet_record["active_holder_lease_issued"])
        self.assertTrue(packet_record["result_envelope_path"])
        self.assertTrue(packet_record["holder_history"])

        role_output_ledger = read_json(run_root / "role_output_ledger.json")
        output_types = {item.get("output_type") for item in role_output_ledger.get("outputs", [])}
        self.assertIn("pm_package_result_disposition", output_types)

        runtime_audit = read_json(
            run_root.joinpath("routes", "route-001", "nodes", "node-001", "reviews", "current_node_packet_runtime_audit.json")
        )
        self.assertTrue(runtime_audit["passed"])
        packet_audit = next(item for item in runtime_audit["audits"] if item["packet_id"] == packet_id)
        self.assertTrue(packet_audit["result_body_hash_checked"])
        self.assertTrue(packet_audit["result_body_hash_matches_envelope"])
        self.assertTrue((run_root / "final_route_wide_gate_ledger.json").exists())
        self.assertTrue((run_root / "terminal_human_backward_replay_map.json").exists())
        self.assertTrue((run_root / "final_summary.md").exists())
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")

    def test_real_router_full_fake_ai_package_rehearsal_reaches_terminal_standard_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        packet_id = "real-router-dry-run-node-packet"

        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id=packet_id)
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.close_run_after_terminal_replay(root, name="full_fake_ai_package")

        self.assert_rehearsal_runtime_receipts(root, run_root, packet_id)

    def test_recovery_rehearsal_resume_idempotency_and_background_proof_gate(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        lock["owner"] = {"pid": 999999999, "process_name": "missing-test-daemon"}
        router.write_json(lock_path, lock)

        router.record_external_event(root, "manual_resume_requested")
        first_action = router.next_action(root)
        self.assertEqual(first_action["action_type"], "load_resume_state")
        self.assertEqual(
            first_action["router_daemon_resume_recovery"]["decision"],
            "restart_router_daemon_from_current_state",
        )

        router.record_external_event(root, "manual_resume_requested")
        second_action = router.next_action(root)
        self.assertEqual(second_action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["resume_state_loaded"])

        with tempfile.TemporaryDirectory(prefix="flowpilot-real-router-bg-proof-") as tmp_name:
            proof_root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(proof_root, "real_router_dry_run_background")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("model regression still running\n", encoding="utf-8")
            progress = test_tier_background.classify_background_artifact(proof_root, "real_router_dry_run_background")
            self.assertEqual(progress["status"], "progress_only")
            self.assertFalse(progress["ok"])

            paths["out"].write_text("model regression passed\n", encoding="utf-8")
            paths["err"].write_text("", encoding="utf-8")
            paths["combined"].write_text("model regression passed\n", encoding="utf-8")
            paths["exit"].write_text("0\n", encoding="utf-8")
            paths["meta"].write_text(
                json.dumps(
                    {
                        "name": "real_router_dry_run_background",
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
            final = test_tier_background.classify_background_artifact(proof_root, "real_router_dry_run_background")
            self.assertEqual(final["status"], "passed")
            self.assertTrue(final["ok"])
