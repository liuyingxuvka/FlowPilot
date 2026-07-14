from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ControlBlockersRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_control_blocker_reviewer_followup_rejects_pm_origin(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "flowguard_operator",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")

        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action while reviewer gate result is waiting",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            decision="repair_completed",
            rerun_target="reviewer_passes_child_skill_gate_manifest",
        )
        decision["repair_transaction"] = {"plan_kind": "await_existing_event"}
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/pm_repair_to_reviewer_gate_followup",
                decision,
            ),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("reviewer_passes_child_skill_gate_manifest", action["allowed_external_events"])
        report = self.role_report_envelope(
            root,
            "reviews/child_skill_gate_manifest_review_pm_impersonation",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        pm_origin_envelope = {
            "schema_version": router.EVENT_ENVELOPE_SCHEMA,
            "event": "reviewer_passes_child_skill_gate_manifest",
            "from_role": "project_manager",
            "to_role": "controller",
            "controller_visibility": "event_envelope_only",
            **report,
        }
        with self.assertRaisesRegex(router.RouterError, "from_role mismatch"):
            router.record_external_event(root, "reviewer_passes_child_skill_gate_manifest", pm_origin_envelope)
    def test_control_plane_reissue_retry_budget_escalates_to_pm(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue-budget")

        blockers: list[dict] = []
        for attempt in range(3):
            with self.assertRaises(router.RouterError) as raised:
                router.record_external_event(
                    root,
                    "current_node_reviewer_passes_result",
                    self.role_report_envelope(
                        root,
                        f"reviews/current_node_result_missing_passed_budget_{attempt}",
                        {
                            "reviewed_by_role": "human_like_reviewer",
                            "agent_role_map": {"agent-worker-1": "worker"},
                        },
                    ),
                )
            blocker = raised.exception.control_blocker
            self.assertIsInstance(blocker, dict)
            blockers.append(blocker)
            if attempt < 2:
                self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
                self.assertEqual(blocker["target_role"], "human_like_reviewer")
                self.assertEqual(blocker["direct_retry_attempts_used"], attempt)
                self.assertFalse(blocker["direct_retry_budget_exhausted"])
                self.assertTrue(self.handle_pending_control_blocker(root))
            else:
                self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
                self.assertEqual(blocker["target_role"], "project_manager")
                self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
                self.assertEqual(blocker["direct_retry_attempts_used"], 2)
                self.assertTrue(blocker["direct_retry_budget_exhausted"])
                self.assertEqual(blocker["allowed_resolution_events"], ["pm_records_control_blocker_repair_decision"])

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        attempts = state["blocker_repair_attempts"][blockers[-1]["attempt_key"]]
        self.assertTrue(attempts["direct_retry_budget_exhausted"])
        self.assertEqual(attempts["latest_target_role"], "project_manager")
    def test_pm_semantic_control_blocker_zero_retry_budget_is_exhausted(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))

        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action while reviewer gate result is waiting",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )

        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["policy_row_id"], "pm_semantic_repair")
        self.assertEqual(blocker["direct_retry_budget"], 0)
        self.assertEqual(blocker["direct_retry_attempts_used"], 0)
        self.assertTrue(blocker["direct_retry_budget_exhausted"])
    def test_already_recorded_event_can_resolve_delivered_control_blocker(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue-race")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed_race",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-1": "worker"},
                    },
                ),
            )

        reissued_payload = self.role_report_envelope(
            root,
            "reviews/current_node_result_reissued_before_blocker_delivery",
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "agent_role_map": {"agent-worker-1": "worker"},
            },
        )
        router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "pending")

        router.next_action(root)
        router.apply_action(root, "handle_control_blocker")
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")

        result = router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        self.assertTrue(result["already_recorded"])
        self.assertTrue(result["control_blocker_resolved"])
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["latest_control_blocker_path"])
        self.assertEqual(len(state["resolved_control_blockers"]), 1)
    def test_already_recorded_event_does_not_resolve_pm_required_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        state["events"].append(
            {
                "event": "host_records_manual_resume_binding",
                "summary": "Host recorded the active run manual-resume binding before PM startup work.",
                "payload": {},
                "recorded_at": "2026-05-05T00:00:00Z",
            }
        )
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_manual_resume_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["handling_lane"], "fatal_protocol_violation")

        self.assertTrue(self.handle_pending_control_blocker(root))
        result = router.record_external_event(root, "host_records_manual_resume_binding")

        self.assertTrue(result["already_recorded"])
        self.assertNotIn("control_blocker_resolved", result)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")
        self.assertEqual(state["latest_control_blocker_path"], blocker["blocker_artifact_path"])
    def test_already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        state["events"].append(
            {
                "event": "host_records_manual_resume_binding",
                "summary": "Host recorded the active run manual-resume binding before PM startup work.",
                "payload": {},
                "recorded_at": "2026-05-05T00:00:00Z",
            }
        )
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_manual_resume_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["handling_lane"], "fatal_protocol_violation")

        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_manual_resume_binding",
        )
        decision["repair_transaction"] = {"plan_kind": "await_existing_event"}
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/fatal_pm_repair_decision",
                decision,
            ),
        )

        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertIn("host_records_manual_resume_binding", state["active_control_blocker"]["allowed_resolution_events"])

        result = router.record_external_event(root, "host_records_manual_resume_binding")

        self.assertTrue(result["already_recorded"])
        self.assertTrue(result["control_blocker_resolved"])
        state = read_json(state_path)
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["latest_control_blocker_path"])
        self.assertEqual(len(state["resolved_control_blockers"]), 1)
    def test_fatal_control_blocker_rejects_pm_ordinary_waiver(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_manual_resume_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["policy_row_id"], "fatal_protocol_violation")
        self.assertTrue(blocker["hard_stop_conditions"])

        self.assertTrue(self.handle_pending_control_blocker(root))
        body = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_manual_resume_binding",
        )
        body["recovery_option"] = "allowed_waiver"
        body["return_gate"] = "host_records_manual_resume_binding"
        with self.assertRaisesRegex(router.RouterError, "not allowed by blocker policy"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "control_blocks/fatal_pm_waiver_rejected", body),
            )
    def test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: PM must repair route draft handoff",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/current-node.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "rerun_target must name a registered external event"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/invalid_pm_repair_decision",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision",
                    ),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotEqual(
            original.get("allowed_resolution_events"),
            ["router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"],
        )
        self.assertNotIn("pm_repair_rerun_target", original)
    def test_delivered_control_blocker_with_unsupported_invalid_wait_requires_pm_repair_resubmission(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: unsupported bad control wait",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/unsupported.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        artifact_path = self.control_blocker_path(root, blocker)
        artifact = read_json(artifact_path)
        artifact["pm_repair_decision_status"] = "recorded"
        artifact["pm_repair_rerun_target"] = "router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"
        artifact["allowed_resolution_events"] = [
            "router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"
        ]
        router.write_json(artifact_path, artifact)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["pm_records_control_blocker_repair_decision"])
        self.assertEqual(
            action["event_contract_issue"]["required_repair_command"],
            "pm_must_resubmit_control_blocker_repair_decision",
        )

    def test_delivered_control_blocker_with_empty_repair_transaction_requires_pm_repair_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["reviewer_worker_result_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="unsupported empty repair transaction has no event producer",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/empty-transaction.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        transaction_path = run_root / "control_blocks" / "repair_transactions" / "repair-tx-empty-role-reissue.json"
        transaction_path.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            transaction_path,
            {
                "schema_version": router.REPAIR_TRANSACTION_SCHEMA,
                "transaction_id": "repair-tx-empty-role-reissue",
                "run_id": run_root.name,
                "blocker_id": blocker["blocker_id"],
                "status": "committed",
                "plan_kind": "role_reissue",
                "execution_plan": {
                    "mode": "role_reissue",
                    "target_role": "human_like_reviewer",
                    "allowed_external_events": ["current_node_reviewer_blocks_result"],
                },
            },
        )
        artifact_path = self.control_blocker_path(root, blocker)
        artifact = read_json(artifact_path)
        artifact["pm_repair_decision_status"] = "recorded"
        artifact["pm_repair_rerun_target"] = "current_node_reviewer_blocks_result"
        artifact["allowed_resolution_events"] = ["current_node_reviewer_blocks_result"]
        artifact["repair_transaction_id"] = "repair-tx-empty-role-reissue"
        artifact["repair_transaction_path"] = self.rel(root, transaction_path)
        router.write_json(artifact_path, artifact)
        state = read_json(state_path)
        state["active_control_blocker"].update(
            {
                "pm_repair_decision_status": "recorded",
                "pm_repair_rerun_target": "current_node_reviewer_blocks_result",
                "allowed_resolution_events": ["current_node_reviewer_blocks_result"],
                "repair_transaction_id": "repair-tx-empty-role-reissue",
                "repair_transaction_path": self.rel(root, transaction_path),
            }
        )
        router.save_run_state(run_root, state)

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["allowed_external_events"], ["pm_records_control_blocker_repair_decision"])
        self.assertEqual(action["event_contract_issue"]["reason"], "repair_transaction_missing_producer_evidence")
        self.assertEqual(
            action["event_contract_issue"]["required_repair_command"],
            "pm_must_resubmit_control_blocker_repair_decision",
        )
    def test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it(self) -> None:
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
            source="test",
            error_message="packet group reviewer audit failed: route draft needs PM reissue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/route-draft.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/valid_route_draft_pm_repair_decision",
                self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
            ),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(
            set(action["allowed_external_events"]),
            {
                "pm_writes_route_draft",
                "pm_records_control_blocker_followup_blocker",
                "pm_records_control_blocker_protocol_blocker",
            },
        )
    def test_repair_transaction_recheck_blocker_registers_followup_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="current route draft repair requires an independently reviewed retry",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/current-route-draft.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/current_route_draft_repair_for_blocker_outcome",
                self.pm_control_blocker_decision_body(
                    blocker["blocker_id"],
                    decision="repair_completed",
                    rerun_target="pm_writes_route_draft",
                ),
            ),
        )

        router.record_external_event(
            root,
            "pm_records_control_blocker_followup_blocker",
            self.role_report_envelope(
                root,
                "control_blocks/current_route_draft_followup_blocker",
                {
                    "from_role": "project_manager",
                    "blockers": ["current route draft still fails the required review"],
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertNotEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(active["handling_lane"], "pm_repair_decision_required")
        self.assertIsNone(state["active_repair_transaction"])
        original = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(original["resolution_status"], "repair_transaction_blocker")
        tx_index = read_json(
            run_root
            / "control_blocks"
            / "repair_transactions"
            / "repair_transaction_index.json"
        )
        self.assertIsNone(tx_index["active_transaction"])
        transaction = read_json(root / tx_index["transactions"][0]["path"])
        self.assertEqual(transaction["status"], "blocked")
        self.assertEqual(transaction["followup_blocker_id"], active["blocker_id"])
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "handle_control_blocker")
    def test_repair_transaction_protocol_blocker_registers_followup_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="current route draft repair requires protocol-safe outcome handling",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/current-route-protocol.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/current_route_draft_repair_for_protocol_outcome",
                self.pm_control_blocker_decision_body(
                    blocker["blocker_id"],
                    decision="repair_completed",
                    rerun_target="pm_writes_route_draft",
                ),
            ),
        )

        router.record_external_event(
            root,
            "pm_records_control_blocker_protocol_blocker",
            self.role_report_envelope(
                root,
                "control_blocks/current_route_draft_protocol_blocker",
                {
                    "from_role": "project_manager",
                    "blockers": ["current route draft repair exposed a protocol blocker"],
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertNotEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(active["handling_lane"], "pm_repair_decision_required")
        self.assertIsNone(state["active_repair_transaction"])
        original = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(
            original["resolution_status"], "repair_transaction_protocol_blocker"
        )
        tx_index = read_json(
            run_root
            / "control_blocks"
            / "repair_transactions"
            / "repair_transaction_index.json"
        )
        self.assertIsNone(tx_index["active_transaction"])
        transaction = read_json(root / tx_index["transactions"][0]["path"])
        self.assertEqual(transaction["status"], "blocked")
        self.assertEqual(transaction["followup_blocker_id"], active["blocker_id"])
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "handle_control_blocker")
    def test_pm_repair_decision_state_persists_before_followup_wait_is_exposed(self) -> None:
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
            source="test",
            error_message="current route draft handoff requires a PM repair decision",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/current-node-block.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/persisted_before_wait_pm_repair_decision",
                self.pm_control_blocker_decision_body(
                    blocker["blocker_id"],
                    rerun_target="pm_writes_route_draft",
                ),
            ),
        )

        persisted = read_json(state_path)
        self.assertTrue(persisted["flags"]["pm_control_blocker_repair_decision_recorded"])
        self.assertEqual(
            persisted["active_control_blocker"]["pm_repair_decision_status"],
            "recorded",
        )
        self.assertEqual(
            persisted["active_control_blocker"]["pm_repair_rerun_target"],
            "pm_writes_route_draft",
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_route_draft", action["allowed_external_events"])
        self.assertTrue(read_json(state_path)["flags"]["pm_control_blocker_repair_decision_recorded"])
    def test_pm_repair_decision_rejects_unsupported_event_replay_plan_kind(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="PM submitted a unsupported replay plan kind",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_manual_resume_binding",
        )
        decision["repair_transaction"] = {"plan_kind": "event_replay"}

        with self.assertRaisesRegex(router.RouterError, "repair_transaction.plan_kind must be one of"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "control_blocks/unsupported_event_replay_plan_kind", decision),
            )
    def test_operation_replay_repair_transaction_queues_replay_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Recorded mail delivery operation needs safe replay",
            action_type="deliver_mail",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_manual_resume_binding",
        )
        decision["repair_transaction"] = {
            "plan_kind": "operation_replay",
            "operation_ref": {
                "operation_kind": "controller_action",
                "action_type": "deliver_mail",
            },
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/operation_replay_pm_repair_decision", decision),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["repair_transaction_id"], read_json(router.run_state_path(run_root))["active_control_blocker"]["repair_transaction_id"])
        self.assertEqual(action["repair_execution_plan"]["mode"], "operation_replay")
    def test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: route draft needs PM reissue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/route-draft-not-ready.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "pm_writes_route_draft: event requires unsatisfied flag"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/not_receivable_route_draft_pm_repair_decision",
                    self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", original)
    def test_pm_repair_decision_can_repeat_for_new_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["reviewer_worker_result_card_delivered"] = True
        router.save_run_state(run_root, state)
        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: first reviewer audit issue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/first.json"},
        )
        self.assertEqual(first["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        first_decision = self.pm_control_blocker_decision_body(
            first["blocker_id"],
            rerun_target="current_node_reviewer_blocks_result",
        )
        first_decision["repair_transaction"] = {"plan_kind": "await_existing_event"}
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/first_pm_repair_decision",
                first_decision,
            ),
        )

        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], first["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: second reviewer audit issue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/second.json"},
        )
        self.assertEqual(second["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        second_decision = self.pm_control_blocker_decision_body(
            second["blocker_id"],
            rerun_target="current_node_reviewer_blocks_result",
        )
        second_decision["repair_transaction"] = {"plan_kind": "await_existing_event"}
        result = router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/second_pm_repair_decision",
                second_decision,
            ),
        )

        self.assertNotIn("already_recorded", result)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], second["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertTrue((run_root / "control_blocks" / f"{second['blocker_id']}.pm_repair_decision.json").exists())
    def test_same_family_pending_pm_control_blocker_reuses_existing_artifact(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        error = "Controller has no legal next action while reviewer gate result is waiting"

        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            read_json(state_path),
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )

        self.assertEqual(second["blocker_id"], first["blocker_id"])
        self.assertEqual(second["same_family_reuse_count"], 1)
        blocker_artifacts = [
            path
            for path in (run_root / "control_blocks").glob("control-blocker-*.json")
            if not path.name.endswith(".sealed_repair_packet.json")
        ]
        self.assertEqual(len(blocker_artifacts), 1)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], first["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["family_key"], first["family_key"])
    def test_same_family_delivered_pm_control_blocker_reuses_existing_artifact(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        error = "Controller has no legal next action while reviewer gate result is waiting"

        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            read_json(state_path),
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )

        self.assertEqual(second["blocker_id"], first["blocker_id"])
        self.assertEqual(second["delivery_status"], "delivered")
        self.assertEqual(second["same_family_reuse_count"], 1)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], first["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")
    def test_distinct_pm_control_blocker_causes_create_distinct_families(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)

        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: first reviewer audit issue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/first.json"},
        )
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            read_json(state_path),
            source="test",
            error_message="packet group reviewer audit failed: second reviewer audit issue",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/second.json"},
        )

        self.assertNotEqual(second["blocker_id"], first["blocker_id"])
        self.assertNotEqual(second["family_key"], first["family_key"])
        blocker_artifacts = [
            path
            for path in (run_root / "control_blocks").glob("control-blocker-*.json")
            if not path.name.endswith(".sealed_repair_packet.json")
        ]
        self.assertEqual(len(blocker_artifacts), 2)
    def test_protocol_dead_end_terminal_family_suppresses_reopened_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        error = "Controller has no legal next action while reviewer gate result is waiting"

        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            decision="repair_not_required",
            rerun_target="",
        )
        decision["recovery_option"] = "protocol_dead_end"
        decision["return_gate"] = "terminal_stop"
        decision["repair_transaction"] = {
            "plan_kind": "terminal_stop",
            "terminal_reason": "PM found no legal recovery path for this control blocker family.",
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/protocol_dead_end_pm_repair_decision", decision),
        )

        state = read_json(state_path)
        self.assertEqual(state["status"], "protocol_dead_end")
        self.assertIsNone(state["active_control_blocker"])
        self.assertTrue(state["flags"]["control_blocker_protocol_dead_end_declared"])
        self.assertTrue((run_root / "lifecycle" / "control_blocker_protocol_dead_end.json").exists())

        reopened = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message=error,
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )

        self.assertEqual(reopened["blocker_id"], blocker["blocker_id"])
        self.assertEqual(reopened["resolution_status"], "repair_transaction_terminal_stop")
        state = read_json(state_path)
        self.assertEqual(state["status"], "protocol_dead_end")
        self.assertIsNone(state["active_control_blocker"])
        self.assertIn(blocker["family_key"], state["control_blocker_family_terminal_dispositions"])
    def test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))

        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: ['result_body_not_opened_by_reviewer_or_pm_after_relay_check']",
            event="current_node_reviewer_blocks_result",
            payload={"report_path": ".flowpilot/runs/test/reviews/current-node.json"},
        )

        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "human_like_reviewer")
        self.assertFalse(blocker["pm_decision_required"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "human_like_reviewer")

