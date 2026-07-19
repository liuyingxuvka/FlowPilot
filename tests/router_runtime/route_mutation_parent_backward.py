from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
import flowpilot_router_route


class RouteMutationParentBackwardRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_route_mutation_rejects_unvalidated_authority_dict(self) -> None:
            root = self.make_project()
            run_root = self.boot_to_controller(root)
            state = read_json(router.run_state_path(run_root))

            with self.assertRaisesRegex(
                router.RouterError,
                "validated_authority must be the current in-memory authority",
            ):
                flowpilot_router_route.write_route_mutation(
                    router,
                    root,
                    run_root,
                    state,
                    {},
                    validated_authority={},
                )

    def _activate_parent_with_completed_child(self, root: Path) -> Path:
            run_root = self.boot_to_controller(root)
            self.complete_pre_route_gates(root)
            router.record_external_event(
                root,
                "pm_activates_reviewed_route",
                {
                    "route_id": "route-001",
                    "active_node_id": "parent-001",
                    "route_version": 1,
                    "route": {
                        "schema_version": "flowpilot.route.v1",
                        "route_id": "route-001",
                        "route_version": 1,
                        "active_node_id": "parent-001",
                        "nodes": [
                            {
                                "node_id": "parent-001",
                                "status": "active",
                                "title": "Parent node",
                                "child_node_ids": ["child-001"],
                            },
                            {"node_id": "child-001", "status": "completed", "title": "Child node"},
                        ],
                    },
                },
            )
            self.seed_child_completion_ledger(root, "child-001")
            self.deliver_current_node_cards(root)
            return run_root

    def _prepare_parent_segment_decision_wait(self, root: Path) -> Path:
            run_root = self._activate_parent_with_completed_child(root)
            self.deliver_expected_card(root, "pm.parent_backward_targets")
            router.record_external_event(root, "pm_builds_parent_backward_targets")
            self.deliver_expected_card(root, "reviewer.parent_backward_replay")
            router.record_external_event(
                root,
                "reviewer_passes_parent_backward_replay",
                self.role_report_envelope(
                    root,
                    "reviews/parent_backward_replay_route_authority",
                    {"reviewed_by_role": "human_like_reviewer", "passed": True},
                ),
            )
            self.deliver_expected_card(root, "pm.parent_segment_decision")
            wait_action = router.next_action(root)
            self.assertEqual(wait_action["action_type"], "await_role_decision")
            self.assertIn("pm_records_parent_segment_decision", wait_action["allowed_external_events"])
            self.assertIn("record_parent_segment_decision", wait_action["legal_next_actions"]["legal_action_ids"])
            self.assertEqual(wait_action["legal_next_actions"]["current_owner"], "project_manager")
            self.assertEqual(wait_action["legal_next_actions"]["required_repair_command"], "submit_pm_parent_segment_decision")
            return run_root

    def _assert_route_authority_blocker(
        self,
        root: Path,
        error: router.RouterError,
        *,
        rejected_action_id: str,
        rejection_kind: str,
        legal_action_id: str,
        current_owner: str = "project_manager",
    ) -> dict:
            blocker = error.control_blocker
            self.assertIsInstance(blocker, dict)
            self.assertEqual(blocker["source"], "router_route_authority_rejected")
            rejection = blocker["route_authority_rejection"]
            self.assertEqual(rejection["rejection_kind"], rejection_kind)
            self.assertEqual(rejection["rejected_action_id"], rejected_action_id)
            self.assertIn(legal_action_id, rejection["legal_action_ids"])
            self.assertEqual(rejection["current_owner"], current_owner)
            self.assertTrue(rejection["required_repair_command"])
            saved = read_json(self.control_blocker_path(root, blocker))
            self.assertEqual(saved["route_authority_rejection"]["rejection_kind"], rejection_kind)
            state = read_json(router.run_state_path(self.run_root_for(root)))
            self.assertEqual(state["active_control_blocker"]["route_authority_rejection"]["rejected_action_id"], rejected_action_id)
            return saved

    def test_parent_backward_targets_require_current_child_completion_ledgers(self) -> None:
            root = self.make_project()
            self.boot_to_controller(root)
            self.complete_pre_route_gates(root)
            router.record_external_event(
                root,
                "pm_activates_reviewed_route",
                {
                    "route_id": "route-001",
                    "active_node_id": "parent-001",
                    "route_version": 1,
                    "route": {
                        "schema_version": "flowpilot.route.v1",
                        "route_id": "route-001",
                        "route_version": 1,
                        "active_node_id": "parent-001",
                        "nodes": [
                            {
                                "node_id": "parent-001",
                                "status": "active",
                                "title": "Parent node",
                                "child_node_ids": ["child-001"],
                            },
                            {"node_id": "child-001", "status": "completed", "title": "Child node"},
                        ],
                    },
                },
            )
            self.deliver_current_node_cards(root)
            state_path = router.run_state_path(self.run_root_for(root))
            state = read_json(state_path)
            state["flags"]["pm_parent_backward_targets_card_delivered"] = True
            router.save_run_state(self.run_root_for(root), state)
            with self.assertRaisesRegex(router.RouterError, "rejected by route authority") as raised:
                router.record_external_event(root, "pm_builds_parent_backward_targets")
            self._assert_route_authority_blocker(
                root,
                raised.exception,
                rejected_action_id="build_parent_backward_targets",
                rejection_kind="wrong_path",
                legal_action_id="enter_next_child",
                current_owner="router",
            )

    def test_parent_completion_wrong_path_returns_route_authority_repair_feedback(self) -> None:
            root = self.make_project()
            self._prepare_parent_segment_decision_wait(root)

            with self.assertRaisesRegex(router.RouterError, "rejected by route authority") as raised:
                router.record_external_event(root, "pm_completes_parent_node_from_backward_replay")

            saved = self._assert_route_authority_blocker(
                root,
                raised.exception,
                rejected_action_id="complete_parent_node",
                rejection_kind="wrong_path",
                legal_action_id="record_parent_segment_decision",
            )
            rejection = saved["route_authority_rejection"]
            self.assertIn("complete_parent_node", rejection["forbidden_action_ids"])
            self.assertEqual(rejection["required_repair_command"], "submit_pm_parent_segment_decision")

    def test_unsupported_route_action_alias_is_rejected_without_translation(self) -> None:
            root = self.make_project()
            self._prepare_parent_segment_decision_wait(root)

            with self.assertRaisesRegex(router.RouterError, "rejected by route authority") as raised:
                router.record_external_event(root, "pm_records_parent_completion")

            self._assert_route_authority_blocker(
                root,
                raised.exception,
                rejected_action_id="complete_parent_node",
                rejection_kind="unsupported_event_alias",
                legal_action_id="record_parent_segment_decision",
            )

    def test_fallback_route_action_payload_is_rejected_without_translation(self) -> None:
            root = self.make_project()
            self._prepare_parent_segment_decision_wait(root)

            with self.assertRaisesRegex(router.RouterError, "rejected by route authority") as raised:
                router.record_external_event(
                    root,
                    "pm_records_parent_segment_decision",
                    {"fallback_route_action": "complete_parent_node", "selected_path_text": "just close the parent"},
                )

            saved = self._assert_route_authority_blocker(
                root,
                raised.exception,
                rejected_action_id="record_parent_segment_decision",
                rejection_kind="unsupported_payload_shape",
                legal_action_id="record_parent_segment_decision",
            )
            self.assertEqual(
                saved["route_authority_rejection"]["unsupported_payload_fields"],
                ["fallback_route_action", "selected_path_text"],
            )


    def test_parent_node_requires_backward_replay_before_completion(self) -> None:
            root = self.make_project()
            run_root = self.boot_to_controller(root)
            self.complete_pre_route_gates(root)
            router.record_external_event(
                root,
                "pm_activates_reviewed_route",
                {
                    "route_id": "route-001",
                    "active_node_id": "parent-001",
                    "route_version": 1,
                    "route": {
                        "schema_version": "flowpilot.route.v1",
                        "route_id": "route-001",
                        "route_version": 1,
                        "active_node_id": "parent-001",
                        "nodes": [
                            {
                                "node_id": "parent-001",
                                "status": "active",
                                "title": "Parent node",
                                "child_node_ids": ["child-001"],
                            },
                            {"node_id": "child-001", "status": "completed", "title": "Child node"},
                        ],
                    },
                },
            )
            self.seed_child_completion_ledger(root, "child-001")
            self.deliver_current_node_cards(root)
            packet = packet_runtime.create_packet(
                root,
                packet_id="parent-node-packet",
                from_role="project_manager",
                to_role="worker",
                node_id="parent-001",
                body_text="parent node work",
                metadata={"route_version": 1},
            )
            packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
            with self.assertRaises(router.RouterError):
                router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "parent-node-packet", "packet_envelope_path": packet_path})

            self.complete_parent_backward_replay_if_due(root)
            router.record_external_event(root, "pm_completes_parent_node_from_backward_replay")
            frontier = read_json(run_root / "execution_frontier.json")
            self.assertIn("parent-001", frontier["completed_nodes"])
            self.assertTrue((run_root / "routes" / "route-001" / "nodes" / "parent-001" / "parent_backward_replay.json").exists())


    def test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun(self) -> None:
            root = self.make_project()
            run_root = self.boot_to_controller(root)
            self.complete_pre_route_gates(root)
            router.record_external_event(
                root,
                "pm_activates_reviewed_route",
                {
                    "route_id": "route-001",
                    "active_node_id": "parent-001",
                    "route_version": 1,
                    "route": {
                        "schema_version": "flowpilot.route.v1",
                        "route_id": "route-001",
                        "route_version": 1,
                        "active_node_id": "parent-001",
                        "nodes": [
                            {
                                "node_id": "parent-001",
                                "status": "active",
                                "title": "Parent node",
                                "child_node_ids": ["child-001"],
                            },
                            {"node_id": "child-001", "status": "completed", "title": "Child node"},
                        ],
                    },
                },
            )
            self.seed_child_completion_ledger(root, "child-001")
            self.deliver_current_node_cards(root)
            self.deliver_expected_card(root, "pm.parent_backward_targets")
            router.record_external_event(root, "pm_builds_parent_backward_targets")
            self.deliver_expected_card(root, "reviewer.parent_backward_replay")
            router.record_external_event(
                root,
                "reviewer_passes_parent_backward_replay",
                self.role_report_envelope(
                    root,
                    "reviews/parent_backward_replay_noncontinue",
                    {"reviewed_by_role": "human_like_reviewer", "passed": True},
                ),
            )
            self.deliver_expected_card(root, "pm.parent_segment_decision")
            router.record_external_event(
                root,
                "pm_records_parent_segment_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/parent_segment_repair_decision",
                    {
                        "decision_owner": "project_manager",
                        "decision": "repair_existing_child",
                        "repair_return_to_node_id": "parent-001",
                        **self.prior_path_context_review(root, "Parent segment repair decision considered prior route memory and replay evidence."),
                    },
                ),
            )

            frontier = read_json(run_root / "execution_frontier.json")
            self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
            self.assertEqual(frontier["active_node_id"], "parent-001")
            self.assertNotEqual(frontier["pending_route_mutation"]["candidate_node_id"], "parent-001")
            decision = read_json(run_root / "routes" / "route-001" / "nodes" / "parent-001" / "pm_parent_segment_decision.json")
            self.assertTrue(decision["same_parent_replay_rerun_required"])
