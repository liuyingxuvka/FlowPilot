from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
import flowpilot_material_artifact_map as material_artifact_map  # noqa: E402
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
        self.assertFalse(continuation["manual_resume_binding_active"])
        self.assertNotIn("heartbeat_active", continuation)
        self.assertNotIn("host_automation_cleanup_status", continuation)
        role_binding_path = run_root / "role_binding_ledger.json"
        if role_binding_path.exists():
            role_binding = read_json(role_binding_path)
            self.assertTrue(all(slot["status"] == "stopped_with_run" for slot in role_binding["role_slots"]))
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
        transaction_id = "repair-tx-terminal-quarantine"
        transaction_path = run_root / "control_blocks" / "repair_transactions" / f"{transaction_id}.json"
        transaction_path.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            transaction_path,
            {
                "schema_version": router.REPAIR_TRANSACTION_SCHEMA,
                "transaction_id": transaction_id,
                "blocker_id": "control-blocker-terminal-quarantine",
                "status": "opened",
                "plan_kind": "same_node_repair",
                "packet_generation_id": "packet-generation-terminal-quarantine",
            },
        )
        state["active_repair_transaction"] = {
            "transaction_id": transaction_id,
            "blocker_id": "control-blocker-terminal-quarantine",
            "status": "opened",
            "path": self.rel(root, transaction_path),
        }
        packet_ledger_path = run_root / "packet_ledger.json"
        packet_ledger = read_json(packet_ledger_path)
        packet_ledger["active_packet_id"] = "packet-terminal-quarantine"
        packet_ledger["active_packet_status"] = "worker-result-returned"
        packet_ledger["active_packet_holder"] = "router"
        packet_ledger.setdefault("packets", []).append(
            {
                "packet_id": "packet-terminal-quarantine",
                "active_packet_status": "worker-result-returned",
                "result_envelope": {
                    "result_id": "result-terminal-quarantine",
                    "completed_by_role": "worker",
                },
            }
        )
        router.write_json(packet_ledger_path, packet_ledger)
        router.save_run_state(run_root, state)

        result = router.record_external_event(root, "user_requests_run_stop", {"reason": "stop during repair"})

        self.assertTrue(result["ok"])
        state_after = read_json(state_path)
        self.assertIsNone(state_after["active_repair_transaction"])
        transaction_after = read_json(transaction_path)
        self.assertEqual(transaction_after["status"], "superseded_by_terminal_lifecycle")
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        receipt_authorities = {
            item.get("authority")
            for item in lifecycle["cleanup_receipts"]
            if isinstance(item, dict) and item.get("authority")
        }
        self.assertIn("repair_transaction", receipt_authorities)
        self.assertIn("packet_result_author_identity", receipt_authorities)
        packet_ledger_after = read_json(packet_ledger_path)
        packet = next(item for item in packet_ledger_after["packets"] if item["packet_id"] == "packet-terminal-quarantine")
        self.assertEqual(
            packet["result_envelope"]["author_identity_quarantine"]["status"],
            "terminal_lifecycle_quarantined",
        )
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
    def test_terminal_pending_legacy_heartbeat_action_is_rejected(self) -> None:
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

        with self.assertRaisesRegex(router.RouterError, "unknown controller action: create_heartbeat_automation"):
            router.apply_action(root, "create_heartbeat_automation", self.unsupported_heartbeat_binding_payload(root))
        binding_after = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertEqual(binding_after, binding_before)
    def test_reconcile_run_recovers_terminal_status_from_current_pointer(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-terminal-drift", status="startup_bootstrap")
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
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
        self.complete_startup_runtime_entry(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.complete_implementation_intent_bridge(root)
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
    def test_final_ledger_requires_pm_accepted_terminal_flowguard_coverage(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-flowguard-required")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        payload = self.final_ledger_payload(root)
        payload.pop("flowguard_terminal_coverage_closure")

        with self.assertRaisesRegex(router.RouterError, "flowguard_terminal_coverage_closure"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", payload)
    def test_final_ledger_rejects_progress_only_terminal_flowguard_report(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-flowguard-progress")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        payload = self.final_ledger_payload(
            root,
            flowguard_report_overrides={
                "progress_only": True,
                "contract_self_check": {
                    "all_required_fields_present": True,
                    "no_progress_only_claim": False,
                    "no_unresolved_blockers": True,
                    "pm_acceptance_required": True,
                },
            },
        )

        with self.assertRaisesRegex(router.RouterError, "progress-only|no_progress_only_claim"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", payload)
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
        self.assertNotIn("material_artifact_map", gate_families)
        self.assertNotIn("material_artifact_map", ledger["source_paths"])
        self.assertFalse(ledger["gate_families"]["material_artifact_map_linked"])
        self.assertTrue(ledger["evidence_integrity"]["material_artifact_map_checked_if_present"])
        self.assertIsNone(ledger["evidence_integrity"]["material_artifact_map_navigation_usable"])
        self.assertIsNone(ledger["evidence_integrity"]["material_artifact_map_body_text_excluded"])
        self.assertEqual(ledger["counts"]["material_artifact_map_blocked_count"], 0)
        self.assertEqual(ledger["counts"]["material_artifact_map_stale_count"], 0)
        self.assertEqual(ledger["counts"]["material_artifact_map_unresolved_count"], 0)
        self.assertFalse(ledger["material_artifact_map_summary"]["present"])
        self.assertFalse(material_artifact_map.material_artifact_map_path(run_root).exists())
        history = read_json(router._route_history_index_path(run_root))
        prior_context = read_json(router._pm_prior_path_context_path(run_root))
        self.assertNotIn("material_artifact_map", history)
        self.assertIsNone(prior_context["material_artifact_map_considered"])
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
        self.assertIn("flowguard_terminal_coverage", {entry["gate_family"] for entry in ledger["entries"]})
        self.assertEqual(ledger["flowguard_terminal_coverage_closure"]["segment_id"], "flowguard-coverage-governance")
        self.assertTrue(ledger["evidence_integrity"]["flowguard_terminal_coverage_report_current"])
        terminal_map = read_json(run_root / "terminal_human_backward_replay_map.json")
        self.assertIn("flowguard-coverage-governance", {segment["segment_id"] for segment in terminal_map["segments"]})
        self.assertIn("flowguard_coverage_governance", terminal_map["replay_order"])

    def test_final_ledger_links_explicit_existing_optional_map_without_using_it_as_acceptance_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-map-present")
        self.complete_evidence_quality_package(root)

        map_doc = material_artifact_map.refresh_material_artifact_map(
            root,
            run_root,
            read_json(router.run_state_path(run_root)),
            create_if_missing=True,
        )
        self.assertTrue(map_doc["body_text_excluded"])
        router._refresh_route_memory(
            root,
            run_root,
            read_json(router.run_state_path(run_root)),
            trigger="explicit_optional_map_requested",
        )
        history = read_json(router._route_history_index_path(run_root))
        prior_context = read_json(router._pm_prior_path_context_path(run_root))
        self.assertTrue(history["material_artifact_map"]["navigation_usable"])
        self.assertFalse(history["material_artifact_map"]["acceptance_evidence"])
        self.assertEqual(
            prior_context["material_artifact_map_considered"]["path"],
            self.rel(root, material_artifact_map.material_artifact_map_path(run_root)),
        )

        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        ledger = read_json(run_root / "final_route_wide_gate_ledger.json")
        map_path = material_artifact_map.material_artifact_map_path(run_root)

        self.assertTrue(map_path.exists())
        self.assertTrue(ledger["gate_families"]["material_artifact_map_linked"])
        self.assertEqual(ledger["source_paths"]["material_artifact_map"], self.rel(root, map_path))
        self.assertTrue(ledger["evidence_integrity"]["material_artifact_map_navigation_usable"])
        self.assertTrue(ledger["evidence_integrity"]["material_artifact_map_body_text_excluded"])
        self.assertTrue(ledger["material_artifact_map_summary"]["present"])
        self.assertFalse(ledger["material_artifact_map_summary"]["acceptance_evidence"])
        map_entry = next(entry for entry in ledger["entries"] if entry["entry_id"] == "material_artifact_map:index")
        self.assertEqual(map_entry["status"], "indexed")
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
    def test_reconcile_recovers_prior_terminal_closure_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-prior-terminal-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
        router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                "closure/pm_prior_terminal_closure_decision",
                self.pm_terminal_closure_body(root),
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
            error_message="Controller has no legal next action after prior terminal closure.",
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
        self.apply_terminal_summary(root, action, run_root, note="Reconciled prior terminal closure.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "closed")
