from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class AckReturnRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_router_daemon_tick_consumes_card_ack_without_manual_next(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        while True:
            action = self.next_after_display_sync(root)
            if action["action_type"] in {
                "confirm_controller_core_boundary",
                "check_prompt_manifest",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
            }:
                router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
                continue
            self.assertIn(action["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})
            break

        self.submit_system_card_ack_without_router_next(root, action)
        before = read_json(router.run_state_path(run_root))
        self.assertEqual(before["pending_action"]["action_type"], action["action_type"])

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        after = read_json(router.run_state_path(run_root))
        labels = [item["label"] for item in after["history"] if isinstance(item, dict)]
        self.assertTrue(
            {
                "router_auto_consumed_card_return_ack",
                "router_return_settlement_cleared_pending_card_bundle_wait",
            }
            & set(labels)
        )
        self.assertNotEqual((after.get("pending_action") or {}).get("action_id"), action.get("action_id"))
    def test_router_daemon_invalid_card_ack_variants_do_not_advance(self) -> None:
        variants = {
            "wrong_role": lambda ack: ack.update({"role_key": "project_manager"}),
            "wrong_hash": lambda ack: ack.update({"card_envelope_hash": "0" * 64}),
        }
        for variant, mutate in variants.items():
            with self.subTest(variant=variant):
                root = self.make_project()
                run_root = self.boot_to_controller(root)
                self.release_startup_daemon_for_explicit_daemon_test(root)
                action = self.deliver_startup_fact_check_card_without_ack(root)
                open_result = card_runtime.open_card(
                    root,
                    envelope_path=str(action["card_envelope_path"]),
                    role=str(action["to_role"]),
                    agent_id=str(action["target_agent_id"]),
                )
                card_runtime.submit_card_ack(
                    root,
                    envelope_path=str(action["card_envelope_path"]),
                    role=str(action["to_role"]),
                    agent_id=str(action["target_agent_id"]),
                    receipt_paths=[str(open_result["read_receipt_path"])],
                )
                ack_path = root / action["expected_return_path"]
                ack = read_json(ack_path)
                mutate(ack)
                ack["ack_hash"] = card_runtime.stable_json_hash(ack)
                router.write_json(ack_path, ack)

                result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

                self.assertEqual(result["ticks"][0]["action_type"], "check_card_return_event")
                state = read_json(router.run_state_path(run_root))
                self.assertFalse(state["flags"]["startup_fact_reported"])
                self.assertEqual(state["pending_action"]["action_type"], "check_card_return_event")
                labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
                self.assertIn("router_deferred_invalid_card_ack_to_explicit_check", labels)
                return_ledger = read_json(run_root / "return_event_ledger.json")
                self.assertNotEqual(return_ledger["pending_returns"][0].get("status"), "resolved")
    def test_router_daemon_incomplete_bundle_ack_waits_without_advancing(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")

        role = str(action["to_role"])
        agent_id = str(action["target_agent_id"])
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        envelope = read_json(root / action["card_bundle_envelope_path"])
        receipt_refs = []
        for receipt_path in opened["read_receipt_paths"][:-1]:
            receipt = read_json(root / receipt_path)
            receipt_refs.append(
                {
                    "receipt_path": receipt_path,
                    "receipt_hash": receipt["receipt_hash"],
                    "card_id": receipt["card_id"],
                    "delivery_id": receipt["delivery_id"],
                    "delivery_attempt_id": receipt["delivery_attempt_id"],
                    "card_hash": receipt["card_hash"],
                    "opened_at": receipt["opened_at"],
                }
            )
        incomplete_ack = {
            "schema_version": card_runtime.CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
            "run_id": envelope["run_id"],
            "resume_tick_id": envelope["resume_tick_id"],
            "role_key": role,
            "agent_id": agent_id,
            "card_return_event": envelope["card_return_event"],
            "status": "acknowledged",
            "card_bundle_id": envelope["bundle_id"],
            "card_bundle_envelope_path": action["card_bundle_envelope_path"],
            "card_bundle_envelope_hash": card_runtime.stable_json_hash(envelope),
            "ack_delivery_mode": "direct_to_router",
            "submitted_to": "router",
            "controller_ack_handoff_used": False,
            "direct_router_ack_token": envelope["direct_router_ack_token"],
            "direct_router_ack_token_hash": envelope["direct_router_ack_token_hash"],
            "acknowledged_bundle": envelope["bundle_id"],
            "acknowledged_envelopes": [envelope["bundle_id"]],
            "member_card_ids": envelope["card_ids"][:-1],
            "receipt_refs": receipt_refs,
            "body_visibility": "ack_envelope_only",
            "contains_card_body": False,
            "runtime_validates_mechanics_only": True,
            "semantic_understanding_validated": False,
            "returned_at": card_runtime.utc_now(),
        }
        incomplete_ack["ack_hash"] = card_runtime.stable_json_hash(incomplete_ack)
        router.write_json(root / action["expected_return_path"], incomplete_ack)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["ticks"][0]["action_type"], "await_card_bundle_return_event")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["pending_action"]["action_type"], "await_card_bundle_return_event")
        self.assertTrue(state["pending_action"]["bundle_ack_incomplete"])
        self.assertEqual(state["pending_action"]["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item
            for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")
    def test_router_daemon_duplicate_stale_card_ack_is_idempotent(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        action = self.deliver_startup_fact_check_card_without_ack(root)
        self.submit_system_card_ack_without_router_next(root, action)

        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        return_ledger = read_json(run_root / "return_event_ledger.json")
        completed = [
            item
            for item in return_ledger["completed_returns"]
            if item.get("delivery_attempt_id") == action["delivery_attempt_id"]
        ]
        self.assertEqual(len(completed), 1)
    def test_recorded_external_event_closes_matching_wait_action_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_wait_closure",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["wait_closure"]["changed"])
        state = read_json(router.run_state_path(run_root))
        action_id = wait_action["controller_action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["status"], "done")
        self.assertEqual(action_record["completion_source"], "router_external_event_reconciliation")
        self.assertEqual(action_record["satisfied_by_external_event"], "reviewer_reports_startup_facts")
        self.assertFalse(action_record["controller_receipt_required"])
        self.assert_controller_receipt_entry_projection(
            action_record,
            receipt_required=False,
            router_pending_apply_required=False,
        )
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        waiting_ids = [item["action_id"] for item in ledger["actions"] if item["status"] == "waiting"]
        self.assertNotIn(action_id, waiting_ids)
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), action_id)
    def test_already_recorded_external_event_closes_stale_wait_action_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        payload = self.role_report_envelope(
            root,
            "startup/reviewer_startup_fact_report_already_recorded_wait_closure",
            self.startup_fact_report_body(root),
        )
        first = router.record_external_event(root, "reviewer_reports_startup_facts", payload)
        self.assertTrue(first["ok"])

        state = read_json(router.run_state_path(run_root))
        stale_wait = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label="test_stale_wait_for_already_recorded_startup_facts",
            summary="Test stale wait row that should be closed by replayed event evidence.",
            to_role="human_like_reviewer",
            extra={
                "waiting_for_role": "human_like_reviewer",
                "allowed_external_events": ["reviewer_reports_startup_facts"],
            },
        )
        state["pending_action"] = stale_wait
        entry = router._write_controller_action_entry(root, run_root, state, stale_wait)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        replay = router.record_external_event(root, "reviewer_reports_startup_facts", payload)

        self.assertTrue(replay["already_recorded"])
        self.assertTrue(replay["wait_closure"]["changed"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["status"], "done")
        self.assertEqual(action_record["completion_source"], "router_external_event_reconciliation")
        self.assertEqual(action_record["satisfied_by_external_event"], "reviewer_reports_startup_facts")
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), entry["action_id"])
    def test_record_external_event_preconsumes_valid_card_ack_before_blocking(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_fact_reported"])
        self.assertIn(
            "router_pre_consumed_card_return_ack_before_external_event",
            [item.get("label") for item in state["history"] if isinstance(item, dict)],
        )
        return_ledger = read_json(run_root / "return_event_ledger.json")
        pending = return_ledger["pending_returns"][0]
        self.assertEqual(pending["status"], "resolved")
        completed = [
            item for item in return_ledger["completed_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ]
        self.assertEqual(len(completed), 1)
    def test_record_external_event_does_not_preconsume_incomplete_bundle_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")

        role = str(action["to_role"])
        agent_id = str(action["target_agent_id"])
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        envelope_path = root / action["card_bundle_envelope_path"]
        envelope = read_json(envelope_path)
        receipt_refs = []
        for receipt_path in opened["read_receipt_paths"][:-1]:
            receipt = read_json(root / receipt_path)
            receipt_refs.append(
                {
                    "receipt_path": receipt_path,
                    "receipt_hash": receipt["receipt_hash"],
                    "card_id": receipt["card_id"],
                    "delivery_id": receipt["delivery_id"],
                    "delivery_attempt_id": receipt["delivery_attempt_id"],
                    "card_hash": receipt["card_hash"],
                    "opened_at": receipt["opened_at"],
                }
            )
        incomplete_ack = {
            "schema_version": card_runtime.CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
            "run_id": envelope["run_id"],
            "resume_tick_id": envelope["resume_tick_id"],
            "role_key": role,
            "agent_id": agent_id,
            "card_return_event": envelope["card_return_event"],
            "status": "acknowledged",
            "card_bundle_id": envelope["bundle_id"],
            "card_bundle_envelope_path": action["card_bundle_envelope_path"],
            "card_bundle_envelope_hash": card_runtime.stable_json_hash(envelope),
            "ack_delivery_mode": "direct_to_router",
            "submitted_to": "router",
            "controller_ack_handoff_used": False,
            "direct_router_ack_token": envelope["direct_router_ack_token"],
            "direct_router_ack_token_hash": envelope["direct_router_ack_token_hash"],
            "acknowledged_bundle": envelope["bundle_id"],
            "acknowledged_envelopes": [envelope["bundle_id"]],
            "member_card_ids": envelope["card_ids"][:-1],
            "receipt_refs": receipt_refs,
            "body_visibility": "ack_envelope_only",
            "contains_card_body": False,
            "runtime_validates_mechanics_only": True,
            "semantic_understanding_validated": False,
            "returned_at": card_runtime.utc_now(),
        }
        incomplete_ack["ack_hash"] = card_runtime.stable_json_hash(incomplete_ack)
        router.write_json(root / action["expected_return_path"], incomplete_ack)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["startup_pre_review_ack_join_blocked"])
        self.assertEqual(result["next_required_action"]["action_type"], "await_current_scope_reconciliation")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(state.get("quarantined_role_reports"), [])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == action.get("card_bundle_id")
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")
    def test_record_external_event_quarantines_missing_same_role_ack_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["report_quarantined"])
        self.assertTrue(result["recoverable"])
        quarantine_path = root / result["quarantine_path"]
        self.assertTrue(quarantine_path.exists())
        quarantine = read_json(quarantine_path)
        self.assertEqual(quarantine["status"], "quarantined_audit_only")
        self.assertFalse(quarantine["recovery"]["old_report_may_be_used_as_acceptance_evidence"])
        self.assertEqual(quarantine["pending_return"]["delivery_attempt_id"], action["delivery_attempt_id"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertIsNone(state.get("active_control_blocker"))
        self.assertEqual(state["pending_action"]["action_type"], "await_card_return_event")
        self.assertEqual(state["quarantined_role_reports"][0]["quarantine_path"], result["quarantine_path"])
        self.assertIn(
            "router_quarantined_pre_ack_role_report_for_same_role_ack_recovery",
            [item.get("label") for item in state["history"] if isinstance(item, dict)],
        )
    def test_quarantined_pre_ack_report_requires_fresh_report_after_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        quarantined = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertTrue(quarantined["report_quarantined"])

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        router.next_action(root)

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(len([item for item in state["events"] if item.get("event") == "reviewer_reports_startup_facts"]), 0)

        accepted = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_post_ack",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(accepted["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_fact_reported"])
        self.assertEqual(len([item for item in state["events"] if item.get("event") == "reviewer_reports_startup_facts"]), 1)
    def test_record_event_rejects_bad_event_envelope_refs_before_payload_reconstruction(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)

        with self.assertRaisesRegex(router.RouterError, "hash mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": "0" * 64}},
            )

        missing_ref = {"event_envelope_ref": {"path": ".flowpilot/runs/missing/events/nope.envelope.json", "hash": envelope_hash}}
        with self.assertRaisesRegex(router.RouterError, "file is missing"):
            router.record_external_event(root, "reviewer_reports_startup_facts", missing_ref)

        outside_path = root.parent / f"{root.name}-outside-event.envelope.json"
        outside_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.addCleanup(lambda: outside_path.unlink(missing_ok=True))
        with self.assertRaisesRegex(router.RouterError, "outside project root"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {
                    "event_envelope_ref": {
                        "path": str(outside_path),
                        "hash": hashlib.sha256(outside_path.read_bytes()).hexdigest(),
                    }
                },
            )

        bad_schema = dict(envelope)
        bad_schema["schema_version"] = "flowpilot.untrusted_event_envelope.v0"
        bad_schema_path, bad_schema_hash = self.write_event_envelope(root, "startup/bad_schema", bad_schema)
        with self.assertRaisesRegex(router.RouterError, "schema_version"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_schema_path, "hash": bad_schema_hash}},
            )

        bad_event = dict(envelope)
        bad_event["event_name"] = "pm_issues_material_and_capability_scan_packets"
        bad_event_path, bad_event_hash = self.write_event_envelope(root, "startup/bad_event", bad_event)
        with self.assertRaisesRegex(router.RouterError, "event mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_event_path, "hash": bad_event_hash}},
            )

        bad_role = dict(envelope)
        bad_role["from_role"] = "project_manager"
        bad_role_path, bad_role_hash = self.write_event_envelope(root, "startup/bad_role", bad_role)
        with self.assertRaisesRegex(router.RouterError, "from_role mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_role_path, "hash": bad_role_hash}},
            )

        bad_visibility = dict(envelope)
        bad_visibility["controller_visibility"] = "sealed_body_visible"
        bad_visibility_path, bad_visibility_hash = self.write_event_envelope(root, "startup/bad_visibility", bad_visibility)
        with self.assertRaisesRegex(router.RouterError, "controller_visibility"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_visibility_path, "hash": bad_visibility_hash}},
            )

        leaked = dict(envelope)
        leaked["recommendations"] = ["inline body content that belongs in the sealed report body"]
        leaked_path, leaked_hash = self.write_event_envelope(root, "startup/leaked_body", leaked)
        with self.assertRaisesRegex(router.RouterError, "leaked role body fields"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": leaked_path, "hash": leaked_hash}},
            )
    def test_record_event_rejects_envelope_outside_current_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)
        self.assertEqual(envelope["event_name"], "reviewer_reports_startup_facts")

        with self.assertRaisesRegex(router.RouterError, "not currently allowed"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
            )
    def test_dispatch_recipient_gate_classifies_ack_only_card_as_prompt(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-ack-only-card")
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_core_card_delivered",
            summary="Deliver an ACK-only PM core card.",
            card_id="pm.core",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "deliver_system_card")
        gate = gated["dispatch_recipient_gate"]
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["work_package_class"], "ack_only_prompt")
        self.assertEqual(gate["output_events"], [])
    def test_dispatch_recipient_gate_allows_work_after_resolved_ack_only_card_wait(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-resolved-ack-only-wait")
        state = read_json(router.run_state_path(run_root))
        wait_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_core_card_ack",
            summary="Controller waits for PM core card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "delivery_attempt_id": "pm-core-attempt",
                "card_id": "pm.core",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            },
        )
        wait_entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        wait_entry["status"] = "resolved"
        wait_entry["completed_at"] = router.utc_now()
        wait_entry["router_reconciliation_status"] = "reconciled"
        wait_entry["router_reconciliation"] = {"clearance_kind": "ack_wait_only"}
        router.write_json(root / wait_entry["action_path"], wait_entry)
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]

        action = router.make_action(
            action_type="deliver_mail",
            actor="controller",
            label="deliver_pm_mail_after_ack_only_wait",
            summary="Deliver PM mail after ACK-only card wait resolved.",
            mail_id="new-pm-mail",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)  # type: ignore[attr-defined]

        self.assertEqual(gated["action_type"], "deliver_mail")
        self.assertTrue(gated["dispatch_recipient_gate"]["passed"])
        self.assertEqual(gated["dispatch_recipient_gate"]["target_roles"], ["project_manager"])
    def test_dispatch_recipient_gate_keeps_output_work_busy_after_card_ack_only(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-output-card-ack-only")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["node_review_blocked"] = True
        state["flags"]["pm_model_miss_triage_card_delivered"] = True
        router.write_json(router.run_state_path(run_root), state)
        wait_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_model_miss_triage_card_ack",
            summary="Controller waits for PM model-miss triage card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "delivery_attempt_id": "pm-model-miss-triage-attempt",
                "card_id": "pm.model_miss_triage",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_model_miss_triage.ack.json",
            },
        )
        wait_entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        wait_entry["status"] = "resolved"
        wait_entry["completed_at"] = router.utc_now()
        wait_entry["router_reconciliation_status"] = "reconciled"
        wait_entry["router_reconciliation"] = {
            "clearance_kind": "ack_wait_only",
            "ack_does_not_complete_output_bearing_work": True,
        }
        router.write_json(root / wait_entry["action_path"], wait_entry)
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]

        route_action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_route_skeleton_phase_card_delivered",
            summary="Deliver an independent PM route card.",
            card_id="pm.route_skeleton",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, route_action)  # type: ignore[attr-defined]

        self.assertEqual(gated["action_type"], "await_role_decision")
        self.assertEqual(gated["to_role"], "project_manager")
        self.assertEqual(gated["allowed_external_events"], ["pm_records_model_miss_triage_decision"])
        gate = gated["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "pending_expected_output")
        self.assertEqual(gate["busy_reason"], "target_role_output_obligation_already_pending")
        self.assertEqual(gate["blocked_work_package_class"], "output_bearing_work_package")
