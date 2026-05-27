from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
import flowpilot_router_io_locks as router_io_locks  # noqa: E402


class TerminalRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        pending_before_stop = self.next_after_display_sync(root)
        self.assertIn(
            pending_before_stop["action_type"],
            {
                "confirm_controller_core_boundary",
                "check_prompt_manifest",
                "create_heartbeat_automation",
                "deliver_system_card",
                "write_display_surface_status",
            },
        )

        router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "stopped_by_user")
        self.assertFalse(action["controller_may_continue_route_work"])
        self.assertTrue(action["controller_may_read_all_current_run_files"])
        self.apply_terminal_summary(root, action, run_root, note="User asked to stop.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "stopped_by_user")
        self.assertFalse(action["controller_may_continue_route_work"])
        result = router.apply_action(root, "run_lifecycle_terminal")
        self.assertTrue(result["terminal"])

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertTrue(state["flags"]["run_stopped_by_user"])
        self.assertTrue((run_root / "lifecycle" / "run_lifecycle.json").exists())
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["reconciliation"]["status"], "stopped_by_user")
        self.assertTrue((run_root / "lifecycle" / "terminal_reconciliation.json").exists())
        continuation = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertFalse(continuation["heartbeat_active"])
        self.assertIn(continuation["host_automation_cleanup_status"], {"inactive_verified", "missing_verified"})
        crew = read_json(run_root / "crew_ledger.json")
        self.assertTrue(all(slot["status"] == "stopped_with_run" for slot in crew["role_slots"]))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertEqual(packet_ledger["active_packet_status"], "stopped_by_user")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "stopped_by_user")
        self.assertTrue(frontier["terminal"])
        snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(snapshot["state"]["status"], "stopped_by_user")
        self.assertTrue(snapshot["state"]["flags"]["run_stopped_by_user"])
        self.assertEqual(snapshot["frontier"]["status"], "stopped_by_user")
        self.assertEqual(snapshot["packet_ledger"]["active_packet_status"], "stopped_by_user")
        self.assertEqual(snapshot["active_ui_task_catalog"]["active_tasks"], [])
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertEqual(current["status"], "stopped_by_user")

        result = router.record_external_event(root, "user_requests_run_cancel", {"reason": "user switched to cancel"})
        self.assertTrue(result["ok"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "cancelled_by_user")
    def test_user_stop_writes_immediate_daemon_terminal_fence_and_clears_current_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        result = router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        fence = read_json(run_root / "lifecycle" / "terminal_fence.json")
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertFalse(state["daemon_mode_enabled"])
        self.assertTrue(state["flags"]["terminal_daemon_fence_written"])
        self.assertTrue(state["flags"]["terminal_projection_refreshed"])
        self.assertTrue(state["flags"]["terminal_next_step_cleared"])
        self.assertEqual(lock["status"], "terminal_stopped")
        self.assertEqual(lock["release_reason"], "user_requests_run_stop_terminal_fence")
        self.assertEqual(status["lifecycle_status"], "terminal_stopped")
        self.assertEqual(status["run_lifecycle_status"], "stopped_by_user")
        self.assertFalse(status["daemon_mode_enabled"])
        self.assertFalse(status["daemon_live"])
        self.assertIsNone(status["current_action"])
        self.assertIsNone(status["continuous_standby_task"])
        self.assertEqual(status["current_work"]["source"], "terminal_lifecycle")
        self.assertFalse(status["current_work"]["diagnostics"]["nonterminal_work_allowed"])
        self.assertEqual(fence["status"], "stopped_by_user")
        self.assertFalse(fence["controller_may_continue_route_work"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
    def test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        flags = state.setdefault("flags", {})
        for flag in (
            "material_scan_packets_relayed",
            "worker_packets_delivered",
            "worker_scan_results_returned",
            "material_scan_results_relayed_to_pm",
            "material_scan_result_disposition_recorded",
        ):
            flags[flag] = True

        tx_id = "repair-tx-terminal-quarantine"
        tx_path = run_root / "control_blocks" / "repair_transactions" / f"{tx_id}.json"
        router.write_json(
            tx_path,
            {
                "schema_version": "flowpilot.repair_transaction.v1",
                "transaction_id": tx_id,
                "run_id": state["run_id"],
                "blocker_id": "control-blocker-terminal-quarantine",
                "status": "committed",
                "plan_kind": "packet_reissue",
            },
        )
        state["active_repair_transaction"] = {
            "transaction_id": tx_id,
            "blocker_id": "control-blocker-terminal-quarantine",
            "status": "committed",
            "plan_kind": "packet_reissue",
            "path": self.rel(root, tx_path),
        }
        body_ref = {
            "path": self.rel(root, run_root / "reviews" / "startup_fact_report-terminal.json"),
            "hash": "duplicate-review-hash",
        }
        state["events"] = [
            {"event": "reviewer_reports_startup_facts", "payload": {"body_ref": body_ref}},
            {"event": "reviewer_reports_startup_facts", "payload": {"body_ref": body_ref}},
        ]
        state["external_event_idempotency"] = {
            "processed": {
                "pm_records_material_scan_result_disposition": {
                    "first": {
                        "scope": {
                            "batch_id": "batch-a",
                            "packet_ids": "packet-a",
                            "packet_generation_id": "generation-a",
                            "body_hash": "hash-a",
                        }
                    },
                    "second": {
                        "scope": {
                            "batch_id": "batch-a",
                            "packet_ids": "packet-a",
                            "packet_generation_id": "generation-a",
                            "body_hash": "hash-b",
                        }
                    },
                }
            }
        }
        router.save_run_state(run_root, state)

        packet_ledger_path = run_root / "packet_ledger.json"
        packet_ledger = read_json(packet_ledger_path)
        packet_ledger.setdefault("packets", []).append(
            {
                "packet_id": "packet-missing-author",
                "result_envelope": {
                    "completed_by_role": "worker_a",
                    "completed_agent_id": None,
                    "completed_agent_id_belongs_to_role": False,
                },
            }
        )
        router.write_json(packet_ledger_path, packet_ledger)

        result = router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})

        self.assertTrue(result["ok"])
        state = read_json(state_path)
        self.assertIsNone(state["active_repair_transaction"])
        for flag in (
            "material_scan_packets_relayed",
            "worker_packets_delivered",
            "worker_scan_results_returned",
            "material_scan_results_relayed_to_pm",
            "material_scan_result_disposition_recorded",
        ):
            self.assertFalse(state["flags"][flag])
        tx = read_json(tx_path)
        self.assertEqual(tx["status"], "superseded_by_terminal_lifecycle")
        self.assertEqual(state["events"][1]["terminal_lifecycle_quarantine"]["status"], "terminal_lifecycle_quarantined")
        records = state["external_event_idempotency"]["processed"]["pm_records_material_scan_result_disposition"]
        self.assertEqual(records["second"]["terminal_lifecycle_quarantine"]["status"], "terminal_lifecycle_quarantined")
        packet_ledger = read_json(packet_ledger_path)
        result_envelope = packet_ledger["packets"][-1]["result_envelope"]
        self.assertEqual(result_envelope["author_identity_quarantine"]["status"], "terminal_lifecycle_quarantined")
        reconciliation = read_json(run_root / "lifecycle" / "terminal_reconciliation.json")
        authorities = {receipt["authority"] for receipt in reconciliation["cleanup_receipts"]}
        self.assertIn("repair_transaction", authorities)
        self.assertIn("material_progress_flags", authorities)
        self.assertIn("role_output_event_identity", authorities)
        self.assertIn("packet_result_author_identity", authorities)
    def test_user_stop_writes_terminal_fence_before_best_effort_scheduler_cleanup(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        write_lock = router._json_write_lock_path(scheduler_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(scheduler_path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS", 0.01):
            result = router.record_external_event(root, "user_requests_run_stop", {"reason": "stop while scheduler is locked"})

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        fence = read_json(run_root / "lifecycle" / "terminal_fence.json")
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertFalse(state["daemon_mode_enabled"])
        self.assertEqual(lock["status"], "terminal_stopped")
        self.assertEqual(status["lifecycle_status"], "terminal_stopped")
        self.assertEqual(status["current_work"]["source"], "terminal_lifecycle")
        self.assertEqual(fence["controller_work_fence"]["status"], "best_effort_failed")
        self.assertEqual(fence["controller_work_fence"]["error"]["type"], "RouterLedgerWriteInProgress")
        write_lock.unlink(missing_ok=True)
    def test_terminal_pending_heartbeat_action_is_noop(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["status"] = "stopped_by_user"
        state.setdefault("flags", {})["run_stopped_by_user"] = True
        state["flags"]["continuation_binding_recorded"] = False
        state["pending_action"] = router.make_action(
            action_type="create_heartbeat_automation",
            actor="bootloader",
            label="host_bootstraps_startup_heartbeat_automation",
            summary="Create a heartbeat automation.",
            extra={"postcondition": "continuation_binding_recorded"},
        )
        router.save_run_state(run_root, state)
        binding_before = read_json(run_root / "continuation" / "continuation_binding.json")

        result = router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))

        binding_after = read_json(run_root / "continuation" / "continuation_binding.json")
        refreshed_state = read_json(router.run_state_path(run_root))
        self.assertTrue(result["heartbeat_binding_skipped"])
        self.assertEqual(result["terminal_lifecycle_status"], "stopped_by_user")
        self.assertEqual(binding_after, binding_before)
        self.assertFalse(refreshed_state["flags"]["continuation_binding_recorded"])
        self.assertIsNone(refreshed_state.get("pending_action"))
    def test_reconcile_run_recovers_terminal_status_from_current_pointer(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-terminal-drift", status="startup_bootstrap")
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "current_run_id": run_root.name,
                "current_run_root": router.project_relative(root, run_root),
                "status": "stopped_by_user",
                "updated_at": router.utc_now(),
            },
        )
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [
                    {
                        "run_id": run_root.name,
                        "run_root": router.project_relative(root, run_root),
                        "status": "stopped_by_user",
                    }
                ],
            },
        )

        result = router.reconcile_current_run(root)

        self.assertTrue(result["ok"])
        self.assertTrue(result["repaired"]["terminal_status_recovered_from_authority"])
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertTrue(state["flags"]["run_stopped_by_user"])
        snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(snapshot["state"]["status"], "stopped_by_user")
        self.assertTrue(snapshot["state"]["flags"]["run_stopped_by_user"])
        self.assertEqual(snapshot["authority"]["active_source"], "explicit_active_set")
        self.assertEqual(snapshot["authority"]["source_authority"], "index_active_runs_with_current_focus")
        self.assertTrue(snapshot["authority"]["current_pointer_is_ui_focus_only"])
    def test_terminal_summary_payload_requires_attribution_display_and_run_root_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertTrue(action["apply_required"])
        self.assertTrue(action["next_step_contract"]["apply_required"])
        self.assertIn(
            "direct terminal action",
            json.dumps(action["payload_contract"]["structural_requirements"], sort_keys=True),
        )

        bad_summary = "Final Summary\n\nNo FlowPilot attribution.\n"
        with self.assertRaisesRegex(router.RouterError, "GitHub attribution"):
            router.apply_controller_action(
                root,
                "write_terminal_summary",
                {
                    "summary_markdown": bad_summary,
                    "displayed_to_user": True,
                    "displayed_summary_sha256": hashlib.sha256(bad_summary.encode("utf-8")).hexdigest(),
                    "read_scope_used": router.TERMINAL_SUMMARY_READ_SCOPE,
                },
            )

        good = self.terminal_summary_payload(root, action, run_root, note="User asked to stop.")
        with self.assertRaisesRegex(router.RouterError, "current run root"):
            router.apply_controller_action(root, "write_terminal_summary", {**good, "source_paths_reviewed": ["outside.json"]})

        with self.assertRaisesRegex(router.RouterError, "displayed_to_user=true"):
            router.apply_controller_action(root, "write_terminal_summary", {**good, "displayed_to_user": False})

        self.apply_terminal_summary(root, action, run_root, note="User asked to stop.")
    def test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [
                    {"node_id": "node-001", "title": "First node"},
                    {"node_id": "node-002", "title": "Second node"},
                ],
                **self.prior_path_context_review(root, "Two-node route draft considered current route memory."),
            },
        )
        self.complete_route_checks(root)
        self.activate_route(root)

        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-nonterminal")

        display_plan = read_json(run_root / "display_plan.json")
        statuses = {item["id"]: item["status"] for item in display_plan["items"]}
        self.assertEqual(statuses["node-001"], "completed")
        self.assertEqual(statuses["node-002"], "in_progress")
        self.assertEqual(list(statuses.values()).count("in_progress"), 1)
    def test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-preconditions")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_final_route_wide_ledger_clean",
                {
                    "pm_owned": True,
                    "entries": [
                        {
                            "entry_id": "route-001:node-001",
                            "node_id": "node-001",
                            "gate_family": "human_review",
                            "required_approver": "human_like_reviewer",
                            "status": "approved",
                            "evidence_paths": [".flowpilot/current-node-result"],
                        }
                    ],
                },
            )
    def test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-segments")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        self.deliver_expected_card(root, "reviewer.final_backward_replay")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_final_backward_replay_passed",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            )
    def test_final_ledger_records_frozen_contract_replay_source_paths(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-sources")
        self.complete_evidence_quality_package(root)
        router.record_external_event(
            root,
            "role_records_gate_decision",
            self.role_decision_envelope(
                root,
                "gate_decisions/final_quality_gate",
                self.gate_decision_body(root, gate_id="final-quality-gate"),
            ),
        )
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

        ledger = read_json(run_root / "final_route_wide_gate_ledger.json")
        self.assertEqual(ledger["root_contract_replay"][0]["requirement_id"], "root-001")
        self.assertIn(self.rel(root, run_root / "root_acceptance_contract.json"), ledger["root_contract_replay"][0]["evidence_paths"])
        self.assertEqual(ledger["source_paths"]["root_acceptance_contract"], self.rel(root, run_root / "root_acceptance_contract.json"))
        gate_families = {entry["gate_family"] for entry in ledger["entries"]}
        self.assertIn("root_acceptance", gate_families)
        self.assertIn("route_node", gate_families)
        self.assertIn("child_skill_gate", gate_families)
        self.assertIn("evidence_integrity", gate_families)
        self.assertIn("material_artifact_map", gate_families)
        self.assertEqual(ledger["source_paths"]["material_artifact_map"], self.rel(root, run_root / "material" / "material_artifact_map.json"))
        self.assertTrue(ledger["evidence_integrity"]["material_artifact_map_body_text_excluded"])
        self.assertEqual(ledger["counts"]["material_artifact_map_blocked_count"], 0)
        self.assertEqual(ledger["counts"]["material_artifact_map_stale_count"], 0)
        self.assertEqual(ledger["counts"]["material_artifact_map_unresolved_count"], 0)
        self.assertEqual(ledger["counts"]["gate_decision_count"], 1)
        self.assertEqual(ledger["gate_decisions"][0]["gate_id"], "final-quality-gate")
        self.assertEqual(ledger["source_paths"]["gate_decision_ledger"], self.rel(root, run_root / "gate_decisions" / "gate_decision_ledger.json"))
        self.assertEqual(ledger["source_paths"]["self_interrogation_index"], self.rel(root, run_root / "self_interrogation_index.json"))
        self.assertTrue(ledger["evidence_integrity"]["self_interrogation_index_clean"])
        self.assertGreaterEqual(ledger["counts"]["self_interrogation_record_count"], 3)
        self.assertEqual(ledger["counts"]["self_interrogation_unresolved_hard_finding_count"], 0)
        self.assertTrue(ledger["terminal_closure_reconciliation"]["clean"])
        self.assertEqual(ledger["counts"]["defect_blocker_open_count"], 0)
        self.assertEqual(ledger["counts"]["defect_fixed_pending_recheck_count"], 0)
        self.assertEqual(ledger["counts"]["imported_artifact_authority_count"], 0)
        self.assertIn("terminal_closure_reconciliation", {entry["gate_family"] for entry in ledger["entries"]})
    def test_final_ledger_rejects_dirty_self_interrogation_index(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-self-interrogation-ledger")
        self.complete_evidence_quality_package(root)
        run_root = self.run_root_for(root)
        self.write_self_interrogation_record(
            root,
            "node_entry",
            clean=False,
            node_id="node-001",
            source_path=run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json",
        )

        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaisesRegex(router.RouterError, "final route-wide ledger requires clean self-interrogation records"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
    def test_final_ledger_rejects_dirty_pm_suggestion_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-suggestion-ledger")
        self.complete_evidence_quality_package(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaisesRegex(router.RouterError, "clean PM suggestion ledger"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
    def test_reconcile_recovers_legacy_terminal_closure_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-legacy-terminal-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
        router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                "closure/pm_legacy_terminal_closure_decision",
                {
                    "approved_by_role": "project_manager",
                    "decision": "approve_terminal_closure",
                    **self.prior_path_context_review(root, "Terminal closure considered clean final ledger and current route memory."),
                    "final_report": {"status": "complete"},
                },
            ),
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["status"] = "active"
        state["phase"] = "route_execution"
        state["flags"].pop("terminal_closure_approved", None)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="router_no_legal_next_action",
            error_message="Controller has no legal next action after legacy terminal closure.",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (run_root / "lifecycle" / "run_lifecycle.json").unlink()

        result = router.reconcile_current_run(root)
        self.assertTrue(result["repaired"]["terminal_closure_status_recovered"])
        self.assertTrue(result["repaired"]["terminal_lifecycle"])
        self.assertTrue(result["repaired"]["terminal_lifecycle_record_written"])
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")
        self.assertEqual(lifecycle["request_event"], "reconcile_current_run")
        state = read_json(state_path)
        self.assertEqual(state["status"], "closed")
        self.assertIsNone(state["active_control_blocker"])
        blocker_record = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(blocker_record["resolution_status"], "superseded_by_terminal_lifecycle")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "closed")
        self.apply_terminal_summary(root, action, run_root, note="Reconciled legacy terminal closure.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "closed")
