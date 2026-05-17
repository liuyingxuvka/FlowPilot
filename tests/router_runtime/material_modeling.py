from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class MaterialModelingRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_pm_material_understanding_accepts_file_backed_memo_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.complete_material_flow(
            root,
            self.role_output_envelope(
                root,
                "pm/material_understanding",
                {
                    "material_summary": "file backed material understanding",
                    "route_consequences": ["continue route construction"],
                },
                path_key="memo_path",
                hash_key="memo_hash",
            ),
        )

        memo = read_json(run_root / "pm_material_understanding.json")
        self.assertEqual(memo["material_summary"], "file backed material understanding")
        self.assertEqual(memo["route_consequences"], ["continue route construction"])
        self.assertEqual(memo["_role_output_envelope"]["body_path_key"], "memo_path")
        self.assertTrue((run_root / "material" / "pm_material_understanding_payload.json").exists())
    def test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_scan")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_results_returned")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_sufficient")
        self.absorb_material_scan_results_with_pm(root, material_index_path)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.material_sufficiency")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_insufficient")
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                    "blockers": ["missing authoritative source"],
                },
            ),
        )

        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_research_requested"])
    def test_material_scan_results_event_requires_result_ledger_absorption(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")

        ledger_path = run_root / "packet_ledger.json"
        ledger = read_json(ledger_path)
        index = read_json(material_index_path)
        packet_id = index["packets"][0]["packet_id"]
        packet_record = next(record for record in ledger["packets"] if record.get("packet_id") == packet_id)
        packet_record["result_body_hash"] = "stale-result-hash"
        router.write_json(ledger_path, ledger)

        with self.assertRaisesRegex(router.RouterError, "packet_ledger_missing_result_absorption") as raised:
            router.record_external_event(root, "worker_scan_results_returned")
        blocker = raised.exception.control_blocker
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])
    def test_material_scan_direct_relay_blocks_body_hash_mismatch(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        envelope = read_json(root / material_index["packets"][0]["packet_envelope_path"])
        body_path = root / envelope["body_path"]
        body_path.write_text(body_path.read_text(encoding="utf-8") + "\nTampered after packet creation.\n", encoding="utf-8")

        with self.assertRaisesRegex(router.RouterError, "body_hash_mismatch"):
            self.apply_next_packet_action(root, "relay_material_scan_packets")
    def test_material_scan_direct_relay_blocks_missing_output_contract(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        envelope_path = root / material_index["packets"][0]["packet_envelope_path"]
        envelope = read_json(envelope_path)
        envelope.pop("output_contract", None)
        envelope.pop("output_contract_id", None)
        router.write_json(envelope_path, envelope)

        with self.assertRaisesRegex(router.RouterError, "missing_output_contract"):
            self.apply_next_packet_action(root, "relay_material_scan_packets")
    def test_research_required_blocks_product_architecture_until_absorbed(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="research needed")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)
        self.deliver_expected_card(root, "reviewer.material_sufficiency")
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_material_understanding")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_package")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_research_package", {})
        router.record_external_event(
            root,
            "pm_writes_research_package",
            {
                "decision_question": "which source is authoritative?",
                "allowed_source_types": [
                    "current_repository_files",
                    "bounded_local_read_only_experiments",
                ],
                "host_capability_decision": "local_sources_first",
                "worker_owner": "worker_a",
                "stop_conditions": ["Do not edit production code."],
            },
        )
        router.record_external_event(root, "research_capability_decision_recorded", {})
        research_package = read_json(run_root / "research" / "research_package.json")
        self.assertEqual(research_package["allowed_source_types"], ["current_repository_files", "bounded_local_read_only_experiments"])
        research_decision = read_json(run_root / "research" / "research_capability_decision.json")
        self.assertEqual(research_decision["allowed_sources"], research_package["allowed_source_types"])
        self.assertEqual(research_decision["stop_conditions"], ["Do not edit production code."])
        research_index = read_json(run_root / "research" / "research_packet.json")
        self.assertIn("packet_body_path", research_index)
        self.assertIn("packet_body_hash", research_index)
        self.assertIn("body_path", research_index["packets"][0])
        research_packet_body = (root / research_index["packet_body_path"]).read_text(encoding="utf-8")
        self.assertIn("current_repository_files", research_packet_body)
        self.assertIn("Do not edit production code.", research_packet_body)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "worker.research_report")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "worker_research_report_returned",
                {"completed_by_role": "worker_a", "answers_decision_question": True},
            )
        state_before_research_relay = read_json(router.run_state_path(run_root))
        ledger_checks_before_research = int(state_before_research_relay.get("ledger_checks", 0))
        ledger_requests_before_research = int(state_before_research_relay.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_research_packet")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_research_packet")
        research_index_path = run_root / "research" / "research_packet.json"
        research_packet_id = read_json(research_index_path)["packets"][0]["packet_id"]
        research_lease = self.active_holder_lease_for_packet(root, research_packet_id)
        self.assertEqual(research_lease["holder_role"], "worker_a")
        state_after_research_packet = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_research_packet["ledger_checks"], ledger_checks_before_research + 1)
        self.assertEqual(state_after_research_packet["ledger_check_requests"], ledger_requests_before_research + 1)
        self.assertFalse(state_after_research_packet.get("ledger_check_requested"))
        self.open_packets_and_write_results(root, research_index_path, result_text="research report result")
        router.record_external_event(
            root,
            "worker_research_report_returned",
            {"completed_by_role": "worker_a", "answers_decision_question": True},
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_research_result_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_research_result_to_pm")
        state_after_research_result = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_research_result["ledger_checks"], ledger_checks_before_research + 2)
        self.assertEqual(state_after_research_result["ledger_check_requests"], ledger_requests_before_research + 2)
        self.assertFalse(state_after_research_result.get("ledger_check_requested"))
        self.open_results_for_pm(root, research_index_path)
        router.record_external_event(
            root,
            "pm_records_research_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "PM absorbed research results for reviewer direct-source gate.",
            },
        )

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.research_direct_source_check")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_research_direct_source_check",
            self.role_report_envelope(
                root,
                "research/reviewer_direct_source_check",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_absorb_or_mutate")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_absorbs_reviewed_research")

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_understanding")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_writes_material_understanding", {"material_summary": "research absorbed"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["research_result_absorbed_by_pm"])
        self.assertTrue(state["flags"]["material_accepted_by_pm"])
        self.assertTrue((run_root / "pm_material_understanding.json").exists())
    def test_product_architecture_and_root_contract_gate_route_skeleton(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture", {"user_task_map": []})
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "ship FlowPilot"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "ship FlowPilot"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "complete FlowPilot route control"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )
        self.assertTrue((run_root / "product_function_architecture.json").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": [{"requirement_id": "root-001"}]})

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "product_officer_passes_product_architecture_modelability", {"passed": True})
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_accepts_product_behavior_model", self.product_behavior_model_decision_body())

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.write_self_interrogation_record(
            root,
            "product_architecture",
            source_path=run_root / "product_function_architecture.json",
        )

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.root_contract")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": []})
        router.record_external_event(
            root,
            "pm_writes_root_acceptance_contract",
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "priority": "must",
                        "proof_required": "mixed",
                    }
                ],
                "proof_matrix": [{"requirement_id": "root-001", "expected_final_replay": True}],
                "selected_scenario_ids": ["terminal_complete_state"],
            },
        )
        self.assertTrue((run_root / "root_acceptance_contract.json").exists())
        self.assertTrue((run_root / "standard_scenario_pack.json").exists())
        self.assertTrue((run_root / "contract.md").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.root_contract_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("product_officer_root_contract_card_delivered", False))
        self.assertFalse(state["flags"].get("root_contract_modelability_passed", False))
        self.assertFalse((run_root / "flowguard" / "root_contract_modelability.json").exists())

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})
        self.complete_child_skill_gates(root)

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior path context before activation."),
            },
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check",
                    self.route_process_pass_body(),
                ),
            )
        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route")
    def test_legacy_product_officer_model_report_does_not_close_modelability_gate(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "ship FlowPilot"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "ship FlowPilot"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "complete FlowPilot route control"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        self.assertEqual(action["gate_contract"]["gate_id"], "product_behavior_model")
        self.ack_system_card_action(root, action)
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["gate_contract"]["gate_id"], "product_behavior_model")
        self.assertIn("product_officer_passes_product_architecture_modelability", wait["allowed_external_events"])
        self.assertIn("product_officer_blocks_product_architecture_modelability", wait["allowed_external_events"])
        self.assertNotIn("product_officer_model_report", wait["allowed_external_events"])

        router.record_external_event(root, "product_officer_model_report", {"legacy_status": "received"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["legacy_product_officer_model_report_received"])
        self.assertFalse(state["flags"]["product_architecture_modelability_passed"])

        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertIn("product_officer_passes_product_architecture_modelability", wait["allowed_external_events"])
        self.assertNotIn("product_officer_model_report", wait["allowed_external_events"])

        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        action = self.deliver_expected_card(root, "pm.product_behavior_model_decision")
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")
    def test_process_route_model_canonical_event_writes_compatibility_alias(self) -> None:
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
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before process model."),
            },
        )

        action = self.deliver_expected_card(root, "process_officer.route_process_check")
        self.assertEqual(action["gate_contract"]["gate_id"], "process_route_model")
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["gate_contract"]["gate_id"], "process_route_model")
        self.assertIn("process_officer_submits_process_route_model", wait["allowed_external_events"])
        self.assertIn("process_officer_passes_route_check", wait["allowed_external_events"])

        router.record_external_event(
            root,
            "process_officer_submits_process_route_model",
            self.role_report_envelope(root, "flowguard/process_route_model", self.route_process_pass_body()),
        )
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["process_route_model_submitted"])
        self.assertTrue(state["flags"]["process_officer_route_check_passed"])
        self.assertTrue((run_root / "flowguard" / "process_route_model.json").exists())
        self.assertTrue((run_root / "flowguard" / "route_process_check.json").exists())

        action = self.deliver_expected_card(root, "pm.process_route_model_decision")
        self.assertEqual(action["card_id"], "pm.process_route_model_decision")
    def test_pm_repair_transaction_commits_material_reissue_generation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action after material dispatch repair request",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            decision="repair_completed",
            rerun_target="router_direct_material_scan_dispatch_recheck_passed",
        )
        decision["repair_transaction"] = {
            "plan_kind": "packet_reissue",
            "replacement_packets": [
                {
                    "packet_id": "material-scan-001-r1",
                    "replacement_for": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Reissued material scan packet with a committed repair generation.",
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/material_reissue_pm_repair_decision", decision),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(
            set(active["allowed_resolution_events"]),
            {
                "router_direct_material_scan_dispatch_recheck_passed",
                "router_direct_material_scan_dispatch_recheck_blocked",
                "router_protocol_blocker_material_scan_dispatch_recheck",
            },
        )
        transaction = read_json(root / active["repair_transaction_path"])
        self.assertEqual(transaction["plan_kind"], "packet_reissue")
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(transaction["generation_commit"]["packet_count"], 1)
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        self.assertEqual(material_index["current_generation_id"], transaction["packet_generation_id"])
        self.assertEqual(material_index["packets"][0]["packet_id"], "material-scan-001-r1")
        self.assertIn("result_body_path", material_index["packets"][0])
        self.assertEqual(
            material_index["packets"][0]["result_write_target"]["result_body_path"],
            material_index["packets"][0]["result_body_path"],
        )
        packet_envelope = read_json(root / material_index["packets"][0]["packet_envelope_path"])
        self.assertEqual(packet_envelope["result_body_path"], material_index["packets"][0]["result_body_path"])
        packet_body = (root / packet_envelope["body_path"]).read_text(encoding="utf-8")
        self.assertIn('"recipient_role": "worker_a"', packet_body)
        self.assertIn('"required_result_envelope_fields"', packet_body)
        self.assertTrue((run_root / "packets" / "material-scan-001-r1" / "packet_envelope.json").exists())
        ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(any(record.get("packet_id") == "material-scan-001-r1" for record in ledger["packets"]))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(set(action["allowed_external_events"]), set(active["allowed_resolution_events"]))
        router.record_external_event(root, "router_direct_material_scan_dispatch_recheck_passed")
        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["active_repair_transaction"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_blocked"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_protocol_blocked"])
        transaction = read_json(run_root / "control_blocks" / "repair_transactions" / f"{transaction['transaction_id']}.json")
        self.assertEqual(transaction["status"], "complete")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_packets")
    def test_material_scan_mechanical_agent_id_gap_reissues_to_worker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        material_index = read_json(material_index_path)
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=envelope["to_role"],
                result_body_text="material scan result with role-name agent id",
                next_recipient="project_manager",
            )
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(root, "worker_scan_results_returned")

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])
        self.assertIn("completed_agent_id_is_role_key_not_agent_id", str(raised.exception))
        self.assertTrue(self.handle_pending_control_blocker(root))
        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state["active_repair_transaction"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["to_role"], "worker_a")
        self.assertIn("worker_scan_results_returned", action["allowed_external_events"])

        material_index = read_json(material_index_path)
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"agent-fixed-{envelope['to_role']}",
                result_body_text="material scan result with corrected agent id",
                next_recipient="project_manager",
            )
        router.record_external_event(root, "worker_scan_results_returned")

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["worker_scan_results_returned"])
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["active_repair_transaction"])
        self.assertIsNone(state["pending_action"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_blocked"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_protocol_blocked"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")
    def test_material_insufficient_event_records_insufficient_state(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.apply_next_non_card_action(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)
        self.apply_next_non_card_action(root)
        self.deliver_expected_card(root, "reviewer.material_sufficiency")

        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
        )

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["material_review_insufficient"])
        self.assertEqual(state["material_review"], "insufficient")
