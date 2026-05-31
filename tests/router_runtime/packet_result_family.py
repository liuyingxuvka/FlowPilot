from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class PacketResultFamilyRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def _prepare_material_scan_batch(self, root: Path) -> tuple[Path, Path]:
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-family-worker-1",
                        "to_role": "worker",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-family-worker-2",
                        "to_role": "worker",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        return run_root, run_root / "material" / "material_scan_packets.json"

    def _prepare_research_batch(self, root: Path) -> tuple[Path, Path]:
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
                "material/reviewer_material_insufficient_for_family",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                    "checked_source_paths": self.material_review_source_paths(root),
                    "runtime_open_receipt_refs": [],
                },
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")
        self.apply_next_non_card_action(root)
        self.ack_system_card_action(root, router.next_action(root))
        router.record_external_event(
            root,
            "pm_writes_research_package",
            {
                "decision_question": "which source is authoritative?",
                "allowed_source_types": ["current_repository_files"],
                "host_capability_decision": "local_sources_first",
                "worker_owner": "worker",
                "batch_id": "research-family-batch-001",
                "packets": [
                    {"packet_id": "research-family-worker-1", "to_role": "worker"},
                    {"packet_id": "research-family-worker-2", "to_role": "worker"},
                ],
                "stop_conditions": ["Do not edit production code."],
            },
        )
        router.record_external_event(root, "research_capability_decision_recorded", {})
        self.apply_next_non_card_action(root)
        self.ack_system_card_action(root, router.next_action(root))
        self.apply_next_packet_action(root, "relay_research_packet")
        return run_root, run_root / "research" / "research_packet.json"

    def _prepare_current_node_batch(self, root: Path) -> tuple[Path, dict[str, str]]:
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet_paths: dict[str, str] = {}
        for packet_id, role in (("family-node-worker-1", "worker"), ("family-node-worker-2", "worker")):
            packet = packet_runtime.create_packet(
                root,
                packet_id=packet_id,
                from_role="project_manager",
                to_role=role,
                node_id="node-001",
                body_text=f"current node work for {role}",
                metadata={"route_version": 1},
            )
            packet_paths[packet_id] = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {
                "batch_id": "current-node-family-batch-001",
                "packets": [
                    {"packet_id": packet_id, "packet_envelope_path": packet_path}
                    for packet_id, packet_path in packet_paths.items()
                ],
            },
        )
        self.apply_until_action(root, "relay_current_node_packet")
        return run_root, packet_paths

    def _prepare_pm_role_work_batch(self, root: Path) -> tuple[Path, list[str]]:
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-family-role-work")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/family_model_miss_role_work_batch",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        request_ids = ["family-product-001", "family-process-001"]
        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            {
                "requested_by_role": "project_manager",
                "batch_id": "pm-role-work-family-batch-001",
                "requests": [
                    self.pm_role_work_request_payload(root, request_id=request_ids[0], to_role="flowguard_operator"),
                    self.pm_role_work_request_payload(root, request_id=request_ids[1], to_role="flowguard_operator"),
                ],
            },
        )
        self.apply_until_action(root, "relay_pm_role_work_request_packet")
        return run_root, request_ids

    def test_material_scan_wrong_recipient_envelope_is_not_counted_as_family_result(self) -> None:
        root = self.make_project()
        run_root, material_index_path = self._prepare_material_scan_batch(root)
        index = read_json(material_index_path)
        first = index["packets"][0]
        second = index["packets"][1]
        for record, next_recipient in ((first, "human_like_reviewer"), (second, "project_manager")):
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"{envelope['to_role']}-agent",
                result_body_text=f"{record['packet_id']} result\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient=next_recipient,
            )

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["worker_scan_results_returned"])
        self.assertEqual(action["to_role"], "worker")
        batch_ref = read_json(run_root / "packet_batches" / "active_material_scan.json")
        batch = read_json(root / batch_ref["batch_path"])
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["invalid_result_roles"], ["worker"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("worker_scan_results_returned"))

    def test_research_full_batch_reconciles_from_durable_results_without_manual_event(self) -> None:
        root = self.make_project()
        run_root, research_index_path = self._prepare_research_batch(root)
        self.open_packets_and_write_results(root, research_index_path, result_text="research family result")

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_research_result_to_pm")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["worker_research_report_returned"])
        self.assertTrue((run_root / "research" / "worker_research_report.json").exists())
        event = next(item for item in state["events"] if item.get("event") == "worker_research_report_returned")
        self.assertTrue(event["payload"]["reconciled_from_result_envelopes"])
        self.assertEqual(sorted(event["payload"]["packet_ids"]), ["research-family-worker-1", "research-family-worker-2"])

    def test_research_partial_batch_waits_only_for_missing_durable_result_member(self) -> None:
        root = self.make_project()
        run_root, research_index_path = self._prepare_research_batch(root)
        index = read_json(research_index_path)
        first = index["packets"][0]
        envelope = packet_runtime.load_envelope(root, first["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
        packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=envelope["to_role"],
            completed_by_agent_id=f"{envelope['to_role']}-agent",
            result_body_text="research worker a result\n\nContract Self-Check\n\nstatus: pass\n",
            next_recipient="project_manager",
        )

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["worker_research_report_returned"])
        self.assertEqual(action["to_role"], "worker")
        batch = read_json(run_root / "packet_batches" / "research-family-batch-001.json")
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker"])

    def test_current_node_mixed_manual_and_durable_members_records_remaining_event(self) -> None:
        root = self.make_project()
        run_root, _packet_paths = self._prepare_current_node_batch(root)
        _agent_a, result_a_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="family-node-worker-1",
            result_body_text="worker a result",
        )
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "family-node-worker-1", "result_envelope_path": result_a_path},
        )
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["to_role"], "worker")
        self.submit_current_node_result_via_active_holder(
            root,
            packet_id="family-node-worker-2",
            result_body_text="worker b result",
        )

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        state = read_json(router.run_state_path(run_root))
        returned_packets = sorted(
            item.get("payload", {}).get("packet_id")
            for item in state["events"]
            if item.get("event") == "worker_current_node_result_returned"
        )
        self.assertEqual(returned_packets, ["family-node-worker-1", "family-node-worker-2"])

    def test_current_node_full_batch_reconciles_from_durable_results_without_manual_events(self) -> None:
        root = self.make_project()
        run_root, packet_paths = self._prepare_current_node_batch(root)
        for packet_id in packet_paths:
            self.submit_current_node_result_via_active_holder(
                root,
                packet_id=packet_id,
                result_body_text=f"{packet_id} result",
            )

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        state = read_json(router.run_state_path(run_root))
        returned_packets = sorted(
            item.get("payload", {}).get("packet_id")
            for item in state["events"]
            if item.get("event") == "worker_current_node_result_returned"
        )
        self.assertEqual(returned_packets, sorted(packet_paths))

    def test_current_node_wrong_recipient_envelope_is_not_counted_as_family_result(self) -> None:
        root = self.make_project()
        run_root, packet_paths = self._prepare_current_node_batch(root)
        for packet_id, next_recipient in (
            ("family-node-worker-1", "human_like_reviewer"),
            ("family-node-worker-2", "project_manager"),
        ):
            lease = self.active_holder_lease_for_packet(root, packet_id)
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role=lease["holder_role"],
                agent_id=lease["holder_agent_id"],
                route_version=lease["route_version"],
                frontier_version=lease["frontier_version"],
            )
            envelope = read_json(root / packet_paths[packet_id])
            packet_runtime.read_packet_body_for_role(root, envelope, role=lease["holder_role"])
            submission = packet_runtime.active_holder_submit_result(
                root,
                lease_path=lease["lease_path"],
                role=lease["holder_role"],
                agent_id=lease["holder_agent_id"],
                result_body_text=f"{packet_id} result\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient=next_recipient,
                route_version=lease["route_version"],
                frontier_version=lease["frontier_version"],
            )
            self.assertTrue(submission["passed"])

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["to_role"], "worker")
        batch = read_json(run_root / "packet_batches" / "current-node-family-batch-001.json")
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["invalid_result_roles"], ["worker"])

    def test_pm_role_work_full_batch_reconciles_from_durable_results_without_manual_events(self) -> None:
        root = self.make_project()
        run_root, request_ids = self._prepare_pm_role_work_batch(root)
        for request_id in request_ids:
            self.open_role_work_packet_and_write_result(root, request_id=request_id)

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        state = read_json(router.run_state_path(run_root))
        returned_requests = sorted(
            item.get("payload", {}).get("request_id")
            for item in state["events"]
            if item.get("event") == "role_work_result_returned"
        )
        self.assertEqual(returned_requests, sorted(request_ids))

    def test_pm_role_work_partial_batch_waits_only_for_missing_member(self) -> None:
        root = self.make_project()
        _run_root, request_ids = self._prepare_pm_role_work_batch(root)
        self.open_role_work_packet_and_write_result(root, request_id=request_ids[0])

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["role_work_result_returned"])
        self.assertIn("flowguard_operator", action["to_role"])
        self.assertNotIn("flowguard_operator", action["to_role"])

    def test_wrong_recipient_envelope_is_not_counted_as_family_result(self) -> None:
        root = self.make_project()
        run_root, research_index_path = self._prepare_research_batch(root)
        index = read_json(research_index_path)
        first = index["packets"][0]
        second = index["packets"][1]
        for record, next_recipient in ((first, "human_like_reviewer"), (second, "project_manager")):
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"{envelope['to_role']}-agent",
                result_body_text=f"{record['packet_id']} result\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient=next_recipient,
            )

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["to_role"], "worker")
        batch = read_json(run_root / "packet_batches" / "research-family-batch-001.json")
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker"])
        self.assertEqual(batch["member_status"]["invalid_result_roles"], ["worker"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("worker_research_report_returned"))
